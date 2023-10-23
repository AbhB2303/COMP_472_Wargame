from __future__ import annotations
import argparse
import copy
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
from time import sleep
from typing import Tuple, TypeVar, Type, Iterable, ClassVar
import random
import requests

# maximum and minimum values for our heuristic scores (usually represents an end of game condition)
MAX_HEURISTIC_SCORE = 2000000000
MIN_HEURISTIC_SCORE = -2000000000

class UnitType(Enum):
    """Every unit type."""
    AI = 0
    Tech = 1
    Virus = 2
    Program = 3
    Firewall = 4

class Player(Enum):
    """The 2 players."""
    Attacker = 0
    Defender = 1

    def next(self) -> Player:
        """The next (other) player."""
        if self is Player.Attacker:
            return Player.Defender
        else:
            return Player.Attacker

class GameType(Enum):
    AttackerVsDefender = 0
    AttackerVsComp = 1
    CompVsDefender = 2
    CompVsComp = 3

##############################################################################################################

@dataclass()
class Unit:
    player: Player = Player.Attacker
    type: UnitType = UnitType.Program
    health : int = 9
    # class variable: damage table for units (based on the unit type constants in order)
    damage_table : ClassVar[list[list[int]]] = [
        [3,3,3,3,1], # AI
        [1,1,6,1,1], # Tech
        [9,6,1,6,1], # Virus
        [3,3,3,3,1], # Program
        [1,1,1,1,1], # Firewall
    ]
    # class variable: repair table for units (based on the unit type constants in order)
    repair_table : ClassVar[list[list[int]]] = [
        [0,1,1,0,0], # AI
        [3,0,0,3,3], # Tech
        [0,0,0,0,0], # Virus
        [0,0,0,0,0], # Program
        [0,0,0,0,0], # Firewall
    ]

    def is_alive(self) -> bool:
        """Are we alive ?"""
        return self.health > 0

    def mod_health(self, health_delta : int):
        """Modify this unit's health by delta amount."""
        self.health += health_delta
        if self.health < 0:
            self.health = 0
        elif self.health > 9:
            self.health = 9

    def to_string(self) -> str:
        """Text representation of this unit."""
        p = self.player.name.lower()[0]
        t = self.type.name.upper()[0]
        return f"{p}{t}{self.health}"

    def __str__(self) -> str:
        """Text representation of this unit."""
        return self.to_string()

    def damage_amount(self, target: Unit) -> int:
        """How much can this unit damage another unit."""
        amount = self.damage_table[self.type.value][target.type.value]
        if target.health - amount < 0:
            return target.health
        return amount

    def repair_amount(self, target: Unit) -> int:
        """How much can this unit repair another unit."""
        amount = self.repair_table[self.type.value][target.type.value]
        if target.health + amount > 9:
            return 9 - target.health
        return amount

##############################################################################################################

@dataclass()
class Coord:
    """Representation of a game cell coordinate (row, col)."""
    row : int = 0
    col : int = 0

    def col_string(self) -> str:
        """Text representation of this Coord's column."""
        coord_char = '?'
        if self.col < 16:
                coord_char = "0123456789abcdef"[self.col]
        return str(coord_char)

    def row_string(self) -> str:
        """Text representation of this Coord's row."""
        coord_char = '?'
        if self.row < 26:
                coord_char = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"[self.row]
        return str(coord_char)

    def to_string(self) -> str:
        """Text representation of this Coord."""
        return self.row_string()+self.col_string()

    def __str__(self) -> str:
        """Text representation of this Coord."""
        return self.to_string()

    def clone(self) -> Coord:
        """Clone a Coord."""
        return copy.copy(self)

    def iter_range(self, dist: int) -> Iterable[Coord]:
        """Iterates over Coords inside a rectangle centered on our Coord."""
        for row in range(self.row-dist,self.row+1+dist):
            for col in range(self.col-dist,self.col+1+dist):
                yield Coord(row,col)

    def iter_adjacent(self) -> Iterable[Coord]:
        """Iterates over adjacent Coords."""
        yield Coord(self.row-1,self.col)
        yield Coord(self.row,self.col-1)
        yield Coord(self.row+1,self.col)
        yield Coord(self.row,self.col+1)

    @classmethod
    def from_string(cls, s : str) -> Coord | None:
        """Create a Coord from a string. ex: D2."""
        s = s.strip()
        for sep in " ,.:;-_":
                s = s.replace(sep, "")
        if (len(s) == 2):
            coord = Coord()
            coord.row = "ABCDEFGHIJKLMNOPQRSTUVWXYZ".find(s[0:1].upper())
            coord.col = "0123456789abcdef".find(s[1:2].lower())
            return coord
        else:
            return None

##############################################################################################################

@dataclass()
class CoordPair:
    """Representation of a game move or a rectangular area via 2 Coords."""
    src : Coord = field(default_factory=Coord)
    dst : Coord = field(default_factory=Coord)

    def to_string(self) -> str:
        """Text representation of a CoordPair."""
        return self.src.to_string()+" "+self.dst.to_string()

    def __str__(self) -> str:
        """Text representation of a CoordPair."""
        return self.to_string()

    def clone(self) -> CoordPair:
        """Clones a CoordPair."""
        return copy.copy(self)

    def iter_rectangle(self) -> Iterable[Coord]:
        """Iterates over cells of a rectangular area."""
        for row in range(self.src.row,self.dst.row+1):
            for col in range(self.src.col,self.dst.col+1):
                yield Coord(row,col)

    @classmethod
    def from_quad(cls, row0: int, col0: int, row1: int, col1: int) -> CoordPair:
        """Create a CoordPair from 4 integers."""
        return CoordPair(Coord(row0,col0),Coord(row1,col1))

    @classmethod
    def from_dim(cls, dim: int) -> CoordPair:
        """Create a CoordPair based on a dim-sized rectangle."""
        return CoordPair(Coord(0,0),Coord(dim-1,dim-1))

    @classmethod
    def from_string(cls, s : str) -> CoordPair | None:
        """Create a CoordPair from a string. ex: A3 B2"""
        s = s.strip()
        for sep in " ,.:;-_":
                s = s.replace(sep, "")
        if (len(s) == 4):
            coords = CoordPair()
            coords.src.row = "ABCDEFGHIJKLMNOPQRSTUVWXYZ".find(s[0:1].upper())
            coords.src.col = "0123456789abcdef".find(s[1:2].lower())
            coords.dst.row = "ABCDEFGHIJKLMNOPQRSTUVWXYZ".find(s[2:3].upper())
            coords.dst.col = "0123456789abcdef".find(s[3:4].lower())
            return coords
        else:
            return None

##############################################################################################################

@dataclass()
class Options:
    """Representation of the game options."""
    dim: int = 5
    max_depth : int | None = 4
    min_depth : int | None = 2
    max_time : float | None = 5.0
    game_type : GameType = GameType.AttackerVsDefender
    alpha_beta : bool = False
    max_turns : int | None = 100
    randomize_moves : bool = False
    broker : str | None = None
    heuristic : int = 0

##############################################################################################################

@dataclass()
class Stats:
    """Representation of the global game statistics."""
    evaluations_per_depth : dict[int,int] = field(default_factory=dict)
    total_seconds: float = 0.0

##############################################################################################################

@dataclass()
class Game:
    """Representation of the game state."""
    board: list[list[Unit | None]] = field(default_factory=list)
    next_player: Player = Player.Attacker
    turns_played : int = 0
    options: Options = field(default_factory=Options)
    stats: Stats = field(default_factory=Stats)
    _attacker_has_ai : bool = True
    _defender_has_ai : bool = True

    def __post_init__(self):
        """Automatically called after class init to set up the default board state."""
        dim = self.options.dim
        self.board = [[None for _ in range(dim)] for _ in range(dim)]
        md = dim-1
        self.set(Coord(0,0),Unit(player=Player.Defender,type=UnitType.AI))
        self.set(Coord(1,0),Unit(player=Player.Defender,type=UnitType.Tech))
        self.set(Coord(0,1),Unit(player=Player.Defender,type=UnitType.Tech))
        self.set(Coord(2,0),Unit(player=Player.Defender,type=UnitType.Firewall))
        self.set(Coord(0,2),Unit(player=Player.Defender,type=UnitType.Firewall))
        self.set(Coord(1,1),Unit(player=Player.Defender,type=UnitType.Program))
        self.set(Coord(md,md),Unit(player=Player.Attacker,type=UnitType.AI))
        self.set(Coord(md-1,md),Unit(player=Player.Attacker,type=UnitType.Virus))
        self.set(Coord(md,md-1),Unit(player=Player.Attacker,type=UnitType.Virus))
        self.set(Coord(md-2,md),Unit(player=Player.Attacker,type=UnitType.Program))
        self.set(Coord(md,md-2),Unit(player=Player.Attacker,type=UnitType.Program))
        self.set(Coord(md-1,md-1),Unit(player=Player.Attacker,type=UnitType.Firewall))

    def clone(self) -> Game:
        """Make a new copy of a game for minimax recursion.

        Shallow copy of everything except the board (options and stats are shared).
        """
        new = copy.copy(self)
        new.board = copy.deepcopy(self.board)
        return new

    def is_empty(self, coord : Coord) -> bool:
        """Check if contents of a board cell of the game at Coord is empty (must be valid coord)."""
        return self.board[coord.row][coord.col] is None

    def get(self, coord : Coord) -> Unit | None:
        """Get contents of a board cell of the game at Coord."""
        if self.is_valid_coord(coord):
            return self.board[coord.row][coord.col]
        else:
            return None

    def set(self, coord : Coord, unit : Unit | None):
        """Set contents of a board cell of the game at Coord."""
        if self.is_valid_coord(coord):
            self.board[coord.row][coord.col] = unit

    def remove_dead(self, coord: Coord):
        """Remove unit at Coord if dead."""
        unit = self.get(coord)
        if unit is not None and not unit.is_alive():
            self.set(coord,None)
            if unit.type == UnitType.AI:
                if unit.player == Player.Attacker:
                    self._attacker_has_ai = False
                else:
                    self._defender_has_ai = False

    def mod_health(self, coord : Coord, health_delta : int):
        """Modify health of unit at Coord (positive or negative delta)."""
        target = self.get(coord)
        if target is not None:
            target.mod_health(health_delta)
            self.remove_dead(coord)

    def movement_disabled_from_combat(self, coords : CoordPair, unit : Unit) -> bool:
        """Check if the unit is in combat"""
        # check if adversarial unit in any of 4 directions
        # AI, firewall, or program can not move if engaged (return false)
        type = unit.type
        unit_player = unit.player
        unit_src = coords.src
        if (type == UnitType.Program or type == UnitType.Firewall or type == UnitType.AI):
            adjacent = unit_src.iter_adjacent()
            for cell in adjacent:
                # if cell is adversary, unit is in combat => return false
                val = self.get(cell)
                if not val is None:
                    if val.player != unit_player:
                        return True
            return False
        else:
            return False

    def restricted_movement(self, coords : CoordPair) -> bool:
        """Whether the intended move is restricted for this unit"""
        type = self.get(coords.src).type
        unit_player = self.get(coords.src).player
        unit_src = coords.src
        unit_dst = coords.dst
        if (unit_src == unit_dst):
            # self destruct - valid for any unit
            return True

        if (type == UnitType.Program or type == UnitType.Firewall or type == UnitType.AI):
            # if attacker, can only move up or left
            if (unit_player == Player.Attacker):
                if ((unit_dst.row == unit_src.row - 1 and unit_dst.col == unit_src.col) or (unit_dst.row == unit_src.row and unit_dst.col == unit_src.col - 1)):
                    return False
                return True
            # if defender, can only move down or right
            if (unit_player == Player.Defender):
                if ((unit_dst.row == unit_src.row + 1 and unit_dst.col == unit_src.col) or (unit_dst.row == unit_src.row and unit_dst.col == unit_src.col + 1)):
                    return False
                return True
        elif (type == UnitType.Tech or type == UnitType.Virus):
            adj_cells = unit_src.iter_adjacent()
            for cell in adj_cells:
                if cell == unit_dst:
                    return False
            return True

        return False

    def handle_attack(self, coords: CoordPair, do_action: bool = True) -> bool:

        attacker_unit = self.get(coords.src)
        defender_unit = self.get(coords.dst)

        # Check if attacking opposing unit
        if defender_unit is None or attacker_unit is None:
            return False

        if attacker_unit.player == defender_unit.player:
            return False

        if attacker_unit.player != self.next_player:
            return False

        surrounding_cells = coords.src.iter_adjacent()
        # check if attacking adjacent unit
        for cell in surrounding_cells:
            if self.get(cell) == defender_unit:
                if do_action:
                    # Calculations for Damage from both units
                    attacker_damage = attacker_unit.damage_amount(defender_unit)
                    defender_damage = defender_unit.damage_amount(attacker_unit)

                    # Have both units damaged
                    defender_unit.mod_health(-attacker_damage)
                    attacker_unit.mod_health(-defender_damage)
                    self.remove_dead(coords.dst)
                    self.remove_dead(coords.src)
                return True
        return False

    # ATTEMPT for the REPAIR
    def handle_repair(self, coords: CoordPair, do_action: bool = True) -> bool:
        # we need to check the repair for the player
        unit_src = self.get(coords.src)
        unit_dst = self.get(coords.dst)

        if unit_src and unit_dst:
            if unit_src.player != self.next_player and unit_dst.player != unit_dst:
                return False


        if unit_src is not None and unit_dst is not None and unit_src != unit_dst:
            # what if the units for destination and source are same
            if unit_src.player == unit_dst.player:
                if coords.dst in coords.src.iter_adjacent():
                    repair_amount = unit_src.repair_amount(unit_dst)
                    # we have to make sure that destination is not at health 9
                    if repair_amount > 0:
                        if unit_dst.health < 9:
                            if do_action:
                                unit_dst.mod_health(repair_amount)
                            return True
        return False

    def handle_self_destruct(self, coords: CoordPair, do_action: bool = True) -> bool:
        unit = self.get(coords.src)
        if (coords.src == coords.dst and unit is not None and unit.player == self.next_player):
            if do_action:
                surrounding_cells = coords.src.iter_range(1)
                destruct_unit = self.get(coords.src)
                destruct_unit.mod_health(-9)
                self.remove_dead(coords.src)
                for cell in surrounding_cells:
                    unit = self.get(cell)
                    if unit is not None:
                        unit.mod_health(-2)
                        self.remove_dead(cell)
            return True
        return False

    def is_valid_move(self, coords : CoordPair) -> bool:
        """Validate a move expressed as a CoordPair. TODO: WRITE MISSING CODE!!!"""
        # check if in bounds
        if not self.is_valid_coord(coords.src) or not self.is_valid_coord(coords.dst):
            return False
        # check if src belongs to next player
        unit = self.get(coords.src)
        if unit is None or unit.player != self.next_player:
            return False
        # check if unit is engaged in combat
        if self.movement_disabled_from_combat(coords, unit):
            return False
        # check if move is valid for this specific unit
        if self.restricted_movement(coords):
            return False
        unit = self.get(coords.dst)
        return (unit is None)

    def perform_move(self, coords: CoordPair, trace_file=None) -> Tuple[bool, str]:
        """Validate and perform a move expressed as a CoordPair. Returns success, move."""
        
        if self.is_valid_move(coords):
            self.set(coords.dst, self.get(coords.src))
            self.set(coords.src, None)
            if trace_file:
                trace_file.write("move: " + str(coords.to_string()))
                print("\nmove: " + str(coords.to_string()) + "\n")
            return (True, "move")
        
        # Check and handle if move is an attack
        if self.handle_attack(coords):
            if trace_file:
                trace_file.write("attack: " + str(coords.to_string()))
                print("\nattack: " + str(coords.to_string()) + "\n")
            return (True, "attack")
        
        # Check and handle if move is a repair
        if self.handle_repair(coords):
            if trace_file:
                trace_file.write("repair: " + str(coords.to_string()))
                print("repair: " + str(coords.to_string()) + "\n")
            return (True, "repair")
        
        if self.handle_self_destruct(coords):
            if trace_file:
                trace_file.write("self-destruct: " + str(coords.to_string()))
                print("self-destruct: " + str(coords.to_string()) + "\n")
            return (True, "self-destruct")

        return (False, "invalid move")

    def next_turn(self):
        """Transitions game to the next turn."""
        self.next_player = self.next_player.next()
        self.turns_played += 1

    def to_string(self) -> str:
        """Pretty text representation of the game."""
        dim = self.options.dim
        output = ""
        output += f"Next player: {self.next_player.name}\n"
        output += f"Turns played: {self.turns_played}\n"
        coord = Coord()
        output += "\n   "
        for col in range(dim):
            coord.col = col
            label = coord.col_string()
            output += f"{label:^3} "
        output += "\n"
        for row in range(dim):
            coord.row = row
            label = coord.row_string()
            output += f"{label}: "
            for col in range(dim):
                coord.col = col
                unit = self.get(coord)
                if unit is None:
                    output += " .  "
                else:
                    output += f"{str(unit):^3} "
            output += "\n"
        return output

    def __str__(self) -> str:
        """Default string representation of a game."""
        return self.to_string()

    def is_valid_coord(self, coord: Coord) -> bool:
        """Check if a Coord is valid within out board dimensions."""
        dim = self.options.dim
        if coord.row < 0 or coord.row >= dim or coord.col < 0 or coord.col >= dim:
            return False
        return True

    def read_move(self) -> CoordPair:
        """Read a move from keyboard and return as a CoordPair."""
        while True:
            s = input(F'Player {self.next_player.name}, enter your move: ')
            coords = CoordPair.from_string(s)
            if coords is not None and self.is_valid_coord(coords.src) and self.is_valid_coord(coords.dst):
                return coords
            else:
                print('Invalid coordinates! Try again.')

    def human_turn(self, trace_file):
        """Human player plays a move (or get via broker)."""
        if self.options.broker is not None:
            print("Getting next move with auto-retry from game broker...")
            while True:
                mv = self.get_move_from_broker()
                if mv is not None:
                    (success,result) = self.perform_move(mv, trace_file)
                    print(f"Broker {self.next_player.name}: ",end='')
                    print(result)
                    if success:
                        self.next_turn()
                        break
                sleep(0.1)
        else:
            while True:
                mv = self.read_move()
                (success,result) = self.perform_move(mv, trace_file)
                if success:
                    print(f"Player {self.next_player.name}: ",end='')
                    print(result)
                    self.next_turn()
                    break
                else:
                    print("The move is not valid! Try again.")

    def computer_turn(self, trace_file) -> CoordPair | None:
        """Computer plays a move."""
        mv = self.suggest_move()
        if mv is not None:
            (success,result) = self.perform_move(mv, trace_file)
            if success:
                print(f"Computer {self.next_player.name}: ",end='')
                print(result)
                self.next_turn()
        return mv

    def player_units(self, player: Player) -> Iterable[Tuple[Coord,Unit]]:
        """Iterates over all units belonging to a player."""
        for coord in CoordPair.from_dim(self.options.dim).iter_rectangle():
            unit = self.get(coord)
            if unit is not None and unit.player == player:
                yield (coord,unit)
                
    def all_units(self) -> dict:
        """Iterates over all units belonging to a player and return them."""
        player1_unit_counts = { "virus": 0, "tech": 0, "firewall": 0, "program": 0, "ai": 0 }
        player1_unit_health = { "virus": 0, "tech": 0, "firewall": 0, "program": 0, "ai": 0 }
        player2_unit_counts = { "virus": 0, "tech": 0, "firewall": 0, "program": 0, "ai": 0 }
        player2_unit_health = { "virus": 0, "tech": 0, "firewall": 0, "program": 0, "ai": 0 }
        for coord in CoordPair.from_dim(self.options.dim).iter_rectangle():
            unit = self.get(coord)
            if unit is not None:
                if unit.player == Player.Attacker:
                    player1_unit_counts[unit.type.name.lower()] += 1
                    player1_unit_health[unit.type.name.lower()] += (unit.health)
                else:
                    player2_unit_counts[unit.type.name.lower()] += 1
                    player2_unit_health[unit.type.name.lower()] += (unit.health)
        return player1_unit_counts, player2_unit_counts, player1_unit_health, player2_unit_health

    def is_finished(self) -> bool:
        """Check if the game is over."""
        return self.has_winner() is not None

    def has_winner(self) -> Player | None:
        """Check if the game is over and returns winner"""
        if self.options.max_turns is not None and self.turns_played >= self.options.max_turns:
            return Player.Defender
        elif self._attacker_has_ai:
            if self._defender_has_ai:
                return None
            else:
                return Player.Attacker
        elif self._defender_has_ai:
            return Player.Defender
        elif not self._defender_has_ai and not self._attacker_has_ai:
            return Player.Defender

    def move_candidates(self) -> Iterable[CoordPair]:
        """Generate valid move candidates for the next player."""
        move = CoordPair()
        for (src,_) in self.player_units(self.next_player):
            move.src = src
            for dst in src.iter_adjacent():
                move.dst = dst
                if self.is_valid_move(move) or self.handle_attack(move, False) or self.handle_repair(move, False) or self.handle_self_destruct(move, False):
                    yield move.clone()
            move.dst = src
            yield move.clone()

    def random_move(self) -> Tuple[int, CoordPair | None, float]:
        """Returns a random move."""
        move_candidates = list(self.move_candidates())
        random.shuffle(move_candidates)
        if len(move_candidates) > 0:
            return (0, move_candidates[0], 1)
        else:
            return (0, None, 0)

    def suggest_move(self) -> CoordPair | None:
        """Suggest the next move using minimax alpha beta. TODO: REPLACE RANDOM_MOVE WITH PROPER GAME LOGIC!!!"""
        start_time = datetime.now()
        if self.options.alpha_beta:
            # We ar allowing 90% of the time limit
            max_time = self.options.max_time * 0.99 
            initial_time_left = max_time
            print(f"Max allowed time: {max_time:.2f} seconds")
            print(f"Initial time left: {initial_time_left:.2f} seconds")
            (score, move) = self.alpha_beta(self.next_player == Player.Attacker, 0, float('-inf'), float('inf'), self.options.randomize_moves, max_time, initial_time_left)
        else:
            (score, move) = self.minimax(self.next_player == Player.Attacker, 0, self.options.randomize_moves)
        elapsed_seconds = (datetime.now() - start_time).total_seconds()
        self.stats.total_seconds += elapsed_seconds
        print(f"Heuristic score: {score}")
        print(f"Evals per depth: ",end='')
        for k in sorted(self.stats.evaluations_per_depth.keys()):
            print(f"{k}:{self.stats.evaluations_per_depth[k]} ",end='')
        print()
        total_evals = sum(self.stats.evaluations_per_depth.values())
        if self.stats.total_seconds > 0:
            print(f"Eval perf.: {total_evals/self.stats.total_seconds/1000:0.1f}k/s")
        print(f"Elapsed time: {elapsed_seconds:0.1f}s")
        return move


    def heuristic (self, heuristic):
        # Retrieve unit counts per player
        # Heuristic value is calculated with formula
        heuristic_value = None
        # heuristic e0, for demo
        if heuristic == 0:
            player1_unit_count, player2_unit_count, _, _ = self.all_units()
            heuristic_value = (3*player1_unit_count["virus"] + 3*player1_unit_count["tech"] + 3*player1_unit_count["firewall"] + 3*player1_unit_count["program"] + 9999*player1_unit_count["ai"] ) - (3*player2_unit_count["virus"] + 3*player2_unit_count["tech"] + 3*player2_unit_count["firewall"] + 3*player2_unit_count["program"] + 9999*player2_unit_count["ai"] )
        elif heuristic == 1: # heuristic e1: using health (needs to be played around with)
            player1_unit_count, player2_unit_count, player1_unit_health, player2_unit_health = self.all_units()
            heuristic_value = (2*player1_unit_count["ai"]*player1_unit_health["ai"] + player1_unit_count["virus"]*player1_unit_health["virus"] + player1_unit_count["tech"]*player1_unit_health["tech"] + player1_unit_count["firewall"]*player1_unit_health["firewall"] + player1_unit_count["program"]*player1_unit_health["program"]) - (2*player2_unit_count["ai"]*player2_unit_health["ai"] + player2_unit_count["virus"]*player2_unit_health["virus"] + player2_unit_count["tech"]*player2_unit_health["tech"] + player2_unit_count["firewall"]*player2_unit_health["firewall"] + player2_unit_count["program"]*player2_unit_health["program"])
        elif heuristic == 2: # heuristic e2
            # using distance? to be discussed
            player1_unit_count, player2_unit_count, player1_unit_health, player2_unit_health = self.all_units()

        return heuristic_value  
    
    def alpha_beta(self, is_max: bool, current_depth: int = 0, alpha: int = float('-inf'), beta: int = float('inf'), random_candidate: bool = False, max_time: float = None, initial_time_left: float = None) -> Tuple[float, CoordPair | None]:

        e = self.options.heuristic
        
        # Base case
        if current_depth == self.options.max_depth or self.is_finished():
            return self.heuristic(e), None

        best_move = None

        # Set initial evaluation based on whether it's a max or min node
        best_score = float('-inf') if is_max else float('inf')

        move_candidates = list(self.move_candidates())

        # Option to randomize candidates
        if random_candidate:
            random.shuffle(move_candidates)

        for move in move_candidates:
            cloned_game = self.clone()
            success, action = cloned_game.perform_move(move)
            cloned_game.next_turn()

            if success:
                child_score, _ = cloned_game.alpha_beta(is_max= (not is_max), current_depth=(current_depth + 1), random_candidate=random_candidate, alpha=alpha, beta=beta)
                if is_max:
                    alpha = max(alpha, best_score)
                    if child_score > best_score:
                        best_score = child_score
                        best_move = move
                else:
                    beta = min(beta, best_score)
                    if child_score < best_score:
                        best_score = child_score
                        best_move = move
                if beta <= alpha:
                    break
            
        return best_score, best_move
    
    def minimax(self,is_max: bool, current_depth: int = 0, random_candidate: bool = False) -> Tuple[float, CoordPair | None]:

        e = self.options.heuristic
        
        # Base case
        if current_depth == self.options.max_depth or self.is_finished():
            return self.heuristic(e), None

        best_move = None

        # Set initial evaluation based on whether it's a max or min node
        best_score = float('-inf') if is_max else float('inf')

        move_candidates = list(self.move_candidates())

        # Option to randomize candidates
        if random_candidate:
            random.shuffle(move_candidates)

        for move in move_candidates:
            cloned_game = self.clone()
            success, action = cloned_game.perform_move(move)
            cloned_game.next_turn()

            if success:
                child_score, _ = cloned_game.minimax(not is_max, current_depth + 1, random_candidate)
                if is_max:
                    if child_score > best_score:
                        best_score = child_score
                        best_move = move
                else:
                    if child_score < best_score:
                        best_score = child_score
                        best_move = move
            
        return best_score, best_move

    def post_move_to_broker(self, move: CoordPair):
        """Send a move to the game broker."""
        if self.options.broker is None:
            return
        data = {
            "from": {"row": move.src.row, "col": move.src.col},
            "to": {"row": move.dst.row, "col": move.dst.col},
            "turn": self.turns_played
        }
        try:
            r = requests.post(self.options.broker, json=data)
            if r.status_code == 200 and r.json()['success'] and r.json()['data'] == data:
                # print(f"Sent move to broker: {move}")
                pass
            else:
                print(f"Broker error: status code: {r.status_code}, response: {r.json()}")
        except Exception as error:
            print(f"Broker error: {error}")

    def get_move_from_broker(self) -> CoordPair | None:
        """Get a move from the game broker."""
        if self.options.broker is None:
            return None
        headers = {'Accept': 'application/json'}
        try:
            r = requests.get(self.options.broker, headers=headers)
            if r.status_code == 200 and r.json()['success']:
                data = r.json()['data']
                if data is not None:
                    if data['turn'] == self.turns_played+1:
                        move = CoordPair(
                            Coord(data['from']['row'],data['from']['col']),
                            Coord(data['to']['row'],data['to']['col'])
                        )
                        print(f"Got move from broker: {move}")
                        return move
                    else:
                        # print("Got broker data for wrong turn.")
                        # print(f"Wanted {self.turns_played+1}, got {data['turn']}")
                        pass
                else:
                    # print("Got no data from broker")
                    pass
            else:
                print(f"Broker error: status code: {r.status_code}, response: {r.json()}")
        except Exception as error:
            print(f"Broker error: {error}")
        return None

##############################################################################################################

def game_parameters(options):
    options.max_time = int(input("What is the maximum amount of time per move? "))

    options.max_turns = int(input("What is the maximum number of turns for the game? "))
    
def get_game_type():
    #  AttackerVsDefender = 0
    #     AttackerVsComp = 1
    #     CompVsDefender = 2
    #     CompVsComp = 3
    print("Please choose a game type by entering number:")
    print("AttackerVsDefender = 0")
    print("AttackerVsComp = 1")
    print("CompVsDefender = 2")
    print("CompVsComp = 3")

    while True:
        answer = input("Enter 0 to 3: ")
        if answer == "0":
            game_type_selected = GameType.AttackerVsDefender
        elif answer == "1":
            game_type_selected = GameType.AttackerVsComp
        elif answer == "2":
            game_type_selected = GameType.CompVsDefender
        elif answer == "3":
            game_type_selected = GameType.CompVsComp
        else:
            print("Invalid answer. Please try again. Enter 0 to 3.")
            continue
        return game_type_selected
def main():

    # parse command line arguments
    parser = argparse.ArgumentParser(
        prog='ai_wargame',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--max_depth', type=int, help='maximum search depth')
    parser.add_argument('--max_time', type=float, help='maximum search time')
    parser.add_argument('--game_type', type=str, default=None, help='game type: auto|attacker|defender|manual')
    parser.add_argument('--broker', type=str, help='play via a game broker')
    parser.add_argument('--alpha_beta', action='store_true', help='use alpha-beta pruning')
    parser.add_argument('--e', type=int, help='heuristic')
    
    args = parser.parse_args()

    # parse the game type
    if not args.game_type:
        game_type = get_game_type()
    else:
        if args.game_type == "attacker":
            game_type = GameType.AttackerVsComp
        elif args.game_type == "defender":
            game_type = GameType.CompVsDefender
        elif args.game_type == "manual":
            game_type = GameType.AttackerVsDefender
        else:
            game_type = GameType.CompVsComp

    # set up game options
    options = Options(game_type=game_type)
    
    # user input for configuration
    game_parameters(options)

    # override class defaults via command line options
    if args.max_depth is not None:
        options.max_depth = args.max_depth
    if args.max_time is not None:
        options.max_time = args.max_time
    if args.broker is not None:
        options.broker = args.broker

    # create a new game
    game = Game(options=options)

    # Create trace file   
    heuristic = "AI off"
    beta_alpha = "AI off"
    if (game.options.game_type != GameType.AttackerVsDefender ):
        # ask what depth to use
        if args.max_depth is None:
            while True:
                answer = input("what depth would you like to use for the AI? (hit enter for default): ")
                # if no input, use default
                if answer == "":
                    break
                else:
                    if int(answer) > 0:
                        options.max_depth = int(answer)
                        break
                    else:
                        print("Invalid answer: Please enter a number greater than 0.")
                        continue
        # check if alpha beta is on
        if args.alpha_beta:
            options.alpha_beta = True
        else:
            # if no argument, ask from command line
            answer = input("Would you like to use alpha-beta? (y/n): ")
            if answer == "y":
                options.alpha_beta = True
            else:
                options.alpha_beta = False
        beta_alpha = str(options.alpha_beta)
        # set heuristic used
        if args.e is not None:
            options.e = args.e
        else:
            while True:
                answer = input("Which heuristic would you like to use? (0, 1, 2):")
                if answer == "0":
                    options.e = 0
                elif answer == "1":
                    options.e = 1
                elif answer == "2":
                    options.e = 2
                else:
                    print("Invalid answer: Please enter a value from 0 to 2.")
                    continue
                break
        heuristic = str(options.e)
    
    if_alpha_beta = str(options.alpha_beta) 
    max_time = str(options.max_time)
    max_turns = str(options.max_turns)
    filename = "gameTrace-" + if_alpha_beta + "-" + max_time + "-" + max_turns + ".txt"
    trace_file = open(filename, "w") 
    trace_file.write("Game Trace \n\n\n" +
                     "Game Parameters:\n" +
                     "\ntimeout: " + str(options.max_time) + " seconds" +
                     "\nmax turns: " + str(options.max_turns) +
                     "\nalpha-beta: " + beta_alpha +
                     "\nplay mode: " + str(options.game_type) +
                     "\nheuristic: " + heuristic + "\n\n\n")


    trace_file.write("\n\nInitial Configuration: \n" + str(game.to_string()) + "\n\n")

    # the main game loop
    while True:
        print()
        print(game)
        winner = game.has_winner()
        
        # write final configuration of board and declare winner if there is one
        # otherwise write the action taken to the trace file
        if winner is not None:
            print(f"{winner.name} wins!")
            trace_file.write("\n\n\n" + f"{winner.name} wins in " + str(game.turns_played) + " turns!")
            trace_file.write("\n\nFinal Board Configuration: \n\n")
            trace_file.write(str(game.to_string()))
            break
        else: 
            trace_file.write("\n\n" + str(game.to_string()))

        if game.options.game_type == GameType.AttackerVsDefender:
            game.human_turn(trace_file)
        elif game.options.game_type == GameType.AttackerVsComp and game.next_player == Player.Attacker:
            game.human_turn(trace_file)
        elif game.options.game_type == GameType.CompVsDefender and game.next_player == Player.Defender:
            game.human_turn(trace_file)
        else:
            move = game.computer_turn(trace_file)
            if move is not None:
                game.post_move_to_broker(move)
            else:
                print("Computer doesn't know what to do!!!")
                exit(1)

    trace_file.write("\n\nGame Terminated")

##############################################################################################################

if __name__ == '__main__':
    main()

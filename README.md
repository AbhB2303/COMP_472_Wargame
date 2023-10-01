# COMP_472_Wargame

## Overview
Wargame is a 5 x 5 board game. It is played by two players: an attacker and a defender. The board features six units for each player. Each player takes turns to make moves. The moves can include attacks, self-destructions, and repairs.

The game involves various types of units: AI, Tech, Virus, Program, and Firewall. They all have unique characteristics and abilities. 

AI: each player has 1 AI unit

Viruses: offensive unit

Techs: defensive units

Programs: generic soldiers

Firewalls: strong at absorbing attacks, weak at damaging other units

An integer between [0... 9] is used to denote the health state of each unit. Each unit starts out with full health. Full health is represented with the integer 9. If a virus, tech, program, or firewall's health level drops to zero or below zero, then the unit is destroyed. The player is eliminated from the game if an AI's health reaches zero.

## Rules of the Game

- Run the game in Python with any necessary game parameters (available flags: --max_depth --max_time --game_type or --broker)
- Choose the play mode: (only one play mode available for D1)
      - human vs human
      - human vs AI defender
      - human vs AI attacker
      - AI attacker vs AI defender
- Players take turns to make moves
- The moves can be among the following: attack, self-destruction, or repair
- attack units can only move up or left, while defending units can only move down or right (techs and viruses free to move to any adjacent cell)
- units can attack an adversarial unit if it is adjacent to the unit
- If the player moves a unit to an occupied cell or outside boundaries of the board, that is considered as an invalid move
- If a human player enters an illegal action, then the human will only be warned and be given a chance to enter another move with no penalty
- If the AI generates an illegal action it will lose the game (D2)
- The game ends when the maximum number of turns is reached, when the defender's units are all defeated, or when the attacker's units are all defeated.


## The Structure of the Code

- The main class in the code is 'Game'
        - this class has many attributes, such as the game board, the number of turns played, the current player's turn, game options
        - it also includes checking if a move is valid, as well as performing moves (including attacks, repairs, and self-destruct actions), transitioning to the next turn, and determining the game's winner
        - To set up the default board state, the '__post_init__' method is called automatically after class initialization
- Enums are used to provide a set of predefined values, such as 'Player' and 'UnitType'
- 'GameType' is another enum that defines the type of game
- 'Coord' and 'CoordPair' are classes used for representing coordinates
- 'Options' and 'Stats' are classes used to manage game options and collect statistics
- 'Unit' is a class that defines the units in the class, such as player, type, and health
- trace file generated using python built in library to open/create a file and write to it as the game progresses

Have a great time playing Wargame! Stay tuned for updates!!!

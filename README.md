# 🎲 LLM ARENA

Complete Monopoly game engine in Python with AI agents and CLI for game simulation.

## Quick Start
Using uv
uv run play_monopoly.py

## Basic Usage

Game with 4 players (default)
uv run play_monopoly.py

Change number of players (for 2 players)
uv run play_monopoly.py --players 2

Set seed for reproducibility 
uv run play_monopoly.py --seed 42

Choose AI type: random or greedy
uv run play_monopoly.py --agent random

Quiet mode + turn limit
uv run play_monopoly.py --quiet --max-turns 200

## Implemented Rules

Complete classic gameplay  
Doubles, jail (3 ways to exit)  
Purchase, auctions, mortgages  
House/hotel building with even build rule  
All cards (33 total)  
Bankruptcy with asset transfer  
Bank with limits (32 houses, 12 hotels)

## License

MIT - use freely. Educational project, unofficial implementation.
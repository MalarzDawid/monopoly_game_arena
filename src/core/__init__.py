"""
Core domain layer for Monopoly.

Exposes game engine primitives and built-in agents.
"""

from src.core.game import Board, GameConfig, GameState, Player, PlayerState, create_game
from src.core.agents import Agent, GreedyAgent, LLMAgent, RandomAgent

__all__ = [
    "Board",
    "GameConfig",
    "GameState",
    "Player",
    "PlayerState",
    "create_game",
    "Agent",
    "GreedyAgent",
    "LLMAgent",
    "RandomAgent",
]


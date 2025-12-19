"""Deprecated shim. Use `src.data.models` instead."""

from src.data.models import (  # noqa: F401
    Base,
    Game,
    GameEvent,
    LLMDecision,
    Player,
)

__all__ = ["Base", "Game", "Player", "GameEvent", "LLMDecision"]

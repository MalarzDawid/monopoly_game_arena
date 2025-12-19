"""
Application services layer.

Provides use-case oriented services that glue core logic with persistence
and external integrations (LLM clients, messaging, etc.).
"""

from .game_service import GameService

__all__ = ["GameService"]

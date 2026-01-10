"""
Custom exception hierarchy for Monopoly engine and services.

Provides typed errors that can be handled consistently across
the core engine, services, and API layer.
"""


class MonopolyError(Exception):
    """Base exception for all game-related errors."""


class GameNotFoundError(MonopolyError):
    """Game does not exist."""


class InvalidActionError(MonopolyError):
    """Action is not legal in the current state."""


class DatabaseError(MonopolyError):
    """Database operation failed."""


class LLMError(MonopolyError):
    """LLM agent communication failed."""


class ValidationError(MonopolyError):
    """Input validation failed."""


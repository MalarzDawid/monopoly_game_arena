"""
Deprecated compatibility shim for the database layer.

All database code now lives in `src.data`. This module re-exports the
new locations so existing imports keep working during the transition.
"""

from src.data import (  # noqa: F401
    Base,
    Game,
    GameEvent,
    GameRepository,
    LLMDecision,
    Player,
    close_db,
    create_tables,
    drop_tables,
    get_engine,
    get_session,
    get_settings,
    init_db,
    session_scope,
)

__all__ = [
    "get_settings",
    "Base",
    "Game",
    "Player",
    "GameEvent",
    "LLMDecision",
    "get_session",
    "init_db",
    "close_db",
    "session_scope",
    "create_tables",
    "drop_tables",
    "get_engine",
    "GameRepository",
]

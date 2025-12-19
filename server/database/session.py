"""Deprecated shim. Use `src.data.session` instead."""

from src.data.session import (  # noqa: F401
    close_db,
    create_tables,
    drop_tables,
    get_engine,
    get_session,
    init_db,
    session_scope,
)

__all__ = [
    "get_session",
    "init_db",
    "close_db",
    "session_scope",
    "create_tables",
    "drop_tables",
    "get_engine",
]

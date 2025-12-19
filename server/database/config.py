"""Deprecated shim. Use `src.data.config` instead."""

from src.data.config import (  # noqa: F401
    DatabaseSettings,
    get_settings,
)

__all__ = ["DatabaseSettings", "get_settings"]

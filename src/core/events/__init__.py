"""
Event utilities: canonical mapping and schemas.

This package exposes helpers to convert internal engine events into a
stable, public-facing JSON shape suitable for logging and real-time UIs.
"""

from core.events.mapper import map_event, map_events

__all__ = [
    "map_event",
    "map_events",
]

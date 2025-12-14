"""
SQLAlchemy models for Monopoly Game Arena.

Architecture:
- Game: metadata about each game session
- Player: participants in a game
- GameEvent: event sourcing - chronological log of all game events (JSONB payload)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all models."""

    pass


def utc_now() -> datetime:
    """Generate timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc)


class Game(Base):
    """
    Game metadata table.

    Tracks high-level game session information. The actual game state
    is reconstructed from GameEvent records (event sourcing).
    """

    __tablename__ = "games"

    # Primary key: UUID for distributed systems compatibility
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )

    # Game identification
    game_id: Mapped[str] = mapped_column(
        String(128),
        unique=True,
        nullable=False,
        index=True,
        comment="Human-readable game ID from GameRegistry",
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    # Game status
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="created",
        index=True,
        comment="created | running | paused | finished | error",
    )

    # Game configuration (stored as JSONB for flexibility)
    config: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
        comment="Game rules, seed, max_turns, etc.",
    )

    # Results
    winner_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Player ID of the winner (if any)",
    )
    total_turns: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    # Game metadata (using 'game_metadata' to avoid SQLAlchemy reserved name)
    game_metadata: Mapped[Dict[str, Any]] = mapped_column(
        "metadata",  # Column name in database
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
        comment="Additional metadata, tags, environment info",
    )

    # Relationships
    players: Mapped[List["Player"]] = relationship(
        "Player",
        back_populates="game",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    events: Mapped[List["GameEvent"]] = relationship(
        "GameEvent",
        back_populates="game",
        cascade="all, delete-orphan",
        lazy="noload",  # Events loaded explicitly via repository
        order_by="GameEvent.sequence_number",
    )

    def __repr__(self) -> str:
        return f"<Game(game_id={self.game_id}, status={self.status}, turns={self.total_turns})>"


class Player(Base):
    """
    Player participation in a game.

    Stores metadata about each player/agent in a game session.
    """

    __tablename__ = "players"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )

    # Foreign key to game
    game_uuid: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("games.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Player identification
    player_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Player ID within the game (0, 1, 2, ...)",
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    agent_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="greedy | random | human | llm",
    )

    # Final results
    final_cash: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    final_net_worth: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    is_winner: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    is_bankrupt: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    placement: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="1st, 2nd, 3rd, etc.",
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    # Relationship
    game: Mapped["Game"] = relationship("Game", back_populates="players")

    # Unique constraint: one player_id per game
    __table_args__ = (
        UniqueConstraint("game_uuid", "player_id", name="uq_game_player"),
        Index("ix_players_game_player", "game_uuid", "player_id"),
    )

    def __repr__(self) -> str:
        return f"<Player(name={self.name}, agent={self.agent_type}, player_id={self.player_id})>"


class GameEvent(Base):
    """
    Event sourcing table - chronological log of all game events.

    Each event represents a discrete action or state change in the game.
    The entire game state can be reconstructed by replaying events in order.
    """

    __tablename__ = "game_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )

    # Foreign key to game
    game_uuid: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("games.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Event sequencing - CRITICAL for event sourcing
    sequence_number: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        comment="Global sequence number across all events in this game (0, 1, 2, ...)",
    )
    turn_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
        comment="Game turn when this event occurred",
    )

    # Event metadata
    event_type: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        index=True,
        comment="e.g., 'turn_start', 'dice_roll', 'property_purchased', 'rent_paid'",
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=text("CURRENT_TIMESTAMP"),
        index=True,
    )

    # Event payload (JSONB) - stores all event data
    payload: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        comment="Full event data in JSON format",
    )

    # Optional: actor (which player triggered this event)
    actor_player_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Player ID who triggered this event (if applicable)",
    )

    # Relationship
    game: Mapped["Game"] = relationship("Game", back_populates="events")

    # Indexes for fast queries
    __table_args__ = (
        # Ensure events are unique and ordered per game
        UniqueConstraint("game_uuid", "sequence_number", name="uq_game_event_sequence"),
        # Fast lookup: get all events for a game
        Index("ix_game_events_game_sequence", "game_uuid", "sequence_number"),
        # Fast lookup: get events for a specific turn
        Index("ix_game_events_game_turn", "game_uuid", "turn_number"),
        # Fast lookup: filter by event type
        Index("ix_game_events_type_timestamp", "event_type", "timestamp"),
        # GIN index for JSONB payload queries (if needed)
        Index("ix_game_events_payload", "payload", postgresql_using="gin"),
    )

    def __repr__(self) -> str:
        return f"<GameEvent(game={self.game_uuid}, seq={self.sequence_number}, type={self.event_type})>"

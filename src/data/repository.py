"""
Repository pattern for game data operations.

Encapsulates all database queries for games, players, and events.
Provides a clean interface for the application layer.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select, func, and_, or_, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from data.models import Game, GameEvent, Player, LLMDecision

logger = logging.getLogger(__name__)


class GameRepository:
    """
    Repository for game-related database operations.

    Handles CRUD operations for games, players, and events using
    the event sourcing pattern.
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize repository with a database session.

        Args:
            session: Active async SQLAlchemy session
        """
        self.session = session

    # ---- Game Operations ----

    async def create_game(
        self,
        game_id: str,
        config: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Game:
        """
        Create a new game record.

        Args:
            game_id: Human-readable game identifier (from GameRegistry)
            config: Game configuration (seed, max_turns, rules, etc.)
            metadata: Optional metadata (tags, environment info)

        Returns:
            Created Game instance
        """
        game = Game(
            game_id=game_id,
            status="created",
            config=config,
            game_metadata=metadata or {},  # Changed from metadata to game_metadata
            total_turns=0,
        )

        self.session.add(game)
        await self.session.flush()  # Get the UUID assigned
        logger.info(f"Created game: {game_id} (UUID: {game.id})")

        return game

    async def get_game_by_id(self, game_id: str) -> Optional[Game]:
        """
        Fetch game by human-readable game_id.

        Args:
            game_id: Game identifier (e.g., "game-abc123")

        Returns:
            Game instance or None if not found
        """
        stmt = (
            select(Game)
            .where(Game.game_id == game_id)
            .options(selectinload(Game.players))  # Eager load players
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_game_by_uuid(self, game_uuid: uuid.UUID) -> Optional[Game]:
        """
        Fetch game by UUID primary key.

        Args:
            game_uuid: Game UUID

        Returns:
            Game instance or None if not found
        """
        stmt = (
            select(Game)
            .where(Game.id == game_uuid)
            .options(selectinload(Game.players))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_game_status(
        self,
        game_id: str,
        status: str,
        started_at: Optional[datetime] = None,
        finished_at: Optional[datetime] = None,
        winner_id: Optional[int] = None,
        total_turns: Optional[int] = None,
    ) -> Optional[Game]:
        """
        Update game status and metadata.

        Args:
            game_id: Game identifier
            status: New status (running | paused | finished | error)
            started_at: Timestamp when game started
            finished_at: Timestamp when game finished
            winner_id: Player ID of the winner
            total_turns: Final turn count

        Returns:
            Updated Game instance or None if not found
        """
        game = await self.get_game_by_id(game_id)
        if not game:
            return None

        game.status = status
        if started_at:
            game.started_at = started_at
        if finished_at:
            game.finished_at = finished_at
        if winner_id is not None:
            game.winner_id = winner_id
        if total_turns is not None:
            game.total_turns = total_turns

        await self.session.flush()
        logger.info(f"Updated game {game_id} status: {status}")

        return game

    async def list_games(
        self,
        limit: int = 100,
        offset: int = 0,
        status: Optional[str] = None,
    ) -> List[Game]:
        """
        List games with optional filtering.

        Args:
            limit: Maximum number of games to return
            offset: Pagination offset
            status: Filter by status (optional)

        Returns:
            List of Game instances
        """
        stmt = select(Game).options(selectinload(Game.players))

        if status:
            stmt = stmt.where(Game.status == status)

        stmt = stmt.order_by(Game.created_at.desc()).limit(limit).offset(offset)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # ---- Player Operations ----

    async def add_player(
        self,
        game_uuid: uuid.UUID,
        player_id: int,
        name: str,
        agent_type: str,
        llm_model_name: Optional[str] = None,
        llm_strategy_profile: Optional[Dict[str, Any]] = None,
    ) -> Player:
        """
        Add a player to a game.

        Args:
            game_uuid: Game UUID
            player_id: Player ID within the game (0, 1, 2, ...)
            name: Player display name
            agent_type: Agent type (greedy | random | human | llm)
            llm_model_name: LLM model name (for LLM agents)
            llm_strategy_profile: LLM strategy profile dict (for LLM agents)

        Returns:
            Created Player instance
        """
        player = Player(
            game_uuid=game_uuid,
            player_id=player_id,
            name=name,
            agent_type=agent_type,
            llm_model_name=llm_model_name,
            llm_strategy_profile=llm_strategy_profile,
        )

        self.session.add(player)
        await self.session.flush()
        logger.info(f"Added player {player_id} ({name}) to game {game_uuid}")

        return player

    async def update_player_results(
        self,
        game_uuid: uuid.UUID,
        player_id: int,
        final_cash: int,
        final_net_worth: int,
        is_winner: bool = False,
        is_bankrupt: bool = False,
        placement: Optional[int] = None,
    ) -> Optional[Player]:
        """
        Update player final results.

        Args:
            game_uuid: Game UUID
            player_id: Player ID
            final_cash: Final cash amount
            final_net_worth: Final total net worth
            is_winner: Whether player won
            is_bankrupt: Whether player went bankrupt
            placement: Final ranking (1st, 2nd, etc.)

        Returns:
            Updated Player instance or None if not found
        """
        stmt = select(Player).where(
            and_(Player.game_uuid == game_uuid, Player.player_id == player_id)
        )
        result = await self.session.execute(stmt)
        player = result.scalar_one_or_none()

        if not player:
            return None

        player.final_cash = final_cash
        player.final_net_worth = final_net_worth
        player.is_winner = is_winner
        player.is_bankrupt = is_bankrupt
        player.placement = placement

        await self.session.flush()
        logger.info(f"Updated player {player_id} results in game {game_uuid}")

        return player

    # ---- Event Sourcing Operations ----

    async def add_event(
        self,
        game_uuid: uuid.UUID,
        sequence_number: int,
        turn_number: int,
        event_type: str,
        payload: Dict[str, Any],
        actor_player_id: Optional[int] = None,
    ) -> GameEvent:
        """
        Add a new event to the game log (event sourcing).

        Args:
            game_uuid: Game UUID
            sequence_number: Sequence number (monotonically increasing)
            turn_number: Turn number when event occurred
            event_type: Type of event (e.g., 'dice_roll', 'property_purchased')
            payload: Event data as JSONB
            actor_player_id: Player who triggered this event (optional)

        Returns:
            Created GameEvent instance
        """
        event = GameEvent(
            game_uuid=game_uuid,
            sequence_number=sequence_number,
            turn_number=turn_number,
            event_type=event_type,
            payload=payload,
            actor_player_id=actor_player_id,
        )

        self.session.add(event)
        await self.session.flush()

        return event

    async def add_events_batch(
        self,
        game_uuid: uuid.UUID,
        events: List[Dict[str, Any]],
    ) -> List[GameEvent]:
        """
        Add multiple events in a batch (more efficient).

        Args:
            game_uuid: Game UUID
            events: List of event dictionaries with keys:
                - sequence_number
                - turn_number
                - event_type
                - payload
                - actor_player_id (optional)

        Returns:
            List of created GameEvent instances
        """
        event_objects = [
            GameEvent(
                game_uuid=game_uuid,
                sequence_number=e["sequence_number"],
                turn_number=e["turn_number"],
                event_type=e["event_type"],
                payload=e["payload"],
                actor_player_id=e.get("actor_player_id"),
            )
            for e in events
        ]

        self.session.add_all(event_objects)
        await self.session.flush()
        logger.info(f"Added {len(event_objects)} events to game {game_uuid}")

        return event_objects

    async def get_game_events(
        self,
        game_uuid: uuid.UUID,
        from_sequence: Optional[int] = None,
        to_sequence: Optional[int] = None,
        turn_number: Optional[int] = None,
    ) -> List[GameEvent]:
        """
        Retrieve events for a game with optional filtering.

        Args:
            game_uuid: Game UUID
            from_sequence: Start from this sequence number (inclusive)
            to_sequence: End at this sequence number (inclusive)
            turn_number: Filter by specific turn

        Returns:
            List of GameEvent instances ordered by sequence_number
        """
        stmt = select(GameEvent).where(GameEvent.game_uuid == game_uuid)

        if from_sequence is not None:
            stmt = stmt.where(GameEvent.sequence_number >= from_sequence)
        if to_sequence is not None:
            stmt = stmt.where(GameEvent.sequence_number <= to_sequence)
        if turn_number is not None:
            stmt = stmt.where(GameEvent.turn_number == turn_number)

        stmt = stmt.order_by(GameEvent.sequence_number)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_latest_sequence_number(self, game_uuid: uuid.UUID) -> int:
        """
        Get the highest sequence number for a game.

        Args:
            game_uuid: Game UUID

        Returns:
            Latest sequence number, or -1 if no events exist
        """
        stmt = select(func.max(GameEvent.sequence_number)).where(
            GameEvent.game_uuid == game_uuid
        )
        result = await self.session.execute(stmt)
        max_seq = result.scalar_one_or_none()

        return max_seq if max_seq is not None else -1

    async def get_event_count(
        self,
        game_uuid: uuid.UUID,
        event_type: Optional[str] = None,
    ) -> int:
        """
        Count events for a game, optionally filtered by type.

        Args:
            game_uuid: Game UUID
            event_type: Filter by event type (optional)

        Returns:
            Number of events
        """
        stmt = select(func.count(GameEvent.id)).where(
            GameEvent.game_uuid == game_uuid
        )

        if event_type:
            stmt = stmt.where(GameEvent.event_type == event_type)

        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def get_game_with_events(
        self,
        game_id: str,
        include_events: bool = True,
    ) -> Optional[tuple[Game, List[GameEvent]]]:
        """
        Retrieve a game with its full event history.

        Args:
            game_id: Game identifier
            include_events: Whether to load events (default True)

        Returns:
            Tuple of (Game, List[GameEvent]) or None if game not found
        """
        game = await self.get_game_by_id(game_id)
        if not game:
            return None

        if include_events:
            events = await self.get_game_events(game.id)
        else:
            events = []

        return game, events

    # ---- Statistics & Analytics ----

    async def get_game_statistics(self, game_uuid: uuid.UUID) -> Dict[str, Any]:
        """
        Get statistics about a game.

        Args:
            game_uuid: Game UUID

        Returns:
            Dictionary with statistics
        """
        total_events = await self.get_event_count(game_uuid)
        latest_seq = await self.get_latest_sequence_number(game_uuid)

        # Count events by type
        stmt = (
            select(GameEvent.event_type, func.count(GameEvent.id))
            .where(GameEvent.game_uuid == game_uuid)
            .group_by(GameEvent.event_type)
        )
        result = await self.session.execute(stmt)
        events_by_type = dict(result.all())

        return {
            "total_events": total_events,
            "latest_sequence": latest_seq,
            "events_by_type": events_by_type,
        }

    # ---- LLM Decision Operations ----

    async def add_llm_decision(
        self,
        game_uuid: uuid.UUID,
        player_id: int,
        turn_number: int,
        sequence_number: int,
        game_state: Dict[str, Any],
        player_state: Dict[str, Any],
        available_actions: Dict[str, Any],
        prompt: str,
        reasoning: str,
        chosen_action: Dict[str, Any],
        strategy_description: Optional[str] = None,
        processing_time_ms: Optional[int] = None,
        model_version: Optional[str] = None,
    ) -> LLMDecision:
        """
        Record an LLM decision with full context and reasoning.

        Args:
            game_uuid: Game UUID
            player_id: Player ID
            turn_number: Turn number when decision was made
            sequence_number: Sequence number (monotonically increasing)
            game_state: Complete game state snapshot
            player_state: Player state including cash, properties, etc.
            available_actions: Actions available to the player
            prompt: Prompt sent to the LLM
            reasoning: LLM's reasoning process
            chosen_action: Action chosen by the LLM
            strategy_description: LLM's description of its strategy (optional)
            processing_time_ms: Time taken to process the decision (optional)
            model_version: LLM model version used (optional)

        Returns:
            Created LLMDecision instance
        """
        decision = LLMDecision(
            game_uuid=game_uuid,
            player_id=player_id,
            turn_number=turn_number,
            sequence_number=sequence_number,
            game_state=game_state,
            player_state=player_state,
            available_actions=available_actions,
            prompt=prompt,
            reasoning=reasoning,
            chosen_action=chosen_action,
            strategy_description=strategy_description,
            processing_time_ms=processing_time_ms,
            model_version=model_version,
        )

        self.session.add(decision)
        await self.session.flush()
        logger.info(f"Added LLM decision for player {player_id} in game {game_uuid}")

        return decision

    async def get_llm_decisions_for_game(
        self,
        game_uuid: uuid.UUID,
        player_id: Optional[int] = None,
    ) -> List[LLMDecision]:
        """
        Retrieve all LLM decisions for a game, optionally filtered by player.

        Args:
            game_uuid: Game UUID
            player_id: Filter by player ID (optional)

        Returns:
            List of LLMDecision instances ordered by sequence_number
        """
        stmt = select(LLMDecision).where(LLMDecision.game_uuid == game_uuid)

        if player_id is not None:
            stmt = stmt.where(LLMDecision.player_id == player_id)

        stmt = stmt.order_by(LLMDecision.sequence_number)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_llm_decision_by_sequence(
        self,
        game_uuid: uuid.UUID,
        sequence_number: int,
    ) -> Optional[LLMDecision]:
        """
        Get a specific LLM decision by sequence number.

        Args:
            game_uuid: Game UUID
            sequence_number: Sequence number

        Returns:
            LLMDecision instance or None if not found
        """
        stmt = select(LLMDecision).where(
            and_(
                LLMDecision.game_uuid == game_uuid,
                LLMDecision.sequence_number == sequence_number,
            )
        )

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def search_llm_reasoning(
        self,
        search_text: str,
        limit: int = 100,
    ) -> List[LLMDecision]:
        """
        Search for LLM decisions by reasoning content using full-text search.

        Args:
            search_text: Text to search for
            limit: Maximum number of results to return

        Returns:
            List of matching LLMDecision instances
        """
        # Convert search text to tsquery format
        search_query = " & ".join(search_text.split())

        stmt = select(LLMDecision).where(
            text("to_tsvector('english', reasoning) @@ to_tsquery('english', :search)")
        ).params(search=search_query).limit(limit)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_llm_player_strategy(
        self,
        game_uuid: uuid.UUID,
        player_id: int,
        strategy_profile: Dict[str, Any],
    ) -> Optional[Player]:
        """
        Update an LLM player's strategy profile.

        Args:
            game_uuid: Game UUID
            player_id: Player ID
            strategy_profile: New strategy profile

        Returns:
            Updated Player instance or None if not found
        """
        stmt = select(Player).where(
            and_(Player.game_uuid == game_uuid, Player.player_id == player_id)
        )
        result = await self.session.execute(stmt)
        player = result.scalar_one_or_none()

        if not player:
            return None

        player.llm_strategy_profile = strategy_profile
        await self.session.flush()
        logger.info(f"Updated strategy profile for player {player_id} in game {game_uuid}")

        return player

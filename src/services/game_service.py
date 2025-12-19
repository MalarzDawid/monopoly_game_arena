"""
GameService orchestrates core game engine with persistence and logging.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence

from src.core import GameConfig, GameState, Player, create_game
from src.core.agents import Agent, GreedyAgent, LLMAgent, RandomAgent
from src.core.game.game import ActionType
from src.core.game.rules import Action, apply_action, get_legal_actions
from src.data import GameRepository

logger = logging.getLogger(__name__)


class GameService:
    """Use-case service for creating and running games."""

    def __init__(self, repo: GameRepository):
        self.repo = repo

    async def create_game(
        self,
        *,
        num_players: int,
        agent: str,
        seed: Optional[int],
        max_turns: Optional[int],
        roles: Optional[List[str]],
        tick_ms: Optional[int],
        llm_strategy: str,
    ) -> tuple[str, GameState, List[Agent]]:
        """Create game state, persist metadata, and build agents."""
        game_id = uuid.uuid4().hex[:12]

        players = [Player(i, name) for i, name in enumerate(self._default_names(num_players))]
        roles = roles or [agent] * num_players

        config = GameConfig(seed=seed, time_limit_turns=max_turns)
        game = create_game(config, players)

        db_game = await self.repo.create_game(
            game_id=game_id,
            config={
                "seed": seed,
                "max_turns": max_turns,
                "num_players": num_players,
                "agent": agent,
                "roles": roles,
                "tick_ms": tick_ms,
            },
            metadata={"created_by": "service"},
        )

        for i, player in enumerate(players):
            agent_type = roles[i] if roles else agent
            await self.repo.add_player(
                game_uuid=db_game.id,
                player_id=i,
                name=player.name,
                agent_type=agent_type,
            )

        agents = self._build_agents(players, roles, llm_strategy=llm_strategy)
        return game_id, game, agents

    async def update_status(
        self,
        game_id: str,
        status: str,
        *,
        started_at: Optional[datetime] = None,
        finished_at: Optional[datetime] = None,
        winner_id: Optional[int] = None,
        total_turns: Optional[int] = None,
    ) -> None:
        """Update persisted game status."""
        await self.repo.update_game_status(
            game_id=game_id,
            status=status,
            started_at=started_at,
            finished_at=finished_at,
            winner_id=winner_id,
            total_turns=total_turns,
        )

    async def persist_events(
        self,
        game_uuid: uuid.UUID,
        events: Sequence[Dict[str, Any]],
    ) -> None:
        """Persist a batch of engine events."""
        if events:
            await self.repo.add_events_batch(game_uuid, list(events))

    async def persist_llm_decisions(
        self,
        game_uuid: uuid.UUID,
        decisions: Sequence[Dict[str, Any]],
    ) -> None:
        """Persist queued LLM decisions."""
        for decision in decisions:
            await self.repo.add_llm_decision(
                game_uuid=game_uuid,
                player_id=decision["player_id"],
                turn_number=decision["turn_number"],
                sequence_number=decision.get("sequence_number", 0),
                game_state=decision.get("game_state", {}),
                player_state=decision.get("player_state", {}),
                available_actions=decision.get("available_actions", {}),
                prompt=decision.get("prompt", ""),
                reasoning=decision.get("reasoning", ""),
                chosen_action=decision.get("chosen_action", {}),
                strategy_description=decision.get("strategy"),
                processing_time_ms=decision.get("processing_time_ms"),
                model_version=decision.get("model_version"),
            )

    # Helpers

    def legal_actions(self, game: GameState, player_id: int) -> List[Action]:
        return get_legal_actions(game, player_id)

    def apply_action(self, game: GameState, action_type: str, params: Dict[str, Any], player_id: Optional[int]) -> tuple[bool, Optional[str]]:
        try:
            action = Action(ActionType(action_type), **params)
            ok = apply_action(game, action, player_id)
            if not ok:
                return False, "Action rejected by engine"
            return True, None
        except Exception as e:
            logger.exception("Failed to apply action")
            return False, str(e)

    # ---- Query helpers (thin repo wrappers) ----

    async def list_games(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
        status: Optional[str] = None,
    ) -> List[Any]:
        return await self.repo.list_games(limit=limit, offset=offset, status=status)

    async def get_game_with_events(self, game_id: str) -> Optional[tuple[Any, List[Any]]]:
        return await self.repo.get_game_with_events(game_id)

    async def get_game_stats(self, game_uuid: uuid.UUID) -> Dict[str, Any]:
        return await self.repo.get_game_statistics(game_uuid)

    @staticmethod
    def _default_names(n: int) -> list[str]:
        base = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank", "Grace", "Hank"]
        if n <= len(base):
            return base[:n]
        return base + [f"P{i}" for i in range(len(base), n)]

    def _build_agents(self, players: List[Player], roles: List[str], llm_strategy: str) -> List[Agent]:
        agents: List[Optional[Agent]] = [None] * len(players)
        for i, role in enumerate(roles):
            name = players[i].name
            if role == "human":
                agents[i] = None
            elif role == "random":
                agents[i] = RandomAgent(i, name)
            elif role == "llm":
                agents[i] = LLMAgent(i, name, strategy=llm_strategy)
            else:
                agents[i] = GreedyAgent(i, name)
        return agents

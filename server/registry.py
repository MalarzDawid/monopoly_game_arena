from __future__ import annotations

import asyncio
import uuid
from typing import Dict, Optional

from monopoly.config import GameConfig
from monopoly.player import Player
from monopoly.game import create_game

from .runner import GameRunner


class GameRegistry:
    """In-memory registry of running games."""

    def __init__(self):
        self._games: Dict[str, GameRunner] = {}
        self._lock = asyncio.Lock()

    async def create_game(
        self,
        *,
        num_players: int = 4,
        agent: str = "greedy",
        seed: Optional[int] = None,
        max_turns: Optional[int] = None,
        roles: Optional[list[str]] = None,
        tick_ms: Optional[int] = 500,
    ) -> str:
        game_id = uuid.uuid4().hex[:12]

        players = [Player(i, name) for i, name in enumerate(self._default_names(num_players))]
        # Default roles: all agents (observer mode)
        if roles is None:
            roles = [agent] * num_players
        config = GameConfig(seed=seed, time_limit_turns=max_turns)
        game = create_game(config, players)

        runner = GameRunner(game_id=game_id, game=game, agent_type=agent, roles=roles, tick_ms=tick_ms)
        async with self._lock:
            self._games[game_id] = runner

        await runner.start()
        return game_id

    async def get(self, game_id: str) -> Optional[GameRunner]:
        return self._games.get(game_id)

    async def stop(self, game_id: str) -> bool:
        async with self._lock:
            runner = self._games.get(game_id)
            if not runner:
                return False
            await runner.stop()
            del self._games[game_id]
            return True

    @staticmethod
    def _default_names(n: int) -> list[str]:
        base = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank", "Grace", "Hank"]
        if n <= len(base):
            return base[:n]
        # Extend if needed
        return base + [f"P{i}" for i in range(len(base), n)]

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any, Dict, List, Optional, Set
from datetime import datetime, timezone

from src.core.game.game import ActionType, GameState
from src.core.game.rules import apply_action, get_legal_actions
from src.services import GameService
from game_logger import GameLogger
from events.mapper import map_events
from snapshot import serialize_snapshot
from src.core.agents import GreedyAgent, LLMAgent, RandomAgent
from src.data import GameRepository, session_scope

logger = logging.getLogger(__name__)


class GameRunner:
    """Owns a single GameState and runs it asynchronously.

    Responsibilities:
    - Drive turns and agent decisions
    - Flush internal engine events to JSONL via GameLogger
    - Broadcast mapped events to subscribed WebSocket clients
    """

    def __init__(
        self,
        game_id: str,
        game: GameState,
        agents: List[Optional[object]],
        agent_type: str = "greedy",
        roles: Optional[List[str]] = None,
        tick_ms: Optional[int] = 500,
        llm_strategy: str = "balanced",
        game_repo: Optional[GameRepository] = None,
        game_service: Optional[GameService] = None,
    ):
        self.game_id = game_id
        self.game = game
        self.agent_type = agent_type
        self.llm_strategy = llm_strategy
        # DB persistence handled via GameService; logger only writes JSONL
        self.logger = GameLogger(game_id=None)
        self._task: Optional[asyncio.Task] = None
        self._stop = asyncio.Event()
        self._clients: Set[asyncio.Queue] = set()  # each client gets a queue of outbound messages
        self._last_engine_idx = len(self.game.event_log.events)
        self._apply_lock = asyncio.Lock()
        self._new_action_event = asyncio.Event()
        self._paused = False
        self._turn_indices: Dict[int, int] = {}
        self._auction_rotation: Dict[int, int] = {}
        # pacing between actions (seconds)
        self._tick: float = max(0.0, (tick_ms or 0) / 1000.0)

        # Database game UUID (set in start() after fetching from DB)
        self._game_uuid: Optional[uuid.UUID] = None

        # Queue for pending LLM decisions to be saved to database
        self._pending_llm_decisions: List[Dict[str, Any]] = []
        self._game_repo = game_repo
        self._game_service = game_service

        # Agents list (one per player)
        names = [self.game.players[i].name for i in sorted(self.game.players)]
        self._player_names = names
        # Determine roles per player
        if roles is None:
            roles = [agent_type for _ in names]
        # Normalize length
        if len(roles) < len(names):
            roles = roles + [agent_type] * (len(names) - len(roles))
        self.roles: List[str] = roles
        self.agents: List[Optional[object]] = agents if agents is not None else [None] * len(names)

        # Create LLM callback that queues decisions for DB persistence
        def llm_decision_callback(decision_data: Dict[str, Any]) -> None:
            # Log to JSONL via GameLogger
            player_id = decision_data["player_id"]
            self.logger.log_llm_decision(
                turn_number=decision_data["turn_number"],
                player_id=player_id,
                player_name=names[player_id],
                action_type=decision_data["chosen_action"]["action_type"],
                params=decision_data["chosen_action"]["params"],
                reasoning=decision_data["reasoning"],
                used_fallback=decision_data["used_fallback"],
                processing_time_ms=decision_data["processing_time_ms"],
                model_version=decision_data["model_version"],
                strategy=decision_data["strategy"],
                error=decision_data.get("error"),
                raw_response=decision_data.get("raw_response"),
            )
            # Queue for database persistence
            self._pending_llm_decisions.append(decision_data)

        # Prepare agents for non-human players if not provided
        if agents is None:
            for i, role in enumerate(self.roles):
                if role == "human":
                    self.agents[i] = None
                elif role == "random":
                    self.agents[i] = RandomAgent(i, names[i])
                elif role == "llm":
                    self.agents[i] = LLMAgent(i, names[i], strategy=self.llm_strategy, decision_callback=llm_decision_callback)
                else:
                    self.agents[i] = GreedyAgent(i, names[i])

    async def start(self) -> None:
        # Flush initial GAME_START and TURN_START
        self.logger.flush_engine_events(self.game)
        # Mark game as running in the database and fetch game_uuid
        try:
            async with session_scope() as session:
                repo = self._game_repo or GameRepository(session)
                # Fetch game to get UUID for LLM decision logging
                db_game = await repo.get_game_by_id(self.game_id)
                if db_game:
                    self._game_uuid = db_game.id
                    logger.info(f"Game {self.game_id} has UUID {self._game_uuid}")
                await repo.update_game_status(
                    game_id=self.game_id,
                    status="running",
                    started_at=datetime.now(timezone.utc),
                )
                if self._game_service:
                    await self._game_service.update_status(
                        game_id=self.game_id,
                        status="running",
                        started_at=datetime.now(timezone.utc),
                    )
        except Exception as e:
            # Non-fatal; continue even if DB update fails
            logger.warning(f"Failed to fetch game UUID or update status: {e}")
        self._task = asyncio.create_task(self._run_loop())

    async def stop(self) -> None:
        self._stop.set()
        if self._task:
            await self._task

    # Subscription management for WS
    async def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self._clients.add(q)
        # Send initial snapshot
        await q.put({
            "type": "snapshot",
            "game_id": self.game_id,
            "snapshot": serialize_snapshot(self.game),
            "last_event_index": self._last_engine_idx,
        })
        return q

    async def unsubscribe(self, q: asyncio.Queue) -> None:
        self._clients.discard(q)

    async def _broadcast(self, payload: Dict[str, Any]) -> None:
        if not self._clients:
            return
        for q in list(self._clients):
            # Best-effort; don't block if client is slow
            try:
                q.put_nowait(payload)
            except asyncio.QueueFull:
                # Drop client if it cannot keep up
                self._clients.discard(q)

    async def _run_loop(self) -> None:
        # Main loop; conservative sleep to avoid tight CPU usage
        while not self.game.game_over and not self._stop.is_set():
            # Flush internal events to JSONL and broadcast them
            await self.flush_and_broadcast()

            # Honor pause flag globally
            if self._paused:
                await self._wait_for_external_action()
                continue

            # Auction phase handling
            if self.game.active_auction and self.game.active_auction.active_bidders:
                # Determine next bidder who can act
                active = sorted([
                    pid for pid in self.game.active_auction.active_bidders
                    if self.game.active_auction.can_player_bid(pid)
                ])
                if not active:
                    # Force pass remaining to complete auction
                    for pid in list(self.game.active_auction.active_bidders):
                        self.game.active_auction.pass_turn(pid)
                    await self.flush_and_broadcast()
                    await asyncio.sleep(self._tick)
                    # Clean rotation when auction completes
                    if not self.game.active_auction:
                        self._auction_rotation.clear()
                    continue

                # Round-robin bidder selection per auction instance
                auction_id = id(self.game.active_auction)
                idx = self._auction_rotation.get(auction_id, 0) % len(active)
                bidder_id = active[idx]
                role = self.roles[bidder_id]
                if role == "human":
                    # Wait for external action
                    await self._wait_for_external_action()
                    continue
                else:
                    actions = get_legal_actions(self.game, bidder_id)
                    if not actions:
                        # If agent cannot act, pass bidder
                        self.game.active_auction.pass_turn(bidder_id)
                        await self.flush_and_broadcast()
                        await asyncio.sleep(self._tick)
                        continue
                    agent = self.agents[bidder_id]
                    action = agent.choose_action(self.game, actions)
                    if action is None:
                        self.game.active_auction.pass_turn(bidder_id)
                        await self.flush_and_broadcast()
                        await asyncio.sleep(self._tick)
                        continue
                    apply_action(self.game, action, player_id=bidder_id)
                    # Advance rotation for next loop
                    self._auction_rotation[auction_id] = idx + 1
                    # If auction completed, clear rotation
                    if not self.game.active_auction:
                        self._auction_rotation.pop(auction_id, None)
                    await asyncio.sleep(self._tick)
                    continue

            # Normal turn flow
            current = self.game.get_current_player()
            role = self.roles[current.player_id]
            actions = get_legal_actions(self.game, current.player_id)
            if not actions:
                # End turn to keep game moving
                self.game.end_turn()
                await asyncio.sleep(self._tick)
                continue

            if role == "human":
                # Wait for external action
                await self._wait_for_external_action()
                continue
            else:
                agent = self.agents[current.player_id]
                action = agent.choose_action(self.game, actions)
                if action is None:
                    self.game.end_turn()
                    await asyncio.sleep(self._tick)
                    continue
                apply_action(self.game, action)
                await asyncio.sleep(self._tick)

        # Final flush and broadcast end state
        await self.flush_and_broadcast()

        # Update final status and results in DB (best-effort)
        try:
            async with session_scope() as session:
                repo = self._game_repo or GameRepository(session)
                service = GameService(repo)
                db_game = await repo.get_game_by_id(self.game_id)
                if db_game:
                    # Update game status and metadata
                    status = "finished" if self.game.game_over else "stopped"
                    await service.update_status(
                        game_id=self.game_id,
                        status=status,
                        finished_at=datetime.now(timezone.utc),
                        winner_id=self.game.winner,
                        total_turns=self.game.turn_number,
                    )

                    # Compute placements by net worth (desc)
                    standings = []
                    for pid, p in self.game.players.items():
                        try:
                            net_worth = self.game._calculate_net_worth(pid)  # engine helper
                        except Exception:
                            net_worth = p.cash
                        standings.append((pid, net_worth))
                    standings.sort(key=lambda t: (-t[1], t[0]))
                    placement_by_pid = {pid: idx + 1 for idx, (pid, _) in enumerate(standings)}

                    # Persist player results
                    for pid, p in self.game.players.items():
                        try:
                            net_worth = self.game._calculate_net_worth(pid)
                        except Exception:
                            net_worth = p.cash
                        await repo.update_player_results(
                            game_uuid=db_game.id,
                            player_id=pid,
                            final_cash=p.cash,
                            final_net_worth=net_worth,
                            is_winner=(self.game.winner == pid),
                            is_bankrupt=p.is_bankrupt,
                            placement=placement_by_pid.get(pid),
                        )
        except Exception:
            # Non-fatal; avoid crashing shutdown
            pass

    async def flush_and_broadcast(self) -> None:
        # Broadcast mapped events generated since last flush
        evs = self.game.event_log.events
        start_index = self._last_engine_idx
        mapped: List[Dict[str, Any]] = []
        if self._last_engine_idx < len(evs):
            slice_ = evs[self._last_engine_idx:]
            # Record turn start indices for querying per turn later
            from src.core.game.money import EventType as _ET
            for i, ev in enumerate(slice_):
                if ev.event_type == _ET.TURN_START:
                    # Extract turn number from details
                    d = ev.details.get("details", ev.details)
                    t = d.get("turn") if "turn" in d else d.get("turn_number")
                    if isinstance(t, int):
                        self._turn_indices.setdefault(t, self._last_engine_idx + i)
            mapped = map_events(
                self.game.board,
                slice_,
                player_positions={pid: p.position for pid, p in self.game.players.items()},
            )
            # Inform clients about new events chunk
            await self._broadcast({
                "type": "events",
                "game_id": self.game_id,
                "events": mapped,
                "from_index": self._last_engine_idx,
                "to_index": self._last_engine_idx + len(mapped) - 1,
            })
            self._last_engine_idx = len(evs)

        # Persist to JSONL
        self.logger.flush_engine_events(self.game)

        # Persist pending events to database
        if mapped and self._game_uuid:
            try:
                async with session_scope() as session:
                    repo = self._game_repo or GameRepository(session)
                    service = GameService(repo)
                    batch = []
                    for idx, e in enumerate(mapped):
                        seq = start_index + idx
                        turn_num = e.get("turn_number", self.game.turn_number)
                        payload = {k: v for k, v in e.items() if k not in {"event_type", "seq"}}
                        batch.append(
                            {
                                "sequence_number": seq,
                                "turn_number": turn_num,
                                "event_type": e["event_type"],
                                "payload": payload,
                                "actor_player_id": e.get("player_id"),
                            }
                        )
                    if batch:
                        await service.persist_events(self._game_uuid, batch)
            except Exception as e:
                logger.warning(f"Failed to persist events to DB: {e}")

        # Persist pending LLM decisions to database
        await self._flush_llm_decisions()

    async def _flush_llm_decisions(self) -> None:
        """Flush pending LLM decisions to the database."""
        if not self._pending_llm_decisions or not self._game_uuid:
            return

        decisions_to_save = self._pending_llm_decisions.copy()
        self._pending_llm_decisions.clear()

        try:
            async with session_scope() as session:
                repo = self._game_repo or GameRepository(session)
                service = GameService(repo)
                await service.persist_llm_decisions(self._game_uuid, decisions_to_save)
        except Exception as e:
            logger.error(f"Failed to save LLM decisions to database: {e}")
            # Re-queue failed decisions for retry
            self._pending_llm_decisions = decisions_to_save + self._pending_llm_decisions

    async def _wait_for_external_action(self) -> None:
        # Wait until an external action is applied or stop/pause toggled
        self._new_action_event.clear()
        try:
            await asyncio.wait_for(self._new_action_event.wait(), timeout=0.5)
        except asyncio.TimeoutError:
            # Periodic wakeup to allow status/flush
            pass

    # ---- External control helpers ----
    async def get_legal_actions(self, player_id: Optional[int] = None) -> list[dict]:
        """Return legal actions for given player (or current)."""
        pid = player_id if player_id is not None else self.game.get_current_player().player_id
        acts = get_legal_actions(self.game, pid)
        return [{"action_type": a.action_type.value, "params": dict(a.params)} for a in acts]

    async def apply_action_request(self, action_type: str, params: dict | None = None, player_id: Optional[int] = None) -> tuple[bool, str]:
        """Try to apply an action for a player. Returns (accepted, reason)."""
        from src.core.game.rules import Action  # local import to avoid cycles

        async with self._apply_lock:
            pid = player_id if player_id is not None else self.game.get_current_player().player_id
            # Validate action type
            try:
                atype = ActionType(action_type)
            except Exception:
                return False, f"unknown action_type: {action_type}"

            # Check legality
            legal = get_legal_actions(self.game, pid)
            if not any(a.action_type == atype for a in legal):
                return False, "action not legal for player"

            act = Action(atype, **(params or {}))
            ok = apply_action(self.game, act)
            await self.flush_and_broadcast()
            self._new_action_event.set()
            return (True, "") if ok else (False, "apply_action returned False")

    # ---- Status helpers ----
    async def status(self) -> Dict[str, Any]:
        actors: List[int] = []
        phase = "turn"
        if self.game.active_auction and self.game.active_auction.active_bidders:
            phase = "auction"
            actors = sorted([
                pid for pid in self.game.active_auction.active_bidders
                if self.game.active_auction.can_player_bid(pid)
            ])
        else:
            actors = [self.game.get_current_player().player_id]
        return {
            "game_id": self.game_id,
            "turn_number": self.game.turn_number,
            "current_player_id": self.game.get_current_player().player_id,
            "phase": phase,
            "actors": actors,
            "roles": self.roles,
            "game_over": self.game.game_over,
            "paused": self._paused,
            "tick_ms": int(self._tick * 1000),
        }

    async def set_paused(self, value: bool) -> None:
        self._paused = value
        if not value:
            self._new_action_event.set()

    async def set_tick_ms(self, tick_ms: int) -> None:
        self._tick = max(0.0, (tick_ms or 0) / 1000.0)
        # Nudge loop so speed applies immediately
        self._new_action_event.set()

    async def list_turns(self) -> List[Dict[str, int]]:
        # Build ranges from recorded indices
        keys = sorted(self._turn_indices.keys())
        res: List[Dict[str, int]] = []
        for idx, t in enumerate(keys):
            start = self._turn_indices[t]
            end = (self._turn_indices[keys[idx + 1]] - 1) if idx + 1 < len(keys) else (len(self.game.event_log.events) - 1)
            res.append({"turn_number": t, "from_index": start, "to_index": end})
        return res

    async def get_turn_events(self, turn_number: int) -> List[Dict[str, Any]]:
        if turn_number not in self._turn_indices:
            return []
        turns = await self.list_turns()
        target = next((r for r in turns if r["turn_number"] == turn_number), None)
        if not target:
            return []
        evs = self.game.event_log.events[target["from_index"] : target["to_index"] + 1]
        mapped = map_events(
            self.game.board,
            evs,
            player_positions={pid: p.position for pid, p in self.game.players.items()},
        )
        return mapped

    # ---- Event cursor helpers for viewers ----
    async def get_last_index(self) -> int:
        return len(self.game.event_log.events) - 1

    async def get_events_since(self, since_index: int) -> Dict[str, Any]:
        evs = self.game.event_log.events
        start = max(since_index + 1, 0)
        if start >= len(evs):
            return {"events": [], "from_index": start, "to_index": start - 1}
        mapped = map_events(
            self.game.board,
            evs[start:],
            player_positions={pid: p.position for pid, p in self.game.players.items()},
        )
        return {
            "events": mapped,
            "from_index": start,
            "to_index": len(evs) - 1,
        }

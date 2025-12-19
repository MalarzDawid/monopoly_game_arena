from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from .registry import GameRegistry
from snapshot import serialize_snapshot
from src.data import init_db, close_db, get_session, GameRepository
from src.services import GameService
from .schemas import (
    GameEventDTO,
    GameHistoryResponse,
    GameListResponse,
    GameStatsResponse,
    GameSummary,
    PlayerSummary,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle - startup and shutdown."""
    # Startup
    print("🚀 Starting Monopoly Arena Server...")
    print("📊 Initializing database connection...")
    await init_db()
    print("✅ Database ready!")

    yield

    # Shutdown
    print("🛑 Shutting down server...")
    print("📊 Closing database connection...")
    await close_db()
    print("✅ Shutdown complete!")


app = FastAPI(
    title="Monopoly Arena Server",
    version="0.2.0",
    lifespan=lifespan
)
registry = GameRegistry()


# ---- Dependencies ----
async def get_repo(session: AsyncSession = Depends(get_session)) -> GameRepository:
    return GameRepository(session)


async def get_game_service(repo: GameRepository = Depends(get_repo)) -> GameService:
    return GameService(repo)


class CreateGameRequest(BaseModel):
    players: int = Field(4, ge=2, le=8)
    agent: str = Field("greedy", pattern=r"^(greedy|random|llm)$")
    roles: Optional[list[str]] = None  # e.g., ["human","greedy","llm",...]
    seed: Optional[int] = None
    max_turns: Optional[int] = Field(default=100, ge=1)
    tick_ms: Optional[int] = Field(default=500, ge=0, le=10000)
    llm_strategy: str = Field("balanced", pattern=r"^(aggressive|balanced|defensive)$")


class CreateGameResponse(BaseModel):
    game_id: str


@app.post("/games", response_model=CreateGameResponse)
async def create_game(req: CreateGameRequest):
    gid = await registry.create_game(
        num_players=req.players,
        agent=req.agent,
        seed=req.seed,
        max_turns=req.max_turns,
        roles=req.roles,
        tick_ms=req.tick_ms,
        llm_strategy=req.llm_strategy,
    )
    return CreateGameResponse(game_id=gid)


@app.get("/games/{game_id}/snapshot")
async def get_snapshot(game_id: str):
    runner = await registry.get(game_id)
    if not runner:
        raise HTTPException(status_code=404, detail="Game not found")
    return serialize_snapshot(runner.game)


class ActionRequest(BaseModel):
    player_id: int | None = None
    action_type: str
    params: dict = Field(default_factory=dict)


class ActionResponse(BaseModel):
    accepted: bool
    reason: str | None = None


@app.get("/games/{game_id}/legal_actions")
async def legal_actions(game_id: str, player_id: int | None = None):
    runner = await registry.get(game_id)
    if not runner:
        raise HTTPException(status_code=404, detail="Game not found")
    acts = await runner.get_legal_actions(player_id)
    return {"game_id": game_id, "player_id": player_id, "actions": acts}


@app.post("/games/{game_id}/actions", response_model=ActionResponse)
async def apply_action(game_id: str, req: ActionRequest):
    runner = await registry.get(game_id)
    if not runner:
        raise HTTPException(status_code=404, detail="Game not found")

    ok, reason = await runner.apply_action_request(req.action_type, req.params, req.player_id)
    return ActionResponse(accepted=ok, reason=None if ok else reason)


@app.get("/games/{game_id}/status")
async def get_status(game_id: str):
    runner = await registry.get(game_id)
    if not runner:
        raise HTTPException(status_code=404, detail="Game not found")
    return await runner.status()


class SpeedRequest(BaseModel):
    tick_ms: int = Field(ge=0, le=10000)


@app.post("/games/{game_id}/speed")
async def set_speed(game_id: str, req: SpeedRequest):
    runner = await registry.get(game_id)
    if not runner:
        raise HTTPException(status_code=404, detail="Game not found")
    await runner.set_tick_ms(req.tick_ms)
    return {"game_id": game_id, "tick_ms": req.tick_ms}


@app.websocket("/ws/games/{game_id}")
async def ws_game(websocket: WebSocket, game_id: str):
    await websocket.accept()
    runner = await registry.get(game_id)
    if not runner:
        await websocket.close(code=4404)
        return

    queue = await runner.subscribe()
    # Proactively broadcast any pending events so clients don't block
    await runner.flush_and_broadcast()
    # Support backlog catch-up via query param ?since=<index>
    try:
        since_raw = websocket.query_params.get("since")
        if since_raw is not None:
            try:
                since_idx = int(since_raw)
                delta = await runner.get_events_since(since_idx)
                if delta["events"]:
                    await websocket.send_json({
                        "type": "events",
                        "game_id": game_id,
                        **delta,
                    })
            except Exception:
                # Ignore malformed since param
                pass
    except Exception:
        pass
    try:
        # Start a task to forward outbound messages
        async def sender():
            while True:
                msg = await queue.get()
                await websocket.send_json(msg)

        sender_task = asyncio.create_task(sender())
        # Heartbeat pings to keep connection alive (every 5s)
        async def heartbeat():
            try:
                while True:
                    await asyncio.sleep(5)
                    await websocket.send_json({"type": "heartbeat"})
            except Exception:
                return

        hb_task = asyncio.create_task(heartbeat())

        # Basic receive loop: ignore inputs for now (future: actions)
        while True:
            try:
                await websocket.receive_text()
            except WebSocketDisconnect:
                break
    finally:
        await runner.unsubscribe(queue)
        try:
            sender_task.cancel()
        except Exception:
            pass
        try:
            hb_task.cancel()
        except Exception:
            pass


@app.post("/games/{game_id}/pause")
async def pause_game(game_id: str):
    runner = await registry.get(game_id)
    if not runner:
        raise HTTPException(status_code=404, detail="Game not found")
    await runner.set_paused(True)
    return {"game_id": game_id, "paused": True}


@app.post("/games/{game_id}/resume")
async def resume_game(game_id: str):
    runner = await registry.get(game_id)
    if not runner:
        raise HTTPException(status_code=404, detail="Game not found")
    await runner.set_paused(False)
    return {"game_id": game_id, "paused": False}


@app.get("/games/{game_id}/turns")
async def list_turns(game_id: str):
    runner = await registry.get(game_id)
    if not runner:
        raise HTTPException(status_code=404, detail="Game not found")
    return {"game_id": game_id, "turns": await runner.list_turns()}


@app.get("/games/{game_id}/turns/{turn_number}")
async def get_turn_events(game_id: str, turn_number: int):
    runner = await registry.get(game_id)
    if not runner:
        raise HTTPException(status_code=404, detail="Game not found")
    events = await runner.get_turn_events(turn_number)
    return {"game_id": game_id, "turn_number": turn_number, "events": events}


# ---- Database History Endpoints ----

@app.get("/api/games", response_model=GameListResponse)
async def list_all_games(
    limit: int = 100,
    offset: int = 0,
    status: Optional[str] = None,
    service: GameService = Depends(get_game_service),
):
    """List all games from database."""
    games = await service.list_games(limit=limit, offset=offset, status=status)

    return GameListResponse(
        games=[
            GameSummary(
                game_id=g.game_id,
                status=g.status,
                total_turns=g.total_turns,
                created_at=g.created_at,
                started_at=g.started_at,
                finished_at=g.finished_at,
                winner_id=g.winner_id,
                config=g.config,
                players=[
                    PlayerSummary(
                        player_id=p.player_id,
                        name=p.name,
                        agent_type=p.agent_type,
                        is_winner=p.is_winner,
                        final_cash=p.final_cash,
                        final_net_worth=p.final_net_worth,
                    )
                    for p in g.players
                ],
            )
            for g in games
        ],
        limit=limit,
        offset=offset,
    )


@app.get("/api/games/{game_id}/history", response_model=GameHistoryResponse)
async def get_game_history(
    game_id: str,
    service: GameService = Depends(get_game_service),
):
    """Get full game history with all events from database."""
    result = await service.get_game_with_events(game_id)

    if not result:
        raise HTTPException(status_code=404, detail="Game not found in database")

    game, events = result

    game_summary = GameSummary(
        game_id=game.game_id,
        status=game.status,
        total_turns=game.total_turns,
        created_at=game.created_at,
        started_at=game.started_at,
        finished_at=game.finished_at,
        winner_id=game.winner_id,
        config=game.config,
        players=[
            PlayerSummary(
                player_id=p.player_id,
                name=p.name,
                agent_type=p.agent_type,
                is_winner=p.is_winner,
                final_cash=p.final_cash,
                final_net_worth=p.final_net_worth,
            )
            for p in game.players
        ],
    )

    return GameHistoryResponse(
        game=game_summary,
        events=[
            GameEventDTO(
                sequence_number=e.sequence_number,
                turn_number=e.turn_number,
                event_type=e.event_type,
                timestamp=e.timestamp,
                payload=e.payload,
                actor_player_id=e.actor_player_id,
            )
            for e in events
        ],
        total_events=len(events),
    )


@app.get("/api/games/{game_id}/stats", response_model=GameStatsResponse)
async def get_game_stats(
    game_id: str,
    service: GameService = Depends(get_game_service),
):
    """Get game statistics from database."""
    repo = service.repo
    game = await repo.get_game_by_id(game_id)

    if not game:
        raise HTTPException(status_code=404, detail="Game not found in database")

    stats = await service.get_game_stats(game.id)

    return GameStatsResponse(
        game_id=game_id,
        status=game.status,
        total_turns=game.total_turns,
        statistics=stats,
    )


# ---- Static UI ----
@app.get("/")
async def root():
    return RedirectResponse(url="/ui/")


# Get static directory path relative to this file
STATIC_DIR = Path(__file__).parent / "static"
app.mount("/ui", StaticFiles(directory=str(STATIC_DIR), html=True), name="ui")

# Disable caching for static UI to make sure latest JS/CSS is loaded
@app.middleware("http")
async def no_cache_ui(request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/ui/"):
        response.headers["Cache-Control"] = "no-store"
    return response


if __name__ == "__main__":
    # Convenience entrypoint for running directly: python monopoly_game_arena/server/app.py
    import uvicorn

    uvicorn.run("monopoly_game_arena.server.app:app", host="0.0.0.0", port=8000, reload=True)

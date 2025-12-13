from __future__ import annotations

import asyncio
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from monopoly_game_arena.server.registry import GameRegistry
from monopoly_game_arena.snapshot import serialize_snapshot


app = FastAPI(title="Monopoly Arena Server", version="0.1.0")
registry = GameRegistry()


class CreateGameRequest(BaseModel):
    players: int = Field(4, ge=2, le=8)
    agent: str = Field("greedy", pattern=r"^(greedy|random)$")
    roles: Optional[list[str]] = None  # e.g., ["human","greedy",...]
    seed: Optional[int] = None
    max_turns: Optional[int] = Field(default=100, ge=1)
    tick_ms: Optional[int] = Field(default=500, ge=0, le=10000)


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


# ---- Static UI ----
@app.get("/")
async def root():
    return RedirectResponse(url="/ui/")


app.mount("/ui", StaticFiles(directory="monopoly_game_arena/server/static", html=True), name="ui")

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

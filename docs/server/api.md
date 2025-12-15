## REST API

The server exposes REST endpoints for game creation, control, and historical queries.

Base URL: `http://localhost:8000`

### Game Creation

**POST /games** - Create new game

```python
import httpx

response = httpx.post("http://localhost:8000/games", json={
    "players": 4,
    "agent": "greedy",
    "seed": 42,
    "max_turns": 100,
    "tick_ms": 500
})
game_id = response.json()["game_id"]
```

Request parameters:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `players` | int | 4 | Number of players (2‑8) |
| `agent` | str | "greedy" | Default agent type ("greedy" or "random") |
| `roles` | list[str] | None | Per‑player roles, e.g. `["human", "greedy", "random"]` |
| `seed` | int | None | RNG seed for deterministic gameplay |
| `max_turns` | int | 100 | Maximum turns before game ends |
| `tick_ms` | int | 500 | Milliseconds between actions (0‑10000) |

### Game State

**GET /games/{game_id}/snapshot** - Current game state

Returns full serialized game snapshot with players, properties, positions, cash, etc.

**GET /games/{game_id}/status** - Game status

```json
{
  "game_id": "abc123",
  "turn_number": 15,
  "current_player_id": 2,
  "phase": "turn",
  "actors": [2],
  "roles": ["human", "greedy", "random", "greedy"],
  "game_over": false,
  "paused": false,
  "tick_ms": 500
}
```

**GET /games/{game_id}/legal_actions** - Query legal actions

Query param: `player_id` (optional, defaults to current player)

```json
[
  {"action_type": "ROLL_DICE", "params": {}},
  {"action_type": "END_TURN", "params": {}}
]
```

### Player Actions

**POST /games/{game_id}/actions** - Apply action

```python
response = httpx.post(f"http://localhost:8000/games/{game_id}/actions", json={
    "player_id": 0,
    "action_type": "ROLL_DICE",
    "params": {}
})
result = response.json()
# {"accepted": true, "reason": ""}
```

Common action types:

| Action | Params | Description |
|--------|--------|-------------|
| `ROLL_DICE` | `{}` | Roll dice to move |
| `BUY_PROPERTY` | `{"amount": int}` | Purchase landed property |
| `END_TURN` | `{}` | End current turn |
| `BID` | `{"amount": int}` | Bid in auction |
| `PASS_AUCTION` | `{}` | Pass on auction bid |
| `BUILD_HOUSE` | `{"position": int}` | Build house on property |
| `MORTGAGE` | `{"position": int}` | Mortgage property |
| `UNMORTGAGE` | `{"position": int}` | Pay off mortgage |
| `PAY_JAIL_FINE` | `{}` | Pay $50 to leave jail |
| `USE_JAIL_CARD` | `{}` | Use Get Out of Jail card |

### Game Control

**POST /games/{game_id}/pause** - Pause game

Suspends agent actions; human players can still inject actions.

**POST /games/{game_id}/resume** - Resume game

Resumes agent‑driven gameplay.

**POST /games/{game_id}/speed** - Set game speed

```python
httpx.post(f"http://localhost:8000/games/{game_id}/speed", json={
    "tick_ms": 200
})
```

### Event Queries

**GET /games/{game_id}/turns** - List all turns

```json
[
  {"turn_number": 0, "from_index": 0, "to_index": 5},
  {"turn_number": 1, "from_index": 6, "to_index": 12}
]
```

**GET /games/{game_id}/turns/{turn_number}** - Events for specific turn

Returns mapped events in client‑friendly format for replay.

### Historical Queries

**GET /api/games** - List all historical games

Query params: `limit` (default 100), `offset`, `status`

**GET /api/games/{game_id}/history** - Full game history

Returns game metadata and complete event log from database.

**GET /api/games/{game_id}/stats** - Game statistics

Returns aggregated statistics for the game.

### Static UI

| Endpoint | Description |
|----------|-------------|
| `GET /` | Redirects to `/ui/` |
| `GET /ui/` | Web UI for gameplay |
| `GET /docs` | OpenAPI documentation |

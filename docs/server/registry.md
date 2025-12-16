## GameRegistry

In‑memory registry managing active game sessions. Creates games, tracks runners, and handles cleanup.

### Usage

```python
from server.registry import GameRegistry

registry = GameRegistry()

# Create new game
game_id = await registry.create_game(
    num_players=4,
    agent="greedy",
    seed=42,
    max_turns=100,
    tick_ms=500
)

# Get active game
runner = await registry.get(game_id)
if runner:
    status = await runner.status()

# Stop game
await registry.stop(game_id)
```

### Player Roles

The `roles` parameter allows mixing human and AI players:

```python
# First player human, rest AI
game_id = await registry.create_game(
    num_players=4,
    roles=["human", "greedy", "random", "greedy"]
)
```

Role types:

| Role | Description |
|------|-------------|
| `human` | Waits for external action via REST API |
| `greedy` | AI that prefers buying and building |
| `random` | AI that picks random legal actions |
| `llm` | LLM‑powered agent (future) |

### Default Player Names

Games use these default names: Alice, Bob, Charlie, Diana, Eve, Frank, Grace, Hank.

### Game ID Format

Game IDs are 12‑character hexadecimal strings generated from `secrets.token_hex(6)`.

### Reference

::: server.registry.GameRegistry

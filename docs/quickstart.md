## Quickstart

This guide shows how to create a game, add players, make moves, and run a simple simulation.

### Create a game

```python
from monopoly import GameConfig, create_game, Player

# Define players
players = [
    Player(0, "Alice"),
    Player(1, "Bob"),
]

# Configure and create the game (seed for reproducibility)
config = GameConfig(seed=42)
game = create_game(config, players)

print(game.get_current_player())  # PlayerState(...)
```

### Query legal actions and apply them

Use the high‑level rules API to get legal actions and apply one.

```python
from monopoly.rules import get_legal_actions, apply_action, Action
from monopoly.game import ActionType

pid = game.get_current_player().player_id

# Ask the engine what this player can legally do now
legal = get_legal_actions(game, pid)
print([a.action_type for a in legal])

# Example: roll dice if allowed
action = next(a for a in legal if a.action_type == ActionType.ROLL_DICE)
apply_action(game, action)

# After movement, you may be offered BUY_PROPERTY / DECLINE_PURCHASE, etc.
legal = get_legal_actions(game, pid)
```

### Add players (users)

Players are simple `Player` objects with an ID and name. You pass a list of players to `create_game`.

```python
players = [Player(i, name) for i, name in enumerate(["Alice", "Bob", "Charlie"])]
game = create_game(GameConfig(seed=123), players)
```

### Use built‑in agents

Two simple agents are included for simulations: `RandomAgent` and `GreedyAgent`.

```python
from agents import RandomAgent, GreedyAgent
from monopoly.rules import get_legal_actions

agents = [GreedyAgent(0, "Alice"), RandomAgent(1, "Bob")]

while not game.game_over:
    current = game.get_current_player()
    legal = get_legal_actions(game, current.player_id)
    if not legal:
        game.end_turn()
        continue
    action = agents[current.player_id].choose_action(game, legal)
    if action:
        from monopoly.rules import apply_action
        apply_action(game, action)
```

### CLI simulation

Run a complete simulation using the CLI script.

```bash
python monopoly_game_arena/play_monopoly.py --players 4 --agent greedy --seed 42 --max-turns 200
```

Flags:

- `--players` 2–8 players
- `--agent` `random` or `greedy`
- `--seed` deterministic RNG seed
- `--max-turns` optional time‑limit variant

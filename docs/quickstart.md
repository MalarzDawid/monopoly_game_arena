## Quickstart

This guide shows how to create a game, add players, make moves, and run simulations with different agents.

### Create a game

```python
from src.core import GameConfig, Player, create_game

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

Use the high-level rules API to get legal actions and apply one.

```python
from src.core.game.rules import get_legal_actions, apply_action, Action
from src.core.game.game import ActionType

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

### Use built-in agents

Three agents are included for simulations:

| Agent | Description |
|-------|-------------|
| `RandomAgent` | Random legal moves |
| `GreedyAgent` | Prefers buying properties |
| `LLMAgent` | LLM-powered strategic decisions |

```python
from src.core.agents import RandomAgent, GreedyAgent, LLMAgent
from src.core.game.rules import get_legal_actions, apply_action

agents = [
    GreedyAgent(0, "Alice"),
    RandomAgent(1, "Bob"),
    LLMAgent(2, "Charlie", strategy="balanced"),
]

while not game.game_over:
    current = game.get_current_player()
    legal = get_legal_actions(game, current.player_id)
    if not legal:
        game.end_turn()
        continue
    action = agents[current.player_id].choose_action(game, legal)
    if action:
        apply_action(game, action)
```

### LLM Agent Setup

LLMAgent requires an LLM backend. Supported options:

**Ollama (recommended for local development):**
```bash
# Install Ollama from https://ollama.ai
ollama pull gemma3:4b
ollama serve  # Runs on port 11434
```

**vLLM (for production/GPU):**
```bash
pip install vllm
python -m vllm.entrypoints.openai.api_server --model google/gemma-3-4b-it
```

**Configuration via environment variables:**
```bash
# .env file
LLM_BASE_URL=http://localhost:11434/v1  # Ollama
LLM_MODEL=gemma3:4b
```

**Usage:**
```python
from agents import LLMAgent

# Uses environment variables by default
agent = LLMAgent(0, "AI Player")

# Or configure explicitly
agent = LLMAgent(
    player_id=0,
    name="AI Player",
    model_name="gemma3:4b",
    strategy="aggressive",  # aggressive, balanced, defensive
    base_url="http://localhost:11434/v1",
)
```

### CLI simulation

Run a complete simulation using the CLI script.

```bash
# Greedy agents (default)
PYTHONPATH=$(pwd) uv run python play_monopoly.py --players 4 --agent greedy --seed 42

# Random agents
uv run python play_monopoly.py --players 4 --agent random

# LLM agents
uv run python play_monopoly.py --players 4 --agent llm --llm-strategy balanced
```

Flags:

| Flag | Description |
|------|-------------|
| `--players` | Number of players (2-8) |
| `--agent` | Agent type: `random`, `greedy`, `llm` |
| `--seed` | Deterministic RNG seed |
| `--max-turns` | Optional turn limit |
| `--llm-strategy` | LLM strategy: `aggressive`, `balanced`, `defensive` |
| `--llm-model` | Model name (default from env) |
| `--llm-base-url` | API base URL (default from env) |

### Batch Games

Run multiple games for testing, data collection, or LLM training:

```bash
# Run 10 games with greedy agents
uv run python scripts/batch_games.py -n 10 -p 4 -a greedy

# Run 5 games with LLM agents (balanced strategy)
uv run python scripts/batch_games.py -n 5 -p 4 -a llm -s balanced

# Run games with mixed agent roles
uv run python scripts/batch_games.py -n 5 --roles llm,greedy,greedy,random

# Run 9 games rotating through all LLM strategies
uv run python scripts/batch_games.py -n 9 -p 4 -a llm --multi-strategy

# Run games in parallel (5 games with 5 workers)
uv run python scripts/batch_games.py -n 5 -w 5 -a llm -s balanced

# Run without database saving (JSONL only)
uv run python scripts/batch_games.py -n 10 -a greedy --no-db
```

Batch game flags:

| Flag | Description |
|------|-------------|
| `-n, --games` | Number of games to run (default: 5) |
| `-p, --players` | Number of players (2-8, default: 4) |
| `-a, --agent` | Agent type: `random`, `greedy`, `llm` |
| `-t, --max-turns` | Maximum turns per game (default: 100) |
| `-s, --llm-strategy` | LLM strategy: `aggressive`, `balanced`, `defensive` |
| `--roles` | Custom roles (comma-separated, e.g., `llm,greedy,greedy,random`) |
| `--multi-strategy` | Rotate through all LLM strategies |
| `-w, --workers` | Parallel workers (default: 1 = sequential) |
| `--no-db` | Disable database saving (only write JSONL files) |
| `-q, --quiet` | Less verbose output |

Output includes:
- Per-game results (turns, winner, time)
- Win distribution statistics
- Turn statistics (min/max/average)
- Strategy breakdown (for multi-strategy runs)
- JSONL log files for each game

### Running the Server

Start the FastAPI server to play via web UI:

```bash
# Start database
make db-up

# Apply migrations
make db-migrate

# Start server
make server
```

Access:
- Web UI: http://localhost:8000/ui/
- API docs: http://localhost:8000/docs

### Creating Games via API

```bash
# Create game with greedy agents
curl -X POST http://localhost:8000/games \
  -H "Content-Type: application/json" \
  -d '{"players": 4, "roles": ["greedy", "greedy", "greedy", "greedy"]}'

# Create game with mixed agents
curl -X POST http://localhost:8000/games \
  -H "Content-Type: application/json" \
  -d '{"players": 4, "roles": ["llm", "greedy", "random", "human"]}'
```

### Next Steps

- [Agents Architecture](agents/index.md) - Learn about different agent types
- [LLMAgent](agents/llm.md) - Configure LLM-powered agents
- [Rules API](monopoly/rules_api.md) - Game mechanics reference
- [Database](server/database/index.md) - Persistence and event sourcing

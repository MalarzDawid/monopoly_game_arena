## Quickstart

This guide walks you from zero to a running stack: database, API server, web UI, dashboard, and programmatic access to the engine and agents.

---

## 1. Prerequisites

Before you start, make sure you have:

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) (for dependency management)
- Docker + Docker Compose (for PostgreSQL)

Check your tools:

```bash
python --version
uv --version
docker --version
docker compose version  # or: docker-compose --version
```

---

## 2. Clone and install

```bash
git clone <YOUR_REPO_URL>
cd monopolyv3

# Create your environment configuration
cp env.example .env

# Install Python dependencies (creates .venv and installs the project)
make install
```

---

## 3. Configure environment

Open `.env` in the project root and adjust it to your environment. The most important sections are:

```bash
# Database configuration
DATABASE_URL=postgresql+asyncpg://monopoly_user:monopoly_pass@localhost:5432/monopoly_arena
DATABASE_URL_SYNC=postgresql://monopoly_user:monopoly_pass@localhost:5432/monopoly_arena

# LLM configuration
LLM_PROVIDER=ollama
LLM_BASE_URL=http://localhost:11434/v1
LLM_MODEL=gemma3:4b
# LLM_API_KEY=your-secret-key

# Dashboard / API configuration
DASHBOARD_HOST=127.0.0.1
DASHBOARD_PORT=8050
MAIN_SERVER_URL=http://localhost:8000
```

You can always refer to `env.example` for all available options.

Internally, these values are loaded via:

- `data.config.DatabaseSettings` for database configuration
- `settings.LLMSettings` for LLM configuration
- `settings.DashboardSettings` for dashboard and API endpoints

---

## 4. Start PostgreSQL and apply migrations

Start the database in Docker and bring the schema up to date:

```bash
# Start PostgreSQL container
make db-up

# Apply Alembic migrations
make db-migrate
```

You can verify connectivity with:

```bash
make db-test
```

---

## 5. Run the API server and web UI

```bash
make server
```

By default the server runs on `http://localhost:8000`.

Key endpoints:

- Web UI: `http://localhost:8000/ui/`
- API docs: `http://localhost:8000/docs`

---

## 6. Run the analytics dashboard (optional)

In a separate terminal:

```bash
make dashboard
```

The dashboard will be available at:

- Dashboard: `http://localhost:8050`

---

## 7. CLI simulations

You can run full games from the command line without the UI.

```bash
# Greedy agents (default)
uv run python scripts/play_monopoly.py --players 4 --agent greedy --seed 42

# Random agents
uv run python scripts/play_monopoly.py --players 4 --agent random

# LLM agents (requires a running LLM backend)
uv run python scripts/play_monopoly.py --players 4 --agent llm --llm-strategy balanced
```

Useful flags:

| Flag | Description |
|------|-------------|
| `--players` | Number of players (2‑8) |
| `--agent` | Agent type: `random`, `greedy`, `llm` |
| `--seed` | Deterministic RNG seed |
| `--max-turns` | Optional turn limit |
| `--llm-strategy` | LLM strategy: `aggressive`, `balanced`, `defensive` |
| `--llm-model` | Model name (default from env) |
| `--llm-base-url` | API base URL (default from env) |

For batch runs, see the **Batch Games** section below.

---

## 8. Programmatic engine usage

The following sections show how to use the core engine and agents directly from Python.

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
# .env file (see env.example for full list)
LLM_PROVIDER=ollama
LLM_BASE_URL=http://localhost:11434/v1  # Ollama
LLM_MODEL=gemma3:4b
LLM_TIMEOUT_SECONDS=30
LLM_MAX_TOKENS=512
```

**Usage:**
```python
from src.core.agents import LLMAgent

# Uses environment variables (LLM_*) by default
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

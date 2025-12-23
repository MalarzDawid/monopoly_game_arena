# Monopoly Game Arena

A deterministic, fully-tested Monopoly rules engine designed for AI agent competitions.

## Features

### Core Game Engine
- Standard 40-space board with 8 color groups
- All spaces: properties, railroads, utilities, taxes, cards
- Turn flow, doubles, jail mechanics, passing GO
- Property purchases and auctions with 10% starting bid
- Building system with even-build rule
- Mortgages and trading

### AI Agents
- **RandomAgent** - Random legal moves
- **GreedyAgent** - Strategic property buying
- **LLMAgent** - LLM-powered decisions via OpenAI-compatible API
  - Supports Ollama, vLLM, and OpenAI
  - Three strategy profiles: aggressive, balanced, defensive
  - Full decision logging for analysis

### Server & Database
- FastAPI REST API and WebSocket for real-time games
- PostgreSQL with event sourcing
- Web UI with color-coded board visualization
- LLM decision tracking and full-text search

## Quick Links

| Section | Description |
|---------|-------------|
| [Quickstart](quickstart.md) | Get started in 5 minutes |
| [Batch Games](quickstart.md#batch-games) | Run multiple games for testing |
| [Agents](agents/index.md) | AI agent architecture |
| [LLMAgent](agents/llm.md) | Configure LLM-powered agents |
| [Game Rules](monopoly/index.md) | Core engine reference |
| [Auctions](monopoly/auction.md) | Auction system with auto-bid |
| [Server](server/index.md) | API and WebSocket docs |
| [Database](server/database/index.md) | Event sourcing and models |

## Installation

```bash
# Clone repository (replace with your URL)
git clone <YOUR_REPO_URL>
cd monopolyv3

# Copy and configure environment
cp env.example .env
# Edit .env to match your local setup (database, LLM, dashboard)

# Install dependencies using uv
make install

# Set up database
make db-up
make db-migrate

# Run tests
make test
```

## Running Games

### CLI Simulation
```bash
# With greedy agents
uv run python scripts/play_monopoly.py --players 4 --agent greedy

# With LLM agents (requires Ollama or vLLM)
uv run python scripts/play_monopoly.py --players 4 --agent llm --llm-strategy balanced

# Or use Makefile shortcuts
make play           # single game (defaults)
make batch-llm      # batch of LLM games
```

### Web Server
```bash
make server
# Open http://localhost:8000/ui/
```

## LLM Configuration

LLMAgent is configured via environment variables read by `LLMSettings` in `src/settings.py`.

```bash
# Backend provider: ollama | vllm | openai | custom
LLM_PROVIDER=ollama

# Base URL for OpenAI-compatible API
# - Ollama (default): http://localhost:11434/v1
# - vLLM:             http://localhost:8000/v1
LLM_BASE_URL=http://localhost:11434/v1

# Model name / identifier
LLM_MODEL=gemma3:4b

# Optional API key (for OpenAI / secured vLLM deployments)
# LLM_API_KEY=your-secret-key

# Timeouts and limits
LLM_TIMEOUT_SECONDS=30
LLM_MAX_TOKENS=512
```

## Architecture Overview

```
monopolyv3/
├── src/core/          # Core game engine (pure logic)
├── src/core/agents/   # AI agents (Random, Greedy, LLM)
├── src/data/          # Database config, models, repository, sessions
├── src/services/      # Application services (GameService, etc.)
├── server/            # FastAPI app, registry, runner, dashboard API, static UI
├── scripts/           # CLI tools (play_monopoly, batch_games, analyzers)
├── templates/         # LLM strategy prompts
├── docs/              # This documentation
└── tests/             # Pytest test suite
```

## What's New

### Batch Game Runner
- Run multiple games for testing and data collection
- Support for parallel execution with configurable workers
- Mixed agent roles (LLM, greedy, random combinations)
- Multi-strategy rotation for LLM comparison
- Automatic database persistence with JSONL logging
- Comprehensive statistics output (win rates, turn counts)

### LLMAgent Implementation
- Full implementation with OpenAI-compatible API
- Support for Ollama and vLLM backends
- Three strategy profiles with customizable prompts
- Automatic decision logging to database
- Per-player decision sequence tracking

### Auction System Improvements
- Initiator automatically places 10% starting bid
- Properties always find an owner
- No more stuck auctions

### Web UI Enhancements
- Color-coded property groups (like real Monopoly board)
- House and hotel indicators
- Player cash display
- Hover tooltips for property info

### Database Schema
- LLM decision tracking with full game state snapshots
- Player LLM configuration fields (model, parameters, strategy)
- Full-text search on reasoning and strategy descriptions
- Per-player decision sequences for multi-LLM games

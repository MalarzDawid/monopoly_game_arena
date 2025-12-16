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
| [Agents](agents/index.md) | AI agent architecture |
| [LLMAgent](agents/llm.md) | Configure LLM-powered agents |
| [Game Rules](monopoly/index.md) | Core engine reference |
| [Auctions](monopoly/auction.md) | Auction system with auto-bid |
| [Server](server/index.md) | API and WebSocket docs |
| [Database](server/database/index.md) | Event sourcing and models |

## Installation

```bash
# Clone repository
git clone https://github.com/your-repo/monopoly_game_arena.git
cd monopoly_game_arena

# Install dependencies
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
uv run python play_monopoly.py --players 4 --agent greedy

# With LLM agents (requires Ollama or vLLM)
uv run python play_monopoly.py --players 4 --agent llm --llm-strategy balanced
```

### Web Server
```bash
make server
# Open http://localhost:8000/ui/
```

## LLM Configuration

For LLMAgent, set environment variables:

```bash
# Ollama (default)
LLM_BASE_URL=http://localhost:11434/v1
LLM_MODEL=gemma3:4b

# vLLM
LLM_BASE_URL=http://localhost:8000/v1
LLM_MODEL=google/gemma-3-4b-it
```

## Architecture Overview

```
monopoly_game_arena/
├── monopoly/          # Core game engine (pure logic)
├── agents/            # AI agents (Random, Greedy, LLM)
├── server/            # FastAPI + WebSocket + Database
├── templates/         # LLM strategy prompts
├── docs/              # This documentation
└── tests/             # Pytest test suite
```

## What's New

### LLMAgent Implementation
- Full implementation with OpenAI-compatible API
- Support for Ollama and vLLM backends
- Three strategy profiles with customizable prompts
- Automatic decision logging to database

### Auction System Improvements
- Initiator automatically places 10% starting bid
- Properties always find an owner
- No more stuck auctions

### Web UI Enhancements
- Color-coded property groups (like real Monopoly board)
- House and hotel indicators
- Player cash display
- Hover tooltips for property info

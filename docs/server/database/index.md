## Database Architecture

PostgreSQL database with SQLAlchemy ORM implementing event sourcing for complete game history.

### Event Sourcing Pattern

All game state changes are recorded as immutable events, enabling:

- Full game replay from event log
- Time‑travel debugging
- Historical analysis and statistics
- Audit trail of all actions

```mermaid
flowchart LR
  subgraph Engine
    GS[GameState]
    EL[EventLog]
  end

  subgraph Persistence
    GL[GameLogger]
    REPO[GameRepository]
  end

  subgraph PostgreSQL
    G[(games)]
    P[(players)]
    E[(game_events)]
    L[(llm_decisions)]
  end

  GS --> EL
  EL --> GL
  GL --> REPO
  REPO --> G
  REPO --> P
  REPO --> E
  REPO --> L
```

### Schema Overview

```mermaid
erDiagram
  games ||--o{ players : has
  games ||--o{ game_events : logs
  games ||--o{ llm_decisions : tracks

  games {
    uuid id PK
    string game_id UK
    datetime created_at
    datetime started_at
    datetime finished_at
    string status
    jsonb config
    int winner_id
    int total_turns
    jsonb metadata
  }

  players {
    uuid id PK
    uuid game_uuid FK
    int player_id
    string name
    string agent_type
    int final_cash
    int final_net_worth
    bool is_winner
    bool is_bankrupt
    int placement
    string llm_model_name
    jsonb llm_parameters
  }

  game_events {
    uuid id PK
    uuid game_uuid FK
    bigint sequence_number
    int turn_number
    string event_type
    datetime timestamp
    jsonb payload
    int actor_player_id
  }

  llm_decisions {
    uuid id PK
    uuid game_uuid FK
    int player_id
    int turn_number
    bigint sequence_number
    datetime timestamp
    jsonb game_state
    jsonb player_state
    jsonb available_actions
    text prompt
    text reasoning
    jsonb chosen_action
    text strategy_description
    int processing_time_ms
    string model_version
  }
```

### Tables

| Table | Purpose |
|-------|---------|
| `games` | Game session metadata and configuration |
| `players` | Per‑player information and final stats |
| `game_events` | Immutable event log (event sourcing) |
| `llm_decisions` | LLM reasoning and decision context |

### Key Concepts

**Sequence Numbers**: Events have monotonically increasing `sequence_number` (0, 1, 2, ...) ensuring strict ordering and enabling catch‑up queries.

**LLM Decision Sequences**: Each LLM player has their own decision sequence per game. The unique constraint is on `(game_uuid, player_id, sequence_number)`, allowing multiple players to have independent sequences.

**JSONB Payloads**: Event data stored as JSONB for flexibility. Each event type has different payload structure.

**Cascade Deletes**: Deleting a game removes all related players, events, and LLM decisions.

**Connection Pooling**: Async engine with configurable pool size for concurrent access.

### Async Operations

All database operations use async/await:

```python
from data import session_scope, GameRepository

async with session_scope() as session:
    repo = GameRepository(session)
    game = await repo.get_game_by_id("abc123")
    events = await repo.get_game_events(game.id)
```

### Module Reference

| Module | Purpose |
|--------|---------|
| `models.py` | SQLAlchemy ORM models |
| `repository.py` | Database operations (GameRepository) |
| `session.py` | Session and connection management |
| `config.py` | Database configuration from environment |

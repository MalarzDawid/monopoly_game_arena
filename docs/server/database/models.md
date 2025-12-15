## Database Models

SQLAlchemy ORM models for game persistence with event sourcing.

### Game Model

Tracks game session metadata:

```python
from server.database.models import Game

# Fields
game.id           # UUID primary key
game.game_id      # Human-readable ID (e.g., "abc123def456")
game.status       # "created" | "running" | "paused" | "finished" | "error"
game.config       # JSONB game configuration
game.winner_id    # Player ID of winner (if finished)
game.total_turns  # Final turn count
game.created_at   # Creation timestamp
game.started_at   # Start timestamp
game.finished_at  # Completion timestamp
game.metadata     # Flexible JSONB metadata

# Relationships
game.players      # List of Player objects (eager loaded)
game.events       # List of GameEvent objects (lazy loaded)
game.llm_decisions  # List of LLMDecision objects (lazy loaded)
```

### Player Model

Per‑player information for each game:

```python
from server.database.models import Player

# Core fields
player.id           # UUID primary key
player.game_uuid    # Foreign key to Game
player.player_id    # Player index (0, 1, 2, ...)
player.name         # Display name
player.agent_type   # "greedy" | "random" | "human" | "llm"

# Final stats
player.final_cash       # Cash at game end
player.final_net_worth  # Total assets at game end
player.is_winner        # Whether player won
player.is_bankrupt      # Whether player went bankrupt
player.placement        # Final ranking (1st, 2nd, ...)

# LLM-specific
player.llm_model_name      # Model identifier
player.llm_parameters      # JSONB model parameters
player.llm_strategy_profile  # JSONB strategy preferences
player.llm_learning_data   # JSONB accumulated learning
```

### GameEvent Model

Immutable event log for event sourcing:

```python
from server.database.models import GameEvent

# Fields
event.id              # UUID primary key
event.game_uuid       # Foreign key to Game
event.sequence_number # Monotonic counter (0, 1, 2, ...)
event.turn_number     # Which turn this occurred in
event.event_type      # Event classification
event.timestamp       # When event was recorded
event.payload         # JSONB event data
event.actor_player_id # Player who triggered event
```

Common event types:

| Type | Description |
|------|-------------|
| `game_started` | Game initialized |
| `turn_start` | New turn began |
| `dice_roll` | Player rolled dice |
| `player_moved` | Position changed |
| `property_purchased` | Property bought |
| `rent_paid` | Rent transferred |
| `auction_started` | Auction began |
| `auction_bid` | Bid placed |
| `auction_won` | Auction completed |
| `house_built` | House constructed |
| `player_bankruptcy` | Player eliminated |
| `game_over` | Game finished |

### LLMDecision Model

Records LLM agent decision context and reasoning:

```python
from server.database.models import LLMDecision

# Context
decision.game_state       # JSONB full game state snapshot
decision.player_state     # JSONB player's state
decision.available_actions  # JSONB legal actions

# LLM process
decision.prompt           # Prompt sent to LLM
decision.reasoning        # Step-by-step reasoning
decision.chosen_action    # JSONB selected action
decision.strategy_description  # Strategy explanation

# Metadata
decision.processing_time_ms  # Decision latency
decision.model_version       # LLM model identifier
```

### Indexes

Key indexes for query performance:

| Table | Index | Purpose |
|-------|-------|---------|
| `games` | `game_id` (unique) | Fast game lookup |
| `games` | `status` | Filter by status |
| `game_events` | `(game_uuid, sequence_number)` (unique) | Event ordering |
| `game_events` | `(game_uuid, turn_number)` | Turn filtering |
| `game_events` | `event_type, timestamp` | Event type queries |
| `game_events` | `payload` (GIN) | JSONB queries |
| `llm_decisions` | `reasoning` (GIN) | Full‑text search |

### Reference

::: server.database.models.Game

::: server.database.models.Player

::: server.database.models.GameEvent

::: server.database.models.LLMDecision

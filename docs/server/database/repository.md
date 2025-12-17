## GameRepository

Repository pattern encapsulating all database operations with async/await.

### Usage

```python
from server.database import session_scope, GameRepository

async with session_scope() as session:
    repo = GameRepository(session)

    # Create game
    game = await repo.create_game(
        game_id="abc123",
        config={"max_turns": 100, "seed": 42},
        metadata={"environment": "production"}
    )

    # Add players
    await repo.add_player(game.id, player_id=0, name="Alice", agent_type="greedy")
    await repo.add_player(game.id, player_id=1, name="Bob", agent_type="random")
```

### Game Operations

**Create and retrieve games:**

```python
# Create new game
game = await repo.create_game(game_id, config, metadata)

# Retrieve by string ID
game = await repo.get_game_by_id("abc123")

# Retrieve by UUID
game = await repo.get_game_by_uuid(uuid_value)

# List games with pagination and filtering
games = await repo.list_games(limit=100, offset=0, status="running")

# Update game status
await repo.update_game_status(
    game_id="abc123",
    status="finished",
    finished_at=datetime.utcnow(),
    winner_id=0,
    total_turns=85
)
```

### Player Operations

```python
# Add player to game
player = await repo.add_player(
    game_uuid=game.id,
    player_id=0,
    name="Alice",
    agent_type="greedy"
)

# Update final results
await repo.update_player_results(
    game_uuid=game.id,
    player_id=0,
    final_cash=2500,
    final_net_worth=5000,
    is_winner=True,
    is_bankrupt=False,
    placement=1
)
```

### Event Operations

```python
# Add single event
event = await repo.add_event(
    game_uuid=game.id,
    sequence_number=0,
    turn_number=0,
    event_type="game_started",
    payload={"players": ["Alice", "Bob"]},
    actor_player_id=None
)

# Batch insert events (more efficient)
events = await repo.add_events_batch(game.id, [
    {"sequence_number": 1, "turn_number": 0, "event_type": "dice_roll",
     "payload": {"dice": [4, 3]}, "actor_player_id": 0},
    {"sequence_number": 2, "turn_number": 0, "event_type": "player_moved",
     "payload": {"position": 7}, "actor_player_id": 0}
])

# Query events
events = await repo.get_game_events(
    game_uuid=game.id,
    from_sequence=0,      # Optional: start sequence
    to_sequence=100,      # Optional: end sequence
    turn_number=5         # Optional: filter by turn
)

# Get latest sequence number
latest = await repo.get_latest_sequence_number(game.id)

# Count events
count = await repo.get_event_count(game.id, event_type="dice_roll")

# Get game with all events
game, events = await repo.get_game_with_events("abc123", include_events=True)
```

### Statistics

```python
stats = await repo.get_game_statistics(game.id)
# {
#   "total_events": 500,
#   "latest_sequence": 499,
#   "events_by_type": {"dice_roll": 85, "property_purchased": 12, ...}
# }
```

### LLM Decision Operations

Each LLM player has their own decision sequence within a game. The unique constraint is on `(game_uuid, player_id, sequence_number)`.

```python
# Record LLM decision
decision = await repo.add_llm_decision(
    game_uuid=game.id,
    player_id=0,
    turn_number=5,
    sequence_number=42,  # Per-player sequence (1, 2, 3, ...)
    game_state={"turn": 5, "players": [...]},
    player_state={"cash": 1500, "properties": [...]},
    available_actions=[{"type": "ROLL_DICE"}, {"type": "END_TURN"}],
    prompt="You are playing Monopoly...",
    reasoning="I should roll the dice because...",
    chosen_action={"type": "ROLL_DICE"},
    strategy_description="balanced",  # aggressive, balanced, defensive
    processing_time_ms=1250,
    model_version="gemma3:4b"
)

# Get all decisions for a specific player in a game
decisions = await repo.get_llm_decisions_for_game(game.id, player_id=0)

# Get all LLM decisions for entire game (all players)
all_decisions = await repo.get_llm_decisions_for_game(game.id)

# Get specific decision by player and sequence
decision = await repo.get_llm_decision_by_sequence(
    game.id,
    player_id=0,
    sequence_number=42
)

# Full-text search in reasoning
results = await repo.search_llm_reasoning("buy property", limit=100)

# Update player strategy profile
await repo.update_llm_player_strategy(
    game_uuid=game.id,
    player_id=0,
    strategy_profile={"style": "aggressive", "risk_tolerance": 0.8}
)
```

### Reference

::: server.database.repository.GameRepository

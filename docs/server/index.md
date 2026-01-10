## Server Architecture

The FastAPI server provides REST and WebSocket APIs for managing Monopoly games, enabling real‑time gameplay with AI agents and human players.

- **GameRegistry**: in‑memory management of active game sessions
- **GameRunner**: async game loop driving agents, broadcasting events, handling human input
- **Database layer**: PostgreSQL with event sourcing for full game history
- **WebSocket streaming**: real‑time event delivery to connected clients

### Component Overview

```mermaid
flowchart TB
  subgraph Clients
    UI[Web UI]
    API[REST Client]
    WS[WebSocket Client]
  end

  subgraph Server
    APP[FastAPI App]
    REG[GameRegistry]
    RUN[GameRunner]
    LOG[GameLogger]
  end

  subgraph Database
    PG[(PostgreSQL)]
    REPO[GameRepository]
  end

  subgraph Engine
    GAME[GameState]
    RULES[Rules API]
    AGENTS[Agents]
  end

  UI --> APP
  API --> APP
  WS --> APP

  APP --> REG
  REG --> RUN
  RUN --> GAME
  RUN --> AGENTS
  AGENTS --> RULES
  RULES --> GAME

  RUN --> LOG
  LOG --> REPO
  REPO --> PG

  RUN -.-> WS
```

### Request Flow

1. Client creates game via `POST /games`
2. GameRegistry creates GameState and GameRunner
3. GameRunner starts background task driving the game loop
4. Agents act automatically; humans inject actions via REST
5. Events broadcast to WebSocket subscribers
6. Events persisted to database via GameRepository

### Lifecycle (Sequence)

```mermaid
sequenceDiagram
  participant Client
  participant App as FastAPI
  participant Registry as GameRegistry
  participant Runner as GameRunner
  participant DB as Database

  Client->>App: POST /games
  App->>Registry: create_game()
  Registry->>DB: save game metadata
  Registry->>Runner: new GameRunner
  Runner->>Runner: start() background task
  Registry-->>App: game_id
  App-->>Client: {"game_id": "..."}

  Client->>App: WS /ws/games/{game_id}
  App->>Runner: subscribe()
  Runner-->>Client: snapshot

  loop Game Loop
    Runner->>Runner: agent.choose_action()
    Runner->>Runner: apply_action()
    Runner->>Client: broadcast events
    Runner->>DB: persist events
  end

  Runner->>DB: update final status
```

### Key Design Patterns

- **Event Sourcing**: all game state changes logged as immutable events
- **Async Game Loop**: non‑blocking I/O with asyncio for concurrent games
- **Legal Actions Pattern**: clients query valid moves before acting
- **Queue‑Based Broadcasting**: each WebSocket gets dedicated queue

### Module Reference

| Module | Purpose |
|--------|---------|
| `server/app.py` | FastAPI routes and WebSocket endpoints |
| `server/registry.py` | In‑memory game session management |
| `server/runner.py` | Game loop orchestration and event broadcasting |
| `src/data/` | PostgreSQL models, repository, sessions |

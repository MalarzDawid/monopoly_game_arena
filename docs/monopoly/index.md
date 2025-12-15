## Monopoly Architecture

This engine separates core responsibilities into small, testable modules:

- Game engine: turn management, movement, purchases, rent, auctions, building, mortgages, bankruptcy
- Rules API: legal action discovery + action execution for agents/controllers
- Board model: spaces and color groups; helpers for railroads/utilities lookup
- Cards & Decks: Chance and Community Chest with deterministic RNG
- Economy & Events: Bank and a structured EventLog
- Trades & Auctions: explicit models and flows for player interactions

Data flow:

1) Controller/agent asks for legal actions via `rules.get_legal_actions(game, player_id)`
2) Controller applies an action with `rules.apply_action(game, action)`
3) Engine mutates `GameState`, logs events in `EventLog`, and resolves space effects

Key modules and classes are linked in the side pages, each with examples.

### High‑level Flow (Diagram)

```mermaid
flowchart TB
  subgraph Controller
    A[Agent / Controller]
  end

  R[Rules API\nget_legal_actions / apply_action]
  G[GameState\nstate, movement, purchases, rent,
    building, mortgages, bankruptcy]
  B[Board & Spaces\nresolution of landing effects]
  E[EventLog]
  L[GameLogger\nJSONL / DB]
  S[Server Runner\nWebSocket broadcast]
  V[Viewer / Analyzer]

  A -- query --> R
  R -- legal actions --> A
  A -- chosen action --> R
  R --> G
  G --> B
  B --> G
  G --> E
  E --> L
  L --> S
  S --> V
  G -. next turn .-> R
```

### Turn Interaction (Sequence)

```mermaid
sequenceDiagram
  participant Agent
  participant Rules
  participant Game as GameState
  participant Board
  participant Log as EventLog

  Agent->>Rules: get_legal_actions(game, player_id)
  Rules-->>Agent: [Action, ...]
  Agent->>Rules: apply_action(game, Action)
  Rules->>Game: mutate state
  Game->>Board: resolve landing/rent/cards/tax/jail
  Board-->>Game: effects
  Game->>Log: record events
  opt auction/trade
    Agent->>Rules: bid / propose/accept trade
    Rules->>Game: update
    Game->>Log: events
  end
  Rules-->>Agent: next legal actions
```

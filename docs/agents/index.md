## Agents Architecture

Agents are AI players that automatically make decisions during Monopoly games. All agents inherit from the abstract `Agent` base class and implement the `choose_action()` method.

### Available Agents

| Agent | Description | Use Case |
|-------|-------------|----------|
| `RandomAgent` | Makes random legal moves | Testing, baseline comparison |
| `GreedyAgent` | Prefers buying and building | Simple competitive play |
| `LLMAgent` | LLM-powered strategic decisions | Advanced AI research, competitions |

### Agent Hierarchy

```mermaid
classDiagram
    class Agent {
        <<abstract>>
        +player_id: int
        +name: str
        +choose_action(game, legal_actions)* Action
    }

    class RandomAgent {
        +rng: Random
        +choose_action(game, legal_actions) Action
    }

    class GreedyAgent {
        +rng: Random
        +choose_action(game, legal_actions) Action
    }

    class LLMAgent {
        +model_name: str
        +strategy: str
        +base_url: str
        +choose_action(game, legal_actions) Action
        -_query_llm(prompt) str
        -_build_prompt(game, actions) str
        -_parse_response(response) Action
    }

    Agent <|-- RandomAgent
    Agent <|-- GreedyAgent
    Agent <|-- LLMAgent
```

### Decision Flow

```mermaid
sequenceDiagram
    participant Runner as GameRunner
    participant Agent
    participant Rules as Rules API
    participant Game as GameState

    Runner->>Rules: get_legal_actions(game, player_id)
    Rules-->>Runner: [Action, ...]
    Runner->>Agent: choose_action(game, legal_actions)
    Agent->>Agent: evaluate options
    Agent-->>Runner: chosen Action
    Runner->>Rules: apply_action(game, action)
    Rules->>Game: mutate state
```

### Usage

```python
from src.core.agents import RandomAgent, GreedyAgent, LLMAgent
from src.core.game.rules import get_legal_actions, apply_action

# Create agents for each player
agents = [
    GreedyAgent(0, "Alice"),
    RandomAgent(1, "Bob"),
    LLMAgent(2, "Charlie", strategy="aggressive"),
]

# Game loop
while not game.game_over:
    current = game.get_current_player()
    legal_actions = get_legal_actions(game, current.player_id)

    if legal_actions:
        agent = agents[current.player_id]
        action = agent.choose_action(game, legal_actions)
        apply_action(game, action)
```

### Creating Custom Agents

Extend the `Agent` base class and implement `choose_action()`:

```python
from agents import Agent
from monopoly.rules import Action

class MyCustomAgent(Agent):
    def __init__(self, player_id: int, name: str):
        super().__init__(player_id, name)
        # Custom initialization

    def choose_action(self, game, legal_actions: list[Action]) -> Action:
        # Your decision logic here
        return legal_actions[0]
```

### Agent Comparison

| Feature | RandomAgent | GreedyAgent | LLMAgent |
|---------|-------------|-------------|----------|
| Deterministic | No | Yes (seeded) | No |
| Property buying | Random | Always buy | Context-aware |
| Building | Random | Prioritized | Strategic |
| Auctions | Random bids | Conservative | Adaptive (by strategy) |
| Trading | Rejects all | Rejects all | Future |
| Complexity | O(1) | O(n) | O(API call) |
| Requires API | No | No | Yes (LLM backend) |

### LLM Agent Configuration

LLMAgent requires an LLM backend (Ollama, vLLM, or OpenAI-compatible API):

```bash
# Environment variables
LLM_BASE_URL=http://localhost:11434/v1  # Ollama
LLM_MODEL=gemma3:4b
```

Three strategy profiles available:
- `aggressive` - Buy everything, bid high
- `balanced` - Sustainable growth (default)
- `defensive` - Conservative, high cash reserves

See [LLMAgent documentation](llm.md) for details.

### Integration with Server

The `GameRunner` uses agents based on player roles:

```python
# In server/runner.py
for i, role in enumerate(roles):
    if role == "human":
        self.agents[i] = None  # Wait for REST API
    elif role == "random":
        self.agents[i] = RandomAgent(i, names[i])
    elif role == "greedy":
        self.agents[i] = GreedyAgent(i, names[i])
    elif role == "llm":
        self.agents[i] = LLMAgent(i, names[i], strategy=llm_strategy)
```

### Running Games with Different Agents

#### CLI

```bash
# Greedy agents (default)
uv run python play_monopoly.py --players 4 --agent greedy

# Random agents
uv run python play_monopoly.py --players 4 --agent random

# LLM agents
uv run python play_monopoly.py --players 4 --agent llm --llm-strategy balanced
```

#### Server API

```bash
# Create game with mixed agents
curl -X POST http://localhost:8000/games \
  -H "Content-Type: application/json" \
  -d '{"players": 4, "roles": ["llm", "greedy", "greedy", "random"]}'
```

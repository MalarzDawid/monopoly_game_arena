## Agent Base Class

Abstract base class that all Monopoly agents must inherit from.

### Interface

```python
from abc import ABC, abstractmethod
from typing import List
from monopoly.game import GameState
from monopoly.rules import Action

class Agent(ABC):
    player_id: int
    name: str

    def __init__(self, player_id: int, name: str): ...

    @abstractmethod
    def choose_action(self, game: GameState, legal_actions: List[Action]) -> Action:
        """Choose an action from the list of legal actions."""
        pass
```

### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `player_id` | `int` | Player's index in the game (0, 1, 2, ...) |
| `name` | `str` | Player's display name |

### Method: choose_action

The core method that every agent must implement.

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `game` | `GameState` | Current game state with all player info, board, auctions |
| `legal_actions` | `List[Action]` | Actions the player can legally perform now |

**Returns:** `Action` - The chosen action to execute.

### Implementation Guidelines

When implementing a custom agent:

1. **Always return a valid action** from `legal_actions`
2. **Handle auction bidding** - set `action.params["amount"]` for `BID` actions
3. **Consider game phase** - check `game.active_auction` for auction state
4. **Access player state** via `game.players[self.player_id]`

### Example Implementation

```python
from src.core.agents import Agent
from src.core.game.game import ActionType
from src.core.game.rules import Action

class ConservativeAgent(Agent):
    """Agent that only buys cheap properties."""

    def __init__(self, player_id: int, name: str, max_spend_ratio: float = 0.3):
        super().__init__(player_id, name)
        self.max_spend_ratio = max_spend_ratio

    def choose_action(self, game, legal_actions: list[Action]) -> Action:
        player = game.players[self.player_id]

        for action in legal_actions:
            # Only buy if property costs less than max_spend_ratio of cash
            if action.action_type == ActionType.BUY_PROPERTY:
                position = action.params.get("position", player.position)
                space = game.board.get_property_space(position)
                if space and space.price < player.cash * self.max_spend_ratio:
                    return action

            # Decline expensive properties
            if action.action_type == ActionType.DECLINE_PURCHASE:
                return action

            # Always roll dice if available
            if action.action_type == ActionType.ROLL_DICE:
                return action

            # End turn to keep game moving
            if action.action_type == ActionType.END_TURN:
                return action

        return legal_actions[0]
```

### Reference

::: agents.base.Agent

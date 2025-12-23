## Game

`GameState` holds the full game state and provides core mechanics like movement, purchases, building, mortgages, cards, rent, and bankruptcy.

Example turn loop with Rules API:

```python
from core import GameConfig, create_game, Player
from core.game.rules import get_legal_actions, apply_action

game = create_game(GameConfig(seed=7), [Player(0, "A"), Player(1, "B")])
pid = game.get_current_player().player_id
legal = get_legal_actions(game, pid)
action = next(a for a in legal if a.action_type.value == "roll_dice")
apply_action(game, action)
```

### Reference

::: core.game.GameState

::: core.game.game.ActionType

::: core.game.game.create_game

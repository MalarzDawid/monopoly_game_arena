## Rules API

High‑level API to query legal actions for a player and apply them safely.

Example loop:

```python
from core.game.rules import get_legal_actions, apply_action

pid = game.get_current_player().player_id
legal = get_legal_actions(game, pid)
if legal:
    action = legal[0]
    apply_action(game, action)
```

### Reference

::: core.game.rules.Action

::: core.game.rules.get_legal_actions

::: core.game.rules.apply_action

::: core.game.rules.step_turn

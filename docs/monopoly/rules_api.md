## Rules API

High‑level API to query legal actions for a player and apply them safely.

Example loop:

```python
from monopoly.rules import get_legal_actions, apply_action

pid = game.get_current_player().player_id
legal = get_legal_actions(game, pid)
if legal:
    action = legal[0]
    apply_action(game, action)
```

### Reference

::: monopoly.rules.Action

::: monopoly.rules.get_legal_actions

::: monopoly.rules.apply_action

::: monopoly.rules.step_turn

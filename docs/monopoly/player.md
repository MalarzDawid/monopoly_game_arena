## Player

Players are defined once and passed to `create_game`. Runtime state lives in `PlayerState` inside `GameState`.

Example:

```python
from monopoly import Player, create_game, GameConfig

players = [Player(0, "Alice"), Player(1, "Bob")]
game = create_game(GameConfig(seed=1), players)

alice = game.players[0]  # PlayerState
print(alice.cash, alice.position, alice.in_jail)
```

### Reference

::: monopoly.player.Player

::: monopoly.player.PlayerState

::: monopoly.player.PropertyOwnership

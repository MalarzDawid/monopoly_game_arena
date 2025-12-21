## Config

Game configuration tweaks core rules and limits.

Example:

```python
from core import GameConfig

cfg = GameConfig(
    starting_cash=1500,
    go_salary=200,
    jail_fine=50,
    mortgage_interest_rate=0.10,
    house_limit=32,
    hotel_limit=12,
    max_jail_turns=3,
    time_limit_turns=300,
    seed=42,
)
```

### Reference

::: core.game.config.GameConfig

## Trading

Trades allow exchanging properties, cash, and jail cards. The engine validates ownership, buildings, and funds before execution.

Example proposal shape:

```python
from core.game.trading import TradeItem, TradeItemType

offers = [TradeItem(TradeItemType.CASH, 100)]
wants  = [TradeItem(TradeItemType.PROPERTY, 1)]
# Use rules.PROPOSE_TRADE action with these lists as params
```

### Reference

::: core.game.trading.TradeItemType

::: core.game.trading.TradeItem

::: core.game.trading.TradeOffer

::: core.game.trading.TradeManager

## Trading

Trades allow exchanging properties, cash, and jail cards. The engine validates ownership, buildings, and funds before execution.

Example proposal shape:

```python
from monopoly.trading import TradeItem, TradeItemType

offers = [TradeItem(TradeItemType.CASH, 100)]
wants  = [TradeItem(TradeItemType.PROPERTY, 1)]
# Use rules.PROPOSE_TRADE action with these lists as params
```

### Reference

::: monopoly.trading.TradeItemType

::: monopoly.trading.TradeItem

::: monopoly.trading.TradeOffer

::: monopoly.trading.TradeManager

## Cards & Decks

Chance and Community Chest are modeled with `Card`, `CardType`, and `Deck`. Cards can move, collect/pay, or interact with buildings and players.

Example:

```python
from core.game.cards import Card, CardType, create_chance_deck
import random

rng = random.Random(42)
deck = create_chance_deck(rng)
card = deck.draw()
print(card.description, card.card_type)
```

### Reference

::: core.game.cards.Card

::: core.game.cards.CardType

::: core.game.cards.Deck

::: core.game.cards.create_chance_deck

::: core.game.cards.create_community_chest_deck

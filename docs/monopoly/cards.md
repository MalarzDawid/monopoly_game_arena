## Cards & Decks

Chance and Community Chest are modeled with `Card`, `CardType`, and `Deck`. Cards can move, collect/pay, or interact with buildings and players.

Example:

```python
from monopoly.cards import Card, CardType, create_chance_deck
import random

rng = random.Random(42)
deck = create_chance_deck(rng)
card = deck.draw()
print(card.description, card.card_type)
```

### Reference

::: monopoly.cards.Card

::: monopoly.cards.CardType

::: monopoly.cards.Deck

::: monopoly.cards.create_chance_deck

::: monopoly.cards.create_community_chest_deck

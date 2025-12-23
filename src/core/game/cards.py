"""
Chance and Community Chest card system.
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional
import random


class CardType(Enum):
    """Types of card effects."""

    MOVE_TO = "move_to"
    MOVE_SPACES = "move_spaces"
    MOVE_TO_NEAREST = "move_to_nearest"
    COLLECT = "collect"
    PAY = "pay"
    PAY_PER_HOUSE = "pay_per_house"
    PAY_PER_BUILDING = "pay_per_building"  # Different costs for houses vs hotels
    COLLECT_FROM_PLAYERS = "collect_from_players"
    PAY_TO_PLAYERS = "pay_to_players"
    GO_TO_JAIL = "go_to_jail"
    GET_OUT_OF_JAIL = "get_out_of_jail"


@dataclass
class Card:
    """Represents a Chance or Community Chest card."""

    description: str = ""
    card_type: Optional[CardType] = None
    value: int = 0
    value2: int = 0  # For PAY_PER_BUILDING: hotel cost
    target_position: Optional[int] = None
    target_type: Optional[str] = None  # "railroad" or "utility" for MOVE_TO_NEAREST
    collect_go: bool = True  # Whether to collect GO when passing it
    # Aliases for backwards compatibility with tests
    text: Optional[str] = None
    action_type: Optional[CardType] = None

    def __post_init__(self):
        # Handle text -> description alias
        if self.text is not None and not self.description:
            self.description = self.text
        # Handle action_type -> card_type alias
        if self.action_type is not None and self.card_type is None:
            self.card_type = self.action_type

    def __repr__(self) -> str:
        return f"Card('{self.description}')"


class Deck:
    """A deck of cards that can be shuffled and drawn from."""

    def __init__(self, cards: List[Card], rng: random.Random):
        self.cards = cards.copy()
        self.rng = rng
        self.discard_pile: List[Card] = []
        self.held_cards: List[Card] = []  # Get Out of Jail Free cards held by players
        self.shuffle()

    def shuffle(self) -> None:
        """Shuffle the deck."""
        self.rng.shuffle(self.cards)

    def draw(self) -> Card:
        """
        Draw a card from the deck.
        If deck is empty, shuffle the discard pile back in.
        """
        if not self.cards:
            if self.discard_pile:
                self.cards = self.discard_pile.copy()
                self.discard_pile.clear()
                self.shuffle()
            else:
                # Both empty - this shouldn't happen in normal play
                # but return a dummy card for safety
                return Card("No cards available", CardType.COLLECT, value=0)

        card = self.cards.pop(0)
        return card

    def discard(self, card: Card) -> None:
        """Return a card to the bottom of the deck (discard pile)."""
        self.discard_pile.append(card)

    def hold_card(self, card: Card) -> None:
        """Mark a card as being held by a player (Get Out of Jail Free)."""
        self.held_cards.append(card)

    def return_held_card(self, card: Card) -> None:
        """Return a held card to the discard pile."""
        if card in self.held_cards:
            self.held_cards.remove(card)
        self.discard(card)


def create_chance_deck(rng: random.Random) -> Deck:
    """Create a standard Chance deck."""
    cards = [
        Card("Advance to Go (Collect $200)", CardType.MOVE_TO, target_position=0),
        Card("Advance to Illinois Ave.", CardType.MOVE_TO, target_position=24),
        Card("Advance to St. Charles Place", CardType.MOVE_TO, target_position=11),
        Card(
            "Advance token to nearest Utility. If unowned, you may buy it. "
            "If owned, pay owner 10 times dice roll.",
            CardType.MOVE_TO_NEAREST,
            target_type="utility",
        ),
        Card(
            "Advance token to nearest Railroad. If unowned, you may buy it. "
            "If owned, pay owner twice the rental.",
            CardType.MOVE_TO_NEAREST,
            target_type="railroad",
        ),
        Card(
            "Advance token to nearest Railroad. If unowned, you may buy it. "
            "If owned, pay owner twice the rental.",
            CardType.MOVE_TO_NEAREST,
            target_type="railroad",
        ),
        Card("Bank pays you dividend of $50", CardType.COLLECT, value=50),
        Card("Get Out of Jail Free", CardType.GET_OUT_OF_JAIL),
        Card("Go Back 3 Spaces", CardType.MOVE_SPACES, value=-3, collect_go=False),
        Card("Go to Jail", CardType.GO_TO_JAIL),
        Card(
            "Make general repairs on all your property: "
            "Pay $25 per house, $100 per hotel",
            CardType.PAY_PER_HOUSE,
            value=25,  # value = house cost, value*4 = hotel cost
        ),
        Card("Pay poor tax of $15", CardType.PAY, value=15),
        Card("Take a trip to Reading Railroad", CardType.MOVE_TO, target_position=5),
        Card("Take a walk on the Boardwalk", CardType.MOVE_TO, target_position=39),
        Card(
            "You have been elected Chairman of the Board. Pay each player $50",
            CardType.PAY_TO_PLAYERS,
            value=50,
        ),
        Card("Your building loan matures. Collect $150", CardType.COLLECT, value=150),
    ]
    return Deck(cards, rng)


def create_community_chest_deck(rng: random.Random) -> Deck:
    """Create a standard Community Chest deck."""
    cards = [
        Card("Advance to Go (Collect $200)", CardType.MOVE_TO, target_position=0),
        Card("Bank error in your favor. Collect $200", CardType.COLLECT, value=200),
        Card("Doctor's fees. Pay $50", CardType.PAY, value=50),
        Card("From sale of stock you get $50", CardType.COLLECT, value=50),
        Card("Get Out of Jail Free", CardType.GET_OUT_OF_JAIL),
        Card("Go to Jail", CardType.GO_TO_JAIL),
        Card("Grand Opera Night. Collect $50 from every player", CardType.COLLECT_FROM_PLAYERS, value=50),
        Card("Holiday Fund matures. Receive $100", CardType.COLLECT, value=100),
        Card("Income tax refund. Collect $20", CardType.COLLECT, value=20),
        Card("It is your birthday. Collect $10 from every player", CardType.COLLECT_FROM_PLAYERS, value=10),
        Card("Life insurance matures. Collect $100", CardType.COLLECT, value=100),
        Card("Hospital fees. Pay $100", CardType.PAY, value=100),
        Card("School fees. Pay $150", CardType.PAY, value=150),
        Card("Receive $25 consultancy fee", CardType.COLLECT, value=25),
        Card(
            "You are assessed for street repairs: Pay $40 per house, $115 per hotel",
            CardType.PAY_PER_HOUSE,
            value=40,
        ),
        Card("You have won second prize in a beauty contest. Collect $10", CardType.COLLECT, value=10),
        Card("You inherit $100", CardType.COLLECT, value=100),
    ]
    return Deck(cards, rng)

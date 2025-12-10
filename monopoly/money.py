"""
Money management and event logging.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class EventType(Enum):
    """Types of game events."""

    GAME_START = "game_start"
    TURN_START = "turn_start"
    DICE_ROLL = "dice_roll"
    MOVE = "move"
    PASS_GO = "pass_go"
    LAND = "land"

    PURCHASE = "purchase"
    AUCTION_START = "auction_start"
    AUCTION_BID = "auction_bid"
    AUCTION_END = "auction_end"

    RENT_PAYMENT = "rent_payment"
    TAX_PAYMENT = "tax_payment"

    CARD_DRAW = "card_draw"
    CARD_EFFECT = "card_effect"

    BUILD_HOUSE = "build_house"
    BUILD_HOTEL = "build_hotel"
    SELL_BUILDING = "sell_building"

    MORTGAGE = "mortgage"
    UNMORTGAGE = "unmortgage"

    GO_TO_JAIL = "go_to_jail"
    JAIL_ATTEMPT = "jail_attempt"
    JAIL_RELEASE = "jail_release"

    TRANSFER = "transfer"
    BANKRUPTCY = "bankruptcy"
    GAME_END = "game_end"

    TRADE_PROPOSED = "trade_proposed"
    TRADE_ACCEPTED = "trade_accepted"
    TRADE_REJECTED = "trade_rejected"
    TRADE_CANCELLED = "trade_cancelled"
    TRADE_EXECUTED = "trade_executed"

@dataclass
class GameEvent:
    """A logged event in the game."""

    event_type: EventType
    player_id: Optional[int] = None
    details: Dict[str, Any] = field(default_factory=dict)

    def __repr__(self) -> str:
        player_str = f"P{self.player_id}" if self.player_id is not None else "System"
        return f"[{player_str}] {self.event_type.value}: {self.details}"


class EventLog:
    """Manages the game event log."""

    def __init__(self):
        self.events: List[GameEvent] = []

    def log(self, event_type: EventType, player_id: Optional[int] = None, **details: Any) -> None:
        """Log a game event."""
        event = GameEvent(event_type, player_id, details)
        self.events.append(event)

    def get_events(self) -> List[GameEvent]:
        """Get all logged events."""
        return self.events.copy()

    def get_recent_events(self, count: int = 10) -> List[GameEvent]:
        """Get the most recent N events."""
        return self.events[-count:]

    def clear(self) -> None:
        """Clear the event log."""
        self.events.clear()


class Bank:
    """
    Manages money transfers and building supply.
    The bank has unlimited money but limited houses and hotels.
    """

    def __init__(self, house_limit: int = 32, hotel_limit: int = 12):
        self.houses_available = house_limit
        self.hotels_available = hotel_limit

    def can_buy_houses(self, count: int) -> bool:
        """Check if enough houses are available."""
        return self.houses_available >= count

    def can_buy_hotel(self) -> bool:
        """Check if a hotel is available."""
        return self.hotels_available > 0

    def buy_houses(self, count: int) -> bool:
        """
        Purchase houses from the bank.
        Returns True if successful, False if not enough houses.
        """
        if self.can_buy_houses(count):
            self.houses_available -= count
            return True
        return False

    def buy_hotel(self, return_houses: int = 4) -> bool:
        """
        Purchase a hotel from the bank, returning houses.
        Returns True if successful, False if no hotels available.
        """
        if self.can_buy_hotel():
            self.hotels_available -= 1
            self.houses_available += return_houses
            return True
        return False

    def sell_houses(self, count: int) -> None:
        """Sell houses back to the bank."""
        self.houses_available += count

    def can_sell_houses(self, count: int) -> bool:
        """Check if bank can provide houses when downgrading hotel."""
        return self.houses_available >= count

    def sell_hotel(self) -> None:
        """Sell a hotel back to the bank."""
        self.hotels_available += 1

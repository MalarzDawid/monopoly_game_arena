"""
Trading system for Monopoly.
Allows players to propose and execute trades of properties, cash, and Get Out of Jail Free cards.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Set
from enum import Enum


class TradeItemType(Enum):
    """Types of items that can be traded."""
    PROPERTY = "property"
    CASH = "cash"
    JAIL_CARD = "jail_card"


@dataclass
class TradeItem:
    """Represents a single item in a trade."""
    item_type: TradeItemType
    # For PROPERTY: position on board
    # For CASH: amount
    # For JAIL_CARD: count (usually 1)
    value: int

    def __repr__(self) -> str:
        if self.item_type == TradeItemType.PROPERTY:
            return f"Property({self.value})"
        elif self.item_type == TradeItemType.CASH:
            return f"${self.value}"
        else:
            return f"JailCard({self.value})"


@dataclass
class TradeOffer:
    """
    Represents a trade offer between two players.

    In Monopoly trading:
    - Any player can propose a trade to any other player
    - Trade can include properties, cash, and Get Out of Jail Free cards
    - Properties with buildings cannot be traded (must sell buildings first)
    - Mortgaged properties can be traded (buyer pays 10% fee)
    - Both parties must agree for trade to execute
    """

    # Unique ID for this trade offer
    trade_id: int

    # Player proposing the trade
    proposer_id: int

    # Player receiving the trade offer
    recipient_id: int

    # Items proposer is offering
    proposer_offers: List[TradeItem] = field(default_factory=list)

    # Items proposer wants in return
    proposer_wants: List[TradeItem] = field(default_factory=list)

    # Status of the trade
    status: str = "pending"  # pending, accepted, rejected, cancelled

    # Turn number when trade was proposed
    proposed_turn: int = 0

    def get_proposer_properties(self) -> Set[int]:
        """Get set of property positions proposer is offering."""
        return {item.value for item in self.proposer_offers
                if item.item_type == TradeItemType.PROPERTY}

    def get_proposer_cash(self) -> int:
        """Get total cash proposer is offering."""
        return sum(item.value for item in self.proposer_offers
                   if item.item_type == TradeItemType.CASH)

    def get_proposer_jail_cards(self) -> int:
        """Get number of jail cards proposer is offering."""
        return sum(item.value for item in self.proposer_offers
                   if item.item_type == TradeItemType.JAIL_CARD)

    def get_recipient_properties(self) -> Set[int]:
        """Get set of property positions proposer wants from recipient."""
        return {item.value for item in self.proposer_wants
                if item.item_type == TradeItemType.PROPERTY}

    def get_recipient_cash(self) -> int:
        """Get total cash proposer wants from recipient."""
        return sum(item.value for item in self.proposer_wants
                   if item.item_type == TradeItemType.CASH)

    def get_recipient_jail_cards(self) -> int:
        """Get number of jail cards proposer wants from recipient."""
        return sum(item.value for item in self.proposer_wants
                   if item.item_type == TradeItemType.JAIL_CARD)

    def __repr__(self) -> str:
        return (f"Trade #{self.trade_id}: Player {self.proposer_id} → Player {self.recipient_id}\n"
                f"  Offering: {self.proposer_offers}\n"
                f"  Wants: {self.proposer_wants}\n"
                f"  Status: {self.status}")


class TradeManager:
    """
    Manages all active and historical trade offers.
    """

    def __init__(self):
        self.next_trade_id = 1
        self.active_trades: List[TradeOffer] = []
        self.trade_history: List[TradeOffer] = []

    def create_trade(
        self,
        proposer_id: int,
        recipient_id: int,
        proposer_offers: List[TradeItem],
        proposer_wants: List[TradeItem],
        current_turn: int
    ) -> TradeOffer:
        """Create a new trade offer."""
        trade = TradeOffer(
            trade_id=self.next_trade_id,
            proposer_id=proposer_id,
            recipient_id=recipient_id,
            proposer_offers=proposer_offers,
            proposer_wants=proposer_wants,
            proposed_turn=current_turn
        )
        self.next_trade_id += 1
        self.active_trades.append(trade)
        return trade

    def get_trade(self, trade_id: int) -> Optional[TradeOffer]:
        """Get a trade offer by ID."""
        for trade in self.active_trades:
            if trade.trade_id == trade_id:
                return trade
        for trade in self.trade_history:
            if trade.trade_id == trade_id:
                return trade
        return None

    def get_active_trades_for_player(self, player_id: int) -> List[TradeOffer]:
        """Get all active trades where player is proposer or recipient."""
        return [trade for trade in self.active_trades
                if trade.proposer_id == player_id or trade.recipient_id == player_id]

    def accept_trade(self, trade_id: int) -> Optional[TradeOffer]:
        """Mark a trade as accepted and move to history."""
        trade = self.get_trade(trade_id)
        if trade and trade.status == "pending":
            trade.status = "accepted"
            self.active_trades.remove(trade)
            self.trade_history.append(trade)
            return trade
        return None

    def reject_trade(self, trade_id: int) -> Optional[TradeOffer]:
        """Mark a trade as rejected and move to history."""
        trade = self.get_trade(trade_id)
        if trade and trade.status == "pending":
            trade.status = "rejected"
            self.active_trades.remove(trade)
            self.trade_history.append(trade)
            return trade
        return None

    def cancel_trade(self, trade_id: int) -> Optional[TradeOffer]:
        """Cancel a trade (proposer can cancel their own pending trades)."""
        trade = self.get_trade(trade_id)
        if trade and trade.status == "pending":
            trade.status = "cancelled"
            self.active_trades.remove(trade)
            self.trade_history.append(trade)
            return trade
        return None

from dataclasses import dataclass, field
from typing import Set, Optional
from monopoly.money import EventLog, EventType


@dataclass
class TradeOffer:
    """
    Represents items offered in a trade.
    """
    cash: int = 0
    properties: Set[int] = field(default_factory=set)  # Set of property positions
    jail_cards: int = 0  # Number of Get Out of Jail Free cards

    def is_empty(self) -> bool:
        """Check if offer contains anything."""
        return self.cash == 0 and len(self.properties) == 0 and self.jail_cards == 0

    def __repr__(self) -> str:
        items = []
        if self.cash > 0:
            items.append(f"${self.cash}")
        if self.properties:
            items.append(f"{len(self.properties)} properties")
        if self.jail_cards > 0:
            items.append(f"{self.jail_cards} GOOJF cards")
        return " + ".join(items) if items else "nothing"


class Trade:
    """
    Manages a trade between two players.

    Trade flow:
    1. Proposer creates trade with their offer and request
    2. Recipient can accept or reject
    3. If accepted, items are transferred atomically
    """

    def __init__(
            self,
            trade_id: int,
            proposer_id: int,
            recipient_id: int,
            proposer_offer: TradeOffer,
            recipient_offer: TradeOffer,
            event_log: EventLog,
    ):
        self.trade_id = trade_id
        self.proposer_id = proposer_id
        self.recipient_id = recipient_id
        self.proposer_offer = proposer_offer
        self.recipient_offer = recipient_offer
        self.event_log = event_log

        self.is_accepted = False
        self.is_rejected = False
        self.is_cancelled = False

        self.event_log.log(
            EventType.TRADE_PROPOSED,
            player_id=proposer_id,
            details={
                "trade_id": trade_id,
                "proposer": proposer_id,
                "recipient": recipient_id,
                "proposer_offers": str(proposer_offer),
                "proposer_requests": str(recipient_offer),
            },
        )

    def accept(self) -> None:
        """Recipient accepts the trade."""
        self.is_accepted = True
        self.event_log.log(
            EventType.TRADE_ACCEPTED,
            player_id=self.recipient_id,
            details={
                "trade_id": self.trade_id,
                "proposer": self.proposer_id,
                "recipient": self.recipient_id,
            },
        )

    def reject(self) -> None:
        """Recipient rejects the trade."""
        self.is_rejected = True
        self.event_log.log(
            EventType.TRADE_REJECTED,
            player_id=self.recipient_id,
            details={
                "trade_id": self.trade_id,
                "proposer": self.proposer_id,
                "recipient": self.recipient_id,
            },
        )

    def cancel(self) -> None:
        """Proposer cancels the trade."""
        self.is_cancelled = True
        self.event_log.log(
            EventType.TRADE_CANCELLED,
            player_id=self.proposer_id,
            details={
                "trade_id": self.trade_id,
                "proposer": self.proposer_id,
                "recipient": self.recipient_id,
            },
        )

    def is_complete(self) -> bool:
        """Check if trade is finished (accepted, rejected, or cancelled)."""
        return self.is_accepted or self.is_rejected or self.is_cancelled

    def get_result(self) -> Optional[str]:
        """Get trade result: 'accepted', 'rejected', 'cancelled', or None."""
        if self.is_accepted:
            return "accepted"
        elif self.is_rejected:
            return "rejected"
        elif self.is_cancelled:
            return "cancelled"
        return None


class TradeManager:
    """
    Manages active trades and trade history.
    Only one active trade per player pair at a time.
    """

    def __init__(self, event_log: EventLog):
        self.event_log = event_log
        self.active_trades: dict[int, Trade] = {}  # trade_id -> Trade
        self.next_trade_id = 1
        self.trade_history: list[Trade] = []

    def create_trade(
            self,
            proposer_id: int,
            recipient_id: int,
            proposer_offer: TradeOffer,
            recipient_offer: TradeOffer,
    ) -> Trade:
        """Create a new trade proposal."""
        trade = Trade(
            self.next_trade_id,
            proposer_id,
            recipient_id,
            proposer_offer,
            recipient_offer,
            self.event_log,
        )
        self.active_trades[self.next_trade_id] = trade
        self.next_trade_id += 1
        return trade

    def get_active_trade_for_player(self, player_id: int) -> Optional[Trade]:
        """Get active trade where player is proposer or recipient."""
        for trade in self.active_trades.values():
            if trade.proposer_id == player_id or trade.recipient_id == player_id:
                if not trade.is_complete():
                    return trade
        return None

    def complete_trade(self, trade_id: int) -> None:
        """Mark trade as complete and move to history."""
        if trade_id in self.active_trades:
            trade = self.active_trades[trade_id]
            self.trade_history.append(trade)
            del self.active_trades[trade_id]

    def get_trade(self, trade_id: int) -> Optional[Trade]:
        """Get trade by ID."""
        return self.active_trades.get(trade_id)
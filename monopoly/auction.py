"""
Auction system for properties.
"""

from typing import Dict, List, Optional
from monopoly.money import EventLog, EventType


class Auction:
    """
    Manages an auction for a property.
    Players bid in turn until all but one have passed.
    """

    def __init__(
        self,
        property_position: int,
        property_name: str,
        eligible_player_ids: List[int],
        event_log: EventLog,
    ):
        self.property_position = property_position
        self.property_name = property_name
        self.eligible_player_ids = eligible_player_ids.copy()
        self.active_bidders = set(eligible_player_ids)
        self.current_bid = 0
        self.high_bidder: Optional[int] = None
        self.event_log = event_log
        self.is_complete = False

        self.event_log.log(
            EventType.AUCTION_START,
            details={
                "property": property_name,
                "position": property_position,
                "players": eligible_player_ids,
            },
        )

    def place_bid(self, player_id: int, amount: int) -> bool:
        """
        Place a bid for a player.
        Returns True if bid is accepted, False if invalid.
        """
        if self.is_complete:
            return False

        if player_id not in self.active_bidders:
            return False

        if amount <= self.current_bid:
            return False

        self.current_bid = amount
        self.high_bidder = player_id

        self.event_log.log(
            EventType.AUCTION_BID,
            player_id=player_id,
            details={"property": self.property_name, "amount": amount},
        )

        return True

    def pass_turn(self, player_id: int) -> None:
        """Player passes on bidding."""
        if player_id in self.active_bidders:
            self.active_bidders.remove(player_id)
            self._check_completion()

    def _check_completion(self) -> None:
        """Check if auction is complete (only one bidder remains)."""
        if len(self.active_bidders) <= 1:
            self.is_complete = True
            winner = self.high_bidder if self.high_bidder is not None else None

            self.event_log.log(
                EventType.AUCTION_END,
                player_id=winner,
                details={
                    "property": self.property_name,
                    "position": self.property_position,
                    "winning_bid": self.current_bid,
                    "winner": winner,
                },
            )

    def get_winner(self) -> Optional[int]:
        """Get the winning player ID, or None if auction incomplete or no bids."""
        if not self.is_complete:
            return None
        return self.high_bidder

    def get_winning_bid(self) -> int:
        """Get the winning bid amount."""
        return self.current_bid

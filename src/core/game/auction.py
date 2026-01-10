from typing import Dict, List, Optional

from core.game.money import EventLog, EventType


class Auction:
    """
    Manages an auction for a property.
    Players bid in turn until all but one have passed.

    The initiator (player who declined to buy) automatically places
    a starting bid of 10% of the property price. If all other players
    pass, the initiator wins with this minimum bid.
    """

    def __init__(
        self,
        property_position: int,
        property_name: str,
        eligible_player_ids: List[int],
        event_log: EventLog,
        initiator_id: int,
        property_price: int,
        max_bids_per_player: int = 3,
    ):
        self.property_position = property_position
        self.property_name = property_name
        self.eligible_player_ids = eligible_player_ids.copy()
        self.active_bidders = set(eligible_player_ids)
        self.event_log = event_log
        self.is_complete = False
        self.max_bids_per_player = max_bids_per_player
        self.bid_counts: Dict[int, int] = {pid: 0 for pid in eligible_player_ids}
        self.initiator_id = initiator_id

        # Calculate starting bid: 10% of property price (minimum $1)
        starting_bid = max(1, property_price // 10)

        # Initiator automatically places the starting bid
        self.current_bid = starting_bid
        self.high_bidder = initiator_id
        self.bid_counts[initiator_id] = 1

        self.event_log.log(
            EventType.AUCTION_START,
            details={
                "property": property_name,
                "position": property_position,
                "players": eligible_player_ids,
                "initiator": initiator_id,
                "starting_bid": starting_bid,
            },
        )

        # Log the automatic starting bid
        self.event_log.log(
            EventType.AUCTION_BID,
            player_id=initiator_id,
            details={
                "property": self.property_name,
                "amount": starting_bid,
                "bid_number": 1,
                "automatic": True,
            },
        )

    def place_bid(self, player_id: int, amount: int) -> bool:
        """
        Place a bid for a player.
        Returns True if bid is accepted, False if invalid.
        If bid is invalid (too low), player is automatically passed.
        """
        if self.is_complete:
            return False

        if player_id not in self.active_bidders:
            return False

        if amount <= self.current_bid:
            # Invalid bid - automatically pass this player
            self.pass_turn(player_id)
            return False

        # Check if player has reached max bids
        if self.bid_counts.get(player_id, 0) >= self.max_bids_per_player:
            # Automatically pass this player
            self.pass_turn(player_id)
            return False

        self.current_bid = amount
        self.high_bidder = player_id
        self.bid_counts[player_id] = self.bid_counts.get(player_id, 0) + 1

        self.event_log.log(
            EventType.AUCTION_BID,
            player_id=player_id,
            details={
                "property": self.property_name,
                "amount": amount,
                "bid_number": self.bid_counts[player_id],
            },
        )

        # Check if this player has exhausted their bids
        if self.bid_counts[player_id] >= self.max_bids_per_player:
            # Remove player from active bidders - they've used all their bids
            # They can still win if they have the high bid
            self.pass_turn(player_id)

        return True

    def pass_turn(self, player_id: int) -> None:
        """Player passes on bidding."""
        if player_id in self.active_bidders:
            self.active_bidders.remove(player_id)
            self.event_log.log(
                EventType.AUCTION_PASS,
                player_id=player_id,
                details={
                    "property": self.property_name,
                    "remaining_bidders": list(self.active_bidders),
                },
            )
            self._check_completion()
        else:
            # Player already passed - log warning
            self.event_log.log(
                EventType.AUCTION_PASS,
                player_id=player_id,
                details={
                    "property": self.property_name,
                    "already_passed": True,
                    "active_bidders": list(self.active_bidders),
                },
            )

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

    def can_player_bid(self, player_id: int) -> bool:
        """Check if a player can still place bids."""
        if player_id not in self.active_bidders:
            return False
        if self.bid_counts.get(player_id, 0) >= self.max_bids_per_player:
            return False
        return True

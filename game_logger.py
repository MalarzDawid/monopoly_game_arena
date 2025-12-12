"""
JSONL logger for Monopoly game events.

Logs all important game events to a JSONL file for analysis and debugging.
"""

import json
import os
from datetime import datetime
from typing import Any, Dict, Optional


class GameLogger:
    """Logger that writes game events to JSONL file."""

    def __init__(self, log_file: str = None):
        """
        Initialize game logger.

        Args:
            log_file: Path to log file. If None, generates timestamped filename.
        """
        if log_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = f"monopoly_game_{timestamp}.jsonl"

        self.log_file = log_file
        self.event_count = 0

        # Create/clear log file
        with open(self.log_file, 'w') as f:
            pass

    def log_event(self, event_type: str, **kwargs):
        """
        Log a game event to JSONL file.

        Args:
            event_type: Type of event (e.g., "game_start", "dice_roll", "purchase")
            **kwargs: Additional event data
        """
        event = {
            "event_id": self.event_count,
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            **kwargs
        }

        with open(self.log_file, 'a') as f:
            f.write(json.dumps(event) + '\n')

        self.event_count += 1

    def log_game_start(self, num_players: int, player_names: list, seed: Optional[int], max_turns: Optional[int]):
        """Log game start event."""
        self.log_event(
            "game_start",
            num_players=num_players,
            player_names=player_names,
            seed=seed,
            max_turns=max_turns
        )

    def log_turn_start(self, turn_number: int, player_id: int, player_name: str):
        """Log turn start event."""
        self.log_event(
            "turn_start",
            turn_number=turn_number,
            player_id=player_id,
            player_name=player_name
        )

    def log_dice_roll(self, player_id: int, player_name: str, die1: int, die2: int, is_doubles: bool):
        """Log dice roll event."""
        self.log_event(
            "dice_roll",
            player_id=player_id,
            player_name=player_name,
            die1=die1,
            die2=die2,
            total=die1 + die2,
            is_doubles=is_doubles
        )

    def log_move(self, player_id: int, player_name: str, from_pos: int, to_pos: int, space_name: str):
        """Log player movement."""
        self.log_event(
            "move",
            player_id=player_id,
            player_name=player_name,
            from_position=from_pos,
            to_position=to_pos,
            space_name=space_name
        )

    def log_purchase(self, player_id: int, player_name: str, property_name: str, position: int, price: int, cash_after: int):
        """Log property purchase."""
        self.log_event(
            "purchase",
            player_id=player_id,
            player_name=player_name,
            property_name=property_name,
            position=position,
            price=price,
            cash_after=cash_after
        )

    def log_decline_purchase(self, player_id: int, player_name: str, property_name: str, position: int):
        """Log declined purchase (triggers auction)."""
        self.log_event(
            "decline_purchase",
            player_id=player_id,
            player_name=player_name,
            property_name=property_name,
            position=position
        )

    def log_auction_start(self, property_name: str, position: int, eligible_players: list):
        """Log auction start."""
        self.log_event(
            "auction_start",
            property_name=property_name,
            position=position,
            eligible_players=eligible_players
        )

    def log_auction_bid(self, player_id: int, player_name: str, property_name: str, bid_amount: int, bid_number: int):
        """Log auction bid."""
        self.log_event(
            "auction_bid",
            player_id=player_id,
            player_name=player_name,
            property_name=property_name,
            bid_amount=bid_amount,
            bid_number=bid_number
        )

    def log_auction_pass(self, player_id: int, player_name: str, property_name: str):
        """Log auction pass."""
        self.log_event(
            "auction_pass",
            player_id=player_id,
            player_name=player_name,
            property_name=property_name
        )

    def log_auction_end(self, property_name: str, winner_id: Optional[int], winner_name: Optional[str], winning_bid: int, winner_cash_after: Optional[int] = None):
        """Log auction end."""
        self.log_event(
            "auction_end",
            property_name=property_name,
            winner_id=winner_id,
            winner_name=winner_name,
            winning_bid=winning_bid,
            winner_cash_after=winner_cash_after
        )

    def log_build_house(self, player_id: int, player_name: str, property_name: str, position: int, cost: int, houses_count: int):
        """Log house building."""
        self.log_event(
            "build_house",
            player_id=player_id,
            player_name=player_name,
            property_name=property_name,
            position=position,
            cost=cost,
            houses_count=houses_count
        )

    def log_build_hotel(self, player_id: int, player_name: str, property_name: str, position: int, cost: int):
        """Log hotel building."""
        self.log_event(
            "build_hotel",
            player_id=player_id,
            player_name=player_name,
            property_name=property_name,
            position=position,
            cost=cost
        )

    def log_rent_payment(self, payer_id: int, payer_name: str, owner_id: int, owner_name: str,
                         property_name: str, amount: int, payer_cash_after: int, owner_cash_after: int):
        """Log rent payment."""
        self.log_event(
            "rent_payment",
            payer_id=payer_id,
            payer_name=payer_name,
            owner_id=owner_id,
            owner_name=owner_name,
            property_name=property_name,
            amount=amount,
            payer_cash_after=payer_cash_after,
            owner_cash_after=owner_cash_after
        )

    def log_jail_entry(self, player_id: int, player_name: str, reason: str):
        """Log player going to jail."""
        self.log_event(
            "jail_entry",
            player_id=player_id,
            player_name=player_name,
            reason=reason
        )

    def log_jail_release(self, player_id: int, player_name: str, method: str):
        """Log player released from jail."""
        self.log_event(
            "jail_release",
            player_id=player_id,
            player_name=player_name,
            method=method
        )

    def log_mortgage(self, player_id: int, player_name: str, property_name: str, value: int):
        """Log property mortgage."""
        self.log_event(
            "mortgage",
            player_id=player_id,
            player_name=player_name,
            property_name=property_name,
            value=value
        )

    def log_unmortgage(self, player_id: int, player_name: str, property_name: str, cost: int):
        """Log property unmortgage."""
        self.log_event(
            "unmortgage",
            player_id=player_id,
            player_name=player_name,
            property_name=property_name,
            cost=cost
        )

    def log_trade_proposed(self, trade_id: int, proposer_id: int, proposer_name: str,
                          recipient_id: int, recipient_name: str,
                          proposer_offers: list, proposer_wants: list):
        """Log trade proposal."""
        self.log_event(
            "trade_proposed",
            trade_id=trade_id,
            proposer_id=proposer_id,
            proposer_name=proposer_name,
            recipient_id=recipient_id,
            recipient_name=recipient_name,
            proposer_offers=proposer_offers,
            proposer_wants=proposer_wants
        )

    def log_trade_accepted(self, trade_id: int, player_id: int, player_name: str):
        """Log trade acceptance."""
        self.log_event(
            "trade_accepted",
            trade_id=trade_id,
            player_id=player_id,
            player_name=player_name
        )

    def log_trade_rejected(self, trade_id: int, player_id: int, player_name: str):
        """Log trade rejection."""
        self.log_event(
            "trade_rejected",
            trade_id=trade_id,
            player_id=player_id,
            player_name=player_name
        )

    def log_trade_cancelled(self, trade_id: int, player_id: int, player_name: str):
        """Log trade cancellation."""
        self.log_event(
            "trade_cancelled",
            trade_id=trade_id,
            player_id=player_id,
            player_name=player_name
        )

    def log_trade_executed(self, trade_id: int, proposer_id: int, proposer_name: str,
                          recipient_id: int, recipient_name: str,
                          proposer_offers: list, proposer_wants: list,
                          proposer_cash_after: int, recipient_cash_after: int):
        """Log completed trade."""
        self.log_event(
            "trade_executed",
            trade_id=trade_id,
            proposer_id=proposer_id,
            proposer_name=proposer_name,
            recipient_id=recipient_id,
            recipient_name=recipient_name,
            proposer_offers=proposer_offers,
            proposer_wants=proposer_wants,
            proposer_cash_after=proposer_cash_after,
            recipient_cash_after=recipient_cash_after
        )

    def log_bankruptcy(self, player_id: int, player_name: str, creditor_id: Optional[int], creditor_name: Optional[str]):
        """Log player bankruptcy."""
        self.log_event(
            "bankruptcy",
            player_id=player_id,
            player_name=player_name,
            creditor_id=creditor_id,
            creditor_name=creditor_name
        )

    def log_game_end(self, turn_number: int, winner_id: Optional[int], winner_name: Optional[str],
                     reason: str, final_standings: list):
        """Log game end."""
        self.log_event(
            "game_end",
            turn_number=turn_number,
            winner_id=winner_id,
            winner_name=winner_name,
            reason=reason,
            final_standings=final_standings
        )

    def log_player_state(self, turn_number: int, player_id: int, player_name: str,
                         cash: int, properties_count: int, position: int, in_jail: bool):
        """Log player state snapshot (basic version for backwards compatibility)."""
        self.log_event(
            "player_state",
            turn_number=turn_number,
            player_id=player_id,
            player_name=player_name,
            cash=cash,
            properties_count=properties_count,
            position=position,
            in_jail=in_jail
        )

    def log_player_state_detailed(self, turn_number: int, player_id: int, player_name: str,
                                  cash: int, position: int, position_name: str,
                                  properties: list, mortgaged_properties: list,
                                  houses: dict, hotels: list,
                                  jail_free_cards: int, in_jail: bool, jail_turns: int,
                                  net_worth: int):
        """
        Log detailed player state snapshot.

        Args:
            turn_number: Current turn number
            player_id: Player ID
            player_name: Player name
            cash: Cash on hand
            position: Board position
            position_name: Name of current space
            properties: List of property names owned
            mortgaged_properties: List of mortgaged property names
            houses: Dict mapping property position to house count
            hotels: List of property names with hotels
            jail_free_cards: Number of "Get Out of Jail Free" cards
            in_jail: Whether player is in jail
            jail_turns: Number of turns in jail
            net_worth: Total net worth (cash + properties + buildings - mortgages)
        """
        self.log_event(
            "player_state_detailed",
            turn_number=turn_number,
            player_id=player_id,
            player_name=player_name,
            cash=cash,
            position=position,
            position_name=position_name,
            properties=properties,
            properties_count=len(properties),
            mortgaged_properties=mortgaged_properties,
            houses=houses,
            hotels=hotels,
            jail_free_cards=jail_free_cards,
            in_jail=in_jail,
            jail_turns=jail_turns if in_jail else 0,
            net_worth=net_worth
        )

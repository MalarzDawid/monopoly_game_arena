"""
JSONL logger for Monopoly game events.

Logs all important game events to a JSONL file and PostgreSQL database.
"""

import asyncio
import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from events.mapper import map_events


class GameLogger:
    """Logger that writes game events to JSONL file and database."""

    def __init__(self, log_file: str = None, game_id: str = None):
        """
        Initialize game logger.

        Args:
            log_file: Path to log file. If None, generates timestamped filename.
            game_id: Game ID for database logging
        """
        if log_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = f"monopoly_game_{timestamp}.jsonl"

        self.log_file = log_file
        self.game_id = game_id
        self.event_count = 0
        self._engine_last_idx = 0  # last flushed index from engine's internal EventLog
        self._db_enabled = game_id is not None
        self._pending_db_events: List[Dict[str, Any]] = []  # Buffer for async DB writes

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

        # Write to JSONL file
        with open(self.log_file, 'a') as f:
            f.write(json.dumps(event) + '\n')

        # Buffer event for database write
        if self._db_enabled:
            self._pending_db_events.append({
                "event_type": event_type,
                "event": event,
            })

        self.event_count += 1

    async def flush_to_db(self) -> int:
        """
        Flush all pending events to database.

        Returns:
            Number of events written to database
        """
        if not self._db_enabled or not self._pending_db_events:
            return 0

        events_to_write = self._pending_db_events.copy()
        self._pending_db_events.clear()

        try:
            from server.database import session_scope, GameRepository

            async with session_scope() as session:
                repo = GameRepository(session)

                # Get game UUID from game_id
                game = await repo.get_game_by_id(self.game_id)
                if not game:
                    return 0

                # Prepare batch of events
                batch_events = []
                for item in events_to_write:
                    event_type = item["event_type"]
                    event = item["event"]

                    batch_events.append({
                        "sequence_number": event.get("event_id", 0),
                        "turn_number": event.get("turn_number", 0),
                        "event_type": event_type,
                        "payload": event,
                        "actor_player_id": event.get("player_id"),
                    })

                # Write batch to database
                if batch_events:
                    await repo.add_events_batch(game.id, batch_events)

                return len(batch_events)
        except Exception as e:
            # Don't crash game if DB logging fails
            print(f"[DB] Database logging failed: {e}")
            return 0

    def flush_engine_events(self, game) -> int:
        """Flush new internal engine events to JSONL using EventMapper.

        Returns the number of events written.
        """
        events = game.event_log.events
        if self._engine_last_idx >= len(events):
            return 0

        new_events = events[self._engine_last_idx :]
        mapped = map_events(
            game.board,
            new_events,
            player_positions={pid: p.position for pid, p in game.players.items()},
        )

        wrote = 0
        for m in mapped:
            # Add turn_number to every event (use game's current turn if not present)
            if "turn_number" not in m:
                m["turn_number"] = game.turn_number

            # Enrich with names
            if "player_id" in m:
                m["player_name"] = game.players[m["player_id"]].name
            if m.get("event_type") == "rent_payment":
                payer_id = m.get("payer_id")
                owner_id = m.get("owner_id")
                if payer_id is not None:
                    m["payer_name"] = game.players[payer_id].name
                if owner_id is not None:
                    m["owner_name"] = game.players[owner_id].name
            if m.get("event_type") == "auction_end" and m.get("winner_id") is not None:
                wid = m["winner_id"]
                m["winner_name"] = game.players[wid].name
                m["winner_cash_after"] = game.players[wid].cash

            if m.get("event_type") == "game_end":
                # Add turn number and winner name for analyzer convenience
                m["turn_number"] = game.turn_number
                wid = m.get("winner_id")
                if wid is not None:
                    m["winner_name"] = game.players[wid].name
                # Include final standings summary
                final = []
                for pid, p in sorted(game.players.items()):
                    try:
                        worth = game._calculate_net_worth(pid)  # engine helper
                    except Exception:
                        worth = p.cash
                    final.append({
                        "player_id": pid,
                        "player_name": p.name,
                        "net_worth": worth,
                        "is_bankrupt": p.is_bankrupt,
                    })
                m["final_standings"] = final

            etype = m.pop("event_type")
            self.log_event(etype, **m)
            wrote += 1

        self._engine_last_idx = len(events)
        return wrote

    def log_turn_snapshot(self, game) -> None:
        """Log detailed state snapshots for all players at the start of a turn."""
        for player_id, player in sorted(game.players.items()):
            # Current space name
            space = game.board.get_space(player.position)
            position_name = space.name

            properties = []
            mortgaged_properties = []
            houses = {}
            hotels = []

            for prop_pos in sorted(player.properties):
                prop_space = game.board.get_property_space(prop_pos)
                if not prop_space:
                    continue
                prop_name = prop_space.name
                properties.append(prop_name)

                ownership = game.property_ownership.get(prop_pos)
                if ownership and ownership.is_mortgaged:
                    mortgaged_properties.append(prop_name)

                if ownership:
                    if ownership.houses == 5:
                        hotels.append(prop_name)
                    elif ownership.houses > 0:
                        houses[prop_name] = ownership.houses

            # Net worth (approx, aligned with engine semantics)
            try:
                net_worth = game._calculate_net_worth(player_id)
            except Exception:
                net_worth = player.cash

            self.log_player_state_detailed(
                turn_number=game.turn_number,
                player_id=player_id,
                player_name=player.name,
                cash=player.cash,
                position=player.position,
                position_name=position_name,
                properties=properties,
                mortgaged_properties=mortgaged_properties,
                houses=houses,
                hotels=hotels,
                jail_free_cards=player.get_out_of_jail_cards,
                in_jail=player.in_jail,
                jail_turns=player.jail_turns,
                net_worth=net_worth,
            )

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
        """Log player going to jail (legacy method, canonical event_type is 'go_to_jail')."""
        self.log_event(
            "go_to_jail",
            player_id=player_id,
            player_name=player_name,
            reason=reason
        )

    def log_go_to_jail(self, player_id: int, player_name: str, reason: str):
        """Log player going to jail (canonical)."""
        self.log_event(
            "go_to_jail",
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

    def log_llm_decision(
        self,
        turn_number: int,
        player_id: int,
        player_name: str,
        action_type: str,
        params: dict,
        reasoning: str,
        used_fallback: bool,
        processing_time_ms: int,
        model_version: str,
        strategy: str,
        error: Optional[str] = None,
        raw_response: Optional[str] = None,
    ):
        """
        Log LLM agent decision.

        Args:
            turn_number: Current turn number
            player_id: Player ID
            player_name: Player name
            action_type: Chosen action type
            params: Action parameters
            reasoning: LLM's rationale for the decision
            used_fallback: Whether fallback was used
            processing_time_ms: Time taken for decision
            model_version: LLM model version
            strategy: Strategy template used
            error: Error message if any
            raw_response: Raw LLM response for debugging
        """
        self.log_event(
            "llm_decision",
            turn_number=turn_number,
            player_id=player_id,
            player_name=player_name,
            action_type=action_type,
            params=params,
            reasoning=reasoning,
            used_fallback=used_fallback,
            processing_time_ms=processing_time_ms,
            model_version=model_version,
            strategy=strategy,
            error=error,
            raw_response=raw_response[:500] if raw_response else None,  # Truncate for log
        )

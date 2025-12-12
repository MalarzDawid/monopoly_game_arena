"""
Text report generator for game analysis.
"""

from typing import List, Dict, Any
from analyzer.game_analyzer import MonopolyGameAnalyzer, PlayerStats


class ReportGenerator:
    """Game report generator."""

    def __init__(self, analyzer: MonopolyGameAnalyzer):
        self.analyzer = analyzer

    def generate_summary_report(self) -> str:
        """Generate game summary report."""
        summary = self.analyzer.game_summary
        if not summary:
            return "❌ No game data available"

        lines = []
        lines.append("=" * 70)
        lines.append("🎲 MONOPOLY - GAME SUMMARY")
        lines.append("=" * 70)
        lines.append(f"📁 Game ID: {summary.game_id}")
        lines.append(f"👥 Number of players: {summary.num_players}")
        lines.append(f"📛 Players: {', '.join(summary.player_names)}")
        lines.append(f"🔄 Total turns: {summary.total_turns}")
        lines.append(f"⏱️  Duration: {summary.game_duration}")
        lines.append(f"🏁 End reason: {summary.end_reason}")

        if summary.winner:
            lines.append(f"🏆 Winner: {summary.winner} (${summary.winner_networth:,})")
        else:
            lines.append("🏆 Winner: Game incomplete")

        lines.append("=" * 70)
        return "\n".join(lines)

    def generate_player_stats_report(self) -> str:
        """Generate player statistics report."""
        lines = []
        lines.append("\n" + "=" * 70)
        lines.append("📊 PLAYER STATISTICS")
        lines.append("=" * 70)

        # Sort players by networth
        sorted_players = sorted(
            self.analyzer.player_stats.values(),
            key=lambda p: p.final_networth,
            reverse=True
        )

        for rank, player in enumerate(sorted_players, 1):
            lines.append(f"\n{'🥇' if rank == 1 else '🥈' if rank == 2 else '🥉' if rank == 3 else '👤'} #{rank} {player.player_name}")
            lines.append(f"   💰 Total networth: ${player.final_networth:,}")
            lines.append(f"   💵 Cash: ${player.final_cash:,}")
            lines.append(f"   🏠 Properties: {player.total_properties}")

            if player.properties_owned:
                props_str = ", ".join(player.properties_owned[:5])
                if len(player.properties_owned) > 5:
                    props_str += f" (+{len(player.properties_owned) - 5} more)"
                lines.append(f"      └─ {props_str}")

            lines.append(f"   🏘️  Houses: {player.total_houses} | Hotels: {player.total_hotels}")
            lines.append(f"   🚔 Times in jail: {player.times_in_jail}")
            lines.append(f"   💸 Rent paid: ${player.total_rent_paid:,}")
            lines.append(f"   💰 Rent received: ${player.total_rent_received:,}")

            if player.bankrupted:
                lines.append(f"   💥 Status: BANKRUPT")

        lines.append("=" * 70)
        return "\n".join(lines)

    def _format_event(self, event: Dict[str, Any]) -> str:
        """Format a single event into readable text."""
        event_type = event.get('event_type')

        # Get cash_after based on event type
        cash_after = None

        if event_type == 'rent_payment':
            cash_after = event.get('payer_cash_after')
        elif event_type == 'purchase':
            cash_after = event.get('cash_after')
        elif event_type == 'auction_end':
            # Only show winner's cash
            cash_after = event.get('winner_cash_after')
        elif event_type == 'card_effect':
            cash_after = event.get('cash_after')
        else:
            cash_after = event.get('cash_after')

        # Helper function to add cash info
        def add_cash_info(text: str) -> str:
            if cash_after is not None:
                return f"{text} | 💵 Cash after: ${cash_after:,}"
            return text

        if event_type == 'dice_roll':
            die1 = event.get('die1', 0)
            die2 = event.get('die2', 0)
            total = event.get('total', 0)
            is_doubles = event.get('is_doubles', False)
            doubles_str = " 🎯 DOUBLES!" if is_doubles else ""
            return f"🎲 Dice roll: {die1} + {die2} = {total}{doubles_str}"

        elif event_type == 'move':
            from_pos = event.get('from_position', 0)
            to_pos = event.get('to_position', 0)
            space_name = event.get('space_name', '?')
            return f"🚶 Move: position {from_pos} → {to_pos} ({space_name})"

        elif event_type == 'land':
            space_name = event.get('space_name', '?')
            position = event.get('position', 0)
            return f"📍 Landing on: {space_name} (space #{position})"

        elif event_type == 'purchase':
            property_name = event.get('property_name', '?')
            price = event.get('price', 0)
            return add_cash_info(f"💰 PURCHASE: {property_name} for ${price:,}")

        elif event_type == 'decline_purchase':
            property_name = event.get('property_name', '?')
            return f"❌ Declined purchase: {property_name}"

        elif event_type == 'rent_payment':
            owner_name = event.get('owner_name', '?')
            amount = event.get('amount', 0)
            property_name = event.get('property_name', '?')
            return add_cash_info(f"💸 Rent: ${amount:,} → {owner_name} for {property_name}")

        elif event_type == 'card_draw':
            deck = event.get('deck', '?')
            card = event.get('card', '?')
            return f"🃏 Card ({deck}): \"{card}\""

        elif event_type == 'card_effect':
            effect_type = event.get('effect_type', '?')
            amount = event.get('amount')
            if amount is not None and amount != 0:
                return add_cash_info(f"   ↳ Card effect: {effect_type} (${amount:,})")
            else:
                return add_cash_info(f"   ↳ Card effect: {effect_type}")

        elif event_type == 'jail_enter':
            return f"🚔 SENT TO JAIL!"

        elif event_type == 'jail_exit':
            method = event.get('method', '?')
            return add_cash_info(f"🔓 Exit from jail (method: {method})")

        elif event_type == 'build_house':
            property_name = event.get('property_name', '?')
            count = event.get('house_count', 1)
            return add_cash_info(f"🏗️  Build house on: {property_name} (houses: {count})")

        elif event_type == 'build_hotel':
            property_name = event.get('property_name', '?')
            return add_cash_info(f"🏨 Build HOTEL on: {property_name}")

        elif event_type == 'sell_building':
            property_name = event.get('property_name', '?')
            return add_cash_info(f"🔨 Sell building from: {property_name}")

        elif event_type == 'mortgage_property':
            property_name = event.get('property_name', '?')
            amount = event.get('amount', 0)
            return add_cash_info(f"🏦 Mortgage: {property_name} for ${amount:,}")

        elif event_type == 'unmortgage_property':
            property_name = event.get('property_name', '?')
            cost = event.get('cost', 0)
            return add_cash_info(f"💳 Unmortgage: {property_name} for ${cost:,}")

        elif event_type == 'bankruptcy':
            creditor_name = event.get('creditor_name', '?')
            return f"💥 BANKRUPTCY! (creditor: {creditor_name})"

        elif event_type == 'pass_go':
            amount = event.get('amount', 200)
            return add_cash_info(f"➡️  Pass GO (+${amount:,})")

        elif event_type == 'tax_payment':
            amount = event.get('amount', 0)
            tax_type = event.get('tax_type', 'tax')
            return add_cash_info(f"💰 Tax: ${amount:,} ({tax_type})")

        elif event_type == 'auction_start':
            property_name = event.get('property_name', '?')
            return f"🔨 Auction started: {property_name}"

        elif event_type == 'auction_bid':
            bid_amount = event.get('bid_amount', 0)
            bid_number = event.get('bid_number', 0)
            player_name = event.get('player_name', '?')
            return f"   ↳ {player_name} bids ${bid_amount:,} (round {bid_number})"

        elif event_type == 'auction_pass':
            player_name = event.get('player_name', '?')
            remaining_count = event.get('remaining_count', 0)
            return f"   ⏸️  {player_name} passes ({remaining_count} bidders remaining)"

        elif event_type == 'auction_end':
            winner_name = event.get('winner_name')
            if winner_name:
                winning_bid = event.get('winning_bid', 0)
                return add_cash_info(f"🔨 Auction won by: {winner_name} for ${winning_bid:,}")
            else:
                return f"🔨 Auction without winner"

        elif event_type == 'trade_proposed':
            recipient_name = event.get('recipient_name', '?')
            return f"🤝 Trade proposal → {recipient_name}"

        elif event_type == 'trade_accepted':
            return f"✅ Trade accepted"

        elif event_type == 'trade_rejected':
            return f"❌ Trade rejected"

        else:
            # Unknown event - show raw
            return f"❓ {event_type}"

    def generate_turn_by_turn_report(self, start_turn: int = 0, end_turn: int = 10) -> str:
        """Generate step-by-step turn report - each turn shows player actions."""
        lines = []
        lines.append("\n" + "=" * 70)
        lines.append(f"📝 GAME PROGRESS (Turns {start_turn}-{end_turn})")
        lines.append("=" * 70)

        for turn in range(start_turn, end_turn + 1):
            # Get player name for this turn
            player_name = self.analyzer.get_turn_player_name(turn)

            # Get all events from this turn
            turn_events = self.analyzer.get_turn_events(turn)

            if not turn_events:
                continue

            # Find player_id for this turn
            turn_start = next((e for e in turn_events if e.get('event_type') == 'turn_start'), None)
            current_player_id = turn_start.get('player_id') if turn_start else None

            # Find initial player state (from player_state_detailed FOR THIS PLAYER)
            initial_state = next((e for e in turn_events
                                  if e.get('event_type') == 'player_state_detailed'
                                  and e.get('player_id') == current_player_id), None)

            current_cash = initial_state.get('cash', 0) if initial_state else 0

            # Turn header
            lines.append(f"\n{'=' * 70}")
            lines.append(f"🔹 TURN {turn}: {player_name} | 💰 Starting: ${current_cash:,}")
            lines.append(f"{'=' * 70}")

            # Skip turn_start and player_state_detailed - focus on actions
            action_events = [e for e in turn_events
                             if e.get('event_type') not in ['turn_start', 'player_state_detailed']]

            if not action_events:
                lines.append("   ⏭️  (no actions - player passed turn)")
            else:
                for event in action_events:
                    event_type = event.get('event_type')

                    # Update cash based on event type
                    if event_type == 'rent_payment':
                        # Only update if this player is the payer
                        if event.get('payer_id') == current_player_id:
                            current_cash = event.get('payer_cash_after', current_cash)
                    elif event_type == 'purchase':
                        current_cash = event.get('cash_after', current_cash)
                    elif event_type == 'auction_end':
                        # Only update if this player won
                        if event.get('winner_id') == current_player_id:
                            current_cash = event.get('winner_cash_after', current_cash)
                    elif event_type == 'card_effect':
                        current_cash = event.get('cash_after', current_cash)
                    elif 'cash_after' in event:
                        current_cash = event.get('cash_after', current_cash)

                    formatted = self._format_event(event)

                    # Show cash only for events that don't already include it
                    if event_type in ['dice_roll', 'move', 'land', 'decline_purchase', 'auction_start', 'auction_bid',
                                      'auction_pass', 'card_draw', 'jail_enter']:
                        lines.append(f"   {formatted} | 💵 Cash: ${current_cash:,}")
                    else:
                        lines.append(f"   {formatted}")

        lines.append("\n" + "=" * 70)
        return "\n".join(lines)

    def generate_property_analysis(self) -> str:
        """Generate property ownership analysis."""
        lines = []
        lines.append("\n" + "=" * 70)
        lines.append("🏘️  PROPERTY ANALYSIS")
        lines.append("=" * 70)

        # Collect all purchases
        purchases = self.analyzer.get_events_by_type('purchase')

        if not purchases:
            lines.append("❌ No purchases in this game")
        else:
            lines.append(f"\n📊 Total properties purchased: {len(purchases)}\n")

            # Group by players
            by_player = {}
            for purchase in purchases:
                player_name = purchase.get('player_name', '?')
                property_name = purchase.get('property_name', '?')
                price = purchase.get('price', 0)

                if player_name not in by_player:
                    by_player[player_name] = []
                by_player[player_name].append((property_name, price))

            for player_name, props in sorted(by_player.items(), key=lambda x: len(x[1]), reverse=True):
                total_spent = sum(p[1] for p in props)
                lines.append(f"👤 {player_name}: {len(props)} properties (spent: ${total_spent:,})")
                for prop_name, price in props[:10]:  # Show max 10
                    lines.append(f"   • {prop_name} (${price:,})")
                if len(props) > 10:
                    lines.append(f"   ... and {len(props) - 10} more")
                lines.append("")

        lines.append("=" * 70)
        return "\n".join(lines)

    def generate_full_report(self, max_turns: int = 10) -> str:
        """Generate full comprehensive report."""
        report = []
        report.append(self.generate_summary_report())
        report.append(self.generate_player_stats_report())
        report.append(self.generate_property_analysis())
        report.append(self.generate_turn_by_turn_report(0, max_turns))
        return "\n".join(report)

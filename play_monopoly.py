#!/usr/bin/env python3
"""
Minimal CLI for simulating Monopoly games.

This script demonstrates the game engine by running simulated games with
simple AI players that make random or basic strategic decisions.
"""

import random
import argparse
from typing import List, Optional

from monopoly.game import create_game, ActionType
from monopoly.player import Player
from monopoly.config import GameConfig
from monopoly.rules import get_legal_actions, apply_action, Action
from game_logger import GameLogger


class RandomAgent:
    """
    Simple AI that makes random legal moves.
    """

    def __init__(self, player_id: int, name: str):
        self.player_id = player_id
        self.name = name
        self.rng = random.Random()

    def choose_action(self, game, legal_actions: List[Action]) -> Action:
        """
        Choose a random legal action with basic priorities to avoid infinite loops.
        Prioritize ROLL_DICE and END_TURN to keep the game moving.
        """
        # Strongly prefer ROLL_DICE to keep game moving
        for a in legal_actions:
            if a.action_type == ActionType.ROLL_DICE and self.rng.random() < 0.8:
                return a

        # Prefer END_TURN to avoid getting stuck
        for a in legal_actions:
            if a.action_type == ActionType.END_TURN and self.rng.random() < 0.7:
                return a

        # Otherwise choose randomly
        action = self.rng.choice(legal_actions)

        # Handle bidding - need to set a bid amount
        if action.action_type == ActionType.BID and game.active_auction:
            current_bid = game.active_auction.current_bid
            player_cash = game.players[self.player_id].cash

            # Randomly bid between current_bid + 1 and a reasonable max
            max_bid = min(player_cash, current_bid + 100)
            if max_bid > current_bid:
                action.params["amount"] = self.rng.randint(current_bid + 1, max_bid)
            else:
                # Can't afford to bid, choose PASS instead
                for a in legal_actions:
                    if a.action_type == ActionType.PASS_AUCTION:
                        return a

        return action


def log_action_effects(game, action: Action, player_id: int, logger: GameLogger, old_position: int = None):
    """Log the effects of an action after it's applied."""
    player = game.players[player_id]
    player_name = player.name

    if action.action_type == ActionType.ROLL_DICE and game.last_dice_roll:
        die1, die2 = game.last_dice_roll
        is_doubles = die1 == die2
        logger.log_dice_roll(player_id, player_name, die1, die2, is_doubles)

        # Log movement after dice roll
        if old_position is not None and player.position != old_position:
            space = game.board.get_space(player.position)
            logger.log_move(player_id, player_name, old_position, player.position, space.name)

    elif action.action_type == ActionType.BUY_PROPERTY:
        pos = action.params.get("position", player.position)
        space = game.board.get_space(pos)
        logger.log_purchase(player_id, player_name, space.name, pos, space.price, player.cash)

    elif action.action_type == ActionType.DECLINE_PURCHASE:
        pos = action.params.get("position", player.position)
        space = game.board.get_space(pos)
        logger.log_decline_purchase(player_id, player_name, space.name, pos)

    elif action.action_type == ActionType.BUILD_HOUSE:
        pos = action.params.get("position")
        space = game.board.get_property_space(pos)
        if space:
            ownership = game.property_ownership[pos]
            logger.log_build_house(player_id, player_name, space.name, pos, space.house_cost, ownership.houses)

    elif action.action_type == ActionType.BUILD_HOTEL:
        pos = action.params.get("position")
        space = game.board.get_property_space(pos)
        if space:
            logger.log_build_hotel(player_id, player_name, space.name, pos, space.house_cost)

    elif action.action_type == ActionType.BID:
        # Note: auction might have completed after this bid, so get info from action params
        amount = action.params.get("amount", 0)
        # Property name should be stored in action or get from last auction event
        property_name = action.params.get("property_name")
        if not property_name:
            # Try to get from active or recently completed auction
            for event in reversed(game.event_log.events[-10:]):
                if event.event_type.value in ['auction_bid', 'auction_start', 'auction_end']:
                    details = event.details.get('details', event.details)
                    property_name = details.get('property')
                    if property_name:
                        break

        # Get bid number from internal event log (most recent auction_bid for this player)
        bid_num = 0
        for event in reversed(game.event_log.events[-20:]):
            if event.event_type.value == 'auction_bid' and event.player_id == player_id:
                details = event.details.get('details', event.details)
                if details.get('property') == property_name:
                    bid_num = details.get('bid_number', 0)
                    break

        if property_name and bid_num > 0:
            logger.log_auction_bid(player_id, player_name, property_name, amount, bid_num)

    elif action.action_type == ActionType.PASS_AUCTION and game.active_auction:
        property_name = game.active_auction.property_name
        logger.log_auction_pass(player_id, player_name, property_name)

    elif action.action_type == ActionType.MORTGAGE_PROPERTY:
        pos = action.params.get("position")
        space = game.board.get_space(pos)
        if hasattr(space, 'mortgage_value'):
            logger.log_mortgage(player_id, player_name, space.name, space.mortgage_value)

    elif action.action_type == ActionType.UNMORTGAGE_PROPERTY:
        pos = action.params.get("position")
        space = game.board.get_space(pos)
        if hasattr(space, 'mortgage_value'):
            cost = int(space.mortgage_value * 1.1)
            logger.log_unmortgage(player_id, player_name, space.name, cost)

    elif action.action_type == ActionType.PAY_JAIL_FINE or action.action_type == ActionType.USE_JAIL_CARD:
        method = "fine" if action.action_type == ActionType.PAY_JAIL_FINE else "card"
        logger.log_jail_release(player_id, player_name, method)

    elif action.action_type == ActionType.DECLARE_BANKRUPTCY:
        creditor_id = action.params.get("creditor_id")
        creditor_name = game.players[creditor_id].name if creditor_id is not None else None
        logger.log_bankruptcy(player_id, player_name, creditor_id, creditor_name)


class GreedyAgent:
    """
    Simple AI that prefers buying properties and building when possible.
    Will occasionally decline expensive purchases to trigger auctions.
    """

    def __init__(self, player_id: int, name: str):
        self.player_id = player_id
        self.name = name
        self.rng = random.Random(player_id)  # Deterministic based on player_id

    def choose_action(self, game, legal_actions: List[Action]) -> Action:
        """Choose action with simple greedy strategy."""
        player = game.players[self.player_id]

        # Check if BUY_PROPERTY is available and decide based on affordability
        buy_action = None
        decline_action = None
        for action in legal_actions:
            if action.action_type == ActionType.BUY_PROPERTY:
                buy_action = action
            elif action.action_type == ActionType.DECLINE_PURCHASE:
                decline_action = action

        # If both buy and decline are available, decide based on cash reserves and randomness
        if buy_action and decline_action:
            position = action.params.get("position", player.position)
            space = game.board.get_property_space(position)
            if space:
                price_ratio = space.price / player.cash

                # Decline if property costs more than 40% of cash
                if price_ratio > 0.4:
                    return decline_action

                # For moderately expensive properties (20-40%), randomly decline 30% of the time
                # This creates more auction opportunities
                if price_ratio > 0.2 and self.rng.random() < 0.3:
                    return decline_action

                # Otherwise buy
                return buy_action

        # Handle trade responses - automatically reject all incoming trades
        # (simple agents don't actively trade)
        for action in legal_actions:
            if action.action_type == ActionType.REJECT_TRADE:
                return action

        # Priority order for other actions
        priority = [
            ActionType.ROLL_DICE,
            ActionType.BUY_PROPERTY,
            ActionType.BUILD_HOTEL,
            ActionType.BUILD_HOUSE,
            ActionType.UNMORTGAGE_PROPERTY,
            ActionType.PAY_JAIL_FINE,
            ActionType.USE_JAIL_CARD,
            ActionType.BID,  # Will need smart bidding in real implementation
            ActionType.END_TURN,
            ActionType.DECLINE_PURCHASE,
            ActionType.PASS_AUCTION,
            # Note: PROPOSE_TRADE, ACCEPT_TRADE, CANCEL_TRADE are intentionally not in priority
            # Simple agents don't actively trade
        ]

        for action_type in priority:
            for action in legal_actions:
                if action.action_type == action_type:
                    # For bidding, bid a reasonable amount
                    if action_type == ActionType.BID and game.active_auction:
                        current_bid = game.active_auction.current_bid
                        max_bid = game.players[self.player_id].cash // 2
                        if current_bid + 10 <= max_bid:
                            action.params["amount"] = current_bid + 10
                            return action
                        # Otherwise pass
                        continue
                    return action

        return legal_actions[0] if legal_actions else None


def log_all_player_states(game, logger):
    """Log detailed state of all players at start of turn."""
    for player_id, player in sorted(game.players.items()):
        # Get current position name
        space = game.board.get_space(player.position)
        position_name = space.name

        # Get list of owned properties with names
        properties = []
        mortgaged_properties = []
        houses = {}
        hotels = []

        for prop_pos in sorted(player.properties):
            prop_space = game.board.get_property_space(prop_pos)
            if prop_space:
                prop_name = prop_space.name
                properties.append(prop_name)

                # Check if mortgaged
                ownership = game.property_ownership.get(prop_pos)
                if ownership and ownership.is_mortgaged:
                    mortgaged_properties.append(prop_name)

                # Check for houses/hotels (5 houses = 1 hotel in game logic)
                if ownership:
                    if ownership.houses == 5:
                        hotels.append(prop_name)
                    elif ownership.houses > 0:
                        houses[prop_name] = ownership.houses

        # Count jail free cards
        jail_free_cards = player.get_out_of_jail_cards

        # Calculate net worth (simplified)
        net_worth = player.cash
        for prop_pos in player.properties:
            prop_space = game.board.get_property_space(prop_pos)
            if prop_space:
                ownership = game.property_ownership.get(prop_pos)
                if ownership:
                    if ownership.is_mortgaged:
                        # Mortgaged property counts as mortgage value
                        net_worth += prop_space.mortgage_value
                    else:
                        # Unmortgaged property counts as price
                        net_worth += prop_space.price
                        # Add building value (5 houses = hotel)
                        if ownership.houses == 5:
                            # Hotel costs 5x house_cost (4 houses + 1 hotel)
                            net_worth += 5 * prop_space.house_cost
                        else:
                            net_worth += ownership.houses * prop_space.house_cost

        logger.log_player_state_detailed(
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
            jail_free_cards=jail_free_cards,
            in_jail=player.in_jail,
            jail_turns=player.jail_turns,
            net_worth=net_worth
        )


def print_game_state(game):
    """Print current game state."""
    print("\n" + "=" * 60)
    print(f"TURN {game.turn_number}")
    print("=" * 60)

    for player_id, player in sorted(game.players.items()):
        if player.is_bankrupt:
            status = "BANKRUPT"
        elif player.in_jail:
            status = f"IN JAIL ({player.jail_turns} turns)"
        else:
            space = game.board.get_space(player.position)
            status = f"at {space.name}"

        print(
            f"Player {player_id} ({player.name}): ${player.cash} | "
            f"{len(player.properties)} properties | {status}"
        )


def print_game_summary(game):
    """Print final game summary."""
    print("\n" + "=" * 60)
    print("GAME OVER")
    print("=" * 60)

    if game.winner is not None:
        winner = game.players[game.winner]
        print(f"\nWinner: {winner.name}")
        print(f"Final Cash: ${winner.cash}")
        print(f"Properties Owned: {len(winner.properties)}")

    print("\nFinal Standings:")
    for player_id, player in sorted(game.players.items()):
        worth = game._calculate_net_worth(player_id)
        status = "BANKRUPT" if player.is_bankrupt else f"${worth}"
        print(f"  {player.name}: {status}")

    print(f"\nTotal Turns: {game.turn_number}")


def simulate_game(
    num_players: int = 4,
    agent_type: str = "greedy",
    seed: int = None,
    verbose: bool = True,
    max_turns: int = None,
    log_file: str = None,
) -> None:
    """
    Simulate a complete game of Monopoly.

    Args:
        num_players: Number of players (2-8)
        agent_type: Type of AI ('random' or 'greedy')
        seed: Random seed for reproducibility
        verbose: Whether to print detailed output
        max_turns: Maximum number of turns (for time limit variant)
        log_file: Path to JSONL log file (None = auto-generate)
    """
    # Initialize logger
    logger = GameLogger(log_file) if log_file is not None else GameLogger()
    # Create players
    player_names = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank", "Grace", "Hank"]
    players = [Player(i, player_names[i]) for i in range(num_players)]

    # Create agents
    if agent_type == "random":
        agents = [RandomAgent(i, player_names[i]) for i in range(num_players)]
    else:
        agents = [GreedyAgent(i, player_names[i]) for i in range(num_players)]

    # Create game
    config = GameConfig(seed=seed, time_limit_turns=max_turns)
    game = create_game(config, players)

    # Log game start
    logger.log_game_start(num_players, player_names[:num_players], seed, max_turns)

    if verbose:
        print(f"Starting game with {num_players} players using {agent_type} agents")
        print(f"Seed: {seed}")
        print(f"Logging to: {logger.log_file}")

    # Safety limit to prevent infinite loops in case of bugs
    # The actual turn limit is handled by config.time_limit_turns
    iteration_count = 0
    max_iterations = 10000  # Safety limit for iterations, not turns

    # Track auction state to cycle through bidders properly
    auction_bidder_rotation = {}  # auction_id -> current_bidder_index
    last_auction_id = None  # Track to detect auction completion

    # Track last event log size to detect new events (like rent payment)
    last_event_log_size = len(game.event_log.events)
    last_turn_number = -1  # Track turn changes

    while not game.game_over and iteration_count < max_iterations:
        iteration_count += 1
        current_player = game.get_current_player()

        # Log detailed player states at start of each new turn
        if game.turn_number != last_turn_number:
            last_turn_number = game.turn_number
            logger.log_turn_start(game.turn_number, current_player.player_id, current_player.name)
            log_all_player_states(game, logger)

        # Check for new events in internal event log (rent payments, auctions, taxes, etc)
        current_event_log_size = len(game.event_log.events)
        if current_event_log_size > last_event_log_size:
            # Process new events
            for event in game.event_log.events[last_event_log_size:]:
                if event.event_type.value == 'rent_payment':
                    payer_id = event.player_id
                    details = event.details.get('details', event.details)
                    owner_id = details.get('owner')
                    amount = details.get('amount')

                    if payer_id is not None and owner_id is not None:
                        payer = game.players[payer_id]
                        owner = game.players[owner_id]
                        # Get property name from payer's position
                        space = game.board.get_space(payer.position)
                        logger.log_rent_payment(
                            payer_id, payer.name,
                            owner_id, owner.name,
                            space.name, amount
                        )

                elif event.event_type.value == 'auction_start':
                    # Log auction start from internal event log
                    # Note: details are nested under 'details' key
                    details = event.details.get('details', event.details)
                    property_name = details.get('property')
                    position = details.get('position')
                    eligible_players = details.get('players', [])
                    logger.log_auction_start(property_name, position, eligible_players)

            last_event_log_size = current_event_log_size

        if verbose and game.turn_number % 10 == 0 and iteration_count % 10 == 1:
            print_game_state(game)

        # Get agent
        agent = agents[current_player.player_id]

        # Play turn with action limit to prevent infinite loops
        actions_this_turn = 0
        max_actions_per_turn = 100  # Safety limit

        while not game.game_over and actions_this_turn < max_actions_per_turn:
            # Check if auction just completed
            if last_auction_id is not None and game.active_auction is None:
                # Auction just completed, check who won from event log
                # The auction class already logged it, but we need to add to our JSONL
                for event in reversed(game.event_log.events[-5:]):
                    if event.event_type.value == 'auction_end':
                        # Handle both nested and non-nested details
                        details = event.details.get('details', event.details)
                        winner_id = details.get('winner')
                        winner_name = game.players[winner_id].name if winner_id is not None else None
                        winning_bid = details.get('winning_bid', 0)
                        property_name = details.get('property')

                        # Get winner's cash after purchase
                        winner_cash_after = None
                        if winner_id is not None:
                            winner_cash_after = game.players[winner_id].cash

                        logger.log_auction_end(property_name, winner_id, winner_name, winning_bid, winner_cash_after)
                        break
                last_auction_id = None

            # Check if there's an active auction - cycle through all active bidders
            if game.active_auction and game.active_auction.active_bidders:
                last_auction_id = id(game.active_auction)
                auction_id = id(game.active_auction)

                # Get sorted list of active bidders who can still bid
                active_bidders = sorted([
                    pid for pid in game.active_auction.active_bidders
                    if game.active_auction.can_player_bid(pid)
                ])

                if not active_bidders:
                    # No one can bid anymore, auction should complete
                    # Pass all remaining bidders
                    for pid in list(game.active_auction.active_bidders):
                        game.active_auction.pass_turn(pid)
                    continue

                # Initialize or get current bidder index for this auction
                if auction_id not in auction_bidder_rotation:
                    auction_bidder_rotation[auction_id] = 0

                # Get next bidder in round-robin fashion
                bidder_idx = auction_bidder_rotation[auction_id] % len(active_bidders)
                auction_player_id = active_bidders[bidder_idx]

                legal_actions = get_legal_actions(game, auction_player_id)

                if legal_actions:
                    auction_agent = agents[auction_player_id]
                    action = auction_agent.choose_action(game, legal_actions)
                    if action:
                        old_pos = game.players[auction_player_id].position
                        success = apply_action(game, action, player_id=auction_player_id)
                        if success:
                            log_action_effects(game, action, auction_player_id, logger, old_pos)
                        actions_this_turn += 1

                        # Move to next bidder
                        auction_bidder_rotation[auction_id] += 1

                        # Clean up if auction completed
                        if not game.active_auction:
                            if auction_id in auction_bidder_rotation:
                                del auction_bidder_rotation[auction_id]

                        continue
                else:
                    # No legal actions, force pass
                    game.active_auction.pass_turn(auction_player_id)
                    auction_bidder_rotation[auction_id] += 1
                    continue

            # Normal turn flow
            legal_actions = get_legal_actions(game, current_player.player_id)

            if not legal_actions:
                # No legal actions available - force end turn to prevent infinite loop
                if verbose:
                    print(f"  WARNING: No legal actions for Player {current_player.player_id}, forcing end turn")
                game.end_turn()
                break

            # Agent chooses action
            action = agent.choose_action(game, legal_actions)

            if action is None:
                break

            # Track position before action for movement logging
            old_position = current_player.position

            # Apply action
            success = apply_action(game, action)
            if success:
                log_action_effects(game, action, current_player.player_id, logger, old_position)

            # Check for new events from internal event log after action
            # Transfer events from internal event_log to JSONL logger
            current_event_log_size = len(game.event_log.events)
            if current_event_log_size > last_event_log_size:
                for event in game.event_log.events[last_event_log_size:]:
                    event_type = event.event_type.value

                    if event_type == 'auction_start':
                        details = event.details.get('details', event.details)
                        property_name = details.get('property')
                        position = details.get('position')
                        eligible_players = details.get('players', [])
                        logger.log_auction_start(property_name, position, eligible_players)

                    elif event_type == 'auction_pass':
                        details = event.details.get('details', event.details)
                        property_name = details.get('property')
                        remaining_bidders = details.get('remaining_bidders', [])
                        player = game.players[event.player_id]
                        logger.log_event('auction_pass',
                                       player_id=event.player_id,
                                       player_name=player.name,
                                       property_name=property_name,
                                       remaining_bidders=remaining_bidders,
                                       remaining_count=len(remaining_bidders))

                    elif event_type == 'land':
                        position = event.details.get('position')
                        space_name = event.details.get('space')
                        logger.log_event('land', player_id=event.player_id,
                                       player_name=game.players[event.player_id].name,
                                       position=position, space_name=space_name)

                    elif event_type == 'card_draw':
                        details = event.details.get('details', event.details)
                        deck = details.get('deck')
                        card_desc = details.get('card')
                        logger.log_event('card_draw', player_id=event.player_id,
                                       player_name=game.players[event.player_id].name,
                                       deck=deck, card=card_desc)

                    elif event_type == 'card_effect':
                        details = event.details.get('details', event.details)
                        card_desc = details.get('card')
                        effect_type = details.get('type')
                        cash_before = details.get('cash_before')
                        cash_after = details.get('cash_after')
                        amount = details.get('amount')

                        logger.log_event('card_effect', player_id=event.player_id,
                                       player_name=game.players[event.player_id].name,
                                       card=card_desc, effect_type=effect_type,
                                       cash_before=cash_before, cash_after=cash_after,
                                       amount=amount)

                    elif event_type == 'rent_payment':
                        payer_id = event.player_id
                        details = event.details.get('details', event.details)
                        owner_id = details.get('owner')
                        amount = details.get('amount')

                        if payer_id is not None and owner_id is not None:
                            payer = game.players[payer_id]
                            owner = game.players[owner_id]
                            # Get property name from payer's position
                            space = game.board.get_space(payer.position)
                            logger.log_rent_payment(
                                payer_id, payer.name,
                                owner_id, owner.name,
                                space.name, amount,
                                payer.cash, owner.cash
                            )

                    elif event_type == 'trade_proposed':
                        details = event.details.get('details', event.details)
                        trade_id = details.get('trade_id')
                        proposer_id = details.get('proposer_id')
                        recipient_id = details.get('recipient_id')
                        proposer_offers = details.get('proposer_offers', [])
                        proposer_wants = details.get('proposer_wants', [])

                        if proposer_id is not None and recipient_id is not None:
                            proposer = game.players[proposer_id]
                            recipient = game.players[recipient_id]
                            logger.log_trade_proposed(
                                trade_id, proposer_id, proposer.name,
                                recipient_id, recipient.name,
                                proposer_offers, proposer_wants
                            )

                    elif event_type == 'trade_accepted':
                        details = event.details.get('details', event.details)
                        trade_id = details.get('trade_id')
                        if event.player_id is not None:
                            player = game.players[event.player_id]
                            logger.log_trade_accepted(trade_id, event.player_id, player.name)

                    elif event_type == 'trade_rejected':
                        details = event.details.get('details', event.details)
                        trade_id = details.get('trade_id')
                        if event.player_id is not None:
                            player = game.players[event.player_id]
                            logger.log_trade_rejected(trade_id, event.player_id, player.name)

                    elif event_type == 'trade_cancelled':
                        details = event.details.get('details', event.details)
                        trade_id = details.get('trade_id')
                        if event.player_id is not None:
                            player = game.players[event.player_id]
                            logger.log_trade_cancelled(trade_id, event.player_id, player.name)

                    elif event_type == 'trade_executed':
                        details = event.details.get('details', event.details)
                        trade_id = details.get('trade_id')
                        proposer_id = details.get('proposer_id')
                        recipient_id = details.get('recipient_id')
                        proposer_offers = details.get('proposer_offers', [])
                        proposer_wants = details.get('proposer_wants', [])

                        if proposer_id is not None and recipient_id is not None:
                            proposer = game.players[proposer_id]
                            recipient = game.players[recipient_id]
                            logger.log_trade_executed(
                                trade_id, proposer_id, proposer.name,
                                recipient_id, recipient.name,
                                proposer_offers, proposer_wants,
                                proposer.cash, recipient.cash
                            )

                last_event_log_size = current_event_log_size

            actions_this_turn += 1

            if verbose and action.action_type in [
                ActionType.BUY_PROPERTY,
                ActionType.BUILD_HOUSE,
                ActionType.BUILD_HOTEL,
            ]:
                print(f"  {agent.name}: {action.action_type.value}")

            # End turn check
            if action.action_type == ActionType.END_TURN:
                break

            # Check if current player changed (bankruptcy, etc)
            if game.get_current_player().player_id != current_player.player_id:
                break

        if actions_this_turn >= max_actions_per_turn:
            # Force end turn if stuck
            if verbose:
                print(f"  WARNING: Player {current_player.player_id} hit action limit, forcing end turn")
            game.end_turn()

    # Check if we hit the safety limit
    if iteration_count >= max_iterations:
        print(f"\n!!! SAFETY LIMIT HIT ({max_iterations} iterations) !!!")
        print(f"Game may have an infinite loop bug.")
        print(f"Game state: turn={game.turn_number}, game_over={game.game_over}")

    # Log game end
    final_standings = []
    for player_id, player in sorted(game.players.items()):
        worth = game._calculate_net_worth(player_id)
        final_standings.append({
            "player_id": player_id,
            "player_name": player.name,
            "net_worth": worth,
            "is_bankrupt": player.is_bankrupt
        })

    reason = "time_limit" if max_turns and game.turn_number >= max_turns else "bankruptcy"
    winner_name = game.players[game.winner].name if game.winner is not None else None
    logger.log_game_end(game.turn_number, game.winner, winner_name, reason, final_standings)

    if verbose:
        print_game_summary(game)
        print(f"\nGame logged to: {logger.log_file}")

    return game


def main():
    """Main entry point for CLI."""
    parser = argparse.ArgumentParser(description="Simulate a Monopoly game")
    parser.add_argument(
        "--players",
        type=int,
        default=4,
        choices=range(2, 9),
        help="Number of players (2-8)",
    )
    parser.add_argument(
        "--agent",
        type=str,
        default="greedy",
        choices=["random", "greedy"],
        help="AI agent type",
    )
    parser.add_argument("--seed", type=int, default=None, help="Random seed")
    parser.add_argument("--quiet", action="store_true", help="Reduce output verbosity")
    parser.add_argument(
        "--max-turns",
        type=int,
        default=None,
        help="Maximum number of turns (time limit variant)",
    )
    parser.add_argument(
        "--log-file",
        type=str,
        default=None,
        help="Path to JSONL log file (default: auto-generated timestamp)",
    )

    args = parser.parse_args()

    simulate_game(
        num_players=args.players,
        agent_type=args.agent,
        seed=args.seed,
        verbose=not args.quiet,
        max_turns=args.max_turns,
        log_file=args.log_file,
    )


if __name__ == "__main__":
    main()

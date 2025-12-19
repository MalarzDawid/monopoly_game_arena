"""
High-level rules API for controlling game flow.
This module provides the public interface for game actions and legal move detection.
"""

from typing import Dict, List, Optional, Any
from monopoly.game import GameState, ActionType
from monopoly.spaces import SpaceType
from monopoly.player import PlayerState
from monopoly.money import EventType


class Action:
    """Represents a game action that can be taken."""

    def __init__(self, action_type: ActionType, **params: Any):
        self.action_type = action_type
        self.params = params

    def __repr__(self) -> str:
        return f"Action({self.action_type.value}, {self.params})"


def get_legal_actions(game_state: GameState, player_id: int) -> List[Action]:
    """
    Get all legal actions available to a player.

    This is the main interface for AI/controllers to determine valid moves.

    Args:
        game_state: Current game state
        player_id: Player to get actions for

    Returns:
        List of legal Action objects
    """
    if game_state.game_over:
        return []

    player = game_state.players[player_id]
    actions: List[Action] = []

    # Handle auction state - IMPORTANT: Check this BEFORE current player check
    # because during auctions, any active bidder can take actions
    if game_state.active_auction is not None:
        auction = game_state.active_auction
        if player_id in auction.active_bidders:
            # Can bid any amount higher than current bid
            actions.append(Action(ActionType.BID))
            actions.append(Action(ActionType.PASS_AUCTION))
            return actions
        # If player has already passed but auction is still active,
        # they must wait for auction to complete
        if not auction.is_complete:
            # No actions available - wait for other players
            return actions
        # Auction completed, fallthrough to normal actions

    # For non-auction actions, must be current player's turn
    current_player = game_state.get_current_player()
    if current_player.player_id != player_id:
        # Not this player's turn
        return []

    # Handle jail
    if player.in_jail:
        if player.jail_turns < game_state.config.max_jail_turns:
            actions.append(Action(ActionType.ROLL_DICE))  # Attempt to roll doubles

        if player.cash >= game_state.config.jail_fine:
            actions.append(Action(ActionType.PAY_JAIL_FINE))

        if player.get_out_of_jail_cards > 0:
            actions.append(Action(ActionType.USE_JAIL_CARD))

        # If no other options and insufficient cash, must declare bankruptcy
        if not actions and player.cash < game_state.config.jail_fine:
            actions.append(Action(ActionType.DECLARE_BANKRUPTCY))

        return actions

    # Handle pending rent payment (player needs to raise funds or go bankrupt)
    if game_state.pending_rent_payment is not None:
        payer_id, owner_id, amount_owed = game_state.pending_rent_payment
        if payer_id == player_id:
            # Player must raise funds or declare bankruptcy
            actions.extend(_get_property_management_actions(game_state, player_id))

            # Always allow bankruptcy as an option
            actions.append(Action(ActionType.DECLARE_BANKRUPTCY, creditor_id=owner_id))

            return actions

    # Handle pending tax payment (player needs to raise funds or go bankrupt)
    if game_state.pending_tax_payment is not None:
        payer_id, amount_owed = game_state.pending_tax_payment
        if payer_id == player_id:
            # Player must raise funds or declare bankruptcy
            actions.extend(_get_property_management_actions(game_state, player_id))

            # Always allow bankruptcy as an option (to the bank, no creditor)
            actions.append(Action(ActionType.DECLARE_BANKRUPTCY))

            return actions

    # After rolling, check current position for purchase opportunities
    # This must be checked BEFORE allowing another dice roll (even with doubles)
    space = game_state.board.get_space(player.position)

    # If landed on purchasable property that's unowned
    if space.space_type in (SpaceType.PROPERTY, SpaceType.RAILROAD, SpaceType.UTILITY):
        ownership = game_state.property_ownership.get(player.position)
        if ownership and not ownership.is_owned():
            # Can buy or decline (which triggers auction)
            # MUST decide before rolling again, even with doubles
            if space.space_type == SpaceType.PROPERTY:
                price = space.price
            elif space.space_type == SpaceType.RAILROAD:
                price = space.price
            elif space.space_type == SpaceType.UTILITY:
                price = space.price

            if player.cash >= price:
                actions.append(Action(ActionType.BUY_PROPERTY, position=player.position))

            actions.append(Action(ActionType.DECLINE_PURCHASE, position=player.position))
            return actions

    # Normal turn flow - can roll if pending
    if game_state.pending_dice_roll:
        actions.append(Action(ActionType.ROLL_DICE))
        # Can also do property management before rolling
        actions.extend(_get_property_management_actions(game_state, player_id))
        return actions

    # Can always end turn (after dice roll)
    if not game_state.pending_dice_roll:
        actions.append(Action(ActionType.END_TURN))

    # Trade actions - can propose trades or respond to pending trades
    actions.extend(_get_trade_actions(game_state, player_id))

    # If player has insufficient funds for something, allow bankruptcy
    if player.cash < 0:
        actions.append(Action(ActionType.DECLARE_BANKRUPTCY))

    return actions


def _get_property_management_actions(game_state: GameState, player_id: int) -> List[Action]:
    """Get actions related to building, mortgaging, etc."""
    actions: List[Action] = []
    player = game_state.players[player_id]

    for position in player.properties:
        # Building
        if game_state.can_build_house(player_id, position):
            actions.append(Action(ActionType.BUILD_HOUSE, position=position))

        if game_state.can_build_hotel(player_id, position):
            actions.append(Action(ActionType.BUILD_HOTEL, position=position))

        # Selling buildings
        ownership = game_state.property_ownership[position]
        if ownership.houses > 0:
            space = game_state.board.get_property_space(position)
            if space and game_state._can_sell_evenly(position, space.color_group):
                actions.append(Action(ActionType.SELL_BUILDING, position=position))

        # Mortgaging
        if ownership.houses == 0 and not ownership.is_mortgaged:
            actions.append(Action(ActionType.MORTGAGE_PROPERTY, position=position))

        # Unmortgaging
        if ownership.is_mortgaged:
            space = game_state.board.get_space(position)
            mortgage_value = 0
            if hasattr(space, "mortgage_value"):
                mortgage_value = space.mortgage_value
            cost = int(mortgage_value * (1 + game_state.config.mortgage_interest_rate))

            if player.cash >= cost:
                actions.append(Action(ActionType.UNMORTGAGE_PROPERTY, position=position))

    return actions


def _get_trade_actions(game_state: GameState, player_id: int) -> List[Action]:
    """Get available trade actions for a player."""
    actions: List[Action] = []
    player = game_state.players[player_id]

    if player.is_bankrupt:
        return actions

    # Check for pending trade offers where this player is the recipient
    active_trades = game_state.trade_manager.get_active_trades_for_player(player_id)
    for trade in active_trades:
        if trade.recipient_id == player_id and trade.status == "pending":
            # Can accept or reject trades offered to us
            actions.append(Action(ActionType.ACCEPT_TRADE, trade_id=trade.trade_id))
            actions.append(Action(ActionType.REJECT_TRADE, trade_id=trade.trade_id))
        elif trade.proposer_id == player_id and trade.status == "pending":
            # Can cancel our own pending trades
            actions.append(Action(ActionType.CANCEL_TRADE, trade_id=trade.trade_id))

    # Can always propose a new trade to any other non-bankrupt player
    # Note: The actual trade details (what to offer/want) would be determined by the agent
    # We just signal that PROPOSE_TRADE is available
    for other_id, other_player in game_state.players.items():
        if other_id != player_id and not other_player.is_bankrupt:
            # Add a PROPOSE_TRADE action (agent will fill in the details)
            actions.append(Action(ActionType.PROPOSE_TRADE, recipient_id=other_id))

    return actions


def apply_action(game_state: GameState, action: Action, player_id: Optional[int] = None) -> bool:
    """
    Apply an action to the game state.

    This is the main interface for executing moves.

    Args:
        game_state: Current game state
        action: Action to apply
        player_id: Player executing the action (optional, defaults to current player)

    Returns:
        True if action was successful, False otherwise
    """
    if player_id is None:
        player_id = game_state.current_player_index
    current_player = game_state.players[player_id]

    if action.action_type == ActionType.ROLL_DICE:
        if current_player.in_jail:
            # Attempt to get out of jail by rolling doubles
            # Note: attempt_jail_release now handles movement if successful
            released = game_state.attempt_jail_release(current_player.player_id)
            if released:
                # Player rolled doubles and got out, already moved by attempt_jail_release
                # Resolve landing on new position
                _resolve_landing(game_state, current_player.player_id, current_player.position)
                # After getting out and moving, can end turn
                game_state.pending_dice_roll = False
            else:
                # Failed to get out, turn ends
                game_state.end_turn()
            return True

        # Normal roll (not in jail)
        die1, die2 = game_state.roll_dice()
        is_doubles = die1 == die2

        # Move player
        total = die1 + die2
        new_position = game_state.move_player(current_player.player_id, total)

        # Handle doubles
        if is_doubles:
            current_player.consecutive_doubles += 1
            if current_player.consecutive_doubles >= 3:
                # Three doubles -> jail
                game_state.send_to_jail(current_player.player_id)
                game_state.end_turn()
                return True
            else:
                # Get another turn
                game_state.pending_dice_roll = True
        else:
            current_player.consecutive_doubles = 0

        # Resolve landing
        _resolve_landing(game_state, current_player.player_id, new_position)

        return True

    elif action.action_type == ActionType.BUY_PROPERTY:
        position = action.params.get("position", current_player.position)
        success = game_state.buy_property(current_player.player_id, position)
        if success and not game_state.pending_dice_roll:
            # After buying, can end turn or do more actions
            pass
        return success

    elif action.action_type == ActionType.DECLINE_PURCHASE:
        position = action.params.get("position", current_player.position)
        # Start auction - note: auction will run via BID/PASS_AUCTION actions
        # The auction remains active and players will bid/pass through separate actions
        # Once complete, the original player can end their turn
        # The current player (initiator) automatically places a 10% starting bid
        game_state.start_auction(position, initiator_id=current_player.player_id)
        return True

    elif action.action_type == ActionType.BID:
        if game_state.active_auction:
            amount = action.params.get("amount", 0)
            success = game_state.active_auction.place_bid(current_player.player_id, amount)
            # Check if this bid completed the auction (shouldn't normally happen from a bid)
            _check_and_complete_auction(game_state)
            return success
        return False

    elif action.action_type == ActionType.PASS_AUCTION:
        if game_state.active_auction:
            game_state.active_auction.pass_turn(current_player.player_id)
            # Check if auction is now complete and handle cleanup
            _check_and_complete_auction(game_state)
            return True
        return False

    elif action.action_type == ActionType.BUILD_HOUSE:
        position = action.params.get("position")
        return game_state.build_house(current_player.player_id, position)

    elif action.action_type == ActionType.BUILD_HOTEL:
        position = action.params.get("position")
        return game_state.build_hotel(current_player.player_id, position)

    elif action.action_type == ActionType.SELL_BUILDING:
        position = action.params.get("position")
        success = game_state.sell_building(current_player.player_id, position)
        # Check if pending rent can now be paid
        _try_resolve_pending_payment(game_state)
        return success

    elif action.action_type == ActionType.MORTGAGE_PROPERTY:
        position = action.params.get("position")
        success = game_state.mortgage_property(current_player.player_id, position)
        # Check if pending rent can now be paid
        _try_resolve_pending_payment(game_state)
        return success

    elif action.action_type == ActionType.UNMORTGAGE_PROPERTY:
        position = action.params.get("position")
        return game_state.unmortgage_property(current_player.player_id, position)

    elif action.action_type == ActionType.PAY_JAIL_FINE:
        return game_state.pay_jail_fine(current_player.player_id)

    elif action.action_type == ActionType.USE_JAIL_CARD:
        success = game_state.use_jail_card(current_player.player_id)
        if success:
            game_state.pending_dice_roll = True
        return success

    elif action.action_type == ActionType.END_TURN:
        game_state.end_turn()
        return True

    elif action.action_type == ActionType.PROPOSE_TRADE:
        # Propose a trade to another player
        recipient_id = action.params.get("recipient_id")
        proposer_offers = action.params.get("proposer_offers", [])
        proposer_wants = action.params.get("proposer_wants", [])

        if recipient_id is None:
            return False

        trade = game_state.trade_manager.create_trade(
            proposer_id=current_player.player_id,
            recipient_id=recipient_id,
            proposer_offers=proposer_offers,
            proposer_wants=proposer_wants,
            current_turn=game_state.turn_number
        )

        # Validate trade
        is_valid, error_msg = game_state.validate_trade(trade)
        if not is_valid:
            # Cancel invalid trade immediately
            game_state.trade_manager.cancel_trade(trade.trade_id)
            game_state.event_log.log(
                EventType.TRADE_FAILED,
                player_id=current_player.player_id,
                details={"trade_id": trade.trade_id, "reason": error_msg}
            )
            return False

        game_state.event_log.log(
            EventType.TRADE_PROPOSED,
            player_id=current_player.player_id,
            details={
                "trade_id": trade.trade_id,
                "proposer_id": trade.proposer_id,
                "recipient_id": trade.recipient_id,
                "proposer_offers": [str(item) for item in trade.proposer_offers],
                "proposer_wants": [str(item) for item in trade.proposer_wants]
            }
        )
        return True

    elif action.action_type == ActionType.ACCEPT_TRADE:
        trade_id = action.params.get("trade_id")
        if trade_id is None:
            return False

        trade = game_state.trade_manager.get_trade(trade_id)
        if not trade or trade.status != "pending":
            return False

        # Only recipient can accept
        if trade.recipient_id != current_player.player_id:
            return False

        # Execute trade
        success = game_state.execute_trade(trade)
        if success:
            game_state.trade_manager.accept_trade(trade_id)
            game_state.event_log.log(
                EventType.TRADE_ACCEPTED,
                player_id=current_player.player_id,
                details={"trade_id": trade_id}
            )
        return success

    elif action.action_type == ActionType.REJECT_TRADE:
        trade_id = action.params.get("trade_id")
        if trade_id is None:
            return False

        trade = game_state.trade_manager.get_trade(trade_id)
        if not trade or trade.status != "pending":
            return False

        # Only recipient can reject
        if trade.recipient_id != current_player.player_id:
            return False

        game_state.trade_manager.reject_trade(trade_id)
        game_state.event_log.log(
            EventType.TRADE_REJECTED,
            player_id=current_player.player_id,
            details={"trade_id": trade_id}
        )
        return True

    elif action.action_type == ActionType.CANCEL_TRADE:
        trade_id = action.params.get("trade_id")
        if trade_id is None:
            return False

        trade = game_state.trade_manager.get_trade(trade_id)
        if not trade or trade.status != "pending":
            return False

        # Only proposer can cancel
        if trade.proposer_id != current_player.player_id:
            return False

        game_state.trade_manager.cancel_trade(trade_id)
        game_state.event_log.log(
            EventType.TRADE_CANCELLED,
            player_id=current_player.player_id,
            details={"trade_id": trade_id}
        )
        return True

    elif action.action_type == ActionType.DECLARE_BANKRUPTCY:
        creditor_id = action.params.get("creditor_id")
        game_state.declare_bankruptcy(current_player.player_id, creditor_id)
        # Clear any pending payments
        game_state.pending_rent_payment = None
        game_state.pending_tax_payment = None
        if not game_state.game_over:
            game_state.end_turn()
        return True

    return False


def _check_and_complete_auction(game_state: GameState) -> None:
    """Check if auction is complete and handle cleanup."""
    if game_state.active_auction and game_state.active_auction.is_complete:
        winner = game_state.active_auction.get_winner()
        if winner is not None:
            position = game_state.active_auction.property_position
            winning_bid = game_state.active_auction.get_winning_bid()

            # Execute purchase
            winner_player = game_state.players[winner]
            winner_player.cash -= winning_bid
            winner_player.properties.add(position)
            game_state.property_ownership[position].owner_id = winner

        game_state.active_auction = None
        # After auction completes, allow turn to end
        game_state.pending_dice_roll = False


def _try_resolve_pending_payment(game_state: GameState) -> bool:
    """
    Try to resolve pending payment (rent or tax) if one exists.
    Returns True if payment was resolved, False otherwise.
    """
    # Try to resolve pending rent
    if game_state.pending_rent_payment is not None:
        payer_id, owner_id, amount = game_state.pending_rent_payment
        payer = game_state.players[payer_id]

        if payer.cash >= amount:
            success = game_state.pay_rent(payer_id, owner_id, amount)
            if success:
                return True

    # Try to resolve pending tax
    if game_state.pending_tax_payment is not None:
        payer_id, amount = game_state.pending_tax_payment
        payer = game_state.players[payer_id]

        if payer.cash >= amount:
            success = game_state.pay_tax(payer_id, amount)
            if success:
                return True

    return False


def _resolve_landing(game_state: GameState, player_id: int, position: int) -> None:
    """
    Resolve the effects of landing on a space.

    This handles automatic effects like taxes, cards, going to jail, etc.
    """
    space = game_state.board.get_space(position)

    from monopoly.money import EventType

    game_state.event_log.log(
        EventType.LAND,
        player_id=player_id,
        position=position,
        space=space.name,
    )

    # GO
    if space.space_type == SpaceType.GO:
        # Already collected salary if passed
        pass

    # Property/Railroad/Utility - check for rent
    elif space.space_type in (SpaceType.PROPERTY, SpaceType.RAILROAD, SpaceType.UTILITY):
        ownership = game_state.property_ownership[position]
        if ownership.is_owned() and ownership.owner_id != player_id:
            rent = game_state.calculate_rent(position)
            game_state.pay_rent(player_id, ownership.owner_id, rent)

    # Tax
    elif space.space_type == SpaceType.TAX:
        game_state.pay_tax(player_id, space.amount)

    # Chance
    elif space.space_type == SpaceType.CHANCE:
        game_state.draw_card("chance")  # Card is executed inside draw_card

    # Community Chest
    elif space.space_type == SpaceType.COMMUNITY_CHEST:
        game_state.draw_card("community_chest")  # Card is executed inside draw_card

    # Go To Jail
    elif space.space_type == SpaceType.GO_TO_JAIL:
        game_state.send_to_jail(player_id)

    # Jail (Just Visiting)
    elif space.space_type == SpaceType.JAIL:
        pass  # Just visiting

    # Free Parking
    elif space.space_type == SpaceType.FREE_PARKING:
        pass  # No effect in standard rules


def step_turn(game_state: GameState) -> List[Action]:
    """
    Automatically step through turn for the current player.
    This is a convenience function for simple AI/automated play.

    Returns:
        List of actions that were taken
    """
    actions_taken: List[Action] = []
    current_player = game_state.get_current_player()

    # Simple greedy strategy: roll, buy if possible, end turn
    legal_actions = get_legal_actions(game_state, current_player.player_id)

    while legal_actions and not game_state.game_over:
        # Priority: roll dice > buy property > end turn
        action = None

        for a in legal_actions:
            if a.action_type == ActionType.ROLL_DICE:
                action = a
                break

        if not action:
            for a in legal_actions:
                if a.action_type == ActionType.BUY_PROPERTY:
                    action = a
                    break

        if not action:
            for a in legal_actions:
                if a.action_type == ActionType.END_TURN:
                    action = a
                    break

        if not action and legal_actions:
            action = legal_actions[0]

        if action:
            apply_action(game_state, action)
            actions_taken.append(action)

            if action.action_type == ActionType.END_TURN:
                break

        legal_actions = get_legal_actions(game_state, current_player.player_id)

    return actions_taken

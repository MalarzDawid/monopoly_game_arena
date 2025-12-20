"""Greedy agent that prefers buying properties and building."""

import random
from typing import List

from src.core.game.game import ActionType, GameState
from src.core.game.rules import Action

from src.core.agents.base import Agent


class GreedyAgent(Agent):
    """
    Simple AI that prefers buying properties and building when possible.

    Will occasionally decline expensive purchases to trigger auctions,
    based on the ratio of property price to available cash.
    """

    def __init__(self, player_id: int, name: str):
        """
        Initialize the greedy agent.

        Args:
            player_id: The player's index in the game.
            name: The player's display name.
        """
        super().__init__(player_id, name)
        self.rng = random.Random(player_id)  # Deterministic based on player_id

    def choose_action(self, game: GameState, legal_actions: List[Action]) -> Action:
        """
        Choose action with simple greedy strategy.

        Priority order:
        1. Buy properties (unless too expensive)
        2. Build hotels/houses
        3. Roll dice
        4. End turn

        Args:
            game: The current game state.
            legal_actions: List of legal actions available to the player.

        Returns:
            The chosen action to execute.
        """
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
            position = buy_action.params.get("position", player.position)
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

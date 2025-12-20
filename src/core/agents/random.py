"""Random agent that makes random legal moves."""

import random
from typing import List

from core.game.game import ActionType, GameState
from core.game.rules import Action

from core.agents.base import Agent


class RandomAgent(Agent):
    """
    Simple AI that makes random legal moves.

    Prioritizes ROLL_DICE and END_TURN actions to keep the game moving
    and avoid infinite loops.
    """

    def __init__(self, player_id: int, name: str):
        """
        Initialize the random agent.

        Args:
            player_id: The player's index in the game.
            name: The player's display name.
        """
        super().__init__(player_id, name)
        self.rng = random.Random()

    def choose_action(self, game: GameState, legal_actions: List[Action]) -> Action:
        """
        Choose a random legal action with basic priorities.

        Prioritizes ROLL_DICE and END_TURN to keep the game moving.

        Args:
            game: The current game state.
            legal_actions: List of legal actions available to the player.

        Returns:
            The chosen action to execute.
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

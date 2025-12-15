"""LLM-powered agent for Monopoly."""

from typing import List

from monopoly.game import GameState
from monopoly.rules import Action

from .base import Agent


class LLMAgent(Agent):
    """
    LLM-powered agent that uses a language model to make decisions.

    This agent will query an LLM with the current game state and legal actions,
    then parse the response to select an action.

    Note:
        This is a stub implementation. The actual LLM integration
        will be implemented in a future version.
    """

    def __init__(self, player_id: int, name: str, model_name: str = "gpt-4"):
        """
        Initialize the LLM agent.

        Args:
            player_id: The player's index in the game.
            name: The player's display name.
            model_name: The LLM model to use for decision making.
        """
        super().__init__(player_id, name)
        self.model_name = model_name

    def choose_action(self, game: GameState, legal_actions: List[Action]) -> Action:
        """
        Choose an action using LLM reasoning.

        Args:
            game: The current game state.
            legal_actions: List of legal actions available to the player.

        Returns:
            The chosen action to execute.

        Raises:
            NotImplementedError: LLM integration is not yet implemented.
        """
        raise NotImplementedError(
            "LLMAgent is not yet implemented. "
            "This stub will be replaced with actual LLM integration."
        )

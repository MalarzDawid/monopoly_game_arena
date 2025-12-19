"""Base class for all Monopoly agents."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from src.core.game.game import GameState
    from src.core.game.rules import Action


class Agent(ABC):
    """
    Abstract base class for Monopoly agents.

    All agents must implement the `choose_action` method to select
    an action from the list of legal actions.

    Attributes:
        player_id: The player's index in the game (0, 1, 2, ...).
        name: The player's display name.
    """

    def __init__(self, player_id: int, name: str):
        """
        Initialize the agent.

        Args:
            player_id: The player's index in the game.
            name: The player's display name.
        """
        self.player_id = player_id
        self.name = name

    @abstractmethod
    def choose_action(self, game: "GameState", legal_actions: List["Action"]) -> "Action":
        """
        Choose an action from the list of legal actions.

        Args:
            game: The current game state.
            legal_actions: List of legal actions available to the player.

        Returns:
            The chosen action to execute.
        """
        pass

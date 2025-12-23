"""
Player state and management.
"""

from dataclasses import dataclass, field
from typing import Optional


class PlayerState:
    """Represents the complete state of a player in the game."""

    def __init__(self, player_id: int, name: str, starting_cash: int):
        self.player_id = player_id
        self.name = name
        self.cash = starting_cash
        self.position = 0
        self.in_jail = False
        self.jail_turns = 0
        self.get_out_of_jail_cards = 0
        self.is_bankrupt = False
        self.properties: set[int] = set()
        self.consecutive_doubles = 0

    def __repr__(self) -> str:
        return (
            f"PlayerState(id={self.player_id}, name='{self.name}', "
            f"cash={self.cash}, position={self.position}, bankrupt={self.is_bankrupt})"
        )


@dataclass
class PropertyOwnership:
    """Tracks ownership state of a property."""

    owner_id: Optional[int] = None
    houses: int = 0
    is_mortgaged: bool = False

    def is_owned(self) -> bool:
        """Check if property is owned by any player."""
        return self.owner_id is not None

    def has_hotel(self) -> bool:
        """Check if property has a hotel (represented as 5 houses)."""
        return self.houses == 5


class Player:
    """
    Convenience wrapper for player information.
    This is primarily for the external API.
    """

    def __init__(self, player_id: int, name: str):
        self.player_id = player_id
        self.name = name

    def __repr__(self) -> str:
        return f"Player(id={self.player_id}, name='{self.name}')"

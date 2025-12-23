"""
Game configuration settings.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class GameConfig:
    """Configuration for a Monopoly game."""

    starting_cash: int = 1500
    go_salary: int = 200
    jail_fine: int = 50
    mortgage_interest_rate: float = 0.10

    house_limit: int = 32
    hotel_limit: int = 12

    max_jail_turns: int = 3

    short_game: bool = False
    time_limit_turns: Optional[int] = None

    seed: Optional[int] = None

    allow_free_parking_jackpot: bool = False


@dataclass
class PropertyData:
    """Data for a property space."""

    name: str
    position: int
    price: int
    color_group: Optional[str]
    rent_base: int
    rent_with_1: int = 0
    rent_with_2: int = 0
    rent_with_3: int = 0
    rent_with_4: int = 0
    rent_hotel: int = 0
    house_cost: int = 0
    mortgage_value: int = 0

    def __post_init__(self) -> None:
        if self.mortgage_value == 0:
            self.mortgage_value = self.price // 2


@dataclass
class RailroadData:
    """Data for a railroad space."""

    name: str
    position: int
    price: int = 200
    mortgage_value: int = 100

    def get_rent(self, railroads_owned: int) -> int:
        """Calculate rent based on number of railroads owned."""
        return 25 * (2 ** (railroads_owned - 1))


@dataclass
class UtilityData:
    """Data for a utility space."""

    name: str
    position: int
    price: int = 150
    mortgage_value: int = 75

    def get_rent(self, dice_roll: int, utilities_owned: int) -> int:
        """Calculate rent based on dice roll and utilities owned."""
        multiplier = 4 if utilities_owned == 1 else 10
        return dice_roll * multiplier


@dataclass
class TaxData:
    """Data for a tax space."""

    name: str
    position: int
    amount: int

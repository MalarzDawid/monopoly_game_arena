"""
Board space definitions and types.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class SpaceType(Enum):
    """Types of spaces on the board."""

    GO = "go"
    PROPERTY = "property"
    RAILROAD = "railroad"
    UTILITY = "utility"
    TAX = "tax"
    CHANCE = "chance"
    COMMUNITY_CHEST = "community_chest"
    JAIL = "jail"
    GO_TO_JAIL = "go_to_jail"
    FREE_PARKING = "free_parking"


@dataclass
class Space:
    """Base class for a board space."""

    name: str
    position: int
    space_type: SpaceType

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}', position={self.position})"


@dataclass
class GoSpace(Space):
    """The GO space."""

    def __init__(self, position: int = 0):
        super().__init__("GO", position, SpaceType.GO)


@dataclass
class PropertySpace(Space):
    """A property that can be owned, built upon, and mortgaged."""

    price: int
    color_group: str
    rent_base: int
    rent_with_1: int
    rent_with_2: int
    rent_with_3: int
    rent_with_4: int
    rent_hotel: int
    house_cost: int
    mortgage_value: int

    def __init__(
        self,
        name: str,
        position: int,
        price: int,
        color_group: str,
        rent_base: int,
        rent_with_1: int,
        rent_with_2: int,
        rent_with_3: int,
        rent_with_4: int,
        rent_hotel: int,
        house_cost: int,
        mortgage_value: int,
    ):
        super().__init__(name, position, SpaceType.PROPERTY)
        self.price = price
        self.color_group = color_group
        self.rent_base = rent_base
        self.rent_with_1 = rent_with_1
        self.rent_with_2 = rent_with_2
        self.rent_with_3 = rent_with_3
        self.rent_with_4 = rent_with_4
        self.rent_hotel = rent_hotel
        self.house_cost = house_cost
        self.mortgage_value = mortgage_value

    def get_rent(self, houses: int, has_monopoly: bool) -> int:
        """
        Calculate rent for this property.

        Args:
            houses: Number of houses (0-4) or 5 for hotel
            has_monopoly: Whether owner has complete color set

        Returns:
            Rent amount
        """
        if houses == 0:
            return self.rent_base * 2 if has_monopoly else self.rent_base
        elif houses == 1:
            return self.rent_with_1
        elif houses == 2:
            return self.rent_with_2
        elif houses == 3:
            return self.rent_with_3
        elif houses == 4:
            return self.rent_with_4
        else:  # houses == 5 (hotel)
            return self.rent_hotel


@dataclass
class RailroadSpace(Space):
    """A railroad space."""

    price: int
    mortgage_value: int

    def __init__(self, name: str, position: int, price: int = 200, mortgage_value: int = 100):
        super().__init__(name, position, SpaceType.RAILROAD)
        self.price = price
        self.mortgage_value = mortgage_value

    def get_rent(self, railroads_owned: int) -> int:
        """Calculate rent based on number of railroads owned by the owner."""
        return 25 * (2 ** (railroads_owned - 1))


@dataclass
class UtilitySpace(Space):
    """A utility space (Electric Company or Water Works)."""

    price: int
    mortgage_value: int

    def __init__(self, name: str, position: int, price: int = 150, mortgage_value: int = 75):
        super().__init__(name, position, SpaceType.UTILITY)
        self.price = price
        self.mortgage_value = mortgage_value

    def get_rent(self, dice_roll: int, utilities_owned: int) -> int:
        """Calculate rent based on dice roll and number of utilities owned."""
        multiplier = 4 if utilities_owned == 1 else 10
        return dice_roll * multiplier


@dataclass
class TaxSpace(Space):
    """A tax space (Income Tax or Luxury Tax)."""

    amount: int
    has_choice: bool = False

    def __init__(self, name: str, position: int, amount: int, has_choice: bool = False):
        super().__init__(name, position, SpaceType.TAX)
        self.amount = amount
        self.has_choice = has_choice


@dataclass
class ChanceSpace(Space):
    """A Chance card space."""

    def __init__(self, position: int):
        super().__init__("Chance", position, SpaceType.CHANCE)


@dataclass
class CommunityChestSpace(Space):
    """A Community Chest card space."""

    def __init__(self, position: int):
        super().__init__("Community Chest", position, SpaceType.COMMUNITY_CHEST)


@dataclass
class JailSpace(Space):
    """The Jail/Just Visiting space."""

    def __init__(self, position: int = 10):
        super().__init__("Jail", position, SpaceType.JAIL)


@dataclass
class GoToJailSpace(Space):
    """The Go To Jail space."""

    def __init__(self, position: int = 30):
        super().__init__("Go To Jail", position, SpaceType.GO_TO_JAIL)


@dataclass
class FreeParkingSpace(Space):
    """The Free Parking space."""

    def __init__(self, position: int = 20):
        super().__init__("Free Parking", position, SpaceType.FREE_PARKING)

from typing import Dict, List, Optional

from src.core.game.spaces import (
    Space,
    SpaceType,
    GoSpace,
    PropertySpace,
    RailroadSpace,
    UtilitySpace,
    TaxSpace,
    ChanceSpace,
    CommunityChestSpace,
    JailSpace,
    GoToJailSpace,
    FreeParkingSpace,
)


class Board:
    """The Monopoly game board with 40 spaces."""

    def __init__(self):
        self.spaces: List[Space] = self._create_standard_board()
        self.color_groups: Dict[str, List[int]] = self._build_color_groups()

    def _create_standard_board(self) -> List[Space]:
        """Create the standard 40-space Monopoly board."""
        return [
            # Bottom row (0-10)
            GoSpace(0),
            PropertySpace("Mediterranean Avenue", 1, 60, "brown", 2, 10, 30, 90, 160, 250, 50, 30),
            CommunityChestSpace(2),
            PropertySpace("Baltic Avenue", 3, 60, "brown", 4, 20, 60, 180, 320, 450, 50, 30),
            TaxSpace("Income Tax", 4, 200),
            RailroadSpace("Reading Railroad", 5),
            PropertySpace("Oriental Avenue", 6, 100, "light_blue", 6, 30, 90, 270, 400, 550, 50, 50),
            ChanceSpace(7),
            PropertySpace("Vermont Avenue", 8, 100, "light_blue", 6, 30, 90, 270, 400, 550, 50, 50),
            PropertySpace("Connecticut Avenue", 9, 120, "light_blue", 8, 40, 100, 300, 450, 600, 50, 60),
            JailSpace(10),
            # Left side (11-20)
            PropertySpace("St. Charles Place", 11, 140, "pink", 10, 50, 150, 450, 625, 750, 100, 70),
            UtilitySpace("Electric Company", 12),
            PropertySpace("States Avenue", 13, 140, "pink", 10, 50, 150, 450, 625, 750, 100, 70),
            PropertySpace("Virginia Avenue", 14, 160, "pink", 12, 60, 180, 500, 700, 900, 100, 80),
            RailroadSpace("Pennsylvania Railroad", 15),
            PropertySpace("St. James Place", 16, 180, "orange", 14, 70, 200, 550, 750, 950, 100, 90),
            CommunityChestSpace(17),
            PropertySpace("Tennessee Avenue", 18, 180, "orange", 14, 70, 200, 550, 750, 950, 100, 90),
            PropertySpace("New York Avenue", 19, 200, "orange", 16, 80, 220, 600, 800, 1000, 100, 100),
            FreeParkingSpace(20),
            # Top row (21-30)
            PropertySpace("Kentucky Avenue", 21, 220, "red", 18, 90, 250, 700, 875, 1050, 150, 110),
            ChanceSpace(22),
            PropertySpace("Indiana Avenue", 23, 220, "red", 18, 90, 250, 700, 875, 1050, 150, 110),
            PropertySpace("Illinois Avenue", 24, 240, "red", 20, 100, 300, 750, 925, 1100, 150, 120),
            RailroadSpace("B. & O. Railroad", 25),
            PropertySpace("Atlantic Avenue", 26, 260, "yellow", 22, 110, 330, 800, 975, 1150, 150, 130),
            PropertySpace("Ventnor Avenue", 27, 260, "yellow", 22, 110, 330, 800, 975, 1150, 150, 130),
            UtilitySpace("Water Works", 28),
            PropertySpace("Marvin Gardens", 29, 280, "yellow", 24, 120, 360, 850, 1025, 1200, 150, 140),
            GoToJailSpace(30),
            # Right side (31-39)
            PropertySpace("Pacific Avenue", 31, 300, "green", 26, 130, 390, 900, 1100, 1275, 200, 150),
            PropertySpace("North Carolina Avenue", 32, 300, "green", 26, 130, 390, 900, 1100, 1275, 200, 150),
            CommunityChestSpace(33),
            PropertySpace("Pennsylvania Avenue", 34, 320, "green", 28, 150, 450, 1000, 1200, 1400, 200, 160),
            RailroadSpace("Short Line", 35),
            ChanceSpace(36),
            PropertySpace("Park Place", 37, 350, "dark_blue", 35, 175, 500, 1100, 1300, 1500, 200, 175),
            TaxSpace("Luxury Tax", 38, 100),
            PropertySpace("Boardwalk", 39, 400, "dark_blue", 50, 200, 600, 1400, 1700, 2000, 200, 200),
        ]

    def _build_color_groups(self) -> Dict[str, List[int]]:
        """Build a mapping of color groups to property positions."""
        groups: Dict[str, List[int]] = {}
        for space in self.spaces:
            if isinstance(space, PropertySpace):
                if space.color_group not in groups:
                    groups[space.color_group] = []
                groups[space.color_group].append(space.position)
        return groups

    def get_space(self, position: int) -> Space:
        """Get the space at the given position."""
        return self.spaces[position % 40]

    def get_property_space(self, position: int) -> Optional[PropertySpace]:
        """Get a property space, or None if not a property."""
        space = self.get_space(position)
        return space if isinstance(space, PropertySpace) else None

    def get_railroad_space(self, position: int) -> Optional[RailroadSpace]:
        """Get a railroad space, or None if not a railroad."""
        space = self.get_space(position)
        return space if isinstance(space, RailroadSpace) else None

    def get_utility_space(self, position: int) -> Optional[UtilitySpace]:
        """Get a utility space, or None if not a utility."""
        space = self.get_space(position)
        return space if isinstance(space, UtilitySpace) else None

    def get_color_group(self, color: str) -> List[int]:
        """Get all property positions in a color group."""
        return self.color_groups.get(color, [])

    def get_all_railroads(self) -> List[int]:
        """Get positions of all railroad spaces."""
        return [s.position for s in self.spaces if isinstance(s, RailroadSpace)]

    def get_all_utilities(self) -> List[int]:
        """Get positions of all utility spaces."""
        return [s.position for s in self.spaces if isinstance(s, UtilitySpace)]

    def find_nearest_railroad(self, position: int) -> int:
        """Find the nearest railroad position moving forward from given position."""
        railroads = self.get_all_railroads()
        for offset in range(1, 40):
            pos = (position + offset) % 40
            if pos in railroads:
                return pos
        return railroads[0]  # Should never reach here

    def find_nearest_utility(self, position: int) -> int:
        """Find the nearest utility position moving forward from given position."""
        utilities = self.get_all_utilities()
        for offset in range(1, 40):
            pos = (position + offset) % 40
            if pos in utilities:
                return pos
        return utilities[0]  # Should never reach here

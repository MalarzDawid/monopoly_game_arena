"""
Tests for building houses and hotels.
"""

import pytest
from monopoly.game import create_game
from monopoly.player import Player
from monopoly.config import GameConfig


def test_cannot_build_without_monopoly():
    """
    Test that building requires complete color set.
    Rule: 'Once you own all Sites of a colour-group, you can buy Houses'
    """
    config = GameConfig(seed=42)
    players = [Player(0, "Alice")]
    game = create_game(config, players)

    # Buy only one brown property
    game.buy_property(0, 1)

    # Try to build
    assert not game.can_build_house(0, 1)


def test_can_build_with_monopoly():
    """Test that building is allowed with complete set."""
    config = GameConfig(seed=42)
    players = [Player(0, "Alice")]
    game = create_game(config, players)

    # Give Alice the brown monopoly
    game.buy_property(0, 1)
    game.buy_property(0, 3)

    # Should be able to build
    assert game.can_build_house(0, 1)


def test_even_build_rule():
    """
    Test that houses must be built evenly across color group.
    Rule: 'you cannot build a second House on any one Site... until you have built one House on every Site'
    """
    config = GameConfig(seed=42)
    players = [Player(0, "Alice")]
    game = create_game(config, players)

    # Give monopoly
    game.buy_property(0, 1)  # Mediterranean
    game.buy_property(0, 3)  # Baltic

    # Build one house on Mediterranean
    game.build_house(0, 1)
    assert game.property_ownership[1].houses == 1

    # Cannot build another on Mediterranean until Baltic has one
    assert not game.can_build_house(0, 1)

    # Can build on Baltic
    assert game.can_build_house(0, 3)

    # Build on Baltic
    game.build_house(0, 3)

    # Now can build on Mediterranean again
    assert game.can_build_house(0, 1)


def test_house_limit():
    """
    Test that building respects bank house supply.
    Rule: 'If there are no Houses left in the Bank, you must wait'
    """
    config = GameConfig(seed=42, house_limit=2)
    players = [Player(0, "Alice")]
    game = create_game(config, players)

    # Give monopoly
    game.buy_property(0, 1)
    game.buy_property(0, 3)

    # Build 2 houses (depleting supply)
    game.build_house(0, 1)
    game.build_house(0, 3)

    assert game.bank.houses_available == 0

    # Cannot build more
    assert not game.can_build_house(0, 1)


def test_hotel_requires_four_houses():
    """
    Test that hotel requires exactly 4 houses.
    Rule: 'You must have four Houses on each Site... before you can buy a Hotel'
    """
    config = GameConfig(seed=42)
    players = [Player(0, "Alice")]
    game = create_game(config, players)

    # Give monopoly
    game.buy_property(0, 1)
    game.buy_property(0, 3)

    # Add houses unevenly across the group (3 on Baltic, 4 on Mediterranean)
    game.property_ownership[1].houses = 4
    game.property_ownership[3].houses = 3

    # Cannot build hotel until EVERY property in group has 4 houses
    assert not game.can_build_hotel(0, 1)

    # Bring Baltic up to 4 as well
    game.property_ownership[3].houses = 4

    # Now can build hotel (represented by houses == 5)
    assert game.can_build_hotel(0, 1)


def test_hotel_returns_houses_to_bank():
    """
    Test that building hotel returns 4 houses to bank.
    Rule: 'cost four Houses, which are returned to the Bank'
    """
    config = GameConfig(seed=42, house_limit=10)
    players = [Player(0, "Alice")]
    game = create_game(config, players)

    # Give monopoly and money
    game.buy_property(0, 1)
    game.buy_property(0, 3)
    game.players[0].cash = 10000

    # Build 4 houses on each property (evenly)
    for _ in range(4):
        game.build_house(0, 1)
        game.build_house(0, 3)

    initial_houses_in_bank = game.bank.houses_available

    # Build hotel on Mediterranean
    # This consumes 1 Hotel, but RELEASES 4 houses back to bank
    game.build_hotel(0, 1)

    # Should have 4 more houses in bank
    assert game.bank.houses_available == initial_houses_in_bank + 4
    assert game.property_ownership[1].houses == 5  # 5 represents hotel


def test_cannot_build_on_group_if_any_mortgaged():
    """
    Test that mortgaged properties block building on the WHOLE group.
    Rule: 'Houses may not be built if any Site of the same colour-group is mortgaged.'
    """
    config = GameConfig(seed=42)
    players = [Player(0, "Alice")]
    game = create_game(config, players)

    # Give monopoly
    game.buy_property(0, 1)
    game.buy_property(0, 3)

    # Mortgage Baltic (3)
    game.property_ownership[3].is_mortgaged = True

    # Try to build on Mediterranean (1) - which is NOT mortgaged
    # This should fail because a group member (3) is mortgaged
    assert not game.can_build_house(0, 1)


def test_sell_building_even_rule():
    """
    Test that buildings must be sold evenly.
    Rule: 'Houses must be sold evenly, in the same way as they were bought'
    """
    config = GameConfig(seed=42)
    players = [Player(0, "Alice")]
    game = create_game(config, players)

    # Give monopoly with buildings
    game.buy_property(0, 1)
    game.buy_property(0, 3)
    game.property_ownership[1].houses = 2
    game.property_ownership[3].houses = 1

    # Cannot sell from Baltic (would leave 2 vs 0, difference of 2)
    # Must sell from the one with MORE houses first
    assert not game._can_sell_evenly(3, "brown")

    # Can sell from Mediterranean (would leave 1 vs 1)
    assert game._can_sell_evenly(1, "brown")


def test_sell_house_returns_half_cost():
    """
    Test that selling buildings returns half the cost.
    Rule: 'sold to the Bank at half the value stated on the relevant Title Deed'
    """
    config = GameConfig(seed=42)
    players = [Player(0, "Alice")]
    game = create_game(config, players)

    # Give monopoly with houses. Oriental Ave (6) house cost is 50.
    game.buy_property(0, 6)
    game.buy_property(0, 8)
    game.buy_property(0, 9)
    game.players[0].cash = 10000 

    # Build houses evenly
    game.build_house(0, 6)
    game.build_house(0, 8)
    game.build_house(0, 9)

    initial_cash = game.players[0].cash

    # Sell a house from Oriental
    game.sell_building(0, 6)

    # Should get 25 (half of 50)
    assert game.players[0].cash == initial_cash + 25
    assert game.property_ownership[6].houses == 0


def test_sell_hotel_breakdown_value():
    """
    Test downgrading hotel to 4 houses.
    Rule: 'receive in exchange four Houses as well as money for the Hotel (i.e. half its cost)'
    """
    config = GameConfig(seed=42)
    players = [Player(0, "Alice")]
    game = create_game(config, players)

    # Give monopoly and build to hotels
    game.buy_property(0, 6) # Oriental, house cost 50
    game.buy_property(0, 8)
    game.buy_property(0, 9)
    game.players[0].cash = 100000

    # Assume setup is done and we have hotels
    game.property_ownership[6].houses = 5 # Hotel

    # Ensure bank has enough houses for the breakdown
    game.bank.houses_available = 10

    initial_cash = game.players[0].cash
    
    # Sell Hotel (downgrade to 4 houses)
    game.downgrade_hotel(0, 6)

    # Verify Houses: Should be 4
    assert game.property_ownership[6].houses == 4
    
    # Verify Cash: Should receive half of HOTEL cost only (50 / 2 = 25)
    # Because you KEEP the 4 houses, you don't get paid for them yet.
    # Note: Rules say 'half the cash price of the Hotel'. 
    # Usually Hotel cost = House Cost + Hotel Premium (often equal to House Cost).
    # If Hotel Cost is 50, half is 25.
    assert game.players[0].cash == initial_cash + 25


def test_cannot_sell_hotel_to_houses_if_bank_empty():
    """
    Test that you cannot downgrade hotel to houses if bank has no houses.
    Rule: 'when selling Hotels you cannot replace them with Houses if there are none left.'
    """
    config = GameConfig(seed=42)
    players = [Player(0, "Alice")]
    game = create_game(config, players)

    # Setup: Alice has a Hotel
    game.buy_property(0, 1)
    game.property_ownership[1].houses = 5 # Hotel

    # Setup: Bank has NO houses
    game.bank.houses_available = 0

    # Try to downgrade
    success = game.downgrade_hotel(0, 1)

    assert not success
    assert game.property_ownership[1].houses == 5 # Still a hotel

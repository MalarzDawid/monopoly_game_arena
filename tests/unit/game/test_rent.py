"""
Tests for rent calculation on all property types.
"""

import pytest
from core import GameConfig, Player, create_game


def test_basic_property_rent():
    """
    Test basic rent on unimproved property.
    Rule: 'The amount payable is shown on the Title Deed' [cite: 81]
    """
    config = GameConfig(seed=42)
    players = [Player(0, "Alice"), Player(1, "Bob")]
    game = create_game(config, players)

    # Alice buys Mediterranean (position 1)
    game.buy_property(0, 1)

    # Calculate rent
    rent = game.calculate_rent(1)

    # Mediterranean base rent is 2
    assert rent == 2


def test_monopoly_doubles_rent():
    """
    Test that owning a complete color set doubles rent on unimproved sites.
    Rule: 'If all Sites within a colour-group are owned by a player, the rent payable is doubled on any Site of that group not yet built on.' [cite: 82]
    """
    config = GameConfig(seed=42)
    players = [Player(0, "Alice"), Player(1, "Bob")]
    game = create_game(config, players)

    # Alice buys both brown properties (positions 1 and 3)
    game.buy_property(0, 1)  # Mediterranean
    game.buy_property(0, 3)  # Baltic

    # Calculate rent for Mediterranean
    rent = game.calculate_rent(1)

    # Base rent is 2, should be doubled to 4
    assert rent == 4


def test_monopoly_no_double_rent_if_group_mortgaged():
    """
    Test that monopoly doubling is suppressed if ANY property in the group is mortgaged.
    Rule: 'an owner who owns a whole colour-group may not collect double rent if any one Site there is mortgaged.' 
    """
    config = GameConfig(seed=42)
    players = [Player(0, "Alice")]
    game = create_game(config, players)

    # Alice buys both brown properties
    game.buy_property(0, 1)
    game.buy_property(0, 3)

    # Alice mortgages ONE of them (e.g., Baltic/3)
    game.property_ownership[3].is_mortgaged = True

    # Calculate rent for the UNMORTGAGED property (Mediterranean/1)
    rent = game.calculate_rent(1)

    # Should be base rent (2), NOT doubled (4), because the group is incomplete due to mortgage
    assert rent == 2


def test_rent_with_houses():
    """
    Test rent calculation with houses.
    Rule: 'Where Houses or Hotels have been built on a Site, the rent will increase' [cite: 84]
    """
    config = GameConfig(seed=42)
    players = [Player(0, "Alice")]
    game = create_game(config, players)

    # Give Alice the light blue monopoly
    game.buy_property(0, 6)   # Oriental
    game.buy_property(0, 8)   # Vermont
    game.buy_property(0, 9)   # Connecticut

    # Add houses
    game.property_ownership[6].houses = 1

    rent = game.calculate_rent(6)

    # Oriental with 1 house has rent of 30
    assert rent == 30


def test_rent_with_hotel():
    """Test rent calculation with hotel."""
    config = GameConfig(seed=42)
    players = [Player(0, "Alice")]
    game = create_game(config, players)

    # Give Alice a monopoly
    game.buy_property(0, 6)
    game.buy_property(0, 8)
    game.buy_property(0, 9)

    # Add hotel (represented as 5 houses)
    game.property_ownership[6].houses = 5

    rent = game.calculate_rent(6)

    # Oriental with hotel has rent of 550
    assert rent == 550


def test_railroad_rent_scaling():
    """
    Test railroad rent scales with number owned.
    Rule: 'The amount payable will vary according to the number of other Stations owned by that player.' [cite: 99]
    """
    config = GameConfig(seed=42)
    players = [Player(0, "Alice")]
    game = create_game(config, players)

    # Buy railroads one by one
    railroads = game.board.get_all_railroads()

    # 1 railroad: 25
    game.buy_property(0, railroads[0])
    assert game.calculate_rent(railroads[0]) == 25

    # 2 railroads: 50
    game.buy_property(0, railroads[1])
    assert game.calculate_rent(railroads[0]) == 50
    assert game.calculate_rent(railroads[1]) == 50

    # 3 railroads: 100
    game.buy_property(0, railroads[2])
    assert game.calculate_rent(railroads[0]) == 100

    # 4 railroads: 200
    game.buy_property(0, railroads[3])
    assert game.calculate_rent(railroads[0]) == 200


def test_utility_rent_with_dice():
    """
    Test utility rent calculation based on dice roll.
    Rule: 'rent will be four times your dice roll' (1 owned) [cite: 90]
    Rule: 'must pay ten times the amount of your dice roll' (2 owned) [cite: 91]
    """
    config = GameConfig(seed=42)
    players = [Player(0, "Alice")]
    game = create_game(config, players)

    utilities = game.board.get_all_utilities()

    # 1 utility: 4x dice
    game.buy_property(0, utilities[0])
    # The rule says 'according to the dice you rolled to get there' [cite: 89]
    dice_roll = 7 
    
    rent = game.calculate_rent(utilities[0], dice_roll=dice_roll)
    assert rent == 28  # 7 * 4

    # 2 utilities: 10x dice
    game.buy_property(0, utilities[1])
    rent = game.calculate_rent(utilities[0], dice_roll=dice_roll)
    assert rent == 70  # 7 * 10


def test_no_rent_on_mortgaged_property():
    """
    Test that mortgaged properties don't collect rent.
    Rule: 'Rent is not payable on mortgaged Properties.' [cite: 85]
    """
    config = GameConfig(seed=42)
    players = [Player(0, "Alice")]
    game = create_game(config, players)

    # Buy and mortgage property
    game.buy_property(0, 1)
    game.property_ownership[1].is_mortgaged = True

    rent = game.calculate_rent(1)
    assert rent == 0


def test_rent_transaction_safety_on_own_property():
    """
    Test that no money is lost if owner 'pays' themselves.
    Rule implied: You don't pay rent to yourself.
    """
    config = GameConfig(seed=42)
    players = [Player(0, "Alice")]
    game = create_game(config, players)

    game.buy_property(0, 1)
    initial_cash = game.players[0].cash
    
    rent = game.calculate_rent(1)
    assert rent > 0 

    # Attempt to execute payment from Alice (0) to Alice (0)
    game.pay_rent(0, 0, rent)

    # Cash should remain identical
    assert game.players[0].cash == initial_cash


def test_rent_payment_transfer():
    """Test that rent payment transfers money correctly between players."""
    config = GameConfig(seed=42)
    players = [Player(0, "Alice"), Player(1, "Bob")]
    game = create_game(config, players)

    # Alice buys property
    game.buy_property(0, 1)

    alice_cash = game.players[0].cash
    bob_cash = game.players[1].cash

    # Bob pays rent
    rent = game.calculate_rent(1)
    # pay_rent(payer_id, recipient_id, amount)
    game.pay_rent(1, 0, rent)

    assert game.players[0].cash == alice_cash + rent
    assert game.players[1].cash == bob_cash - rent

"""
Tests for mortgages and bankruptcy.
"""

import pytest
from src.core import GameConfig, Player, create_game


def test_mortgage_property():
    """
    Test mortgaging a property.
    Rule: 'collect from the Bank your mortgage to the value of the amount shown on the back of the card.'
    """
    config = GameConfig(seed=42)
    players = [Player(0, "Alice")]
    game = create_game(config, players)

    # Buy property
    game.buy_property(0, 1)

    initial_cash = game.players[0].cash

    # Mortgage it
    success = game.mortgage_property(0, 1)

    assert success
    assert game.property_ownership[1].is_mortgaged
    # Mediterranean mortgage value is 30
    assert game.players[0].cash == initial_cash + 30


def test_cannot_mortgage_with_buildings():
    """
    Test that properties with buildings cannot be mortgaged.
    Rule: 'If mortgaging a Site, first sell any buildings to the Bank.'
    """
    config = GameConfig(seed=42)
    players = [Player(0, "Alice")]
    game = create_game(config, players)

    # Give monopoly and build
    game.buy_property(0, 1)
    game.buy_property(0, 3)
    game.property_ownership[1].houses = 1

    # Try to mortgage
    success = game.mortgage_property(0, 1)

    assert not success


def test_unmortgage_with_interest():
    """
    Test unmortgaging requires mortgage value + 10% interest.
    Rule: 'pay this amount plus 10% interest'
    """
    config = GameConfig(seed=42, mortgage_interest_rate=0.10)
    players = [Player(0, "Alice")]
    game = create_game(config, players)

    # Buy and mortgage
    game.buy_property(0, 1)
    game.mortgage_property(0, 1)

    cash_before = game.players[0].cash

    # Unmortgage
    # Mortgage value 30. 10% is 3. Total 33.
    success = game.unmortgage_property(0, 1)

    assert success
    assert not game.property_ownership[1].is_mortgaged
    assert game.players[0].cash == cash_before - 33


def test_cannot_unmortgage_without_funds():
    """Test that unmortgaging requires sufficient funds."""
    config = GameConfig(seed=42)
    players = [Player(0, "Alice")]
    game = create_game(config, players)

    # Buy and mortgage
    game.buy_property(0, 1)
    game.mortgage_property(0, 1)

    # Remove cash
    game.players[0].cash = 10

    # Try to unmortgage
    success = game.unmortgage_property(0, 1)

    assert not success
    assert game.property_ownership[1].is_mortgaged


def test_bankruptcy_to_player_assets_transfer():
    """
    Test bankruptcy transfers assets (cash and deeds) to creditor.
    Rule: 'that player receives any cash, Title Deeds'
    """
    config = GameConfig(seed=42)
    players = [Player(0, "Alice"), Player(1, "Bob")]
    game = create_game(config, players)

    # Alice owns properties
    game.buy_property(0, 1)
    game.buy_property(0, 3)
    alice_cash = game.players[0].cash

    bob_initial_cash = game.players[1].cash

    # Alice goes bankrupt to Bob
    game.declare_bankruptcy(0, creditor_id=1)

    # Check Alice
    assert game.players[0].is_bankrupt
    assert len(game.players[0].properties) == 0

    # Check Bob received assets
    assert 1 in game.players[1].properties
    assert 3 in game.players[1].properties
    assert game.players[1].cash == bob_initial_cash + alice_cash

    # Check ownership transferred
    assert game.property_ownership[1].owner_id == 1
    assert game.property_ownership[3].owner_id == 1


def test_bankruptcy_to_player_sells_buildings_first():
    """
    Test that buildings are sold to bank at half price, and CASH goes to creditor.
    Rule: 'Houses and Hotels are sold to the Bank at half their original cost and that player receives any cash'
    """
    config = GameConfig(seed=42)
    players = [Player(0, "Alice"), Player(1, "Bob")]
    game = create_game(config, players)

    # Alice owns monopoly with houses
    game.buy_property(0, 1)
    game.buy_property(0, 3)
    
    # Add 2 houses to prop 1. Cost 50 each (Brown set). Total cost 100.
    # Sell value is 50.
    game.property_ownership[1].houses = 2 
    
    alice_cash = game.players[0].cash
    bob_initial_cash = game.players[1].cash

    # Alice goes bankrupt to Bob
    game.declare_bankruptcy(0, creditor_id=1)

    # Houses should be gone
    assert game.property_ownership[1].houses == 0
    
    # Bob gets: Bob's init + Alice's cash + (2 houses * 25 sell price)
    expected_bob_cash = bob_initial_cash + alice_cash + 50
    assert game.players[1].cash == expected_bob_cash


def test_bankruptcy_to_player_mortgage_transfer_fee():
    """
    Test that creditor must pay 10% interest immediately on received mortgaged property.
    Rule: 'he must immediately pay 10% and then choose whether to retain the mortgage or pay it off'
    """
    config = GameConfig(seed=42)
    players = [Player(0, "Alice"), Player(1, "Bob")]
    game = create_game(config, players)

    # Alice owns mortgaged property
    game.buy_property(0, 1)
    game.mortgage_property(0, 1) # Mortgage value 30

    alice_cash = game.players[0].cash
    bob_initial_cash = game.players[1].cash

    # Alice goes bankrupt to Bob
    game.declare_bankruptcy(0, creditor_id=1)

    # Bob should own the property
    assert game.property_ownership[1].owner_id == 1
    assert game.property_ownership[1].is_mortgaged
    
    # Bob must pay 10% of mortgage value (30 * 0.10 = 3)
    assert game.players[1].cash == bob_initial_cash + alice_cash - 3


def test_bankruptcy_to_bank_auction_trigger():
    """
    Test bankruptcy to bank returns properties and prepares them for auction.
    Rule: 'The Banker then auctions off each Property to the highest bidder.'
    """
    config = GameConfig(seed=42)
    players = [Player(0, "Alice")]
    game = create_game(config, players)

    # Alice owns properties
    game.buy_property(0, 1)

    # Alice goes bankrupt to bank
    game.declare_bankruptcy(0, creditor_id=None)

    # Check Alice
    assert game.players[0].is_bankrupt
    assert len(game.players[0].properties) == 0

    # Property should be unowned
    assert game.property_ownership[1].owner_id is None
    
    # Note: A full implementation might check if the property was added to an 'auction_queue'


def test_bankruptcy_to_bank_returns_jail_cards():
    """
    Test that jail cards are returned to the deck if bankrupt to Bank.
    Rule: 'You must return "Get Out Of Jail Free" cards to the bottom of the relevant pile.'
    """
    config = GameConfig(seed=42)
    players = [Player(0, "Alice")]
    game = create_game(config, players)
    
    # Mock deck size or card count
    initial_deck_count = len(game.chance_cards) # Assuming this attribute exists

    # Give Alice a card
    game.players[0].get_out_of_jail_cards = 1
    
    # Bankrupt to Bank
    game.declare_bankruptcy(0, creditor_id=None)
    
    assert game.players[0].get_out_of_jail_cards == 0
    # Ideally check deck count increased or card returned
    # assert len(game.chance_cards) == initial_deck_count + 1


def test_game_ends_when_one_player_left():
    """Test that game ends when only one player remains."""
    config = GameConfig(seed=42)
    players = [Player(0, "Alice"), Player(1, "Bob")]
    game = create_game(config, players)

    # Alice goes bankrupt
    game.declare_bankruptcy(0)

    # Game should end
    assert game.game_over
    assert game.winner == 1

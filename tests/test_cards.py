"""
Tests for Chance and Community Chest cards.
"""

import pytest
from src.core import GameConfig, Player, create_game
from src.core.game.cards import Card, CardType


def test_card_move_to_pass_go():
    """
    Test card that moves player to specific position and passes GO.
    Rule: 'If you pass "GO" on the way, collect £200.'
    """
    config = GameConfig(seed=42)
    players = [Player(0, "Alice")]
    game = create_game(config, players)

    # Position 35. Card says advance to 5 (Reading Railroad/Kings Cross).
    # Path is 35 -> 36... -> 39 -> 0 -> ... -> 5.
    card = Card("Advance to Kings Cross", CardType.MOVE_TO, target_position=5)

    game.players[0].position = 35
    initial_cash = game.players[0].cash

    game.execute_card(card, 0)

    # Player should be at 5
    assert game.players[0].position == 5
    # Should collect salary because they passed GO
    assert game.players[0].cash == initial_cash + config.go_salary


def test_card_move_to_no_pass_go():
    """Test card that moves player backwards or short distance without passing GO."""
    config = GameConfig(seed=42)
    players = [Player(0, "Alice")]
    game = create_game(config, players)

    # Position 10. Move to 20.
    card = Card("Advance to Free Parking", CardType.MOVE_TO, target_position=20)
    game.players[0].position = 10
    initial_cash = game.players[0].cash
    
    game.execute_card(card, 0)
    
    assert game.players[0].position == 20
    assert game.players[0].cash == initial_cash # No salary


def test_card_collect_money():
    """Test card that collects money."""
    config = GameConfig(seed=42)
    players = [Player(0, "Alice")]
    game = create_game(config, players)

    card = Card("Bank pays you $50", CardType.COLLECT, value=50)

    initial_cash = game.players[0].cash
    game.execute_card(card, 0)

    assert game.players[0].cash == initial_cash + 50


def test_card_pay_money():
    """Test card that requires payment."""
    config = GameConfig(seed=42)
    players = [Player(0, "Alice")]
    game = create_game(config, players)

    card = Card("Pay poor tax $15", CardType.PAY, value=15)

    initial_cash = game.players[0].cash
    game.execute_card(card, 0)

    assert game.players[0].cash == initial_cash - 15


def test_card_go_to_jail():
    """
    Test Go to Jail card.
    Rule: 'You do not pass "GO" when you are sent to Jail'
    """
    config = GameConfig(seed=42)
    players = [Player(0, "Alice")]
    game = create_game(config, players)

    card = Card("Go to Jail", CardType.GO_TO_JAIL)

    # Place player past GO trigger point just in case
    game.players[0].position = 35 
    initial_cash = game.players[0].cash
    
    game.execute_card(card, 0)

    assert game.players[0].in_jail
    assert game.players[0].position == 10
    # Ensure no salary collected even if logic might suggest "moving" from 35 to 10
    assert game.players[0].cash == initial_cash


def test_card_get_out_of_jail():
    """
    Test Get Out of Jail Free card retention.
    Rule: 'you may keep it until you wish to use it'
    """
    config = GameConfig(seed=42)
    players = [Player(0, "Alice")]
    game = create_game(config, players)

    card = Card("Get Out of Jail Free", CardType.GET_OUT_OF_JAIL)

    game.execute_card(card, 0)

    assert game.players[0].get_out_of_jail_cards == 1
    # Card should be removed from deck (implied, hard to test without deck access)


def test_card_pay_per_house_hotel_split():
    """
    Test card that charges different amounts for houses and hotels.
    Example: 'For each House pay $25, For each Hotel $100'
    """
    config = GameConfig(seed=42)
    players = [Player(0, "Alice")]
    game = create_game(config, players)

    # Give player properties
    game.buy_property(0, 1)
    game.buy_property(0, 3)
    
    # 2 Houses on prop 1
    game.property_ownership[1].houses = 2
    
    # 1 Hotel on prop 3 (stored as 5 houses internally usually, but card logic needs to distinguish)
    # Assuming internal representation: 5 houses = 1 Hotel
    game.property_ownership[3].houses = 5

    # Card: $40 per house, $115 per hotel
    card = Card(
        "Street Repairs", 
        CardType.PAY_PER_BUILDING, 
        value=40,    # Per house
        value2=115   # Per hotel
    )

    initial_cash = game.players[0].cash
    game.execute_card(card, 0)

    # Calculation:
    # Houses: 2 * 40 = 80
    # Hotels: 1 * 115 = 115 (Prop 3 has 5 'houses', which means 1 hotel, 0 houses)
    # Total: 195
    assert game.players[0].cash == initial_cash - 195


def test_card_collect_from_players():
    """Test card that collects from all other players."""
    config = GameConfig(seed=42)
    players = [Player(0, "Alice"), Player(1, "Bob"), Player(2, "Charlie")]
    game = create_game(config, players)

    card = Card("Collect $10 from every player", CardType.COLLECT_FROM_PLAYERS, value=10)

    alice_cash = game.players[0].cash
    bob_cash = game.players[1].cash
    charlie_cash = game.players[2].cash

    game.execute_card(card, 0)

    # Alice should gain 20 (10 from each of 2 other players)
    assert game.players[0].cash == alice_cash + 20
    assert game.players[1].cash == bob_cash - 10
    assert game.players[2].cash == charlie_cash - 10


def test_card_move_to_nearest_railroad_and_rent():
    """
    Test card that moves to nearest railroad.
    Note: Often these cards say 'pay owner twice the rental'.
    This test checks movement.
    """
    config = GameConfig(seed=42)
    players = [Player(0, "Alice")]
    game = create_game(config, players)

    card = Card(
        "Advance to nearest Railroad",
        CardType.MOVE_TO_NEAREST,
        target_type="railroad",
    )

    # Position 7 (Chance 1) -> nearest railroad is 15 (Marylebone/Penn)
    # Railroads are at 5, 15, 25, 35
    game.players[0].position = 7
    game.execute_card(card, 0)

    assert game.players[0].position == 15
    # Verify player logic triggers 'land_on_space' (implied by execution flow)


def test_card_move_to_nearest_utility():
    """Test card that moves to nearest utility."""
    config = GameConfig(seed=42)
    players = [Player(0, "Alice")]
    game = create_game(config, players)

    card = Card(
        "Advance to nearest Utility",
        CardType.MOVE_TO_NEAREST,
        target_type="utility",
    )

    # Position 7 (Chance 1) -> nearest utility is 12 (Electric Company)
    # Utilities are at 12, 28
    game.players[0].position = 7
    game.execute_card(card, 0)

    assert game.players[0].position == 12


def test_card_go_back_spaces():
    """
    Test card that moves player backward.
    Rule: 'Go Back 3 Spaces'
    """
    config = GameConfig(seed=42)
    players = [Player(0, "Alice")]
    game = create_game(config, players)

    card = Card("Go back 3 spaces", CardType.MOVE_SPACES, value=-3)

    game.players[0].position = 10
    game.execute_card(card, 0)

    assert game.players[0].position == 7
    # Important: Player should then ACT on space 7 (Chance again? or Property?)
    # Usually space 7 is Chance. 
    # If starting at Chance (36) -> back 3 to 33 (Community Chest).

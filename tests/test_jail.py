"""
Tests specifically for jail mechanics.
"""

import pytest
from monopoly.game import create_game
from monopoly.player import Player
from monopoly.config import GameConfig
from monopoly.cards import Card, CardType


def test_jail_pay_fine():
    """
    Test paying fine to get out of jail.
    Rule: 'pay a fine of £50 and continue on your next turn' (standard play allows paying before rolling)
    """
    config = GameConfig(seed=42, jail_fine=50)
    players = [Player(0, "Alice")]
    game = create_game(config, players)

    # Send to jail
    game.send_to_jail(0)

    initial_cash = game.players[0].cash

    # Pay fine
    # Assuming the method handles the logic: Pay -> Set in_jail=False -> Allow roll
    success = game.pay_jail_fine(0)

    assert success
    assert not game.players[0].in_jail
    assert game.players[0].cash == initial_cash - 50


def test_jail_use_card():
    """
    Test using Get Out of Jail Free card.
    Rule: 'use a "Get Out Of Jail Free" card if you have one'
    """
    config = GameConfig(seed=42)
    players = [Player(0, "Alice")]
    game = create_game(config, players)

    # Give player a jail card
    game.players[0].get_out_of_jail_cards = 1

    # Send to jail
    game.send_to_jail(0)

    # Use card
    success = game.use_jail_card(0)

    assert success
    assert not game.players[0].in_jail
    assert game.players[0].get_out_of_jail_cards == 0


def test_jail_forced_payment_after_three_turns():
    """
    Test that player must pay after 3 failed attempts.
    Rule: 'After you have waited three turns, you must move out of Jail and pay £50'
    """
    config = GameConfig(seed=42, jail_fine=50, max_jail_turns=3)
    players = [Player(0, "Alice")]
    game = create_game(config, players)

    game.send_to_jail(0)
    player = game.players[0]

    # Simulate 2 failed turns, entering 3rd
    player.jail_turns = 2
    initial_cash = player.cash

    # Force a non-doubles roll seed
    game.rng.seed(50) 
    
    # Process the turn (Roll -> Fail -> Force Pay -> Move)
    game.process_jail_turn(0)

    assert not player.in_jail
    assert player.cash == initial_cash - 50
    # Player should have moved from pos 10
    assert player.position != 10


def test_collect_rent_while_in_jail():
    """
    Test that a player in jail can still collect rent.
    Rule: 'While in Jail you can collect rent on Properties provided they are not mortgaged.'
    """
    config = GameConfig(seed=42)
    players = [Player(0, "Alice"), Player(1, "Bob")]
    game = create_game(config, players)

    # Alice owns a property
    game.buy_property(0, 1) # Mediterranean Avenue
    
    # Alice goes to jail
    game.send_to_jail(0)
    assert game.players[0].in_jail

    # Bob lands on Alice's property
    game.players[1].position = 1
    
    # Calculate and Pay Rent
    rent = game.calculate_rent(1)
    initial_alice_cash = game.players[0].cash
    
    game.pay_rent(1, 0, rent)

    # Alice should receive money despite being in jail
    assert game.players[0].cash == initial_alice_cash + rent


def test_cannot_pay_fine_without_money():
    """Test that paying fine requires sufficient cash."""
    config = GameConfig(seed=42, jail_fine=50)
    players = [Player(0, "Alice")]
    game = create_game(config, players)

    game.send_to_jail(0)
    game.players[0].cash = 30  # Not enough

    success = game.pay_jail_fine(0)

    assert not success
    assert game.players[0].in_jail


def test_cannot_use_jail_card_without_having_one():
    """Test that using jail card requires having one."""
    config = GameConfig(seed=42)
    players = [Player(0, "Alice")]
    game = create_game(config, players)

    game.send_to_jail(0)
    game.players[0].get_out_of_jail_cards = 0

    success = game.use_jail_card(0)

    assert not success
    assert game.players[0].in_jail


def test_jail_position_is_ten():
    """Test that jail is at position 10 (Just Visiting/Jail space)."""
    config = GameConfig(seed=42)
    players = [Player(0, "Alice")]
    game = create_game(config, players)

    game.players[0].position = 20
    game.send_to_jail(0)

    assert game.players[0].position == 10


def test_jail_resets_doubles_count():
    """Test that going to jail resets consecutive doubles."""
    config = GameConfig(seed=42)
    players = [Player(0, "Alice")]
    game = create_game(config, players)

    game.players[0].consecutive_doubles = 2
    game.send_to_jail(0)

    assert game.players[0].consecutive_doubles == 0


def test_jail_from_card():
    """
    Test going to jail from a card.
    Rule: 'pick a Chance or Community Chest card which tells you to "GO DIRECTLY TO JAIL"'
    """
    config = GameConfig(seed=42)
    players = [Player(0, "Alice")]
    game = create_game(config, players)

    # Create a mock card
    card = Card(
        text="Go to Jail", 
        action_type=CardType.GO_TO_JAIL, 
        value=0
    )

    game.players[0].position = 7
    game.execute_card(card, 0)

    assert game.players[0].in_jail
    assert game.players[0].position == 10
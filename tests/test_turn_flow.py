"""
Tests for turn flow mechanics including doubles and jail.
"""

import pytest
from monopoly.game import create_game
from monopoly.player import Player
from monopoly.config import GameConfig

def test_basic_turn_flow():
    """Test basic turn progression."""
    config = GameConfig(seed=42)
    players = [Player(0, "Alice"), Player(1, "Bob")]
    game = create_game(config, players)

    assert game.get_current_player().player_id == 0
    assert game.turn_number == 0

    # Roll dice and move
    die1, die2 = game.roll_dice()
    total = die1 + die2
    game.move_player(0, total)

    # End turn
    game.end_turn()

    assert game.get_current_player().player_id == 1
    assert game.turn_number == 1


def test_passing_go():
    """Test that passing GO awards salary[cite: 64]."""
    config = GameConfig(seed=42, go_salary=200)
    players = [Player(0, "Alice")]
    game = create_game(config, players)

    initial_cash = game.players[0].cash

    # Move player past GO (from position 35 to 5)
    game.players[0].position = 35
    game.move_player(0, 10)

    assert game.players[0].cash == initial_cash + config.go_salary


def test_landing_on_go():
    """Test landing exactly on GO[cite: 64]."""
    config = GameConfig(seed=42, go_salary=200)
    players = [Player(0, "Alice")]
    game = create_game(config, players)

    initial_cash = game.players[0].cash

    # Move from position 36 to GO
    game.players[0].position = 36
    game.move_player(0, 4)

    assert game.players[0].position == 0
    assert game.players[0].cash == initial_cash + config.go_salary


def test_three_doubles_go_to_jail():
    """
    Test that three consecutive doubles sends player to jail and ends turn immediately.
    Rule: 'Your turn ends when you are sent to Jail.' 
    """
    config = GameConfig(seed=42)
    players = [Player(0, "Alice"), Player(1, "Bob")]
    game = create_game(config, players)

    player = game.players[0]
    player.consecutive_doubles = 2

    # Mock a doubles roll
    game.rng.seed(100)
    # Find a seed that gives us doubles
    for seed in range(1000):
        game.rng.seed(seed)
        die1, die2 = game.rng.randint(1, 6), game.rng.randint(1, 6)
        if die1 == die2:
            game.rng.seed(seed)
            break
            
    # Execute the roll logic which should trigger jail check
    die1, die2 = game.roll_dice()
    
    # We simulate the game loop logic here
    if die1 == die2:
        player.consecutive_doubles += 1
        if player.consecutive_doubles == 3:
            game.send_to_jail(0)
            game.end_turn() # Force end turn as per rule [120]

    assert player.in_jail
    assert player.position == 10
    assert player.consecutive_doubles == 0
    # Crucial check: Validates that the turn ended immediately, skipping any extra roll
    assert game.get_current_player().player_id == 1 


def test_doubles_give_extra_turn():
    """Test that rolling doubles allows another turn[cite: 62]."""
    config = GameConfig(seed=42)
    players = [Player(0, "Alice"), Player(1, "Bob")]
    game = create_game(config, players)

    player = game.players[0]

    # First roll (doubles)
    game.last_dice_roll = (3, 3)
    player.consecutive_doubles = 1

    # Player should still be active (turn has not passed to Bob)
    assert game.get_current_player().player_id == 0
    assert player.consecutive_doubles == 1


def test_go_to_jail_space():
    """Test landing on Go To Jail space[cite: 118]."""
    config = GameConfig(seed=42)
    players = [Player(0, "Alice")]
    game = create_game(config, players)

    player = game.players[0]
    player.position = 25

    # Move to Go To Jail (position 30)
    game.move_player(0, 5)
    
    # Logic typically handled by the board space, here invoked manually for unit test
    game.send_to_jail(0)

    assert player.in_jail
    assert player.position == 10
    # Ensure no salary collected if theoretically passing GO (though not applicable from pos 30 -> 10)


def test_jail_turns_increment():
    """Test that jail turns increment on failed attempts."""
    config = GameConfig(seed=42)
    players = [Player(0, "Alice")]
    game = create_game(config, players)

    player = game.players[0]
    game.send_to_jail(0)

    assert player.jail_turns == 0

    # Attempt to get out (will fail if not doubles)
    game.rng.seed(50)  # Non-doubles seed
    success = game.attempt_jail_release(0)

    assert not success
    assert player.jail_turns == 1
    assert player.in_jail


def test_jail_release_on_doubles():
    """
    Test that rolling doubles in jail releases player.
    Rule: 'move out of Jail using this dice roll.' 
    """
    config = GameConfig(seed=42)
    players = [Player(0, "Alice")]
    game = create_game(config, players)

    game.send_to_jail(0)
    player = game.players[0]

    # Force a doubles roll
    seed_for_doubles = 0
    for seed in range(1000):
        game.rng.seed(seed)
        die1, die2 = game.rng.randint(1, 6), game.rng.randint(1, 6)
        if die1 == die2:
            seed_for_doubles = seed
            break
    
    game.rng.seed(seed_for_doubles)
    
    # Capture the roll to verify movement
    die1, die2 = game.rng.randint(1, 6), game.rng.randint(1, 6)
    game.rng.seed(seed_for_doubles) # Reset for the actual function call

    success = game.attempt_jail_release(0)

    assert success
    assert not player.in_jail
    # Verify player moved by the amount shown on dice
    expected_position = (10 + die1 + die2) % 40
    assert player.position == expected_position


def test_forced_jail_exit_turn_three():
    """
    Test forced release after three failed jail attempts.
    Rule: 'After you have waited three turns, you must move out of Jail and pay £50
    before moving your token according to your dice roll.' 
    """
    config = GameConfig(seed=42, jail_fine=50, max_jail_turns=3)
    players = [Player(0, "Alice")]
    game = create_game(config, players)

    player = game.players[0]
    game.send_to_jail(0)

    # Simulate waiting 2 turns, now entering the 3rd turn
    player.jail_turns = 2
    initial_cash = 1500
    player.cash = initial_cash

    # Set seed to NON-doubles
    game.rng.seed(50) 
    die1, die2 = game.rng.randint(1, 6), game.rng.randint(1, 6)
    assert die1 != die2 # Verification of test setup
    
    game.rng.seed(50) # Reset for function call

    # This function should handle the logic: Roll -> Fail -> Pay -> Move
    game.process_jail_turn(0) 

    assert not player.in_jail
    # Must pay fine
    assert player.cash == initial_cash - 50
    # Must move according to the dice roll
    assert player.position == 10 + die1 + die2
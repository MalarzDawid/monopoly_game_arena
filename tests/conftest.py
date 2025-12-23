"""Shared test fixtures for Monopoly V3 tests."""

import pytest
from core import GameConfig, Player, create_game


@pytest.fixture
def game_config():
    """Default game configuration with fixed seed for reproducibility."""
    return GameConfig(seed=42)


@pytest.fixture
def two_players():
    """Two test players."""
    return [Player(0, "Alice"), Player(1, "Bob")]


@pytest.fixture
def four_players():
    """Four test players."""
    return [
        Player(0, "Alice"),
        Player(1, "Bob"),
        Player(2, "Charlie"),
        Player(3, "Diana"),
    ]


@pytest.fixture
def basic_game(game_config, two_players):
    """Basic game with two players and fixed seed."""
    return create_game(game_config, two_players)


@pytest.fixture
def four_player_game(game_config, four_players):
    """Game with four players and fixed seed."""
    return create_game(game_config, four_players)

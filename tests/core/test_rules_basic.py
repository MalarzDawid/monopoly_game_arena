import pytest

from src.core import GameConfig, Player, create_game
from src.core.game.rules import get_legal_actions, ActionType


def test_basic_turn_flow():
    players = [Player(0, "Alice"), Player(1, "Bob")]
    game = create_game(GameConfig(seed=42), players)

    # Player 0 starts, should be able to roll dice
    actions = get_legal_actions(game, player_id=0)
    assert any(a.action_type == ActionType.ROLL_DICE for a in actions)

    # Player 1 should have no actions before turn
    actions_p1 = get_legal_actions(game, player_id=1)
    assert actions_p1 == []

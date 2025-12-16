import pytest

from monopoly.config import GameConfig
from monopoly.player import Player
from monopoly.rules import Action, apply_action
from monopoly.game import create_game, ActionType

from monopoly_game_arena.events.mapper import map_events


def test_map_basic_roll_move_land_events():
    cfg = GameConfig(seed=123)
    game = create_game(cfg, [Player(0, "A"), Player(1, "B")])

    # Apply a roll action to generate DICE_ROLL, MOVE, LAND
    current = game.get_current_player()
    assert current.player_id == 0
    ok = apply_action(game, Action(ActionType.ROLL_DICE))
    assert ok

    # Collect the last few events
    events = game.event_log.get_recent_events(5)
    mapped = map_events(game.board, events, player_positions={pid: p.position for pid, p in game.players.items()})

    # Ensure at least one dice_roll, move, and land were mapped with expected keys
    types = [e["event_type"] for e in mapped]
    assert "dice_roll" in types
    assert "move" in types
    assert "land" in types

    dice = next(e for e in mapped if e["event_type"] == "dice_roll")
    assert set(["die1", "die2", "total", "is_doubles"]).issubset(dice.keys())
    assert dice["total"] == dice["die1"] + dice["die2"]

    move = next(e for e in mapped if e["event_type"] == "move")
    assert set(["from_position", "to_position", "space_name"]).issubset(move.keys())

    land = next(e for e in mapped if e["event_type"] == "land")
    assert set(["position", "space_name"]).issubset(land.keys())


def test_map_rent_and_jail_events():
    cfg = GameConfig(seed=1)
    game = create_game(cfg, [Player(0, "A"), Player(1, "B")])

    # Simulate a rent payment directly
    # Both players start with enough cash, amount is arbitrary
    ok = game.pay_rent(0, 1, 50)
    assert ok

    events = game.event_log.get_recent_events(2)
    mapped = map_events(game.board, events, player_positions={pid: p.position for pid, p in game.players.items()})

    rent = next(e for e in mapped if e["event_type"] == "rent_payment")
    assert rent["payer_id"] == 0
    assert rent["owner_id"] == 1
    assert rent["amount"] == 50
    assert rent["payer_cash_after"] == game.players[0].cash
    assert rent["owner_cash_after"] == game.players[1].cash

    # Send to jail and map
    game.send_to_jail(0)
    jail_ev = game.event_log.get_recent_events(1)
    mapped_jail = map_events(game.board, jail_ev)
    assert mapped_jail[0]["event_type"] == "go_to_jail"

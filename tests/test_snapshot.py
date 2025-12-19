from src.core import GameConfig, Player, create_game

from snapshot import serialize_snapshot


def test_basic_snapshot_structure():
    game = create_game(GameConfig(seed=42), [Player(0, "A"), Player(1, "B")])

    snap = serialize_snapshot(game)

    # Core keys exist
    assert "turn_number" in snap
    assert "current_player_id" in snap
    assert "players" in snap and isinstance(snap["players"], list) and len(snap["players"]) == 2
    assert "bank" in snap and "houses_available" in snap["bank"] and "hotels_available" in snap["bank"]
    assert "decks" in snap and "chance" in snap["decks"] and "community_chest" in snap["decks"]

    # No sensitive deck data exposed (only counts)
    chance = snap["decks"]["chance"]
    assert set(chance.keys()) == {"cards_remaining", "discard_count", "held_count"}

    # Players contain public info only
    p0 = next(p for p in snap["players"] if p["player_id"] == 0)
    assert set(["player_id", "name", "cash", "position", "in_jail", "jail_turns", "jail_cards", "is_bankrupt", "properties"]).issubset(p0.keys())

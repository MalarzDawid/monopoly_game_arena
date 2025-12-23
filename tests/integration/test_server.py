import time
from typing import List

from fastapi.testclient import TestClient

from server.app import app


def _create_game(client: TestClient, players: int = 4, agent: str = "greedy", max_turns: int = 10) -> str:
    resp = client.post(
        "/games",
        json={"players": players, "agent": agent, "max_turns": max_turns},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "game_id" in data and isinstance(data["game_id"], str)
    return data["game_id"]


def test_create_game_and_snapshot():
    client = TestClient(app)
    gid = _create_game(client, players=4, max_turns=10)

    snap = client.get(f"/games/{gid}/snapshot")
    assert snap.status_code == 200
    data = snap.json()

    # Basic snapshot structure assertions
    assert "turn_number" in data
    assert "current_player_id" in data
    assert "players" in data and isinstance(data["players"], list) and len(data["players"]) == 4
    assert "bank" in data and "houses_available" in data["bank"]
    assert "decks" in data and "chance" in data["decks"] and "community_chest" in data["decks"]


def test_websocket_streams_initial_snapshot():
    client = TestClient(app)
    gid = _create_game(client, players=4, max_turns=10)

    with client.websocket_connect(f"/ws/games/{gid}") as ws:
        first = ws.receive_json()
        assert first["type"] == "snapshot"
        assert first["game_id"] == gid
        assert "snapshot" in first and isinstance(first["snapshot"], dict)


def test_snapshot_404_for_unknown_game():
    client = TestClient(app)
    resp = client.get("/games/doesnotexist/snapshot")
    assert resp.status_code == 404


def test_legal_actions_endpoint():
    client = TestClient(app)
    gid = _create_game(client, players=4, max_turns=10)
    resp = client.get(f"/games/{gid}/legal_actions")
    assert resp.status_code == 200
    data = resp.json()
    assert data["game_id"] == gid
    assert isinstance(data.get("actions"), list)


def test_apply_action_rejects_unknown_action():
    client = TestClient(app)
    gid = _create_game(client, players=4, max_turns=10)
    # Unknown action_type should be rejected (accepted=false)
    resp = client.post(f"/games/{gid}/actions", json={"action_type": "not_an_action", "params": {}})
    assert resp.status_code == 200
    body = resp.json()
    assert body["accepted"] is False

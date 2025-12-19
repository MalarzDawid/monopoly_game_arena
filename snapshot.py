"""
Public snapshot serialization of GameState.

Produces a sanitized, UI-friendly view of the current game without
exposing hidden information (e.g., deck order).
"""

from __future__ import annotations

from typing import Any, Dict, List

from src.core.game.game import GameState
from src.core.game.spaces import PropertySpace, RailroadSpace, UtilitySpace


def serialize_snapshot(game: GameState) -> Dict[str, Any]:
    """Serialize a GameState into a public, stable JSON dict.

    The snapshot includes:
    - turn_number and current_player_id
    - players with public info (cash, position, jail, properties with status)
    - bank supply counts
    - active auction (if any)
    - deck counts (remaining / discard / held) only
    """
    players: List[Dict[str, Any]] = []
    for pid, pstate in sorted(game.players.items()):
        props: List[Dict[str, Any]] = []
        for pos in sorted(pstate.properties):
            space = game.board.get_space(pos)
            ownership = game.property_ownership.get(pos)
            entry: Dict[str, Any] = {
                "position": pos,
                "name": space.name,
                "houses": ownership.houses if ownership else 0,
                "mortgaged": ownership.is_mortgaged if ownership else False,
            }
            if isinstance(space, PropertySpace):
                entry["color_group"] = space.color_group
            props.append(entry)

        players.append(
            {
                "player_id": pid,
                "name": pstate.name,
                "cash": pstate.cash,
                "position": pstate.position,
                "in_jail": pstate.in_jail,
                "jail_turns": pstate.jail_turns,
                "jail_cards": pstate.get_out_of_jail_cards,
                "is_bankrupt": pstate.is_bankrupt,
                "properties": props,
            }
        )

    auction = None
    if game.active_auction is not None:
        a = game.active_auction
        auction = {
            "property_position": a.property_position,
            "property_name": a.property_name,
            "current_bid": a.current_bid,
            "high_bidder": a.high_bidder,
            "active_bidders": sorted(list(a.active_bidders)),
            "is_complete": a.is_complete,
        }

    snapshot: Dict[str, Any] = {
        "turn_number": game.turn_number,
        "current_player_id": game.get_current_player().player_id,
        "players": players,
        "bank": {
            "houses_available": game.bank.houses_available,
            "hotels_available": game.bank.hotels_available,
        },
        "auction": auction,
        "decks": {
            "chance": {
                "cards_remaining": len(game.chance_deck.cards),
                "discard_count": len(game.chance_deck.discard_pile),
                "held_count": len(game.chance_deck.held_cards),
            },
            "community_chest": {
                "cards_remaining": len(game.community_chest_deck.cards),
                "discard_count": len(game.community_chest_deck.discard_pile),
                "held_count": len(game.community_chest_deck.held_cards),
            },
        },
    }

    return snapshot

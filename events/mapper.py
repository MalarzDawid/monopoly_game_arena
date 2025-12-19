"""
Mapping from internal EventLog objects to canonical public JSON events.

The internal engine emits GameEvent objects where:
- event_type is money.EventType
- player_id is optional
- details may be nested (often passed as details={...})

This module produces stable, UI/JSONL-friendly dicts with consistent
event_type strings and payload keys.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from src.core.game.board import Board
from src.core.game.money import EventType, GameEvent


def _flatten_details(details: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize nested details payloads from engine logs."""
    if not details:
        return {}
    if "details" in details and isinstance(details["details"], dict):
        return details["details"]
    return details


def _space_name(board: Board, position: Optional[int]) -> Optional[str]:
    if position is None:
        return None
    try:
        return board.get_space(position).name
    except Exception:
        return None


def map_event(board: Board, event: GameEvent, *, player_positions: Optional[Dict[int, int]] = None) -> Dict[str, Any]:
    """
    Map a single GameEvent to a canonical JSON dict.

    Args:
        board: Board instance (for resolving space names)
        event: internal event object
        player_positions: optional mapping player_id->position for enrichment

    Returns:
        dict with keys: event_type (str), player_id (optional), and event-specific fields
    """
    etype = event.event_type.value
    d = _flatten_details(event.details)

    base: Dict[str, Any] = {"event_type": etype}
    if event.player_id is not None:
        base["player_id"] = event.player_id

    # Dice
    if event.event_type == EventType.DICE_ROLL:
        base.update(
            die1=d.get("die1"),
            die2=d.get("die2"),
            total=d.get("total"),
            is_doubles=d.get("doubles", d.get("is_doubles")),
        )
        return base

    # Movement
    if event.event_type == EventType.MOVE:
        from_pos = d.get("from") or d.get("from_position")
        to_pos = d.get("to") or d.get("to_position")
        base.update(
            from_position=from_pos,
            to_position=to_pos,
            spaces=d.get("spaces"),
            direct=d.get("direct", False),
            space_name=_space_name(board, to_pos),
        )
        return base

    if event.event_type == EventType.PASS_GO:
        base.update(amount=d.get("amount"), cash_after=d.get("new_balance"))
        return base

    if event.event_type == EventType.LAND:
        position = d.get("position")
        space_name = d.get("space") or d.get("space_name") or _space_name(board, position)
        base.update(position=position, space_name=space_name)
        return base

    # Purchases and payments
    if event.event_type == EventType.PURCHASE:
        base.update(
            property_name=d.get("property") or d.get("property_name"),
            position=d.get("position"),
            price=d.get("price"),
            cash_after=d.get("new_balance") or d.get("cash_after"),
        )
        return base

    if event.event_type == EventType.RENT_PAYMENT:
        payer_id = event.player_id
        owner_id = d.get("owner") or d.get("owner_id")
        # Derive property name from payer's current position if possible
        prop_name: Optional[str] = None
        if payer_id is not None and player_positions is not None:
            pos = player_positions.get(payer_id)
            if pos is not None:
                prop_name = _space_name(board, pos)
        base.update(
            payer_id=payer_id,
            owner_id=owner_id,
            amount=d.get("amount"),
            payer_cash_after=d.get("payer_balance") or d.get("payer_cash_after"),
            owner_cash_after=d.get("owner_balance") or d.get("owner_cash_after"),
        )
        if prop_name:
            base["property_name"] = prop_name
        return base

    if event.event_type == EventType.TAX_PAYMENT:
        base.update(amount=d.get("amount"), cash_after=d.get("new_balance"))
        return base

    # Cards
    if event.event_type == EventType.CARD_DRAW:
        base.update(deck=d.get("deck"), card=d.get("card"))
        return base

    if event.event_type == EventType.CARD_EFFECT:
        base.update(
            card=d.get("card"),
            effect_type=d.get("type") or d.get("effect_type"),
            cash_before=d.get("cash_before"),
            cash_after=d.get("cash_after"),
        )
        if "amount" in d:
            base["amount"] = d.get("amount")
        return base

    # Buildings
    if event.event_type == EventType.BUILD_HOUSE:
        base.update(
            property_name=d.get("property"),
            position=d.get("position"),
            cost=d.get("cost"),
            house_count=d.get("houses"),
            cash_after=d.get("new_balance"),
        )
        return base

    if event.event_type == EventType.BUILD_HOTEL:
        base.update(
            property_name=d.get("property"),
            position=d.get("position"),
            cost=d.get("cost"),
            cash_after=d.get("new_balance"),
        )
        return base

    if event.event_type == EventType.SELL_BUILDING:
        base.update(
            property_name=d.get("property"),
            position=d.get("position"),
            type=d.get("type"),
            sale_price=d.get("sale_price"),
            house_count=d.get("houses"),
            cash_after=d.get("new_balance"),
        )
        return base

    # Mortgage
    if event.event_type == EventType.MORTGAGE:
        base.update(
            property_name=d.get("property"),
            position=d.get("position"),
            value=d.get("value"),
            cash_after=d.get("new_balance"),
        )
        return base

    if event.event_type == EventType.UNMORTGAGE:
        base.update(
            property_name=d.get("property"),
            position=d.get("position"),
            cost=d.get("cost"),
            cash_after=d.get("new_balance"),
        )
        return base

    # Auctions
    if event.event_type == EventType.AUCTION_START:
        base.update(
            property_name=d.get("property"),
            position=d.get("position"),
            eligible_players=d.get("players", []),
        )
        return base

    if event.event_type == EventType.AUCTION_BID:
        base.update(
            property_name=d.get("property"),
            bid_amount=d.get("amount") or d.get("bid_amount"),
            bid_number=d.get("bid_number"),
        )
        return base

    if event.event_type == EventType.AUCTION_PASS:
        remaining = d.get("remaining_bidders", [])
        base.update(
            property_name=d.get("property"),
            remaining_bidders=remaining,
            remaining_count=len(remaining) if isinstance(remaining, list) else None,
        )
        return base

    if event.event_type == EventType.AUCTION_END:
        base.update(
            property_name=d.get("property"),
            position=d.get("position"),
            winning_bid=d.get("winning_bid"),
            winner_id=d.get("winner"),
        )
        return base

    # Jail + game state
    if event.event_type == EventType.GO_TO_JAIL:
        return base

    if event.event_type == EventType.JAIL_ATTEMPT:
        base.update(attempt=d.get("attempt"), is_doubles=d.get("doubles"))
        return base

    if event.event_type == EventType.JAIL_RELEASE:
        if "method" in d:
            base.update(method=d.get("method"))
        if "amount" in d:
            base.update(amount=d.get("amount"))
        return base

    if event.event_type == EventType.TURN_START:
        base.update(turn_number=(d.get("turn") if "turn" in d else d.get("turn_number")))
        return base

    if event.event_type == EventType.GAME_START:
        players = d.get("players") or d.get("player_names") or []
        base.update(
            player_names=players,
            num_players=len(players),
            starting_cash=d.get("starting_cash"),
            seed=d.get("seed"),
        )
        return base

    if event.event_type == EventType.GAME_END:
        # Prefer explicit winner from details if provided; otherwise fall back to player_id
        base.update(
            reason=d.get("reason"),
            winner_id=(d.get("winner") if d.get("winner") is not None else event.player_id),
        )
        if "net_worth" in d:
            base.update(winner_networth=d.get("net_worth"))
        return base

    # Money transfers / generic payments
    if event.event_type in (EventType.PAYMENT, EventType.TRANSFER):
        for key in ("amount", "reason", "to", "from"):
            if key in d:
                base[key] = d[key]
        return base

    # Bankruptcy
    if event.event_type == EventType.BANKRUPTCY:
        base.update(creditor_id=d.get("creditor"))
        return base

    # Default: echo raw fields
    base.update(d)
    return base


def map_events(board: Board, events: Iterable[GameEvent], *, player_positions: Optional[Dict[int, int]] = None) -> List[Dict[str, Any]]:
    """Map a sequence of GameEvent objects.

    Args:
        board: Board instance
        events: iterable of GameEvent
        player_positions: optional snapshot of player positions for enrichment
    """
    positions = player_positions or {}
    mapped: List[Dict[str, Any]] = []
    for idx, ev in enumerate(events):
        mev = map_event(board, ev, player_positions=positions)
        mev["seq"] = idx
        mapped.append(mev)
    return mapped

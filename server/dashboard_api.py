from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from data import get_session

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


async def _fetch_one(session: AsyncSession, query: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    result = await session.execute(text(query), params)
    row = result.mappings().first()
    return dict(row) if row else None


async def _fetch_all(session: AsyncSession, query: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
    result = await session.execute(text(query), params)
    return [dict(row) for row in result.mappings().all()]


@router.get("/summary")
async def dashboard_summary(session: AsyncSession = Depends(get_session)) -> Dict[str, Any]:
    query = """
        SELECT
            COUNT(*) as total_games,
            COUNT(*) FILTER (WHERE status = 'finished') as finished_games,
            COUNT(*) FILTER (WHERE status = 'running') as running_games,
            AVG(total_turns) FILTER (WHERE status = 'finished') as avg_turns,
            MIN(created_at) as first_game,
            MAX(created_at) as last_game
        FROM games
    """
    row = await _fetch_one(session, query, {})
    return row or {}


@router.get("/timeline")
async def dashboard_timeline(
    days: int = Query(30, ge=1, le=365),
    session: AsyncSession = Depends(get_session),
) -> List[Dict[str, Any]]:
    date_from = datetime.now() - timedelta(days=days)
    date_to = datetime.now()
    query = """
        SELECT
            DATE(created_at) as date,
            COUNT(*) as games_count,
            AVG(total_turns) FILTER (WHERE status = 'finished') as avg_turns,
            COUNT(*) FILTER (WHERE EXISTS (
                SELECT 1 FROM players p WHERE p.game_uuid = games.id AND p.agent_type = 'llm'
            )) as llm_games_count
        FROM games
        WHERE created_at >= :date_from AND created_at <= :date_to
        GROUP BY DATE(created_at)
        ORDER BY date
    """
    return await _fetch_all(session, query, {"date_from": date_from, "date_to": date_to})


@router.get("/win_rates/agents")
async def win_rates_by_agent(session: AsyncSession = Depends(get_session)) -> List[Dict[str, Any]]:
    query = """
        SELECT
            p.agent_type,
            COUNT(DISTINCT p.game_uuid) as games_played,
            SUM(CASE WHEN p.is_winner THEN 1 ELSE 0 END) as wins,
            ROUND(
                SUM(CASE WHEN p.is_winner THEN 1 ELSE 0 END)::numeric /
                NULLIF(COUNT(DISTINCT p.game_uuid), 0) * 100,
                2
            ) as win_rate,
            AVG(p.final_net_worth) FILTER (WHERE p.is_winner) as avg_winner_net_worth
        FROM players p
        JOIN games g ON p.game_uuid = g.id
        WHERE g.status = 'finished'
        GROUP BY p.agent_type
        ORDER BY win_rate DESC
    """
    return await _fetch_all(session, query, {})


@router.get("/win_rates/llm")
async def win_rates_by_llm(session: AsyncSession = Depends(get_session)) -> List[Dict[str, Any]]:
    query = """
        WITH llm_decision_info AS (
            SELECT DISTINCT ON (d.game_uuid, d.player_id)
                d.game_uuid,
                d.player_id,
                d.model_version,
                d.strategy_description
            FROM llm_decisions d
            ORDER BY d.game_uuid, d.player_id, d.sequence_number DESC
        ),
        llm_players AS (
            SELECT
                p.game_uuid,
                p.player_id,
                p.is_winner,
                p.final_net_worth,
                p.is_bankrupt,
                COALESCE(
                    ldi.model_version,
                    p.llm_model_name,
                    'unknown'
                ) as model_version,
                COALESCE(
                    ldi.strategy_description,
                    p.llm_strategy_profile->>'name',
                    'unknown'
                ) as strategy_description
            FROM players p
            JOIN games g ON p.game_uuid = g.id
            LEFT JOIN llm_decision_info ldi
                ON ldi.game_uuid = p.game_uuid AND ldi.player_id = p.player_id
            WHERE p.agent_type = 'llm' AND g.status = 'finished'
        )
        SELECT
            model_version,
            strategy_description,
            COUNT(*) as players_count,
            COUNT(*) FILTER (WHERE is_winner) as wins,
            ROUND(
                COUNT(*) FILTER (WHERE is_winner)::numeric / NULLIF(COUNT(*),0) * 100,
                2
            ) as win_rate,
            AVG(final_net_worth) FILTER (WHERE is_winner) as avg_winner_net_worth
        FROM llm_players
        GROUP BY model_version, strategy_description
        ORDER BY win_rate DESC NULLS LAST
    """
    return await _fetch_all(session, query, {})


@router.get("/games/recent")
async def recent_games(limit: int = 10, session: AsyncSession = Depends(get_session)) -> List[Dict[str, Any]]:
    query = """
        SELECT
            g.game_id,
            g.status,
            g.created_at,
            g.finished_at,
            g.total_turns,
            g.winner_id
        FROM games g
        ORDER BY g.created_at DESC
        LIMIT :limit
    """
    return await _fetch_all(session, query, {"limit": limit})


@router.get("/games/{game_id}/events")
async def events_for_game(
    game_id: str,
    limit: int = 1000,
    session: AsyncSession = Depends(get_session),
) -> List[Dict[str, Any]]:
    query = """
        SELECT
            e.sequence_number,
            e.turn_number,
            e.event_type,
            e.timestamp,
            e.payload,
            e.actor_player_id
        FROM game_events e
        JOIN games g ON e.game_uuid = g.id
        WHERE g.game_id = :game_id
        ORDER BY e.sequence_number
        LIMIT :limit
    """
    return await _fetch_all(session, query, {"game_id": game_id, "limit": limit})


@router.get("/games/{game_id}/players")
async def players_for_game(game_id: str, session: AsyncSession = Depends(get_session)) -> List[Dict[str, Any]]:
    query = """
        SELECT
            p.player_id,
            p.name,
            p.agent_type,
            p.is_winner,
            p.final_cash,
            p.final_net_worth
        FROM players p
        JOIN games g ON p.game_uuid = g.id
        WHERE g.game_id = :game_id
        ORDER BY p.player_id
    """
    return await _fetch_all(session, query, {"game_id": game_id})


@router.get("/games/{game_id}/latest_events")
async def latest_events_for_game(game_id: str, limit: int = 10, session: AsyncSession = Depends(get_session)) -> List[Dict[str, Any]]:
    query = """
        SELECT
            e.sequence_number,
            e.turn_number,
            e.event_type,
            e.timestamp,
            e.payload,
            e.actor_player_id
        FROM game_events e
        JOIN games g ON e.game_uuid = g.id
        WHERE g.game_id = :game_id
        ORDER BY e.sequence_number DESC
        LIMIT :limit
    """
    rows = await _fetch_all(session, query, {"game_id": game_id, "limit": limit})
    return list(reversed(rows))


@router.get("/games/{game_id}/llm_decisions")
async def llm_decisions_for_game(
    game_id: str,
    player_id: Optional[int] = None,
    limit: int = 100,
    session: AsyncSession = Depends(get_session),
) -> List[Dict[str, Any]]:
    """
    Return LLM decisions for a given game (optionally filtered by player).
    """
    base_query = """
        SELECT
            d.sequence_number,
            d.turn_number,
            d.player_id,
            d.timestamp,
            d.reasoning,
            d.chosen_action,
            d.strategy_description,
            d.processing_time_ms,
            d.model_version
        FROM llm_decisions d
        JOIN games g ON d.game_uuid = g.id
        WHERE g.game_id = :game_id
    """
    params: Dict[str, Any] = {"game_id": game_id, "limit": limit}
    if player_id is not None:
        base_query += " AND d.player_id = :player_id"
        params["player_id"] = player_id

    base_query += " ORDER BY d.sequence_number LIMIT :limit"
    return await _fetch_all(session, base_query, params)

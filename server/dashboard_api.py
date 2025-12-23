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


# ============================================================================
# GLOBAL ANALYTICS ENDPOINTS
# ============================================================================

@router.get("/global_stats")
async def global_stats(session: AsyncSession = Depends(get_session)) -> Dict[str, Any]:
    """
    Global KPI statistics across all games.
    """
    query = """
        WITH game_stats AS (
            SELECT
                COUNT(*) as total_games,
                SUM(total_turns) as total_turns,
                COUNT(*) FILTER (WHERE status = 'finished') as finished_games
            FROM games
        ),
        player_stats AS (
            SELECT
                COUNT(*) FILTER (WHERE is_bankrupt = true) as total_bankruptcies
            FROM players
        ),
        event_stats AS (
            SELECT
                COUNT(*) FILTER (WHERE event_type = 'purchase') as total_properties_bought,
                COUNT(*) FILTER (WHERE event_type IN ('purchase', 'trade', 'rent_payment', 'auction_end')) as total_transactions
            FROM game_events
        )
        SELECT
            gs.total_games,
            COALESCE(gs.total_turns, 0) as total_turns,
            gs.finished_games,
            ps.total_bankruptcies,
            es.total_properties_bought,
            es.total_transactions
        FROM game_stats gs, player_stats ps, event_stats es
    """
    row = await _fetch_one(session, query, {})
    return row or {
        "total_games": 0,
        "total_turns": 0,
        "finished_games": 0,
        "total_bankruptcies": 0,
        "total_properties_bought": 0,
        "total_transactions": 0,
    }


@router.get("/model_leaderboard")
async def model_leaderboard(session: AsyncSession = Depends(get_session)) -> List[Dict[str, Any]]:
    """
    Leaderboard grouping by model/agent type with win rates and average ROI.
    Groups LLM players by llm_model_name and non-LLM by agent_type.
    Falls back to llm_decisions table for older games without player LLM info.
    Shows ALL model/strategy combinations that exist in the database.
    """
    query = """
        WITH llm_decision_info AS (
            -- Get model info from llm_decisions for fallback
            SELECT DISTINCT ON (d.game_uuid, d.player_id)
                d.game_uuid,
                d.player_id,
                d.model_version,
                d.strategy_description
            FROM llm_decisions d
            ORDER BY d.game_uuid, d.player_id, d.sequence_number DESC
        ),
        player_info AS (
            -- All players with their model/strategy info
            SELECT
                p.game_uuid,
                p.player_id,
                p.agent_type,
                CASE
                    WHEN p.agent_type = 'llm' THEN COALESCE(
                        p.llm_model_name,
                        ldi.model_version,
                        'unknown_llm'
                    )
                    ELSE p.agent_type
                END as model_name,
                CASE
                    WHEN p.agent_type = 'llm' THEN COALESCE(
                        p.llm_strategy_profile->>'name',
                        ldi.strategy_description,
                        'Unknown'
                    )
                    ELSE 'Scripted'
                END as strategy_profile,
                g.status as game_status,
                p.is_winner,
                p.is_bankrupt,
                p.final_net_worth,
                p.final_cash
            FROM players p
            JOIN games g ON p.game_uuid = g.id
            LEFT JOIN llm_decision_info ldi ON ldi.game_uuid = p.game_uuid AND ldi.player_id = p.player_id
        )
        SELECT
            model_name,
            strategy_profile,
            COUNT(DISTINCT game_uuid) as games_played,
            COUNT(DISTINCT game_uuid) FILTER (WHERE game_status = 'finished') as finished_games,
            SUM(CASE WHEN is_winner THEN 1 ELSE 0 END) as wins,
            SUM(CASE WHEN is_bankrupt THEN 1 ELSE 0 END) as bankruptcies,
            CASE
                WHEN COUNT(*) FILTER (WHERE game_status = 'finished') > 0 THEN
                    ROUND(
                        SUM(CASE WHEN is_winner THEN 1 ELSE 0 END)::numeric /
                        COUNT(*) FILTER (WHERE game_status = 'finished') * 100,
                        2
                    )
                ELSE NULL
            END as win_rate,
            ROUND(AVG(COALESCE(final_net_worth, 0)) FILTER (WHERE game_status = 'finished')::numeric, 0) as avg_net_worth,
            ROUND(AVG(COALESCE(final_cash, 0)) FILTER (WHERE game_status = 'finished')::numeric, 0) as avg_final_cash
        FROM player_info
        GROUP BY model_name, strategy_profile
        ORDER BY win_rate DESC NULLS LAST, games_played DESC
    """
    return await _fetch_all(session, query, {})


@router.get("/luck_vs_skill")
async def luck_vs_skill(session: AsyncSession = Depends(get_session)) -> List[Dict[str, Any]]:
    """
    Scatter plot data: Average dice roll (luck) vs Win rate (skill) per model/agent.
    """
    query = """
        WITH llm_decision_info AS (
            SELECT DISTINCT ON (d.game_uuid, d.player_id)
                d.game_uuid,
                d.player_id,
                d.model_version
            FROM llm_decisions d
            ORDER BY d.game_uuid, d.player_id, d.sequence_number DESC
        ),
        dice_rolls AS (
            SELECT
                e.game_uuid,
                e.actor_player_id as player_id,
                (e.payload->>'die1')::int + (e.payload->>'die2')::int as roll_total
            FROM game_events e
            WHERE e.event_type = 'dice_roll'
                AND e.payload->>'die1' IS NOT NULL
                AND e.payload->>'die2' IS NOT NULL
        ),
        player_dice_avg AS (
            SELECT
                p.game_uuid,
                p.player_id,
                CASE
                    WHEN p.agent_type = 'llm' THEN COALESCE(
                        p.llm_model_name,
                        ldi.model_version,
                        'unknown_llm'
                    )
                    ELSE p.agent_type
                END as model_name,
                p.is_winner,
                AVG(dr.roll_total) as avg_dice
            FROM players p
            JOIN games g ON p.game_uuid = g.id
            LEFT JOIN llm_decision_info ldi ON ldi.game_uuid = p.game_uuid AND ldi.player_id = p.player_id
            LEFT JOIN dice_rolls dr ON dr.game_uuid = p.game_uuid AND dr.player_id = p.player_id
            WHERE g.status = 'finished'
            GROUP BY p.game_uuid, p.player_id, p.agent_type, p.llm_model_name, ldi.model_version, p.is_winner
        )
        SELECT
            model_name,
            ROUND(AVG(avg_dice)::numeric, 2) as avg_dice_roll,
            ROUND(
                SUM(CASE WHEN is_winner THEN 1 ELSE 0 END)::numeric /
                NULLIF(COUNT(*), 0) * 100,
                2
            ) as win_rate,
            COUNT(*) as total_games
        FROM player_dice_avg
        WHERE avg_dice IS NOT NULL
        GROUP BY model_name
        HAVING COUNT(*) >= 1
        ORDER BY win_rate DESC
    """
    return await _fetch_all(session, query, {})


@router.get("/kill_zones")
async def kill_zones(session: AsyncSession = Depends(get_session)) -> List[Dict[str, Any]]:
    """
    Properties where most bankruptcies occurred (rent payments that led to bankruptcy).
    Uses the position from the last rent_payment before a bankruptcy event.
    """
    # Property names mapping (Monopoly board positions)
    property_names = {
        1: "Mediterranean Ave", 3: "Baltic Ave",
        6: "Oriental Ave", 8: "Vermont Ave", 9: "Connecticut Ave",
        11: "St. Charles Place", 13: "States Ave", 14: "Virginia Ave",
        16: "St. James Place", 18: "Tennessee Ave", 19: "New York Ave",
        21: "Kentucky Ave", 23: "Indiana Ave", 24: "Illinois Ave",
        26: "Atlantic Ave", 27: "Ventnor Ave", 29: "Marvin Gardens",
        31: "Pacific Ave", 32: "North Carolina Ave", 34: "Pennsylvania Ave",
        37: "Park Place", 39: "Boardwalk",
        5: "Reading Railroad", 15: "Pennsylvania Railroad", 25: "B&O Railroad", 35: "Short Line",
        12: "Electric Company", 28: "Water Works",
    }

    query = """
        WITH bankruptcy_events AS (
            SELECT
                e.game_uuid,
                e.actor_player_id as bankrupt_player_id,
                e.sequence_number as bankruptcy_seq,
                e.turn_number
            FROM game_events e
            WHERE e.event_type = 'bankruptcy'
        ),
        last_rent_before_bankruptcy AS (
            SELECT DISTINCT ON (b.game_uuid, b.bankrupt_player_id)
                b.game_uuid,
                b.bankrupt_player_id,
                (rent.payload->>'position')::int as position
            FROM bankruptcy_events b
            JOIN game_events rent ON
                rent.game_uuid = b.game_uuid
                AND rent.event_type = 'rent_payment'
                AND rent.sequence_number < b.bankruptcy_seq
                AND (rent.payload->>'payer_id')::int = b.bankrupt_player_id
            ORDER BY b.game_uuid, b.bankrupt_player_id, rent.sequence_number DESC
        )
        SELECT
            position,
            COUNT(*) as bankruptcy_count
        FROM last_rent_before_bankruptcy
        WHERE position IS NOT NULL
        GROUP BY position
        ORDER BY bankruptcy_count DESC
        LIMIT 20
    """
    rows = await _fetch_all(session, query, {})

    # Add property names to results
    for row in rows:
        pos = row.get("position")
        row["property_name"] = property_names.get(pos, f"Position {pos}")

    return rows


@router.get("/strategy_property_correlation")
async def strategy_property_correlation(session: AsyncSession = Depends(get_session)) -> List[Dict[str, Any]]:
    """
    Heatmap data showing which property groups each strategy tends to purchase.
    Returns purchase counts grouped by strategy and property color group.
    """
    # Property position to color group mapping
    property_groups = {
        1: "Brown", 3: "Brown",
        6: "Light Blue", 8: "Light Blue", 9: "Light Blue",
        11: "Pink", 13: "Pink", 14: "Pink",
        16: "Orange", 18: "Orange", 19: "Orange",
        21: "Red", 23: "Red", 24: "Red",
        26: "Yellow", 27: "Yellow", 29: "Yellow",
        31: "Green", 32: "Green", 34: "Green",
        37: "Dark Blue", 39: "Dark Blue",
        5: "Railroad", 15: "Railroad", 25: "Railroad", 35: "Railroad",
        12: "Utility", 28: "Utility",
    }

    query = """
        WITH llm_decision_info AS (
            SELECT DISTINCT ON (d.game_uuid, d.player_id)
                d.game_uuid,
                d.player_id,
                d.strategy_description
            FROM llm_decisions d
            ORDER BY d.game_uuid, d.player_id, d.sequence_number DESC
        ),
        player_strategies AS (
            SELECT
                p.game_uuid,
                p.player_id,
                CASE
                    WHEN p.agent_type = 'llm' THEN COALESCE(
                        p.llm_strategy_profile->>'name',
                        ldi.strategy_description,
                        'Unknown'
                    )
                    WHEN p.agent_type = 'greedy' THEN 'Greedy'
                    WHEN p.agent_type = 'random' THEN 'Random'
                    ELSE p.agent_type
                END as strategy
            FROM players p
            LEFT JOIN llm_decision_info ldi ON ldi.game_uuid = p.game_uuid AND ldi.player_id = p.player_id
        ),
        purchases AS (
            SELECT
                e.game_uuid,
                e.actor_player_id as player_id,
                (e.payload->>'position')::int as position
            FROM game_events e
            WHERE e.event_type = 'purchase'
                AND e.payload->>'position' IS NOT NULL
        )
        SELECT
            ps.strategy,
            p.position,
            COUNT(*) as purchase_count
        FROM purchases p
        JOIN player_strategies ps ON ps.game_uuid = p.game_uuid AND ps.player_id = p.player_id
        WHERE ps.strategy IS NOT NULL
        GROUP BY ps.strategy, p.position
        ORDER BY ps.strategy, p.position
    """
    rows = await _fetch_all(session, query, {})

    # Group by strategy and add color group info
    result = []
    for row in rows:
        position = row.get("position")
        color_group = property_groups.get(position, "Other")
        result.append({
            "strategy": row["strategy"],
            "position": position,
            "color_group": color_group,
            "purchase_count": row["purchase_count"],
        })

    return result


@router.get("/game_duration_histogram")
async def game_duration_histogram(
    bucket_size: int = Query(20, ge=5, le=100),
    session: AsyncSession = Depends(get_session),
) -> List[Dict[str, Any]]:
    """
    Histogram of game durations (number of turns).
    Returns buckets with counts of games that ended within each range.
    """
    query = """
        WITH buckets AS (
            SELECT
                FLOOR(total_turns / :bucket_size) * :bucket_size as bucket_start,
                FLOOR(total_turns / :bucket_size) * :bucket_size + :bucket_size - 1 as bucket_end,
                COUNT(*) as game_count
            FROM games
            WHERE status = 'finished' AND total_turns > 0
            GROUP BY FLOOR(total_turns / :bucket_size)
        )
        SELECT
            bucket_start,
            bucket_end,
            CONCAT(bucket_start::text, '-', bucket_end::text) as bucket_label,
            game_count
        FROM buckets
        ORDER BY bucket_start
    """
    return await _fetch_all(session, query, {"bucket_size": bucket_size})

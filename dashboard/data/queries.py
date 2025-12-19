"""
Database queries for the dashboard.

Uses synchronous psycopg2 for compatibility with Dash callbacks.
"""

import json
import logging
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import httpx
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor

from dashboard.config import DATABASE_URL

logger = logging.getLogger(__name__)

# API client
from dashboard.data.api import fetch_json


@contextmanager
def get_connection():
    """Get a database connection context manager."""
    conn = None
    try:
        conn = psycopg2.connect(DATABASE_URL)
        yield conn
    except psycopg2.OperationalError as e:
        logger.error(f"Database connection failed: {e}")
        raise
    except psycopg2.Error as e:
        logger.error(f"Database error: {e}")
        raise
    finally:
        if conn:
            conn.close()


def execute_query(query: str, params: tuple = None) -> List[Dict[str, Any]]:
    """Execute a query and return results as list of dicts."""
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            return [dict(row) for row in cur.fetchall()]


def execute_query_df(query: str, params: tuple = None) -> pd.DataFrame:
    """Execute a query and return results as DataFrame."""
    results = execute_query(query, params)
    return pd.DataFrame(results) if results else pd.DataFrame()


# ============================================================================
# Game Queries
# ============================================================================

def get_all_games(
    limit: int = 100,
    offset: int = 0,
    status: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
) -> pd.DataFrame:
    """Get all games with optional filtering (API-first, DB fallback)."""
    data = fetch_json(
        "/api/games",
        params={"limit": limit, "offset": offset, "status": status},
    )
    if data and "games" in data:
        df = pd.DataFrame(data["games"])
        if date_from:
            df = df[df["created_at"] >= pd.to_datetime(date_from)]
        if date_to:
            df = df[df["created_at"] <= pd.to_datetime(date_to)]
        return df

    query = """
        SELECT
            g.id,
            g.game_id,
            g.status,
            g.created_at,
            g.started_at,
            g.finished_at,
            g.winner_id,
            g.total_turns,
            g.config,
            g.metadata
        FROM games g
        WHERE 1=1
    """
    params = []

    if status:
        query += " AND g.status = %s"
        params.append(status)

    if date_from:
        query += " AND g.created_at >= %s"
        params.append(date_from)

    if date_to:
        query += " AND g.created_at <= %s"
        params.append(date_to)

    query += " ORDER BY g.created_at DESC LIMIT %s OFFSET %s"
    params.extend([limit, offset])

    return execute_query_df(query, tuple(params))


def get_game_by_id(game_id: str) -> Optional[Dict[str, Any]]:
    """Get a single game by its game_id (API-first, DB fallback)."""
    data = fetch_json(f"/api/games/{game_id}/history")
    if data and "game" in data:
        return data["game"]

    query = """
        SELECT
            g.id,
            g.game_id,
            g.status,
            g.created_at,
            g.started_at,
            g.finished_at,
            g.winner_id,
            g.total_turns,
            g.config,
            g.metadata
        FROM games g
        WHERE g.game_id = %s
    """
    results = execute_query(query, (game_id,))
    return results[0] if results else None


def get_game_players(game_id: str) -> pd.DataFrame:
    """Get all players for a game."""
    query = """
        SELECT
            p.player_id,
            p.name,
            p.agent_type,
            p.final_cash,
            p.final_net_worth,
            p.is_winner,
            p.is_bankrupt,
            p.placement,
            p.llm_model_name,
            p.llm_strategy_profile
        FROM players p
        JOIN games g ON p.game_uuid = g.id
        WHERE g.game_id = %s
        ORDER BY p.player_id
    """
    return execute_query_df(query, (game_id,))


def get_game_events(
    game_id: str,
    event_types: Optional[List[str]] = None,
    turn_number: Optional[int] = None,
    limit: int = 1000,
) -> pd.DataFrame:
    """Get events for a game (API-first, DB fallback)."""
    data = fetch_json(f"/api/games/{game_id}/history")
    if data and "events" in data:
        df = pd.DataFrame(data["events"])
        if event_types:
            df = df[df["event_type"].isin(event_types)]
        if turn_number is not None:
            df = df[df["turn_number"] == turn_number]
        if limit:
            df = df.head(limit)
        return df

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
        WHERE g.game_id = %s
    """
    params = [game_id]

    if event_types:
        query += " AND e.event_type = ANY(%s)"
        params.append(event_types)

    if turn_number is not None:
        query += " AND e.turn_number = %s"
        params.append(turn_number)

    query += " ORDER BY e.sequence_number LIMIT %s"
    params.append(limit)

    return execute_query_df(query, tuple(params))


def get_latest_game_events(game_id: str, limit: int = 10) -> pd.DataFrame:
    """Get the most recent events for a game (newest first) via API history."""
    data = fetch_json(f"/api/games/{game_id}/history")
    if data and "events" in data:
        df = pd.DataFrame(data["events"])
        if df.empty:
            return df
        df = df.sort_values("sequence_number", ascending=False).head(limit)
        return df
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
        WHERE g.game_id = %s
        ORDER BY e.sequence_number DESC
        LIMIT %s
    """
    return execute_query_df(query, (game_id, limit))


def get_cash_timeline_data(game_id: str) -> pd.DataFrame:
    """
    Get cash values over time for each player in a game.

    Reconstructs cash timeline from various event types:
    - purchase: cash_after for buyer
    - rent_payment: payer_cash_after, owner_cash_after
    - auction_end: winner_cash_after
    - pass_go: player gets +$200
    - tax_payment: player pays tax

    Returns DataFrame with columns: turn_number, player_id, player_name, cash
    """
    query = """
        WITH game_info AS (
            SELECT id as game_uuid FROM games WHERE game_id = %s
        ),
        players_info AS (
            SELECT player_id, name as player_name
            FROM players p
            JOIN game_info gi ON p.game_uuid = gi.game_uuid
        ),
        -- Starting cash for all players (turn 0)
        starting_cash AS (
            SELECT
                0 as turn_number,
                p.player_id,
                p.player_name,
                1500 as cash,
                0 as sequence_number
            FROM players_info p
        ),
        -- Cash changes from purchase events
        purchase_cash AS (
            SELECT
                e.turn_number,
                (e.payload->>'player_id')::int as player_id,
                e.payload->>'player_name' as player_name,
                (e.payload->>'cash_after')::int as cash,
                e.sequence_number
            FROM game_events e
            JOIN game_info gi ON e.game_uuid = gi.game_uuid
            WHERE e.event_type = 'purchase'
                AND e.payload->>'cash_after' IS NOT NULL
        ),
        -- Cash changes from rent payments (payer)
        rent_payer_cash AS (
            SELECT
                e.turn_number,
                (e.payload->>'payer_id')::int as player_id,
                e.payload->>'payer_name' as player_name,
                (e.payload->>'payer_cash_after')::int as cash,
                e.sequence_number
            FROM game_events e
            JOIN game_info gi ON e.game_uuid = gi.game_uuid
            WHERE e.event_type = 'rent_payment'
                AND e.payload->>'payer_cash_after' IS NOT NULL
                AND e.payload->>'payer_id' IS NOT NULL
        ),
        -- Cash changes from rent payments (owner)
        rent_owner_cash AS (
            SELECT
                e.turn_number,
                COALESCE(
                    (e.payload->>'owner_id')::int,
                    (SELECT (e2.payload->>'player_id')::int
                     FROM game_events e2
                     WHERE e2.game_uuid = e.game_uuid
                       AND e2.event_type = 'purchase'
                       AND e2.payload->>'property_name' = e.payload->>'property_name'
                     ORDER BY e2.sequence_number DESC LIMIT 1)
                ) as player_id,
                COALESCE(
                    e.payload->>'owner_name',
                    (SELECT e2.payload->>'player_name'
                     FROM game_events e2
                     WHERE e2.game_uuid = e.game_uuid
                       AND e2.event_type = 'purchase'
                       AND e2.payload->>'property_name' = e.payload->>'property_name'
                     ORDER BY e2.sequence_number DESC LIMIT 1)
                ) as player_name,
                (e.payload->>'owner_cash_after')::int as cash,
                e.sequence_number
            FROM game_events e
            JOIN game_info gi ON e.game_uuid = gi.game_uuid
            WHERE e.event_type = 'rent_payment'
                AND e.payload->>'owner_cash_after' IS NOT NULL
        ),
        -- Cash changes from auction wins
        auction_cash AS (
            SELECT
                e.turn_number,
                (e.payload->>'winner_id')::int as player_id,
                e.payload->>'winner_name' as player_name,
                (e.payload->>'winner_cash_after')::int as cash,
                e.sequence_number
            FROM game_events e
            JOIN game_info gi ON e.game_uuid = gi.game_uuid
            WHERE e.event_type = 'auction_end'
                AND e.payload->>'winner_cash_after' IS NOT NULL
                AND e.payload->>'winner_id' IS NOT NULL
        ),
        -- Combine all cash events
        all_cash_events AS (
            SELECT * FROM starting_cash
            UNION ALL
            SELECT * FROM purchase_cash
            UNION ALL
            SELECT * FROM rent_payer_cash
            UNION ALL
            SELECT * FROM rent_owner_cash WHERE player_id IS NOT NULL
            UNION ALL
            SELECT * FROM auction_cash
        )
        SELECT
            turn_number,
            player_id,
            COALESCE(player_name, 'Player ' || player_id) as player_name,
            cash
        FROM all_cash_events
        WHERE player_id IS NOT NULL AND cash IS NOT NULL
        ORDER BY sequence_number, turn_number, player_id
    """
    return execute_query_df(query, (game_id,))


def get_recent_games(limit: int = 10) -> pd.DataFrame:
    """Get recent games with player info."""
    query = """
        SELECT
            g.game_id,
            g.status,
            g.created_at,
            g.finished_at,
            g.winner_id,
            g.total_turns,
            g.config,
            COALESCE(
                (SELECT p.name FROM players p WHERE p.game_uuid = g.id AND p.is_winner = true LIMIT 1),
                'No winner'
            ) as winner_name,
            (SELECT COUNT(*) FROM players p WHERE p.game_uuid = g.id) as player_count,
            (SELECT string_agg(DISTINCT p.agent_type, ', ') FROM players p WHERE p.game_uuid = g.id) as agent_types
        FROM games g
        ORDER BY g.created_at DESC
        LIMIT %s
    """
    return execute_query_df(query, (limit,))


def get_active_games() -> pd.DataFrame:
    """Get currently running games."""
    query = """
        SELECT
            g.game_id,
            g.status,
            g.started_at,
            g.total_turns,
            (SELECT COUNT(*) FROM players p WHERE p.game_uuid = g.id) as player_count,
            (SELECT json_agg(json_build_object(
                'player_id', p.player_id,
                'name', p.name,
                'agent_type', p.agent_type
            )) FROM players p WHERE p.game_uuid = g.id) as players
        FROM games g
        WHERE g.status IN ('running', 'paused')
        ORDER BY g.started_at DESC
    """
    return execute_query_df(query)


# ============================================================================
# Statistics & Analytics
# ============================================================================

def get_games_summary() -> Dict[str, Any]:
    """Get overall games summary statistics (API-first, DB fallback)."""
    data = fetch_json("/api/games", params={"limit": 100, "offset": 0})
    if data and "games" in data:
        df = pd.DataFrame(data["games"])
        total_games = len(df)
        finished_games = len(df[df["status"] == "finished"])
        running_games = len(df[df["status"] == "running"])
        avg_turns = df[df["status"] == "finished"]["total_turns"].mean()
        first_game = pd.to_datetime(df["created_at"]).min() if not df.empty else None
        last_game = pd.to_datetime(df["created_at"]).max() if not df.empty else None
        return {
            "total_games": total_games,
            "finished_games": finished_games,
            "running_games": running_games,
            "avg_turns": avg_turns,
            "first_game": first_game,
            "last_game": last_game,
        }

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
    results = execute_query(query)
    return results[0] if results else {}


def get_games_timeline(
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
) -> pd.DataFrame:
    """Get games count by date for timeline chart (API-first, DB fallback)."""
    if not date_from:
        date_from = datetime.now() - timedelta(days=30)
    if not date_to:
        date_to = datetime.now()

    data = fetch_json("/api/games", params={"limit": 5000, "offset": 0})
    if data and "games" in data:
        df = pd.DataFrame(data["games"])
        if df.empty:
            return pd.DataFrame()
        df["date"] = pd.to_datetime(df["created_at"]).dt.date
        mask = (df["created_at"] >= pd.to_datetime(date_from)) & (df["created_at"] <= pd.to_datetime(date_to))
        df = df[mask]
        grouped = df.groupby("date").agg(
            games_count=("game_id", "count"),
            avg_turns=("total_turns", "mean"),
        )
        grouped = grouped.reset_index()
        grouped["llm_games_count"] = 0  # Placeholder; API lacks agent breakdown
        return grouped

    query = """
        SELECT
            DATE(created_at) as date,
            COUNT(*) as games_count,
            AVG(total_turns) FILTER (WHERE status = 'finished') as avg_turns,
            COUNT(*) FILTER (WHERE EXISTS (
                SELECT 1 FROM players p WHERE p.game_uuid = games.id AND p.agent_type = 'llm'
            )) as llm_games_count
        FROM games
        WHERE created_at >= %s AND created_at <= %s
        GROUP BY DATE(created_at)
        ORDER BY date
    """
    return execute_query_df(query, (date_from, date_to))


def get_win_rates_by_agent_type() -> pd.DataFrame:
    """Get win rates grouped by agent type (DB fallback)."""
    data = fetch_json("/api/dashboard/win_rates/agents")
    if data:
        return pd.DataFrame(data)
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
    return execute_query_df(query)


def get_win_rates_by_model_strategy() -> pd.DataFrame:
    """Get win rates grouped by LLM model and strategy."""
    query = """
        WITH llm_decision_info AS (
            -- Get model and strategy from llm_decisions table (one per player per game)
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
                -- Get model from: llm_decisions > players table > 'unknown'
                COALESCE(
                    ldi.model_version,
                    p.llm_model_name,
                    'unknown'
                ) as model_name,
                -- Get strategy from: llm_decisions > players table > game config > 'unknown'
                COALESCE(
                    ldi.strategy_description,
                    p.llm_strategy_profile->>'strategy',
                    g.config->>'llm_strategy',
                    g.metadata->>'llm_strategy',
                    'unknown'
                ) as strategy,
                g.total_turns
            FROM players p
            JOIN games g ON p.game_uuid = g.id
            LEFT JOIN llm_decision_info ldi ON ldi.game_uuid = p.game_uuid AND ldi.player_id = p.player_id
            WHERE p.agent_type = 'llm' AND g.status = 'finished'
        )
        SELECT
            model_name,
            strategy,
            COUNT(*) as games_played,
            SUM(CASE WHEN is_winner THEN 1 ELSE 0 END) as wins,
            ROUND(
                SUM(CASE WHEN is_winner THEN 1 ELSE 0 END)::numeric /
                NULLIF(COUNT(*), 0) * 100,
                2
            ) as win_rate,
            AVG(total_turns) FILTER (WHERE is_winner) as avg_turns_to_win,
            AVG(final_net_worth) as avg_net_worth,
            SUM(CASE WHEN is_bankrupt THEN 1 ELSE 0 END)::numeric /
                NULLIF(COUNT(*), 0) * 100 as bankruptcy_rate
        FROM llm_players
        GROUP BY model_name, strategy
        HAVING COUNT(*) >= 1
        ORDER BY win_rate DESC, games_played DESC
    """
    return execute_query_df(query)


def get_strategy_metrics() -> pd.DataFrame:
    """Get aggregated metrics grouped by strategy only."""
    query = """
        WITH llm_decision_info AS (
            -- Get strategy from llm_decisions table (one per player per game)
            SELECT DISTINCT ON (d.game_uuid, d.player_id)
                d.game_uuid,
                d.player_id,
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
                    ldi.strategy_description,
                    p.llm_strategy_profile->>'strategy',
                    g.config->>'llm_strategy',
                    g.metadata->>'llm_strategy',
                    'unknown'
                ) as strategy,
                g.total_turns
            FROM players p
            JOIN games g ON p.game_uuid = g.id
            LEFT JOIN llm_decision_info ldi ON ldi.game_uuid = p.game_uuid AND ldi.player_id = p.player_id
            WHERE p.agent_type = 'llm' AND g.status = 'finished'
        )
        SELECT
            strategy,
            COUNT(*) as games_played,
            SUM(CASE WHEN is_winner THEN 1 ELSE 0 END) as wins,
            ROUND(
                SUM(CASE WHEN is_winner THEN 1 ELSE 0 END)::numeric /
                NULLIF(COUNT(*), 0) * 100,
                2
            ) as win_rate,
            AVG(total_turns) FILTER (WHERE is_winner) as avg_turns_to_win,
            AVG(final_net_worth) as avg_net_worth,
            SUM(CASE WHEN is_bankrupt THEN 1 ELSE 0 END)::numeric /
                NULLIF(COUNT(*), 0) * 100 as bankruptcy_rate
        FROM llm_players
        GROUP BY strategy
        HAVING COUNT(*) >= 1
        ORDER BY win_rate DESC, games_played DESC
    """
    return execute_query_df(query)


def get_property_purchases_by_strategy() -> pd.DataFrame:
    """Get property purchase patterns grouped by strategy."""
    query = """
        WITH llm_decision_info AS (
            -- Get strategy from llm_decisions table (one per player per game)
            SELECT DISTINCT ON (d.game_uuid, d.player_id)
                d.game_uuid,
                d.player_id,
                d.strategy_description
            FROM llm_decisions d
            ORDER BY d.game_uuid, d.player_id, d.sequence_number DESC
        ),
        purchases AS (
            SELECT
                p.game_uuid,
                COALESCE(
                    ldi.strategy_description,
                    p.llm_strategy_profile->>'strategy',
                    g.config->>'llm_strategy',
                    g.metadata->>'llm_strategy',
                    p.agent_type
                ) as strategy,
                e.payload->>'property_position' as property_position,
                e.payload->>'property_name' as property_name,
                COALESCE((e.payload->>'price')::int, 0) as price
            FROM game_events e
            JOIN games g ON e.game_uuid = g.id
            JOIN players p ON p.game_uuid = g.id AND p.player_id = e.actor_player_id
            LEFT JOIN llm_decision_info ldi ON ldi.game_uuid = p.game_uuid AND ldi.player_id = p.player_id
            WHERE e.event_type = 'property_purchased'
                AND g.status = 'finished'
        )
        SELECT
            strategy,
            property_position::int as position,
            property_name,
            COUNT(*) as purchase_count,
            AVG(price) as avg_price
        FROM purchases
        WHERE property_position IS NOT NULL
        GROUP BY strategy, property_position, property_name
        ORDER BY strategy, purchase_count DESC
    """
    return execute_query_df(query)


def get_head_to_head_results() -> pd.DataFrame:
    """Get head-to-head win/loss results between agent types."""
    query = """
        WITH llm_decision_info AS (
            -- Get strategy from llm_decisions table (one per player per game)
            SELECT DISTINCT ON (d.game_uuid, d.player_id)
                d.game_uuid,
                d.player_id,
                d.strategy_description
            FROM llm_decisions d
            ORDER BY d.game_uuid, d.player_id, d.sequence_number DESC
        ),
        game_results AS (
            SELECT
                g.id as game_uuid,
                p.agent_type,
                p.is_winner,
                CASE
                    WHEN p.agent_type = 'llm' THEN
                        COALESCE(
                            ldi.strategy_description,
                            p.llm_strategy_profile->>'strategy',
                            g.config->>'llm_strategy',
                            'llm'
                        )
                    ELSE p.agent_type
                END as agent_key
            FROM players p
            JOIN games g ON p.game_uuid = g.id
            LEFT JOIN llm_decision_info ldi ON ldi.game_uuid = p.game_uuid AND ldi.player_id = p.player_id
            WHERE g.status = 'finished'
        )
        SELECT
            a.agent_key as agent_a,
            b.agent_key as agent_b,
            COUNT(*) as total_games,
            SUM(CASE WHEN a.is_winner THEN 1 ELSE 0 END) as wins_a,
            SUM(CASE WHEN b.is_winner THEN 1 ELSE 0 END) as wins_b
        FROM game_results a
        JOIN game_results b ON a.game_uuid = b.game_uuid AND a.agent_key < b.agent_key
        GROUP BY a.agent_key, b.agent_key
        ORDER BY total_games DESC
    """
    return execute_query_df(query)


# ============================================================================
# LLM Decision Queries
# ============================================================================

def get_llm_decisions_for_game(
    game_id: str,
    player_id: Optional[int] = None,
    limit: int = 100,
) -> pd.DataFrame:
    """Get LLM decisions for a specific game."""
    query = """
        SELECT
            d.player_id,
            d.turn_number,
            d.sequence_number,
            d.timestamp,
            d.game_state,
            d.player_state,
            d.available_actions,
            d.reasoning,
            d.chosen_action,
            d.strategy_description,
            d.processing_time_ms,
            d.model_version
        FROM llm_decisions d
        JOIN games g ON d.game_uuid = g.id
        WHERE g.game_id = %s
    """
    params = [game_id]

    if player_id is not None:
        query += " AND d.player_id = %s"
        params.append(player_id)

    query += " ORDER BY d.turn_number, d.sequence_number LIMIT %s"
    params.append(limit)

    return execute_query_df(query, tuple(params))


def get_llm_decision_stats() -> pd.DataFrame:
    """Get aggregate statistics about LLM decisions."""
    query = """
        SELECT
            d.model_version,
            d.strategy_description as strategy,
            COUNT(*) as total_decisions,
            AVG(d.processing_time_ms) as avg_processing_time_ms,
            COUNT(DISTINCT d.game_uuid) as games_count
        FROM llm_decisions d
        GROUP BY d.model_version, d.strategy_description
        ORDER BY total_decisions DESC
    """
    return execute_query_df(query)


# ============================================================================
# Cash Timeline (for game detail)
# ============================================================================

def get_cash_timeline(game_id: str) -> pd.DataFrame:
    """Get cash values over turns for each player in a game."""
    # This requires parsing event payloads to extract cash changes
    # For now, we'll get turn start events which often have cash info
    query = """
        WITH turn_events AS (
            SELECT
                e.turn_number,
                e.payload,
                e.event_type
            FROM game_events e
            JOIN games g ON e.game_uuid = g.id
            WHERE g.game_id = %s
                AND e.event_type IN ('turn_start', 'game_started', 'rent_paid', 'property_purchased')
            ORDER BY e.sequence_number
        )
        SELECT * FROM turn_events
    """
    return execute_query_df(query, (game_id,))


# ============================================================================
# Live Game Queries
# ============================================================================

def get_live_player_states(game_id: str) -> pd.DataFrame:
    """
    Get current player states for a live game by reconstructing from transaction events.

    Reconstructs cash from: purchase (cash_after), rent_payment (payer_cash_after, owner_cash_after),
    auction_end (winner_cash_after), pass_go (+200), tax_payment (-amount).

    Returns DataFrame with columns: player_id, player_name, cash, position, position_name, is_bankrupt
    """
    query = """
        WITH game_info AS (
            SELECT id as game_uuid FROM games WHERE game_id = %s
        ),
        -- Get all players from the players table
        base_players AS (
            SELECT
                p.player_id,
                p.name as player_name,
                p.agent_type,
                p.is_bankrupt,
                1500 as starting_cash
            FROM players p
            JOIN game_info gi ON p.game_uuid = gi.game_uuid
        ),
        -- Get latest position from 'land' or 'move' events
        latest_positions AS (
            SELECT DISTINCT ON (e.actor_player_id)
                e.actor_player_id as player_id,
                COALESCE(
                    (e.payload->>'to_position')::int,
                    (e.payload->>'position')::int
                ) as position,
                e.payload->>'space_name' as position_name
            FROM game_events e
            JOIN game_info gi ON e.game_uuid = gi.game_uuid
            WHERE e.event_type IN ('land', 'move')
                AND e.actor_player_id IS NOT NULL
            ORDER BY e.actor_player_id, e.sequence_number DESC
        ),
        -- Check who is in jail (last go_to_jail without subsequent jail_release)
        jail_status AS (
            SELECT DISTINCT ON (player_id)
                player_id,
                in_jail
            FROM (
                SELECT
                    (e.payload->>'player_id')::int as player_id,
                    true as in_jail,
                    e.sequence_number
                FROM game_events e
                JOIN game_info gi ON e.game_uuid = gi.game_uuid
                WHERE e.event_type = 'go_to_jail'

                UNION ALL

                SELECT
                    (e.payload->>'player_id')::int as player_id,
                    false as in_jail,
                    e.sequence_number
                FROM game_events e
                JOIN game_info gi ON e.game_uuid = gi.game_uuid
                WHERE e.event_type = 'jail_release'
            ) jail_events
            ORDER BY player_id, sequence_number DESC
        ),
        -- Reconstruct cash from various event types
        -- We need the LAST known cash value for each player
        cash_events AS (
            -- From purchase events (buyer's cash_after)
            SELECT
                (e.payload->>'player_id')::int as player_id,
                (e.payload->>'cash_after')::int as cash,
                e.sequence_number
            FROM game_events e
            JOIN game_info gi ON e.game_uuid = gi.game_uuid
            WHERE e.event_type = 'purchase'
                AND e.payload->>'cash_after' IS NOT NULL

            UNION ALL

            -- From rent_payment (payer's cash)
            SELECT
                (e.payload->>'payer_id')::int as player_id,
                (e.payload->>'payer_cash_after')::int as cash,
                e.sequence_number
            FROM game_events e
            JOIN game_info gi ON e.game_uuid = gi.game_uuid
            WHERE e.event_type = 'rent_payment'
                AND e.payload->>'payer_cash_after' IS NOT NULL
                AND e.payload->>'payer_id' IS NOT NULL

            UNION ALL

            -- From rent_payment (owner's cash)
            SELECT
                COALESCE(
                    (e.payload->>'owner_id')::int,
                    -- If owner_id is null, try to find from property ownership
                    (SELECT (e2.payload->>'player_id')::int
                     FROM game_events e2
                     WHERE e2.game_uuid = e.game_uuid
                       AND e2.event_type = 'purchase'
                       AND e2.payload->>'property_name' = e.payload->>'property_name'
                     ORDER BY e2.sequence_number DESC LIMIT 1)
                ) as player_id,
                (e.payload->>'owner_cash_after')::int as cash,
                e.sequence_number
            FROM game_events e
            JOIN game_info gi ON e.game_uuid = gi.game_uuid
            WHERE e.event_type = 'rent_payment'
                AND e.payload->>'owner_cash_after' IS NOT NULL

            UNION ALL

            -- From auction_end (winner's cash)
            SELECT
                (e.payload->>'winner_id')::int as player_id,
                (e.payload->>'winner_cash_after')::int as cash,
                e.sequence_number
            FROM game_events e
            JOIN game_info gi ON e.game_uuid = gi.game_uuid
            WHERE e.event_type = 'auction_end'
                AND e.payload->>'winner_cash_after' IS NOT NULL
                AND e.payload->>'winner_id' IS NOT NULL
        ),
        latest_cash AS (
            SELECT DISTINCT ON (player_id)
                player_id,
                cash
            FROM cash_events
            WHERE player_id IS NOT NULL
            ORDER BY player_id, sequence_number DESC
        )
        SELECT
            bp.player_id,
            bp.player_name,
            bp.agent_type,
            COALESCE(lc.cash, bp.starting_cash) as cash,
            COALESCE(lc.cash, bp.starting_cash) as net_worth,  -- Simplified, just cash for now
            COALESCE(lp.position, 0) as position,
            COALESCE(lp.position_name, 'GO') as position_name,
            bp.is_bankrupt,
            COALESCE(js.in_jail, false) as in_jail
        FROM base_players bp
        LEFT JOIN latest_cash lc ON bp.player_id = lc.player_id
        LEFT JOIN latest_positions lp ON bp.player_id = lp.player_id
        LEFT JOIN jail_status js ON bp.player_id = js.player_id
        ORDER BY bp.player_id
    """
    return execute_query_df(query, (game_id,))


def get_live_game_info(game_id: str) -> Optional[Dict[str, Any]]:
    """
    Get current game info including the actual current turn from events.

    Returns dict with: game_id, status, started_at, current_turn, player_count
    """
    query = """
        SELECT
            g.game_id,
            g.status,
            g.started_at,
            g.total_turns,
            COALESCE(
                (SELECT MAX(e.turn_number) FROM game_events e WHERE e.game_uuid = g.id),
                0
            ) as current_turn,
            (SELECT COUNT(*) FROM players p WHERE p.game_uuid = g.id) as player_count
        FROM games g
        WHERE g.game_id = %s
    """
    results = execute_query(query, (game_id,))
    return results[0] if results else None


def get_active_games_with_turn() -> pd.DataFrame:
    """Get currently running games with actual current turn from events."""
    query = """
        SELECT
            g.game_id,
            g.status,
            g.started_at,
            COALESCE(
                (SELECT MAX(e.turn_number) FROM game_events e WHERE e.game_uuid = g.id),
                0
            ) as current_turn,
            (SELECT COUNT(*) FROM players p WHERE p.game_uuid = g.id) as player_count,
            (SELECT json_agg(json_build_object(
                'player_id', p.player_id,
                'name', p.name,
                'agent_type', p.agent_type
            )) FROM players p WHERE p.game_uuid = g.id) as players
        FROM games g
        WHERE g.status IN ('running', 'paused')
        ORDER BY g.started_at DESC
    """
    return execute_query_df(query)

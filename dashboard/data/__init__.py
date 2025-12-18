"""
Data layer for the dashboard.

Provides database queries and data aggregation functions.
"""

from .queries import (
    get_all_games,
    get_game_by_id,
    get_game_events,
    get_game_players,
    get_games_summary,
    get_win_rates_by_agent_type,
    get_win_rates_by_model_strategy,
    get_strategy_metrics,
    get_property_purchases_by_strategy,
    get_head_to_head_results,
    get_llm_decisions_for_game,
    get_active_games,
    get_recent_games,
    get_games_timeline,
)

__all__ = [
    "get_all_games",
    "get_game_by_id",
    "get_game_events",
    "get_game_players",
    "get_games_summary",
    "get_win_rates_by_agent_type",
    "get_win_rates_by_model_strategy",
    "get_strategy_metrics",
    "get_property_purchases_by_strategy",
    "get_head_to_head_results",
    "get_llm_decisions_for_game",
    "get_active_games",
    "get_recent_games",
    "get_games_timeline",
]

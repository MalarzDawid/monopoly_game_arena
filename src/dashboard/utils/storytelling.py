"""
Data storytelling utilities for generating insights.

This module provides auto-generated insights based on game data analysis.
"""

from typing import Optional
import pandas as pd


def generate_overview_insight(win_rates_df: pd.DataFrame) -> str:
    """
    Generate an insight about overall game performance.

    Args:
        win_rates_df: DataFrame with agent_type, wins, games_played, win_rate columns

    Returns:
        Human-readable insight string
    """
    if win_rates_df.empty:
        return "No game data available yet. Run some games to see insights!"

    total_games = win_rates_df["games_played"].sum() if "games_played" in win_rates_df.columns else 0

    if total_games == 0:
        return "No completed games yet. Start playing to generate insights!"

    # Find best performing agent type
    if "win_rate" in win_rates_df.columns:
        best_agent = win_rates_df.loc[win_rates_df["win_rate"].idxmax()]
        best_type = best_agent.get("agent_type", "Unknown")
        best_rate = best_agent.get("win_rate", 0)
        best_wins = best_agent.get("wins", 0)

        # Generate insight based on performance
        if best_rate > 50:
            insight = (
                f"{best_type.upper()} agents are dominating with a {best_rate:.1f}% win rate "
                f"({best_wins} wins). They're significantly outperforming other agent types."
            )
        elif best_rate > 35:
            insight = (
                f"{best_type.upper()} agents lead with a {best_rate:.1f}% win rate. "
                f"The competition is balanced but they have a slight edge."
            )
        else:
            insight = (
                f"Games are highly competitive. {best_type.upper()} agents have the highest "
                f"win rate at {best_rate:.1f}%, but no clear dominant strategy has emerged."
            )

        # Add comparison if LLM agents exist
        llm_row = win_rates_df[win_rates_df["agent_type"] == "llm"]
        if not llm_row.empty and best_type != "llm":
            llm_rate = llm_row.iloc[0].get("win_rate", 0)
            diff = best_rate - llm_rate
            if diff > 10:
                insight += f" LLM agents are underperforming by {diff:.1f} percentage points."
            elif diff < -10:
                insight += f" However, LLM agents are actually stronger with a {llm_rate:.1f}% rate."

        return insight

    return f"Analyzed {total_games} games across {len(win_rates_df)} agent types."


def generate_ranking_insight(model_strategy_df: pd.DataFrame) -> str:
    """
    Generate an insight about LLM model/strategy rankings.

    Args:
        model_strategy_df: DataFrame with model_name, strategy, win_rate, games_played columns

    Returns:
        Human-readable insight string
    """
    if model_strategy_df.empty:
        return "No LLM game data available. Run games with LLM agents to see rankings!"

    if len(model_strategy_df) == 0:
        return "Need more LLM game data to generate meaningful rankings."

    # Get top performer
    top = model_strategy_df.iloc[0]
    model = top.get("model_name", "Unknown model")
    strategy = top.get("strategy", "unknown")
    win_rate = top.get("win_rate", 0) or 0
    games = top.get("games_played", 0) or 0

    # Statistical confidence check
    confidence = "high" if games >= 20 else "medium" if games >= 10 else "low"

    # Build insight
    if win_rate > 50:
        performance = "exceptional"
    elif win_rate > 35:
        performance = "strong"
    elif win_rate > 20:
        performance = "competitive"
    else:
        performance = "developing"

    insight = (
        f"The {model} model with {strategy.upper()} strategy shows {performance} performance "
        f"with a {win_rate:.1f}% win rate across {games} games. "
    )

    if confidence == "high":
        insight += "This ranking has high statistical confidence."
    elif confidence == "medium":
        insight += "More games would increase ranking confidence."
    else:
        insight += "Results are preliminary - more games needed for reliable rankings."

    # Add comparison with second place if available
    if len(model_strategy_df) > 1:
        second = model_strategy_df.iloc[1]
        second_model = second.get("model_name", "Unknown")
        second_strategy = second.get("strategy", "unknown")
        second_rate = second.get("win_rate", 0) or 0
        gap = win_rate - second_rate

        if gap > 10:
            insight += f" Clear lead of {gap:.1f}pp over {second_model} ({second_strategy})."
        elif gap > 5:
            insight += f" Leads {second_model} ({second_strategy}) by {gap:.1f}pp."
        else:
            insight += f" Close competition with {second_model} ({second_strategy})."

    return insight


def generate_strategy_insight(strategy_df: pd.DataFrame) -> str:
    """
    Generate an insight about strategy performance.

    Args:
        strategy_df: DataFrame with strategy, win_rate, avg_net_worth, bankruptcy_rate columns

    Returns:
        Human-readable insight string
    """
    if strategy_df.empty:
        return "No strategy data available. Run games with different LLM strategies!"

    strategies = strategy_df["strategy"].unique() if "strategy" in strategy_df.columns else []

    if len(strategies) == 0:
        return "Need strategy data to generate insights."

    # Find best by win rate
    if "win_rate" in strategy_df.columns:
        best_win = strategy_df.loc[strategy_df["win_rate"].idxmax()]
        best_strategy = best_win.get("strategy", "unknown")
        best_rate = best_win.get("win_rate", 0) or 0
    else:
        best_strategy = strategies[0]
        best_rate = 0

    # Find safest (lowest bankruptcy)
    safest_strategy = None
    safest_rate = None
    if "bankruptcy_rate" in strategy_df.columns:
        safest = strategy_df.loc[strategy_df["bankruptcy_rate"].idxmin()]
        safest_strategy = safest.get("strategy", "unknown")
        safest_rate = safest.get("bankruptcy_rate", 0) or 0

    # Find richest (highest avg net worth)
    richest_strategy = None
    richest_worth = None
    if "avg_net_worth" in strategy_df.columns:
        richest = strategy_df.loc[strategy_df["avg_net_worth"].idxmax()]
        richest_strategy = richest.get("strategy", "unknown")
        richest_worth = richest.get("avg_net_worth", 0) or 0

    # Build insight
    insight = f"The {best_strategy.upper()} strategy leads with a {best_rate:.1f}% win rate. "

    if safest_strategy and safest_strategy != best_strategy:
        insight += (
            f"For risk-averse play, {safest_strategy.upper()} has the lowest bankruptcy rate "
            f"at {safest_rate:.1f}%. "
        )

    if richest_strategy and richest_worth:
        if richest_strategy == best_strategy:
            insight += f"It also achieves the highest average net worth at ${richest_worth:,.0f}."
        else:
            insight += (
                f"However, {richest_strategy.upper()} accumulates the most wealth "
                f"averaging ${richest_worth:,.0f} net worth."
            )

    # Strategy-specific observations
    if "aggressive" in [s.lower() for s in strategies]:
        agg_row = strategy_df[strategy_df["strategy"].str.lower() == "aggressive"]
        if not agg_row.empty:
            agg_bankruptcy = agg_row.iloc[0].get("bankruptcy_rate", 0) or 0
            if agg_bankruptcy > 40:
                insight += " Note: Aggressive play carries high bankruptcy risk."

    if "defensive" in [s.lower() for s in strategies]:
        def_row = strategy_df[strategy_df["strategy"].str.lower() == "defensive"]
        if not def_row.empty:
            def_win = def_row.iloc[0].get("win_rate", 0) or 0
            if def_win < 20:
                insight += " Defensive strategies may be too conservative to win consistently."

    return insight


def generate_game_insight(
    game_data: dict,
    players_df: pd.DataFrame,
    events_count: int,
) -> str:
    """
    Generate an insight about a specific game.

    Args:
        game_data: Game metadata dictionary
        players_df: DataFrame with player information
        events_count: Total number of events in the game

    Returns:
        Human-readable insight string
    """
    if not game_data:
        return "Game data not available."

    status = game_data.get("status", "unknown")
    total_turns = game_data.get("total_turns", 0)
    winner_id = game_data.get("winner_id")

    if status != "finished":
        return f"Game is {status}. {total_turns} turns played so far with {events_count} events."

    # Find winner info
    winner_name = "Unknown"
    winner_agent = "unknown"
    if winner_id is not None and not players_df.empty:
        winner_row = players_df[players_df.index == winner_id]
        if not winner_row.empty:
            winner_name = winner_row.iloc[0].get("name", f"Player {winner_id}")
            winner_agent = winner_row.iloc[0].get("agent_type", "unknown")

    # Classify game length
    if total_turns < 50:
        length_desc = "quick"
    elif total_turns < 150:
        length_desc = "standard"
    elif total_turns < 300:
        length_desc = "extended"
    else:
        length_desc = "marathon"

    insight = (
        f"A {length_desc} game of {total_turns} turns. {winner_name} ({winner_agent}) "
        f"emerged victorious. "
    )

    # Count agent types
    if not players_df.empty and "agent_type" in players_df.columns:
        agent_counts = players_df["agent_type"].value_counts()
        if "llm" in agent_counts:
            llm_count = agent_counts["llm"]
            if winner_agent == "llm":
                insight += f"LLM won against {len(players_df) - 1} opponents."
            else:
                insight += f"{llm_count} LLM players competed but didn't win."

    return insight

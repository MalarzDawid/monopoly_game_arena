"""
Filter components for the dashboard.
"""

from datetime import datetime, timedelta
from typing import List, Optional

import dash_bootstrap_components as dbc
from dash import dcc, html


def create_date_filter(
    id_prefix: str = "date",
    default_days: int = 30,
) -> dbc.Card:
    """
    Create a date range filter.

    Args:
        id_prefix: Prefix for component IDs
        default_days: Default number of days to show
    """
    end_date = datetime.now()
    start_date = end_date - timedelta(days=default_days)

    return dbc.Card(
        dbc.CardBody(
            [
                html.Label("Date Range", className="fw-bold mb-2"),
                dcc.DatePickerRange(
                    id=f"{id_prefix}-range",
                    start_date=start_date.date(),
                    end_date=end_date.date(),
                    display_format="YYYY-MM-DD",
                    className="w-100",
                ),
            ]
        ),
        className="mb-3",
    )


def create_agent_filter(
    id_prefix: str = "agent",
    include_all: bool = True,
) -> dbc.Card:
    """
    Create an agent type filter.

    Args:
        id_prefix: Prefix for component IDs
        include_all: Whether to include "All" option
    """
    options = []
    if include_all:
        options.append({"label": "All Agents", "value": "all"})

    options.extend([
        {"label": "LLM", "value": "llm"},
        {"label": "Greedy", "value": "greedy"},
        {"label": "Random", "value": "random"},
        {"label": "Human", "value": "human"},
    ])

    return dbc.Card(
        dbc.CardBody(
            [
                html.Label("Agent Type", className="fw-bold mb-2"),
                dcc.Dropdown(
                    id=f"{id_prefix}-filter",
                    options=options,
                    value="all" if include_all else None,
                    clearable=not include_all,
                    className="dash-dropdown",
                ),
            ]
        ),
        className="mb-3",
    )


def create_strategy_filter(
    id_prefix: str = "strategy",
    include_all: bool = True,
) -> dbc.Card:
    """
    Create an LLM strategy filter.

    Args:
        id_prefix: Prefix for component IDs
        include_all: Whether to include "All" option
    """
    options = []
    if include_all:
        options.append({"label": "All Strategies", "value": "all"})

    options.extend([
        {"label": "Aggressive", "value": "aggressive"},
        {"label": "Balanced", "value": "balanced"},
        {"label": "Defensive", "value": "defensive"},
    ])

    return dbc.Card(
        dbc.CardBody(
            [
                html.Label("LLM Strategy", className="fw-bold mb-2"),
                dcc.Dropdown(
                    id=f"{id_prefix}-filter",
                    options=options,
                    value="all" if include_all else None,
                    clearable=not include_all,
                    className="dash-dropdown",
                ),
            ]
        ),
        className="mb-3",
    )


def create_game_selector(
    id_prefix: str = "game",
    games: Optional[List[dict]] = None,
) -> dbc.Card:
    """
    Create a game selector dropdown.

    Args:
        id_prefix: Prefix for component IDs
        games: Optional list of games to populate
    """
    options = []
    if games:
        for g in games:
            label = f"{g['game_id']} - {g.get('status', 'unknown')}"
            if g.get('winner_name'):
                label += f" (Winner: {g['winner_name']})"
            options.append({"label": label, "value": g["game_id"]})

    return dbc.Card(
        dbc.CardBody(
            [
                html.Label("Select Game", className="fw-bold mb-2"),
                dcc.Dropdown(
                    id=f"{id_prefix}-selector",
                    options=options,
                    placeholder="Select a game to analyze...",
                    className="dash-dropdown",
                ),
            ]
        ),
        className="mb-3",
    )


def create_filter_row(
    filters: List[dbc.Card],
    title: str = "Filters",
) -> dbc.Card:
    """
    Create a row of filters in a card.

    Args:
        filters: List of filter components
        title: Title for the filter section
    """
    cols = [dbc.Col(f, md=4) for f in filters]

    return dbc.Card(
        [
            dbc.CardHeader(
                [
                    html.I(className="fas fa-filter me-2"),
                    title,
                ]
            ),
            dbc.CardBody(dbc.Row(cols)),
        ],
        className="mb-4",
    )

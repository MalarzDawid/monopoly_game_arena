"""
Overview page - High-level view of all games played.
"""

import dash_bootstrap_components as dbc
from dash import dcc, html, callback, Input, Output
import pandas as pd

from dashboard.components.kpi_cards import create_kpi_card, create_insight_card
from dashboard.components.charts import (
    create_timeline_chart,
    create_bar_chart,
    create_pie_chart,
)
from dashboard.data import (
    get_games_summary,
    get_games_timeline,
    get_win_rates_by_agent_type,
    get_recent_games,
)
from dashboard.utils.storytelling import generate_overview_insight


def create_layout():
    """Create the overview page layout."""
    return dbc.Container(
        [
            # Page header
            dbc.Row(
                dbc.Col(
                    html.H2(
                        [
                            html.I(className="fas fa-home me-2"),
                            "Games Overview",
                        ],
                        className="mb-4",
                    )
                )
            ),

            # KPI Cards
            html.Div(id="overview-kpis"),

            # Insight card
            html.Div(id="overview-insight", className="mb-4"),

            # Charts row 1
            dbc.Row(
                [
                    dbc.Col(
                        dbc.Card(
                            [
                                dbc.CardHeader("Games Timeline"),
                                dbc.CardBody(dcc.Graph(id="timeline-chart")),
                            ],
                            className="h-100",
                        ),
                        lg=8,
                        className="mb-4",
                    ),
                    dbc.Col(
                        dbc.Card(
                            [
                                dbc.CardHeader("Win Distribution by Agent Type"),
                                dbc.CardBody(dcc.Graph(id="win-distribution-chart")),
                            ],
                            className="h-100",
                        ),
                        lg=4,
                        className="mb-4",
                    ),
                ]
            ),

            # Charts row 2
            dbc.Row(
                [
                    dbc.Col(
                        dbc.Card(
                            [
                                dbc.CardHeader("Win Rate by Agent Type"),
                                dbc.CardBody(dcc.Graph(id="win-rate-chart")),
                            ],
                            className="h-100",
                        ),
                        lg=6,
                        className="mb-4",
                    ),
                    dbc.Col(
                        dbc.Card(
                            [
                                dbc.CardHeader("Recent Games"),
                                dbc.CardBody(
                                    html.Div(id="recent-games-table"),
                                    style={"maxHeight": "400px", "overflowY": "auto"},
                                ),
                            ],
                            className="h-100",
                        ),
                        lg=6,
                        className="mb-4",
                    ),
                ]
            ),

            # Auto-refresh interval
            dcc.Interval(
                id="overview-refresh",
                interval=30000,  # 30 seconds
                n_intervals=0,
            ),
        ],
        fluid=True,
    )


@callback(
    Output("overview-kpis", "children"),
    Input("overview-refresh", "n_intervals"),
)
def update_kpis(_):
    """Update KPI cards."""
    try:
        summary = get_games_summary()
    except Exception:
        summary = {}

    total_games = summary.get("total_games", 0) or 0
    finished_games = summary.get("finished_games", 0) or 0
    running_games = summary.get("running_games", 0) or 0
    avg_turns = summary.get("avg_turns", 0) or 0

    return dbc.Row(
        [
            dbc.Col(
                create_kpi_card(
                    title="Total Games",
                    value=total_games,
                    icon="fas fa-gamepad",
                    color="primary",
                ),
                md=6,
                lg=3,
                className="mb-4",
            ),
            dbc.Col(
                create_kpi_card(
                    title="Finished Games",
                    value=finished_games,
                    icon="fas fa-flag-checkered",
                    color="success",
                ),
                md=6,
                lg=3,
                className="mb-4",
            ),
            dbc.Col(
                create_kpi_card(
                    title="Running Games",
                    value=running_games,
                    icon="fas fa-play-circle",
                    color="warning",
                ),
                md=6,
                lg=3,
                className="mb-4",
            ),
            dbc.Col(
                create_kpi_card(
                    title="Avg Game Length",
                    value=f"{avg_turns:.0f} turns",
                    icon="fas fa-clock",
                    color="info",
                ),
                md=6,
                lg=3,
                className="mb-4",
            ),
        ]
    )


@callback(
    Output("overview-insight", "children"),
    Input("overview-refresh", "n_intervals"),
)
def update_insight(_):
    """Generate and update insight card."""
    try:
        win_rates = get_win_rates_by_agent_type()
        insight = generate_overview_insight(win_rates)
    except Exception:
        insight = "Unable to generate insights at this time."

    return create_insight_card(insight, insight_type="info", title="Key Insight")


@callback(
    Output("timeline-chart", "figure"),
    Input("overview-refresh", "n_intervals"),
)
def update_timeline(_):
    """Update games timeline chart."""
    try:
        df = get_games_timeline()
    except Exception:
        df = pd.DataFrame()

    return create_timeline_chart(
        df,
        x="date",
        y="games_count",
        title="",
        y_label="Games",
    )


@callback(
    Output("win-distribution-chart", "figure"),
    Input("overview-refresh", "n_intervals"),
)
def update_win_distribution(_):
    """Update win distribution pie chart."""
    try:
        df = get_win_rates_by_agent_type()
    except Exception:
        df = pd.DataFrame()

    return create_pie_chart(
        df,
        values="wins",
        names="agent_type",
        title="",
    )


@callback(
    Output("win-rate-chart", "figure"),
    Input("overview-refresh", "n_intervals"),
)
def update_win_rate(_):
    """Update win rate bar chart."""
    try:
        df = get_win_rates_by_agent_type()
    except Exception:
        df = pd.DataFrame()

    return create_bar_chart(
        df,
        x="agent_type",
        y="win_rate",
        title="",
    )


@callback(
    Output("recent-games-table", "children"),
    Input("overview-refresh", "n_intervals"),
)
def update_recent_games(_):
    """Update recent games table."""
    try:
        df = get_recent_games(limit=10)
    except Exception:
        df = pd.DataFrame()

    if df.empty:
        return html.P("No games found.", className="text-muted")

    # Create table rows
    rows = []
    for _, row in df.iterrows():
        status_badge = "success" if row.get("status") == "finished" else "warning"
        rows.append(
            html.Tr(
                [
                    html.Td(
                        dcc.Link(
                            row.get("game_id", "Unknown"),
                            href=f"/game?id={row.get('game_id')}",
                        )
                    ),
                    html.Td(
                        dbc.Badge(
                            row.get("status", "unknown"),
                            color=status_badge,
                        )
                    ),
                    html.Td(row.get("winner_name", "-")),
                    html.Td(f"{row.get('total_turns', 0)} turns"),
                    html.Td(row.get("agent_types", "-")),
                ]
            )
        )

    return dbc.Table(
        [
            html.Thead(
                html.Tr(
                    [
                        html.Th("Game ID"),
                        html.Th("Status"),
                        html.Th("Winner"),
                        html.Th("Length"),
                        html.Th("Agents"),
                    ]
                )
            ),
            html.Tbody(rows),
        ],
        striped=True,
        hover=True,
        responsive=True,
        className="mb-0",
    )

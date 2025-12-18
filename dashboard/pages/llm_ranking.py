"""
LLM Ranking page - Compare LLM models and strategies.
"""

import dash_bootstrap_components as dbc
from dash import dcc, html, callback, Input, Output
import pandas as pd
import plotly.express as px

from dashboard.components.kpi_cards import create_insight_card
from dashboard.components.charts import (
    create_bar_chart,
    create_heatmap,
    create_radar_chart,
    apply_dark_theme,
)
from dashboard.data import (
    get_win_rates_by_model_strategy,
    get_head_to_head_results,
)
from dashboard.utils.storytelling import generate_ranking_insight
from dashboard.config import CHART_COLORS


def create_layout():
    """Create the LLM ranking page layout."""
    return dbc.Container(
        [
            # Page header
            dbc.Row(
                dbc.Col(
                    html.H2(
                        [
                            html.I(className="fas fa-trophy me-2"),
                            "LLM Model Rankings",
                        ],
                        className="mb-4",
                    )
                )
            ),

            # Insight card
            html.Div(id="ranking-insight", className="mb-4"),

            # Ranking table
            dbc.Row(
                dbc.Col(
                    dbc.Card(
                        [
                            dbc.CardHeader(
                                [
                                    html.I(className="fas fa-list-ol me-2"),
                                    "Performance Ranking",
                                ]
                            ),
                            dbc.CardBody(
                                html.Div(id="ranking-table"),
                                style={"overflowX": "auto"},
                            ),
                        ]
                    ),
                    className="mb-4",
                )
            ),

            # Charts row
            dbc.Row(
                [
                    dbc.Col(
                        dbc.Card(
                            [
                                dbc.CardHeader("Win Rate by Model & Strategy"),
                                dbc.CardBody(dcc.Graph(id="win-rate-comparison")),
                            ],
                            className="h-100",
                        ),
                        lg=6,
                        className="mb-4",
                    ),
                    dbc.Col(
                        dbc.Card(
                            [
                                dbc.CardHeader("Performance Radar"),
                                dbc.CardBody(dcc.Graph(id="performance-radar")),
                            ],
                            className="h-100",
                        ),
                        lg=6,
                        className="mb-4",
                    ),
                ]
            ),

            # Head-to-head heatmap
            dbc.Row(
                dbc.Col(
                    dbc.Card(
                        [
                            dbc.CardHeader("Head-to-Head Results"),
                            dbc.CardBody(dcc.Graph(id="head-to-head-heatmap")),
                        ]
                    ),
                    className="mb-4",
                )
            ),

            # Refresh interval
            dcc.Interval(
                id="ranking-refresh",
                interval=60000,  # 1 minute
                n_intervals=0,
            ),
        ],
        fluid=True,
    )


@callback(
    Output("ranking-insight", "children"),
    Input("ranking-refresh", "n_intervals"),
)
def update_insight(_):
    """Generate ranking insight."""
    try:
        df = get_win_rates_by_model_strategy()
        insight = generate_ranking_insight(df)
    except Exception:
        insight = "Unable to generate insights. No LLM games found yet."

    return create_insight_card(insight, insight_type="primary", title="Top Performer")


@callback(
    Output("ranking-table", "children"),
    Input("ranking-refresh", "n_intervals"),
)
def update_ranking_table(_):
    """Update the ranking table."""
    try:
        df = get_win_rates_by_model_strategy()
    except Exception:
        df = pd.DataFrame()

    if df.empty:
        return html.P(
            "No LLM game data available yet. Run some games with LLM agents!",
            className="text-muted text-center py-4",
        )

    # Add rank column
    df = df.copy()
    df["rank"] = range(1, len(df) + 1)

    # Create table rows
    rows = []
    for _, row in df.iterrows():
        # Color code win rate
        win_rate = row.get("win_rate", 0) or 0
        if win_rate >= 40:
            badge_color = "success"
        elif win_rate >= 25:
            badge_color = "warning"
        else:
            badge_color = "danger"

        rows.append(
            html.Tr(
                [
                    html.Td(
                        html.Strong(f"#{row['rank']}"),
                        className="text-center",
                    ),
                    html.Td(row.get("model_name", "unknown")),
                    html.Td(
                        dbc.Badge(
                            row.get("strategy", "unknown"),
                            color="info",
                        )
                    ),
                    html.Td(row.get("games_played", 0)),
                    html.Td(row.get("wins", 0)),
                    html.Td(
                        dbc.Badge(
                            f"{win_rate:.1f}%",
                            color=badge_color,
                        )
                    ),
                    html.Td(
                        f"{row.get('avg_turns_to_win', 0):.0f}"
                        if row.get("avg_turns_to_win")
                        else "-"
                    ),
                    html.Td(f"${row.get('avg_net_worth', 0):,.0f}" if row.get("avg_net_worth") else "-"),
                    html.Td(
                        f"{row.get('bankruptcy_rate', 0):.1f}%"
                        if row.get("bankruptcy_rate")
                        else "-"
                    ),
                ]
            )
        )

    return dbc.Table(
        [
            html.Thead(
                html.Tr(
                    [
                        html.Th("Rank", className="text-center"),
                        html.Th("Model"),
                        html.Th("Strategy"),
                        html.Th("Games"),
                        html.Th("Wins"),
                        html.Th("Win Rate"),
                        html.Th("Avg Turns to Win"),
                        html.Th("Avg Net Worth"),
                        html.Th("Bankruptcy Rate"),
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


@callback(
    Output("win-rate-comparison", "figure"),
    Input("ranking-refresh", "n_intervals"),
)
def update_win_rate_comparison(_):
    """Update win rate comparison chart."""
    try:
        df = get_win_rates_by_model_strategy()
    except Exception:
        df = pd.DataFrame()

    if df.empty:
        import plotly.graph_objects as go
        fig = go.Figure()
        fig.add_annotation(
            text="No LLM data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="#6b7280"),
        )
        return apply_dark_theme(fig)

    # Create grouped bar chart
    fig = px.bar(
        df,
        x="model_name",
        y="win_rate",
        color="strategy",
        barmode="group",
        title="",
        text_auto=".1f",
        color_discrete_sequence=CHART_COLORS,
    )

    fig.update_layout(
        xaxis_title="Model",
        yaxis_title="Win Rate (%)",
        legend_title="Strategy",
    )

    return apply_dark_theme(fig)


@callback(
    Output("performance-radar", "figure"),
    Input("ranking-refresh", "n_intervals"),
)
def update_radar(_):
    """Update performance radar chart."""
    try:
        df = get_win_rates_by_model_strategy()
    except Exception:
        df = pd.DataFrame()

    if df.empty or len(df) == 0:
        import plotly.graph_objects as go
        fig = go.Figure()
        fig.add_annotation(
            text="No data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="#6b7280"),
        )
        return apply_dark_theme(fig)

    # Get top performer
    top = df.iloc[0]

    # Normalize metrics for radar
    categories = ["Win Rate", "Games Played", "Avg Net Worth", "Survival Rate"]

    # Calculate normalized values (0-100 scale)
    max_games = df["games_played"].max() or 1
    max_net_worth = df["avg_net_worth"].max() or 1

    values = [
        top.get("win_rate", 0) or 0,
        (top.get("games_played", 0) / max_games) * 100 if max_games > 0 else 0,
        (top.get("avg_net_worth", 0) / max_net_worth) * 100 if max_net_worth > 0 else 0,
        100 - (top.get("bankruptcy_rate", 0) or 0),
    ]

    return create_radar_chart(
        categories=categories,
        values=values,
        title=f"Top: {top.get('model_name', 'Unknown')} ({top.get('strategy', 'unknown')})",
    )


@callback(
    Output("head-to-head-heatmap", "figure"),
    Input("ranking-refresh", "n_intervals"),
)
def update_heatmap(_):
    """Update head-to-head heatmap."""
    try:
        df = get_head_to_head_results()
    except Exception:
        df = pd.DataFrame()

    if df.empty:
        import plotly.graph_objects as go
        fig = go.Figure()
        fig.add_annotation(
            text="Not enough data for head-to-head comparison",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="#6b7280"),
        )
        return apply_dark_theme(fig)

    # Create win rate matrix
    df["win_rate_a"] = df["wins_a"] / df["total_games"] * 100

    return create_heatmap(
        df,
        x="agent_b",
        y="agent_a",
        z="win_rate_a",
        title="",
        color_scale="RdYlGn",
    )

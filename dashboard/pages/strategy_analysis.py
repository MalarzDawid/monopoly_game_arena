"""
Strategy Analysis page - Understand what makes strategies work.
"""

import dash_bootstrap_components as dbc
from dash import dcc, html, callback, Input, Output
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from dashboard.components.charts import (
    create_bar_chart,
    create_heatmap,
    apply_dark_theme,
)
from dashboard.data import (
    get_property_purchases_by_strategy,
    get_strategy_metrics,
    get_win_rates_by_model_strategy,
)
from dashboard.utils.storytelling import generate_strategy_insight
from dashboard.components.kpi_cards import create_insight_card
from dashboard.config import CHART_COLORS, PROPERTY_COLORS, BOARD_NAMES


def create_layout():
    """Create the strategy analysis page layout."""
    return dbc.Container(
        [
            # Page header
            dbc.Row(
                dbc.Col(
                    html.H2(
                        [
                            html.I(className="fas fa-chess me-2"),
                            "Strategy Analysis",
                        ],
                        className="mb-4",
                    )
                )
            ),

            # Insight card
            html.Div(id="strategy-insight", className="mb-4"),

            # Strategy selector
            dbc.Row(
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.Label("Filter by Strategy", className="fw-bold"),
                                dcc.Dropdown(
                                    id="strategy-filter",
                                    options=[
                                        {"label": "All Strategies", "value": "all"},
                                        {"label": "Aggressive", "value": "aggressive"},
                                        {"label": "Balanced", "value": "balanced"},
                                        {"label": "Defensive", "value": "defensive"},
                                    ],
                                    value="all",
                                    className="dash-dropdown",
                                ),
                            ]
                        )
                    ),
                    md=4,
                    className="mb-4",
                )
            ),

            # Strategy metrics cards
            html.Div(id="strategy-metrics-cards", className="mb-4"),

            # Charts row 1
            dbc.Row(
                [
                    dbc.Col(
                        dbc.Card(
                            [
                                dbc.CardHeader("Property Purchases by Color Group"),
                                dbc.CardBody(dcc.Graph(id="color-group-chart")),
                            ],
                            className="h-100",
                        ),
                        lg=6,
                        className="mb-4",
                    ),
                    dbc.Col(
                        dbc.Card(
                            [
                                dbc.CardHeader("Cash Management by Strategy"),
                                dbc.CardBody(dcc.Graph(id="cash-management-chart")),
                            ],
                            className="h-100",
                        ),
                        lg=6,
                        className="mb-4",
                    ),
                ]
            ),

            # Property heatmap
            dbc.Row(
                dbc.Col(
                    dbc.Card(
                        [
                            dbc.CardHeader(
                                [
                                    html.I(className="fas fa-th me-2"),
                                    "Property Purchase Frequency Heatmap",
                                ]
                            ),
                            dbc.CardBody(dcc.Graph(id="property-heatmap")),
                        ]
                    ),
                    className="mb-4",
                )
            ),

            # Strategy comparison
            dbc.Row(
                [
                    dbc.Col(
                        dbc.Card(
                            [
                                dbc.CardHeader("Bankruptcy Rate by Strategy"),
                                dbc.CardBody(dcc.Graph(id="bankruptcy-chart")),
                            ],
                            className="h-100",
                        ),
                        lg=6,
                        className="mb-4",
                    ),
                    dbc.Col(
                        dbc.Card(
                            [
                                dbc.CardHeader("Average Net Worth by Strategy"),
                                dbc.CardBody(dcc.Graph(id="net-worth-chart")),
                            ],
                            className="h-100",
                        ),
                        lg=6,
                        className="mb-4",
                    ),
                ]
            ),

            # Refresh interval
            dcc.Interval(
                id="strategy-refresh",
                interval=60000,  # 1 minute
                n_intervals=0,
            ),
        ],
        fluid=True,
    )


@callback(
    Output("strategy-insight", "children"),
    Input("strategy-refresh", "n_intervals"),
)
def update_insight(_):
    """Generate strategy insight."""
    try:
        df = get_strategy_metrics()
        insight = generate_strategy_insight(df)
    except Exception:
        insight = "Unable to generate insights. Run some games with different strategies!"

    return create_insight_card(insight, insight_type="success", title="Strategy Insight")


@callback(
    Output("strategy-metrics-cards", "children"),
    Input("strategy-refresh", "n_intervals"),
    Input("strategy-filter", "value"),
)
def update_metrics_cards(_, strategy_filter):
    """Update strategy metrics cards."""
    try:
        df = get_strategy_metrics()
    except Exception:
        df = pd.DataFrame()

    if df.empty:
        return html.P(
            "No strategy data available. Run games with LLM agents!",
            className="text-muted text-center",
        )

    # Filter if needed
    if strategy_filter and strategy_filter != "all":
        df = df[df["strategy"] == strategy_filter]

    if df.empty:
        return html.P(
            f"No data for strategy: {strategy_filter}",
            className="text-muted text-center",
        )

    cards = []
    for _, row in df.iterrows():
        strategy = row.get("strategy", "unknown")
        win_rate = row.get("win_rate", 0) or 0
        avg_net_worth = row.get("avg_net_worth", 0) or 0
        bankruptcy_rate = row.get("bankruptcy_rate", 0) or 0

        # Color code by win rate
        if win_rate >= 40:
            badge_color = "success"
        elif win_rate >= 25:
            badge_color = "warning"
        else:
            badge_color = "danger"

        cards.append(
            dbc.Col(
                dbc.Card(
                    dbc.CardBody(
                        [
                            html.H5(
                                [
                                    dbc.Badge(
                                        strategy.upper(),
                                        color="info",
                                        className="mb-2",
                                    )
                                ]
                            ),
                            html.Div(
                                [
                                    html.Span("Win Rate: ", className="text-muted"),
                                    dbc.Badge(
                                        f"{win_rate:.1f}%",
                                        color=badge_color,
                                    ),
                                ],
                                className="mb-2",
                            ),
                            html.Div(
                                [
                                    html.Span("Avg Net Worth: ", className="text-muted"),
                                    html.Strong(f"${avg_net_worth:,.0f}"),
                                ],
                                className="mb-2",
                            ),
                            html.Div(
                                [
                                    html.Span("Bankruptcy: ", className="text-muted"),
                                    html.Strong(f"{bankruptcy_rate:.1f}%"),
                                ],
                            ),
                        ]
                    ),
                    className="h-100",
                ),
                md=4,
                className="mb-3",
            )
        )

    return dbc.Row(cards)


@callback(
    Output("color-group-chart", "figure"),
    Input("strategy-refresh", "n_intervals"),
    Input("strategy-filter", "value"),
)
def update_color_group_chart(_, strategy_filter):
    """Update color group preferences chart."""
    try:
        df = get_property_purchases_by_strategy()
    except Exception:
        df = pd.DataFrame()

    if df.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="No property purchase data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="#6b7280"),
        )
        return apply_dark_theme(fig)

    # Filter if needed
    if strategy_filter and strategy_filter != "all":
        df = df[df["strategy"] == strategy_filter]

    if df.empty:
        fig = go.Figure()
        fig.add_annotation(
            text=f"No data for strategy: {strategy_filter}",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="#6b7280"),
        )
        return apply_dark_theme(fig)

    # Group by property name (since color_group may not exist)
    if "property_name" in df.columns:
        grouped_df = df.groupby(["strategy", "property_name"]).agg({
            "purchase_count": "sum"
        }).reset_index()
        # Take top 10 properties by purchase count
        top_props = grouped_df.groupby("property_name")["purchase_count"].sum().nlargest(10).index
        grouped_df = grouped_df[grouped_df["property_name"].isin(top_props)]
        x_col = "property_name"
    else:
        grouped_df = df.groupby("strategy").agg({"purchase_count": "sum"}).reset_index()
        x_col = "strategy"

    fig = px.bar(
        grouped_df,
        x=x_col,
        y="purchase_count",
        color="strategy" if "strategy" in grouped_df.columns and x_col != "strategy" else None,
        barmode="group",
        title="",
        color_discrete_sequence=CHART_COLORS,
    )

    fig.update_layout(
        xaxis_title="Property" if x_col == "property_name" else "Strategy",
        yaxis_title="Purchase Count",
        legend_title="Strategy",
    )

    return apply_dark_theme(fig)


@callback(
    Output("cash-management-chart", "figure"),
    Input("strategy-refresh", "n_intervals"),
)
def update_cash_management(_):
    """Update cash management chart."""
    try:
        df = get_strategy_metrics()
    except Exception:
        df = pd.DataFrame()

    if df.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="No strategy data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="#6b7280"),
        )
        return apply_dark_theme(fig)

    # Create bar chart showing average net worth by strategy
    fig = px.bar(
        df,
        x="strategy",
        y="avg_net_worth",
        title="",
        color="strategy",
        color_discrete_sequence=CHART_COLORS,
        text_auto=",.0f",
    )

    fig.update_layout(
        xaxis_title="Strategy",
        yaxis_title="Average Net Worth ($)",
        showlegend=False,
    )

    return apply_dark_theme(fig)


@callback(
    Output("property-heatmap", "figure"),
    Input("strategy-refresh", "n_intervals"),
    Input("strategy-filter", "value"),
)
def update_property_heatmap(_, strategy_filter):
    """Update property purchase heatmap."""
    try:
        df = get_property_purchases_by_strategy()
    except Exception:
        df = pd.DataFrame()

    if df.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="No property data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="#6b7280"),
        )
        return apply_dark_theme(fig)

    # Filter if needed
    if strategy_filter and strategy_filter != "all":
        df = df[df["strategy"] == strategy_filter]

    if df.empty:
        fig = go.Figure()
        fig.add_annotation(
            text=f"No data for strategy: {strategy_filter}",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="#6b7280"),
        )
        return apply_dark_theme(fig)

    # Check which position column exists
    pos_col = "position" if "position" in df.columns else "property_position" if "property_position" in df.columns else None

    if pos_col is None or "strategy" not in df.columns:
        fig = go.Figure()
        fig.add_annotation(
            text="Missing required columns for heatmap",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="#6b7280"),
        )
        return apply_dark_theme(fig)

    # Pivot for heatmap
    pivot_df = df.pivot_table(
        index="strategy",
        columns=pos_col,
        values="purchase_count",
        aggfunc="sum",
        fill_value=0,
    )

    # Create property names for x-axis (BOARD_NAMES is a list, not dict)
    positions = list(pivot_df.columns)
    property_names = []
    for pos in positions:
        try:
            pos_int = int(pos)
            if 0 <= pos_int < len(BOARD_NAMES):
                property_names.append(BOARD_NAMES[pos_int])
            else:
                property_names.append(f"Pos {pos}")
        except (ValueError, TypeError):
            property_names.append(f"Pos {pos}")

    fig = go.Figure(
        data=go.Heatmap(
            z=pivot_df.values,
            x=property_names,
            y=list(pivot_df.index),
            colorscale="Viridis",
            hovertemplate="Strategy: %{y}<br>Property: %{x}<br>Purchases: %{z}<extra></extra>",
        )
    )

    fig.update_layout(
        xaxis_title="Property",
        yaxis_title="Strategy",
        xaxis=dict(tickangle=45),
    )

    return apply_dark_theme(fig)


@callback(
    Output("bankruptcy-chart", "figure"),
    Input("strategy-refresh", "n_intervals"),
)
def update_bankruptcy_chart(_):
    """Update bankruptcy rate chart."""
    try:
        df = get_strategy_metrics()
    except Exception:
        df = pd.DataFrame()

    if df.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="No strategy data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="#6b7280"),
        )
        return apply_dark_theme(fig)

    fig = px.bar(
        df,
        x="strategy",
        y="bankruptcy_rate",
        title="",
        color="bankruptcy_rate",
        color_continuous_scale="Reds",
        text_auto=".1f",
    )

    fig.update_layout(
        xaxis_title="Strategy",
        yaxis_title="Bankruptcy Rate (%)",
        showlegend=False,
    )

    return apply_dark_theme(fig)


@callback(
    Output("net-worth-chart", "figure"),
    Input("strategy-refresh", "n_intervals"),
)
def update_net_worth_chart(_):
    """Update net worth chart."""
    try:
        df = get_strategy_metrics()
    except Exception:
        df = pd.DataFrame()

    if df.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="No strategy data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="#6b7280"),
        )
        return apply_dark_theme(fig)

    fig = px.bar(
        df,
        x="strategy",
        y="avg_net_worth",
        title="",
        color="avg_net_worth",
        color_continuous_scale="Greens",
        text_auto=",.0f",
    )

    fig.update_layout(
        xaxis_title="Strategy",
        yaxis_title="Average Net Worth ($)",
        showlegend=False,
    )

    return apply_dark_theme(fig)

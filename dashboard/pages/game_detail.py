"""
Game Detail page - Deep dive into a single game.
"""

import json

import dash_bootstrap_components as dbc
from dash import dcc, html, callback, Input, Output, State
import pandas as pd
import plotly.graph_objects as go

from dashboard.components.charts import create_line_chart, apply_dark_theme
from dashboard.data import (
    get_game_by_id,
    get_game_players,
    get_game_events,
    get_recent_games,
    get_llm_decisions_for_game,
    get_cash_timeline_data,
)
from dashboard.config import PLAYER_COLORS, BOARD_NAMES


def create_layout():
    """Create the game detail page layout."""
    return dbc.Container(
        [
            # Page header
            dbc.Row(
                dbc.Col(
                    html.H2(
                        [
                            html.I(className="fas fa-search me-2"),
                            "Game Analysis",
                        ],
                        className="mb-4",
                    )
                )
            ),

            # Game selector
            dbc.Row(
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(
                            [
                                dbc.Row(
                                    [
                                        dbc.Col(
                                            [
                                                html.Label("Select Game", className="fw-bold"),
                                                dcc.Dropdown(
                                                    id="game-selector",
                                                    placeholder="Choose a game to analyze...",
                                                    className="dash-dropdown",
                                                ),
                                            ],
                                            md=8,
                                        ),
                                        dbc.Col(
                                            [
                                                html.Label("Or enter Game ID", className="fw-bold"),
                                                dbc.Input(
                                                    id="game-id-input",
                                                    placeholder="e.g., batch-abc123def456",
                                                    type="text",
                                                ),
                                            ],
                                            md=4,
                                        ),
                                    ]
                                ),
                            ]
                        ),
                        className="dropdown-card",
                        style={"overflow": "visible", "zIndex": 1000},
                    ),
                    className="mb-4",
                    style={"position": "relative", "zIndex": 1000},
                )
            ),

            # Game info card
            html.Div(id="game-info-card", className="mb-4"),

            # Players table
            html.Div(id="players-table", className="mb-4"),

            # Charts row
            dbc.Row(
                [
                    dbc.Col(
                        dbc.Card(
                            [
                                dbc.CardHeader("Cash Over Time"),
                                dbc.CardBody(dcc.Graph(id="cash-timeline")),
                            ],
                            className="h-100",
                        ),
                        lg=8,
                        className="mb-4",
                    ),
                    dbc.Col(
                        dbc.Card(
                            [
                                dbc.CardHeader("Game Stats"),
                                dbc.CardBody(html.Div(id="game-stats")),
                            ],
                            className="h-100",
                        ),
                        lg=4,
                        className="mb-4",
                    ),
                ]
            ),

            # Event log and LLM decisions
            dbc.Row(
                [
                    dbc.Col(
                        dbc.Card(
                            [
                                dbc.CardHeader(
                                    [
                                        html.I(className="fas fa-list me-2"),
                                        "Event Log",
                                    ]
                                ),
                                dbc.CardBody(
                                    [
                                        dbc.Input(
                                            id="event-search",
                                            placeholder="Filter events...",
                                            type="text",
                                            className="mb-3",
                                        ),
                                        html.Div(
                                            id="event-log",
                                            style={"maxHeight": "400px", "overflowY": "auto"},
                                        ),
                                    ]
                                ),
                            ],
                            className="h-100",
                        ),
                        lg=6,
                        className="mb-4",
                    ),
                    dbc.Col(
                        dbc.Card(
                            [
                                dbc.CardHeader(
                                    [
                                        html.I(className="fas fa-brain me-2"),
                                        "LLM Decisions",
                                    ]
                                ),
                                dbc.CardBody(
                                    html.Div(
                                        id="llm-decisions",
                                        style={"maxHeight": "400px", "overflowY": "auto"},
                                    )
                                ),
                            ],
                            className="h-100",
                        ),
                        lg=6,
                        className="mb-4",
                    ),
                ]
            ),

            # Store for selected game
            dcc.Store(id="selected-game-store"),

            # Interval for refreshing game list
            dcc.Interval(
                id="game-list-refresh",
                interval=30000,
                n_intervals=0,
            ),
        ],
        fluid=True,
    )


@callback(
    Output("game-selector", "options"),
    Input("game-list-refresh", "n_intervals"),
)
def update_game_options(_):
    """Update game selector options."""
    try:
        df = get_recent_games(limit=50)
    except Exception:
        df = pd.DataFrame()

    if df.empty:
        return []

    options = []
    for _, row in df.iterrows():
        game_id = row.get("game_id", "Unknown")
        status = row.get("status", "unknown")
        winner = row.get("winner_name", "No winner")
        turns = row.get("total_turns", 0)
        label = f"{game_id} | {status} | {winner} | {turns} turns"
        options.append({"label": label, "value": game_id})

    return options


@callback(
    Output("selected-game-store", "data"),
    Input("game-selector", "value"),
    Input("game-id-input", "value"),
)
def update_selected_game(selector_value, input_value):
    """Update selected game from either input."""
    # Prioritize direct input if provided
    if input_value and len(input_value) > 5:
        return input_value
    return selector_value


@callback(
    Output("game-info-card", "children"),
    Input("selected-game-store", "data"),
)
def update_game_info(game_id):
    """Update game info card."""
    if not game_id:
        return dbc.Alert(
            "Select a game above to view details.",
            color="info",
        )

    try:
        game = get_game_by_id(game_id)
    except Exception:
        game = None

    if not game:
        return dbc.Alert(
            f"Game '{game_id}' not found.",
            color="warning",
        )

    status_color = {
        "finished": "success",
        "running": "primary",
        "paused": "warning",
        "error": "danger",
    }.get(game.get("status"), "secondary")

    return dbc.Card(
        dbc.CardBody(
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.H4(game.get("game_id", "Unknown"), className="mb-2"),
                            dbc.Badge(
                                game.get("status", "unknown").upper(),
                                color=status_color,
                                className="me-2",
                            ),
                        ],
                        md=4,
                    ),
                    dbc.Col(
                        [
                            html.P(
                                [
                                    html.Strong("Total Turns: "),
                                    str(game.get("total_turns", 0)),
                                ],
                                className="mb-1",
                            ),
                            html.P(
                                [
                                    html.Strong("Winner: "),
                                    f"Player {game.get('winner_id')}"
                                    if game.get("winner_id") is not None
                                    else "None",
                                ],
                                className="mb-1",
                            ),
                        ],
                        md=4,
                    ),
                    dbc.Col(
                        [
                            html.P(
                                [
                                    html.Strong("Started: "),
                                    str(game.get("started_at", "-"))[:19],
                                ],
                                className="mb-1",
                            ),
                            html.P(
                                [
                                    html.Strong("Finished: "),
                                    str(game.get("finished_at", "-"))[:19]
                                    if game.get("finished_at")
                                    else "-",
                                ],
                                className="mb-1",
                            ),
                        ],
                        md=4,
                    ),
                ]
            )
        ),
        className="bg-dark",
    )


@callback(
    Output("players-table", "children"),
    Input("selected-game-store", "data"),
)
def update_players_table(game_id):
    """Update players table."""
    if not game_id:
        return None

    try:
        df = get_game_players(game_id)
    except Exception:
        df = pd.DataFrame()

    if df.empty:
        return None

    rows = []
    for idx, row in df.iterrows():
        # Use player_id for color assignment, not iteration index
        player_id = row.get("player_id", idx)
        player_color = PLAYER_COLORS[int(player_id) % len(PLAYER_COLORS)]
        winner_badge = (
            dbc.Badge("WINNER", color="success", className="ms-2")
            if row.get("is_winner")
            else ""
        )
        bankrupt_badge = (
            dbc.Badge("BANKRUPT", color="danger", className="ms-2")
            if row.get("is_bankrupt")
            else ""
        )

        rows.append(
            html.Tr(
                [
                    html.Td(
                        [
                            html.Span(
                                "",
                                style={
                                    "display": "inline-block",
                                    "width": "12px",
                                    "height": "12px",
                                    "borderRadius": "50%",
                                    "backgroundColor": player_color,
                                    "marginRight": "8px",
                                },
                            ),
                            row.get("name", "Unknown"),
                            winner_badge,
                            bankrupt_badge,
                        ]
                    ),
                    html.Td(
                        dbc.Badge(
                            row.get("agent_type", "unknown"),
                            color="info" if row.get("agent_type") == "llm" else "secondary",
                        )
                    ),
                    html.Td(f"${row.get('final_cash', 0):,}" if row.get("final_cash") else "-"),
                    html.Td(
                        f"${row.get('final_net_worth', 0):,}"
                        if row.get("final_net_worth")
                        else "-"
                    ),
                    html.Td(f"#{row.get('placement', '-')}" if row.get("placement") else "-"),
                ]
            )
        )

    return dbc.Card(
        [
            dbc.CardHeader("Players"),
            dbc.CardBody(
                dbc.Table(
                    [
                        html.Thead(
                            html.Tr(
                                [
                                    html.Th("Player"),
                                    html.Th("Agent"),
                                    html.Th("Final Cash"),
                                    html.Th("Net Worth"),
                                    html.Th("Placement"),
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
            ),
        ]
    )


@callback(
    Output("cash-timeline", "figure"),
    Input("selected-game-store", "data"),
)
def update_cash_timeline(game_id):
    """Update cash timeline chart showing each player's cash over turns."""
    fig = go.Figure()

    if not game_id:
        fig.add_annotation(
            text="Select a game to view timeline",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=16, color="#6b7280"),
        )
        return apply_dark_theme(fig)

    try:
        df = get_cash_timeline_data(game_id)
    except Exception:
        df = pd.DataFrame()

    if df.empty:
        fig.add_annotation(
            text="No cash data available for this game",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=14, color="#6b7280"),
        )
        return apply_dark_theme(fig)

    # Get unique players
    players = df[["player_id", "player_name"]].drop_duplicates()

    # Create a line for each player
    for _, player in players.iterrows():
        player_id = player["player_id"]
        player_name = player["player_name"]
        player_color = PLAYER_COLORS[int(player_id) % len(PLAYER_COLORS)]

        # Get this player's cash data
        player_data = df[df["player_id"] == player_id].copy()

        # Sort by turn number and keep last value per turn (in case of multiple events)
        player_data = player_data.sort_values("turn_number")
        player_data = player_data.groupby("turn_number").last().reset_index()

        fig.add_trace(
            go.Scatter(
                x=player_data["turn_number"],
                y=player_data["cash"],
                mode="lines+markers",
                name=player_name,
                line=dict(color=player_color, width=2),
                marker=dict(size=4),
                hovertemplate=(
                    f"<b>{player_name}</b><br>"
                    "Turn %{x}<br>"
                    "Cash: $%{y:,.0f}<extra></extra>"
                ),
            )
        )

    # Update layout
    fig.update_layout(
        xaxis_title="Turn",
        yaxis_title="Cash ($)",
        hovermode="x unified",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
        ),
        margin=dict(l=60, r=20, t=40, b=60),
    )

    # Add starting cash reference line
    fig.add_hline(
        y=1500,
        line_dash="dash",
        line_color="#6b7280",
        annotation_text="Starting cash ($1,500)",
        annotation_position="bottom right",
    )

    return apply_dark_theme(fig)


@callback(
    Output("game-stats", "children"),
    Input("selected-game-store", "data"),
)
def update_game_stats(game_id):
    """Update game statistics panel."""
    if not game_id:
        return html.P("Select a game to view stats.", className="text-muted")

    try:
        events = get_game_events(game_id, limit=10000)
    except Exception:
        events = pd.DataFrame()

    if events.empty:
        return html.P("No events found.", className="text-muted")

    # Count event types
    event_counts = events["event_type"].value_counts().head(10)

    stats = []
    for event_type, count in event_counts.items():
        stats.append(
            html.Div(
                [
                    html.Span(event_type, className="text-muted"),
                    html.Span(str(count), className="float-end fw-bold"),
                ],
                className="mb-2",
            )
        )

    return html.Div(stats)


@callback(
    Output("event-log", "children"),
    Input("selected-game-store", "data"),
    Input("event-search", "value"),
)
def update_event_log(game_id, search_term):
    """Update event log."""
    if not game_id:
        return html.P("Select a game to view events.", className="text-muted")

    try:
        df = get_game_events(game_id, limit=200)
    except Exception:
        df = pd.DataFrame()

    if df.empty:
        return html.P("No events found.", className="text-muted")

    # Filter by search term
    if search_term:
        search_lower = search_term.lower()
        df = df[
            df["event_type"].str.lower().str.contains(search_lower, na=False)
            | df["payload"].astype(str).str.lower().str.contains(search_lower, na=False)
        ]

    items = []
    for _, row in df.iterrows():
        event_type = row.get("event_type", "unknown")
        turn = row.get("turn_number", 0)
        player_id = row.get("actor_player_id")

        # Format event
        badge_color = {
            "dice_roll": "primary",
            "property_purchased": "success",
            "rent_paid": "warning",
            "turn_start": "secondary",
            "auction_start": "info",
            "auction_won": "info",
        }.get(event_type, "light")

        player_text = f"P{player_id}" if player_id is not None else ""

        items.append(
            dbc.ListGroupItem(
                [
                    dbc.Badge(f"T{turn}", color="dark", className="me-2"),
                    dbc.Badge(event_type, color=badge_color, className="me-2"),
                    html.Small(player_text, className="text-muted"),
                ],
                className="py-2",
            )
        )

    return dbc.ListGroup(items[:100], flush=True)


@callback(
    Output("llm-decisions", "children"),
    Input("selected-game-store", "data"),
)
def update_llm_decisions(game_id):
    """Update LLM decisions panel."""
    if not game_id:
        return html.P("Select a game to view LLM decisions.", className="text-muted")

    try:
        df = get_llm_decisions_for_game(game_id, limit=50)
    except Exception:
        df = pd.DataFrame()

    if df.empty:
        return html.P(
            "No LLM decisions found for this game. (Only LLM agents log decisions.)",
            className="text-muted",
        )

    items = []
    for _, row in df.iterrows():
        turn = row.get("turn_number", 0)
        player_id = row.get("player_id", 0)
        reasoning = row.get("reasoning", "No reasoning provided")
        action = row.get("chosen_action", {})

        if isinstance(action, str):
            try:
                action = json.loads(action)
            except Exception:
                action = {"action_type": action}

        action_type = action.get("action_type", "unknown") if isinstance(action, dict) else str(action)

        items.append(
            dbc.Card(
                dbc.CardBody(
                    [
                        html.Div(
                            [
                                dbc.Badge(f"Turn {turn}", color="dark", className="me-2"),
                                dbc.Badge(f"Player {player_id}", color="primary", className="me-2"),
                                dbc.Badge(action_type, color="success"),
                            ],
                            className="mb-2",
                        ),
                        html.Small(
                            reasoning[:200] + "..." if len(reasoning) > 200 else reasoning,
                            className="text-muted",
                        ),
                    ]
                ),
                className="mb-2",
            )
        )

    return html.Div(items[:20])

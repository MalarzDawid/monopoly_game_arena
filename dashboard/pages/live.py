"""
Live Dashboard page - Real-time game monitoring.
"""

import json

import dash_bootstrap_components as dbc
from dash import dcc, html, callback, Input, Output, State, ALL, ctx
import pandas as pd
import plotly.graph_objects as go

from dashboard.components.charts import apply_dark_theme
from dashboard.data import (
    get_active_games,
    get_game_by_id,
    get_game_players,
    get_game_events,
    get_llm_decisions_for_game,
)
from dashboard.config import PLAYER_COLORS, BOARD_NAMES


def create_layout():
    """Create the live dashboard page layout."""
    return dbc.Container(
        [
            # Page header
            dbc.Row(
                dbc.Col(
                    html.H2(
                        [
                            html.I(className="fas fa-satellite-dish me-2"),
                            "Live Game Monitor",
                            dbc.Badge(
                                "LIVE",
                                color="danger",
                                className="ms-2 pulse-badge",
                            ),
                        ],
                        className="mb-4",
                    )
                )
            ),

            # Refresh status
            dbc.Row(
                dbc.Col(
                    html.Div(
                        [
                            html.I(className="fas fa-sync-alt me-2"),
                            html.Span(id="last-update-time", className="text-muted"),
                        ],
                        className="mb-3",
                    ),
                    className="text-end",
                )
            ),

            # Main content
            dbc.Row(
                [
                    # Left panel - Active games list
                    dbc.Col(
                        dbc.Card(
                            [
                                dbc.CardHeader(
                                    [
                                        html.I(className="fas fa-list me-2"),
                                        "Active Games",
                                    ]
                                ),
                                dbc.CardBody(
                                    html.Div(
                                        id="active-games-list",
                                        style={"maxHeight": "600px", "overflowY": "auto"},
                                    )
                                ),
                            ],
                            className="h-100",
                        ),
                        lg=4,
                        className="mb-4",
                    ),

                    # Right panel - Selected game details
                    dbc.Col(
                        [
                            # Game info header
                            html.Div(id="selected-game-header", className="mb-3"),

                            # Player status
                            dbc.Card(
                                [
                                    dbc.CardHeader("Player Status"),
                                    dbc.CardBody(html.Div(id="player-status-panel")),
                                ],
                                className="mb-4",
                            ),

                            # Two columns for events and board
                            dbc.Row(
                                [
                                    # Live event feed
                                    dbc.Col(
                                        dbc.Card(
                                            [
                                                dbc.CardHeader(
                                                    [
                                                        html.I(className="fas fa-stream me-2"),
                                                        "Live Event Feed",
                                                    ]
                                                ),
                                                dbc.CardBody(
                                                    html.Div(
                                                        id="live-events-feed",
                                                        style={
                                                            "maxHeight": "300px",
                                                            "overflowY": "auto",
                                                        },
                                                    )
                                                ),
                                            ],
                                            className="h-100",
                                        ),
                                        lg=6,
                                    ),

                                    # Mini board / Current turn info
                                    dbc.Col(
                                        dbc.Card(
                                            [
                                                dbc.CardHeader("Current Turn"),
                                                dbc.CardBody(
                                                    html.Div(id="current-turn-panel")
                                                ),
                                            ],
                                            className="h-100",
                                        ),
                                        lg=6,
                                    ),
                                ]
                            ),
                        ],
                        lg=8,
                        className="mb-4",
                    ),
                ]
            ),

            # Store for selected game
            dcc.Store(id="live-selected-game"),

            # URL location for game_id parameter
            dcc.Location(id="live-url", refresh=False),

            # Fast refresh interval (2 seconds for live updates)
            dcc.Interval(
                id="live-refresh",
                interval=2000,  # 2 seconds
                n_intervals=0,
            ),

            # Slower refresh for games list (10 seconds)
            dcc.Interval(
                id="games-list-refresh",
                interval=10000,  # 10 seconds
                n_intervals=0,
            ),
        ],
        fluid=True,
    )


@callback(
    Output("live-selected-game", "data"),
    Input("live-url", "search"),
    Input("active-games-list", "children"),
    State("live-selected-game", "data"),
)
def update_selected_game_from_url(search, _, current_selection):
    """Update selected game from URL parameter."""
    if search:
        # Parse ?game_id=xxx from URL
        params = dict(p.split("=") for p in search[1:].split("&") if "=" in p)
        game_id = params.get("game_id")
        if game_id:
            return game_id
    return current_selection


@callback(
    Output("last-update-time", "children"),
    Input("live-refresh", "n_intervals"),
)
def update_timestamp(n):
    """Update last refresh timestamp."""
    from datetime import datetime
    return f"Last updated: {datetime.now().strftime('%H:%M:%S')}"


@callback(
    Output("active-games-list", "children"),
    Input("games-list-refresh", "n_intervals"),
)
def update_active_games(_):
    """Update list of active games."""
    try:
        df = get_active_games()
    except Exception:
        df = pd.DataFrame()

    if df.empty:
        return dbc.Alert(
            [
                html.I(className="fas fa-info-circle me-2"),
                "No active games. Start a game to see it here!",
            ],
            color="info",
        )

    cards = []
    for _, row in df.iterrows():
        game_id = row.get("game_id", "Unknown")
        status = row.get("status", "unknown")
        current_turn = row.get("current_turn", 0)
        player_count = row.get("player_count", 0)

        # Status color
        status_color = {
            "running": "success",
            "paused": "warning",
        }.get(status, "secondary")

        cards.append(
            dbc.Card(
                dbc.CardBody(
                    [
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        html.Strong(game_id[:20] + "..." if len(game_id) > 20 else game_id),
                                        html.Br(),
                                        dbc.Badge(status.upper(), color=status_color),
                                    ],
                                    width=8,
                                ),
                                dbc.Col(
                                    [
                                        html.Small(f"Turn {current_turn}", className="text-muted"),
                                        html.Br(),
                                        html.Small(f"{player_count} players", className="text-muted"),
                                    ],
                                    width=4,
                                    className="text-end",
                                ),
                            ]
                        ),
                    ]
                ),
                className="mb-2 game-card",
                id={"type": "game-card", "index": game_id},
                style={"cursor": "pointer"},
            )
        )

    return html.Div(cards)


@callback(
    Output("selected-game-header", "children"),
    Input("live-selected-game", "data"),
    Input("live-refresh", "n_intervals"),
)
def update_game_header(game_id, _):
    """Update selected game header."""
    if not game_id:
        return dbc.Alert(
            "Select a game from the list to view live details.",
            color="info",
        )

    try:
        game = get_game_by_id(game_id)
    except Exception:
        game = None

    if not game:
        return dbc.Alert(
            f"Game '{game_id}' not found or has ended.",
            color="warning",
        )

    status = game.get("status", "unknown")
    status_color = {
        "running": "success",
        "paused": "warning",
        "finished": "secondary",
    }.get(status, "secondary")

    return dbc.Card(
        dbc.CardBody(
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.H4(game_id, className="mb-1"),
                            dbc.Badge(
                                status.upper(),
                                color=status_color,
                                className="me-2",
                            ),
                            dbc.Badge(
                                f"Turn {game.get('total_turns', 0)}",
                                color="dark",
                            ),
                        ],
                        md=8,
                    ),
                    dbc.Col(
                        [
                            html.Small("Started: ", className="text-muted"),
                            html.Span(str(game.get("started_at", "-"))[:19]),
                        ],
                        md=4,
                        className="text-end",
                    ),
                ]
            )
        ),
        className="bg-dark border-primary",
    )


@callback(
    Output("player-status-panel", "children"),
    Input("live-selected-game", "data"),
    Input("live-refresh", "n_intervals"),
)
def update_player_status(game_id, _):
    """Update player status panel."""
    if not game_id:
        return html.P("Select a game to view player status.", className="text-muted")

    try:
        df = get_game_players(game_id)
    except Exception:
        df = pd.DataFrame()

    if df.empty:
        return html.P("No player data available.", className="text-muted")

    player_cards = []
    for idx, row in df.iterrows():
        name = row.get("name", f"Player {idx}")
        cash = row.get("final_cash", 0) or 0
        net_worth = row.get("final_net_worth", 0) or 0
        is_bankrupt = row.get("is_bankrupt", False)
        agent_type = row.get("agent_type", "unknown")
        color = PLAYER_COLORS[idx % len(PLAYER_COLORS)]

        # Status indicator
        if is_bankrupt:
            status_badge = dbc.Badge("BANKRUPT", color="danger")
        else:
            status_badge = dbc.Badge("ACTIVE", color="success")

        # Cash bar (relative to starting $1500)
        cash_percent = min(100, (cash / 1500) * 100)

        player_cards.append(
            dbc.Col(
                dbc.Card(
                    dbc.CardBody(
                        [
                            html.Div(
                                [
                                    html.Span(
                                        "",
                                        style={
                                            "display": "inline-block",
                                            "width": "12px",
                                            "height": "12px",
                                            "borderRadius": "50%",
                                            "backgroundColor": color,
                                            "marginRight": "8px",
                                        },
                                    ),
                                    html.Strong(name),
                                    status_badge,
                                ],
                                className="mb-2",
                            ),
                            html.Small(
                                [
                                    dbc.Badge(agent_type, color="info", className="me-2"),
                                    f"${cash:,}",
                                ],
                                className="d-block mb-2",
                            ),
                            dbc.Progress(
                                value=cash_percent,
                                color="success" if cash > 500 else "warning" if cash > 100 else "danger",
                                className="mb-1",
                                style={"height": "6px"},
                            ),
                            html.Small(f"Net worth: ${net_worth:,}", className="text-muted"),
                        ]
                    ),
                    className="h-100",
                ),
                md=6,
                lg=3,
                className="mb-2",
            )
        )

    return dbc.Row(player_cards)


@callback(
    Output("live-events-feed", "children"),
    Input("live-selected-game", "data"),
    Input("live-refresh", "n_intervals"),
)
def update_events_feed(game_id, _):
    """Update live events feed."""
    if not game_id:
        return html.P("Select a game to view events.", className="text-muted")

    try:
        df = get_game_events(game_id, limit=50)
    except Exception:
        df = pd.DataFrame()

    if df.empty:
        return html.P("No events yet.", className="text-muted")

    # Reverse to show newest first
    df = df.iloc[::-1]

    items = []
    for _, row in df.head(30).iterrows():
        event_type = row.get("event_type", "unknown")
        turn = row.get("turn_number", 0)
        player_id = row.get("actor_player_id")

        # Event type badge colors
        badge_color = {
            "dice_roll": "primary",
            "property_purchased": "success",
            "rent_paid": "warning",
            "turn_start": "secondary",
            "turn_end": "secondary",
            "auction_start": "info",
            "auction_won": "info",
            "bankruptcy": "danger",
            "game_start": "primary",
            "game_end": "dark",
        }.get(event_type, "light")

        # Format event description
        payload = row.get("payload", {})
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except Exception:
                payload = {}

        description = _format_event_description(event_type, payload)

        items.append(
            html.Div(
                [
                    dbc.Badge(f"T{turn}", color="dark", className="me-1"),
                    dbc.Badge(event_type, color=badge_color, className="me-1"),
                    html.Small(
                        f"P{player_id}" if player_id is not None else "",
                        className="text-muted me-2",
                    ),
                    html.Small(description, className="text-muted"),
                ],
                className="mb-2 py-1 border-bottom border-secondary",
            )
        )

    return html.Div(items)


def _format_event_description(event_type: str, payload: dict) -> str:
    """Format event payload into human-readable description."""
    if event_type == "dice_roll":
        dice = payload.get("dice", [0, 0])
        return f"Rolled {dice[0]}+{dice[1]}={sum(dice)}"
    elif event_type == "property_purchased":
        prop = payload.get("property_name", "property")
        price = payload.get("price", 0)
        return f"Bought {prop} for ${price}"
    elif event_type == "rent_paid":
        amount = payload.get("amount", 0)
        return f"Paid ${amount} rent"
    elif event_type == "auction_won":
        prop = payload.get("property_name", "property")
        bid = payload.get("winning_bid", 0)
        return f"Won {prop} for ${bid}"
    elif event_type == "bankruptcy":
        return "Went bankrupt"
    return ""


@callback(
    Output("current-turn-panel", "children"),
    Input("live-selected-game", "data"),
    Input("live-refresh", "n_intervals"),
)
def update_current_turn(game_id, _):
    """Update current turn panel."""
    if not game_id:
        return html.P("Select a game to view turn info.", className="text-muted")

    try:
        game = get_game_by_id(game_id)
        players_df = get_game_players(game_id)
        events_df = get_game_events(game_id, limit=10)
    except Exception:
        return html.P("Error loading turn info.", className="text-muted")

    if not game:
        return html.P("Game not found.", className="text-muted")

    current_turn = game.get("total_turns", 0)
    status = game.get("status", "unknown")

    # Get current player (approximate from recent events)
    current_player = "Unknown"
    if not events_df.empty:
        last_event = events_df.iloc[-1]
        player_id = last_event.get("actor_player_id")
        if player_id is not None and not players_df.empty:
            player_row = players_df[players_df.index == player_id]
            if not player_row.empty:
                current_player = player_row.iloc[0].get("name", f"Player {player_id}")

    # Winner info if game finished
    winner_info = None
    if status == "finished" and game.get("winner_id") is not None:
        winner_id = game.get("winner_id")
        if not players_df.empty:
            winner_row = players_df[players_df.index == winner_id]
            if not winner_row.empty:
                winner_name = winner_row.iloc[0].get("name", f"Player {winner_id}")
                winner_info = dbc.Alert(
                    [
                        html.I(className="fas fa-trophy me-2"),
                        f"Winner: {winner_name}",
                    ],
                    color="success",
                )

    return html.Div(
        [
            html.Div(
                [
                    html.H1(str(current_turn), className="display-4 text-center"),
                    html.P("Current Turn", className="text-muted text-center"),
                ],
                className="mb-3",
            ),
            html.Hr(),
            html.Div(
                [
                    html.P(
                        [
                            html.Strong("Status: "),
                            dbc.Badge(
                                status.upper(),
                                color="success" if status == "running" else "secondary",
                            ),
                        ]
                    ),
                    html.P(
                        [
                            html.Strong("Last Action: "),
                            html.Span(current_player, className="text-muted"),
                        ]
                    ),
                ]
            ),
            winner_info if winner_info else None,
        ]
    )


# Callback to handle game card clicks
@callback(
    Output("live-selected-game", "data", allow_duplicate=True),
    Input({"type": "game-card", "index": ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def select_game(n_clicks):
    """Handle game card click to select game."""
    if not ctx.triggered_id:
        return None
    # ctx.triggered_id contains the id dict of the clicked component
    if isinstance(ctx.triggered_id, dict) and ctx.triggered_id.get("type") == "game-card":
        return ctx.triggered_id.get("index")
    return None

"""
Monopoly Game Arena Dashboard

A comprehensive analytics dashboard for monitoring and analyzing Monopoly games.
Built with Dash and Plotly for interactive data visualization.

Usage:
    python -m dashboard.app
    # or
    python dashboard/app.py

Dashboard will be available at http://localhost:8050
"""

import dash
from dash import dcc, html, Input, Output, callback
import dash_bootstrap_components as dbc

from dashboard.components.navbar import create_navbar
from dashboard.pages import overview, llm_ranking, game_detail, strategy_analysis, live

# Initialize the Dash app with Bootstrap dark theme
app = dash.Dash(
    __name__,
    external_stylesheets=[
        dbc.themes.DARKLY,  # Dark Bootstrap theme
        "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css",  # Font Awesome icons
    ],
    suppress_callback_exceptions=True,
    title="Monopoly Game Arena",
    update_title="Loading...",
    meta_tags=[
        {"name": "viewport", "content": "width=device-width, initial-scale=1"},
    ],
)

# Create the app layout
app.layout = dbc.Container(
    [
        # URL routing
        dcc.Location(id="url", refresh=False),

        # Navigation bar
        create_navbar(),

        # Page content
        html.Div(id="page-content", className="mt-4"),

        # Footer
        html.Footer(
            dbc.Container(
                dbc.Row(
                    dbc.Col(
                        html.P(
                            [
                                "Monopoly Game Arena Dashboard ",
                                html.I(className="fas fa-dice me-1"),
                                " | ",
                                html.A(
                                    "Documentation",
                                    href="http://localhost:8000/docs",
                                    target="_blank",
                                    className="text-muted",
                                ),
                                " | ",
                                html.A(
                                    "Game UI",
                                    href="http://localhost:8000/ui/",
                                    target="_blank",
                                    className="text-muted",
                                ),
                            ],
                            className="text-muted text-center mb-0",
                        ),
                        className="py-3",
                    )
                ),
                fluid=True,
            ),
            className="mt-5 border-top border-secondary",
        ),
    ],
    fluid=True,
    className="px-4",
)


@callback(
    Output("page-content", "children"),
    Input("url", "pathname"),
)
def display_page(pathname):
    """Route to the appropriate page based on URL pathname."""
    if pathname == "/" or pathname == "/overview":
        return overview.create_layout()
    elif pathname == "/ranking":
        return llm_ranking.create_layout()
    elif pathname == "/game":
        return game_detail.create_layout()
    elif pathname == "/strategy":
        return strategy_analysis.create_layout()
    elif pathname == "/live":
        return live.create_layout()
    else:
        # 404 page
        return dbc.Container(
            [
                html.H1("404 - Page Not Found", className="text-danger"),
                html.Hr(),
                html.P(f"The page '{pathname}' does not exist."),
                dbc.Button(
                    "Go to Overview",
                    href="/",
                    color="primary",
                ),
            ],
            className="py-5 text-center",
        )


# Server instance for deployment
server = app.server


def main():
    """Run the dashboard server."""
    print("\n" + "=" * 60)
    print("  MONOPOLY GAME ARENA DASHBOARD")
    print("=" * 60)
    print("\n  Starting dashboard server...")
    print("  Dashboard URL: http://localhost:8050")
    print("\n  Pages:")
    print("    /          - Games Overview")
    print("    /ranking   - LLM Rankings")
    print("    /game      - Game Detail")
    print("    /strategy  - Strategy Analysis")
    print("    /live      - Live Game Monitor")
    print("\n  Press Ctrl+C to stop the server")
    print("=" * 60 + "\n")

    app.run(
        debug=True,
        host="0.0.0.0",
        port=8050,
    )


if __name__ == "__main__":
    main()

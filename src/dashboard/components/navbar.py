"""
Navigation bar component for the dashboard.
"""

import dash_bootstrap_components as dbc
from dash import html


def create_navbar() -> dbc.Navbar:
    """Create the main navigation bar."""
    return dbc.Navbar(
        dbc.Container(
            [
                # Brand/Logo
                dbc.NavbarBrand(
                    [
                        html.I(className="fas fa-dice me-2"),
                        "Monopoly Arena Dashboard",
                    ],
                    href="/",
                    className="fw-bold",
                ),
                # Toggler for mobile
                dbc.NavbarToggler(id="navbar-toggler"),
                # Navigation links
                dbc.Collapse(
                    dbc.Nav(
                        [
                            dbc.NavItem(
                                dbc.NavLink(
                                    [html.I(className="fas fa-home me-1"), "Overview"],
                                    href="/",
                                    active="exact",
                                )
                            ),
                            dbc.NavItem(
                                dbc.NavLink(
                                    [html.I(className="fas fa-trophy me-1"), "LLM Ranking"],
                                    href="/ranking",
                                    active="exact",
                                )
                            ),
                            dbc.NavItem(
                                dbc.NavLink(
                                    [html.I(className="fas fa-search me-1"), "Game Detail"],
                                    href="/game",
                                    active="exact",
                                )
                            ),
                            dbc.NavItem(
                                dbc.NavLink(
                                    [html.I(className="fas fa-chart-bar me-1"), "Strategy Analysis"],
                                    href="/strategy",
                                    active="exact",
                                )
                            ),
                            dbc.NavItem(
                                dbc.NavLink(
                                    [html.I(className="fas fa-broadcast-tower me-1"), "Live"],
                                    href="/live",
                                    active="exact",
                                    className="text-success",
                                )
                            ),
                        ],
                        className="ms-auto",
                        navbar=True,
                    ),
                    id="navbar-collapse",
                    navbar=True,
                ),
                # External link to game UI
                dbc.Nav(
                    [
                        dbc.NavItem(
                            dbc.NavLink(
                                [html.I(className="fas fa-external-link-alt me-1"), "Game UI"],
                                href="http://localhost:8000/ui/",
                                target="_blank",
                                className="ms-3",
                            )
                        ),
                    ],
                    navbar=True,
                ),
            ],
            fluid=True,
        ),
        color="dark",
        dark=True,
        sticky="top",
        className="mb-4",
    )

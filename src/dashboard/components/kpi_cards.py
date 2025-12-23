"""
KPI card components for the dashboard.
"""

from typing import Any, List, Optional

import dash_bootstrap_components as dbc
from dash import html


def create_kpi_card(
    title: str,
    value: Any,
    subtitle: Optional[str] = None,
    icon: str = "fas fa-chart-line",
    color: str = "primary",
    change: Optional[float] = None,
    change_label: str = "vs last period",
) -> dbc.Card:
    """
    Create a KPI card with title, value, and optional change indicator.

    Args:
        title: Card title
        value: Main value to display
        subtitle: Optional subtitle/description
        icon: FontAwesome icon class
        color: Bootstrap color name (primary, success, warning, danger, info)
        change: Optional percentage change (positive or negative)
        change_label: Label for the change indicator
    """
    # Change indicator
    change_element = None
    if change is not None:
        change_color = "success" if change >= 0 else "danger"
        change_icon = "fa-arrow-up" if change >= 0 else "fa-arrow-down"
        change_element = html.Div(
            [
                html.I(className=f"fas {change_icon} me-1"),
                f"{abs(change):.1f}%",
                html.Small(f" {change_label}", className="text-muted ms-1"),
            ],
            className=f"text-{change_color} small mt-2",
        )

    return dbc.Card(
        dbc.CardBody(
            [
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                html.H6(title, className="text-muted text-uppercase mb-1"),
                                html.H3(
                                    str(value),
                                    className="mb-0 fw-bold",
                                ),
                                html.Small(subtitle, className="text-muted") if subtitle else None,
                                change_element,
                            ],
                            width=9,
                        ),
                        dbc.Col(
                            html.Div(
                                html.I(className=f"{icon} fa-2x text-{color}"),
                                className="text-end",
                            ),
                            width=3,
                        ),
                    ],
                    align="center",
                ),
            ]
        ),
        className="h-100 shadow-sm",
    )


def create_kpi_row(cards_data: List[dict]) -> dbc.Row:
    """
    Create a row of KPI cards.

    Args:
        cards_data: List of dicts with keys matching create_kpi_card parameters
    """
    cols = []
    for data in cards_data:
        cols.append(
            dbc.Col(
                create_kpi_card(**data),
                md=6,
                lg=3,
                className="mb-4",
            )
        )

    return dbc.Row(cols)


def create_insight_card(
    insight_text: str,
    insight_type: str = "info",
    title: str = "Insight",
) -> dbc.Alert:
    """
    Create an insight/storytelling card.

    Args:
        insight_text: The insight text to display
        insight_type: Alert type (info, success, warning, primary)
        title: Title for the insight
    """
    icons = {
        "info": "fas fa-lightbulb",
        "success": "fas fa-check-circle",
        "warning": "fas fa-exclamation-triangle",
        "primary": "fas fa-star",
    }

    return dbc.Alert(
        [
            html.H5(
                [
                    html.I(className=f"{icons.get(insight_type, 'fas fa-info-circle')} me-2"),
                    title,
                ],
                className="alert-heading",
            ),
            html.P(insight_text, className="mb-0"),
        ],
        color=insight_type,
        className="shadow-sm",
    )

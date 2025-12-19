"""
Reusable chart components for the dashboard.
"""

from typing import Any, Dict, List, Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from dashboard.config import CHART_TEMPLATE, CHART_COLORS, PROPERTY_COLORS


def apply_dark_theme(fig: go.Figure) -> go.Figure:
    """Apply consistent dark theme to a figure."""
    fig.update_layout(
        template=CHART_TEMPLATE,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#e5e7eb"),
        margin=dict(l=40, r=40, t=40, b=40),
    )
    return fig


def create_timeline_chart(
    df: pd.DataFrame,
    x: str,
    y: str,
    title: str = "Timeline",
    color: Optional[str] = None,
    y_label: str = "",
) -> go.Figure:
    """
    Create a timeline/line chart.

    Args:
        df: DataFrame with the data
        x: Column name for x-axis (usually date)
        y: Column name for y-axis
        title: Chart title
        color: Optional column for color grouping
        y_label: Label for y-axis
    """
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="No data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="#6b7280"),
        )
        return apply_dark_theme(fig)

    if color:
        fig = px.line(
            df, x=x, y=y, color=color,
            title=title,
            color_discrete_sequence=CHART_COLORS,
        )
    else:
        fig = px.line(
            df, x=x, y=y,
            title=title,
            color_discrete_sequence=CHART_COLORS,
        )

    fig.update_traces(mode="lines+markers")
    fig.update_layout(
        xaxis_title="",
        yaxis_title=y_label,
        hovermode="x unified",
    )

    return apply_dark_theme(fig)


def create_bar_chart(
    df: pd.DataFrame,
    x: str,
    y: str,
    title: str = "Bar Chart",
    color: Optional[str] = None,
    orientation: str = "v",
    barmode: str = "group",
    text_auto: bool = True,
) -> go.Figure:
    """
    Create a bar chart.

    Args:
        df: DataFrame with the data
        x: Column name for x-axis (or y if horizontal)
        y: Column name for y-axis (or x if horizontal)
        title: Chart title
        color: Optional column for color grouping
        orientation: "v" for vertical, "h" for horizontal
        barmode: "group", "stack", or "relative"
        text_auto: Whether to show values on bars
    """
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="No data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="#6b7280"),
        )
        return apply_dark_theme(fig)

    fig = px.bar(
        df, x=x, y=y, color=color,
        title=title,
        orientation=orientation,
        barmode=barmode,
        text_auto=text_auto,
        color_discrete_sequence=CHART_COLORS,
    )

    fig.update_layout(
        xaxis_title="",
        yaxis_title="",
    )

    return apply_dark_theme(fig)


def create_pie_chart(
    df: pd.DataFrame,
    values: str,
    names: str,
    title: str = "Distribution",
    hole: float = 0.4,
) -> go.Figure:
    """
    Create a pie/donut chart.

    Args:
        df: DataFrame with the data
        values: Column name for values
        names: Column name for labels
        title: Chart title
        hole: Size of hole (0 for pie, >0 for donut)
    """
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="No data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="#6b7280"),
        )
        return apply_dark_theme(fig)

    fig = px.pie(
        df, values=values, names=names,
        title=title,
        hole=hole,
        color_discrete_sequence=CHART_COLORS,
    )

    fig.update_traces(
        textposition="inside",
        textinfo="percent+label",
    )

    return apply_dark_theme(fig)


def create_heatmap(
    df: pd.DataFrame,
    x: str,
    y: str,
    z: str,
    title: str = "Heatmap",
    color_scale: str = "Viridis",
) -> go.Figure:
    """
    Create a heatmap.

    Args:
        df: DataFrame with the data
        x: Column name for x-axis
        y: Column name for y-axis
        z: Column name for values
        title: Chart title
        color_scale: Plotly color scale name
    """
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="No data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="#6b7280"),
        )
        return apply_dark_theme(fig)

    # Pivot for heatmap
    pivot_df = df.pivot(index=y, columns=x, values=z)

    fig = px.imshow(
        pivot_df,
        title=title,
        color_continuous_scale=color_scale,
        aspect="auto",
    )

    fig.update_layout(
        xaxis_title="",
        yaxis_title="",
    )

    return apply_dark_theme(fig)


def create_line_chart(
    df: pd.DataFrame,
    x: str,
    y: List[str],
    title: str = "Line Chart",
    y_labels: Optional[List[str]] = None,
) -> go.Figure:
    """
    Create a multi-line chart.

    Args:
        df: DataFrame with the data
        x: Column name for x-axis
        y: List of column names for y-axis lines
        title: Chart title
        y_labels: Optional custom labels for each line
    """
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="No data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="#6b7280"),
        )
        return apply_dark_theme(fig)

    fig = go.Figure()

    for i, col in enumerate(y):
        label = y_labels[i] if y_labels and i < len(y_labels) else col
        fig.add_trace(
            go.Scatter(
                x=df[x],
                y=df[col],
                name=label,
                mode="lines+markers",
                line=dict(color=CHART_COLORS[i % len(CHART_COLORS)]),
            )
        )

    fig.update_layout(
        title=title,
        xaxis_title="",
        yaxis_title="",
        hovermode="x unified",
    )

    return apply_dark_theme(fig)


def create_table(
    df: pd.DataFrame,
    title: str = "Table",
    max_rows: int = 100,
) -> go.Figure:
    """
    Create a styled table.

    Args:
        df: DataFrame with the data
        title: Table title
        max_rows: Maximum rows to display
    """
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="No data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="#6b7280"),
        )
        return apply_dark_theme(fig)

    df = df.head(max_rows)

    fig = go.Figure(
        data=[
            go.Table(
                header=dict(
                    values=list(df.columns),
                    fill_color="#1e293b",
                    align="left",
                    font=dict(color="#e5e7eb", size=12),
                ),
                cells=dict(
                    values=[df[col] for col in df.columns],
                    fill_color="#0f172a",
                    align="left",
                    font=dict(color="#e5e7eb", size=11),
                ),
            )
        ]
    )

    fig.update_layout(
        title=title,
        margin=dict(l=0, r=0, t=40, b=0),
    )

    return apply_dark_theme(fig)


def create_radar_chart(
    categories: List[str],
    values: List[float],
    title: str = "Radar Chart",
    fill: bool = True,
) -> go.Figure:
    """
    Create a radar/spider chart.

    Args:
        categories: List of category names
        values: List of values for each category
        title: Chart title
        fill: Whether to fill the area
    """
    fig = go.Figure()

    fig.add_trace(
        go.Scatterpolar(
            r=values + [values[0]],  # Close the polygon
            theta=categories + [categories[0]],
            fill="toself" if fill else None,
            line=dict(color=CHART_COLORS[0]),
            fillcolor=f"rgba(34, 211, 238, 0.3)" if fill else None,
        )
    )

    fig.update_layout(
        title=title,
        polar=dict(
            radialaxis=dict(
                visible=True,
                gridcolor="#374151",
            ),
            angularaxis=dict(
                gridcolor="#374151",
            ),
            bgcolor="rgba(0,0,0,0)",
        ),
    )

    return apply_dark_theme(fig)


def create_gauge_chart(
    value: float,
    title: str = "Gauge",
    min_val: float = 0,
    max_val: float = 100,
    thresholds: Optional[List[float]] = None,
) -> go.Figure:
    """
    Create a gauge chart.

    Args:
        value: Current value
        title: Chart title
        min_val: Minimum value
        max_val: Maximum value
        thresholds: Optional list of threshold values for color steps
    """
    if thresholds is None:
        thresholds = [max_val * 0.33, max_val * 0.66, max_val]

    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=value,
            title={"text": title},
            gauge=dict(
                axis=dict(range=[min_val, max_val], tickcolor="#e5e7eb"),
                bar=dict(color=CHART_COLORS[0]),
                bgcolor="rgba(0,0,0,0)",
                borderwidth=0,
                steps=[
                    {"range": [min_val, thresholds[0]], "color": "#ef4444"},
                    {"range": [thresholds[0], thresholds[1]], "color": "#f59e0b"},
                    {"range": [thresholds[1], max_val], "color": "#22c55e"},
                ],
            ),
        )
    )

    return apply_dark_theme(fig)

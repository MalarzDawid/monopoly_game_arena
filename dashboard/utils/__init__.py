"""
Dashboard utility modules.
"""

from dashboard.utils.storytelling import (
    generate_overview_insight,
    generate_ranking_insight,
    generate_strategy_insight,
)
from dashboard.utils.formatting import (
    format_currency,
    format_percentage,
    format_number,
    truncate_text,
)

__all__ = [
    "generate_overview_insight",
    "generate_ranking_insight",
    "generate_strategy_insight",
    "format_currency",
    "format_percentage",
    "format_number",
    "truncate_text",
]

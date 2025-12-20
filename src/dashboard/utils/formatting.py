"""
Formatting utilities for the dashboard.

This module provides consistent number, currency, and text formatting.
"""

from typing import Optional, Union


def format_currency(value: Union[int, float, None], decimal_places: int = 0) -> str:
    """
    Format a number as currency.

    Args:
        value: The number to format
        decimal_places: Number of decimal places (default 0)

    Returns:
        Formatted string like "$1,234" or "-" for None

    Examples:
        >>> format_currency(1500)
        '$1,500'
        >>> format_currency(1234.56, decimal_places=2)
        '$1,234.56'
        >>> format_currency(None)
        '-'
    """
    if value is None:
        return "-"

    try:
        value = float(value)
        if decimal_places == 0:
            return f"${value:,.0f}"
        else:
            return f"${value:,.{decimal_places}f}"
    except (ValueError, TypeError):
        return "-"


def format_percentage(
    value: Union[int, float, None],
    decimal_places: int = 1,
    include_sign: bool = False,
) -> str:
    """
    Format a number as a percentage.

    Args:
        value: The percentage value (0-100 scale)
        decimal_places: Number of decimal places (default 1)
        include_sign: Whether to include +/- sign (default False)

    Returns:
        Formatted string like "45.2%" or "-" for None

    Examples:
        >>> format_percentage(45.23)
        '45.2%'
        >>> format_percentage(10.5, include_sign=True)
        '+10.5%'
        >>> format_percentage(-5.0, include_sign=True)
        '-5.0%'
    """
    if value is None:
        return "-"

    try:
        value = float(value)
        formatted = f"{value:.{decimal_places}f}%"
        if include_sign and value > 0:
            formatted = "+" + formatted
        return formatted
    except (ValueError, TypeError):
        return "-"


def format_number(
    value: Union[int, float, None],
    decimal_places: int = 0,
    use_thousands: bool = True,
) -> str:
    """
    Format a number with optional thousands separators.

    Args:
        value: The number to format
        decimal_places: Number of decimal places (default 0)
        use_thousands: Whether to use thousands separators (default True)

    Returns:
        Formatted string like "1,234" or "-" for None

    Examples:
        >>> format_number(1234567)
        '1,234,567'
        >>> format_number(1234.567, decimal_places=2)
        '1,234.57'
        >>> format_number(1234, use_thousands=False)
        '1234'
    """
    if value is None:
        return "-"

    try:
        value = float(value)
        if use_thousands:
            if decimal_places == 0:
                return f"{value:,.0f}"
            else:
                return f"{value:,.{decimal_places}f}"
        else:
            if decimal_places == 0:
                return f"{value:.0f}"
            else:
                return f"{value:.{decimal_places}f}"
    except (ValueError, TypeError):
        return "-"


def truncate_text(text: str, max_length: int = 50, suffix: str = "...") -> str:
    """
    Truncate text to a maximum length with suffix.

    Args:
        text: The text to truncate
        max_length: Maximum length including suffix (default 50)
        suffix: Suffix to append when truncated (default "...")

    Returns:
        Truncated text or original if shorter than max_length

    Examples:
        >>> truncate_text("Hello World", max_length=8)
        'Hello...'
        >>> truncate_text("Hi", max_length=10)
        'Hi'
    """
    if not text:
        return ""

    text = str(text)
    if len(text) <= max_length:
        return text

    return text[: max_length - len(suffix)] + suffix


def format_duration(seconds: Union[int, float, None]) -> str:
    """
    Format seconds as human-readable duration.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted string like "2h 30m" or "45s"

    Examples:
        >>> format_duration(9000)
        '2h 30m'
        >>> format_duration(90)
        '1m 30s'
        >>> format_duration(45)
        '45s'
    """
    if seconds is None:
        return "-"

    try:
        seconds = int(seconds)
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            minutes = seconds // 60
            secs = seconds % 60
            if secs > 0:
                return f"{minutes}m {secs}s"
            return f"{minutes}m"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            if minutes > 0:
                return f"{hours}h {minutes}m"
            return f"{hours}h"
    except (ValueError, TypeError):
        return "-"


def format_game_id(game_id: str, max_length: int = 20) -> str:
    """
    Format game ID for display.

    Args:
        game_id: The full game ID
        max_length: Maximum display length

    Returns:
        Formatted game ID, truncated with ... if too long
    """
    if not game_id:
        return "Unknown"

    if len(game_id) <= max_length:
        return game_id

    # Try to show meaningful parts (e.g., batch-abc123def456 -> batch-abc...f456)
    if len(game_id) > max_length + 3:
        half = (max_length - 3) // 2
        return game_id[:half] + "..." + game_id[-half:]

    return truncate_text(game_id, max_length)


def format_rank(rank: int) -> str:
    """
    Format rank with ordinal suffix.

    Args:
        rank: The rank number (1, 2, 3, etc.)

    Returns:
        Formatted string like "1st", "2nd", "3rd", "4th"

    Examples:
        >>> format_rank(1)
        '1st'
        >>> format_rank(2)
        '2nd'
        >>> format_rank(11)
        '11th'
        >>> format_rank(21)
        '21st'
    """
    if rank is None:
        return "-"

    try:
        rank = int(rank)
        if 10 <= rank % 100 <= 20:
            suffix = "th"
        else:
            suffix = {1: "st", 2: "nd", 3: "rd"}.get(rank % 10, "th")
        return f"{rank}{suffix}"
    except (ValueError, TypeError):
        return "-"


def format_change(
    current: Union[int, float],
    previous: Union[int, float],
    as_percentage: bool = True,
) -> tuple[str, str]:
    """
    Format a change between two values.

    Args:
        current: Current value
        previous: Previous value
        as_percentage: Whether to show as percentage change

    Returns:
        Tuple of (formatted_change, color) where color is 'success', 'danger', or 'secondary'

    Examples:
        >>> format_change(110, 100)
        ('+10.0%', 'success')
        >>> format_change(90, 100)
        ('-10.0%', 'danger')
    """
    if current is None or previous is None:
        return ("-", "secondary")

    try:
        current = float(current)
        previous = float(previous)

        if previous == 0:
            if current > 0:
                return ("+inf", "success")
            elif current < 0:
                return ("-inf", "danger")
            else:
                return ("0%", "secondary")

        if as_percentage:
            change = ((current - previous) / abs(previous)) * 100
            formatted = format_percentage(abs(change), include_sign=False)
            if change > 0:
                return (f"+{formatted}", "success")
            elif change < 0:
                return (f"-{formatted}", "danger")
            else:
                return (formatted, "secondary")
        else:
            change = current - previous
            if change > 0:
                return (f"+{format_number(change)}", "success")
            elif change < 0:
                return (f"-{format_number(abs(change))}", "danger")
            else:
                return ("0", "secondary")

    except (ValueError, TypeError):
        return ("-", "secondary")

"""
Dashboard configuration.

Loads settings from environment variables and provides constants
for the dashboard application.

Configuration is managed via `settings.DashboardSettings` (pydantic-settings)
to ensure type safety and a single source of truth.
"""

from pathlib import Path

from settings import get_dashboard_settings

_settings = get_dashboard_settings()

# Database configuration (sync URL for dashboard)
DATABASE_URL = _settings.database_url

# Dashboard server settings
DASHBOARD_HOST = _settings.dashboard_host
DASHBOARD_PORT = _settings.dashboard_port
DASHBOARD_DEBUG = _settings.dashboard_debug

# Main server URL (for API calls)
MAIN_SERVER_URL = _settings.main_server_url
# API base for dashboard data (can be same as MAIN_SERVER_URL)
API_BASE_URL = _settings.api_base_url

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
DASHBOARD_ROOT = Path(__file__).parent

# Player colors (matching existing UI)
PLAYER_COLORS = [
    "#22d3ee",  # Cyan
    "#f59e0b",  # Amber
    "#ef4444",  # Red
    "#84cc16",  # Lime
    "#a78bfa",  # Purple
    "#f472b6",  # Pink
    "#10b981",  # Emerald
    "#eab308",  # Yellow
]

# Property color groups (matching Monopoly board)
PROPERTY_COLORS = {
    "brown": "#8B4513",
    "light-blue": "#87CEEB",
    "pink": "#FF69B4",
    "orange": "#FFA500",
    "red": "#FF0000",
    "yellow": "#FFD700",
    "green": "#228B22",
    "dark-blue": "#00008B",
    "railroad": "#4a4a4a",
    "utility": "#c0c0c0",
}

# Property positions by color group
PROPERTY_GROUPS = {
    "brown": [1, 3],
    "light-blue": [6, 8, 9],
    "pink": [11, 13, 14],
    "orange": [16, 18, 19],
    "red": [21, 23, 24],
    "yellow": [26, 27, 29],
    "green": [31, 32, 34],
    "dark-blue": [37, 39],
    "railroad": [5, 15, 25, 35],
    "utility": [12, 28],
}

# Board space names
BOARD_NAMES = [
    "GO",
    "Mediterranean Avenue", "Community Chest", "Baltic Avenue", "Income Tax", "Reading Railroad",
    "Oriental Avenue", "Chance", "Vermont Avenue", "Connecticut Avenue", "Jail",
    "St. Charles Place", "Electric Company", "States Avenue", "Virginia Avenue", "Pennsylvania Railroad",
    "St. James Place", "Community Chest", "Tennessee Avenue", "New York Avenue", "Free Parking",
    "Kentucky Avenue", "Chance", "Indiana Avenue", "Illinois Avenue", "B. & O. Railroad",
    "Atlantic Avenue", "Ventnor Avenue", "Water Works", "Marvin Gardens", "Go To Jail",
    "Pacific Avenue", "North Carolina Avenue", "Community Chest", "Pennsylvania Avenue", "Short Line",
    "Chance", "Park Place", "Luxury Tax", "Boardwalk",
]

# Strategy descriptions
STRATEGY_DESCRIPTIONS = {
    "aggressive": "Buy everything, bid high, build fast",
    "balanced": "Strategic purchases with $200+ reserve",
    "defensive": "Conservative with $400+ cash reserve",
}

# Chart theme (dark mode to match existing UI)
CHART_TEMPLATE = "plotly_dark"
CHART_COLORS = [
    "#22d3ee", "#f59e0b", "#ef4444", "#84cc16",
    "#a78bfa", "#f472b6", "#10b981", "#eab308",
]

# Refresh intervals (milliseconds)
LIVE_REFRESH_INTERVAL = 2000  # 2 seconds for live dashboard
OVERVIEW_REFRESH_INTERVAL = 30000  # 30 seconds for overview

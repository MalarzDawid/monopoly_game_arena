"""
Lightweight API client for dashboard data.

Uses FastAPI endpoints exposed by the server. Falls back to None on error.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import httpx

from dashboard.config import API_BASE_URL

logger = logging.getLogger(__name__)


def _url(path: str) -> str:
    return f"{API_BASE_URL.rstrip('/')}/{path.lstrip('/')}"


def fetch_json(path: str, params: Optional[dict] = None) -> Optional[Dict[str, Any]]:
    """Fetch JSON from the API; return None on error."""
    try:
        resp = httpx.get(_url(path), params=params or {}, timeout=5.0)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.warning(f"API fetch failed for {path}: {e}")
        return None

"""Fetch and simplify the free CosmyDay daily astrology feed."""

from __future__ import annotations

import re
from datetime import datetime, timezone

import requests

API_URL = "https://api.cosmyday.com/content/daily"
USER_AGENT = "SurfHoroscopes/1.0 (github.com/Lachie-Perris/surf_horoscopes)"


def _daily_tip(text: str) -> str | None:
    match = re.search(r"Today's tip:\s*(.+?)(?:\n|$)", text or "", re.IGNORECASE)
    return match.group(1).strip() if match else None


def fallback_context() -> dict:
    """Return a neutral context so an API outage never stops site generation."""
    return {
        "source": "local fallback",
        "source_url": "https://cosmyday.com/api-docs",
        "date": datetime.now(timezone.utc).date().isoformat(),
        "sun": {"sign": "the current season"},
        "moon": {"sign": "the night sky", "phase_name": "changing", "illumination": None},
        "retrogrades": [],
        "top_aspect": None,
        "signs": {},
    }


def fetch_cosmic_context(timeout: int = 20) -> dict:
    """Fetch one daily payload and retain only fields useful to surf readings."""
    try:
        response = requests.get(API_URL, headers={"User-Agent": USER_AGENT}, timeout=timeout)
        response.raise_for_status()
        payload = response.json()
        sky = payload.get("sky", {})
        moon = sky.get("moon", {})
        retrogrades = [
            name.title() for name, placement in sky.items()
            if isinstance(placement, dict) and placement.get("retrograde")
        ]
        aspects = payload.get("aspects", [])
        sign_context = {}
        for sign, item in payload.get("horoscopes", {}).items():
            sign_context[sign.title()] = {
                "lead_event": item.get("lead_event"),
                "daily_tip": _daily_tip(item.get("content", "")),
            }
        return {
            "source": "CosmyDay",
            "source_url": "https://cosmyday.com/api-docs",
            "date": payload.get("date"),
            "sun": sky.get("sun", {}),
            "moon": {
                "sign": moon.get("sign", "the night sky"),
                "phase_name": moon.get("phase_name", "Changing Moon"),
                "illumination": moon.get("illumination"),
            },
            "retrogrades": retrogrades,
            "top_aspect": aspects[0] if aspects else None,
            "signs": sign_context,
        }
    except (requests.RequestException, ValueError, TypeError):
        return fallback_context()

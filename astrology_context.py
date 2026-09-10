"""Fetch and simplify the free CosmyDay daily astrology feed."""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

import requests

API_URL = "https://api.cosmyday.com/content/daily"
EVENTS_URL = "https://api.cosmyday.com/events/upcoming"
MOON_URL = "https://www.cyclecalcs.com/v2/moon"
PLANETS_URL = "https://www.cyclecalcs.com/v2/planet-board"
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
        "future": {},
    }


def _future_sky(start_date, days, timeout):
    start = f"{start_date.isoformat()}T00:00:00Z"
    params = {"start": start, "count": days, "step": "1d", "verbosity": "compact"}
    moon_response = requests.get(MOON_URL, params={**params, "next_phases": 0}, timeout=timeout)
    moon_response.raise_for_status()
    planet_response = requests.get(
        PLANETS_URL, params={**params, "include": "position,motion"}, timeout=timeout
    )
    planet_response.raise_for_status()
    events_response = requests.get(
        EVENTS_URL,
        params={"days": days + 1, "min_importance": 0, "limit": 100},
        headers={"User-Agent": USER_AGENT}, timeout=timeout,
    )
    events_response.raise_for_status()
    events_by_date = {}
    for event in events_response.json().get("events", []):
        events_by_date.setdefault(event.get("date"), []).append(event)
    future = {}
    planet_series = planet_response.json().get("data", {}).get("series", [])
    for moon_row, planet_row in zip(
        moon_response.json().get("data", {}).get("series", []), planet_series
    ):
        date = moon_row["instant"][:10]
        phase = moon_row.get("phase", {})
        future[date] = {
            "moon": {
                "sign": moon_row.get("tropical_sign", {}).get("name", "the night sky"),
                "phase_name": phase.get("name", "Changing Moon"),
                "illumination": phase.get("illuminated_fraction"),
                "waxing": phase.get("waxing"),
            },
            "planets": {
                body["name"]: {
                    "sign": body.get("tropical_sign", {}).get("name"),
                    "retrograde": body.get("motion", {}).get("is_retrograde", False),
                }
                for body in planet_row.get("bodies", [])
            },
            "events": events_by_date.get(date, []),
        }
    return future


def fetch_cosmic_context(timeout: int = 20, future_days: int = 14) -> dict:
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
        result = {
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
        try:
            start_date = datetime.now(timezone.utc).date() + timedelta(days=1)
            result["future"] = _future_sky(start_date, future_days, timeout)
        except (requests.RequestException, ValueError, TypeError, KeyError):
            result["future"] = {}
        return result
    except (requests.RequestException, ValueError, TypeError):
        return fallback_context()

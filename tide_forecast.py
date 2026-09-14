"""Fetch and attach free BOM tide predictions for the two surf locations.

The Bureau publishes high/low water events rather than a continuous series.  The
curve used in the website is a cosine interpolation between consecutive events;
published event times and heights remain available separately in the output CSVs.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import requests

BOM_PRINT_URL = "https://www.bom.gov.au/australia/tides/print.php"
BOM_TIDE_PAGE = "https://www.bom.gov.au/australia/tides/"


@dataclass(frozen=True)
class TideStation:
    code: str
    name: str


TIDE_STATIONS = {
    "Bondi Beach": TideStation("NSW_TP007", "Sydney (Fort Denison)"),
    "Byron Bay": TideStation("NSW_TP016", "Brunswick Heads"),
}

_EVENT_RE = re.compile(
    r'<th[^>]*class="instance\s+(high|low)-tide"[^>]*>.*?</th>\s*'
    r'<td[^>]*data-time-utc="([^"]+)"[^>]*>.*?</td>\s*</tr>\s*<tr>\s*'
    r'<td[^>]*class="height\s+(?:high|low)-tide"[^>]*>\s*([0-9.]+)\s*m',
    re.IGNORECASE | re.DOTALL,
)


def _fetch_station_events(station, start_date, days=16):
    response = requests.get(
        BOM_PRINT_URL,
        params={"aac": station.code, "date": str(start_date), "days": days,
                "region": "NSW", "type": "tide", "tz": "Australia/Sydney",
                "tz_js": "AEST"},
        headers={
            "User-Agent": ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                           "Chrome/124.0 Safari/537.36 surf-horoscopes/1.0"),
            "Accept": "text/html,application/xhtml+xml",
            "Referer": BOM_TIDE_PAGE,
        },
        timeout=30,
    )
    response.raise_for_status()
    events = [
        {"event": kind.lower(), "time_utc": pd.Timestamp(time),
         "height_m": float(height), "station": station.name}
        for kind, time, height in _EVENT_RE.findall(response.text)
    ]
    if len(events) < 4:
        raise RuntimeError(f"Could not parse tide predictions for {station.name}")
    return pd.DataFrame(events).drop_duplicates("time_utc").sort_values("time_utc")


def _demo_station_events(station, start, end, phase_hours=0.0):
    # Clearly marked synthetic events are used only by build_site.py --demo.
    first = start.floor("h") - pd.Timedelta(hours=8) + pd.Timedelta(hours=phase_hours)
    times = pd.date_range(first, end.ceil("h") + pd.Timedelta(hours=8), freq="6h12min", tz="UTC")
    return pd.DataFrame({
        "event": ["high" if i % 2 == 0 else "low" for i in range(len(times))],
        "time_utc": times,
        "height_m": [1.55 if i % 2 == 0 else 0.35 for i in range(len(times))],
        "station": station.name + " (demo)",
    })


def fetch_tide_events(forecast, demo=False):
    """Return BOM high/low events bracketing the forecast for each location."""
    times = pd.to_datetime(forecast["valid_time_utc"], utc=True)
    start, end = times.min(), times.max()
    # Begin a day early so the first forecast point is bracketed for interpolation.
    start_date = (start.tz_convert("Australia/Sydney") - pd.Timedelta(days=1)).date()
    days = max(16, int(math.ceil((end - start).total_seconds() / 86400)) + 3)
    results = {}
    for location in forecast["location"].unique():
        station = TIDE_STATIONS.get(str(location))
        if station is None:
            raise KeyError(f"No tide station configured for {location!r}")
        results[location] = (
            _demo_station_events(station, start, end, 0 if location == "Bondi Beach" else 0.5)
            if demo else _fetch_station_events(station, start_date, days)
        )
    return results


def _interpolate_one(times, events):
    event_times = pd.to_datetime(events["time_utc"], utc=True)
    # Timestamp.value is always nanoseconds; pandas 3 may otherwise expose a
    # lower-resolution integer and make comparisons silently fail.
    event_ns = event_times.map(lambda value: value.value).to_numpy(dtype="int64")
    heights = events["height_m"].astype(float).to_numpy()
    kinds = events["event"].astype(str).to_numpy()
    rows = []
    for value in pd.to_datetime(times, utc=True):
        stamp = value.value
        after = int(event_ns.searchsorted(stamp, side="right"))
        before = after - 1
        if before < 0 or after >= len(events):
            rows.append((float("nan"), "unavailable", None, None, None))
            continue
        span = event_ns[after] - event_ns[before]
        fraction = (stamp - event_ns[before]) / span
        eased = (1 - math.cos(math.pi * fraction)) / 2
        height = heights[before] + (heights[after] - heights[before]) * eased
        nearest = before if stamp - event_ns[before] <= event_ns[after] - stamp else after
        close = abs(stamp - event_ns[nearest]) <= pd.Timedelta(minutes=45).value
        state = kinds[nearest] if close else ("rising" if heights[after] > heights[before] else "falling")
        rows.append((height, state, kinds[after], event_times.iloc[after], heights[after]))
    return rows


def attach_tides(forecast, tide_events):
    """Add interpolated tide height/state and the next event to forecast rows."""
    data = forecast.copy()
    data["valid_time_utc"] = pd.to_datetime(data["valid_time_utc"], utc=True)
    parts = []
    for location, group in data.groupby("location", sort=False):
        group = group.copy()
        values = _interpolate_one(group["valid_time_utc"], tide_events[location])
        columns = ["tide_height_m", "tide_state", "next_tide_type", "next_tide_time_utc",
                   "next_tide_height_m"]
        for column, value in zip(columns, zip(*values)):
            group[column] = value
        group["tide_station"] = tide_events[location]["station"].iloc[0]
        group["tide_source"] = "Bureau of Meteorology high/low predictions"
        parts.append(group)
    return pd.concat(parts, ignore_index=True).sort_values(["valid_time_utc", "location"])


def write_tide_events(tide_events, output_dir):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    for location, events in tide_events.items():
        slug = location.lower().replace(" beach", "").replace(" ", "_")
        events.to_csv(output_dir / f"tide_events_{slug}.csv", index=False)

"""Build the static GitHub Pages site from current GFS Wave conditions."""

from __future__ import annotations

import argparse
import json
import shutil
from dataclasses import asdict
from pathlib import Path

import pandas as pd

from surf_horoscope import generate_all_horoscopes, interpret_conditions

DESIGN_DIR = Path(__file__).parent / "surf-horoscopes-sample"


def render_site(forecast, destination="site"):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    reports = generate_all_horoscopes(forecast, destination / "data")
    profiles = {row["location"]: interpret_conditions(row) for _, row in forecast.iterrows()}
    payload = {
        location: {"conditions": profiles[location], "report": asdict(report)}
        for location, report in reports.items()
    }

    for name in ("styles.css", "app.js", "favicon.svg", "og.png"):
        shutil.copy2(DESIGN_DIR / name, destination / name)

    template = (DESIGN_DIR / "index.html").read_text(encoding="utf-8")
    data_script = (
        "<script>window.SURF_DATA="
        + json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
        + ";</script>\n  <script src=\"app.js\"></script>"
    )
    page = template.replace('<script src="app.js"></script>', data_script)
    generated = pd.Timestamp.now(tz="UTC").strftime("%d %b %Y")
    page = page.replace("21 AUG 2026", generated.upper())
    (destination / "index.html").write_text(page, encoding="utf-8")
    (destination / "data" / "forecast.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return destination / "index.html"


def demo_forecast():
    now = pd.Timestamp.now(tz="UTC")
    return pd.DataFrame([
        {"location": "Bondi Beach", "valid_time_utc": now, "wave_height_m": 1.2,
         "primary_period_s": 11, "primary_direction_deg": 135,
         "wind_speed_m_s": 4, "wind_direction_deg": 300},
        {"location": "Byron Bay", "valid_time_utc": now, "wave_height_m": 0.9,
         "primary_period_s": 9, "primary_direction_deg": 110,
         "wind_speed_m_s": 3, "wind_direction_deg": 180},
    ])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--demo", action="store_true", help="Build without downloading live data")
    parser.add_argument("--destination", default="site")
    args = parser.parse_args()
    if args.demo:
        data = demo_forecast()
    else:
        from gfs_wave_current import current_conditions
        data = current_conditions()
    print(f"Built {render_site(data, args.destination)}")

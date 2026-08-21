"""Build the static GitHub Pages site from current GFS Wave conditions."""

from __future__ import annotations

import argparse
import json
import math
import shutil
from dataclasses import asdict
from pathlib import Path

import pandas as pd

from forecast_charts import make_forecast_charts
from surf_horoscope import current_rows, generate_all_horoscopes, interpret_conditions

DESIGN_DIR = Path(__file__).parent / "surf-horoscopes-sample"


def render_site(forecast, destination="site"):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    reports = generate_all_horoscopes(forecast, destination / "data")
    current = current_rows(forecast)
    profiles = {row["location"]: interpret_conditions(row) for _, row in current.iterrows()}
    payload = {
        location: {"conditions": profiles[location], "report": asdict(report)}
        for location, report in reports.items()
    }

    for name in ("styles.css", "app.js", "favicon.svg", "og.png"):
        shutil.copy2(DESIGN_DIR / name, destination / name)
    make_forecast_charts(forecast, destination)

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
    data_page = (DESIGN_DIR / "data.html").read_text(encoding="utf-8")
    (destination / "data.html").write_text(
        data_page.replace("21 AUG 2026", generated.upper()), encoding="utf-8"
    )
    (destination / "data" / "forecast.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    forecast.to_csv(destination / "data" / "five_day_forecast.csv", index=False)
    return destination / "index.html"


def demo_forecast():
    now = pd.Timestamp.now(tz="UTC")
    rows = []
    for hour in range(0, 121, 3):
        for location, base_height, base_period, wind_direction in (
            ("Bondi Beach", 1.2, 11, 300), ("Byron Bay", .9, 9, 180)
        ):
            rows.append({"location": location, "cycle_utc": now,
                         "forecast_hour": hour, "valid_time_utc": now + pd.Timedelta(hours=hour),
                         "wave_height_m": base_height + .25 * math.sin(hour / 14),
                         "primary_period_s": base_period + .8 * math.cos(hour / 18),
                         "primary_direction_deg": 120 + hour / 5,
                         "wind_speed_m_s": 4 + 1.8 * math.sin(hour / 9),
                         "wind_direction_deg": wind_direction})
    return pd.DataFrame(rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--demo", action="store_true", help="Build without downloading live data")
    parser.add_argument("--destination", default="site")
    args = parser.parse_args()
    if args.demo:
        data = demo_forecast()
    else:
        from gfs_wave_current import forecast_conditions
        data = forecast_conditions()
    print(f"Built {render_site(data, args.destination)}")

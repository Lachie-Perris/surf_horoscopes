"""Build the static GitHub Pages site from current GFS Wave conditions."""

from __future__ import annotations

import argparse
import html
import json
from dataclasses import asdict
from pathlib import Path

import pandas as pd

from surf_horoscope import generate_all_horoscopes, interpret_conditions


def render_site(forecast, destination="site"):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    reports = generate_all_horoscopes(forecast, destination / "data")
    profiles = {row["location"]: interpret_conditions(row) for _, row in forecast.iterrows()}
    payload = {
        location: {"conditions": profiles[location], "report": asdict(report)}
        for location, report in reports.items()
    }
    (destination / "data" / "forecast.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    cards = []
    for location, report in reports.items():
        p = profiles[location]
        readings = "".join(
            f'<article class="reading" data-sign="{html.escape(h.sign)}">'
            f'<p class="sign">{html.escape(h.sign)}</p><h3>{html.escape(h.headline)}</h3>'
            f'<p>{html.escape(h.reading)}</p><p class="intention">{html.escape(h.surf_intention)}</p></article>'
            for h in report.horoscopes
        )
        cards.append(f"""
        <section class="spot" id="{location.lower().replace(' beach', '').replace(' ', '-')}">
          <div class="spot-head"><div><p class="eyebrow">CURRENT READING</p><h2>{html.escape(location)}</h2>
          <p>{html.escape(report.conditions_summary)}</p></div>
          <div class="metrics"><span><b>{p['wave_height_m']:.1f}</b> m Hs</span>
          <span><b>{p['primary_period_s']:.0f}</b> sec</span><span><b>{p['wind_direction']}</b> wind</span></div></div>
          <div class="readings">{readings}</div>
        </section>""")

    generated = pd.Timestamp.now(tz="UTC").strftime("%d %b %Y, %H:%M UTC")
    page = TEMPLATE.replace("{{CONTENT}}", "".join(cards)).replace("{{UPDATED}}", generated)
    (destination / "index.html").write_text(page, encoding="utf-8")
    return destination / "index.html"


TEMPLATE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="Daily surf horoscopes for Bondi Beach and Byron Bay, shaped by GFS Wave conditions.">
<title>Surf Horoscopes</title><style>
:root{--ink:#092532;--sea:#087e8b;--foam:#eef8f6;--sun:#f3b562;--paper:#fbfaf5}
*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font-family:Inter,ui-sans-serif,system-ui,sans-serif;line-height:1.55}
header{padding:5rem max(5vw,1.25rem) 4rem;background:linear-gradient(135deg,#073b4c,#087e8b);color:white}
header p{max-width:42rem}h1{font-family:Georgia,serif;font-size:clamp(3rem,8vw,7rem);line-height:.9;margin:.4rem 0 1.5rem;font-weight:500}
nav{display:flex;gap:1rem;flex-wrap:wrap;margin-top:2rem}nav a{color:white;text-decoration:none;border:1px solid #ffffff66;border-radius:99px;padding:.55rem 1rem}
main{max-width:1200px;margin:auto;padding:2rem max(3vw,1rem) 5rem}.spot{padding:3.5rem 0;border-bottom:1px solid #b7cfca}
.spot-head{display:grid;grid-template-columns:1.4fr 1fr;gap:3rem;align-items:end}.eyebrow,.sign{letter-spacing:.14em;font-size:.72rem;font-weight:800;color:var(--sea)}
h2{font-family:Georgia,serif;font-size:clamp(2.4rem,5vw,4.7rem);margin:0}.metrics{display:flex;gap:.7rem;flex-wrap:wrap}.metrics span{background:var(--foam);padding:.8rem 1rem;border-radius:.4rem}.metrics b{font-size:1.4rem}
.readings{display:grid;grid-template-columns:repeat(3,1fr);gap:1rem;margin-top:2.5rem}.reading{background:white;border-top:4px solid var(--sun);padding:1.4rem;box-shadow:0 7px 24px #082f3a0d}.reading h3{font-family:Georgia,serif;font-size:1.45rem;margin:.2rem 0 1rem}.intention{font-weight:700;color:var(--sea)}
footer{text-align:center;padding:2rem;background:var(--ink);color:#cfe4df;font-size:.85rem}
@media(max-width:800px){.spot-head{grid-template-columns:1fr}.readings{grid-template-columns:1fr}header{padding-top:3rem}}
</style></head><body><header><p class="eyebrow" style="color:#9de2d7">GFS WAVE × THE ZODIAC</p><h1>Surf<br>Horoscopes</h1>
<p>A playful daily reading of the ocean at Bondi and Byron—written from wave height, period and the wind.</p>
<nav><a href="#bondi">Bondi Beach</a><a href="#byron-bay">Byron Bay</a></nav></header>
<main>{{CONTENT}}</main><footer>Updated {{UPDATED}} · Offshore model guidance, not a safety forecast.</footer></body></html>"""


def demo_forecast():
    now = pd.Timestamp.now(tz="UTC")
    return pd.DataFrame([
        {"location":"Bondi Beach","valid_time_utc":now,"wave_height_m":1.2,"primary_period_s":11,
         "primary_direction_deg":135,"wind_speed_m_s":4,"wind_direction_deg":300},
        {"location":"Byron Bay","valid_time_utc":now,"wave_height_m":0.9,"primary_period_s":9,
         "primary_direction_deg":110,"wind_speed_m_s":3,"wind_direction_deg":180},
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

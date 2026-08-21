"""Create separate Surfline-style forecast charts for the website."""

from pathlib import Path
from zoneinfo import ZoneInfo

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

LOCAL_TZ = ZoneInfo("Australia/Sydney")
BG, PANEL, GRID = "#0c0b13", "#15131d", "#393444"
WAVE, PERIOD, WIND, TEXT = "#6eced0", "#f0cc62", "#9ccf8e", "#e9e4dc"


def _shade_days(ax, times):
    days = pd.date_range(times.min().normalize(), times.max().normalize() + pd.Timedelta(days=1), freq="D")
    for i in range(len(days) - 1):
        if i % 2:
            ax.axvspan(days[i], days[i + 1], color="white", alpha=0.035, lw=0)


def _arrows(ax, times, directions, y, color, every=2, size=12):
    for x, direction in zip(times.iloc[::every], directions.iloc[::every]):
        if pd.notna(direction):
            ax.text(x, y, "↓", color=color, fontsize=size, ha="center", va="center",
                    rotation=-float(direction), rotation_mode="anchor", fontweight="bold")


def make_forecast_charts(forecast, destination):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    paths = {}
    for location, group in forecast.groupby("location"):
        g = group.sort_values("valid_time_utc").copy()
        g["local_time"] = pd.to_datetime(g.valid_time_utc, utc=True).dt.tz_convert(LOCAL_TZ)
        # Web-friendly canvas: approximately 1200 x 720 px at the saved DPI.
        fig = plt.figure(figsize=(10, 6), facecolor=BG)
        grid = fig.add_gridspec(3, 1, height_ratios=[4.4, .8, 2.3], hspace=.08)
        wave_ax = fig.add_subplot(grid[0]); direction_ax = fig.add_subplot(grid[1], sharex=wave_ax)
        wind_ax = fig.add_subplot(grid[2], sharex=wave_ax)
        for ax in (wave_ax, direction_ax, wind_ax):
            ax.set_facecolor(PANEL); _shade_days(ax, g.local_time)
        wave_ax.fill_between(g.local_time, 0, g.wave_height_m, color=WAVE, alpha=.24)
        wave_ax.plot(g.local_time, g.wave_height_m, color=WAVE, lw=2.6)
        period_ax = wave_ax.twinx()
        period_ax.plot(g.local_time, g.primary_period_s, color=PERIOD, lw=1.9)
        wave_ax.set_ylim(bottom=0); period_ax.set_ylim(bottom=0)
        wave_ax.set_ylabel("Wave height (m)", color=WAVE, fontweight="bold")
        period_ax.set_ylabel("Primary period (s)", color=PERIOD, fontweight="bold")
        _arrows(direction_ax, g.local_time, g.primary_direction_deg, .5, WAVE, size=14)
        direction_ax.set_ylim(0, 1); direction_ax.set_yticks([])
        direction_ax.set_ylabel("Swell dir.", color=TEXT, rotation=0, ha="right", va="center")
        wind_ax.fill_between(g.local_time, 0, g.wind_speed_m_s, color=WIND, alpha=.2)
        wind_ax.plot(g.local_time, g.wind_speed_m_s, color=WIND, lw=2.1)
        top = max(float(g.wind_speed_m_s.max()) * 1.3, 2)
        wind_ax.set_ylim(0, top); wind_ax.set_ylabel("Wind (m/s)", color=WIND, fontweight="bold")
        _arrows(wind_ax, g.local_time, g.wind_direction_deg, top * .84, WIND)
        for ax in (wave_ax, wind_ax): ax.grid(axis="y", color=GRID, lw=.8)
        for ax in (wave_ax, direction_ax, wind_ax, period_ax):
            ax.tick_params(colors=TEXT)
            for spine in ax.spines.values(): spine.set_color(GRID)
        plt.setp(wave_ax.get_xticklabels(), visible=False); plt.setp(direction_ax.get_xticklabels(), visible=False)
        wind_ax.xaxis.set_major_locator(mdates.DayLocator(tz=LOCAL_TZ))
        wind_ax.xaxis.set_major_formatter(mdates.DateFormatter("%a\n%d %b", tz=LOCAL_TZ))
        wind_ax.set_xlabel("Local time — Australia/Sydney", color=TEXT)
        cycle = pd.to_datetime(g.cycle_utc.iloc[0], utc=True)
        fig.suptitle(f"{location} — five-day offshore forecast", x=.07, ha="left",
                     color=TEXT, fontsize=19, fontweight="bold")
        fig.text(.07, .925, f"GFS Wave cycle {cycle:%Y-%m-%d %H} UTC · arrows point where waves and wind travel",
                 color="#aaa5b1", fontsize=9)
        fig.subplots_adjust(left=.07, right=.93, top=.88, bottom=.10)
        slug = location.lower().replace(" beach", "").replace(" ", "_")
        path = destination / f"forecast_{slug}.png"
        fig.savefig(path, dpi=120, bbox_inches="tight", facecolor=BG)
        plt.close(fig); paths[location] = path
    return paths

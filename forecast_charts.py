"""Create Quiet Field surf and celestial forecast charts for the website."""

from pathlib import Path
import math
from zoneinfo import ZoneInfo

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

LOCAL_TZ = ZoneInfo("Australia/Sydney")
BG, PANEL, GRID = "#dcefee", "#eef5e9", "#9dbbb7"
WAVE, PERIOD, WIND, TIDE, MOON, TEXT, MUTED = "#167f91", "#b87422", "#437d62", "#3979a8", "#7953a6", "#10232a", "#526d70"


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


def _celestial_rows(cosmic):
    rows = []
    current_date = cosmic.get("date")
    if current_date:
        rows.append((current_date, cosmic.get("moon", {}), cosmic.get("retrogrades", [])))
    for date, sky in cosmic.get("future", {}).items():
        retrogrades = [name.title() for name, value in sky.get("planets", {}).items()
                       if value.get("retrograde")]
        rows.append((date, sky.get("moon", {}), retrogrades))
    return sorted(rows, key=lambda row: row[0])


def _plot_celestial(ax, cosmic, start, end):
    rows = _celestial_rows(cosmic)
    points = [(pd.Timestamp(date, tz=LOCAL_TZ), moon, retrogrades)
              for date, moon, retrogrades in rows
              if start.date() <= pd.Timestamp(date).date() <= end.date()]
    ax.set_ylim(0, 1.08); ax.set_ylabel("Moon light", color=MOON, fontweight="bold")
    if not points:
        ax.text(.5, .5, "Celestial cycle unavailable", transform=ax.transAxes,
                ha="center", va="center", color=MUTED)
        return
    times = [item[0] for item in points]
    illumination = [float(item[1].get("illumination") or 0) for item in points]
    illumination = [value / 100 if value > 1 else value for value in illumination]
    ax.fill_between(times, 0, illumination, color=MOON, alpha=.15)
    ax.plot(times, illumination, color=MOON, lw=2.2, marker="o", ms=4)
    all_retrogrades = sorted({planet for _, _, retrogrades in points for planet in retrogrades})
    for time, moon, retrogrades in points:
        sign = moon.get("sign", "")
        phase = moon.get("phase_name", "")
        label = f"{phase}\nMoon in {sign}" if sign else phase
        light = float(moon.get("illumination") or 0)
        light = light / 100 if light > 1 else light
        ax.annotate(label, (time, light), xytext=(0, 10),
                    textcoords="offset points", ha="center", va="bottom", fontsize=7,
                    color=TEXT)
        if retrogrades:
            ax.scatter([time], [.035], marker="x", s=15, color=MUTED, zorder=4)
    if all_retrogrades:
        ax.text(.99, .055, "Retrograde · " + " · ".join(all_retrogrades),
                transform=ax.transAxes, ha="right", va="bottom", fontsize=7, color=MUTED)


def _plot_tide(ax, group, events=None):
    plot_times, plot_heights = group.local_time, group.tide_height_m
    if events is not None:
        smooth_times, smooth_heights = [], []
        ordered = events.sort_values("time_utc").reset_index(drop=True)
        for i in range(len(ordered) - 1):
            left, right = ordered.iloc[i], ordered.iloc[i + 1]
            segment = pd.date_range(left.time_utc, right.time_utc, periods=25)
            for step, time in enumerate(segment):
                fraction = step / (len(segment) - 1)
                eased = (1 - math.cos(math.pi * fraction)) / 2
                smooth_times.append(time.tz_convert(LOCAL_TZ))
                smooth_heights.append(left.height_m + (right.height_m - left.height_m) * eased)
        plot_times, plot_heights = pd.Series(smooth_times), pd.Series(smooth_heights)
        visible = plot_times.between(group.local_time.min(), group.local_time.max())
        plot_times, plot_heights = plot_times[visible], plot_heights[visible]
    ax.fill_between(plot_times, 0, plot_heights, color=TIDE, alpha=.17)
    ax.plot(plot_times, plot_heights, color=TIDE, lw=2.1)
    ax.set_ylim(bottom=0)
    ax.set_ylabel("Tide (m)", color=TIDE, fontweight="bold")
    if events is None:
        return
    points = events.copy()
    points["local_time"] = pd.to_datetime(points.time_utc, utc=True).dt.tz_convert(LOCAL_TZ)
    points = points[points.local_time.between(group.local_time.min(), group.local_time.max())]
    for kind, marker in (("high", "o"), ("low", "v")):
        subset = points[points.event == kind]
        ax.scatter(subset.local_time, subset.height_m, s=18, marker=marker,
                   color=TIDE, edgecolor=PANEL, linewidth=.5, zorder=4)


def make_forecast_charts(forecast, destination, cosmic=None, tide_events=None):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    paths = {}
    for location, group in forecast.groupby("location"):
        # Keep the detailed public chart readable; the full fortnight still feeds
        # the "Your future" selector and downloadable forecast data.
        g = group[group["forecast_hour"] <= 120].sort_values("valid_time_utc").copy()
        g["local_time"] = pd.to_datetime(g.valid_time_utc, utc=True).dt.tz_convert(LOCAL_TZ)
        # Web-friendly canvas with separate tide and celestial cycle panels.
        fig = plt.figure(figsize=(11, 9.6), facecolor=BG)
        grid = fig.add_gridspec(5, 1, height_ratios=[4.1, .75, 2.0, 1.65, 2.15], hspace=.12)
        wave_ax = fig.add_subplot(grid[0]); direction_ax = fig.add_subplot(grid[1], sharex=wave_ax)
        wind_ax = fig.add_subplot(grid[2], sharex=wave_ax)
        tide_ax = fig.add_subplot(grid[3], sharex=wave_ax)
        celestial_ax = fig.add_subplot(grid[4], sharex=wave_ax)
        for ax in (wave_ax, direction_ax, wind_ax, tide_ax, celestial_ax):
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
        _plot_tide(tide_ax, g, (tide_events or {}).get(location))
        _plot_celestial(celestial_ax, cosmic or {}, g.local_time.min(), g.local_time.max())
        for ax in (wave_ax, wind_ax, tide_ax, celestial_ax): ax.grid(axis="y", color=GRID, lw=.8, alpha=.55)
        for ax in (wave_ax, direction_ax, wind_ax, tide_ax, celestial_ax, period_ax):
            ax.tick_params(colors=TEXT)
            for spine in ax.spines.values(): spine.set_color(GRID)
        plt.setp(wave_ax.get_xticklabels(), visible=False); plt.setp(direction_ax.get_xticklabels(), visible=False); plt.setp(wind_ax.get_xticklabels(), visible=False); plt.setp(tide_ax.get_xticklabels(), visible=False)
        celestial_ax.xaxis.set_major_locator(mdates.DayLocator(tz=LOCAL_TZ))
        celestial_ax.xaxis.set_major_formatter(mdates.DateFormatter("%a\n%d %b", tz=LOCAL_TZ))
        celestial_ax.set_xlabel("Local time — Australia/Sydney", color=TEXT)
        cycle = pd.to_datetime(g.cycle_utc.iloc[0], utc=True)
        fig.suptitle(f"{location} — five-day offshore forecast", x=.07, ha="left",
                     color=TEXT, fontsize=19, fontweight="bold")
        fig.text(.07, .925, f"GFS Wave cycle {cycle:%Y-%m-%d %H} UTC · arrows point where waves and wind travel",
                 color=MUTED, fontsize=9)
        station = g.tide_station.iloc[0] if "tide_station" in g else "nearest reference port"
        fig.text(.07, .045, f"Tide: BOM high/low predictions for {station}; curve interpolated · Celestial: Moon and retrogrades",
                 color=MUTED, fontsize=8)
        fig.subplots_adjust(left=.08, right=.92, top=.89, bottom=.12)
        slug = location.lower().replace(" beach", "").replace(" ", "_")
        path = destination / f"forecast_{slug}.png"
        fig.savefig(path, dpi=120, bbox_inches="tight", facecolor=BG)
        plt.close(fig); paths[location] = path
    return paths

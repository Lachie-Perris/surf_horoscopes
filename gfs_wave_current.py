"""Download a five-day GFS Wave forecast for Bondi and Byron Bay."""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import requests
import xarray as xr

BEACHES = {
    "Bondi Beach": {"lat": -33.8915, "lon": 151.2767},
    "Byron Bay": {"lat": -28.6434, "lon": 153.6122},
}
BBOX = {"leftlon": 150.0, "rightlon": 155.0, "bottomlat": -35.0, "toplat": -27.0}
BASE_URL = "https://nomads.ncep.noaa.gov/cgi-bin/filter_gfswave.pl"
FORECAST_HOURS = tuple(range(0, 121, 3))
ALIASES = {
    "wave_height_m": ("swh", "htsgw"), "primary_period_s": ("perpw",),
    "primary_direction_deg": ("dirpw",), "wind_speed_m_s": ("ws", "wind"),
    "wind_direction_deg": ("wdir",),
}


def cycle_candidates(hours_back=48):
    now = datetime.now(timezone.utc)
    first = now.replace(hour=(now.hour // 6) * 6, minute=0, second=0, microsecond=0)
    return [first - timedelta(hours=6 * i) for i in range(hours_back // 6 + 1)]


def request_params(cycle, forecast_hour):
    return {
        "file": f"gfswave.t{cycle:%H}z.global.0p25.f{forecast_hour:03d}.grib2",
        "lev_surface": "on", "var_HTSGW": "on", "var_PERPW": "on",
        "var_DIRPW": "on", "var_WIND": "on", "var_WDIR": "on", "subregion": "",
        **BBOX, "dir": f"/gfs.{cycle:%Y%m%d}/{cycle:%H}/wave/gridded",
    }


def _download(cycle, forecast_hour, data_dir, retries=3):
    target_dir = Path(data_dir) / cycle.strftime("%Y%m%d_%H")
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"f{forecast_hour:03d}.grib2"
    if target.exists() and target.stat().st_size > 1000:
        return target
    last_error = None
    for attempt in range(retries):
        try:
            response = requests.get(
                BASE_URL, params=request_params(cycle, forecast_hour), timeout=90
            )
            response.raise_for_status()
            if len(response.content) < 1000 or response.content[:4] != b"GRIB":
                raise RuntimeError("NOMADS did not return a GRIB file")
            target.write_bytes(response.content)
            return target
        except Exception as exc:
            last_error = exc
            if attempt + 1 < retries:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"Could not download forecast hour {forecast_hour}: {last_error}")


def download_forecast(data_dir="data", forecast_hours=FORECAST_HOURS):
    for cycle in cycle_candidates():
        try:
            first = _download(cycle, 0, data_dir, retries=1)
            files = [(0, first)]
            files.extend(
                (hour, _download(cycle, hour, data_dir))
                for hour in forecast_hours if hour != 0
            )
            return cycle, files
        except Exception:
            continue
    raise RuntimeError("No complete recent GFS Wave cycle was available from NOAA NOMADS")


def haversine_km(lat1, lon1, lat2, lon2):
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dp, dl = np.radians(lat2 - lat1), np.radians(lon2 - lon1)
    a = np.sin(dp / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    return 6371.0 * 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))


def _field_name(ds, names, description=None):
    for name in names:
        if name in ds.data_vars:
            return name
    if description:
        for name, value in ds.data_vars.items():
            if description in str(value.attrs).lower():
                return name
    return None


def _selected_points(path):
    with xr.open_dataset(path, engine="cfgrib", backend_kwargs={"indexpath": ""}) as ds:
        height_name = _field_name(ds, ("swh", "htsgw"), "significant height")
        if not height_name:
            raise KeyError(f"Wave-height field missing from {list(ds.data_vars)}")
        height = ds[height_name].squeeze()
        lat2d, lon2d = xr.broadcast(height.latitude, height.longitude)
        valid = np.isfinite(height.values)
        wet_lats, wet_lons = lat2d.values[valid], lon2d.values[valid]
        points = {}
        for location, beach in BEACHES.items():
            distance = haversine_km(beach["lat"], beach["lon"], wet_lats, wet_lons)
            i = int(np.argmin(distance))
            points[location] = {
                "lat": float(wet_lats[i]), "lon": float(wet_lons[i]),
                "distance_km": float(distance[i]),
            }
        return points


def forecast_conditions(data_dir="data", forecast_hours=FORECAST_HOURS):
    cycle, files = download_forecast(data_dir, forecast_hours)
    points = _selected_points(files[0][1])
    rows = []
    for hour, path in files:
        with xr.open_dataset(path, engine="cfgrib", backend_kwargs={"indexpath": ""}) as ds:
            for location, point in points.items():
                row = {
                    "location": location, "cycle_utc": pd.Timestamp(cycle),
                    "forecast_hour": hour,
                    "valid_time_utc": pd.Timestamp(cycle) + pd.Timedelta(hours=hour),
                    "grid_latitude": point["lat"], "grid_longitude": point["lon"],
                    "distance_from_beach_km": point["distance_km"],
                }
                for output, names in ALIASES.items():
                    name = _field_name(ds, names)
                    row[output] = float(
                        ds[name].sel(
                            latitude=point["lat"], longitude=point["lon"], method="nearest"
                        ).squeeze()
                    )
                rows.append(row)
    return pd.DataFrame(rows)


def current_conditions(data_dir="data"):
    return forecast_conditions(data_dir, forecast_hours=(0,))

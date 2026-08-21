"""Download the newest current GFS Wave conditions for Bondi and Byron Bay."""

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


def cycle_candidates(hours_back=48):
    now = datetime.now(timezone.utc)
    first = now.replace(hour=(now.hour // 6) * 6, minute=0, second=0, microsecond=0)
    return [first - timedelta(hours=6 * i) for i in range(hours_back // 6 + 1)]


def request_params(cycle):
    return {
        "file": f"gfswave.t{cycle:%H}z.global.0p25.f000.grib2",
        "lev_surface": "on", "var_HTSGW": "on", "var_PERPW": "on",
        "var_DIRPW": "on", "var_WIND": "on", "var_WDIR": "on", "subregion": "",
        **BBOX, "dir": f"/gfs.{cycle:%Y%m%d}/{cycle:%H}/wave/gridded",
    }


def download_current(data_dir="data", retries=3):
    data_dir = Path(data_dir)
    for cycle in cycle_candidates():
        target_dir = data_dir / cycle.strftime("%Y%m%d_%H")
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / "f000.grib2"
        if target.exists() and target.stat().st_size > 1000:
            return cycle, target
        for attempt in range(retries):
            try:
                response = requests.get(BASE_URL, params=request_params(cycle), timeout=90)
                response.raise_for_status()
                if len(response.content) < 1000 or response.content[:4] != b"GRIB":
                    raise RuntimeError("NOMADS did not return a GRIB file")
                target.write_bytes(response.content)
                return cycle, target
            except Exception:
                if attempt + 1 < retries:
                    time.sleep(2 ** attempt)
    raise RuntimeError("No recent GFS Wave cycle was available from NOAA NOMADS")


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


def current_conditions(data_dir="data"):
    cycle, path = download_current(data_dir)
    with xr.open_dataset(path, engine="cfgrib", backend_kwargs={"indexpath": ""}) as ds:
        height_name = _field_name(ds, ("swh", "htsgw"), "significant height")
        if not height_name:
            raise KeyError(f"Wave-height field missing from {list(ds.data_vars)}")
        height = ds[height_name].squeeze()
        lat2d, lon2d = xr.broadcast(height.latitude, height.longitude)
        valid = np.isfinite(height.values)
        wet_lats, wet_lons = lat2d.values[valid], lon2d.values[valid]
        aliases = {
            "wave_height_m": ("swh", "htsgw"), "primary_period_s": ("perpw",),
            "primary_direction_deg": ("dirpw",), "wind_speed_m_s": ("ws", "wind"),
            "wind_direction_deg": ("wdir",),
        }
        rows = []
        for location, beach in BEACHES.items():
            distances = haversine_km(beach["lat"], beach["lon"], wet_lats, wet_lons)
            i = int(np.argmin(distances))
            lat, lon = float(wet_lats[i]), float(wet_lons[i])
            row = {
                "location": location, "cycle_utc": pd.Timestamp(cycle),
                "forecast_hour": 0, "valid_time_utc": pd.Timestamp(cycle),
                "grid_latitude": lat, "grid_longitude": lon,
                "distance_from_beach_km": float(distances[i]),
            }
            for output, names in aliases.items():
                name = _field_name(ds, names)
                row[output] = float(ds[name].sel(latitude=lat, longitude=lon, method="nearest").squeeze())
            rows.append(row)
    return pd.DataFrame(rows)


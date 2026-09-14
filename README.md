# Bondi and Byron Bay GFS Wave forecast

Open `gfs_wave_bondi_byron.ipynb` in Jupyter and run all cells. The notebook:

- finds the newest available NOAA/NCEP GFS Wave cycle;
- downloads only a small NSW coastal subset of the 0.25-degree global grid;
- evaluates the next 14 days for a sign-specific "Your future" recommendation;
- retrieves official high/low tide predictions from the Bureau of Meteorology for
  Sydney (Fort Denison) and Brunswick Heads, then interpolates a display curve;
- automatically selects the nearest valid ocean grid cell to Bondi Beach and Byron Bay;
- creates separate Surfline-style Bondi and Byron Bay panels showing significant
  wave height, primary period, swell direction, local wind speed, and wind direction; and
- saves the tidy forecast to `output/gfs_wave_bondi_byron.csv`.

All downloads and outputs stay below this folder (`data/` and `output/`). The first
cell can install the packages listed in `requirements.txt` into the active Jupyter
kernel. NOAA normally retains only recent model cycles, so rerun the notebook to
refresh the forecast.

## Current-condition surf horoscopes

`surf_horoscope.py` converts the current forecast row into ocean-feeling and
wind-quality labels, then combines them with the day's Sun sign, Moon sign and
phase, planetary aspects, retrogrades, and a sign-specific lead event from the free
[CosmyDay astrology API](https://cosmyday.com/api-docs). It requires no API key or
paid AI model. If the astrology service is temporarily unavailable, the build uses
a local neutral fallback instead of failing:

```python
from surf_horoscope import generate_all_horoscopes

reports = generate_all_horoscopes(forecast, OUTPUT_DIR)
```

This saves Markdown and JSON reports under `output/`. For the future view, each
morning is scored for clean or light wind, useful swell height, period and direction.
That surf score is combined with the sign's elemental relationship to the Moon and
the placement and motion of its ruling planet. The highest clean-wind result becomes
that sign's recommended day at each beach.

### East Coast writing style

`clean_surf_report_log.py` preserves the original report log and produces
`surf_report_log_cleaned.txt`, containing separated, deduplicated and heuristically
tagged report sentences. `surf_style_library.py` keeps those sentences searchable,
but the live writer retrieves short condition-matched language motifs rather than
copying full historical sentences. This prevents old tide, timing, location and
breaking-wave claims from leaking into a new offshore forecast. The selected motifs
respond to swell trend, period and wind quality, and are recomposed into varied
sentence structures before the horoscope layer is added.

## GitHub Pages website

The repository includes a static site generator and a GitHub Actions deployment. To
preview it locally without downloading forecast data, run:

```bash
python build_site.py --demo
```

Then open `site/index.html`. On GitHub, open **Settings → Pages**, choose **GitHub
Actions** as the source, and manually run **Update surf horoscopes** from the Actions
tab. The same workflow refreshes the live fourteen-day GFS Wave data four times daily.
The generated `data.html` page displays readable five-day Bondi and Byron charts for wave
height, primary period, swell direction, wind speed, wind direction, interpolated tide
height, and celestial cycles. Exact BOM high/low events are also saved as separate CSVs.

Tide heights are reference-port predictions, not observations at the beach. The continuous
website curve is interpolated between the published events and must not be used for
navigation. Attribution and the required BOM disclaimer link appear on the data page.

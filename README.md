# Bondi and Byron Bay GFS Wave forecast

Open `gfs_wave_bondi_byron.ipynb` in Jupyter and run all cells. The notebook:

- finds the newest available NOAA/NCEP GFS Wave cycle;
- downloads only a small NSW coastal subset of the 0.25-degree global grid;
- automatically selects the nearest valid ocean grid cell to Bondi Beach and Byron Bay;
- creates separate Surfline-style Bondi and Byron Bay panels showing significant
  wave height, primary period, swell direction, local wind speed, and wind direction; and
- saves the tidy forecast to `output/gfs_wave_bondi_byron.csv`.

All downloads and outputs stay below this folder (`data/` and `output/`). The first
cell can install the packages listed in `requirements.txt` into the active Jupyter
kernel. NOAA normally retains only recent model cycles, so rerun the notebook to
refresh the forecast.

## Current-condition surf horoscopes

`surf_horoscope.py` converts the current forecast row into deterministic ocean-feeling
and wind-quality labels, then assembles a distinct report for every star sign from
curated local templates. It is fully offline and requires no API key or AI model:

```python
from surf_horoscope import generate_all_horoscopes

reports = generate_all_horoscopes(forecast, OUTPUT_DIR)
```

This saves Markdown and JSON reports under `output/`. The same spot, date, and sign
produce the same text, while different dates select different curated variations.

## GitHub Pages website

The repository includes a static site generator and a GitHub Actions deployment. To
preview it locally without downloading forecast data, run:

```bash
python build_site.py --demo
```

Then open `site/index.html`. On GitHub, open **Settings → Pages**, choose **GitHub
Actions** as the source, and manually run **Update surf horoscopes** from the Actions
tab. The same workflow refreshes the live five-day GFS Wave data four times daily.
The generated `data.html` page displays separate Bondi and Byron charts for wave
height, primary period, swell direction, wind speed, and wind direction.

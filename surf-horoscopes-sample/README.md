# Surf Horoscopes — GitHub Pages redesign

This is a dependency-free static site for GitHub Pages.

## Publishing

These files are the editable website design source. `build_site.py` copies them into
the generated Pages artifact and injects the latest forecast and horoscope data.

## Update daily conditions

Do not edit conditions in JavaScript. GitHub Actions downloads the latest GFS Wave
conditions and rebuilds the site four times daily.

The interface remembers no personal information; selecting a sign only changes the current page state.

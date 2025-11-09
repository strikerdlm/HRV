# HRV Analysis — Space Weather Integration

This application extends the HRV analysis with a Space Weather tab that fetches real‑time NOAA SWPC feeds and correlates them with your HRV window metrics.

## Features
- NOAA SWPC JSON feeds (no API key) for planetary K‑index and F10.7 solar radio flux.
- Optional weather covariates for Bogotá, Colombia via Open‑Meteo Archive (no API key).
- Lag‑aware correlations (scan a user‑defined lag range).
- Pearson r and p‑values (SciPy if available), Benjamini–Hochberg FDR q‑values.
- Partial correlations controlling for temperature, humidity, pressure.
- OLS residual diagnostics (R², Durbin–Watson, normality test, residual plots).
- Local JSONL database for correlation summaries keyed by Cedula.

## Quick Start
```bash
pip install -r requirements.txt
streamlit run app/app.py
```

## Requirements
- Python 3.10+
- Packages: streamlit, requests, pandas, numpy, scipy (optional but recommended).

## Data Sources
- NOAA SWPC JSON feeds: `https://services.swpc.noaa.gov/json/` (e.g., `planetary_k_index_1m.json`, `solar_radio_flux.json`).
- Open‑Meteo Archive: `https://archive-api.open-meteo.com/v1/era5` (hourly temperature, humidity, pressure for Bogotá).

## Using the Space Weather Tab
1. Review live K‑index and solar flux charts.
2. Configure lag range, step, and merge tolerance.
3. (Optional) Enable weather covariates.
4. Enter your Cedula to save best results to the JSONL database.
5. Inspect correlation tables, FDR‑adjusted results, residual diagnostics.

## Local Database
- JSON Lines file: `data/hrv_solar_db.jsonl` (created on first save).
- Fields: `cedula`, `session_id`, `created_utc`, `metric`, `pearson_r`, `p_value`, `n`, `lag_hours`, (optionally `q_value`).

## Notes
- P‑values require SciPy; otherwise they display as NaN.
- Correlations are sensitive to timing; use lags to align HRV window times to storm arrival.
- Interpret results cautiously; literature shows effects are modest and variable.

## SpaceWeatherLive agent (scrape with OpenAI fallback)
- New: Fetch a concise snapshot from `https://www.spaceweatherlive.com/` (Kp forecast, solar wind speed/density, IMF Bt/Bz, sunspot number, F10.7, flare probabilities). The Streamlit Space Weather tab includes an expander to pull these values and display them alongside NOAA SWPC data.

### CLI
```bash
python -m app.swl_fetch --output data/spaceweatherlive_snapshot.json
```
This writes a JSON snapshot with the parsed fields. The command first tries a direct scrape; if that fails, it falls back to OpenAI-assisted extraction from the HTML.

### Environment and security
- Add your OpenAI key to `.env`:
```
OPENAI_API_KEY=sk-...
```
- Do not commit secrets. Ensure `.env` is ignored by Git. Never hard‑code API keys in code or notebooks.

### Libraries used
- requests (HTTP with timeouts)
- beautifulsoup4 (robust HTML parsing)
- openai (Responses API for fallback extraction)

### Sources
- SpaceWeatherLive home and Solar activity pages (`https://www.spaceweatherlive.com/`)  
  See help pages for context: Kp Index and IMF sections.
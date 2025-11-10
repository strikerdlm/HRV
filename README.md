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
- SpaceWeatherLive CACTus CME ingestion (direct scrape + OpenAI fallback) covering counts, velocity statistics, angular width, halo rate, and SIDC Ursigram commentary.
- Interactive feature-matrix builder that aligns HRV metrics with DONKI and SpaceWeatherLive predictors, includes correlation/ranking utilities, and offers an experimental linear response model with downloadable coefficients.

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
6. Expand the SpaceWeatherLive snapshot to pull CACTus CME metrics (velocity distribution, angular width, halo incidence) and SIDC narrative highlights.
7. Use the **HRV ↔ space-weather feature matrix (beta)** tools to:
   - Generate a lagged feature matrix combining HRV metrics with DONKI/SWL predictors.
   - Rank the strongest predictors per HRV metric with minimum-sample guardrails.
   - Train a quick linear response model and download correlations, rankings, feature matrix, and coefficient tables.

## Local Database
- JSON Lines file: `data/hrv_solar_db.jsonl` (created on first save).
- Fields: `cedula`, `session_id`, `created_utc`, `metric`, `pearson_r`, `p_value`, `n`, `lag_hours`, (optionally `q_value`).

## Notes
- P‑values require SciPy; otherwise they display as NaN.
- Correlations are sensitive to timing; use lags to align HRV window times to storm arrival.
- Interpret results cautiously; literature shows effects are modest and variable.

## SpaceWeatherLive agent (scrape with OpenAI fallback)
- New: Fetch a concise snapshot from `https://www.spaceweatherlive.com/` (Kp forecast, solar wind speed/density, IMF Bt/Bz, sunspot number, F10.7, flare probabilities). The Streamlit Space Weather tab includes an expander to pull these values and display them alongside NOAA SWPC data.
- New: Parse the CACTus “Latest CMEs” table and SIDC Ursigram bulletin to capture CME counts, velocity statistics, halo status, and narrative highlights for downstream HRV correlation, ranking, and modelling workflows.

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
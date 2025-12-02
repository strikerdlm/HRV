# WARP.md

This file provides guidance to WARP (warp.dev), Cursor, and other AI agents when working with code in this repository.

**Version**: 1.6.4 | **Last Updated**: 2025-12-02

## Overview
HRV (Heart Rate Variability) Analysis application with Space Weather and NOAA Integration. This is a Streamlit-based scientific application that analyzes heart rate variability metrics from Polar RR-interval recordings and correlates them with space weather data from NOAA SWPC feeds, NASA DONKI, and SpaceWeatherLive snapshots. The application is designed for aerospace medicine and psychophysiology research.

### Key Capabilities (v1.6.4)
- **GPU Acceleration**: Optional CUDA-powered HRV computations (RTX 5070 supported)
- **User Profiles**: Centralized biometrics, clinical scales (ESS, Samn-Perelli, KSS, VAS)
- **Space Weather Impact Predictions**: Real-time arrival time calculations for solar events
- **Performance Optimization**: Configurable CPU/memory presets with smart caching
- **Persistent Logging**: File-based debug logs in `logs/` directory

## Running the Application

### Start the Streamlit app
```powershell
streamlit run app/app.py
```

### Install dependencies
```powershell
pip install -r requirements.txt
```

### Python version
Python 3.10+ required

### Environment setup
Create a `.env` file in the project root with API keys:
```
OPENAI_API_KEY=sk-...
NASA_API_KEY=...
ACCUWEATHER_API_KEY=...
```

Never commit secrets or API keys. The `.env` file is already in `.gitignore`.

## Architecture

### Core Module Structure
The application follows a modular architecture with strict separation of concerns:

1. **`app/hrv_core.py`** — Core HRV computation engine
   - Artifact detection and interpolation
   - Time-domain metrics (RMSSD, SDNN, pNN50, etc.)
   - Frequency-domain analysis (VLF, LF, HF power via Welch/Periodogram/AR)
   - Geometric metrics (Triangular Index, TINN, Baevsky Stress Index)
   - Nonlinear metrics (Poincaré SD1/SD2, DFA, entropy)
   - Windowed analysis for time-varying conditions
   - Autonomic function tests (Valsalva ratio, deep breathing E:I ratio, 30:15 ratio)
   - Readiness baseline builder from historical parasympathetic indices

2. **`app/noaa_space.py`** — NOAA Space Weather data ingestion
   - Fetches and harmonizes JSON feeds from NOAA SWPC (https://services.swpc.noaa.gov/json/)
   - Typed data bundles (`NOAASourceSpec`, `NOAADataBundle`) with metadata
   - Deterministic caching in `app/data_cache/noaa_space/` (6-hour TTL)
   - Supports F10.7 flux, planetary K-index, solar wind, IMF, GOES x-ray/proton flux, geomagnetic Dst
   - All timestamps normalized to UTC timezone-aware format

3. **`app/app.py`** — Main Streamlit application
   - Multi-tab interface: Overview, Time Series, Frequency, Nonlinear, Spectrogram, Windowed, Metrics, ANS Function Tests, Readiness, Gauges, Science, Space Weather, NOAA Space, Export, References, About
   - Manages Streamlit session state for uploaded files and computed metrics
   - Integrates HRV core, NOAA space data, NASA DONKI events, SpaceWeatherLive scraping, ECharts visualizations, and optional GPT‑5 interpretation
   - Correlation workflows for HRV↔space-weather analysis with lag scanning, FDR-adjusted p-values, partial correlations, and simple linear response models

4. **`app/spaceweatherlive_client.py`** — SpaceWeatherLive scraper
   - Direct HTML parsing of https://www.spaceweatherlive.com/ for Kp forecast, solar wind, IMF, sunspot number
   - Parses CACTus CME table and SIDC Ursigram for CME velocity stats, halo rates, narrative highlights
   - Bounded retries/timeouts (≤10s)

5. **`app/spaceweather_openai_fallback.py`** — OpenAI-assisted extraction
   - Fallback for SpaceWeatherLive when direct scraping fails
   - Uses OpenAI API for structured data extraction from HTML

6. **`app/ml_enhancements.py`** — Deterministic k-means clustering
   - Clusters windowed HRV metrics to identify baseline vs high-deviation segments
   - No random sampling; bounded by `max_iterations` with early convergence exit
   - Returns enriched dataframe with cluster labels, scores, and summary

7. **`app/gpt_interpretation.py`** — GPT-5 high-reasoning interpretation
   - Builds JSON payload from HRV analysis (datasets overview, metrics tables, windowed results, episodes, ML clusters)
   - Requests doctoral-level markdown report from OpenAI GPT-5 (high reasoning)
   - Includes reasoning summary and source listing; UI surfaces the markdown only (reasoning is never logged)

8. **`app/echarts_component.py`** — ECharts visualization wrapper
   - Streamlit component for rendering Apache ECharts (gauge, line, scatter, heatmap)
   - Consistent styling (double-ring gauges, responsive layout, tooltips, color semantics)

9. **`app/export_utils.py`** — Export utilities
   - Markdown report builder for exporting analysis results
   - Configurable export scope and formatting

10. **`app/gpu_processing.py`** — GPU-accelerated HRV computations (NEW v1.6.4)
    - CUDA-powered RMSSD, SDNN, pNN50, FFT-based PSD, band powers, Poincaré metrics
    - Automatic GPU detection with CPU fallback
    - Benchmark tool to compare GPU vs CPU performance
    - Requires `cupy-cuda12x` (optional dependency)

11. **`app/user_profile_tab.py`** — User profile management (NEW v1.6.4)
    - Centralized biometric data (age, weight, height, BMI, VO2max)
    - Clinical scale assessments (ESS, Samn-Perelli, KSS, VAS Fatigue/Pain)
    - Persistent SQLite storage via `user_database.py`
    - Historical assessment tracking with timestamps

12. **`app/performance_utils.py`** — CPU performance optimization (NEW v1.6.3)
    - Configurable presets (Fast, Balanced, Full Quality)
    - Smart downsampling for large datasets
    - Session-state caching with TTL
    - DataFrame optimization utilities

13. **`app/space_weather_impact.py`** — Solar event impact predictions (NEW v1.6.2)
    - Exact arrival time calculations for photons, SEPs, plasma, geomagnetic storms
    - Bogotá timezone display with countdown timers
    - Biological effect descriptions and Polar H10 recommendations
    - Severity classification (LOW/MODERATE/HIGH/SEVERE)

14. **`app/logging_config.py`** — Centralized logging infrastructure (NEW v1.6.4)
    - Rotating file logs in `logs/` directory (app.log, errors.log)
    - 10 MB per file with 5 backup rotations
    - Audit trail for user actions
    - Console + file dual output

### Data Flow
1. User uploads Polar RR-interval text files (one RR in ms per line, filename format `YYYY-MM-DD HH-MM-SS.txt` inferred as GMT-5)
2. `hrv_core.clean_rr_intervals` detects artifacts via threshold-median or threshold-prev heuristics
3. Time/frequency/nonlinear/entropy metrics computed on cleaned RR
4. Windowed analysis applies sliding window (default 5 min window, 1 min step) with optional deviation detection (robust z-scores via median/MAD)
5. NOAA space data fetched/cached in `app/data_cache/noaa_space/`
6. HRV metrics paired with NOAA time-series for lag-aware Pearson/Spearman correlations
7. FDR q-values (Benjamini-Hochberg), partial correlations (controlling for weather covariates), and OLS residual diagnostics computed
8. Best correlations persisted to `data/hrv_solar_db.jsonl` (keyed by Cedula)
9. ECharts gauges/charts render metrics against short-term anchors

### Extended Modules and New Features
- **Multi-source device imports**: `actigraph_import.py`, `garmin_import.py`, `somfit_import.py`, `ecg_rpeak_detection.py` handle ActiGraph, Garmin, Somfit and ECG R-peak data, normalising into a common RR/HRV schema.
- **Real‑time monitoring**: `realtime_ble.py`, `realtime_hrv.py` stream BLE heart‑rate / RR data for near‑real‑time HRV and quality control.
- **Fatigue and operational performance**: `fatigue_calculator/`, `fatigue_integration.py`, `fatigue_integration.py`, and `exercise_hrv.py` connect HRV, workload and circadian factors to fatigue and performance risk indices.
- **Sleep & long‑term tracking**: `sleep_analysis.py`, `sleep_metrics.py`, `sleep_tab.py`, `multiday_tracker.py`, `longterm_trending.py` support multi‑night / multi‑day trends, sleep staging metrics, and readiness trajectories.
- **Multimodal & wearable fusion**: `wearable_fusion.py`, `multimodal_fusion.py`, `user_data_manager.py` integrate multiple devices (e.g. wearables + RR files) into unified profiles.
- **Advanced analytics and predictions**: `ml_analytics.py`, `ml_predictions.py`, `solar_physiology_correlation.py`, `scientific_charts.py` implement clustering, regression and scientific visualisations for HRV↔environment relationships.
- **Publication export**: `publication_export.py` supports exporting results and figures in a form aligned with journal-style reporting.

These modules extend the original single‑session HRV app into a broader platform for multiday tracking, multi‑device ingestion, fatigue/sleep analytics, and research‑grade HRV↔space‑weather studies.

### Key Design Principles (From Global Python Rule)
This codebase adheres to strict deterministic, analyzable, reliable Python standards:
- **No recursion**; loops must be bounded with explicit counters or finite iterables
- **All I/O and IPC use finite timeouts** (e.g., `requests` with 10–15s timeout, `asyncio.wait_for` for async)
- **Explicit input validation** with precise exceptions (ValueError, TypeError); asserts only for internal invariants
- **Full type hints** (compatible with mypy/pyright strict mode)
- **Immutable data across module boundaries** (frozen dataclasses, tuples); avoid mutable defaults
- **Context managers** for files, sockets, locks (no resource leaks)
- **Small, cohesive functions** (~≤60 LOC, cyclomatic complexity ≤10)
- **Zero-warnings policy**: ruff/pylint, Black/isort formatting, Bandit security checks

### Logging & Error Tracking
The application maintains persistent logs for debugging and audit trails:

```
logs/
├── app.log        # Main application log (DEBUG level, 10 MB rotating)
├── errors.log     # Error-only log (ERROR level, 10 MB rotating)
└── session_*.log  # Per-session logs (optional)
```

**Log Configuration** (`app/logging_config.py`):
- `setup_logging()` — Initialize file + console logging (call once at startup)
- `get_logger(__name__)` — Get module-specific logger
- `log_exception(logger, msg, exc)` — Consistent exception formatting
- `log_user_action(action, details)` — Audit trail for user interactions

**Viewing Logs**:
```powershell
# Tail the main log
Get-Content logs/app.log -Tail 50 -Wait

# View errors only
Get-Content logs/errors.log
```

### Testing
- Test suite lives under `tests/`:
  - `tests/test_comprehensive_modules.py` — end-to-end checks for core HRV and app wiring
  - `tests/test_new_modules.py` — coverage for recently added modules and utilities
  - `tests/test_noaa_cache.py` — NOAA caching and cache invalidation behavior
- Run tests with `pytest` from the project root (`HRV`).
- For new core logic, prefer **pytest + Hypothesis** property-based tests (artifact detection, interpolation, PSD, correlations).
- Target ≥90% coverage on critical modules (`app/hrv_core.py`, `app/noaa_space.py`) and treat warnings as errors during CI.

### Caching Strategy
- NOAA space data cached in `app/data_cache/noaa_space/` with 6-hour TTL
- Cache files named by source key and content hash
- SpaceWeatherLive snapshots cached in `app/data_cache/space_weather/`
- Stale cache entries ignored; fresh fetches on cache miss

### Correlation Database
- `data/hrv_solar_db.jsonl` stores best HRV↔space-weather correlations
- Each line is a JSON record with fields: `cedula`, `session_id`, `created_utc`, `metric`, `pearson_r`, `p_value`, `n`, `lag_hours`, optional `q_value`
- Append-only; no modification of existing records

## Working with HRV Metrics

### Key Metrics and Interpretation
- **RMSSD (ms)**: Vagal modulation proxy; higher = stronger parasympathetic tone
- **SDNN (ms)**: Overall variability (short-term); not equivalent to 24-h SDNN
- **HF power (ms²)**: Respiratory sinus arrhythmia; parasympathetic/breathing-related
- **LF power (ms²)**: Baroreflex with mixed sympathetic/parasympathetic contributions
- **LF/HF ratio**: Limited "balance" index; sensitive to breathing rate (use with caution)
- **SD1 (Poincaré)**: Short-term variability ≈ RMSSD/√2
- **SD2 (Poincaré)**: Long-term variability
- **DFA α1**: Fractal scaling exponent; ~0.75–1.25 at healthy rest
- **ApEn/SampEn**: Regularity/complexity; lower = more rigid autonomic regulation

### Autonomic Function Tests
- **Valsalva ratio**: Longest RR (phase IV) / shortest RR (phase II); ≥1.2 typical for middle-aged adults
- **Deep breathing E:I**: Expiratory–inspiratory RR difference/ratio; larger = greater vagal modulation
- **30:15 ratio**: Longest RR near 30th beat post-stand / shortest RR near 15th beat; ≥1.04 typical

### Data Quality Checks
- Visualize RR time series with artifact flags in "Time Series" tab
- If >5–10% artifacts flagged, consider retesting or interpreting cautiously
- Require stationarity for windowed metrics (use ≥5 min recording with stabilization period)
- Document posture, time-of-day, breathing (spontaneous vs paced), device type, recent exertion/caffeine

## NOAA Space Weather Integration

### Available NOAA Feeds (see `docs/NOAA json.md` for full list)
- F10.7 cm solar radio flux (3 daily slots)
- Planetary K-index (3-hour cadence)
- Solar wind proton speed/density/temperature (ACE/DSCOVR)
- Interplanetary magnetic field (Bt, Bz GSE/GSM)
- GOES x-ray flux (0.05–0.4 nm)
- GOES integral proton flux (≥1–≥500 MeV thresholds)
- Predicted Kp (1-hour model)
- Geomagnetic Dst (1-hour, 7-day)

### Correlation Workflow
1. Select HRV metric (e.g., RMSSD) and NOAA metric (e.g., Kp-index)
2. Configure lag range (e.g., 0–48 hours), step (e.g., 1 hour), merge tolerance (e.g., 30 min)
3. Optionally enable weather covariates (temperature, humidity, pressure from Open-Meteo Archive for Bogotá)
4. Compute Pearson r and p-values (requires SciPy)
5. Apply Benjamini-Hochberg FDR correction for multiple comparisons
6. Optionally compute partial correlations controlling for weather
7. Run OLS residual diagnostics (R², Durbin-Watson, normality test, residual plots)
8. Save best results to JSONL database with Cedula key

### SpaceWeatherLive Scraping
- CLI: `python -m app.swl_fetch --output data/spaceweatherlive_snapshot.json`
- Fetches Kp forecast, solar wind speed/density, IMF Bt/Bz, sunspot number, F10.7, flare probabilities
- Parses CACTus "Latest CMEs" table for counts, velocity stats (mean/median/max), angular width, halo rate
- SIDC Ursigram narrative highlights for CME context

## Modifying the Codebase

### Adding a New HRV Metric
1. Implement computation in `app/hrv_core.py` as a pure function with full type hints and docstring
2. Add metric to `compute_comprehensive_hrv` return dict
3. Update `docs/Manual.md` with metric definition, physiological interpretation, and clinical emphasis
4. Add property-based tests in `test_hrv_core.py` (to be created)

### Adding a New NOAA Feed
1. Define a `NOAASourceSpec` in `app/noaa_space.py` with key, path, title, description, value_columns, units, cadence_minutes
2. Add spec to `NOAA_SOURCES` dict in `noaa_space.py`
3. Test feed ingestion with `load_noaa_space_data(key)` to verify schema normalization and timestamp alignment
4. Update correlation UI in `app/app.py` Space Weather tab to surface new metric

### Adding a New Visualization
1. Build ECharts option dict in `app/echarts_component.py` or inline in `app.py`
2. Use `render_echarts(config)` to display chart in Streamlit
3. Ensure responsive layout, tooltips, legends, and color semantics match existing gauges/charts
4. Document chart interpretation in `docs/Manual.md`

### Code Style and Tooling
- **Linting**: Use `ruff check app/` or `pylint app/`
- **Formatting**: `black app/ --line-length 120` and `isort app/`
- **Type checking**: `mypy app/ --strict` or `pyright app/`
- **Security**: `bandit -r app/`
- **Pre-commit hooks**: Recommended for ruff, Black, isort, mypy, Bandit

### Commit Workflow
- **Never commit API keys or secrets**; always use `.env` and ensure it's in `.gitignore`
- Document changes in `CHANGELOG.md` (features, fixes, notes)
- Keep commit messages concise and imperative (e.g., "Add NOAA Dst feed ingestion")
- Before committing large refactors, ensure zero linter warnings and type errors

## File Naming Conventions
- RR-interval files: `YYYY-MM-DD HH-MM-SS.txt` (parsed as GMT-5, converted to UTC)
- Cache files: `<source_key>_<hash>.json` in `app/data_cache/noaa_space/` or `app/data_cache/space_weather/`
- Output snapshots: `spaceweatherlive_snapshot.json`, `hrv_solar_db.jsonl`

## Known Limitations
- **Arrhythmias/ectopy**: HRV metrics assume sinus rhythm; extensive ectopy invalidates standard interpretations
- **Short-term vs 24-hour**: SDNN and spectral indices differ across durations; do not extrapolate short-term to 24-h risk markers
- **Respiration sensitivity**: HF power and LF/HF highly sensitive to breathing rate/depth; document breathing protocol
- **Entropy parameters**: ApEn/SampEn are parameter- and length-sensitive; compare like-with-like
- **Readiness baseline**: Requires stable conditions (posture, time-of-day, breathing, sensor type); rebuild if conditions change
- **P-values require SciPy**: Without SciPy, p-values display as NaN; install SciPy for statistical inference

## Scientific References
- Task Force ESC/NASPE (1996): Heart rate variability standards ([ESC PDF](https://www.escardio.org/static-file/Escardio/Guidelines/Scientific-Statements/guidelines-Heart-Rate-Variability-FT-1996.pdf))
- Psychophysiology Publication Guidelines (Part 1, 2024)
- Shaffer & Ginsberg (2017): An Overview of Heart Rate Variability Metrics and Norms
- Sacha (2016): Heart rate contribution to HRV (Frontiers)

See `docs/Manual.md` for full references and metric-specific citations.

## AI Agent & Development Rules

**CRITICAL**: All agents and developers must follow the detailed rules in [`docs/Agent_Rules.md`](docs/Agent_Rules.md).

### Summary of Key Rules
1.  **Global Python Rules**: Deterministic, analyzable, bounded execution, strict typing, zero warnings.
2.  **Scientific Standards**: Evidence-based changes with peer-reviewed citations.
3.  **Documentation**: Update `README.md`, `docs/Manual.md`, and `CHANGELOG.md` with every meaningful change.
4.  **Agentic Best Practices**:
    *   Act as a specialized **Research Engineer**.
    *   Use **Chain of Thought** for planning.
    *   Check `WARP.md` and `docs/Manual.md` for architecture context.

See [`docs/Agent_Rules.md`](docs/Agent_Rules.md) for the complete standard.

## Troubleshooting

### Debugging with Logs
**First step for any issue**: Check the log files:
```powershell
# View recent errors
Get-Content logs/errors.log -Tail 100

# Search for specific error
Select-String -Path logs/app.log -Pattern "ERROR|EXCEPTION" -Context 3
```

### Streamlit hangs on Windows shutdown
The app includes Windows console safety workarounds (Colorama fix) in `app/app.py`. If Streamlit still hangs, ensure `CLICOLOR=0` and `NO_COLOR=1` are set in environment.

### OpenAI API errors
- Verify `OPENAI_API_KEY` in `.env`
- Check OpenAI service status and API quota
- Fallback interpretation disabled if key missing; app will skip GPT-5.1 report
- Check `logs/app.log` for API response details

### NOAA feed fetch timeout
- Default timeout is 10–15s; increase `REQUEST_TIMEOUT` in `noaa_space.py` if network is slow
- Check NOAA SWPC service status: https://services.swpc.noaa.gov/
- Cache prevents repeated fetches; delete stale cache files in `app/data_cache/noaa_space/` to force refresh

### SpaceWeatherLive scraping fails
- Direct scraping may fail due to site structure changes; fallback to OpenAI extraction if `OPENAI_API_KEY` is set
- Verify site is accessible: https://www.spaceweatherlive.com/
- Increase timeout or retry logic in `spaceweatherlive_client.py`

### GPU Acceleration Issues
- **GPU not detected**: Verify CUDA installation: `nvidia-smi`
- **CuPy import fails**: Install correct version: `pip install cupy-cuda12x`
- **Out of memory**: Reduce batch size or disable GPU for large datasets
- Check `logs/app.log` for GPU initialization messages

### Import errors
- Ensure all dependencies in `requirements.txt` are installed
- Use Python 3.10+ (some type hints and syntax require 3.10)
- Activate virtual environment if using `.venv`

### Database/Profile Issues
- SQLite database stored in `app/hrv_users.db`
- Backup before schema changes: `copy app\hrv_users.db app\hrv_users.db.bak`
- Reset profiles: Delete `app/hrv_users.db` (data will be lost)

## Documentation
- **User Manual**: `docs/Manual.md` — comprehensive guide for clinicians/researchers
- **NOAA Feeds**: `docs/NOAA json.md` — full list of SWPC JSON endpoints
- **Scientific Discussion**: `docs/Scientific_Discussion_Parasympathetic_Analysis.md`
- **CHANGELOG**: `CHANGELOG.md` — version history and feature additions
- **README**: `README.md` — quick start and high-level features
- **Agent Rules**: `.cursor/rules/agent.mdc` — AI agent development guidelines

## Project Structure (Updated v1.6.4)
```
HRV/
├── app/
│   ├── app.py                    # Main Streamlit application
│   ├── hrv_core.py               # Core HRV computations
│   ├── noaa_space.py             # NOAA data ingestion
│   ├── gpu_processing.py         # GPU-accelerated computations (NEW)
│   ├── user_profile_tab.py       # User profile management (NEW)
│   ├── user_database.py          # SQLite persistence (NEW)
│   ├── performance_utils.py      # CPU optimization utilities (NEW)
│   ├── space_weather_impact.py   # Solar event predictions (NEW)
│   ├── logging_config.py         # Centralized logging (NEW)
│   └── data_cache/               # Cached API responses
├── logs/                         # Application logs (NEW)
│   ├── app.log                   # Main log (rotating)
│   └── errors.log                # Error-only log
├── tests/                        # pytest test suite
├── docs/                         # Documentation
├── requirements.txt              # Dependencies
├── WARP.md                       # This file
└── .cursor/rules/agent.mdc       # AI agent rules
```

## Maintenance Checklist
When modifying this codebase:

1. **Before Changes**:
   - Read `WARP.md` and `docs/Manual.md` for context
   - Check `logs/errors.log` for existing issues
   - Run `pytest` to verify baseline

2. **During Development**:
   - Follow Global Python Rules (see `.cursor/rules/agent.mdc`)
   - Add type hints and docstrings
   - Use `get_logger(__name__)` for logging

3. **After Changes**:
   - Update `CHANGELOG.md` with user-visible changes
   - Update `docs/Manual.md` if feature affects users
   - Run linters: `ruff check app/`
   - Check for new errors in `logs/errors.log`

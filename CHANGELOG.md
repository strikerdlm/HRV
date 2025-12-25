# Changelog

All notable changes to the Mission Control - Flight Surgeon are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.8.58] - 2025-12-25

### Added
- **Space Analytics event-aligned analysis (prototype)** (`app/app.py`, `app/space_analytics_events.py`, `docs/Manual.md`): Added threshold-based event detection (Kp/Dst) with explicit start/end and an on-demand **baseline vs event delta table** for HRV/HRF targets to identify which physiology metrics shift during a space-weather event.

## [1.8.57] - 2025-12-25

### Changed
- **Heart Rate Fragmentation (HRF) documentation** (`app/app.py`, `docs/Manual.md`): Expanded the in-app HRF explanations with clear **medical/physiology meaning**, **operational interpretation**, and practical factors that can increase/decrease HRF. Added peer-reviewed citations (Costa 2017; Hayano 2020; Guichard 2025 PROOF‑AF) to the UI and manual.

## [1.8.56] - 2025-12-25

### Fixed
- **Export tab responsiveness** (`app/app.py`): Prevented heavy, unrequested work on reruns by making **markdown report generation** explicitly button-driven (session-cached) and by requiring an explicit **Prepare HRV export files** click before serializing large windowed data to CSV/JSON.
- **Science tab responsiveness** (`app/app.py`): Replaced the always-rendered full “Scientific Reference Guide” expanders with a **fast section picker** so the Research app stays responsive while switching tabs (Streamlit tabs are not lazy).

## [1.8.55] - 2025-12-25

### Fixed
- **Space Data tab “fade” rerun loops** (`.streamlit/config.toml`, `app/app.py`): Disabled Streamlit’s file watcher (`server.fileWatcherType = "none"`) to prevent unrequested reruns triggered by runtime cache/log writes (common on Windows/OneDrive). Also removed an unnecessary `st.rerun()` from the Space Data “Clear fetched feed” action to avoid extra flicker.
- **References tab loads reliably** (`app/app.py`): Removed legacy DONKI/correlation/feature-matrix logic that was incorrectly embedded in the **📚 References** tab and could trigger slow/failed renders. References now remain lightweight and point users to **🌐 Space Data** and **🔬 Space Analytics** for data and analysis.
- **About tab full renderer no longer mis-detects docs as errors** (`app/about_tab.py`): Replaced the fragile “contains the word ‘error’” heuristic with structured file-load status so `docs/Manual.md` and `CHANGELOG.md` previews render reliably.

### Changed
- **Streamlit config cleanup** (`.streamlit/config.toml`): Removed deprecated/invalid options (Streamlit 1.36.0) to eliminate startup warnings.

## [1.8.54] - 2025-12-25

### Added
- **Space Analytics tab (Correlations + ML)** (`app/app.py`): Added **🔬 Space Analytics** — an on-demand workspace to correlate NOAA predictors against **HRV + HRF** windowed metrics and train ML models from lagged space-data features. All analyses are **button-driven** and results persist in session state.
- **HRF↔HRV pairwise stats table** (`app/app.py`): The **🧩 HRF ↔ HRV** tab now includes a per-pair statistical summary table (test, result, p-value, meaning) with p-values formatted to **4 decimals**.

### Changed
- **GPU-aware boosting** (`app/app.py`): When GPU processing is enabled, XGBoost and LightGBM models now attempt GPU acceleration (safe CPU fallback on unsupported builds).
- **Unified Space Data tab (data-only)** (`app/app.py`): Space Data remains a stable, data-only dashboard for SWPC + NOAA + DONKI fetch/visualization. Correlation/ML workflows live in **🔬 Space Analytics**.
- **GPT-5.2 report interpretation includes Space Analytics results** (`app/app.py`, `app/gpt_interpretation.py`, `app/export_utils.py`): Export report generation now passes Space Analytics correlation/ML outputs into the **GPT‑5.2 high reasoning** payload and renders a bounded Space Analytics section in the markdown report when available.
- **Documented app-mode separation** (`docs/Manual.md`, `WARP.md`): Operational app is the crew-facing intake/mission workflow; Research app is the core statistics/analytics workspace.

### Fixed
- **Research app entrypoint loads the full UI reliably** (`app/research_app.py`): Hardened import path setup so `streamlit run app/research_app.py` always launches `app/app.py` (and therefore exposes Space Data/Space Analytics tabs) regardless of Streamlit/sys.path ordering.

## [1.8.52] - 2025-12-25

### Added
- **Dedicated HRF ↔ HRV tab** (`app/app.py`): Added **🧩 HRF ↔ HRV** — an offline workspace for heart-rate fragmentation (HRF) gauges and per-recording HRF↔HRV correlation matrices/scatter plots, intentionally decoupled from NOAA/SWPC/DONKI fetch pipelines.

### Fixed
- **Space Weather correlations persist across tab switches** (`app/app.py`): HRV↔Kp correlation outputs are now cached in session state and re-displayed when returning to the Space Weather tab, preventing “compute → switch tab → reset” behavior. Added a **Run HRV window analysis** CTA when windowed metrics are missing and stabilized Space Weather correlation widgets with explicit keys.
- **Heart-rate fragmentation metrics available in fast workflows** (`app/hrv_core.py`): HRF metrics (PIP/IALS/PSS and PROOF‑AF-derived PIP_H/PIP_S/PAS/W0–W3) are now computed regardless of the `include_advanced` flag, so fragmentation metrics are available for windowed and per-recording analyses without requiring “high compute” mode.

## [1.8.51] - 2025-12-24

### Added
- **NOAA correlation CTAs** (`app/app.py`): Added inline buttons beside the NOAA correlation callouts to trigger HRV window analysis when windowed metrics are missing, so users can start correlations and batch scans directly from the NOAA tab.
- **On-demand metric correlations** (`app/app.py`): The physiology correlation matrix now runs only when you click **Run correlations**, preventing any automatic correlation/analysis on render.
- **User-facing on-demand notices** (`app/app.py`): Added explicit “click to run” info and spinners for NOAA correlations, batch NOAA scans, and the physiology correlation matrix so users see a clear warning that computations may take time.
- **Instant Space Weather/NOAA tabs** (`app/app.py`): Removed automatic cache loads; both tabs now render immediately and only load cached or fresh data when you click **Load cached copy/NOAA** or **Fetch**, with spinners and success messaging. This keeps the UI responsive even with no HRV data.
- **About tab performance fix** (`app/app.py`, `app/about_tab.py`): About now defaults to a lightweight preview (instant), with optional buttons to load the full page/manual/changelog on demand to avoid long UI hangs.

### Changed
- **Moved inline HRV “Key References” list** (`app/app.py`): Removed non-APA inline reference links from the Circadian tab area; references are consolidated in the **📚 References** tab (APA 7 format).
- **NOAA Space tab reliability** (`app/app.py`, `app/noaa_space.py`, `app/user_profile_tab.py`): Fixed cache-load handling for “Full” scope, prevented Clinical Assessments from triggering NOAA network fetches, and added a hard overall fetch timeout so NOAA downloads can’t hang indefinitely.
- **Space Weather tab reliability** (`app/app.py`): Prevented “Fetch space weather” from hanging due to executor shutdown waiting on stuck network threads; added cache-only auto-bootstrap so the tab renders immediately without any network calls.
- **Logout reliability** (`app/user_profile_tab.py`, `app/app.py`): Logout is now executed via `on_click` callback (runs before rerender), preventing long “logout hangs”; and the `user_logged_out` flag is no longer accidentally cleared by unrelated flows.
- **Logout hardening across modules** (`app/app.py`, `app/user_management_ui.py`, `app/sleep_tab.py`): All logout buttons now use unique keys; `user_management_ui` logout sets the global `user_logged_out` flag; and `app.py` enforces a hard logout guard that clears any restored profile when logged out.
- **Disabled default auto-profile selection** (`app/app.py`): The app no longer silently auto-selects the author/single profile when none is set (this made logout appear broken). You can re-enable for demos via `HRV_AUTO_SELECT_DEFAULT_PROFILE=1`.

### Fixed
- **Wrist Monitoring refresh + Garmin Connect integrity** (`app/user_profile_tab.py`, `app/garmin_connect_service.py`): Wrist Monitoring history now refreshes immediately after Garmin sync/import (token-based cache bust + Refresh button, no forced rerun). Garmin Connect fetch no longer reports success while returning all-null placeholder rows, and daily field extraction is more robust for Vivosmart 5 exports.
- **Research app login reliability** (`app/user_profile_tab.py`): User selection login now uses stable widget keys + a pre-rerun `on_click` handler, and surfaces a clear error when the selected profile cannot be loaded. This fixes “login user does not work” in `app/research_app.py` (research mode).

## [1.8.50] - 2025-12-23

### Fixed
- **HRV data survives WebSocket reconnects** (`app/app.py`): Added unconditional cache restoration at the start of `main()` so that `windowed_df`, `multi_results_df`, `meta_rows`, `ml_summary_df`, and `episodes_df` are always restored from session state on every script rerun. This ensures NOAA Space correlations, ML, and plots work correctly even after browser disconnects/reconnects.
- **NOAA Space correlations and ML now display properly** (`app/app.py`): The correlation and batch ML sections no longer show "Run the HRV window analysis to enable…" after HRV analysis is completed; the cached results are now reliably available across tab switches and page scrolls.
- **Red warning box placed directly below Mode badge** (`app/app.py`): Moved the "Heavy Computations" warning to render immediately after the Mode: Research badge at the top of the page, with matching purple/red styling.

### Changed
- **Removed redundant cache rehydration code** (`app/app.py`): The late-stage rehydration block (added in 1.8.49) was replaced by the more robust unconditional restoration at variable initialization, simplifying the code flow.
- **Removed misplaced tab disclaimers** (`app/app.py`): Removed the inline red disclaimer messages from inside Space Weather and NOAA Space tabs since the warning is now prominently placed at the top.

## [1.8.49] - 2025-12-23

### Fixed
- **Space Weather loads fast (no hidden network fetches)** (`app/app.py`): Removed the automatic SWPC Kp download that was triggered during correlation UI rendering; Kp now loads from cache-only and requires an explicit user fetch to refresh.

### Changed
- **NOAA Space “Today (fast)” mode** (`app/app.py`): Added a fast default scope that loads only Kp + F10.7 for instant context; Core/Full remain available on demand.
- **Cache-only bootstrap for Space Weather + NOAA Space** (`app/app.py`, `app/noaa_space.py`): Tabs now show the last cached copy immediately without hitting the network.
- **Background prefetch now optional (default OFF)** (`app/app.py`): Background 12h refresh is no longer automatic; it’s a user toggle to avoid slow startup/CPU contention on Windows/OneDrive setups.

## [1.8.48] - 2025-12-23

### Fixed
- **Space Weather tab reliably renders** (`app/app.py`): Removed accidental gating of the SWPC dashboard on `SPACE_WEATHER_IMPACT_AVAILABLE` and fixed the Impact Predictions section so its controls render consistently.
- **User Profile errors no longer block NOAA/Export** (`app/app.py`): Added a safety net around `render_user_profile_tab()` so a profile-side exception can’t stop the rest of the app from rendering.
- **Streamlit rerun loops caused by repo file writes** (`app/app.py`, `.streamlit/config.toml`): Disabled file-based `_agent_debug_log` by default (logs to the main logger only when debug is enabled) and blacklisted `.cursor/` to prevent IDE background writes from triggering reloads.

## [1.8.47] - 2025-12-23

### Fixed
- **Population Norms now works immediately after RR upload** (`app/app.py`): The norms comparison no longer depends on windowed metrics being present; it now falls back to full-recording or quick RR-derived summaries and lets you choose the recording to compare.

### Changed
- **OpenAI/Agents analysis is now Export-tab only and strictly on-demand** (`app/app.py`): AI analysis no longer runs from analysis tabs and will never auto-trigger; it runs only when you click the Export-tab buttons.
- **Metric Explainer is now Export-tab only and on-demand** (`app/app.py`): Explanations are generated only when requested from Export; auto-refresh is off by default.
- **GPT-5.2 interpretation now exposes code interpreter** (`app/gpt_interpretation.py`): The export interpretation request now includes the `code_interpreter` tool for numeric/derived-stat computations from the payload.

### Added
- **Friendly “How to read this plot” guidance** (`app/app.py`): Added concise axis/interpretation help expanders for Time Series, Frequency (PSD), Nonlinear (Poincaré), and Spectrogram tabs.

## [1.8.46] - 2025-12-23

### Fixed
- **Streamlit “fade/restart” loops during HRV + space-weather work** (`.streamlit/config.toml`): Blacklisted `crew/`, `app/data_cache/`, and `logs/` from Streamlit’s watcher so writing HRV outputs / NOAA caches no longer triggers unintended reloads.
- **Space Weather / NOAA button flicker** (`app/app.py`): Removed redundant `st.rerun()` calls after fetch actions so results render immediately without extra UI restart.

### Changed
- **12h background refresh scope tuned for responsiveness** (`app/app.py`): Background auto-refresh now preloads the **Core NOAA feeds** (fast) and keeps DONKI background queries conservative, preventing UI stalls while still supporting research correlations.

### Added
- **Extended HRF (Heart Rate Fragmentation) metrics in HRV computation** (`app/hrv_core.py`): Added PIP_H/PIP_S, PAS, W0–W3, and a quality flag to the computed metric set for performance-oriented analysis.
- **HRF panel in Readiness tab** (`app/app.py`): New HRF expander summarizes fragmentation markers per dataset with literature-based interpretation.
- **Cache reset controls** (`app/app.py`): Added explicit (opt-in) buttons to clear NOAA/SWPC/DONKI cache folders for troubleshooting, without automatic deletion.

## [1.8.45] - 2025-12-23

### Added
- **Operational vs Research enforcement** (`app/app_mode.py`, `app/app.py`, `app/operational_app.py`, `app/research_app.py`): Added an app-mode badge and hard policy gates so Operational mode stays fast and Research mode owns correlations/ML dashboards.

### Changed
- **Operational-mode hard blocks** (`app/performance_utils.py`): Heavy downloads and heavy computations are forced OFF in Operational mode (even if toggled elsewhere), preventing accidental long-running correlation/ML workflows in the clinical UI.

## [1.8.44] - 2025-12-23

### Fixed
- **Startup stability (no crashes on page config)** (`app/app.py`, `app/operational_app.py`): Page config is now applied best-effort and will never crash the app if Streamlit disallows `set_page_config()` in a given run.

## [1.8.43] - 2025-12-23

### Fixed
- **Research app startup** (`app/app.py`, `app/research_app.py`): Resolved Streamlit `set_page_config()` ordering errors by ensuring page config is applied before importing Streamlit-cached modules.

### Added
- **Streamlit stability config** (`.streamlit/config.toml`): Enabled polling file watcher for OneDrive reliability and disabled fast reruns to reduce session race conditions.

## [1.8.42] - 2025-12-23

### Added
- **Operational vs Research apps** (`app/operational_app.py`, `app/research_app.py`): New split entrypoints in the same repo. Operational mode focuses on User Profile + lightweight space-weather context; Research mode keeps the full HRV/HRF computation + NOAA/Space Weather correlation dashboards.

## [1.8.41] - 2025-12-23

### Changed
- **Faster NOAA Space loads (Core vs Full)** (`app/app.py`): NOAA Space now defaults to a **Core** scope (key geomagnetic + solar-wind feeds) for fast loading, with an optional **Full** scope for the entire feed library.
- **HTTP connection pooling** (`app/app.py`, `app/noaa_space.py`, `app/space_weather_impact.py`): Reuse pooled `requests.Session` connections to reduce repeated TLS handshakes when pulling many SWPC feeds.
- **Background auto-fetch tuned for responsiveness** (`app/app.py`): Background fetch now preloads only the NOAA Core scope and uses a shorter DONKI default window to keep background refresh lightweight.

### Fixed
- **Space Weather fetch latency** (`app/app.py`): Kp and F10.7 fetches now run in parallel when using **📥 Fetch space weather**.

## [1.8.40] - 2025-12-23

### Fixed
- **Clinical Assessment wake time** (`app/user_profile_tab.py`): Garmin sleep end timestamps are now converted to the local timezone with timezone-aware defaults, and Garmin daily metric rows are normalized safely (dataclass/`asdict`). Wake time and hours-since-waking now reflect today's Vivosmart data instead of showing UTC-shifted times.
- **Bogotá timezone alignment** (`app/user_profile_tab.py`): All user-facing wake times and “hours since waking” now use Bogotá time (UTC-5) across clinical assessment and Garmin autofill flows, avoiding Pacific/UTC drift.
- **Visible timezone indicator** (`app/user_profile_tab.py`): Clinical Assessment and Profile Tools now display the detected Bogotá timezone (UTC-5) so users can confirm clock alignment.
- **Auto-only hours awake** (`app/user_profile_tab.py`): Hours since waking is now strictly auto-computed from the selected wake time and local clock to prevent drift or manual inconsistencies.
- **Space Weather/NOAA tab load guard** (`app/app.py`): Fixed an uninitialized loading placeholder that could raise an error before the NOAA Space tab rendered when the Space Weather dashboard wasn’t loaded, restoring the “Load Space Weather dashboard” and NOAA Space tabs.

## [1.8.39] - 2025-12-23

### Added
- **Low-End Computer Performance Mode** (`app/performance_utils.py`): New performance optimization features for users with limited CPU/memory resources:
  - **Heavy Computation Toggles**: Checkboxes to enable/disable CPU-intensive operations:
    - Spectrogram Analysis (FFT over sliding windows)
    - Nonlinear Metrics (DFA, entropy, Poincaré)
    - ML Pattern Detection (K-means clustering)
    - Windowed HRV Analysis (time-varying metrics)
    - Frequency Domain Analysis (PSD, band powers)
  - **Heavy Download Toggles**: Checkboxes to enable/disable network-intensive operations:
    - NOAA Space Weather Data (multiple feeds)
    - SpaceWeatherLive Data (web scraping)
    - NASA DONKI Events (CME, SEP, flares)
    - Space Weather Impact Predictions
    - GPT AI Interpretation (API calls)
  - **Auto-Detection**: Performance settings automatically adjust based on detected CPU tier (high/medium/low)
  - **Preset Integration**: Fast (Low CPU) preset now disables heavy computations and downloads automatically

### Changed
- **Performance Settings UI** (`app/performance_utils.py`): Reorganized sidebar expander with clear sections for computations and downloads
- **ML Clustering** (`app/app.py`): ML checkbox now respects performance settings and shows help text when disabled
- **Visualization Checkboxes** (`app/app.py`): Skip checkboxes for frequency/Poincaré/spectrogram now default to skip when respective computation is disabled in performance settings
- **Space Weather Auto-Fetch** (`app/app.py`): Background fetching now respects download toggle settings

### Documentation
- **updates2026.md**: Created research document with Heart Rate Fragmentation literature review, biomathematical models for human performance, and UAV combat simulation research

## [1.8.38] - 2025-12-22

### Fixed
- **Clinical assessment Garmin autofill** (`app/user_profile_tab.py`): Handle GarminDailyMetrics dataclass objects when populating sleep context to prevent `'GarminDailyMetrics' object has no attribute 'get'` errors in the clinical assessment panel.
- **Hours since waking calculation** (`app/user_profile_tab.py`): Hours awake now derives directly from wake time (manual or Garmin) and current clock time on every rerun, ensuring today's value stays accurate without extra Garmin fetches.

## [1.8.37] - 2025-12-21

### Added
- **Dual Garmin sleep autofill buttons** (`app/user_profile_tab.py`): One-click Vivosmart pull now exists both in the Profile Tools Engine and in the Sleep & Chronotype section under Energy & Nutrition. It fills sleep hours, sleep quality, hours awake, RMSSD, and resting HR for SAFTE and Operational Performance tools.

### Changed
- **Sleep input emphasis** (`app/user_profile_tab.py`): Sleep/chronotype inputs are highlighted alongside nutrition basics, with shared session keys feeding SAFTE fatigue and Operational Performance (HRV+SAFTE) tools.

### Notes
- All tests pass (`pytest`).

## [1.8.36] - 2025-12-21

### Added
- **Background Space Weather Fetch with 12-hour Auto-Refresh** (`app/app.py`): Space weather data (NOAA, SWPC, NASA DONKI) now fetches in a background daemon thread on app startup. Data automatically refreshes every 12 hours without user intervention. The UI remains fully responsive during fetches. Each tab shows data age and refresh status (e.g., "✅ Data: 2h ago | Auto-refresh: 12h").
- **Garmin sleep autofill in Profile Tools Engine** (`app/user_profile_tab.py`): One-click Vivosmart/Garmin pull populates sleep hours, sleep quality, hours awake, RMSSD, and resting HR for SAFTE/operational tools.
- **Sleep & chronotype inputs under Energy & Nutrition** (`app/user_profile_tab.py`): Added synced sliders/inputs (sleep hours, hours awake, sleep quality, chronotype offset, RMSSD, resting HR, VO₂) that push values into the Profile Tools Engine for SAFTE fatigue and Operational Performance.

### Changed
- **EVA Clearance Semaphore** (`app/user_profile_tab.py`): Replaced the bar chart for EVA Clearance States with a traffic-light semaphore visualization. Three circular indicators (GO/MONITOR/NO-GO) glow when active, with a summary panel showing the dominant status and total assessments.
- **Space Weather Tab UI** (`app/app.py`): Updated fetch buttons with icons and clearer help text. Status indicators now show data age and auto-refresh schedule. Stale data (>12h) triggers automatic background refresh on next page load.

### Fixed
- **node_modules restoration** (`node_modules/`): Restored ECharts npm package files that were inadvertently marked as deleted in git.

## [1.8.35] - 2025-12-20

### Added
- **XGBoost and LightGBM ML models** (`app/app.py`): Added optional XGBoost and LightGBM gradient boosting models to space-weather ML analysis. These models often outperform RandomForest by 5-15% on tabular data. Models are automatically included if packages are installed (`pip install xgboost lightgbm`).
- **SHAP model interpretability** (`app/app.py`): Added SHapley Additive exPlanations (SHAP) for model interpretability. SHAP provides individual prediction explanations, feature interaction effects, and global vs local importance rankings. Available if `shap` package is installed (`pip install shap`).
- **Enhanced ML UI** (`app/app.py`): Updated Space Weather tab to display XGBoost and LightGBM metrics alongside existing models. Added tabs for Permutation Importance and SHAP Values with separate dataframes. Button text dynamically updates to show available models.
- **SHAP export support** (`app/export_utils.py`): Added SHAP importances to PDF/Markdown export reports alongside permutation importances.

### Changed
- **ML model function signature** (`app/app.py`): Updated `_run_ml_models_space_weather()` to include XGBoost, LightGBM, and SHAP computation. Function gracefully handles missing optional dependencies.
- **Requirements documentation** (`requirements.txt`): Added optional ML dependencies section with installation instructions for XGBoost, LightGBM, and SHAP.

### Documentation
- **ML enhancements guide** (`docs/ML_Enhancements_2025.md`): Created comprehensive guide documenting current ML implementations, recommended enhancements, priority matrix, and implementation roadmap.
- **Manual updates** (`docs/Manual.md`): Updated Space Weather ML section to document new models (XGBoost, LightGBM) and SHAP interpretability features.

## [1.8.34] - 2025-12-19

### Documentation
- **Canonical run command uses `hrv-py312`** (`README.md`, `docs/Manual.md`): Documented `conda run -n hrv-py312 streamlit run app/app.py` (and matching `conda run` for `pip`) so the app is always run under the pinned Streamlit 1.36.0 environment.

## [1.8.33] - 2025-12-19

### Changed
- **Plot titles moved outside chart area** (`app/echarts_component.py`, `app/circadian_tab.py`, `app/gauge_builder.py`): ECharts plot titles are now rendered as Streamlit text above each plot (and removed from the ECharts option) so the plot canvas stays clean. Gauges also hide their in-gauge title label and rely on the external title.

## [1.8.32] - 2025-12-19

### Performance
- **Default plot cap set to 500** (`app/app.py`, `app/performance_utils.py`): Default rendering now uses 500 points for rapid identification and smoother UI; you can still increase caps via the RR plot dropdown and Performance Settings presets.
- **Time Series + HR plot rendering speedup** (`app/app.py`): Downsample *before* converting full columns to Python lists, preventing large list allocations on reruns and reducing the “faded / always running” UI when plotting long recordings.
- **Spectrogram rendering speedup** (`app/app.py`): Use cached spectrogram computation, downsample the heatmap resolution, and build ECharts heatmap triplets via NumPy (vectorized) to keep browser rendering responsive on long recordings.
- **RR upload caching speedup** (`app/app.py`): Cache `UploadedRR` objects directly in session state to avoid reconstructing large DataFrames on every rerun; also avoids re-reading file bytes twice during cache cleanup.
- **Library loader speedup** (`app/app.py`): Cache the RR library listing (`@st.cache_data`) and clear it after saving so the sidebar stays responsive even with many stored files.

### Changed
- **Save-to-library interaction** (`app/app.py`): Changed from a stateful checkbox to a one-shot button to reduce rerun churn and avoid UI race issues.

## [1.8.31] - 2025-12-19

### Added
- **RR Library Loader in sidebar** (`app/app.py`): New "📚 Load from Library" expander in the sidebar allows users to browse and load previously saved RR interval files from any user profile without re-uploading. Files are sorted by modification time (most recent first) and can be loaded directly into the analysis workspace with one click or loaded and analyzed immediately with "🚀 Load + Analyze".
- **Save uploaded files to library** (`app/app.py`): When files are uploaded via the sidebar and a user profile is active, a new "💾 Save X file(s) to library" button appears. Clicking it saves the uploaded RR files to the active user's profile for future analysis without needing to re-upload. Files are saved with timestamp prefixes if the original filename lacks a date.

### Fixed
- **Critical: HRV tab infinite loading fix** (`app/app.py`): Fixed bug where Time Series, Frequency, Nonlinear, and Spectrogram tabs would get stuck in infinite loading state (faded results) after uploading RR data. Root cause: `datasets` was not being cached after HRV analysis completed, so on each rerun the tabs received empty datasets. Added session_state caching (`_hrv_cached_datasets`, `_hrv_cached_windowed_df`) to persist processed data between reruns.
- **Library loader persistence fix** (`app/app.py`): Fixed bug where files loaded from the library would cause faded/stuck pages. Root cause: `st.session_state.pop("queued_rr_filepaths")` removed the queue after first processing, leaving `uploads` empty on subsequent reruns. Added `_persisted_uploads` session state to keep uploads alive across reruns.
- **datetime.time TypeError fix** (`app/app.py`): Fixed `TypeError: descriptor 'time' for 'datetime.datetime' objects doesn't apply to a 'int' object` by importing `time as dt_time` from datetime module and using `dt_time(20, 0)` instead of `datetime.time(20, 0)`.

## [1.8.30] - 2025-12-19

### Fixed
- **User Profile performance fix** (`app/user_profile_tab.py`): **Critical fix** - Replaced nested `st.tabs()` with selectbox-based navigation for profile sub-sections (Assessments, Clinical Profile, History, HRV, Readiness, Data, Sessions). Nested tabs in Streamlit render ALL content on every rerun, causing severe slowdowns and browser freezes in Edge/Chromium browsers. The new pattern only renders the selected section (lazy loading), dramatically improving performance.
- **SAFTE/USAF Crew Rest time input fix** (`app/app.py`): Fixed `TypeError: 'module' object is not callable` caused by `import time` shadowing `from datetime import time`. Changed `time(20, 0)` and `time(8, 0)` to `datetime.time(20, 0)` and `datetime.time(8, 0)` respectively.
- **SAFTE Auto-run stability improvements** (`app/app.py`): Reduced unnecessary operations by only saving tab settings when user explicitly clicks a button (not on every rerun). Added guard to prevent double-runs when auto-run button is clicked. Shows data source info after auto-run completes.

## [1.8.29] - 2025-12-19

### Fixed
- **Streamlit version stabilization** (`requirements.txt`): Pinned to **Streamlit 1.36.0**, the most stable version for this app. Testing showed:
  - 1.35.0: Tabs don't load properly - broken
  - **1.36.0: Most stable version - RECOMMENDED** (no SessionInfo/setIn errors)
  - 1.37.0+: Fragment changes cause SessionInfo/setIn errors
  - 1.40.2: Has cosmetic error popups but functionally works
  
  **Reinstall dependencies with `pip install --upgrade -r requirements.txt` to apply.**
  
- **Simplified error suppressor** (`app/app.py`): Removed aggressive client-side suppression that could interfere with legitimate UI elements. With Streamlit 1.36.0, the aggressive suppressor is no longer needed as the root cause errors are avoided.

### Documentation
- **Added Streamlit version requirements** (`docs/Manual.md`): Documented Streamlit 1.36.0 as the required stable version in the Troubleshooting section.

## [1.8.28] - 2025-12-18

### Added
- **Operational Performance predictor (HRV + SAFTE fusion)** (`app/profile_tools_engine.py`, `app/user_profile_tab.py`): Added a transparent, bounded **operational readiness score (0–100)** that fuses SAFTE effectiveness with HRV-derived recovery/autonomic markers, including **GO/CAUTION/NO‑GO** categories plus **best/worst 2‑hour task windows** and next‑12h alert windows.
- **Crew mission workspaces** (`app/app.py`, `app/user_database.py`, `app/user_data_manager.py`): Added a `crew/` folder with **Mission 1** and **Mission 2** workspaces and a sidebar mission selector. The app now stores the active mission’s **SQLite DB + backups** under `crew/<Mission>/db/` and per-subject files under `crew/<Mission>/subjects/` (legacy root DB/data are copied into Mission 1 on first use for safety).

### Fixed
- **Profile Tools RMSSD input default** (`app/user_profile_tab.py`): Corrected the RMSSD parameter widget default (previously incorrectly seeded from resting HR), improving out-of-the-box Profile Tools behavior.
- **ECharts HTML export template** (`app/echarts_component.py`): Escaped CSS/JS braces inside the Streamlit HTML f-string to prevent a runtime `NameError: name 'height' is not defined` when rendering charts.
- **ECharts charts not appearing** (`app/echarts_component.py`): Load the ECharts runtime from a Streamlit-served local static bundle (`.streamlit/static/echarts.min.js`) with CDN fallback and an in-iframe status/error message, preventing blank plots when CDN access is blocked.
- **USAF Crew Rest checker date/time defaults** (`app/app.py`): Fixed incorrect `datetime.date.today()` / `datetime.time(...)` usage caused by `from datetime import datetime` shadowing, which could crash the app before any plots rendered.

### Tests
- Added a regression test to ensure `render_echarts()` does not raise on CSS brace literals (`tests/test_echarts_component.py`).

### Documentation
- Updated `README.md` and `docs/Manual.md` to document the new Operational Performance tool and add neurovisceral integration references.

## [1.8.27] - 2025-12-18

### Added
- **Per-user SAFTE/FRMS default inputs** (`app/user_database.py`, `app/app.py`, `app/fatigue_integration.py`): Added persisted **fatigue profile defaults** (typical sleep window + duty window + weekend policy) so SAFTE and FRMS can auto-run using user-collected variables without manual re-entry.
- **SAFTE duty-weekend toggle** (`app/app.py`): FRMS “in-scope” duty mask can now optionally include weekends, improving schedule realism for shift/mission operations.

### Changed
- **Fatigue tab exports (ECharts-first)** (`app/app.py`): Removed the Plotly/Kaleido publication-export fallback and standardized on the built-in ECharts client-side export toolbar (PNG/SVG/HTML/spec JSON + Print/Save PDF).

### Tests
- Added regression coverage for fatigue profile defaults and assessment automation (`tests/test_fatigue_profile_defaults.py`).

### Documentation
- Synced `README.md`, `docs/Manual.md`, `WARP.md`, and `requirements.txt` version headers to **v1.8.27** and replaced placeholder clone URLs with the canonical repository (`strikerdlm/HRV`).

## [1.8.26] - 2025-12-18

### Added
- **Mission FRMS v2 prototype: Crew Risk Board** (`app/frms_v2.py`, `app/app.py`): Export tab now includes a **multi-profile** FRMS “crew risk board” that runs bounded SAFTE forecasts per selected active user and aggregates FRMS metrics/classifications into a roster view.
- **FRMS v2 exports + decision log** (`app/frms_v2.py`, `app/app.py`): Added **crew risk board CSV/JSON exports** and an exportable **decision log JSON** (decision owner + mitigations + embedded evidence payload) for audit trail workflows.

## [1.8.25] - 2025-12-18

### Added
- **Persisted study groups & assignments** (`app/user_database.py`, `app/app.py`): Export → Longitudinal cohort comparisons now supports **persisted** `study_groups` / `study_assignments` (Study ID + roster editor) instead of ad‑hoc control/intervention selectors.
- **Mixed-effects longitudinal inference** (`app/export_utils.py`, `app/app.py`): Optional **random-intercept mixed model** for Group × Time on Δ vs baseline (exports CSV + included in longitudinal Markdown report when enabled).
- **FRMS rule-based alerts** (`app/frms.py`, `app/app.py`): FRMS dashboard now emits a deterministic “why it triggered” alert list and includes alerts in the exported FRMS JSON payload.

### Dependencies
- Added `statsmodels` to `requirements.txt` for mixed-effects modeling.

## [1.8.24] - 2025-12-18

### Added
- **Longitudinal cohort comparisons (T0–T21)** (`app/app.py`, `app/export_utils.py`): Export tab now supports **control vs intervention** comparisons using **within-subject Δ vs baseline** per timepoint, with CSV + Markdown exports (includes effect sizes and FDR-adjusted p-values).

### Fixed
- **ECharts export controls** (`app/echarts_component.py`): All ECharts visuals now include built-in, client-side exports for **PNG (high-DPI)**, **SVG (vector)**, **HTML**, and **spec JSON**, plus a **Print/Save PDF** workflow (browser print).
- **Sleep tab compatibility import** (`app/echarts_component.py`): Restored the `st_echarts(...)` API used by `app/sleep_tab.py` so the sleep UI no longer degrades due to a missing import.

### Documentation
- Updated `README.md` and `docs/Manual.md` to reflect the new longitudinal cohort export workflow.

## [1.8.23] - 2025-12-17

### Added
- **Profile Tools Engine** (`app/profile_tools_engine.py`): New comprehensive calculation engine accessible per user profile:
  - **Recovery Score Calculator**: lnRMSSD-based recovery assessment with HRV, sleep, and resting HR components
  - **Training Readiness Assessment**: Multi-component readiness score with workout recommendations
  - **SAFTE Fatigue Prediction**: 24-hour cognitive effectiveness forecast using sleep homeostasis and circadian models
  - **Personalized HRV Analysis**: Age/sex-adjusted HRV interpretation with parasympathetic and stress indices
  - **Performance Forecast**: Hour-by-hour performance prediction with peak/low time identification
- **Profile Tools Engine UI** (`app/user_profile_tab.py`): New "🛠️ Profile Tools Engine" expander in Clinical Profile tab:
  - Tool selector for individual or combined analysis
  - Configurable input parameters (sleep, chronotype, HRV values)
  - Interactive results display with component breakdowns
  - 24-hour performance curve visualization
  - Markdown export functionality
  - Workout suggestions and clinical recommendations
- **Run All Tools Summary**: One-click execution of all profile tools with aggregated results display

### Fixed
- **Clinical Profile tab** (`app/user_profile_tab.py`): Removed nested Streamlit expanders that could crash the app with `StreamlitAPIException: Expanders may not be nested...` by converting inner panels (parameters/history/recommendations/subjective logs) to checkbox-controlled sections.
- **Wrist Monitoring history** (`app/user_profile_tab.py`): Fixed “latest available metric” selection so per-metric values truly come from the most recent non-null row in the latest-first table order (avoids index-label pitfalls when the DataFrame index is not reset or not unique).

### Scientific References (Profile Tools Engine)
- Plews DJ et al. (2013). J Appl Physiol - lnRMSSD for training monitoring
- Kiviniemi AM et al. (2007). Med Sci Sports Exerc - HRV-guided training
- Hursh SR et al. (2004). Aviat Space Environ Med - SAFTE fatigue model
- Borbély AA (1982). Hum Neurobiol - Two-process model of sleep regulation

## [1.8.22] - 2025-12-17

### Added
- **Personalized Health Metrics** (`app/personalized_computations.py`): New module providing user-specific physiological calculations tailored to individual profile data:
  - **Body fat estimation** using US Navy method (Hodgdon & Beckett 1984) with neck/waist/hip circumferences
  - **Sleep apnea risk** assessment using STOP-BANG score components (Chung et al. 2008)
  - **Age/sex-adjusted HRV reference ranges** from Nunan et al. (2010) and Shaffer & Ginsberg (2017)
  - **VO2max fitness classification** using ACSM Guidelines percentile tables
  - **Cardiovascular risk profile** assessment with multiple risk/protective factors
  - **Personalized hydration requirements** based on NASA-STD-3001 (32 mL/kg body weight)
- **Personalized Health Metrics UI** (`app/user_profile_tab.py`): New expander panel in Clinical Profile tab displaying:
  - BMI with WHO classification
  - Body fat percentage with ACSM category (Athletes/Fitness/Average/Obese)
  - STOP-BANG sleep apnea risk score with recommendations
  - Personalized HRV reference ranges table by age group
  - Fitness classification with percentile estimate
  - Cardiovascular risk factors and protective factors
  - Hydration requirements with glasses/liters display
  - One-click markdown summary export
- **Personalized HRV Interpretation** (`app/hrv_core.py`): New `interpret_hrv_personalized()` function that:
  - Interprets HRV metrics against age/sex-adjusted norms
  - Returns status (very_low/low/normal/high/very_high) per metric
  - Provides percentile estimate and z-score for each metric
  - Generates overall autonomic assessment with recommendations
- **Enhanced User Context** (`app/user_profile_tab.py`): `get_active_user_context()` now includes:
  - Body composition data (neck_cm, waist_cm, hip_cm, body_fat_pct, lean_mass_kg)
  - Personalized HRV norms for the user's age group
  - All personalized metrics calculations
- **Diego Malpica Profile Setup** (`app/setup_diego_profile.py`): Utility script to initialize complete user profile with:
  - Biometrics (weight 91 kg, height 173 cm)
  - Body composition (neck 41 cm, waist 94 cm, hip 102 cm)
  - Clinical assessment scales (ESS, PSQI, KSS, Samn-Perelli)
  - VO2max and fitness data

### Changed
- **User Profile Tab** imports and integrates the personalized_computations module with graceful fallback
- **Clinical Profile** section now includes "Personalized Health Metrics" expander after Exploration Medical Analytics
- **Active User Context** propagates body composition and personalized metrics to all tabs

### Documentation
- Updated `WARP.md` roadmap with Phase 5: Personalized User Profile Features (marked complete)
- Updated `README.md` features table with personalized health metrics and HRV interpretation
- Updated `docs/Manual.md` with comprehensive Personalized Health Metrics guide including:
  - US Navy body fat formula and classification tables
  - STOP-BANG score interpretation
  - Age-adjusted HRV reference ranges
  - VO2max fitness classification by age/sex
  - Cardiovascular risk factors
  - Hydration calculation methodology

### Scientific References
- Hodgdon JA, Beckett MB (1984). Naval Health Research Center - Body Fat Prediction
- Chung F et al. (2008). Anesthesiology - STOP-BANG Questionnaire
- Nunan D et al. (2010). PACE - Short-term HRV Normal Values
- Shaffer F, Ginsberg JP (2017). Front Public Health - HRV Metrics and Norms
- ACSM Guidelines for Exercise Testing and Prescription (11th Ed)
- NASA-STD-3001 Water Requirements

## [1.8.21] - 2025-12-14

### Added
- **Cohort / Group Summaries export** (`app/app.py`, `app/export_utils.py`): the Export tab now supports cohort-level exports for multi-user sessions, including a per-subject “latest snapshot” roster (HRV + clinical scales + exploration medical record fields when present) plus cohort descriptive statistics. CSV and Markdown downloads are provided.

### Tests
- Added regression coverage for cohort export utilities (`tests/test_cohort_export_utils.py`).

### Documentation
- Updated `WARP.md`, `README.md`, and `docs/Manual.md` to mark Group Summaries complete and describe the new cohort export workflow.

## [Unreleased]

### Added
- **FRMS + USAF crew rest dashboard (SAFTE tab)** (`app/app.py`, `app/frms.py`): The SAFTE/Fatigue tab now includes an ICAO-aligned FRMS summary (WOCL exposure + threshold-based risk matrix) and a USAF crew rest compliance checker (AFMAN 11-202V3 baseline), plus publication-grade plot exports (Plotly fallback: HTML/PNG/SVG/PDF).
- **Doctoral thesis proposal** (`docs/PhD.md`): Literature-backed dissertation concept for pilot/commander readiness classification, including multimodal predictors (sleep/fatigue/circadian/HRV/objective vigilance), countermeasure governance, and a 5×5 operational risk matrix for mission go/no-go decision support.
- **Per-user HRV analysis artifact cache in SQLite** (`app/user_database.py`, `app/app.py`): reusable HRV analysis payloads are now persisted per user and keyed by **file hash + analysis settings hash**, enabling cross-session reuse without recomputation when inputs and settings match.
- **Per-user GPT-5.2 export persistence** (`app/user_database.py`, `app/app.py`): GPT-5.2 high-reasoning interpretation markdown (and citation metadata) is now stored per user + payload hash so exports can include prior interpretations even when GPT is disabled/offline. A **combined HRV + GPT** markdown download is provided in the Export tab.
- **Longitudinal timepoints (T0–T21)** (`app/user_database.py`, `app/user_profile_tab.py`, `app/app.py`): Added a `measurement_timepoints` table and UI controls to tag new HRV measurements and clinical assessments to a study timepoint so baseline/Δ workflows can be built deterministically.
- **Baseline/Δ analytics (T0–T21)** (`app/user_database.py`, `app/user_profile_tab.py`): The **User Profile → HRV → HRV Measurement History** panel now includes a baseline/Δ table grouped by timepoint label (T0…T21), computing per-timepoint aggregates and deltas vs T0.
- **Profile HRV performance/recovery plots** (`app/user_profile_tab.py`): The **User Profile → HRV → HRV Measurement History** panel now includes additional trend visualizations (lnRMSSD, heart-rate, autonomic indices, and quality) plus optional HRV↔Garmin daily metric relationship plots when wearable history is present.
- **Profile RR Library → Analysis Workspace** (`app/user_profile_tab.py`, `app/app.py`): Added a **Stored RR Library** loader inside **User Profile → HRV** so you can load already-saved RR recordings into the main analysis workspace (with an optional “Load + run analysis” shortcut) without re-uploading files.
- **Profile Readiness & Recovery** (`app/user_profile_tab.py`): Added a **Readiness** sub-tab inside User Profile that computes readiness from stored parasympathetic-index history and renders HRV metric gauges in the same ECharts style as the main gauges tab.
- **Profile body composition persistence** (`app/user_profile_tab.py`, `app/user_database.py`): The **Body Composition** panel now saves measurements (body fat, lean/muscle mass, circumferences) to the database and renders trends/history per profile.
- **Profile exploration medicine auto-enrichment** (`app/user_profile_tab.py`): The **Exploration Medical Record** can now align records to a log date and auto-compute (a) **space-weather alert level** from NOAA Kp + >10 MeV proton flux (G/S scales) and (b) a **baseline cumulative radiation dose estimate** from mission profile/habitat + EVA hours (with NASA limit guidance). Stress and sleep fields can seed from objective HRV and Garmin daily metrics when available.
- **Garmin export JSON ingest (Vivosmart 5)** (`app/garmin_import.py`, `app/user_profile_tab.py`): The **User Profile → Data → Wrist Monitoring (Vivosmart 5)** uploader now accepts unzipped Garmin export `.json` files, including:
  - `UDSFile_*.json` daily summaries (steps, distance, active calories, stress, SpO₂, respiration, body battery)
  - `*_sleepData.json` (sleep stages + scores; supports the newer nested `sleepScores` schema)

### Changed
- **Fatigue zone thresholds** (`app/fatigue_integration.py`, `app/app.py`): Updated operational effectiveness zones to SAFTE/FAST-style thresholds and clarified boundary labels (≥90, >77–<90, >70–≤77, ≤70) for safer interpretation.
- **Covariate adjustment defaults** (`app/app.py`): age/sex/BMI/activity inputs now default to the active user profile context when available (with a “Use active profile defaults” toggle), ensuring profile-aware HRV interpretation is user-scoped.
- **Performance** (`app/app.py`, `app/user_profile_tab.py`, `app/user_database.py`, `app/i18n.py`): Bounded Streamlit caches (heavy HRV compute, space-weather fetches, profile/history loaders, i18n lookups) with explicit TTL + `max_entries` to keep memory usage stable during long sessions.
- **Readiness tab** (`app/app.py`): Readiness scoring now prefers the user’s **stored HRV history** in the database (parasympathetic index) so it can include more sessions than the currently loaded uploads.
- **SAFTE/Fatigue inputs** (`app/app.py`): Sleep duration and sleep quality can now auto-seed from the latest stored Garmin daily metrics (one-shot per new Garmin day), improving per-user workflow when wearable sleep data is available.

### Fixed
- **Garmin gauge thresholds** (`app/gauge_builder.py`): Fixed accidental constant shadowing and corrected `distance_km`/Garmin wellness thresholds so the intended km/kcal/stress/SpO₂ ranges are consistently applied.
- **User Profile** (`app/user_profile_tab.py`): Fixed Streamlit duplicate form-key crash by rendering the longitudinal timepoint selector once above the profile sub-tabs (instead of inside multiple tab panels).
- **User Profile HRV history refresh** (`app/user_profile_tab.py`): Added a **Regenerate plots** control in **HRV Measurement History** to force-refresh charts after new uploads/analysis runs (clears Streamlit data caches and reruns the HRV history renderer).
- **Navigation after HRV analysis** (`app/app.py`): Removed an early return that could trap the UI on an “already completed” message after analysis; the full tab navigation now renders and the action button switches to **Recompute HRV Analysis** when appropriate.
- **Logging** (`app/logging_config.py`): Suppressed benign Streamlit/Tornado `WebSocketClosedError` “Task exception was never retrieved” noise so `logs/errors.log` stays actionable.
- **Device imports** (`app/app.py`): ActiGraph and Somfit sidebar imports now run only when clicking an explicit **Import** button (prevents expensive re-processing on every rerun) and always clean up temporary files, improving UI smoothness and reliability.
- **Garmin daily metrics upsert** (`app/user_database.py`): Partial imports no longer wipe previously stored non-null fields (upsert now preserves existing values when the new value is NULL).
- **Wrist Monitoring stats/trends** (`app/user_profile_tab.py`): The History tab now loads a configurable number of stored Garmin days and renders trends + summary statistics across all saved daily metrics (not just a subset), and the “View all daily metrics” panel now shows the full loaded table (not just 10 rows).

### Tests
- Added regression coverage for timepoint persistence and database backups (`tests/test_longitudinal_timepoints.py`).
- Added regression coverage for tz-aware datetime handling in SWPC solar flux retrieval (`tests/test_space_weather_alignment.py`).

### Documentation
- Updated `README.md`, `docs/Manual.md`, and `docs/index.md` to reflect the current roadmap status (plot governance next), corrected the docs landing page away from the legacy notebook instructions, and added the verifiable PROOF-AF DOI citation.
- Updated `WARP.md` to match the current conda environment name (`hrv-py312`) and roadmap status.

## [1.8.20] - 2025-12-12

### Changed
- **OpenAI models**: Updated all OpenAI *language-model* calls to use `gpt-5.2` with high reasoning effort (`reasoning.effort="high"`) for interpretation, Agents SDK personas, and the SpaceWeatherLive extraction fallback (`app/gpt_interpretation.py`, `app/agent_runtime.py`, `app/spaceweather_openai_fallback.py`, `app/app.py`).

### Fixed
- **Fatigue tab auto-run** (`app/app.py`, `app/fatigue_integration.py`): the 5-day “Auto-run” button now matches the actual data priority (wrist → clinical → Garmin Connect) and attempts Garmin Connect only when credentials are configured, avoiding spurious error logs when `GARMIN_EMAIL`/`GARMIN_PASSWORD` are unset.

## [1.8.19] - 2025-12-11

### Fixed
- **Space Weather correlations** (`app/app.py`): the “Include weather covariates (Bogotá)” toggle now performs partial Pearson correlations that regress out ERA5 temperature, humidity, pressure, wind, precipitation, and cloud cover before computing HRV↔space-weather statistics. Previously the checkbox fetched data but never influenced the coefficients, leaving meteorological confounds in place.

### Tests
- Added regression tests to ensure (a) the new partial-correlation path actually dampens shared-weather artefacts and (b) the assessment-driven SAFTE automation keeps prioritizing wrist monitoring data ahead of clinical fallbacks (`tests/test_space_weather_alignment.py`, `tests/test_new_modules.py`).

### Documentation
- `docs/Manual.md`: documented how enabling weather covariates swaps the correlation engine into partial-r mode so analysts know when geomagnetic findings already control for local meteorology.

## [1.8.18] - 2025-12-11

### Added
- **Assessment-aware SAFTE auto-forecast** (`app/fatigue_integration.py`, `app/app.py`): the 5-day automation now prioritizes wrist monitoring data from the Assessment tab, falls back to subjective clinical sleep quality if wrist data is absent, and only then attempts a Garmin Connect fetch (`GARMIN_EMAIL`/`GARMIN_PASSWORD`). The source used and summary are displayed for traceability.

### Documentation
- README.md and docs/Manual.md now describe the Garmin auto-run flow and the `.env` variables it depends on.

## [1.8.17] - 2025-12-11

### Added
- **Agent telemetry logging** (`app/agent_logging.py`, `app/agent_runtime.py`, `app/agent_insights.py`, `app/gpt_interpretation.py`, `app/spaceweather_openai_fallback.py`): every OpenAI persona now records request payloads, doctor-level answers, and citation metadata to the rotating log/audit trail so flight surgeons can reconstruct each recommendation.
- **Markdown + audio exports** (`app/agent_insights.py`, `app/app.py`, `app/agent_audio.py`): metric explanations and GPT-5 interpretations can be downloaded as publication-grade markdown and rendered to discrete tts-hd audio clips for hands-free playback on-console.
- **TTS helper** (`app/agent_audio.py`): hardened HTTPS client for OpenAI `tts-1-hd` endpoints with configurable voice/model plus audit logging of synthesized clips.

### Changed
- **Agents SDK enforcement** (`app/agent_runtime.py`, `app/gpt_interpretation.py`): Personas now require `web_search` citations, append `## Sources` to every report, and run with high-effort reasoning so exported markdown stays doctorate-level and evidence based.
- **Metrics tab UI** (`app/app.py`): Agent appendix preview plus download/audio controls live alongside the explainability table, ensuring the reporting pipeline stays within a single workflow.

### Fixed
- Metric explainability exports previously lacked a consolidated appendix, making downstream reporting manual; the new markdown assembler guarantees deterministic references even without API keys.

## [1.8.16] - 2025-12-11

### Added
- **Metric Explainability Specialist** (`app/agent_runtime.py`, `app/agent_insights.py`, `app/app.py`): GPT-5.2 high-reasoning persona paired with `code_interpreter` plus a deterministic fallback panel inside the Metrics tab so every SDNN, RMSSD, pNN50, LF/HF, HF power, and mean HR value now includes a citation-backed explanation.
- **Unit tests** (`tests/test_agent_insights.py`): Coverage for the new agent insight manager to ensure per-metric classifications stay synchronized with Task Force (1996) and Shaffer & Ginsberg (2017) ranges.

### Changed
- Metrics tab now hashes its dataset snapshot and auto-refreshes the explanation panel when values change, ensuring users always read up-to-date interpretations before invoking the agent.

### Fixed
- Addressed the missing per-metric guidance in the Metrics tab by adding a deterministic explainer so users can always read contextual analysis even when the Agents SDK is offline or API keys are absent.

### Documentation
- README.md / docs/Manual.md: Documented the Metric Explainability Specialist persona, the new Metrics-tab panel, and how it ties into the Agents SDK rollout.

## [1.8.15] - 2025-12-10

### Added
- Sleep Analysis sidebar login and device import controls now run inside debounced forms with explicit submit buttons, reducing unnecessary reruns and completing the roadmap's batch submission objective for this tab.
- `app/agent_runtime.py`: structured OpenAI Agents SDK scaffold (tool belt, MCP servers, and personas) plus an About-tab expander so flight surgeons can audit forthcoming autonomous copilots.

### Changed
- Welcome header, sidebar branding, and the About tab now surface release date + git branch/commit metadata derived from `CHANGELOG.md`, ensuring the UI always mirrors the current build without restarting Streamlit.
- README.md and docs/Manual.md highlight the new release-awareness chips and link directly to the Agents SDK blueprint that is now backed by code.

### Fixed
- Garmin/ActiGraph/Somfit uploads no longer reprocess the same file on every rerun; imports execute only when the user presses the corresponding button and the uploader state is cleared afterwards to prevent duplicate data entries.
- `version_info.py` reloads when `CHANGELOG.md` changes instead of relying on a one-time cache, so Streamlit reruns instantly pick up new versions/badges.

### Documentation
- README.md: Added v1.8.15 highlights plus a status note that the agent blueprint now lives in code.
- docs/Manual.md: Updated version banner, release-awareness note, and a new section describing the agent runtime roadmap.

## [1.8.14] - 2025-12-10

### Added
- **📂 Load RR files** controls inside the Time, Frequency, and Nonlinear tabs so analysts can explicitly load a subset of uploaded RR recordings per visualization without touching the sidebar cache.
- Apache ECharts timelines across the User Profile (assessment history, Garmin wellness, HRV history, Exploration Medical analytics) for consistent, publication-ready styling.
- Unit tests covering the new space-weather alignment helpers.

### Changed
- Space weather correlations now resample NOAA/DONKI predictors onto the exact HRV window timestamps (bounded interpolation, no nearest-neighbor drift), matching heliobiology best practices.
- Weather covariates and the feature-matrix builder reuse the same alignment helper, ensuring every predictor/HRV pair references the same instant before statistics are computed.

### Fixed
- Prevented mismatched timestamps from contaminating Kp/NOAA correlation coefficients; empty joins now warn users instead of quietly reusing stale data.

## [1.8.13] - 2025-12-10

### Added
- Dataset info headers in Time Series, Frequency, Nonlinear, Spectrogram, and Gauges tabs showing file names, recording dates, durations, and beat counts for clearer analysis context.

### Changed
- Default analysis settings now enable Frequency plots, Poincaré, Spectrogram, Gauges, and ML-assisted deviation clustering for a richer out-of-the-box experience.

### Fixed
- Fixed pandas `MergeError` when reusing cached results that already contain `sdann_5min`/`sdnnidx_5min` columns; duplicate columns are dropped before merge.

## [1.8.12] - 2025-12-10

### Added
- Data tab tools to convert Garmin FIT → CSV inside the User Profile and download the result.
- CSV ingestion in the Data tab: upload Garmin CSV files to store them under the active profile.
- FIT → CSV conversion uses bounded parsing (fitparse) with per-profile storage of both raw FIT and generated CSV.

### Changed
- Data tab now surfaces FIT/CSV utilities before Garmin ingest for a streamlined workflow.

## [1.8.11] - 2025-12-10

### Added
- Optional reuse of cached HRV results by file hash + analysis settings with a sidebar toggle; warns when settings differ so you can recompute.
- Raw RR uploads now persist immediately to `data/{user}/rr_intervals` for the active profile (sidebar and profile uploads) so tracings are never lost between runs.

### Changed
- Analysis settings persistence now records covariate inputs (age/sex/BMI/exercise) and validates them before reusing cached results.
- Profile-tab RR uploads now set the active profile automatically to prevent cross-user mixing during analysis.

## [1.8.10] - 2025-12-10

### Added
- Per-user RR upload persistence and duplicate detection: RR uploads now store raw files and computed HRV results keyed by file hash per active profile, with sidebar warnings when a file was already analyzed.
- Profile-tab RR uploads: users can upload RR files directly inside the User Profile tab; files are saved to their data folder and queued for analysis without using the sidebar.
- Active profile indicator: a prominent light-bulb banner shows which profile is currently driving HRV analyses to prevent cross-user mix-ups.

### Changed
- HRV measurements table now tracks `source_file`, `file_hash`, `recording_start_utc`, `analysis_settings_json`, and `created_at` to bind analyses to uploads and settings.

---

## [1.8.9] - 2025-12-10

### Documentation
- **README.md**: Added the OpenAI Agents SDK integration blueprint outlining MCP bridges, toolchain activation (code interpreter, file/web search, Wolfram Alpha, E2B), and aerospace medicine use cases for autonomous agents.

---

## [1.8.8] - 2025-12-09

### Fixed
- **Garmin FIT wellness monitoring data** (`app/garmin_import.py`): 
  - Now properly extracts heart rate, stress, SpO2, respiration, and body battery from `monitoring` message types in FIT files (24/7 wellness tracking)
  - Previously only captured activity metrics (steps/calories); now captures ALL physiological data from monitoring messages
  - Added sleep message parsing (`sleep` and `sleep_level` message types)
  - Fixed data validation: returns wellness data even when RR intervals are absent (Vivosmart 5 optical sensor limitation)
  - **Fixed daily aggregation**: Steps, distance, and calories now use `max()` instead of sum for cumulative counters (fixes inflated values)
  - Added comprehensive logging to track extraction success for each metric type and daily summaries
  - Fixed undefined variable error (`fit_count`) in ZIP parsing logging
- **Garmin ZIP parsing** (`app/garmin_import.py`): 
  - ZIPs containing only embedded FIT files (no wellness JSON) now parse those FIT files properly
  - Batch processing of multiple FIT files inside ZIP with merged dataframes
- **Batch upload support** (`app/device_imports.py`): Sidebar Garmin uploader now accepts multiple FIT/ZIP files and processes all wellness metrics
- **Gauge aesthetics** (`app/gauge_builder.py`): Reduced ring width from 20px to 8px for cleaner, narrower gauge appearance

### Changed
- **User guidance** (`app/user_profile_tab.py`, `app/device_imports.py`): Added help sections explaining how to request complete wellness export from Garmin Connect to get sleep, stress, body battery, SpO₂, and respiration JSON files (not available in individual activity FIT exports)
- **Gauge aesthetics** (`app/gauge_builder.py`, `app/user_profile_tab.py`):
  - Added proper thresholds for all Garmin wellness metrics (steps, distance, calories, SpO2, stress, body battery, respiration, sleep)
  - Organized gauges into logical sections: Activity & Movement, Heart Rate & Stress, Sleep & Recovery, Respiration & SpO₂, Body Battery
  - Added prominent display of latest day values with thousand separators for large numbers
  - Improved layout with consistent two-ring gauge design matching the rest of the app

---

## [1.8.7] - 2025-12-09

### Added
- **Batch Garmin wrist uploads** (`app/device_imports.py`): Sidebar Garmin import now accepts multiple FIT/ZIP files at once, captures wellness metrics (steps, distance, sleep score/efficiency/duration, SpO₂, respiration awake/sleep, stress, calories, body battery) and queues them for Wrist Monitoring history.
- **FIT parser dependency**: Added `fitparse` to `requirements.txt` for Vivosmart 5 FIT ingestion.

### Changed
- Wrist monitoring automatically ingests pending sidebar metrics into the user’s history tab after batch uploads.

---

## [1.8.6] - 2025-12-09

### Added
- **Garmin Vivosmart 5 clinical ingest** (`app/garmin_import.py`, `app/user_profile_tab.py`, `app/user_database.py`, `app/device_imports.py`):
  - FIT and wellness ZIP parsing now captures steps, distance, calories, sleep score/efficiency/duration, stress, SpO₂, respiration (awake/sleep), and body battery charge/drain.
  - New `garmin_daily_metrics` table with upsert support to store per-day wellness summaries tied to each user profile.
  - User Profile → Data tab adds a Garmin Vivosmart 5 uploader; History tab shows double-ring ECharts gauges and recent daily metrics.
  - Sidebar Garmin import now accepts `.fit` for RR extraction from Vivosmart 5 FIT files.

### Documentation
- **README.md / docs/Manual.md**: Added guidance for the Vivosmart 5 clinical ingest workflow, thresholds (respiration 10–17 rpm), and the new gauges available in the Clinical Profile history.

## [1.8.5] - 2025-12-06

### Added
- **Polar AccessLink Automation** (`app/polar_accesslink.py`): Complete OAuth token management and VO2max sync
  - `PolarAccessLinkClient` class for per-user credential management
  - Secure token storage with XOR encryption (obfuscation for local SQLite)
  - VO2max history tracking with source attribution (Polar, manual, etc.)
  - Automatic sync with duplicate detection (avoids redundant entries)
  - Fitness class determination based on VO2max values
- **Database schema updates** (`app/user_database.py`):
  - `polar_credentials` table for persisting OAuth tokens per user
  - `vo2max_history` table for longitudinal VO2max tracking
  - `PolarCredentials` and `VO2maxEntry` dataclasses
  - Database methods: `save_polar_credentials()`, `get_polar_credentials()`, `delete_polar_credentials()`
  - Database methods: `save_vo2max_entry()`, `get_vo2max_history()`, `get_latest_vo2max()`, `get_vo2max_dataframe()`
- **Unit tests** (`tests/test_polar_accesslink.py`): 24 comprehensive tests covering:
  - Token encryption/decryption round-trips
  - Database CRUD operations for credentials and VO2max history
  - PolarAccessLinkClient lifecycle and sync operations
  - Mocked API response handling
- **Exploration Medical Analytics Dashboard** (`app/user_profile_tab.py`):
  - Radiation gauge tracks cumulative mSv vs NASA 1000 mSv guideline with daily accumulation rate
  - EVA workload cards summarize 72 h EVA hours, peaks, and days since last EVA alongside clearance histograms
  - Stress panel surfaces rolling averages for confinement stress, workload rating, and sleep duration
  - Frequency tables tally the most common acute symptoms and behavioral flags straight from ExMC logs
- **Unit tests** (`tests/test_new_modules.py`): Added coverage for the radiation-rate computation and frequency aggregation helper powering the dashboard

### Changed
- **NASA Nutrition Calculator** (`app/user_profile_tab.py`):
  - VO2max section now uses `PolarAccessLinkClient` for persistent sync
  - Added "💾 Save Manual Entry" button to record manual VO2max values
  - VO2max history expander shows recent entries with source and fitness class
  - Improved source attribution ("Polar AccessLink sync", "History", "Manual entry")
- **Import structure** (`app/polar_accesslink.py`): Fallback imports for both `app.` prefix and direct module imports

### Fixed
- **Token encryption** (`app/polar_accesslink.py`): `os.getlogin()` now falls back to environment variables when running in non-TTY environments

### Documentation
- **README.md / docs/Manual.md / WARP.md**: Documented the Exploration Medical Analytics dashboard, updated the roadmap status, and highlighted the new radiation/EVA/stress cards.

---

## [1.8.4] - 2025-12-05

### Fixed
- **FutureWarning** (`app/app.py`): Fixed deprecated `.fillna()` downcasting on artifact_flag column using explicit `boolean` dtype conversion.
- **CPU name detection** (`app/cpu_optimization.py`): Fixed `[WinError 2]` on modern Windows by reading CPU name from registry instead of deprecated `wmic` command.

---

## [1.8.3] - 2025-12-05

### Added
- **PANAS Scale (Positive and Negative Affect Schedule)** (`app/user_profile_tab.py`, `app/i18n.py`):
  - Full 20-item PANAS assessment (Watson, Clark & Tellegen, 1988)
  - Validated English and Spanish (Sandín et al., 1999) translations
  - Interactive select sliders for all 10 PA and 10 NA items
  - Real-time ECharts gauge visualizations for PA and NA scores
  - Normative interpretation thresholds (Crawford & Henry, 2004)
  - Integration with clinical assessment history and trends

### Changed
- **User Profile performance** (`app/user_profile_tab.py`): Assessment history now uses `@st.cache_data` with TTL for faster repeated loads after login.
- **ESS slider optimization** (`app/user_profile_tab.py`): Epworth Sleepiness Scale uses `st.select_slider` with pre-initialized session state for smoother interaction.
- **Medical history summary** (`app/user_profile_tab.py`): Summary now pulls latest exploration medical record from database, showing mission/EVA/radiation at a glance.
- **Assessment history** (`app/user_profile_tab.py`): Now displays PANAS PA/NA averages and trends alongside fatigue scales.
- **Exploration Medical Record (ExMC/EIMO)** (`app/user_profile_tab.py`): Expanded form per NASA Exploration Medical Capability and Earth-Independent Medical Operations frameworks:
  - Mission profiles: LEO through Mars Surface with EIMO autonomy levels
  - Radiation & space weather: cumulative dose, GCR concern flag
  - Health status: HRP risk categories, expanded acute symptoms, workload rating
  - Countermeasures: sleep quality, exercise modality, caloric intake
  - Medical logistics: resupply days tracking

### Fixed
- **Schema migration resilience** (`app/user_profile_tab.py`): All selectbox and multiselect widgets now gracefully handle stale values from database records when option lists change. Prevents `StreamlitAPIException` when stored defaults no longer match current options; logs migration events for debugging.
- **Database schema** (`app/user_database.py`): Added `panas_positive_affect` and `panas_negative_affect` columns to clinical_scales table with automatic migration.

### Removed
- **Deprecated MIST reference** (`app/user_profile_tab.py`): Removed outdated NASA MIST URL; form now cites ExMC/EIMO peer-reviewed sources.

### Documentation
- **PANAS documentation** (`docs/Manual.md`): Complete guide including interpretation tables, clinical significance, and scientific references.
- **Roadmap** (`docs/Manual.md`): Added ExMC Clinical Assessment milestone (Q4 2025 in progress) with planned Q1 2026 enhancements (CDSS, probabilistic risk, XR telepresence).

---

## [1.8.2] - 2025-12-05

### Changed
- **Always-on space weather pipelines** (`app/app.py`, `app/noaa_space.py`): Space Weather, NOAA Space, and impact predictions now auto-load on tab entry even with no RR uploads, using cache-first fetches and stale-cache fallback for Kp/F10.7 and NOAA feeds when connectivity drops.
- **Resilience and logging** (`app/app.py`, `app/noaa_space.py`): SWPC/NOAA fetch failures now log centrally and surface warnings while keeping prior cached data available.

### Fixed
- **NOAA auto-load retry storm** (`app/app.py`): Added auto-loading/attempt guards so NOAA auto-fetch runs once per session and won't hammer the APIs when feeds fail (empty bundles no longer trigger repeated retries).

### Documentation
- Updated **README.md** and **docs/Manual.md** to explain automatic loading and offline-friendly cache behavior for space weather features.

---

## [1.8.1] - 2025-12-05

### Added
- **Cross-tab result broker** (`app/ui_state_manager.py`): New per-user, per-tab broker shares small summaries safely across Streamlit reruns.
- **Circadian → SAFTE sync** (`app/circadian_tab.py`, `app/app.py`): Circadian tab publishes DLMO/CBT/ESRI plus light windows; SAFTE tab can apply the latest circadian sleep window and chronotype with one click.
- **Unit tests** (`tests/test_ui_state_manager.py`): Coverage for the broker’s publish/get/eviction behavior.

### Changed
- **Documentation** (`README.md`, `docs/Manual.md`, `WARP.md`): Roadmap now marks cross-tab correlation complete and explains the new circadian-to-fatigue bridge.

---

## [1.8.0] - 2025-12-05

### Changed
- **Portable database location** (`app/user_database.py`): Database now lives alongside the app (`hrv_users.db` in the project folder) for easy copying between machines.
- **Explicit HRV run control** (`app/app.py`): HRV analysis only runs after clicking **Run HRV Analysis**; uploads alone no longer trigger automatic computation.
- **Docs and version** (`README.md`, `docs/Manual.md`, `WARP.md`, `app/version_info.py`): Version bumped to 1.8.0 and navigation notes updated for the new workflow.

---

## [1.7.8] - 2025-12-05

### Changed
- **Tab layout** (`app/app.py`): Science tab moved next to References; About, Space Weather, and NOAA tabs remain fully active/visible.
- **Documentation** (`README.md`, `docs/Manual.md`, `WARP.md`): Updated version badges and navigation notes to match the new layout and visibility rules.
- **Version sync** (`app/version_info.py`): Default version updated to 1.7.8 to keep About and headers consistent with the changelog.

---

## [1.7.9] - 2025-12-05

### Changed
- **Profile load performance** (`app/user_database.py`, `app/user_profile_tab.py`, `app/user_management_ui.py`): HRV history queries now fetch only recent records without RR JSON payloads by default, reducing profile load times for large datasets.
- **Version sync** (`app/version_info.py`): Updated default version to align UI badges and About with this release.

---

## [1.7.7] - 2025-12-05

### Added
- **Tab-specific settings persistence** (`app/ui_state_manager.py`, `app/app.py`, `app/circadian_tab.py`): Circadian and SAFTE tabs now remember per-user configurations for the current session, rehydrating sliders and selectors when switching users or rerunning the app.

### Changed
- **Welcome/About auto-versioning** (`app/version_info.py` consumers): UI badges now source version numbers directly from the latest changelog entry to keep the welcome header and About tab synchronized with releases.

---

## [1.7.6] - 2025-12-05

### Added
- **Active user context bridge** (`app/app.py`, `app/circadian_tab.py`): The app now fetches the active astronaut’s demographics, chronotype, and latest exploration medical record once per rerun and shares it across mission tabs.
- **Profile-aware scenario sync** (`app/circadian_tab.py`): New **Align with active profile** button maps user chronotype/mission profile to light schedules, shift cadence, and model presets.

### Changed
- **SAFTE/Fatigue tab** (`app/app.py`): Inputs auto-populate age, sex, chronotype offset, sleep debt, and work cadence from the active profile. A sync button lets operators refresh values after editing NASA logs.
- **Documentation** (`README.md`, `docs/Manual.md`): Added guidance for the new profile sync workflows and updated the roadmap to mark the feature complete.

### Fixed
- **Pytest warning cleanup** (`app/statistical_analysis.py`, `tests/test_comprehensive_modules.py`): Renamed `TestType` to `StatisticalTestType` so pytest no longer attempts to collect it as a test class.

---

## [1.7.5] - 2025-12-05

### Added
- **Circadian scenario builder** (`app/circadian_tab.py`): Moved every configuration control from the global sidebar into the Circadian tab, added a batched form with an explicit **Apply scenario** button, and introduced a preset vault (up to five saved schedules per session).

### Changed
- **Circadian documentation** (`README.md`, `docs/Manual.md`, `WARP.md`): Roadmap now marks the relocation task as complete, manuals describe the new workflow, and Phase 3 lists SAFTE settings as the next configuration refactor target.

---

## [1.7.4] - 2025-12-05

### Added
- **Clinical assessment preview panel** (`app/user_profile_tab.py`): New Preview button summarizes ESS, KSS, Samn-Perelli, and VAS scores plus context before saving so crews can validate entries without hitting the database.

### Changed
- **Clinical assessment forms batched**: Epworth, Samn-Perelli, Karolinska, and VAS controls now live inside Streamlit forms. Slider adjustments no longer trigger full reruns, which keeps the Clinical Profile tab responsive even on lower-tier CPUs.
- **Debounced submissions**: A shared 0.8 s debounce guard prevents duplicate clinical assessments and exploration medical record entries when users double-click or multiple tabs submit simultaneously.

---

## [1.7.3] - 2025-12-04

### Added
- **HRV Results Caching System** (`app/hrv_cache.py`): Multi-layer caching for major performance gains
  - Hash-based cache keys using data fingerprints (size, first/last values, statistics)
  - Session state caching survives Streamlit reruns without recomputation
  - Automatic cache invalidation when data or settings change
  - `ComputationState` tracking to skip redundant computations entirely
- **Parallel Windowed Analysis**: Automatic parallel processing for multiple datasets
  - Uses ThreadPoolExecutor when multiple datasets are uploaded
  - Automatically enabled for systems with 4+ CPU cores
  - 2-4x faster when processing multiple datasets simultaneously
  - Falls back to sequential processing for single datasets or low-core systems
- **Process Priority Optimization**: Sets high priority for Python process on startup
  - Uses psutil to boost process priority (if available)
  - Windows: HIGH_PRIORITY_CLASS
  - Linux/Mac: nice value -10 (requires appropriate permissions)
  - 5-15% overall performance improvement
- **Performance Optimization Guide**: Comprehensive documentation
  - `docs/PERFORMANCE_OPTIMIZATION.md`: Technical deep-dive
  - `PERFORMANCE_OPTIONS.md`: Quick reference for users
  - Installation instructions for Numba and psutil
  - System-level optimization recommendations

### Changed
- **Upload Section Performance**: Files now cached in session state with hash-based invalidation
  - Files only re-parsed when content actually changes (hash comparison)
  - Eliminates repeated file parsing on tab switches and UI interactions
  - Automatic cleanup of stale cache entries when files are removed
- **Cleaning Performance**: `clean_rr_intervals()` results now cached
  - Cache key combines data hash + settings hash
  - Cache hit skips entire cleaning computation loop
  - Progress indicators show "Loading cached results..." when using cache
- **Computation State Tracking**: Smart detection of when recomputation is needed
  - Tracks uploaded files hash + analysis settings hash
  - Skips cleaning/windowed/comprehensive computations when data unchanged
  - Reduces redundant work on every Streamlit rerun

### Fixed
- **FutureWarning**: Fixed deprecated pandas `fillna()` downcasting behavior
  - Updated `artifact_flag` column handling to use `.infer_objects(copy=False)`
  - Eliminates console warning spam during time series visualization
- **Repeated Cleaning Operations**: Addressed root cause of slow app responsiveness
  - Cleaning was running on every user interaction (tab switch, slider move, etc.)
  - Now only runs when data or settings actually change

### Performance Impact
- **Typical speedup**: 5-10x faster on subsequent interactions after initial load
- **Parallel processing**: 2-4x faster when processing multiple datasets
- **With Numba installed**: Additional 2-5x speedup for advanced metrics (entropy, DFA)
- **Total potential gain**: 10-20x faster with all optimizations enabled
- **Memory**: Cache uses ~2-5% additional session state memory
- **Cache stats**: Available via Performance Settings sidebar button

### Recommendations
- **Install Numba**: `pip install numba` for 2-5x additional speedup on advanced metrics
- **Install psutil**: `pip install psutil` for better CPU detection and process priority
- **See**: `PERFORMANCE_OPTIONS.md` for quick setup guide

---

## [1.7.2] - 2025-12-04

### Added
- **Multi-User Sessions Expanded**: Support increased from 7 to 13 concurrent user sessions
  - Optimized for longitudinal study groups and research cohorts
  - Per-user calculation caching with improved memory management
  - Module version updated to 1.1.0

- **CPU Optimization Module**: New `app/cpu_optimization.py` for non-GPU systems
  - Smart CPU detection (cores, frequency, memory, performance tier)
  - Cross-platform support (Linux, macOS, Windows)
  - Automatic performance tier classification (low/medium/high)
  - Adaptive algorithm selection based on hardware capabilities

- **Optimized HRV Algorithms**: CPU-only performance enhancements
  - `compute_time_domain_fast()`: Vectorized time-domain metrics with reduced allocations
  - `compute_entropy_fast()`: Chunked entropy calculation (O(n) vs O(n²) for large arrays)
  - `compute_poincare_fast()`: Minimal allocation Poincaré analysis
  - `compute_dfa_fast()`: Segment-batched DFA with vectorized fluctuation
  - `compute_psd_fast()`: Optimized FFT with linear interpolation
  - `compute_hrv_fast()`: Comprehensive HRV with adaptive algorithm selection
  - `compute_windowed_hrv_fast()`: Adaptive windowed analysis with limits

- **Auto-Tuning Performance Settings**: Settings automatically adjust to hardware
  - "Auto (Recommended)" preset detects CPU and applies optimal settings
  - Visual CPU tier indicator in sidebar (🟢 High / 🟡 Medium / 🔴 Low)
  - New settings: `max_windows`, `use_fast_entropy`
  - Optional Numba JIT compilation support when available
  - Optional psutil integration for detailed CPU information

### Changed
- **Performance Settings UI**: Now shows detected CPU tier and auto-tunes defaults
  - Fast entropy mode enabled by default for low/medium CPUs
  - Window limits adjusted based on CPU performance tier
  - Memory optimization enabled by default for non-high-tier CPUs
- `performance_utils.py` updated to v1.1.0 with CPU detection integration

### Technical
- Added optional dependencies: `psutil` (CPU detection), `numba` (JIT compilation)
- All optimized functions maintain API compatibility with original implementations
- Subsample-based entropy for arrays >2000 samples on low-end CPUs

---

## [1.7.1] - 2025-12-03

### Changed
- **Performance Optimizations**: Major improvements to app responsiveness
  - `get_database()` now uses `@st.cache_resource` for singleton caching
  - Added `get_cached_user_list()` with 30-second TTL to avoid DB queries on rerun
  - User login dropdown uses cached data; full profile fetched only on selection
  - Multi-user session manager now cached with `@st.cache_resource`
  - i18n translation functions optimized with fast-path dictionary lookups
  - Added `@st.fragment` decorator to clinical assessment forms (ESS, KSS, Samn-Perelli)
  - NASA Nutrition Calculator and Medical Record forms now use partial reruns
  - Loading spinners added for assessment history and HRV data queries
  - **Space Weather Tab**: HRV-Kp correlation now requires explicit button click instead of auto-compute
  - Weather covariates checkbox defaults to unchecked for faster tab loading
  - `fetch_open_meteo_hourly()` cache decorator now has `show_spinner=False`
- **Fast Mode Enabled by Default**: All performance settings now default to fastest options
  - Minimal mode ON by default (skip heavy plots, limit datasets)
  - Skip Gauges, Frequency overlay, Poincaré, Spectrogram all ON by default
  - Max windows reduced from 1500 to 500
  - Step size increased from 1min to 2min for fewer windows
  - Performance preset defaults to "Fast (Low CPU)" instead of "Balanced"
  - Max plot points reduced from 2000 to 1000
  - Max dataframe rows reduced from 500 to 200

### Fixed
- **FutureWarning**: Fixed deprecated `pd.to_numeric(errors='ignore')` in SWPC and DONKI data fetchers
- Reduced unnecessary full page reruns when interacting with form widgets
- Eliminated repeated database initialization on every Streamlit rerun
- User list queries no longer block UI during page refresh

### Requirements
- Streamlit minimum version updated to 1.37 (required for `@st.fragment` support)

---

## [1.7.0] - 2025-12-03

### Added
- **Rebrand**: Physiological Laboratory → Mission Control - Flight Surgeon across UI, docs, metadata, and automation.

- **Exploration Medical Record**: NASA-style mission log stored in `medical_history`
  - Mission profile/day, habitat, EVA clearance, radiation dose, and space-weather alerts
  - Behavioral health, confinement stress, hydration, and countermeasure adherence tracking
  - Tabular history for 22-day isolation campaigns with JSON export for statistics

- **Polar AccessLink VO₂max Sync**: Optional integration with Polar Flow
  - Environment variable configuration (`POLAR_ACCESSLINK_TOKEN`, `POLAR_ACCESSLINK_USER_ID`)
  - One-click VO₂max fetch inside NASA Nutrition calculator
  - Exercise energy expenditure now compensates MET values using VO₂max-derived factors

- **Clinical Profile UI Tab**: New "🏥 Clinical Profile" tab in User Profile
  - NASA Nutrition Calculator with real-time BMR/TDEE/hydration calculations
  - Body composition entry form (body fat%, lean mass, circumferences)
  - Medical history summary view
  - Profile completeness indicators with missing field alerts
  - Exercise type selection with configurable duration (default 2 hours)

- **Multi-User Session Management**: Support for up to 7 concurrent users
  - New module: `app/multi_user_session.py`
  - User session tracking with quick-switch capability
  - Per-user calculation caching
  - Sessions tab in User Profile for management
  - `get_active_user_context()` for tabs to access user settings
  - `get_all_active_users()` for group analysis preparation

- **Multi-User & Longitudinal Study Roadmap** (see WARP.md):
  - Baseline + 22 measurements longitudinal tracking (planned)
  - Intra-subject analysis: within-individual change detection (planned)
  - Inter-subject analysis: between-group comparisons (planned)
  - Group × Time interaction effects (planned)

- **Spanish Language Support (i18n)**: Full bilingual support for clinical assessments
  - Colombian-validated translations for clinical scales (ESE-VC, KSS)
  - Escala de Somnolencia de Epworth (Chica-Urzola et al., 2007)
  - Escala de Somnolencia de Karolinska (Velásquez-Paz et al., 2022)
  - Escala de Fatiga de Samn-Perelli (aviation standards)
  - Language selector in User Profile settings
  - Automatic language sync when user logs in
  - New module: `app/i18n.py`

- **Comprehensive Clinical Profile Module**: Astronaut-grade physiological assessment
  - **Extended Anthropometrics**: Body composition analysis
    - Body fat %, lean mass, muscle mass, bone mass, water %
    - Circumference measurements (waist, hip, neck, chest, arm, thigh, calf)
    - Skinfold measurements for caliper-based body fat
    - US Navy body fat estimation method
    - Waist-to-hip and waist-to-height ratios
    - Visceral fat level tracking
  
  - **Basal Metabolic Rate Calculations**:
    - Mifflin-St Jeor equation (gold standard, ADA recommended)
    - Harris-Benedict equation (for comparison)
    - Katch-McArdle equation (when lean mass known)
    - VO2max-adjusted calculations
  
  - **NASA-Based Nutrition Requirements** (JSC67378):
    - Daily water: 32 mL/kg body weight minimum (2500 mL/day floor)
    - Activity-adjusted hydration with exercise add-ons
    - Macronutrient ratios: 15% protein, 30% fat, 55% carbs
    - Protein: 1.2-1.8 g/kg body mass
    - Extra 500 kcal for EVA/intense activities
  
  - **Exercise Energy Expenditure**:
    - MET-based calorie calculations for 15+ exercise types
    - Astronaut-specific exercises (ARED, CEVIS, T2)
    - Configurable duration (default: 2 hours)
    - Activity factor multipliers (PAL 1.2-2.0)
  
  - **Complete Medical History Tracking**:
    - Cardiovascular, respiratory, metabolic conditions
    - Neurological, musculoskeletal, psychiatric history
    - Allergies (drug, environmental, food, latex)
    - Surgical history, family history
    - Current medications and supplements
    - Lifestyle factors (tobacco, alcohol)
    - Cardiovascular risk factor summary
  
  - **Laboratory Data Management**:
    - Complete Blood Count (CBC/Hemogram)
    - Comprehensive Metabolic Panel
    - Lipid Panel with calculated ratios
    - Thyroid function tests
    - Iron studies and vitamins
    - Inflammatory markers
    - Urinalysis with microscopy
    - eGFR calculation (CKD-EPI 2021 race-free equation)
  
  - New module: `app/clinical_profile.py`

- **Database Schema Expansion**: New tables for clinical data
  - `body_composition` - Extended anthropometric measurements
  - `medical_history` - Comprehensive medical antecedents (JSON storage)
  - `lab_cbc` - Complete blood count results
  - `lab_chemistry` - Blood chemistry/metabolic panel
  - `lab_urinalysis` - Urinalysis results
  - `physiological_calcs` - Cached calculation results
  - Language preference field in user profiles

### Changed
- User Profile tab now supports language preference (EN/ES)
- Clinical scales render with translated strings based on user language
- Database schema version updated with migration support
- GPT-5.2 high reasoning workflow now lives inside the Export tab and consumes the rendered statistical report payload.

### Technical
- Database connection pooling with persistent connections
- WAL mode for concurrent database access
- Optimized user registration (single-transaction username check + creation)
- Added indices for body composition and laboratory tables

### References
- Mifflin MD et al. Am J Clin Nutr. 1990;51(2):241-247
- NASA JSC67378 Exploration Nutrition Requirements
- NASA-STD-3001 Water Requirements
- Inker LA et al. N Engl J Med. 2021;385(19):1737-1749 (CKD-EPI 2021)

---

## [1.6.4] - 2025-12-02

### Added
- **NVIDIA GPU Processing Support**: Hardware acceleration for HRV computations
  - Auto-detection of NVIDIA GPUs (RTX 5070, RTX 4090, RTX 3080, etc.)
  - CUDA-accelerated RMSSD, SDNN, pNN50, FFT PSD, and Poincaré calculations
  - Built-in GPU benchmark with CPU comparison (2-10x speedup on large arrays)
  - GPU settings sidebar panel with enable/disable toggle
  - Automatic fallback to CPU when GPU unavailable
  - New module: `app/gpu_processing.py`

- **Centralized User Profile Tab**: Complete user data management
  - User registration with biometric data (age, height, weight, BMI)
  - Validated clinical scales: ESS (Johns 1991), Samn-Perelli (1982), KSS (Åkerstedt 1990)
  - VAS fatigue/pain assessments with timestamped history
  - Assessment trend charts and longitudinal tracking
  - HRV measurement history linked to user profile
  - Data export/import (JSON format for portability)
  - SQLite database storage with multi-user support
  - New module: `app/user_profile_tab.py`

- **Centralized Logging Infrastructure**: Persistent debug and error logs
  - Rotating file logs in `logs/` directory (auto-created)
  - `logs/app.log` — All application logs (DEBUG level, 10 MB rotating)
  - `logs/errors.log` — Error-only log for critical issues
  - User action audit trail via `log_user_action()`
  - Console + file dual output with consistent formatting
  - New module: `app/logging_config.py`

### Changed
- Sidebar now includes GPU Processing settings (⚡ Performance + 🖥️ GPU)
- User Profile tab added as second tab (after Overview)
- Models can now access centralized user profile data via `get_current_user_data()`
- Updated requirements.txt with GPU installation instructions
- `setup_console_logging()` now integrates with centralized file logging
- Updated `.gitignore` to exclude `logs/` directory

### Fixed
- VO2max input field now accepts 0 (for "unknown - will be estimated")

### Documentation
- Updated `WARP.md` with logging infrastructure, GPU support, and troubleshooting
- Updated `.cursor/rules/agent.mdc` with logging policy and common bug patterns
- Added maintenance checklist and module architecture quick reference

## [1.6.3] - 2025-12-02

### Added
- **No-Data Navigation**: All tabs now accessible without uploading HRV data
  - Space Weather, Circadian, SAFTE, and Biofeedback tabs fully functional without uploads
  - Data-dependent tabs show friendly explanations with example data
- **Enhanced Welcome Experience**: Interactive module cards with availability indicators
- **User-Friendly Examples**: Each data-dependent tab shows reference values and interpretation guides
- **Sidebar Exploration Mode**: Quick-access panel highlighting available features
- **CPU Performance Optimization**: New performance utilities module
  - Configurable performance presets (Fast/Balanced/Quality/Custom)
  - Smart downsampling for plots based on CPU capability
  - DataFrame row limits with feedback
  - Session-state caching with TTL for expensive operations
  - Performance metrics tracking (cache hits, slowest operations)
  - New module: `app/performance_utils.py`

### Changed
- App structure refactored to show tabs immediately on load
- Welcome header now emphasizes modules that work without data
- Getting Started guide expanded with immediate exploration options
- Plot functions now auto-downsample based on performance settings
- Windowed metrics display respects performance row limits

---

## [1.6.2] - 2025-12-01

### Added
- **Space Weather Impact Predictions**: Real-time arrival time calculations for all solar energy categories
  - Photon/X-ray impacts (instantaneous detection)
  - Solar Energetic Particles (SEPs) from GOES proton flux
  - Solar wind plasma with L1→Earth travel time calculation
  - Geomagnetic conditions (Kp/Dst indices)
- **Polar H10 Monitoring Recommendations**: Automatic EKG capture timing guidance based on space weather severity
- **Bogotá Local Time Display**: All arrival times shown in Colombia timezone (UTC-5)
- **Priority Alert System**: Color-coded severity banners with countdown to next impact
- New module: `app/space_weather_impact.py` with complete prediction engine

### Changed
- Space Weather tab now displays impact predictions prominently at the top
- Enhanced severity classification (Quiet → Minor → Moderate → Strong → Severe → Extreme)

---

## [1.6.1] - 2025-11-29

### Added
- **Complete Circadian Module Integration**: All circadian files now in `app/circadian/`
  - **phasetools.py**: Cosinor analysis for phase extraction from time series data
  - **prc.py**: Phase Response Curves (PRC), Intensity Response Curves (IRC), Dosage Response Curves (DRC)
  - **sleep.py**: Two-Process Model of sleep regulation with clustering algorithms
  - **synthetic_data.py**: Generate synthetic wearable data from light schedules
  - **readers.py**: Actiwatch and generic wearable data loading with timestamp alignment
  - **plots.py**: Actogram visualization and stroboscopic plots
- **Removed Future_integrations folder**: All models fully integrated into main app

### Changed
- Circadian module version updated to 1.0.3
- All circadian imports now use `app.circadian.*` namespace
- Cross-platform compatibility verified for Windows and Linux

---

## [1.6.0] - 2025-11-29

### Added
- **Population Norms Tab**: Compare HRV metrics against scientifically validated population norms
  - Age and sex-stratified reference values from Nunan et al. (2010), Ortega et al. (2024), MESA Study
  - Percentile rankings and deviation categories (Very Low → Very High)
  - Full scientific citations with PMID links
- **Blood Pressure Variability (BPV) Module**: Comprehensive BPV analysis
  - Systolic/diastolic SD, CV, ARV (Average Real Variability), SV (Successive Variation)
  - Pulse pressure and MAP calculations
  - Risk assessment based on Parati et al. (2018), Rothwell et al. (2010) thresholds
  - HRV-BPV correlation analysis for autonomic assessment
- **Enhanced Welcome Page**: Professional laboratory branding with quick access
  - Data status panel showing loaded datasets
  - Quick access grid to all analysis modules
  - Getting started guide for new users
  - Contributing modules display (Circadian, SAFTE, HRV Core, ECharts)
- **UI State Manager**: Centralized data availability tracking
  - Conditional compute button enabling/disabling
  - Session persistence for data status
  - Multi-data-type awareness (RR, sleep, ECG, BP)
- **Device Import Reorganization**: Streamlined sidebar interface
  - Polar H10 RR data with professional interface
  - Garmin Vivosmart 5 integration
  - Generic RR file support
  - Unified data normalization pipeline

### Changed
- All tabs now accessible without data upload (navigation-first design)
- Compute buttons disabled until required data is uploaded
- Welcome header uses Streamlit native components for reliable rendering
- Sidebar reorganized with device-specific import sections

---

## [1.5.0] - 2025-11-28

### Added
- **Circadian Physiology Module**: Integrated circadian rhythm simulation with multiple mathematical models (Forger99, Jewett99, Hannay19, Hannay19TP)
- **User Profiles System**: Comprehensive biometric profiles with validated clinical scales (ESS, KSS, PSQI, Samn-Perelli)
- **Docker Support**: Full containerization with PostgreSQL/TimescaleDB for production deployment
- **Professional About Tab**: Complete documentation viewer with version info, changelog, and author details
- **Space Weather Persistence**: NOAA/NASA data stored in database for longitudinal correlation studies

### Changed
- Fixed wake validation logic in circadian models (Bug: `and` → `or` for proper range checking)
- Fixed CLI function calls in circadian module (`read_standard_json` → `load_json`, etc.)
- Improved cross-platform compatibility (Windows/Linux temp paths using `tempfile`)

### Fixed
- Chronic load calculation now uses proper daily average normalization
- Sample entropy range corrected to include all complete templates
- Fusion confidence now uses variance-based coefficient of variation instead of arbitrary scaling

---

## [1.4.0] - 2025-11-15

### Added
- **ECG R-Peak Detection**: Pan-Tompkins algorithm with template matching for research-grade beat detection
- **Multi-Modal Sensor Fusion**: Integration with Oura, WHOOP, Apple Health, Fitbit, and Garmin
- **Long-Term HRV Trending**: Baseline establishment, trend detection, and anomaly alerts
- **Exercise HRV Analysis**: Heart rate recovery (HRR), parasympathetic reactivation, TRIMP calculation
- **ML Predictions**: Atrial fibrillation risk, sudden cardiac death stratification, sleep apnea screening
- **Real-Time BLE Integration**: Live streaming from Polar H10/H9, Garmin HRM-Pro, Wahoo TICKR

### Changed
- Enhanced ECharts visualizations with modern two-ring gauge style
- Improved responsive chart sizing with ResizeObserver

---

## [1.3.0] - 2025-10-20

### Added
- **NOAA Space Weather Dashboard**: Comprehensive solar and geomagnetic data feeds
- **Fatigue Prediction (SAFTE Model)**: Sleep-based cognitive effectiveness modeling
- **Scientific Charts Module**: Publication-ready visualizations with unified physiological timelines
- **Biofeedback Mode**: Real-time coherence training with breathing guides

### Changed
- Reorganized tab structure for better workflow navigation
- Updated gauge builder with ECharts-based modern gauges

---

## [1.2.0] - 2025-09-15

### Added
- **ActiGraph GT3X Integration**: Research-grade accelerometer data import
- **Somfit Pro Integration**: Home sleep testing device support with EDF parsing
- **Publication Export**: APA-formatted tables and LaTeX export for journals
- **AI-Powered Interpretation**: GPT-5 integration for clinical narrative generation

### Changed
- Improved artifact detection algorithms
- Enhanced windowed analysis with configurable parameters

---

## [1.1.0] - 2025-08-01

### Added
- **Garmin Connect Integration**: Bulk export and FIT file support
- **Autonomic Function Tests**: Valsalva ratio, deep breathing E:I, 30:15 standing test
- **Readiness Assessment**: Morning HRV-based training readiness scoring
- **Multi-file Analysis**: Comparative analysis across multiple recordings

### Changed
- Redesigned sidebar configuration
- Improved PSD computation methods (Welch, Periodogram, AR)

---

## [1.0.0] - 2025-07-01

### Added
- **Core HRV Analysis**: Time-domain, frequency-domain, and nonlinear metrics
- **Poincaré Plots**: SD1/SD2 analysis with ellipse visualization
- **Spectrogram View**: Time-frequency analysis of HRV patterns
- **Quality Control**: Artifact detection with threshold-based filtering
- **Space Weather Correlation**: Integration with NASA DONKI and NOAA data
- **Export Functionality**: Markdown, CSV, and JSON export options

### Technical Foundation
- Streamlit-based web interface
- ECharts integration for interactive visualizations
- Modular architecture with separation of concerns
- Comprehensive type hints and documentation

---

## Version History Summary

| Version | Date | Highlights |
|---------|------|------------|
| 1.6.4 | 2025-12-02 | GPU acceleration (NVIDIA CUDA), centralized user profile, clinical scales |
| 1.6.3 | 2025-12-02 | No-data navigation, enhanced welcome experience, user-friendly examples |
| 1.6.2 | 2025-12-01 | Space weather impact predictions, Polar H10 timing recommendations |
| 1.6.0 | 2025-11-29 | Population norms, BPV analysis, enhanced welcome |
| 1.5.0 | 2025-11-28 | Circadian module, user profiles, Docker |
| 1.4.0 | 2025-11-15 | ECG detection, sensor fusion, ML predictions |
| 1.3.0 | 2025-10-20 | NOAA space weather, SAFTE fatigue model |
| 1.2.0 | 2025-09-15 | ActiGraph, Somfit, publication export |
| 1.1.0 | 2025-08-01 | Garmin, ANS tests, readiness scoring |
| 1.0.0 | 2025-07-01 | Initial release with core HRV analysis |

---

## Roadmap

### Completed (Q4 2025)
- ✅ Population normative database with age/sex stratification
- ✅ Blood Pressure Variability (BPV) integration
- ✅ Circadian rhythm analysis module
- ✅ Docker containerization with TimescaleDB
- ✅ NVIDIA GPU acceleration (RTX 5070/4090/3080)
- ✅ Centralized user profile system with clinical scales (ESS, Samn-Perelli, KSS)
- ✅ CPU performance optimization with presets

### Research-Based Priorities (2025-2026)

*Based on latest peer-reviewed literature (2024-2025):*

#### High Priority (Q1 2026)

| Feature | Scientific Basis | Impact |
|---------|------------------|--------|
| **Multimodal Fatigue ML** | Kim et al. 2025 - HRV+cortisol TabNet (AUC 0.77) | High |
| **Gradient Boosting Fatigue** | Goutham 2025 - LightGBM/XGBoost on WESAD | High |
| **Sleep-Phasic HRV** | Fan et al. 2024 - CAP/NCAP/REM analysis (80% accuracy) | Medium |
| **Edge Computing Mode** | Lavanya et al. 2023 - DL+DWT (99.3% arrhythmia) | Medium |

#### Medium Priority (Q2-Q3 2026)

| Feature | Scientific Basis | Impact |
|---------|------------------|--------|
| **Drowsiness Detection** | AlArnaout et al. 2025 - RF HRV (86% accuracy) | High |
| **Sleep Quality CNN** | Kiliç et al. 2023 - Wearable+survey deep learning | Medium |
| **Syncope Prediction** | Lee et al. 2024 - XGB 3-min advance warning | Medium |
| **Wearable Validation** | Dial et al. 2025 - Oura/WHOOP/Garmin benchmarks | Low |

### Legacy Planned Features
- Advanced nonlinear dynamics (MSE, RQA, Lyapunov)
- Mobile companion app for data collection
- RESTful API for third-party integration

### Under Research (Aerospace Medicine)
- G-tolerance assessment for aerospace applications
- Altitude/hypoxia HRV analysis
- Spatial disorientation markers
- Baroreflex sensitivity from HRV-BPV coherence

---

## Contributors

**Lead Developer & Author:**  
Dr. Diego Leonel Malpica Hincapié, MD  
Aerospace Medicine Specialist  
National University of Colombia

**Circadian Module:**  
Original package by Arcascope (Franco Tavella, Kevin Hannay, Olivia Walch)  
UI updates and integration by Dr. Diego L. Malpica

---

*For detailed feature documentation, see `docs/Manual.md`*

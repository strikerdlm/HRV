# HRV Analysis — Streamlit + Apache ECharts

Modern, interactive Heart Rate Variability (HRV) analysis app focused on scientific visualization and robust, reproducible metrics. Upload Polar‑style RR text files and explore time/frequency, nonlinear, spectrogram, windowed metrics, and normogram gauges in one place.

## Quick Start

### 1) Prerequisites
- Python 3.10+ recommended
- Windows PowerShell 7+ (this repo includes PowerShell helpers for Windows)

### 2) Install
```powershell
# From the project root
python -m venv .venv
. .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 3) Run the app
```powershell
streamlit run app/app.py
```
Then open the local URL shown by Streamlit (typically http://localhost:8501).

### 4) Load RR data
- Click “Upload RR (.txt)” in the sidebar and select one or more text files.
- Format: one RR value per line in milliseconds (ms). Values outside [300, 2000] ms are ignored.

## What’s Included
- Time series of RR and heart rate (derived)
- Frequency domain (Welch PSD) with VLF/LF/HF overlays
- Nonlinear Poincaré plot
- Spectrogram (time–frequency) of interpolated RR
- Sliding window metrics (window/step/min RR configurable)
- Normogram‑style gauges (SDNN, RMSSD, LF/HF, HF power) against common short‑term anchors
- Advanced analytics: heart rate fragmentation (PIP/IALS/PSS), deceleration & acceleration capacity (PRSA), symbolic dynamics (0V/2UV), permutation entropy, multifractal DFA, recurrence quantification (DET/LAM/Lmax), frequency-domain entropy, heart-rate–normalized RMSSD (“master curve”)
- Deviation detection timeline for sliding-window metrics with anomaly episodes and tachogram overlays
- Patient profile adjustments (age, sex, BMI, exercise) and readiness baselines with Kubios-style categories
- Autonomic function test helpers (Valsalva ratio, deep-breathing E:I response, 30:15 ratio) with configurable time windows
- Basic “Interpretation” notes and references

## Data Expectations
- Short‑term analyses typically use ∼5 minutes of stationary RR intervals.
- The app uses basic bounds (300–2000 ms) and interpolation for spectral methods (4 Hz).
- Quality of input (artifact/ectopic handling) directly impacts frequency and nonlinear metrics.

### Frequency method
- Choose PSD method in the sidebar: Welch (default), Periodogram, or AR (Yule–Walker approximation).

## Troubleshooting
- No plots? The app loads ECharts from a CDN by default. If you need offline support, install a local copy:
  ```powershell
  npm i echarts
  ```
  The app will auto‑use `node_modules/echarts/dist/echarts.min.js` when present.
- Empty metrics: ensure enough RR samples (≥50 for frequency, ≥100 for DFA, ≥10 for basic stats).
- Windowed metrics: ensure the “Min RR per window” threshold is attainable with your data.

## Security and Keys
- The app itself does not require API keys. If you integrate optional online search (e.g., literature lookups), store keys in a `.env` file and never commit secrets. Add `.env` to `.gitignore`.

## Roadmap (science‑driven)
The items below are informed by the existing enhanced system (see `docs/Enhanced_HRV_Analysis.md`) and recent literature. Order roughly reflects expected implementation sequence.

1) Data quality and preprocessing
   - Configurable artifact/ectopic handling with interpolation strategies and audit logs
   - Visual QC (tachogram with flagged beats) before metrics
   - HR‑correction options for selected indices where justified (e.g., Sacha‑style corrections)

2) Expanded metrics
   - Geometric: RR triangular index, TINN
   - Stress index (Baevsky) and related geometric distributions
   - Entropy: ApEn, SampEn (with explicit m, r parameters) and documentation
   - Nonlinear extensions: additional DFA options and parameter transparency

3) Frequency and time–frequency
   - Autoregressive (Burg) PSD alongside Welch; method selection in UI
   - Wavelet‑based time–frequency option with band energy tracking over time
   - Respiration‑aware overlays (estimate from HF peak or input breathing rate)

4) Norms and personalization
   - Age/sex‑aware reference ranges and cohort caveats
   - Within‑subject trend focus; exportable baseline definitions

5) Modeling and ML (optional, opt‑in dependencies)
   - GAMs/mixed‑effects summaries for longitudinal data (statsmodels)
   - Clustering (phenotypes) and forecasting (ARIMA/Prophet) on selected metrics
   - Export interactive HTML summaries (Plotly) and CSV/JSON results

6) Evidence & reproducibility
   - “Evidence” panel surfacing key references for each metric/method
   - Optional in‑app literature links (no full text), with API keys in `.env` only
   - Deterministic seeds; explicit version/method reporting in exports

## References (selected)
- Task Force of the ESC/NASPE (1996). Heart rate variability: standards of measurement, physiological interpretation, and clinical use. Circulation, 93(5), 1043–1065.
- Shaffer & Ginsberg (2017). An overview of HRV metrics and norms. Frontiers in Public Health. [Frontiers link](https://www.frontiersin.org/journals/public-health/articles/10.3389/fpubh.2017.00258/full)
- Quigley et al. (2024). Publication guidelines for HR and HRV studies in Psychophysiology—Part 1. Psychophysiology. [Wiley link](https://onlinelibrary.wiley.com/doi/10.1111/psyp.14604)
- Sacha (2016)–style HR correction considerations: see discussion in Frontiers in Physiology (2016). [Frontiers link](https://www.frontiersin.org/journals/physiology/articles/10.3389/fphys.2016.00356/full)

Additional resources are listed inside the app’s “References” tab.

## New: Data Quality & Preprocessing (artifact correction)
- Toggle artifact correction in the sidebar (“Data Quality”). Current method: threshold vs moving median or previous beat, with deviation threshold and median window size.
- The time series tab overlays:
  - raw series
  - cleaned series (green)
  - flagged artifacts (red points)
- Cleaned RR is used automatically in frequency, nonlinear, spectrogram, and windowed metrics when enabled.

Notes:
- The simple, transparent heuristics implemented here are conservative and bounded. Published software (e.g., Kubios) offers advanced options; our aim is reproducibility and clarity. See Quigley et al. 2024 (Psychophysiology) for measurement/reporting guidance and Frontiers (2016) for HR/respiration influences.

## New: Geometric metrics
- The app now adds geometric HRV metrics to the metrics table:
  - HRV triangular index (HRVI)
  - TINN (approximated baseline width)
  - Baevsky Stress Index (SI = AMo/(2·Mo·MxDMn); AMo as fraction)

These follow common definitions in the HRV literature; interpretation depends on protocol and cohort.

## New: Entropy metrics
- Default nonlinear metrics now include Approximate Entropy (ApEn) and Sample Entropy (SampEn) with m=2 and r=0.2·SD.
- View values in the “Metrics” tab; UI parameter controls (m, r) are planned.

## New: Autonomic function tests
- The “ANS Function Tests” tab lets you configure time windows (in seconds from recording start) for:
  - **Valsalva ratio** (phase II vs phase IV windows)
  - **Deep breathing** E:I difference/ratio over repeated breathing cycles
  - **30:15 ratio** around a sit-to-stand event
- Use cleaned RR data (when QC is enabled) to minimise artifact influence. Each test reports component RR values alongside the derived ratio for transparency.

## New: Advanced HRV metrics (2025 update)
- Heart rate fragmentation suite (PIP, IALS, PSS) for detecting autonomous disorganization and arrhythmic risk signals.
- Phase-rectified signal averaging capacities (DC/AC) with anchor counts for vagal vs sympathetic modulation.
- Symbolic dynamics (0V, 1V, 2LV, 2UV), permutation entropy, and frequency-domain entropy to characterise stress resilience in short recordings.
- Multifractal DFA spectrum width and recurrence quantification metrics (RR, DET, LAM, Lmax) for multi-scale and phase-space complexity tracking.
- Heart rate “master curve” normalization of RMSSD to minimise heart-rate dependence when comparing across workloads or individuals.
- All advanced metrics are listed in the metrics tab (with a dedicated summary table) and are available in exported data frames for modelling workflows.

## New: Deviation detection & readiness (Q4 2025)
- **Robust deviation detection** — enable the sidebar toggle to compute median/MAD-based z-scores across windowed metrics (RMSSD, SDNN, LF/HF, HF power by default). Windows breaching the warn or alert thresholds are colour-coded (yellow/red), displayed on the deviation timeline, and shaded directly on the tachogram.
- **Anomaly episodes** — contiguous yellow/red runs that meet the “Min windows to define an episode” requirement are summarised so you can quickly flag sustained shifts for review.
- **Patient profile adjustments** — supply age, sex, BMI, and exercise level to generate covariate-adjusted expectations (`rmssd_expected`, `sdnn_expected`) with z-scores; both the metrics table and exports include these comparisons.
- **Readiness tab** — build a Kubios-style readiness baseline from historical parasympathetic index values. Select the current session, choose a historical window, and view readiness percentile, category, baseline statistics, and trend plot.
- **Respiratory-rate gauge** — when an HF peak is detected reliably, the gauges tab now surfaces breaths/min as a qualitative respiration cue for protocol adherence.
- See `docs/Manual.md` for detailed workflows covering covariate adjustment, deviation detection, and readiness baseline configuration.

## New: Markdown exports & ML-assisted deviation clustering
- **Export tab** — download a Markdown report summarising the current session. Choose between *summary* (partial) and *complete* scopes, optionally filter datasets, and append analyst notes before exporting.
- **Section controls** — include or omit windowed metrics and ML insights on demand. The summaries render directly in-app so you can review the report before downloading.
- **ML-assisted clustering (optional)** — toggle “ML-assisted deviation clustering” in the sidebar to run a deterministic, bounded k-means pass across windowed metrics. High-deviation clusters appear in the windowed tab and can be injected into the Markdown report.
- Reports embed timestamps and method choices for traceability. Store any downstream API keys or secrets in `.env` files—never commit credentials to the repository.

## Legacy materials
If you need the earlier comprehensive Jupyter workflows and enhanced system description, see:
- `docs/Enhanced_HRV_Analysis.md`
- `docs/scripts/HRV_Comprehensive_Analysis.ipynb`

## License
MIT — see `LICENSE`.

## Author
Dr. Diego Leonel Malpica Hincapié — Aerospace Medicine (Colombia). Project links and citations appear in‑app under “About” and “References.”
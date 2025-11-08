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
- Basic “Interpretation” notes and references

## Data Expectations
- Short‑term analyses typically use ∼5 minutes of stationary RR intervals.
- The app uses basic bounds (300–2000 ms) and interpolation for spectral methods (4 Hz).
- Quality of input (artifact/ectopic handling) directly impacts frequency and nonlinear metrics.

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

## Legacy materials
If you need the earlier comprehensive Jupyter workflows and enhanced system description, see:
- `docs/Enhanced_HRV_Analysis.md`
- `docs/scripts/HRV_Comprehensive_Analysis.ipynb`

## License
MIT — see `LICENSE`.

## Author
Dr. Diego Leonel Malpica Hincapié — Aerospace Medicine (Colombia). Project links and citations appear in‑app under “About” and “References.”
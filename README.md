# Author: Dr Diego Malpica MD

# Mission Control - Flight Surgeon

**A Research-Grade Heart Rate Variability Operations Console for Aerospace Medicine**

[![GitHub](https://img.shields.io/badge/GitHub-strikerdlm%2FHRV-blue?logo=github)](https://github.com/strikerdlm/HRV)
[![Version](https://img.shields.io/badge/Version-1.17.0-green)](CHANGELOG.md)
[![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python)](https://python.org)
[![Next.js](https://img.shields.io/badge/Next.js-14-black?logo=next.js)](https://nextjs.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![CUDA](https://img.shields.io/badge/CUDA-Optional-76B900?logo=nvidia)](https://developer.nvidia.com/cuda-toolkit)
[![i18n](https://img.shields.io/badge/i18n-EN%20%7C%20ES-blue)](app/i18n.py)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

---

## About the Author

**Dr Diego Malpica MD**
*Aerospace Medicine Specialist*
National University of Colombia
Physiology Instructor, Colombian Aerospace Force
Contributing to the **AsterPhysiology** Research Initiative

---

## What is Mission Control - Flight Surgeon?

Mission Control - Flight Surgeon is a comprehensive, open-source **Heart Rate Variability (HRV) operations console** designed for clinicians, researchers, pilots, and aerospace medicine specialists. It goes far beyond a simple HRV calculator: this is a full **physiological operations platform** that fuses HRV analysis with circadian rhythm modeling, fatigue prediction, space weather intelligence, radiation exposure tracking, wearable device integration, and AI-powered clinical interpretation.

Think of it as a **flight surgeon's digital companion** — a single place where you can upload an astronaut's (or patient's, or athlete's) heart rate data and immediately get:

- Publication-ready HRV metrics across all domains (time, frequency, nonlinear, fragmentation)
- Population norms comparison stratified by age and sex
- Circadian rhythm simulation and fatigue forecasting
- Real-time space weather monitoring from NOAA and NASA
- Correlations between solar activity and autonomic function
- Clinical decision support with evidence-based recommendations
- Beautiful, exportable charts suitable for Nature-quality publications

**This project is entirely free, open-source, and built on peer-reviewed science.**

> For the complete, in-depth guide to every feature, see [docs/Manual.md](docs/Manual.md).

---

## Why is This Project Original?

Most HRV tools do one thing: compute RMSSD and a few frequency-domain metrics. Mission Control - Flight Surgeon is different in several fundamental ways:

1. **Aerospace Medicine Focus**: This is the only open-source HRV platform designed specifically for flight surgeons and operational medicine. It includes NASA Exploration Medical Capability (ExMC) assessments, radiation dose tracking across 10 space environments, and EVA Go/No-Go decision matrices.
2. **Space Weather-HRV Correlation**: No other tool correlates your HRV data with real-time NOAA/NASA space weather feeds (Kp index, solar wind, CMEs, X-ray flux) using lag-aware analysis with FDR correction. This enables novel research into how solar activity affects human autonomic function.
3. **Multi-Model Circadian Simulation**: Integrates three validated mathematical circadian models (Forger99, Jewett99, Hannay19) from the Arcascope research package to simulate circadian rhythms, shift work adaptation, and entrainment dynamics.
4. **SAFTE Fatigue Prediction with FAST-Style Visualization**: Implements the reservoir-based SAFTE biomathematical model (Hursh et al. 2004 / DRDC Peng & Bouak 2015) with multi-day forecasting (1–7 days), Garmin Connect sleep schedule integration, BAC equivalence thresholds (Dawson & Reid 1997), cognitive lapse probability (Van Dongen et al. 2003), and ICAO-aligned FRMS dashboards. Inspired by the FAST (Fatigue Avoidance Scheduling Tool) used by the US Air Force, FAA, and FRA.
5. **Ventilatory Threshold Estimation**: Non-invasive detection of aerobic (VT1) and anaerobic (VT2) thresholds using DFA-alpha1 analysis, eliminating the need for laboratory CPET — a breakthrough for field and operational settings.
6. **Allostatic Load Monitoring**: Multi-day physiological trajectory tracking that catches cumulative degradation (declining HRV, rising resting HR, eroding sleep quality) before a single-day snapshot would flag a problem.
7. **Dual Architecture**: Both a feature-rich Streamlit research application and a modern TypeScript/Next.js frontend with FastAPI backend, giving you the choice between rapid prototyping and production deployment.
8. **Multi-Device Support**: Native import from Polar H10, Garmin Vivosmart 5, ActiGraph GT3X, and Compumedics Somfit Pro — plus FIT-to-CSV conversion tools built right in.
9. **Fully Reproducible Science**: Every metric includes citations (Task Force 1996, Shaffer & Ginsberg 2017, Nunan et al. 2010), every chart is exportable in SVG/PDF/PNG at 300+ DPI, and every analysis step is logged for complete audit trails.

---

## Architecture Overview

> **Primary interface (2026 →): Next.js + FastAPI.** The TypeScript/Next.js frontend over the FastAPI backend is the **main** application for all new development and deployment. All new features (including the Operational Performance Indicator framework, the in-platform Psychomotor Vigilance Task, the research-grade HRV endpoints, and the Q1 manuscript submission package) are built on this stack. The legacy Streamlit interface remains in the repository as a secondary research workbench for single-user/local workflows but receives only maintenance fixes — new features land on Next.js + FastAPI first.

Mission Control - Flight Surgeon is organised around one Python analysis core served through two interfaces:

### The TypeScript/Next.js Frontend + FastAPI Backend (primary — modern UI, production deployment)

The main application, under `frontend/` and `api/`, is a **production-grade, responsive web platform** built with:

- **Frontend**: Next.js 14, React, TypeScript, Tailwind CSS, Apache ECharts
- **Backend**: FastAPI (Python) exposing all HRV, fatigue, readiness, PVT, and space-weather modules as REST endpoints
- **Integration target** for the Operational Performance Indicator (OPI) framework, the Psychomotor Vigilance Task module, and the scheduling/readiness pipeline

Suited for:

- Production and multi-user environments
- Crew scheduling and human performance management
- Mobile-responsive and remote access
- Integration with external systems via REST API

**Key frontend pages include:**

| Page                            | Description                                                                               |
| ------------------------------- | ----------------------------------------------------------------------------------------- |
| **Dashboard**             | Crew profiles, space weather widget, IHPI gauges                                          |
| **Scheduling**            | Activity cards, Go/No-Go indicators, crew management                                      |
| **Operational PVT**       | 3-minute PVT-B pre-flight gate — `/scheduling/pvt`                                        |
| **Research Hub**          | 21+ dedicated analysis pages including workload, vigilance, and flight-fatigue tooling    |
| **Research PVT**          | 5-minute PVT with history + variant selector — `/research/pvt`                            |
| **Ventilatory Threshold** | DFA-alpha1 analysis with publication-quality charts                                       |
| **Space Weather**         | Real-time Kp, F10.7, solar wind gauges                                                    |
| **Export**                | Publication-grade reports, CSV/JSON data                                                  |

### The Streamlit Application (legacy — secondary research workbench)

> ⚠️ **Legacy status.** The Streamlit interface is retained in the repository for single-user / local research workflows and for historical continuity. It remains fully functional and receives bug fixes, but new features (OPI, PVT, …) land on the Next.js + FastAPI stack first. Where a capability exists on both stacks, the Next.js version is canonical.

The original interface, built with [Streamlit](https://streamlit.io), is a full-featured research workbench with 20+ interactive tabs covering HRV analysis, circadian physiology, fatigue prediction, and space weather monitoring. Suited for:

- Exploratory single-user data analysis
- Clinical autonomic assessments on a local workstation
- Quick data visualisation and report generation
- Workflows where launching the full FastAPI + Next.js stack is unnecessary

Three Streamlit entry points remain available:

| Entry Point            | File                            | Purpose                                                                   |
| ---------------------- | ------------------------------- | ------------------------------------------------------------------------- |
| **Operational**  | `app/operational_app.py`      | Local clinical workflows, user profiles, lightweight space weather context |
| **Research**     | `app/research_app.py`         | Full local dashboards: HRV analysis, NOAA correlations, ML analytics       |
| **Data Science** | `app/space_weather_ds_app.py` | Single-user space weather data science with latest Streamlit              |

Both stacks share the same Python analysis core under `app/`; the Streamlit app talks to SQLite directly, while the Next.js frontend communicates via the FastAPI REST API.

---

## HRV-Cognition Frontend Update

The frontend + API stack now includes a dedicated HRV-cognition workflow for operational decision support:

- **Comprehensive backend-driven analysis** via `/api/research/hrv/analyze` with persistent session IDs and quality metadata.
- **Quality/context propagation** (`AnalysisContext`) shown in-page through a reusable `QualityPanel` (stationarity, method validity, confidence, caveats).
- **Frequency method parity** with Welch and Lomb-Scargle comparison plus method-specific validity scoring.
- **Cognitive workload module** (`/research/workload`) with baseline/task/recovery annotation and reactivity metrics (`ΔlnRMSSD`, `ΔHF`, `ΔLF/HF`).
- **Vigilance tracker** (`/research/vigilance`) using calibrated sliding-window HRV scoring + SAFTE overlay for low-vigilance flagging.
- **Flight fatigue classifier** (`/research/flight-fatigue`) with calibrated multifeature risk probabilities and transparent missing-feature fallbacks.
- **Offline train / online infer split** for vigilance + flight-fatigue via JSON model artifacts (`api/model_artifacts/*`) and runtime loader.
- **Calibration transparency endpoint** at `/api/research/models/calibration-report` to expose model versioning/metrics/references.
- **In-app scientific traceability** with per-page metric interpretation + citation cards in workload, vigilance, and flight-fatigue modules.
- **Advanced nonlinear outputs** (RCMSE/MM-DFA) with strict data sufficiency gating.
- **Integrated physiological fusion** exposed with uncertainty intervals instead of a single deterministic score.
- **Persistent RR tracing catalog** (`/api/research/hrv/tracings/{user_id}` + detail endpoint) with dedupe-aware upload/analyze storage.
- **Global RR tracing loader** in the research header so all HRV pages can analyze the same selected recording.
- **Production-grade windowed longitudinal analytics** (`/api/research/hrv/windowed/{user_id}`) with `scope=all|selected`, robust trend inference (Kendall + Theil-Sen CI), anomaly/change-point flags, and FDR-adjusted physiological correlation outputs (`q` values).

## Getting Started

### Prerequisites

| Requirement            | Minimum    | Recommended               |
| ---------------------- | ---------- | ------------------------- |
| Python                 | 3.10       | 3.12+                     |
| Node.js (for frontend) | 18 LTS     | 20 LTS                    |
| RAM                    | 4 GB       | 8 GB                      |
| Storage                | 500 MB     | 1 GB                      |
| Browser                | Chrome 90+ | Chrome/Edge latest        |
| GPU (optional)         | —         | NVIDIA RTX 3080/4090/5070 |

### Step 1: Clone the Repository

```bash
git clone https://github.com/strikerdlm/HRV.git
cd HRV
```

### Step 2: Set Up the Python Environment

**Option A: Using Conda (Recommended)**

```bash
# Create environment
conda create -n hrv-py312 python=3.12 -y
conda activate hrv-py312

# Install dependencies
pip install -r requirements.txt
```

**Option B: Using venv**

```bash
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows

pip install -r requirements.txt
```

### Step 3: Configure Environment Variables

Create a `.env` file in the project root (never commit this file):

```env
# Optional — the app works without any of these
OPENAI_API_KEY=sk-...               # For AI interpretation
NASA_API_KEY=DEMO_KEY                # For NASA DONKI data
GARMIN_EMAIL=your_email@example.com  # For Garmin Connect API
GARMIN_PASSWORD=your_password        # For Garmin Connect API
ACCUWEATHER_API_KEY=your_key         # For weather covariates
```

> **Security**: The `.env` file is already in `.gitignore`. Never commit API keys or secrets to version control.

### Step 4: Launch the Application

**Option A: Streamlit (Research & Clinical)**

```bash
# Operational mode (fast, focused on profiles + space weather)
streamlit run app/operational_app.py

# Research mode (full dashboards: HRV + correlations + ML)
streamlit run app/research_app.py

# Data science mode (single-user, latest Streamlit)
pip install -r requirements_streamlit_latest.txt
streamlit run app/space_weather_ds_app.py
```

The app will open in your browser at `http://localhost:8501`.

**Option B: TypeScript Frontend + FastAPI Backend ((Recommended)**

```bash
# Terminal 1 — Start the FastAPI backend (port 8180)
conda activate hrv-py312
uvicorn api.main:app --reload --port 8180

# Terminal 2 — Start the Next.js frontend (port 3100)
cd frontend
npm install   # first time only
npm run dev
```

Access points:

- Frontend: http://localhost:3100
- API Docs: http://localhost:8180/docs
- Streamlit (if running): http://localhost:8501

**Option C: Docker (Production)**

```bash
docker-compose up -d
```

### Step 5: Your First Analysis (5 Minutes)

1. **Prepare your data**: Create a text file with one RR interval (in milliseconds) per line:

   ```
   1027
   1007
   991
   1010
   1020
   ```

   Name it with a timestamp for automatic alignment: `2025-11-06 00-43-42.txt`
2. **Upload**: Click "Browse files" in the sidebar and select your RR file(s)
3. **Run Analysis**: Click **Run HRV Analysis** — you will see real-time progress with elapsed time and completion percentage
4. **Explore tabs**: Start with **Overview** for summary statistics, then explore **Gauges** for visual benchmarks
5. **Export**: Go to the **Export** tab to download a comprehensive Markdown report or generate an AI-powered analysis

> **No data? No problem!** The app is fully navigable without uploading any HRV data. Space Weather, Circadian simulation, SAFTE/Fatigue prediction, and Biofeedback all work immediately.

---

## Module Guide

Below is a guide to every major module in the platform. Each module is grounded in peer-reviewed science and designed for both clinical utility and research rigor. For in-depth usage instructions with screenshots and examples, see [docs/Manual.md](docs/Manual.md).

### Core HRV Analysis

These modules implement the gold-standard HRV analysis pipeline as defined by the Task Force of ESC/NASPE (1996) and updated by Shaffer & Ginsberg (2017).

| Module                                   | What It Computes                                                | Why It Matters                                                                                                                                                                                                                                                                   |
| ---------------------------------------- | --------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Time-Domain**                    | SDNN, RMSSD, pNN50, Mean HR, LnRMSSD, CVI, CSI                  | These are the foundational metrics of heart rate variability. RMSSD reflects parasympathetic (vagal) activity and is the most reliable short-term HRV measure. SDNN captures overall autonomic regulation. LnRMSSD provides a normalized metric ideal for longitudinal tracking. |
| **Frequency-Domain**               | VLF, LF, HF power (ms2 and n.u.), LF/HF ratio                   | Spectral analysis decomposes HRV into frequency bands: HF (0.15-0.40 Hz) reflects respiratory-linked vagal activity, LF (0.04-0.15 Hz) reflects both sympathetic and baroreflex modulation, and VLF (<0.04 Hz) relates to thermoregulation and hormonal rhythms.                 |
| **Nonlinear Analysis**             | Poincare SD1/SD2, DFA alpha1/alpha2, Sample/Approximate Entropy | These capture the complexity and fractal properties of heart rate dynamics. DFA-alpha1 is particularly important — values near 1.0 indicate healthy fractal organization, while deviations signal autonomic dysfunction or physiological stress.                                |
| **Heart Rate Fragmentation (HRF)** | PIP, IALS, PSS                                                  | HRF metrics quantify beat-to-beat directional changes. The PROOF-AF study (2025) demonstrated that elevated fragmentation predicts atrial fibrillation risk independently of traditional HRV metrics.                                                                            |
| **Geometric Metrics**              | HRV Triangular Index, TINN, Baevsky Stress Index                | Geometric methods provide robust estimates of overall HRV that are less sensitive to recording quality than spectral methods. The Baevsky Stress Index, developed for cosmonaut monitoring, quantifies sympathetic activation.                                                   |
| **Sliding Window Analysis**        | Time-varying metrics with deviation detection                   | Tracks how HRV changes over the course of a recording, identifying non-stationary segments and anomaly episodes using configurable z-score thresholds.                                                                                                                           |
| **Population Norms**               | Age/sex-stratified percentile rankings                          | Compares your metrics against published normative data from Nunan et al. (2010), Ortega et al. (2024), and the MESA Study, so you know whether a value is truly abnormal or simply reflects age and sex.                                                                         |

### Exercise Physiology

| Module                                     | What It Does                                                                         | Why It Matters                                                                                                                                                                                                                                                                                                                                                                                                                      |
| ------------------------------------------ | ------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Ventilatory Threshold Estimation** | Detects VT1 (aerobic) and VT2 (anaerobic) thresholds from DFA-alpha1 during exercise | Traditionally, finding these thresholds requires expensive laboratory CPET with gas exchange analysis. This module achieves comparable accuracy (VT2: r=0.93, SE<7 bpm) using only a heart rate monitor. This is a game-changer for field testing, remote monitoring, and aerospace operations where lab equipment is unavailable. See[the full scientific report](docs/HRV_Ventilatory_Threshold_Comprehensive_Scientific_Report.md). |
| **Readiness Scoring**                | Kubios-style parasympathetic index with baseline comparison                          | Answers the daily question: "Am I recovered enough to train/work today?" Uses HF power, RMSSD, pNN50, and SD1 to compute a readiness score relative to your personal 7-day baseline.                                                                                                                                                                                                                                                |
| **Autonomic Function Tests**         | Valsalva ratio, deep breathing E:I, 30:15 standing ratio                             | Standardized clinical tests of autonomic nervous system integrity, essential for screening pilots, astronauts, and patients with suspected autonomic neuropathy.                                                                                                                                                                                                                                                                    |

### Aerospace Medicine

| Module                                     | What It Does                                               | Why It Matters                                                                                                                                                                                          |
| ------------------------------------------ | ---------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Space Weather Monitoring**         | Live NOAA SWPC and NASA DONKI feeds                        | Displays Kp index, F10.7 solar flux, solar wind parameters, CME arrival predictions, and flare probabilities. Essential for understanding the geomagnetic environment that may affect human physiology. |
| **Space Weather-HRV Correlation**    | Lag-aware correlation analysis (0-72h) with FDR correction | Enables research into how geomagnetic storms and solar events correlate with changes in autonomic function — an emerging field with significant implications for space exploration medicine.           |
| **Radiation Exposure Module**        | Evidence-based dose models for 10 environments             | Tracks cumulative radiation dose from Earth surface through Mars transit, with EVA Go/No-Go assessment matrices aligned to NASA STD-3001 career limits (600 mSv).                                       |
| **Exploration Medical Record**       | NASA ExMC/EIMO-aligned clinical logs                       | Comprehensive mission medical logging with EVA hours, radiation exposure, stress markers, behavioral health flags, and countermeasure tracking for deep-space mission autonomy.                         |
| **Space Weather Impact Predictions** | Exact arrival times for photon, SEP, and plasma events     | Calculates when solar events will arrive at your location and provides Polar H10 EKG timing recommendations so you can capture HRV during geomagnetic disturbances.                                     |

### Fatigue and Circadian Science

| Module                                      | What It Does                                          | Why It Matters                                                                                                                                                                                                                                                                     |
| ------------------------------------------- | ----------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Circadian Physiology**              | Forger99, Jewett99, Hannay19 mathematical models      | Simulates how your internal body clock responds to light schedules. Generate actograms, predict DLMO (dim light melatonin onset), and calculate the Entrainment Signal Regularity Index (ESRI). Based on the Arcascope circadian package (Tavella, Hannay, Walch, 2023).           |
| **SAFTE Fatigue Model**               | Reservoir-based cognitive effectiveness prediction    | Full SAFTE implementation (Hursh et al. 2004 / DRDC 2015) with reservoir dynamics, fatigue-amplified circadian drive, and sleep inertia. Multi-day forecasting (1–7 days) with Garmin Connect sleep schedule integration. Shared module used by both Research and Operational tabs.  |
| **FAST-Style Risk Metrics**           | BAC equivalence, lapse probability, risk-hour analysis | Inspired by FAST (Fatigue Avoidance Scheduling Tool): BAC mapping (Dawson & Reid 1997), PVT lapse probability (Van Dongen et al. 2003), and color-coded risk zones validated by FRA (77% = 2.5x accident cost, 50% = +65% accident risk). Publication-quality plots with no internal titles. |
| **Integrated Physiological Model**    | Log-linear fusion: SAFTE + HRV/HRF + Workload + Environment | Multiplicative fusion architecture: P(t) = σ(Σ αᵢ·log Fᵢ) combining schedule-based SAFTE, quality-gated autonomic physiology (lnRMSSD, PIP), workload context, and environmental modifiers. Fail-closed behavior when HRV quality is insufficient. |
| **Process Decomposition**             | Separate visualization of Process S and Process C     | Dual-axis chart showing the homeostatic sleep reservoir (linear depletion/exponential recovery) and two-harmonic circadian drive independently — the Borbely (1982) two-process model components that produce the effectiveness curve.                                             |
| **Trajectory Risk (Allostatic Load)** | Multi-day physiological degradation detection         | Implements McEwen's (1998) allostatic load concept: even if today's metrics look fine, a multi-day downward trend in HRV, resting HR, and sleep quality predicts functional decline. Uses EWMA smoothing and Smallest Worthwhile Change (SWC) thresholds from Plews et al. (2013). |
| **Psychomotor Vigilance Task (PVT)**   | In-platform 3-min and 5-min sustained-attention tests  | PVT-B (3 min, 355 ms lapse threshold; Basner & Dinges 2011) for pre-flight / shift-check; PVT-5 (5 min) for longitudinal tracking; PVT-10 (Dinges 1997 standard). Browser variant (Next.js, ~5–10 ms RT precision) for operational and research routes; research-grade PsychoPy desktop driver (`app/pvt_desktop.py`) for sub-ms timing. Full validated metric set: lapses, major lapses, false starts, mean/median/fastest-10%/slowest-10% RT, reciprocal response speed (1/RT), Basner-Dinges transformed lapses, `pvt_lapses_3min` feeding the existing scheduling/IHPI hard gate. See `docs/PVT.md`. |
| **Sleep Module (Garmin-backed)**       | Research dashboard + operational pre-flight sleep gate | Sleep debt, Sleep Regularity Index (Lunsford-Avery 2018), stage balance, and a SpO₂ **screening** proxy (never apnea diagnosis) computed from `garmin_daily_metrics`. Three FastAPI endpoints (`/api/research/garmin/sleep-summary`, `/sleep-correlations`, `/sleep-debt-trend`) serve a chart-first research dashboard at `/research/sleep` (duration trend, debt curve, stage stacked bar, regularity strip, correlation matrix with FDR-q, six pair scatter plots with OLS fit, evidence map) and an operational gate at `/scheduling/sleep` (GO / GO_MONITOR / CAUTION / NO_GO with debt gauge + 7-night duration bar + SpO₂ screening). All charts carry "Exploratory — Garmin wellness device; not PSG-diagnostic" (Lee 2025 DOI 10.5664/jcsm.11460; Schyvens 2024 DOI 10.2196/52192). See `docs/SLEEP.md`. |

### Wearable Device Integration

| Module                       | Supported Devices              | Key Data                                                          |
| ---------------------------- | ------------------------------ | ----------------------------------------------------------------- |
| **Polar H10**          | Polar H10 chest strap          | RR intervals (gold-standard ECG-grade), VO2max via AccessLink API |
| **Garmin Vivosmart 5** | Garmin wearables (FIT/ZIP/CSV) | Steps, sleep, SpO2, respiration, stress, body battery, calories   |
| **ActiGraph GT3X**     | ActiGraph accelerometers       | Activity counts, raw acceleration, sleep/wake scoring             |
| **Somfit Pro**         | Compumedics Somfit             | EDF/EDF+ polysomnography, sleep staging, SpO2                     |
| **FIT-to-CSV Tools**   | Any Garmin FIT file            | Convert and store FIT/CSV per profile directly in the app         |

### Clinical Assessment

| Module                                | What It Covers                                                                                                                                      |
| ------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| **User Profile System**         | Centralized biometrics, clinical scales (ESS, Samn-Perelli, KSS), mission context, and history tracking with ECharts timelines                      |
| **Personalized Health Metrics** | Body fat (US Navy method), sleep apnea risk (STOP-BANG), age-adjusted HRV norms, VO2max classification, cardiovascular risk, hydration requirements |
| **Blood Pressure Variability**  | BPV metrics (SD, CV, ARV, SV) with HRV-BPV correlation for comprehensive autonomic assessment                                                       |
| **Laboratory Tracking**         | CBC/Hemogram, blood chemistry, urinalysis with normal reference ranges                                                                              |
| **Profile Tools Engine**        | One-click computation of SAFTE fatigue, recovery score, training readiness, operational performance, and 24-hour performance forecast               |

### AI and Machine Learning

| Module                                  | Capability                                                                                                                                             |
| --------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Advanced HRV Analytics**        | ML pattern recognition, statistical tests (Shapiro-Wilk, t-tests, Mann-Whitney U), 7-day forecasting, anomaly detection, and clinical decision support |
| **Wearable Predictive Analytics** | Body Battery forecasting (Holt-Winters), Allostatic Load Index, circadian rhythm analysis, stress prediction, recovery analysis                        |

### Physiological SMS Risk Assessment

| Module | What It Does | Why It Matters |
|---|---|---|
| **BP Readiness Modifier** | Classifies resting blood pressure (ACC/AHA 2017) into Optimal/Elevated/Stage1/Stage2/Hypotension, applying a bounded +/-4 point readiness modifier | Resting BP provides complementary autonomic information to HRV (Porta et al., 2012). Hypotension flags G-LOC risk for pilots. |
| **Temperature Modifier** | Classifies basal oral temperature into Normal/LowGrade/Fever/Hypothermia, applying a bounded +/-3 point modifier | Core body temperature combined with HRV predicts fatigue with 86% accuracy (Zhang et al., 2025). Fever is disqualifying for EVA/flight. |
| **EVA SMS Risk Matrix** | 5x5 risk matrix (ICAO Doc 9859) mapping readiness + physiological flags to Acceptable/Tolerable/Undesirable/Intolerable | SMS approach adapted for spacewalk operations with hard disqualifiers for fever, severe hypertension, and critical PSI. |
| **Military Flight SMS** | 4x5 risk matrix (MIL-STD-882E) with G-LOC risk assessment and USAF crew rest compliance | Standard Practice for System Safety applied to high-performance flight with specific flags for hypotension + low HRV. |

### Environmental Monitoring and Weather

| Module | What It Does | Why It Matters |
|---|---|---|
| **ICE Station Monitor** | Simulated Antarctic research station with 8 environmental sensors (temp, humidity, CO2, pressure, PM2.5, noise, light, O2) | Monitors habitability of isolated confined environments. CO2 >1000 ppm impairs cognition (Satish et al., 2012). |
| **METAR Aviation Weather** | Real-time decoded METAR from any ICAO station worldwide via FAA AviationWeather.gov API | Provides pilots and flight surgeons with standard aviation weather in decoded, visual format with wind compass. |
| **Wind Chill / Frostbite** | NWS 2001 formula (Osczevski & Bluestein) with frostbite time estimation | Calculates when exposed skin will freeze, critical for Antarctic EVA and outdoor military operations. |
| **WBGT Heat Stress** | ISO 7243:2017 simplified estimation with work/rest guidance | Determines safe work durations in hot environments with NIOSH-aligned risk categories. |
| **Jet Lag Performance** | Circadian resynchronization model (Waterhouse et al., 2007; Arendt, 2009) with exponential recovery curve | Quantifies performance degradation from time zone travel. Eastward is ~50% harder to recover from than westward. |

### Biofeedback and Real-Time

| Module | What It Does |
|---|---|
| **HRV Biofeedback** | Paced breathing guide with coherence score tracking |
| **Real-Time Streaming** | Live HRV computation from BLE heart rate monitors |

---

## Project Structure

```
HRV/
├── app/                          # Python application core
│   ├── operational_app.py        # Streamlit: fast clinical workflows
│   ├── research_app.py           # Streamlit: full research dashboards
│   ├── space_weather_ds_app.py   # Streamlit: single-user data science
│   ├── hrv_core.py               # Core HRV computation engine
│   ├── vt_analysis.py            # Ventilatory threshold (DFA-alpha1)
│   ├── trajectory_risk.py        # Allostatic load / trajectory risk
│   ├── physiological_sms.py      # BP/temp modifiers + SMS risk matrices
│   ├── environment_calculators.py # Wind chill, WBGT, heat index, jet lag
│   ├── noaa_space.py             # NOAA space weather data ingestion
│   ├── space_weather_impact.py   # Impact predictions & Polar H10 timing
│   ├── radiation_exposure.py     # Evidence-based radiation dose models
│   ├── circadian/                # Circadian rhythm simulation models
│   ├── fatigue_calculator/       # SAFTE fatigue prediction engine
│   ├── wearable_analytics.py     # Garmin predictive analytics
│   ├── advanced_hrv_analytics.py # ML/statistics/clinical decisions
│   ├── user_profile_tab.py       # User profile & clinical scales UI
│   ├── user_database.py          # SQLite persistence layer
│   ├── gpu_processing.py         # NVIDIA CUDA acceleration
│   ├── logging_config.py         # Centralized logging setup
│   └── ...                       # 50+ modules (see docs/Manual.md)
│
├── api/                          # FastAPI backend
│   ├── main.py                   # API entry point, all endpoints
│   ├── research_endpoints.py     # Research-specific endpoints (VT, etc.)
│   └── requirements.txt          # API-specific dependencies
│
├── frontend/                     # TypeScript/Next.js frontend
│   ├── src/
│   │   ├── app/                  # Next.js pages (18+ research pages)
│   │   ├── components/           # Reusable UI components
│   │   ├── lib/                  # API clients, state management, SAFTE model
│   │   └── types/                # TypeScript type definitions
│   ├── package.json
│   └── tailwind.config.ts
│
├── docs/
│   ├── Manual.md                 # Comprehensive user manual (6000+ lines)
│   ├── Fatigue Biomathematical model/
│   │   ├── BiomathematicalModel.md     # DRDC Peng & Bouak (2015) full report
│   │   └── TECHNICAL_DOCUMENTATION.md  # Implementation docs (v2.0)
│   ├── Discussion about integrated model.md  # Integrated performance model design
│   └── HRV_Ventilatory_Threshold_Comprehensive_Scientific_Report.md
│
├── tests/                        # pytest test suite
├── db/init/                      # Database schema initialization
├── crew/                         # Mission-scoped data storage
├── logs/                         # Application and error logs
├── requirements.txt              # Python dependencies
├── docker-compose.yml            # Docker deployment
├── CHANGELOG.md                  # Detailed version history
└── WARP.md                       # Architecture reference
```

---

## Explore Without Data

The app is fully navigable **without uploading any HRV data**. These features work immediately:

| Module                  | What You Can Do                                                                              |
| ----------------------- | -------------------------------------------------------------------------------------------- |
| **Space Weather** | Fetch live NASA/NOAA data, see CME arrival predictions, get Polar H10 timing recommendations |
| **Circadian**     | Simulate circadian rhythms with different light schedules and shift work scenarios           |
| **SAFTE/Fatigue** | Run 1–7 day SAFTE forecasts with Garmin sleep data, BAC equivalence, lapse probability, and FAST-style risk metrics |
| **Biofeedback**   | Try the paced breathing demo with real-time coherence feedback                               |
| **User Profile**  | Register profiles, complete clinical scales, explore all assessment tools                    |

All other tabs show **example data** and **reference values** so you can understand every feature before uploading your own recordings.

---

## Input Data Formats

### Polar-Style RR Text Files

One RR interval per line, in milliseconds:

```
1027
1007
991
1010
```

**Filename convention**: `YYYY-MM-DD HH-MM-SS.txt` (e.g., `2025-11-06 00-43-42.txt`)
The timestamp is parsed to align HRV windows with space weather data. Values outside 300-2000 ms are automatically filtered.

### Garmin Data Sources

- **Wellness Export ZIP**: Download from Garmin Connect account settings
- **FIT Files**: Export individual activities from Garmin Connect web
- **JSON Files**: Upload individual Garmin export JSON files in User Profile
- **API Access**: Configure `GARMIN_EMAIL` and `GARMIN_PASSWORD` in `.env`

### Other Supported Formats

- **ActiGraph**: GT3X binary, AGD database, CSV exports
- **Somfit Pro**: EDF/EDF+ from Compumedics, XML annotations, CSV summary

---

## Environment Configuration

The application uses a **portable environment loader** (`app/env_loader.py`) that automatically finds and loads your `.env` file from the project root, regardless of computer or directory structure.

**Supported variables** (all optional):

| Variable                     | Purpose                                          |
| ---------------------------- | ------------------------------------------------ |
| `OPENAI_API_KEY`           | GPT-5.2 AI interpretation                        |
| `NASA_API_KEY`             | NASA DONKI data (use `DEMO_KEY` for free tier) |
| `GARMIN_EMAIL`             | Garmin Connect API access                        |
| `GARMIN_PASSWORD`          | Garmin Connect API access                        |
| `ACCUWEATHER_API_KEY`      | Weather covariate data                           |
| `POLAR_ACCESSLINK_TOKEN`   | Polar VO2max sync                                |
| `POLAR_ACCESSLINK_USER_ID` | Polar user identifier                            |
| `WOLFRAM_APP_ID`           | Wolfram Alpha symbolic math (future)             |

> **Security reminder**: Never commit `.env` to version control. The file is already in `.gitignore`.

### Garmin Connect Token Authentication (Recommended)

For environments where interactive MFA is impractical:

1. Set `GARMIN_EMAIL` and `GARMIN_PASSWORD` in `.env`
2. Run `python tests/test_garmin_email.py` and follow the prompts
3. Tokens are saved to `~/.garminconnect/` — treat this directory like a password

---

## Docker Deployment

For production deployment with persistent data storage:

```bash
# Start all services (PostgreSQL, Redis, App)
docker-compose up -d

# View logs
docker-compose logs -f app

# Include pgAdmin for database management
docker-compose --profile admin up -d

# Run TypeScript frontend with FastAPI backend
docker-compose --profile typescript up -d api
```

---

## Running Tests

```bash
pytest tests/ -v --cov=app
```

## Code Quality

```bash
# Format
black app/ tests/
isort app/ tests/

# Lint
ruff check app/ tests/

# Type check
mypy app/ --strict

# Security
bandit -r app/
pip-audit
```

---

## Scientific References

All metrics, thresholds, and interpretations in this project are grounded in peer-reviewed literature. Below are the key references organized by domain. Every citation includes a verifiable identifier (PMID or DOI).

### Core HRV Standards

- Task Force of the European Society of Cardiology and the North American Society of Pacing and Electrophysiology. (1996). Heart rate variability: Standards of measurement, physiological interpretation and clinical use. *Circulation, 93*(5), 1043-1065. [PMID: 8598068](https://pubmed.ncbi.nlm.nih.gov/8598068/)
- Shaffer, F., & Ginsberg, J. P. (2017). An overview of heart rate variability metrics and norms. *Frontiers in Public Health, 5*, 258. [PMID: 29034226](https://pubmed.ncbi.nlm.nih.gov/29034226/)
- Nunan, D., Sandercock, G. R. H., & Brodie, D. A. (2010). A quantitative systematic review of normal values for short-term heart rate variability in healthy adults. *Pacing and Clinical Electrophysiology, 33*(11), 1407-1417. [PMID: 20663071](https://pubmed.ncbi.nlm.nih.gov/20663071/)
- Quigley, K. S., Gianaros, P. J., Norman, G. J., Jennings, J. R., de Geus, E. J. C., Berntson, G. G., & Task Force on Publication Guidelines for HRV. (2024). Publication guidelines for heart rate and heart rate variability. *Psychophysiology, 61*(4), e14604.

### Population Norms

- Ortega, E., Malek, S., Chan, Y. H., Ho, C. L., Rodrigues, B. S., Singh, D., & Foo, R. (2024). The Pulse of Singapore: Short-term heart rate variability norms derived from a general population study. *Journal of General Internal Medicine, 39*(1), 101-108. [PMID: 37755550](https://pubmed.ncbi.nlm.nih.gov/37755550/)
- O'Neal, W. T., Chen, L. Y., Nazarian, S., & Soliman, E. Z. (2016). Reference ranges for short-term heart rate variability measures in individuals free of cardiovascular disease: The Multi-Ethnic Study of Atherosclerosis (MESA). *American Journal of Cardiology*. [PMID: 27396499](https://pubmed.ncbi.nlm.nih.gov/27396499/)

### Ventilatory Threshold and Exercise Physiology

- Eronen, T., Tikkanen, J., Junttila, J., Kaikkonen, K., Kentta, T. V., Huikuri, H. V., et al. (2024). Heart rate variability based ventilatory threshold estimation — Validation of a commercially available algorithm. *medRxiv*. [DOI: 10.1101/2024.08.14.24311967](https://doi.org/10.1101/2024.08.14.24311967)
- Gronwald, T., Rogers, B., & Hoos, O. (2020). Correlation properties of heart rate variability during endurance exercise: A systematic review. *Annals of Noninvasive Electrocardiology, 25*(1), e12697. [DOI: 10.1111/anec.12697](https://doi.org/10.1111/anec.12697)
- Rogers, B., Giles, D., Draper, N., Hoos, O., & Gronwald, T. (2021). A new detection method defining the aerobic threshold for endurance exercise and training prescription based on fractal correlation properties of heart rate variability. *Frontiers in Physiology, 11*, 596567. [DOI: 10.3389/fphys.2020.596567](https://doi.org/10.3389/fphys.2020.596567)
- Peng, C. K., Havlin, S., Stanley, H. E., & Goldberger, A. L. (1995). Quantification of scaling exponents and crossover phenomena in nonstationary heartbeat time series. *Chaos, 5*(1), 82-87. [DOI: 10.1063/1.166141](https://doi.org/10.1063/1.166141)
- Poole, D. C., Rossiter, H. B., Brooks, G. A., & Gladden, L. B. (2021). The anaerobic threshold: 50+ years of controversy. *Journal of Physiology, 599*(3), 737-767. [DOI: 10.1113/JP279963](https://doi.org/10.1113/JP279963)
- Aubert, A. E., Seps, B., & Beckers, F. (2003). Heart rate variability in athletes. *Sports Medicine, 33*(12), 889-919. [DOI: 10.2165/00007256-200333120-00003](https://doi.org/10.2165/00007256-200333120-00003)

### Blood Pressure Variability

- Parati, G., Stergiou, G. S., Dolan, E., & Bilo, G. (2018). Blood pressure variability: Clinical relevance and application. *Journal of Clinical Hypertension, 20*(7), 1133-1137. [PMID: 29927042](https://pubmed.ncbi.nlm.nih.gov/29927042/)
- Rothwell, P. M., Howard, S. C., Dolan, E., O'Brien, E., Dobson, J. E., Dahlof, B., Sever, P. S., & Poulter, N. R. (2010). Prognostic significance of visit-to-visit variability, maximum systolic blood pressure, and episodic hypertension. *The Lancet, 375*(9718), 895-905. [PMID: 20226988](https://pubmed.ncbi.nlm.nih.gov/20226988/)
- Saren, J., Kallio, M., & Jula, A. (2024). Blood pressure variability and health outcomes in adults 65 and older. *Age and Ageing*. [DOI: 10.1093/ageing/afae262](https://doi.org/10.1093/ageing/afae262)

### Circadian Physiology

- Tavella, F., Hannay, K., & Walch, O. (2023). Arcascope/circadian. Zenodo. [DOI: 10.5281/zenodo.8206871](https://doi.org/10.5281/zenodo.8206871)
- Forger, D. B., Jewett, M. E., & Kronauer, R. E. (1999). A simpler model of the human circadian pacemaker. *Journal of Biological Rhythms, 14*(6), 532-537.

### Fatigue Science

- Hursh, S. R., Redmond, D. P., Johnson, M. L., Thorne, D. R., Belenky, G., Balkin, T. J., Storm, W. F., Miller, J. C., & Eddy, D. R. (2004). Fatigue models for applied research in warfighting. *Aviation, Space, and Environmental Medicine, 75*(3 Suppl), A44-A53. [DOI: 10.1097/01.ASM.0000122824.30373.5E](https://doi.org/10.1097/01.ASM.0000122824.30373.5E)
- Peng, H., & Bouak, F. (2015). Development of bio-mathematical models for human performance under fatigue. *Defence Research and Development Canada Scientific Report*, DRDC-RDDC-2015-R280.
- Van Dongen, H. P. A., Maislin, G., Mullington, J. M., & Dinges, D. F. (2003). The cumulative cost of additional wakefulness: Dose-response effects on neurobehavioral functions and sleep physiology from chronic sleep restriction and total sleep deprivation. *Sleep, 26*(2), 117-126. [DOI: 10.1093/sleep/26.2.117](https://doi.org/10.1093/sleep/26.2.117)
- Dawson, D., & Reid, K. (1997). Fatigue, alcohol and performance impairment. *Nature, 388*(6639), 235. [DOI: 10.1038/40775](https://doi.org/10.1038/40775)
- Hursh, S. R., Raslear, T. G., Kaye, A. S., & Fanzone, J. F. (2006). Validation and calibration of a fatigue assessment tool for railroad work schedules. *U.S. DOT/FRA Technical Report DOT/FRA/ORD-06/21*.
- Borbely, A. A. (1982). A two process model of sleep regulation. *Human Neurobiology, 1*(3), 195-204.
- International Civil Aviation Organization. (2016). *Manual for the Oversight of Fatigue Management Approaches* (Doc 9966, 2nd ed.). [PDF](https://www.icao.int/safety/fatiguemanagement/FRMS%20Tools/Doc%209966.FRMS.2016%20Edition.en.pdf)

### Allostatic Load and Trajectory Risk

- McEwen, B. S. (1998). Protective and damaging effects of stress mediators. *New England Journal of Medicine, 338*(3), 171-179. [DOI: 10.1056/NEJM199801153380307](https://doi.org/10.1056/NEJM199801153380307)
- Plews, D. J., Laursen, P. B., Kilding, A. E., & Buchheit, M. (2013). Heart rate variability in elite triathletes: Is variation in variability the key to effective training? *European Journal of Applied Physiology, 113*(12), 3089-3099. [DOI: 10.1007/s00421-013-2727-4](https://doi.org/10.1007/s00421-013-2727-4)
- Buchheit, M. (2014). Monitoring training status with HR measures: Do all roads lead to Rome? *Frontiers in Physiology, 5*, 73. [DOI: 10.3389/fphys.2014.00073](https://doi.org/10.3389/fphys.2014.00073)

### Space Weather and Physiology

- Vieira, C. L. Z., Alvares, D., Blomberg, A., & Schwartz, J. (2022). Geomagnetic disturbances driven by solar activity enhance total and cardiovascular mortality risk in 263 U.S. cities. *Science of The Total Environment, 839*, 156312.
- Alabdulgader, A., McCraty, R., Atkinson, M., Dobyns, Y., Vainoras, A., Ragulskis, M., & Stolc, V. (2018). Long-term study of heart rate variability responses to changes in the solar and geomagnetic environment. *Scientific Reports, 8*(1), 2663.
- Vencloviene, J., Babarskiene, R., & Slapikas, R. (2020). The association between solar wind conditions and acute myocardial infarction risk. *International Journal of Environmental Research and Public Health, 17*(9), 3153.

### Physiological SMS and Combined Autonomic Assessment

- Porta, A., Castiglioni, P., Di Rienzo, M., et al. (2012). Short-term complexity indexes of heart period and systolic arterial pressure variabilities provide complementary information. *Journal of Applied Physiology, 113*(12), 1810-1820. [PMID: 23104699](https://pubmed.ncbi.nlm.nih.gov/23104699/)

- Lucini, D., Solaro, N., & Pagani, M. (2014). May autonomic indices from cardiovascular variability help identify hypertension? *Journal of Hypertension, 32*(2), 363-373. [PMID: 24232167](https://pubmed.ncbi.nlm.nih.gov/24232167/)

- Zhang, R., Hua, Z., Chen, C., Liu, G., & Wen, W. (2020). Analysis of autonomic nervous pattern in hypertension based on short-term HRV. *Biomedizinische Technik, 65*(4), 437-447. [PMID: 32769220](https://pubmed.ncbi.nlm.nih.gov/32769220/)

- Crowe, M., Meehan, M. T., & Jones, R. (2025). Comparison of rectal and gastrointestinal core temperatures during heat tolerance testing. *Medicina, 61*(6), 1111. [DOI: 10.3390/medicina61061111](https://doi.org/10.3390/medicina61061111)

- Zhang, Z., Guo, S., Xu, W., & Li, L. (2025). Research of physiological monitoring models in the military domain. *Proceedings of ICCNEA 2025*. [DOI: 10.1109/ICCNEA66167.2025.11211893](https://doi.org/10.1109/ICCNEA66167.2025.11211893)

- International Civil Aviation Organization. (2018). *Safety Management Manual* (Doc 9859, 4th ed.). [ICAO Store](https://store.icao.int/en/safety-management-manual-doc-9859)

- US Department of Defense. (2012). *MIL-STD-882E: Standard Practice for System Safety*. [PDF](https://safety.army.mil/Portals/0/Documents/ON-DUTY/SYSTEMSAFETY/Standard/MIL-STD-882E-change-1.pdf)

### Environmental Science and Extreme Weather

- Osczevski, R., & Bluestein, M. (2005). The new wind chill equivalent temperature chart. *Bulletin of the American Meteorological Society, 86*(10), 1453-1458.

- International Organization for Standardization. (2017). *ISO 7243:2017 -- Ergonomics of the thermal environment -- Assessment of heat stress using the WBGT index*.

- Steadman, R. G. (1979). The assessment of sultriness. Part I: A temperature-humidity index based on human physiology and clothing science. *Journal of Applied Meteorology, 18*, 861-873.

- Satish, U., Mendell, M. J., Shekhar, K., et al. (2012). Is CO2 an indoor pollutant? Direct effects of low-to-moderate CO2 concentrations on human decision-making performance. *Environmental Health Perspectives, 120*(12), 1671-1677. [DOI: 10.1289/ehp.1104789](https://doi.org/10.1289/ehp.1104789)

### Jet Lag and Circadian Disruption

- Waterhouse, J., Reilly, T., Atkinson, G., & Edwards, B. (2007). Jet lag: trends and coping strategies. *The Lancet, 369*(9567), 1117-1129. [PMID: 17398311](https://pubmed.ncbi.nlm.nih.gov/17398311/)

- Arendt, J. (2009). Managing jet lag: Some of the problems and possible new solutions. *Sleep Medicine Reviews, 13*(4), 249-256. [PMID: 19153053](https://pubmed.ncbi.nlm.nih.gov/19153053/)

- Burgess, H. J., Crowley, S. J., Gazda, C. J., Fogg, L. F., & Eastman, C. I. (2003). Preflight adjustment to eastward travel: 3 days of advancing sleep with and without morning bright light. *Journal of Biological Rhythms, 18*(4), 318-328. [PMID: 12932084](https://pubmed.ncbi.nlm.nih.gov/12932084/)

### Heart Rate Fragmentation

- PROOF-AF Study. (2025). Heart rate fragmentation and DFA-alpha1 predict atrial fibrillation in a community-dwelling cohort. *European Heart Journal Open, 5*(1), oeaf030.

### Radiation Exposure

- Zhang, S., Wimmer-Schweingruber, R. F., Yu, J., et al. (2020). First measurements of the radiation dose on the lunar surface. *Science Advances, 6*(39), eaaz1334. [DOI: 10.1126/sciadv.aaz1334](https://doi.org/10.1126/sciadv.aaz1334)
- Zeitlin, C., Hassler, D. M., Cucinotta, F. A., et al. (2013). Measurements of energetic particle radiation in transit to Mars on the Mars Science Laboratory. *Science, 340*(6136), 1080-1084. [DOI: 10.1126/science.1235989](https://doi.org/10.1126/science.1235989)
- Hassler, D. M., Zeitlin, C., Wimmer-Schweingruber, R. F., et al. (2014). Mars' surface radiation environment measured with the Mars Science Laboratory's Curiosity rover. *Science, 343*(6169), 1244797. [DOI: 10.1126/science.1244797](https://doi.org/10.1126/science.1244797)

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## License

MIT License — See [LICENSE](LICENSE) for details.

---

## Support

- **Full Documentation**: [docs/Manual.md](docs/Manual.md) — 6000+ lines of detailed instructions, examples, and science
- **Scientific Report**: [docs/HRV_Ventilatory_Threshold_Comprehensive_Scientific_Report.md](docs/HRV_Ventilatory_Threshold_Comprehensive_Scientific_Report.md)
- **Issues**: Open a [GitHub issue](https://github.com/strikerdlm/HRV/issues) for bugs or feature requests
- **Discussions**: Use [GitHub Discussions](https://github.com/strikerdlm/HRV/discussions) for questions
- **Changelog**: See [CHANGELOG.md](CHANGELOG.md) for detailed version history

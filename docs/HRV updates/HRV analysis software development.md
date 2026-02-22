---
updated: 2026-02-22T09:14:00
authors:
  - Dr Diego Malpica
tags:
  - HRV
  - sleep
  - Physiology
  - biomathematical
  - models
---



# HRV - Mission Control Flight Surgeon

## Project Overview

Mission Control - Flight Surgeon is a comprehensive, research-grade Heart Rate Variability (HRV) operations console designed specifically for aerospace medicine professionals, clinicians, researchers, pilots, and flight surgeons. This is an advanced physiological operations platform that integrates HRV analysis with circadian rhythm modeling, fatigue prediction, space weather intelligence, radiation exposure tracking, and AI-powered clinical interpretation.

**Repository:** https://github.com/strikerdlm/HRV
**Language:** Python
**Status:** Private
**Current Version:** 1.16.0
**License:** MIT

## Current Functionalities

### Core HRV Analysis
- **Time-Domain Metrics:** SDNN, RMSSD, pNN50, Mean HR, LnRMSSD, CVI, CSI
- **Frequency-Domain Analysis:** VLF, LF, HF power (ms² and n.u.), LF/HF ratio using Welch and AR methods
- **Nonlinear Analysis:** Poincaré SD1/SD2, DFA alpha1/alpha2, Sample/Approximate Entropy
- **Heart Rate Fragmentation (HRF):** PIP, IALS, PSS metrics from PROOF-AF study
- **Geometric Metrics:** HRV Triangular Index, TINN, Baevsky Stress Index
- **Sliding Window Analysis:** Time-varying metrics with deviation detection

### Advanced Features
- **Population Norms:** Age/sex-stratified percentile rankings against published normative data (Nunan et al. 2010, Ortega et al. 2024, MESA Study)
- **Ventilatory Threshold Estimation:** Non-invasive VT1/VT2 detection using DFA-alpha1 (r=0.93, SE<7 bpm accuracy)
- **Readiness Scoring:** Kubios-style parasympathetic index with baseline comparison
- **Autonomic Function Tests:** Valsalva ratio, deep breathing E:I, 30:15 standing ratio

### Aerospace Medicine Modules
- **Space Weather Monitoring:** Live NOAA SWPC and NASA DONKI feeds (Kp index, F10.7, solar wind, CME predictions)
- **Space Weather-HRV Correlation:** Lag-aware analysis (0-72h) with FDR correction
- **Radiation Exposure:** Evidence-based dose models for 10 environments (Earth to Mars transit)
- **Exploration Medical Record:** NASA ExMC/EIMO-aligned clinical logs
- **Space Weather Impact Predictions:** Exact arrival times for photon, SEP, plasma events

### Fatigue & Circadian Science
- **Circadian Physiology:** Forger99, Jewett99, Hannay19 mathematical models with actograms and DLMO prediction
- **SAFTE Fatigue Model:** Full implementation with reservoir dynamics, 1-7 day forecasting, Garmin Connect integration
- **FAST-Style Risk Metrics:** BAC equivalence, PVT lapse probability, color-coded risk zones
- **Integrated Physiological Model:** Log-linear fusion combining SAFTE + HRV/HRF + Workload + Environment
- **Trajectory Risk (Allostatic Load):** Multi-day physiological degradation detection

### Wearable Device Integration
- **Polar H10:** RR intervals (ECG-grade), VO2max via AccessLink API
- **Garmin Vivosmart 5:** Steps, sleep, SpO2, respiration, stress, body battery
- **ActiGraph GT3X:** Activity counts, raw acceleration, sleep/wake scoring
- **Somfit Pro:** EDF/EDF+ polysomnography, sleep staging, SpO2
- **FIT-to-CSV Tools:** Convert any Garmin FIT file

### Clinical Assessment
- **User Profile System:** Centralized biometrics, clinical scales (ESS, Samn-Perelli, KSS)
- **Personalized Health Metrics:** Body fat, sleep apnea risk (STOP-BANG), age-adjusted HRV norms
- **Blood Pressure Variability:** BPV metrics (SD, CV, ARV, SV) with HRV-BPV correlation
- **Laboratory Tracking:** CBC/Hemogram, blood chemistry, urinalysis

### AI & Machine Learning
- **GPT-5.2 Interpretation:** High-reasoning AI analysis with web-search citations
- **Advanced HRV Analytics:** ML pattern recognition, statistical tests, 7-day forecasting
- **Wearable Predictive Analytics:** Body Battery forecasting, Allostatic Load Index

### Environmental Monitoring
- **ICE Station Monitor:** Simulated Antarctic station with 8 environmental sensors
- **METAR Aviation Weather:** Real-time decoded METAR from any ICAO station
- **Wind Chill/Frostbite:** NWS 2001 formula with frostbite time estimation
- **WBGT Heat Stress:** ISO 7243:2017 simplified estimation
- **Jet Lag Performance:** Circadian resynchronization model

## Technical Stack

### Core Technologies
- **Python:** 3.10+ (recommended 3.12+)
- **Frontend:** Next.js 14, React, TypeScript, Tailwind CSS, Apache ECharts
- **Backend:** FastAPI with REST endpoints
- **Database:** SQLite for persistence
- **Visualization:** Streamlit, Plotly, ECharts

### Key Libraries
- numpy, scipy, pandas for scientific computing
- scikit-learn for ML analytics
- neurokit2, hrv-analysis for HRV computation
- astropy for astronomical calculations
- circadian (Arcascope) for rhythm modeling

### Architecture
- **Dual Interface:** Streamlit research app + TypeScript/Next.js production frontend
- **Three Entry Points:**
  - Operational: `app/operational_app.py` (fast clinical workflows)
  - Research: `app/research_app.py` (full dashboards)
  - Data Science: `app/space_weather_ds_app.py` (single-user space weather)

## Next Steps for Development

### High-Priority Enhancements
1. **Multi-User Production Deployment**
   - Complete authentication and authorization system
   - Role-based access control (RBAC) for clinical teams
   - HIPAA compliance features for medical data
   - Multi-tenant database architecture

2. **Real-Time Streaming Integration**
   - Expand BLE heart rate monitor support beyond Polar H10
   - WebSocket implementation for live dashboard updates
   - Integration with hospital telemetry systems
   - Mobile app companion for field data collection

3. **Advanced ML Capabilities**
   - Supervised learning for arrhythmia detection
   - Transfer learning from clinical datasets
   - Federated learning for multi-institution collaboration
   - AutoML for personalized model optimization

4. **Enhanced Aerospace Features**
   - G-force tolerance prediction integration
   - Hypoxia risk assessment module
   - Decompression sickness probability models
   - EVA (spacewalk) readiness scoring

### Research & Validation
5. **Clinical Validation Studies**
   - Multi-center validation trials
   - Comparison against gold-standard equipment
   - Publication in peer-reviewed journals
   - FDA/CE marking pathway exploration

6. **Population Norms Expansion**
   - Integrate additional international datasets
   - Age-specific models for pediatric/geriatric populations
   - Ethnicity-adjusted reference ranges
   - Athlete-specific normative data

### User Experience
7. **Mobile Application**
   - Native iOS/Android apps
   - Offline analysis capabilities
   - Push notifications for anomaly detection
   - Wearable sync management

8. **Educational Resources**
   - Interactive tutorials for medical students
   - Webinar series on aerospace medicine
   - Case study library
   - Certification program for flight surgeons

## Recommended Improvements

### Code Quality & Maintainability
- **Comprehensive Test Suite:** Expand pytest coverage to >90% (currently scattered)
- **Type Hints:** Complete type annotation across all modules
- **Documentation:** Auto-generate API docs with Sphinx
- **CI/CD Pipeline:** Automated testing, linting, and deployment

### Performance Optimization
- **Database Optimization:** Migrate to PostgreSQL for production environments
- **Caching Layer:** Implement Redis for frequently accessed computations
- **Async Processing:** Leverage FastAPI async capabilities throughout
- **GPU Acceleration:** Expand CUDA utilization beyond current implementations

### Security & Compliance
- **Data Encryption:** At-rest and in-transit encryption for PHI
- **Audit Logging:** Comprehensive activity logs for medical records
- **GDPR Compliance:** Data privacy controls for European deployment
- **Penetration Testing:** Third-party security assessment

### Scientific Rigor
- **Reproducibility:** Version control for analysis pipelines
- **Statistical Methods:** Bayesian approaches for uncertainty quantification
- **Cross-Validation:** K-fold validation for ML models
- **Effect Size Reporting:** Cohen's d, eta-squared for all comparisons

### Interoperability
- **FHIR Integration:** HL7 FHIR API for EHR connectivity
- **DICOM Support:** Import/export medical imaging data
- **Standard Formats:** Support for PhysioNet, EDF+, MIT-BIH formats
- **Cloud Platforms:** AWS HealthLake, Azure Health Data Services compatibility

### User Feedback & Usability
- **A/B Testing:** Feature flag system for UI experiments
- **User Analytics:** Privacy-respecting usage telemetry
- **Accessibility:** WCAG 2.1 AA compliance
- **Internationalization:** Multi-language support (Spanish, French, German)

## Scientific Foundation

All metrics and interpretations are grounded in peer-reviewed literature with explicit citations to:
- Task Force 1996 (Heart rate variability standards)
- Shaffer & Ginsberg 2017 (HRV metrics overview)
- Convertino et al. 2020 (Space weather-physiology correlations)
- Hursh et al. 2004 (SAFTE fatigue model)
- Forger et al. 1999 (Circadian rhythm modeling)

The platform includes 100+ scientific references with PMID/DOI identifiers for full traceability.

---

## Deep research update (2020–2026): HRV computation + cognition/outcomes

### Research plan (repeatable, “living” protocol)

- **Scope**: HRV computation methods (preprocessing → metrics) and peer‑reviewed evidence linking HRV ↔ cognition / performance outcomes (especially aviation & operational contexts).
- **Databases**: PubMed (PMID/PMCID), Semantic Scholar, and open-access full text (PMC/HAL/MDPI).
- **Inclusion**:
  - Human studies or validated methods papers
  - HRV computed from ECG RR/NN or validated PPG inter‑beat intervals (IBI)
  - Clear window duration and preprocessing described
  - Cognition/outcome endpoints: executive function, mental workload, fatigue, reaction time, situational awareness, training completion
- **Extraction**:
  - Window length, posture, respiration control/estimation, artifact strategy, frequency method (Welch/AR/Lomb–Scargle), nonlinear parameters (m, r, scales)
  - Primary quantitative results (effect size, ICC/LoA, OR/HR, model performance)
- **Quality checks**:
  - Report confounders: age/sex, breathing, posture, sleep, medication/caffeine, signal quality
  - Prefer within‑subject baselines and reactivity/recovery designs for operational inference

### What’s materially “new” for the software stack (vs older HRV summaries)

#### 1) Artifact correction is not a footnote — it can change the metric itself

- **Robust ectopic/artifact detection** (RR/NN time series) can reach very high sensitivity/specificity when using adaptive thresholds + beat classification. This is directly software-implementable and outperforms many static-threshold heuristics. See [“A robust algorithm for HRV time series artefact correction…” (Lipponen & Tarvainen, 2019)](https://pubmed.ncbi.nlm.nih.gov/31314618/) and DOI [10.1080/03091902.2019.1640306](https://doi.org/10.1080/03091902.2019.1640306).
- **Filter strength matters**: applying “very strong” threshold-based correction in Kubios-style pipelines can significantly change time, frequency, and nonlinear metrics (including DFA). This implies your console should (a) log the correction regime, and (b) report sensitivity to the chosen correction level. See [Scientific Reports 2024 artifact filter level impact](https://doi.org/10.1038/s41598-024-76287-z).

**Implementation takeaways**
- Store both **raw NN** and **cleaned NN** series; compute metrics on both (or at least report % edited beats).
- For mobile/field data, prefer **exclusion** over aggressive interpolation when doing uneven-sampling spectral methods (see Lomb–Scargle section below).

#### 2) Ultra‑short HRV is now operationally useful, but only for specific metrics and under constraints

Peer‑reviewed evidence has converged on a pragmatic rule: **time‑domain vagal indices (especially lnRMSSD)** can be meaningfully estimated from ~60 s windows in many contexts; frequency‑domain indices need longer windows and careful respiration handling.

- **UST validity/reliability** improves with longer duration and is more sensitive to confounders (respiration, CO₂, BP) at short durations. Time‑domain metrics can be acceptable at ≥60 s, while relative frequency-domain metrics typically require longer durations. See [Burma et al., 2021](https://doi.org/10.1152/japplphysiol.00955.2020).
- **Stationarity is a key hidden constraint**: non‑stationary RR segments in 1–2 min windows can bias UST HRV in athletes; using a stationarity test (e.g., ADF) or simpler drift checks is recommended before trusting UST outputs. See [Gąsior et al., 2025](https://doi.org/10.2478/bhk-2025-0027).

**Implementation takeaways**
- Provide “UST modes” that explicitly restrict which metrics are computed:
  - **Allowed (UST)**: mean HR, mean NN, RMSSD/lnRMSSD, pNN50 (context-dependent)
  - **Caution**: SDNN (needs more data for stability), HF/LF band powers (need longer + respiration)
- Add a **stationarity gate** per window (pass/fail + reason), and do not silently compute “high‑precision” outputs from non‑stationary windows.

#### 3) Frequency-domain computation: Welch (resampled) vs Lomb–Scargle (uneven sampling) — the preprocessing rules differ

- Many HRV pipelines resample/interpolate to a uniform grid before Welch/FFT. This can be convenient but can also **distort** the spectrum, especially when “editing” suspect points.
- For irregular/noisy clinical data, Lomb–Scargle is attractive because it operates directly on uneven sampling. But common “edit/replace/interpolate” practices can mislead spectral interpretation: suspicious points should be **excluded rather than edited**, and denoising can be done via **empirical mode decomposition**; a **false alarm probability** metric can help validate whether spectral estimates are meaningful. See [Stewart et al., 2020 (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC7738214/) and DOI [10.1155/2020/8862074](https://doi.org/10.1155/2020/8862074).
- For cardiovagal RSA/HF analysis, Lomb–Scargle without resampling can detect posture-related effects and improve regression relationships vs FFT/AR in some settings. See [Mestanik et al., 2019](https://doi.org/10.1016/j.resp.2018.08.002).

**Implementation takeaways**
- Offer two frequency pipelines:
  - **Pipeline A (Welch)**: interpolate evenly sampled tachogram (document interpolation rate + method).
  - **Pipeline B (Lomb–Scargle)**: do not interpolate; **exclude** suspect intervals; compute PSD with LSP + band integration; compute a validity score (e.g., FAP proxy).

#### 4) Wearables/PPG: “valid enough” for some HRV use cases at rest; HF is the first casualty in motion

- Contemporary validation papers show good agreement for **HR and selected time-domain HRV at rest**, but warn about **high-frequency HRV** under motion/ecologically valid contexts. See, for example, [PPG finger sensor validity (Sports, 2025; PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC11861371/) and DOI [10.3390/sports13020029](https://doi.org/10.3390/sports13020029).
- For wearable implementation details, microcontroller-friendly filtering choices can materially impact interchangeability with ECG-derived frequency bands; e.g., zero-phase Butterworth at ≥500 Hz was reported as a good fidelity/efficiency trade-off in a pilot dataset. See [PPG-HRV filtering study (Sensors, 2025; PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC12656279/) and DOI [10.3390/s25227091](https://doi.org/10.3390/s25227091).

**Implementation takeaways**
- Always compute and persist a **signal quality index** per window (PPG especially).
- In operational dashboards, “HF power” from PPG should be presented with a **confidence/quality flag**.

---

## HRV ↔ cognition / performance outcomes (what you can credibly predict)

### 1) Executive function (trait-level cognition): small but robust association

A 2022 systematic review/meta-analysis of correlational studies found a **small positive association** between **vagally mediated HRV** (HF/RMSSD/RSA) and executive functioning:

- Pooled effect: \(r = 0.19\) (95% CI 0.15–0.23). See [Magnon et al., 2022 (HAL PDF)](https://hal.science/hal-03851527/file/Magnon_et_al_DoesHeartRateVariability_Ctx_2022.pdf) and DOI [10.1016/j.cortex.2022.07.008](https://doi.org/10.1016/j.cortex.2022.07.008).
- Moderator insight: vagally mediated HRV predicted **inhibition** and **cognitive flexibility** more than **working memory**, and was moderated by HRV measure and age. [Magnon et al., 2022](https://hal.science/hal-03851527/file/Magnon_et_al_DoesHeartRateVariability_Ctx_2022.pdf)

**What this means for Mission Control**
- Resting vmHRV is best treated as a **risk factor / resilience marker**, not a deterministic “cognition meter.”
- The highest yield in operations is usually **within-person change** (baseline → task/stressor → recovery), not raw cross-sectional comparisons.

### 2) Pilot mental workload: detectable, but context and methods drive heterogeneity

A 2024 systematic review focused on pilots reported:

- **29 included papers**, common HRV features: HR, SDNN, RMSSD, LF, HF, LF/HF, with broad heterogeneity. [Wang et al., 2024](https://www.mdpi.com/1424-8220/24/12/3723)
- Typical directional pattern: **HR increases** and **HRV decreases** with higher mental workload, but individual features (notably **LF/HF**) show inconsistent results across studies. [Wang et al., 2024](https://www.mdpi.com/1424-8220/24/12/3723)
- ML models used include SVM/MLP/RF/KNN/LDA; reported binary classification accuracy can exceed ~90% in some setups, but real-flight validation remains a major gap. [Wang et al., 2024](https://www.mdpi.com/1424-8220/24/12/3723)

**What this means for Mission Control**
- Workload inference should be **multimodal** (HRV + respiration proxy + EDA/behavioral) and should explicitly model **task context**.

### 3) Operational aviation outcomes: HRV can predict training/selection and operator state in specific settings

- **Pilot training completion**: pre-training **RMSSD** derived from a **10‑second ECG** predicted completion of an intensive pilot course; completers had higher RMSSD in a matched analysis. See [Kula et al., 2025 (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC12331047/) and DOI [10.1371/journal.pone.0327406](https://doi.org/10.1371/journal.pone.0327406).
- **Situational awareness prediction** (air traffic/remote tower simulation): HRV features (including LF/HF) combined with eye-tracking improved prediction of SA (adjusted \(R^2 \approx 0.78\) reported). See [Pan et al., 2025 (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC11991212/) and DOI [10.3390/s25072052](https://doi.org/10.3390/s25072052).

### 4) Stress / fatigue / reaction time: HRV is most useful when anchored to a known stressor

- Acute mental stress + cognitive tasks show that **integrating respiration** can materially change which HRV indices are significant; nonlinear metrics (e.g., SampEn) may be task-specific. See [Coelli et al., 2026 (PubMed)](https://pubmed.ncbi.nlm.nih.gov/41507329/) and DOI [10.1038/s41598-025-34921-4](https://doi.org/10.1038/s41598-025-34921-4).
- Workplace fatigue: associations between HRV and reaction time/fatigue indicators have been reported in high-demand occupations (e.g., wildland firefighters). See [Jeklin et al., 2021](https://doi.org/10.1007/s00420-020-01641-3).
- Environmental stress: cognitive performance under heat exposure has been modeled using time-domain HRV, with RMSSD highlighted as a key correlate in that experiment. See [Zhu et al., 2024](https://doi.org/10.1177/1420326X241284031).

---

## Expected outcomes you can extract (and how to represent them safely)

### Outcome families (recommended product primitives)

- **Trait resilience / selection (low-frequency updates)**:
  - Inputs: resting vmHRV (lnRMSSD, HF), demographics, baseline sleep
  - Output: percentile / risk band + uncertainty (not a binary label)
  - Evidence example: pilot course completion prediction with RMSSD. [Kula et al., 2025](https://pmc.ncbi.nlm.nih.gov/articles/PMC12331047/)
- **State workload (high-frequency updates, task-contextual)**:
  - Inputs: reactivity + recovery deltas (ΔlnRMSSD, ΔHF), HR, respiration proxy, EDA
  - Output: probability of “high workload” + confidence flag (driven by signal quality)
  - Evidence example: pilot MWL systematic review. [Wang et al., 2024](https://www.mdpi.com/1424-8220/24/12/3723)
- **State fatigue / degraded cognition risk (contextual)**:
  - Inputs: sleep deprivation markers + HRV trend + reaction-time probes
  - Output: risk of lapses / slowed RT (calibrated per person)
  - Evidence examples: sleep deprivation HRV meta-analysis (RMSSD decrease) and occupational fatigue links. [Zhang et al., 2025](https://pmc.ncbi.nlm.nih.gov/articles/PMC12394884) [Jeklin et al., 2021](https://doi.org/10.1007/s00420-020-01641-3)

---

## Mathematics: metric definitions (implementation-precise)

Let \(RR_i\) be the i-th normal-to-normal interval (NN) in **seconds**; \(N\) is the number of intervals.

### Time-domain

- **MeanNN**: \(\overline{RR} = \frac{1}{N}\sum_{i=1}^{N} RR_i\)
- **SDNN**: \(\mathrm{SDNN}=\sqrt{\frac{1}{N-1}\sum_{i=1}^{N}(RR_i-\overline{RR})^2}\)
- **RMSSD**:
\[
\mathrm{RMSSD}=\sqrt{\frac{1}{N-1}\sum_{i=1}^{N-1}(RR_{i+1}-RR_i)^2}
\]
- **pNN50** (if RR in seconds, 50 ms = 0.05 s):
\[
\mathrm{pNN50}=\frac{1}{N-1}\sum_{i=1}^{N-1}\mathbf{1}\left(|RR_{i+1}-RR_i|>0.05\right)
\]
- **lnRMSSD**: \(\ln(\mathrm{RMSSD})\) (use natural log)

### Frequency-domain (band powers)

Given a power spectral density estimate \(S(f)\), band power for band \(B=[f_1,f_2]\) is:
\[
P_B=\int_{f_1}^{f_2} S(f)\,df
\]
Standard short-term HRV bands:
- VLF: 0.0033–0.04 Hz
- LF: 0.04–0.15 Hz
- HF: 0.15–0.4 Hz

### Poincaré (nonlinear geometry)

Define \(\Delta RR_i = RR_{i+1}-RR_i\).

- \(SD1 = \sqrt{\frac{1}{2}}\;\mathrm{SD}(\Delta RR)\)
- \(SD2 = \sqrt{2\cdot SDNN^2 - \frac{1}{2}\cdot \mathrm{SD}(\Delta RR)^2}\)

### Sample Entropy (SampEn)

Given embedding dimension \(m\) and tolerance \(r\):

- Build vectors \(u_i=[RR_i,RR_{i+1},...,RR_{i+m-1}]\)
- Count matches using Chebyshev distance \(d_\infty(u_i,u_j)=\max_k |u_{i,k}-u_{j,k}|\)
- Let \(A\) be number of matches for \(m+1\), \(B\) for \(m\). Then:
\[
\mathrm{SampEn}(m,r)=-\ln\left(\frac{A}{B}\right)
\]

### DFA (Detrended Fluctuation Analysis)

Compute integrated series \(y(k)=\sum_{i=1}^{k}(RR_i-\overline{RR})\). For window size \(n\), detrend each segment with a linear fit and compute RMS fluctuation \(F(n)\). DFA exponent \(\alpha\) is the slope of \(\log F(n)\) vs \(\log n\) over chosen scales (e.g., \(\alpha_1\) short-term).

---

## Reference Python code (deterministic, bounded, “drop-in”)

The snippets below are written to be directly portable into your `FastAPI` backend HRV engine and unit-tested against Kubios/neurokit2 outputs.

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

import math

import numpy as np
from numpy.typing import NDArray
from scipy import signal


RRArray = NDArray[np.float64]


@dataclass(frozen=True, slots=True)
class HrvBandPowers:
    """Frequency band powers for short-term HRV (seconds-based input)."""

    vlf: float
    lf: float
    hf: float
    total_power: float


def _as_float64_1d(x: Iterable[float]) -> RRArray:
    arr = np.asarray(list(x), dtype=np.float64)
    if arr.ndim != 1:
        raise ValueError("Expected 1D RR/NN sequence.")
    if arr.size < 3:
        raise ValueError("Need at least 3 RR intervals for HRV metrics.")
    if not np.isfinite(arr).all():
        raise ValueError("RR/NN contains non-finite values.")
    return arr


def quality_mask_basic(
    rr_s: RRArray,
    *,
    min_rr_s: float = 0.30,
    max_rr_s: float = 2.00,
    max_abs_diff_s: float = 0.20,
) -> NDArray[np.bool_]:
    """Basic RR quality mask.

    Marks intervals as "valid" if they are in [min_rr_s, max_rr_s] and if local
    successive differences are not extreme.

    This is intentionally conservative and bounded. For production, replace/extend
    with an adaptive classifier (e.g., Lipponen & Tarvainen 2019).
    """
    if min_rr_s <= 0.0 or max_rr_s <= min_rr_s:
        raise ValueError("Invalid RR bounds.")
    if max_abs_diff_s <= 0.0:
        raise ValueError("max_abs_diff_s must be > 0.")

    valid = (rr_s >= min_rr_s) & (rr_s <= max_rr_s)
    d = np.diff(rr_s)
    # mark both endpoints of extreme jumps as invalid
    jump = np.abs(d) > max_abs_diff_s
    if jump.size:
        valid[:-1] &= ~jump
        valid[1:] &= ~jump
    return valid


def interpolate_invalid_linear(rr_s: RRArray, valid: NDArray[np.bool_]) -> RRArray:
    """Linearly interpolate invalid RR intervals (bounded; no extrapolation)."""
    if rr_s.shape != valid.shape:
        raise ValueError("rr_s and valid must have same shape.")
    if valid.sum() < 3:
        raise ValueError("Too few valid RR intervals to interpolate.")

    idx = np.arange(rr_s.size, dtype=np.float64)
    out = rr_s.copy()
    out[~valid] = np.interp(idx[~valid], idx[valid], rr_s[valid])
    return out


def rmssd(rr_s: Iterable[float]) -> float:
    rr = _as_float64_1d(rr_s)
    d = np.diff(rr)
    return float(np.sqrt(np.mean(d * d)))


def lnrMSSD(rr_s: Iterable[float]) -> float:
    value = rmssd(rr_s)
    if value <= 0.0:
        raise ValueError("RMSSD must be > 0 to take log.")
    return float(math.log(value))


def sdnn(rr_s: Iterable[float]) -> float:
    rr = _as_float64_1d(rr_s)
    return float(np.std(rr, ddof=1))


def pnn50(rr_s: Iterable[float]) -> float:
    rr = _as_float64_1d(rr_s)
    d = np.abs(np.diff(rr))
    return float(np.mean(d > 0.05))


def poincare_sd1_sd2(rr_s: Iterable[float]) -> tuple[float, float]:
    rr = _as_float64_1d(rr_s)
    d = np.diff(rr)
    sdnn_v = np.std(rr, ddof=1)
    sdd_v = np.std(d, ddof=1) if d.size > 1 else 0.0
    sd1 = math.sqrt(0.5) * float(sdd_v)
    sd2_sq = (2.0 * (sdnn_v**2)) - (0.5 * (sdd_v**2))
    sd2 = float(math.sqrt(sd2_sq)) if sd2_sq > 0.0 else 0.0
    return sd1, sd2


def bandpowers_welch(
    rr_s: Iterable[float],
    *,
    fs_hz: float = 4.0,
    vlf: tuple[float, float] = (0.0033, 0.04),
    lf: tuple[float, float] = (0.04, 0.15),
    hf: tuple[float, float] = (0.15, 0.40),
) -> HrvBandPowers:
    """Welch band powers from an interpolated RR tachogram.

    Notes:
    - RR intervals are unevenly sampled; we convert to an evenly sampled series via
      linear interpolation of RR(t) and then apply Welch PSD.
    - This is convenient but can be distorted by aggressive RR editing.
    """
    rr = _as_float64_1d(rr_s)
    if fs_hz <= 0.0:
        raise ValueError("fs_hz must be > 0.")

    t = np.cumsum(rr)
    t = t - t[0]
    t_uniform = np.arange(0.0, float(t[-1]), 1.0 / fs_hz, dtype=np.float64)
    if t_uniform.size < 16:
        raise ValueError("Recording too short for Welch PSD at this fs.")

    rr_uniform = np.interp(t_uniform, t, rr)
    rr_uniform = rr_uniform - float(np.mean(rr_uniform))

    f, pxx = signal.welch(rr_uniform, fs=fs_hz, nperseg=min(256, rr_uniform.size))
    return _integrate_bands(f, pxx, vlf=vlf, lf=lf, hf=hf)


def _integrate_bands(
    f_hz: RRArray,
    pxx: RRArray,
    *,
    vlf: tuple[float, float],
    lf: tuple[float, float],
    hf: tuple[float, float],
) -> HrvBandPowers:
    def band_power(band: tuple[float, float]) -> float:
        lo, hi = band
        if not (0.0 <= lo < hi):
            raise ValueError("Invalid band.")
        m = (f_hz >= lo) & (f_hz < hi)
        if not np.any(m):
            return 0.0
        return float(np.trapz(pxx[m], f_hz[m]))

    vlf_p = band_power(vlf)
    lf_p = band_power(lf)
    hf_p = band_power(hf)
    total = float(np.trapz(pxx[(f_hz >= vlf[0]) & (f_hz < hf[1])], f_hz[(f_hz >= vlf[0]) & (f_hz < hf[1])]))
    return HrvBandPowers(vlf=vlf_p, lf=lf_p, hf=hf_p, total_power=total)


def sample_entropy(
    rr_s: Iterable[float],
    *,
    m: int = 2,
    r_ratio: float = 0.20,
    max_n: int = 5000,
) -> float:
    """Sample entropy (SampEn) with Chebyshev distance.

    Complexity is O(N^2 * m) and bounded via max_n.
    """
    rr = _as_float64_1d(rr_s)
    if rr.size > max_n:
        raise ValueError(f"RR length {rr.size} exceeds max_n={max_n}.")
    if m < 1:
        raise ValueError("m must be >= 1.")
    if not (0.0 < r_ratio < 1.0):
        raise ValueError("r_ratio must be in (0, 1).")

    sd = float(np.std(rr, ddof=1))
    if sd <= 0.0:
        raise ValueError("RR standard deviation must be > 0 for SampEn.")
    r = r_ratio * sd

    n = rr.size
    # counts for matches of length m and m+1
    b = 0
    a = 0

    # bounded loops; avoid large intermediate arrays
    for i in range(0, n - (m + 1)):
        xi_m = rr[i : i + m]
        xi_m1 = rr[i : i + m + 1]
        for j in range(i + 1, n - (m + 1)):
            xj_m = rr[j : j + m]
            if float(np.max(np.abs(xi_m - xj_m))) <= r:
                b += 1
                xj_m1 = rr[j : j + m + 1]
                if float(np.max(np.abs(xi_m1 - xj_m1))) <= r:
                    a += 1

    if b == 0 or a == 0:
        raise ValueError("Insufficient matches to compute SampEn (increase N or adjust r).")
    return float(-math.log(a / b))


def dfa_alpha(
    rr_s: Iterable[float],
    *,
    scales: Iterable[int] = (4, 5, 6, 8, 10, 12, 16),
) -> float:
    """DFA alpha over provided beat-length scales."""
    rr = _as_float64_1d(rr_s)
    x = rr - float(np.mean(rr))
    y = np.cumsum(x)

    scales_list = [int(s) for s in scales]
    if any(s < 4 for s in scales_list):
        raise ValueError("All DFA scales must be >= 4.")

    fn: list[float] = []
    nn: list[float] = []

    for n in scales_list:
        k = (y.size // n) * n
        if k < n * 2:
            continue  # need at least 2 windows
        yk = y[:k]
        y_seg = yk.reshape((-1, n))

        # detrend each segment with linear fit
        t = np.arange(n, dtype=np.float64)
        t_mean = float(np.mean(t))
        t_var = float(np.sum((t - t_mean) ** 2))
        if t_var <= 0.0:
            raise RuntimeError("Unexpected DFA time variance.")

        rms2: list[float] = []
        for seg in y_seg:
            seg_mean = float(np.mean(seg))
            cov = float(np.sum((t - t_mean) * (seg - seg_mean)))
            slope = cov / t_var
            intercept = seg_mean - slope * t_mean
            trend = slope * t + intercept
            resid = seg - trend
            rms2.append(float(np.mean(resid * resid)))

        fn.append(float(math.sqrt(float(np.mean(rms2)))))
        nn.append(float(n))

    if len(fn) < 3:
        raise ValueError("Not enough valid DFA scales for regression.")

    log_n = np.log(np.asarray(nn, dtype=np.float64))
    log_f = np.log(np.asarray(fn, dtype=np.float64))
    A = np.vstack([log_n, np.ones_like(log_n)]).T
    slope, _intercept = np.linalg.lstsq(A, log_f, rcond=None)[0]
    return float(slope)


def extract_hrv_features(rr_s: Iterable[float]) -> Mapping[str, float]:
    rr = _as_float64_1d(rr_s)
    valid = quality_mask_basic(rr)
    rr_clean = interpolate_invalid_linear(rr, valid)

    sd1, sd2 = poincare_sd1_sd2(rr_clean)
    bp = bandpowers_welch(rr_clean)

    return {
        "n_beats": float(rr.size),
        "pct_interpolated": float(1.0 - (float(valid.mean()))),
        "mean_nn_s": float(np.mean(rr_clean)),
        "sdnn_s": sdnn(rr_clean),
        "rmssd_s": rmssd(rr_clean),
        "lnrmssd": lnrMSSD(rr_clean),
        "pnn50": pnn50(rr_clean),
        "sd1_s": float(sd1),
        "sd2_s": float(sd2),
        "vlf": bp.vlf,
        "lf": bp.lf,
        "hf": bp.hf,
        "total_power": bp.total_power,
        # nonlinear examples (bounded; may raise if too-short)
        "sampen_m2_r02": sample_entropy(rr_clean, m=2, r_ratio=0.20),
        "dfa_alpha_short": dfa_alpha(rr_clean),
    }
```

---

## Roadmap: implementation in Mission Control (engineering + validation)

### Phase 0 — Make computation reproducible (1–2 weeks)

- **Define canonical units**: RR/NN stored in seconds; convert at UI edge.
- **Metric contract**: every metric records:
  - window length, posture, time-of-day, device type (ECG/PPG), preprocessing strategy
  - % edited/excluded beats, stationarity pass/fail, signal quality score
- **Golden datasets**: add a small suite of RR segments (clean + injected artifacts) and expected metric outputs (cross-checked with Kubios/neurokit2).

### Phase 1 — Dual spectral pipeline (2–4 weeks)

- Implement **Welch pipeline** (current) + **Lomb–Scargle pipeline** for uneven sampling.
- Add a “frequency validity” score (e.g., FAP proxy + minimum duration gate). [Stewart et al., 2020](https://pmc.ncbi.nlm.nih.gov/articles/PMC7738214/)

### Phase 2 — UST mode + stationarity gating (2–3 weeks)

- Add explicit **UST profile presets** (e.g., 60 s, 120 s) that compute only supported metrics.
- Add stationarity checks per window and UI warnings. [Gąsior et al., 2025](https://doi.org/10.2478/bhk-2025-0027) [Burma et al., 2021](https://doi.org/10.1152/japplphysiol.00955.2020)

### Phase 3 — Cognition/workload modeling (4–8+ weeks, needs data)

- Add a **task annotation layer**: baseline/task/recovery segments + task label (e.g., n-back, Stroop, ATC simulation).
- Start with simple, interpretable models:
  - within-person z-scores of lnRMSSD/HF + HR + respiration proxy
  - mixed-effects models for person-level random intercepts
- Expand to ML only after:
  - proper splits (subject-level), calibration, and real-world validation. [Wang et al., 2024](https://www.mdpi.com/1424-8220/24/12/3723)

### Phase 4 — Aviation readiness primitives (ongoing)

- Implement operational outputs as **probabilities + uncertainty**, not single-point “scores”:
  - workload risk, fatigue risk, recovery debt
- Validate against outcomes:
  - training completion proxies, SA probes, RT probes. [Kula et al., 2025](https://pmc.ncbi.nlm.nih.gov/articles/PMC12331047/) [Pan et al., 2025](https://pmc.ncbi.nlm.nih.gov/articles/PMC11991212/)

---

## Sources (selected, peer-reviewed; accessed Feb 2026)

- [Does heart rate variability predict better executive functioning? (HAL PDF)](https://hal.science/hal-03851527/file/Magnon_et_al_DoesHeartRateVariability_Ctx_2022.pdf) — DOI: [10.1016/j.cortex.2022.07.008](https://doi.org/10.1016/j.cortex.2022.07.008) (2022)
- [Detecting and Predicting Pilot Mental Workload Using HRV: A Systematic Review (MDPI)](https://www.mdpi.com/1424-8220/24/12/3723) (2024)
- [Application of the Lomb–Scargle Periodogram to Investigate HRV during Haemodialysis (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC7738214/) — DOI: [10.1155/2020/8862074](https://doi.org/10.1155/2020/8862074) (2020)
- [A robust algorithm for HRV time series artefact correction (PubMed)](https://pubmed.ncbi.nlm.nih.gov/31314618/) — DOI: [10.1080/03091902.2019.1640306](https://doi.org/10.1080/03091902.2019.1640306) (2019)
- [The validity and reliability of ultra-short-term HRV parameters (DOI)](https://doi.org/10.1152/japplphysiol.00955.2020) (2021)
- [Time series stationarity for ultra-short-term HRV (DOI)](https://doi.org/10.2478/bhk-2025-0027) (2025)
- [Pre-training HRV predicts Air Force Academy completion (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC12331047/) — DOI: [10.1371/journal.pone.0327406](https://doi.org/10.1371/journal.pone.0327406) (2025)
- [Situational awareness prediction with eye-tracking + HRV (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC11991212/) — DOI: [10.3390/s25072052](https://doi.org/10.3390/s25072052) (2025)
- [Modulation of autonomic responses to cognitive tasks under acute mental stress (PubMed)](https://pubmed.ncbi.nlm.nih.gov/41507329/) — DOI: [10.1038/s41598-025-34921-4](https://doi.org/10.1038/s41598-025-34921-4) (2026)
- [Workplace fatigue links HRV and reaction time in firefighters (DOI)](https://doi.org/10.1007/s00420-020-01641-3) (2021)
- [Cognitive performance in the heat predicted with HRV time-domain indices (DOI)](https://doi.org/10.1177/1420326X241284031) (2024)
- [Threshold-based artifact correction can change HRV metrics (DOI)](https://doi.org/10.1038/s41598-024-76287-z) (2024)
- [Sleep deprivation effects on HRV: systematic review & meta-analysis (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC12394884) (2025)
- [RSA spectral analysis without resampling using Lomb–Scargle (DOI)](https://doi.org/10.1016/j.resp.2018.08.002) (2019)
- [PPG finger sensor HRV validity (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC11861371/) — DOI: [10.3390/sports13020029](https://doi.org/10.3390/sports13020029) (2025)
- [PPG-HRV filtering (Butterworth ≥500 Hz) (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC12656279) — DOI: [10.3390/s25227091](https://doi.org/10.3390/s25227091) (2025)

## updates2026.md — Research notes + implementation roadmap (append-only)

**Created:** 2025-12-23  
**Scope:** Heart Rate Fragmentation (HRF) literature; biomathematical human performance models; open-source simulation stacks for UAV/combat-scenario research; and an implementation plan for this repository.

---

## 1) Heart Rate Fragmentation (HRF): what it is and why it matters

### 1.1 Definition (conceptual)
Heart Rate Fragmentation (HRF) describes **frequent, rapid alternations in the direction of beat-to-beat interval changes** (RR “accelerations/decelerations”), interpreted as a marker of **sinoatrial pacemaker/beat-to-beat control fragmentation** that is **not fully explained by autonomic modulation** (i.e., distinct from classic vagal HRV features).

### 1.2 Canonical HRF metrics (as used in the Costa/Goldberger framework)
Common metrics include:
- **PIP**: percentage of inflection points (direction changes).
- **IALS**: inverse average length of acceleration/deceleration segments.
- **PSS / PAS**: percent short segments / alternating segments.
- “Word” distributions (e.g., W0–W3) from symbolic encodings of inflection patterns.

Core methodological sources:
- Costa, M. D., Davis, R. B., & Goldberger, A. L. (2017). *Heart Rate Fragmentation: A New Approach to the Analysis of Cardiac Interbeat Interval Dynamics.* **Frontiers in Physiology, 8**, 255. https://doi.org/10.3389/fphys.2017.00255 (PMID: 28536533)
- Costa, M. D., Davis, R. B., & Goldberger, A. L. (2017). *Heart Rate Fragmentation: A Symbolic Dynamical Approach.* **Frontiers in Physiology, 8**, 827. https://doi.org/10.3389/fphys.2017.00827 (PMID: 29184505)

### 1.3 HRF as a marker of “biological aging” / pacemaker dynamics
- Costa, M. D., & Goldberger, A. L. (2019). *Heart rate fragmentation: using cardiac pacemaker dynamics to probe the pace of biological aging.* **American Journal of Physiology-Heart and Circulatory Physiology, 316**(6), H1341–H1344. https://doi.org/10.1152/ajpheart.00110.2019 (PMID: 30951362)

### 1.4 HRF for event prediction (atrial fibrillation; cardiovascular risk signals)
Evidence that HRF features can add predictive value beyond conventional HRV:
- Costa, M. D., Redline, S., Soliman, E. Z., Goldberger, A. L., & Heckbert, S. R. (2021). *Fragmented sinoatrial dynamics in the prediction of atrial fibrillation: the Multi-Ethnic Study of Atherosclerosis.* **American Journal of Physiology-Heart and Circulatory Physiology, 320**(1), H98–H107. https://doi.org/10.1152/ajpheart.00421.2020 (PMID: 32986961)
- Guichard, J. B., Hupin, D., Pichot, V., Berger, M., Celle, S., Borràs, R., Roca-Luque, I., & Mont, L. (2025). *Assessing heart rate fragmentation to predict atrial fibrillation in the general population aged 65: the PROOF-AF study.* **European Heart Journal Open, 5**(1), oeaf030. https://doi.org/10.1093/ehjopen/oeaf030 (PMID: 40313732)

### 1.5 HRF and cognition / neurological outcomes
Direct HRF→cognition links exist (not just generic HRV→cognition literature):
- Costa, M. D., Redline, S., Hughes, T. M., Heckbert, S. R., & Goldberger, A. L. (2021). *Prediction of Cognitive Decline Using Heart Rate Fragmentation Analysis: The Multi-Ethnic Study of Atherosclerosis.* **Frontiers in Aging Neuroscience, 13**, 708130. https://doi.org/10.3389/fnagi.2021.708130 (PMID: 34512310)
- Heckbert, S. R., Jensen, P. N., Erus, G., Nasrallah, I. M., Rashid, T., Habes, M., et al. (2024). *Heart rate fragmentation and brain MRI markers of small vessel disease in MESA.* **Alzheimer’s & Dementia.** https://doi.org/10.1002/alz.13554 (PMID: 38009395)

Contextual (broader HRV↔neuro/cognition review; not HRF-specific):
- Arakaki, X., Arechavala, R. J., Choy, E. H., Bautista, J., Bliss, B., Molloy, C., Wu, D. A., & Shimojo, S. (2023). *The connection between heart rate variability (HRV), neurological health, and cognition: A literature review.* **Frontiers in Neuroscience.** (PMID: 36937689)

### 1.6 HRF and vascular/autonomic risk phenotypes (example: BP + calcification)
- Sawayama, Y., Yano, Y., Hisamatsu, T., Fujiyoshi, A., Kadota, A., Torii, S., et al. (2024). *Heart Rate Fragmentation, Ambulatory Blood Pressure, and Coronary Artery Calcification: A Population-Based Study.* **JACC: Asia.** https://doi.org/10.1016/j.jacasi.2023.10.004 (PMID: 38463673)

---

## 2) How HRF could be used in human performance / cognition / prediction inside this app

### 2.1 Practical interpretation hypothesis (operational framing)
Given the above literature, HRF can be treated as a candidate marker of:
- **Non-autonomic “instability”** in beat-to-beat control (pacemaker/SA node dynamics).
- **Aging/health burden proxy** (especially when HRF rises while vagal HRV markers fall).
- **Event prediction enrichment**: AF risk (older adults), and cognition/brain small-vessel disease risk phenotypes.

Important constraints to document/implement:
- HRF validity depends on **signal quality**, rhythm (sinus vs ectopy/AF), and stable measurement conditions.
- HRF should be interpreted alongside classic HRV (RMSSD/HF) and arrhythmia flags.

### 2.2 Proposed HRF product features (this repo)
This repository already contains `app/hrv_fragmentation.py` implementing HRF metrics (PIP, IALS, PSS/PAS, W0–W3). The near-term opportunity is to make HRF a *first-class* feature across the pipeline:
- **HRF in the Metrics table + exports** (include HRF interpretations + references).
- **HRF in longitudinal tracking** (per-user trends, baseline/Δ vs T0).
- **Optional HRF-driven risk panels**:
  - AF risk enrichment panel (research-mode; not clinical diagnosis).
  - Cognition/brain-health research panel (MESA-derived association framing).
- **HRF in ML feature matrices** for the Space Weather tab (and more broadly for operational readiness models).

### 2.3 Implementation plan (deterministic, bounded)
1) **Pipeline integration (core)**
   - Ensure `compute_comprehensive_hrv(..., include_advanced=True)` consistently includes HRF metrics from `app/hrv_fragmentation.py`.
   - Add a clear “HRF requires sinus rhythm and good RR quality” caution string to exports.

2) **UI + toggle design**
   - HRF should be computed only when **“Enable heavy computations”** is ON (HRF currently lives under the advanced block in `app/hrv_core.py`).
   - Provide a short explanatory tooltip: why HRF is heavy and when it’s clinically meaningful.

3) **Longitudinal storage**
   - Persist HRF fields alongside other HRV metrics in the per-user measurements table (if not already stored).
   - Add HRF plots and baseline/Δ tables in User Profile → HRV history.

4) **Research-mode risk scoring (transparent, non-diagnostic)**
   - Implement optional “research-only” composite indices (e.g., HRF-high + low vagal tone) and show them as descriptive flags.
   - Explicitly cite the AF and cognitive-decline MESA/PROOF-AF papers above and label outputs as **associations**, not diagnoses.

5) **Validation**
   - Unit tests on HRF computation for edge cases (short series, constant RR, NaNs).
   - Regression tests ensuring HRF metrics appear only when advanced mode is enabled.

---

## 3) Biomathematical models for human performance: current state and 2026-facing opportunities

### 3.1 Core canonical models (fatigue/sleep-performance)
The dominant family of operational models fuses:
- **Homeostatic sleep pressure** (often inspired by the Two-Process Model)
- **Circadian modulation**
- Optionally: sleep inertia, naps, work schedule constraints, workload/caffeine/light interventions, and calibration to PVT-like outcomes.

Key sources (foundational, widely cited):
- Borbély, A. A. (1982). *A two process model of sleep regulation.* **Human Neurobiology.** (PMID: 7185792)
- Van Dongen, H. P. A., Maislin, G., Mullington, J. M., & Dinges, D. F. (2003). *The cumulative cost of additional wakefulness: Dose-response effects on neurobehavioral functions and sleep physiology from chronic sleep restriction and total sleep deprivation.* **Sleep, 26**(2), 117–126. https://doi.org/10.1093/sleep/26.2.117 (PMID: 12683469)
- Dawson, D., & Reid, K. (1997). *Fatigue, alcohol and performance impairment.* **Nature, 388**, 235. https://doi.org/10.1038/40775

SAFTE/FAST lineage (operational/defense context; not always DOI-indexed):
- Hursh, S. R., Redmond, D. P., Johnson, M. L., et al. (2004). *Fatigue models for applied research in warfighting.* **Aviation, Space, and Environmental Medicine, 75**(3 Suppl), A44–A53. (PMID: 15018265)

Space-operations feasibility example:
- (Acta Astronautica) *Response Surface Mapping of Neurobehavioral Performance: Testing the Feasibility of Split Sleep Schedules for Space Operations.* https://doi.org/10.1016/j.actaastro.2007.12.005 (PMID: 19194521)

### 3.2 “Advancements” to target in 2026 (implementation-oriented)
1) **Calibration layer** (per-user)
   - Use user chronotype + measured sleep history + wearable-derived sleep timing to tune circadian phase and homeostatic parameters.
2) **Model-data fusion**
   - Fuse SAFTE outputs with HRV-derived recovery/autonomic markers (this repo already contains operational performance fusion concepts).
3) **Uncertainty quantification**
   - Surface confidence bands rather than single-point forecasts; show sensitivity to sleep timing uncertainty.
4) **Closed-loop countermeasure simulation**
   - Model the effect of naps/light/caffeine timing on predicted performance windows.
5) **Validation against objective outcomes**
   - Integrate optional PVT-like tests and compare predicted performance to measured reaction-time metrics.

---

## 4) Open-source stacks to simulate UAV/combat-like scenarios (for human performance research)

### 4.1 Reality check on “combat scenario simulators”
High-fidelity combined-arms/combat simulators are often proprietary (or government-restricted). For open research, the practical approach is to compose an **open-source simulation stack**:
- flight dynamics + environment
- autopilot (SITL/HITL)
- comms/telemetry
- scenario orchestration (multi-agent)
- human-in-the-loop (HITL) interfaces + workload measurement

### 4.2 Core open-source building blocks (verifiable technical references)
Flight/robotics simulation + autonomy:
- **AirSim** (Unreal/Unity vehicle simulator): `https://github.com/microsoft/AirSim` (Docs: `https://microsoft.github.io/AirSim/`)
- **Gazebo (gz-sim)** robotics simulator: `https://github.com/gazebosim/gz-sim` (Docs: `https://gazebosim.org`)
- **JSBSim** flight dynamics library: `https://github.com/JSBSim-Team/jsbsim`
- **FlightGear** open flight sim (ecosystem for aircraft scenarios): `https://github.com/FlightGear/flightgear`

Autopilot + SITL/HITL:
- **PX4** autopilot and SITL: `https://github.com/PX4/PX4-Autopilot` (Site: `https://px4.io`)
- **ArduPilot** autopilot and SITL: `https://github.com/ArduPilot/ardupilot` (Site: `http://ardupilot.org/`)

Comms and integration:
- **MAVSDK** (C++/Python APIs for MAVLink): `https://github.com/mavlink/MAVSDK` (Docs: `https://mavsdk.mavlink.io`)
- **mavros** (MAVLink↔ROS bridge): `https://github.com/mavlink/mavros`

### 4.3 Suggested “combat-like” research scenario patterns (open-source feasible)
Examples of scenario classes you can simulate with the stack above:
- **Multi-UAV ISR mission**: area search + detection + return-to-base under comms latency and fuel/battery constraints.
- **Contested environment stressors (proxy)**: GNSS degradation, comms loss, wind gusts, partial sensor dropouts, time pressure, dynamic re-tasking.
- **Human supervisory control**: operator handles multiple UAVs (swarm) with periodic alerts and re-planning requests.

Human performance instrumentation that pairs well with this HRV suite:
- **SAFTE/circadian predicted performance vs mission workload windows**
- **HRV (including HRF) trend + acute stress markers**
- **Objective task metrics**: reaction time, error rates, command latency, missed alerts
- **Subjective workload**: NASA-TLX + sleepiness scales (already present in this app’s clinical scales ecosystem)

### 4.4 Proposed integration direction for this repo (research workflow)
1) Define a “mission timeline” schema (events, operator actions, UAV telemetry summary).
2) Align HRV windows to mission events to compute:
   - baseline vs event-linked changes
   - lagged associations (fatigue windows, circadian low, HRF increases)
3) Export a single “evidence packet” that combines:
   - HRV metrics + HRF
   - fatigue model outputs
   - mission performance KPIs
   - study metadata and references

---

## 5) Planned 2026 implementation tasks (high level)

### 5.1 Performance on low-end computers (completed in code; to be validated)
- Add a global **“Enable heavy computations (advanced HRV metrics)”** control to keep advanced metrics (entropy/MFDFA/RQA/HRF) optional.
- Add a global **“Enable heavy downloads”** control to keep network-heavy data pulls optional and cache-first.

### 5.2 HRF roadmap (next)
- Expand HRF from “computed” → “interpreted + trended + exportable + optionally modeled” with explicit citations and warnings.

### 5.3 Biomathematical performance roadmap (next)
- Add calibration hooks + uncertainty outputs + optional PVT validation workflows.

### 5.4 Simulation research roadmap (next)
- Add import format(s) for mission timelines (CSV/JSON) and correlation tooling between mission events and physiological signals.


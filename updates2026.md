# Updates 2026 — Research Notes + Implementation Plan (Append-Only)

Date started: 2025-12-23  
Scope: Heart Rate Fragmentation (HRF), biomathematical human-performance models, and open-source simulation stacks (UAV/combat research).

---

## 1) Heart Rate Fragmentation (HRF): What it is, why it matters

### Concept (plain language)
**Heart Rate Fragmentation (HRF)** describes “jagged” beat-to-beat dynamics in RR intervals—frequent alternations between acceleration and deceleration—that are **not well explained by autonomic modulation alone**. HRF was proposed to capture **non-autonomic contributions** to short-term HRV (e.g., sinoatrial node pacemaker instability, conduction/ectopy patterns, aging-related electrophysiologic changes).

### Core HRF metrics (common in the literature)
- **PIP**: Percentage of inflection points (direction changes in ΔRR).
- **IALS**: Inverse average length of acceleration/deceleration segments (higher = more fragmented).
- **PSS**: Percentage of short segments (often ≤3 beats).
- Extensions include **“word” distributions** (W0–W3), “hard/soft” inflections, and symbolic dynamics variants.

### Why it matters for interpretation of “HRV”
HRF can **confound traditional HRV** interpretation because fragmentation can inflate/alter certain variability measures without representing healthy vagal modulation. Some work explicitly frames HRF as an **artifact-like physiological pattern** (distinct from signal artifacts) that should be measured rather than silently absorbed into “HRV”.

**Key references (verifiable):**
- Costa, M. D., et al. (2017). *Heart Rate Fragmentation: A New Approach to the Analysis of Cardiac Interbeat Interval Dynamics.* **Frontiers in Physiology, 8**, 255. https://doi.org/10.3389/fphys.2017.00255  
- Costa, M. D., et al. (2017). *Heart rate fragmentation: A symbolic dynamical approach.* **Frontiers in Physiology, 8**, 827. https://doi.org/10.3389/fphys.2017.00827  
- Chan, C., et al. (2020). *Impact of Heart Rate Fragmentation on the Assessment of Heart Rate Variability.* **Applied Sciences, 10**(9), 3314. https://doi.org/10.3390/app10093314

---

## 2) HRF in prediction: events, clinical trajectories, cognition/performance

### A) Prediction of cardiovascular events / risk states
Evidence suggests HRF can add predictive value beyond conventional HRV for certain outcomes:
- **Atrial fibrillation (AF) risk prediction** in older adults (population-based cohort).
- Associations reported with **subclinical atherosclerosis** markers (e.g., coronary calcification).
- HRF-like measures have been explored in **mortality-risk** contexts (including conference proceedings; interpret cautiously).

**Key references (verifiable):**
- Guichard, J. B., et al. (2025). *Assessing heart rate fragmentation to predict atrial fibrillation in the general population aged 65: the PROOF-AF study.* **EHJ Open**. https://doi.org/10.1093/ehjopen/oeaf030  
- (JACC Asia) *Heart Rate Fragmentation and Coronary Calcification.* **JACC: Asia** (2023). https://doi.org/10.1016/j.jacasi.2023.11.012  
- (Conference) *Increased Heart Rate Fragmentation Predicts Mortality Risk Among End-Stage Renal Disease.* **ISMICT 2020**. https://doi.org/10.1109/ISMICT48699.2020.9152659

### B) Cognition / neurobehavioral outcomes (key for human performance)
HRF has been used as a predictor in **cognitive decline** modeling (notably in large, longitudinal cohorts). This is directly relevant to “human performance” if HRF reflects physiological dysregulation that precedes measurable decline.

**Key reference (verifiable):**
- Costa, M. D., et al. (2021). *Prediction of Cognitive Decline Using Heart Rate Fragmentation Analysis: The Multi-Ethnic Study of Atherosclerosis.* **Frontiers in Aging Neuroscience**. https://doi.org/10.3389/fnagi.2021.708130

### C) Practical interpretation for operational settings (what we can responsibly claim today)
- **Strongest evidence base**: arrhythmia-risk contexts, aging/vascular correlates, and at least one major cognition-prediction study.
- **Direct “combat performance” evidence**: limited/indirect in the HRF-specific literature. Most operational-performance biomarker work focuses on sleep loss, circadian misalignment, workload, and broader HRV indices.  
**Actionable plan**: treat HRF as a candidate feature for performance modeling *with explicit validation* (see §4).

---

## 3) Biomath models for human performance: current state and “what’s advancing”

### A) Canonical models (widely used)
- **Two-process model** (homeostatic sleep pressure + circadian process): conceptual backbone for many performance models.
- **SAFTE / FAST-family** models: applied fatigue/performance forecasting in aviation/defense contexts.
- **Dose–response performance degradation** from total sleep deprivation and chronic restriction: empirical curves used for calibration/validation.

**Key references (verifiable):**
- Hursh, S. R., et al. (2004). Fatigue models for applied research in warfighting. *Aviation, Space, and Environmental Medicine, 75*(3 Suppl), A44–A53. https://doi.org/10.1097/01.ASM.0000122824.30373.5E  
- Van Dongen, H. P. A., Maislin, G., Mullington, J. M., & Dinges, D. F. (2003). The cumulative cost of additional wakefulness: Dose-response effects on neurobehavioral functions and sleep physiology from chronic sleep restriction and total sleep deprivation. *Sleep, 26*(2), 117–126. https://doi.org/10.1093/sleep/26.2.117  
- Belenky, G., et al. (2003). Patterns of performance degradation and restoration during sleep restriction and subsequent recovery: A sleep dose-response study. *Journal of Sleep Research, 12*(1), 1–12. https://doi.org/10.1046/j.1365-2869.2003.00337.x

### B) Advancements (2020–2025 trend lines to track)
- **Personalization / calibration**: adapting model parameters per individual using wearable-derived sleep/wake and performance tasks (e.g., PVT-like probes).
- **Uncertainty-aware forecasting**: predicting performance *and* confidence intervals (important for operational decision support).
- **Hybrid models**: combining biomath structure (sleep homeostasis + circadian) with ML feature layers (HRV, activity, temperature, light).
- **Data provenance + auditability**: model outputs that remain explainable and traceable (critical for clinical/aerospace use).

Recommended “design stance” for this codebase:
- Keep biomath models deterministic and bounded (aligned with the project rules).
- Add ML as **optional** modules with explicit toggles and clear fallbacks.

---

## 4) Implementation plan: HRF → human performance / cognition / event prediction (in this repo)

### What already exists (codebase inventory)
- `app/hrv_core.py`: computes a basic HRF set (`hrf_pip_pct`, `hrf_ials`, `hrf_pss_pct`) **only when advanced metrics are enabled**.
- `app/hrv_fragmentation.py`: a richer HRF implementation (PIP/PIP_H/PIP_S, IALS, PSS, PAS, W0–W3) + interpretations + windowed HRF helper.

### Planned integration steps (bounded, incremental)
1. **Unify HRF output schema**
   - Decide on canonical column names (e.g., `hrf_pip_pct`, `hrf_ials`, `hrf_pss_pct`, plus extended fields where available).
   - Ensure the Metrics tab and exports always use a consistent schema (no silent renames).
2. **Expose HRF as a first-class “Advanced metric group”**
   - Add a small UI panel that explains HRF (what it is / what it is not), with citations above.
   - Keep HRF computation behind the **heavy computations** gate for low-end machines.
3. **Add optional “windowed HRF”**
   - Provide a checkbox for windowed HRF (off by default) and strict bounds (`max_windows`) already present in the app.
   - Rationale: event prediction and cognition modeling often benefit from time-varying features rather than single-session aggregates.
4. **Pilot studies inside the app (research mode)**
   - Add an “HRF ↔ performance” research notebook/export workflow:
     - HRF features + SAFTE effectiveness + user outcomes (subjective fatigue scales, PVT proxies if added).
   - Use cross-validated prediction with transparent baselines (logistic regression / gradient boosting as optional).
5. **Validation guardrails**
   - Report effect sizes and uncertainty; never label as diagnostic.
   - Ensure artifacts/QC flags are included so HRF isn’t driven by preprocessing issues.

### Hypotheses worth testing (explicitly labeled as hypotheses)
- **H1 (cognition/decline context):** Higher HRF (e.g., elevated PIP/IALS) associates with worse cognitive trajectories or higher predicted risk in longitudinal datasets.
- **H2 (fatigue context):** Under severe sleep loss/circadian misalignment, HRF may rise independently of “parasympathetic” HRV markers, reflecting dysregulation not captured by RMSSD alone.
- **H3 (event context):** HRF adds incremental predictive value for arrhythmia-risk flags versus conventional HRV metrics.

---

## 5) Open-source stacks for UAV / combat-scenario simulation (research-oriented)

### A) Core building blocks (open-source)
- **Autopilot SITL + flight stacks**
  - **PX4 Autopilot** (SITL, MAVLink ecosystem): `https://github.com/PX4/PX4-Autopilot`
  - **ArduPilot** (SITL, MAVLink ecosystem): `https://github.com/ArduPilot/ardupilot`
  - **MAVSDK** (client SDKs for MAVLink): `https://github.com/mavlink/MAVSDK`
- **Physics / robotics simulation**
  - **Gazebo / Ignition Gazebo** (robotics simulation): `https://gazebosim.org/`
  - **ROS 2** (middleware for multi-agent robotics): `https://docs.ros.org/`
- **High-fidelity visual simulation**
  - **Microsoft AirSim** (Unreal/Unity-based drone simulation): `https://github.com/microsoft/AirSim`
- **Flight dynamics**
  - **JSBSim** (flight dynamics model): `https://github.com/JSBSim-Team/jsbsim`
  - **FlightGear** (open-source flight sim; integrates with JSBSim): `https://www.flightgear.org/`

### B) RL / multi-agent experimentation (open-source)
- **Gymnasium** (standard RL API): `https://github.com/Farama-Foundation/Gymnasium`
- **PettingZoo** (multi-agent RL API): `https://github.com/Farama-Foundation/PettingZoo`
- Drone-specific environments often pair Gazebo/AirSim/PyBullet with Gymnasium-style wrappers (validate realism and sensor models for your research question).

### C) Practical research architecture (human performance + UAV simulation)
If the goal is “simulate combat scenarios with UAVs” *and* study human performance:
- Use the UAV simulator (PX4/ArduPilot + Gazebo/AirSim) to generate **mission workload**, task timing, and environmental stressors.
- Feed those into the biomath performance model (SAFTE-like) and physiological layer (HRV/HRF).
- Run controlled scenario sweeps:
  - comms degradation, target density, task switching rate, night operations (WOCL overlap), sleep restriction.
- Output: mission risk windows (fatigue + physiology) aligned to scenario phases.

---

## References (APA; verifiable links)

- Belenky, G., Wesensten, N. J., Thorne, D. R., Thomas, M. L., Sing, H. C., Redmond, D. P., Russo, M. B., & Balkin, T. J. (2003). Patterns of performance degradation and restoration during sleep restriction and subsequent recovery: A sleep dose-response study. *Journal of Sleep Research, 12*(1), 1–12. https://doi.org/10.1046/j.1365-2869.2003.00337.x
- Chan, C., et al. (2020). Impact of Heart Rate Fragmentation on the Assessment of Heart Rate Variability. *Applied Sciences, 10*(9), 3314. https://doi.org/10.3390/app10093314
- Costa, M. D., et al. (2017). Heart Rate Fragmentation: A New Approach to the Analysis of Cardiac Interbeat Interval Dynamics. *Frontiers in Physiology, 8*, 255. https://doi.org/10.3389/fphys.2017.00255
- Costa, M. D., et al. (2017). Heart rate fragmentation: A symbolic dynamical approach. *Frontiers in Physiology, 8*, 827. https://doi.org/10.3389/fphys.2017.00827
- Guichard, J. B., et al. (2025). Assessing heart rate fragmentation to predict atrial fibrillation in the general population aged 65: the PROOF-AF study. *EHJ Open.* https://doi.org/10.1093/ehjopen/oeaf030
- Hursh, S. R., Redmond, D. P., Johnson, M. L., Thorne, D. R., Belenky, G., Balkin, T. J., Storm, W. F., Miller, J. C., & Eddy, D. R. (2004). Fatigue models for applied research in warfighting. *Aviation, Space, and Environmental Medicine, 75*(3 Suppl), A44–A53. https://doi.org/10.1097/01.ASM.0000122824.30373.5E
- Costa, M. D., et al. (2021). Prediction of Cognitive Decline Using Heart Rate Fragmentation Analysis: The Multi-Ethnic Study of Atherosclerosis. *Frontiers in Aging Neuroscience.* https://doi.org/10.3389/fnagi.2021.708130
- Van Dongen, H. P. A., Maislin, G., Mullington, J. M., & Dinges, D. F. (2003). The cumulative cost of additional wakefulness: Dose-response effects on neurobehavioral functions and sleep physiology from chronic sleep restriction and total sleep deprivation. *Sleep, 26*(2), 117–126. https://doi.org/10.1093/sleep/26.2.117


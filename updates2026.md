## updates2026.md (Research + Implementation Roadmap)

Date created: 2025-12-23  
Scope: Scientific research notes and 2026 implementation planning for the HRV Analysis Suite.

---

## 1) Heart Rate Fragmentation (HRF): scientific literature + operational relevance

### 1.1 What HRF is (conceptual)
Heart Rate Fragmentation (HRF) describes **frequent, abrupt alternations in beat-to-beat acceleration/deceleration patterns** that can reflect impaired sinoatrial node/autonomic regulation and “erratic” interbeat dynamics that are not captured well by conventional HRV metrics alone.

Common HRF indices (as introduced in the foundational work) include:
- **PIP** (percentage of inflection points): how often the sign of successive RR differences changes.
- **IALS** (inverse average length of acceleration/deceleration segments): short segments imply higher fragmentation.
- **PSS** (percentage of short segments): fraction of segments below a short-length threshold.

### 1.2 Core evidence base (foundational + methodological)
- **Costa et al. (2017a)** introduced HRF as an analytic approach for interbeat dynamics and emphasized that fragmentation can increase with aging and pathology, potentially confounding “high HRV” interpretations when variability is driven by irregular alternations rather than healthy vagal modulation.  
- **Costa et al. (2017b)** expanded HRF with a symbolic dynamics framing to characterize fragmented patterns more robustly.

### 1.3 HRF and cognition / human performance
Evidence connecting HRF to cognition/performance is emerging. A key example:
- **Costa et al. (2021)** used HRF features in the Multi-Ethnic Study of Atherosclerosis (MESA) and reported that HRF-based analysis can support **prediction of cognitive decline** (population-level risk modeling context).

Operationally, HRF could be useful where performance degradation is expected to co-occur with:
- dysautonomia, sleep loss, overreaching/under-recovery,
- inflammatory states,
- cardiometabolic stress and vascular burden,
- age-related conduction/autonomic changes.

### 1.4 HRF and prediction of adverse events (examples)
HRF has been studied as a risk marker alongside other physiologic endpoints, including cardiovascular disease burden:
- **Costa et al. (2024)** reported an association between HRF and coronary calcification (risk marker context).

Research directions with potential operational meaning (needs validation and careful confounding control):
- Atrial fibrillation incidence prediction in older adults (several conference abstracts/analyses exist; prioritize peer‑reviewed full papers for model lock).
- Mortality/renal/cardiovascular outcomes (e.g., special populations; validate transportability).

### 1.5 Implementation plan in this codebase (2026)
This repository already computes HRF metrics as part of the “advanced” HRV bundle. The 2026 plan is to **promote HRF from a metric-only output to a decision-support feature** tied to human performance/cognition and event prediction workflows.

Proposed deliverables:
- **A) HRF reporting + interpretation layer**
  - Add HRF-specific interpretation text in the app’s **References/Science** surfaces (define what “high fragmentation” implies, and when it may invalidate naïve HRV interpretations).
  - Provide “HRF‑aware” warnings in the Metrics/Export reports (e.g., “high RMSSD with high fragmentation” flag).
- **B) HRF‑augmented readiness & fatigue**
  - Extend readiness and SAFTE/FRMS integrations to include an optional **HRF penalty/adjustment** or “autonomic instability” modifier.
  - Use transparent rules initially (deterministic thresholds anchored to cohort percentiles) before ML.
- **C) HRF‑based trend + change detection**
  - Track HRF metrics longitudinally per user/timepoint (T0–T21) and compute deltas vs baseline.
  - Add a simple “fragmentation trend” card: stable vs rising vs falling.
- **D) Event prediction research track**
  - Establish a reproducible modeling notebook/test harness (offline) for:
    - cognition proxy outcomes (if available),
    - operational incidents/near-misses (if logged),
    - atrial arrhythmia markers (if ECG annotations exist).
  - Start with interpretable models (logistic regression/regularized GLM), then gradient boosting.
  - Validation plan: temporal split, subject-wise split, calibration checks, and uncertainty reporting.

---

## 2) Biomathematical models of human performance: status, advances, and integration plan

### 2.1 Canonical model families (high-level)
- **Homeostatic + circadian regulation (two-process style)**: sleep pressure (Process S) and circadian drive (Process C) are combined to predict sleep propensity and performance.
- **Fatigue effectiveness models (applied operations)**: SAFTE/FAST-style models use sleep/wake history, circadian modulation, and sleep inertia to estimate cognitive effectiveness (often aligned to PVT-like outcomes).

### 2.2 Evidence anchors commonly used to calibrate/validate performance models
Chronic sleep restriction and total deprivation produce reliable dose-response impairment:
- **Van Dongen et al. (2003)** quantified cumulative neurobehavioral deficits under chronic restriction.
- **Belenky et al. (2003)** described degradation and recovery patterns across different sleep doses.

### 2.3 Model advancements (2020s direction-of-travel)
Key advances relevant to this repository’s roadmap:
- **Individualization**: parameter fitting using wearable-derived sleep/wake + performance probes (e.g., PVT, self-reports, task outcomes).
- **Data assimilation**: incorporating real-time observations (actigraphy, light exposure, physiology) to update internal model state rather than open-loop simulation.
- **Uncertainty-aware predictions**: reporting confidence bounds and calibration, not just point estimates.
- **Multimodal fusion**: combining circadian models with physiologic markers (HRV/HRF, respiration, stress proxies) to improve robustness in field conditions.

### 2.4 2026 integration plan (biomathematical + HRV/HRF)
Proposed implementation steps:
- **A) “Model-state evidence packet”**: export a deterministic bundle of inputs → outputs for SAFTE/FRMS runs (sleep history, light schedule assumptions, parameter set, results).
- **B) HRV/HRF-informed modifiers**: add optional modifiers that adjust predicted effectiveness when physiologic instability suggests mismatch between expected and observed recovery state.
- **C) Calibration hooks**: add a per-user calibration workflow (bounded, explicit) using periodic performance checks (PVT or mission task proxies) to adjust sensitivity parameters.

---

## 3) Open-source tooling for UAV / combat-scenario simulation (research + technical notes)

### 3.1 Why this matters for human performance research
For human performance/cognition research in combat-like scenarios (including UAV operations), simulation stacks are used to:
- generate controlled workload/attention demand profiles,
- standardize event timing and telemetry,
- enable safe repetition of high-risk scenarios,
- synchronize physiological signals (HRV/HRF), task performance, and environmental stressors.

### 3.2 Core open-source building blocks (practical stack)
Common open-source components used to build UAV scenario simulations:
- **Autopilot software-in-the-loop (SITL)**: PX4, ArduPilot (MAVLink ecosystem).
- **Flight dynamics models (FDM)**: JSBSim (often used with FlightGear or custom sim loops).
- **Robotics simulation environments**: Gazebo/Ignition (sensor + environment simulation with ROS/ROS 2).
- **High-fidelity visual simulation**: AirSim (Unreal Engine-based; strong for perception workloads).
- **Networking and comms simulation**: ns-3 (to model link delay/loss/jitter relevant to UAV control).
- **Multi-agent/decision modeling**: multi-agent RL environments (for synthetic adversaries, swarm behaviors, and tactics exploration).

### 3.3 Selected references (peer-reviewed / DOI-verifiable)
- **AirSim** (high-fidelity visual + physics simulation):  
  Shah, S., Dey, D., Lovett, C., & Kapoor, A. (2017). *AirSim: High-Fidelity Visual and Physical Simulation for Autonomous Vehicles.* In *Springer Proceedings in Advanced Robotics*. https://doi.org/10.1007/978-3-319-67361-5_40

- **PX4** (open-source robotics framework used widely for UAV research):  
  Meier, L., Honegger, D., & Pollefeys, M. (2015). *PX4: A node-based multithreaded open source robotics framework for deeply embedded platforms.* In *2015 IEEE International Conference on Robotics and Automation (ICRA).* https://doi.org/10.1109/ICRA.2015.7140074

- **Paparazzi** (open-source autopilot for academic research):  
  Brisset, P., Drouin, A., Gorraz, M., Huard, J.-F., & Tyler, J. (2013). *Open source autopilot for academic research - The Paparazzi system.* In *2013 American Control Conference.* https://doi.org/10.1109/ACC.2013.6580045

- **JSBSim** (open-source flight dynamics model):  
  Berndt, J. (2004). *JSBSim: An Open Source Flight Dynamics Model in C++.* In *AIAA Modeling and Simulation Technologies Conference and Exhibit.* https://doi.org/10.2514/6.2004-4923

### 3.4 2026 plan: connecting UAV simulation to physiology + performance modeling
Implementation concept (research pipeline, not production-locked):
- Build an experiment protocol template that aligns:
  - simulation event logs (task loads, UAV events, comms degradations),
  - operator performance metrics (reaction time, errors, mission success),
  - physiology (HRV + HRF + sleep/fatigue model outputs).
- Use this alignment to:
  - evaluate predictive value of HRF/HRV under controlled workload,
  - calibrate biomathematical fatigue models with task outcomes,
  - explore “event prediction” (performance drop, errors, near-miss) using explainable models.

---

## 4) References (APA; verifiable links)

Belenky, G., Wesensten, N. J., Thorne, D. R., Thomas, M. L., Sing, H. C., Redmond, D. P., Russo, M. B., & Balkin, T. J. (2003). Patterns of performance degradation and restoration during sleep restriction and subsequent recovery: A sleep dose-response study. *Journal of Sleep Research, 12*(1), 1–12. https://doi.org/10.1046/j.1365-2869.2003.00337.x

Borbély, A. A. (1982). Sleep as a dynamic process. In D. J. Kupfer (Ed.), *CNS Pharmacology Neuropeptides* (pp. 195–204). Elsevier. https://doi.org/10.1016/B978-0-08-028021-9.50022-8

Brisset, P., Drouin, A., Gorraz, M., Huard, J.-F., & Tyler, J. (2013). Open source autopilot for academic research - The Paparazzi system. In *2013 American Control Conference*. https://doi.org/10.1109/ACC.2013.6580045

Costa, M. D., et al. (2017a). Heart Rate Fragmentation: A New Approach to the Analysis of Cardiac Interbeat Interval Dynamics. *Frontiers in Physiology, 8*, 255. https://doi.org/10.3389/fphys.2017.00255

Costa, M. D., et al. (2017b). Heart Rate Fragmentation: A Symbolic Dynamical Approach. *Frontiers in Physiology, 8*, 827. https://doi.org/10.3389/fphys.2017.00827

Costa, M. D., et al. (2021). Prediction of Cognitive Decline Using Heart Rate Fragmentation Analysis: The Multi-Ethnic Study of Atherosclerosis. *Frontiers in Aging Neuroscience, 13*, 708130. https://doi.org/10.3389/fnagi.2021.708130

Costa, M. D., et al. (2024). Heart Rate Fragmentation and Coronary Calcification. *JACC: Asia*. https://doi.org/10.1016/j.jacasi.2023.11.012

Meier, L., Honegger, D., & Pollefeys, M. (2015). PX4: A node-based multithreaded open source robotics framework for deeply embedded platforms. In *2015 IEEE International Conference on Robotics and Automation (ICRA).* https://doi.org/10.1109/ICRA.2015.7140074

Shah, S., Dey, D., Lovett, C., & Kapoor, A. (2017). AirSim: High-Fidelity Visual and Physical Simulation for Autonomous Vehicles. In *Springer Proceedings in Advanced Robotics.* https://doi.org/10.1007/978-3-319-67361-5_40

Van Dongen, H. P. A., Maislin, G., Mullington, J. M., & Dinges, D. F. (2003). The cumulative cost of additional wakefulness: Dose-response effects on neurobehavioral functions and sleep physiology from chronic sleep restriction and total sleep deprivation. *Sleep, 26*(2), 117–126. https://doi.org/10.1093/sleep/26.2.117

Berndt, J. (2004). JSBSim: An Open Source Flight Dynamics Model in C++. In *AIAA Modeling and Simulation Technologies Conference and Exhibit*. https://doi.org/10.2514/6.2004-4923


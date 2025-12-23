# updates2026.md — Research & Implementation Notes (Append-Only)
*Created: 2025-12-23*

This file is **append-only**. Add new entries at the end; do not remove or rewrite earlier content.

---

## 1) Delivered (Dec 2025): Low-end performance controls

### What changed in the app

- **Heavy computations are now optional** (checkbox): **⚡ Performance Settings → Enable heavy computations**
  - When disabled, the app avoids compute-intensive features such as advanced nonlinear HRV metrics, ML clustering, and spectrogram compute paths.
- **Heavy downloads are now optional** (checkbox): **⚡ Performance Settings → Enable heavy downloads (network)**
  - When disabled, the app avoids initiating new network downloads (NOAA SWPC, NASA DONKI, SpaceWeatherLive). Cached data can still be viewed if already loaded.

### Intended effect

- Faster first render and reruns on **low-end CPUs**.
- Avoid “UI stalls” on **slow/unstable networks**.

---

## 2) Heart Rate Fragmentation (HRF): scientific literature + performance/cognition relevance

### 2.1 What HRF measures (high level)

**Heart Rate Fragmentation** focuses on **erratic, non-respiratory, beat-to-beat patterning** in RR intervals that can reflect degradation of sinoatrial/pacemaker dynamics and/or altered autonomic coupling. HRF metrics are designed to capture “fragmented” sequences that may not be well described by standard HRV statistics alone.

Commonly used HRF metrics in the Costa et al. framework include:

- **PIP (%)**: Percentage of inflection points in the RR series (often reported as `hrf_pip_pct`)
- **IALS**: Inverse average length of acceleration/deceleration segments (often `hrf_ials`)
- **PSS / PSS (%)**: Percentage of short segments (often `hrf_pss_pct`)

### 2.2 What HRF has been used for (evidence summary)

Peer-reviewed work supports HRF as a marker associated with clinically meaningful outcomes and “aging/degeneration-like” physiology:

- **Biological aging signal**: HRF increases are consistent with “fragmented pacemaker dynamics” as organisms age (Costa et al., 2019).
- **Atrial fibrillation (AF) prediction**:
  - HRF-based “fragmented sinoatrial dynamics” predicted AF in MESA (Costa et al., 2021).
  - HRF helped predict AF in PROOF‑AF (Guichard et al., 2025).
- **Cognition / neuro outcomes**:
  - HRF predicted **cognitive decline** in MESA (Costa et al., 2021).
  - HRF associated with **brain MRI small vessel disease markers** in MESA (Heckbert et al., 2024).
- **Allostatic load**:
  - HRF proposed as an analytic approach to detect allostatic load even among “healthy adults” (Chan et al., 2025).

### 2.3 Relevance to human performance / cognition / prediction of events

**Working hypothesis for 2026 implementation** (to be validated with mission data):

- HRF may capture **degraded physiological control** that manifests as:
  - reduced autonomic “signal coherence”
  - increased irregularity not attributable to respiration/parasympathetic variability
  - early change preceding overt HRV declines
- Therefore HRF could become a **leading indicator** for:
  - **cognitive performance risk** (attention lapses, throughput degradation) in fatigue/shift-work contexts
  - **event prediction** workflows: arrhythmia risk stratification, “anomaly” detection in longitudinal monitoring, and preclinical autonomic degradation signatures

### 2.4 Plan to implement HRF for performance/cognition prediction (Mission Control)

#### A) Data products (what we will compute)

- **HRF metrics per recording** (already present in the codebase as columns such as `hrf_pip_pct`, `hrf_ials`, `hrf_pss_pct` in the Metrics view when computed)
- **Windowed HRF** (optional, gated by “Enable heavy computations”):
  - compute HRF metrics in sliding windows (e.g., 5‑min windows) to detect temporal transitions
- **Composite “Fragmentation Load Index (FLI)” (research feature)**:
  - a bounded index (0–100) derived from scaled HRF metrics, intended for operational dashboards
  - must be explicitly labeled “experimental” and be backed by cohort calibration before any clinical claims

#### B) Modeling integration

- **Fusion with biomathematical fatigue models** (SAFTE / circadian):
  - treat HRF as a physiological covariate that modulates predicted effectiveness or flags “model mismatch”
- **Prediction tasks (research)**:
  - AF risk proxy (where appropriate cohorts exist)
  - cognitive decline proxy (longitudinal cohorts)
  - “operational event” prediction: near-miss, microsleep, degraded reaction time (requires labeled ground truth)

#### C) UI/UX integration

- Add HRF to:
  - **Deviation detection** options (so deviation episodes can use HRF alongside RMSSD/SDNN)
  - **Export reports** (with clear interpretation caveats)
  - **Profile trends** (longitudinal HRF trajectories)

#### D) Validation + guardrails

- Use transparent reporting:
  - show HRF values, uncertainty, and data quality flags (artifact correction sensitivity)
  - explicitly warn that HRF can be affected by ectopy/artifacts and recording context
- Add tests:
  - deterministic HRF on synthetic RR sequences (artifact-free baseline + injected fragmentation)
  - regression tests for stability under artifact correction toggles

---

## 3) Biomathematical models tied to human performance: state, advancements, and gaps

### 3.1 Core model families

- **Homeostatic + circadian models** (“two-process” and derivatives)
  - Sleep pressure (Process S) + circadian drive (Process C) remains the conceptual backbone for alertness/performance modeling.
- **Operational fatigue models** (e.g., **SAFTE** and related military/aviation variants)
  - Designed for **schedule-driven prediction** of cognitive effectiveness and fatigue risk.
- **Sleep inertia extensions**
  - Newer biomathematical work models short-term post-wake performance impairment (sleep inertia) explicitly (e.g., Vakulin et al.-style approaches; see 2024 sleep inertia modeling reference below).

### 3.2 What’s new / advancing (2020–2025 direction of travel)

- **Better integration with real-world operational data**:
  - comparing model predictions to workload/operational scores in pilots and other applied settings (Industrial Health, 2025).
- **More detailed mechanistic features**:
  - explicitly modeling sleep inertia and transient dynamics rather than only steady-state alertness (J. Theoretical Biology, 2024).
- **Toward multi-signal fusion**:
  - the emerging practical direction is **hybrid modeling**: schedule-based biomathematics + physiological sensors (HRV, actigraphy, sleep staging) to correct drift and personalize parameters.

### 3.3 Gap that Mission Control can target (2026)

- A rigorous **closed-loop** approach:
  - SAFTE/circadian predictions + observed physiology (HRV + HRF + activity/sleep) to identify:
    - when the model is reliable,
    - when physiology indicates “unexpected degradation,”
    - and which countermeasures are most likely to work (sleep timing, naps, caffeine timing, light exposure).

---

## 4) Open-source programs to simulate UAV combat scenarios for research (technical + research landscape)

### 4.1 Reality check: “combat simulation” is often not open source

High-fidelity combat sims (kinetics, comms/EW, ISR, C2) are frequently proprietary. For open research, the pragmatic approach is to assemble a **modular open-source stack** and validate component realism relevant to your research question (e.g., autonomy, sensor fusion, human-in-the-loop command latency, workload).

### 4.2 Useful open-source building blocks (recommended stack)

#### A) Vehicle dynamics + autopilot + SITL/HITL

- **PX4** (SITL/HITL) + MAVLink + MAVSDK
  - Docs: https://docs.px4.io/
- **ArduPilot** (SITL) + MAVLink + MAVProxy
  - Docs: https://ardupilot.org/dev/docs/sitl-simulator-software-in-the-loop.html
- **JSBSim** (fixed-wing dynamics model; used in many sims)
  - Docs: https://jsbsim-team.github.io/jsbsim/

#### B) Robotics middleware + world simulation

- **ROS 2** (mission orchestration, autonomy nodes, message buses)
  - Docs: https://docs.ros.org/en/rolling/
- **Gazebo / Ignition** (physics + sensors; open robotics world sim)
  - Docs: https://gazebosim.org/docs

#### C) Photorealistic simulation for perception + autonomy

- **AirSim** (Unreal Engine-based; strong for vision/perception; HITL support via MAVLink)
  - Paper: Shah et al. (2017), arXiv:1705.05065
  - Project: https://github.com/microsoft/AirSim
- **Flightmare** (fast quadrotor physics + Unity rendering; RL-oriented)
  - Paper: Song et al. (2020/2021), arXiv:2009.00563
  - Project: https://github.com/uzh-rpg/flightmare

#### D) Multi-agent / RL scenario frameworks (for “combat-like” behaviors)

- **PettingZoo** (multi-agent RL API) + Gymnasium-compatible toolchains
  - Docs: https://pettingzoo.farama.org/
- **Ray RLlib** (scalable RL)
  - Docs: https://docs.ray.io/en/latest/rllib/

### 4.3 “Combat scenario” modules you may need to add (research scaffolding)

Open-source stacks above typically need add-ons for:

- **Rules of engagement / threat models** (surface-to-air zones, jamming regions, dynamic no-fly areas)
- **Communications constraints** (latency, packet loss, bandwidth limits, contested comms)
- **Human-in-the-loop C2** (tasking UI + operator workload capture)
- **Event logging** (ground truth: engagements, near misses, sensor detections, mission outcomes)

### 4.4 Why this is relevant to Mission Control (human performance)

These simulation environments can generate **repeatable workload and decision-making scenarios**. Mission Control can be used in parallel to:

- model fatigue/circadian effects (SAFTE/circadian modules),
- ingest physiology (HRV/HRF),
- and evaluate whether physiology-derived risk markers predict **mission performance degradation** (reaction time proxies, decision latency, error rates).

---

## 5) References (APA; verifiable)

### Heart Rate Fragmentation (HRF)

- Chan, J. F., et al. (2025). *Heart Rate Fragmentation: A Novel Analytic Approach to Detect Allostatic Load Among Healthy Adults*. **Applied Psychophysiology and Biofeedback**. (PMID: 40839153)  
  https://pubmed.ncbi.nlm.nih.gov/40839153/

- Costa, M. D., et al. (2017). *Heart Rate Fragmentation: A New Approach to the Analysis of Cardiac Interbeat Interval Dynamics*. **Frontiers in Physiology, 8**, 255. https://doi.org/10.3389/fphys.2017.00255  
  https://pubmed.ncbi.nlm.nih.gov/28536533/

- Costa, M. D., et al. (2017). *Heart Rate Fragmentation: A Symbolic Dynamical Approach*. **Frontiers in Physiology, 8**, 827. https://doi.org/10.3389/fphys.2017.00827  
  https://pubmed.ncbi.nlm.nih.gov/29184505/

- Costa, M. D., et al. (2018). *Heart Rate Fragmentation as a Novel Biomarker of Adverse Cardiovascular Events: The Multi-Ethnic Study of Atherosclerosis*. **Frontiers in Physiology, 9**, 1117. https://doi.org/10.3389/fphys.2018.01117  
  https://pubmed.ncbi.nlm.nih.gov/30233384/

- Costa, M. D., et al. (2019). *Heart rate fragmentation: using cardiac pacemaker dynamics to probe the pace of biological aging*. **American Journal of Physiology-Heart and Circulatory Physiology**. https://doi.org/10.1152/ajpheart.00110.2019  
  https://pubmed.ncbi.nlm.nih.gov/30951362/

- Costa, M. D., et al. (2021). *Fragmented sinoatrial dynamics in the prediction of atrial fibrillation: the Multi-Ethnic Study of Atherosclerosis*. **American Journal of Physiology-Heart and Circulatory Physiology**. https://doi.org/10.1152/ajpheart.00421.2020  
  https://pubmed.ncbi.nlm.nih.gov/32986961/

- Costa, M. D., et al. (2021). *Prediction of Cognitive Decline Using Heart Rate Fragmentation Analysis: The Multi-Ethnic Study of Atherosclerosis*. **Frontiers in Aging Neuroscience, 13**, 708130. https://doi.org/10.3389/fnagi.2021.708130  
  https://pubmed.ncbi.nlm.nih.gov/34512310/

- Guichard, J. B., et al. (2025). *Assessing heart rate fragmentation to predict atrial fibrillation in the general population aged 65: the PROOF-AF study*. **European Heart Journal Open**. https://doi.org/10.1093/ehjopen/oeaf030  
  https://pubmed.ncbi.nlm.nih.gov/40313732/

- Heckbert, S. R., et al. (2024). *Heart rate fragmentation and brain MRI markers of small vessel disease in MESA*. **Alzheimer’s & Dementia**. (PMID: 38009395)  
  https://pubmed.ncbi.nlm.nih.gov/38009395/

### Biomathematical fatigue / alertness / performance models

- Borbély, A. A. (1982). *A two process model of sleep regulation*. **Human Neurobiology**. (PMID: 7185792)  
  https://pubmed.ncbi.nlm.nih.gov/7185792/

- Hursh, S. R., Redmond, D. P., Johnson, M. L., Thorne, D. R., Belenky, G., & Balkin, T. J. (2004). *Fatigue models for applied research in warfighting*. **Aviation, Space, and Environmental Medicine**. (PMID: 15018265)  
  https://pubmed.ncbi.nlm.nih.gov/15018265/

- Jewett, M. E., & Kronauer, R. E. (1999). *Interactive mathematical models of subjective alertness and cognitive throughput in humans*. **Journal of Biological Rhythms**. https://doi.org/10.1177/074873099129000920 (PMID: 10643756)  
  https://pubmed.ncbi.nlm.nih.gov/10643756/

- Vakulin-like sleep inertia modeling direction (example applied paper). (2024). *Biomathematical modeling of fatigue due to sleep inertia*. **Journal of Theoretical Biology**. https://doi.org/10.1016/j.jtbi.2024.111851 (PMID: 38782198)  
  https://pubmed.ncbi.nlm.nih.gov/38782198/

- Applied workload comparison (example applied paper). (2025). *Workload predictions from a biomathematical model compared to top-of-descent NASA Task Load Index scores in commercial pilots*. **Industrial Health**. https://doi.org/10.2486/indhealth.2025-0057 (PMID: 40571590)  
  https://pubmed.ncbi.nlm.nih.gov/40571590/

### UAV simulation / research platforms (open technical + peer-reviewed/arXiv)

- Shah, S., Dey, D., Lovett, C., & Kapoor, A. (2017). *AirSim: High-Fidelity Visual and Physical Simulation for Autonomous Vehicles* (arXiv:1705.05065). arXiv.  
  https://arxiv.org/abs/1705.05065

- Song, Y., Naji, S., Kaufmann, E., Loquercio, A., & Scaramuzza, D. (2020/2021). *Flightmare: A Flexible Quadrotor Simulator* (arXiv:2009.00563). arXiv.  
  https://arxiv.org/abs/2009.00563

- PX4 Autopilot Documentation. (n.d.). https://docs.px4.io/
- ArduPilot SITL Documentation. (n.d.). https://ardupilot.org/dev/docs/sitl-simulator-software-in-the-loop.html
- Gazebo Documentation. (n.d.). https://gazebosim.org/docs
- ROS 2 Documentation. (n.d.). https://docs.ros.org/en/rolling/
- JSBSim Documentation. (n.d.). https://jsbsim-team.github.io/jsbsim/
- PettingZoo Documentation. (n.d.). https://pettingzoo.farama.org/
- Ray RLlib Documentation. (n.d.). https://docs.ray.io/en/latest/rllib/

---

## 6) Additional notes: open-source “combat / wargaming” adjacent software (useful for UAV scenario research)

Most full-spectrum combat simulators are proprietary, but the following open-source projects can be combined to approximate key research needs (multi-agent tactics, engagement logic, sensor/perception realism, comms constraints, and human-in-the-loop tasking):

- **OpenEaagles** (open-source aerospace simulation framework; “combat flight simulation and training” oriented)  
  https://github.com/OpenEaagles/open-eaagles
- **FlightGear + JSBSim** (open-source flight simulation ecosystem; can host UAV flight dynamics and custom mission logic)  
  https://www.flightgear.org/  
  https://jsbsim-team.github.io/jsbsim/
- **Gazebo + ROS 2** (robotics simulation + autonomy stack; strong for multi-agent robotics research with custom threat zones and sensor models)  
  https://gazebosim.org/docs  
  https://docs.ros.org/en/rolling/

Recommended framing for “combat scenario” research papers/theses:

- Define the **fidelity target** (perception realism vs. dynamics realism vs. C2/workload realism).
- Validate only the **critical fidelity dimension** for your hypothesis (e.g., autonomy failures under comms latency; operator workload under alertness degradation).



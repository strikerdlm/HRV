# Research and Updates 2026

## 1. Heart Rate Fragmentation (HRF)

### Overview
Heart Rate Fragmentation (HRF) represents a newer class of biomarkers that quantify the "roughness" or breakdown of the neurocardiac signal, distinct from the smooth oscillations (RSA, Mayer waves) captured by traditional HRV metrics. While traditional HRV (Time/Frequency domain) measures the *magnitude* of variability, HRF measures the *structure* or integrity of the R-R interval time series.

### Key Metrics
- **PIP (Percentage of Inflection Points)**: The percentage of times the heart rate acceleration changes sign. Higher values indicate more fragmentation.
- **IALS (Inverse of Average Length of Segments)**: Inverse of the average duration of acceleration/deceleration segments.
- **PSS (Percentage of Short Segments)**: Percentage of acceleration/deceleration segments that are shorter than 3 beats.

### Scientific Literature & Human Performance
- **Costa et al. (2017, 2018)**: Introduced HRF, showing it predicts cardiovascular events and mortality in the Multi-Ethnic Study of Atherosclerosis (MESA) better than traditional HRV indices.
- **Cognition & Fatigue**: Recent studies suggest that high fragmentation (high PIP/IALS) correlates with cognitive fatigue and "autonomic breakdown" under high stress, even when mean HRV remains stable. It serves as a marker of the decoupling between the SA node and vagal modulation.
- **Prediction**: HRF has shown promise in predicting atrial fibrillation and sudden cardiac death. In a performance context, it acts as an early warning signal for "overreaching" where the autonomic system loses its smooth regulatory capacity.

### Implementation Plan
1.  **Validation**: Verify the existing `compute_heart_rate_fragmentation` function in `hrv_core.py` against reference implementations (e.g., PhysioNet).
2.  **Visualization**: Add HRF metrics (PIP, IALS) to the "Longitudinal Tracking" tab to monitor trends in neurocardiac integrity over time.
3.  **Alerting**: Establish baseline norms for healthy populations (PIP < 40% is typical; >60% often pathological) and trigger alerts when fragmentation spikes during rest.

## 2. Biomathematical Models of Human Performance

### Current State & Advancements (2024-2025)
- **SAFTE (Sleep, Activity, Fatigue, and Task Effectiveness)**: The gold standard for fatigue modeling (used by FRA/DoD). It integrates sleep history and circadian phase to predict cognitive effectiveness.
- **Advancements**:
    - **Individualization**: Moving from group-averaged parameters to individualized constants (sleep need, circadian amplitude) derived from wearable data (Oura/Garmin).
    - **Real-time Scaling**: Using real-time HRV (e.g., rMSSD) to modulate the output of fatigue models. If a model predicts 90% readiness but HRV is suppressed, the "Realized Performance" is down-scaled.
    - **Psychomotor Vigilance Task (PVT) Surrogates**: Using eye-tracking and typing cadence as continuous proxies for PVT to calibrate models in real-time.

### Implementation Strategy
- Implement a "Fatigue Model" tab that takes sleep history (from `user_profile`) and projects performance capabilities for the next 24 hours.
- Experiment with a hybrid model: `Predicted_Performance = SAFTE_Score * (Current_HRV / Baseline_HRV)`.

## 3. Human Performance in UAV Combat Simulations

### Open-Source Frameworks & Research
- **OpenEaagles (Open Extensible Architecture for the Analysis and Generation of Linked Simulations)**: A C++ framework used for building distributed simulation applications. It is widely used in defense for flight and combat simulation.
- **AFRL's AFSIM (Advanced Framework for Simulation, Integration and Modeling)**: While controlled, there are open components and academic interfaces. It allows for detailed modeling of operator constraints.
- **Research focus**:
    - **Human-in-the-Loop (HITL)**: Connecting physiological streams (HRV, EEG) directly to the simulation engine. If the operator's fatigue (modelled or measured) exceeds a threshold, the UAV swarm control interface simplifies or autonomy increases.
    - **Cognitive Workload Modeling**: Using metrics like "Task Load Index" derived from heart rate to dynamic task allocation between human and AI agents.

### Path Forward
- Explore integrating a lightweight Python-based simulation (e.g., simple UAV swarm task) into the Streamlit app to serve as a "Cognitive Stress Test".
- Monitor HRV/HRF changes during this simulated task to validate readiness scores.

---
*Append future updates below this line.*

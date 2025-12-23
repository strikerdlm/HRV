# Research Updates & Implementation Plan 2026

**Status:** Draft / Planning
**Date:** 2025-12-23
**Focus:** Advanced physiological metrics, biomathematical fatigue modelling, and human-autonomy teaming simulations.

---

## 1. Heart Rate Fragmentation (HRF)

### Scientific Foundation
Heart Rate Fragmentation (HRF) is a family of metrics introduced by Costa et al. (2017) to quantify the "roughness" of the interbeat interval time series. Unlike traditional short-term HRV (which is dominated by respiratory sinus arrhythmia) or long-term HRV (dominated by circadian/activity rhythms), HRF captures rapid, frequent changes in heart rate acceleration sign that are inconsistent with smooth autonomic control.

**Key Metrics:**
*   **PIP (Percentage of Inflection Points):** The percentage of times the heart rate acceleration changes sign (accelerate -> decelerate or vice versa). High values indicate "jagged" rhythms.
*   **IALS (Inverse of Average Length of Segments):** The inverse of the average duration of unidirectional acceleration/deceleration segments.
*   **PSS (Percentage of Short Segments):** Percentage of segments with duration < 3 beats.
*   **PAS (Percentage of Alternant Segments):** Percentage of segments with alternating acceleration signs.

### Clinical & Performance Relevance
*   **Cardiovascular Risk:** HRF is a robust predictor of Major Adverse Cardiac Events (MACE) and Sudden Cardiac Death (SCD), often outperforming traditional HRV measures in high-risk cohorts (MADIT-II). It reflects the breakdown of neuroautonomic coupling and the emergence of erratic sinus rhythm.
*   **Cognitive Performance:** High fragmentation suggests a loss of "integrated" control. While RSA reflects healthy vagal flexibility, fragmentation reflects system noise. In operator states, high HRF may correlate with acute stress, cognitive overload, or fatigue-induced breakdown of top-down regulation.
*   **Aging:** HRF consistently increases with age, independent of traditional HRV decline, serving as a marker of biological aging of the cardiovascular system.

### Implementation Status
*   **Current State:** The core logic is implemented in `app/hrv_core.py` (`compute_heart_rate_fragmentation`).
*   **Plan:**
    1.  **UI Exposure:** Ensure HRF metrics (PIP, IALS) are displayed in the "Nonlinear" analysis tab.
    2.  **Interpretation:** Add tooltip guidance distinguishing HRF (noise/breakdown) from RMSSD (vagal tone). High RMSSD is generally good; High HRF is generally bad.
    3.  **Research:** Pilot correlation of HRF with cognitive task performance (MATB) in the simulation module.

---

## 2. Biomathematical Models of Human Performance

### Overview
Biomathematical models (BMMs) predict fatigue and performance capability based on sleep history, circadian phase, and time awake. They are essential for Fatigue Risk Management Systems (FRMS).

### Key Models
1.  **Two-Process Model (Borbély, 1982):**
    *   **Process S (Homeostatic):** Sleep pressure builds during wakefulness (exponential saturation) and dissipates during sleep.
    *   **Process C (Circadian):** A sinusoidal oscillator independent of sleep/wake.
    *   **Alertness:** $Alertness = C - S$.

2.  **Three-Process Model (Åkerstedt & Folkard):**
    *   Adds **Process W (Sleep Inertia):** A transient depression of alertness immediately upon awakening (exponential decay, $\tau \approx 2h$).

3.  **SAFTE (Sleep, Activity, Fatigue, and Task Effectiveness):**
    *   Used by US Dept of Defense (FAST) and DOT.
    *   Includes a "Sleep Reservoir" (akin to Process S), circadian modulation of reservoir outflow, and sleep inertia.
    *   Predicts **Performance Effectiveness** (0-100 scale) and **Reaction Time**.

### Implementation Plan
*   **Refinement:** Enhance the existing `fatigue_calculator` module to explicitly expose Process S and Process C components for visualization.
*   **Personalization:** Allow users to tune "Sleep Need" (reservoir capacity) and "Circadian Amplitude" (chronotype strength).
*   **Validation:** Compare model predictions against subjective fatigue (KSS) and objective performance (PVT) entered by the user.

---

## 3. Combat & UAV Simulations for Research

### Objective
To assess human performance in realistic, high-workload environments, static cognitive tests (like PVT) are insufficient. Dynamic simulations of "Human-Autonomy Teaming" (HAT) are required.

### AF-MATB (Multi-Attribute Task Battery)
*   **Description:** The standard for aviation workload research. Requires the operator to simultaneously perform tracking, system monitoring, resource management, and communications.
*   **Open Source:** "OpenMATB" (Python/HTML5 variants) allows integration into web apps.
*   **Metrics:** Reaction time, error rate, resource deviations, composite workload score.

### UAV Swarm Simulation
*   **Scenario:** Operator manages a swarm of semi-autonomous drones.
*   **Task:** Assign targets, monitor fuel/health, intervene when automation fails.
*   **Research Utility:** Tests "vigilance decrement" (monitoring automation) and "saturation" (task overload during swarm anomalies).
*   **Technologies:** Python (PyGame), Unity, or lightweight JS canvas apps embedded in Streamlit.

### Implementation Plan (2026)
1.  **Embedded Simulation Tab:** Add a "Performance Lab" tab in the application.
2.  **Simple MATB:** Implement a simplified Resource Management task (fuel tanks balancing) and Tracking task using Streamlit custom components or a simple Python-driven canvas.
3.  **Data Link:** Synchronize simulation event timestamps with HRV data to analyze "Phasic HRV" (response to specific events) vs. "Tonic HRV" (baseline load).
4.  **Hypothesis:** High HRF and low HRV (RMSSD) will predict performance degradation in the 2nd hour of continuous UAV monitoring (vigilance decrement).

---

## 4. References & Literature

*   **Costa, M. D., Davis, R. B., & Goldberger, A. L. (2017).** Heart Rate Fragmentation: A New Approach to the Analysis of Cardiac Interbeat Interval Dynamics. *Frontiers in Physiology*, 8, 255.
*   **Borbély, A. A. (1982).** A two process model of sleep regulation. *Human Neurobiology*, 1(3), 195–204.
*   **Hursh, S. R., et al. (2004).** Fatigue models for applied research in warfighting. *Aviation, Space, and Environmental Medicine*, 75(3 Suppl), A44-53.
*   **Santiago-Espada, Y., et al. (2011).** The Multi-Attribute Task Battery II (MATB-II) Software for Human Performance and Workload Research: A User’s Guide. *NASA Technical Memorandum*.

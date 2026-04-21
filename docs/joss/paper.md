---
title: 'Mission Control — Flight Surgeon: an open-source reference implementation of the Operational Performance Indicator (OPI) framework for aviation and unmanned aircraft system operators'
tags:
  - Python
  - TypeScript
  - Next.js
  - FastAPI
  - heart rate variability
  - HRV
  - SAFTE
  - operator readiness
  - aviation human factors
  - unmanned aircraft systems
authors:
  - name: Diego Malpica
    orcid: 0000-0000-0000-0000   # TODO: replace with actual ORCID before JOSS submission
    affiliation: 1
    corresponding: true
affiliations:
  - name: Aerospace Medicine, Bogotá, Colombia   # TODO: update institutional affiliation
    index: 1
date: 21 April 2026
bibliography: paper.bib
---

# Summary

**Mission Control — Flight Surgeon** is an open-source biomathematical platform that implements the Operational Performance Indicator (OPI) framework for aviation and unmanned aircraft system (UAS) operators. OPI is a task-calibrated composite readiness index that fuses four biomathematical components — SAFTE-style reservoir fatigue effectiveness, heart-rate-variability (HRV) derived autonomic markers, task-specific cognitive-load modifiers grounded in Multiple Resource Theory [@wickens2002; @wickens2008], and environmental or operational modifiers — into a single per-task readiness score with interpretable category bands. The framework covers ten manned-aviation task categories (instrument flight, night-vision operations, helmet-mounted-display flying, high-density air-traffic control, critical and non-critical emergencies, test-pilot operations, carrier landing, weapons delivery, and new-platform testing) and seven UAS or teleoperator categories (intelligence-surveillance-reconnaissance, strike, search-and-rescue, autonomous-swarm supervisory control, contested-environment operations, ground-robot teleoperation, and subsea or long-latency teleoperation). For the UAS subset, OPI extends the composite with a Warm-type vigilance-decrement model [@warm2008] and a Chen-type logarithmic control-latency penalty [@chen2007].

The platform is delivered through a Next.js 14 client over a FastAPI orchestration layer and a shared Python biomathematical backend. It exposes standards-aligned HRV analytics [@shaffer2017; @quigley2024], a reservoir-based SAFTE implementation [@hursh2004] mirrored in TypeScript for responsive operational displays, deterministic readiness-fusion logic, longitudinal user-profile persistence, environmental-context ingestion (including NOAA space-weather feeds as an optional modifier), and structured export utilities for auditable reporting.

# Statement of need

Operator-state monitoring in aviation and UAS operations increasingly combines physiological signals, biomathematical fatigue models, and subjective workload ratings. Published approaches fall into three families: single-channel pipelines (HRV-only, SAFTE-only, or EEG/fNIRS/eye-tracking head-worn sensing [@hamann2025]), cognitive-architecture or composite-score studies constrained to narrow task slices [@stevens2022; @feng2018], and machine-learning classifiers trained on individual populations [@vogl2025; @jin2025]. A recent systematic review identified the absence of unified frameworks integrating physiological signals, biomathematical fatigue, and task-specific weighting as a principal research gap for UAS operators [@li2025]. A parallel review called for "an infrastructure for physiological monitoring and integrated analyses" combined with explainable and interpretable modelling for military operators [@rabat2025]. Kubios [@tarvainen2014] provides mature HRV analytics but does not extend to task-calibrated readiness fusion; the Fatigue Avoidance Scheduling Tool [@hursh2004] provides validated fatigue forecasting but does not integrate HRV or cognitive-load modifiers.

Mission Control — Flight Surgeon addresses this gap by shipping an open-source, inspectable, extensible implementation of the OPI framework. The software is intended for researchers and operational teams who need a transparent substrate on which task-specific calibration, new task categories, or future classifier hybridisation can be layered without losing auditability. It is not a certified medical device or regulated decision-support system; it is a research and development tool.

# Functionality

The platform implements the following capabilities relevant to JOSS scope:

- **HRV analytics (`app/hrv_core.py`).** Computes time-domain (RMSSD, SDNN, pNNx family, CVNN, MAD-NN), frequency-domain (VLF/LF/HF power, LF/HF ratio, Welch and Lomb-Scargle spectral estimation), and nonlinear (SD1, SD2, SampEn, DFA-$\alpha_1$, $\alpha_2$, Poincaré ellipse area, Baevsky stress index) metrics from RR-interval series with bounded artefact heuristics and linear interpolation.

- **SAFTE fatigue model (`app/fatigue_calculator/safte_model.py`).** Reservoir-based implementation with 24-hour and 12-hour circadian harmonics, sleep-inertia handling, and optional phase-shift behaviour for jet-lag or schedule-transition use cases. A TypeScript mirror (`frontend/src/lib/safte-model.ts`) reproduces the canonical Python equations for responsive client-side displays.

- **OPI readiness fusion (`app/scheduling_core.py`, `app/frms.py`, `app/frms_v2.py`).** Deterministic weighted fusion of SAFTE effectiveness, HRV-derived recovery and autonomic-reserve indices, task-complexity modifiers, stress-index penalty, and (for UAS tasks) vigilance-capacity and latency-penalty terms. Per-task weight profiles and thresholds are specified for all 17 task categories. The fusion logic is rule-based and inspectable rather than opaque.

- **User-profile persistence (`app/user_profile_tab.py`, `app/user_database.py`).** Longitudinal storage of operator characteristics, assessment history, and context variables propagated into downstream readiness calculations.

- **Environmental modifiers (`app/noaa_space.py`, `app/space_weather_impact.py`, `app/space_weather_alignment.py`).** Ingestion and alignment of NOAA Space Weather Prediction Center feeds with bounded caching. Environmental inputs are treated as optional modifiers, not as primary causal physiology.

- **FastAPI orchestration (`api/main.py`, `api/research_endpoints.py`).** Structured endpoints exposing HRV analytics, scheduling, readiness, user-profile, and environmental context over HTTP for the Next.js client and for programmatic access.

- **Delivery surfaces (`frontend/`).** Next.js 14 operational client (mission-control workflows) and research client (HRV, fatigue, readiness, correlation views). Streamlit entrypoints under `app/` remain as secondary interfaces.

- **Reproducibility tooling (`app/publication_export.py`, `app/export_utils.py`, `analysis/opi_worked_example.py`).** Structured export of statistical summaries, confidence intervals, effect-size reports, and manuscript-oriented artefacts. A worked-example script reproduces the framework-instantiation outputs used in the accompanying methodology paper.

The test surface under `tests/` exercises readiness-fusion behaviour, FRMS and SAFTE logic, NOAA ingestion and alignment, API endpoint normalisation, and broader statistical and charting modules. Integration tests span the OPI pathway end-to-end at the software level. These tests represent engineering verification and do not substitute for field validation of the framework's predictive properties, which is explicitly positioned as future work.

# Research context

A companion methodology paper introducing the OPI framework and its theoretical grounding has been prepared for submission to *Applied Ergonomics*. That paper specifies the framework formulation, per-task weight profiles, vigilance-decrement and latency models, and an illustrative worked example. The present JOSS submission cites the software itself as an independent scholarly contribution; it does not duplicate the methodology paper.

# Acknowledgements

The author acknowledges the open-source scientific Python ecosystem, the Node.js and Next.js communities, and the public technical and data resources that inform the environmental-modifier modules (NOAA Space Weather Prediction Center). The theoretical basis of the framework draws on foundational human factors research on Multiple Resource Theory, vigilance, teleoperation, fatigue modelling, and situation awareness.

# References

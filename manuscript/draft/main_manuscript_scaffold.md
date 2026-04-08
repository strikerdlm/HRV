# Author: Dr Diego Malpica MD

## Title

**Mission Control - Flight Surgeon: an open-source aerospace medicine platform for HRV analytics, fatigue modeling, space-weather context, and operational decision support**

**Running title:** Aerospace Physiology Ops Platform

## Structured Abstract

### Background and objective

[Draft in 2-3 sentences]

This manuscript describes **Mission Control - Flight Surgeon**, an open-source software platform designed to support aerospace medicine research and operational workflows by integrating heart rate variability (HRV) analytics, longitudinal user context, circadian and fatigue modeling, space-weather context, and mission-oriented decision support.

### Methods

[Draft in 3-4 sentences]

Describe:

- the shared Python analysis core,
- the operational and research Streamlit entrypoints,
- the FastAPI plus Next.js deployment pathway,
- the main validation posture as engineering verification plus bounded exploratory evidence.

### Results

[Draft in 3-4 sentences]

Only report:

- implemented architecture and reproducibility assets,
- tested module families,
- any curated quantitative artifacts whose provenance is fully documented.

### Conclusions

[Draft in 2-3 sentences]

Conclude on integration, translational utility, and current validation boundaries. Avoid claims of outcome improvement or certification unless new evidence is added.

### Keywords

- heart rate variability
- aerospace medicine
- fatigue risk management
- circadian modeling
- decision support systems
- space weather
- physiological monitoring
- open-source software

## 1. Introduction

### 1.1 Context and significance

Heart rate variability (HRV) is widely used as a non-invasive marker of autonomic regulation and has become a common analytic layer in research on recovery, workload, vigilance, sleep disruption, and physiological readiness (Task Force of the European Society of Cardiology and the North American Society of Pacing and Electrophysiology, 1996; Shaffer & Ginsberg, 2017; Quigley et al., 2024). However, the practical value of HRV depends on more than the calculation of RMSSD, SDNN, or spectral indices alone. Interpretation is highly conditioned by measurement protocol, artifact handling, record duration, respiratory context, sleep history, circadian phase, workload exposure, and the intended operational decision. In safety-critical environments, this means that even technically correct HRV values can be operationally misleading if they are detached from the broader physiological and environmental context.

Aerospace medicine and related operational domains amplify this problem. Flight crews, spaceflight analog participants, and other mission-critical personnel operate under schedules that are constrained by circadian misalignment, accumulated fatigue, variable sleep opportunity, environmental stressors, and mission tasking rather than by isolated laboratory conditions. Aviation fatigue management therefore increasingly depends on ecological monitoring rather than on single time-point assessments. A recent narrative review on consumer sleep technologies in aviation argued that longitudinal field monitoring could strengthen fatigue risk management systems (FRMS), but also emphasized that such technologies must be used within scientifically and operationally appropriate frameworks rather than as stand-alone gadgets (Devine & Hursh, 2025). Likewise, work in military and civil aviation continues to show that fatigue perceptions, mitigation strategies, and circadian typology interact in ways that matter for operational risk, even when organizations already use fatigue-management tools (Morris et al., 2020).

The same need for contextualization applies to environmental physiology. A subset of the literature suggests that geomagnetic and solar activity may be associated with measurable changes in autonomic regulation and cardiovascular risk, although the causal pathways remain incompletely understood and the evidence base remains heterogeneous (Alabdulgader et al., 2018; Gaisenok et al., 2025). For an aerospace medicine platform, such environmental information is not a curiosity; it is part of the domain context in which physiological measurements may be collected and interpreted. This becomes particularly relevant when the intended users are researchers, flight surgeons, and operational teams who need auditable, reproducible, and cross-linked interpretations rather than disconnected dashboards.

These constraints motivate a systems-level view of translational physiology software. A useful platform for aerospace medicine should not merely compute HRV metrics. It should also connect measurement to person-specific context, fatigue and circadian models, environmental overlays, operational readiness logic, and reproducible exports. The present manuscript addresses that need by documenting a full-platform software system rather than a single analytic module.

### 1.2 State of the art

The existing tool landscape can be grouped into several partially overlapping categories. First, dedicated HRV analysis packages provide strong signal-processing and analytics functionality. Kubios HRV is the clearest example of a mature and widely used platform in this space, offering artifact correction, flexible preprocessing, time-domain and frequency-domain analysis, nonlinear metrics, and export functions (Tarvainen et al., 2014). More extensible processing frameworks such as PhysioScripts emphasize open and customizable physiological data pipelines that researchers can adapt to different measurement types (Christie & Gianaros, 2013). More recent tools, such as the open-source Fatmaxxer application for exercise DFA-alpha1 analysis, show that low-cost or domain-specific HRV tools can be validated against established software for narrower use cases (Rogers et al., 2025). These systems are important benchmarks for analytic quality, but they are primarily designed around signal analysis rather than translational operational decision support.

Second, a different body of work has focused on interoperability and context-aware physiological monitoring architectures. Arney et al. (2023) described an open-source, interoperable architecture for generating real-time surgical team cognitive alerts from HRV monitoring. That work is particularly relevant because it demonstrates that HRV can be embedded in a modular, multi-user, context-aware software architecture. At the same time, the authors explicitly distinguish architecture verification from algorithmic or clinical validation, noting that their prototype was intended to verify the data pipeline and interoperability pattern rather than to establish final validity of the cognitive-load inference itself. This distinction is important for the present manuscript because it provides a precedent for responsibly reporting integrated physiological software systems whose strongest immediate evidence lies in architecture and engineering verification.

Third, fatigue and circadian decision tools have developed largely along a separate trajectory. The Fatigue Avoidance Scheduling Tool (FAST), built on the SAFTE model, was developed to compare schedules in terms of predicted effectiveness and to support mission or duty planning in fatigue-sensitive operations (Hursh et al., 2004). Related aviation and sleep research continues to demonstrate the importance of combining schedule exposure, fatigue perceptions, mitigation strategies, and circadian considerations when assessing operational risk (Morris et al., 2020; Devine & Hursh, 2025). In parallel, wearable-based circadian physiology methods have shown that daily physiological rhythms can be inferred from widely used consumer devices, opening a path toward personalized circadian analytics outside the laboratory (Bowman et al., 2021). These contributions are highly relevant, but they typically prioritize either fatigue forecasting or circadian inference rather than integrating them with standards-informed HRV analysis, longitudinal user profiles, and operational decision logic in one open platform.

Fourth, multimodal wearable monitoring and health-platform research has expanded rapidly. Multi-wearable approaches for tracking diurnal light exposure and body rhythms in night-shift workers suggest that distributed sensing can support ecological circadian and health monitoring in high-risk populations (Hartmeyer et al., 2025). AI-edge and multimodal physiological monitoring platforms show how multiple streams can be fused at the sensing or device layer (Yang et al., 2020). These systems are valuable examples of sensor integration, but they generally do not provide a full translational pathway from standardized HRV analysis through fatigue and environmental interpretation to auditable operational outputs tailored to aerospace medicine.

Taken together, the literature shows strong progress in HRV analytics, open physiological processing, real-time contextual monitoring, fatigue forecasting, circadian inference, and wearable integration. What remains less well represented is an open, reproducible platform that unifies these components specifically for aerospace and operational medicine workflows. Table 2 summarizes this landscape and motivates the present manuscript’s focus on integration and translational deployment rather than on a single algorithmic advance.

### 1.3 Gap statement

Current tools do not adequately combine standards-informed HRV analytics, individualized physiological context, circadian and fatigue modeling, environmental overlays, and operational scheduling logic within one open, reproducible aerospace medicine platform. Existing systems are often excellent within their own scope, but they tend to specialize in one of four roles: HRV analysis software, physiological data-processing infrastructure, fatigue or circadian forecasting, or multimodal sensing. As a result, researchers and operational users who need an integrated workflow must often bridge multiple tools manually, with inconsistent provenance, limited audit trails, and uncertain transferability from exploratory analysis to operational action.

### 1.4 Objective and contribution

The objective of this work is to describe the design, implementation, and bounded verification of **Mission Control - Flight Surgeon**, an open-source translational software platform for aerospace medicine research and operational physiology. Rather than proposing a new standalone biomarker, the platform is designed to integrate validated and standards-informed analytic elements into one reproducible system that can support both exploratory research and mission-oriented workflows.

This work makes four main contributions. First, it documents an integrated software architecture for translational aerospace medicine that links HRV analytics, longitudinal user context, circadian and fatigue modeling, environmental and space-weather overlays, and operational scheduling logic. Second, it presents a shared Python analysis core exposed through separate research and operational interfaces, including Streamlit, FastAPI, and a modern web frontend. Third, it describes a decision-support layer that translates physiological and schedule information into readiness-oriented outputs, including crew-level scheduling and GO/NO-GO logic. Fourth, it provides a reproducibility-oriented reporting structure that explicitly separates implemented capabilities, engineering verification, exploratory analyses, and evidence gaps that still require formal external validation.

## 2. Methods

### 2.1 Requirements and design rationale

The platform was designed as a translational system rather than as a single-purpose analysis package. The main functional requirement was to support workflows that begin with physiological measurement but end with either interpretable research outputs or operationally relevant summaries. This required a software design that could handle RR-interval and wearable-derived inputs, compute standard HRV domains, preserve longitudinal user context, incorporate circadian and fatigue state information, and expose the resulting outputs in a form useful to both investigators and operational users.

Several non-functional requirements shaped the architecture. First, the platform needed to support transparent and reproducible computation. This requirement favored deterministic implementations, explicit parameterization, exportable outputs, and a preference for bounded rather than opaque decision logic. Second, the platform needed to support operational auditability. In practice, this meant keeping track of user context, schedule assumptions, and derived outputs in a way that could be revisited or exported, rather than relying on transient interface state alone. Third, the system had to support translational flexibility: a research user may want broad exploratory analysis and richer diagnostic views, whereas an operational user may need a narrower, faster interface centered on readiness, crew context, and risk mitigation.

The design rationale was therefore to separate **analytic breadth** from **operational focus** without duplicating the computational core. Research-facing workflows were implemented through a broad Streamlit surface that prioritizes exploration, visualization, and cross-domain analysis. Operational workflows were implemented through a lighter Streamlit entrypoint that emphasizes crew workspace management, scheduling, and actionable summaries. A FastAPI layer and a Next.js frontend extend the same core modules to a more modern web application architecture. This dual-path design was chosen to support both rapid scientific iteration and more structured operational deployment.

Domain-specific design choices were also influenced by aerospace and fatigue-management reference frameworks. Modules related to readiness, scheduling, and safety framing were designed with reference to published fatigue-modeling and operational guidance, including FAST/SAFTE literature, NASA human-systems standards, and aviation fatigue-management concepts such as those summarized in ICAO Doc 9966. These references inform threshold selection and workflow logic, but the platform is not presented here as a certified or regulated medical device.

### 2.2 System architecture

The platform is organized around a shared Python analysis core located primarily under `app/`. This core contains the HRV computation engine, environmental data ingestion modules, fatigue and circadian logic, user-profile management, scheduling and decision-support modules, and export utilities. The repository also includes testing modules under `tests/`, API delivery under `api/`, and a web frontend under `frontend/`.

Two Streamlit entrypoints expose different views of the same underlying system. The research entrypoint, `app/research_app.py`, delegates to the broader research interface implemented in `app/app.py`. This research mode exposes the full analytic workbench, including HRV analysis, visualization, environmental overlays, and exploratory workflows. The operational entrypoint, `app/operational_app.py`, is narrower by design. It initializes a crew-oriented workspace, mission context, scheduling and experiment interfaces, and user-profile views intended for lower-friction operational use. This distinction is architectural rather than conceptual: both entrypoints rely on the same underlying modules for analysis and persistence.

In parallel, the repository provides a FastAPI backend in `api/main.py`. The API exposes structured endpoints for health checks, mission context, user profiles, experiments, scheduling, HRV summaries, and space-weather data. This backend allows the same analytic core to be consumed by a Next.js frontend, creating a second delivery surface that is more suitable for modern responsive web workflows. The manuscript therefore treats the platform as a dual-interface system: exploratory research tools and operational decision-support interfaces are different views over one analytic substrate.

User persistence is handled through the platform’s profile and database layers, including `app/user_profile_tab.py` and `app/user_database.py`. These modules provide longitudinal storage of user characteristics, assessment history, and context variables that are subsequently propagated into fatigue, readiness, and interpretation workflows. The effect is that HRV or environmental outputs are not computed as context-free numbers; they are interpreted relative to person-level and mission-level information when such context is available.

The core data flow is modular. RR intervals are ingested and cleaned before HRV metrics are computed across time-domain, frequency-domain, nonlinear, and windowed representations. Environmental context is fetched through dedicated ingestion layers such as `app/noaa_space.py`, which harmonizes and caches NOAA-derived space-weather data. Additional domain layers then consume both physiological and contextual information. Fatigue and circadian modules transform sleep- and schedule-related inputs into readiness-relevant states; scheduling modules integrate these states into crew-level decision logic; and export modules assemble structured summaries suitable for reporting or audit. This composition-oriented architecture allows the platform to support both isolated analyses and cross-layer workflows.

### 2.3 Implementation

The HRV engine is centered in `app/hrv_core.py`. Based on repository documentation and source inspection, this module supports artifact handling and the computation of common short-term HRV families, including time-domain metrics, frequency-domain measures, geometric indices, nonlinear measures, and windowed summaries. The broader platform supplements this engine with interpretation logic, longitudinal context handling, and UI-specific presentation layers. Input formats include Polar-style RR interval files and normalized wearable-derived data, allowing the computational core to remain independent of any single acquisition device.

Operational decision support is implemented primarily through `app/scheduling_core.py`, `app/scheduling_engine.py`, and `app/scheduling_tab.py`. These modules provide rule-based scoring and integration for physiological and schedule-related variables, including SAFTE-derived effectiveness mapping, Karolinska Sleepiness Scale (KSS) and psychomotor vigilance task (PVT) related scoring pathways, energy-availability and hydration components, circadian alignment, and task-specific modifiers. The repository documents explicit threshold logic and bounded scoring, which is important for reproducibility and for later manuscript discussion of auditability.

Environmental and space-weather context is implemented through modules such as `app/noaa_space.py`, `app/space_weather_impact.py`, and `app/space_weather_alignment.py`. The NOAA ingestion layer normalizes selected feeds and caches them locally with bounded time-to-live behavior. Downstream modules use this information to support temporal alignment, impact timing, and exploratory coupling with physiological outputs. At the manuscript level, these modules are important not because they establish a causal effect of space weather on physiology, but because they instantiate a domain-specific environmental layer that is uncommon in generic HRV software.

Reproducibility and reporting are supported by export layers including `app/publication_export.py` and `app/export_utils.py`. These modules were designed to produce structured statistical summaries, confidence intervals, effect-size reporting, and other manuscript-oriented artifacts. Their presence is relevant to the current paper because they show that reporting support was treated as a first-class implementation concern rather than as a downstream manual task.

### 2.4 Validation and evaluation methodology

The validation posture adopted in this manuscript is tiered. The strongest evidence currently available in the repository is **engineering verification** rather than full prospective validation of the integrated platform. Accordingly, the Methods and Results sections distinguish between implemented capabilities, software verification, exploratory quantitative artifacts, and validation work that remains future-facing.

Engineering verification is represented by the repository’s automated test surface. The most manuscript-relevant test domains include scheduling and readiness logic (`tests/test_scheduling_core.py`), fatigue and FRMS behavior (`tests/test_frms.py`, `tests/test_frms_v2.py`, `tests/test_fatigue_integration.py`), space-weather ingestion and alignment (`tests/test_noaa_cache.py`, `tests/test_space_weather_impact.py`, `tests/test_space_weather_alignment.py`), broader statistical and scientific charting modules (`tests/test_comprehensive_modules.py`), and selected API or endpoint behaviors such as profile normalization and windowed research endpoints (`tests/test_api_user_profile_normalization.py`, `tests/test_research_windowed_endpoint.py`). These tests justify reporting the platform as implemented and partly verified at the software level.

Exploratory quantitative artifacts are also present in the repository, including exported lag-aware HRV to space-weather correlation tables under `analysis/`. However, these outputs are not treated here as publication-ready scientific findings unless their analytical provenance can be fully documented, including cohort definition, unit of analysis, preprocessing, alignment rules, and inferential scope. In the present manuscript strategy, such artifacts are therefore considered optional demonstrations of analytic capability rather than default headline results.

Importantly, this manuscript does not treat engineering verification as a substitute for external numerical benchmarking or human-subject validation. In particular, although the HRV engine is clearly implemented, the repository does not yet provide a manuscript-ready benchmark against a trusted reference package across the full integrated platform. Likewise, if future versions of the manuscript include retrospective or prospective participant data, those analyses will require dedicated protocol description, ethics reporting, and design-specific reporting guidance. The current evaluation methodology is therefore intentionally conservative: it reports what the repository can substantiate today while reserving stronger claims for future validation studies.

## 3. Results

### 3.1 System implementation summary

[Draft]

Report the final implemented platform components and deployment pathways.

### 3.2 Engineering verification

[Draft]

Summarize verified domains using representative test files and module families.

### 3.3 Reproducibility and reporting assets

[Draft]

Report:

- repository URL,
- license,
- branch and commit hash,
- environment expectations,
- export and logging support.

### 3.4 Optional curated analysis vignette

[Draft only if provenance is documented]

Candidate material:

- lag-aware HRV to space-weather exploratory outputs,
- windowed longitudinal analytics,
- scheduling and readiness examples tied to documented inputs.

## 4. Discussion

### 4.1 Principal findings

[Draft]

Emphasize platform integration, translational reach, and auditability.

### 4.2 Interpretation in context of the literature

[Draft]

Position the platform relative to HRV software, fatigue tools, circadian wearable methods, and multimodal monitoring systems.

### 4.3 Strengths and limitations

[Draft]

Required limitations:

- incomplete external benchmarking of the integrated platform,
- uneven evidence depth across module families,
- broad scope relative to a single-purpose software paper,
- lack of certification evidence.

### 4.4 Implications for operational and clinical translation

[Draft]

Address:

- mission medicine,
- crew readiness workflows,
- research-to-operations transfer,
- training and governance requirements before deployment.

### 4.5 Future work

[Draft]

Include:

- external benchmarking,
- prospective validation studies,
- formal data-sharing pathways,
- possible regulatory maturation.

## 5. Compliance and Transparency

### 5.1 Data availability statement

[Draft from `manuscript/evidence/compliance_and_transparency_map.md`]

### 5.2 Code and artifact availability

[Draft from `manuscript/evidence/compliance_and_transparency_map.md`]

### 5.3 Ethics and regulatory alignment

[Draft from `manuscript/evidence/compliance_and_transparency_map.md`]

### 5.4 Author contributions

[Insert final CRediT roles]

### 5.5 Funding and conflict of interest

[Insert final declarations]

### 5.6 Acknowledgments

[Insert contributors and infrastructure acknowledgments]

## References

Seed references are collected in `manuscript/references/seed_references.md`.

## Supplementary materials

Supplementary structure is planned in `manuscript/supplement/supplement_outline.md`.

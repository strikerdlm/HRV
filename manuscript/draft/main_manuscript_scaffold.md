# Author: Dr Diego Malpica MD

## Title

Mission Control - Flight Surgeon: an open-source biomathematical platform for HRV, fatigue-circadian modeling, and aerospace readiness

**Running title:** Aerospace Biomath Platform

## Structured Abstract

### Background and objective

Mission Control - Flight Surgeon is an open-source biomathematical software platform that couples a Next.js client to a FastAPI/Python backend for heart rate variability (HRV) analytics, fatigue-circadian modeling, environmental alignment, and aerospace readiness support. This manuscript describes the translational platform, defines its layered model stack, and reports its current verification posture without overstating external validation.

### Methods

The manuscript documents an API-backed Next.js frontend over a FastAPI orchestration layer and shared Python modeling core, while retaining Streamlit as a secondary repository interface. Methods focus on multistage HRV preprocessing and metric extraction, reservoir-based SAFTE-style fatigue and circadian dynamics, deterministic readiness and scheduling fusion, environmental timing and alignment models, and reproducibility infrastructure. Evaluation is intentionally bounded to supported evidence, emphasizing architecture inspection, automated software verification, and auditable reporting assets rather than human-subject validation.

### Results

The implemented system centers on a Next.js client backed by FastAPI endpoints and a shared Python model stack that integrates HRV analytics, longitudinal user persistence, fatigue-circadian dynamics, environmental alignment, and readiness-oriented scheduling logic. Automated tests verify representative operational domains including scheduling and FRMS behavior, space-weather caching and alignment, API normalization, and endpoint-level analytics. Public code availability, deterministic rule-based fusion, mirrored client and backend fatigue logic, and structured export utilities support reproducible and auditable workflows, although external numerical benchmarking and participant-level validation remain incomplete.

### Conclusions

Mission Control - Flight Surgeon extends beyond single-purpose HRV software by coupling a Node-first client architecture to an explicit biomathematical backend for physiological inference and readiness support. The current evidence base supports a systems-and-modeling contribution with strong implementation detail and engineering verification, while stronger claims regarding numerical benchmarking, clinical benefit, or operational effectiveness require dedicated future validation.

### Keywords

- heart rate variability
- biomathematical modeling
- aerospace medicine
- fatigue risk management
- circadian modeling
- Next.js
- decision support systems
- space weather
- physiological monitoring
- open-source software

## 1. Introduction

### 1.1 Context and significance

Heart rate variability (HRV) is widely used as a non-invasive marker of autonomic regulation and has become a common analytic layer in research on recovery, workload, vigilance, sleep disruption, and physiological readiness (Task Force of the European Society of Cardiology and the North American Society of Pacing and Electrophysiology, 1996; Shaffer & Ginsberg, 2017; Quigley et al., 2024). However, the practical value of HRV depends on more than the calculation of RMSSD, SDNN, or spectral indices alone. Interpretation is highly conditioned by measurement protocol, artifact handling, record duration, respiratory context, sleep history, circadian phase, workload exposure, and the intended operational decision. In safety-critical environments, this means that even technically correct HRV values can be operationally misleading if they are detached from the broader physiological and environmental context.

Aerospace medicine and related operational domains amplify this problem. Flight crews, spaceflight analog participants, and other mission-critical personnel operate under schedules that are constrained by circadian misalignment, accumulated fatigue, variable sleep opportunity, environmental stressors, and mission tasking rather than by isolated laboratory conditions. Aviation fatigue management therefore increasingly depends on ecological monitoring rather than on single time-point assessments. A recent narrative review on consumer sleep technologies in aviation argued that longitudinal field monitoring could strengthen fatigue risk management systems (FRMS), but also emphasized that such technologies must be used within scientifically and operationally appropriate frameworks rather than as stand-alone gadgets (Devine & Hursh, 2025). Likewise, work in military and civil aviation continues to show that fatigue perceptions, mitigation strategies, and circadian typology interact in ways that matter for operational risk, even when organizations already use fatigue-management tools (Morris et al., 2020).

The same need for contextualization applies to environmental physiology. A subset of the literature suggests that geomagnetic and solar activity may be associated with measurable changes in autonomic regulation and cardiovascular risk, although the causal pathways remain incompletely understood and the evidence base remains heterogeneous (Alabdulgader et al., 2018; Gaisenok et al., 2025). For an aerospace medicine platform, such environmental information is not a curiosity; it is part of the domain context in which physiological measurements may be collected and interpreted. This becomes particularly relevant when the intended users are researchers, flight surgeons, and operational teams who need auditable, reproducible, and cross-linked interpretations rather than disconnected dashboards.

These constraints motivate a systems-level view of translational physiology software. A useful platform for aerospace medicine should not merely compute HRV metrics. It should also connect measurement to person-specific context, biomathematical fatigue and circadian models, environmental overlays, operational readiness logic, and reproducible exports. The present manuscript addresses that need by documenting a layered biomathematical software system with a Next.js client and Python modeling backend rather than a single analytic module.

### 1.2 State of the art

The existing tool landscape can be grouped into several partially overlapping categories. First, dedicated HRV analysis packages provide strong signal-processing and analytics functionality. Kubios HRV is the clearest example of a mature and widely used platform in this space, offering artifact correction, flexible preprocessing, time-domain and frequency-domain analysis, nonlinear metrics, and export functions (Tarvainen et al., 2014). More extensible processing frameworks such as PhysioScripts emphasize open and customizable physiological data pipelines that researchers can adapt to different measurement types (Christie & Gianaros, 2013). More recent tools, such as the open-source Fatmaxxer application for exercise DFA-alpha1 analysis, show that low-cost or domain-specific HRV tools can be validated against established software for narrower use cases (Rogers et al., 2025). These systems are important benchmarks for analytic quality, but they are primarily designed around signal analysis rather than translational operational decision support.

Second, a different body of work has focused on interoperability and context-aware physiological monitoring architectures. Arney et al. (2023) described an open-source, interoperable architecture for generating real-time surgical team cognitive alerts from HRV monitoring. That work is particularly relevant because it demonstrates that HRV can be embedded in a modular, multi-user, context-aware software architecture. At the same time, the authors explicitly distinguish architecture verification from algorithmic or clinical validation, noting that their prototype was intended to verify the data pipeline and interoperability pattern rather than to establish final validity of the cognitive-load inference itself. This distinction is important for the present manuscript because it provides a precedent for responsibly reporting integrated physiological software systems whose strongest immediate evidence lies in architecture and engineering verification.

Third, fatigue and circadian decision tools have developed largely along a separate trajectory. The Fatigue Avoidance Scheduling Tool (FAST), built on the SAFTE model, was developed to compare schedules in terms of predicted effectiveness and to support mission or duty planning in fatigue-sensitive operations (Hursh et al., 2004). Related aviation and sleep research continues to demonstrate the importance of combining schedule exposure, fatigue perceptions, mitigation strategies, and circadian considerations when assessing operational risk (Morris et al., 2020; Devine & Hursh, 2025). In parallel, wearable-based circadian physiology methods have shown that daily physiological rhythms can be inferred from widely used consumer devices, opening a path toward personalized circadian analytics outside the laboratory (Bowman et al., 2021). These contributions are highly relevant, but they typically prioritize either fatigue forecasting or circadian inference rather than integrating them with standards-informed HRV analysis, longitudinal user profiles, and operational decision logic in one open platform.

Fourth, multimodal wearable monitoring and health-platform research has expanded rapidly. Multi-wearable approaches for tracking diurnal light exposure and body rhythms in night-shift workers suggest that distributed sensing can support ecological circadian and health monitoring in high-risk populations (Hartmeyer et al., 2025). AI-edge and multimodal physiological monitoring platforms show how multiple streams can be fused at the sensing or device layer (Yang et al., 2020). These systems are valuable examples of sensor integration, but they generally do not provide a full translational pathway from standardized HRV analysis through fatigue and environmental interpretation to auditable operational outputs tailored to aerospace medicine.

Taken together, the literature shows strong progress in HRV analytics, open physiological processing, real-time contextual monitoring, fatigue forecasting, circadian inference, and wearable integration. What remains less well represented is an open, reproducible system that unifies these components specifically for aerospace and operational medicine workflows while making the underlying biomathematical layers explicit enough to inspect, deploy, and audit. Table 2 summarizes this landscape and motivates the present manuscript’s focus on a Node-first delivery stack over a transparent modeling substrate rather than on a single isolated algorithmic advance.

### 1.3 Gap statement

Current tools do not adequately combine standards-informed HRV analytics, individualized physiological context, reservoir-based fatigue and circadian modeling, environmental timing layers, and operational scheduling logic within one open, reproducible aerospace medicine system. Existing systems are often excellent within their own scope, but they tend to specialize in one of four roles: HRV analysis software, physiological data-processing infrastructure, fatigue or circadian forecasting, or multimodal sensing. As a result, researchers and operational users who need a biomathematically coherent workflow must often bridge multiple tools manually, with inconsistent provenance, limited audit trails, and uncertain transferability from exploratory analysis to operational action.

### 1.4 Objective and contribution

The objective of this work is to describe the design, implementation, and bounded verification of **Mission Control - Flight Surgeon**, an open-source translational biomathematical software system for aerospace medicine research and operational physiology. Rather than proposing a new standalone biomarker, the platform is designed to integrate standards-informed HRV analytics, explicit fatigue and circadian dynamics, deterministic readiness fusion, and environmental timing layers into one reproducible system that can support both exploratory research and mission-oriented workflows.

This work makes four main contributions. First, it documents a Node-first software architecture in which a Next.js frontend and FastAPI orchestration layer expose a shared Python modeling backend for aerospace medicine workflows. Second, it details a layered modeling stack that links HRV analytics, longitudinal user context, reservoir-based fatigue and circadian dynamics, environmental and space-weather alignment, and deterministic readiness fusion. Third, it describes a decision-support layer that translates physiological and schedule information into readiness-oriented outputs, including crew-level scheduling and GO/NO-GO logic. Fourth, it provides a reproducibility-oriented reporting structure that explicitly separates implemented capabilities, engineering verification, exploratory analyses, and evidence gaps that still require formal external validation.

## 2. Methods

### 2.1 Requirements and design rationale

The platform was designed as a translational system rather than as a single-purpose analysis package. The main functional requirement was to support workflows that begin with physiological measurement but end with either interpretable research outputs or operationally relevant summaries. This required a software design that could handle RR-interval and wearable-derived inputs, compute standard HRV domains, preserve longitudinal user context, incorporate circadian and fatigue state information, and expose the resulting outputs in a form useful to both investigators and operational users.

Several non-functional requirements shaped the architecture. First, the platform needed to support transparent and reproducible computation. This requirement favored deterministic implementations, explicit parameterization, exportable outputs, and a preference for bounded rather than opaque decision logic. Second, the platform needed to support operational auditability. In practice, this meant keeping track of user context, schedule assumptions, and derived outputs in a way that could be revisited or exported, rather than relying on transient interface state alone. Third, the system had to support translational flexibility across a mission-oriented client and deeper research views without fragmenting the underlying model stack. Fourth, the biomathematical layers themselves needed to remain inspectable enough that HRV, fatigue, circadian, and environmental computations could be described as model components rather than hidden backend behavior.

The design rationale was therefore to separate **client delivery** from **model execution** without duplicating the computational core. In the scope of the present manuscript, the primary frontend is the Next.js application in the Node.js ecosystem, while FastAPI provides route-level access to the shared Python model stack. This architecture supports operational and research route families through one API-backed web client, while retaining Streamlit entrypoints in the repository as secondary interfaces for legacy workflows and rapid iteration. The resulting design is not simply a frontend refresh; it is a model-serving architecture in which delivery surfaces are downstream of an explicit physiological and biomathematical backend.

Domain-specific design choices were also influenced by aerospace and fatigue-management reference frameworks. Modules related to readiness, scheduling, and safety framing were designed with reference to published fatigue-modeling and operational guidance, including FAST/SAFTE literature, NASA human-systems standards, and aviation fatigue-management concepts such as those summarized in ICAO Doc 9966 (Hursh et al., 2004; International Civil Aviation Organization [ICAO], 2020; National Aeronautics and Space Administration [NASA], 2023). These references inform threshold selection and workflow logic, but the platform is not presented here as a certified or regulated medical device.

### 2.2 System architecture

In the scope of this manuscript, the primary client is the Next.js application under `frontend/`, which runs in the Node.js ecosystem and organizes separate operational and research route families over one backend. Operational navigation supports mission control workflows such as scheduling, experiments, and user profiles, whereas research navigation exposes HRV, fatigue, readiness, circadian, and correlation views through a broader route tree. This frontend emphasis is important to the present paper because it reflects a modular, API-backed deployment path rather than a monolithic analytic dashboard.

The corresponding orchestration layer is implemented in `api/main.py` and `api/research_endpoints.py`. FastAPI exposes structured endpoints for health checks, mission context, user profiles, scheduling, HRV analysis, space-weather data, readiness views, and multiple research-specific analytical paths. In architectural terms, this API layer is the contract between the Node.js/Next.js client and the shared Python model stack. It is therefore more accurate for the present manuscript to describe the system as a Node-first client over a Python backend than as a frontend-neutral bundle of interfaces.

The shared Python analysis core remains located primarily under `app/`. This core contains the HRV computation engine, environmental data ingestion modules, fatigue and circadian logic, user-profile management, scheduling and decision-support modules, and export utilities. Secondary Streamlit entrypoints remain in the repository and still expose valuable workflows, but in the present manuscript they are treated as auxiliary surfaces over the same analytic substrate rather than as the primary frontend scope.

User persistence is handled through the platform’s profile and database layers, including `app/user_profile_tab.py` and `app/user_database.py`. These modules provide longitudinal storage of user characteristics, assessment history, and context variables that are subsequently propagated into fatigue, readiness, and interpretation workflows. The effect is that HRV or environmental outputs are not computed as context-free numbers; they are interpreted relative to person-level and mission-level information when such context is available.

The core data flow is modular. RR intervals are ingested and cleaned before HRV metrics are computed across time-domain, frequency-domain, nonlinear, and windowed representations. Environmental context is fetched through dedicated ingestion layers such as `app/noaa_space.py`, which harmonizes and caches NOAA-derived space-weather data. Additional domain layers then consume both physiological and contextual information. Fatigue and circadian modules transform sleep- and schedule-related inputs into readiness-relevant states; scheduling modules integrate these states into crew-level decision logic; and export modules assemble structured summaries suitable for reporting or audit. This composition-oriented architecture allows the platform to support both isolated analyses and cross-layer workflows.

The major architecture layers retained in the main text are summarized in Table 1. Submission figures should pair this description with a high-level architecture diagram (Figure 1), an end-to-end workflow view (Figure 2), and a research-to-operations coupling diagram (Figure 3).

### 2.3 Implementation

The implementation is best understood as a layered modeling stack rather than as a flat collection of application features. Table 6 summarizes the main model layers, their inputs and outputs, and the current evidence tier attached to each one.

#### 2.3.1 HRV analytic model layer

The physiological engine is centered in `app/hrv_core.py`. RR-interval series are first screened with bounded artifact heuristics, including moving-median and previous-beat deviation rules, before invalid samples are linearly interpolated for downstream computation. The engine then computes time-domain measures such as RMSSD, lnRMSSD, SDNN, and pNNx families; frequency-domain measures derived from interpolated tachograms and spectral integration; and nonlinear summaries including Poincare, detrended fluctuation, and windowed representations. This layer is important because it defines the physiological state variables consumed by the rest of the system. It is standards-informed and explicit in code, but still lacks the manuscript-ready external benchmark package that would be needed for stronger numerical equivalence claims.

#### 2.3.2 Fatigue and circadian biomathematical layer

The strongest explicit dynamical model in the repository is the reservoir-based SAFTE-style fatigue implementation in `app/fatigue_calculator/safte_model.py`. In simplified form, the model combines a homeostatic reservoir, circadian drive, and sleep inertia to generate percent effectiveness over time. The circadian term uses a 24-hour plus 12-hour harmonic structure, while the sleep and wake updates govern reservoir depletion and recovery. The repository also supports optional phase-shift and re-entrainment behavior relevant to jet-lag and schedule transitions. This model layer is mirrored for responsive operational displays in `frontend/src/lib/safte-model.ts`, which reproduces the same parameter defaults and core equations inside the Node.js/Next.js client. In the manuscript, the Python implementation is treated as the canonical model reference, while the TypeScript implementation is treated as an architectural mirror rather than as a separately validated biomathematical contribution (Hursh et al., 2004; Devine et al., 2022; Forger et al., 1999).

#### 2.3.3 Readiness fusion and decision layer

Operational decision support is implemented primarily through `app/scheduling_core.py`, `app/scheduling_engine.py`, and related scheduling views. These modules are not a second dynamical model in the same sense as SAFTE; instead, they form a deterministic fusion layer that converts physiological and schedule state variables into operationally interpretable outputs. The fusion logic combines SAFTE-derived effectiveness bands, lnRMSSD-related readiness signals, Karolinska Sleepiness Scale (KSS) and psychomotor vigilance task (PVT) pathways, hydration and energy modifiers, mission-specific constraints, and bounded threshold logic for crew-level interpretation. This layer is central to the paper because it is the point at which biomathematical state estimates become auditable readiness and GO/NO-GO framing.

#### 2.3.4 Environmental timing and alignment layer

Environmental and space-weather context is implemented through modules such as `app/noaa_space.py`, `app/space_weather_impact.py`, `app/space_weather_alignment.py`, and `app/space_weather_influence.py`. The NOAA ingestion layer normalizes selected feeds and caches them locally with bounded time-to-live behavior, while downstream alignment modules synchronize environmental data with physiological observation windows. The repository also contains deterministic propagation logic for solar-event timing, including drag-based treatment of CME transit and L1-to-Earth timing assumptions. In the present manuscript, these modules are treated as contextual timing and alignment models that make environmental overlays analytically usable. They are not presented as validated causal models of autonomic physiology.

#### 2.3.5 Delivery and orchestration layer

The frontend and orchestration stack are also part of the implementation story because they determine how these models are surfaced and composed. The Next.js application under `frontend/` organizes operational and research routes over one client in the Node.js ecosystem, while `api/main.py` and `api/research_endpoints.py` expose the shared Python models as structured endpoints. This API-backed design allows modeling layers to be reused across operational pages, research tools, and web-delivered workflows. Streamlit remains in the repository as a secondary interface, but the present manuscript centers the Node.js/Next.js client and FastAPI orchestration path as the primary frontend scope.

Reproducibility and reporting are supported by export layers including `app/publication_export.py` and `app/export_utils.py`. These modules were designed to produce structured statistical summaries, confidence intervals, effect-size reporting, and other manuscript-oriented artifacts. Their presence is relevant to the current paper because they show that model outputs were designed for traceable downstream reporting rather than as ephemeral user-interface values.

### 2.4 Validation and evaluation methodology

The validation posture adopted in this manuscript is tiered. The strongest evidence currently available in the repository is **engineering verification** rather than full prospective validation of the integrated platform. Accordingly, the Methods and Results sections distinguish between implemented model layers, software verification, exploratory quantitative artifacts, and validation work that remains future-facing.

Engineering verification is represented by the repository’s automated test surface. The strongest test-backed domains cluster around readiness and scheduling logic (`tests/test_scheduling_core.py`), fatigue and FRMS behavior (`tests/test_frms.py`, `tests/test_frms_v2.py`, `tests/test_fatigue_integration.py`), space-weather ingestion and alignment (`tests/test_noaa_cache.py`, `tests/test_space_weather_impact.py`, `tests/test_space_weather_alignment.py`), broader statistical and scientific charting modules (`tests/test_comprehensive_modules.py`), and selected API or endpoint behaviors such as profile normalization and windowed research endpoints (`tests/test_api_user_profile_normalization.py`, `tests/test_research_windowed_endpoint.py`). These tests justify reporting the fusion, orchestration, and environmental layers as implemented and partly verified at the software level.

Exploratory quantitative artifacts are also present in the repository, including exported lag-aware HRV to space-weather correlation tables under `analysis/`. However, these outputs are not treated here as publication-ready scientific findings unless their analytical provenance can be fully documented, including cohort definition, unit of analysis, preprocessing, alignment rules, and inferential scope. In the present manuscript strategy, such artifacts are therefore considered optional demonstrations of analytic capability rather than default headline results.

Importantly, this manuscript does not treat engineering verification as a substitute for external numerical benchmarking or human-subject validation. In particular, although the HRV engine and the canonical SAFTE implementation are explicit and inspectable, the repository does not yet provide a manuscript-ready benchmark package against trusted reference outputs across the full integrated platform. The client-side TypeScript SAFTE mirror is useful implementation evidence for frontend-backend model consistency, but it is not treated as an independent validation layer. Likewise, if future versions of the manuscript include retrospective or prospective participant data, those analyses will require dedicated protocol description, ethics reporting, and design-specific reporting guidance. The current evaluation methodology is therefore intentionally conservative: it reports what the repository can substantiate today while reserving stronger claims for future validation studies.

## 3. Results

### 3.1 System implementation summary

Mission Control - Flight Surgeon is implemented as a Node-first biomathematical system rather than as a single analytic script or a Streamlit-centered dashboard. The repository couples a Next.js client in the Node.js ecosystem to a FastAPI service layer and a shared Python model stack. Within this architecture, HRV analysis, longitudinal user context, reservoir-based fatigue and circadian dynamics, environmental ingestion and timing, scheduling logic, and reporting utilities are organized as interoperable layers rather than disconnected features. This makes it possible to expose the same physiological and operational logic across mission-facing and research-facing routes without duplicating the computational substrate.

The implemented system also supports persistent user context and mission-oriented interpretation. User-profile and database layers allow physiological outputs to be interpreted alongside person-level and mission-level information when available, while downstream decision-support modules translate schedule, fatigue, hydration, and environmental state into readiness-oriented summaries. In practical terms, the platform can therefore be described as an API-backed aerospace physiology workbench whose primary frontend is a web client rather than a monolithic interactive notebook-style surface.

For submission assembly, Table 1 should accompany this section as the compact module-family summary, Table 6 should anchor the biomathematical layer summary, and Figures 1 and 2 should provide the corresponding architecture and workflow visuals.

### 3.2 Engineering verification

Automated verification currently provides the strongest empirical support for the platform, but that evidence is asymmetric across model layers. Representative tests cover deterministic scheduling and readiness behavior, FRMS and fatigue logic, NOAA ingest and cache handling, space-weather impact and alignment pathways, API normalization, and endpoint-level windowed analysis behavior. Taken together, these test-backed domains support the claim that the readiness fusion, orchestration, and contextual model layers are implemented and regression-tested at the software level.

This evidence should be interpreted as engineering verification rather than clinical or operational validation. The available tests demonstrate bounded rule behavior, stable data transformations, and interface-to-core coupling for key modules, but they do not by themselves establish diagnostic accuracy, real-world deployment effectiveness, or numerical equivalence to external reference HRV packages across the whole platform. In particular, the readiness fusion and environmental layers are better verified than the full numerical behavior of the HRV engine, and frontend/backend model mirroring is more directly evidenced than independent physiological validation.

Representative test-backed domains are organized in Table 3, and the corresponding submission figure should be a verification coverage map (Figure 4) that visually separates implemented-and-tested modules from areas that still require external validation.

### 3.3 Reproducibility and reporting assets

Mission Control - Flight Surgeon is distributed as open-source software at `https://github.com/strikerdlm/HRV.git` under the MIT license. The documented primary execution environment is conda `hrv-py312` with Python 3.12 and dependencies declared in `requirements.txt`, while the primary web client is a Next.js/TypeScript application with its own dependency surface under `frontend/package.json`. Reproducibility is further supported by automated tests, structured logging, cached data management, and export layers designed to emit manuscript-oriented statistics, tables, and supporting artifacts.

These features matter because they make the platform auditable beyond the interface layer. Logging, persistence, and export support allow investigators to revisit analysis settings and outputs, while the shared code base permits the same analytic logic to be exercised from research and operational interfaces. These characteristics are also consistent with common recommendations for reproducible computational research, such as preserving transparent workflows and inspectable outputs (Sandve et al., 2013). Before formal submission, the manuscript should cite a tagged software release or archived DOI rather than a moving development snapshot.

The current reproducibility and deployment metadata are summarized in Table 4.

### 3.4 Optional curated analysis vignette

The repository also contains exported lag-aware HRV-to-space-weather correlation outputs and related analytic artifacts that demonstrate the platform’s ability to generate advanced cross-domain analyses. However, these materials are not elevated to primary manuscript findings in the present draft because the cohort definition, preprocessing pipeline, unit of analysis, and inferential scope are not yet curated in a manuscript-ready form. They are therefore best interpreted as demonstrations of implemented analytical capability and may be moved to supplementary material or a future validation paper once provenance is fully documented.

## 4. Discussion

### 4.1 Principal findings

The principal finding of this manuscript is not the validation of a single new biomarker, but the successful implementation of a Node-first software system built around a layered biomathematical backend. Mission Control - Flight Surgeon combines standards-informed HRV computation, longitudinal user context, SAFTE-style fatigue and circadian dynamics, environmental timing layers, deterministic readiness fusion, and reproducibility-oriented export paths within an API-backed architecture that can be delivered through operational and research web routes.

A second principal finding is that the current repository provides meaningful engineering evidence across several model-adjacent modules that are highly relevant to aerospace medicine workflows. This evidence supports reporting the system as implemented and partly verified at the software level, while also reinforcing the need to keep stronger claims about operational performance, clinical benefit, or numerical benchmarking outside the scope of the present paper.

### 4.2 Interpretation in context of the literature

Viewed against dedicated HRV packages such as Kubios, the present system contributes breadth of context and workflow integration rather than a claim of superior standalone signal-analysis performance (Tarvainen et al., 2014). Relative to open physiological processing frameworks such as PhysioScripts, it extends beyond data handling toward an explicit model-serving architecture for readiness- and decision-oriented layers targeted to aerospace and operational medicine (Christie & Gianaros, 2013). Relative to context-aware HRV architectures such as Arney et al. (2023), the present system similarly treats interoperability and modular integration as central design goals, but expands the domain scope to include crew context, fatigue modeling, environmental overlays, and export-ready reporting.

The manuscript also occupies a different niche than FAST/SAFTE-style scheduling tools and wearable circadian monitoring approaches. FAST demonstrates the value of schedule-based fatigue prediction for operational planning, and later biomathematical fatigue comparisons reinforce the importance of explicit model structure and objective sleep context (Hursh et al., 2004; Devine et al., 2022). Circadian modeling work, from simplified pacemaker formulations through wearable-derived daily physiology, shows that phase and timing can be formalized rather than merely described (Forger et al., 1999; Bowman et al., 2021). Mission Control - Flight Surgeon brings these strands together with standards-informed HRV interpretation and aerospace-specific environmental framing. Its contribution is therefore not just integrative but also architectural: it places multiple biomathematical layers behind one API-backed operational client.

### 4.3 Strengths and limitations

The manuscript has several strengths. The system is open source, modular, and broad enough to reflect real operational physiology workflows rather than isolated laboratory analysis. It includes a genuine biomathematical core rather than only interface-level integration: explicit HRV preprocessing and mult-domain feature extraction, a reservoir-based fatigue and circadian model, deterministic readiness fusion, and environmental timing layers. Its decision-support logic favors inspectable rules over opaque black-box inference, and its test surface covers representative scheduling, fatigue, environmental, and API pathways. The system also treats export and audit support as part of the architecture, which is important for translational research, governance, and future reproducibility.

The limitations are equally important. First, the integrated platform has not yet been externally benchmarked end-to-end against trusted reference HRV software or published test vectors, so the paper should not claim validated numerical parity across all analytic outputs. Second, the evidence depth is uneven across model layers: scheduling, FRMS, and environmental pathways are better verified in the repository than the full numerical behavior of the HRV engine. Third, the Next.js client and FastAPI backend expose some model layers more directly than others, and simplified API-facing or client-facing implementations should not be mistaken for full independent validation of the canonical Python models. Fourth, the software scope remains broad for a single manuscript, which increases translational relevance but risks diffuseness relative to a narrower software or biomathematics paper. Fifth, the platform is not accompanied by certification, clearance, or formal regulatory evidence. Finally, the documented primary conda environment uses Python 3.12 whereas the current Docker path is not fully harmonized with that environment, so reproducibility claims should remain tied to the documented primary execution route until that inconsistency is resolved.

### 4.4 Implications for operational and clinical translation

For operational and clinical translation, the platform’s main value lies in its ability to place physiological measurements inside a richer mission context through an API-backed client that exposes an explicit model stack rather than disconnected calculators. In mission medicine or crew-readiness settings, isolated HRV values are rarely sufficient. What is often needed is a structured view that links HRV to sleep opportunity, circadian alignment, fatigue state, workload, environmental exposure, and person-specific history, then presents those relationships in an auditable way. The current architecture is well suited to that role because the same modeling backend can support web-delivered operational views, research pages, and secondary interfaces without duplicating core logic.

At the same time, translation requires governance. Before such a platform is used for consequential operational or clinical decisions, organizations would need local validation, configuration control, operator training, documented escalation rules, and human oversight over any readiness or GO/NO-GO interpretations. The present results support a deployment pathway toward those uses, but they do not establish that the current version should be used autonomously or without institution-specific validation.

### 4.5 Future work

The most immediate next step is external numerical benchmarking of the HRV engine against trusted reference software or published test vectors. A second priority is a curated dataset with explicit cohort definition, preprocessing rules, missing-data handling, and inferential scope so that exploratory correlation or readiness outputs can be promoted to manuscript-grade empirical results. A third priority is prospective or retrospective validation in clearly described aerospace, aviation, or analog populations with study-specific ethics and reporting guidance. A fourth priority is more formal model-layer harmonization and sensitivity analysis so that the canonical Python implementations, API-facing services, and client-side mirrors can be compared explicitly rather than inferred from code structure.

Beyond validation, future work should include a harmonized release package for the exact reported software version, ideally with a tagged release or archived DOI, plus a more formal artifact manifest for figures, tables, and exports. Usability studies, governance workflows, and role-specific deployment playbooks for flight surgeons and operational teams would also strengthen the research-to-operations transfer pathway. If the project matures toward a narrower methods paper, the biomathematical layers could later be separated into dedicated validation studies for HRV numerics, fatigue/circadian dynamics, or environment-linked operational modeling.

## 5. Conclusions

Mission Control - Flight Surgeon is best understood as an open, layered biomathematical software platform rather than as a single HRV calculator or a fully validated clinical decision engine. The repository already substantiates a publishable systems contribution through explicit architecture, inspectable model layers, deterministic readiness logic, and meaningful engineering verification across several operational paths. That combination is sufficient for a defensible software-and-methods paper if the claims remain bounded to implementation, verification, and reproducibility.

At the same time, the manuscript should remain explicit about what is not yet established. The current package does not justify claims of end-to-end numerical equivalence to external HRV reference software, operational outcome benefit, or clinical deployment readiness. For a strong Q1 submission, the paper should therefore foreground its integration and auditability contribution, cite a frozen release artifact, and treat stronger empirical validation as the next step rather than as an implied accomplishment.

## 6. Compliance and Transparency

The key manuscript declarations that are already supportable from repository evidence are summarized in Table 5. Narrative statements for each required subsection are provided below and should be finalized once authorship, funding, and conflict disclosures are confirmed.

### 6.1 Data availability statement

No new human-subject dataset was generated for the software-verification components reported in this manuscript. Code, manuscript support files, and repository artifacts are available through the public source repository. Additional derived analysis artifacts can be shared by the authors on reasonable request, subject to provenance review and any applicable institutional constraints.

### 6.2 Code and artifact availability

Mission Control - Flight Surgeon is available as open-source software at `https://github.com/strikerdlm/HRV.git` under the MIT license. The documented primary execution environment is conda `hrv-py312` with Python 3.12 and dependencies declared in `requirements.txt`, while the primary web client is implemented in Next.js/TypeScript under `frontend/`. Before submission, the authors should archive or tag the exact release corresponding to the final manuscript and cite that frozen identifier in the paper.

### 6.3 Ethics and regulatory alignment

Ethics approval and informed consent were not required for the software-development and repository-verification components reported in this manuscript because no new human-subject dataset was generated or analyzed as part of the primary reported results. If future versions of the manuscript include retrospective or prospective participant data, a study-specific ethics protocol, institutional approval details, and consent language should be added.

The platform is not presented as a certified medical device. Several operational modules were designed with reference to published aerospace, fatigue-management, and safety frameworks, including NASA-STD-3001, ICAO fatigue-management guidance, MIL-STD-882E-aligned risk framing, and crew-rest guidance used in FRMS-related modules (ICAO, 2020; NASA, 2023). These references inform design and threshold logic but should not be interpreted as evidence of certification, legal compliance, or regulatory clearance.

### 6.4 Author contributions

Dr Diego Malpica MD contributed conceptualization, methodology, software, validation, formal analysis, investigation, writing - original draft, writing - review and editing, visualization, supervision, and project administration. This CRediT statement should be revised if additional authors are added to the final manuscript.

### 6.5 Funding and conflict of interest

At the time of drafting, no project-level external funding statement was identified in the repository materials. This statement should be updated before submission if grant support, institutional sponsorship, or other funding applies. Conflict-of-interest declarations were not explicitly documented in the repository and should be confirmed for all authors before final submission.

### 6.6 Acknowledgments

The draft acknowledges the open-source scientific Python ecosystem and the public technical and data resources that inform the platform’s environmental modules and standards framing, including NOAA, NASA, and aviation fatigue-management reference materials. Final acknowledgments for collaborators, institutions, and infrastructure support should be confirmed before submission.

### 6.7 Reporting guideline positioning

This manuscript is being developed as a software, systems, and biomathematical modeling paper with a primary emphasis on transparent description of architecture, implementation, verification, and reproducibility. If the final paper remains limited to software verification and repository-backed artifacts, journal-specific software or methods-paper guidance should form the main reporting backbone. If observational analyses are added, adapted STROBE elements should be incorporated. TRIPOD+AI, CLAIM, or related AI reporting extensions should be used only for sections that make genuine predictive-model claims.

## References

The current in-text citations used in this draft are listed below. Additional candidate sources remain tracked in `manuscript/references/seed_references.md`.

Alabdulgader, A., McCraty, R., Atkinson, M., Dobyns, Y., Vainoras, A., Ragulskis, M., & Stolc, V. (2018). Long-term study of heart rate variability responses to changes in the solar and geomagnetic environment. *Scientific Reports, 8*(1), 2663. <https://doi.org/10.1038/s41598-018-20932-x>

Arney, D., Zhang, Y., Kennedy-Metz, L. R., Dias, R. D., Goldman, J. M., & Zenati, M. A. (2023). An open-source, interoperable architecture for generating real-time surgical team cognitive alerts from heart-rate variability monitoring. *Sensors, 23*(8), 3890. <https://doi.org/10.3390/s23083890>

Bowman, C., Huang, Y., Walch, O. J., Fang, Y., Frank, E., Tyler, J., Mayer, C., Stockbridge, C., Goldstein, C., Sen, S., & Forger, D. B. (2021). A method for characterizing daily physiology from widely used wearables. *Cell Reports Methods, 1*(4), 100058. <https://doi.org/10.1016/j.crmeth.2021.100058>

Christie, I. C., & Gianaros, P. J. (2013). PhysioScripts: An extensible, open source platform for the processing of physiological data. *Behavior Research Methods, 45*(1), 125-131. <https://doi.org/10.3758/s13428-012-0233-x>

Devine, J. K., & Hursh, S. R. (2025). A narrative review on in-flight use of consumer sleep technologies for aviation research. *Sleep Advances*. <https://doi.org/10.1093/sleepadvances/zpaf076>

Devine, J. K., Garcia, C. R., Simoes, A. S., Guelere, M. R., de Godoy, B., Silva, D. S., Pacheco, P. C., Choynowski, J., & Hursh, S. R. (2022). Predictive biomathematical modeling compared to objective sleep during COVID-19 humanitarian flights. *Aerospace Medicine and Human Performance, 93*(1), 4-12. <https://doi.org/10.3357/AMHP.5909.2022>

Forger, D. B., Jewett, M. E., & Kronauer, R. E. (1999). A simpler model of the human circadian pacemaker. *Journal of Biological Rhythms, 14*(6), 533-538. <https://doi.org/10.1177/074873099129000867>

Gaisenok, O., Gaisenok, D., & Bogachev, S. (2025). The influence of geomagnetic storms on the risks of developing myocardial infarction, acute coronary syndrome, and stroke: Systematic review and meta-analysis. *Journal of Natural Science, Biology and Medicine*. <https://doi.org/10.4103/jmp.jmp_122_24>

Hartmeyer, S. L., Phillips, N. E., Jassil, F. C., Joris, C., Dibner, C., Collet, T. H., & Andersen, M. (2025). Multi-wearable approach for monitoring diurnal light exposure and body rhythms in nightshift workers. *Acta Physiologica*. <https://doi.org/10.1111/apha.70069>

International Civil Aviation Organization. (2020). *Manual for the oversight of fatigue management approaches (Doc 9966, 2nd ed., Version 2, revised).* <https://www.icao.int/publications/doc-9966-includes-complete-set-fatigue-management-implementation-manuals>

Hursh, S. R., Balkin, T. J., Miller, J. C., & Eddy, D. R. (2004). The Fatigue Avoidance Scheduling Tool: Modeling to minimize the effects of fatigue on cognitive performance. *SAE Technical Paper Series*. <https://doi.org/10.4271/2004-01-2151>

Morris, M. B., Howland, J. P., Amaddio, K. M., & Gunzelmann, G. (2020). Aircrew fatigue perceptions, fatigue mitigation strategies, and circadian typology. *Aerospace Medicine and Human Performance, 91*(4), 363-368. <https://doi.org/10.3357/AMHP.5396.2020>

National Aeronautics and Space Administration. (2023). *NASA Spaceflight Human-System Standard Volume 1, Crew Health (NASA-STD-3001, Vol. 1, Rev. C).* <https://standards.nasa.gov/standard/NASA/NASA-STD-3001_VOL_1>

Quigley, K. S., Gianaros, P. J., Norman, G. J., Jennings, J. R., Berntson, G. G., & de Geus, E. J. C. (2024). Publication guidelines for human heart rate and heart rate variability studies in psychophysiology-Part 1: Physiological underpinnings and foundations of measurement. *Psychophysiology, 61*(9), e14604. <https://doi.org/10.1111/psyp.14604>

Rogers, B., Murias, J. M., & Fleitas-Paniagua, P. R. (2025). Validity of an open-source mobile app to measure fractal correlation properties of heart rate variability during exercise. *European Journal of Applied Physiology*. <https://doi.org/10.1007/s00421-025-06037-0>

Sandve, G. K., Nekrutenko, A., Taylor, J., & Hovig, E. (2013). Ten Simple Rules for Reproducible Computational Research. *PLoS Computational Biology, 9*(10), e1003285. <https://doi.org/10.1371/journal.pcbi.1003285>

Shaffer, F., & Ginsberg, J. P. (2017). An overview of heart rate variability metrics and norms. *Frontiers in Public Health, 5*, 258. <https://doi.org/10.3389/fpubh.2017.00258>

Tarvainen, M. P., Niskanen, J.-P., Lipponen, J. A., Ranta-aho, P. O., & Karjalainen, P. A. (2014). Kubios HRV - Heart rate variability analysis software. *Computer Methods and Programs in Biomedicine, 113*(1), 210-220. <https://doi.org/10.1016/j.cmpb.2013.07.024>

Task Force of the European Society of Cardiology and the North American Society of Pacing and Electrophysiology. (1996). Heart rate variability: Standards of measurement, physiological interpretation and clinical use. *Circulation, 93*(5), 1043-1065. <https://doi.org/10.1161/01.cir.93.5.1043>

Yang, C.-J., Fahier, N., He, C.-Y., Li, W.-C., & Fang, W.-C. (2020). An AI-edge platform with multimodal wearable physiological signals monitoring sensors for affective computing applications. In *2020 IEEE International Symposium on Circuits and Systems* (pp. 1-5). IEEE. <https://doi.org/10.1109/ISCAS45731.2020.9180909>

## Supplementary materials

The current supplementary package includes `manuscript/supplement/submission_support_appendix.md`, which consolidates the extended engineering verification inventory, standards crosswalk, reporting-guideline positioning, non-claims, and deployment prerequisites. The broader supplementary roadmap remains tracked in `manuscript/supplement/supplement_outline.md`.

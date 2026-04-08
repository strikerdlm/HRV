# Author: Dr Diego Malpica MD

## Title

Mission Control - Flight Surgeon: an open-source aerospace medicine platform for HRV analytics, fatigue modeling, space-weather context, and operational decision support

**Running title:** Aerospace Physiology Ops Platform

## Structured Abstract

### Background and objective

Mission Control - Flight Surgeon is an open-source software platform developed to unify heart rate variability (HRV) analytics with longitudinal physiology, circadian and fatigue context, environmental overlays, and operational decision support for aerospace medicine. The objective of this manuscript is to describe the system architecture, implementation, and current verification posture of the platform while explicitly separating engineering evidence from pending external validation.

### Methods

The platform was documented as a dual-interface software system built on a shared Python analysis core exposed through research and operational Streamlit applications, a FastAPI backend, and a Next.js frontend. Methods focused on the HRV engine, longitudinal user-profile persistence, fatigue and circadian modules, space-weather context, scheduling logic, and export utilities. Evaluation was intentionally bounded to repository-supported evidence, emphasizing architecture inspection, automated software verification, and reproducibility assets rather than human-subject validation.

### Results

The implemented platform integrates HRV computation, longitudinal user persistence, fatigue and circadian modeling, space-weather ingestion, operational scheduling logic, and publication-oriented export workflows within one open repository. Automated tests verify representative operational domains including scheduling and FRMS behavior, space-weather caching and alignment, API normalization, and endpoint-level windowed analytics. Public code availability, deterministic rule-based components, structured logging, and export utilities support reproducible research and auditable deployment-oriented workflows, although integrated external benchmarking and participant validation remain incomplete.

### Conclusions

Mission Control - Flight Surgeon extends beyond single-purpose HRV software by coupling physiological analytics with operational context and readiness-oriented workflows in an open-source architecture. Its current evidence base supports a systems and software contribution with engineering verification, while stronger claims regarding numerical benchmarking, clinical benefit, or operational effectiveness require dedicated future validation.

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

The major architecture layers retained in the main text are summarized in Table 1. Submission figures should pair this description with a high-level architecture diagram (Figure 1), an end-to-end workflow view (Figure 2), and a research-to-operations coupling diagram (Figure 3).

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

Mission Control - Flight Surgeon is implemented as a modular translational platform rather than as a single analytic script or isolated dashboard. The repository couples a shared Python analysis core with two Streamlit delivery surfaces, a FastAPI service layer, and a Next.js frontend. Within this architecture, HRV analysis, longitudinal user context, circadian and fatigue modeling, environmental ingestion, scheduling logic, and reporting utilities are organized as interoperable modules rather than disconnected features. This enables the same physiological and contextual logic to be exposed to exploratory research workflows and more focused operational workflows without duplicating the computational substrate.

The implemented system also supports persistent user context and mission-oriented interpretation. User-profile and database layers allow physiological outputs to be interpreted alongside person-level and mission-level information when available, while downstream decision-support modules translate schedule, fatigue, hydration, and environmental state into readiness-oriented summaries. In practical terms, the platform can therefore be described as an integrated aerospace physiology workbench with a shared analytic backend and multiple delivery pathways.

For submission assembly, Table 1 should accompany this section as the compact module-family summary, while Figures 1 and 2 should provide the corresponding architecture and workflow visuals.

### 3.2 Engineering verification

Automated verification currently provides the strongest empirical support for the platform. Representative tests cover deterministic scheduling and readiness behavior, FRMS and fatigue logic, NOAA ingest and cache handling, space-weather impact and alignment pathways, API normalization, and endpoint-level windowed analysis behavior. Taken together, these test-backed domains support the claim that major operational pathways are implemented and regression-tested at the software level.

This evidence should be interpreted as engineering verification rather than clinical or operational validation. The available tests demonstrate bounded rule behavior, stable data transformations, and interface-to-core coupling for key modules, but they do not by themselves establish diagnostic accuracy, real-world deployment effectiveness, or numerical equivalence to external reference HRV packages across the whole platform.

Representative test-backed domains are organized in Table 3, and the corresponding submission figure should be a verification coverage map (Figure 4) that visually separates implemented-and-tested modules from areas that still require external validation.

### 3.3 Reproducibility and reporting assets

Mission Control - Flight Surgeon is distributed as open-source software at `https://github.com/strikerdlm/HRV.git` under the MIT license. At the time of this draft, the working repository head corresponds to branch `main`, commit `a32959258ff01e459ac9d06609f58c3cd09fee47`. The documented primary execution environment is conda `hrv-py312` with Python 3.12 and dependencies declared in `requirements.txt`. Reproducibility is further supported by automated tests, structured logging, cached data management, and export layers designed to emit manuscript-oriented statistics, tables, and supporting artifacts.

These features matter because they make the platform auditable beyond the interface layer. Logging, persistence, and export support allow investigators to revisit analysis settings and outputs, while the shared code base permits the same analytic logic to be exercised from research and operational interfaces. Before formal submission, the project would benefit from a tagged software release or archived DOI corresponding exactly to the manuscript version.

The current reproducibility and deployment metadata are summarized in Table 4.

### 3.4 Optional curated analysis vignette

The repository also contains exported lag-aware HRV-to-space-weather correlation outputs and related analytic artifacts that demonstrate the platform’s ability to generate advanced cross-domain analyses. However, these materials are not elevated to primary manuscript findings in the present draft because the cohort definition, preprocessing pipeline, unit of analysis, and inferential scope are not yet curated in a manuscript-ready form. They are therefore best interpreted as demonstrations of implemented analytical capability and may be moved to supplementary material or a future validation paper once provenance is fully documented.

## 4. Discussion

### 4.1 Principal findings

The principal finding of this manuscript is not the validation of a single new biomarker, but the successful implementation of an integrated translational software platform that connects physiological analytics to operational context. Mission Control - Flight Surgeon combines HRV analysis, longitudinal user context, circadian and fatigue models, environmental overlays, scheduling logic, and reproducibility-oriented export paths within a shared architecture that can be delivered through research and operational interfaces.

A second principal finding is that the current repository provides meaningful engineering evidence across several modules that are highly relevant to aerospace medicine workflows. This evidence supports reporting the platform as implemented and partly verified at the software level, while also reinforcing the need to keep stronger claims about operational performance, clinical benefit, or numerical benchmarking outside the scope of the present paper.

### 4.2 Interpretation in context of the literature

Viewed against dedicated HRV packages such as Kubios, the present platform contributes breadth of context and workflow integration rather than a claim of superior standalone signal-analysis performance (Tarvainen et al., 2014). Relative to open physiological processing frameworks such as PhysioScripts, it extends beyond data handling toward readiness- and decision-oriented layers targeted to aerospace and operational medicine (Christie & Gianaros, 2013). Relative to context-aware HRV architectures such as Arney et al. (2023), the present system similarly treats interoperability and modular integration as central design goals, but expands the domain scope to include crew context, fatigue modeling, environmental overlays, and export-ready reporting.

The platform also occupies a different niche than FAST/SAFTE-style scheduling tools and wearable circadian monitoring approaches. FAST demonstrates the value of schedule-based fatigue prediction for operational planning (Hursh et al., 2004), while wearable physiology work shows that ecologically collected signals can inform circadian and readiness assessment outside the laboratory (Bowman et al., 2021; Hartmeyer et al., 2025). Mission Control - Flight Surgeon brings these strands together with standards-informed HRV interpretation and aerospace-specific environmental framing. Its contribution is therefore integrative and translational: it reduces the fragmentation that otherwise forces researchers and operators to move between separate analytic, scheduling, and contextual tools.

### 4.3 Strengths and limitations

The manuscript has several strengths. The platform is open source, modular, and broad enough to reflect real operational physiology workflows rather than isolated laboratory analysis. Its decision-support layers favor explicit, inspectable rules over opaque logic, and its test surface covers representative scheduling, fatigue, environmental, and interface pathways. The system also treats export and audit support as part of the architecture, which is important for translational research, governance, and future reproducibility.

The limitations are equally important. First, the integrated platform has not yet been externally benchmarked end-to-end against trusted reference HRV software or published test vectors, so the paper should not claim validated numerical parity across all analytic outputs. Second, the evidence depth is uneven across module families: scheduling, FRMS, and environmental pathways are better verified in the repository than some underlying HRV benchmark questions. Relatedly, some endpoint-level tests emphasize data plumbing more directly than full numerical equivalence, which is still valuable engineering evidence but not a substitute for analytic benchmarking. Third, the software scope is broad for a single manuscript, which increases translational relevance but risks diffuseness relative to a narrower software paper. Fourth, the platform is not accompanied by certification, clearance, or formal regulatory evidence. Finally, the documented primary conda environment uses Python 3.12 whereas the current Docker path is not fully harmonized with that environment, so reproducibility claims should remain tied to the documented primary execution route until that inconsistency is resolved.

### 4.4 Implications for operational and clinical translation

For operational and clinical translation, the platform’s main value lies in its ability to place physiological measurements inside a richer mission context. In mission medicine or crew-readiness settings, isolated HRV values are rarely sufficient. What is often needed is a structured view that links HRV to sleep opportunity, circadian alignment, workload, environmental exposure, and person-specific history, then presents those relationships in an auditable way. The current architecture is well suited to that role because the same analytic core can support exploratory research, crew-level planning, and more structured web delivery without duplicating logic across tools.

At the same time, translation requires governance. Before such a platform is used for consequential operational or clinical decisions, organizations would need local validation, configuration control, operator training, documented escalation rules, and human oversight over any readiness or GO/NO-GO interpretations. The present results support a deployment pathway toward those uses, but they do not establish that the current version should be used autonomously or without institution-specific validation.

### 4.5 Future work

The most immediate next step is external numerical benchmarking of the HRV engine against trusted reference software or published test vectors. A second priority is a curated dataset with explicit cohort definition, preprocessing rules, missing-data handling, and inferential scope so that exploratory correlation or readiness outputs can be promoted to manuscript-grade empirical results. A third priority is prospective or retrospective validation in clearly described aerospace, aviation, or analog populations with study-specific ethics and reporting guidance.

Beyond validation, future work should include a harmonized release package for the exact reported software version, ideally with a tagged release or archived DOI, plus a more formal artifact manifest for figures, tables, and exports. Usability studies, governance workflows, and role-specific deployment playbooks for flight surgeons and operational teams would also strengthen the research-to-operations transfer pathway.

## 5. Compliance and Transparency

The key manuscript declarations that are already supportable from repository evidence are summarized in Table 5. Narrative statements for each required subsection are provided below and should be finalized once authorship, funding, and conflict disclosures are confirmed.

### 5.1 Data availability statement

No new human-subject dataset was generated for the software-verification components reported in this manuscript. Code, manuscript support files, and repository artifacts are available through the public source repository. Additional derived analysis artifacts can be shared by the authors on reasonable request, subject to provenance review and any applicable institutional constraints.

### 5.2 Code and artifact availability

Mission Control - Flight Surgeon is available as open-source software at `https://github.com/strikerdlm/HRV.git` under the MIT license. The current draft references the `main` branch at commit `a32959258ff01e459ac9d06609f58c3cd09fee47`. The documented primary execution environment is conda `hrv-py312` with Python 3.12 and dependencies declared in `requirements.txt`. Before submission, the authors should archive or tag the exact release corresponding to the final manuscript.

### 5.3 Ethics and regulatory alignment

Ethics approval and informed consent were not required for the software-development and repository-verification components reported in this manuscript because no new human-subject dataset was generated or analyzed as part of the primary reported results. If future versions of the manuscript include retrospective or prospective participant data, a study-specific ethics protocol, institutional approval details, and consent language should be added.

The platform is not presented as a certified medical device. Several operational modules were designed with reference to published aerospace, fatigue-management, and safety frameworks, including NASA-STD-3001, ICAO fatigue-management guidance, MIL-STD-882E-aligned risk framing, and crew-rest guidance used in FRMS-related modules. These references inform design and threshold logic but should not be interpreted as evidence of certification, legal compliance, or regulatory clearance.

### 5.4 Author contributions

Dr Diego Malpica MD contributed conceptualization, methodology, software, validation, formal analysis, investigation, writing - original draft, writing - review and editing, visualization, supervision, and project administration. This CRediT statement should be revised if additional authors are added to the final manuscript.

### 5.5 Funding and conflict of interest

At the time of drafting, no project-level external funding statement was identified in the repository materials. This statement should be updated before submission if grant support, institutional sponsorship, or other funding applies. Conflict-of-interest declarations were not explicitly documented in the repository and should be confirmed for all authors before final submission.

### 5.6 Acknowledgments

The draft acknowledges the open-source scientific Python ecosystem and the public technical and data resources that inform the platform’s environmental modules and standards framing, including NOAA, NASA, and aviation fatigue-management reference materials. Final acknowledgments for collaborators, institutions, and infrastructure support should be confirmed before submission.

### 5.7 Reporting guideline positioning

This manuscript is being developed as a software and systems paper with a primary emphasis on transparent description of architecture, implementation, verification, and reproducibility. If the final paper remains limited to software verification and repository-backed artifacts, journal-specific software reporting guidance should form the main reporting backbone. If observational analyses are added, adapted STROBE elements should be incorporated. TRIPOD+AI, CLAIM, or related AI reporting extensions should be used only for sections that make genuine predictive-model claims.

## References

The current in-text citations used in this draft are listed below. Additional candidate sources remain tracked in `manuscript/references/seed_references.md`.

Alabdulgader, A., McCraty, R., Atkinson, M., Dobyns, Y., Vainoras, A., Ragulskis, M., & Stolc, V. (2018). Long-term study of heart rate variability responses to changes in the solar and geomagnetic environment. *Scientific Reports, 8*(1), 2663. <https://doi.org/10.1038/s41598-018-20932-x>

Arney, D., Zhang, Y., Kennedy-Metz, L. R., Dias, R. D., Goldman, J. M., & Zenati, M. A. (2023). An open-source, interoperable architecture for generating real-time surgical team cognitive alerts from heart-rate variability monitoring. *Sensors, 23*(8), 3890. <https://doi.org/10.3390/s23083890>

Bowman, C., Huang, Y., Walch, O. J., Fang, Y., Frank, E., Tyler, J., Mayer, C., Stockbridge, C., Goldstein, C., Sen, S., & Forger, D. B. (2021). A method for characterizing daily physiology from widely used wearables. *Cell Reports Methods, 1*(4), 100058. <https://doi.org/10.1016/j.crmeth.2021.100058>

Christie, I. C., & Gianaros, P. J. (2013). PhysioScripts: An extensible, open source platform for the processing of physiological data. *Behavior Research Methods, 45*(1), 125-131. <https://doi.org/10.3758/s13428-012-0233-x>

Devine, J. K., & Hursh, S. R. (2025). A narrative review on in-flight use of consumer sleep technologies for aviation research. *Sleep Advances*. <https://doi.org/10.1093/sleepadvances/zpaf076>

Gaisenok, O., Gaisenok, D., & Bogachev, S. (2025). The influence of geomagnetic storms on the risks of developing myocardial infarction, acute coronary syndrome, and stroke: Systematic review and meta-analysis. *Journal of Natural Science, Biology and Medicine*. <https://doi.org/10.4103/jmp.jmp_122_24>

Hartmeyer, S. L., Phillips, N. E., Jassil, F. C., Joris, C., Dibner, C., Collet, T. H., & Andersen, M. (2025). Multi-wearable approach for monitoring diurnal light exposure and body rhythms in nightshift workers. *Acta Physiologica*. <https://doi.org/10.1111/apha.70069>

Hursh, S. R., Balkin, T. J., Miller, J. C., & Eddy, D. R. (2004). The Fatigue Avoidance Scheduling Tool: Modeling to minimize the effects of fatigue on cognitive performance. *SAE Technical Paper Series*. <https://doi.org/10.4271/2004-01-2151>

Morris, M. B., Howland, J. P., Amaddio, K. M., & Gunzelmann, G. (2020). Aircrew fatigue perceptions, fatigue mitigation strategies, and circadian typology. *Aerospace Medicine and Human Performance, 91*(4), 363-368. <https://doi.org/10.3357/AMHP.5396.2020>

Quigley, K. S., Gianaros, P. J., Norman, G. J., Jennings, J. R., de Geus, E. J. C., Berntson, G. G., & Task Force on Publication Guidelines for Heart Rate Variability. (2024). Publication guidelines for heart rate and heart rate variability. *Psychophysiology, 61*(4), e14604.

Rogers, B., Murias, J. M., & Fleitas-Paniagua, P. R. (2025). Validity of an open-source mobile app to measure fractal correlation properties of heart rate variability during exercise. *European Journal of Applied Physiology*. <https://doi.org/10.1007/s00421-025-06037-0>

Shaffer, F., & Ginsberg, J. P. (2017). An overview of heart rate variability metrics and norms. *Frontiers in Public Health, 5*, 258. <https://doi.org/10.3389/fpubh.2017.00258>

Tarvainen, M. P., Niskanen, J.-P., Lipponen, J. A., Ranta-aho, P. O., & Karjalainen, P. A. (2014). Kubios HRV - Heart rate variability analysis software. *Computer Methods and Programs in Biomedicine, 113*(1), 210-220. <https://doi.org/10.1016/j.cmpb.2013.07.024>

Task Force of the European Society of Cardiology and the North American Society of Pacing and Electrophysiology. (1996). Heart rate variability: Standards of measurement, physiological interpretation and clinical use. *Circulation, 93*(5), 1043-1065.

Yang, C.-J., Fahier, N., He, C.-Y., Li, W.-C., & Fang, W.-C. (2020). An AI-edge platform with multimodal wearable physiological signals monitoring sensors for affective computing applications. In *2020 IEEE International Symposium on Circuits and Systems* (pp. 1-5). IEEE. <https://doi.org/10.1109/ISCAS45731.2020.9180909>

## Supplementary materials

Supplementary structure is planned in `manuscript/supplement/supplement_outline.md`.

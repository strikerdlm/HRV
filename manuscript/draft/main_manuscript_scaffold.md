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

[Draft]

Key points to cover:

- HRV is widely used for autonomic assessment, workload monitoring, and readiness tracking.
- Operational aerospace environments require more than isolated HRV values; they require schedule context, fatigue risk, environmental context, and auditable decision pathways.
- Existing solutions tend to be narrow: signal-processing software, fatigue-only tools, wearable-only platforms, or context-aware but domain-limited monitoring systems.

### 1.2 State of the art

[Draft]

Use `manuscript/tables/literature_gap_comparison.md` to organize this section around:

- HRV analysis platforms,
- physiological processing frameworks,
- fatigue and circadian decision tools,
- multimodal wearable monitoring systems,
- context-aware clinical interoperability platforms.

### 1.3 Gap statement

[Draft]

Suggested direction:

> Current tools do not adequately combine standards-informed HRV analytics, individualized physiological context, circadian and fatigue modeling, environmental overlays, and operational scheduling logic within one open, reproducible aerospace medicine platform.

### 1.4 Objective and contribution

[Draft]

Suggested contribution structure:

1. an integrated software architecture for translational aerospace medicine,
2. a shared Python analysis core exposed across research and operational interfaces,
3. an operational decision-support layer connecting HRV, fatigue, and schedule context,
4. a reproducibility-oriented export and documentation workflow.

## 2. Methods

### 2.1 Requirements and design rationale

[Draft]

Cover:

- translational requirements from aerospace medicine and operational physiology,
- need for explicit audit trails and bounded interpretation,
- rationale for integrating research and operational delivery modes.

### 2.2 System architecture

[Draft]

Describe:

- the shared Python core,
- `app/research_app.py` and `app/operational_app.py`,
- `api/main.py` and the frontend delivery surface,
- user persistence and longitudinal context,
- coupling between HRV, fatigue, circadian, scheduling, and space-weather modules.

### 2.3 Implementation

[Draft]

Include:

- HRV engine scope from `app/hrv_core.py`,
- scheduling and GO/NO-GO logic from `app/scheduling_core.py`,
- space-weather ingestion from `app/noaa_space.py`,
- publication export support from `app/publication_export.py`.

### 2.4 Validation and evaluation methodology

[Draft]

Use the staged validation posture defined in `manuscript/evidence/validation_story.md`:

- engineering verification through tests,
- bounded use of exported quantitative artifacts,
- explicit separation from future external validation.

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

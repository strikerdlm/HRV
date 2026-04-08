# Author: Dr Diego Malpica MD

## Figure Plan

This file defines the figures that the manuscript should reference. It now records both the intended content and the current rendered SVG assets for the submission-candidate package.

## Figure 1. Platform architecture

- **Purpose:** Show the full system at a glance.
- **Status:** Rendered.
- **Asset:** `manuscript/figures/figure1_platform_architecture.svg`
- **Resolution target:** 1600 x 960 SVG
- **Insertion point:** Methods 2.2 or Results 3.1
- **Content:** Inputs, shared Python modeling backend, user persistence, HRV analytic layer, SAFTE/circadian dynamics, environmental timing, readiness fusion, Next.js delivery routes, FastAPI orchestration, and secondary Streamlit interfaces.
- **Primary sources:** `README.md`, `api/main.py`, `app/research_app.py`, `app/operational_app.py`, `manuscript/evidence/core_modules_scope.md`
- **Caption goal:** Explain how one modeling backend supports a Node-first client, FastAPI orchestration, and secondary interfaces.
- **Draft caption:** *Figure 1. High-level architecture of Mission Control - Flight Surgeon. RR-interval and wearable-derived inputs feed a shared Python modeling backend that is coupled to user persistence, HRV analytics, SAFTE/circadian dynamics, environmental timing, readiness fusion, and export utilities. The same backend is exposed primarily through a Next.js frontend and FastAPI orchestration layer, while Streamlit remains a secondary interface in the repository.*

## Figure 2. End-to-end translational workflow

- **Purpose:** Show how raw RR or wearable inputs become operational outputs.
- **Status:** Rendered.
- **Asset:** `manuscript/figures/figure2_end_to_end_workflow.svg`
- **Resolution target:** 1600 x 900 SVG
- **Insertion point:** Results 3.1
- **Content:** RR ingestion -> HRV computation -> user context fusion -> fatigue and circadian interpretation -> readiness fusion -> scheduling and GO/NO-GO outputs -> export and audit trail.
- **Primary sources:** `app/hrv_core.py`, `app/user_profile_tab.py`, `app/scheduling_core.py`, `app/publication_export.py`
- **Caption goal:** Emphasize the transition from physiological measurement to decision support.
- **Draft caption:** *Figure 2. End-to-end translational workflow. Physiological inputs are ingested and processed into HRV metrics, linked to longitudinal user context, interpreted through fatigue and circadian model layers, and translated into readiness-oriented outputs, scheduling summaries, and exportable audit artifacts.*

## Figure 3. Research-to-operations coupling

- **Purpose:** Show that exploratory analytics and operational workflows are related but not identical.
- **Status:** Rendered.
- **Asset:** `manuscript/figures/figure3_research_to_operations_coupling.svg`
- **Resolution target:** 1600 x 920 SVG
- **Insertion point:** Methods 2.2 or Discussion 4.4
- **Content:** Next.js research routes, Next.js operational routes, FastAPI orchestration, shared Python model layers, and secondary Streamlit views; indicate where analysis artifacts and operational summaries originate.
- **Primary sources:** `README.md`, `WARP.md`, `api/main.py`
- **Caption goal:** Clarify the Node-first client architecture and why model-serving consistency matters for translational deployment.
- **Draft caption:** *Figure 3. Research-to-operations coupling in the platform. Research and operational routes in the Next.js client rely on a common FastAPI/Python modeling substrate while exposing different levels of detail and workflow focus. Secondary Streamlit interfaces remain available but are not the primary frontend scope of the manuscript.*

## Figure 4. Verification coverage map

- **Purpose:** Summarize engineering verification across the platform.
- **Status:** Rendered.
- **Asset:** `manuscript/figures/figure4_verification_coverage_map.svg`
- **Resolution target:** 1600 x 980 SVG
- **Insertion point:** Results 3.2
- **Content:** Matrix showing major biomathematical and orchestration layers such as HRV analytics, SAFTE/circadian dynamics, readiness fusion, environmental timing, API-backed Node delivery, and export utilities.
- **Primary sources:** `tests/`, `manuscript/evidence/validation_story.md`
- **Caption goal:** Distinguish strong model-adjacent implementation evidence from areas awaiting external numerical or physiological validation.
- **Draft caption:** *Figure 4. Verification coverage map. Representative automated tests support major readiness, environmental, and API-facing layers, while the HRV and SAFTE/circadian cores remain stronger in explicit code-level formulation than in external benchmark validation. The figure should visually distinguish engineering verification from future-facing model validation.*

## Optional Figure 5. Exploratory HRV to space-weather example

- **Purpose:** Illustrate the implemented correlation workflow if the underlying dataset provenance is documented well enough for publication.
- **Status:** Optional only; do not render unless dataset provenance is manuscript-ready.
- **Content:** A single lag-aware analysis example with metric, confidence interval, and sample size.
- **Primary sources:** `analysis/noaa_batch_correlations_20251124T020423Z.csv`, `app/app.py`
- **Caption goal:** Demonstrate analysis capability without overstating causal inference.
- **Draft caption:** *Figure 5. Optional exploratory lag-aware HRV to space-weather example. This figure should be included only if the sample definition, preprocessing rules, and inferential scope are documented well enough to support manuscript reporting.*

## Figure preparation rules

1. Each figure must be supported by a self-contained caption.
2. Figures should appear in the manuscript only after the supporting claims have been classified as `Supported` or carefully qualified `Partial`.
3. UI screenshots are acceptable only if used as implementation evidence, not as substitutes for validation.
4. Any exploratory figure based on `analysis/` artifacts must include explicit provenance and sample definition.
5. Prefer a clean systems-diagram style for Figures 1-3 and a matrix or coverage heatmap style for Figure 4.
6. The current submission-candidate package already includes SVG filenames, resolution targets, and suggested insertion points; revise these only if a journal template requires different sizing.

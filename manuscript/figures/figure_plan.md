# Author: Dr Diego Malpica MD

## Figure Plan

This file defines the figures that the manuscript should reference. It now records both the intended content and the current rendered SVG assets for the submission-candidate package.

## Figure 1. Platform architecture

- **Purpose:** Show the full system at a glance.
- **Status:** Rendered.
- **Asset:** `manuscript/figures/figure1_platform_architecture.svg`
- **Resolution target:** 1600 x 960 SVG
- **Insertion point:** Methods 2.2 or Results 3.1
- **Content:** Inputs, shared Python analysis core, user persistence, fatigue and circadian layer, space-weather layer, scheduling and decision logic, operational and research delivery surfaces.
- **Primary sources:** `README.md`, `api/main.py`, `app/research_app.py`, `app/operational_app.py`, `manuscript/evidence/core_modules_scope.md`
- **Caption goal:** Explain how one analysis core supports multiple interfaces and workflow layers.
- **Draft caption:** *Figure 1. High-level architecture of Mission Control - Flight Surgeon. RR-interval and wearable-derived inputs feed a shared Python analysis core that is coupled to user persistence, circadian and fatigue interpretation, space-weather context, scheduling logic, and export utilities. The same core is exposed through research and operational Streamlit applications, a FastAPI backend, and a Next.js frontend.*

## Figure 2. End-to-end translational workflow

- **Purpose:** Show how raw RR or wearable inputs become operational outputs.
- **Status:** Rendered.
- **Asset:** `manuscript/figures/figure2_end_to_end_workflow.svg`
- **Resolution target:** 1600 x 900 SVG
- **Insertion point:** Results 3.1
- **Content:** RR ingestion -> HRV computation -> user context fusion -> fatigue and circadian interpretation -> scheduling and GO/NO-GO outputs -> export and audit trail.
- **Primary sources:** `app/hrv_core.py`, `app/user_profile_tab.py`, `app/scheduling_core.py`, `app/publication_export.py`
- **Caption goal:** Emphasize the transition from physiological measurement to decision support.
- **Draft caption:** *Figure 2. End-to-end translational workflow. Physiological inputs are ingested and processed into HRV metrics, linked to longitudinal user context, interpreted alongside circadian and fatigue state, and translated into readiness-oriented outputs, scheduling summaries, and exportable audit artifacts.*

## Figure 3. Research-to-operations coupling

- **Purpose:** Show that exploratory analytics and operational workflows are related but not identical.
- **Status:** Rendered.
- **Asset:** `manuscript/figures/figure3_research_to_operations_coupling.svg`
- **Resolution target:** 1600 x 920 SVG
- **Insertion point:** Methods 2.2 or Discussion 4.4
- **Content:** Research Streamlit, operational Streamlit, FastAPI backend, and shared code modules; indicate where analysis artifacts and operational summaries originate.
- **Primary sources:** `README.md`, `WARP.md`, `api/main.py`
- **Caption goal:** Clarify the dual-interface architecture and why it matters for translational deployment.
- **Draft caption:** *Figure 3. Research-to-operations coupling in the platform. Exploratory analytics, operational dashboards, and web-delivered interfaces rely on a common analysis substrate while exposing different levels of detail and workflow focus.*

## Figure 4. Verification coverage map

- **Purpose:** Summarize engineering verification across the platform.
- **Status:** Rendered.
- **Asset:** `manuscript/figures/figure4_verification_coverage_map.svg`
- **Resolution target:** 1600 x 980 SVG
- **Insertion point:** Results 3.2
- **Content:** Matrix or grouped diagram showing tested domains such as scheduling, FRMS, space-weather ingest, API normalization, and export utilities.
- **Primary sources:** `tests/`, `manuscript/evidence/validation_story.md`
- **Caption goal:** Distinguish implemented-and-tested workflows from areas awaiting external validation.
- **Draft caption:** *Figure 4. Verification coverage map. Representative automated tests support major software pathways including scheduling and readiness logic, FRMS behavior, space-weather ingestion and alignment, and API-facing workflows. The figure should visually distinguish software verification from validation work that remains future-facing.*

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

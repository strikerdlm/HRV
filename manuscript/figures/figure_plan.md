# Author: Dr Diego Malpica MD

## Figure Plan

This file defines the figures that the manuscript should reference. It does not generate images; it documents the intended content, data source, and caption purpose for each figure.

## Figure 1. Platform architecture

- **Purpose:** Show the full system at a glance.
- **Content:** Inputs, shared Python analysis core, user persistence, fatigue and circadian layer, space-weather layer, scheduling and decision logic, operational and research delivery surfaces.
- **Primary sources:** `README.md`, `api/main.py`, `app/research_app.py`, `app/operational_app.py`, `manuscript/evidence/core_modules_scope.md`
- **Caption goal:** Explain how one analysis core supports multiple interfaces and workflow layers.

## Figure 2. End-to-end translational workflow

- **Purpose:** Show how raw RR or wearable inputs become operational outputs.
- **Content:** RR ingestion -> HRV computation -> user context fusion -> fatigue and circadian interpretation -> scheduling and GO/NO-GO outputs -> export and audit trail.
- **Primary sources:** `app/hrv_core.py`, `app/user_profile_tab.py`, `app/scheduling_core.py`, `app/publication_export.py`
- **Caption goal:** Emphasize the transition from physiological measurement to decision support.

## Figure 3. Research-to-operations coupling

- **Purpose:** Show that exploratory analytics and operational workflows are related but not identical.
- **Content:** Research Streamlit, operational Streamlit, FastAPI backend, and shared code modules; indicate where analysis artifacts and operational summaries originate.
- **Primary sources:** `README.md`, `WARP.md`, `api/main.py`
- **Caption goal:** Clarify the dual-interface architecture and why it matters for translational deployment.

## Figure 4. Verification coverage map

- **Purpose:** Summarize engineering verification across the platform.
- **Content:** Matrix or grouped diagram showing tested domains such as scheduling, FRMS, space-weather ingest, API normalization, and export utilities.
- **Primary sources:** `tests/`, `manuscript/evidence/validation_story.md`
- **Caption goal:** Distinguish implemented-and-tested workflows from areas awaiting external validation.

## Optional Figure 5. Exploratory HRV to space-weather example

- **Purpose:** Illustrate the implemented correlation workflow if the underlying dataset provenance is documented well enough for publication.
- **Content:** A single lag-aware analysis example with metric, confidence interval, and sample size.
- **Primary sources:** `analysis/noaa_batch_correlations_20251124T020423Z.csv`, `app/app.py`
- **Caption goal:** Demonstrate analysis capability without overstating causal inference.

## Figure preparation rules

1. Each figure must be supported by a self-contained caption.
2. Figures should appear in the manuscript only after the supporting claims have been classified as `Supported` or carefully qualified `Partial`.
3. UI screenshots are acceptable only if used as implementation evidence, not as substitutes for validation.
4. Any exploratory figure based on `analysis/` artifacts must include explicit provenance and sample definition.

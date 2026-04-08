# Author: Dr Diego Malpica MD

## Evidence Matrix

This document binds each planned manuscript claim to concrete repository evidence before drafting begins.

### Status rubric

- `Supported`: directly evidenced by code, documentation, tests, or versioned repository metadata.
- `Partial`: implemented in the repository, but publication-ready validation, provenance, or quantitative benchmarking is incomplete.
- `Gap`: should not be claimed without new data, approvals, or documentation.

| Planned manuscript claim | Evidence type | Primary anchors | Status | Planned manuscript use | Notes |
| --- | --- | --- | --- | --- | --- |
| The platform integrates HRV analytics, longitudinal user context, circadian and fatigue modeling, space-weather context, and operational decision support. | Code + documentation | `README.md`, `WARP.md`, `app/operational_app.py`, `app/research_app.py`, `api/main.py`, `app/scheduling_core.py` | Supported | Title, Introduction, Methods | Safe as an architecture and scope claim. |
| Research and operational delivery modes share the same Python analysis core across Streamlit, FastAPI, and Next.js surfaces. | Code + documentation | `README.md`, `app/research_app.py`, `app/operational_app.py`, `api/main.py`, `frontend/` | Supported | Methods | Phrase as a deployment model, not a usability or adoption claim. |
| The HRV engine computes standards-aligned time-domain, frequency-domain, nonlinear, and windowed metrics. | Code + documentation | `app/hrv_core.py`, `docs/Manual.md`, `README.md` | Partial | Methods | Implementation is evident, but external numerical agreement against a reference package is not yet documented. |
| Personalized user profiles and persistent longitudinal context are propagated into downstream calculations. | Code + documentation | `app/user_profile_tab.py`, `app/user_database.py`, `WARP.md`, `docs/Manual.md` | Supported | Methods | Appropriate for the system architecture and workflow description. |
| The fatigue, FRMS, IHPI, and scheduling layers are literature-anchored and deterministic rather than heuristic-only. | Code + tests | `app/scheduling_core.py`, `app/frms.py`, `app/frms_v2.py`, `tests/test_scheduling_core.py`, `tests/test_frms.py`, `tests/test_frms_v2.py` | Supported | Methods, Results | Present as an implemented decision-support engine, not as proof of operational outcome benefit. |
| Space-weather ingestion, caching, and impact modeling are implemented and tested. | Code + tests | `app/noaa_space.py`, `app/space_weather_impact.py`, `tests/test_noaa_cache.py`, `tests/test_space_weather_impact.py` | Supported | Methods, Results | Safe as an implementation and verification claim. |
| The platform supports lag-aware HRV to space-weather correlation analysis with multiplicity control. | Code + analysis artifacts | `app/app.py`, `WARP.md`, `tests/test_comprehensive_modules.py`, `analysis/noaa_batch_correlations_20251124T020423Z.csv` | Partial | Methods, possibly Results | Quantitative outputs exist, but cohort provenance, inclusion criteria, and analysis protocol must be documented before manuscript reporting. |
| Publication-oriented export utilities include statistical summaries and reproducibility metadata. | Code | `app/publication_export.py`, `app/export_utils.py` | Supported | Methods | Safe as a software capability claim. |
| Engineering verification exists across major operational paths, including scheduling, FRMS, space-weather alignment, and API endpoints. | Tests + documentation | `tests/`, `AGENTS.md`, `tests/test_research_windowed_endpoint.py`, `tests/test_space_weather_alignment.py`, `tests/test_comprehensive_modules.py` | Supported | Results | Avoid overstating total test counts unless rerun for the manuscript session. |
| The repository already demonstrates complete empirical validation of the integrated platform in human participants. | None identified | No dedicated study package found in the repository | Gap | Do not claim | Requires protocol, cohort description, outcomes, and ethics approval. |
| Regulatory certification or legal compliance has already been established for deployment. | Documentation only | `docs/lit_review.md`, `app/scheduling_core.py`, `app/physiological_sms.py`, `README.md` | Gap for certification; Supported for standards alignment | Discussion, Compliance | Use `aligned with`, `informed by`, or `designed with reference to`; do not claim certification or formal compliance. |
| Code can be openly shared and versioned for reproducibility. | Repository metadata | `LICENSE`, `README.md`, `requirements.txt`, `WARP.md`, git remote, git commit `a9141a3260ff5cab39eb8ae91dcce516b8d19864` | Supported | Transparency sections | Include repo URL, license, branch, and commit hash in the manuscript. |
| Data availability for manuscript results is already publication-ready. | Analysis artifacts + review notes | `analysis/`, `docs/lit_review.md` | Partial | Transparency sections | A formal dataset manifest, sharing conditions, and ethics linkage are still needed. |

## Immediate drafting rules

1. Results claims must map to `Supported` rows or to narrowly qualified `Partial` rows with explicit caveats.
2. `Partial` rows can be used in Methods and Discussion when framed as implemented workflows or exploratory outputs.
3. `Gap` rows must be moved into limitations, deployment prerequisites, or future work.
4. Roadmap items in `WARP.md` and feature summaries in `CHANGELOG.md` are not manuscript evidence unless paired with concrete code, tests, or export artifacts.

## Additional artifacts needed before final submission

- External numerical benchmarking of `app/hrv_core.py` against a trusted reference implementation or published test vectors.
- Study-specific IRB or ethics documentation if any human data are reported in the final manuscript.
- A manuscript-tagged software release or archived DOI for the exact reported version.
- A centralized dataset manifest for all empirical tables and figures, including access constraints.

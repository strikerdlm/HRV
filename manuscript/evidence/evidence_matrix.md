# Author: Dr Diego Malpica MD

## Evidence Matrix

This document binds each planned manuscript claim to concrete repository evidence before drafting begins.

### Status rubric

- `Supported`: directly evidenced by code, documentation, tests, or versioned repository metadata.
- `Partial`: implemented in the repository, but publication-ready validation, provenance, or quantitative benchmarking is incomplete.
- `Gap`: should not be claimed without new data, approvals, or documentation.

| Planned manuscript claim | Evidence type | Primary anchors | Status | Planned manuscript use | Notes |
| --- | --- | --- | --- | --- | --- |
| The platform integrates HRV analytics, longitudinal user context, circadian and fatigue modeling, space-weather context, and operational decision support. | Code + documentation | `README.md`, `WARP.md`, `frontend/`, `api/main.py`, `app/scheduling_core.py` | Supported | Title, Introduction, Methods | Safe as an architecture and scope claim when framed around a layered model stack rather than a feature inventory. |
| The primary frontend scope of the manuscript can be framed as a Next.js/Node.js client over FastAPI and a shared Python analysis core, while Streamlit remains secondary in the repository. | Code + documentation | `frontend/package.json`, `frontend/src/components/layout/sidebar.tsx`, `api/main.py`, `api/research_endpoints.py`, `app/research_app.py`, `app/operational_app.py` | Supported | Title, Abstract, Methods | Safe if described as a primary client and deployment path, not as proof that Streamlit is removed from the repo. |
| The HRV engine computes standards-aligned time-domain, frequency-domain, nonlinear, and windowed metrics. | Code + documentation | `app/hrv_core.py`, `docs/Manual.md`, `README.md` | Partial | Methods | Implementation is evident, but external numerical agreement against a reference package is not yet documented. |
| The fatigue and circadian layer includes an explicit reservoir-based SAFTE-style model with a mirrored TypeScript implementation for the web client. | Code + documentation | `app/fatigue_calculator/safte_model.py`, `frontend/src/lib/safte-model.ts`, `app/frms.py` | Partial | Methods, Results | Strong code-level formulation; treat the Python version as canonical and the TypeScript version as architectural mirroring, not independent validation. |
| Personalized user profiles and persistent longitudinal context are propagated into downstream calculations. | Code + documentation | `app/user_profile_tab.py`, `app/user_database.py`, `WARP.md`, `docs/Manual.md` | Supported | Methods | Appropriate for the system architecture and workflow description. |
| The readiness fusion layer combines HRV-derived features, fatigue state, and rule-based operational modifiers in a deterministic rather than heuristic-only way. | Code + tests | `app/scheduling_core.py`, `app/frms.py`, `app/frms_v2.py`, `tests/test_scheduling_core.py`, `tests/test_frms.py`, `tests/test_frms_v2.py` | Supported | Methods, Results | Present as an implemented decision-support engine, not as proof of operational outcome benefit. |
| Space-weather ingestion, caching, propagation, and alignment workflows are implemented and tested. | Code + tests | `app/noaa_space.py`, `app/space_weather_impact.py`, `app/space_weather_alignment.py`, `app/space_weather_influence.py`, `tests/test_noaa_cache.py`, `tests/test_space_weather_impact.py`, `tests/test_space_weather_alignment.py` | Supported | Methods, Results | Safe as an implementation and verification claim when framed as contextual timing/alignment rather than causal physiology. |
| The platform supports lag-aware HRV to space-weather correlation analysis with multiplicity control. | Code + analysis artifacts | `app/app.py`, `WARP.md`, `tests/test_comprehensive_modules.py`, `analysis/noaa_batch_correlations_20251124T020423Z.csv` | Partial | Methods, possibly Results | Quantitative outputs exist, but cohort provenance, inclusion criteria, and analysis protocol must be documented before manuscript reporting. |
| Publication-oriented export utilities include statistical summaries and reproducibility metadata. | Code | `app/publication_export.py`, `app/export_utils.py` | Supported | Methods | Safe as a software capability claim. |
| Engineering verification exists across major operational paths, including readiness fusion, FRMS behavior, space-weather alignment, and API endpoints that serve the Node-first client. | Tests + documentation | `tests/`, `AGENTS.md`, `tests/test_research_windowed_endpoint.py`, `tests/test_space_weather_alignment.py`, `tests/test_comprehensive_modules.py` | Supported | Results | Avoid overstating total test counts unless rerun for the manuscript session. |
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

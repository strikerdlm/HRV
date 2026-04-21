# Author: Dr Diego Malpica MD

## Evidence Matrix (OPI reframe)

This document binds each planned manuscript claim to concrete repository evidence before drafting. Supersedes the prior systems-and-software framing. Historical context: `manuscript/outline/novelty_and_venue_2026-04-21.md`.

### Status rubric

- `Supported`: directly evidenced by code, documentation, tests, or versioned repository metadata.
- `Partial`: implemented in the repository, but publication-ready validation, provenance, or quantitative benchmarking is incomplete.
- `Gap`: should not be claimed without new data, approvals, or documentation.

### Claims matrix

| Planned manuscript claim | Evidence type | Primary anchors | Status | Planned manuscript use | Notes |
| --- | --- | --- | --- | --- | --- |
| The Operational Performance Indicator (OPI) framework fuses SAFTE-style fatigue effectiveness, HRV-derived autonomic markers, Multiple Resource Theory cognitive-load modifiers, and environmental modifiers into a weighted per-task composite index. | Framework document + code | `analysis/operational_performance_indicators_research.md`, `app/scheduling_core.py`, `app/scheduling_engine.py`, `app/frms.py`, `app/frms_v2.py` | Supported | Title, abstract, introduction, methods, results | Framework formulation is theory-derived from HF literature and instantiated in code. Not externally validated in a field population. |
| Per-task OPI weight profiles are specified for ten manned-aviation task categories and seven UAS operator categories. | Framework document | `analysis/operational_performance_indicators_research.md` (sections 2.1-2.10, 4.2, 5.2, 5.6) | Supported | Methods, Table 1, Table 2 | Document this as theory-derived. Remaining empirical calibration is future work. |
| Vigilance-decrement and control-latency penalties are formalised for UAS/teleoperation use cases. | Framework document | `analysis/operational_performance_indicators_research.md` (sections 5.3, 5.4) | Supported | Methods, Table 3 | Formalised from Warm (2008) and Chen et al. (2007). Parameters are theory-derived. |
| The OPI framework is distributed as open-source reference code. | Repository metadata | `LICENSE` (MIT), `README.md`, git remote https://github.com/strikerdlm/HRV | Supported | Transparency, Discussion | Include a frozen release identifier (Zenodo DOI or git tag) in the final manuscript. |
| The reference implementation is delivered through a Next.js client over a FastAPI orchestration layer and a shared Python model stack. | Code + documentation | `frontend/`, `api/main.py`, `api/research_endpoints.py`, `app/` | Supported | Methods, Figure 4 | Describe as delivery architecture, not as a separate validated contribution. |
| The HRV engine computes standards-aligned time-domain, frequency-domain, and nonlinear metrics used as inputs to the OPI autonomic component. | Code + documentation | `app/hrv_core.py`, `docs/Manual.md` | Partial | Methods | Implementation evident; external numerical equivalence against a reference HRV package is not part of the manuscript claims. State this as a limitation. |
| The SAFTE fatigue component is implemented as a reservoir model with 24-hour + 12-hour circadian harmonics and optional phase-shift behaviour. | Code + mirrored client | `app/fatigue_calculator/safte_model.py`, `frontend/src/lib/safte-model.ts`, `app/frms.py` | Partial | Methods | Python implementation is canonical. TypeScript mirror is architectural consistency, not independent validation. |
| The readiness-fusion layer combines SAFTE, HRV, cognitive-load, and environmental modifiers deterministically rather than via opaque classifiers. | Code + tests | `app/scheduling_core.py`, `app/scheduling_engine.py`, `app/frms.py`, `app/frms_v2.py`, `tests/test_scheduling_core.py`, `tests/test_frms.py`, `tests/test_frms_v2.py` | Supported | Methods, Results | Inspectable rule-based fusion; this is a key differentiator vs. ML classifier approaches (Vogl 2025, Li 2025). |
| Engineering verification exists across the fusion logic, FRMS behaviour, and API endpoints that expose the OPI pathway. | Tests + documentation | `tests/test_scheduling_core.py`, `tests/test_frms.py`, `tests/test_frms_v2.py`, `tests/test_fatigue_integration.py`, `tests/test_api_user_profile_normalization.py`, `tests/test_research_windowed_endpoint.py` | Supported | Results, Table 5 | Report as engineering verification, not as operational validation. Avoid headline total-test-count claims unless rerun for the manuscript session. |
| An illustrative worked example instantiates the OPI pipeline end-to-end for a single 128-minute HRV recording across three task hypotheses. | Analysis artifacts + code | `analysis/hrv_report_complete_20251124T020445Z.md`, `app/hrv_core.py`, `app/fatigue_calculator/safte_model.py`, `app/scheduling_core.py` | Partial → Supported (after e2b worked-example commit) | Results, Figure 3 | Treat as a framework-instantiation demonstration. State explicitly that this is not an inferential test and does not generalise beyond the single recording. |
| Environmental modifiers (e.g., NOAA space-weather context) can be incorporated as an optional input to the OPI. | Code | `app/noaa_space.py`, `app/space_weather_impact.py`, `app/space_weather_alignment.py`, `tests/test_noaa_cache.py`, `tests/test_space_weather_impact.py` | Supported (as modifier) | Methods (brief), Supplement | Do not treat environmental influences as primary evidence. The single-subject HRV↔space-weather correlation CSVs move to Supplementary demonstrations with explicit caveats about autocorrelation and inferential scope. |
| Publication-oriented export utilities and structured logging support auditable reporting of OPI outputs. | Code | `app/publication_export.py`, `app/export_utils.py` | Supported | Methods, reproducibility | Safe as a software capability claim. |
| Per-task OPI weight profiles have been empirically validated against field performance data. | None identified | No dedicated validation study in the repository | Gap | Do not claim | Requires field study with operator performance outcomes, ethics approval, and adequate statistical power. |
| The integrated OPI framework has been externally benchmarked against alternative operator-readiness models (Stevens 2022 CMP, Feng 2018 MRT-logistic, Vogl 2025 SVM). | None identified | — | Gap | Position as future work | Head-to-head benchmarking requires matched datasets and shared task taxonomies; outside the scope of a methodology-introduction paper. |
| Regulatory certification or legal compliance has been established. | Documentation only | `docs/lit_review.md`, `README.md` | Gap for certification; Supported for standards alignment | Discussion, Compliance | Use "aligned with", "informed by". Never "certified". |
| Code can be shared and versioned openly for reproducibility. | Repository metadata | `LICENSE`, `README.md`, `requirements.txt`, `frontend/package.json` | Supported | Transparency | Include repo URL, license, and a frozen release identifier in the final manuscript. |

### Component-specific claim audit

| OPI component | Implementation evidence | Verification evidence | Validation evidence | Manuscript use |
| --- | --- | --- | --- | --- |
| SAFTE fatigue | `app/fatigue_calculator/safte_model.py`, `frontend/src/lib/safte-model.ts` | `tests/test_frms.py`, `tests/test_fatigue_integration.py` | None (framework paper does not revalidate SAFTE; relies on Hursh 2004 and Devine 2022) | Methods. Hedged. |
| HRV autonomic | `app/hrv_core.py` | `tests/test_comprehensive_modules.py`, `tests/test_research_windowed_endpoint.py` (endpoint monkeypatched) | External benchmarking against reference HRV package is explicitly out of scope for this paper. | Methods. State limitation explicitly. |
| MRT cognitive-load modifier | `app/scheduling_core.py` (task-specific weights), `analysis/operational_performance_indicators_research.md` | `tests/test_scheduling_core.py` | None. Weights are theory-derived from Wickens 2002/2008, Feng 2018. | Methods, Table 2. |
| Vigilance decrement (UAS) | `analysis/operational_performance_indicators_research.md` section 5.3 | None implemented yet (framework-level) | None. Parameters are theory-derived from Warm 2008. | Methods, Table 3. Implementation in reference code is a future-work candidate. |
| Latency penalty (UAS teleop) | `analysis/operational_performance_indicators_research.md` section 5.4 | None implemented yet | None. Parameters are theory-derived from Chen et al. 2007. | Methods, Table 3. Implementation in reference code is a future-work candidate. |
| Environmental modifiers | `app/noaa_space.py`, alignment modules | `tests/test_noaa_cache.py`, `tests/test_space_weather_impact.py`, `tests/test_space_weather_alignment.py` | No causal-physiology validation claimed. | Methods (brief), Supplement. |
| Readiness fusion orchestration | `app/scheduling_core.py`, `app/frms.py`, `app/frms_v2.py`, `app/scheduling_engine.py` | `tests/test_scheduling_core.py`, `tests/test_frms.py`, `tests/test_frms_v2.py` | No operational outcome validation. | Methods, Results. |

### Immediate drafting rules

1. Results claims must map to `Supported` rows or to narrowly qualified `Partial` rows with explicit caveats.
2. `Partial` rows can be used in Methods and Discussion when framed as implemented workflows or illustrative outputs.
3. `Gap` rows must be moved into limitations, deployment prerequisites, or future work.
4. Per-task OPI weights must always be described as theory-derived pending field validation. Never as "validated".
5. The 128-minute recording must always be described as an illustrative worked example. Never as an empirical test.

### Additional artifacts needed before final submission

- Tagged software release or archived DOI (Zenodo) for the exact reported version.
- Centralised dataset manifest for any empirical table or figure, including access constraints.
- If any future version adds field data, study-specific IRB/ethics documentation, protocol, and reporting-guideline positioning (STROBE / TRIPOD+AI as applicable).

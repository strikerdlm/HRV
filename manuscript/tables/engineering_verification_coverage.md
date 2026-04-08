# Author: Dr Diego Malpica MD

## Table 3. Engineering Verification Coverage by Model and Orchestration Layer

This table summarizes representative software-verification evidence that is safe to cite in the Results section. It should be interpreted as engineering verification, not as clinical or operational validation.

| Layer | Representative tests or artifacts | What is verified | Manuscript-safe interpretation | Boundary or caveat |
| --- | --- | --- | --- | --- |
| HRV analytic core | `app/hrv_core.py`, `tests/test_research_windowed_endpoint.py` | Indirect evidence that the HRV computation layer is wired into endpoint workflows and can be executed through repository pathways. | Supports reporting of implemented HRV numerics and endpoint connectivity. | Stronger as implementation evidence than as external numerical benchmark evidence. |
| SAFTE/circadian model layer | `tests/test_frms.py`, `tests/test_frms_v2.py`, `tests/test_fatigue_integration.py`, `frontend/src/lib/safte-model.ts` | Fatigue-model behavior, FRMS-related scoring, and mirrored client/backend fatigue logic. | Supports reporting of an explicit fatigue-governance and circadian modeling layer. | Not a substitute for prospective fatigue-outcome validation or full frontend/backend parity testing. |
| Readiness fusion and scheduling logic | `tests/test_scheduling_core.py` | Deterministic threshold logic, score composition, and rule behavior for operational decision pathways. | Supports the claim that readiness fusion is implemented and regression-tested. | Does not establish real-world mission effectiveness. |
| Environmental timing and alignment | `tests/test_noaa_cache.py`, `tests/test_space_weather_impact.py`, `tests/test_space_weather_alignment.py` | NOAA ingestion, cache behavior, impact-model plumbing, and temporal alignment between environmental and physiological layers. | Supports the claim that environmental timing context is implemented and tested as a software pathway. | Does not prove physiological causality or predictive validity. |
| API-backed Node delivery | `tests/test_api_user_profile_normalization.py`, `tests/test_research_windowed_endpoint.py` | Profile normalization, request/response behavior, and endpoint-level analytical pathways that support the Next.js client. | Supports the Node-first delivery and reproducibility claims. | Endpoint verification is stronger than some underlying numeric benchmark evidence. |
| Reporting and export infrastructure | `tests/test_comprehensive_modules.py` | Statistical helper behavior and parts of the broader reporting surface. | Supports the claim that reporting-related utilities are software-backed rather than ad hoc. | Should not be framed as validation of every downstream analytic interpretation. |

# Author: Dr Diego Malpica MD

## Table 3. Engineering Verification Coverage by Module Family

This table summarizes representative software-verification evidence that is safe to cite in the Results section. It should be interpreted as engineering verification, not as clinical or operational validation.

| Module family | Representative tests or artifacts | What is verified | Manuscript-safe interpretation | Boundary or caveat |
| --- | --- | --- | --- | --- |
| Scheduling, IHPI, and readiness logic | `tests/test_scheduling_core.py` | Deterministic threshold logic, score composition, and rule behavior for operational decision pathways. | Supports the claim that core scheduling logic is implemented and regression-tested. | Does not establish real-world mission effectiveness. |
| FRMS and fatigue modeling | `tests/test_frms.py`, `tests/test_frms_v2.py`, `tests/test_fatigue_integration.py` | Fatigue-model behavior, FRMS-related scoring, and integration of fatigue variables into platform workflows. | Supports reporting of implemented fatigue-governance pathways. | Not a substitute for prospective fatigue-outcome validation. |
| Space-weather ingest and cache handling | `tests/test_noaa_cache.py`, `tests/test_space_weather_impact.py` | NOAA data ingestion, caching behavior, and impact-model plumbing. | Supports the claim that environmental context is implemented and tested as a software pathway. | Does not prove physiological causality or predictive validity. |
| Space-weather alignment workflows | `tests/test_space_weather_alignment.py` | Temporal alignment and cross-domain coupling support between environmental and physiological layers. | Supports reporting of implemented alignment workflows. | Exploratory analysis outputs remain manuscript-secondary until provenance is curated. |
| API normalization and endpoint behavior | `tests/test_api_user_profile_normalization.py`, `tests/test_research_windowed_endpoint.py` | Profile normalization, request/response behavior, and endpoint-level windowed analysis pathways. | Supports the dual-interface delivery and reproducibility claims. | Endpoint verification is stronger than some underlying numeric benchmark evidence. |
| Broader statistical and charting utilities | `tests/test_comprehensive_modules.py` | Statistical helper behavior and parts of the broader reporting surface. | Supports the claim that reporting-related utilities are software-backed rather than ad hoc. | Should not be framed as validation of every downstream analytic interpretation. |

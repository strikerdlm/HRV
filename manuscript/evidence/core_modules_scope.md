# Author: Dr Diego Malpica MD

## Core Module Scope

This document fixes the minimum set of modules and workflows that belong in the main manuscript for a full-platform translational aerospace medicine paper.

## Main-text system story

```mermaid
flowchart LR
rrInput["RR and wearable inputs"] --> hrvCore["HRV analytics core"]
userContext["User profile and longitudinal context"] --> hrvCore
userContext --> fatigueLayer["Circadian and fatigue layer"]
spaceContext["Space-weather context"] --> fatigueLayer
hrvCore --> decisionLayer["Scheduling and GO/NO-GO logic"]
fatigueLayer --> decisionLayer
decisionLayer --> delivery["Operational UI, research UI, API, exports"]
```

## Modules to keep in the main manuscript

| Workflow | Primary files | Why it stays in the main paper | Evidence anchor |
| --- | --- | --- | --- |
| HRV analytics core | `app/hrv_core.py`, `docs/Manual.md` | This is the physiological measurement backbone for the whole platform and the main source of reproducible computational detail. | Implemented code, user manual, export modules |
| User profile and persistence | `app/user_profile_tab.py`, `app/user_database.py` | The paper needs a clear explanation of how person-level context enters the analysis and decision layers. | Persistent schema and documented longitudinal workflow |
| Circadian and fatigue modeling | `app/circadian/`, `app/frms.py`, `app/frms_v2.py`, `app/fatigue_integration.py` | These modules convert physiological data and schedule context into operationally interpretable forecasts. | Literature references in code and dedicated test files |
| Scheduling, IHPI, and GO/NO-GO logic | `app/scheduling_core.py`, `app/scheduling_engine.py`, `app/scheduling_tab.py` | This is the clearest translational bridge from analytics to actionable aerospace-medicine decision support. | `tests/test_scheduling_core.py`, explicit threshold logic |
| Space-weather ingestion and impact modeling | `app/noaa_space.py`, `app/space_weather_impact.py`, `app/space_weather_alignment.py` | This is the domain-specific differentiator that separates the platform from generic HRV tools. | NOAA caching tests, alignment tests, analysis artifacts |
| Dual delivery architecture | `app/operational_app.py`, `app/research_app.py`, `api/main.py`, `frontend/` | The manuscript should show that one Python core supports both exploratory research and operational deployment. | Repo architecture docs and API surface |
| Publication and reproducibility exports | `app/publication_export.py`, `app/export_utils.py` | Q1 software papers expect explicit reporting and export pathways, not only computation. | Export code and reproducibility fields |

## Modules to move to supplementary material

| Supplementary area | Primary files | Why it moves out of the main paper |
| --- | --- | --- |
| Device-specific ingestion details | `app/actigraph_import.py`, `app/garmin_import.py`, `app/somfit_import.py`, `app/polar_accesslink.py`, related import utilities | Important for implementation depth, but too detailed for the primary systems narrative. |
| Real-time and BLE pathways | `app/realtime_ble.py`, `app/realtime_hrv.py`, `app/polar_h10_recorder.py` | Operationally interesting, but not necessary to establish the core translational architecture. |
| GPU and CPU optimization internals | `app/gpu_processing.py`, `app/performance_utils.py`, other optimization helpers | Relevant to engineering performance, not central to the paper's clinical and operational contribution. |
| ML, GPT, and agentic interpretation layers | `app/ml_enhancements.py`, `app/ml_analytics.py`, `app/ml_predictions.py`, `app/gpt_interpretation.py`, `app/agent_insights.py` | These features raise separate validation and reporting questions; include only if they are independently supported. |
| Deep exploratory specialty modules | `app/radiation_exposure.py`, `app/advanced_hrv_analytics.py`, `app/hrv_fragmentation.py`, other niche analytics modules | Valuable as breadth indicators, but they would diffuse the main argument if described in detail. |
| Single-user data-science entrypoint | `app/space_weather_ds_app.py` | Useful for specialized workflows, but secondary to the research and operational deployment story. |

## Claim boundaries for the main paper

1. The manuscript should describe an integrated translational platform, not a validation paper for every module in the repository.
2. The main Results section should prioritize workflows with both code-level implementation and clear test or artifact support.
3. The paper should mention advanced AI, real-time, and niche modules only when they strengthen the platform narrative or belong in Supplementary Methods.
4. Any module without a stable validation story should appear as optional architecture, not as a central contribution.

## Recommended main-paper contributions

1. A dual-interface aerospace medicine platform built on a shared Python analysis core.
2. A standards-informed physiological pipeline that integrates HRV, longitudinal user context, circadian and fatigue modeling, and space-weather context.
3. An operational decision-support layer for scheduling, readiness, and GO/NO-GO logic.
4. A reproducibility-oriented export and reporting workflow suitable for research and operational audit trails.

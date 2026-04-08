# Author: Dr Diego Malpica MD

## Table 1. Platform Architecture and Module Families

This table summarizes the main-text architecture layers for the manuscript. It is a system-description table, not a benchmark table.

| Layer or module family | Representative files | Role in the platform | Main manuscript use | Evidence posture |
| --- | --- | --- | --- | --- |
| Physiological analytics core | `app/hrv_core.py`, `docs/Manual.md` | Computes HRV domains, preprocessing pathways, and windowed summaries from RR-interval inputs. | Methods backbone for the computational core. | Implemented and documented; external numerical benchmarking remains incomplete. |
| User context and persistence | `app/user_profile_tab.py`, `app/user_database.py` | Stores longitudinal user characteristics, assessments, and mission-relevant context that can influence downstream interpretation. | Explains how outputs become person-specific rather than context-free. | Supported by code and documented workflow. |
| Circadian and fatigue layer | `app/circadian/`, `app/frms.py`, `app/frms_v2.py`, `app/fatigue_integration.py` | Converts sleep, circadian, and schedule information into operationally interpretable fatigue and readiness states. | Core translational layer linking physiology to operational exposure. | Supported by code, documentation, and dedicated tests. |
| Scheduling and decision support | `app/scheduling_core.py`, `app/scheduling_engine.py`, `app/scheduling_tab.py` | Integrates physiological and schedule variables into crew-level scoring, readiness framing, and GO/NO-GO style outputs. | Main operational contribution in Results and Discussion. | Supported by deterministic code paths and representative tests. |
| Space-weather ingestion and alignment | `app/noaa_space.py`, `app/space_weather_impact.py`, `app/space_weather_alignment.py` | Ingests, caches, harmonizes, and aligns environmental context for exploratory coupling with physiological data. | Domain-specific differentiator relative to generic HRV tools. | Supported for implementation and engineering verification. |
| Delivery surfaces | `app/research_app.py`, `app/operational_app.py`, `api/main.py`, `frontend/` | Exposes one shared analysis core through research, operational, API, and modern web workflows. | Supports the dual-interface deployment claim. | Supported by repository architecture and delivery code. |
| Export and audit support | `app/publication_export.py`, `app/export_utils.py`, `logging_config.py` | Produces structured outputs, reproducibility-oriented exports, and audit/logging support. | Supports transparency and reporting sections. | Supported for implementation; best strengthened further by release archiving. |

# Author: Dr Diego Malpica MD

## Table 4. Reproducibility and Deployment Metadata

This table captures manuscript-level reproducibility metadata for the current submission candidate.

| Item | Current state | Evidence source | Submission note |
| --- | --- | --- | --- |
| Repository URL | `https://github.com/strikerdlm/HRV.git` | Git remote, `README.md` | Safe to report in the manuscript. |
| License | MIT | `LICENSE` | Safe to report in the manuscript. |
| Current working branch | `main` | Git metadata | Safe to report in the manuscript. |
| Current commit hash used in draft | `a32959258ff01e459ac9d06609f58c3cd09fee47` | Git metadata | Prefer a tagged release or archived DOI before submission. |
| Primary documented environment | conda `hrv-py312`, Python 3.12 | `WARP.md`, `README.md`, `AGENTS.md` | Treat this as the authoritative environment unless container wording is harmonized. |
| Primary dependency declaration | `requirements.txt` | Repository root | Safe to cite as the dependency anchor. |
| Main delivery surfaces | Research Streamlit, operational Streamlit, FastAPI, Next.js | `README.md`, `api/main.py`, `app/research_app.py`, `app/operational_app.py` | Supports the dual-interface deployment claim. |
| Logging and audit support | Centralized logs under `logs/` with structured helpers | `logging_config.py`, `WARP.md` | Safe to describe as audit-oriented software infrastructure. |
| Export and reporting utilities | Structured export modules for tables, summaries, and reporting artifacts | `app/publication_export.py`, `app/export_utils.py` | Safe to report as implemented reproducibility support. |
| Automated verification surface | Representative tests across scheduling, FRMS, NOAA, API, and alignment pathways | `tests/`, `manuscript/evidence/validation_story.md` | Safe to summarize as engineering verification only. |
| Derived analysis artifacts | `analysis/` outputs exist for exploratory workflows | Repository artifacts, validation story | Keep secondary unless provenance is manuscript-ready. |

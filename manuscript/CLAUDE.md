# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## What this directory is

`manuscript/` is a **Q1 journal submission package** for a systems/methods/software paper describing *Mission Control – Flight Surgeon*: an open-source, Node-first biomathematical platform for HRV analytics, SAFTE/circadian fatigue modeling, space-weather integration, and aerospace operational readiness. The primary target venue is **Computer Methods and Programs in Biomedicine (CMPB)**; the shortlist and packaging implications are in `outline/manuscript_outline.md`.

The manuscript subfolder is **not a draft pile**. The IMRaD scaffold (`draft/main_manuscript_scaffold.md`), all six tables, all four SVG figures, the evidence/compliance maps, and the seed bibliography are complete. Blocking work is: final venue selection → journal template export → authorship/DOI metadata.

---

## Read order for orientation

Start here before touching any file:

1. `README.md` — pipeline status, Q1 roadmap (tasks A–E), guardrails
2. `outline/manuscript_outline.md` — thesis, venue shortlist, writing order
3. `evidence/validation_story.md` — what can be claimed vs. what is future work
4. `draft/main_manuscript_scaffold.md` — full draft (≈25 KB; complete IMRaD)
5. `tables/model_layers_and_evidence_tiers.md` — Table 6 / biomathematical spine
6. `supplement/submission_support_appendix.md` — reviewer-facing extensions

---

## Folder map

| Folder | Contents |
|---|---|
| `outline/` | Thesis, section plan, Q1 venue shortlist (`manuscript_outline.md`) |
| `draft/` | Full IMRaD manuscript (`main_manuscript_scaffold.md`) |
| `tables/` | Tables 1–6 (architecture, literature gap, verification, reproducibility, compliance, model layers) |
| `figures/` | SVG figures 1–4 and figure captions/specs (`figure_plan.md`) |
| `references/` | Seed bibliography (`seed_references.md`) and MCP research notes |
| `supplement/` | Supplementary outline and submission-support appendix |
| `evidence/` | Evidence matrix, module scope, validation posture, compliance map |

---

## Parent-repo run commands

These commands are for the **parent platform** this paper describes (run from the repo root unless noted):

| Task | Command |
|---|---|
| Streamlit research UI | `streamlit run app/research_app.py` (port 8501) |
| FastAPI backend | `uvicorn api.main:app --reload --port 8180` |
| Next.js frontend | `npm run dev` inside `frontend/` (port 3100; requires FastAPI) |
| Python tests | `pytest tests/ -v` (366 tests) |
| Python lint | `ruff check app/ tests/` |
| Frontend lint | `npx eslint .` inside `frontend/` |
| Frontend build | `npm run build` inside `frontend/` |

Run a single test: `pytest tests/path/to/test_file.py::test_function_name -v`

For service ports, `.env` requirements, and known gotchas (Streamlit version pin, Tornado pin, `kaleido` slow import) see root `AGENTS.md`.

---

## Guardrails — do not skip

1. **Evidence discipline:** If a claim is not backed by code in the repo (tests, docs, logged outputs) or a cited paper, it is a *limitation* or *future work*—see `evidence/validation_story.md`. Do not upgrade evidence tiers without real new data.

2. **Regulatory language:** Standards (NASA, ICAO, etc.) are *alignment*, not *certification*. The platform is "standards-informed." See `evidence/compliance_and_transparency_map.md`.

3. **No scope drift:** Primary delivery is **Next.js + TypeScript over FastAPI**; **Streamlit is secondary**. Do not revert to Streamlit-led framing without explicit author direction.

4. **Centralized project docs:** Repo-wide changes belong in root `README.md`, `CHANGELOG.md`, and `docs/Manual.md`. This manuscript folder is local except for cross-links.

5. **Claims audit:** After any code change, re-audit the draft against `evidence/evidence_matrix.md`. Downgrade or remove anything that drifts from Supported/Partial evidence tiers.

---

## Current pipeline status (as of 2026-04-08)

| Item | Status |
|---|---|
| IMRaD draft | Done |
| Tables 1–6 | Done |
| Figures 1–4 (SVG) | Done |
| Evidence matrix + validation posture | Done |
| Seed bibliography | Done |
| Q1 venue shortlist | Done (in `outline/manuscript_outline.md`) |
| Journal template export | Not started — depends on final venue |
| Tagged release / archived DOI | Not started — needed for reproducibility statement |
| Authorship / funding / COI metadata | Not started — must be confirmed before submission |

---

## Author

Dr. Diego Malpica MD — Aerospace Medicine Specialist

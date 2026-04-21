# Author: Dr Diego Malpica MD

## Manuscript workspace — orientation for agents and contributors

**Read this file first** when working under `manuscript/`. It records where the paper sits in the publication pipeline, what is already done, and what remains for a **Q1 scientific journal** submission.

### Current framing — OPI methodology paper for Applied Ergonomics

As of 2026-04-21, the manuscript has been repositioned on branch `q1-hf-opi-reframe` around a task-calibrated **Operational Performance Indicator (OPI)** framework targeted at *Applied Ergonomics* (Elsevier, Q1 Human Factors, JIF 3.4). The prior biomedical-computing (CMPB/JBI) framing remains in git history on `main` but is not the active direction. The OPI reframe is motivated by the author's decision to prioritise medical / psychology / human factors venues where the current evidence base (framework + reference implementation + engineering verification + illustrative worked example) is sufficient for Q1 submission without new external validation studies.

Literature verification and venue targeting rationale: `manuscript/outline/novelty_and_venue_2026-04-21.md`.

### One-line status

Draft submission package complete on branch `q1-hf-opi-reframe`: IMRaD draft (~5,800 words), three OPI tables (taxonomy, weight profiles, vigilance/latency), four-figure plan, seed references (23 cited + 10 pool, all Crossref-verified), cover letter draft, highlights. Blocking work is now mostly human metadata (authorship, funding, COI), figure generation at publication quality, journal template import, and frozen release identifier.

---

## Pipeline position (OPI reframe)

| Stage | Status | Notes |
| --- | --- | --- |
| Novelty verification vs. 2022–2026 HF literature | Done | `outline/novelty_and_venue_2026-04-21.md` |
| Evidence matrix and validation-story reframe | Done | `evidence/evidence_matrix.md`, `evidence/validation_story.md` |
| OPI tables (taxonomy, weights, vigilance/latency) | Done | `tables/opi_task_taxonomy.md`, `tables/opi_weight_profiles.md`, `tables/opi_vigilance_latency_models.md` |
| Main draft (IMRaD, Applied Ergonomics) | Done, updated 2026-04-21 with (a) PVT + Sleep integration pass and (b) novelty / principled-simplicity editorial pass for the doctoral reader — §4.3 expanded to five-paragraph case-for-principled-simplicity | `draft/opi_main_manuscript.md` (~7,700 words) |
| Seed references (23 cited + pool) | Done, DOI-verified; manuscript body now cites Basner & Dinges 2011, Dinges 1997, Grant 2017, Anwyl-Irvine 2020, Garaizar & Vadillo 2014, Lunsford-Avery 2018, Lee 2025, Schyvens 2024 inline | `references/seed_references.md` + opi_main_manuscript.md References |
| Figure plan (4 figures) | Done | `figures/figure_plan_opi.md` |
| Cover letter (Applied Ergonomics) | Done, draft | `submission/cover_letter_applied_ergonomics.md` |
| Highlights (Elsevier format) | Done | `submission/highlights.md` |
| Publication workflow (Zenodo, JOSS, medRxiv) | Done | `submission/publication_workflow.md` |
| Figure 3 (publication quality) | Done | `figures/figure3_opi_worked_example.{pdf,svg,png}` + `analysis/opi_worked_example.py` |
| Worked-example numerical output for Results §3.1 | Done | `analysis/opi_worked_example.json`; §3.1 text updated |
| Figures 1, 2, 4 (publication quality) | Not started | Adapt existing SVG per `figures/figure_plan_opi.md` |
| Supplementary appendix refresh | Not started | Terminology alignment to OPI framing in `supplement/submission_support_appendix.md` |
| Journal template / final layout | Not started | Elsevier Applied Ergonomics template import |
| Tagged release / archive DOI | Not started | Needed for final availability statement |
| Final authorship / funding / COI | Not started | Must be confirmed before submission |

---

## Target outcome (reaffirmed)

- **Goal:** A **Q1** journal article in **Human Factors / Ergonomics** describing the OPI framework as a translational aerospace medicine methodology contribution, with open-source reference implementation and illustrative worked example.
- **Primary target:** *Applied Ergonomics* (Elsevier). JIF 3.4. Q1 Human Factors.
- **Paper type:** Methodology + reference software + illustrative case — **not** a clinical trial, **not** a diagnostic-accuracy study, **not** a validation paper. Field validation of per-task OPI weights is explicit future work.
- **Success criterion:** Reviewers can trace every major claim to repository code, engineering verification, or DOI-verified HF literature, with limitations clearly separated from framework claims.

---

## Q1 publication roadmap — remaining tasks (priority order)

### A. Complete the submission package

1. **Refresh supplementary appendix** (`supplement/submission_support_appendix.md`) to align terminology with OPI framing — light edit, keep engineering verification inventory, standards crosswalk, non-claims, and deployment prerequisites.
2. **Generate Figures 1-4 at publication quality** — adapt SVG assets per `figures/figure_plan_opi.md`. Build Figure 3 from worked-example output (can regenerate via e2b or Python locally).
3. **Run the worked example numerically** — optional but recommended. Produce `analysis/opi_worked_example.json` and `analysis/opi_worked_example_figure.*` for Figure 3 and numerical text in Results §3.1. Currently the draft references expected qualitative behaviour; numerical specifics can be inserted once the e2b run completes.

### B. Author metadata and human decisions

1. **Finalise author list, affiliations, ORCIDs, CRediT roles.** Currently single-author; expand if collaborators added.
2. **Confirm funding declaration and conflict-of-interest statements** for all authors.
3. **Confirm acknowledgments** for collaborators, institutions, and infrastructure support.

### C. Reproducibility

1. **Cut a tagged release** on the `strikerdlm/HRV` repository (semantic version, e.g., `v0.6.0-opi`), archive to Zenodo, cite Concept DOI in §6.2 and Table 4. Full procedure in `submission/publication_workflow.md` §1.
2. **Harmonise environment wording** across draft, supplementary, and root `README.md` (`conda hrv-py312`, Python 3.12, `requirements.txt`, `frontend/package.json`).
3. **Post preprint** to medRxiv Health Informatics before Applied Ergonomics submission — see `submission/publication_workflow.md` §2.
4. **Optional JOSS parallel track** for independent software credit — see `submission/publication_workflow.md` §3.

### D. Venue-specific formatting

1. **Download the Applied Ergonomics author guidelines** and import the journal template (Word / LaTeX / Overleaf). Adjust headings, reference style, figure file formats (PDF + EPS + TIFF 300 dpi), word limits.
2. **Adjust reference style** from APA7 to the journal's preferred style if different (Elsevier Applied Ergonomics uses Harvard/APA hybrid).

### E. Submission mechanics

1. **Editorial Manager portal submission** with cover letter, manuscript, Highlights, figures, tables, supplement.
2. **Prepare the anonymised version** for double-masked review if required.
3. **Track submission ID** and first-decision date (Applied Ergonomics median 79 days).

---

## Guardrails (do not skip)

1. **Evidence discipline:** Framework is theory-derived. Per-task weights are theory-derived pending field calibration. The 128-min worked example is illustrative, not inferential. See `evidence/validation_story.md`.
2. **Regulatory language:** Standards (NASA, ICAO) are **alignment**, not certification — see `evidence/compliance_and_transparency_map.md`.
3. **No silent scope drift:** OPI + open-source reference implementation is the spine. Do not revert to the prior CMPB/JBI systems-paper framing without explicit author direction. The prior draft is preserved in git history and supersedes only if the reframe is abandoned.
4. **Centralised project docs:** Repo-wide documentation changes belong in root `README.md`, `CHANGELOG.md`, and `docs/Manual.md`. This manuscript folder is local except for cross-links.
5. **Citation discipline:** Every in-text citation in the draft must have a Crossref- or publisher-verified DOI in `references/seed_references.md`. See the verification notes in `outline/novelty_and_venue_2026-04-21.md`.

---

## Folder map

- `outline/` — Framing documents: `manuscript_outline.md` (authoritative), `novelty_and_venue_2026-04-21.md` (verification rationale)
- `draft/` — Active draft: `opi_main_manuscript.md`; prior scaffold retained as `main_manuscript_scaffold.md` for history
- `tables/` — OPI framework tables (opi_task_taxonomy, opi_weight_profiles, opi_vigilance_latency_models); retained prior tables for context
- `figures/` — Figure plan `figure_plan_opi.md`; existing SVG assets serve as source material for adaptation
- `references/` — `seed_references.md` (23 cited + pool, all DOI-verified) and `mcp_research_notes.md`
- `supplement/` — `submission_support_appendix.md` (needs OPI terminology refresh), `supplement_outline.md`
- `evidence/` — `evidence_matrix.md`, `validation_story.md`, `core_modules_scope.md`, `compliance_and_transparency_map.md`
- `submission/` — `cover_letter_applied_ergonomics.md`, `highlights.md`, `publication_workflow.md` (Zenodo/JOSS/preprint/hygiene)

## High-value files (read order for new agents)

1. `outline/manuscript_outline.md` — thesis, table/figure index, venue choice
2. `outline/novelty_and_venue_2026-04-21.md` — literature verification and venue rationale
3. `evidence/validation_story.md` — what can be claimed vs. verified
4. `draft/opi_main_manuscript.md` — active draft
5. `tables/opi_weight_profiles.md` — OPI formulation and per-task weights
6. `submission/cover_letter_applied_ergonomics.md` — venue framing and contribution statement

## Relation to the rest of the repo

- Service ports and run commands: root `AGENTS.md`
- Application behaviour and features: `docs/Manual.md`, `WARP.md`
- Framework derivation source: `analysis/operational_performance_indicators_research.md`
- Manuscript milestones: root `CHANGELOG.md` (Documentation entries)

---

*Last updated: 2026-04-21 — OPI reframe for Applied Ergonomics, branch `q1-hf-opi-reframe`.*

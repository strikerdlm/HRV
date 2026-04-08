# Author: Dr Diego Malpica MD

## Manuscript workspace — orientation for agents and contributors

**Read this file first** when working under `manuscript/`. It records where the paper sits in the publication pipeline, what is already done, and what remains for a **Q1 scientific journal** submission.

### One-line status

The package is a **submission-oriented draft**: IMRaD scaffold is written, tables (1–6) and Figures 1–4 (SVG) exist, evidence and compliance maps are aligned with a **Node-first (Next.js + FastAPI) + Python biomathematical stack** narrative. **Blocking work is mostly human metadata, venue-specific formatting, and archival reproducibility**—not empty section shells.

---

## Pipeline position (where we are)

| Stage | Status | Notes |
| --- | --- | --- |
| Evidence and scope | Done | `evidence/evidence_matrix.md`, `evidence/validation_story.md`, `evidence/core_modules_scope.md` |
| Main draft (abstract → compliance) | Done | `draft/main_manuscript_scaffold.md` |
| Tables 1–6 | Done | `tables/*.md` including `model_layers_and_evidence_tiers.md` |
| Figures 1–4 + captions | Done | `figures/*.svg`, `figures/figure_plan.md` |
| Supplement / appendix | Done | `supplement/submission_support_appendix.md`, `supplement/supplement_outline.md` |
| Reference seed + MCP notes | Done | `references/seed_references.md`, `references/mcp_research_notes.md` |
| Journal template / final layout | Not started | Depends on target venue |
| Tagged release / archive DOI | Not started | Needed for iron-clad reproducibility statement |
| Final authorship / funding / COI | Not started | Must be confirmed before submission |

**Framing locked in:** primary delivery is **Next.js + TypeScript** over **FastAPI**; **Streamlit** is **secondary**. Claims stay bounded to **engineering verification** and **repository-backed** results unless new empirical studies are added.

---

## Where this is going (target outcome)

- **Goal:** A **Q1** (high-impact / top-quartile in its category) journal article describing the platform as a **translational aerospace-medicine software system** with explicit **biomathematical layering** (HRV analytics, SAFTE/circadian-style dynamics, readiness fusion, environmental timing), not as a single-algorithm paper.
- **Paper type:** Systems / methods / software with operational translation angle—**not** a standalone clinical trial report unless the team later adds that evidence tier.
- **Success criterion:** Reviewers can trace every major claim to **code, tests, or cited literature**, with limitations clearly separated from implementation boasts.

---

## Q1 publication roadmap — future tasks for agents (priority order)

Use this as a checklist; tick items off in repo commits and, where user-visible, in root `CHANGELOG.md` under Documentation.

### A. Venue and packaging (gates everything else)

1. **Shortlist 3–5 Q1 targets** (aerospace medicine, digital health methods, physiological monitoring, or software for science) and record the choice in `outline/manuscript_outline.md` or a short “journal targeting” subsection there.
2. **Download the official author guidelines** and note: word limits, structured abstract rules, reference style, figure file formats (PDF/EPS/TIFF vs SVG), and open-access fees.
3. **Export manuscript** from Markdown into the journal template (Word/LaTeX/Overleaf). Adjust headings, references, and figure callouts to match the template—do not claim template compliance until this is done.

### B. Claims, evidence, and optional empirical lift

1. **Re-audit the draft** against `evidence/evidence_matrix.md` after any code change; downgrade or remove anything that drifts from Supported / Partial tiers.
2. **Decide** whether an exploratory analysis vignette stays in the main paper or moves fully to supplementary material (`validation_story.md` / outline already flag this).
3. **If Q1 expectations require it:** add a minimal **external validation or benchmark** subsection (e.g., public HRV dataset, fatigue model comparison, or structured expert review)—only with clean provenance and IRB/ethics as applicable.

### C. Reproducibility and software citation

1. **Cut a tagged release** (Git tag) that matches the cited commit hash in `tables/reproducibility_and_deployment_metadata.md` and the draft’s availability statement.
2. **Archive** the release (e.g., Zenodo) to obtain a **DOI**; update the manuscript and Table 4 text to match.
3. **Harmonize environment wording** (Python 3.12, `requirements.txt`, frontend `package.json`, optional container instructions) across the draft, supplement, and root `README.md`.

### D. Authorship, ethics, and compliance

1. **Finalize** author list, affiliations, ORCID, CRediT roles, funding, conflicts of interest, and acknowledgments—mirror into `tables/compliance_and_transparency_declarations.md` and the draft compliance section.
2. **Confirm** any ethics/IRB language with real approvals if human data or identifiable records appear; otherwise keep statements accurate and minimal.
3. **Map reporting guidelines** (STROBE / TRIPOD+AI / CLAIM only where predictive claims exist) in one short, honest paragraph—see `supplement/submission_support_appendix.md`.

### E. Editorial polish and submission mechanics

1. **Professional language pass:** tighten redundancy, unify notation for model layers (consistent with Table 6), and ensure Abstract/Discussion do not overclaim regulatory certification.
2. **Figure finalization:** export publication-resolution assets per journal specs; ensure fonts and line weights meet print guidance.
3. **Internal consistency sweep:** abstract ↔ methods ↔ results ↔ table 6 ↔ figures; update hashes and dates only with real git state.
4. **Cover letter + highlights** (if required): 3–5 bullet contributions aimed at the journal’s scope.
5. **Submit** via the journal portal; retain anonymized version if double-masked review is required.

---

## Guardrails (do not skip)

1. **Evidence discipline:** If it is not in the repo (tests, docs, logged outputs) or in a cited paper, it is a **limitation** or **future work**—see `evidence/validation_story.md`.
2. **Regulatory language:** Standards (e.g., NASA, ICAO) are **alignment**, not certification—see `evidence/compliance_and_transparency_map.md`.
3. **No silent scope drift:** Node-first + biomathematical layers are the agreed spine; do not revert to Streamlit-led framing without explicit author direction.
4. **Centralized project docs:** Repository-wide documentation changes belong in root `README.md`, `CHANGELOG.md`, and `docs/Manual.md` per project rules; this file is **manuscript-folder local** except for cross-links.

---

## Folder map

- `outline/` — Framing, titles, section plan, writing order (`manuscript_outline.md`)
- `draft/` — Main manuscript (`main_manuscript_scaffold.md`)
- `tables/` — Tables 1–6 (architecture, literature gap, verification, reproducibility, compliance, model layers)
- `figures/` — SVG figures 1–4 and `figure_plan.md`
- `references/` — Seed bibliography and MCP research log
- `supplement/` — Supplementary outline and submission support appendix
- `evidence/` — Evidence matrix, module scope, validation posture, compliance map

## High-value files (read order for new agents)

1. `outline/manuscript_outline.md` — Thesis, tables/figures index, submission-candidate notes  
2. `evidence/validation_story.md` — What can be claimed vs verified  
3. `draft/main_manuscript_scaffold.md` — Full draft  
4. `tables/model_layers_and_evidence_tiers.md` — Table 6 / model spine  
5. `supplement/submission_support_appendix.md` — Reviewer-facing extensions  
6. `.cursor/plans/scientific_paper_plan_66be74c8.plan.md` — Historical plan and “next writing targets” (do not treat as sole source of truth if this README disagrees; prefer repo state)

## Relation to the rest of the repo

- Service ports and run commands: root `AGENTS.md`  
- Application behavior and features: `docs/Manual.md`, `WARP.md`  
- Manuscript milestones: root `CHANGELOG.md` (Documentation entries)

---

*Last expanded: 2026-04-08 — agent orientation and Q1 roadmap.*

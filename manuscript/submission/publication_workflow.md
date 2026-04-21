# Publication Workflow — OPI Methodology Paper

Author: Dr Diego Malpica MD
Branch: `q1-hf-opi-reframe`
Primary venue: *Applied Ergonomics* (Elsevier, Q1 Human Factors, JIF 3.4)

Workflow elements compatible with any Q1 target, adapted to the Applied Ergonomics primary target. Integrates Zenodo archiving, JOSS parallel track, medRxiv preprint strategy, and repository hygiene that are independent of the venue shortlist.

Venue selection, shortlist, and packaging rationale remain in `manuscript/outline/manuscript_outline.md` and `manuscript/outline/novelty_and_venue_2026-04-21.md`. This file covers the mechanics that apply regardless.

---

## 1. Pre-submission reproducibility and archiving workflow

The Applied Ergonomics submission benefits from — and JOSS requires — a citable software artefact corresponding to the exact reported version. Execute the following steps before submitting the manuscript.

### 1.1 Repository hygiene

1. Add `CITATION.cff` at repository root with software metadata. Use the format Zenodo expects; verify on the GitHub sidebar that the "Cite this repository" button renders.
2. Confirm `LICENSE` at repository root is an OSI-approved licence (MIT already in use at `https://github.com/strikerdlm/HRV` — satisfied).
3. Add an installation-instructions section to root `README.md` with tested commands for the `conda hrv-py312` environment, Python 3.12, `requirements.txt`, and the Next.js frontend build.
4. Add a minimal reproducible example under `analysis/` that takes an RR-interval CSV and emits an OPI output file. The existing `analysis/opi_worked_example.py` script satisfies this requirement for the manuscript's worked example but a minimal generic example may be useful for JOSS reviewers.

### 1.2 GitHub release and Zenodo DOI

1. Tag a semantic version release on `main` after merging `q1-hf-opi-reframe`, for example `v0.6.0-opi`. The tag should correspond exactly to the manuscript-reported version.
2. Enable Zenodo-GitHub integration at `https://zenodo.org/account/settings/github/`; activate the `strikerdlm/HRV` repository.
3. Create a GitHub release from the tag; Zenodo automatically mints a DOI.
4. Cite the **Zenodo Concept DOI** (resolves to latest version) in the manuscript's Data and Code Availability statement and Table 4, rather than the version-specific DOI which would change on subsequent releases.
5. Optional: trigger Software Heritage archival via `save.softwareheritage.org` to generate an SWHID. This is not required for Applied Ergonomics but strengthens reproducibility posture and costs nothing.

### 1.3 Pre-submission checklist

- [ ] `CITATION.cff` present and valid
- [ ] `LICENSE` (MIT) present at repo root
- [ ] `README.md` with installation instructions
- [ ] Tag `v0.6.0-opi` (or equivalent) pushed to `main`
- [ ] Zenodo DOI minted for the tagged release
- [ ] Concept DOI documented in manuscript Section 6.2 and Table 4
- [ ] Software Heritage archival (optional)

---

## 2. Preprint strategy

A preprint posted before Applied Ergonomics submission establishes priority for the OPI framework and avoids any ambiguity about whether related venues (e.g., a parallel JOSS submission, see Section 3) compete with the primary publication.

### 2.1 Preferred server

Post to **medRxiv** in the **Health Informatics** subject area. medRxiv accepts methods and software manuscripts without requiring clinical-trial data and is compatible with all Q1 HF journals that accept preprints, including Applied Ergonomics.

**Fallback:** If medRxiv scope screening fails, re-submit to **arXiv cs.HC** (Human-Computer Interaction). Do not dual-post to both simultaneously; re-post only after formal medRxiv rejection.

### 2.2 Timing

Post the preprint **immediately before** submission to Applied Ergonomics. The Concept DOI from Zenodo (Section 1.2) should be cited in the preprint and in the manuscript's Data and Code Availability statement.

### 2.3 Post-acceptance update

After Applied Ergonomics publication, update the medRxiv metadata with the published DOI. This is best practice, not mandatory.

---

## 3. JOSS parallel submission (optional, recommended)

The Journal of Open Source Software (JOSS) is a zero-APC, DOAJ-indexed, peer-reviewed software journal whose scope matches the OPI reference implementation's delivery stack (Next.js + FastAPI + Python). A JOSS publication cites the software artefact as an independent scholarly contribution and does not compete with the Applied Ergonomics methodology paper.

### 3.1 Scope fit

- **Primary target:** Applied Ergonomics (methodology paper)
- **Software companion:** JOSS (software-as-scholarly-contribution paper)

Both publications are ethically acceptable. JOSS explicitly asks authors to disclose related publications in the Statement of Need. The two papers serve different scholarly functions: Applied Ergonomics publishes the framework and its theoretical grounding; JOSS publishes the reference implementation.

### 3.2 JOSS requirements (all currently satisfied or nearly so)

1. Open-source licence: **MIT — satisfied**.
2. Public repository with tests: **satisfied** (tests under `tests/`).
3. Documentation: installation, API reference, usage examples — **mostly satisfied**; may need a concise `docs/joss/paper.md` short paper.
4. Statement of Need: a 250-word problem statement.
5. Ongoing maintenance signal: recent commits, issue triage, release cadence — **satisfied**.

### 3.3 Workflow

1. Prepare `paper.md` (short paper, ~1,000 words) and `paper.bib` in a `docs/joss/` subdirectory.
2. Submit to JOSS via `https://joss.theoj.org/papers/new` with the GitHub repository URL.
3. JOSS review is GitHub-issue-based and typically takes 6-10 weeks.
4. Accepted JOSS papers get their own DOI on publication.

### 3.4 Ordering

Submit the JOSS paper after the Applied Ergonomics manuscript is accepted (or during revision), so the JOSS Statement of Need can cite the Applied Ergonomics paper as the methodological justification for the software. This avoids a chicken-and-egg problem with "where is the methodology published?" at JOSS review time.

---

## 4. Data and Code Availability statement — Elsevier template

For Applied Ergonomics (Elsevier hybrid), the following statement template applies once the Zenodo DOI has been minted. Drop this into Section 6.2 of the manuscript at submission time, replacing the placeholder.

```
Data Availability:
The single heart-rate-variability recording used for the illustrative
worked example in Section 3.1 is available from the corresponding
author on reasonable request. The JSON artefact containing the full
per-window worked-example outputs is included as Supplementary
Material and is also available at [GitHub URL]/analysis/opi_worked_example.json.

Code Availability:
The reference implementation of the OPI framework is available as
open-source software at https://github.com/strikerdlm/HRV under the
MIT License. The exact software version corresponding to this
manuscript is archived at Zenodo with DOI https://doi.org/10.5281/zenodo.XXXXXXX
(Concept DOI; resolves to the latest archived version). The
reproduction script for the illustrative worked example is
available at [GitHub URL]/analysis/opi_worked_example.py.
```

---

## 5. Graphical abstract

Applied Ergonomics does not require a graphical abstract for research articles, but the journal encourages them for improved discoverability. The content for a graphical abstract is already captured in Figure 1 (OPI conceptual schematic) with minor adaptations. Optional; prepare a 531 × 1328 px version with minimal text for the submission portal if time allows.

---

## 6. Actionable next steps (post-merge)

### Pre-submission (after merging this branch to `main`)

1. [ ] Verify `CITATION.cff` and `LICENSE` at repo root (may need to add `CITATION.cff`)
2. [ ] Tag `v0.6.0-opi` release on `main` matching the submitted manuscript
3. [ ] Enable Zenodo-GitHub integration and mint DOI for the tagged release
4. [ ] Insert the Zenodo Concept DOI into Section 6.2 of `manuscript/draft/opi_main_manuscript.md` and Table 4
5. [ ] Generate Figures 1, 2, 4 at publication quality per `manuscript/figures/figure_plan_opi.md` (Figure 3 is already at 300 dpi PNG + PDF + SVG)
6. [ ] Finalise author metadata (ORCID, affiliations, funding, COI) in Section 6.4-6.5 of the draft

### Submission

7. [ ] Post preprint to medRxiv Health Informatics with the Zenodo DOI cited
8. [ ] Download Applied Ergonomics author guidelines; import into the journal template (Word or LaTeX)
9. [ ] Convert APA7 references to Elsevier's preferred style if different (Applied Ergonomics uses Harvard/APA hybrid)
10. [ ] Submit to Editorial Manager with cover letter, manuscript, Highlights, figures, tables, supplementary material
11. [ ] Track submission ID and first-decision timing (Applied Ergonomics median 79 days)

### Parallel software credit track (optional)

12. [ ] Prepare `docs/joss/paper.md` (~1,000-word short paper) and submit to JOSS after Applied Ergonomics acceptance or during revision

### Post-acceptance

13. [ ] Update medRxiv metadata with the published DOI
14. [ ] Update the Zenodo record with the journal citation

---

*All items in this workflow are independent of the venue shortlist and apply to any Q1 HF / medical / psychology target. Venue choice and rationale are fixed in `manuscript/outline/manuscript_outline.md`.*

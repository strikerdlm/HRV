# JOSS submission package — Mission Control — Flight Surgeon

This directory contains the draft materials for a Journal of Open Source Software (JOSS) submission covering the OPI reference implementation.

## Files

- `paper.md` — JOSS short paper (~1,000 words) with YAML frontmatter
- `paper.bib` — BibTeX references (all DOIs Crossref-verified)

## Submission workflow

See `manuscript/submission/publication_workflow.md` §3 for the full workflow.

Short version:

1. Finalise `paper.md` YAML frontmatter: replace ORCID placeholder and institutional affiliation.
2. Tag a release on the main repo (`v0.6.0-opi`) and mint the Zenodo DOI first.
3. Ensure `CITATION.cff`, `LICENSE` (MIT), `README.md` with installation instructions, and test suite are all present on the tagged release.
4. Submit via `https://joss.theoj.org/papers/new` using the GitHub repository URL. Indicate `paper.md` at `docs/joss/paper.md` in the submission form.
5. JOSS review is GitHub-issue-based; typical turnaround is 6–10 weeks.

## Timing relative to Applied Ergonomics

Submit to JOSS **after** the Applied Ergonomics methodology paper is accepted or well into revision. The JOSS Statement of Need cites the Applied Ergonomics paper as the methodological justification for the software. Dual submission is ethically acceptable; JOSS explicitly asks authors to disclose related publications.

## Pre-flight checklist

- [ ] `paper.md` frontmatter complete (ORCID, affiliation, date)
- [ ] `paper.bib` complete with all cited references
- [ ] Paper word count between 250 and 1,000 words
- [ ] Statement of Need clearly describes the problem and target audience
- [ ] Summary section covers functionality
- [ ] License file present at repo root (MIT — satisfied)
- [ ] `CITATION.cff` present at repo root (pending — see manuscript/submission/publication_workflow.md §1.1)
- [ ] Installation instructions in root `README.md`
- [ ] Tests passing (existing `tests/` suite)
- [ ] Zenodo DOI minted and cited in `paper.md` references (pending release)

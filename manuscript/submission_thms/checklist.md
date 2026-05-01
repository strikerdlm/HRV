# IEEE THMS submission checklist

Pre-flight before pressing submit on `https://mc.manuscriptcentral.com/thms`.

## A. Manuscript file

- [ ] Title shortened to ≤16 words and includes "human-machine systems"
- [ ] Running title ≤50 characters
- [ ] Abstract 100–250 words (target 200)
- [ ] 5–6 IEEE thesaurus keywords
- [ ] RQ1, RQ2, RQ3 explicitly stated in §1.4 (or end of §1.3)
- [ ] Word count of main text ≤ 6,000
- [ ] LaTeX two-column compile fits within **10 IEEE Transactions pages** including figures, tables, references, but excluding photos/bios at submission stage
- [ ] No code blocks in main text — pseudocode only
- [ ] All references in IEEE numbered style
- [ ] Reference count ≤ 60
- [ ] Equation numbering IEEE-compliant
- [ ] Figures: 3 in main text, vector format where possible, ≥600 dpi raster
- [ ] Tables: ≤4 in main text, IEEE format
- [ ] Author photos and bios drafted (required at acceptance — can be deferred at first submission)
- [ ] AI-assistance disclosure paragraph retained in Acknowledgements

## B. Supplement file

- [ ] All cut code blocks captured
- [ ] Engineering verification matrix (full Table 5)
- [ ] Reproducibility and deployment metadata (full Table 6)
- [ ] Compliance and reporting-guideline positioning details (full Table 7 / §6.6)
- [ ] Reference implementation reference card with frozen GitHub release tag and Zenodo DOI
- [ ] Vigilance and latency derivation appendices
- [ ] Per-task weight derivation tables in full

## C. Cover letter

- [ ] Addressed to Prof. Ljiljana Trajkovic, Editor-in-Chief
- [ ] Includes research questions
- [ ] Maps contribution to THMS scope (cognitive ergonomics; system test and evaluation; human-machine systems)
- [ ] Prior-submission disclosure paragraph
- [ ] Authorship and corresponding-author identification
- [ ] Conflict-of-interest declaration
- [ ] AI-assistance declaration
- [ ] Mentions 6 suggested reviewers (entered in portal form)

## D. ScholarOne portal entries

- [ ] Manuscript type: **Regular Paper**
- [ ] Title and abstract pasted
- [ ] Both authors entered with ORCIDs (Diego 0000-0002-2257-4940, Ingrid 0000-0002-7981-2356)
- [ ] Diego marked corresponding author
- [ ] Affiliations correct (DIMAE; CITAE)
- [ ] 6 suggested reviewers entered: name + email + affiliation + URL
  - [ ] None is a current THMS Associate Editor
  - [ ] None is a co-author within last 3 years
  - [ ] Spans ≥3 countries
- [ ] Cover letter pasted in cover-letter field
- [ ] Main manuscript PDF uploaded
- [ ] Supplement PDF uploaded
- [ ] Code/video/data attachments uploaded if any
- [ ] No PDF/PostScript files used as **source** files (Word or LaTeX source only — relevant at acceptance)

## E. Mandatory declarations

- [ ] ORCID linked for both authors
- [ ] Funding statement present
- [ ] CRediT author-contribution statement present
- [ ] Data availability statement present
- [ ] Code availability statement (with archival DOI) present
- [ ] Ethics statement (no human-subjects measurement requiring IRB; or appropriate IRB reference if recording counts as human-subjects research)
- [ ] AI-assistance declaration present
- [ ] Conflict-of-interest declaration present

## F. Co-author sign-off

- [ ] Ingrid Bejarano has reviewed the THMS-revised manuscript
- [ ] Ingrid has approved the venue change from Applied Ergonomics to IEEE THMS
- [ ] Ingrid has reviewed and approved the cover letter

## G. Local repository hygiene

- [ ] Tag created: `git tag rejected-AE-2026-04-30`
- [ ] Branch: `thms-revision`
- [ ] CHANGELOG entry added for the revision
- [ ] `manuscript/CLAUDE.md` updated to reflect THMS as the active target (replace Applied Ergonomics references)
- [x] ~~`manuscript/outline/manuscript_outline.md` venue-targeting section updated~~ — outline retired with the AE-era working folders (2026-04-30 cleanup)

## G2. Verification before sending

- [ ] **Editor-in-Chief currency.** Confirm Ljiljana Trajkovic is still the THMS Editor-in-Chief on submission day at https://www.ieeesmc.org/publications/transactions-on-human-machine-systems/ — masthead changes happen and an outdated salutation in the cover letter is a small but avoidable signal.
- [ ] **Plagiarism self-check.** Run the manuscript through the institutional plagiarism tool (or a free service such as iThenticate via library access) before upload — IEEE screens automatically and you want to see what they will see.
- [ ] **Self-overlap check against open-source repository.** Determine whether the public GitHub repo describes the OPI framework in enough detail that THMS' plagiarism screen flags self-overlap. If material overlap exists, name the repo URL explicitly in the cover letter prior-disclosure paragraph.
- [ ] **Antarctic-campaign mention count.** Across the manuscript and cover letter combined, the Antarctic 2026–2027 campaign should appear **once**, briefly, as motivation for the validation roadmap. Search the rendered document for "Antarctic" and verify count.
- [ ] **Cover-letter variant chosen.** Either Variant A (conservative-truthful) or Variant B (full disclosure) — not both, not the original false statement.

## H. Post-submission

- [ ] Confirmation email and ScholarOne reference number archived in `manuscript/submission_thms/`
- [ ] Calendar reminder set for **+10 weeks** to follow up on first decision if silent
- [ ] Diego notified Ingrid of submission with reference number
- [ ] Local memory note created: `/root/.openclaw/workspace/memory/2026-MM-DD.md` with submission record

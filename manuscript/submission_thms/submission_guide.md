# IEEE THMS — Submission Guide

**Target:** IEEE Transactions on Human-Machine Systems (THMS) — IEEE SMC Society
**Editor-in-Chief:** Ljiljana Trajkovic, Simon Fraser University
**Submission portal:** https://mc.manuscriptcentral.com/thms (ScholarOne)
**Review model:** Single-anonymous · two reviewers minimum · ~10-week first-decision target
**Publication frequency:** Bimonthly (Feb · Apr · Jun · Aug · Oct · Dec)
**Cost (traditional submission):** **$0 APC.** No fee unless the author opts into open access at acceptance ($2,195 hybrid OA, optional). Voluntary post-acceptance page charge $110/page. Mandatory overlength surcharge $220/page beyond the cap.

---

## 1. Manuscript format — non-negotiable

| Item | Rule | Source |
|---|---|---|
| File format | PDF or PostScript for review; final source file in **Word or LaTeX** (no PDF/PS for source) | THMS Information for Authors |
| Layout | **IEEE Transactions two-column**, 8.5 × 11 in | THMS IfA |
| Language | English only — papers not in English are withdrawn | THMS IfA |
| Spacing (review draft) | Double-spaced or IEEE format acceptable | THMS Information for Accepted Papers |
| Reference style | **IEEE numbered style** (alphabetical or order-of-use, numbered) | IEEE Style Manual |
| Equations | IEEE numbering, displayed equations on separate lines | IEEE Style Manual |
| Figures | Sharp, noise-free, high contrast. Use **patterns over colour** unless paying for colour. Lettering legible at 4:1 reduction. One illustration per page. | THMS IfA |
| Captions | On a separate page from figures | THMS IfA |

**LaTeX template:** IEEEtran.cls, two-column, 10pt — `\documentclass[10pt,journal,twocolumn]{IEEEtran}`. Available from `https://www.ieee.org/conferences/publishing/templates.html`.

**Word template:** IEEE Transactions two-column template — same source.

---

## 2. Length limits (the binding constraint)

| Article type | Max length | Notes |
|---|---|---|
| **Regular paper** | **10 IEEE Transactions pages** | Includes author photos and biographies if provided. **This is your target.** |
| Technical correspondence | 5 pages | Short formats, not for this manuscript |
| Survey paper | 15 pages | Doesn't apply — OPI is not a survey |
| Overlength | $220/page surcharge | Editor-in-Chief approval required *in advance* of submission for additional pages |

**Page-to-word conversion (IEEE two-column).** A 10-page IEEE Transactions paper typically holds:
- Body prose: ~5,500–6,000 words
- 4–6 figures: ~1.5–2 pages of footprint
- 2–3 tables: ~0.5–1 page
- ~40–60 references: ~1–1.5 pages

**Working budget for the OPI manuscript revision:** **5,500–6,000 words main text** + figures + tables + ≤60 references, all fitting within 10 IEEE pages.

The current manuscript at `submission_package/01_manuscript/manuscript.md` is ~7,800 words. **Cut target: ~25–30%.**

---

## 3. Abstract and front matter

| Item | Rule |
|---|---|
| **Abstract** | **100–250 words.** Currently ~245 — within budget but tight; trim to ~200 to leave room. |
| Index Terms (keywords) | IEEE thesaurus terms preferred. Currently ~3 keywords; expand to 5–6. |
| Author photos/bios | Required for accepted version, count against the 10-page limit |
| Graphical abstract | Accepted, peer-reviewed — optional |
| Video abstract | Encouraged; hosted via SMC Society Resource Center |

---

## 4. Reviewer suggestions (mandatory)

The cover letter must **suggest 6 reviewers**. Constraints:
- Cannot be current THMS Associate Editors
- Cannot have co-authored with you in the past 3 years
- Should span affiliations and continents

Existing list at `submission_package/08_suggested_reviewers/` was built for Applied Ergonomics. Audit and rebuild to favour HMS / cognitive ergonomics / aerospace operator-state engineering reviewers (drop pure ergonomics-theory names; add IEEE THMS / IEEE TSMC / aerospace human factors authors). Target list to seed from: Wickens, Parasuraman heirs, Endsley collaborators, Chen (teleoperation), Warm-tradition vigilance researchers, Salas (team cognition), Hancock (workload), Lee (trust in automation), and active THMS publishing labs.

---

## 5. Mandatory declarations

| Declaration | Required by THMS | Required by IEEE | Source |
|---|---|---|---|
| ORCID for all authors | Yes | Yes | IEEE policy — both authors already have ORCIDs |
| IEEE Copyright Form | At acceptance | Yes | IEEE policy |
| Prior publication / preprint disclosure | In cover letter | Yes | THMS IfA |
| Plagiarism screening | Automatic at submission | Yes | THMS IfA |
| AI/LLM disclosure | **Not explicitly stated by THMS**, but IEEE policy requires disclosure of generative AI use in manuscript preparation in the Acknowledgements; preserve the existing AI declaration paragraph from `submission_package/04_declarations/` | IEEE generative AI policy 2023 |
| Conflicts of interest | IEEE general requirement | Yes | IEEE policy |
| Funding statement | IEEE general requirement | Yes | IEEE policy |
| Author contributions (CRediT) | Recommended, not required by THMS specifically | Encouraged | — |
| Data availability | Recommended for IEEE; required if data is the contribution | Encouraged | — |
| Ethics statement | If human-subjects data | Required | — |

For OPI: there are no human-subjects measurements requiring IRB approval (the 128-min HRV recording is an illustrative worked example from the PI's own data — confirm IRB framing in your existing declarations file is consistent).

---

## 6. Supplementary material policy

THMS **encourages** code, data, video, and other artefacts. Direct quote: *"video, animations, applets, code, data, etc."* — referenced in the text. This is the right venue for the OPI MIT-licensed reference implementation.

Recommended structure:
- Frozen GitHub release with archival DOI (Zenodo) — cite in main text
- Brief code description in supplementary, not in main text
- Engineering verification details and worked-example walkthrough → supplement
- Per-task weight derivation tables → supplement
- Main text retains: framework definition, illustrative worked example summary, Discussion

---

## 7. Submission portal walkthrough (ScholarOne)

URL: `https://mc.manuscriptcentral.com/thms`

Step 1. **Account.** Use existing IEEE account or register; ensure ORCID is linked.
Step 2. **Manuscript type.** Select "Regular Paper" (NOT Technical Correspondence, NOT Survey).
Step 3. **Title, authors, affiliations.** Enter both authors with ORCIDs. Diego = corresponding author.
Step 4. **Abstract.** Paste 200-word abstract.
Step 5. **Keywords.** 5–6 IEEE thesaurus terms.
Step 6. **Cover letter.** Paste from `cover_letter_template.md`. Disclose preprint/prior submission posture.
Step 7. **File upload.** Order: (1) main manuscript PDF (single-column allowed for review, but two-column recommended), (2) supplementary material PDF, (3) any code/video files, (4) signed copyright form (collected post-acceptance).
Step 8. **Suggested reviewers.** 6 names with affiliation + email + URL.
Step 9. **Confirm and submit.** ScholarOne emails confirmation and reference number.

---

## 8. Decision categories (THMS)

- **Accept** (rare on first round)
- **Minor revision** — typically 2–6 weeks to revise
- **Major revision** — typically 8–12 weeks to revise
- **Reject and resubmit as new** — substantial reframe needed
- **Reject** — out of scope or fundamental issues

Median first-round outcome at THMS for a methodology paper is **major revision**. Plan for it.

---

## 9. Review timeline (target)

| Stage | THMS target |
|---|---|
| Submission → Editor-in-Chief assigns Associate Editor | ~1–2 weeks |
| AE assigns reviewers | ~1–3 weeks |
| Reviewers complete | ~6–10 weeks |
| First decision communicated | **~10 weeks total** |
| Major revision turnaround (author) | 60–90 days |
| Second-round review | 4–8 weeks |
| Final decision | typically ~6–9 months end-to-end |

---

## 10. Specific guidance for the OPI manuscript

THMS' scope is essentially the OPI manuscript's scope, restated: *"human systems and human organizational interactions including cognitive ergonomics, system test and evaluation, and human information processing concerns in systems and organizations."* Frame your gap and contribution against this scope explicitly in the introduction.

The Editor-in-Chief Ljiljana Trajkovic's research is in network/system dynamics — not aerospace HF specifically. Expect the manuscript to be assigned to an Associate Editor with cognitive ergonomics, human-AI teaming, or human-machine teaming expertise. Major-revision likelihood is high; outright rejection at AE-stage less likely than at AE because the format expects framework papers.

**Things to *add* for THMS that were not emphasized at AE:**
- Reframe section 4 as a **Human-Machine System integration discussion**: how OPI sits as substrate for downstream classifier composition, audit trails, and human-AI teaming workflows.
- Add a brief section on **inspectability / safety review traceability** of the linear composite — IEEE THMS reviewers value this where pure-HF venues do not.
- Strengthen the teleoperation/UAS sections — they map directly onto THMS' active topic mix.

**Things to *cut/move* for THMS:**
- Code blocks → supplement
- Engineering verification matrix detail → supplement
- Compliance and Transparency subsections beyond data/code availability → supplement appendix
- Prior-section walkthrough text duplicating tables → drop

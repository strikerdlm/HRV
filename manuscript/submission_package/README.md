# Applied Ergonomics submission package

**Manuscript:** *Task-calibrated Operational Performance Indicators for aviation and unmanned aircraft system operators: a biomathematical framework integrating SAFTE fatigue, heart-rate variability, and cognitive-load theory, with open-source reference implementation*

**Authors:** Diego L. Malpica MD (corresponding) · Ingrid Xiomara Bejarano Cifuentes
**Target journal:** Applied Ergonomics — Elsevier — Editorial Manager portal `https://www.editorialmanager.com/JERG`
**Article type:** Research Article (3,000–5,000 words)
**Build date:** 2026-04-29
**Compliance:** all hard rules satisfied — see `09_compliance/PortalCompliance.md`

---

## Editorial Manager upload map

Upload these files in this order at `https://www.editorialmanager.com/JERG`:

| Editorial Manager slot | File to upload |
|---|---|
| Cover Letter | `03_cover_letter/CoverLetter.docx` |
| Manuscript | `01_manuscript/Manuscript.docx` *(or `Manuscript.pdf` if Word fails)* |
| Highlights | `02_highlights/Highlights.docx` |
| Declaration of Competing Interests | `04_declarations/DeclarationOfCompetingInterests.docx` *(replace with the official Elsevier `.docx` template if the portal requires it)* |
| AI-use declaration | text already in manuscript before References; copy-paste into the portal field if asked, or upload `04_declarations/AI_Use_Declaration.docx` |
| Suggested Reviewers | enter five entries from `08_suggested_reviewers/SuggestedReviewers.md` |
| Supplementary Material *(optional)* | `07_supplement/SupplementaryAppendix.docx`; `06_tables/Tables_1-5.docx` *(only if the editor requests separated tables)* |
| Figures *(initial submission — embedded in manuscript)* | none needed for initial review; for revision after acceptance, upload each figure from `05_figures/` separately |

> **"Your Paper Your Way":** the journal accepts a single combined Word/PDF for the initial review. The Manuscript file already has all four figures and their captions embedded. Strict file separation is only required at the revision stage.

---

## Authors

| Order | Name | Role | Affiliation | E-mail | ORCID |
|---|---|---|---|---|---|
| 1 | **Diego L. Malpica MD** | PI; corresponding | Aerospace Medicine — Subdirectorate of Aerospace Sciences; Direction of Aerospace Medicine (DIMAE); Colombian Aerospace Force; Bogotá, Colombia | diego.malpica@fac.mil.co | https://orcid.org/0000-0002-2257-4940 |
| 2 | **Ingrid Xiomara Bejarano Cifuentes** | Researcher | Centro de Investigación y Desarrollo de Tecnologías Aeroespaciales (CITAE); Colombian Aerospace Force; Bogotá, Colombia | ingrid.bejarano@fac.mil.co | https://orcid.org/0000-0002-7981-2356 |

---

## Suggested reviewers (verified institutional emails)

1. **Christopher A. Stevens** — AFRL 711th HPW, Wright-Patterson AFB — `christopher.stevens.28@us.af.mil` (NRC RAP listing)
2. **Frédéric Dehais** — ISAE-SUPAERO, Toulouse — `frederic.dehais@isae.fr` (Drexel BME affiliated faculty page)
3. **Jaime K. Devine** — Institutes for Behavior Resources, Baltimore — `jdevine@ibrinc.org` (PMC corresponding-author block)
4. **Oleksandra (Olivia) Molloy** — UNSW Canberra — `o.molloy@unsw.edu.au` (UNSW media expert list)
5. **Hussein A. Abbass** — UNSW Canberra — `h.abbass@unsw.edu.au` (UNSW staff profile)

Full rationales and source URLs in `08_suggested_reviewers/SuggestedReviewers.md`.

---

## Pre-submission checklist (run through these before clicking Submit)

- [ ] Confirm Diego's full courier-style postal address on the title page.
- [ ] Cut a tagged release on `https://github.com/strikerdlm/HRV` (e.g. `v0.6.0-opi`) and deposit to Zenodo. Paste the Concept DOI into:
  - `01_manuscript/manuscript.md` §6.2 *(Code and artefact availability)*
  - `03_cover_letter/CoverLetter.md` *(Data and code availability)*
  - regenerate the `.docx` and `.pdf` afterwards.
- [ ] Re-verify each suggested reviewer's email by opening their institutional homepage.
- [ ] Verify no suggested reviewer is currently on the Applied Ergonomics editorial board (page on Elsevier's site).
- [ ] On the Editorial Manager system-PDF proof, check: author names visible (NOT anonymised — single-anonymized review), abstract on its own page within 150 words, ≤3 keywords, 5 highlight bullets, all four figures present and cited, references in author-date format.

---

## Compile commands

```bash
# Manuscript .docx (figures embedded)
sed 's|\.\./05_figures/|/root/.openclaw/workspace/hrv/HRV/manuscript/submission_package/05_figures/|g; s|\.\./figures/|/root/.openclaw/workspace/hrv/HRV/manuscript/submission_package/05_figures/|g' \
    01_manuscript/manuscript.md > /tmp/_pandoc_input.md
pandoc /tmp/_pandoc_input.md -o 01_manuscript/Manuscript.docx --from=markdown+pipe_tables --to=docx

# Manuscript .pdf
pandoc /tmp/_pandoc_input.md -o 01_manuscript/Manuscript.pdf --pdf-engine=xelatex \
  -V geometry:margin=1in -V mainfont="DejaVu Serif" -V monofont="DejaVu Sans Mono" \
  -V fontsize=11pt -V linestretch=1.5

# Sidecars
pandoc 02_highlights/Highlights.md   -o 02_highlights/Highlights.docx
pandoc 03_cover_letter/CoverLetter.md -o 03_cover_letter/CoverLetter.docx
pandoc 04_declarations/DeclarationOfCompetingInterests.md -o 04_declarations/DeclarationOfCompetingInterests.docx
pandoc 04_declarations/AI_Use_Declaration.md -o 04_declarations/AI_Use_Declaration.docx
pandoc 08_suggested_reviewers/SuggestedReviewers.md -o 08_suggested_reviewers/SuggestedReviewers.docx
```

---

## Re-run compliance check

```bash
python3 -c "
import re
text = open('01_manuscript/manuscript.md').read()
body = text.split('## 1. Introduction',1)[1].split('## 6. Compliance and Transparency',1)[0]
body = re.sub(r'\`\`\`.*?\`\`\`','',body,flags=re.S)
body = re.sub(r'!\[.*?\]\(.*?\)','',body)
body = re.sub(r'^\*\*Figure \d+\.\*\*.*$','',body,flags=re.M)
print('body words:', len(re.findall(r\"[A-Za-z][A-Za-z'\-]*\", body)))
abs_block = text.split('## Abstract',1)[1].split('### Keywords',1)[0]
print('abstract words:', len(re.findall(r\"[A-Za-z][A-Za-z'\-]*\", abs_block)))
"
```

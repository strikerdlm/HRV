# Author: Dr Diego Malpica MD

## MCP Research Notes

This file records the manuscript-development research performed through the configured MCP servers and related tools.

## Server coverage

| Source | Status | What it was used for |
| --- | --- | --- |
| `user-paper-search` | Successful | PubMed and Crossref searches for comparator systems, aviation fatigue monitoring, circadian and wearable methods, and reporting-guideline papers. |
| `user-scite` | Successful | Citation-context retrieval, full-text excerpts, and retraction-aware checks for key papers and reporting guidelines. |
| `user-zotero` | Partially successful | Confirmed relevant items in the local Zotero library; one metadata search succeeded, some search modes timed out or were unsupported, and one full-text lookup returned not found. |
| `user-brave` | Successful | Official technical and standards-document discovery for NASA-STD-3001, ICAO Doc 9966, and EQUATOR guidance. |
| `user-firecrawl` | Blocked | `firecrawl_search` returned `Unauthorized: Invalid token`, so no usable Firecrawl MCP results were available in this session. |
| `tavily` | Not configured as MCP | No Tavily MCP server is available in this workspace. |

## Key scientific sources recovered with `paper-search`

### Comparator and systems papers

- Tarvainen, M. P., Niskanen, J.-P., Lipponen, J. A., Ranta-aho, P. O., & Karjalainen, P. A. (2014). *Kubios HRV - Heart rate variability analysis software*. *Computer Methods and Programs in Biomedicine, 113*(1), 210-220. https://doi.org/10.1016/j.cmpb.2013.07.024
- Christie, I. C., & Gianaros, P. J. (2013). *PhysioScripts: An extensible, open source platform for the processing of physiological data*. *Behavior Research Methods, 45*(1), 125-131. https://doi.org/10.3758/s13428-012-0233-x
- Rogers, B., Murias, J. M., & Fleitas-Paniagua, P. R. (2025). *Validity of an open-source mobile app to measure fractal correlation properties of heart rate variability during exercise*. *European Journal of Applied Physiology*. https://doi.org/10.1007/s00421-025-06037-0
- Arney, D., Zhang, Y., Kennedy-Metz, L. R., Dias, R. D., Goldman, J. M., & Zenati, M. A. (2023). *An open-source, interoperable architecture for generating real-time surgical team cognitive alerts from heart-rate variability monitoring*. *Sensors, 23*(8), 3890. https://doi.org/10.3390/s23083890
- Bowman, C., Huang, Y., Walch, O. J., Fang, Y., Frank, E., Tyler, J., Mayer, C., Stockbridge, C., Goldstein, C., Sen, S., & Forger, D. B. (2021). *A method for characterizing daily physiology from widely used wearables*. *Cell Reports Methods, 1*(4), 100058. https://doi.org/10.1016/j.crmeth.2021.100058
- Hursh, S. R., Balkin, T. J., Miller, J. C., & Eddy, D. R. (2004). *The Fatigue Avoidance Scheduling Tool: Modeling to minimize the effects of fatigue on cognitive performance*. *SAE Technical Paper Series*. https://doi.org/10.4271/2004-01-2151

### Aviation, fatigue, and circadian monitoring

- Devine, J. K., & Hursh, S. R. (2025). *A narrative review on in-flight use of consumer sleep technologies for aviation research*. *Sleep Advances*. https://doi.org/10.1093/sleepadvances/zpaf076
- Morris, M. B., Howland, J. P., Amaddio, K. M., & Gunzelmann, G. (2020). *Aircrew fatigue perceptions, fatigue mitigation strategies, and circadian typology*. *Aerospace Medicine and Human Performance, 91*(4), 363-368. https://doi.org/10.3357/AMHP.5396.2020
- Yang, S. X., Cheng, S., Sun, Y., Tang, X., & Huang, Z. (2024). *Circadian disruption in civilian airline pilots*. *Aerospace Medicine and Human Performance*. https://doi.org/10.3357/AMHP.6316.2024
- Hartmeyer, S. L., Phillips, N. E., Jassil, F. C., Joris, C., Dibner, C., Collet, T. H., & Andersen, M. (2025). *Multi-wearable approach for monitoring diurnal light exposure and body rhythms in nightshift workers*. *Acta Physiologica*. https://doi.org/10.1111/apha.70069

### Space-weather and autonomic physiology

- Alabdulgader, A., McCraty, R., Atkinson, M., Dobyns, Y., Vainoras, A., Ragulskis, M., & Stolc, V. (2018). *Long-term study of heart rate variability responses to changes in the solar and geomagnetic environment*. *Scientific Reports, 8*(1), 2663. https://doi.org/10.1038/s41598-018-20932-x
- Gaisenok, O., Gaisenok, D., & Bogachev, S. (2025). *The influence of geomagnetic storms on the risks of developing myocardial infarction, acute coronary syndrome, and stroke: Systematic review and meta-analysis*. https://doi.org/10.4103/jmp.jmp_122_24

### Reporting-guideline sources

- von Elm, E., Altman, D. G., Egger, M., Pocock, S. J., Gotzsche, P. C., & Vandenbroucke, J. P. (2007). *The Strengthening the Reporting of Observational Studies in Epidemiology (STROBE) statement: Guidelines for reporting observational studies*. *PLoS Medicine, 4*(10), e296. https://doi.org/10.1371/journal.pmed.0040296
- TRIPOD+AI Consortium. (2024). *TRIPOD+AI statement: updated guidance for reporting clinical prediction models that use regression or machine learning methods*. *BMJ*, q902. https://doi.org/10.1136/bmj.q902
- Mongan, J., Moy, L., & Kahn, C. E. (2020). *Checklist for Artificial Intelligence in Medical Imaging (CLAIM): A guide for authors and reviewers*. *Radiology: Artificial Intelligence, 2*(2), e200029. https://doi.org/10.1148/ryai.2020200029

## Key findings from `scite`

### OpenICE / Arney et al. (2023)

Most useful finding for the manuscript:

> The prototype was designed to verify the system architecture and data pipeline, not to validate the HRV or cognitive-load algorithms themselves.

This is highly relevant to the present manuscript because it supports a defensible distinction between **architecture verification** and **algorithmic or clinical validation**.

### Kubios / Tarvainen et al. (2014)

Most useful finding for the manuscript:

> Kubios is centered on advanced HRV analysis, preprocessing, artifact correction, configurable analysis settings, and report export.

This supports positioning Kubios as a strong comparator for HRV analysis, but not as an integrated operational physiology platform.

### Alabdulgader et al. (2018)

Most useful findings for the manuscript:

- The study used repeated HRV recordings over time rather than isolated one-off measurements.
- The authors explicitly handled multiplicity across lags and variables.

This supports the manuscript’s rationale for lag-aware environmental analysis and conservative statistical governance.

### STROBE and CLAIM

Useful excerpts recovered through `scite` emphasize:

- transparent reporting as a prerequisite for critical appraisal and synthesis,
- explicit description of data partitions, evaluation data, demographics, and validation pathways when AI or predictive modules are reported.

## Key findings from `zotero`

### Successful metadata result

- `Kubios HRV - Heart rate variability analysis software`
  - Zotero key: `6E56DBAC`
  - Tags: `Analysis software`, `Computer program`, `HRV`, `Heart rate variability`, `Matlab`

### Successful tag-based results

- McCraty et al. (2017). *Synchronization of Human Autonomic Nervous System Rhythms with Geomagnetic Activity in Human Subjects*
- Arsintescu et al. (2019). *Validation of a touchscreen psychomotor vigilance task*
- Pagel & Choukèr (2016). *Effects of isolation and confinement on humans-implications for manned space explorations*

These Zotero results are useful because they match the manuscript’s three translational axes:

- autonomic and geomagnetic coupling,
- fatigue and vigilance measurement,
- isolated and confined operational environments relevant to spaceflight analogs.

### Zotero limitations encountered

- `search_zotero_abstracts` timed out in `everything` mode for broad queries.
- `search_zotero_abstracts` rejected `quick` mode as an invalid `qmode`.
- `get_zotero_fulltext` returned `404 Not found` for the Kubios item key.

## Official technical documentation found with `brave`

### NASA

- NASA-STD-3001 Volume 1 standards page:
  - `https://standards.nasa.gov/standard/NASA/NASA-STD-3001_VOL_1`
- NASA-STD-3001 Volume 1 PDF:
  - `https://www.nasa.gov/wp-content/uploads/2020/10/2022-01-05_nasa-std-3001_vol.1_rev._b_final_draft_with_signature_010522.pdf`
- NASA-STD-3001 Volume 2 standards page:
  - `https://standards.nasa.gov/standard/NASA/NASA-STD-3001_VOL_2`

### ICAO

- ICAO Doc 9966 landing page:
  - `https://www.icao.int/publications/doc-9966-includes-complete-set-fatigue-management-implementation-manuals`
- ICAO Doc 9966 PDF:
  - `https://www2023.icao.int/safety/fatiguemanagement/FRMS%20Tools/Doc%209966.FRMS.2016%20Edition.en.pdf`

### EQUATOR

- Reporting guidelines index:
  - `https://www.equator-network.org/reporting-guidelines/`
- Reporting-guideline selection resource:
  - `https://www.equator-network.org/toolkits/selecting-the-appropriate-reporting-guideline/`

## Firecrawl status

Attempted MCP call:

- `user-firecrawl.firecrawl_search`

Observed result:

- `Unauthorized: Invalid token`

Interpretation:

- Firecrawl is configured as an MCP server in the workspace, but it is not currently usable for manuscript research in this session.
- The manuscript-development record should therefore note that Firecrawl was attempted but unavailable because of authentication failure.

## Drafting implications

1. Use `paper-search` and `scite` as the primary evidence base for the Introduction and reporting-guideline rationale.
2. Use `zotero` results to prioritize library-backed references on HRV, vigilance, geomagnetic coupling, and space analogs.
3. Use `brave` results for official NASA, ICAO, and EQUATOR documentation in Methods, Discussion, and compliance sections.
4. Do not cite Firecrawl-derived content in the manuscript unless the token issue is resolved and successful results are collected in a later session.

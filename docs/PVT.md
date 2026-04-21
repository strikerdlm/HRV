# Psychomotor Vigilance Task (PVT) — platform guide

**Author:** Dr Diego Malpica MD
**Status:** active (added 2026-04-21)

## What it is

The Psychomotor Vigilance Task (PVT) is a simple sustained-attention reaction-time test originally developed by Dinges and Powell (1985) and validated extensively for assessing neurobehavioural impairment from sleep loss. The operator sees a millisecond counter appear at random intervals and must press a key as quickly as possible. Lapses (RT ≥ 500 ms standard, 355 ms for the 3-min variant), false starts, mean RT, and reciprocal-RT (1/RT) are the canonical outcome metrics.

This platform ships three variants and two administration surfaces (browser + PsychoPy desktop). All variants share the same canonical Python scoring module (`app/pvt_core.py`).

## Variants

| Variant  | Duration | ISI range  | Lapse threshold | Primary use case |
|----------|----------|------------|-----------------|------------------|
| PVT-B    | 3 min    | 1 – 4 s    | 355 ms          | Pre-flight / shift-check — operational gate |
| PVT-5    | 5 min    | 2 – 10 s   | 500 ms          | Routine longitudinal research tracking |
| PVT-10   | 10 min   | 2 – 10 s   | 500 ms          | Gold-standard reference duration (Dinges 1997) |

The PVT-B 3-minute duration and 355 ms lapse threshold come from Basner & Dinges (2011, *Sleep* 34(5):581–591, DOI 10.1093/sleep/34.5.581). Grant et al. (2017, *Behav Res Methods* 49(3):1020–1029, DOI 10.3758/s13428-016-0763-8) further validated a 3-min smartphone/tablet PVT against the 10-min laptop standard across 38 hours of total sleep deprivation.

## Administration surfaces

### Browser (primary — operational + research)

Components and routes:

| Purpose       | Path | Notes |
|---------------|------|-------|
| React component | `frontend/src/components/pvt/pvt-test.tsx` | Keyboard + touch; configurable variant, seed, minimal mode |
| TS scoring     | `frontend/src/lib/pvt-scoring.ts` | Mirrors `app/pvt_core.py`; identical metric definitions |
| Operational route | `frontend/src/app/scheduling/pvt/page.tsx` | Fixed PVT-B; feeds `pvt_lapses_3min` to readiness pipeline |
| Research route | `frontend/src/app/research/pvt/page.tsx` | Variant selector; history table; defaults to PVT-5 |

**Timing precision.** Browser-based RT measurement via `performance.now()` achieves approximately 5–10 ms precision on modern hardware (Anwyl-Irvine et al. 2020, *Behav Res Methods* 53:1407–1425, DOI 10.3758/s13428-020-01501-5, using a robot-actuator benchmarking methodology). This is adequate for:

- Operational GO / NO-GO decisions (which are gated on lapse counts, not individual RT values)
- Longitudinal within-operator tracking (relative change is far more stable than absolute millisecond timing)
- Research applications where research-grade timing is not a hard requirement

It is **not** adequate for:

- Lab-grade absolute RT claims requiring sub-millisecond precision
- Cross-platform RT comparisons where different displays / input devices confound raw RT values
- Publishing claims about RT distributional properties (ex-Gaussian parameters etc.) where even small timing noise distorts the tail

### PsychoPy desktop (research-grade alternative)

File: `app/pvt_desktop.py`

Install: `pip install psychopy>=2024.1` (recommended: dedicated conda env per module docstring).

Run:

```bash
python app/pvt_desktop.py --variant PVT-B --user <operator-id>
python app/pvt_desktop.py --variant PVT-5 --out session.json
python app/pvt_desktop.py --variant PVT-10 --post http://localhost:8180/api/pvt/sessions
```

PsychoPy has been independently validated for sub-millisecond stimulus timing precision (Garaizar & Vadillo 2014, *PLoS ONE* 9(11):e112033, DOI 10.1371/journal.pone.0112033). It is the open-source research-grade choice when browser precision is insufficient.

The desktop driver shares `app/pvt_core` scoring with the browser variant — there is one canonical scoring implementation for both surfaces.

## Backend

### Scoring module

`app/pvt_core.py` is the single source of truth for PVT scoring. It is:
- Imported by the FastAPI endpoints (server-side canonical scoring)
- Mirrored by `frontend/src/lib/pvt-scoring.ts` (client-side preview)
- Used by `app/pvt_desktop.py` (desktop driver)

Do not add metric definitions anywhere else. If a metric needs changing, change it here and propagate to the TS mirror with bit-for-bit equivalence verified by `tests/test_pvt_core.py`.

### Metrics computed

| Metric | Formula / definition | Source |
|--------|----------------------|--------|
| `n_trials`, `n_valid_trials` | Trial counts after classification | Dinges 1997 |
| `n_lapses`, `n_major_lapses`, `n_false_starts`, `n_no_response` | Classification counts | Dinges 1997 |
| `mean_rt_ms`, `median_rt_ms`, `sd_rt_ms`, `min_rt_ms`, `max_rt_ms`, `p10_rt_ms`, `p90_rt_ms` | Standard descriptive statistics over valid trials | Dinges 1997 |
| `cv_rt` | SD / mean of valid RTs | Di Muzio et al. 2021 |
| `fastest_10pct_mean_rt_ms`, `slowest_10pct_mean_rt_ms` | Mean RT of fastest 10 % / slowest 10 % of valid trials | Dinges 1997 composite |
| `mean_response_speed_per_s`, `median_response_speed_per_s` | Reciprocal RT (1000 / RT_ms); more normal distribution, more sensitive to TSD | Basner & Dinges 2011 |
| `fastest_10pct_mean_speed_per_s`, `slowest_10pct_mean_speed_per_s` | Tail means of 1/RT | Basner & Dinges 2011 |
| `transformed_lapses` | √L + √(L+1) | Basner & Dinges 2011 |
| `response_speed_index` | Mean 1/RT (aggregate alertness) | Dinges 1997 |
| `pvt_lapses_3min` | Lapse count scaled to 3-min equivalent; feeds `app.scheduling_core.score_pvt_lapses_3min` | Basner & Dinges 2011 |

### API

`api/pvt_endpoints.py` (mounted at `/api/pvt`):

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/api/pvt/score` | Stateless scoring — compute metrics from a raw trial list without saving |
| `POST` | `/api/pvt/sessions` | Save a completed session; returns the saved summary including `decision` |
| `GET`  | `/api/pvt/sessions/{user_id}` | List user's sessions (limit / variant filter) |
| `GET`  | `/api/pvt/sessions/{user_id}/latest` | Most recent session with full trial detail |
| `GET`  | `/api/pvt/variants` | Canonical variant defaults |

Persistence uses SQLite in `pvt_sessions.db` with a `user_id`-indexed history.

## Integration with the readiness pipeline

The operational PVT-B gate surfaces `pvt_lapses_3min`, which is the exact input already consumed by `app/scheduling_core.py`:

- `score_pvt_lapses_3min(lapses)` maps the lapse count to a [0, 1] readiness subscore
- Hard gate: `PVT_LOW_PERFORMANCE_MIN_LAPSES = 20` triggers "low performance" classification
- This flows into IHPI (Integrated Human Performance Index) and the downstream GO / NO-GO decision

The operational route (`/scheduling/pvt`) POSTs the session to `/api/pvt/sessions` with `device_label="web-operational"`, making it visible in the user-profile layer and downstream readiness analytics.

## Relation to the OPI manuscript

The Operational Performance Indicator (OPI) framework described in `manuscript/draft/opi_main_manuscript.md` references PVT as one of the inputs to the readiness-fusion layer (§2.3.3). With the PVT module in place, operators can now generate their own `pvt_lapses_3min` inside the platform rather than importing it from an external PVT.

## Validation references (all DOIs Crossref-verified)

- Dinges DF, Pack F, Williams K, Gillen KA, Powell JW, Ott GE, Aptowicz C, Pack AI. (1997). Cumulative sleepiness, mood disturbance, and psychomotor vigilance performance decrements during a week of sleep restricted to 4-5 hours per night. *Sleep* 20(4):267-277. [10.1093/sleep/20.4.267](https://doi.org/10.1093/sleep/20.4.267)
- Basner M, Dinges DF. (2011). Maximizing sensitivity of the PVT to sleep loss. *Sleep* 34(5):581-591. [10.1093/sleep/34.5.581](https://doi.org/10.1093/sleep/34.5.581)
- Grant DA, Honn KA, Layton ME, Riedy SM, Van Dongen HPA. (2017). 3-minute smartphone-based and tablet-based psychomotor vigilance tests for the assessment of reduced alertness due to sleep deprivation. *Behav Res Methods* 49(3):1020-1029. [10.3758/s13428-016-0763-8](https://doi.org/10.3758/s13428-016-0763-8)
- Di Muzio M, et al. (2021). Comparison of sleep and attention metrics among nurses working shifts on a forward- vs backward-rotating schedule. *JAMA Netw Open* 4(10):e2129906. [10.1001/jamanetworkopen.2021.29906](https://doi.org/10.1001/jamanetworkopen.2021.29906)
- Anwyl-Irvine A, Dalmaijer ES, Hodges N, Evershed JK. (2020). Realistic precision and accuracy of online experiment platforms, web browsers, and devices. *Behav Res Methods* 53(4):1407-1425. [10.3758/s13428-020-01501-5](https://doi.org/10.3758/s13428-020-01501-5)
- Garaizar P, Vadillo MA. (2014). Accuracy and precision of visual stimulus timing in PsychoPy: no timing errors in standard usage. *PLoS ONE* 9(11):e112033. [10.1371/journal.pone.0112033](https://doi.org/10.1371/journal.pone.0112033)
- Basner M, Dinges DF, et al. (2014). Psychological and behavioral changes during confinement in a 520-day simulated interplanetary mission to Mars. *PLoS ONE* 9(3):e93298. [10.1371/journal.pone.0093298](https://doi.org/10.1371/journal.pone.0093298)
- Tu D, Basner M, et al. (2022). Dynamic ensemble prediction of cognitive performance in spaceflight. *Sci Rep* 12:11032. [10.1038/s41598-022-14456-8](https://doi.org/10.1038/s41598-022-14456-8)
- Nishimura Y, et al. (2025). Enhanced repeated measurement of psychological tasks and form questions via a web-based mobile app. *Environmental and Occupational Health Practice*. [10.1539/eohp.2025-0019](https://doi.org/10.1539/eohp.2025-0019)

## Testing

Python: `pytest tests/test_pvt_core.py -v` — 28 tests covering classification, alert session, fatigued session, variant scaling, edge cases, builders, and ISI schedule generation.

TypeScript: the mirror is pure functional code; parity with Python is validated by identical fixture calculations (extend `tests/test_pvt_core.py` with a parallel TS test if needed).

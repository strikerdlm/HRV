# Table 1 — OPI Task Taxonomy and Autonomic Signatures

Author: Dr Diego Malpica MD

This table defines the task categories covered by the Operational Performance Indicator (OPI) framework, their dominant performance demands, expected HRV signatures under high workload, and canonical failure modes. Seventeen categories span ten manned-aviation roles and seven unmanned aircraft system (UAS) / teleoperator roles. The taxonomy anchors the per-task weight profiles in Table 2 and the vigilance/latency models in Table 3.

## Source derivation

Task demands and HRV signatures are derived from the following peer-reviewed sources:

- Wilson, G. F. (2002) — HRV sensitivity to flight-phase workload; LF/HF ratio increases 40-80% during high-workload flight phases.
- Wickens, C. D. (2002, 2008) — Multiple Resource Theory (MRT) for dual-task interference and attention capacity under display complexity.
- Roscoe, A. H. (1992) — Instrument flying increases cognitive workload 40-60% vs. VFR.
- Svensson et al. (1997) — LF/HF ratio associated with spatial-disorientation susceptibility.
- Brookings et al. (1996); Vogt et al. (2006) — ATC controller HRV under traffic-density loads.
- Crowley (1991); Rash et al. (2009) — NVG workload and visual fatigue.
- Harding et al. (2001) — HMD workload assessment via HRV.
- Driskell & Salas (1996); Stokes & Kite (2017) — Stress and performance in aviation emergencies.
- Carretta (2011); Retzlaff & Gibertini (1988) — Test pilot selection and state thresholds.
- Bolia et al. (2007); Roza et al. (2015) — Naval aviation and precision motor control.
- Endsley (1995); Schreiber et al. (2004) — Situation awareness in weapons employment.
- Casner et al. (2014); Parasuraman & Riley (1997) — Automation interaction and skill degradation.
- Warm et al. (2008) — Vigilance decrement and attention-resource theory for sustained monitoring.
- Chen et al. (2007) — Teleoperator latency sensitivity and control strategy selection.
- Stevens et al. (2022) [doi:10.1080/08995605.2022.2130673] — Cognitive Metrics Profiling in unmanned-vehicle control.

## Manned aviation task categories

| # | Task category | Primary performance demands | Dominant failure mode | Expected HRV signature under high load |
| --- | --- | --- | --- | --- |
| 1 | Instrument Meteorological Conditions (IMC) flying | Continuous instrument cross-check; spatial-orientation maintenance without visual references; approach/missed-approach workload spikes | Spatial disorientation; task saturation during approach | LF/HF ↑ 40-80%; RMSSD ↓; stress index ↑ |
| 2 | Night Vision Device (NVD) operations | Reduced 40° visual field; degraded depth perception; terrain interpretation under circadian trough | Obstacle collision; misjudged clearances | Sustained stress index ↑; RMSSD ↓ with time-on-goggles |
| 3 | Helmet-Mounted Display (HMD) flying | Display clutter management; divided attention HMD vs. out-the-window; vestibular-visual conflict risk | Target fixation; display overreliance | HRV complexity (SampEn) ↓; dual-task LF power changes |
| 4 | High-density air traffic control | Communication tempo; multiple-aircraft tracking; conflict detection and resolution | Sequencing errors; missed communications | HF power ↓↓ (vagal withdrawal); entropy ↓ at saturation |
| 5 | Critical emergency (immediate-action) | Acute stress mobilisation; time-compressed decision; rapid execution of memory items | Decision paralysis; fixation errors | Acute HRV suppression (RMSSD ↓↓, HF ↓↓); heart-rate elevation; brief eustress window |
| 6 | Non-critical emergency (abnormal/cautionary) | Procedure-driven problem-solving; prioritisation; time available for checklists | Checklist errors; sequence mistakes | Moderate arousal; LF/HF ↑ modest; stress index moderate |
| 7 | Test pilot operations | Novel stimuli tolerance; envelope expansion with unknown limits; rapid adaptation; ambiguity tolerance | Unexpected dynamics; recovery failure | Wider acceptable arousal band; rapid recovery required; self-selected population baseline |
| 8 | Carrier landing (CV/CVN) | Precision motor control (3° glideslope); power/attitude coordination; deck-motion compensation | Bolter; ramp strike | Precision-task markers: RMSSD target >35 ms; SD1/SD2 ~0.4-0.6; SampEn >1.2 |
| 9 | Weapons delivery | Target acquisition and tracking; weapons-system management; ROE compliance | Fratricide; collateral damage | Sustained-attention markers; ingress moderate LF ↑; target area HF ↓, entropy ↓; release stress spike |
| 10 | New platform / new weapons-platform testing | Procedure unfamiliarity; mode-confusion risk; learning-curve effects | Mode confusion; incorrect inputs | Learning-load signatures; delta and theta EEG changes typical; HRV complexity reduced |

## UAS / teleoperator task categories

| # | Task category | Primary performance demands | Dominant failure mode | Expected autonomic / behavioural signature |
| --- | --- | --- | --- | --- |
| 11 | ISR (intelligence, surveillance, reconnaissance) | Sustained vigilance; low-event detection; prolonged monitoring of sparse scenes | Vigilance decrement; missed events | Vigilance-capacity decay (Warm 2008); LF/HF modestly elevated early, entropy ↓ later |
| 12 | Strike operations | Target discrimination; ROE and collateral assessment; decision accuracy under threat | Target misclassification; collateral damage | Acute stress response at release; entropy ↓ during target acquisition |
| 13 | SAR / CSAR (search and rescue / combat SAR) | Multi-task coordination; situational awareness under time pressure; dynamic target tracking | Situational-awareness breakdown | Sustained moderate-to-high arousal; LF/HF ↑ with tempo |
| 14 | Autonomous-swarm supervisory control | Supervisory monitoring across multiple vehicles; exception handling; human-in-the-loop policy decisions | Automation bias; exception-queue overflow | Multi-vehicle penalty; HRV complexity ↓ at saturation; attention capacity depleted |
| 15 | Contested-environment operations | Dual-task threat monitoring + mission execution; higher decision tempo under uncertainty | Dual-task interference | Persistent LF ↑; parasympathetic withdrawal; entropy ↓ |
| 16 | Ground-robot teleoperation | Spatial transformation; mental rotation; proprioceptive mismatch | Orientation errors; control reversals | Cognitive-load signatures; reduced HRV complexity; control-strategy shift with latency |
| 17 | Subsea / long-latency teleoperation | Communication delays (>1 s); predictive control; move-and-wait strategies | Control-loop instability; autonomous handoff needed | Latency penalty dominates; sustained stress index ↑ with loop time |

## Readiness categories (consistent across all tasks)

| OPI score | Category | Operational interpretation |
| --- | --- | --- |
| ≥85 | GO | Full mission capability |
| 70-84 | GO (Monitor) | Proceed with enhanced crew-resource-management coordination |
| 55-69 | CAUTION | Consider mission modification or task swap |
| <55 | NO-GO | Unacceptable operational risk under the task-specific threshold |

Thresholds are theory-derived and calibrated to be consistent with SAFTE effectiveness bands (Hursh 2004) and published fatigue-management guidance (ICAO Doc 9966 §3.3). Empirical calibration against field outcome data is future work.

## Notes on taxonomy design

1. The seventeen categories are **not mutually exclusive** at the mission level — a single sortie can transition across categories (e.g., IMC departure → weapons delivery → carrier recovery). The OPI pipeline is designed to be re-evaluated per-window as the active task category changes.
2. The taxonomy is **extensible**. Additional categories (e.g., space-station EVA, rotary-wing confined-area landing, air ambulance HEMS) can be added by specifying their primary demands, failure modes, and weight profile following the same template.
3. **UAS operator roles** were given their own block because three demand factors (sustained vigilance, control latency, multi-vehicle supervisory load) have no direct analogue in manned aviation and require dedicated OPI components (Table 3).
4. **Readiness-category thresholds** are held constant across tasks; only the **component weights** and **task-complexity modifiers** differ by task (Table 2). This separation keeps the decision-threshold semantics interpretable across roles.

## Cross-reference

- Per-task OPI component weights: `manuscript/tables/opi_weight_profiles.md`
- Vigilance-decrement and control-latency parameter values: `manuscript/tables/opi_vigilance_latency_models.md`
- Theoretical grounding and formula derivation: `analysis/operational_performance_indicators_research.md` sections 2-5.

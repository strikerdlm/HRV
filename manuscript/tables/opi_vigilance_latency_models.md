# Table 3 — Vigilance-Decrement and Control-Latency Models (UAS / Teleoperation)

Author: Dr Diego Malpica MD

This table specifies the two UAS-specific OPI components that have no direct analogue in manned aviation: the vigilance-decrement model for sustained monitoring and the control-latency penalty for teleoperated systems. Both models feed into `OPI_UAS` (Table 2) and are theory-derived from the cited HF literature. Empirical calibration against field operator performance is future work.

---

## 1. Vigilance-decrement model

### Functional form

Vigilance capacity is modelled as an exponential decay toward an asymptotic minimum over time-on-task (Warm, Parasuraman & Matthews, 2008):

```
Vigilance_capacity(t) = V0 · e^(−λ · t) + Vmin
```

where
- `V0` — initial vigilance capacity at time zero, typically 95-100 (index units)
- `λ` — task-specific decay constant in per-hour units
- `t` — time-on-task in hours
- `Vmin` — asymptotic minimum, typically 60-70 (index units)

For OPI use, `Vigilance_capacity(t)` is normalised to the `[0, 100]` scale and substituted for the `Vigilance_adj` term in the UAS formula.

### Task-specific decay constants

| UAS task type | λ (per hour) | V0 | Vmin | Time to 80 % of V0 | Recommended maximum sortie duration |
| --- | --- | --- | --- | --- | --- |
| High-event ISR | 0.08 | 100 | 70 | ≈ 2.5 h | 2.0 h |
| Low-event ISR | 0.12 | 100 | 65 | ≈ 1.8 h | 1.5 h |
| Multi-vehicle supervisory | 0.15 | 100 | 60 | ≈ 1.3 h | 1.0 h |
| Ground teleoperation | 0.10 | 100 | 70 | ≈ 2.0 h | 1.5 h |

Notes:

- `λ` values reflect the combined effect of sustained monitoring load and event rate; higher event rates partially counteract the decrement but introduce transient stress spikes (Warm 2008; Li et al. 2025 UAS cognitive-load systematic review).
- Recommended maximum sortie durations in the final column are **operational planning heuristics**, not validated thresholds. They are intended to inform scheduling decisions before empirical field calibration is available.
- Subsea / long-latency teleoperation tasks (category 17) use `λ = 0.10` unless control loop times exceed 1,500 ms, in which case `λ` increases by 50 % due to additional cognitive load from predictive-control strategy requirements.

### Worked example

ISR operator 1.5 h into a high-event sortie:

```
Vigilance_capacity(1.5) = 100 · e^(−0.08 · 1.5) + 70
                        = 100 · 0.8869 + 70   [note: formula in practice uses (V0 − Vmin) · decay]
```

Interpreted with the compositional form `Vigilance = (V0 − Vmin) · e^(−λt) + Vmin`:

```
Vigilance_capacity(1.5) = (100 − 70) · e^(−0.12) + 70
                        = 30 · 0.8869 + 70
                        = 96.6
```

At 3 hours:

```
Vigilance_capacity(3.0) = (100 − 70) · e^(−0.24) + 70
                        = 30 · 0.7866 + 70
                        = 93.6
```

The compositional form is preferred in implementation because it bounds the output cleanly to `[Vmin, V0]`.

---

## 2. Control-latency penalty

### Functional form

Control latency degrades teleoperator performance through move-and-wait behaviour and predictive-control burden (Chen, Haas & Barnes, 2007; Li et al. 2025 UAS cognitive-load systematic review):

```
Latency_penalty = 0.5 · ln(1 + latency_ms / 100)
```

The logarithmic form captures the observed diminishing-returns relationship between latency and performance loss: small latencies have minimal impact, intermediate latencies force strategy changes, and large latencies trigger supervisory-control transitions or autonomous handoff.

### Latency tiers and strategy selection

| Latency range (ms) | Latency_penalty (OPI points deducted) | Observed performance impact | Compensatory control strategy |
| --- | --- | --- | --- |
| < 100 | ≈ 0 | Negligible | Direct teleoperation; no adjustment |
| 100 – 300 | 0.35 – 0.69 | Mild — minor path deviations | Anticipatory control |
| 300 – 700 | 0.69 – 1.05 | Moderate — reduced dynamic response | Move-and-wait control |
| 700 – 1500 | 1.05 – 1.39 | Significant — persistent overshoots | Supervisory-control shift |
| > 1500 | > 1.39 | Severe — control-loop instability | Autonomous handoff recommended |

Penalty magnitudes are intentionally modest in absolute terms. The operational effect on OPI comes primarily from **combination** with a reduced Vigilance_adj and Multi_vehicle_penalty (Table 2), not from latency alone.

### Worked example

Ground-robot teleoperator with 450 ms one-way control latency:

```
Latency_penalty = 0.5 · ln(1 + 450 / 100)
                = 0.5 · ln(5.5)
                = 0.5 · 1.7047
                = 0.85
```

Subsea teleoperator with 1.2 s latency:

```
Latency_penalty = 0.5 · ln(1 + 1200 / 100)
                = 0.5 · ln(13)
                = 0.5 · 2.5649
                = 1.28
```

---

## 3. Multi-vehicle (supervisory) penalty

For supervisory control of multiple vehicles (e.g., swarm supervisory control, distributed ISR), the OPI includes an additive penalty:

```
Multi_vehicle_penalty = 3 · (n_vehicles − 1)
```

| n_vehicles | Penalty |
| --- | --- |
| 1 | 0 |
| 2 | 3 |
| 3 | 6 |
| 4 | 9 |
| 5 | 12 |
| 8 | 21 |

Rationale: the operator's attention capacity is assumed to share across vehicles with diminishing per-vehicle resource availability. The linear coefficient 3 was chosen to produce roughly 10 OPI-point deductions at 4-vehicle supervision, consistent with reported performance-cost ranges in supervisory-control literature. This is a conservative operational default; empirical calibration against sortie outcomes is future work.

---

## 4. Implementation notes

- Vigilance decay integrates with the user-profile layer (`app/user_profile_tab.py`, `app/user_database.py`) so that previous time-on-task carries forward across sessions.
- Latency penalty requires external input from the control-loop telemetry. In absence of this input, the default assumption is `latency_ms = 50` (i.e., negligible penalty), with a warning emitted.
- Multi-vehicle penalty is inferred from the active-vehicle count in the scheduling module (`app/scheduling_core.py`) and can be overridden by the operator-facing UI.

## Cross-reference

- Task taxonomy and HRV signatures: `manuscript/tables/opi_task_taxonomy.md`
- Component weight profiles and overall OPI formulation: `manuscript/tables/opi_weight_profiles.md`
- Source literature derivation: `analysis/operational_performance_indicators_research.md` §5.3-5.6

## Primary source references

- Warm, J. S., Parasuraman, R., & Matthews, G. (2008). Vigilance requires hard mental work and is stressful. *Human Factors, 50*(3), 433-441. doi:10.1518/001872008X312152
- Chen, J. Y. C., Haas, E. C., & Barnes, M. J. (2007). Human performance issues and user interface design for teleoperated robots. *IEEE Transactions on Systems, Man, and Cybernetics, Part C, 37*(6), 1231-1245. doi:10.1109/TSMCC.2007.905819
- Li, Q., Molloy, O., El-Fiqi, H., & Eves, G. (2025). Applications of Machine Learning in Assessing Cognitive Load of Uncrewed Aerial System Operators and in Enhancing Training: A Systematic Review. *Drones, 9*(11), 760. doi:10.3390/drones9110760

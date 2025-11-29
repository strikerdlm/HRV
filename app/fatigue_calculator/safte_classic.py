"""
Classic SAFTE (SAFTEr) model port to Python.

Implements the core algorithmic steps used by the R SAFTEr package's
`SAFTE_model` function, adapted for Python and this project.

Inputs are simple per-hour sleep schedules (booleans) and a bedtime hour used
to compute the circadian acrophase as in the SAFTEr reference implementation.

The simulation runs at 1-minute resolution and returns hourly samples of
Effectiveness (%), consistent with the Streamlit UI expectations.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple
import datetime as _dt

import math


@dataclass(frozen=True)
class ClassicSafteParams:
    # Time base
    epoch_length_min: float = 1.0  # minutes

    # Reservoir/capacity
    reservoir_capacity: float = 2880.0
    normalization_constant: float = 96.7

    # Homeostatic / sleep propensity
    alpha_limit: float = 3.4
    relative_amp_swc: float = 0.00312
    mesor_sleep_propensity_rhythm: float = 0.0
    amplitude_sleep_propensity_rhythm: float = 0.55

    # Sleep inertia
    amplitude_sleep_inertia: float = 0.08
    max_sleep_inertia_percent: float = 5.0

    # Circadian dual oscillator
    amp_12hr_cycle: float = 0.5
    relative_phase_12hr_cycle_h: float = 3.0
    amp1: float = 7.8
    amp2: float = 5.0

    # Process rates
    kappa_var: float = 0.5
    reservoir_param1: float = 0.22
    reservoir_param2: float = 0.5
    reservoir_param3: float = 0.0015


def _acrophase_from_bedtime(bedtime_hour_24: float) -> float:
    """Replicate SAFTEr acrophase calculation.

    In SAFTEr, acrophase = bedtime_hour - 5 (wrapped to 0..24).
    """
    value = bedtime_hour_24 - 5.0
    if value < 0.0:
        value += 24.0
    return value


def _circadian_component(
    time_of_day_h: float, acrophase_h: float, params: ClassicSafteParams
) -> float:
    primary = math.cos(2.0 * math.pi * (time_of_day_h - acrophase_h) / 24.0)
    secondary = params.amp_12hr_cycle * math.cos(
        4.0
        * math.pi
        * (time_of_day_h - acrophase_h - params.relative_phase_12hr_cycle_h)
        / 24.0
    )
    return primary + secondary


def _sleep_and_awake_counters(
    is_sleep_min: List[int],
) -> Tuple[List[int], List[int]]:
    """Return per-minute counters for asleep and awake states.

    Replicates the rle(group) + per-run counter logic used in SAFTEr to
    compute Min_Asleep and Min_Awake.
    """
    min_asleep: List[int] = [0] * len(is_sleep_min)
    min_awake: List[int] = [0] * len(is_sleep_min)

    run_count = 0
    current_state = is_sleep_min[0] if is_sleep_min else 0
    for i, s in enumerate(is_sleep_min):
        if i == 0:
            run_count = 1
        else:
            if s == current_state:
                run_count += 1
            else:
                current_state = s
                run_count = 1

        if s == 1:
            min_asleep[i] = run_count
            min_awake[i] = 0
        else:
            min_awake[i] = run_count
            min_asleep[i] = 0

    return min_asleep, min_awake


def simulate_classic_safte(
    total_hours: int,
    is_asleep_by_hour: Dict[int, bool],
    bedtime_hour_24: float,
    params: ClassicSafteParams | None = None,
    t0_local_hour_24: float | None = None,
) -> Tuple[List[int], List[float]]:
    """Simulate the classic SAFTEr model.

    Returns hourly time points (0..hours-1) and Effectiveness (%) sampled
    each hour. Sleep schedule is provided per-hour; this function expands to
    1-minute epochs.
    """
    if params is None:
        params = ClassicSafteParams()

    total_minutes = int(total_hours * 60)

    # Anchor circadian time-of-day to the actual local clock at the start
    if t0_local_hour_24 is None:
        now = _dt.datetime.now()
        t0_local_hour_24 = now.hour + now.minute / 60.0 + now.second / 3600.0

    # Build minute-resolution sleep vector from per-hour map
    is_sleep_min: List[int] = [0] * total_minutes
    for m in range(total_minutes):
        hour_index = m // 60
        is_sleep_min[m] = (
            1 if bool(is_asleep_by_hour.get(hour_index, False)) else 0
        )

    # Running counters of contiguous state lengths
    min_asleep, min_awake = _sleep_and_awake_counters(is_sleep_min)

    # Time-of-day in hours for circadian input
    time_of_day_h: List[float] = [
        (((t0_local_hour_24 * 60.0 + m) % (24 * 60)) / 60.0) for m in range(total_minutes)
    ]
    acrophase_h = _acrophase_from_bedtime(bedtime_hour_24)

    # Precompute circadian and sleep propensity signals
    circ_24p12: List[float] = [
        _circadian_component(tod, acrophase_h, params)
        for tod in time_of_day_h
    ]
    sleep_propensity: List[float] = [
        params.mesor_sleep_propensity_rhythm
        - params.amplitude_sleep_propensity_rhythm * c
        for c in circ_24p12
    ]

    # Allocate arrays
    sleep_debt = [0.0] * total_minutes
    sleep_intensity = [0.0] * total_minutes
    alpha_var = [0.0] * total_minutes
    func_s = [0.0] * total_minutes
    func_p = [0.0] * total_minutes
    rc_adjust = [params.reservoir_capacity] * total_minutes
    reservoir_balance = [0.0] * total_minutes
    variable_c_amp = [0.0] * total_minutes
    func_c = [0.0] * total_minutes
    sleep_inertia = [0.0] * total_minutes

    # Awake penalty per minute
    for i in range(total_minutes):
        func_p[i] = (
            params.kappa_var * params.epoch_length_min
            if is_sleep_min[i] == 0
            else 0.0
        )

    # Initialize first minute (mirrors the i == 1 block in R)
    i = 0
    sleep_debt[i] = params.relative_amp_swc * (
        params.reservoir_capacity - 2400.0
    )
    sleep_intensity[i] = sleep_debt[i] + sleep_propensity[i]
    alpha_var[i] = sleep_intensity[i] if is_sleep_min[i] == 1 else 0.0
    func_s[i] = (
        params.alpha_limit * params.epoch_length_min
        if alpha_var[i] > params.alpha_limit
        else alpha_var[i] * params.epoch_length_min
    )
    rc_adjust[i] = (
        params.reservoir_capacity
        + params.epoch_length_min * params.reservoir_param1
        if is_sleep_min[i] == 1
        else params.reservoir_capacity
    )
    reservoir_balance[i] = 2400.0 - func_p[i]

    # Iterate remaining minutes
    for i in range(1, total_minutes):
        # Homeostatic terms
        sleep_debt[i] = params.relative_amp_swc * (
            rc_adjust[i - 1] - reservoir_balance[i - 1]
        )
        sleep_intensity[i] = sleep_debt[i] + sleep_propensity[i]
        alpha_var[i] = sleep_intensity[i] if is_sleep_min[i] == 1 else 0.0
        func_s[i] = (
            params.alpha_limit * params.epoch_length_min
            if alpha_var[i] > params.alpha_limit
            else alpha_var[i] * params.epoch_length_min
        )

        # Reservoir capacity adjustment during sleep
        if is_sleep_min[i] == 1:
            prev_rc = rc_adjust[i - 1]
            if prev_rc > params.reservoir_capacity:
                rc_adjust[i] = params.reservoir_capacity
            else:
                rc_adjust[i] = prev_rc + params.epoch_length_min * (
                    params.reservoir_param1
                    * (1.0 - (sleep_debt[i - 1] / params.reservoir_param2))
                    + params.reservoir_param3
                    * (params.reservoir_capacity - prev_rc)
                )
        else:
            rc_adjust[i] = rc_adjust[i - 1]

        # Reservoir balance dynamics
        if is_sleep_min[i] == 1:
            candidate = reservoir_balance[i - 1] + func_s[i] - func_p[i]
            if candidate < 0.0:
                reservoir_balance[i] = 0.0
            elif reservoir_balance[i - 1] > params.reservoir_capacity:
                reservoir_balance[i] = reservoir_balance[i - 1] - func_p[i]
            else:
                reservoir_balance[i] = candidate
        else:
            reservoir_balance[i] = reservoir_balance[i - 1] - func_p[i]

    # Circadian modulation amplitude and component (vectorized style)
    for i in range(total_minutes):
        prev_reservoir = params.reservoir_capacity if i == 0 else reservoir_balance[i - 1]
        variable_c_amp[i] = (
            params.amp2
            * (params.reservoir_capacity - prev_reservoir)
            / params.reservoir_capacity
            + params.amp1
        )
        candidate_reservoir = (
            (2400.0 + func_s[i] - func_p[i])
            if i == 0
            else (prev_reservoir + func_s[i] - func_p[i])
        )
        func_c[i] = (
            0.0
            if candidate_reservoir < 0.0
            else variable_c_amp[i] * circ_24p12[i]
        )

        # Sleep inertia component
        if i == 0 or min_awake[i] <= 0:
            sleep_inertia[i] = 0.0
        else:
            last_awake_minutes = min_awake[i - 1]
            if last_awake_minutes > 240:
                sleep_inertia[i] = 0.0
            else:
                intensity = sleep_intensity[i]
                denom = 0.01 if intensity < 0.01 else intensity
                sleep_inertia[i] = -(
                    params.max_sleep_inertia_percent
                    ** (
                        -last_awake_minutes
                        * (1.0 / denom)
                        * params.amplitude_sleep_inertia
                    )
                )

    # Minute-level sampling of Effectiveness (%) to keep continuity in plots
    time_points: List[int] = []
    effectiveness_pct: List[float] = []
    physiological_floor = 30.0
    for m in range(0, total_minutes):
        # Sample every minute to allow smooth daily transitions in plots
        avg_reservoir = reservoir_balance[m]
        cc = func_c[m]
        si = sleep_inertia[m]
        eff = (
            100.0
            * (
                100.0 * (avg_reservoir / params.reservoir_capacity)
                + cc
                + si
            )
            / params.normalization_constant
        )
        # Always provide a numeric effectiveness so analytics are well-defined.
        # During sleep, emit the latent state (no NaNs) using the same formula,
        # which will usually be near the floor during consolidated sleep.
        eff_value = max(physiological_floor, min(100.0, eff))
        time_points.append(m)
        effectiveness_pct.append(eff_value)

    return time_points, effectiveness_pct



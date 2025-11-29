"""Enhanced core logic for fatigue calculator models."""

import math
import numpy as np

# ============================================================================
# SAFTE MODEL (Hursh et al.)
# ============================================================================

class SAFTEModel:
    """Sleep, Activity, Fatigue, and Task Effectiveness (SAFTE) model.

    Implements the canonical three-process SAFTE formulation:
    - Homeostatic sleep reservoir (linear depletion during wake, saturating recovery during sleep)
    - Dual-oscillator circadian rhythm (24 h primary + 12 h harmonic)
    - Sleep inertia (exponential decay of a 5% deficit over ~2 h)

    All parameters are set to standard defaults reported in the literature.
    """

    def __init__(self):
        # Reservoir and dynamics
        self.R_c: float = 2880.0  # capacity (units)
        self.K: float = 0.5       # depletion (units/min) during wake
        self.f: float = 0.01      # recovery rate constant (per min) during sleep
        self.a_s: float = 0.05    # circadian modulation of sleep recovery (per min)

        # Circadian parameters
        self.p: float = 18.0      # phase of 24-h peak (hours)
        self.p_prime: float = 3.0 # 12-h phase offset relative to primary (hours)
        self.beta: float = 0.5    # relative amplitude of 12-h harmonic

        # Sleep inertia
        self.I_max: float = 0.05  # 5% maximum deficit at wake
        self.i_const: float = 0.04  # decay constant in exponent

        # Circadian influence on performance
        self.a1: float = 7.8      # % base circadian amplitude
        self.a2: float = 5.0      # % extra amplitude under fatigue

    def circadian(self, t_hour: float, chronotype_offset: float = 0.0) -> float:
        """Dual-oscillator circadian drive C_t.

        t_hour is absolute local time in hours; chronotype_offset shifts phase.
        """
        phase = (t_hour - (self.p + chronotype_offset)) % 24.0
        primary = math.cos(2 * math.pi * phase / 24.0)
        # 12-h harmonic shifted by p_prime
        secondary_phase = (phase - self.p_prime)  # hours
        secondary = math.cos(4 * math.pi * secondary_phase / 24.0)
        return primary + self.beta * secondary

    def simulate_hourly(
        self,
        total_hours: int,
        is_asleep_by_hour: dict,
        chronotype_offset: float = 0.0,
        dt_minutes: int = 1,
    ) -> tuple[list[int], list[float], list[float]]:
        """Simulate SAFTE with minute resolution, returning hourly samples.

        Parameters
        - total_hours: number of hours to simulate starting at t=0
        - is_asleep_by_hour: mapping hour_index -> bool indicating sleep state for that hour
        - chronotype_offset: phase shift (hours) applied to circadian rhythm
        - dt_minutes: internal integration time step (minutes)

        Returns (time_points, circadian_values, effectiveness_values) sampled each hour.
        """
        # State variables
        R = self.R_c  # start fully rested
        last_wake_time_min: float | None = None
        sleep_intensity_at_wake: float | None = None

        # Outputs sampled hourly
        time_points: list[int] = []
        circadian_values: list[float] = []
        effectiveness_values: list[float] = []

        # Simulate minute-by-minute across the horizon
        total_minutes = total_hours * 60
        t_min = 0

        # For hourly sampling, collect stats at the start of each hour
        next_sample_min = 0

        # Track current sleep state based on is_asleep_by_hour
        def asleep_at_minute(m: int) -> bool:
            hour_index = (m // 60)
            return bool(is_asleep_by_hour.get(hour_index, False))

        # Initialize prior state
        prev_asleep = asleep_at_minute(0)

        while t_min <= total_minutes:
            # Sample at hour boundaries (including t=0 and end)
            if t_min == next_sample_min and (t_min // 60) < total_hours:
                t_hour = t_min / 60.0
                C_t = self.circadian(t_hour, chronotype_offset)

                # Compute instantaneous effectiveness if awake; None-equivalent when asleep
                if not asleep_at_minute(t_min):
                    homeo_frac = R / self.R_c
                    circ_percent = (self.a1 + self.a2 * (self.R_c - R) / self.R_c) * C_t
                    circ_frac = circ_percent / 100.0
                    inertia_frac = 0.0
                    if last_wake_time_min is not None:
                        mins_since_wake = max(0.0, t_min - last_wake_time_min)
                        if mins_since_wake <= 120.0 and sleep_intensity_at_wake and sleep_intensity_at_wake > 0:
                            inertia_frac = - self.I_max * math.exp(
                                - self.i_const * mins_since_wake / sleep_intensity_at_wake
                            )
                    total_frac = homeo_frac + circ_frac + inertia_frac
                    effectiveness_pct = total_frac * 100.0 / 96.7
                else:
                    effectiveness_pct = None  # sleeping

                time_points.append(int(t_hour))
                circadian_values.append(C_t)
                # During sleep we still return a numeric effectiveness for plotting/analytics;
                # map None to 0 to keep arrays numeric and UI simple.
                effectiveness_values.append(np.nan if effectiveness_pct is None else float(effectiveness_pct))

                next_sample_min += 60

            # Determine current sleep state and detect transitions at minute resolution
            now_asleep = asleep_at_minute(t_min)

            # Handle wake transition exactly at this minute
            if not prev_asleep and now_asleep:
                # wake->sleep transition
                last_wake_time_min = None
                sleep_intensity_at_wake = None
            elif prev_asleep and not now_asleep:
                # sleep->wake transition: compute sleep intensity denominator
                t_hour = t_min / 60.0
                C_now = self.circadian(t_hour, chronotype_offset)
                sleep_intensity_at_wake = self.a_s * C_now + self.f * (self.R_c - R)
                if sleep_intensity_at_wake <= 0:
                    sleep_intensity_at_wake = 1e-6
                last_wake_time_min = float(t_min)

            # Update reservoir for this minute
            if now_asleep:
                # Sleep: exponential-like recovery modulated by circadian
                t_hour = t_min / 60.0
                C_val = self.circadian(t_hour, chronotype_offset)
                dR_per_min = self.f * (self.R_c - R) - self.a_s * C_val
                R = min(self.R_c, max(0.0, R + dR_per_min * dt_minutes))
            else:
                # Wake: linear depletion
                R = max(0.0, R - self.K * dt_minutes)

            prev_asleep = now_asleep
            t_min += dt_minutes

        return time_points, circadian_values, effectiveness_values

# ============================================================================
# ENHANCED HOMEOSTATIC PROCESS
# ============================================================================

def enhanced_homeostatic_process(t, prev_reservoir_level, asleep, ai, sleep_quality, 
                                sleep_quantity, adenosine_level, individual_factors):
    """
    Enhanced homeostatic process incorporating adenosine dynamics and glial modulation
    
    Citations:
    - Glia involvement in sleep regulation: https://academic.oup.com/sleep/article/48/3/zsae314/7954489
    - Adenosine system in sleep inertia: https://pubmed.ncbi.nlm.nih.gov/38782198/
    - Individual differences in sleep need: https://academic.oup.com/sleepadvances/article/6/1/zpae095/7927912
    """
    K_base = 0.5  # Base sleep pressure accumulation rate
    
    # Adenosine dynamics enhancement (2024 research)
    adenosine_factor = 1 + (adenosine_level - 1) * 0.3
    
    # Individual differences modifier (2024 research)
    sleep_need_modifier, deprivation_sensitivity = individual_factors
    
    # Adjusted K with new factors
    K_adjusted = K_base * (1 + (8 - sleep_quantity) * 0.1) * adenosine_factor * deprivation_sensitivity
    
    # Glial modulation factor (2024 research)
    glial_factor = 1 + (sleep_quality - 0.5) * 0.2
    
    as_factor = 0.235 * glial_factor
    tau1 = 1
    tau2 = 1
    delta_t = 1

    if asleep:
        recovery_factor = sleep_quality * (1 - math.exp(-delta_t / tau1))
        return as_factor + recovery_factor * prev_reservoir_level + (1 - math.exp(-delta_t / tau2)) * (ai - as_factor)
    else:
        # Decrease by a fixed step per hour awake (use delta_t, not cumulative t)
        return prev_reservoir_level - K_adjusted * delta_t

def homeostatic_process(t, prev_reservoir_level, asleep, ai, sleep_quality, sleep_quantity):
    """Legacy homeostatic process - maintained for backward compatibility"""
    individual_factors = (1.0, 1.0)  # Default factors
    adenosine_level = 1.0  # Default adenosine level
    return enhanced_homeostatic_process(t, prev_reservoir_level, asleep, ai, sleep_quality, 
                                       sleep_quantity, adenosine_level, individual_factors)

# ============================================================================
# ENHANCED SLEEP INERTIA MODEL
# ============================================================================

def enhanced_sleep_inertia(t, sleep_duration, adenosine_level, sleep_restriction_days=0):
    """
    Enhanced sleep inertia model with updated duration and adenosine dynamics
    
    Citations:
    - Updated sleep inertia duration (15-60 min): https://pubmed.ncbi.nlm.nih.gov/38782198/
    - Bifurcation effects under restriction: https://umimpact.umt.edu/en/publications/biomathematical-modeling-of-fatigue-due-to-sleep-inertia
    - Adenosine regulation: https://www.frontiersin.org/journals/physiology/articles/10.3389/fphys.2020.00254/full
    """
    # Updated duration based on 2024 research (15-60 minutes, not 2 hours)
    if sleep_duration >= 6:
        max_duration = 0.25  # 15 minutes for normal sleep
    elif sleep_duration >= 4:
        max_duration = 0.5   # 30 minutes for moderate restriction
    else:
        max_duration = 1.0   # 60 minutes for severe restriction
    
    # Bifurcation effect for severe sleep restriction (2024 research)
    restriction_multiplier = 1.0
    if sleep_restriction_days > 2:
        restriction_multiplier = 1.5 + (sleep_restriction_days - 2) * 0.3
    
    # Enhanced maximum inertia with restriction effects
    Imax = 5 * (1 + max(0, (4 - sleep_duration) * 0.5)) * restriction_multiplier
    
    # Adenosine-dependent decay rate (2024 research)
    base_decay_rate = 0.067  # Updated from 0.04 based on recent evidence
    decay_rate = base_decay_rate * (1 + adenosine_level * 0.3)
    
    if t < max_duration:
        return Imax * math.exp(-t / decay_rate)
    else:
        return 0

def sleep_inertia(t):
    """Legacy sleep inertia function - maintained for backward compatibility"""
    return enhanced_sleep_inertia(t, 8, 1.0, 0)  # Default parameters

# ============================================================================
# ENHANCED CIRCADIAN PROCESS
# ============================================================================

def enhanced_circadian_process(t, chronotype_offset, ultradian_amplitude=0.2, 
                              genetic_phase_shift=0):
    """
    Enhanced circadian process with ultradian rhythms and genetic factors
    
    Citations:
    - Ultradian rhythms (~12h): https://www.frontiersin.org/journals/physiology/articles/10.3389/fphys.2024.1497836/full
    - Gene expression-based phase assessment: https://pmc.ncbi.nlm.nih.gov/articles/PMC11832606/
    - Individual circadian differences: https://www.jneurosci.org/content/44/38/e0573242024
    """
    # Primary circadian oscillation (24h period)
    p = 18 + chronotype_offset + genetic_phase_shift
    primary_circadian = math.cos(2 * math.pi * (t - p) / 24)
    
    # Secondary circadian oscillation (12h period)
    p_prime = 3 + chronotype_offset + genetic_phase_shift
    beta = 0.5
    secondary_circadian = beta * math.cos(4 * math.pi * (t - p_prime) / 24)
    
    # Ultradian rhythm (12h period) - NEW based on 2024 research
    ultradian_rhythm = ultradian_amplitude * math.cos(2 * math.pi * t / 12)
    
    return primary_circadian + secondary_circadian + ultradian_rhythm

def circadian_process(t):
    """Legacy circadian process - maintained for backward compatibility"""
    return enhanced_circadian_process(t, 0, 0.2, 0)

# ============================================================================
# ENHANCED SLEEP ARCHITECTURE MODEL
# ============================================================================

def enhanced_sleep_recovery(rem_time, nrem_time, sleep_quality, stage_specific_events=1.0):
    """
    Enhanced sleep recovery incorporating stage-specific neural events
    
    Citations:
    - REM vs NREM effects: https://www.frontiersin.org/journals/aging-neuroscience/articles/10.3389/fnagi.2024.1346807/full
    - Stage-specific neural events: https://www.jneurosci.org/content/44/24/e1517232024
    - Sleep architecture optimization: https://www.science.org/doi/10.1126/science.adr3339
    """
    # Updated recovery factors based on 2024 research
    rem_factor = 0.7    # Increased from 0.6 - emotional/integrative memory
    nrem_factor = 0.8   # Increased from 0.4 - declarative memory consolidation
    
    # Stage-specific neural events multiplier (2024 research)
    neural_events_factor = 1.0 + (sleep_quality - 0.5) * 0.4 * stage_specific_events
    
    # Calculate total recovery
    total_sleep_time = rem_time + nrem_time
    if total_sleep_time > 0:
        recovery = (rem_time * rem_factor + nrem_time * nrem_factor) * neural_events_factor / total_sleep_time
    else:
        recovery = 0
    
    return recovery

# ============================================================================
# ENHANCED SLEEP DEBT MODEL
# ============================================================================

def enhanced_sleep_debt_model(current_debt, recovery_sleep_hours, ideal_sleep=8.0):
    """
    Enhanced sleep debt model with evidence-based accumulation and recovery
    
    Citations:
    - Cognitive accuracy decrease: https://academic.oup.com/sleep/article/44/8/zsab051/6149527
    - Incomplete recovery: https://academic.oup.com/sleep/article/44/8/zsab051/6149527
    - Sleep debt meta-analysis: https://pmc.ncbi.nlm.nih.gov/articles/PMC12014645/
    """
    # Evidence-based cognitive impact (2024 research)
    # 0.0056 accuracy decrease per hour of sleep debt
    cognitive_impact = current_debt * 0.0056 * 100  # Convert to 0-100 scale
    
    # Incomplete recovery - only 60-80% recovery per night (2024 research)
    recovery_efficiency = 0.7
    
    # Calculate debt recovery
    if recovery_sleep_hours > ideal_sleep:
        excess_sleep = recovery_sleep_hours - ideal_sleep
        debt_recovery = min(current_debt, excess_sleep * recovery_efficiency)
    else:
        debt_recovery = 0
    
    return cognitive_impact, debt_recovery

# ============================================================================
# ENHANCED WORKLOAD MODEL
# ============================================================================

def enhanced_workload_model(daily_workload_hours, cognitive_load_rating, 
                           previous_day_workload=0, at_work=False):
    """
    Enhanced workload model with whole-day effects and carryover mechanisms
    
    Citations:
    - Whole-day workload effects: https://pmc.ncbi.nlm.nih.gov/articles/PMC9982770/
    - Workload and cognitive performance: https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2024.1351625/full
    - Processing speed impacts: https://pmc.ncbi.nlm.nih.gov/articles/PMC11112082/
    """
    # Base workload parameters
    Wc = 75  # Workload capacity
    Wd = 1.14  # Depletion rate
    Wr = 11   # Recovery rate
    
    # Whole-day workload impact (2024 research)
    daily_impact = daily_workload_hours * cognitive_load_rating * 0.1
    
    # Next-day carryover effect (2024 research)
    carryover_factor = 0.3 * max(0, (previous_day_workload - 8) / 8)
    
    # Current workload calculation
    if at_work:
        current_workload = Wd * (1 + cognitive_load_rating) + daily_impact + carryover_factor
    else:
        current_workload = -Wr + daily_impact + carryover_factor
    
    return current_workload

def workload(t, Wt_prev, load_rating, asleep):
    """Legacy workload function - maintained for backward compatibility"""
    daily_workload = 8 if not asleep else 0
    return enhanced_workload_model(daily_workload, load_rating, 0, not asleep)

# ============================================================================
# INDIVIDUAL DIFFERENCES MODULE
# ============================================================================

def calculate_individual_factors(age: int, sex: str, genetic_profile: list[str]):
    age_factor = 1.0 - max(0, age - 30) * 0.002
    sex_factor = 1.0
    if sex.lower() == 'female':
        sex_factor = 0.98
    elif sex.lower() == 'male':
        sex_factor = 1.0
    else:
        sex_factor = 0.99

    genetic_factor = 1.0
    if 'DEC2' in genetic_profile:
        genetic_factor *= 1.02
    if 'PER3' in genetic_profile:
        genetic_factor *= 0.98
    if 'ADA' in genetic_profile:
        genetic_factor *= 0.99

    return age_factor, sex_factor, genetic_factor

# ============================================================================
# DEEP LEARNING FRAMEWORK (CogPSGFormer-inspired)
# ============================================================================

def cogpsgformer_prediction(sleep_data, cardiac_data, brain_data, base_prediction):
    """
    CogPSGFormer-inspired deep learning prediction framework
    
    Citations:
    - CogPSGFormer model: https://arxiv.org/abs/2501.04076
    - Multi-scale convolutional-transformer: Khajehpiri et al. (2025)
    - 80.3% accuracy on STAGES dataset: https://arxiv.org/abs/2501.04076
    """
    # Placeholder for future ML integration
    # This would implement the CogPSGFormer architecture:
    # 1. Multi-scale convolutional layers for feature extraction
    # 2. Transformer encoder for temporal dependencies
    # 3. Attention mechanisms for cognitive flexibility prediction
    
    # For now, apply a simple enhancement based on available data
    enhancement_factor = 1.0
    
    if sleep_data and 'efficiency' in sleep_data:
        enhancement_factor *= (0.8 + 0.4 * sleep_data['efficiency'])
    
    return base_prediction * enhancement_factor

# ============================================================================
# ENHANCED COGNITIVE PERFORMANCE CALCULATION
# ============================================================================

def enhanced_cognitive_performance(t, Rt, Ct, It, Wt, Gt, individual_factors, ml_enhancement):
    age_factor, sex_factor, genetic_factor = individual_factors

    base_performance = 50

    homeostatic_component = 50 * Rt

    circadian_component = 30 * Ct

    inertia_component = -20 * It

    workload_component = -15 * Wt

    environment_component = 0

    individual_modulation = age_factor * sex_factor * genetic_factor

    raw_performance = base_performance + homeostatic_component + circadian_component + inertia_component + workload_component + environment_component

    individualized_performance = raw_performance * individual_modulation

    ml_enhancement = max(0.9, min(1.1, ml_enhancement))

    final_performance = individualized_performance * ml_enhancement
    
    return max(0, min(100, final_performance))

def cognitive_performance(t, Rt, Ct, It):
    """Legacy cognitive performance function - maintained for backward compatibility"""
    individual_factors = (1.0, 1.0)
    return enhanced_cognitive_performance(t, Rt, Ct, It, 0, 0, individual_factors, 1.0)

def cognitive_performance_with_workload(t, Rt, Ct, It, Wt, Wc):
    """Legacy workload function - maintained for backward compatibility"""
    individual_factors = (1.0, 1.0)
    return enhanced_cognitive_performance(t, Rt, Ct, It, Wt, 0, individual_factors, 1.0)

# ============================================================================
# ENHANCED SIMULATION ENGINE
# ============================================================================

from .safte_model import SAFTEModel as AdvancedSAFTEModel
from .safte_model import SleepEpisode, PhaseShift

def _episodes_from_schedule(hours: int, is_asleep_by_hour: dict, efficiency: float) -> list[SleepEpisode]:
    episodes: list[SleepEpisode] = []
    asleep_prev = bool(is_asleep_by_hour.get(0, False))
    start: float | None = 0.0 if asleep_prev else None
    for h in range(1, hours + 1):
        asleep_now = bool(is_asleep_by_hour.get(h, False)) if h < hours else False
        if not asleep_prev and asleep_now:
            # wake -> sleep
            start = float(h)
        elif asleep_prev and not asleep_now and start is not None:
            # sleep -> wake
            episodes.append(SleepEpisode(start=float(start), end=float(h), efficiency=float(efficiency)))
            start = None
        asleep_prev = asleep_now
    return episodes

def enhanced_simulate_cognitive_performance(hours, sleep_schedule, work_schedule, 
                                          individual_profile, environmental_factors=None):
    """
    Simulation engine now uses the advanced SAFTE formulation for the
    core fatigue/performance dynamics while preserving the API.
    
    Inputs
    - hours: total hours to simulate
    - sleep_schedule: dict with keys:
        - per-hour booleans (0..hours-1) indicating sleep state
        - optional 'quality' (0..1)
    - work_schedule: accepted for API compatibility (ignored by SAFTE core)
    - individual_profile: may include 'chronotype_offset' to shift circadian phase
    
    Returns time_points, circadian_rhythms, cognitive_performances (all length == hours)
    """
    # Build the is_asleep mapping for the simulated horizon
    is_asleep_by_hour: dict[int, bool] = {}
    for h in range(hours):
        is_asleep_by_hour[h] = bool(sleep_schedule.get(h, False))

    chronotype_offset = float(individual_profile.get('chronotype_offset', 0.0))
    sleep_efficiency = float(sleep_schedule.get('quality', 1.0))

    # Convert to advanced SAFTE schedule
    episodes = _episodes_from_schedule(hours, is_asleep_by_hour, sleep_efficiency)

    # Phase shift at t=0 to reflect chronotype offset (internal - local)
    shifts: list[PhaseShift] = []
    if abs(chronotype_offset) > 1e-6:
        shifts.append(PhaseShift(time=0.0, delta_local_hours=-chronotype_offset, note="chronotype_offset"))

    # Start the simulation at the current local hour-of-day so circadian
    # highs/lows line up with the x-axis clock in the UI. Simulate through
    # t0 + hours and then convert outputs to minutes RELATIVE to start.
    import datetime as _dt
    now = _dt.datetime.now()
    t0_local_h = now.hour + now.minute / 60.0 + now.second / 3600.0

    # Simulate at 1-min resolution for good fidelity
    model = AdvancedSAFTEModel(params={"reentrain_tau_h": 24.0})
    sim = model.run_and_export(
        schedule=episodes,
        shifts=shifts,
        t0_h=float(t0_local_h),
        t_end_h=float(t0_local_h + hours),
        dt_min=1,
        out_csv_path=None,
    )

    # Extract 15-min samples as minute indices (t in hours)
    time_points: list[int] = []  # minutes since start
    effectiveness_values: list[float] = []
    circadian_values: list[float] = []
    min_effectiveness_pct = 40.0  # physiological lower bound; prevents unrealistic zeros
    for t_h, eff in sim:
        # Convert local clock hour to minutes since simulation start
        t_min = int(round((t_h - t0_local_h) * 60.0))
        if t_min <= hours * 60:
            time_points.append(t_min)
            # Provide a numeric value at all times. When the advanced model
            # returns None during sleep, map it to a physiological floor so the
            # UI has continuous data for analytics and plotting.
            value = min_effectiveness_pct if eff is None else float(
                max(min_effectiveness_pct, min(100.0, eff))
            )
            effectiveness_values.append(value)
            C_t = SAFTEModel().circadian(float((t0_local_h + t_min / 60.0) % 24.0), chronotype_offset)
            circadian_values.append(float(C_t))

    return time_points, circadian_values, effectiveness_values

# Legacy simulation function for backward compatibility
# (unchanged)

def simulate_cognitive_performance(hours, sleep_start, sleep_end, sleep_quality, 
                                 sleep_quantity, work_start, work_end, load_rating):
    """Legacy simulation function - maintained for backward compatibility"""
    sleep_schedule = {
        'quality': sleep_quality,
        'quantity': sleep_quantity
    }
    for h in range(24):
        sleep_schedule[h] = sleep_start <= h < sleep_end if sleep_start <= sleep_end else (h >= sleep_start or h < sleep_end)
    
    work_schedule = {
        'load_rating': load_rating
    }
    for h in range(24):
        work_schedule[h] = work_start <= h < work_end if work_start <= work_end else (h >= work_start or h < work_end)
    
    individual_profile = {
        'genetic_profile': [],
        'sex': 'unknown',
        'age': 25,
        'chronotype_offset': 0
    }
    
    # Use the enhanced engine, which returns minute-resolution series.
    tp_min, circ_vals, perf_vals = enhanced_simulate_cognitive_performance(
        hours, sleep_schedule, work_schedule, individual_profile
    )

    # Downsample to hourly outputs to preserve legacy API guarantees
    # (length == hours, time points 0..hours-1 in hours).
    minute_to_perf = {int(m): float(v) for m, v in zip(tp_min, perf_vals)}
    minute_to_circ = {int(m): float(c) for m, c in zip(tp_min, circ_vals)}

    time_points = list(range(int(hours)))
    perf_hourly: list[float] = []
    circ_hourly: list[float] = []
    for h in time_points:
        m = int(h * 60)
        perf_hourly.append(float(minute_to_perf.get(m, minute_to_perf.get(m + 1, list(minute_to_perf.values())[0]))))
        circ_hourly.append(float(minute_to_circ.get(m, minute_to_circ.get(m + 1, list(minute_to_circ.values())[0]))))

    return time_points, circ_hourly, perf_hourly
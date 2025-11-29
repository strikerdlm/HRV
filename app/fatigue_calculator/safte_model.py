# safte_model.py
# ---------------------------------------------------------------------
# Sleep, Activity, Fatigue, and Task Effectiveness (SAFTE) model
# Implements % Effectiveness with:
#   - Homeostatic reservoir (wake depletion, sleep recovery)
#   - Circadian drive (24 h + 12 h; phase can be offset for jet lag)
#   - Sleep inertia (exponential decay tied to "sleep intensity")
#   - Jet-lag: phase-shift events + optional first-order re-entrainment
#   - Sleep quality: per-episode efficiency scaling of recovery
#
# Notes:
# - Canonical SAFTE doesn't prescribe a re-entrainment ODE; we add an
#   optional exponential relaxation of internal-vs-local phase offset.
# - Sleep quality is operationalized as an efficiency (0..1) on recovery.
# ---------------------------------------------------------------------

from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict
import math
import json

# --------------------------- Data types ------------------------------

@dataclass(frozen=True)
class SleepEpisode:
    """
    A single sleep episode in absolute hours.

    Args:
        start (float): start time (hours on a common absolute axis)
        end (float):   end time   (hours on the same axis), must be > start
        efficiency (float): sleep efficiency in [0, 1]; scales recovery
                            during this episode (sleep quality proxy).
    """
    start: float
    end: float
    efficiency: float = 1.0


@dataclass(frozen=True)
class PhaseShift:
    """
    An instantaneous local-time shift (e.g., crossing time zones).

    Args:
        time (float): absolute time (hours) of the shift
        delta_local_hours (float): change in local time (e.g., +6 for eastward)
        note (str): optional annotation
    """
    time: float
    delta_local_hours: float
    note: str = ""


# --------------------------- SAFTE model -----------------------------

class SAFTEModel:
    """
    SAFTE (Hursh et al., 2004) with pragmatic extensions:

    Outputs:
        % Effectiveness vs. time (None while sleeping)

    Core parameters (defaults reflect common SAFTE usage):
        R_c: reservoir capacity (units)                   -> 2880.0
        K:   wake depletion rate (units/min)              -> 0.5
        f:   sleep recovery rate constant (per min)       -> 0.01
        a_s: circadian effect on recovery (per min)       -> 0.05
        p:   24 h circadian peak phase (hours)            -> 18.0
        p_prime: 12 h harmonic phase (hours)              -> 3.0
        beta: 12 h harmonic relative amplitude            -> 0.5
        a1:  base circadian contribution to %             -> 7.0
        a2:  extra circadian contribution under fatigue % -> 5.0
        I_max: max sleep inertia drop (fraction)          -> 0.05 (5%)
        i_const: inertia decay constant                   -> 0.04
        inertia_window_min: inertia active minutes        -> 120

    Jet lag / re-entrainment:
        internal_minus_local (state): internal - local phase offset (h)
        reentrain_tau_h: time constant (hours) for exponential relaxation.
                         Set to None to disable dynamic re-entrainment.
                         Default: 24 h (≈1 h/day catch-up).

    Methods:
        circadian(t_local_h, internal_minus_local_h) -> C_t
        simulate(schedule, shifts, t0_h, t_end_h, dt_min) -> [(t, %Eff|None)]
        run_and_export(...) -> writes CSV (t_hour,effectiveness_percent)
        to_json_params() -> JSON of current parameters
    """

    # ---- Defaults (can be overridden via __init__(params=...)) ----
    R_c: float = 2880.0
    K: float = 0.5
    f: float = 0.01
    a_s: float = 0.05
    p: float = 18.0
    p_prime: float = 3.0
    beta: float = 0.5
    a1: float = 7.8
    a2: float = 5.0
    I_max: float = 0.05
    i_const: float = 0.04
    inertia_window_min: float = 120.0
    reentrain_tau_h: Optional[float] = 24.0

    # ---- Construction / overrides ----
    def __init__(self, params: Optional[Dict[str, float]] = None):
        if params:
            for k, v in params.items():
                if not hasattr(self, k):
                    raise ValueError(f"Unknown parameter: {k}")
                setattr(self, k, v)

    # ---------------- Circadian process (24 h + 12 h) ----------------

    def circadian(self, t_local_h: float, internal_minus_local_h: float) -> float:
        """
        Two-harmonic circadian drive C_t as a function of LOCAL time and
        internal-minus-local offset (jet-lag aware).

        Returns:
            C_t (dimensionless), roughly in [-1.5, +1.5] with default beta.
        """
        internal_phase = (t_local_h + internal_minus_local_h) % 24.0
        phase_rel = (internal_phase - self.p) % 24.0
        c1 = math.cos(2.0 * math.pi * phase_rel / 24.0)
        c2 = math.cos(4.0 * math.pi * (phase_rel - self.p_prime) / 24.0)
        return c1 + self.beta * c2

    # ------------------- Sleep inertia denominator -------------------

    def sleep_intensity_denominator(self, C_at_wake: float, R_at_wake: float) -> float:
        """
        Denominator in the inertia exponential; acts like 'sleep intensity'.
        """
        denom = self.a_s * C_at_wake + self.f * (self.R_c - R_at_wake)
        return max(denom, 1e-6)

    # ---------------------- Schedule validation ----------------------

    @staticmethod
    def _validate_schedule(schedule: List[SleepEpisode]) -> None:
        if any(ep.end <= ep.start for ep in schedule):
            raise ValueError("Each SleepEpisode must have end > start.")
        # check overlaps
        s = sorted(schedule, key=lambda e: e.start)
        for i in range(1, len(s)):
            if s[i].start < s[i - 1].end:
                raise ValueError("Sleep episodes overlap; please merge or correct them.")
        if any(not (0.0 <= ep.efficiency <= 1.0) for ep in schedule):
            raise ValueError("SleepEpisode.efficiency must be within [0, 1].")

    # ------------------------ Simulation engine ----------------------

    def simulate(
        self,
        schedule: List[SleepEpisode],
        shifts: List[PhaseShift],
        t0_h: float,
        t_end_h: float,
        dt_min: int = 1,
    ) -> List[Tuple[float, Optional[float]]]:
        """
        Simulate % Effectiveness across [t0_h, t_end_h] in steps of dt_min.

        Args:
            schedule: list of SleepEpisode (absolute hours)
            shifts:   list of PhaseShift (absolute hours)
            t0_h:     start time (hours)
            t_end_h:  end time (hours)
            dt_min:   step (minutes); 1 min recommended for fidelity

        Returns:
            List of (t_local_hour, effectiveness_percent_or_None).
            When asleep, effectiveness is None.
        """
        if dt_min <= 0:
            raise ValueError("dt_min must be positive.")
        if t_end_h <= t0_h:
            raise ValueError("t_end_h must be > t0_h.")
        self._validate_schedule(schedule)

        schedule = sorted(schedule, key=lambda e: e.start)
        shifts = sorted(shifts, key=lambda e: e.time)

        # Internal minus local offset (captures jet lag); 0 at start
        internal_minus_local = 0.0
        shift_idx = 0

        # Find active sleep episode at time t
        def active_sleep(t: float) -> Optional[SleepEpisode]:
            # schedules are typically small; linear scan suffices
            for ep in schedule:
                if ep.start <= t < ep.end:
                    return ep
            return None

        t = t0_h
        dt_h = dt_min / 60.0

        # Homeostatic reservoir and inertia bookkeeping
        R = self.R_c
        asleep = active_sleep(t) is not None
        last_wake_time: Optional[float] = None
        R_at_last_wake: float = R
        C_at_last_wake: float = 0.0

        if not asleep:
            last_wake_time = t
            C_at_last_wake = self.circadian(t, internal_minus_local)
            R_at_last_wake = R

        results: List[Tuple[float, Optional[float]]] = []

        # --------- Main loop ---------
        while t <= t_end_h + 1e-9:
            # Apply instantaneous phase shifts at this time (if any)
            while shift_idx < len(shifts) and abs(t - shifts[shift_idx].time) < 1e-9:
                # Local time jumps by +delta; internal clock unchanged:
                # internal_minus_local := internal_minus_local - delta_local_hours
                internal_minus_local -= shifts[shift_idx].delta_local_hours
                shift_idx += 1

            # Optional re-entrainment (exponential relaxation toward 0 offset)
            if self.reentrain_tau_h is not None and self.reentrain_tau_h > 0:
                internal_minus_local -= (internal_minus_local / self.reentrain_tau_h) * dt_h

            # State transitions
            ep = active_sleep(t)
            if asleep:
                if ep is None:
                    # Waking up now
                    asleep = False
                    last_wake_time = t
                    C_at_last_wake = self.circadian(t, internal_minus_local)
                    R_at_last_wake = R
            else:
                if ep is not None:
                    # Falling asleep now
                    asleep = True

            # Update reservoir
            C_val = self.circadian(t, internal_minus_local)
            if asleep:
                eff = ep.efficiency if ep is not None else 1.0
                # Exponential-like recovery minus circadian term
                dR_dt = (self.f * eff) * (self.R_c - R) - self.a_s * C_val
                R = min(self.R_c, max(0.0, R + dR_dt * dt_min))
            else:
                # Linear depletion while awake
                R = max(0.0, R - self.K * dt_min)

            # Compute % Effectiveness during wake and sleep.
            # During sleep, inertia is zero but we still report the latent
            # effectiveness based on reservoir and circadian state so the UI
            # can display continuous predictions.
            # Compute in percent space (classic SAFTE style) to avoid
            # saturation artifacts and to align with validated behavior.
            homeo_percent = 100.0 * (R / self.R_c)
            circ_percent = (self.a1 + self.a2 * (1.0 - (R / self.R_c))) * C_val
            inertia_frac = 0.0
            if not asleep and last_wake_time is not None:
                mins_since_wake = (t - last_wake_time) * 60.0
                if 0.0 <= mins_since_wake <= self.inertia_window_min:
                    denom = self.sleep_intensity_denominator(
                        C_at_wake=C_at_last_wake, R_at_wake=R_at_last_wake
                    )
                    inertia_frac = - self.I_max * math.exp(
                        - self.i_const * mins_since_wake / denom
                    )
            inertia_percent = 100.0 * inertia_frac
            # Normalization to map to percent effectiveness
            norm = 96.7
            E_percent = 100.0 * (homeo_percent + circ_percent + inertia_percent) / norm
            # Physiological bounding per literature: [~30, 100]
            E_percent = max(30.0, min(100.0, E_percent))
            results.append((t, E_percent))

            t += dt_h

        return results

    # ---------------- Convenience / export / introspection ------------

    def run_and_export(
        self,
        schedule: List[SleepEpisode],
        shifts: List[PhaseShift],
        t0_h: float,
        t_end_h: float,
        dt_min: int = 5,
        out_csv_path: Optional[str] = None,
    ) -> List[Tuple[float, Optional[float]]]:
        """
        Simulate and optionally export to CSV with headers:
            t_hour,effectiveness_percent
        """
        data = self.simulate(schedule, shifts, t0_h, t_end_h, dt_min)
        if out_csv_path:
            with open(out_csv_path, "w", encoding="utf-8") as f:
                f.write("t_hour,effectiveness_percent\n")
                for t, e in data:
                    f.write(f"{t:.4f},{'' if e is None else f'{e:.4f}'}\n")
        return data

    def to_json_params(self) -> str:
        """Return current parameters as pretty JSON."""
        keys = [
            "R_c", "K", "f", "a_s", "p", "p_prime", "beta",
            "a1", "a2", "I_max", "i_const",
            "inertia_window_min", "reentrain_tau_h",
        ]
        return json.dumps({k: getattr(self, k) for k in keys}, indent=2)


# ------------------------------ Demo ---------------------------------

if __name__ == "__main__":
    # Example: three nights of sleep, with an eastward 6 h phase shift before night 3.
    model = SAFTEModel(params={"reentrain_tau_h": 24.0})  # ~1 h/day re-entrainment

    schedule = [
        SleepEpisode(23.0, 31.0, efficiency=0.95),  # Night 1: 23:00–07:00, slightly fragmented
        SleepEpisode(47.0, 55.0, efficiency=1.00),  # Night 2
        SleepEpisode(71.0, 79.0, efficiency=0.85),  # Night 3 (after time-zone jump)
    ]
    shifts = [
        PhaseShift(time=70.0, delta_local_hours=+6, note="Eastward flight at t=70 h"),
    ]

    results = model.run_and_export(
        schedule=schedule,
        shifts=shifts,
        t0_h=0.0,
        t_end_h=96.0,
        dt_min=15,
        out_csv_path=None  # set a path (e.g., "safte_demo.csv") to export
    )

    # Print a few samples
    for t, eff in results[::8][:10]:
        status = "asleep" if eff is None else f"{eff:6.2f}%"
        print(f"t={t:6.2f} h, %Effectiveness={status}")
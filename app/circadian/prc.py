"""
Phase Response Curve (PRC) tools for circadian models.

Implements methods for computing and analyzing phase response curves,
which characterize how light pulses at different circadian times affect
the phase of the circadian oscillator.

Original implementation: Arcascope (https://github.com/Arcascope/circadian)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Optional, Tuple

import numpy as np
from numpy.typing import NDArray

from .lights import LightSchedule

if TYPE_CHECKING:
    from .models import CircadianModel


__all__ = [
    "make_pulse",
    "get_pulse",
    "heaviside",
    "PRCFinder",
    "PhaseResponseCurveLight",
    "IntensityResponseCurveLight",
    "DosageResponseCurve",
    "compute_prc",
]


def make_pulse(
    t: float,
    tstart: float,
    tend: float,
    steep: float = 30.0,
) -> float:
    """Create a smooth pulse using hyperbolic tangent transitions.
    
    Args:
        t: Current time.
        tstart: Start time of pulse.
        tend: End time of pulse.
        steep: Steepness of transitions (higher = sharper).
        
    Returns:
        Pulse value (approximately 0 outside [tstart, tend], 1 inside).
    """
    return 0.5 * np.tanh(steep * (t - tstart)) - 0.5 * np.tanh(steep * (t - tend))


def get_pulse(
    t: float,
    t1: float,
    t2: float,
    repeat: bool = False,
    intensity: float = 150.0,
) -> float:
    """Get light intensity for a repeating or single pulse.
    
    Args:
        t: Current time in hours.
        t1: Pulse start time (hour of day, 0-24).
        t2: Pulse end time (hour of day, 0-24).
        repeat: If True, pulse repeats every 24 hours.
        intensity: Peak light intensity in lux.
        
    Returns:
        Light intensity at time t.
    """
    if repeat:
        t = np.fmod(t, 24.0)
    if t < 0.0:
        t += 24.0
    
    light_value = intensity * make_pulse(t, t1, t2)
    return float(np.abs(light_value))


def heaviside(x: float) -> float:
    """Heaviside step function.
    
    Args:
        x: Input value.
        
    Returns:
        0 if x < 0, else 1.
    """
    return 0.0 if x < 0 else 1.0


class PhaseResponseCurveLight:
    """Light schedules replicating classic PRC experiments."""
    
    @staticmethod
    def light_khalsa(t: float, CR: float) -> float:
        """Khalsa et al. light schedule for PRC determination.
        
        Args:
            t: Time in hours.
            CR: Constant routine length before stimulus.
            
        Returns:
            Light intensity in lux.
        """
        low_light = 15.0  # From the paper
        val = (
            low_light * make_pulse(t, 0.0, CR)
            + low_light * make_pulse(t, CR + 8.0, CR + 24.0)
            + low_light * make_pulse(t, CR + 32.0, CR + 1000.0)
        )
        val += 9985.0 * make_pulse(t, CR + 8.0 + 4.65, CR + 8.0 + 11.35)
        return val
    
    @staticmethod
    def light_hilaire(t: float, CR: float) -> float:
        """St. Hilaire et al. light schedule.
        
        Args:
            t: Time in hours.
            CR: Constant routine length.
            
        Returns:
            Light intensity in lux.
        """
        low_light = 3.0  # Amount of light during CR
        val = (
            low_light * make_pulse(t, 0, CR)
            + low_light * make_pulse(t, CR + 8, CR + 24)
            + low_light * make_pulse(t, CR + 32, CR + 1000)
        )
        val += 7997 * make_pulse(t, CR + 8 + 7.5, CR + 8 + 8.5)
        return val
    
    @staticmethod
    def light_amplitude_resetting(t: float, CR: float) -> float:
        """Light schedule for amplitude resetting experiments.
        
        Args:
            t: Time in hours.
            CR: Constant routine length.
            
        Returns:
            Light intensity in lux.
        """
        room_light = 150.0
        after_light = 150.0
        before_light = 150.0
        
        val = before_light * make_pulse(t, 0, CR)
        val += room_light * make_pulse(t, CR + 8, CR + 24)
        val += (
            0.02 * make_pulse(t, 24.0, CR + 24.0)
            + room_light * make_pulse(t, CR + 8 + 24.0, CR + 48.0)
        )
        val += after_light * make_pulse(t, CR + 48.0 + 8.0, CR + 24 + 48.0 + 1000)
        val += (
            9850 * make_pulse(t, CR + 8 + 8 - 2.5, CR + 8 + 8 + 2.5)
            + 9850 * make_pulse(t, CR + 8 + 8 - 2.5 + 24.0, CR + 8 + 8 + 2.5 + 24.0)
        )
        return val
    
    @staticmethod
    def light_czeisler_type0(t: float, CR: float) -> float:
        """Czeisler Type 0 PRC light schedule.
        
        Implements the bright light protocol from Czeisler et al.
        that produces a Type 0 (strong resetting) PRC.
        
        Args:
            t: Time in hours.
            CR: Constant routine length.
            
        Returns:
            Light intensity in lux.
        """
        room_light = 150.0
        after_light = 150.0
        before_light = 150.0
        
        val = before_light * make_pulse(t, 0, CR)
        val += room_light * make_pulse(t, CR + 8, CR + 24)
        val += (
            0.02 * make_pulse(t, 24.0, CR + 24.0)
            + room_light * make_pulse(t, CR + 8 + 24.0, CR + 24 + 24.0)
        )
        val += (
            0.02 * make_pulse(t, 48.0, CR + 48.0)
            + room_light * make_pulse(t, CR + 8 + 48.0, CR + 24 + 48.0)
        )
        val += after_light * make_pulse(t, CR + 24 + 48.0 + 8.0, CR + 24 + 48.0 + 1000)
        val += (
            9850 * make_pulse(t, CR + 8 + 8 - 2.5, CR + 8 + 8 + 2.5)
            + 9850 * make_pulse(t, CR + 8 + 8 - 2.5 + 24.0, CR + 8 + 8 + 2.5 + 24.0)
            + 9850 * make_pulse(t, CR + 8 + 8 - 2.5 + 48.0, CR + 8 + 8 + 2.5 + 48.0)
        )
        return val


class PRCFinder:
    """Tools for computing phase response curves from circadian models."""
    
    # Experimental data from Czeisler et al. Type 0 PRC
    type0x: NDArray = np.array([
        16.2593, 16.304, 16.3018, 16.2738, 16.493, 16.7512, 17.9321, 19.1632,
        20.0534, 20.2959, 20.4188, 20.6394, 20.787, 21.1123, 21.1377,
        21.1579, 21.183, 21.2433, 21.2689, 22.2468, 25.2147, 27.1642,
        27.1974, 27.2108, 27.2363, 27.257, 27.5736, 27.8422, 28.0516,
        28.3226, 28.3779, 28.4506, 28.6003, 28.6608, 28.7964, 28.8359,
        28.8422, 29.0239, 29.0813, 29.1065, 29.1506, 29.2144, 29.2561,
        29.4005, 29.8354, 26.0773, 25.5784, 24.256, 20.0592, 15.2187,
        6.93359, 6.95777, 6.98051, 7.00128, 7.08384, 7.99415, 8.25918,
        8.7184, 8.91649, 8.97987, 9.2621, 9.30382, 9.47454, 10.3813, 10.8293,
        10.8903, 10.9258, 11.0337, 11.8089, 16.15, 16.3256, 16.363, 16.3653,
        16.6808, 16.7064
    ])
    
    @staticmethod
    def exp_type0(x: float, b: float) -> float:
        """Empirical fit function for Type 0 PRC.
        
        Args:
            x: Circadian phase.
            b: Breakpoint parameter.
            
        Returns:
            Phase shift in hours.
        """
        val = (
            (-1.57154 + 0.228932 / (-1.0 * b + x) - 0.650632 * x) * heaviside(b - x)
            + (9.66876 + 0.1321196 / (-1.0 * b + x) - 0.463105 * x) * heaviside(x - b)
        )
        return float(np.clip(val, -12.0, 12.0))
    
    @staticmethod
    def prc_type0_point(
        CR_length: float,
        initial_value: NDArray,
        model: "CircadianModel",
    ) -> Tuple[float, float]:
        """Compute a single point on the Type 0 PRC.
        
        Simulates the Czeisler Type 0 protocol and computes the phase
        shift induced by the light stimulus.
        
        Args:
            CR_length: Constant routine length (typically varies 6-30 hours).
            initial_value: Entrained initial conditions for the model.
            model: CircadianModel instance to simulate.
            
        Returns:
            Tuple of (phase, shift) where:
            - phase: Circadian phase at stimulus (hours, 0-24)
            - shift: Phase shift induced (hours, -12 to +12)
        """
        CR_final = 30.0
        tend = 72.0 + 8.0 + 30.0 + CR_final
        time = np.arange(0, tend, 0.10)
        
        light_vals = np.array([
            PhaseResponseCurveLight.light_czeisler_type0(t, CR_length)
            for t in time
        ])
        
        trajectory = model(time, initial_value, light_vals)
        CBT = model.cbt(trajectory)
        
        # Find phase shift (negative number between 0 and -24)
        shift = (CBT[0] - CBT[-1]) % 24.0
        
        # Convert to range (-12, 12)
        if shift < -12.0:
            shift += 24.0
        
        # Find phase of stimulus relative to CBT
        phase = (CR_length - CBT[0] + 12.0 + 16.0 - 2.5) % 24.0
        
        return phase, shift


class IntensityResponseCurveLight:
    """Light schedules for intensity response experiments."""
    
    @staticmethod
    def light_intensity(t: float, intensity: float) -> float:
        """Light schedule for intensity response curve experiments.
        
        Based on protocols where all light exposures started at φ 6.75 hours
        before Tmin and lasted 6.5 hours at varying intensities.
        
        Args:
            t: Time in hours.
            intensity: Stimulus intensity in lux.
            
        Returns:
            Light intensity at time t.
        """
        cr_light_level = 10.0
        wake_light_level = 10.0
        wake_stimulus_light_level = 0.03
        sleep_light_level = 0.03
        stimulus_light_level = intensity
        
        w = 50.0  # Length of constant routine (~50 hours)
        
        val = cr_light_level * make_pulse(t, 0, w)  # 50h constant routine
        val += sleep_light_level * make_pulse(t, w, w + 8.0)  # 8h sleep bout
        val += wake_stimulus_light_level * make_pulse(t, w + 8.0, w + 24.0)  # Wake/stimulus
        val += (stimulus_light_level - wake_stimulus_light_level) * make_pulse(
            t, w + 16.0 - 3.25, w + 16.0 + 3.25
        )  # Stimulus centered during wakefulness
        val += sleep_light_level * make_pulse(t, w + 24.0, w + 32.0)  # Post-stimulus sleep
        val += cr_light_level * make_pulse(t, w + 32.0, w + 32.0 + 30.0)  # Final CR
        
        return val


class DosageResponseCurve:
    """Light schedules for dosage (duration) response experiments."""
    
    @staticmethod
    def light_dosage(t: float, length: float) -> float:
        """Light schedule for Chang et al. dosage response experiments.
        
        Args:
            t: Time in hours.
            length: Duration of light pulse in hours.
            
        Returns:
            Light intensity at time t.
        """
        CR1 = 48.0  # ~50h
        CR_light_level = 1.0
        stimulus_light_level = 10000.0
        wake_light_level = 3.0
        
        val = CR_light_level * make_pulse(t, 0.0, CR1)
        val += wake_light_level * make_pulse(t, CR1 + 8.0, CR1 + 8.0 + 16.0)
        
        if length == 0.2:
            # Special case for shortest duration
            val += stimulus_light_level * make_pulse(
                t, CR1 + 8.0 + 8.5 - length / 2.0 - 12.0 / 60.0,
                CR1 + 8.0 + 8.5 + length / 2.0 - 12.0 / 60.0
            )
        else:
            val += stimulus_light_level * make_pulse(
                t, CR1 + 8.0 + 8.5 - length / 2.0, CR1 + 8.0 + 8.5 + length / 2.0
            )
        
        val += CR_light_level * make_pulse(t, CR1 + 32.0, CR1 + 32.0 + 30.0)
        
        return val
    
    @staticmethod
    def light_dosage_day1(t: float) -> float:
        """Prep day light schedule before constant routine.
        
        Args:
            t: Time in hours.
            
        Returns:
            Light intensity.
        """
        s = t % 24.0
        if s < 8.0:
            return 90.0
        elif 8.0 <= s <= 16.0:
            return 3.0
        return 0.0


def compute_prc(
    model: "CircadianModel",
    pulse_duration: float = 1.0,
    pulse_intensity: float = 1000.0,
    n_phases: int = 24,
    baseline_light: float = 150.0,
    equilibration_days: int = 10,
    measurement_days: int = 3,
    dt: float = 0.1,
) -> Tuple[NDArray, NDArray]:
    """Compute the phase response curve for a circadian model.
    
    Systematically delivers light pulses at different circadian phases
    and measures the resulting phase shifts.
    
    Args:
        model: CircadianModel instance.
        pulse_duration: Duration of light pulse in hours.
        pulse_intensity: Intensity of light pulse in lux.
        n_phases: Number of phases to sample (0-24 hours).
        baseline_light: Background light level in lux.
        equilibration_days: Days to entrain before pulse.
        measurement_days: Days to wait after pulse for measurement.
        dt: Time step for simulation.
        
    Returns:
        Tuple of (phases, shifts) where:
        - phases: Array of circadian phases (0-24 hours)
        - shifts: Array of phase shifts (hours, + = delay, - = advance)
        
    Example:
        >>> from app.circadian.models import Hannay19
        >>> model = Hannay19()
        >>> phases, shifts = compute_prc(model, pulse_duration=1.0)
        >>> plt.plot(phases, shifts, 'o-')
        >>> plt.xlabel('Circadian Phase (hours)')
        >>> plt.ylabel('Phase Shift (hours)')
    """
    phases = np.linspace(0, 24, n_phases, endpoint=False)
    shifts = np.zeros(n_phases)
    
    for i, pulse_phase in enumerate(phases):
        # Create light schedule with pulse at specified phase
        total_hours = 24 * (equilibration_days + measurement_days + 2)
        time = np.arange(0, total_hours, dt)
        
        # Baseline 16:8 light:dark cycle
        light = np.array([
            baseline_light if 8 <= (t % 24) < 22 else 0.0
            for t in time
        ])
        
        # Add pulse at specified phase on day after equilibration
        pulse_time = equilibration_days * 24 + pulse_phase
        pulse_mask = (time >= pulse_time) & (time < pulse_time + pulse_duration)
        light[pulse_mask] = pulse_intensity
        
        # Run model
        x0 = model.equilibrate(time[:int(24/dt)], light[:int(24/dt)], reps=equilibration_days)
        traj = model(time, x0, light)
        
        # Get phase markers
        dlmo_times = model.dlmos(traj)
        
        if len(dlmo_times) >= 2:
            # Compare DLMO before and after pulse
            pre_pulse_dlmo = [d for d in dlmo_times if d < pulse_time]
            post_pulse_dlmo = [d for d in dlmo_times if d > pulse_time + 24]
            
            if pre_pulse_dlmo and post_pulse_dlmo:
                # Expected DLMO time if no shift
                expected = pre_pulse_dlmo[-1] + 24 * len(post_pulse_dlmo)
                actual = post_pulse_dlmo[-1]
                shift = actual - expected
                
                # Wrap to (-12, 12)
                shift = ((shift + 12) % 24) - 12
                shifts[i] = shift
    
    return phases, shifts


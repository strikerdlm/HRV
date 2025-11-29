"""
Light schedule utilities for circadian rhythm simulation.

Provides LightSchedule class with factory methods for common schedules:
- Regular: Standard daily photoperiod
- ShiftWork: Rotating shift patterns
- SlamShift: Abrupt phase shifts
- SocialJetlag: Weekend sleep delay patterns
- Custom pulses and composable schedules

Original implementation: Arcascope (https://github.com/Arcascope/circadian)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional

import numpy as np
from numpy.typing import NDArray


@dataclass(slots=True)
class LightSchedule:
    """A light schedule defined by a callable that maps time (hours) to lux.
    
    Factory methods provide common schedule types for circadian research.
    """
    
    schedule_func: Callable[[NDArray], NDArray]
    name: str = "Custom"
    params: dict = field(default_factory=dict)
    
    def __call__(self, time: NDArray) -> NDArray:
        """Evaluate the light schedule at given time points.
        
        Args:
            time: Time array in hours.
            
        Returns:
            Light intensity in lux at each time point.
        """
        if not isinstance(time, np.ndarray):
            time = np.asarray(time, dtype=np.float64)
        return self.schedule_func(time)
    
    @staticmethod
    def Regular(
        lux: float = 500.0,
        lights_on: float = 8.0,
        lights_off: float = 22.0,
    ) -> LightSchedule:
        """Create a regular daily light schedule.
        
        Args:
            lux: Light intensity during wake period (lux).
            lights_on: Hour when lights turn on (0-24).
            lights_off: Hour when lights turn off (0-24).
            
        Returns:
            LightSchedule with daily photoperiod.
        """
        def schedule(time: NDArray) -> NDArray:
            hour_of_day = np.mod(time, 24.0)
            if lights_on < lights_off:
                # Normal schedule: lights on during day
                is_light = (hour_of_day >= lights_on) & (hour_of_day < lights_off)
            else:
                # Inverted schedule: lights on through midnight
                is_light = (hour_of_day >= lights_on) | (hour_of_day < lights_off)
            return np.where(is_light, lux, 0.0)
        
        return LightSchedule(
            schedule_func=schedule,
            name="Regular",
            params={"lux": lux, "lights_on": lights_on, "lights_off": lights_off},
        )
    
    @staticmethod
    def ShiftWork(
        lux: float = 300.0,
        days_on: int = 3,
        days_off: int = 2,
        day_lights_on: float = 8.0,
        day_lights_off: float = 22.0,
        night_lights_on: float = 20.0,
        night_lights_off: float = 8.0,
    ) -> LightSchedule:
        """Create a shift work light schedule.
        
        Args:
            lux: Light intensity during wake period (lux).
            days_on: Number of consecutive night shifts.
            days_off: Number of consecutive days off.
            day_lights_on: Wake time on day shifts.
            day_lights_off: Sleep time on day shifts.
            night_lights_on: Wake time on night shifts.
            night_lights_off: Sleep time on night shifts.
            
        Returns:
            LightSchedule with rotating shift pattern.
        """
        cycle_length = days_on + days_off
        
        def schedule(time: NDArray) -> NDArray:
            hour_of_day = np.mod(time, 24.0)
            day_in_cycle = np.mod(time // 24, cycle_length).astype(int)
            
            result = np.zeros_like(time, dtype=np.float64)
            
            # Night shift days (0 to days_on-1)
            is_night_shift = day_in_cycle < days_on
            if night_lights_on > night_lights_off:
                # Lights on through midnight
                is_light_night = (hour_of_day >= night_lights_on) | (hour_of_day < night_lights_off)
            else:
                is_light_night = (hour_of_day >= night_lights_on) & (hour_of_day < night_lights_off)
            
            # Day off (days_on to cycle_length-1)
            is_day_off = ~is_night_shift
            is_light_day = (hour_of_day >= day_lights_on) & (hour_of_day < day_lights_off)
            
            result = np.where(
                is_night_shift & is_light_night, lux,
                np.where(is_day_off & is_light_day, lux, 0.0)
            )
            return result
        
        return LightSchedule(
            schedule_func=schedule,
            name="ShiftWork",
            params={
                "lux": lux,
                "days_on": days_on,
                "days_off": days_off,
                "day_lights_on": day_lights_on,
                "day_lights_off": day_lights_off,
                "night_lights_on": night_lights_on,
                "night_lights_off": night_lights_off,
            },
        )
    
    @staticmethod
    def SlamShift(
        lux: float = 500.0,
        shift_hours: float = -6.0,
        baseline_days: int = 7,
        lights_on: float = 8.0,
        lights_off: float = 22.0,
    ) -> LightSchedule:
        """Create a slam shift (jet lag) light schedule.
        
        Args:
            lux: Light intensity during wake period (lux).
            shift_hours: Phase shift in hours (negative = advance, positive = delay).
            baseline_days: Days before shift occurs.
            lights_on: Baseline wake time.
            lights_off: Baseline sleep time.
            
        Returns:
            LightSchedule with abrupt phase shift.
        """
        shift_time = baseline_days * 24.0
        
        def schedule(time: NDArray) -> NDArray:
            hour_of_day = np.mod(time, 24.0)
            is_post_shift = time >= shift_time
            
            # Apply shift to lights on/off times
            shifted_on = np.mod(lights_on + shift_hours, 24.0)
            shifted_off = np.mod(lights_off + shift_hours, 24.0)
            
            # Pre-shift schedule
            if lights_on < lights_off:
                is_light_pre = (hour_of_day >= lights_on) & (hour_of_day < lights_off)
            else:
                is_light_pre = (hour_of_day >= lights_on) | (hour_of_day < lights_off)
            
            # Post-shift schedule
            if shifted_on < shifted_off:
                is_light_post = (hour_of_day >= shifted_on) & (hour_of_day < shifted_off)
            else:
                is_light_post = (hour_of_day >= shifted_on) | (hour_of_day < shifted_off)
            
            is_light = np.where(is_post_shift, is_light_post, is_light_pre)
            return np.where(is_light, lux, 0.0)
        
        return LightSchedule(
            schedule_func=schedule,
            name="SlamShift",
            params={
                "lux": lux,
                "shift_hours": shift_hours,
                "baseline_days": baseline_days,
                "lights_on": lights_on,
                "lights_off": lights_off,
            },
        )
    
    @staticmethod
    def SocialJetlag(
        lux: float = 500.0,
        regular_days: int = 5,
        weekend_days: int = 2,
        lights_on: float = 8.0,
        lights_off: float = 22.0,
        weekend_delay: float = 2.0,
    ) -> LightSchedule:
        """Create a social jetlag (5+2) light schedule.
        
        Args:
            lux: Light intensity during wake period (lux).
            regular_days: Days with regular schedule (typically 5 weekdays).
            weekend_days: Days with delayed schedule (typically 2 weekend days).
            lights_on: Weekday wake time.
            lights_off: Weekday sleep time.
            weekend_delay: Hours later for weekend wake/sleep times.
            
        Returns:
            LightSchedule with weekly social jetlag pattern.
        """
        cycle_length = regular_days + weekend_days
        
        def schedule(time: NDArray) -> NDArray:
            hour_of_day = np.mod(time, 24.0)
            day_in_cycle = np.mod(time // 24, cycle_length).astype(int)
            
            is_weekend = day_in_cycle >= regular_days
            
            # Weekday schedule
            is_light_weekday = (hour_of_day >= lights_on) & (hour_of_day < lights_off)
            
            # Weekend schedule (delayed)
            weekend_on = lights_on + weekend_delay
            weekend_off = lights_off + weekend_delay
            if weekend_off > 24.0:
                weekend_off = weekend_off - 24.0
                is_light_weekend = (hour_of_day >= weekend_on) | (hour_of_day < weekend_off)
            else:
                is_light_weekend = (hour_of_day >= weekend_on) & (hour_of_day < weekend_off)
            
            is_light = np.where(is_weekend, is_light_weekend, is_light_weekday)
            return np.where(is_light, lux, 0.0)
        
        return LightSchedule(
            schedule_func=schedule,
            name="SocialJetlag",
            params={
                "lux": lux,
                "regular_days": regular_days,
                "weekend_days": weekend_days,
                "lights_on": lights_on,
                "lights_off": lights_off,
                "weekend_delay": weekend_delay,
            },
        )
    
    @staticmethod
    def from_pulse(
        pulse_lux: float = 1000.0,
        pulse_start: float = 20.0,
        pulse_duration: float = 2.0,
        pulse_period: float = 24.0,
        baseline_lux: float = 0.0,
    ) -> LightSchedule:
        """Create a pulsed light schedule.
        
        Args:
            pulse_lux: Light intensity during pulse (lux).
            pulse_start: Start time of pulse within period (hours).
            pulse_duration: Duration of pulse (hours).
            pulse_period: Period of pulse repetition (hours, 24 = daily).
            baseline_lux: Light intensity between pulses (lux).
            
        Returns:
            LightSchedule with periodic pulse pattern.
        """
        def schedule(time: NDArray) -> NDArray:
            time_in_period = np.mod(time, pulse_period)
            pulse_end = pulse_start + pulse_duration
            
            if pulse_end <= pulse_period:
                is_pulse = (time_in_period >= pulse_start) & (time_in_period < pulse_end)
            else:
                # Pulse wraps around period
                is_pulse = (time_in_period >= pulse_start) | (time_in_period < (pulse_end - pulse_period))
            
            return np.where(is_pulse, pulse_lux, baseline_lux)
        
        return LightSchedule(
            schedule_func=schedule,
            name="Pulse",
            params={
                "pulse_lux": pulse_lux,
                "pulse_start": pulse_start,
                "pulse_duration": pulse_duration,
                "pulse_period": pulse_period,
                "baseline_lux": baseline_lux,
            },
        )
    
    @staticmethod
    def from_array(
        time: NDArray,
        light: NDArray,
        name: str = "FromArray",
    ) -> LightSchedule:
        """Create a light schedule from time and light arrays.
        
        Uses linear interpolation between provided data points.
        
        Args:
            time: Time array in hours.
            light: Light intensity array in lux.
            name: Name for the schedule.
            
        Returns:
            LightSchedule interpolated from data.
        """
        if len(time) != len(light):
            raise ValueError("time and light arrays must have same length")
        
        time_arr = np.asarray(time, dtype=np.float64)
        light_arr = np.asarray(light, dtype=np.float64)
        
        def schedule(t: NDArray) -> NDArray:
            return np.interp(t, time_arr, light_arr)
        
        return LightSchedule(
            schedule_func=schedule,
            name=name,
            params={"time_range": (float(time_arr[0]), float(time_arr[-1]))},
        )
    
    def __add__(self, other: LightSchedule) -> LightSchedule:
        """Combine two light schedules additively.
        
        Args:
            other: Another LightSchedule to add.
            
        Returns:
            Combined LightSchedule.
        """
        def combined(time: NDArray) -> NDArray:
            return self(time) + other(time)
        
        return LightSchedule(
            schedule_func=combined,
            name=f"{self.name}+{other.name}",
            params={"schedules": [self.params, other.params]},
        )
    
    def __mul__(self, factor: float) -> LightSchedule:
        """Scale light schedule by a factor.
        
        Args:
            factor: Scaling factor.
            
        Returns:
            Scaled LightSchedule.
        """
        def scaled(time: NDArray) -> NDArray:
            return self(time) * factor
        
        return LightSchedule(
            schedule_func=scaled,
            name=f"{self.name}*{factor}",
            params={**self.params, "scale_factor": factor},
        )


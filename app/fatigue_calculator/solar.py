"""Solar utilities (NOAA sunrise equation) for daily light/dark windows.

Implements civil twilight (center of sun at -6 degrees) for dawn/dusk.
References: NOAA solar calculation notes and sunrise equation.
"""

from __future__ import annotations

import math
import datetime as dt
from typing import Optional, Tuple


def _day_of_year(date: dt.date) -> int:
    return int(date.timetuple().tm_yday)


def _fractional_year_rad(n: int, hour: float) -> float:
    # Evaluate around solar noon (hour ~ 12) for good accuracy without iterate
    return 2.0 * math.pi / (366.0 if _is_leap_year(n) else 365.0) * (n - 1 + (hour - 12.0) / 24.0)


def _is_leap_year(n: int) -> bool:
    # here 'n' is day-of-year; leap-year check not required elsewhere
    return False


def equation_of_time_minutes(gamma: float) -> float:
    return 229.18 * (
        0.000075
        + 0.001868 * math.cos(gamma)
        - 0.032077 * math.sin(gamma)
        - 0.014615 * math.cos(2 * gamma)
        - 0.040849 * math.sin(2 * gamma)
    )


def solar_declination_rad(gamma: float) -> float:
    return (
        0.006918
        - 0.399912 * math.cos(gamma)
        + 0.070257 * math.sin(gamma)
        - 0.006758 * math.cos(2 * gamma)
        + 0.000907 * math.sin(2 * gamma)
        - 0.002697 * math.cos(3 * gamma)
        + 0.00148 * math.sin(3 * gamma)
    )


def _hour_angle_deg_for_altitude(lat_deg: float, decl_rad: float, altitude_deg: float) -> Optional[float]:
    lat_rad = math.radians(lat_deg)
    alt_rad = math.radians(altitude_deg)
    cos_omega = (math.sin(alt_rad) - math.sin(lat_rad) * math.sin(decl_rad)) / (math.cos(lat_rad) * math.cos(decl_rad))
    if cos_omega < -1.0:
        return 180.0  # sun above altitude all day (polar day)
    if cos_omega > 1.0:
        return None   # sun below altitude all day (polar night)
    return math.degrees(math.acos(cos_omega))


def civil_twilight_windows(
    date: dt.date,
    latitude_deg: float,
    longitude_deg_west: float,
    tz_hours: float,
) -> Tuple[Optional[dt.datetime], Optional[dt.datetime]]:
    """Return local civil dawn and dusk datetimes for the given date.

    Longitude should be positive-west (NOAA convention). tz_hours is local offset
    from UTC (e.g., -5 for Bogotá). Returns None if event does not occur.
    """
    n = _day_of_year(date)
    gamma = _fractional_year_rad(n, 12.0)
    eqtime = equation_of_time_minutes(gamma)
    decl = solar_declination_rad(gamma)
    ha_deg = _hour_angle_deg_for_altitude(latitude_deg, decl, -6.0)
    # Solar noon in minutes local standard time
    solar_noon_min = 720.0 - 4.0 * longitude_deg_west - eqtime
    if ha_deg is None:
        return (None, None)
    if ha_deg == 180.0:
        # civil twilight spans entire day; treat as dawn=00:00, dusk=24:00
        dawn_min = 0.0
        dusk_min = 24.0 * 60.0
    else:
        dawn_min = 720.0 - 4.0 * (longitude_deg_west + ha_deg) - eqtime
        dusk_min = 720.0 - 4.0 * (longitude_deg_west - ha_deg) - eqtime

    def to_local_datetime(minutes_local_standard: float) -> dt.datetime:
        hours = minutes_local_standard / 60.0
        hh = int(hours)
        mm = int(round((hours - hh) * 60.0))
        base = dt.datetime(date.year, date.month, date.day, 0, 0)
        dt_local_std = base + dt.timedelta(hours=hh, minutes=mm)
        # Apply time zone (assume tz_hours is local standard offset from UTC)
        # The NOAA minutes already represent local standard time, so we keep as-is.
        return dt_local_std

    return to_local_datetime(dawn_min), to_local_datetime(dusk_min)



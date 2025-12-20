"""
Garmin Connect import helpers (Vivosmart 5 and similar) using python-garminconnect.

This module:
- Authenticates with Garmin Connect using GARMIN_EMAIL / GARMIN_PASSWORD.
- Fetches daily wellness metrics (sleep, HRV, resting HR, stress, activity, SpO2, respiration, body battery).
- Normalizes into GarminDailyMetrics records for persistence.
"""

from __future__ import annotations

import os
from dataclasses import asdict
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

import pandas as pd

try:
    from garminconnect import (  # type: ignore
        Garmin,
        GarminConnectAuthenticationError,
        GarminConnectConnectionError,
        GarminConnectTooManyRequestsError,
    )

    GARMIN_LIB_AVAILABLE = True
except Exception:  # pragma: no cover - optional dependency
    Garmin = None  # type: ignore
    GarminConnectAuthenticationError = Exception  # type: ignore
    GarminConnectConnectionError = Exception  # type: ignore
    GarminConnectTooManyRequestsError = Exception  # type: ignore
    GARMIN_LIB_AVAILABLE = False

from user_database import GarminDailyMetrics


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


class GarminAuthError(RuntimeError):
    """Raised when Garmin authentication is unavailable or fails."""


def _env_credentials() -> Tuple[str, str]:
    email = os.getenv("GARMIN_EMAIL")
    password = os.getenv("GARMIN_PASSWORD")
    if not email or not password:
        raise GarminAuthError("GARMIN_EMAIL/GARMIN_PASSWORD not configured in environment.")
    return email, password


def _safe_float(val: Any) -> Optional[float]:
    try:
        f = float(val)
    except (TypeError, ValueError):
        return None
    return f if pd.notna(f) else None


def _safe_int(val: Any) -> Optional[int]:
    try:
        i = int(val)
    except (TypeError, ValueError):
        return None
    return i


class GarminConnectClient:
    """Context-managed Garmin client with defensive login."""

    def __init__(self) -> None:
        self.client: Optional[Garmin] = None

    def __enter__(self) -> Garmin:
        if not GARMIN_LIB_AVAILABLE:
            raise GarminAuthError("python-garminconnect is not installed (see requirements.txt).")
        email, password = _env_credentials()
        try:
            self.client = Garmin(email=email, password=password, is_cn=False, return_on_mfa=True)  # type: ignore[arg-type]
            self.client.login()
        except GarminConnectAuthenticationError as exc:
            raise GarminAuthError(f"Garmin authentication failed: {exc}") from exc
        except GarminConnectConnectionError as exc:
            raise GarminAuthError(f"Garmin connection error: {exc}") from exc
        except GarminConnectTooManyRequestsError as exc:
            raise GarminAuthError(f"Garmin rate limit reached: {exc}") from exc
        except Exception as exc:  # pragma: no cover - defensive
            raise GarminAuthError(f"Garmin login failed: {exc}") from exc
        return self.client

    def __exit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        try:
            if self.client:
                self.client.logout()
        except Exception:
            # Ignore logout failures
            pass


# -----------------------------------------------------------------------------
# Normalization helpers
# -----------------------------------------------------------------------------


def _extract_sleep(sleep_payload: Any) -> Dict[str, Any]:
    """Parse sleep payload to duration (h), efficiency (0..1), score (0..100), start/end UTC ISO."""
    if not sleep_payload:
        return {}
    if isinstance(sleep_payload, dict) and "dailySleepDTO" in sleep_payload:
        main = sleep_payload.get("dailySleepDTO") or {}
    else:
        main = sleep_payload if isinstance(sleep_payload, dict) else {}

    duration_s = (
        main.get("sleepDurationInSeconds")
        or main.get("durationInSeconds")
        or main.get("sleepTimeSeconds")
        or main.get("duration")
    )
    efficiency = main.get("sleepEfficiency")
    score = (
        main.get("sleepScore")
        or main.get("overallScore")
        or (main.get("sleepScores", {}).get("qualifiers"))  # some payloads
    )
    start_ts = main.get("sleepStartTimestampGMT") or main.get("sleepStartTimestamp")
    end_ts = main.get("sleepEndTimestampGMT") or main.get("sleepEndTimestamp")

    def _to_iso(ts_val: Any) -> Optional[str]:
        if ts_val is None:
            return None
        try:
            # Garmin often returns milliseconds
            ts_int = int(ts_val)
            if ts_int > 1e12:
                ts_dt = datetime.fromtimestamp(ts_int / 1000.0, tz=timezone.utc)
            else:
                ts_dt = datetime.fromtimestamp(ts_int, tz=timezone.utc)
            return ts_dt.isoformat()
        except Exception:
            return None

    sleep_start_utc = _to_iso(start_ts)
    sleep_end_utc = _to_iso(end_ts)
    duration_hours = None
    if duration_s:
        duration_hours = float(max(0.0, _safe_float(duration_s) or 0.0) / 3600.0)

    eff = _safe_float(efficiency)
    if eff is not None and eff > 1.2:
        eff = eff / 100.0

    return {
        "sleep_duration_hours": duration_hours,
        "sleep_efficiency": eff,
        "sleep_score": _safe_float(score),
        "sleep_start_utc": sleep_start_utc,
        "sleep_end_utc": sleep_end_utc,
    }


def _extract_stress(stress_payload: Any) -> Optional[float]:
    if not stress_payload:
        return None
    if isinstance(stress_payload, dict):
        for key in ("overallStressLevel", "averageStressLevel", "avgStressLevel"):
            val = stress_payload.get(key)
            if val is not None:
                return _safe_float(val)
    if isinstance(stress_payload, list) and stress_payload:
        try:
            first = stress_payload[0]
            if isinstance(first, dict):
                return _safe_float(first.get("overallStressLevel") or first.get("stressLevel"))
        except Exception:
            return None
    return None


def _extract_body_battery(body_payload: Any) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    """Return (avg, charge, drain)."""
    if not body_payload:
        return None, None, None
    levels: List[float] = []
    charge: Optional[float] = None
    drain: Optional[float] = None
    try:
        if isinstance(body_payload, list):
            for row in body_payload:
                lvl = _safe_float(row.get("bodyBatteryValue") or row.get("batteryLevel") or row.get("bodyBatteryLevel"))
                if lvl is not None:
                    levels.append(lvl)
                if charge is None:
                    charge = _safe_float(row.get("charged"))
                if drain is None:
                    drain = _safe_float(row.get("drained"))
        elif isinstance(body_payload, dict):
            levels.append(_safe_float(body_payload.get("bodyBatteryValue") or body_payload.get("batteryLevel")) or 0.0)
            charge = _safe_float(body_payload.get("charged"))
            drain = _safe_float(body_payload.get("drained"))
    except Exception:
        return None, None, None
    avg_level = float(pd.Series(levels).mean()) if levels else None
    return avg_level, charge, drain


def _extract_respiration(resp_payload: Any) -> Tuple[Optional[float], Optional[float]]:
    awake = None
    sleep = None
    if isinstance(resp_payload, dict):
        awake = _safe_float(resp_payload.get("awakeRespirationAvg"))
        sleep = _safe_float(resp_payload.get("sleepRespirationAvg"))
    elif isinstance(resp_payload, list) and resp_payload:
        try:
            first = resp_payload[0]
            if isinstance(first, dict):
                awake = _safe_float(first.get("awakeRespirationAvg"))
                sleep = _safe_float(first.get("sleepRespirationAvg"))
        except Exception:
            return None, None
    return awake, sleep


def _extract_spo2(spo_payload: Any) -> Optional[float]:
    if isinstance(spo_payload, dict):
        return _safe_float(
            spo_payload.get("avgSpO2Value")
            or spo_payload.get("avgSpO2")
            or spo_payload.get("averageSpO2")
            or spo_payload.get("spo2Value")
        )
    if isinstance(spo_payload, list) and spo_payload:
        try:
            first = spo_payload[0]
            if isinstance(first, dict):
                return _safe_float(first.get("avgSpO2Value") or first.get("averageSpO2") or first.get("avgSpO2"))
        except Exception:
            return None
    return None


def _extract_hrv(hrv_payload: Any) -> Tuple[Optional[float], Optional[float]]:
    rmssd = None
    sdnn = None
    if isinstance(hrv_payload, dict):
        rmssd = _safe_float(
            hrv_payload.get("rmssd") or hrv_payload.get("hrvRmssd") or hrv_payload.get("lastNightAvgRmssd")
        )
        sdnn = _safe_float(hrv_payload.get("sdnn") or hrv_payload.get("hrvSdnn"))
    elif isinstance(hrv_payload, list) and hrv_payload:
        try:
            first = hrv_payload[0] if isinstance(hrv_payload[0], dict) else None
            if first:
                rmssd = _safe_float(first.get("rmssd") or first.get("hrvRmssd"))
                sdnn = _safe_float(first.get("sdnn") or first.get("hrvSdnn"))
        except Exception:
            return None, None
    return rmssd, sdnn


# -----------------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------------


def fetch_garmin_daily_metrics(user_id: str, days: int = 14) -> List[GarminDailyMetrics]:
    """
    Fetch daily Garmin metrics for the last N days (inclusive of today).

    Returns a list of GarminDailyMetrics ready for persistence.
    """
    if not user_id:
        raise ValueError("user_id is required to fetch Garmin metrics.")
    if days <= 0:
        return []

    start_date = date.today() - timedelta(days=days - 1)
    records: List[GarminDailyMetrics] = []
    now_iso = datetime.now(timezone.utc).isoformat()

    with GarminConnectClient() as client:
        for idx in range(days):
            day = start_date + timedelta(days=idx)
            day_iso = day.isoformat()

            # Activity + heart
            summary = {}
            try:
                summary = client.get_user_summary(day_iso) or {}
            except Exception:
                summary = {}

            steps = _safe_int(summary.get("totalSteps"))
            distance_km = None
            dist_m = summary.get("totalDistanceMeters") or summary.get("distance")
            if dist_m is not None:
                distance_km = _safe_float(dist_m)
                if distance_km is not None:
                    distance_km = distance_km / 1000.0
            calories = _safe_float(summary.get("totalKilocalories") or summary.get("totalCalories"))
            avg_hr = _safe_float(summary.get("averageHR") or summary.get("averageHeartRate"))
            resting_hr = _safe_float(summary.get("restingHeartRate") or summary.get("restingHR"))

            # Sleep
            sleep_info: Dict[str, Any] = {}
            try:
                sleep_payload = client.get_sleep_data(day_iso)
                sleep_info = _extract_sleep(sleep_payload)
            except Exception:
                sleep_info = {}

            # Stress
            stress_score = None
            try:
                stress_payload = client.get_all_day_stress(day_iso)
                stress_score = _extract_stress(stress_payload)
            except Exception:
                stress_score = None

            # Respiration
            resp_awake = None
            resp_sleep = None
            try:
                resp_payload = client.get_respiration_data(day_iso)
                resp_awake, resp_sleep = _extract_respiration(resp_payload)
            except Exception:
                resp_awake, resp_sleep = None, None

            # SpO2
            spo2_avg = None
            try:
                spo2_payload = client.get_spo2_data(day_iso)
                spo2_avg = _extract_spo2(spo2_payload)
            except Exception:
                spo2_avg = None

            # Body battery
            body_avg = None
            body_charge = None
            body_drain = None
            try:
                body_payload = client.get_body_battery(day_iso)
                body_avg, body_charge, body_drain = _extract_body_battery(body_payload)
            except Exception:
                body_avg, body_charge, body_drain = None, None, None

            # HRV (nightly)
            hrv_rmssd = None
            hrv_sdnn = None
            try:
                hrv_payload = client.get_hrv_data(day_iso)
                hrv_rmssd, hrv_sdnn = _extract_hrv(hrv_payload)
            except Exception:
                hrv_rmssd, hrv_sdnn = None, None

            records.append(
                GarminDailyMetrics(
                    entry_id="",
                    user_id=user_id,
                    metric_date=day_iso,
                    steps=steps,
                    distance_km=distance_km,
                    calories_kcal=calories,
                    avg_hr_bpm=avg_hr,
                    resting_hr_bpm=resting_hr,
                    stress_score=stress_score,
                    sleep_score=sleep_info.get("sleep_score"),
                    sleep_efficiency=sleep_info.get("sleep_efficiency"),
                    sleep_duration_hours=sleep_info.get("sleep_duration_hours"),
                    sleep_start_utc=sleep_info.get("sleep_start_utc"),
                    sleep_end_utc=sleep_info.get("sleep_end_utc"),
                    avg_spo2=spo2_avg,
                    avg_respiration_awake=resp_awake,
                    avg_respiration_sleep=resp_sleep,
                    hrv_rmssd_ms=hrv_rmssd,
                    hrv_sdnn_ms=hrv_sdnn,
                    body_battery_avg=body_avg,
                    body_battery_charge=body_charge,
                    body_battery_drain=body_drain,
                    source="garmin_connect_api",
                    created_at=now_iso,
                )
            )

    return records


def summarize_garmin_daily(records: Iterable[GarminDailyMetrics]) -> Dict[str, Any]:
    """Small helper to produce a user-facing summary."""
    recs = list(records)
    if not recs:
        return {"count": 0}
    df = pd.DataFrame([asdict(r) for r in recs])
    return {
        "count": len(recs),
        "dates": (
            f"{pd.to_datetime(df['metric_date']).min().date().isoformat()} → "
            f"{pd.to_datetime(df['metric_date']).max().date().isoformat()}"
        ),
        "steps_mean": _safe_float(pd.to_numeric(df.get("steps"), errors="coerce").mean()),
        "sleep_hours_mean": _safe_float(pd.to_numeric(df.get("sleep_duration_hours"), errors="coerce").mean()),
        "resting_hr_mean": _safe_float(pd.to_numeric(df.get("resting_hr_bpm"), errors="coerce").mean()),
    }

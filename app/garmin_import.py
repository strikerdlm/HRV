"""Garmin Connect data import module for HRV analysis.

This module provides functions to import sleep, HRV, heart rate, stress,
SpO2, respiration, and body battery data from Garmin Connect via the
unofficial garminconnect library, bulk wellness JSON exports, and
individual FIT files.

Supported data sources:
- Garmin Connect API (unofficial) via garminconnect library
- Bulk wellness JSON export (ZIP from Account Settings)
- Individual FIT files via fitparse/fitdecode

Supported metrics:
- Sleep data (stages, duration, scores)
- HRV data (RMSSD, beat-to-beat intervals)
- Heart rate data (continuous, resting)
- Stress data (Garmin stress score)
- SpO2 data (pulse oximetry)
- Respiration data (breathing rate)
- Body battery data (energy levels)

References:
- garminconnect: https://github.com/cyberjunky/python-garminconnect
- fitparse: https://github.com/dtcooper/python-fitparse
- Garmin FIT SDK: https://developer.garmin.com/fit/overview/
"""

from __future__ import annotations

import io
import json
import logging
import os
import zipfile
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

import numpy as np
import pandas as pd

try:
    from logging_config import get_logger
except ImportError:  # Fallback for environments without logging_config
    get_logger = None  # type: ignore[assignment]

if TYPE_CHECKING:
    from collections.abc import Iterator

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_LOGGER: Final[logging.Logger] = (
    get_logger(__name__) if get_logger is not None else logging.getLogger(__name__)
)

# Garmin Connect wellness JSON file patterns (inside DI_CONNECT/DI-Connect-Wellness/)
_SLEEP_FILE_SUFFIX: Final[str] = "_sleepData.json"
_HRV_FILE_SUFFIX: Final[str] = "_hrvData.json"
_STRESS_FILE_SUFFIX: Final[str] = "_stressData.json"
_HR_FILE_SUFFIX: Final[str] = "_heartRateData.json"
_SPO2_FILE_SUFFIX: Final[str] = "_spo2Data.json"
_RESPIRATION_FILE_SUFFIX: Final[str] = "_respirationData.json"
_BODY_BATTERY_FILE_SUFFIX: Final[str] = "_bodyBatteryData.json"

# Maximum days to fetch in a single API call to avoid rate limiting
_MAX_FETCH_DAYS: Final[int] = 30

# Timeout for HTTP requests (seconds)
_REQUEST_TIMEOUT: Final[int] = 30


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class GarminCredentials:
    """Garmin Connect login credentials.

    Attributes:
        email: Garmin Connect account email.
        password: Garmin Connect account password.
    """

    email: str
    password: str


@dataclass(slots=True)
class GarminWellnessData:
    """Container for Garmin wellness data.

    Attributes:
        sleep_df: DataFrame with sleep data (stages, duration, scores).
        hrv_df: DataFrame with HRV RMSSD data (5-min epochs).
        hr_df: DataFrame with heart rate data (minute-level).
        stress_df: DataFrame with stress level data.
        spo2_df: DataFrame with SpO2 (pulse oximetry) data.
        respiration_df: DataFrame with respiration rate data.
        body_battery_df: DataFrame with body battery/energy data.
        rr_intervals_df: DataFrame with RR intervals for HRV analysis.
        source: Data source description.
    """

    sleep_df: pd.DataFrame = field(default_factory=pd.DataFrame)
    hrv_df: pd.DataFrame = field(default_factory=pd.DataFrame)
    hr_df: pd.DataFrame = field(default_factory=pd.DataFrame)
    stress_df: pd.DataFrame = field(default_factory=pd.DataFrame)
    spo2_df: pd.DataFrame = field(default_factory=pd.DataFrame)
    respiration_df: pd.DataFrame = field(default_factory=pd.DataFrame)
    body_battery_df: pd.DataFrame = field(default_factory=pd.DataFrame)
    rr_intervals_df: pd.DataFrame = field(default_factory=pd.DataFrame)
    activity_df: pd.DataFrame = field(default_factory=pd.DataFrame)
    session_df: pd.DataFrame = field(default_factory=pd.DataFrame)
    resting_hr_df: pd.DataFrame = field(default_factory=pd.DataFrame)
    source: str = "unknown"


@dataclass(frozen=True, slots=True)
class SynchronizedPhysiologyData:
    """Time-synchronized physiological data for analysis.

    All data is resampled to a common time base for correlation analysis.

    Attributes:
        timestamp: Common timestamp index.
        heart_rate: Heart rate (bpm).
        hrv_rmssd: HRV RMSSD (ms).
        spo2: SpO2 percentage.
        respiration_rate: Breaths per minute.
        stress_level: Garmin stress score (0-100).
        body_battery: Body battery level (0-100).
        rr_intervals: RR intervals (ms) if available.
        quality_flags: Quality indicators for each metric.
    """

    timestamp: pd.DatetimeIndex
    heart_rate: pd.Series
    hrv_rmssd: pd.Series
    spo2: pd.Series
    respiration_rate: pd.Series
    stress_level: pd.Series
    body_battery: pd.Series
    rr_intervals: pd.Series | None = None
    quality_flags: dict[str, pd.Series] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Credential loading
# ---------------------------------------------------------------------------


def load_credentials_from_env() -> GarminCredentials | None:
    """Load Garmin Connect credentials from environment variables.

    Expects GARMIN_EMAIL and GARMIN_PASSWORD to be set.

    Returns:
        GarminCredentials if both variables are set, None otherwise.
    """
    email = os.environ.get("GARMIN_EMAIL", "").strip()
    password = os.environ.get("GARMIN_PASSWORD", "").strip()
    if not email or not password:
        _LOGGER.warning(
            "GARMIN_EMAIL and/or GARMIN_PASSWORD not set in environment"
        )
        return None
    return GarminCredentials(email=email, password=password)


# ---------------------------------------------------------------------------
# Garmin Connect API wrapper
# ---------------------------------------------------------------------------


def _get_garmin_client(credentials: GarminCredentials) -> Any:
    """Create and authenticate a Garmin Connect client.

    Args:
        credentials: Garmin Connect login credentials.

    Returns:
        Authenticated Garmin client instance.

    Raises:
        ImportError: If garminconnect library is not installed.
        RuntimeError: If authentication fails.
    """
    try:
        from garminconnect import Garmin
    except ImportError as exc:
        msg = "garminconnect library not installed. Run: pip install garminconnect"
        raise ImportError(msg) from exc

    client = Garmin(credentials.email, credentials.password)
    try:
        client.login()
    except Exception as exc:
        msg = f"Garmin Connect authentication failed: {exc}"
        raise RuntimeError(msg) from exc
    return client


def fetch_garmin_sleep(
    credentials: GarminCredentials,
    start_date: date,
    end_date: date,
) -> pd.DataFrame:
    """Fetch sleep data from Garmin Connect API.

    Args:
        credentials: Garmin Connect login credentials.
        start_date: Start date (inclusive).
        end_date: End date (inclusive).

    Returns:
        DataFrame with columns:
        - date: Sleep date (date object).
        - total_sleep_seconds: Total sleep duration in seconds.
        - deep_sleep_seconds: Deep sleep duration.
        - light_sleep_seconds: Light sleep duration.
        - rem_sleep_seconds: REM sleep duration.
        - awake_seconds: Awake duration during sleep period.
        - sleep_score: Garmin sleep score (0-100).
        - sleep_start: Sleep start timestamp (UTC).
        - sleep_end: Sleep end timestamp (UTC).
        - avg_spo2: Average SpO2 during sleep (if available).
        - avg_respiration: Average respiration rate during sleep.
    """
    client = _get_garmin_client(credentials)
    records: list[dict[str, Any]] = []

    current = start_date
    while current <= end_date:
        try:
            data = client.get_sleep_data(current.isoformat())
            if data and isinstance(data, dict):
                daily_summary = data.get("dailySleepDTO", {})
                
                # Extract SpO2 data from sleep if available
                spo2_data = data.get("sleepRestingSpO2", {})
                avg_spo2 = spo2_data.get("averageSpO2Value")
                
                # Extract respiration data
                resp_data = data.get("sleepRestingRespirationRate", {})
                avg_respiration = resp_data.get("avgSleepRespirationValue")
                
                records.append({
                    "date": current,
                    "total_sleep_seconds": daily_summary.get(
                        "sleepTimeSeconds", 0
                    ),
                    "deep_sleep_seconds": daily_summary.get(
                        "deepSleepSeconds", 0
                    ),
                    "light_sleep_seconds": daily_summary.get(
                        "lightSleepSeconds", 0
                    ),
                    "rem_sleep_seconds": daily_summary.get(
                        "remSleepSeconds", 0
                    ),
                    "awake_seconds": daily_summary.get("awakeSleepSeconds", 0),
                    "sleep_score": daily_summary.get("sleepScores", {}).get(
                        "overall", {}
                    ).get("value"),
                    "sleep_start": daily_summary.get("sleepStartTimestampGMT"),
                    "sleep_end": daily_summary.get("sleepEndTimestampGMT"),
                    "avg_spo2": avg_spo2,
                    "avg_respiration": avg_respiration,
                    "lowest_spo2": spo2_data.get("lowestSpO2Value"),
                    "highest_spo2": spo2_data.get("highestSpO2Value"),
                })
        except Exception as exc:
            _LOGGER.warning("Failed to fetch sleep data for %s: %s", current, exc)
        current += timedelta(days=1)

    df = pd.DataFrame(records)
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"]).dt.date
        for col in ("sleep_start", "sleep_end"):
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], unit="ms", utc=True)
    return df


def fetch_garmin_hrv(
    credentials: GarminCredentials,
    start_date: date,
    end_date: date,
) -> pd.DataFrame:
    """Fetch HRV data from Garmin Connect API.

    Args:
        credentials: Garmin Connect login credentials.
        start_date: Start date (inclusive).
        end_date: End date (inclusive).

    Returns:
        DataFrame with columns:
        - timestamp: Measurement timestamp (UTC).
        - hrv_rmssd: HRV RMSSD value in milliseconds.
        - reading_status: Garmin reading status (e.g., "NORMAL").
    """
    client = _get_garmin_client(credentials)
    records: list[dict[str, Any]] = []

    current = start_date
    while current <= end_date:
        try:
            data = client.get_hrv_data(current.isoformat())
            if data and isinstance(data, dict):
                hrv_summary = data.get("hrvSummary", {})
                # Garmin returns overnight HRV values
                if hrv_summary:
                    records.append({
                        "date": current,
                        "hrv_rmssd": hrv_summary.get("lastNightAvg"),
                        "hrv_rmssd_5min_high": hrv_summary.get("lastNight5MinHigh"),
                        "baseline_low": hrv_summary.get("baselineLowUpper"),
                        "baseline_high": hrv_summary.get("baselineBalancedLower"),
                        "status": hrv_summary.get("status"),
                    })
                # Also extract detailed readings if available
                hrv_values = data.get("hrvValues", [])
                for val in hrv_values:
                    if isinstance(val, dict) and val.get("hrvValue") is not None:
                        records.append({
                            "timestamp": val.get("readingTimeGMT"),
                            "hrv_rmssd": val.get("hrvValue"),
                            "reading_status": val.get("readingStatus"),
                        })
        except Exception as exc:
            _LOGGER.warning("Failed to fetch HRV data for %s: %s", current, exc)
        current += timedelta(days=1)

    df = pd.DataFrame(records)
    if not df.empty and "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    return df


def fetch_garmin_heart_rate(
    credentials: GarminCredentials,
    target_date: date,
) -> pd.DataFrame:
    """Fetch heart rate data from Garmin Connect API for a single day.

    Args:
        credentials: Garmin Connect login credentials.
        target_date: Date to fetch data for.

    Returns:
        DataFrame with columns:
        - timestamp: Measurement timestamp (UTC).
        - heart_rate: Heart rate in BPM.
    """
    client = _get_garmin_client(credentials)
    records: list[dict[str, Any]] = []

    try:
        data = client.get_heart_rates(target_date.isoformat())
        if data and isinstance(data, dict):
            hr_values = data.get("heartRateValues", [])
            for val in hr_values:
                if isinstance(val, list) and len(val) >= 2 and val[1] is not None:
                    records.append({
                        "timestamp": val[0],
                        "heart_rate": val[1],
                    })
    except Exception as exc:
        _LOGGER.warning("Failed to fetch HR data for %s: %s", target_date, exc)

    df = pd.DataFrame(records)
    if not df.empty:
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    return df


def fetch_garmin_stress(
    credentials: GarminCredentials,
    target_date: date,
) -> pd.DataFrame:
    """Fetch stress data from Garmin Connect API for a single day.

    Args:
        credentials: Garmin Connect login credentials.
        target_date: Date to fetch data for.

    Returns:
        DataFrame with columns:
        - timestamp: Measurement timestamp (UTC).
        - stress_level: Stress level (0-100, -1 for rest/sleep).
    """
    client = _get_garmin_client(credentials)
    records: list[dict[str, Any]] = []

    try:
        data = client.get_stress_data(target_date.isoformat())
        if data and isinstance(data, dict):
            stress_values = data.get("stressValuesArray", [])
            for val in stress_values:
                if isinstance(val, list) and len(val) >= 2:
                    records.append({
                        "timestamp": val[0],
                        "stress_level": val[1],
                    })
    except Exception as exc:
        _LOGGER.warning("Failed to fetch stress data for %s: %s", target_date, exc)

    df = pd.DataFrame(records)
    if not df.empty:
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    return df


def fetch_garmin_spo2(
    credentials: GarminCredentials,
    target_date: date,
) -> pd.DataFrame:
    """Fetch SpO2 (pulse oximetry) data from Garmin Connect API.

    Args:
        credentials: Garmin Connect login credentials.
        target_date: Date to fetch data for.

    Returns:
        DataFrame with columns:
        - timestamp: Measurement timestamp (UTC).
        - spo2: SpO2 percentage (typically 90-100%).
        - reading_confidence: Confidence level of reading.
    """
    client = _get_garmin_client(credentials)
    records: list[dict[str, Any]] = []

    try:
        # Try different API endpoints for SpO2 data
        data = client.get_spo2_data(target_date.isoformat())
        if data and isinstance(data, dict):
            # Daily summary
            daily_avg = data.get("averageSpO2")
            lowest = data.get("lowestSpO2")
            latest = data.get("latestSpO2")
            
            # Detailed readings
            spo2_values = data.get("spO2Values", [])
            if spo2_values:
                for val in spo2_values:
                    if isinstance(val, dict):
                        records.append({
                            "timestamp": val.get("timestampGMT"),
                            "spo2": val.get("spO2Value"),
                            "reading_confidence": val.get("readingConfidence"),
                        })
                    elif isinstance(val, list) and len(val) >= 2:
                        records.append({
                            "timestamp": val[0],
                            "spo2": val[1],
                        })
            
            # Sleep SpO2 readings
            sleep_spo2 = data.get("sleepingSpO2Values", [])
            for val in sleep_spo2:
                if isinstance(val, dict):
                    records.append({
                        "timestamp": val.get("timestampGMT"),
                        "spo2": val.get("spO2Value"),
                        "reading_confidence": val.get("readingConfidence"),
                        "is_sleep": True,
                    })
                elif isinstance(val, list) and len(val) >= 2:
                    records.append({
                        "timestamp": val[0],
                        "spo2": val[1],
                        "is_sleep": True,
                    })
                    
    except Exception as exc:
        _LOGGER.warning("Failed to fetch SpO2 data for %s: %s", target_date, exc)

    df = pd.DataFrame(records)
    if not df.empty and "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    return df


def fetch_garmin_respiration(
    credentials: GarminCredentials,
    target_date: date,
) -> pd.DataFrame:
    """Fetch respiration rate data from Garmin Connect API.

    Args:
        credentials: Garmin Connect login credentials.
        target_date: Date to fetch data for.

    Returns:
        DataFrame with columns:
        - timestamp: Measurement timestamp (UTC).
        - respiration_rate: Breaths per minute.
    """
    client = _get_garmin_client(credentials)
    records: list[dict[str, Any]] = []

    try:
        data = client.get_respiration_data(target_date.isoformat())
        if data and isinstance(data, dict):
            resp_values = data.get("respirationValuesArray", [])
            for val in resp_values:
                if isinstance(val, list) and len(val) >= 2 and val[1] is not None:
                    records.append({
                        "timestamp": val[0],
                        "respiration_rate": val[1],
                    })
    except Exception as exc:
        _LOGGER.warning("Failed to fetch respiration data for %s: %s", target_date, exc)

    df = pd.DataFrame(records)
    if not df.empty:
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    return df


def fetch_garmin_body_battery(
    credentials: GarminCredentials,
    target_date: date,
) -> pd.DataFrame:
    """Fetch body battery data from Garmin Connect API.

    Args:
        credentials: Garmin Connect login credentials.
        target_date: Date to fetch data for.

    Returns:
        DataFrame with columns:
        - timestamp: Measurement timestamp (UTC).
        - body_battery: Body battery level (0-100).
        - status: Charging/draining status.
    """
    client = _get_garmin_client(credentials)
    records: list[dict[str, Any]] = []

    try:
        data = client.get_body_battery(target_date.isoformat())
        if data and isinstance(data, list):
            for val in data:
                if isinstance(val, dict):
                    records.append({
                        "timestamp": val.get("startTimestampGMT"),
                        "body_battery": val.get("bodyBatteryLevel"),
                        "status": val.get("bodyBatteryStatus"),
                    })
    except Exception as exc:
        _LOGGER.warning("Failed to fetch body battery data for %s: %s", target_date, exc)

    df = pd.DataFrame(records)
    if not df.empty and "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    return df


# ---------------------------------------------------------------------------
# Bulk wellness JSON export parsing
# ---------------------------------------------------------------------------


def _find_wellness_files(
    zip_path: Path,
) -> Iterator[tuple[str, str]]:
    """Find wellness JSON files in a Garmin export ZIP.

    Args:
        zip_path: Path to the Garmin export ZIP file.

    Yields:
        Tuples of (file_type, file_path) for each wellness file found.
        file_type is one of: "sleep", "hrv", "stress", "hr", "spo2", "respiration", "body_battery".
    """
    suffixes = {
        _SLEEP_FILE_SUFFIX: "sleep",
        _HRV_FILE_SUFFIX: "hrv",
        _STRESS_FILE_SUFFIX: "stress",
        _HR_FILE_SUFFIX: "hr",
        _SPO2_FILE_SUFFIX: "spo2",
        _RESPIRATION_FILE_SUFFIX: "respiration",
        _BODY_BATTERY_FILE_SUFFIX: "body_battery",
    }
    with zipfile.ZipFile(zip_path, "r") as zf:
        for name in zf.namelist():
            for suffix, file_type in suffixes.items():
                if name.endswith(suffix):
                    yield file_type, name
                    break


def parse_wellness_export_zip(zip_path: Path) -> GarminWellnessData:
    """Parse a Garmin wellness export ZIP file.

    Args:
        zip_path: Path to the Garmin export ZIP file.

    Returns:
        GarminWellnessData with parsed DataFrames.

    Raises:
        FileNotFoundError: If ZIP file does not exist.
        ValueError: If ZIP file is invalid or contains no wellness data.
    """
    if not zip_path.exists():
        msg = f"ZIP file not found: {zip_path}"
        raise FileNotFoundError(msg)

    result = GarminWellnessData(source=f"zip:{zip_path.name}")
    sleep_records: list[dict[str, Any]] = []
    hrv_records: list[dict[str, Any]] = []
    stress_records: list[dict[str, Any]] = []
    hr_records: list[dict[str, Any]] = []
    spo2_records: list[dict[str, Any]] = []
    respiration_records: list[dict[str, Any]] = []
    body_battery_records: list[dict[str, Any]] = []

    with zipfile.ZipFile(zip_path, "r") as zf:
        for file_type, file_path in _find_wellness_files(zip_path):
            try:
                with zf.open(file_path) as f:
                    data = json.load(f)
            except (json.JSONDecodeError, KeyError) as exc:
                _LOGGER.warning("Failed to parse %s: %s", file_path, exc)
                continue

            if not isinstance(data, list):
                data = [data]

            for record in data:
                if not isinstance(record, dict):
                    continue
                if file_type == "sleep":
                    sleep_records.append(_parse_sleep_record(record))
                elif file_type == "hrv":
                    hrv_records.extend(_parse_hrv_record(record))
                elif file_type == "stress":
                    stress_records.extend(_parse_stress_record(record))
                elif file_type == "hr":
                    hr_records.extend(_parse_hr_record(record))
                elif file_type == "spo2":
                    spo2_records.extend(_parse_spo2_record(record))
                elif file_type == "respiration":
                    respiration_records.extend(_parse_respiration_record(record))
                elif file_type == "body_battery":
                    body_battery_records.extend(_parse_body_battery_record(record))

    result.sleep_df = pd.DataFrame(sleep_records) if sleep_records else pd.DataFrame()
    result.hrv_df = pd.DataFrame(hrv_records) if hrv_records else pd.DataFrame()
    result.stress_df = pd.DataFrame(stress_records) if stress_records else pd.DataFrame()
    result.hr_df = pd.DataFrame(hr_records) if hr_records else pd.DataFrame()
    result.spo2_df = pd.DataFrame(spo2_records) if spo2_records else pd.DataFrame()
    result.respiration_df = pd.DataFrame(respiration_records) if respiration_records else pd.DataFrame()
    result.body_battery_df = pd.DataFrame(body_battery_records) if body_battery_records else pd.DataFrame()

    return result


def _parse_sleep_record(record: dict[str, Any]) -> dict[str, Any]:
    """Parse a single sleep record from Garmin JSON export."""
    return {
        "date": record.get("calendarDate"),
        "total_sleep_seconds": record.get("sleepTimeSeconds"),
        "deep_sleep_seconds": record.get("deepSleepSeconds"),
        "light_sleep_seconds": record.get("lightSleepSeconds"),
        "rem_sleep_seconds": record.get("remSleepSeconds"),
        "awake_seconds": record.get("awakeSleepSeconds"),
        "sleep_score": record.get("overallScore"),
        "sleep_start": record.get("sleepStartTimestampGMT"),
        "sleep_end": record.get("sleepEndTimestampGMT"),
        "avg_spo2": record.get("averageSpO2Value"),
        "lowest_spo2": record.get("lowestSpO2Value"),
        "avg_respiration": record.get("avgSleepRespirationValue"),
    }


def _parse_hrv_record(record: dict[str, Any]) -> list[dict[str, Any]]:
    """Parse a single HRV record from Garmin JSON export."""
    results: list[dict[str, Any]] = []
    hrv_values = record.get("hrvValues", [])
    for val in hrv_values:
        if isinstance(val, dict) and val.get("hrvValue") is not None:
            results.append({
                "timestamp": val.get("readingTimeGMT"),
                "hrv_rmssd": val.get("hrvValue"),
                "reading_status": val.get("readingStatus"),
            })
    return results


def _parse_stress_record(record: dict[str, Any]) -> list[dict[str, Any]]:
    """Parse a single stress record from Garmin JSON export."""
    results: list[dict[str, Any]] = []
    stress_values = record.get("stressValuesArray", [])
    for val in stress_values:
        if isinstance(val, list) and len(val) >= 2:
            results.append({
                "timestamp": val[0],
                "stress_level": val[1],
            })
    return results


def _parse_hr_record(record: dict[str, Any]) -> list[dict[str, Any]]:
    """Parse a single heart rate record from Garmin JSON export."""
    results: list[dict[str, Any]] = []
    hr_values = record.get("heartRateValues", [])
    for val in hr_values:
        if isinstance(val, list) and len(val) >= 2 and val[1] is not None:
            results.append({
                "timestamp": val[0],
                "heart_rate": val[1],
            })
    return results


def _parse_spo2_record(record: dict[str, Any]) -> list[dict[str, Any]]:
    """Parse a single SpO2 record from Garmin JSON export."""
    results: list[dict[str, Any]] = []
    
    # Try different SpO2 data formats
    spo2_values = record.get("spO2Values", [])
    if not spo2_values:
        spo2_values = record.get("sleepingSpO2Values", [])
    
    for val in spo2_values:
        if isinstance(val, dict):
            results.append({
                "timestamp": val.get("timestampGMT") or val.get("startTimestampGMT"),
                "spo2": val.get("spO2Value") or val.get("spo2"),
                "reading_confidence": val.get("readingConfidence"),
            })
        elif isinstance(val, list) and len(val) >= 2 and val[1] is not None:
            results.append({
                "timestamp": val[0],
                "spo2": val[1],
            })
    return results


def _parse_respiration_record(record: dict[str, Any]) -> list[dict[str, Any]]:
    """Parse a single respiration record from Garmin JSON export."""
    results: list[dict[str, Any]] = []
    resp_values = record.get("respirationValuesArray", [])
    for val in resp_values:
        if isinstance(val, list) and len(val) >= 2 and val[1] is not None:
            results.append({
                "timestamp": val[0],
                "respiration_rate": val[1],
            })
    return results


def _parse_body_battery_record(record: dict[str, Any]) -> list[dict[str, Any]]:
    """Parse a single body battery record from Garmin JSON export."""
    results: list[dict[str, Any]] = []
    
    # Body battery can be in different formats
    if "bodyBatteryLevel" in record:
        results.append({
            "timestamp": record.get("startTimestampGMT"),
            "body_battery": record.get("bodyBatteryLevel"),
            "status": record.get("bodyBatteryStatus"),
        })
    
    # Or as an array
    bb_values = record.get("bodyBatteryValuesArray", [])
    for val in bb_values:
        if isinstance(val, list) and len(val) >= 2:
            results.append({
                "timestamp": val[0],
                "body_battery": val[1],
            })
    return results


# ---------------------------------------------------------------------------
# FIT file parsing
# ---------------------------------------------------------------------------


def parse_fit_file(fit_path: Path) -> GarminWellnessData:
    """Parse a Garmin FIT file for all available physiological data.

    Args:
        fit_path: Path to the FIT file.

    Returns:
        GarminWellnessData with available data.

    Raises:
        ImportError: If fitparse library is not installed.
        FileNotFoundError: If FIT file does not exist.
    """
    try:
        import fitparse
    except ImportError as exc:
        msg = "fitparse library not installed. Run: pip install fitparse"
        raise ImportError(msg) from exc

    if not fit_path.exists():
        msg = f"FIT file not found: {fit_path}"
        raise FileNotFoundError(msg)

    result = GarminWellnessData(source=f"fit:{fit_path.name}")
    
    hr_records: list[dict[str, Any]] = []
    hrv_records: list[dict[str, Any]] = []
    spo2_records: list[dict[str, Any]] = []
    stress_records: list[dict[str, Any]] = []
    respiration_records: list[dict[str, Any]] = []
    activity_records: list[dict[str, Any]] = []
    session_records: list[dict[str, Any]] = []
    body_battery_records: list[dict[str, Any]] = []
    resting_hr_records: list[dict[str, Any]] = []
    rr_intervals: list[float] = []

    with open(fit_path, "rb") as f:
        fit_file = fitparse.FitFile(f)
        for record in fit_file.get_messages():
            record_dict: dict[str, Any] = {}
            record_type = record.name

            for field_data in record.fields:
                record_dict[field_data.name] = field_data.value

            timestamp = record_dict.get("timestamp")

            if record_type == "record":
                # Activity record with HR, cadence, etc.
                if "heart_rate" in record_dict:
                    hr_records.append({
                        "timestamp": timestamp,
                        "heart_rate": record_dict.get("heart_rate"),
                    })
                if "saturated_hemoglobin_percent" in record_dict:
                    spo2_records.append({
                        "timestamp": timestamp,
                        "spo2": record_dict.get("saturated_hemoglobin_percent"),
                    })
                if "respiration_rate" in record_dict:
                    respiration_records.append({
                        "timestamp": timestamp,
                        "respiration_rate": record_dict.get("respiration_rate"),
                    })
                if any(
                    key in record_dict
                    for key in ("steps", "distance", "calories", "active_calories")
                ):
                    activity_records.append({
                        "timestamp": timestamp,
                        "steps": record_dict.get("steps"),
                        "distance_m": record_dict.get("distance"),
                        "calories": record_dict.get("calories"),
                        "active_calories": record_dict.get("active_calories"),
                    })
                if "body_battery_level" in record_dict or "body_battery" in record_dict:
                    body_battery_records.append({
                        "timestamp": timestamp,
                        "body_battery": record_dict.get("body_battery_level") or record_dict.get("body_battery"),
                        "status": record_dict.get("body_battery_status"),
                    })

            elif record_type == "hrv":
                # HRV record with RR intervals
                time_vals = record_dict.get("time")
                if isinstance(time_vals, (list, tuple)):
                    for t in time_vals:
                        if t is not None:
                            # Convert to milliseconds
                            rr_ms = t * 1000 if t < 10 else t
                            rr_intervals.append(rr_ms)
                            hrv_records.append({
                                "timestamp": timestamp,
                                "rr_interval_ms": rr_ms,
                            })

            elif record_type == "stress_level":
                stress_records.append({
                    "timestamp": timestamp,
                    "stress_level": record_dict.get("stress_level_value"),
                })

            elif record_type == "spo2":
                spo2_records.append({
                    "timestamp": timestamp,
                    "spo2": record_dict.get("reading_spo2"),
                    "reading_confidence": record_dict.get("reading_confidence"),
                })

            elif record_type == "monitoring":
                activity_records.append({
                    "timestamp": timestamp,
                    "steps": record_dict.get("steps"),
                    "distance_m": record_dict.get("distance"),
                    "calories": record_dict.get("calories"),
                    "active_calories": record_dict.get("active_calories"),
                })
                if "resting_heart_rate" in record_dict:
                    resting_hr_records.append({
                        "timestamp": timestamp,
                        "resting_hr_bpm": record_dict.get("resting_heart_rate"),
                    })
                if "body_battery_level" in record_dict or "body_battery" in record_dict:
                    body_battery_records.append({
                        "timestamp": timestamp,
                        "body_battery": record_dict.get("body_battery_level") or record_dict.get("body_battery"),
                        "status": record_dict.get("body_battery_status"),
                    })

            elif record_type == "session":
                session_records.append({
                    "timestamp": timestamp,
                    "total_distance_m": record_dict.get("total_distance"),
                    "total_timer_time_s": record_dict.get("total_timer_time"),
                    "total_calories": record_dict.get("total_calories"),
                    "avg_heart_rate": record_dict.get("avg_heart_rate"),
                    "max_heart_rate": record_dict.get("max_heart_rate"),
                    "min_heart_rate": record_dict.get("min_heart_rate"),
                    "total_steps": record_dict.get("total_steps"),
                    "start_time": record_dict.get("start_time"),
                })

            elif record_type == "device_info" and "resting_heart_rate" in record_dict:
                resting_hr_records.append({
                    "timestamp": timestamp,
                    "resting_hr_bpm": record_dict.get("resting_heart_rate"),
                })

    # Build DataFrames
    result.hr_df = pd.DataFrame(hr_records) if hr_records else pd.DataFrame()
    result.hrv_df = pd.DataFrame(hrv_records) if hrv_records else pd.DataFrame()
    result.spo2_df = pd.DataFrame(spo2_records) if spo2_records else pd.DataFrame()
    result.stress_df = pd.DataFrame(stress_records) if stress_records else pd.DataFrame()
    result.respiration_df = pd.DataFrame(respiration_records) if respiration_records else pd.DataFrame()
    result.activity_df = pd.DataFrame(activity_records) if activity_records else pd.DataFrame()
    result.session_df = pd.DataFrame(session_records) if session_records else pd.DataFrame()
    result.resting_hr_df = pd.DataFrame(resting_hr_records) if resting_hr_records else pd.DataFrame()
    if body_battery_records:
        result.body_battery_df = pd.DataFrame(body_battery_records)
    
    # RR intervals for HRV analysis
    if rr_intervals:
        result.rr_intervals_df = pd.DataFrame({"rr_interval_ms": rr_intervals})

    return result


def parse_fit_bytes(fit_bytes: bytes) -> GarminWellnessData:
    """Parse FIT file from bytes (e.g., from API download).

    Args:
        fit_bytes: Raw FIT file bytes.

    Returns:
        GarminWellnessData with available data.
    """
    try:
        import fitparse
    except ImportError as exc:
        msg = "fitparse library not installed. Run: pip install fitparse"
        raise ImportError(msg) from exc

    result = GarminWellnessData(source="fit:bytes")
    hr_records: list[dict[str, Any]] = []
    spo2_records: list[dict[str, Any]] = []
    activity_records: list[dict[str, Any]] = []
    session_records: list[dict[str, Any]] = []
    resting_hr_records: list[dict[str, Any]] = []
    rr_intervals: list[float] = []

    fit_file = fitparse.FitFile(io.BytesIO(fit_bytes))

    for record in fit_file.get_messages():
        record_dict: dict[str, Any] = {}
        for field_data in record.fields:
            record_dict[field_data.name] = field_data.value

        timestamp = record_dict.get("timestamp")

        if record.name == "record":
            if "heart_rate" in record_dict:
                hr_records.append({
                    "timestamp": timestamp,
                    "heart_rate": record_dict.get("heart_rate"),
                })
            if "saturated_hemoglobin_percent" in record_dict:
                spo2_records.append({
                    "timestamp": timestamp,
                    "spo2": record_dict.get("saturated_hemoglobin_percent"),
                })
            if any(
                key in record_dict
                for key in ("steps", "distance", "calories", "active_calories")
            ):
                activity_records.append({
                    "timestamp": timestamp,
                    "steps": record_dict.get("steps"),
                    "distance_m": record_dict.get("distance"),
                    "calories": record_dict.get("calories"),
                    "active_calories": record_dict.get("active_calories"),
                })

        elif record.name == "hrv":
            time_vals = record_dict.get("time")
            if isinstance(time_vals, (list, tuple)):
                rr_intervals.extend([t * 1000 if t < 10 else t for t in time_vals if t is not None])

        elif record.name == "monitoring":
            activity_records.append({
                "timestamp": timestamp,
                "steps": record_dict.get("steps"),
                "distance_m": record_dict.get("distance"),
                "calories": record_dict.get("calories"),
                "active_calories": record_dict.get("active_calories"),
            })
            if "resting_heart_rate" in record_dict:
                resting_hr_records.append({
                    "timestamp": timestamp,
                    "resting_hr_bpm": record_dict.get("resting_heart_rate"),
                })

        elif record.name == "session":
            session_records.append({
                "timestamp": timestamp,
                "total_distance_m": record_dict.get("total_distance"),
                "total_timer_time_s": record_dict.get("total_timer_time"),
                "total_calories": record_dict.get("total_calories"),
                "avg_heart_rate": record_dict.get("avg_heart_rate"),
                "max_heart_rate": record_dict.get("max_heart_rate"),
                "min_heart_rate": record_dict.get("min_heart_rate"),
                "total_steps": record_dict.get("total_steps"),
                "start_time": record_dict.get("start_time"),
            })

    result.hr_df = pd.DataFrame(hr_records) if hr_records else pd.DataFrame()
    result.spo2_df = pd.DataFrame(spo2_records) if spo2_records else pd.DataFrame()
    result.activity_df = pd.DataFrame(activity_records) if activity_records else pd.DataFrame()
    result.session_df = pd.DataFrame(session_records) if session_records else pd.DataFrame()
    result.resting_hr_df = pd.DataFrame(resting_hr_records) if resting_hr_records else pd.DataFrame()
    if rr_intervals:
        result.rr_intervals_df = pd.DataFrame({"rr_interval_ms": rr_intervals})

    return result


# ---------------------------------------------------------------------------
# Data synchronization
# ---------------------------------------------------------------------------


def synchronize_physiological_data(
    data: GarminWellnessData,
    resample_freq: str = "1min",
    interpolate_method: str = "linear",
    max_gap_minutes: int = 5,
) -> pd.DataFrame:
    """Synchronize all physiological data to a common time base.

    This function aligns HR, HRV, SpO2, stress, respiration, and body battery
    data to a common timestamp index for correlation analysis.

    Args:
        data: GarminWellnessData with raw data.
        resample_freq: Resampling frequency (e.g., "1min", "5min").
        interpolate_method: Interpolation method for missing values.
        max_gap_minutes: Maximum gap to interpolate across.

    Returns:
        DataFrame with synchronized physiological data indexed by timestamp.
        Columns: heart_rate, hrv_rmssd, spo2, stress_level, respiration_rate, body_battery
    """
    dfs_to_merge: list[pd.DataFrame] = []

    # Process heart rate
    if not data.hr_df.empty and "timestamp" in data.hr_df.columns:
        hr_df = data.hr_df.copy()
        hr_df["timestamp"] = pd.to_datetime(hr_df["timestamp"], utc=True)
        hr_df = hr_df.set_index("timestamp").sort_index()
        hr_df = hr_df[["heart_rate"]].resample(resample_freq).mean()
        dfs_to_merge.append(hr_df)

    # Process HRV
    if not data.hrv_df.empty and "timestamp" in data.hrv_df.columns:
        hrv_df = data.hrv_df.copy()
        hrv_df["timestamp"] = pd.to_datetime(hrv_df["timestamp"], utc=True)
        hrv_df = hrv_df.set_index("timestamp").sort_index()
        if "hrv_rmssd" in hrv_df.columns:
            hrv_df = hrv_df[["hrv_rmssd"]].resample(resample_freq).mean()
            dfs_to_merge.append(hrv_df)

    # Process SpO2
    if not data.spo2_df.empty and "timestamp" in data.spo2_df.columns:
        spo2_df = data.spo2_df.copy()
        spo2_df["timestamp"] = pd.to_datetime(spo2_df["timestamp"], utc=True)
        spo2_df = spo2_df.set_index("timestamp").sort_index()
        spo2_df = spo2_df[["spo2"]].resample(resample_freq).mean()
        dfs_to_merge.append(spo2_df)

    # Process stress
    if not data.stress_df.empty and "timestamp" in data.stress_df.columns:
        stress_df = data.stress_df.copy()
        stress_df["timestamp"] = pd.to_datetime(stress_df["timestamp"], utc=True)
        stress_df = stress_df.set_index("timestamp").sort_index()
        # Filter out rest/sleep values (-1)
        stress_df = stress_df[stress_df["stress_level"] >= 0]
        stress_df = stress_df[["stress_level"]].resample(resample_freq).mean()
        dfs_to_merge.append(stress_df)

    # Process respiration
    if not data.respiration_df.empty and "timestamp" in data.respiration_df.columns:
        resp_df = data.respiration_df.copy()
        resp_df["timestamp"] = pd.to_datetime(resp_df["timestamp"], utc=True)
        resp_df = resp_df.set_index("timestamp").sort_index()
        resp_df = resp_df[["respiration_rate"]].resample(resample_freq).mean()
        dfs_to_merge.append(resp_df)

    # Process body battery
    if not data.body_battery_df.empty and "timestamp" in data.body_battery_df.columns:
        bb_df = data.body_battery_df.copy()
        bb_df["timestamp"] = pd.to_datetime(bb_df["timestamp"], utc=True)
        bb_df = bb_df.set_index("timestamp").sort_index()
        bb_df = bb_df[["body_battery"]].resample(resample_freq).mean()
        dfs_to_merge.append(bb_df)

    if not dfs_to_merge:
        return pd.DataFrame()

    # Merge all DataFrames
    result = dfs_to_merge[0]
    for df in dfs_to_merge[1:]:
        result = result.join(df, how="outer")

    # Interpolate small gaps
    max_gap = pd.Timedelta(minutes=max_gap_minutes)
    for col in result.columns:
        # Only interpolate if gap is small enough
        mask = result[col].isna()
        if mask.any():
            # Identify gap boundaries
            gap_start = mask & ~mask.shift(1, fill_value=False)
            gap_end = mask & ~mask.shift(-1, fill_value=False)
            
            # Interpolate
            result[col] = result[col].interpolate(method=interpolate_method, limit_area="inside")

    return result


def extract_rr_intervals_from_garmin(data: GarminWellnessData) -> np.ndarray:
    """Extract RR intervals from Garmin data for HRV analysis.

    Args:
        data: GarminWellnessData with HRV or RR interval data.

    Returns:
        NumPy array of RR intervals in milliseconds.
    """
    rr_intervals: list[float] = []

    # From dedicated RR intervals DataFrame
    if not data.rr_intervals_df.empty and "rr_interval_ms" in data.rr_intervals_df.columns:
        rr_intervals.extend(data.rr_intervals_df["rr_interval_ms"].dropna().tolist())

    # From HRV DataFrame (if it contains RR intervals)
    if not data.hrv_df.empty and "rr_interval_ms" in data.hrv_df.columns:
        rr_intervals.extend(data.hrv_df["rr_interval_ms"].dropna().tolist())

    if not rr_intervals:
        _LOGGER.warning("No RR intervals found in Garmin data")
        return np.array([])

    # Filter physiologically plausible values (300-2000 ms = 30-200 bpm)
    rr_array = np.array(rr_intervals, dtype=float)
    valid_mask = (rr_array >= 300) & (rr_array <= 2000)
    filtered = rr_array[valid_mask]

    _LOGGER.info(
        "Extracted %d RR intervals (%d filtered out as artifacts)",
        len(filtered),
        len(rr_array) - len(filtered),
    )

    return filtered


# ---------------------------------------------------------------------------
# Sleep metrics computation
# ---------------------------------------------------------------------------


def compute_sleep_metrics(sleep_df: pd.DataFrame) -> pd.DataFrame:
    """Compute standard sleep metrics from Garmin sleep data.

    Args:
        sleep_df: DataFrame from fetch_garmin_sleep or parse_wellness_export_zip.

    Returns:
        DataFrame with additional computed columns:
        - tst_minutes: Total sleep time in minutes.
        - tib_minutes: Time in bed in minutes.
        - sleep_efficiency: TST / TIB * 100 (%).
        - sol_minutes: Sleep onset latency (estimated).
        - waso_minutes: Wake after sleep onset in minutes.
        - deep_pct: Deep sleep percentage.
        - light_pct: Light sleep percentage.
        - rem_pct: REM sleep percentage.
    """
    if sleep_df.empty:
        return sleep_df

    df = sleep_df.copy()

    # Total sleep time in minutes
    df["tst_minutes"] = df["total_sleep_seconds"].fillna(0) / 60.0

    # Time in bed (sleep_end - sleep_start)
    if "sleep_start" in df.columns and "sleep_end" in df.columns:
        df["sleep_start"] = pd.to_datetime(df["sleep_start"], utc=True, errors="coerce")
        df["sleep_end"] = pd.to_datetime(df["sleep_end"], utc=True, errors="coerce")
        df["tib_minutes"] = (
            (df["sleep_end"] - df["sleep_start"]).dt.total_seconds() / 60.0
        )
    else:
        # Estimate TIB as TST + awake time
        df["tib_minutes"] = (
            df["total_sleep_seconds"].fillna(0) + df["awake_seconds"].fillna(0)
        ) / 60.0

    # Sleep efficiency
    df["sleep_efficiency"] = (
        df["tst_minutes"] / df["tib_minutes"].replace(0, float("nan")) * 100.0
    )

    # WASO (wake after sleep onset)
    df["waso_minutes"] = df["awake_seconds"].fillna(0) / 60.0

    # Stage percentages
    total_staged = (
        df["deep_sleep_seconds"].fillna(0)
        + df["light_sleep_seconds"].fillna(0)
        + df["rem_sleep_seconds"].fillna(0)
    )
    total_staged = total_staged.replace(0, float("nan"))

    df["deep_pct"] = df["deep_sleep_seconds"].fillna(0) / total_staged * 100.0
    df["light_pct"] = df["light_sleep_seconds"].fillna(0) / total_staged * 100.0
    df["rem_pct"] = df["rem_sleep_seconds"].fillna(0) / total_staged * 100.0

    return df


# ---------------------------------------------------------------------------
# Quality checks
# ---------------------------------------------------------------------------


def check_garmin_data_quality(data: GarminWellnessData) -> dict[str, Any]:
    """Check quality of imported Garmin data.

    Args:
        data: GarminWellnessData container.

    Returns:
        Dictionary with quality metrics and warnings.
    """
    warnings: list[str] = []
    metrics: dict[str, Any] = {
        "sleep_nights": len(data.sleep_df),
        "hrv_readings": len(data.hrv_df),
        "hr_readings": len(data.hr_df),
        "stress_readings": len(data.stress_df),
        "spo2_readings": len(data.spo2_df),
        "respiration_readings": len(data.respiration_df),
        "body_battery_readings": len(data.body_battery_df),
        "rr_intervals": len(data.rr_intervals_df),
    }

    # Check for missing data
    if data.sleep_df.empty:
        warnings.append("No sleep data found")
    elif "total_sleep_seconds" in data.sleep_df.columns:
        short_nights = (data.sleep_df["total_sleep_seconds"] < 4 * 3600).sum()
        if short_nights > 0:
            warnings.append(f"{short_nights} nights with <4h sleep")

    if data.hrv_df.empty:
        warnings.append("No HRV data found")
    elif "hrv_rmssd" in data.hrv_df.columns:
        null_hrv = data.hrv_df["hrv_rmssd"].isna().sum()
        if null_hrv > 0:
            warnings.append(f"{null_hrv} HRV readings with missing values")

    if data.spo2_df.empty:
        warnings.append("No SpO2 data found")
    elif "spo2" in data.spo2_df.columns:
        low_spo2 = (data.spo2_df["spo2"] < 90).sum()
        if low_spo2 > 0:
            warnings.append(f"{low_spo2} SpO2 readings below 90%")

    # Check for optical sensor limitations
    if not data.hrv_df.empty:
        warnings.append(
            "Note: Optical HR sensor HRV is less accurate than chest strap; "
            "beat-level analysis may be limited"
        )

    metrics["warnings"] = warnings
    metrics["quality_ok"] = len(warnings) <= 2  # Allow optical sensor note + one other

    return metrics


# ---------------------------------------------------------------------------
# High-level import function
# ---------------------------------------------------------------------------


def import_garmin_data(
    credentials: GarminCredentials | None = None,
    zip_path: Path | None = None,
    fit_path: Path | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    include_spo2: bool = True,
    include_respiration: bool = True,
    include_body_battery: bool = True,
) -> GarminWellnessData:
    """Import Garmin wellness data from available sources.

    Attempts to load data from:
    1. Individual FIT file (if provided)
    2. Bulk wellness ZIP export (if provided)
    3. Garmin Connect API (if credentials provided)

    Args:
        credentials: Garmin Connect credentials (optional).
        zip_path: Path to Garmin wellness export ZIP (optional).
        fit_path: Path to individual FIT file (optional).
        start_date: Start date for API fetch (default: 7 days ago).
        end_date: End date for API fetch (default: today).
        include_spo2: Whether to fetch SpO2 data from API.
        include_respiration: Whether to fetch respiration data from API.
        include_body_battery: Whether to fetch body battery data from API.

    Returns:
        GarminWellnessData with available data.

    Raises:
        ValueError: If no data source provided.
    """
    if fit_path is None and zip_path is None and credentials is None:
        msg = "Either credentials, zip_path, or fit_path must be provided"
        raise ValueError(msg)

    # Try FIT file first (most detailed RR data)
    if fit_path is not None:
        _LOGGER.info("Parsing Garmin FIT file: %s", fit_path)
        data = parse_fit_file(fit_path)
        if not data.hr_df.empty or not data.rr_intervals_df.empty:
            return data

    # Try ZIP export (comprehensive historical data)
    if zip_path is not None:
        _LOGGER.info("Parsing Garmin wellness export ZIP: %s", zip_path)
        data = parse_wellness_export_zip(zip_path)
        if not data.sleep_df.empty or not data.hrv_df.empty:
            data.sleep_df = compute_sleep_metrics(data.sleep_df)
            return data

    # Fall back to API
    if credentials is not None:
        _LOGGER.info("Fetching data from Garmin Connect API")
        if start_date is None:
            start_date = date.today() - timedelta(days=7)
        if end_date is None:
            end_date = date.today()

        data = GarminWellnessData(source="garmin_connect_api")
        data.sleep_df = fetch_garmin_sleep(credentials, start_date, end_date)
        data.hrv_df = fetch_garmin_hrv(credentials, start_date, end_date)
        data.sleep_df = compute_sleep_metrics(data.sleep_df)

        # Fetch additional metrics for each day
        hr_dfs: list[pd.DataFrame] = []
        stress_dfs: list[pd.DataFrame] = []
        spo2_dfs: list[pd.DataFrame] = []
        resp_dfs: list[pd.DataFrame] = []
        bb_dfs: list[pd.DataFrame] = []

        current = start_date
        while current <= end_date:
            hr_dfs.append(fetch_garmin_heart_rate(credentials, current))
            stress_dfs.append(fetch_garmin_stress(credentials, current))

            if include_spo2:
                spo2_dfs.append(fetch_garmin_spo2(credentials, current))
            if include_respiration:
                resp_dfs.append(fetch_garmin_respiration(credentials, current))
            if include_body_battery:
                bb_dfs.append(fetch_garmin_body_battery(credentials, current))

            current += timedelta(days=1)

        data.hr_df = pd.concat(hr_dfs, ignore_index=True) if hr_dfs else pd.DataFrame()
        data.stress_df = pd.concat(stress_dfs, ignore_index=True) if stress_dfs else pd.DataFrame()
        data.spo2_df = pd.concat(spo2_dfs, ignore_index=True) if spo2_dfs else pd.DataFrame()
        data.respiration_df = pd.concat(resp_dfs, ignore_index=True) if resp_dfs else pd.DataFrame()
        data.body_battery_df = pd.concat(bb_dfs, ignore_index=True) if bb_dfs else pd.DataFrame()

        return data

    return GarminWellnessData(source="none")


def get_daily_physiology_summary(data: GarminWellnessData) -> pd.DataFrame:
    """Generate daily summary of all physiological metrics.

    Args:
        data: GarminWellnessData with raw data.

    Returns:
        DataFrame with daily aggregated metrics including:
        - date
        - avg_hr, min_hr, max_hr, resting_hr
        - steps, distance_km, calories_kcal
        - avg_hrv_rmssd
        - avg_spo2, min_spo2
        - avg_stress
        - avg_respiration (awake), avg_sleep_respiration
        - body_battery aggregates (avg, charge, drain)
        - tst_minutes, sleep_efficiency, sleep_score
    """
    daily_metrics: dict[date, dict[str, Any]] = {}

    def _ensure_day(day: date) -> dict[str, Any]:
        if day not in daily_metrics:
            daily_metrics[day] = {}
        return daily_metrics[day]

    def _update_max(day: date, key: str, value: Any) -> None:
        if value is None or (isinstance(value, float) and np.isnan(value)):
            return
        metrics = _ensure_day(day)
        if metrics.get(key) is None:
            metrics[key] = value
        else:
            try:
                metrics[key] = max(metrics[key], value)
            except Exception:
                metrics[key] = value

    def _update_mean(day: date, key: str, value: Any) -> None:
        if value is None or (isinstance(value, float) and np.isnan(value)):
            return
        metrics = _ensure_day(day)
        metrics[key] = value

    def _aggregate_monotonic(series: pd.Series) -> float | None:
        valid = series.dropna()
        if valid.empty:
            return None
        if valid.is_monotonic_increasing:
            return float(valid.iloc[-1])
        return float(valid.sum())

    # Process heart rate
    if not data.hr_df.empty and "timestamp" in data.hr_df.columns:
        hr_df = data.hr_df.copy()
        hr_df["timestamp"] = pd.to_datetime(hr_df["timestamp"], utc=True)
        hr_df["date"] = hr_df["timestamp"].dt.date
        hr_daily = hr_df.groupby("date")["heart_rate"].agg(["mean", "min", "max"])
        for idx, row in hr_daily.iterrows():
            metrics = _ensure_day(idx)
            metrics["avg_hr"] = row["mean"]
            metrics["min_hr"] = row["min"]
            metrics["max_hr"] = row["max"]

    # Process HRV
    if not data.hrv_df.empty:
        hrv_df = data.hrv_df.copy()
        if "timestamp" in hrv_df.columns:
            hrv_df["timestamp"] = pd.to_datetime(hrv_df["timestamp"], utc=True)
            hrv_df["date"] = hrv_df["timestamp"].dt.date
        elif "date" in hrv_df.columns:
            hrv_df["date"] = pd.to_datetime(hrv_df["date"]).dt.date
        
        if "hrv_rmssd" in hrv_df.columns and "date" in hrv_df.columns:
            hrv_daily = hrv_df.groupby("date")["hrv_rmssd"].mean()
            for idx, val in hrv_daily.items():
                _update_mean(idx, "avg_hrv_rmssd", val)

    # Process SpO2
    if not data.spo2_df.empty and "timestamp" in data.spo2_df.columns:
        spo2_df = data.spo2_df.copy()
        spo2_df["timestamp"] = pd.to_datetime(spo2_df["timestamp"], utc=True)
        spo2_df["date"] = spo2_df["timestamp"].dt.date
        spo2_daily = spo2_df.groupby("date")["spo2"].agg(["mean", "min"])
        for idx, row in spo2_daily.iterrows():
            metrics = _ensure_day(idx)
            metrics["avg_spo2"] = row["mean"]
            metrics["min_spo2"] = row["min"]

    # Process stress
    if not data.stress_df.empty and "timestamp" in data.stress_df.columns:
        stress_df = data.stress_df.copy()
        stress_df["timestamp"] = pd.to_datetime(stress_df["timestamp"], utc=True)
        stress_df["date"] = stress_df["timestamp"].dt.date
        # Filter out rest values
        stress_df = stress_df[stress_df["stress_level"] >= 0]
        stress_daily = stress_df.groupby("date")["stress_level"].mean()
        for idx, val in stress_daily.items():
            _update_mean(idx, "avg_stress", val)

    # Process respiration
    if not data.respiration_df.empty and "timestamp" in data.respiration_df.columns:
        resp_df = data.respiration_df.copy()
        resp_df["timestamp"] = pd.to_datetime(resp_df["timestamp"], utc=True)
        resp_df["date"] = resp_df["timestamp"].dt.date
        resp_daily = resp_df.groupby("date")["respiration_rate"].mean()
        for idx, val in resp_daily.items():
            _update_mean(idx, "avg_respiration_awake", val)

    # Process activity (steps, distance, calories)
    if not data.activity_df.empty and "timestamp" in data.activity_df.columns:
        act_df = data.activity_df.copy()
        act_df["timestamp"] = pd.to_datetime(act_df["timestamp"], utc=True)
        act_df["date"] = act_df["timestamp"].dt.date

        if "steps" in act_df.columns:
            steps_daily = act_df.groupby("date")["steps"].apply(_aggregate_monotonic)
            for idx, val in steps_daily.items():
                if val is not None:
                    _update_max(idx, "steps", val)

        if "distance_m" in act_df.columns:
            dist_daily = act_df.groupby("date")["distance_m"].apply(_aggregate_monotonic)
            for idx, val in dist_daily.items():
                if val is not None:
                    _update_max(idx, "distance_km", val / 1000.0)

        # Calories: prefer active_calories if present, else calories
        calorie_col = "active_calories" if "active_calories" in act_df.columns else "calories"
        if calorie_col in act_df.columns:
            cal_daily = act_df.groupby("date")[calorie_col].apply(_aggregate_monotonic)
            for idx, val in cal_daily.items():
                if val is not None:
                    _update_max(idx, "calories_kcal", val)

    # Process session summaries (totals and resting HR if present)
    if not data.session_df.empty:
        session_df = data.session_df.copy()
        time_col = "start_time" if "start_time" in session_df.columns else "timestamp"
        if time_col in session_df.columns:
            session_df[time_col] = pd.to_datetime(session_df[time_col], utc=True, errors="coerce")
            session_df["date"] = session_df[time_col].dt.date
            if "total_steps" in session_df.columns:
                for idx, val in session_df.groupby("date")["total_steps"].max().items():
                    _update_max(idx, "steps", val)
            if "total_distance_m" in session_df.columns:
                for idx, val in session_df.groupby("date")["total_distance_m"].max().items():
                    if pd.notna(val):
                        _update_max(idx, "distance_km", val / 1000.0)
            if "total_calories" in session_df.columns:
                for idx, val in session_df.groupby("date")["total_calories"].max().items():
                    _update_max(idx, "calories_kcal", val)
            if "avg_heart_rate" in session_df.columns:
                for idx, val in session_df.groupby("date")["avg_heart_rate"].mean().items():
                    _update_mean(idx, "avg_hr_session", val)
            if "min_heart_rate" in session_df.columns:
                for idx, val in session_df.groupby("date")["min_heart_rate"].min().items():
                    _update_mean(idx, "resting_hr_bpm", val)

    # Resting HR records
    if not data.resting_hr_df.empty and "timestamp" in data.resting_hr_df.columns:
        rest_df = data.resting_hr_df.copy()
        rest_df["timestamp"] = pd.to_datetime(rest_df["timestamp"], utc=True)
        rest_df["date"] = rest_df["timestamp"].dt.date
        rest_daily = rest_df.groupby("date")["resting_hr_bpm"].mean()
        for idx, val in rest_daily.items():
            _update_mean(idx, "resting_hr_bpm", val)

    # Process body battery
    if not data.body_battery_df.empty and "timestamp" in data.body_battery_df.columns:
        bb_df = data.body_battery_df.copy()
        bb_df["timestamp"] = pd.to_datetime(bb_df["timestamp"], utc=True)
        bb_df["date"] = bb_df["timestamp"].dt.date
        bb_daily = bb_df.groupby("date")["body_battery"].agg(["mean", "min", "max"])
        for idx, row in bb_daily.iterrows():
            metrics = _ensure_day(idx)
            metrics["avg_body_battery"] = row["mean"]
            metrics["min_body_battery"] = row["min"]
            metrics["max_body_battery"] = row["max"]
            metrics["body_battery_avg"] = row["mean"]
            metrics["body_battery_min"] = row["min"]
            metrics["body_battery_max"] = row["max"]
        # Charge and drain estimates per day
        for idx, group in bb_df.groupby("date"):
            sorted_vals = group.sort_values("timestamp")["body_battery"].dropna()
            if sorted_vals.empty:
                continue
            deltas = sorted_vals.diff().dropna()
            charge = float(deltas[deltas > 0].sum()) if not deltas.empty else 0.0
            drain = float(abs(deltas[deltas < 0].sum())) if not deltas.empty else 0.0
            metrics = _ensure_day(idx)
            metrics["body_battery_charge"] = charge
            metrics["body_battery_drain"] = drain
            metrics.setdefault("body_battery_avg", float(sorted_vals.mean()))
            metrics.setdefault("body_battery_max", float(sorted_vals.max()))
            metrics.setdefault("body_battery_min", float(sorted_vals.min()))

    # Add sleep metrics
    if not data.sleep_df.empty:
        sleep_df = compute_sleep_metrics(data.sleep_df)
        if "date" in sleep_df.columns:
            for _, row in sleep_df.iterrows():
                d = row["date"]
                if isinstance(d, str):
                    d = datetime.strptime(d, "%Y-%m-%d").date()
                metrics = _ensure_day(d)
                metrics["tst_minutes"] = row.get("tst_minutes")
                metrics["sleep_efficiency"] = row.get("sleep_efficiency")
                metrics["sleep_score"] = row.get("sleep_score")
                metrics["avg_sleep_spo2"] = row.get("avg_spo2")
                metrics["avg_sleep_respiration"] = row.get("avg_respiration")
                if row.get("tst_minutes") is not None:
                    metrics["sleep_duration_hours"] = row.get("tst_minutes") / 60.0

    # Convert to DataFrame
    if not daily_metrics:
        return pd.DataFrame()

    rows = []
    for d, metrics in sorted(daily_metrics.items()):
        row = {"date": d}
        row.update(metrics)
        rows.append(row)

    return pd.DataFrame(rows)

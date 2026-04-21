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
from typing import TYPE_CHECKING, Any, Final, Iterable, Sequence, Tuple

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

# Garmin "DI-Connect-Aggregator" daily summary exports (common in newer exports).
_UDS_FILE_PREFIX: Final[str] = "UDSFile_"

# Maximum days to fetch in a single API call to avoid rate limiting
_MAX_FETCH_DAYS: Final[int] = 30

# Timeout for HTTP requests (seconds)
_REQUEST_TIMEOUT: Final[int] = 30

_DEFAULT_FIT_FIELDS: Final[tuple[str, ...]] = (
    "timestamp",
    "heart_rate",
    "cadence",
    "distance",
    "speed",
    "enhanced_speed",
    "altitude",
    "enhanced_altitude",
    "temperature",
    "position_lat",
    "position_long",
    "fractional_cadence",
)
_MAX_FIT_RECORDS: Final[int] = 200_000


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
    # Optional daily summary rows (e.g., DI-Connect-Aggregator UDSFile exports)
    # used to populate day-level metrics without requiring minute-level streams.
    daily_summary_df: pd.DataFrame = field(default_factory=pd.DataFrame)
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
# FIT conversion utilities
# ---------------------------------------------------------------------------


def convert_fit_to_csv(
    fit_path: Path,
    *,
    allowed_fields: Sequence[str] | None = None,
    max_records: int = _MAX_FIT_RECORDS,
) -> Tuple[pd.DataFrame, bytes]:
    """Convert a FIT file to CSV bytes with selected fields.

    Args:
        fit_path: Path to the FIT file.
        allowed_fields: Optional list of FIT record fields to include. Defaults to common activity fields.
        max_records: Maximum number of records to process (safety bound).

    Returns:
        Tuple of (DataFrame of parsed records, CSV bytes).

    Raises:
        FileNotFoundError: If the FIT file does not exist.
        ImportError: If fitparse is not installed.
        ValueError: If max_records is not positive.
    """
    path = Path(fit_path)
    if not path.exists():
        msg = f"FIT file not found: {path}"
        raise FileNotFoundError(msg)
    if max_records <= 0:
        raise ValueError("max_records must be positive")

    fields: Iterable[str] = allowed_fields or _DEFAULT_FIT_FIELDS

    try:
        from fitparse import FitFile
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise ImportError(
            "fitparse is required for FIT conversion. Install via `pip install fitparse`."
        ) from exc

    rows: list[dict[str, Any]] = []
    fit_file = FitFile(str(path))
    for msg in fit_file.get_messages("record"):
        if len(rows) >= max_records:
            break
        record: dict[str, Any] = {}
        found = False
        for field in fields:
            value = msg.get_value(field)
            if value is None:
                continue
            if field == "timestamp":
                try:
                    ts = pd.to_datetime(value)
                    if ts.tzinfo is None or ts.tzinfo.utcoffset(ts) is None:
                        ts = ts.tz_localize(timezone.utc)
                    else:
                        ts = ts.tz_convert(timezone.utc)
                    record[field] = ts
                except (ValueError, TypeError, AttributeError) as exc:
                    _LOGGER.debug("Timestamp parsing fallback for value %r: %s", value, exc)
                    record[field] = value
            else:
                record[field] = value
            found = True
        if found:
            rows.append(record)

    df = pd.DataFrame(rows)
    if not df.empty and "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)

    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    return df, csv_buffer.getvalue().encode("utf-8")


# ---------------------------------------------------------------------------
# Credential loading
# ---------------------------------------------------------------------------


def load_credentials_from_env() -> GarminCredentials | None:
    """Load Garmin Connect credentials from environment variables.

    Expects GARMIN_EMAIL and GARMIN_PASSWORD to be set.
    Automatically loads .env file from project root if available.

    Returns:
        GarminCredentials if both variables are set, None otherwise.
    """
    try:
        try:
            # Package import (tests, package mode)
            from app.env_loader import load_env_file  # type: ignore
        except ImportError:
            # Script import (Streamlit adds app/ to sys.path)
            from env_loader import load_env_file  # type: ignore

        load_env_file()
    except ImportError:
        # env_loader and/or python-dotenv not available; fall back to existing env
        pass

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

    tokenstore_path = str((Path.home() / ".garminconnect"))
    # Use the upstream-recommended login flow:
    # - Loads and refreshes existing tokens from tokenstore when available
    # - Falls back to credential auth when needed
    client = Garmin(
        credentials.email,
        credentials.password,
        is_cn=False,
        return_on_mfa=True,
    )
    try:
        login_result = client.login(tokenstore_path)
        if isinstance(login_result, tuple) and len(login_result) >= 1:
            if login_result[0] == "needs_mfa":
                msg = (
                    "Garmin Connect requires MFA. Complete one interactive login with the "
                    "official python-garminconnect example.py to generate token files in "
                    "~/.garminconnect, then retry."
                )
                raise RuntimeError(msg)
        # Ensure display name is initialized for APIs that require it internally.
        if hasattr(client, "get_full_name"):
            try:
                _ = client.get_full_name()
            except Exception:
                pass
    except Exception as exc:
        msg = f"Garmin Connect authentication failed: {exc}"
        raise RuntimeError(msg) from exc
    return client


def fetch_garmin_sleep(
    credentials: GarminCredentials,
    start_date: date,
    end_date: date,
    client: Any | None = None,
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
    local_client = client if client is not None else _get_garmin_client(credentials)
    records: list[dict[str, Any]] = []

    current = start_date
    while current <= end_date:
        try:
            data = local_client.get_sleep_data(current.isoformat())
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
    client: Any | None = None,
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
    local_client = client if client is not None else _get_garmin_client(credentials)
    records: list[dict[str, Any]] = []

    current = start_date
    while current <= end_date:
        try:
            data = local_client.get_hrv_data(current.isoformat())
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
    client: Any | None = None,
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
    local_client = client if client is not None else _get_garmin_client(credentials)
    records: list[dict[str, Any]] = []

    try:
        data = local_client.get_heart_rates(target_date.isoformat())
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
    client: Any | None = None,
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
    local_client = client if client is not None else _get_garmin_client(credentials)
    records: list[dict[str, Any]] = []

    try:
        data: Any = None
        if hasattr(local_client, "get_stress_data"):
            data = local_client.get_stress_data(target_date.isoformat())
        elif hasattr(local_client, "get_all_day_stress"):
            data = local_client.get_all_day_stress(target_date.isoformat())
        if data and isinstance(data, dict):
            stress_values = data.get("stressValuesArray", [])
            for val in stress_values:
                if isinstance(val, list) and len(val) >= 2:
                    records.append(
                        {
                            "timestamp": val[0],
                            "stress_level": val[1],
                        }
                    )
            if not records:
                avg_stress = data.get("averageStressLevel") or data.get("overallStressLevel")
                if avg_stress is not None:
                    records.append(
                        {
                            "timestamp": pd.Timestamp(target_date).timestamp() * 1000,
                            "stress_level": avg_stress,
                        }
                    )
    except Exception as exc:
        _LOGGER.warning("Failed to fetch stress data for %s: %s", target_date, exc)

    df = pd.DataFrame(records)
    if not df.empty:
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    return df


def fetch_garmin_spo2(
    credentials: GarminCredentials,
    target_date: date,
    client: Any | None = None,
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
    local_client = client if client is not None else _get_garmin_client(credentials)
    records: list[dict[str, Any]] = []

    try:
        # Try different API endpoints for SpO2 data
        data = local_client.get_spo2_data(target_date.isoformat())
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
    client: Any | None = None,
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
    local_client = client if client is not None else _get_garmin_client(credentials)
    records: list[dict[str, Any]] = []

    try:
        data = local_client.get_respiration_data(target_date.isoformat())
        if data and isinstance(data, dict):
            resp_values = data.get("respirationValuesArray", [])
            for val in resp_values:
                if isinstance(val, list) and len(val) >= 2 and val[1] is not None:
                    respiration_val = val[1]
                    if isinstance(respiration_val, list) and len(respiration_val) >= 1:
                        respiration_val = respiration_val[0]
                    records.append(
                        {
                            "timestamp": val[0],
                            "respiration_rate": respiration_val,
                        }
                    )
            if not records:
                avg_awake = data.get("avgWakingRespirationValue") or data.get("awakeRespirationAvg")
                if avg_awake is not None:
                    records.append(
                        {
                            "timestamp": pd.Timestamp(target_date).timestamp() * 1000,
                            "respiration_rate": avg_awake,
                        }
                    )
    except Exception as exc:
        _LOGGER.warning("Failed to fetch respiration data for %s: %s", target_date, exc)

    df = pd.DataFrame(records)
    if not df.empty:
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    return df


def fetch_garmin_body_battery(
    credentials: GarminCredentials,
    target_date: date,
    client: Any | None = None,
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
    local_client = client if client is not None else _get_garmin_client(credentials)
    records: list[dict[str, Any]] = []

    try:
        data = local_client.get_body_battery(target_date.isoformat())
        if data and isinstance(data, list):
            for val in data:
                if isinstance(val, dict):
                    values_array = val.get("bodyBatteryValuesArray")
                    if isinstance(values_array, list) and values_array:
                        for pair in values_array:
                            if (
                                isinstance(pair, list)
                                and len(pair) >= 2
                                and pair[1] is not None
                            ):
                                records.append(
                                    {
                                        "timestamp": pair[0],
                                        "body_battery": pair[1],
                                        "status": "measured",
                                    }
                                )
                    else:
                        records.append(
                            {
                                "timestamp": val.get("startTimestampGMT"),
                                "body_battery": val.get("bodyBatteryLevel"),
                                "status": val.get("bodyBatteryStatus"),
                            }
                        )
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
        file_type is one of: "sleep", "hrv", "stress", "hr", "spo2", "respiration", "body_battery",
        or "daily_summary" (DI-Connect-Aggregator UDSFile exports).
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
        all_files = zf.namelist()
        _LOGGER.info("ZIP contains %d files total", len(all_files))
        _LOGGER.info("Files in ZIP: %s", ", ".join(all_files[:20]))  # Show first 20 files
        
        # Log directory structure
        wellness_dir_found = any("DI_CONNECT" in name or "DI-Connect" in name for name in all_files)
        if wellness_dir_found:
            _LOGGER.info("Found DI_CONNECT/DI-Connect-Wellness directory structure")
        else:
            _LOGGER.warning(
                "No DI_CONNECT/DI-Connect-Wellness directory found. "
                "This ZIP may not contain wellness JSON files (sleep, stress, body battery, etc.). "
                "To get complete wellness data, request 'Export Your Data' from Garmin Connect → Account Settings."
            )
        
        # Count JSON vs FIT files
        json_count = sum(1 for name in all_files if name.lower().endswith(".json"))
        fit_count_check = sum(1 for name in all_files if name.lower().endswith(".fit"))
        _LOGGER.info("File breakdown: %d JSON files, %d FIT files", json_count, fit_count_check)
        
        for name in all_files:
            # Check for wellness JSON files
            for suffix, file_type in suffixes.items():
                if name.endswith(suffix):
                    _LOGGER.info("Found wellness JSON: %s (type: %s)", name, file_type)
                    yield file_type, name
                    break
            else:
                # Newer Garmin exports often include a daily summary aggregator file (UDSFile_*.json)
                # under DI_CONNECT/DI-Connect-Aggregator/. This contains steps, distance, calories,
                # stress aggregates, SpO2 aggregates, respiration aggregates, and body battery stats.
                base = Path(name).name
                if base.startswith(_UDS_FILE_PREFIX) and base.lower().endswith(".json"):
                    _LOGGER.info("Found Garmin daily summary JSON: %s (type: daily_summary)", name)
                    yield "daily_summary", name


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
    daily_summary_records: list[dict[str, Any]] = []
    activity_records: list[dict[str, Any]] = []
    resting_hr_records: list[dict[str, Any]] = []
    fit_hr_records: list[dict[str, Any]] = []
    fit_hrv_records: list[dict[str, Any]] = []
    fit_spo2_records: list[dict[str, Any]] = []
    fit_stress_records: list[dict[str, Any]] = []
    fit_respiration_records: list[dict[str, Any]] = []
    fit_body_battery_records: list[dict[str, Any]] = []
    fit_rr_intervals: list[float] = []
    fit_session_records: list[dict[str, Any]] = []
    fit_activity_records: list[dict[str, Any]] = []
    fit_resting_hr_records: list[dict[str, Any]] = []
    found_wellness_json = False
    fit_count = 0

    with zipfile.ZipFile(zip_path, "r") as zf:
        for file_type, file_path in _find_wellness_files(zip_path):
            found_wellness_json = True
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
                elif file_type == "daily_summary":
                    daily_summary_records.append(_parse_daily_summary_record(record))
                    activity_record = _extract_activity_record_from_daily_summary(record)
                    if activity_record is not None:
                        activity_records.append(activity_record)
                    resting_record = _extract_resting_hr_record_from_daily_summary(record)
                    if resting_record is not None:
                        resting_hr_records.append(resting_record)
                    stress_record = _extract_stress_record_from_daily_summary(record)
                    if stress_record is not None:
                        stress_records.append(stress_record)
                    spo2_record = _extract_spo2_record_from_daily_summary(record)
                    if spo2_record is not None:
                        spo2_records.append(spo2_record)
                    resp_record = _extract_respiration_record_from_daily_summary(record)
                    if resp_record is not None:
                        respiration_records.append(resp_record)
                    body_battery_records.extend(_extract_body_battery_records_from_daily_summary(record))

        # Additionally parse any FIT files inside the ZIP (common in wellness exports)
        for name in zf.namelist():
            if name.lower().endswith(".fit"):
                fit_count += 1
                _LOGGER.info("Parsing embedded FIT file #%d: %s", fit_count, name)
                try:
                    with zf.open(name) as f_fit:
                        fit_bytes = f_fit.read()
                    fit_data = parse_fit_bytes(fit_bytes)
                    if not fit_data.hr_df.empty:
                        fit_hr_records.extend(fit_data.hr_df.to_dict(orient="records"))
                    if not fit_data.hrv_df.empty:
                        fit_hrv_records.extend(fit_data.hrv_df.to_dict(orient="records"))
                    if not fit_data.spo2_df.empty:
                        fit_spo2_records.extend(fit_data.spo2_df.to_dict(orient="records"))
                    if not fit_data.stress_df.empty:
                        fit_stress_records.extend(fit_data.stress_df.to_dict(orient="records"))
                    if not fit_data.respiration_df.empty:
                        fit_respiration_records.extend(fit_data.respiration_df.to_dict(orient="records"))
                    if not fit_data.body_battery_df.empty:
                        fit_body_battery_records.extend(fit_data.body_battery_df.to_dict(orient="records"))
                    if not fit_data.rr_intervals_df.empty:
                        fit_rr_intervals.extend(fit_data.rr_intervals_df["rr_interval_ms"].dropna().tolist())
                    if not fit_data.session_df.empty:
                        fit_session_records.extend(fit_data.session_df.to_dict(orient="records"))
                    if not fit_data.activity_df.empty:
                        fit_activity_records.extend(fit_data.activity_df.to_dict(orient="records"))
                    if not fit_data.resting_hr_df.empty:
                        fit_resting_hr_records.extend(fit_data.resting_hr_df.to_dict(orient="records"))
                except Exception as exc:  # noqa: BLE001
                    _LOGGER.warning("Failed to parse embedded FIT %s: %s", name, exc)

    result.sleep_df = pd.DataFrame(sleep_records) if sleep_records else pd.DataFrame()
    result.hrv_df = pd.DataFrame(hrv_records) if hrv_records else pd.DataFrame()
    result.stress_df = pd.DataFrame(stress_records) if stress_records else pd.DataFrame()
    result.hr_df = pd.DataFrame(hr_records) if hr_records else pd.DataFrame()
    result.spo2_df = pd.DataFrame(spo2_records) if spo2_records else pd.DataFrame()
    result.respiration_df = pd.DataFrame(respiration_records) if respiration_records else pd.DataFrame()
    result.body_battery_df = pd.DataFrame(body_battery_records) if body_battery_records else pd.DataFrame()
    result.daily_summary_df = (
        pd.DataFrame(daily_summary_records) if daily_summary_records else pd.DataFrame()
    )
    result.activity_df = pd.DataFrame(activity_records) if activity_records else pd.DataFrame()
    result.resting_hr_df = pd.DataFrame(resting_hr_records) if resting_hr_records else pd.DataFrame()
    if fit_hr_records:
        fit_hr_df = pd.DataFrame(fit_hr_records)
        result.hr_df = pd.concat([result.hr_df, fit_hr_df], ignore_index=True) if not result.hr_df.empty else fit_hr_df
    if fit_hrv_records:
        fit_hrv_df = pd.DataFrame(fit_hrv_records)
        result.hrv_df = pd.concat([result.hrv_df, fit_hrv_df], ignore_index=True) if not result.hrv_df.empty else fit_hrv_df
    if fit_spo2_records:
        fit_spo2_df = pd.DataFrame(fit_spo2_records)
        result.spo2_df = pd.concat([result.spo2_df, fit_spo2_df], ignore_index=True) if not result.spo2_df.empty else fit_spo2_df
    if fit_stress_records:
        fit_stress_df = pd.DataFrame(fit_stress_records)
        result.stress_df = pd.concat([result.stress_df, fit_stress_df], ignore_index=True) if not result.stress_df.empty else fit_stress_df
    if fit_respiration_records:
        fit_resp_df = pd.DataFrame(fit_respiration_records)
        result.respiration_df = pd.concat([result.respiration_df, fit_resp_df], ignore_index=True) if not result.respiration_df.empty else fit_resp_df
    if fit_body_battery_records:
        fit_bb_df = pd.DataFrame(fit_body_battery_records)
        result.body_battery_df = pd.concat([result.body_battery_df, fit_bb_df], ignore_index=True) if not result.body_battery_df.empty else fit_bb_df
    if fit_rr_intervals:
        fit_rr_df = pd.DataFrame({"rr_interval_ms": fit_rr_intervals})
        result.rr_intervals_df = pd.concat([result.rr_intervals_df, fit_rr_df], ignore_index=True) if not result.rr_intervals_df.empty else fit_rr_df
    if fit_session_records:
        result.session_df = pd.DataFrame(fit_session_records)
    if fit_activity_records:
        fit_act_df = pd.DataFrame(fit_activity_records)
        result.activity_df = (
            pd.concat([result.activity_df, fit_act_df], ignore_index=True)
            if not result.activity_df.empty
            else fit_act_df
        )
    if fit_resting_hr_records:
        fit_rest_df = pd.DataFrame(fit_resting_hr_records)
        result.resting_hr_df = (
            pd.concat([result.resting_hr_df, fit_rest_df], ignore_index=True)
            if not result.resting_hr_df.empty
            else fit_rest_df
        )

    # If no wellness JSON was found but FIT data exists, mark source
    if not found_wellness_json and (fit_hr_records or fit_rr_intervals or fit_spo2_records or fit_activity_records):
        result.source = f"zip-fit:{zip_path.name}"
        _LOGGER.info(
            "ZIP contained %d FIT files. Extracted: HR=%d, Stress=%d, SpO2=%d, Resp=%d, BodyBat=%d, Activity=%d, Session=%d, RestingHR=%d",
            fit_count, len(fit_hr_records), len(fit_stress_records), len(fit_spo2_records),
            len(fit_respiration_records), len(fit_body_battery_records), len(fit_activity_records),
            len(fit_session_records), len(fit_resting_hr_records),
        )
    elif found_wellness_json:
        _LOGGER.info(
            "ZIP contained wellness JSON. Parsed: Sleep=%d, HRV=%d, HR=%d, Stress=%d, SpO2=%d, Resp=%d, BodyBat=%d",
            len(sleep_records), len(hrv_records), len(hr_records), len(stress_records),
            len(spo2_records), len(respiration_records), len(body_battery_records),
        )
    else:
        _LOGGER.warning("ZIP did not contain recognizable wellness JSON or usable FIT data")

    return result


def parse_wellness_export_json(json_path: Path) -> GarminWellnessData:
    """Parse a single Garmin export JSON file (from an unzipped export).

    Supported JSON files:
    - `*_sleepData.json` (sleep stages + scores; multiple schemas supported)
    - `*_hrvData.json`
    - `*_stressData.json`
    - `*_heartRateData.json`
    - `*_spo2Data.json`
    - `*_respirationData.json`
    - `*_bodyBatteryData.json`
    - `UDSFile_*.json` (daily summary aggregator)
    """
    path = Path(json_path)
    if not path.exists():
        msg = f"JSON file not found: {path}"
        raise FileNotFoundError(msg)

    try:
        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON file: {path.name}") from exc

    records: list[dict[str, Any]] = []
    if isinstance(payload, dict):
        records = [payload]
    elif isinstance(payload, list):
        records = [r for r in payload if isinstance(r, dict)]
    else:
        raise ValueError(f"Unsupported JSON payload type in {path.name}: {type(payload)}")

    name = path.name
    file_type: str | None = None

    # Prefer filename-based routing when available (most direct).
    if name.startswith(_UDS_FILE_PREFIX) and name.lower().endswith(".json"):
        file_type = "daily_summary"
    elif name.endswith(_SLEEP_FILE_SUFFIX):
        file_type = "sleep"
    elif name.endswith(_HRV_FILE_SUFFIX):
        file_type = "hrv"
    elif name.endswith(_STRESS_FILE_SUFFIX):
        file_type = "stress"
    elif name.endswith(_HR_FILE_SUFFIX):
        file_type = "hr"
    elif name.endswith(_SPO2_FILE_SUFFIX):
        file_type = "spo2"
    elif name.endswith(_RESPIRATION_FILE_SUFFIX):
        file_type = "respiration"
    elif name.endswith(_BODY_BATTERY_FILE_SUFFIX):
        file_type = "body_battery"

    # Fallback: infer from contents (handles temp filenames like tmpXXXX.json).
    if file_type is None:
        if not records:
            raise ValueError(f"Empty JSON export file: {name}")
        sample = records[0]

        # Sleep: has sleep start/end + stage seconds or total seconds.
        if (
            "sleepStartTimestampGMT" in sample
            and "sleepEndTimestampGMT" in sample
            and (
                "deepSleepSeconds" in sample
                or "lightSleepSeconds" in sample
                or "remSleepSeconds" in sample
                or "sleepTimeSeconds" in sample
                or "sleepScores" in sample
            )
        ):
            file_type = "sleep"
        # HRV RMSSD export
        elif "hrvValues" in sample:
            file_type = "hrv"
        # Stress export
        elif "stressValuesArray" in sample:
            file_type = "stress"
        # Heart-rate export
        elif "heartRateValues" in sample:
            file_type = "hr"
        # SpO2 export
        elif "spO2Values" in sample or "sleepingSpO2Values" in sample:
            file_type = "spo2"
        # Respiration export
        elif "respirationValuesArray" in sample:
            file_type = "respiration"
        # Body battery export (time series)
        elif "bodyBatteryLevel" in sample or "bodyBatteryValuesArray" in sample:
            file_type = "body_battery"
        # Daily summary export (UDSFile content)
        elif "calendarDate" in sample and any(
            k in sample
            for k in (
                "totalSteps",
                "totalDistanceMeters",
                "activeKilocalories",
                "allDayStress",
                "bodyBattery",
                "respiration",
                "averageSpo2Value",
            )
        ):
            file_type = "daily_summary"
        else:
            keys_preview = sorted(list(sample.keys()))[:25]
            raise ValueError(
                "Unrecognized Garmin JSON export file (content-based detection failed). "
                "Expected one of: "
                f"{_UDS_FILE_PREFIX}*.json, *{_SLEEP_FILE_SUFFIX}, *{_HRV_FILE_SUFFIX}, "
                f"*{_STRESS_FILE_SUFFIX}, *{_HR_FILE_SUFFIX}, *{_SPO2_FILE_SUFFIX}, "
                f"*{_RESPIRATION_FILE_SUFFIX}, *{_BODY_BATTERY_FILE_SUFFIX}. "
                f"Got: {name}. Sample keys: {keys_preview}"
            )

    result = GarminWellnessData(source=f"json:{name}")

    if file_type == "sleep":
        sleep_records = [_parse_sleep_record(r) for r in records]
        result.sleep_df = pd.DataFrame(sleep_records) if sleep_records else pd.DataFrame()
        return result

    if file_type == "hrv":
        hrv_records: list[dict[str, Any]] = []
        for r in records:
            hrv_records.extend(_parse_hrv_record(r))
        result.hrv_df = pd.DataFrame(hrv_records) if hrv_records else pd.DataFrame()
        return result

    if file_type == "stress":
        stress_records: list[dict[str, Any]] = []
        for r in records:
            stress_records.extend(_parse_stress_record(r))
        result.stress_df = pd.DataFrame(stress_records) if stress_records else pd.DataFrame()
        return result

    if file_type == "hr":
        hr_records: list[dict[str, Any]] = []
        for r in records:
            hr_records.extend(_parse_hr_record(r))
        result.hr_df = pd.DataFrame(hr_records) if hr_records else pd.DataFrame()
        return result

    if file_type == "spo2":
        spo2_records: list[dict[str, Any]] = []
        for r in records:
            spo2_records.extend(_parse_spo2_record(r))
        result.spo2_df = pd.DataFrame(spo2_records) if spo2_records else pd.DataFrame()
        return result

    if file_type == "respiration":
        respiration_records: list[dict[str, Any]] = []
        for r in records:
            respiration_records.extend(_parse_respiration_record(r))
        result.respiration_df = pd.DataFrame(respiration_records) if respiration_records else pd.DataFrame()
        return result

    if file_type == "body_battery":
        body_battery_records: list[dict[str, Any]] = []
        for r in records:
            body_battery_records.extend(_parse_body_battery_record(r))
        result.body_battery_df = (
            pd.DataFrame(body_battery_records) if body_battery_records else pd.DataFrame()
        )
        return result

    # daily_summary
    daily_summary_records: list[dict[str, Any]] = []
    activity_records: list[dict[str, Any]] = []
    resting_hr_records: list[dict[str, Any]] = []
    stress_records: list[dict[str, Any]] = []
    spo2_records: list[dict[str, Any]] = []
    respiration_records: list[dict[str, Any]] = []
    body_battery_records: list[dict[str, Any]] = []

    for r in records:
        daily_summary_records.append(_parse_daily_summary_record(r))
        activity_record = _extract_activity_record_from_daily_summary(r)
        if activity_record is not None:
            activity_records.append(activity_record)
        resting_record = _extract_resting_hr_record_from_daily_summary(r)
        if resting_record is not None:
            resting_hr_records.append(resting_record)
        stress_record = _extract_stress_record_from_daily_summary(r)
        if stress_record is not None:
            stress_records.append(stress_record)
        spo2_record = _extract_spo2_record_from_daily_summary(r)
        if spo2_record is not None:
            spo2_records.append(spo2_record)
        resp_record = _extract_respiration_record_from_daily_summary(r)
        if resp_record is not None:
            respiration_records.append(resp_record)
        body_battery_records.extend(_extract_body_battery_records_from_daily_summary(r))

    result.daily_summary_df = (
        pd.DataFrame(daily_summary_records) if daily_summary_records else pd.DataFrame()
    )
    result.activity_df = pd.DataFrame(activity_records) if activity_records else pd.DataFrame()
    result.resting_hr_df = pd.DataFrame(resting_hr_records) if resting_hr_records else pd.DataFrame()
    result.stress_df = pd.DataFrame(stress_records) if stress_records else pd.DataFrame()
    result.spo2_df = pd.DataFrame(spo2_records) if spo2_records else pd.DataFrame()
    result.respiration_df = pd.DataFrame(respiration_records) if respiration_records else pd.DataFrame()
    result.body_battery_df = (
        pd.DataFrame(body_battery_records) if body_battery_records else pd.DataFrame()
    )
    return result


def _parse_sleep_record(record: dict[str, Any]) -> dict[str, Any]:
    """Parse a single sleep record from Garmin JSON export."""
    # Garmin exports have at least two common sleep JSON schemas:
    # 1) Older: top-level "sleepTimeSeconds" + "overallScore" (+ sleepRestingSpO2, etc.)
    # 2) Newer: staged seconds + nested "sleepScores" and optional "spo2SleepSummary".
    date_val = record.get("calendarDate")

    deep = record.get("deepSleepSeconds")
    light = record.get("lightSleepSeconds")
    rem = record.get("remSleepSeconds")
    awake = record.get("awakeSleepSeconds")
    unmeasurable = record.get("unmeasurableSeconds")

    total_sleep = record.get("sleepTimeSeconds")
    if total_sleep is None:
        staged_total = 0
        staged_any = False
        for val in (deep, light, rem):
            try:
                if val is None:
                    continue
                staged_total += int(val)
                staged_any = True
            except (TypeError, ValueError):
                continue
        if staged_any:
            try:
                if unmeasurable is not None:
                    staged_total += int(unmeasurable)
            except (TypeError, ValueError):
                pass
            total_sleep = staged_total

    # Sleep score (may be top-level or nested in "sleepScores")
    sleep_score = record.get("overallScore")
    if sleep_score is None:
        sleep_scores = record.get("sleepScores")
        if isinstance(sleep_scores, dict):
            sleep_score = sleep_scores.get("overallScore")

    # SpO2 during sleep (may be top-level or nested in "spo2SleepSummary")
    avg_spo2 = record.get("averageSpO2Value")
    lowest_spo2 = record.get("lowestSpO2Value")
    if avg_spo2 is None or lowest_spo2 is None:
        spo2_summary = record.get("spo2SleepSummary")
        if isinstance(spo2_summary, dict):
            if avg_spo2 is None:
                avg_spo2 = spo2_summary.get("averageSPO2")
            if lowest_spo2 is None:
                lowest_spo2 = spo2_summary.get("lowestSPO2")

    # Respiration during sleep (may be top-level or nested)
    avg_resp = record.get("avgSleepRespirationValue")
    if avg_resp is None:
        avg_resp = record.get("averageRespiration")

    return {
        "date": date_val,
        "total_sleep_seconds": total_sleep,
        "deep_sleep_seconds": deep,
        "light_sleep_seconds": light,
        "rem_sleep_seconds": rem,
        "awake_seconds": awake,
        "sleep_score": sleep_score,
        "sleep_start": record.get("sleepStartTimestampGMT"),
        "sleep_end": record.get("sleepEndTimestampGMT"),
        "avg_spo2": avg_spo2,
        "lowest_spo2": lowest_spo2,
        "avg_respiration": avg_resp,
    }


def _parse_daily_summary_record(record: dict[str, Any]) -> dict[str, Any]:
    """Parse a single Garmin daily summary record (UDSFile export).

    The UDSFile payload is a day-level aggregator and typically includes:
    - steps, distance, active/total calories
    - all-day stress aggregates (TOTAL/AWAKE/ASLEEP)
    - body battery charged/drained + summary stats list
    - respiration aggregates
    - SpO2 aggregates
    """
    date_val = record.get("calendarDate")

    steps = record.get("totalSteps")
    distance_m = record.get("totalDistanceMeters")
    active_kcal = record.get("activeKilocalories")

    # Daily heart-rate summary (UDS includes min/max of "avg heart rate" over the day)
    avg_hr: Any = None
    min_avg_hr = record.get("minAvgHeartRate")
    max_avg_hr = record.get("maxAvgHeartRate")
    try:
        candidates: list[float] = []
        if min_avg_hr is not None and not pd.isna(min_avg_hr):
            candidates.append(float(min_avg_hr))
        if max_avg_hr is not None and not pd.isna(max_avg_hr):
            candidates.append(float(max_avg_hr))
        if candidates:
            avg_hr = float(np.mean(candidates))
    except (ValueError, TypeError) as exc:
        _LOGGER.debug("Could not compute avg heart rate from %r/%r: %s", min_avg_hr, max_avg_hr, exc)
        avg_hr = None

    # Stress aggregate (prefer TOTAL; ignore sentinel -2 values)
    avg_stress: Any = None
    all_day_stress = record.get("allDayStress")
    if isinstance(all_day_stress, dict):
        aggregator_list = all_day_stress.get("aggregatorList")
        if isinstance(aggregator_list, list):
            # Prefer TOTAL, else first non-negative
            picked: dict[str, Any] | None = None
            for item in aggregator_list:
                if isinstance(item, dict) and item.get("type") == "TOTAL":
                    picked = item
                    break
            if picked is None:
                for item in aggregator_list:
                    if isinstance(item, dict) and item.get("averageStressLevel") not in (None, -2):
                        picked = item
                        break
            if picked is not None:
                avg_stress = picked.get("averageStressLevel")

    # Respiration aggregate
    avg_resp_awake: Any = None
    resp = record.get("respiration")
    if isinstance(resp, dict):
        avg_resp_awake = resp.get("avgWakingRespirationValue")

    # SpO2 aggregate
    avg_spo2 = record.get("averageSpo2Value")
    min_spo2 = record.get("lowestSpo2Value")

    # Body battery aggregates
    body_battery_avg: Any = None
    body_battery_charge: Any = None
    body_battery_drain: Any = None
    bb = record.get("bodyBattery")
    bb_values: list[float] = []
    if isinstance(bb, dict):
        body_battery_charge = bb.get("chargedValue")
        body_battery_drain = bb.get("drainedValue")
        stats_list = bb.get("bodyBatteryStatList")
        if isinstance(stats_list, list):
            for item in stats_list:
                if not isinstance(item, dict):
                    continue
                raw = item.get("statsValue")
                try:
                    if raw is None:
                        continue
                    bb_values.append(float(raw))
                except (TypeError, ValueError):
                    continue
    if bb_values:
        body_battery_avg = float(np.mean(bb_values))

    resting_hr = record.get("currentDayRestingHeartRate")
    if resting_hr is None:
        resting_hr = record.get("restingHeartRate")

    return {
        "date": date_val,
        "steps": steps,
        "distance_km": (float(distance_m) / 1000.0) if distance_m is not None else None,
        "calories_kcal": active_kcal,
        "avg_hr": avg_hr,
        "avg_stress": avg_stress,
        "avg_spo2": avg_spo2,
        "min_spo2": min_spo2,
        "avg_respiration_awake": avg_resp_awake,
        "body_battery_avg": body_battery_avg,
        "body_battery_charge": body_battery_charge,
        "body_battery_drain": body_battery_drain,
        "resting_hr_bpm": resting_hr,
        "min_hr": record.get("minHeartRate"),
        "max_hr": record.get("maxHeartRate"),
    }


def _extract_activity_record_from_daily_summary(record: dict[str, Any]) -> dict[str, Any] | None:
    """Extract a minimal activity counter row from a daily summary record."""
    ts = record.get("wellnessEndTimeGmt") or record.get("wellnessStartTimeGmt")
    if ts is None:
        return None
    if not any(k in record for k in ("totalSteps", "totalDistanceMeters", "activeKilocalories", "totalKilocalories")):
        return None
    return {
        "timestamp": ts,
        "steps": record.get("totalSteps"),
        "distance_m": record.get("totalDistanceMeters"),
        # Prefer active calories for alignment with FIT monitoring counters.
        "active_calories": record.get("activeKilocalories"),
        "calories": record.get("totalKilocalories"),
    }


def _extract_resting_hr_record_from_daily_summary(record: dict[str, Any]) -> dict[str, Any] | None:
    """Extract a resting HR row from a daily summary record."""
    ts = record.get("wellnessEndTimeGmt") or record.get("wellnessStartTimeGmt")
    if ts is None:
        return None
    val = record.get("currentDayRestingHeartRate")
    if val is None:
        val = record.get("restingHeartRate")
    if val is None:
        return None
    return {"timestamp": ts, "resting_hr_bpm": val}


def _extract_stress_record_from_daily_summary(record: dict[str, Any]) -> dict[str, Any] | None:
    """Extract a daily average stress row from a daily summary record."""
    ts = record.get("wellnessEndTimeGmt") or record.get("wellnessStartTimeGmt")
    if ts is None:
        return None
    parsed = _parse_daily_summary_record(record).get("avg_stress")
    if parsed is None or parsed == -2:
        return None
    return {"timestamp": ts, "stress_level": parsed}


def _extract_spo2_record_from_daily_summary(record: dict[str, Any]) -> dict[str, Any] | None:
    """Extract a daily SpO2 row from a daily summary record."""
    ts = record.get("latestSpo2ValueReadingTimeGmt") or record.get("wellnessEndTimeGmt") or record.get("wellnessStartTimeGmt")
    if ts is None:
        return None
    val = record.get("averageSpo2Value")
    if val is None:
        val = record.get("latestSpo2Value")
    if val is None:
        return None
    return {"timestamp": ts, "spo2": val}


def _extract_respiration_record_from_daily_summary(record: dict[str, Any]) -> dict[str, Any] | None:
    """Extract a daily respiration row from a daily summary record."""
    resp = record.get("respiration")
    if not isinstance(resp, dict):
        return None
    ts = resp.get("latestRespirationTimeGMT") or record.get("wellnessEndTimeGmt") or record.get("wellnessStartTimeGmt")
    if ts is None:
        return None
    val = resp.get("avgWakingRespirationValue")
    if val is None:
        val = resp.get("latestRespirationValue")
    if val is None:
        return None
    return {"timestamp": ts, "respiration_rate": val}


def _extract_body_battery_records_from_daily_summary(record: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract body-battery stat points from a daily summary record."""
    bb = record.get("bodyBattery")
    if not isinstance(bb, dict):
        return []
    stats_list = bb.get("bodyBatteryStatList")
    if not isinstance(stats_list, list):
        return []
    out: list[dict[str, Any]] = []
    for item in stats_list:
        if not isinstance(item, dict):
            continue
        ts = item.get("statTimestamp")
        val = item.get("statsValue")
        if ts is None or val is None:
            continue
        out.append(
            {
                "timestamp": ts,
                "body_battery": val,
                "status": item.get("bodyBatteryStatus"),
            }
        )
    return out


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
    sleep_records: list[dict[str, Any]] = []
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
                # 24/7 wellness monitoring data
                # Activity metrics
                if any(key in record_dict for key in ("steps", "distance", "calories", "active_calories")):
                    activity_records.append({
                        "timestamp": timestamp,
                        "steps": record_dict.get("steps"),
                        "distance_m": record_dict.get("distance"),
                        "calories": record_dict.get("calories"),
                        "active_calories": record_dict.get("active_calories"),
                    })
                
                # Heart rate monitoring
                if "heart_rate" in record_dict:
                    hr_records.append({
                        "timestamp": timestamp,
                        "heart_rate": record_dict.get("heart_rate"),
                    })
                
                if "resting_heart_rate" in record_dict:
                    resting_hr_records.append({
                        "timestamp": timestamp,
                        "resting_hr_bpm": record_dict.get("resting_heart_rate"),
                    })
                
                # Stress monitoring
                if "stress_level_value" in record_dict or "stress" in record_dict:
                    stress_val = record_dict.get("stress_level_value") or record_dict.get("stress")
                    if stress_val is not None:
                        stress_records.append({
                            "timestamp": timestamp,
                            "stress_level": stress_val,
                        })
                
                # Body Battery monitoring
                if "body_battery_level" in record_dict or "body_battery" in record_dict:
                    body_battery_records.append({
                        "timestamp": timestamp,
                        "body_battery": record_dict.get("body_battery_level") or record_dict.get("body_battery"),
                        "status": record_dict.get("body_battery_status"),
                    })
                
                # SpO2 monitoring
                if "spo2_percentage" in record_dict or "saturated_hemoglobin_percent" in record_dict:
                    spo2_val = record_dict.get("spo2_percentage") or record_dict.get("saturated_hemoglobin_percent")
                    if spo2_val is not None:
                        spo2_records.append({
                            "timestamp": timestamp,
                            "spo2": spo2_val,
                        })
                
                # Respiration monitoring
                if "respiration_rate" in record_dict:
                    respiration_records.append({
                        "timestamp": timestamp,
                        "respiration_rate": record_dict.get("respiration_rate"),
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

            elif record_type == "sleep" or record_type == "sleep_level":
                # Sleep tracking data
                sleep_records.append({
                    "timestamp": timestamp,
                    "sleep_level": record_dict.get("sleep_level"),
                    "duration_seconds": record_dict.get("duration"),
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
    result.sleep_df = pd.DataFrame(sleep_records) if sleep_records else pd.DataFrame()
    if body_battery_records:
        result.body_battery_df = pd.DataFrame(body_battery_records)
    
    # RR intervals for HRV analysis
    if rr_intervals:
        result.rr_intervals_df = pd.DataFrame({"rr_interval_ms": rr_intervals})
    
    # Log what was found for debugging
    _LOGGER.info(
        "FIT parse complete: HR=%d, Stress=%d, SpO2=%d, Resp=%d, BodyBat=%d, Activity=%d, Session=%d, Sleep=%d",
        len(hr_records), len(stress_records), len(spo2_records), len(respiration_records),
        len(body_battery_records), len(activity_records), len(session_records), len(sleep_records),
    )

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
    stress_records: list[dict[str, Any]] = []
    respiration_records: list[dict[str, Any]] = []
    body_battery_records: list[dict[str, Any]] = []
    activity_records: list[dict[str, Any]] = []
    session_records: list[dict[str, Any]] = []
    resting_hr_records: list[dict[str, Any]] = []
    sleep_records: list[dict[str, Any]] = []
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
            # 24/7 wellness monitoring data
            if any(key in record_dict for key in ("steps", "distance", "calories", "active_calories")):
                activity_records.append({
                    "timestamp": timestamp,
                    "steps": record_dict.get("steps"),
                    "distance_m": record_dict.get("distance"),
                    "calories": record_dict.get("calories"),
                    "active_calories": record_dict.get("active_calories"),
                })
            
            if "heart_rate" in record_dict:
                hr_records.append({
                    "timestamp": timestamp,
                    "heart_rate": record_dict.get("heart_rate"),
                })
            
            if "resting_heart_rate" in record_dict:
                resting_hr_records.append({
                    "timestamp": timestamp,
                    "resting_hr_bpm": record_dict.get("resting_heart_rate"),
                })
            
            if "stress_level_value" in record_dict or "stress" in record_dict:
                stress_val = record_dict.get("stress_level_value") or record_dict.get("stress")
                if stress_val is not None:
                    stress_records.append({
                        "timestamp": timestamp,
                        "stress_level": stress_val,
                    })
            
            if "body_battery_level" in record_dict or "body_battery" in record_dict:
                body_battery_records.append({
                    "timestamp": timestamp,
                    "body_battery": record_dict.get("body_battery_level") or record_dict.get("body_battery"),
                    "status": record_dict.get("body_battery_status"),
                })
            
            if "spo2_percentage" in record_dict or "saturated_hemoglobin_percent" in record_dict:
                spo2_val = record_dict.get("spo2_percentage") or record_dict.get("saturated_hemoglobin_percent")
                if spo2_val is not None:
                    spo2_records.append({
                        "timestamp": timestamp,
                        "spo2": spo2_val,
                    })
            
            if "respiration_rate" in record_dict:
                respiration_records.append({
                    "timestamp": timestamp,
                    "respiration_rate": record_dict.get("respiration_rate"),
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

        elif record.name == "sleep" or record.name == "sleep_level":
            # Sleep tracking data
            sleep_records.append({
                "timestamp": timestamp,
                "sleep_level": record_dict.get("sleep_level"),
                "duration_seconds": record_dict.get("duration"),
            })

    result.hr_df = pd.DataFrame(hr_records) if hr_records else pd.DataFrame()
    result.spo2_df = pd.DataFrame(spo2_records) if spo2_records else pd.DataFrame()
    result.stress_df = pd.DataFrame(stress_records) if stress_records else pd.DataFrame()
    result.respiration_df = pd.DataFrame(respiration_records) if respiration_records else pd.DataFrame()
    result.body_battery_df = pd.DataFrame(body_battery_records) if body_battery_records else pd.DataFrame()
    result.activity_df = pd.DataFrame(activity_records) if activity_records else pd.DataFrame()
    result.session_df = pd.DataFrame(session_records) if session_records else pd.DataFrame()
    result.resting_hr_df = pd.DataFrame(resting_hr_records) if resting_hr_records else pd.DataFrame()
    result.sleep_df = pd.DataFrame(sleep_records) if sleep_records else pd.DataFrame()
    if rr_intervals:
        result.rr_intervals_df = pd.DataFrame({"rr_interval_ms": rr_intervals})
    
    # Log what was found for debugging
    _LOGGER.info(
        "FIT parse (bytes) complete: HR=%d, Stress=%d, SpO2=%d, Resp=%d, BodyBat=%d, Activity=%d, Session=%d, Sleep=%d",
        len(hr_records), len(stress_records), len(spo2_records), len(respiration_records),
        len(body_battery_records), len(activity_records), len(session_records), len(sleep_records),
    )

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
    json_path: Path | None = None,
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
    3. Single Garmin export JSON file (if provided; from an unzipped export)
    4. Garmin Connect API (if credentials provided)

    Args:
        credentials: Garmin Connect credentials (optional).
        zip_path: Path to Garmin wellness export ZIP (optional).
        fit_path: Path to individual FIT file (optional).
        json_path: Path to a single Garmin export JSON file (optional).
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
    if fit_path is None and zip_path is None and json_path is None and credentials is None:
        msg = "Either credentials, zip_path, json_path, or fit_path must be provided"
        raise ValueError(msg)

    # Try FIT file first (most detailed RR data)
    if fit_path is not None:
        _LOGGER.info("Parsing Garmin FIT file: %s", fit_path)
        data = parse_fit_file(fit_path)
        # Return if ANY wellness data found (not just RR intervals)
        has_data = any([
            not data.hr_df.empty,
            not data.rr_intervals_df.empty,
            not data.stress_df.empty,
            not data.spo2_df.empty,
            not data.respiration_df.empty,
            not data.body_battery_df.empty,
            not data.activity_df.empty,
            not data.session_df.empty,
        ])
        if has_data:
            return data

    # Try ZIP export (comprehensive historical data)
    if zip_path is not None:
        _LOGGER.info("Parsing Garmin wellness export ZIP: %s", zip_path)
        data = parse_wellness_export_zip(zip_path)
        # Return if ANY wellness data found
        has_data = any([
            not data.sleep_df.empty,
            not data.hrv_df.empty,
            not data.hr_df.empty,
            not data.stress_df.empty,
            not data.spo2_df.empty,
            not data.respiration_df.empty,
            not data.body_battery_df.empty,
            not data.activity_df.empty,
            not data.session_df.empty,
            not data.daily_summary_df.empty,
        ])
        if has_data:
            if not data.sleep_df.empty:
                data.sleep_df = compute_sleep_metrics(data.sleep_df)
            return data

    # Try single JSON export file (unpacked Garmin export)
    if json_path is not None:
        _LOGGER.info("Parsing Garmin export JSON: %s", json_path)
        data = parse_wellness_export_json(json_path)
        has_data = any(
            [
                not data.sleep_df.empty,
                not data.hrv_df.empty,
                not data.hr_df.empty,
                not data.stress_df.empty,
                not data.spo2_df.empty,
                not data.respiration_df.empty,
                not data.body_battery_df.empty,
                not data.activity_df.empty,
                not data.session_df.empty,
                not data.daily_summary_df.empty,
            ]
        )
        if has_data:
            if not data.sleep_df.empty:
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
        shared_client = _get_garmin_client(credentials)
        try:
            data.sleep_df = fetch_garmin_sleep(
                credentials,
                start_date,
                end_date,
                client=shared_client,
            )
            data.hrv_df = fetch_garmin_hrv(
                credentials,
                start_date,
                end_date,
                client=shared_client,
            )
            data.sleep_df = compute_sleep_metrics(data.sleep_df)

            # Fetch additional metrics for each day
            hr_dfs: list[pd.DataFrame] = []
            stress_dfs: list[pd.DataFrame] = []
            spo2_dfs: list[pd.DataFrame] = []
            resp_dfs: list[pd.DataFrame] = []
            bb_dfs: list[pd.DataFrame] = []

            current = start_date
            while current <= end_date:
                hr_dfs.append(fetch_garmin_heart_rate(credentials, current, client=shared_client))
                stress_dfs.append(fetch_garmin_stress(credentials, current, client=shared_client))

                if include_spo2:
                    spo2_dfs.append(fetch_garmin_spo2(credentials, current, client=shared_client))
                if include_respiration:
                    resp_dfs.append(
                        fetch_garmin_respiration(credentials, current, client=shared_client)
                    )
                if include_body_battery:
                    bb_dfs.append(
                        fetch_garmin_body_battery(credentials, current, client=shared_client)
                    )

                current += timedelta(days=1)

            data.hr_df = pd.concat(hr_dfs, ignore_index=True) if hr_dfs else pd.DataFrame()
            data.stress_df = pd.concat(stress_dfs, ignore_index=True) if stress_dfs else pd.DataFrame()
            data.spo2_df = pd.concat(spo2_dfs, ignore_index=True) if spo2_dfs else pd.DataFrame()
            data.respiration_df = (
                pd.concat(resp_dfs, ignore_index=True) if resp_dfs else pd.DataFrame()
            )
            data.body_battery_df = (
                pd.concat(bb_dfs, ignore_index=True) if bb_dfs else pd.DataFrame()
            )
        finally:
            if hasattr(shared_client, "logout"):
                try:
                    shared_client.logout()
                except Exception:
                    pass

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
    _LOGGER.info(
        "Generating daily summary from: HR rows=%d, Stress=%d, SpO2=%d, Resp=%d, BodyBat=%d, Activity=%d, Session=%d, Sleep=%d",
        len(data.hr_df), len(data.stress_df), len(data.spo2_df), len(data.respiration_df),
        len(data.body_battery_df), len(data.activity_df), len(data.session_df), len(data.sleep_df),
    )
    
    daily_metrics: dict[date, dict[str, Any]] = {}

    def _ensure_day(day: date) -> dict[str, Any]:
        if day not in daily_metrics:
            daily_metrics[day] = {}
        return daily_metrics[day]

    def _update_max(day: date, key: str, value: Any) -> None:
        if value is None or pd.isna(value):
            return
        metrics = _ensure_day(day)
        if metrics.get(key) is None:
            metrics[key] = value
        else:
            try:
                metrics[key] = max(metrics[key], value)
            except (TypeError, ValueError):
                # Incompatible types for max comparison; keep new value
                metrics[key] = value

    def _update_mean(day: date, key: str, value: Any) -> None:
        if value is None or pd.isna(value):
            return
        metrics = _ensure_day(day)
        metrics[key] = value

    def _aggregate_monotonic(series: pd.Series) -> float | None:
        """Aggregate cumulative counter values (steps, distance, calories).
        
        For monitoring data, these are cumulative counters that reset daily.
        Take the maximum value as the daily total.
        """
        valid = series.dropna()
        if valid.empty:
            return None
        # For cumulative counters, the maximum value is the daily total
        return float(valid.max())

    # ---------------------------------------------------------------------
    # Precomputed daily summary rows (e.g., UDSFile exports)
    # ---------------------------------------------------------------------
    if not data.daily_summary_df.empty and "date" in data.daily_summary_df.columns:
        summary_df = data.daily_summary_df.copy()
        summary_df["date"] = pd.to_datetime(summary_df["date"], errors="coerce").dt.date
        summary_df = summary_df.dropna(subset=["date"])
        for _, row in summary_df.iterrows():
            d = row.get("date")
            if d is None or pd.isna(d):
                continue
            if not isinstance(d, date):
                try:
                    d = pd.to_datetime(d, errors="coerce").date()
                except (ValueError, TypeError, AttributeError):
                    # Could not parse date; skip this record
                    continue
            # Steps / distance / calories
            _update_max(d, "steps", row.get("steps"))
            _update_max(d, "distance_km", row.get("distance_km"))
            _update_max(d, "calories_kcal", row.get("calories_kcal"))

            # Heart rate (daily summary proxy)
            _update_mean(d, "avg_hr", row.get("avg_hr"))

            # Stress / respiration / SpO2 aggregates
            _update_mean(d, "avg_stress", row.get("avg_stress"))
            _update_mean(d, "avg_respiration_awake", row.get("avg_respiration_awake"))
            _update_mean(d, "avg_spo2", row.get("avg_spo2"))
            _update_mean(d, "min_spo2", row.get("min_spo2"))

            # Resting HR (when present)
            _update_mean(d, "resting_hr_bpm", row.get("resting_hr_bpm"))
            _update_mean(d, "min_hr", row.get("min_hr"))
            _update_mean(d, "max_hr", row.get("max_hr"))

            # Body battery aggregates (when present)
            _update_mean(d, "body_battery_avg", row.get("body_battery_avg"))
            _update_mean(d, "body_battery_charge", row.get("body_battery_charge"))
            _update_mean(d, "body_battery_drain", row.get("body_battery_drain"))

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
        spo2_daily = spo2_df.groupby("date")["spo2"].agg(["mean", "min", "count"])
        for idx, row in spo2_daily.iterrows():
            metrics = _ensure_day(idx)
            # If we already have aggregated day-level values (e.g., from UDSFile daily_summary_df)
            # and only a single placeholder reading exists for this day, preserve the aggregated values.
            has_precomputed = (
                not data.daily_summary_df.empty
                and metrics.get("avg_spo2") is not None
                and metrics.get("min_spo2") is not None
            )
            count = int(row.get("count") or 0)
            if has_precomputed and count <= 1:
                continue
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
            # Preserve any precomputed daily charge/drain values (e.g., from UDSFile exports).
            metrics.setdefault("body_battery_charge", charge)
            metrics.setdefault("body_battery_drain", drain)
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
        _LOGGER.warning("No daily metrics generated - all input dataframes may be empty or lack timestamp/date columns")
        return pd.DataFrame()

    rows = []
    for d, metrics in sorted(daily_metrics.items()):
        row = {"date": d}
        row.update(metrics)
        rows.append(row)

    result_df = pd.DataFrame(rows)
    _LOGGER.info("Generated daily summary: %d days with %d unique metrics per day", len(result_df), len(result_df.columns) - 1 if not result_df.empty else 0)
    
    return result_df

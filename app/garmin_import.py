"""Garmin Connect data import module for HRV analysis.

This module provides functions to import sleep, HRV, heart rate, and stress
data from Garmin Connect via the unofficial garminconnect library, bulk
wellness JSON exports, and individual FIT files.

Supported data sources:
- Garmin Connect API (unofficial) via garminconnect library
- Bulk wellness JSON export (ZIP from Account Settings)
- Individual FIT files via fitparse/fitdecode

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

import pandas as pd

if TYPE_CHECKING:
    from collections.abc import Iterator

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)

# Garmin Connect wellness JSON file patterns (inside DI_CONNECT/DI-Connect-Wellness/)
_SLEEP_FILE_SUFFIX: Final[str] = "_sleepData.json"
_HRV_FILE_SUFFIX: Final[str] = "_hrvData.json"
_STRESS_FILE_SUFFIX: Final[str] = "_stressData.json"
_HR_FILE_SUFFIX: Final[str] = "_heartRateData.json"

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
        source: Data source description.
    """

    sleep_df: pd.DataFrame = field(default_factory=pd.DataFrame)
    hrv_df: pd.DataFrame = field(default_factory=pd.DataFrame)
    hr_df: pd.DataFrame = field(default_factory=pd.DataFrame)
    stress_df: pd.DataFrame = field(default_factory=pd.DataFrame)
    source: str = "unknown"


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
    """
    client = _get_garmin_client(credentials)
    records: list[dict[str, Any]] = []

    current = start_date
    while current <= end_date:
        try:
            data = client.get_sleep_data(current.isoformat())
            if data and isinstance(data, dict):
                daily_summary = data.get("dailySleepDTO", {})
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
                        "overall", {}).get("value"),
                    "sleep_start": daily_summary.get("sleepStartTimestampGMT"),
                    "sleep_end": daily_summary.get("sleepEndTimestampGMT"),
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
        file_type is one of: "sleep", "hrv", "stress", "hr".
    """
    suffixes = {
        _SLEEP_FILE_SUFFIX: "sleep",
        _HRV_FILE_SUFFIX: "hrv",
        _STRESS_FILE_SUFFIX: "stress",
        _HR_FILE_SUFFIX: "hr",
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

    result.sleep_df = pd.DataFrame(sleep_records) if sleep_records else pd.DataFrame()
    result.hrv_df = pd.DataFrame(hrv_records) if hrv_records else pd.DataFrame()
    result.stress_df = pd.DataFrame(stress_records) if stress_records else pd.DataFrame()
    result.hr_df = pd.DataFrame(hr_records) if hr_records else pd.DataFrame()

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


# ---------------------------------------------------------------------------
# FIT file parsing
# ---------------------------------------------------------------------------


def parse_fit_file(fit_path: Path) -> pd.DataFrame:
    """Parse a Garmin FIT file for HRV/HR data.

    Args:
        fit_path: Path to the FIT file.

    Returns:
        DataFrame with available data (HR, HRV, etc.).
        Columns depend on data present in the FIT file.

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

    records: list[dict[str, Any]] = []
    hrv_records: list[dict[str, Any]] = []

    with open(fit_path, "rb") as f:
        fit_file = fitparse.FitFile(f)
        for record in fit_file.get_messages():
            record_dict: dict[str, Any] = {}
            record_type = record.name

            for field in record.fields:
                record_dict[field.name] = field.value

            if record_type == "record":
                # Activity record with HR, cadence, etc.
                records.append(record_dict)
            elif record_type == "hrv":
                # HRV record with RR intervals
                hrv_records.append(record_dict)

    # Combine into DataFrames
    df = pd.DataFrame(records) if records else pd.DataFrame()
    hrv_df = pd.DataFrame(hrv_records) if hrv_records else pd.DataFrame()

    # If HRV data exists, extract RR intervals
    if not hrv_df.empty and "time" in hrv_df.columns:
        # HRV records contain arrays of RR intervals
        rr_intervals: list[float] = []
        for _, row in hrv_df.iterrows():
            time_vals = row.get("time")
            if isinstance(time_vals, (list, tuple)):
                rr_intervals.extend([t for t in time_vals if t is not None])
        if rr_intervals:
            df = pd.DataFrame({"rr_interval_ms": rr_intervals})

    return df


def parse_fit_bytes(fit_bytes: bytes) -> pd.DataFrame:
    """Parse FIT file from bytes (e.g., from API download).

    Args:
        fit_bytes: Raw FIT file bytes.

    Returns:
        DataFrame with available data.
    """
    try:
        import fitparse
    except ImportError as exc:
        msg = "fitparse library not installed. Run: pip install fitparse"
        raise ImportError(msg) from exc

    records: list[dict[str, Any]] = []
    fit_file = fitparse.FitFile(io.BytesIO(fit_bytes))

    for record in fit_file.get_messages("record"):
        record_dict: dict[str, Any] = {}
        for field in record.fields:
            record_dict[field.name] = field.value
        records.append(record_dict)

    return pd.DataFrame(records) if records else pd.DataFrame()


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

    # Check for optical sensor limitations
    if not data.hrv_df.empty:
        warnings.append(
            "Note: Optical HR sensor HRV is less accurate than chest strap; "
            "beat-level analysis may be limited"
        )

    metrics["warnings"] = warnings
    metrics["quality_ok"] = len(warnings) <= 1  # Allow optical sensor note

    return metrics


# ---------------------------------------------------------------------------
# High-level import function
# ---------------------------------------------------------------------------


def import_garmin_data(
    credentials: GarminCredentials | None = None,
    zip_path: Path | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> GarminWellnessData:
    """Import Garmin wellness data from available sources.

    Attempts to load data from:
    1. Bulk wellness ZIP export (if provided)
    2. Garmin Connect API (if credentials provided)

    Args:
        credentials: Garmin Connect credentials (optional).
        zip_path: Path to Garmin wellness export ZIP (optional).
        start_date: Start date for API fetch (default: 7 days ago).
        end_date: End date for API fetch (default: today).

    Returns:
        GarminWellnessData with available data.

    Raises:
        ValueError: If neither credentials nor zip_path provided.
    """
    if zip_path is None and credentials is None:
        msg = "Either credentials or zip_path must be provided"
        raise ValueError(msg)

    # Try ZIP export first (more complete data)
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
        return data

    return GarminWellnessData(source="none")


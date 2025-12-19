"""Multi-Modal Sensor Fusion Module.

This module provides integration with multiple wearable sensor platforms
to create a unified physiological data model for comprehensive analysis.

Author: Dr. Diego Malpica, MD
        Aerospace Medicine Specialist
        National University of Colombia

Supported Platforms:
    - Oura Ring (sleep, HRV, activity, readiness)
    - WHOOP (strain, recovery, sleep)
    - Apple Health (heart rate, HRV, activity, sleep)
    - Fitbit (heart rate, HRV, sleep, SpO2)
    - Polar (heart rate, RR intervals, training)

References:
    - Stone, J. D., et al. (2021). Accuracy of WHOOP 4.0 for Sleep Detection.
    - Roberts, D. M., et al. (2020). Accuracy of Oura Ring for Sleep Detection.
"""

from __future__ import annotations

import json
import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Final, TypedDict
import zipfile

import numpy as np
from numpy.typing import NDArray
import pandas as pd

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)

# Data quality thresholds
MIN_HRV_SAMPLES_FOR_ANALYSIS: Final[int] = 30
MIN_SLEEP_DURATION_MINUTES: Final[int] = 30
MAX_HR_BPM: Final[float] = 220.0
MIN_HR_BPM: Final[float] = 30.0


class DataSource(Enum):
    """Supported data sources."""
    
    OURA = "oura"
    WHOOP = "whoop"
    APPLE_HEALTH = "apple_health"
    FITBIT = "fitbit"
    POLAR = "polar"
    GARMIN = "garmin"
    SAMSUNG_HEALTH = "samsung_health"
    UNKNOWN = "unknown"


class SleepStageMapping(Enum):
    """Unified sleep stage mapping."""
    
    WAKE = 0
    LIGHT = 1  # N1 + N2
    DEEP = 2   # N3
    REM = 3
    UNKNOWN = -1


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class UnifiedHRVData:
    """Unified HRV data from any source.
    
    Attributes:
        timestamp: Measurement timestamp (UTC).
        rmssd_ms: RMSSD value in milliseconds.
        sdnn_ms: SDNN value in milliseconds (if available).
        mean_hr_bpm: Mean heart rate in BPM.
        respiratory_rate: Respiratory rate in breaths/min (if available).
        hrv_score: Platform-specific HRV score (0-100, if available).
        measurement_duration_s: Duration of measurement in seconds.
        source: Data source platform.
        confidence: Data quality confidence (0-1).
        raw_rr_intervals_ms: Raw RR intervals if available.
    """
    
    timestamp: datetime
    rmssd_ms: float
    sdnn_ms: float | None = None
    mean_hr_bpm: float | None = None
    respiratory_rate: float | None = None
    hrv_score: float | None = None
    measurement_duration_s: float | None = None
    source: DataSource = DataSource.UNKNOWN
    confidence: float = 1.0
    raw_rr_intervals_ms: NDArray[np.float64] = field(default_factory=lambda: np.array([]))


@dataclass(slots=True)
class UnifiedSleepData:
    """Unified sleep data from any source.
    
    Attributes:
        date: Sleep date (night starting).
        bedtime: Time went to bed.
        wake_time: Time woke up.
        total_sleep_minutes: Total sleep time in minutes.
        sleep_efficiency: Sleep efficiency percentage.
        sleep_latency_minutes: Time to fall asleep.
        wake_after_sleep_onset_minutes: WASO in minutes.
        light_sleep_minutes: Light sleep duration.
        deep_sleep_minutes: Deep sleep duration.
        rem_sleep_minutes: REM sleep duration.
        awakenings: Number of awakenings.
        sleep_score: Platform-specific sleep score (0-100).
        hrv_during_sleep: Average HRV during sleep.
        rhr_during_sleep: Resting heart rate during sleep.
        respiratory_rate: Average respiratory rate.
        spo2_average: Average SpO2 during sleep.
        spo2_minimum: Minimum SpO2 during sleep.
        stages: List of (timestamp, stage) tuples for hypnogram.
        source: Data source platform.
        confidence: Data quality confidence (0-1).
    """
    
    date: date
    bedtime: datetime | None = None
    wake_time: datetime | None = None
    total_sleep_minutes: float = 0.0
    sleep_efficiency: float = 0.0
    sleep_latency_minutes: float = 0.0
    wake_after_sleep_onset_minutes: float = 0.0
    light_sleep_minutes: float = 0.0
    deep_sleep_minutes: float = 0.0
    rem_sleep_minutes: float = 0.0
    awakenings: int = 0
    sleep_score: float | None = None
    hrv_during_sleep: float | None = None
    rhr_during_sleep: float | None = None
    respiratory_rate: float | None = None
    spo2_average: float | None = None
    spo2_minimum: float | None = None
    stages: list[tuple[datetime, SleepStageMapping]] = field(default_factory=list)
    source: DataSource = DataSource.UNKNOWN
    confidence: float = 1.0


@dataclass(slots=True)
class UnifiedActivityData:
    """Unified activity data from any source.
    
    Attributes:
        date: Activity date.
        steps: Total steps.
        distance_km: Total distance in kilometers.
        active_calories: Calories burned during activity.
        total_calories: Total calories burned.
        active_minutes: Minutes of activity.
        sedentary_minutes: Minutes sedentary.
        floors_climbed: Floors climbed (if available).
        activity_score: Platform-specific activity score.
        strain_score: Platform-specific strain score (WHOOP).
        training_load: Training load estimate.
        vo2max_estimate: VO2max estimate (if available).
        source: Data source platform.
        confidence: Data quality confidence (0-1).
    """
    
    date: date
    steps: int = 0
    distance_km: float = 0.0
    active_calories: float = 0.0
    total_calories: float = 0.0
    active_minutes: int = 0
    sedentary_minutes: int = 0
    floors_climbed: int = 0
    activity_score: float | None = None
    strain_score: float | None = None
    training_load: float | None = None
    vo2max_estimate: float | None = None
    source: DataSource = DataSource.UNKNOWN
    confidence: float = 1.0


@dataclass(slots=True)
class UnifiedReadinessData:
    """Unified readiness/recovery data from any source.
    
    Attributes:
        date: Assessment date.
        readiness_score: Overall readiness score (0-100).
        recovery_score: Recovery score (WHOOP).
        hrv_balance: HRV relative to baseline.
        rhr_balance: RHR relative to baseline.
        body_temperature_deviation: Temp deviation from baseline (°C).
        sleep_balance: Sleep quality relative to baseline.
        activity_balance: Activity level relative to baseline.
        strain_balance: Recent strain vs recovery capacity.
        recommendations: List of recommendations.
        source: Data source platform.
        confidence: Data quality confidence (0-1).
    """
    
    date: date
    readiness_score: float | None = None
    recovery_score: float | None = None
    hrv_balance: float | None = None
    rhr_balance: float | None = None
    body_temperature_deviation: float | None = None
    sleep_balance: float | None = None
    activity_balance: float | None = None
    strain_balance: float | None = None
    recommendations: list[str] = field(default_factory=list)
    source: DataSource = DataSource.UNKNOWN
    confidence: float = 1.0


@dataclass(slots=True)
class FusedPhysiologicalProfile:
    """Combined physiological profile from multiple sources.
    
    Attributes:
        date: Profile date.
        hrv_data: HRV data from all sources.
        sleep_data: Sleep data from all sources.
        activity_data: Activity data from all sources.
        readiness_data: Readiness data from all sources.
        fused_hrv: Best HRV estimate from all sources.
        fused_sleep: Best sleep estimate from all sources.
        fused_readiness: Best readiness estimate from all sources.
        data_completeness: Percentage of expected data available.
        sources_available: List of available data sources.
    """
    
    date: date
    hrv_data: list[UnifiedHRVData] = field(default_factory=list)
    sleep_data: list[UnifiedSleepData] = field(default_factory=list)
    activity_data: list[UnifiedActivityData] = field(default_factory=list)
    readiness_data: list[UnifiedReadinessData] = field(default_factory=list)
    fused_hrv: UnifiedHRVData | None = None
    fused_sleep: UnifiedSleepData | None = None
    fused_readiness: UnifiedReadinessData | None = None
    data_completeness: float = 0.0
    sources_available: list[DataSource] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Oura Ring Parser
# ---------------------------------------------------------------------------


def parse_oura_export(file_path: Path) -> tuple[list[UnifiedHRVData], list[UnifiedSleepData], list[UnifiedReadinessData]]:
    """Parse Oura Ring JSON export.
    
    Args:
        file_path: Path to Oura export JSON file.
        
    Returns:
        Tuple of (HRV data, sleep data, readiness data).
    """
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    hrv_list: list[UnifiedHRVData] = []
    sleep_list: list[UnifiedSleepData] = []
    readiness_list: list[UnifiedReadinessData] = []
    
    # Parse sleep data
    for sleep_record in data.get("sleep", []):
        try:
            sleep_date = datetime.strptime(sleep_record.get("summary_date", ""), "%Y-%m-%d").date()
            
            bedtime_str = sleep_record.get("bedtime_start")
            wake_str = sleep_record.get("bedtime_end")
            
            bedtime = datetime.fromisoformat(bedtime_str.replace("Z", "+00:00")) if bedtime_str else None
            wake_time = datetime.fromisoformat(wake_str.replace("Z", "+00:00")) if wake_str else None
            
            sleep_data = UnifiedSleepData(
                date=sleep_date,
                bedtime=bedtime,
                wake_time=wake_time,
                total_sleep_minutes=sleep_record.get("total", 0) / 60,  # Oura stores in seconds
                sleep_efficiency=sleep_record.get("efficiency", 0),
                sleep_latency_minutes=sleep_record.get("onset_latency", 0) / 60,
                wake_after_sleep_onset_minutes=sleep_record.get("awake", 0) / 60,
                light_sleep_minutes=sleep_record.get("light", 0) / 60,
                deep_sleep_minutes=sleep_record.get("deep", 0) / 60,
                rem_sleep_minutes=sleep_record.get("rem", 0) / 60,
                awakenings=sleep_record.get("restless", 0),
                sleep_score=sleep_record.get("score"),
                hrv_during_sleep=sleep_record.get("rmssd"),
                rhr_during_sleep=sleep_record.get("hr_lowest"),
                respiratory_rate=sleep_record.get("breath_average"),
                source=DataSource.OURA,
            )
            sleep_list.append(sleep_data)
            
            # Extract HRV from sleep
            if sleep_record.get("rmssd"):
                hrv_data = UnifiedHRVData(
                    timestamp=bedtime or datetime.combine(sleep_date, datetime.min.time()),
                    rmssd_ms=float(sleep_record.get("rmssd", 0)),
                    mean_hr_bpm=float(sleep_record.get("hr_average", 0)) if sleep_record.get("hr_average") else None,
                    respiratory_rate=float(sleep_record.get("breath_average", 0)) if sleep_record.get("breath_average") else None,
                    source=DataSource.OURA,
                )
                hrv_list.append(hrv_data)
                
        except Exception as exc:
            _LOGGER.warning("Failed to parse Oura sleep record: %s", exc)
    
    # Parse readiness data
    for readiness_record in data.get("readiness", []):
        try:
            readiness_date = datetime.strptime(readiness_record.get("summary_date", ""), "%Y-%m-%d").date()
            
            readiness_data = UnifiedReadinessData(
                date=readiness_date,
                readiness_score=readiness_record.get("score"),
                hrv_balance=readiness_record.get("score_hrv_balance"),
                rhr_balance=readiness_record.get("score_resting_hr"),
                body_temperature_deviation=readiness_record.get("score_temperature"),
                sleep_balance=readiness_record.get("score_sleep_balance"),
                activity_balance=readiness_record.get("score_activity_balance"),
                source=DataSource.OURA,
            )
            readiness_list.append(readiness_data)
            
        except Exception as exc:
            _LOGGER.warning("Failed to parse Oura readiness record: %s", exc)
    
    _LOGGER.info(
        "Parsed Oura export: %d sleep records, %d HRV records, %d readiness records",
        len(sleep_list), len(hrv_list), len(readiness_list)
    )
    
    return hrv_list, sleep_list, readiness_list


# ---------------------------------------------------------------------------
# WHOOP Parser
# ---------------------------------------------------------------------------


def parse_whoop_export(file_path: Path) -> tuple[list[UnifiedHRVData], list[UnifiedSleepData], list[UnifiedActivityData], list[UnifiedReadinessData]]:
    """Parse WHOOP CSV export.
    
    WHOOP exports data as a ZIP containing multiple CSVs.
    
    Args:
        file_path: Path to WHOOP export ZIP or CSV file.
        
    Returns:
        Tuple of (HRV data, sleep data, activity data, readiness data).
    """
    hrv_list: list[UnifiedHRVData] = []
    sleep_list: list[UnifiedSleepData] = []
    activity_list: list[UnifiedActivityData] = []
    readiness_list: list[UnifiedReadinessData] = []
    
    # Handle ZIP file
    if file_path.suffix.lower() == ".zip":
        with zipfile.ZipFile(file_path, "r") as zf:
            for name in zf.namelist():
                if name.endswith(".csv"):
                    with zf.open(name) as f:
                        df = pd.read_csv(f)
                        _parse_whoop_csv(df, name, hrv_list, sleep_list, activity_list, readiness_list)
    else:
        df = pd.read_csv(file_path)
        _parse_whoop_csv(df, file_path.name, hrv_list, sleep_list, activity_list, readiness_list)
    
    _LOGGER.info(
        "Parsed WHOOP export: %d sleep records, %d HRV records, %d activity records, %d recovery records",
        len(sleep_list), len(hrv_list), len(activity_list), len(readiness_list)
    )
    
    return hrv_list, sleep_list, activity_list, readiness_list


def _parse_whoop_csv(
    df: pd.DataFrame,
    filename: str,
    hrv_list: list[UnifiedHRVData],
    sleep_list: list[UnifiedSleepData],
    activity_list: list[UnifiedActivityData],
    readiness_list: list[UnifiedReadinessData],
) -> None:
    """Parse a single WHOOP CSV file."""
    
    # WHOOP exports have different CSV formats for different data types
    columns_lower = [c.lower() for c in df.columns]
    
    # Recovery/HRV data
    if "hrv" in columns_lower or "recovery" in columns_lower:
        for _, row in df.iterrows():
            try:
                date_str = str(row.get("date", row.get("Date", "")))
                if not date_str:
                    continue
                    
                record_date = pd.to_datetime(date_str).date()
                
                # HRV data
                hrv_value = row.get("hrv", row.get("HRV", row.get("hrv_rmssd", None)))
                if hrv_value and pd.notna(hrv_value):
                    hrv_data = UnifiedHRVData(
                        timestamp=datetime.combine(record_date, datetime.min.time(), tzinfo=timezone.utc),
                        rmssd_ms=float(hrv_value),
                        mean_hr_bpm=float(row.get("resting_heart_rate", row.get("Resting Heart Rate", 0))) if pd.notna(row.get("resting_heart_rate", row.get("Resting Heart Rate", np.nan))) else None,
                        source=DataSource.WHOOP,
                    )
                    hrv_list.append(hrv_data)
                
                # Recovery data
                recovery_score = row.get("recovery", row.get("Recovery", row.get("recovery_score", None)))
                if recovery_score and pd.notna(recovery_score):
                    readiness_data = UnifiedReadinessData(
                        date=record_date,
                        recovery_score=float(recovery_score),
                        hrv_balance=float(hrv_value) if hrv_value and pd.notna(hrv_value) else None,
                        source=DataSource.WHOOP,
                    )
                    readiness_list.append(readiness_data)
                    
            except Exception as exc:
                _LOGGER.debug("Failed to parse WHOOP recovery row: %s", exc)
    
    # Sleep data
    if "sleep_performance" in columns_lower or "time_in_bed" in columns_lower:
        for _, row in df.iterrows():
            try:
                date_str = str(row.get("date", row.get("Date", "")))
                if not date_str:
                    continue
                    
                record_date = pd.to_datetime(date_str).date()
                
                sleep_data = UnifiedSleepData(
                    date=record_date,
                    total_sleep_minutes=float(row.get("total_sleep_time", 0)) if pd.notna(row.get("total_sleep_time", np.nan)) else 0,
                    sleep_efficiency=float(row.get("sleep_efficiency", row.get("sleep_performance", 0))) if pd.notna(row.get("sleep_efficiency", row.get("sleep_performance", np.nan))) else 0,
                    light_sleep_minutes=float(row.get("light_sleep", 0)) if pd.notna(row.get("light_sleep", np.nan)) else 0,
                    deep_sleep_minutes=float(row.get("slow_wave_sleep", row.get("deep_sleep", 0))) if pd.notna(row.get("slow_wave_sleep", row.get("deep_sleep", np.nan))) else 0,
                    rem_sleep_minutes=float(row.get("rem_sleep", 0)) if pd.notna(row.get("rem_sleep", np.nan)) else 0,
                    awakenings=int(row.get("disturbances", row.get("awakenings", 0))) if pd.notna(row.get("disturbances", row.get("awakenings", np.nan))) else 0,
                    sleep_score=float(row.get("sleep_performance", row.get("sleep_score", None))) if pd.notna(row.get("sleep_performance", row.get("sleep_score", np.nan))) else None,
                    respiratory_rate=float(row.get("respiratory_rate", None)) if pd.notna(row.get("respiratory_rate", np.nan)) else None,
                    source=DataSource.WHOOP,
                )
                sleep_list.append(sleep_data)
                
            except Exception as exc:
                _LOGGER.debug("Failed to parse WHOOP sleep row: %s", exc)
    
    # Strain/Activity data
    if "strain" in columns_lower or "day_strain" in columns_lower:
        for _, row in df.iterrows():
            try:
                date_str = str(row.get("date", row.get("Date", "")))
                if not date_str:
                    continue
                    
                record_date = pd.to_datetime(date_str).date()
                
                activity_data = UnifiedActivityData(
                    date=record_date,
                    active_calories=float(row.get("calories", row.get("kilojoules", 0) * 0.239)) if pd.notna(row.get("calories", row.get("kilojoules", np.nan))) else 0,
                    strain_score=float(row.get("strain", row.get("day_strain", None))) if pd.notna(row.get("strain", row.get("day_strain", np.nan))) else None,
                    source=DataSource.WHOOP,
                )
                activity_list.append(activity_data)
                
            except Exception as exc:
                _LOGGER.debug("Failed to parse WHOOP strain row: %s", exc)


# ---------------------------------------------------------------------------
# Apple Health Parser
# ---------------------------------------------------------------------------


def parse_apple_health_export(file_path: Path) -> tuple[list[UnifiedHRVData], list[UnifiedSleepData], list[UnifiedActivityData]]:
    """Parse Apple Health XML export.
    
    Args:
        file_path: Path to Apple Health export.xml or export.zip.
        
    Returns:
        Tuple of (HRV data, sleep data, activity data).
    """
    hrv_list: list[UnifiedHRVData] = []
    sleep_list: list[UnifiedSleepData] = []
    activity_list: list[UnifiedActivityData] = []
    
    # Handle ZIP file
    if file_path.suffix.lower() == ".zip":
        with zipfile.ZipFile(file_path, "r") as zf:
            # Find export.xml in the ZIP
            for name in zf.namelist():
                if name.endswith("export.xml"):
                    with zf.open(name) as f:
                        _parse_apple_health_xml(f, hrv_list, sleep_list, activity_list)
                    break
    else:
        with open(file_path, "rb") as f:
            _parse_apple_health_xml(f, hrv_list, sleep_list, activity_list)
    
    _LOGGER.info(
        "Parsed Apple Health export: %d HRV records, %d sleep records, %d activity records",
        len(hrv_list), len(sleep_list), len(activity_list)
    )
    
    return hrv_list, sleep_list, activity_list


def _parse_apple_health_xml(
    file_obj,
    hrv_list: list[UnifiedHRVData],
    sleep_list: list[UnifiedSleepData],
    activity_list: list[UnifiedActivityData],
) -> None:
    """Parse Apple Health XML content."""
    
    # Use iterparse for large files
    context = ET.iterparse(file_obj, events=("end",))
    
    # Temporary storage for aggregating daily data
    daily_activity: dict[date, dict[str, Any]] = {}
    daily_sleep: dict[date, dict[str, Any]] = {}
    
    for event, elem in context:
        if elem.tag == "Record":
            record_type = elem.get("type", "")
            
            try:
                # HRV SDNN
                if record_type == "HKQuantityTypeIdentifierHeartRateVariabilitySDNN":
                    timestamp_str = elem.get("startDate", "")
                    if timestamp_str:
                        timestamp = pd.to_datetime(timestamp_str).to_pydatetime()
                        if timestamp.tzinfo is None:
                            timestamp = timestamp.replace(tzinfo=timezone.utc)
                        
                        sdnn_value = float(elem.get("value", 0))
                        
                        hrv_data = UnifiedHRVData(
                            timestamp=timestamp,
                            rmssd_ms=sdnn_value * 0.71,  # Approximate RMSSD from SDNN
                            sdnn_ms=sdnn_value,
                            source=DataSource.APPLE_HEALTH,
                        )
                        hrv_list.append(hrv_data)
                
                # Heart rate
                elif record_type == "HKQuantityTypeIdentifierHeartRate":
                    timestamp_str = elem.get("startDate", "")
                    if timestamp_str:
                        timestamp = pd.to_datetime(timestamp_str).to_pydatetime()
                        record_date = timestamp.date()
                        
                        hr_value = float(elem.get("value", 0))
                        
                        # Update daily activity
                        if record_date not in daily_activity:
                            daily_activity[record_date] = {
                                "hr_values": [],
                                "steps": 0,
                                "distance": 0,
                                "active_energy": 0,
                            }
                        daily_activity[record_date]["hr_values"].append(hr_value)
                
                # Steps
                elif record_type == "HKQuantityTypeIdentifierStepCount":
                    timestamp_str = elem.get("startDate", "")
                    if timestamp_str:
                        timestamp = pd.to_datetime(timestamp_str).to_pydatetime()
                        record_date = timestamp.date()
                        
                        steps = int(float(elem.get("value", 0)))
                        
                        if record_date not in daily_activity:
                            daily_activity[record_date] = {
                                "hr_values": [],
                                "steps": 0,
                                "distance": 0,
                                "active_energy": 0,
                            }
                        daily_activity[record_date]["steps"] += steps
                
                # Distance
                elif record_type == "HKQuantityTypeIdentifierDistanceWalkingRunning":
                    timestamp_str = elem.get("startDate", "")
                    if timestamp_str:
                        timestamp = pd.to_datetime(timestamp_str).to_pydatetime()
                        record_date = timestamp.date()
                        
                        distance = float(elem.get("value", 0))
                        unit = elem.get("unit", "km")
                        if unit == "m":
                            distance /= 1000
                        
                        if record_date not in daily_activity:
                            daily_activity[record_date] = {
                                "hr_values": [],
                                "steps": 0,
                                "distance": 0,
                                "active_energy": 0,
                            }
                        daily_activity[record_date]["distance"] += distance
                
                # Active energy
                elif record_type == "HKQuantityTypeIdentifierActiveEnergyBurned":
                    timestamp_str = elem.get("startDate", "")
                    if timestamp_str:
                        timestamp = pd.to_datetime(timestamp_str).to_pydatetime()
                        record_date = timestamp.date()
                        
                        energy = float(elem.get("value", 0))
                        unit = elem.get("unit", "kcal")
                        if unit == "kJ":
                            energy *= 0.239
                        
                        if record_date not in daily_activity:
                            daily_activity[record_date] = {
                                "hr_values": [],
                                "steps": 0,
                                "distance": 0,
                                "active_energy": 0,
                            }
                        daily_activity[record_date]["active_energy"] += energy
                
                # Sleep analysis
                elif record_type == "HKCategoryTypeIdentifierSleepAnalysis":
                    start_str = elem.get("startDate", "")
                    end_str = elem.get("endDate", "")
                    value = elem.get("value", "")
                    
                    if start_str and end_str:
                        start_time = pd.to_datetime(start_str).to_pydatetime()
                        end_time = pd.to_datetime(end_str).to_pydatetime()
                        sleep_date = start_time.date()
                        
                        duration_minutes = (end_time - start_time).total_seconds() / 60
                        
                        if sleep_date not in daily_sleep:
                            daily_sleep[sleep_date] = {
                                "total_minutes": 0,
                                "asleep_minutes": 0,
                                "deep_minutes": 0,
                                "rem_minutes": 0,
                                "bedtime": start_time,
                                "wake_time": end_time,
                            }
                        
                        # Update based on sleep value
                        if "Asleep" in value or "Core" in value:
                            daily_sleep[sleep_date]["asleep_minutes"] += duration_minutes
                        elif "Deep" in value:
                            daily_sleep[sleep_date]["deep_minutes"] += duration_minutes
                        elif "REM" in value:
                            daily_sleep[sleep_date]["rem_minutes"] += duration_minutes
                        
                        daily_sleep[sleep_date]["total_minutes"] += duration_minutes
                        
                        # Update bedtime/wake_time
                        if start_time < daily_sleep[sleep_date]["bedtime"]:
                            daily_sleep[sleep_date]["bedtime"] = start_time
                        if end_time > daily_sleep[sleep_date]["wake_time"]:
                            daily_sleep[sleep_date]["wake_time"] = end_time
                            
            except Exception as exc:
                _LOGGER.debug("Failed to parse Apple Health record: %s", exc)
            
            # Clear element to free memory
            elem.clear()
    
    # Convert aggregated daily data to unified format
    for record_date, data in daily_activity.items():
        activity_data = UnifiedActivityData(
            date=record_date,
            steps=data["steps"],
            distance_km=data["distance"],
            active_calories=data["active_energy"],
            source=DataSource.APPLE_HEALTH,
        )
        activity_list.append(activity_data)
    
    for sleep_date, data in daily_sleep.items():
        if data["total_minutes"] >= MIN_SLEEP_DURATION_MINUTES:
            sleep_data = UnifiedSleepData(
                date=sleep_date,
                bedtime=data["bedtime"],
                wake_time=data["wake_time"],
                total_sleep_minutes=data["asleep_minutes"] + data["deep_minutes"] + data["rem_minutes"],
                light_sleep_minutes=data["asleep_minutes"],
                deep_sleep_minutes=data["deep_minutes"],
                rem_sleep_minutes=data["rem_minutes"],
                source=DataSource.APPLE_HEALTH,
            )
            sleep_list.append(sleep_data)


# ---------------------------------------------------------------------------
# Fitbit Parser
# ---------------------------------------------------------------------------


def parse_fitbit_export(file_path: Path) -> tuple[list[UnifiedHRVData], list[UnifiedSleepData], list[UnifiedActivityData]]:
    """Parse Fitbit JSON export.
    
    Args:
        file_path: Path to Fitbit export folder or ZIP.
        
    Returns:
        Tuple of (HRV data, sleep data, activity data).
    """
    hrv_list: list[UnifiedHRVData] = []
    sleep_list: list[UnifiedSleepData] = []
    activity_list: list[UnifiedActivityData] = []
    
    # Handle ZIP file or folder
    if file_path.suffix.lower() == ".zip":
        with zipfile.ZipFile(file_path, "r") as zf:
            for name in zf.namelist():
                if name.endswith(".json"):
                    with zf.open(name) as f:
                        try:
                            data = json.load(f)
                            _parse_fitbit_json(data, name, hrv_list, sleep_list, activity_list)
                        except json.JSONDecodeError:
                            pass
    elif file_path.is_dir():
        for json_file in file_path.glob("**/*.json"):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    _parse_fitbit_json(data, json_file.name, hrv_list, sleep_list, activity_list)
            except Exception as exc:
                _LOGGER.debug("Failed to parse Fitbit file %s: %s", json_file, exc)
    
    _LOGGER.info(
        "Parsed Fitbit export: %d HRV records, %d sleep records, %d activity records",
        len(hrv_list), len(sleep_list), len(activity_list)
    )
    
    return hrv_list, sleep_list, activity_list


def _parse_fitbit_json(
    data: Any,
    filename: str,
    hrv_list: list[UnifiedHRVData],
    sleep_list: list[UnifiedSleepData],
    activity_list: list[UnifiedActivityData],
) -> None:
    """Parse a single Fitbit JSON file."""
    
    filename_lower = filename.lower()
    
    # HRV data
    if "hrv" in filename_lower:
        if isinstance(data, list):
            for record in data:
                try:
                    date_str = record.get("dateTime", record.get("date", ""))
                    if date_str:
                        timestamp = pd.to_datetime(date_str).to_pydatetime()
                        if timestamp.tzinfo is None:
                            timestamp = timestamp.replace(tzinfo=timezone.utc)
                        
                        hrv_value = record.get("value", {})
                        if isinstance(hrv_value, dict):
                            rmssd = hrv_value.get("rmssd", hrv_value.get("dailyRmssd", 0))
                        else:
                            rmssd = float(hrv_value)
                        
                        if rmssd > 0:
                            hrv_data = UnifiedHRVData(
                                timestamp=timestamp,
                                rmssd_ms=rmssd,
                                source=DataSource.FITBIT,
                            )
                            hrv_list.append(hrv_data)
                except (KeyError, TypeError, ValueError) as exc:
                    _LOGGER.debug("Failed to parse Fitbit HRV record: %s", exc)
    
    # Sleep data
    if "sleep" in filename_lower:
        records = data if isinstance(data, list) else data.get("sleep", [])
        for record in records:
            try:
                date_str = record.get("dateOfSleep", "")
                if date_str:
                    sleep_date = pd.to_datetime(date_str).date()
                    
                    start_str = record.get("startTime", "")
                    end_str = record.get("endTime", "")
                    
                    bedtime = pd.to_datetime(start_str).to_pydatetime() if start_str else None
                    wake_time = pd.to_datetime(end_str).to_pydatetime() if end_str else None
                    
                    # Get sleep stages
                    levels = record.get("levels", {})
                    summary = levels.get("summary", {})
                    
                    sleep_data = UnifiedSleepData(
                        date=sleep_date,
                        bedtime=bedtime,
                        wake_time=wake_time,
                        total_sleep_minutes=record.get("minutesAsleep", 0),
                        sleep_efficiency=record.get("efficiency", 0),
                        wake_after_sleep_onset_minutes=record.get("minutesAwake", 0),
                        light_sleep_minutes=summary.get("light", {}).get("minutes", 0),
                        deep_sleep_minutes=summary.get("deep", {}).get("minutes", 0),
                        rem_sleep_minutes=summary.get("rem", {}).get("minutes", 0),
                        awakenings=record.get("awakeCount", 0),
                        source=DataSource.FITBIT,
                    )
                    sleep_list.append(sleep_data)
            except (KeyError, TypeError, ValueError) as exc:
                _LOGGER.debug("Failed to parse Fitbit sleep record: %s", exc)
    
    # Activity data
    if "activities" in filename_lower or "daily" in filename_lower:
        records = data if isinstance(data, list) else [data]
        for record in records:
            try:
                date_str = record.get("dateTime", record.get("date", ""))
                if date_str:
                    activity_date = pd.to_datetime(date_str).date()
                    
                    activity_data = UnifiedActivityData(
                        date=activity_date,
                        steps=int(record.get("steps", record.get("value", 0))),
                        distance_km=float(record.get("distance", 0)),
                        active_calories=float(record.get("activityCalories", record.get("caloriesOut", 0))),
                        active_minutes=int(record.get("fairlyActiveMinutes", 0)) + int(record.get("veryActiveMinutes", 0)),
                        sedentary_minutes=int(record.get("sedentaryMinutes", 0)),
                        floors_climbed=int(record.get("floors", 0)),
                        source=DataSource.FITBIT,
                    )
                    activity_list.append(activity_data)
            except (KeyError, TypeError, ValueError) as exc:
                _LOGGER.debug("Failed to parse Fitbit activity record: %s", exc)


# ---------------------------------------------------------------------------
# Data Fusion
# ---------------------------------------------------------------------------


def fuse_hrv_data(hrv_records: list[UnifiedHRVData]) -> UnifiedHRVData | None:
    """Fuse HRV data from multiple sources into a single estimate.
    
    Priority order (based on typical accuracy):
    1. Polar (chest strap)
    2. Garmin (when using chest strap)
    3. Oura (nighttime measurements)
    4. WHOOP (nighttime measurements)
    5. Apple Watch
    6. Fitbit
    
    Args:
        hrv_records: List of HRV records from different sources.
        
    Returns:
        Fused HRV data or None if no valid records.
    """
    if not hrv_records:
        return None
    
    # Priority weights
    source_priority: dict[DataSource, float] = {
        DataSource.POLAR: 1.0,
        DataSource.GARMIN: 0.9,
        DataSource.OURA: 0.85,
        DataSource.WHOOP: 0.85,
        DataSource.APPLE_HEALTH: 0.7,
        DataSource.FITBIT: 0.65,
        DataSource.SAMSUNG_HEALTH: 0.6,
        DataSource.UNKNOWN: 0.5,
    }
    
    # Weighted average
    total_weight = 0.0
    weighted_rmssd = 0.0
    weighted_hr = 0.0
    hr_count = 0
    
    best_record: UnifiedHRVData | None = None
    best_priority = 0.0
    
    for record in hrv_records:
        weight = source_priority.get(record.source, 0.5) * record.confidence
        weighted_rmssd += record.rmssd_ms * weight
        total_weight += weight
        
        if record.mean_hr_bpm:
            weighted_hr += record.mean_hr_bpm * weight
            hr_count += 1
        
        # Track best single record
        priority = source_priority.get(record.source, 0.5)
        if priority > best_priority:
            best_priority = priority
            best_record = record
    
    if total_weight == 0:
        return best_record
    
    # Create fused record
    fused_rmssd = weighted_rmssd / total_weight
    fused_hr = weighted_hr / total_weight if hr_count > 0 else None
    
    return UnifiedHRVData(
        timestamp=hrv_records[0].timestamp,
        rmssd_ms=fused_rmssd,
        mean_hr_bpm=fused_hr,
        source=DataSource.UNKNOWN,  # Indicates fused data
        confidence=min(1.0, total_weight / len(hrv_records)),
    )


def _compute_fusion_confidence(
    sleep_records: list[UnifiedSleepData],
    tst_values: list[float],
    efficiency_values: list[float],
) -> float:
    """Compute confidence score for fused sleep data based on source agreement.
    
    Confidence is based on the coefficient of variation (CV) of averaged metrics.
    Low CV (high agreement) yields high confidence; high CV yields lower confidence.
    
    Args:
        sleep_records: Input sleep records being fused.
        tst_values: Total sleep time values from all sources.
        efficiency_values: Sleep efficiency values from all sources.
        
    Returns:
        Confidence score between 0.0 and 1.0.
    """
    if len(sleep_records) <= 1:
        # Single source: use its confidence if available, otherwise moderate default
        return sleep_records[0].confidence if sleep_records else 0.5
    
    cv_scores: list[float] = []
    
    # Compute CV for total sleep time
    if len(tst_values) >= 2:
        tst_mean = float(np.mean(tst_values))
        tst_std = float(np.std(tst_values, ddof=1))
        if tst_mean > 0:
            cv_tst = tst_std / tst_mean
            # Convert CV to confidence: CV=0 → 1.0, CV≥0.5 → 0.0
            cv_scores.append(max(0.0, 1.0 - 2.0 * cv_tst))
    
    # Compute CV for sleep efficiency
    if len(efficiency_values) >= 2:
        eff_mean = float(np.mean(efficiency_values))
        eff_std = float(np.std(efficiency_values, ddof=1))
        if eff_mean > 0:
            cv_eff = eff_std / eff_mean
            cv_scores.append(max(0.0, 1.0 - 2.0 * cv_eff))
    
    if cv_scores:
        # Average agreement-based confidence
        return float(np.mean(cv_scores))
    
    # Fallback: moderate confidence for fused data with insufficient metrics
    return 0.6


def fuse_sleep_data(sleep_records: list[UnifiedSleepData]) -> UnifiedSleepData | None:
    """Fuse sleep data from multiple sources.
    
    Priority order:
    1. Somfit/PSG (medical grade)
    2. Oura (well-validated)
    3. WHOOP
    4. Garmin
    5. Apple Watch
    6. Fitbit
    
    Args:
        sleep_records: List of sleep records from different sources.
        
    Returns:
        Fused sleep data or None if no valid records.
    """
    if not sleep_records:
        return None
    
    # Find highest priority record as base
    source_priority: dict[DataSource, int] = {
        DataSource.OURA: 5,
        DataSource.WHOOP: 4,
        DataSource.GARMIN: 3,
        DataSource.APPLE_HEALTH: 2,
        DataSource.FITBIT: 2,
        DataSource.SAMSUNG_HEALTH: 1,
        DataSource.UNKNOWN: 0,
    }
    
    # Sort by priority
    sorted_records = sorted(
        sleep_records,
        key=lambda r: source_priority.get(r.source, 0),
        reverse=True
    )
    
    # Use highest priority as base
    base = sorted_records[0]
    
    # Average metrics where available from multiple sources
    tst_values = [r.total_sleep_minutes for r in sleep_records if r.total_sleep_minutes > 0]
    efficiency_values = [r.sleep_efficiency for r in sleep_records if r.sleep_efficiency > 0]
    
    return UnifiedSleepData(
        date=base.date,
        bedtime=base.bedtime,
        wake_time=base.wake_time,
        total_sleep_minutes=np.mean(tst_values) if tst_values else base.total_sleep_minutes,
        sleep_efficiency=np.mean(efficiency_values) if efficiency_values else base.sleep_efficiency,
        sleep_latency_minutes=base.sleep_latency_minutes,
        wake_after_sleep_onset_minutes=base.wake_after_sleep_onset_minutes,
        light_sleep_minutes=base.light_sleep_minutes,
        deep_sleep_minutes=base.deep_sleep_minutes,
        rem_sleep_minutes=base.rem_sleep_minutes,
        awakenings=base.awakenings,
        sleep_score=base.sleep_score,
        hrv_during_sleep=base.hrv_during_sleep,
        rhr_during_sleep=base.rhr_during_sleep,
        respiratory_rate=base.respiratory_rate,
        spo2_average=base.spo2_average,
        spo2_minimum=base.spo2_minimum,
        stages=base.stages,
        source=DataSource.UNKNOWN,  # Indicates fused
        confidence=_compute_fusion_confidence(sleep_records, tst_values, efficiency_values),
    )


def create_fused_profile(
    hrv_data: list[UnifiedHRVData],
    sleep_data: list[UnifiedSleepData],
    activity_data: list[UnifiedActivityData],
    readiness_data: list[UnifiedReadinessData],
    target_date: date,
) -> FusedPhysiologicalProfile:
    """Create a fused physiological profile for a specific date.
    
    Args:
        hrv_data: All HRV data.
        sleep_data: All sleep data.
        activity_data: All activity data.
        readiness_data: All readiness data.
        target_date: Date to create profile for.
        
    Returns:
        FusedPhysiologicalProfile for the target date.
    """
    # Filter data for target date
    date_hrv = [h for h in hrv_data if h.timestamp.date() == target_date]
    date_sleep = [s for s in sleep_data if s.date == target_date]
    date_activity = [a for a in activity_data if a.date == target_date]
    date_readiness = [r for r in readiness_data if r.date == target_date]
    
    # Get unique sources
    sources = set()
    for h in date_hrv:
        sources.add(h.source)
    for s in date_sleep:
        sources.add(s.source)
    for a in date_activity:
        sources.add(a.source)
    for r in date_readiness:
        sources.add(r.source)
    
    # Calculate data completeness
    expected_metrics = 4  # HRV, sleep, activity, readiness
    available_metrics = sum([
        len(date_hrv) > 0,
        len(date_sleep) > 0,
        len(date_activity) > 0,
        len(date_readiness) > 0,
    ])
    completeness = available_metrics / expected_metrics * 100
    
    return FusedPhysiologicalProfile(
        date=target_date,
        hrv_data=date_hrv,
        sleep_data=date_sleep,
        activity_data=date_activity,
        readiness_data=date_readiness,
        fused_hrv=fuse_hrv_data(date_hrv),
        fused_sleep=fuse_sleep_data(date_sleep),
        fused_readiness=date_readiness[0] if date_readiness else None,
        data_completeness=completeness,
        sources_available=list(sources),
    )


# ---------------------------------------------------------------------------
# Import Functions
# ---------------------------------------------------------------------------


def import_wearable_data(
    file_path: Path,
    source: DataSource | None = None,
) -> tuple[list[UnifiedHRVData], list[UnifiedSleepData], list[UnifiedActivityData], list[UnifiedReadinessData]]:
    """Import data from a wearable device export.
    
    Automatically detects the source if not specified.
    
    Args:
        file_path: Path to export file or folder.
        source: Data source (auto-detected if None).
        
    Returns:
        Tuple of (HRV data, sleep data, activity data, readiness data).
    """
    hrv_list: list[UnifiedHRVData] = []
    sleep_list: list[UnifiedSleepData] = []
    activity_list: list[UnifiedActivityData] = []
    readiness_list: list[UnifiedReadinessData] = []
    
    # Auto-detect source
    if source is None:
        source = _detect_data_source(file_path)
    
    _LOGGER.info("Importing data from %s (detected source: %s)", file_path, source.value)
    
    if source == DataSource.OURA:
        hrv_list, sleep_list, readiness_list = parse_oura_export(file_path)
    elif source == DataSource.WHOOP:
        hrv_list, sleep_list, activity_list, readiness_list = parse_whoop_export(file_path)
    elif source == DataSource.APPLE_HEALTH:
        hrv_list, sleep_list, activity_list = parse_apple_health_export(file_path)
    elif source == DataSource.FITBIT:
        hrv_list, sleep_list, activity_list = parse_fitbit_export(file_path)
    else:
        _LOGGER.warning("Unknown data source: %s", source.value)
    
    return hrv_list, sleep_list, activity_list, readiness_list


def _detect_data_source(file_path: Path) -> DataSource:
    """Detect the data source from file structure/content.
    
    Args:
        file_path: Path to export file.
        
    Returns:
        Detected DataSource.
    """
    filename_lower = file_path.name.lower()
    
    # Check filename patterns
    if "oura" in filename_lower:
        return DataSource.OURA
    if "whoop" in filename_lower:
        return DataSource.WHOOP
    if "apple" in filename_lower or "health" in filename_lower:
        return DataSource.APPLE_HEALTH
    if "fitbit" in filename_lower:
        return DataSource.FITBIT
    if "garmin" in filename_lower:
        return DataSource.GARMIN
    if "polar" in filename_lower:
        return DataSource.POLAR
    
    # Check file content
    if file_path.suffix.lower() == ".json":
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            # Oura has specific keys
            if "sleep" in data and "readiness" in data:
                return DataSource.OURA
            # Fitbit patterns
            if "sleep" in data and isinstance(data.get("sleep"), list):
                if data["sleep"] and "minutesAsleep" in data["sleep"][0]:
                    return DataSource.FITBIT
        except (json.JSONDecodeError, OSError, KeyError, IndexError) as exc:
            _LOGGER.debug("Could not determine data source from JSON content: %s", exc)
    
    elif file_path.suffix.lower() == ".xml":
        return DataSource.APPLE_HEALTH
    
    elif file_path.suffix.lower() == ".zip":
        try:
            with zipfile.ZipFile(file_path, "r") as zf:
                names = zf.namelist()
                
                if any("export.xml" in n for n in names):
                    return DataSource.APPLE_HEALTH
                if any("oura" in n.lower() for n in names):
                    return DataSource.OURA
                if any("whoop" in n.lower() for n in names):
                    return DataSource.WHOOP
        except (zipfile.BadZipFile, OSError) as exc:
            _LOGGER.debug("Could not determine data source from ZIP content: %s", exc)
    
    return DataSource.UNKNOWN


# ---------------------------------------------------------------------------
# Utility Functions
# ---------------------------------------------------------------------------


def unified_data_to_dataframe(
    hrv_data: list[UnifiedHRVData],
    sleep_data: list[UnifiedSleepData],
    activity_data: list[UnifiedActivityData],
) -> pd.DataFrame:
    """Convert unified data to a single DataFrame.
    
    Args:
        hrv_data: List of HRV records.
        sleep_data: List of sleep records.
        activity_data: List of activity records.
        
    Returns:
        DataFrame with all data merged by date.
    """
    # Create date-indexed dataframes
    records: list[dict[str, Any]] = []
    
    # Get all unique dates
    all_dates: set[date] = set()
    for h in hrv_data:
        all_dates.add(h.timestamp.date())
    for s in sleep_data:
        all_dates.add(s.date)
    for a in activity_data:
        all_dates.add(a.date)
    
    for d in sorted(all_dates):
        record: dict[str, Any] = {"date": d}
        
        # Add HRV data
        date_hrv = [h for h in hrv_data if h.timestamp.date() == d]
        if date_hrv:
            fused = fuse_hrv_data(date_hrv)
            if fused:
                record["hrv_rmssd_ms"] = fused.rmssd_ms
                record["hrv_mean_hr_bpm"] = fused.mean_hr_bpm
                record["hrv_source"] = fused.source.value
        
        # Add sleep data
        date_sleep = [s for s in sleep_data if s.date == d]
        if date_sleep:
            fused = fuse_sleep_data(date_sleep)
            if fused:
                record["sleep_tst_min"] = fused.total_sleep_minutes
                record["sleep_efficiency"] = fused.sleep_efficiency
                record["sleep_deep_min"] = fused.deep_sleep_minutes
                record["sleep_rem_min"] = fused.rem_sleep_minutes
                record["sleep_score"] = fused.sleep_score
                record["sleep_source"] = fused.source.value
        
        # Add activity data
        date_activity = [a for a in activity_data if a.date == d]
        if date_activity:
            # Sum activity from all sources
            record["activity_steps"] = sum(a.steps for a in date_activity)
            record["activity_distance_km"] = sum(a.distance_km for a in date_activity)
            record["activity_calories"] = sum(a.active_calories for a in date_activity)
        
        records.append(record)
    
    return pd.DataFrame(records)


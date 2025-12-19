"""Wearable data fusion module for multi-device HRV analysis.

This module provides functionality for:
- Importing data from multiple wearable platforms (Oura, Whoop, Apple Watch, Fitbit)
- Cross-validating RR intervals from ECG vs PPG sources
- Signal quality scoring per modality
- Unified data structure for downstream analysis

Supported platforms:
- Oura Ring (JSON export)
- Whoop (CSV export)
- Apple Watch (Health export XML)
- Fitbit (JSON export)
- Garmin (via garmin_import module)

Scientific basis:
- Multi-sensor fusion improves HRV estimation accuracy [Biosensors 2024]
- PPG-derived HRV shows good agreement with ECG under controlled conditions
- Signal quality assessment is critical for wearable HRV validity

References:
- Bent et al. (2020). Investigating sources of inaccuracy in wearable optical HR sensors.
- Georgiou et al. (2018). Can wearable devices accurately measure HRV?
"""

from __future__ import annotations

import json
import logging
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Final

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)

# Quality thresholds
MIN_COVERAGE_PCT: Final[float] = 70.0  # Minimum data coverage for valid analysis
MIN_AGREEMENT_R: Final[float] = 0.80  # Minimum correlation for cross-validation
MAX_ARTIFACT_PCT: Final[float] = 15.0  # Maximum artifact percentage

# Valid RR interval range
MIN_RR_MS: Final[int] = 300
MAX_RR_MS: Final[int] = 2000


class WearablePlatform(str, Enum):
    """Supported wearable platforms."""

    OURA = "oura"
    WHOOP = "whoop"
    APPLE_WATCH = "apple_watch"
    FITBIT = "fitbit"
    GARMIN = "garmin"
    POLAR = "polar"
    UNKNOWN = "unknown"


class SignalSource(str, Enum):
    """Signal source type."""

    ECG = "ecg"
    PPG = "ppg"
    ACCELEROMETER = "accelerometer"
    UNKNOWN = "unknown"


class QualityLevel(str, Enum):
    """Signal quality classification."""

    EXCELLENT = "excellent"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    POOR = "poor"
    INVALID = "invalid"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SignalQualityMetrics:
    """Signal quality assessment metrics.

    Attributes:
        coverage_pct: Percentage of expected data points present.
        artifact_pct: Percentage of samples flagged as artifacts.
        snr_db: Signal-to-noise ratio estimate (dB).
        beat_detection_confidence: Beat detection confidence (0-1).
        motion_artifact_score: Motion artifact severity (0-1).
        quality_level: Overall quality classification.
        quality_score: Numeric quality score (0-100).
        notes: Quality assessment notes.
    """

    coverage_pct: float
    artifact_pct: float
    snr_db: float
    beat_detection_confidence: float
    motion_artifact_score: float
    quality_level: QualityLevel
    quality_score: float
    notes: str = ""


@dataclass(slots=True)
class WearableDataStream:
    """Data stream from a single wearable device.

    Attributes:
        platform: Source platform.
        device_id: Device identifier.
        signal_source: Signal source type (ECG/PPG).
        start_time: Stream start timestamp.
        end_time: Stream end timestamp.
        rr_intervals_ms: RR intervals in milliseconds.
        timestamps: Timestamps for each RR interval.
        heart_rate_bpm: Heart rate values (if available).
        hrv_rmssd: Pre-computed RMSSD values (if available).
        sleep_data: Sleep staging data (if available).
        activity_data: Activity/steps data (if available).
        quality: Signal quality metrics.
        metadata: Additional platform-specific metadata.
    """

    platform: WearablePlatform
    device_id: str
    signal_source: SignalSource
    start_time: datetime
    end_time: datetime
    rr_intervals_ms: np.ndarray = field(default_factory=lambda: np.array([]))
    timestamps: np.ndarray = field(default_factory=lambda: np.array([]))
    heart_rate_bpm: np.ndarray = field(default_factory=lambda: np.array([]))
    hrv_rmssd: np.ndarray = field(default_factory=lambda: np.array([]))
    sleep_data: pd.DataFrame = field(default_factory=pd.DataFrame)
    activity_data: pd.DataFrame = field(default_factory=pd.DataFrame)
    quality: SignalQualityMetrics | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class FusedWearableData:
    """Fused data from multiple wearable sources.

    Attributes:
        streams: List of individual data streams.
        primary_stream: Index of the primary (highest quality) stream.
        fused_rr_ms: Fused RR intervals.
        fused_timestamps: Timestamps for fused data.
        cross_validation: Cross-validation results between streams.
        overall_quality: Overall fused data quality.
        time_range: Tuple of (start, end) timestamps.
    """

    streams: list[WearableDataStream] = field(default_factory=list)
    primary_stream: int = 0
    fused_rr_ms: np.ndarray = field(default_factory=lambda: np.array([]))
    fused_timestamps: np.ndarray = field(default_factory=lambda: np.array([]))
    cross_validation: dict[str, Any] = field(default_factory=dict)
    overall_quality: SignalQualityMetrics | None = None
    time_range: tuple[datetime, datetime] | None = None


@dataclass(frozen=True, slots=True)
class CrossValidationResult:
    """Cross-validation result between two streams.

    Attributes:
        stream1_idx: Index of first stream.
        stream2_idx: Index of second stream.
        correlation_r: Pearson correlation coefficient.
        mean_diff_ms: Mean difference in RR intervals.
        std_diff_ms: Standard deviation of differences.
        agreement_pct: Percentage of intervals within ±10%.
        bland_altman_bias: Bland-Altman bias.
        bland_altman_loa: Limits of agreement (lower, upper).
        is_valid: Whether cross-validation passes threshold.
    """

    stream1_idx: int
    stream2_idx: int
    correlation_r: float
    mean_diff_ms: float
    std_diff_ms: float
    agreement_pct: float
    bland_altman_bias: float
    bland_altman_loa: tuple[float, float]
    is_valid: bool


# ---------------------------------------------------------------------------
# Signal Quality Assessment
# ---------------------------------------------------------------------------


def assess_signal_quality(
    rr_intervals: np.ndarray,
    timestamps: np.ndarray | None = None,
    expected_duration_sec: float | None = None,
    signal_source: SignalSource = SignalSource.UNKNOWN,
) -> SignalQualityMetrics:
    """Assess signal quality of RR interval data.

    Args:
        rr_intervals: Array of RR intervals in milliseconds.
        timestamps: Optional timestamps for each interval.
        expected_duration_sec: Expected recording duration.
        signal_source: Signal source type.

    Returns:
        SignalQualityMetrics with comprehensive quality assessment.
    """
    if len(rr_intervals) == 0:
        return SignalQualityMetrics(
            coverage_pct=0.0,
            artifact_pct=100.0,
            snr_db=0.0,
            beat_detection_confidence=0.0,
            motion_artifact_score=1.0,
            quality_level=QualityLevel.INVALID,
            quality_score=0.0,
            notes="No RR intervals provided",
        )

    rr = np.asarray(rr_intervals, dtype=float)

    # 1. Coverage assessment
    actual_duration = float(np.sum(rr)) / 1000.0  # seconds
    if expected_duration_sec:
        coverage_pct = 100.0 * actual_duration / expected_duration_sec
    else:
        coverage_pct = 100.0  # Assume full coverage if not specified

    # 2. Artifact detection
    # Check for physiologically implausible values
    out_of_range = (rr < MIN_RR_MS) | (rr > MAX_RR_MS)

    # Check for excessive beat-to-beat changes (>25%)
    if len(rr) > 1:
        diff_pct = np.abs(np.diff(rr)) / rr[:-1]
        excessive_change = np.concatenate([[False], diff_pct > 0.25])
    else:
        excessive_change = np.array([False])

    artifacts = out_of_range | excessive_change
    artifact_pct = 100.0 * np.sum(artifacts) / len(rr)

    # 3. SNR estimation (based on variability structure)
    clean_rr = rr[~artifacts]
    if len(clean_rr) > 10:
        # Estimate signal as RMSSD, noise as high-frequency component
        diff_rr = np.diff(clean_rr)
        signal_power = np.var(clean_rr)
        noise_power = np.var(np.diff(diff_rr)) / 2  # Second derivative
        if noise_power > 0:
            snr_db = 10 * np.log10(signal_power / noise_power)
        else:
            snr_db = 30.0  # Very clean signal
    else:
        snr_db = 0.0

    # 4. Beat detection confidence
    # Based on consistency of RR intervals
    if len(clean_rr) > 5:
        cv = np.std(clean_rr) / np.mean(clean_rr)
        # Normal HRV CV is typically 0.05-0.15
        if cv < 0.05:
            beat_confidence = 0.7  # Too regular, might be interpolated
        elif cv < 0.20:
            beat_confidence = 0.95
        elif cv < 0.30:
            beat_confidence = 0.80
        else:
            beat_confidence = 0.60  # High variability, possible artifacts
    else:
        beat_confidence = 0.5

    # 5. Motion artifact score
    # Higher for PPG, based on sudden large changes
    if len(rr) > 10:
        large_jumps = np.sum(np.abs(np.diff(rr)) > 200) / len(rr)
        motion_score = min(1.0, large_jumps * 5)
        if signal_source == SignalSource.PPG:
            motion_score *= 1.2  # PPG more susceptible to motion
    else:
        motion_score = 0.5

    # 6. Overall quality score (0-100)
    quality_score = (
        0.30 * min(100, coverage_pct) +
        0.30 * max(0, 100 - artifact_pct * 2) +
        0.20 * min(100, snr_db * 3) +
        0.10 * beat_confidence * 100 +
        0.10 * (1 - motion_score) * 100
    )

    # 7. Quality level classification
    if quality_score >= 85:
        quality_level = QualityLevel.EXCELLENT
    elif quality_score >= 70:
        quality_level = QualityLevel.GOOD
    elif quality_score >= 50:
        quality_level = QualityLevel.ACCEPTABLE
    elif quality_score >= 30:
        quality_level = QualityLevel.POOR
    else:
        quality_level = QualityLevel.INVALID

    # Generate notes
    notes_parts = []
    if coverage_pct < MIN_COVERAGE_PCT:
        notes_parts.append(f"Low coverage ({coverage_pct:.1f}%)")
    if artifact_pct > MAX_ARTIFACT_PCT:
        notes_parts.append(f"High artifact rate ({artifact_pct:.1f}%)")
    if motion_score > 0.5:
        notes_parts.append("Motion artifacts detected")
    notes = "; ".join(notes_parts) if notes_parts else "Quality acceptable"

    return SignalQualityMetrics(
        coverage_pct=float(min(100, coverage_pct)),
        artifact_pct=float(artifact_pct),
        snr_db=float(snr_db),
        beat_detection_confidence=float(beat_confidence),
        motion_artifact_score=float(motion_score),
        quality_level=quality_level,
        quality_score=float(quality_score),
        notes=notes,
    )


# ---------------------------------------------------------------------------
# Platform-Specific Importers
# ---------------------------------------------------------------------------


def import_oura_data(file_path: Path) -> WearableDataStream:
    """Import data from Oura Ring JSON export.

    Oura exports include:
    - Daily readiness scores
    - Sleep data with HRV
    - Activity data

    Args:
        file_path: Path to Oura JSON export file.

    Returns:
        WearableDataStream with Oura data.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Initialize arrays
    rr_intervals: list[float] = []
    timestamps: list[datetime] = []
    hrv_rmssd: list[float] = []
    hr_values: list[float] = []

    # Parse sleep data (contains HRV)
    sleep_records = data.get("sleep", [])
    sleep_rows: list[dict[str, Any]] = []

    for record in sleep_records:
        # Extract HRV data
        hrv_data = record.get("hrv", {})
        if hrv_data:
            rmssd = hrv_data.get("rmssd")
            if rmssd is not None:
                hrv_rmssd.append(float(rmssd))

            # Some exports include RR intervals
            rr_list = hrv_data.get("rr_intervals", [])
            for rr in rr_list:
                if MIN_RR_MS <= rr <= MAX_RR_MS:
                    rr_intervals.append(float(rr))

        # Extract HR data
        hr_data = record.get("heart_rate", {})
        if hr_data:
            hr_avg = hr_data.get("average")
            if hr_avg:
                hr_values.append(float(hr_avg))

        # Sleep summary
        sleep_rows.append({
            "date": record.get("summary_date"),
            "total_sleep_sec": record.get("total", 0),
            "rem_sec": record.get("rem", 0),
            "deep_sec": record.get("deep", 0),
            "light_sec": record.get("light", 0),
            "awake_sec": record.get("awake", 0),
            "efficiency": record.get("efficiency", 0),
            "score": record.get("score", 0),
        })

    # Determine time range
    if sleep_records:
        dates = [r.get("summary_date") for r in sleep_records if r.get("summary_date")]
        if dates:
            start_date = min(dates)
            end_date = max(dates)
            start_time = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            end_time = datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc) + timedelta(days=1)
        else:
            start_time = datetime.now(timezone.utc)
            end_time = start_time
    else:
        start_time = datetime.now(timezone.utc)
        end_time = start_time

    # Create stream
    stream = WearableDataStream(
        platform=WearablePlatform.OURA,
        device_id="oura_ring",
        signal_source=SignalSource.PPG,
        start_time=start_time,
        end_time=end_time,
        rr_intervals_ms=np.array(rr_intervals),
        hrv_rmssd=np.array(hrv_rmssd),
        heart_rate_bpm=np.array(hr_values),
        sleep_data=pd.DataFrame(sleep_rows) if sleep_rows else pd.DataFrame(),
        metadata={"source_file": str(file_path)},
    )

    # Assess quality
    if len(rr_intervals) > 0:
        duration = (end_time - start_time).total_seconds()
        stream.quality = assess_signal_quality(
            np.array(rr_intervals),
            expected_duration_sec=duration,
            signal_source=SignalSource.PPG,
        )

    return stream


def import_whoop_data(file_path: Path) -> WearableDataStream:
    """Import data from Whoop CSV export.

    Whoop exports include:
    - Recovery scores with HRV
    - Strain data
    - Sleep data

    Args:
        file_path: Path to Whoop CSV export file.

    Returns:
        WearableDataStream with Whoop data.
    """
    # Whoop exports as CSV
    df = pd.read_csv(file_path)

    # Common column mappings
    hrv_col = None
    hr_col = None
    date_col = None

    for col in df.columns:
        col_lower = col.lower()
        if "hrv" in col_lower or "rmssd" in col_lower:
            hrv_col = col
        elif "heart" in col_lower and "rate" in col_lower:
            hr_col = col
        elif "date" in col_lower or "time" in col_lower:
            date_col = col

    hrv_rmssd = df[hrv_col].dropna().values if hrv_col else np.array([])
    hr_values = df[hr_col].dropna().values if hr_col else np.array([])

    # Determine time range
    if date_col and not df[date_col].empty:
        try:
            dates = pd.to_datetime(df[date_col])
            start_time = dates.min().to_pydatetime().replace(tzinfo=timezone.utc)
            end_time = dates.max().to_pydatetime().replace(tzinfo=timezone.utc)
        except (ValueError, TypeError, AttributeError) as exc:
            _LOGGER.debug("Could not parse WHOOP date range, using current time: %s", exc)
            start_time = datetime.now(timezone.utc)
            end_time = start_time
    else:
        start_time = datetime.now(timezone.utc)
        end_time = start_time

    stream = WearableDataStream(
        platform=WearablePlatform.WHOOP,
        device_id="whoop_strap",
        signal_source=SignalSource.PPG,
        start_time=start_time,
        end_time=end_time,
        hrv_rmssd=np.array(hrv_rmssd, dtype=float),
        heart_rate_bpm=np.array(hr_values, dtype=float),
        metadata={"source_file": str(file_path), "columns": list(df.columns)},
    )

    return stream


def import_apple_health_data(file_path: Path) -> WearableDataStream:
    """Import data from Apple Health export.

    Apple Health exports as XML with various record types:
    - HKQuantityTypeIdentifierHeartRate
    - HKQuantityTypeIdentifierHeartRateVariabilitySDNN
    - HKCategoryTypeIdentifierSleepAnalysis

    Args:
        file_path: Path to Apple Health export.xml or export.zip.

    Returns:
        WearableDataStream with Apple Health data.
    """
    # Handle ZIP file
    if file_path.suffix.lower() == ".zip":
        with zipfile.ZipFile(file_path, "r") as zf:
            # Find export.xml in the archive
            xml_files = [n for n in zf.namelist() if n.endswith("export.xml")]
            if not xml_files:
                raise ValueError("No export.xml found in Apple Health ZIP")
            with zf.open(xml_files[0]) as f:
                tree = ET.parse(f)
    else:
        tree = ET.parse(file_path)

    root = tree.getroot()

    # Parse records
    hr_records: list[tuple[datetime, float]] = []
    hrv_records: list[tuple[datetime, float]] = []
    rr_records: list[tuple[datetime, float]] = []

    for record in root.iter("Record"):
        record_type = record.get("type", "")
        value_str = record.get("value", "")
        date_str = record.get("startDate", "")

        if not value_str or not date_str:
            continue

        try:
            # Parse timestamp
            # Format: 2024-01-15 08:30:00 -0500
            dt = datetime.strptime(date_str[:19], "%Y-%m-%d %H:%M:%S")
            dt = dt.replace(tzinfo=timezone.utc)
            value = float(value_str)
        except (ValueError, TypeError):
            continue

        if record_type == "HKQuantityTypeIdentifierHeartRate":
            hr_records.append((dt, value))
        elif record_type == "HKQuantityTypeIdentifierHeartRateVariabilitySDNN":
            hrv_records.append((dt, value))
        elif record_type == "HKQuantityTypeIdentifierHeartRateRecoveryOneMinute":
            pass  # Could be useful for recovery analysis

    # Sort by timestamp
    hr_records.sort(key=lambda x: x[0])
    hrv_records.sort(key=lambda x: x[0])

    # Extract arrays
    hr_timestamps = [r[0] for r in hr_records]
    hr_values = [r[1] for r in hr_records]
    hrv_timestamps = [r[0] for r in hrv_records]
    hrv_values = [r[1] for r in hrv_records]

    # Determine time range
    all_timestamps = hr_timestamps + hrv_timestamps
    if all_timestamps:
        start_time = min(all_timestamps)
        end_time = max(all_timestamps)
    else:
        start_time = datetime.now(timezone.utc)
        end_time = start_time

    stream = WearableDataStream(
        platform=WearablePlatform.APPLE_WATCH,
        device_id="apple_watch",
        signal_source=SignalSource.PPG,
        start_time=start_time,
        end_time=end_time,
        heart_rate_bpm=np.array(hr_values),
        hrv_rmssd=np.array(hrv_values),  # Apple reports SDNN, but we store it here
        timestamps=np.array([t.timestamp() for t in hr_timestamps]),
        metadata={
            "source_file": str(file_path),
            "hrv_metric": "SDNN",
            "n_hr_records": len(hr_records),
            "n_hrv_records": len(hrv_records),
        },
    )

    return stream


def import_fitbit_data(file_path: Path) -> WearableDataStream:
    """Import data from Fitbit JSON export.

    Fitbit exports include:
    - Heart rate data
    - Sleep data
    - Activity data

    Args:
        file_path: Path to Fitbit JSON export file or directory.

    Returns:
        WearableDataStream with Fitbit data.
    """
    # Fitbit exports can be a single JSON or directory of JSONs
    hr_values: list[float] = []
    hr_timestamps: list[datetime] = []
    hrv_values: list[float] = []

    if file_path.is_dir():
        json_files = list(file_path.glob("*.json"))
    else:
        json_files = [file_path]

    for json_file in json_files:
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue

        # Handle different Fitbit export formats
        if isinstance(data, list):
            for item in data:
                # Heart rate data
                if "value" in item and "bpm" in str(item.get("value", {})):
                    try:
                        bpm = item["value"]["bpm"]
                        dt_str = item.get("dateTime", "")
                        if dt_str:
                            dt = datetime.strptime(dt_str[:19], "%Y-%m-%dT%H:%M:%S")
                            dt = dt.replace(tzinfo=timezone.utc)
                            hr_values.append(float(bpm))
                            hr_timestamps.append(dt)
                    except (KeyError, ValueError, TypeError):
                        # Malformed heart rate record; skip and continue
                        continue

                # HRV data (if available)
                if "hrv" in item:
                    try:
                        hrv = item["hrv"]["rmssd"]
                        hrv_values.append(float(hrv))
                    except (KeyError, ValueError, TypeError):
                        # HRV data missing or malformed; skip and continue
                        continue

    # Determine time range
    if hr_timestamps:
        start_time = min(hr_timestamps)
        end_time = max(hr_timestamps)
    else:
        start_time = datetime.now(timezone.utc)
        end_time = start_time

    stream = WearableDataStream(
        platform=WearablePlatform.FITBIT,
        device_id="fitbit",
        signal_source=SignalSource.PPG,
        start_time=start_time,
        end_time=end_time,
        heart_rate_bpm=np.array(hr_values),
        hrv_rmssd=np.array(hrv_values),
        timestamps=np.array([t.timestamp() for t in hr_timestamps]),
        metadata={
            "source_path": str(file_path),
            "n_hr_records": len(hr_values),
        },
    )

    return stream


# ---------------------------------------------------------------------------
# Cross-Validation
# ---------------------------------------------------------------------------


def cross_validate_streams(
    stream1: WearableDataStream,
    stream2: WearableDataStream,
    time_tolerance_sec: float = 60.0,
) -> CrossValidationResult:
    """Cross-validate two data streams.

    Compares RR intervals or HR values from two sources to assess agreement.

    Args:
        stream1: First data stream.
        stream2: Second data stream.
        time_tolerance_sec: Maximum time difference for matching samples.

    Returns:
        CrossValidationResult with agreement metrics.
    """
    # Use RR intervals if available, otherwise HR
    if len(stream1.rr_intervals_ms) > 0 and len(stream2.rr_intervals_ms) > 0:
        values1 = stream1.rr_intervals_ms
        values2 = stream2.rr_intervals_ms
        metric = "rr_ms"
    elif len(stream1.heart_rate_bpm) > 0 and len(stream2.heart_rate_bpm) > 0:
        values1 = stream1.heart_rate_bpm
        values2 = stream2.heart_rate_bpm
        metric = "hr_bpm"
    else:
        # Cannot cross-validate
        return CrossValidationResult(
            stream1_idx=0,
            stream2_idx=1,
            correlation_r=0.0,
            mean_diff_ms=0.0,
            std_diff_ms=0.0,
            agreement_pct=0.0,
            bland_altman_bias=0.0,
            bland_altman_loa=(0.0, 0.0),
            is_valid=False,
        )

    # For simplicity, compare summary statistics if timestamps not aligned
    # In production, would do proper time alignment

    # Use minimum length
    n = min(len(values1), len(values2))
    if n < 10:
        return CrossValidationResult(
            stream1_idx=0,
            stream2_idx=1,
            correlation_r=0.0,
            mean_diff_ms=0.0,
            std_diff_ms=0.0,
            agreement_pct=0.0,
            bland_altman_bias=0.0,
            bland_altman_loa=(0.0, 0.0),
            is_valid=False,
        )

    v1 = values1[:n]
    v2 = values2[:n]

    # Correlation
    correlation_r = float(np.corrcoef(v1, v2)[0, 1])

    # Differences
    diff = v1 - v2
    mean_diff = float(np.mean(diff))
    std_diff = float(np.std(diff, ddof=1))

    # Agreement percentage (within ±10%)
    relative_diff = np.abs(diff) / ((v1 + v2) / 2)
    agreement_pct = 100.0 * np.sum(relative_diff < 0.10) / len(diff)

    # Bland-Altman
    bland_altman_bias = mean_diff
    bland_altman_loa = (mean_diff - 1.96 * std_diff, mean_diff + 1.96 * std_diff)

    # Validity check
    is_valid = (
        correlation_r >= MIN_AGREEMENT_R and
        agreement_pct >= 70.0
    )

    return CrossValidationResult(
        stream1_idx=0,
        stream2_idx=1,
        correlation_r=correlation_r,
        mean_diff_ms=mean_diff,
        std_diff_ms=std_diff,
        agreement_pct=float(agreement_pct),
        bland_altman_bias=bland_altman_bias,
        bland_altman_loa=bland_altman_loa,
        is_valid=is_valid,
    )


# ---------------------------------------------------------------------------
# Data Fusion
# ---------------------------------------------------------------------------


class WearableDataFusion:
    """Fuse data from multiple wearable sources.

    This class:
    - Imports data from various platforms
    - Assesses quality of each stream
    - Cross-validates overlapping streams
    - Selects or combines data for analysis

    Example:
        fusion = WearableDataFusion()
        fusion.add_stream(import_oura_data("oura_export.json"))
        fusion.add_stream(import_apple_health_data("export.xml"))
        fused = fusion.fuse()
    """

    def __init__(self) -> None:
        """Initialize the fusion engine."""
        self._streams: list[WearableDataStream] = []
        self._cross_validations: list[CrossValidationResult] = []

    @property
    def streams(self) -> list[WearableDataStream]:
        """List of added data streams."""
        return self._streams.copy()

    @property
    def n_streams(self) -> int:
        """Number of data streams."""
        return len(self._streams)

    def add_stream(self, stream: WearableDataStream) -> int:
        """Add a data stream.

        Args:
            stream: WearableDataStream to add.

        Returns:
            Index of the added stream.
        """
        # Assess quality if not already done
        if stream.quality is None and len(stream.rr_intervals_ms) > 0:
            duration = (stream.end_time - stream.start_time).total_seconds()
            stream.quality = assess_signal_quality(
                stream.rr_intervals_ms,
                expected_duration_sec=duration,
                signal_source=stream.signal_source,
            )

        self._streams.append(stream)
        return len(self._streams) - 1

    def import_file(self, file_path: Path | str) -> int:
        """Import data from a file and add as stream.

        Auto-detects platform based on file format.

        Args:
            file_path: Path to data file.

        Returns:
            Index of the added stream.

        Raises:
            ValueError: If file format not recognized.
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        # Detect platform by filename or content
        name_lower = path.name.lower()

        if "oura" in name_lower or path.suffix == ".json":
            # Try Oura first
            try:
                stream = import_oura_data(path)
                if len(stream.rr_intervals_ms) > 0 or len(stream.hrv_rmssd) > 0:
                    return self.add_stream(stream)
            except (json.JSONDecodeError, KeyError, ValueError, OSError) as exc:
                _LOGGER.debug("File %s not Oura format, trying Fitbit: %s", path.name, exc)

            # Try Fitbit
            try:
                stream = import_fitbit_data(path)
                if len(stream.heart_rate_bpm) > 0:
                    return self.add_stream(stream)
            except (json.JSONDecodeError, KeyError, ValueError, OSError) as exc:
                _LOGGER.debug("File %s not Fitbit format: %s", path.name, exc)

        elif "whoop" in name_lower or path.suffix == ".csv":
            stream = import_whoop_data(path)
            return self.add_stream(stream)

        elif "apple" in name_lower or "health" in name_lower or path.suffix in [".xml", ".zip"]:
            stream = import_apple_health_data(path)
            return self.add_stream(stream)

        raise ValueError(f"Could not detect platform for file: {path}")

    def cross_validate_all(self) -> list[CrossValidationResult]:
        """Cross-validate all pairs of streams.

        Returns:
            List of CrossValidationResult for each pair.
        """
        self._cross_validations.clear()

        for i in range(len(self._streams)):
            for j in range(i + 1, len(self._streams)):
                result = cross_validate_streams(
                    self._streams[i],
                    self._streams[j],
                )
                result = CrossValidationResult(
                    stream1_idx=i,
                    stream2_idx=j,
                    correlation_r=result.correlation_r,
                    mean_diff_ms=result.mean_diff_ms,
                    std_diff_ms=result.std_diff_ms,
                    agreement_pct=result.agreement_pct,
                    bland_altman_bias=result.bland_altman_bias,
                    bland_altman_loa=result.bland_altman_loa,
                    is_valid=result.is_valid,
                )
                self._cross_validations.append(result)

        return self._cross_validations

    def select_primary_stream(self) -> int:
        """Select the highest quality stream as primary.

        Returns:
            Index of the primary stream.
        """
        if not self._streams:
            return 0

        # Score each stream
        scores = []
        for stream in self._streams:
            if stream.quality:
                score = stream.quality.quality_score
            else:
                # Estimate score from data availability
                score = 50.0
                if len(stream.rr_intervals_ms) > 100:
                    score += 20.0
                if len(stream.hrv_rmssd) > 10:
                    score += 10.0
                if len(stream.heart_rate_bpm) > 100:
                    score += 10.0

            # Prefer ECG over PPG
            if stream.signal_source == SignalSource.ECG:
                score += 15.0

            scores.append(score)

        return int(np.argmax(scores))

    def fuse(self) -> FusedWearableData:
        """Fuse all streams into unified data.

        Returns:
            FusedWearableData with combined data.
        """
        if not self._streams:
            return FusedWearableData()

        # Cross-validate
        self.cross_validate_all()

        # Select primary stream
        primary_idx = self.select_primary_stream()
        primary = self._streams[primary_idx]

        # For now, use primary stream's data
        # Future: implement weighted averaging or Kalman filtering

        fused_rr = primary.rr_intervals_ms.copy() if len(primary.rr_intervals_ms) > 0 else np.array([])
        fused_ts = primary.timestamps.copy() if len(primary.timestamps) > 0 else np.array([])

        # Determine time range
        all_starts = [s.start_time for s in self._streams]
        all_ends = [s.end_time for s in self._streams]
        time_range = (min(all_starts), max(all_ends))

        # Overall quality
        if primary.quality:
            overall_quality = primary.quality
        else:
            overall_quality = assess_signal_quality(fused_rr)

        return FusedWearableData(
            streams=self._streams.copy(),
            primary_stream=primary_idx,
            fused_rr_ms=fused_rr,
            fused_timestamps=fused_ts,
            cross_validation={
                "results": self._cross_validations,
                "n_valid_pairs": sum(1 for cv in self._cross_validations if cv.is_valid),
            },
            overall_quality=overall_quality,
            time_range=time_range,
        )

    def get_quality_report(self) -> pd.DataFrame:
        """Generate quality report for all streams.

        Returns:
            DataFrame with quality metrics per stream.
        """
        rows = []
        for i, stream in enumerate(self._streams):
            row = {
                "stream_idx": i,
                "platform": stream.platform.value,
                "device_id": stream.device_id,
                "signal_source": stream.signal_source.value,
                "n_rr_intervals": len(stream.rr_intervals_ms),
                "n_hr_samples": len(stream.heart_rate_bpm),
                "n_hrv_samples": len(stream.hrv_rmssd),
                "duration_hours": (stream.end_time - stream.start_time).total_seconds() / 3600,
            }

            if stream.quality:
                row.update({
                    "quality_score": stream.quality.quality_score,
                    "quality_level": stream.quality.quality_level.value,
                    "coverage_pct": stream.quality.coverage_pct,
                    "artifact_pct": stream.quality.artifact_pct,
                    "notes": stream.quality.notes,
                })

            rows.append(row)

        return pd.DataFrame(rows)


"""Compumedics Somfit Pro sleep study data import module for HRV analysis.

This module provides functions to import polysomnography (PSG) and sleep study
data from Compumedics Somfit/Somfit Pro devices. The Somfit is a miniaturized
forehead-mounted sleep monitoring device that captures EEG, EOG, and physiological
signals for home sleep testing.

Supported file formats:
- .edf/.edf+: European Data Format (standard PSG export)
- .xml: Compumedics Profusion scoring annotations
- .csv: Exported summary data from Profusion Nexus360

Data extraction:
- Sleep staging (Wake, N1, N2, N3, REM)
- Heart rate and RR intervals (from ECG/PPG channel)
- SpO2 (pulse oximetry)
- Respiratory events (apneas, hypopneas)
- Sleep efficiency and architecture metrics
- EEG power spectral features (optional)

Scientific references:
- Compumedics Somfit: https://www.compumedics.com.au/en/products/somfit/
- EDF format: Kemp B, et al. (1992). A simple format for exchange of digitized
  polygraphic recordings. Electroenceph Clin Neurophysiol 82:391-393.
- AASM Manual for Sleep Scoring (2020)

Author: Dr. Diego Malpica, MD - Aerospace Medicine Specialist
National University of Colombia | Colombian Aerospace Force
"""

from __future__ import annotations

import csv
import logging
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    from collections.abc import Iterator

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)

# Sleep stage mapping (AASM standard)
_SLEEP_STAGES: Final[dict[str, int]] = {
    "Wake": 0,
    "W": 0,
    "N1": 1,
    "Stage 1": 1,
    "N2": 2,
    "Stage 2": 2,
    "N3": 3,
    "Stage 3": 3,
    "Stage 4": 3,  # Old R&K terminology
    "SWS": 3,
    "REM": 4,
    "R": 4,
    "Movement": 5,
    "Unknown": -1,
    "Unscored": -1,
}

# EDF signal labels for physiological channels
_EDF_HR_LABELS: Final[tuple[str, ...]] = (
    "HR",
    "Heart Rate",
    "HeartRate",
    "Pulse",
    "ECG HR",
    "PPG HR",
)

_EDF_SPO2_LABELS: Final[tuple[str, ...]] = (
    "SpO2",
    "SaO2",
    "Oxygen Saturation",
    "OxSat",
    "Pulse Ox",
)

_EDF_RESP_LABELS: Final[tuple[str, ...]] = (
    "Resp",
    "Respiration",
    "Airflow",
    "Nasal",
    "Thoracic",
    "Abdominal",
    "RIP",
)

_EDF_EEG_LABELS: Final[tuple[str, ...]] = (
    "EEG",
    "F3",
    "F4",
    "C3",
    "C4",
    "O1",
    "O2",
    "Fp1",
    "Fp2",
    "Fz",
    "Cz",
    "Pz",
)

# Epoch duration for sleep staging (standard: 30 seconds)
_EPOCH_DURATION_SEC: Final[int] = 30


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SomfitMetadata:
    """Metadata from Somfit/EDF recording.

    Attributes:
        patient_id: Patient/subject identifier.
        recording_id: Recording identifier.
        start_date: Recording start date.
        start_time: Recording start time.
        duration_seconds: Total recording duration.
        num_signals: Number of signals in recording.
        signal_labels: List of signal channel names.
        sample_rates: Dictionary of signal label to sample rate.
        device_type: Device type (e.g., "Somfit", "Somfit Pro").
        technician: Recording technician (if available).
        equipment: Recording equipment description.
    """

    patient_id: str = ""
    recording_id: str = ""
    start_date: datetime | None = None
    start_time: datetime | None = None
    duration_seconds: float = 0.0
    num_signals: int = 0
    signal_labels: tuple[str, ...] = ()
    sample_rates: dict[str, float] = field(default_factory=dict)
    device_type: str = ""
    technician: str = ""
    equipment: str = ""


@dataclass(slots=True)
class SleepStaging:
    """Sleep staging data.

    Attributes:
        epochs: DataFrame with epoch number, timestamp, stage.
        hypnogram: NumPy array of stage values per epoch.
        total_sleep_time: Total sleep time in minutes.
        sleep_efficiency: Sleep efficiency percentage.
        sleep_latency: Sleep onset latency in minutes.
        rem_latency: REM onset latency in minutes.
        waso: Wake after sleep onset in minutes.
        stage_durations: Dictionary of stage to duration in minutes.
        stage_percentages: Dictionary of stage to percentage of TST.
    """

    epochs: pd.DataFrame = field(default_factory=pd.DataFrame)
    hypnogram: np.ndarray = field(default_factory=lambda: np.array([]))
    total_sleep_time: float = 0.0
    sleep_efficiency: float = 0.0
    sleep_latency: float = 0.0
    rem_latency: float = 0.0
    waso: float = 0.0
    stage_durations: dict[str, float] = field(default_factory=dict)
    stage_percentages: dict[str, float] = field(default_factory=dict)


@dataclass(slots=True)
class RespiratoryEvents:
    """Respiratory event data.

    Attributes:
        events: DataFrame with event type, start, duration, desaturation.
        ahi: Apnea-Hypopnea Index (events per hour).
        odi: Oxygen Desaturation Index (desaturations per hour).
        apnea_count: Total apnea count.
        hypopnea_count: Total hypopnea count.
        mean_desat: Mean desaturation percentage.
        min_spo2: Minimum SpO2 during sleep.
    """

    events: pd.DataFrame = field(default_factory=pd.DataFrame)
    ahi: float = 0.0
    odi: float = 0.0
    apnea_count: int = 0
    hypopnea_count: int = 0
    mean_desat: float = 0.0
    min_spo2: float = 100.0


@dataclass(slots=True)
class SomfitData:
    """Container for Somfit sleep study data.

    Attributes:
        metadata: Recording metadata.
        staging: Sleep staging data.
        respiratory: Respiratory event data.
        heart_rate: DataFrame with timestamp and heart rate.
        spo2: DataFrame with timestamp and SpO2.
        rr_intervals: DataFrame with RR intervals for HRV analysis.
        eeg_power: DataFrame with EEG spectral power (optional).
        raw_signals: Dictionary of signal label to raw data array.
        source: Data source description.
    """

    metadata: SomfitMetadata = field(default_factory=SomfitMetadata)
    staging: SleepStaging = field(default_factory=SleepStaging)
    respiratory: RespiratoryEvents = field(default_factory=RespiratoryEvents)
    heart_rate: pd.DataFrame = field(default_factory=pd.DataFrame)
    spo2: pd.DataFrame = field(default_factory=pd.DataFrame)
    rr_intervals: pd.DataFrame = field(default_factory=pd.DataFrame)
    eeg_power: pd.DataFrame = field(default_factory=pd.DataFrame)
    raw_signals: dict[str, np.ndarray] = field(default_factory=dict)
    source: str = "unknown"


# ---------------------------------------------------------------------------
# EDF file parsing
# ---------------------------------------------------------------------------


def _parse_edf_header(f: Any) -> dict[str, Any]:
    """Parse EDF file header.

    Args:
        f: File handle positioned at start of EDF file.

    Returns:
        Dictionary with header information.
    """
    header: dict[str, Any] = {}

    # Fixed header (256 bytes)
    header["version"] = f.read(8).decode("ascii").strip()
    header["patient_id"] = f.read(80).decode("ascii").strip()
    header["recording_id"] = f.read(80).decode("ascii").strip()
    header["start_date"] = f.read(8).decode("ascii").strip()
    header["start_time"] = f.read(8).decode("ascii").strip()
    header["header_bytes"] = int(f.read(8).decode("ascii").strip())
    header["reserved"] = f.read(44).decode("ascii").strip()
    header["num_records"] = int(f.read(8).decode("ascii").strip())
    header["record_duration"] = float(f.read(8).decode("ascii").strip())
    header["num_signals"] = int(f.read(4).decode("ascii").strip())

    # Signal headers
    ns = header["num_signals"]
    header["labels"] = [f.read(16).decode("ascii").strip() for _ in range(ns)]
    header["transducers"] = [f.read(80).decode("ascii").strip() for _ in range(ns)]
    header["units"] = [f.read(8).decode("ascii").strip() for _ in range(ns)]
    header["physical_min"] = [float(f.read(8).decode("ascii").strip()) for _ in range(ns)]
    header["physical_max"] = [float(f.read(8).decode("ascii").strip()) for _ in range(ns)]
    header["digital_min"] = [int(f.read(8).decode("ascii").strip()) for _ in range(ns)]
    header["digital_max"] = [int(f.read(8).decode("ascii").strip()) for _ in range(ns)]
    header["prefiltering"] = [f.read(80).decode("ascii").strip() for _ in range(ns)]
    header["samples_per_record"] = [int(f.read(8).decode("ascii").strip()) for _ in range(ns)]
    header["reserved_signals"] = [f.read(32).decode("ascii").strip() for _ in range(ns)]

    return header


def _parse_edf_datetime(date_str: str, time_str: str) -> datetime | None:
    """Parse EDF date and time strings.

    Args:
        date_str: Date in DD.MM.YY format.
        time_str: Time in HH.MM.SS format.

    Returns:
        datetime object or None if parsing fails.
    """
    try:
        # Handle 2-digit year
        day, month, year = date_str.split(".")
        year_int = int(year)
        if year_int < 85:  # Y2K handling: 00-84 -> 2000-2084
            year_int += 2000
        else:
            year_int += 1900

        hour, minute, second = time_str.split(".")
        return datetime(
            year=year_int,
            month=int(month),
            day=int(day),
            hour=int(hour),
            minute=int(minute),
            second=int(second),
            tzinfo=timezone.utc,
        )
    except (ValueError, AttributeError) as exc:
        _LOGGER.warning("Failed to parse EDF datetime: %s %s - %s", date_str, time_str, exc)
        return None


def read_edf_file(
    file_path: Path,
    load_signals: bool = True,
    signal_filter: list[str] | None = None,
) -> SomfitData:
    """Read EDF/EDF+ file from Somfit or PSG system.

    Args:
        file_path: Path to .edf file.
        load_signals: Whether to load raw signal data.
        signal_filter: List of signal labels to load (None = all).

    Returns:
        SomfitData with parsed data.

    Raises:
        FileNotFoundError: If file does not exist.
        ValueError: If file is not a valid EDF file.
    """
    if not file_path.exists():
        msg = f"EDF file not found: {file_path}"
        raise FileNotFoundError(msg)

    result = SomfitData(source=f"edf:{file_path.name}")

    try:
        with open(file_path, "rb") as f:
            header = _parse_edf_header(f)

            # Build metadata
            start_datetime = _parse_edf_datetime(
                header["start_date"], header["start_time"]
            )
            duration = header["num_records"] * header["record_duration"]

            # Calculate sample rates
            sample_rates = {
                label: samples / header["record_duration"]
                for label, samples in zip(
                    header["labels"],
                    header["samples_per_record"],
                    strict=True,
                )
            }

            result.metadata = SomfitMetadata(
                patient_id=header["patient_id"],
                recording_id=header["recording_id"],
                start_date=start_datetime,
                start_time=start_datetime,
                duration_seconds=duration,
                num_signals=header["num_signals"],
                signal_labels=tuple(header["labels"]),
                sample_rates=sample_rates,
                device_type="Somfit" if "somfit" in header["recording_id"].lower() else "PSG",
                equipment=header.get("reserved", ""),
            )

            # Load signal data if requested
            if load_signals:
                # Position at start of data
                f.seek(header["header_bytes"])

                # Initialize signal arrays
                signals: dict[str, list[float]] = {
                    label: [] for label in header["labels"]
                }

                # Read data records
                for _ in range(header["num_records"]):
                    for i, label in enumerate(header["labels"]):
                        if signal_filter is not None and label not in signal_filter:
                            # Skip this signal
                            f.seek(header["samples_per_record"][i] * 2, 1)
                            continue

                        # Read samples (16-bit signed integers)
                        num_samples = header["samples_per_record"][i]
                        raw_data = f.read(num_samples * 2)
                        if len(raw_data) < num_samples * 2:
                            break

                        # Convert to physical units
                        digital_values = np.frombuffer(raw_data, dtype="<i2")
                        scale = (
                            (header["physical_max"][i] - header["physical_min"][i])
                            / (header["digital_max"][i] - header["digital_min"][i])
                        )
                        offset = header["physical_min"][i] - header["digital_min"][i] * scale
                        physical_values = digital_values * scale + offset
                        signals[label].extend(physical_values.tolist())

                # Convert to numpy arrays
                result.raw_signals = {
                    label: np.array(data) for label, data in signals.items() if data
                }

                # Extract physiological data
                _extract_physiological_data(result, header, start_datetime)

    except Exception as exc:
        msg = f"Failed to read EDF file: {file_path}"
        raise ValueError(msg) from exc

    _LOGGER.info(
        "Read EDF file: %d signals, %.1f hours",
        result.metadata.num_signals,
        result.metadata.duration_seconds / 3600,
    )

    return result


def read_edf_with_pyedflib(file_path: Path) -> SomfitData:
    """Read EDF file using pyEDFlib library.

    This provides more robust parsing and handles edge cases better.

    Args:
        file_path: Path to .edf file.

    Returns:
        SomfitData with parsed data.

    Raises:
        ImportError: If pyedflib is not installed.
        FileNotFoundError: If file does not exist.
    """
    try:
        import pyedflib
    except ImportError as exc:
        msg = "pyedflib library not installed. Run: pip install pyedflib"
        raise ImportError(msg) from exc

    if not file_path.exists():
        msg = f"EDF file not found: {file_path}"
        raise FileNotFoundError(msg)

    result = SomfitData(source=f"pyedflib:{file_path.name}")

    edf_reader = pyedflib.EdfReader(str(file_path))
    try:
        # Get header information
        num_signals = edf_reader.signals_in_file
        signal_labels = edf_reader.getSignalLabels()
        sample_rates = {
            label: edf_reader.getSampleFrequency(i)
            for i, label in enumerate(signal_labels)
        }

        # Get recording info
        start_datetime = edf_reader.getStartdatetime()
        if start_datetime.tzinfo is None:
            start_datetime = start_datetime.replace(tzinfo=timezone.utc)

        duration = edf_reader.getFileDuration()

        result.metadata = SomfitMetadata(
            patient_id=edf_reader.getPatientCode(),
            recording_id=edf_reader.getRecordingAdditional(),
            start_date=start_datetime,
            start_time=start_datetime,
            duration_seconds=duration,
            num_signals=num_signals,
            signal_labels=tuple(signal_labels),
            sample_rates=sample_rates,
            technician=edf_reader.getTechnician(),
            equipment=edf_reader.getEquipment(),
        )

        # Read signals
        for i, label in enumerate(signal_labels):
            signal_data = edf_reader.readSignal(i)
            result.raw_signals[label] = signal_data

        # Extract physiological data
        _extract_physiological_data_pyedflib(result, edf_reader)

    finally:
        edf_reader.close()

    _LOGGER.info(
        "Read EDF file with pyedflib: %d signals, %.1f hours",
        result.metadata.num_signals,
        result.metadata.duration_seconds / 3600,
    )

    return result


def _extract_physiological_data(
    data: SomfitData,
    header: dict[str, Any],
    start_time: datetime | None,
) -> None:
    """Extract heart rate, SpO2, and other physiological data from raw signals.

    Args:
        data: SomfitData to populate.
        header: EDF header information.
        start_time: Recording start timestamp.
    """
    if start_time is None:
        start_time = datetime.now(tz=timezone.utc)

    # Find and extract heart rate
    for label in _EDF_HR_LABELS:
        if label in data.raw_signals:
            hr_data = data.raw_signals[label]
            sample_rate = data.metadata.sample_rates.get(label, 1)
            timestamps = [
                start_time + timedelta(seconds=i / sample_rate)
                for i in range(len(hr_data))
            ]
            data.heart_rate = pd.DataFrame({
                "timestamp": timestamps,
                "heart_rate": hr_data,
            })
            # Filter physiologically plausible values
            data.heart_rate = data.heart_rate[
                (data.heart_rate["heart_rate"] >= 30)
                & (data.heart_rate["heart_rate"] <= 220)
            ]
            break

    # Find and extract SpO2
    for label in _EDF_SPO2_LABELS:
        if label in data.raw_signals:
            spo2_data = data.raw_signals[label]
            sample_rate = data.metadata.sample_rates.get(label, 1)
            timestamps = [
                start_time + timedelta(seconds=i / sample_rate)
                for i in range(len(spo2_data))
            ]
            data.spo2 = pd.DataFrame({
                "timestamp": timestamps,
                "spo2": spo2_data,
            })
            # Filter physiologically plausible values
            data.spo2 = data.spo2[
                (data.spo2["spo2"] >= 50) & (data.spo2["spo2"] <= 100)
            ]
            break


def _extract_physiological_data_pyedflib(
    data: SomfitData,
    edf_reader: Any,
) -> None:
    """Extract physiological data using pyedflib reader.

    Args:
        data: SomfitData to populate.
        edf_reader: pyedflib EdfReader instance.
    """
    start_time = data.metadata.start_time
    if start_time is None:
        start_time = datetime.now(tz=timezone.utc)

    signal_labels = data.metadata.signal_labels

    # Find and extract heart rate
    for label in _EDF_HR_LABELS:
        if label in signal_labels:
            idx = signal_labels.index(label)
            hr_data = data.raw_signals.get(label)
            if hr_data is not None:
                sample_rate = data.metadata.sample_rates.get(label, 1)
                timestamps = [
                    start_time + timedelta(seconds=i / sample_rate)
                    for i in range(len(hr_data))
                ]
                data.heart_rate = pd.DataFrame({
                    "timestamp": timestamps,
                    "heart_rate": hr_data,
                })
                data.heart_rate = data.heart_rate[
                    (data.heart_rate["heart_rate"] >= 30)
                    & (data.heart_rate["heart_rate"] <= 220)
                ]
            break

    # Find and extract SpO2
    for label in _EDF_SPO2_LABELS:
        if label in signal_labels:
            spo2_data = data.raw_signals.get(label)
            if spo2_data is not None:
                sample_rate = data.metadata.sample_rates.get(label, 1)
                timestamps = [
                    start_time + timedelta(seconds=i / sample_rate)
                    for i in range(len(spo2_data))
                ]
                data.spo2 = pd.DataFrame({
                    "timestamp": timestamps,
                    "spo2": spo2_data,
                })
                data.spo2 = data.spo2[
                    (data.spo2["spo2"] >= 50) & (data.spo2["spo2"] <= 100)
                ]
            break


# ---------------------------------------------------------------------------
# XML annotation parsing (Compumedics Profusion)
# ---------------------------------------------------------------------------


def read_profusion_xml(file_path: Path) -> SleepStaging:
    """Read Compumedics Profusion XML scoring annotations.

    Args:
        file_path: Path to XML annotation file.

    Returns:
        SleepStaging with parsed epochs and metrics.

    Raises:
        FileNotFoundError: If file does not exist.
        ValueError: If file is not valid Profusion XML.
    """
    if not file_path.exists():
        msg = f"XML file not found: {file_path}"
        raise FileNotFoundError(msg)

    staging = SleepStaging()
    epochs: list[dict[str, Any]] = []

    try:
        tree = ET.parse(file_path)
        root = tree.getroot()

        # Find sleep stages
        for event in root.iter():
            if "SleepStage" in event.tag or "Stage" in event.tag:
                stage_text = event.text or event.get("Stage", "")
                start = event.get("Start") or event.get("Onset")
                duration = event.get("Duration")

                if stage_text and start is not None:
                    stage_code = _SLEEP_STAGES.get(stage_text.strip(), -1)
                    epochs.append({
                        "epoch": len(epochs) + 1,
                        "start_seconds": float(start),
                        "duration": float(duration) if duration else _EPOCH_DURATION_SEC,
                        "stage": stage_code,
                        "stage_name": stage_text.strip(),
                    })

            # Also check for scored events
            if "ScoredEvent" in event.tag:
                event_type = event.find("EventType")
                if event_type is not None and "Stage" in (event_type.text or ""):
                    stage_text = event.find("EventConcept")
                    start = event.find("Start")
                    duration = event.find("Duration")

                    if stage_text is not None and start is not None:
                        stage_code = _SLEEP_STAGES.get(stage_text.text.strip(), -1)
                        epochs.append({
                            "epoch": len(epochs) + 1,
                            "start_seconds": float(start.text),
                            "duration": float(duration.text) if duration is not None else _EPOCH_DURATION_SEC,
                            "stage": stage_code,
                            "stage_name": stage_text.text.strip(),
                        })

    except ET.ParseError as exc:
        msg = f"Invalid XML file: {file_path}"
        raise ValueError(msg) from exc

    if epochs:
        staging.epochs = pd.DataFrame(epochs)
        staging.hypnogram = np.array([e["stage"] for e in epochs])

        # Compute sleep metrics
        _compute_sleep_metrics(staging)

    _LOGGER.info("Read Profusion XML: %d epochs", len(epochs))

    return staging


def _compute_sleep_metrics(staging: SleepStaging) -> None:
    """Compute sleep architecture metrics from staging data.

    Args:
        staging: SleepStaging to update with computed metrics.
    """
    if staging.epochs.empty:
        return

    df = staging.epochs
    epoch_duration = df["duration"].iloc[0] if "duration" in df.columns else _EPOCH_DURATION_SEC

    # Total recording time
    trt_minutes = len(df) * epoch_duration / 60

    # Total sleep time (all non-wake epochs)
    sleep_epochs = df[df["stage"] > 0]
    tst_minutes = len(sleep_epochs) * epoch_duration / 60
    staging.total_sleep_time = tst_minutes

    # Sleep efficiency
    if trt_minutes > 0:
        staging.sleep_efficiency = (tst_minutes / trt_minutes) * 100

    # Sleep onset latency (time to first sleep epoch)
    first_sleep_idx = df[df["stage"] > 0].index.min()
    if pd.notna(first_sleep_idx):
        staging.sleep_latency = first_sleep_idx * epoch_duration / 60

    # REM latency (time from sleep onset to first REM)
    first_rem_idx = df[df["stage"] == 4].index.min()
    if pd.notna(first_rem_idx) and pd.notna(first_sleep_idx):
        staging.rem_latency = (first_rem_idx - first_sleep_idx) * epoch_duration / 60

    # WASO (wake epochs after sleep onset)
    if pd.notna(first_sleep_idx):
        post_onset = df.loc[first_sleep_idx:]
        wake_epochs = post_onset[post_onset["stage"] == 0]
        staging.waso = len(wake_epochs) * epoch_duration / 60

    # Stage durations and percentages
    stage_names = {0: "Wake", 1: "N1", 2: "N2", 3: "N3", 4: "REM"}
    for stage_code, stage_name in stage_names.items():
        count = len(df[df["stage"] == stage_code])
        duration_min = count * epoch_duration / 60
        staging.stage_durations[stage_name] = duration_min
        if tst_minutes > 0 and stage_code > 0:
            staging.stage_percentages[stage_name] = (duration_min / tst_minutes) * 100


# ---------------------------------------------------------------------------
# CSV export parsing
# ---------------------------------------------------------------------------


def read_somfit_csv(file_path: Path) -> SomfitData:
    """Read Somfit CSV export from Profusion Nexus360.

    Args:
        file_path: Path to CSV export file.

    Returns:
        SomfitData with parsed summary data.

    Raises:
        FileNotFoundError: If file does not exist.
    """
    if not file_path.exists():
        msg = f"CSV file not found: {file_path}"
        raise FileNotFoundError(msg)

    result = SomfitData(source=f"csv:{file_path.name}")

    # Read CSV and detect format
    df = pd.read_csv(file_path)

    # Look for common column patterns
    columns_lower = {c.lower(): c for c in df.columns}

    # Extract heart rate data
    hr_cols = [c for c in columns_lower if "heart" in c or "hr" in c or "pulse" in c]
    if hr_cols:
        hr_col = columns_lower[hr_cols[0]]
        time_col = None
        for tc in ["timestamp", "time", "datetime", "epoch"]:
            if tc in columns_lower:
                time_col = columns_lower[tc]
                break

        if time_col:
            result.heart_rate = pd.DataFrame({
                "timestamp": pd.to_datetime(df[time_col]),
                "heart_rate": df[hr_col],
            })

    # Extract SpO2 data
    spo2_cols = [c for c in columns_lower if "spo2" in c or "sao2" in c or "oxygen" in c]
    if spo2_cols:
        spo2_col = columns_lower[spo2_cols[0]]
        time_col = None
        for tc in ["timestamp", "time", "datetime", "epoch"]:
            if tc in columns_lower:
                time_col = columns_lower[tc]
                break

        if time_col:
            result.spo2 = pd.DataFrame({
                "timestamp": pd.to_datetime(df[time_col]),
                "spo2": df[spo2_col],
            })

    # Extract sleep staging if present
    stage_cols = [c for c in columns_lower if "stage" in c or "sleep" in c]
    if stage_cols:
        stage_col = columns_lower[stage_cols[0]]
        epochs = []
        for i, stage in enumerate(df[stage_col]):
            stage_code = _SLEEP_STAGES.get(str(stage), -1)
            epochs.append({
                "epoch": i + 1,
                "stage": stage_code,
                "stage_name": str(stage),
            })
        if epochs:
            result.staging.epochs = pd.DataFrame(epochs)
            result.staging.hypnogram = np.array([e["stage"] for e in epochs])
            _compute_sleep_metrics(result.staging)

    _LOGGER.info("Read Somfit CSV: %d rows", len(df))

    return result


# ---------------------------------------------------------------------------
# RR interval extraction
# ---------------------------------------------------------------------------


def extract_rr_from_hr(
    hr_df: pd.DataFrame,
    method: str = "interpolate",
) -> pd.DataFrame:
    """Extract RR intervals from heart rate data.

    Since Somfit provides heart rate rather than beat-to-beat intervals,
    this function estimates RR intervals for HRV analysis.

    Note: This is an approximation. True beat-to-beat HRV requires ECG
    with R-peak detection. Use with caution for research purposes.

    Args:
        hr_df: DataFrame with timestamp and heart_rate columns.
        method: Extraction method ("interpolate" or "instantaneous").

    Returns:
        DataFrame with estimated RR intervals.
    """
    if hr_df.empty or "heart_rate" not in hr_df.columns:
        return pd.DataFrame()

    df = hr_df.copy()
    df = df.dropna(subset=["heart_rate"])
    df = df[df["heart_rate"] > 0]

    if method == "instantaneous":
        # Simple conversion: RR = 60000 / HR (ms)
        df["rr_interval_ms"] = 60000.0 / df["heart_rate"]
    else:
        # Interpolate to higher resolution then convert
        # Resample to 1-second intervals
        if "timestamp" in df.columns:
            df = df.set_index("timestamp")
        df_resampled = df.resample("1s").mean().interpolate()
        df_resampled["rr_interval_ms"] = 60000.0 / df_resampled["heart_rate"]
        df = df_resampled.reset_index()

    # Filter physiologically plausible values
    df = df[(df["rr_interval_ms"] >= 300) & (df["rr_interval_ms"] <= 2000)]

    return df[["timestamp", "rr_interval_ms"]] if "timestamp" in df.columns else df[["rr_interval_ms"]]


def extract_rr_from_ecg(
    ecg_signal: np.ndarray,
    sample_rate: float,
    start_time: datetime | None = None,
) -> pd.DataFrame:
    """Extract RR intervals from raw ECG signal using R-peak detection.

    Args:
        ecg_signal: Raw ECG signal array.
        sample_rate: ECG sampling rate in Hz.
        start_time: Signal start timestamp.

    Returns:
        DataFrame with detected RR intervals.
    """
    if len(ecg_signal) < sample_rate * 10:  # Need at least 10 seconds
        _LOGGER.warning("ECG signal too short for R-peak detection")
        return pd.DataFrame()

    try:
        from scipy import signal as scipy_signal
    except ImportError:
        _LOGGER.warning("scipy not available for ECG processing")
        return pd.DataFrame()

    # Band-pass filter (5-15 Hz for QRS complex)
    nyquist = sample_rate / 2
    low = 5 / nyquist
    high = min(15 / nyquist, 0.99)
    b, a = scipy_signal.butter(2, [low, high], btype="band")
    filtered = scipy_signal.filtfilt(b, a, ecg_signal)

    # Square the signal
    squared = filtered ** 2

    # Moving average
    window = int(sample_rate * 0.15)  # 150 ms window
    if window > 0:
        smoothed = np.convolve(squared, np.ones(window) / window, mode="same")
    else:
        smoothed = squared

    # Find peaks (R-peaks)
    threshold = np.mean(smoothed) + 0.5 * np.std(smoothed)
    min_distance = int(sample_rate * 0.3)  # Minimum 300 ms between beats

    peaks, _ = scipy_signal.find_peaks(
        smoothed,
        height=threshold,
        distance=min_distance,
    )

    if len(peaks) < 2:
        _LOGGER.warning("Too few R-peaks detected")
        return pd.DataFrame()

    # Calculate RR intervals
    rr_samples = np.diff(peaks)
    rr_ms = (rr_samples / sample_rate) * 1000

    # Create timestamps
    if start_time is None:
        start_time = datetime.now(tz=timezone.utc)

    timestamps = [
        start_time + timedelta(seconds=peaks[i + 1] / sample_rate)
        for i in range(len(rr_ms))
    ]

    df = pd.DataFrame({
        "timestamp": timestamps,
        "rr_interval_ms": rr_ms,
    })

    # Filter physiologically plausible values
    df = df[(df["rr_interval_ms"] >= 300) & (df["rr_interval_ms"] <= 2000)]

    _LOGGER.info("Extracted %d RR intervals from ECG", len(df))

    return df


# ---------------------------------------------------------------------------
# Integration with HRV analysis
# ---------------------------------------------------------------------------


def extract_sleep_hrv_windows(
    somfit_data: SomfitData,
    window_minutes: int = 5,
) -> list[tuple[datetime, datetime, str, np.ndarray]]:
    """Extract HRV analysis windows aligned with sleep stages.

    Args:
        somfit_data: SomfitData with staging and RR intervals.
        window_minutes: Window duration in minutes.

    Returns:
        List of (start_time, end_time, stage_name, rr_intervals) tuples.
    """
    if somfit_data.rr_intervals.empty or somfit_data.staging.epochs.empty:
        return []

    windows: list[tuple[datetime, datetime, str, np.ndarray]] = []
    rr_df = somfit_data.rr_intervals.copy()

    if "timestamp" not in rr_df.columns:
        return []

    rr_df["timestamp"] = pd.to_datetime(rr_df["timestamp"], utc=True)
    rr_df = rr_df.set_index("timestamp").sort_index()

    # Get staging epochs
    staging_df = somfit_data.staging.epochs
    start_time = somfit_data.metadata.start_time or datetime.now(tz=timezone.utc)

    for _, epoch in staging_df.iterrows():
        epoch_start = start_time + timedelta(seconds=epoch.get("start_seconds", 0))
        epoch_end = epoch_start + timedelta(seconds=epoch.get("duration", 30))
        stage_name = epoch.get("stage_name", "Unknown")

        # Get RR intervals in this epoch
        mask = (rr_df.index >= epoch_start) & (rr_df.index < epoch_end)
        epoch_rr = rr_df.loc[mask, "rr_interval_ms"].values

        if len(epoch_rr) >= 10:  # Minimum beats for analysis
            windows.append((epoch_start, epoch_end, stage_name, epoch_rr))

    return windows


def get_stage_specific_hrv(
    somfit_data: SomfitData,
) -> dict[str, dict[str, float]]:
    """Compute HRV metrics for each sleep stage.

    Args:
        somfit_data: SomfitData with staging and RR intervals.

    Returns:
        Dictionary of stage name to HRV metrics dictionary.
    """
    windows = extract_sleep_hrv_windows(somfit_data)

    if not windows:
        return {}

    stage_rr: dict[str, list[np.ndarray]] = {}
    for _, _, stage_name, rr_intervals in windows:
        if stage_name not in stage_rr:
            stage_rr[stage_name] = []
        stage_rr[stage_name].append(rr_intervals)

    results: dict[str, dict[str, float]] = {}
    for stage_name, rr_arrays in stage_rr.items():
        # Concatenate all RR intervals for this stage
        all_rr = np.concatenate(rr_arrays)

        if len(all_rr) < 30:
            continue

        # Compute basic HRV metrics
        results[stage_name] = {
            "mean_rr": float(np.mean(all_rr)),
            "sdnn": float(np.std(all_rr, ddof=1)),
            "rmssd": float(np.sqrt(np.mean(np.diff(all_rr) ** 2))),
            "mean_hr": float(60000 / np.mean(all_rr)),
            "n_beats": len(all_rr),
        }

        # pNN50
        diffs = np.abs(np.diff(all_rr))
        results[stage_name]["pnn50"] = float(100 * np.sum(diffs > 50) / len(diffs))

    return results


# ---------------------------------------------------------------------------
# High-level import function
# ---------------------------------------------------------------------------


def import_somfit_data(
    file_path: Path,
    annotation_path: Path | None = None,
    use_pyedflib: bool = True,
    extract_rr: bool = True,
) -> SomfitData:
    """Import Somfit/PSG data from any supported format.

    Automatically detects file format based on extension.

    Args:
        file_path: Path to data file (.edf, .csv).
        annotation_path: Optional path to XML annotation file.
        use_pyedflib: Use pyedflib for EDF parsing (more robust).
        extract_rr: Extract RR intervals from heart rate data.

    Returns:
        SomfitData with all available data.

    Raises:
        FileNotFoundError: If file does not exist.
        ValueError: If file format is not supported.
    """
    if not file_path.exists():
        msg = f"File not found: {file_path}"
        raise FileNotFoundError(msg)

    suffix = file_path.suffix.lower()

    if suffix in (".edf", ".edf+"):
        if use_pyedflib:
            try:
                data = read_edf_with_pyedflib(file_path)
            except ImportError:
                _LOGGER.warning("pyedflib not available, using built-in parser")
                data = read_edf_file(file_path)
        else:
            data = read_edf_file(file_path)

    elif suffix == ".csv":
        data = read_somfit_csv(file_path)

    else:
        msg = f"Unsupported file format: {suffix}"
        raise ValueError(msg)

    # Load annotations if provided
    if annotation_path is not None and annotation_path.exists():
        if annotation_path.suffix.lower() == ".xml":
            data.staging = read_profusion_xml(annotation_path)

    # Extract RR intervals from heart rate
    if extract_rr and not data.heart_rate.empty:
        data.rr_intervals = extract_rr_from_hr(data.heart_rate)

    # Try to extract RR from ECG if available
    for label in ["ECG", "EKG", "ECG I", "ECG II"]:
        if label in data.raw_signals and data.rr_intervals.empty:
            ecg_signal = data.raw_signals[label]
            sample_rate = data.metadata.sample_rates.get(label, 256)
            data.rr_intervals = extract_rr_from_ecg(
                ecg_signal,
                sample_rate,
                data.metadata.start_time,
            )
            if not data.rr_intervals.empty:
                break

    return data


def check_somfit_data_quality(data: SomfitData) -> dict[str, Any]:
    """Check quality of imported Somfit data.

    Args:
        data: SomfitData container.

    Returns:
        Dictionary with quality metrics and warnings.
    """
    warnings: list[str] = []
    metrics: dict[str, Any] = {
        "recording_duration_hours": data.metadata.duration_seconds / 3600,
        "num_signals": data.metadata.num_signals,
        "hr_samples": len(data.heart_rate),
        "spo2_samples": len(data.spo2),
        "rr_intervals": len(data.rr_intervals),
        "staging_epochs": len(data.staging.epochs),
        "device_type": data.metadata.device_type,
    }

    # Check recording duration
    if data.metadata.duration_seconds < 4 * 3600:
        warnings.append("Recording duration less than 4 hours")

    # Check sleep staging
    if data.staging.epochs.empty:
        warnings.append("No sleep staging data found")
    elif data.staging.total_sleep_time < 120:
        warnings.append("Total sleep time less than 2 hours")

    # Check SpO2 data
    if not data.spo2.empty and "spo2" in data.spo2.columns:
        min_spo2 = data.spo2["spo2"].min()
        if min_spo2 < 88:
            warnings.append(f"Low SpO2 detected: minimum {min_spo2:.1f}%")

    # Check heart rate data
    if data.heart_rate.empty:
        warnings.append("No heart rate data found")

    # Check RR intervals
    if data.rr_intervals.empty:
        warnings.append("No RR intervals extracted - HRV analysis may be limited")
    elif len(data.rr_intervals) < 300:
        warnings.append("Limited RR intervals - HRV analysis may be unreliable")

    # Note about derived RR intervals
    if not data.rr_intervals.empty and data.heart_rate.empty is False:
        warnings.append(
            "Note: RR intervals derived from heart rate data; "
            "true beat-to-beat HRV requires ECG with R-peak detection"
        )

    metrics["warnings"] = warnings
    metrics["quality_ok"] = len([w for w in warnings if "Note:" not in w]) <= 1

    return metrics


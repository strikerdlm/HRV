"""Actigraph GT3X/GT3X+ accelerometer data import module for HRV analysis.

This module provides functions to import accelerometer and activity data from
ActiGraph GT3X/GT3X+ devices. Data can be used for sleep/wake classification,
activity pattern analysis, and correlation with HRV metrics.

Supported file formats:
- .gt3x: ActiGraph binary format (via pygt3x or direct parsing)
- .agd: ActiLife processed database (SQLite)
- .csv: ActiLife exported CSV files (counts or raw acceleration)

Data extraction:
- Raw triaxial acceleration (X, Y, Z axes in gravitational units)
- Activity counts (epoch-based summaries)
- Sleep/wake classifications (if available)
- Light exposure data (if sensor equipped)
- Device metadata and calibration info

Scientific references:
- Neishabouri A, et al. (2022). Quantification of acceleration as activity counts
  in ActiGraph wearables. Sci Rep 12:3958.
- ActiGraph GT3X File Format: https://github.com/actigraph/GT3X-File-Format
- pygt3x: https://github.com/actigraph/pygt3x

Author: Dr. Diego Malpica, MD - Aerospace Medicine Specialist
National University of Colombia | Colombian Aerospace Force
"""

from __future__ import annotations

import io
import json
import logging
import sqlite3
import struct
import zipfile
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

# GT3X file structure constants
_GT3X_INFO_FILE: Final[str] = "info.txt"
_GT3X_LOG_FILE: Final[str] = "log.bin"
_GT3X_LUX_FILE: Final[str] = "lux.bin"

# Activity record types in log.bin
_RECORD_ACTIVITY: Final[int] = 0x00
_RECORD_BATTERY: Final[int] = 0x02
_RECORD_EVENT: Final[int] = 0x03
_RECORD_HEART_RATE_BPM: Final[int] = 0x04
_RECORD_LUX: Final[int] = 0x05
_RECORD_METADATA: Final[int] = 0x06
_RECORD_TAG: Final[int] = 0x07
_RECORD_EPOCH: Final[int] = 0x0C
_RECORD_HEART_RATE_ANT: Final[int] = 0x0D
_RECORD_EPOCH2: Final[int] = 0x0E
_RECORD_CAPSENSE: Final[int] = 0x0F
_RECORD_HEART_RATE_BLE: Final[int] = 0x10
_RECORD_ACTIVITY2: Final[int] = 0x1A
_RECORD_SENSOR_DATA: Final[int] = 0x15

# Physical activity intensity thresholds (counts per minute)
_CUT_POINTS_FREEDSON: Final[dict[str, tuple[int, int]]] = {
    "sedentary": (0, 99),
    "light": (100, 1951),
    "moderate": (1952, 5724),
    "vigorous": (5725, 99999),
}

# Sleep/wake classification threshold (Cole-Kripke algorithm)
_SLEEP_THRESHOLD: Final[int] = 40  # Activity counts


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class GT3XMetadata:
    """Metadata from ActiGraph GT3X device.

    Attributes:
        serial_number: Device serial number.
        device_type: Device model (e.g., "GT3X+", "wGT3X+", "GT9X").
        firmware_version: Device firmware version.
        sample_rate: Sampling rate in Hz.
        start_date: Recording start timestamp (UTC).
        stop_date: Recording stop timestamp (UTC).
        time_zone: Device timezone offset.
        acceleration_scale: Scale factor for raw acceleration.
        acceleration_min: Minimum acceleration value.
        acceleration_max: Maximum acceleration value.
        subject_name: Subject identifier (if recorded).
        download_date: Data download timestamp.
        battery_voltage: Battery voltage at download.
    """

    serial_number: str = ""
    device_type: str = ""
    firmware_version: str = ""
    sample_rate: int = 30
    start_date: datetime | None = None
    stop_date: datetime | None = None
    time_zone: str = ""
    acceleration_scale: float = 256.0
    acceleration_min: int = -6
    acceleration_max: int = 6
    subject_name: str = ""
    download_date: datetime | None = None
    battery_voltage: float = 0.0


@dataclass(slots=True)
class ActigraphData:
    """Container for ActiGraph accelerometer data.

    Attributes:
        metadata: Device and recording metadata.
        raw_acceleration: DataFrame with timestamp, X, Y, Z acceleration (g).
        activity_counts: DataFrame with epoch-based activity counts.
        heart_rate: DataFrame with heart rate data (if HR monitor used).
        lux: DataFrame with light exposure data (if equipped).
        sleep_wake: DataFrame with sleep/wake classifications.
        epochs: DataFrame with processed epoch summaries.
        source: Data source description.
    """

    metadata: GT3XMetadata = field(default_factory=GT3XMetadata)
    raw_acceleration: pd.DataFrame = field(default_factory=pd.DataFrame)
    activity_counts: pd.DataFrame = field(default_factory=pd.DataFrame)
    heart_rate: pd.DataFrame = field(default_factory=pd.DataFrame)
    lux: pd.DataFrame = field(default_factory=pd.DataFrame)
    sleep_wake: pd.DataFrame = field(default_factory=pd.DataFrame)
    epochs: pd.DataFrame = field(default_factory=pd.DataFrame)
    source: str = "unknown"


# ---------------------------------------------------------------------------
# GT3X file parsing
# ---------------------------------------------------------------------------


def _parse_gt3x_info(info_content: str) -> GT3XMetadata:
    """Parse info.txt from GT3X file.

    Args:
        info_content: Contents of info.txt file.

    Returns:
        GT3XMetadata with parsed values.
    """
    info_dict: dict[str, str] = {}
    for line in info_content.strip().split("\n"):
        if ": " in line:
            key, value = line.split(": ", 1)
            info_dict[key.strip()] = value.strip()

    # Parse timestamps
    start_date = None
    stop_date = None
    download_date = None

    if "Start Date" in info_dict:
        try:
            # Format: "2019-09-17 14:00:00"
            start_date = datetime.strptime(
                info_dict["Start Date"], "%Y-%m-%d %H:%M:%S"
            ).replace(tzinfo=timezone.utc)
        except ValueError:
            _LOGGER.warning("Failed to parse start date: %s", info_dict["Start Date"])

    if "Stop Date" in info_dict:
        try:
            stop_date = datetime.strptime(
                info_dict["Stop Date"], "%Y-%m-%d %H:%M:%S"
            ).replace(tzinfo=timezone.utc)
        except ValueError:
            _LOGGER.warning("Failed to parse stop date: %s", info_dict["Stop Date"])

    if "Download Date" in info_dict:
        try:
            download_date = datetime.strptime(
                info_dict["Download Date"], "%Y-%m-%d %H:%M:%S"
            ).replace(tzinfo=timezone.utc)
        except ValueError:
            pass

    return GT3XMetadata(
        serial_number=info_dict.get("Serial Number", ""),
        device_type=info_dict.get("Device Type", ""),
        firmware_version=info_dict.get("Firmware", ""),
        sample_rate=int(info_dict.get("Sample Rate", "30")),
        start_date=start_date,
        stop_date=stop_date,
        time_zone=info_dict.get("TimeZone", ""),
        acceleration_scale=float(info_dict.get("Acceleration Scale", "256")),
        acceleration_min=int(info_dict.get("Acceleration Min", "-6")),
        acceleration_max=int(info_dict.get("Acceleration Max", "6")),
        subject_name=info_dict.get("Subject Name", ""),
        download_date=download_date,
        battery_voltage=float(info_dict.get("Battery Voltage", "0")),
    )


def _unpack_activity_samples(
    data: bytes,
    sample_rate: int,
    scale: float,
    start_time: datetime,
) -> Iterator[tuple[datetime, float, float, float]]:
    """Unpack raw activity samples from log.bin.

    ActiGraph uses a compressed format where samples are packed as 12-bit values.

    Args:
        data: Raw binary data from activity record.
        sample_rate: Device sampling rate in Hz.
        scale: Acceleration scale factor.
        start_time: Timestamp of first sample.

    Yields:
        Tuples of (timestamp, x, y, z) acceleration in g.
    """
    sample_interval = timedelta(seconds=1.0 / sample_rate)
    current_time = start_time

    # Each sample is 36 bits (12 bits per axis), packed into 9 bytes for 2 samples
    offset = 0
    while offset + 9 <= len(data):
        # Unpack two samples from 9 bytes
        chunk = data[offset : offset + 9]
        if len(chunk) < 9:
            break

        # First sample (bytes 0-4, bits 0-35)
        # X: bits 0-11, Y: bits 12-23, Z: bits 24-35
        b0, b1, b2, b3, b4 = chunk[0], chunk[1], chunk[2], chunk[3], chunk[4]

        x1_raw = b0 | ((b1 & 0x0F) << 8)
        y1_raw = ((b1 & 0xF0) >> 4) | (b2 << 4)
        z1_raw = b3 | ((b4 & 0x0F) << 8)

        # Convert from 12-bit signed to float
        if x1_raw >= 2048:
            x1_raw -= 4096
        if y1_raw >= 2048:
            y1_raw -= 4096
        if z1_raw >= 2048:
            z1_raw -= 4096

        x1 = x1_raw / scale
        y1 = y1_raw / scale
        z1 = z1_raw / scale

        yield (current_time, x1, y1, z1)
        current_time += sample_interval

        # Second sample (bytes 4-8, bits 36-71)
        b4, b5, b6, b7, b8 = chunk[4], chunk[5], chunk[6], chunk[7], chunk[8]

        x2_raw = ((b4 & 0xF0) >> 4) | (b5 << 4)
        y2_raw = b6 | ((b7 & 0x0F) << 8)
        z2_raw = ((b7 & 0xF0) >> 4) | (b8 << 4)

        if x2_raw >= 2048:
            x2_raw -= 4096
        if y2_raw >= 2048:
            y2_raw -= 4096
        if z2_raw >= 2048:
            z2_raw -= 4096

        x2 = x2_raw / scale
        y2 = y2_raw / scale
        z2 = z2_raw / scale

        yield (current_time, x2, y2, z2)
        current_time += sample_interval

        offset += 9


def _parse_log_bin(
    log_data: bytes,
    metadata: GT3XMetadata,
) -> tuple[list[tuple[datetime, float, float, float]], list[tuple[datetime, int]], list[tuple[datetime, float]]]:
    """Parse log.bin binary file from GT3X.

    Args:
        log_data: Raw binary data from log.bin.
        metadata: Device metadata for calibration.

    Returns:
        Tuple of (acceleration_samples, heart_rate_samples, lux_samples).
    """
    acceleration_samples: list[tuple[datetime, float, float, float]] = []
    heart_rate_samples: list[tuple[datetime, int]] = []
    lux_samples: list[tuple[datetime, float]] = []

    offset = 0
    current_time = metadata.start_date or datetime.now(tz=timezone.utc)

    while offset < len(log_data):
        if offset + 8 > len(log_data):
            break

        # Record header: separator (1), type (1), timestamp (4), size (2)
        separator = log_data[offset]
        if separator != 0x1E:
            offset += 1
            continue

        record_type = log_data[offset + 1]
        timestamp_raw = struct.unpack_from("<I", log_data, offset + 2)[0]
        record_size = struct.unpack_from("<H", log_data, offset + 6)[0]

        # Convert timestamp (ticks since device start)
        if timestamp_raw > 0 and metadata.start_date is not None:
            current_time = metadata.start_date + timedelta(
                seconds=timestamp_raw / metadata.sample_rate
            )

        offset += 8  # Skip header

        if offset + record_size > len(log_data):
            break

        record_data = log_data[offset : offset + record_size]

        if record_type == _RECORD_ACTIVITY:
            # Raw acceleration data
            for sample in _unpack_activity_samples(
                record_data,
                metadata.sample_rate,
                metadata.acceleration_scale,
                current_time,
            ):
                acceleration_samples.append(sample)

        elif record_type == _RECORD_HEART_RATE_BPM:
            # Heart rate in BPM
            if len(record_data) >= 1:
                hr = record_data[0]
                if 30 <= hr <= 220:  # Valid HR range
                    heart_rate_samples.append((current_time, hr))

        elif record_type == _RECORD_HEART_RATE_BLE:
            # BLE heart rate
            if len(record_data) >= 2:
                hr = struct.unpack_from("<H", record_data, 0)[0]
                if 30 <= hr <= 220:
                    heart_rate_samples.append((current_time, hr))

        elif record_type == _RECORD_LUX:
            # Light exposure
            if len(record_data) >= 2:
                lux_val = struct.unpack_from("<H", record_data, 0)[0]
                lux_samples.append((current_time, float(lux_val)))

        offset += record_size

        # Skip checksum byte
        if offset < len(log_data):
            offset += 1

    return acceleration_samples, heart_rate_samples, lux_samples


def read_gt3x_file(file_path: Path) -> ActigraphData:
    """Read ActiGraph GT3X file.

    A GT3X file is a ZIP archive containing:
    - info.txt: Device and recording metadata
    - log.bin: Binary activity data
    - lux.bin: Light sensor data (optional)

    Args:
        file_path: Path to .gt3x file.

    Returns:
        ActigraphData with parsed data.

    Raises:
        FileNotFoundError: If file does not exist.
        ValueError: If file is not a valid GT3X file.
    """
    if not file_path.exists():
        msg = f"GT3X file not found: {file_path}"
        raise FileNotFoundError(msg)

    result = ActigraphData(source=f"gt3x:{file_path.name}")

    try:
        with zipfile.ZipFile(file_path, "r") as zf:
            # Parse metadata from info.txt
            if _GT3X_INFO_FILE in zf.namelist():
                with zf.open(_GT3X_INFO_FILE) as f:
                    info_content = f.read().decode("utf-8")
                    result.metadata = _parse_gt3x_info(info_content)
            else:
                _LOGGER.warning("No info.txt found in GT3X file")

            # Parse activity data from log.bin
            if _GT3X_LOG_FILE in zf.namelist():
                with zf.open(_GT3X_LOG_FILE) as f:
                    log_data = f.read()

                acc_samples, hr_samples, lux_samples = _parse_log_bin(
                    log_data, result.metadata
                )

                # Build acceleration DataFrame
                if acc_samples:
                    result.raw_acceleration = pd.DataFrame(
                        acc_samples,
                        columns=["timestamp", "x", "y", "z"],
                    )
                    result.raw_acceleration["timestamp"] = pd.to_datetime(
                        result.raw_acceleration["timestamp"], utc=True
                    )

                # Build heart rate DataFrame
                if hr_samples:
                    result.heart_rate = pd.DataFrame(
                        hr_samples,
                        columns=["timestamp", "heart_rate"],
                    )
                    result.heart_rate["timestamp"] = pd.to_datetime(
                        result.heart_rate["timestamp"], utc=True
                    )

                # Build lux DataFrame
                if lux_samples:
                    result.lux = pd.DataFrame(
                        lux_samples,
                        columns=["timestamp", "lux"],
                    )
                    result.lux["timestamp"] = pd.to_datetime(
                        result.lux["timestamp"], utc=True
                    )

    except zipfile.BadZipFile as exc:
        msg = f"Invalid GT3X file (not a valid ZIP archive): {file_path}"
        raise ValueError(msg) from exc

    _LOGGER.info(
        "Read GT3X file: %d acceleration samples, %d HR samples",
        len(result.raw_acceleration),
        len(result.heart_rate),
    )

    return result


def read_gt3x_with_pygt3x(file_path: Path) -> ActigraphData:
    """Read GT3X file using official pygt3x library.

    This provides more robust parsing with proper calibration.

    Args:
        file_path: Path to .gt3x file.

    Returns:
        ActigraphData with parsed data.

    Raises:
        ImportError: If pygt3x is not installed.
        FileNotFoundError: If file does not exist.
    """
    try:
        from pygt3x.reader import FileReader
    except ImportError as exc:
        msg = "pygt3x library not installed. Run: pip install pygt3x"
        raise ImportError(msg) from exc

    if not file_path.exists():
        msg = f"GT3X file not found: {file_path}"
        raise FileNotFoundError(msg)

    result = ActigraphData(source=f"pygt3x:{file_path.name}")

    with FileReader(str(file_path)) as reader:
        # Get metadata
        info = reader.info
        result.metadata = GT3XMetadata(
            serial_number=info.get("Serial Number", ""),
            device_type=info.get("Device Type", ""),
            firmware_version=info.get("Firmware", ""),
            sample_rate=int(info.get("Sample Rate", 30)),
            subject_name=info.get("Subject Name", ""),
        )

        # Get calibrated acceleration data
        df = reader.to_pandas()
        if not df.empty:
            # Rename columns to standard format
            column_map = {
                "X": "x",
                "Y": "y",
                "Z": "z",
                "Timestamp": "timestamp",
            }
            df = df.rename(columns=column_map)

            if "timestamp" not in df.columns and df.index.name:
                df = df.reset_index()
                if "Timestamp" in df.columns:
                    df = df.rename(columns={"Timestamp": "timestamp"})

            result.raw_acceleration = df

    _LOGGER.info(
        "Read GT3X file with pygt3x: %d samples",
        len(result.raw_acceleration),
    )

    return result


# ---------------------------------------------------------------------------
# AGD (ActiLife database) parsing
# ---------------------------------------------------------------------------


def read_agd_file(file_path: Path) -> ActigraphData:
    """Read ActiLife AGD database file.

    AGD files are SQLite databases containing processed epoch data.

    Args:
        file_path: Path to .agd file.

    Returns:
        ActigraphData with epoch data.

    Raises:
        FileNotFoundError: If file does not exist.
        ValueError: If file is not a valid AGD database.
    """
    if not file_path.exists():
        msg = f"AGD file not found: {file_path}"
        raise FileNotFoundError(msg)

    result = ActigraphData(source=f"agd:{file_path.name}")

    try:
        conn = sqlite3.connect(str(file_path))

        # Read settings/metadata
        try:
            settings_df = pd.read_sql_query(
                "SELECT * FROM settings", conn
            )
            settings_dict = dict(
                zip(
                    settings_df["settingName"].tolist(),
                    settings_df["settingValue"].tolist(),
                    strict=False,
                )
            )
            result.metadata = GT3XMetadata(
                serial_number=settings_dict.get("deviceSerial", ""),
                device_type=settings_dict.get("devicename", ""),
                sample_rate=int(settings_dict.get("samplerate", 30)),
                subject_name=settings_dict.get("subjectname", ""),
            )
        except Exception as exc:
            _LOGGER.warning("Failed to read AGD settings: %s", exc)

        # Read epoch data
        try:
            epochs_df = pd.read_sql_query(
                """
                SELECT dataTimestamp, axis1, axis2, axis3,
                       steps, lux, inclineOff, inclineStanding,
                       inclineSitting, inclineLying, hr
                FROM data
                ORDER BY dataTimestamp
                """,
                conn,
            )
            if not epochs_df.empty:
                epochs_df["timestamp"] = pd.to_datetime(
                    epochs_df["dataTimestamp"], unit="s", utc=True
                )
                epochs_df = epochs_df.rename(
                    columns={
                        "axis1": "counts_x",
                        "axis2": "counts_y",
                        "axis3": "counts_z",
                        "hr": "heart_rate",
                    }
                )
                result.epochs = epochs_df
                result.activity_counts = epochs_df[
                    ["timestamp", "counts_x", "counts_y", "counts_z"]
                ].copy()
        except Exception as exc:
            _LOGGER.warning("Failed to read AGD epoch data: %s", exc)

        conn.close()

    except sqlite3.Error as exc:
        msg = f"Invalid AGD file (not a valid SQLite database): {file_path}"
        raise ValueError(msg) from exc

    _LOGGER.info("Read AGD file: %d epochs", len(result.epochs))

    return result


# ---------------------------------------------------------------------------
# CSV file parsing
# ---------------------------------------------------------------------------


def read_actigraph_csv(
    file_path: Path,
    file_type: str = "auto",
) -> ActigraphData:
    """Read ActiLife exported CSV file.

    Supports multiple CSV formats:
    - "raw": Raw acceleration data (X, Y, Z in g)
    - "counts": Activity counts per epoch
    - "auto": Auto-detect format

    Args:
        file_path: Path to CSV file.
        file_type: File type ("raw", "counts", or "auto").

    Returns:
        ActigraphData with parsed data.

    Raises:
        FileNotFoundError: If file does not exist.
        ValueError: If file format is not recognized.
    """
    if not file_path.exists():
        msg = f"CSV file not found: {file_path}"
        raise FileNotFoundError(msg)

    result = ActigraphData(source=f"csv:{file_path.name}")

    # Read file to detect format
    with open(file_path, encoding="utf-8") as f:
        # Skip header lines starting with "---"
        header_lines: list[str] = []
        data_start = 0
        for i, line in enumerate(f):
            if line.startswith("---") or line.startswith("Serial"):
                header_lines.append(line)
                data_start = i + 1
            elif line.strip() and not line.startswith(","):
                # Found data header
                break

    # Parse metadata from header
    for line in header_lines:
        if "Serial Number:" in line:
            result.metadata = GT3XMetadata(
                serial_number=line.split(":")[-1].strip()
            )

    # Read data
    df = pd.read_csv(file_path, skiprows=data_start)

    # Auto-detect format
    if file_type == "auto":
        columns_lower = [c.lower() for c in df.columns]
        if any("accelerometer" in c or "axis1" in c.lower() for c in df.columns):
            # Raw acceleration or counts
            if any("axis1" in c.lower() for c in df.columns):
                file_type = "counts"
            else:
                file_type = "raw"
        else:
            file_type = "raw"

    if file_type == "raw":
        # Raw acceleration data
        # Typical columns: Timestamp, Accelerometer X, Accelerometer Y, Accelerometer Z
        col_map = {}
        for col in df.columns:
            col_lower = col.lower()
            if "timestamp" in col_lower or "time" in col_lower:
                col_map[col] = "timestamp"
            elif "x" in col_lower and ("accel" in col_lower or "axis" in col_lower):
                col_map[col] = "x"
            elif "y" in col_lower and ("accel" in col_lower or "axis" in col_lower):
                col_map[col] = "y"
            elif "z" in col_lower and ("accel" in col_lower or "axis" in col_lower):
                col_map[col] = "z"

        df = df.rename(columns=col_map)
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        result.raw_acceleration = df[
            [c for c in ["timestamp", "x", "y", "z"] if c in df.columns]
        ]

    elif file_type == "counts":
        # Activity counts data
        col_map = {}
        for col in df.columns:
            col_lower = col.lower()
            if "timestamp" in col_lower or "time" in col_lower or "date" in col_lower:
                col_map[col] = "timestamp"
            elif "axis1" in col_lower:
                col_map[col] = "counts_x"
            elif "axis2" in col_lower:
                col_map[col] = "counts_y"
            elif "axis3" in col_lower:
                col_map[col] = "counts_z"
            elif "steps" in col_lower:
                col_map[col] = "steps"
            elif "hr" in col_lower or "heart" in col_lower:
                col_map[col] = "heart_rate"
            elif "lux" in col_lower:
                col_map[col] = "lux"

        df = df.rename(columns=col_map)
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        result.activity_counts = df
        result.epochs = df

    _LOGGER.info(
        "Read ActiGraph CSV: %d rows, type=%s",
        len(df),
        file_type,
    )

    return result


# ---------------------------------------------------------------------------
# Activity metrics computation
# ---------------------------------------------------------------------------


def compute_activity_counts(
    raw_data: pd.DataFrame,
    epoch_seconds: int = 60,
    sample_rate: int = 30,
) -> pd.DataFrame:
    """Compute activity counts from raw acceleration data.

    Implements the ActiGraph counts algorithm as described in
    Neishabouri et al. (2022).

    Args:
        raw_data: DataFrame with timestamp, x, y, z columns.
        epoch_seconds: Epoch length in seconds.
        sample_rate: Original sampling rate in Hz.

    Returns:
        DataFrame with epoch-based activity counts.
    """
    if raw_data.empty or "x" not in raw_data.columns:
        return pd.DataFrame()

    df = raw_data.copy()

    # Ensure timestamp is datetime
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        df = df.set_index("timestamp")

    # Compute vector magnitude
    df["vm"] = np.sqrt(df["x"] ** 2 + df["y"] ** 2 + df["z"] ** 2)

    # Band-pass filter (0.25-2.5 Hz for ActiGraph)
    # Simplified: use rolling mean subtraction as high-pass
    window = int(sample_rate * 4)  # 4-second window
    if window > 0 and len(df) > window:
        df["x_filt"] = df["x"] - df["x"].rolling(window, center=True).mean()
        df["y_filt"] = df["y"] - df["y"].rolling(window, center=True).mean()
        df["z_filt"] = df["z"] - df["z"].rolling(window, center=True).mean()
    else:
        df["x_filt"] = df["x"]
        df["y_filt"] = df["y"]
        df["z_filt"] = df["z"]

    # Resample to epochs
    epoch_str = f"{epoch_seconds}s"
    counts = df.resample(epoch_str).agg(
        {
            "x_filt": lambda s: np.sum(np.abs(s)) * (1000 / sample_rate),
            "y_filt": lambda s: np.sum(np.abs(s)) * (1000 / sample_rate),
            "z_filt": lambda s: np.sum(np.abs(s)) * (1000 / sample_rate),
            "vm": lambda s: np.sum(np.abs(s - 1)) * (1000 / sample_rate),
        }
    )

    counts = counts.rename(
        columns={
            "x_filt": "counts_x",
            "y_filt": "counts_y",
            "z_filt": "counts_z",
            "vm": "counts_vm",
        }
    )

    counts = counts.reset_index()
    counts = counts.rename(columns={"index": "timestamp"})

    return counts


def classify_activity_intensity(
    counts_df: pd.DataFrame,
    count_column: str = "counts_vm",
    cut_points: dict[str, tuple[int, int]] | None = None,
) -> pd.DataFrame:
    """Classify activity intensity based on count cut-points.

    Args:
        counts_df: DataFrame with activity counts.
        count_column: Column to use for classification.
        cut_points: Dictionary of intensity levels to (min, max) counts.
            Default uses Freedson adult cut-points.

    Returns:
        DataFrame with added 'intensity' column.
    """
    if counts_df.empty or count_column not in counts_df.columns:
        return counts_df

    if cut_points is None:
        cut_points = _CUT_POINTS_FREEDSON

    df = counts_df.copy()
    df["intensity"] = "unknown"

    for intensity, (min_val, max_val) in cut_points.items():
        mask = (df[count_column] >= min_val) & (df[count_column] <= max_val)
        df.loc[mask, "intensity"] = intensity

    return df


def classify_sleep_wake(
    counts_df: pd.DataFrame,
    count_column: str = "counts_vm",
    threshold: int = _SLEEP_THRESHOLD,
    min_sleep_epochs: int = 3,
) -> pd.DataFrame:
    """Classify sleep/wake based on activity counts.

    Uses a simplified Cole-Kripke algorithm.

    Args:
        counts_df: DataFrame with activity counts.
        count_column: Column to use for classification.
        threshold: Activity count threshold for sleep.
        min_sleep_epochs: Minimum consecutive epochs to classify as sleep.

    Returns:
        DataFrame with added 'sleep_wake' column (0=sleep, 1=wake).
    """
    if counts_df.empty or count_column not in counts_df.columns:
        return counts_df

    df = counts_df.copy()

    # Initial classification based on threshold
    df["sleep_wake"] = (df[count_column] > threshold).astype(int)

    # Apply minimum duration rule
    # Find sleep periods and filter short ones
    sleep_runs = []
    current_run_start = None

    for i, row in df.iterrows():
        if row["sleep_wake"] == 0:  # Sleep
            if current_run_start is None:
                current_run_start = i
        else:
            if current_run_start is not None:
                run_length = i - current_run_start
                if run_length >= min_sleep_epochs:
                    sleep_runs.append((current_run_start, i))
                current_run_start = None

    # Apply filtered sleep periods
    df["sleep_wake"] = 1  # Default to wake
    for start, end in sleep_runs:
        df.loc[start:end, "sleep_wake"] = 0

    return df


# ---------------------------------------------------------------------------
# Integration with HRV analysis
# ---------------------------------------------------------------------------


def extract_sleep_periods(
    actigraph_data: ActigraphData,
) -> list[tuple[datetime, datetime]]:
    """Extract sleep period timestamps from actigraphy data.

    Args:
        actigraph_data: ActigraphData with sleep/wake classifications.

    Returns:
        List of (start, end) tuples for each sleep period.
    """
    if actigraph_data.sleep_wake.empty:
        # Try to classify from activity counts
        if not actigraph_data.activity_counts.empty:
            df = classify_sleep_wake(actigraph_data.activity_counts)
        else:
            return []
    else:
        df = actigraph_data.sleep_wake

    if "sleep_wake" not in df.columns or "timestamp" not in df.columns:
        return []

    sleep_periods: list[tuple[datetime, datetime]] = []
    in_sleep = False
    sleep_start: datetime | None = None

    for _, row in df.iterrows():
        if row["sleep_wake"] == 0 and not in_sleep:
            # Sleep onset
            in_sleep = True
            sleep_start = row["timestamp"]
        elif row["sleep_wake"] == 1 and in_sleep:
            # Wake onset
            in_sleep = False
            if sleep_start is not None:
                sleep_periods.append((sleep_start, row["timestamp"]))

    # Handle case where recording ends during sleep
    if in_sleep and sleep_start is not None:
        sleep_periods.append((sleep_start, df["timestamp"].iloc[-1]))

    return sleep_periods


def synchronize_with_hrv(
    actigraph_data: ActigraphData,
    hrv_timestamps: pd.DatetimeIndex,
    resample_freq: str = "1min",
) -> pd.DataFrame:
    """Synchronize actigraphy data with HRV measurement timestamps.

    Args:
        actigraph_data: ActigraphData with activity data.
        hrv_timestamps: DatetimeIndex of HRV measurements.
        resample_freq: Resampling frequency for alignment.

    Returns:
        DataFrame with synchronized actigraphy metrics aligned to HRV timestamps.
    """
    if actigraph_data.activity_counts.empty:
        return pd.DataFrame(index=hrv_timestamps)

    df = actigraph_data.activity_counts.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")

    # Resample to common frequency
    resampled = df.resample(resample_freq).mean()

    # Align with HRV timestamps
    aligned = resampled.reindex(hrv_timestamps, method="nearest", tolerance="5min")

    return aligned


# ---------------------------------------------------------------------------
# High-level import function
# ---------------------------------------------------------------------------


def import_actigraph_data(
    file_path: Path,
    use_pygt3x: bool = False,
    compute_counts: bool = True,
    classify_intensity: bool = True,
    classify_sleep: bool = True,
    epoch_seconds: int = 60,
) -> ActigraphData:
    """Import ActiGraph data from any supported format.

    Automatically detects file format based on extension.

    Args:
        file_path: Path to ActiGraph data file.
        use_pygt3x: Use pygt3x library for GT3X files (more accurate).
        compute_counts: Compute activity counts from raw data.
        classify_intensity: Classify activity intensity.
        classify_sleep: Classify sleep/wake periods.
        epoch_seconds: Epoch length for count computation.

    Returns:
        ActigraphData with all available data and classifications.

    Raises:
        FileNotFoundError: If file does not exist.
        ValueError: If file format is not supported.
    """
    if not file_path.exists():
        msg = f"File not found: {file_path}"
        raise FileNotFoundError(msg)

    suffix = file_path.suffix.lower()

    if suffix == ".gt3x":
        if use_pygt3x:
            try:
                data = read_gt3x_with_pygt3x(file_path)
            except ImportError:
                _LOGGER.warning("pygt3x not available, using built-in parser")
                data = read_gt3x_file(file_path)
        else:
            data = read_gt3x_file(file_path)

    elif suffix == ".agd":
        data = read_agd_file(file_path)

    elif suffix == ".csv":
        data = read_actigraph_csv(file_path)

    else:
        msg = f"Unsupported file format: {suffix}"
        raise ValueError(msg)

    # Compute activity counts if raw data available
    if compute_counts and not data.raw_acceleration.empty and data.activity_counts.empty:
        data.activity_counts = compute_activity_counts(
            data.raw_acceleration,
            epoch_seconds=epoch_seconds,
            sample_rate=data.metadata.sample_rate,
        )

    # Classify intensity
    if classify_intensity and not data.activity_counts.empty:
        data.activity_counts = classify_activity_intensity(data.activity_counts)

    # Classify sleep/wake
    if classify_sleep and not data.activity_counts.empty:
        data.sleep_wake = classify_sleep_wake(data.activity_counts)

    return data


def check_actigraph_data_quality(data: ActigraphData) -> dict[str, Any]:
    """Check quality of imported ActiGraph data.

    Args:
        data: ActigraphData container.

    Returns:
        Dictionary with quality metrics and warnings.
    """
    warnings: list[str] = []
    metrics: dict[str, Any] = {
        "raw_samples": len(data.raw_acceleration),
        "epoch_count": len(data.epochs) if not data.epochs.empty else len(data.activity_counts),
        "hr_readings": len(data.heart_rate),
        "lux_readings": len(data.lux),
        "device_type": data.metadata.device_type,
        "sample_rate": data.metadata.sample_rate,
    }

    # Check for data gaps
    if not data.raw_acceleration.empty and "timestamp" in data.raw_acceleration.columns:
        timestamps = pd.to_datetime(data.raw_acceleration["timestamp"])
        expected_interval = timedelta(seconds=1.0 / data.metadata.sample_rate)
        gaps = timestamps.diff()
        large_gaps = gaps[gaps > expected_interval * 10]
        if len(large_gaps) > 0:
            warnings.append(f"{len(large_gaps)} data gaps detected in raw acceleration")

    # Check acceleration range
    if not data.raw_acceleration.empty:
        for axis in ["x", "y", "z"]:
            if axis in data.raw_acceleration.columns:
                vals = data.raw_acceleration[axis]
                if vals.abs().max() > 8:
                    warnings.append(f"Extreme {axis.upper()}-axis values detected (>8g)")

    # Check epoch coverage
    if not data.activity_counts.empty and "timestamp" in data.activity_counts.columns:
        duration = (
            data.activity_counts["timestamp"].max()
            - data.activity_counts["timestamp"].min()
        )
        expected_epochs = duration.total_seconds() / 60  # 1-minute epochs
        actual_epochs = len(data.activity_counts)
        coverage = actual_epochs / expected_epochs if expected_epochs > 0 else 0
        metrics["epoch_coverage"] = coverage
        if coverage < 0.9:
            warnings.append(f"Low epoch coverage: {coverage:.1%}")

    metrics["warnings"] = warnings
    metrics["quality_ok"] = len(warnings) == 0

    return metrics


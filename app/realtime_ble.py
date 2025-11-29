"""Real-Time Bluetooth Low Energy (BLE) Heart Rate Monitor Integration.

This module provides real-time connection to BLE heart rate monitors
for live HRV streaming, biofeedback, and continuous monitoring.

Author: Dr. Diego Malpica, MD
        Aerospace Medicine Specialist
        National University of Colombia

Supported Devices:
    - Polar H10/H9/OH1 (RR intervals via BLE)
    - Garmin HRM-Pro/HRM-Dual
    - Wahoo TICKR/TICKR X
    - Generic BLE Heart Rate Service devices

References:
    - Bluetooth SIG Heart Rate Service Specification
    - Polar Measurement Data Specification
    - Gilgen-Ammann, R., et al. (2019). RR interval signal quality
      of a heart rate monitor and an ECG Holter.

Note: BLE functionality requires the `bleak` library and appropriate
system Bluetooth permissions. Some features may be limited in
web-based (Streamlit) deployments.
"""

from __future__ import annotations

import asyncio
import logging
import struct
from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Final

import numpy as np
from numpy.typing import NDArray

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)

# BLE UUIDs
HEART_RATE_SERVICE_UUID: Final[str] = "0000180d-0000-1000-8000-00805f9b34fb"
HEART_RATE_MEASUREMENT_UUID: Final[str] = "00002a37-0000-1000-8000-00805f9b34fb"
BATTERY_SERVICE_UUID: Final[str] = "0000180f-0000-1000-8000-00805f9b34fb"
BATTERY_LEVEL_UUID: Final[str] = "00002a19-0000-1000-8000-00805f9b34fb"

# Polar-specific UUIDs
POLAR_PMD_SERVICE_UUID: Final[str] = "fb005c80-02e7-f387-1cad-8acd2d8df0c8"
POLAR_PMD_CONTROL_UUID: Final[str] = "fb005c81-02e7-f387-1cad-8acd2d8df0c8"
POLAR_PMD_DATA_UUID: Final[str] = "fb005c82-02e7-f387-1cad-8acd2d8df0c8"

# Buffer sizes
RR_BUFFER_SIZE: Final[int] = 1000  # Store last 1000 RR intervals
HR_BUFFER_SIZE: Final[int] = 500  # Store last 500 HR values

# Validation thresholds
MIN_RR_MS: Final[float] = 300.0  # Minimum valid RR interval
MAX_RR_MS: Final[float] = 2000.0  # Maximum valid RR interval
MIN_HR_BPM: Final[float] = 30.0
MAX_HR_BPM: Final[float] = 220.0


class ConnectionState(Enum):
    """BLE connection state."""
    
    DISCONNECTED = "disconnected"
    SCANNING = "scanning"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    STREAMING = "streaming"
    ERROR = "error"


class DeviceType(Enum):
    """Heart rate monitor device type."""
    
    POLAR_H10 = "polar_h10"
    POLAR_H9 = "polar_h9"
    POLAR_OH1 = "polar_oh1"
    GARMIN_HRM = "garmin_hrm"
    WAHOO_TICKR = "wahoo_tickr"
    GENERIC_BLE = "generic_ble"
    SIMULATED = "simulated"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class BLEDevice:
    """Discovered BLE device information.
    
    Attributes:
        address: Device MAC address or UUID.
        name: Device name.
        rssi: Signal strength (dBm).
        device_type: Detected device type.
        services: List of advertised service UUIDs.
        is_connectable: Whether device is connectable.
    """
    
    address: str
    name: str
    rssi: int = -100
    device_type: DeviceType = DeviceType.GENERIC_BLE
    services: list[str] = field(default_factory=list)
    is_connectable: bool = True


@dataclass(slots=True)
class HeartRateMeasurement:
    """Single heart rate measurement from BLE.
    
    Attributes:
        timestamp: Measurement timestamp.
        heart_rate_bpm: Heart rate in BPM.
        rr_intervals_ms: RR intervals in milliseconds (if available).
        sensor_contact: Whether sensor contact is detected.
        energy_expended: Energy expended in kJ (if available).
        is_valid: Whether measurement passes validation.
    """
    
    timestamp: datetime
    heart_rate_bpm: float
    rr_intervals_ms: list[float] = field(default_factory=list)
    sensor_contact: bool = True
    energy_expended: float | None = None
    is_valid: bool = True


@dataclass(slots=True)
class StreamingSession:
    """Real-time streaming session data.
    
    Attributes:
        session_id: Unique session identifier.
        start_time: Session start time.
        device: Connected device info.
        rr_buffer: Circular buffer of RR intervals.
        hr_buffer: Circular buffer of heart rates.
        total_beats: Total beats received.
        invalid_beats: Count of invalid beats.
        connection_state: Current connection state.
        last_update: Last data update time.
    """
    
    session_id: str
    start_time: datetime
    device: BLEDevice | None = None
    rr_buffer: deque[float] = field(default_factory=lambda: deque(maxlen=RR_BUFFER_SIZE))
    hr_buffer: deque[float] = field(default_factory=lambda: deque(maxlen=HR_BUFFER_SIZE))
    total_beats: int = 0
    invalid_beats: int = 0
    connection_state: ConnectionState = ConnectionState.DISCONNECTED
    last_update: datetime | None = None


@dataclass(slots=True)
class RealTimeHRVMetrics:
    """Real-time HRV metrics computed from streaming data.
    
    Attributes:
        timestamp: Computation timestamp.
        window_size_beats: Number of beats in analysis window.
        mean_rr_ms: Mean RR interval.
        sdnn_ms: SDNN.
        rmssd_ms: RMSSD.
        pnn50: pNN50 percentage.
        mean_hr_bpm: Mean heart rate.
        current_hr_bpm: Most recent heart rate.
        coherence_score: Coherence score (0-100).
        respiratory_rate: Estimated respiratory rate.
        stress_index: Stress index.
    """
    
    timestamp: datetime
    window_size_beats: int = 0
    mean_rr_ms: float = 0.0
    sdnn_ms: float = 0.0
    rmssd_ms: float = 0.0
    pnn50: float = 0.0
    mean_hr_bpm: float = 0.0
    current_hr_bpm: float = 0.0
    coherence_score: float = 0.0
    respiratory_rate: float = 0.0
    stress_index: float = 50.0


# ---------------------------------------------------------------------------
# BLE Heart Rate Parser
# ---------------------------------------------------------------------------


def parse_heart_rate_measurement(data: bytes) -> HeartRateMeasurement:
    """Parse BLE Heart Rate Measurement characteristic data.
    
    Follows Bluetooth SIG Heart Rate Service specification.
    
    Args:
        data: Raw bytes from HR Measurement characteristic.
        
    Returns:
        HeartRateMeasurement with parsed data.
    """
    timestamp = datetime.now(timezone.utc)
    
    if len(data) < 2:
        return HeartRateMeasurement(
            timestamp=timestamp,
            heart_rate_bpm=0,
            is_valid=False,
        )
    
    flags = data[0]
    
    # Bit 0: Heart rate value format (0 = UINT8, 1 = UINT16)
    hr_format_16bit = bool(flags & 0x01)
    
    # Bit 1-2: Sensor contact status
    sensor_contact_supported = bool(flags & 0x04)
    sensor_contact_detected = bool(flags & 0x02) if sensor_contact_supported else True
    
    # Bit 3: Energy expended present
    energy_present = bool(flags & 0x08)
    
    # Bit 4: RR intervals present
    rr_present = bool(flags & 0x10)
    
    # Parse heart rate
    offset = 1
    if hr_format_16bit:
        if len(data) < 3:
            return HeartRateMeasurement(timestamp=timestamp, heart_rate_bpm=0, is_valid=False)
        heart_rate = struct.unpack_from("<H", data, offset)[0]
        offset += 2
    else:
        heart_rate = data[offset]
        offset += 1
    
    # Parse energy expended (if present)
    energy = None
    if energy_present:
        if len(data) >= offset + 2:
            energy = struct.unpack_from("<H", data, offset)[0]
            offset += 2
    
    # Parse RR intervals (if present)
    rr_intervals: list[float] = []
    if rr_present:
        while offset + 1 < len(data):
            # RR intervals are in 1/1024 second units
            rr_raw = struct.unpack_from("<H", data, offset)[0]
            rr_ms = rr_raw / 1024.0 * 1000.0  # Convert to milliseconds
            
            # Validate RR interval
            if MIN_RR_MS <= rr_ms <= MAX_RR_MS:
                rr_intervals.append(rr_ms)
            
            offset += 2
    
    # Validate heart rate
    is_valid = MIN_HR_BPM <= heart_rate <= MAX_HR_BPM
    
    return HeartRateMeasurement(
        timestamp=timestamp,
        heart_rate_bpm=float(heart_rate),
        rr_intervals_ms=rr_intervals,
        sensor_contact=sensor_contact_detected,
        energy_expended=float(energy) if energy is not None else None,
        is_valid=is_valid,
    )


# ---------------------------------------------------------------------------
# Real-Time HRV Computation
# ---------------------------------------------------------------------------


def compute_realtime_hrv(
    rr_intervals: list[float] | deque[float],
    window_beats: int = 60,
) -> RealTimeHRVMetrics:
    """Compute real-time HRV metrics from RR intervals.
    
    Args:
        rr_intervals: List or deque of RR intervals in milliseconds.
        window_beats: Number of beats to use for computation.
        
    Returns:
        RealTimeHRVMetrics with computed values.
    """
    timestamp = datetime.now(timezone.utc)
    
    # Get recent intervals
    rr_list = list(rr_intervals)
    if len(rr_list) < 10:
        return RealTimeHRVMetrics(timestamp=timestamp)
    
    # Use most recent window_beats
    rr = np.array(rr_list[-window_beats:], dtype=np.float64)
    
    # Time-domain metrics
    mean_rr = float(np.mean(rr))
    sdnn = float(np.std(rr, ddof=1))
    
    diff_rr = np.diff(rr)
    rmssd = float(np.sqrt(np.mean(diff_rr ** 2)))
    pnn50 = float(np.sum(np.abs(diff_rr) > 50) / len(diff_rr) * 100) if len(diff_rr) > 0 else 0
    
    mean_hr = 60000.0 / mean_rr if mean_rr > 0 else 0
    current_hr = 60000.0 / rr[-1] if rr[-1] > 0 else 0
    
    # Coherence score (simplified)
    coherence = _calculate_coherence(rr)
    
    # Respiratory rate estimation
    resp_rate = _estimate_respiratory_rate(rr)
    
    # Stress index (Baevsky)
    stress_index = _calculate_stress_index(rr)
    
    return RealTimeHRVMetrics(
        timestamp=timestamp,
        window_size_beats=len(rr),
        mean_rr_ms=mean_rr,
        sdnn_ms=sdnn,
        rmssd_ms=rmssd,
        pnn50=pnn50,
        mean_hr_bpm=mean_hr,
        current_hr_bpm=current_hr,
        coherence_score=coherence,
        respiratory_rate=resp_rate,
        stress_index=stress_index,
    )


def _calculate_coherence(rr: NDArray) -> float:
    """Calculate coherence score for biofeedback.
    
    Coherence is based on the regularity of the HRV pattern,
    particularly the presence of a dominant frequency in the
    0.04-0.26 Hz range (resonance frequency).
    """
    if len(rr) < 30:
        return 0.0
    
    from scipy import signal as sig
    from scipy import interpolate
    
    # Create time vector
    time = np.cumsum(rr) / 1000
    time = time - time[0]
    
    # Resample to 4 Hz
    duration = time[-1]
    if duration < 5:
        return 0.0
    
    n_samples = int(duration * 4)
    uniform_time = np.linspace(0, duration, n_samples)
    
    f = interpolate.interp1d(time, rr, kind='linear', fill_value='extrapolate')
    rr_resampled = f(uniform_time)
    
    # Detrend
    rr_detrended = sig.detrend(rr_resampled)
    
    # Compute PSD
    freqs, psd = sig.welch(rr_detrended, fs=4, nperseg=min(64, len(rr_detrended)))
    
    # Find power in coherence band (0.04-0.26 Hz)
    coherence_mask = (freqs >= 0.04) & (freqs <= 0.26)
    total_mask = (freqs >= 0.003) & (freqs <= 0.4)
    
    coherence_power = np.sum(psd[coherence_mask])
    total_power = np.sum(psd[total_mask])
    
    if total_power <= 0:
        return 0.0
    
    # Coherence ratio (0-100)
    coherence = (coherence_power / total_power) * 100
    
    # Find peak in coherence band
    if np.any(coherence_mask):
        peak_idx = np.argmax(psd[coherence_mask])
        peak_power = psd[coherence_mask][peak_idx]
        
        # Bonus for sharp peak (indicates regular rhythm)
        mean_power = np.mean(psd[coherence_mask])
        if mean_power > 0:
            peak_ratio = peak_power / mean_power
            coherence *= min(2.0, peak_ratio / 2)
    
    return min(100.0, coherence)


def _estimate_respiratory_rate(rr: NDArray) -> float:
    """Estimate respiratory rate from HRV (respiratory sinus arrhythmia)."""
    if len(rr) < 30:
        return 0.0
    
    from scipy import signal as sig
    from scipy import interpolate
    
    # Create time vector
    time = np.cumsum(rr) / 1000
    time = time - time[0]
    
    duration = time[-1]
    if duration < 10:
        return 0.0
    
    # Resample to 4 Hz
    n_samples = int(duration * 4)
    uniform_time = np.linspace(0, duration, n_samples)
    
    f = interpolate.interp1d(time, rr, kind='linear', fill_value='extrapolate')
    rr_resampled = f(uniform_time)
    
    # Bandpass filter for respiratory frequencies (0.1-0.5 Hz = 6-30 breaths/min)
    b, a = sig.butter(2, [0.1 / 2, 0.5 / 2], btype='band')
    rr_filtered = sig.filtfilt(b, a, rr_resampled)
    
    # Find dominant frequency
    freqs, psd = sig.welch(rr_filtered, fs=4, nperseg=min(64, len(rr_filtered)))
    
    resp_mask = (freqs >= 0.1) & (freqs <= 0.5)
    if not np.any(resp_mask):
        return 0.0
    
    peak_idx = np.argmax(psd[resp_mask])
    peak_freq = freqs[resp_mask][peak_idx]
    
    # Convert to breaths per minute
    resp_rate = peak_freq * 60
    
    return float(resp_rate)


def _calculate_stress_index(rr: NDArray) -> float:
    """Calculate Baevsky's stress index.
    
    SI = AMo / (2 * Mo * MxDMn)
    where:
    - AMo = amplitude of mode (% of intervals at mode)
    - Mo = mode (most frequent RR interval)
    - MxDMn = variation range (max - min)
    """
    if len(rr) < 20:
        return 50.0
    
    # Calculate histogram
    bin_width = 50  # 50ms bins
    bins = np.arange(np.min(rr), np.max(rr) + bin_width, bin_width)
    
    if len(bins) < 2:
        return 50.0
    
    hist, bin_edges = np.histogram(rr, bins=bins)
    
    # Mode (most frequent bin)
    mode_idx = np.argmax(hist)
    mo = (bin_edges[mode_idx] + bin_edges[mode_idx + 1]) / 2
    
    # Amplitude of mode (percentage)
    amo = hist[mode_idx] / len(rr) * 100
    
    # Variation range
    mxdmn = np.max(rr) - np.min(rr)
    
    if mo <= 0 or mxdmn <= 0:
        return 50.0
    
    # Stress index
    si = amo / (2 * mo / 1000 * mxdmn / 1000)  # Convert to seconds
    
    # Normalize to 0-100 scale (typical SI range is 50-500)
    normalized_si = min(100, si / 5)
    
    return float(normalized_si)


# ---------------------------------------------------------------------------
# Simulated Device (for testing)
# ---------------------------------------------------------------------------


class SimulatedHRMonitor:
    """Simulated heart rate monitor for testing.
    
    Generates realistic HRV data without requiring actual BLE hardware.
    """
    
    def __init__(
        self,
        baseline_hr: float = 70.0,
        hrv_amplitude: float = 30.0,
        respiratory_rate: float = 12.0,
    ) -> None:
        """Initialize simulated monitor.
        
        Args:
            baseline_hr: Baseline heart rate in BPM.
            hrv_amplitude: HRV amplitude in milliseconds.
            respiratory_rate: Respiratory rate in breaths/min.
        """
        self.baseline_hr = baseline_hr
        self.hrv_amplitude = hrv_amplitude
        self.respiratory_rate = respiratory_rate
        self._time = 0.0
        self._running = False
        self._callback: Callable[[HeartRateMeasurement], None] | None = None
    
    def start(self, callback: Callable[[HeartRateMeasurement], None]) -> None:
        """Start simulated streaming.
        
        Args:
            callback: Function to call with each measurement.
        """
        self._callback = callback
        self._running = True
        self._time = 0.0
    
    def stop(self) -> None:
        """Stop simulated streaming."""
        self._running = False
        self._callback = None
    
    def generate_measurement(self) -> HeartRateMeasurement | None:
        """Generate a simulated measurement.
        
        Returns:
            HeartRateMeasurement or None if not running.
        """
        if not self._running:
            return None
        
        # Simulate respiratory sinus arrhythmia
        resp_phase = 2 * np.pi * self.respiratory_rate / 60 * self._time
        
        # RR interval with RSA
        baseline_rr = 60000.0 / self.baseline_hr
        rr_variation = self.hrv_amplitude * np.sin(resp_phase)
        rr_noise = np.random.normal(0, 5)  # Small random noise
        
        rr_ms = baseline_rr + rr_variation + rr_noise
        rr_ms = max(MIN_RR_MS, min(MAX_RR_MS, rr_ms))
        
        hr_bpm = 60000.0 / rr_ms
        
        # Advance time
        self._time += rr_ms / 1000.0
        
        measurement = HeartRateMeasurement(
            timestamp=datetime.now(timezone.utc),
            heart_rate_bpm=hr_bpm,
            rr_intervals_ms=[rr_ms],
            sensor_contact=True,
            is_valid=True,
        )
        
        if self._callback:
            self._callback(measurement)
        
        return measurement


# ---------------------------------------------------------------------------
# BLE Manager Interface
# ---------------------------------------------------------------------------


class BLEManagerInterface(ABC):
    """Abstract interface for BLE device management.
    
    Implementations should handle platform-specific BLE operations.
    """
    
    @abstractmethod
    async def scan_devices(self, timeout: float = 10.0) -> list[BLEDevice]:
        """Scan for BLE heart rate monitors.
        
        Args:
            timeout: Scan timeout in seconds.
            
        Returns:
            List of discovered devices.
        """
        pass
    
    @abstractmethod
    async def connect(self, device: BLEDevice) -> bool:
        """Connect to a BLE device.
        
        Args:
            device: Device to connect to.
            
        Returns:
            True if connection successful.
        """
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from current device."""
        pass
    
    @abstractmethod
    async def start_streaming(
        self,
        callback: Callable[[HeartRateMeasurement], None],
    ) -> bool:
        """Start heart rate streaming.
        
        Args:
            callback: Function to call with each measurement.
            
        Returns:
            True if streaming started successfully.
        """
        pass
    
    @abstractmethod
    async def stop_streaming(self) -> None:
        """Stop heart rate streaming."""
        pass
    
    @abstractmethod
    def get_connection_state(self) -> ConnectionState:
        """Get current connection state."""
        pass


# ---------------------------------------------------------------------------
# Bleak-based BLE Manager (if available)
# ---------------------------------------------------------------------------


def create_ble_manager() -> BLEManagerInterface | None:
    """Create a BLE manager instance.
    
    Returns:
        BLEManagerInterface implementation or None if BLE not available.
    """
    try:
        from bleak import BleakClient, BleakScanner
        return BleakBLEManager()
    except ImportError:
        _LOGGER.warning("bleak library not available - BLE features disabled")
        return None


class BleakBLEManager(BLEManagerInterface):
    """BLE manager using the bleak library."""
    
    def __init__(self) -> None:
        """Initialize BLE manager."""
        self._client: Any = None
        self._device: BLEDevice | None = None
        self._state = ConnectionState.DISCONNECTED
        self._streaming_callback: Callable[[HeartRateMeasurement], None] | None = None
    
    async def scan_devices(self, timeout: float = 10.0) -> list[BLEDevice]:
        """Scan for BLE heart rate monitors."""
        try:
            from bleak import BleakScanner
            
            self._state = ConnectionState.SCANNING
            
            devices: list[BLEDevice] = []
            discovered = await BleakScanner.discover(timeout=timeout)
            
            for d in discovered:
                # Check if device advertises HR service
                name = d.name or "Unknown"
                
                # Detect device type from name
                device_type = DeviceType.GENERIC_BLE
                name_lower = name.lower()
                
                if "polar h10" in name_lower:
                    device_type = DeviceType.POLAR_H10
                elif "polar h9" in name_lower:
                    device_type = DeviceType.POLAR_H9
                elif "polar oh1" in name_lower:
                    device_type = DeviceType.POLAR_OH1
                elif "garmin" in name_lower and "hrm" in name_lower:
                    device_type = DeviceType.GARMIN_HRM
                elif "tickr" in name_lower:
                    device_type = DeviceType.WAHOO_TICKR
                
                devices.append(BLEDevice(
                    address=d.address,
                    name=name,
                    rssi=d.rssi or -100,
                    device_type=device_type,
                ))
            
            self._state = ConnectionState.DISCONNECTED
            return devices
            
        except Exception as exc:
            _LOGGER.error("BLE scan failed: %s", exc)
            self._state = ConnectionState.ERROR
            return []
    
    async def connect(self, device: BLEDevice) -> bool:
        """Connect to a BLE device."""
        try:
            from bleak import BleakClient
            
            self._state = ConnectionState.CONNECTING
            
            self._client = BleakClient(device.address)
            connected = await self._client.connect()
            
            if connected:
                self._device = device
                self._state = ConnectionState.CONNECTED
                _LOGGER.info("Connected to %s", device.name)
                return True
            else:
                self._state = ConnectionState.DISCONNECTED
                return False
                
        except Exception as exc:
            _LOGGER.error("BLE connect failed: %s", exc)
            self._state = ConnectionState.ERROR
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from current device."""
        if self._client:
            try:
                await self._client.disconnect()
            except Exception:
                pass
            self._client = None
        
        self._device = None
        self._state = ConnectionState.DISCONNECTED
    
    async def start_streaming(
        self,
        callback: Callable[[HeartRateMeasurement], None],
    ) -> bool:
        """Start heart rate streaming."""
        if not self._client or self._state != ConnectionState.CONNECTED:
            return False
        
        try:
            self._streaming_callback = callback
            
            def notification_handler(sender: Any, data: bytes) -> None:
                measurement = parse_heart_rate_measurement(data)
                if self._streaming_callback:
                    self._streaming_callback(measurement)
            
            await self._client.start_notify(
                HEART_RATE_MEASUREMENT_UUID,
                notification_handler,
            )
            
            self._state = ConnectionState.STREAMING
            return True
            
        except Exception as exc:
            _LOGGER.error("Failed to start streaming: %s", exc)
            return False
    
    async def stop_streaming(self) -> None:
        """Stop heart rate streaming."""
        if self._client and self._state == ConnectionState.STREAMING:
            try:
                await self._client.stop_notify(HEART_RATE_MEASUREMENT_UUID)
            except Exception:
                pass
        
        self._streaming_callback = None
        if self._device:
            self._state = ConnectionState.CONNECTED
        else:
            self._state = ConnectionState.DISCONNECTED
    
    def get_connection_state(self) -> ConnectionState:
        """Get current connection state."""
        return self._state


# ---------------------------------------------------------------------------
# Session Management
# ---------------------------------------------------------------------------


def create_streaming_session(device: BLEDevice | None = None) -> StreamingSession:
    """Create a new streaming session.
    
    Args:
        device: Connected device (optional).
        
    Returns:
        New StreamingSession instance.
    """
    import uuid
    
    return StreamingSession(
        session_id=str(uuid.uuid4())[:8],
        start_time=datetime.now(timezone.utc),
        device=device,
    )


def update_session_with_measurement(
    session: StreamingSession,
    measurement: HeartRateMeasurement,
) -> None:
    """Update session with new measurement.
    
    Args:
        session: Streaming session to update.
        measurement: New measurement to add.
    """
    session.last_update = measurement.timestamp
    
    # Add heart rate
    if measurement.is_valid:
        session.hr_buffer.append(measurement.heart_rate_bpm)
    
    # Add RR intervals
    for rr in measurement.rr_intervals_ms:
        if MIN_RR_MS <= rr <= MAX_RR_MS:
            session.rr_buffer.append(rr)
            session.total_beats += 1
        else:
            session.invalid_beats += 1


def export_session_data(session: StreamingSession) -> dict[str, Any]:
    """Export session data for saving.
    
    Args:
        session: Streaming session to export.
        
    Returns:
        Dictionary with session data.
    """
    return {
        "session_id": session.session_id,
        "start_time": session.start_time.isoformat(),
        "end_time": datetime.now(timezone.utc).isoformat(),
        "device": {
            "name": session.device.name if session.device else "Unknown",
            "type": session.device.device_type.value if session.device else "unknown",
        },
        "total_beats": session.total_beats,
        "invalid_beats": session.invalid_beats,
        "rr_intervals_ms": list(session.rr_buffer),
        "heart_rates_bpm": list(session.hr_buffer),
    }


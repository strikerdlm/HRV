"""Real-time HRV streaming and analysis module.

This module provides functionality for:
- Real-time RR interval streaming via BLE heart rate monitors
- Live HRV computation with sliding windows
- Coherence calculation for biofeedback
- Session management and data buffering

Supported devices:
- Polar H10, H9, OH1 (via Bluetooth Low Energy)
- Any BLE heart rate monitor with RR interval support
- Simulated data for testing

Scientific basis:
- HRV biofeedback (10×20 min sessions) significantly increases resting
  vagally-mediated HRV in healthy adults [Appl Psychophysiol Biofeedback 2024]
- Resonance frequency breathing (~6 breaths/min) maximizes HRV amplitude
  [Lehrer & Gevirtz, 2014; Front Public Health]

References:
- Polar SDK: https://github.com/polarofficial/polar-ble-sdk
- bleak library: https://github.com/hbldh/bleak
- Lehrer, P. M., & Gevirtz, R. (2014). Heart rate variability biofeedback.
"""

from __future__ import annotations

import asyncio
import logging
import math
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Final

import numpy as np

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)

# BLE UUIDs for Heart Rate Service
HR_SERVICE_UUID: Final[str] = "0000180d-0000-1000-8000-00805f9b34fb"
HR_MEASUREMENT_UUID: Final[str] = "00002a37-0000-1000-8000-00805f9b34fb"

# HRV computation parameters
DEFAULT_WINDOW_SIZE: Final[int] = 60  # seconds
MIN_RR_FOR_HRV: Final[int] = 30  # minimum RR intervals for valid HRV
MAX_RR_BUFFER: Final[int] = 1000  # maximum RR intervals to keep in buffer

# Coherence calculation parameters
COHERENCE_WINDOW: Final[float] = 64.0  # seconds for coherence calculation
RESONANCE_FREQ_LOW: Final[float] = 0.04  # Hz (lower bound of resonance band)
RESONANCE_FREQ_HIGH: Final[float] = 0.26  # Hz (upper bound of resonance band)

# Artifact detection
MIN_RR_MS: Final[int] = 300  # minimum valid RR interval
MAX_RR_MS: Final[int] = 2000  # maximum valid RR interval
MAX_RR_CHANGE_PCT: Final[float] = 0.25  # maximum beat-to-beat change


class ConnectionState(str, Enum):
    """BLE connection state."""

    DISCONNECTED = "disconnected"
    SCANNING = "scanning"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


class SessionState(str, Enum):
    """Biofeedback session state."""

    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"


class CoherenceLevel(str, Enum):
    """Coherence level classification."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class RRSample:
    """Single RR interval sample.

    Attributes:
        timestamp: UTC timestamp when received.
        rr_ms: RR interval in milliseconds.
        hr_bpm: Instantaneous heart rate in BPM.
        is_artifact: Whether this sample is flagged as artifact.
    """

    timestamp: datetime
    rr_ms: int
    hr_bpm: float
    is_artifact: bool = False


@dataclass(slots=True)
class RealtimeHRVMetrics:
    """Real-time HRV metrics computed from sliding window.

    Attributes:
        timestamp: Computation timestamp.
        window_size_sec: Window size in seconds.
        n_beats: Number of beats in window.
        mean_hr: Mean heart rate (BPM).
        sdnn: SDNN (ms).
        rmssd: RMSSD (ms).
        pnn50: pNN50 (%).
        coherence: Coherence score (0-100).
        coherence_level: Coherence classification.
        lf_power: LF power (ms²).
        hf_power: HF power (ms²).
        lf_hf_ratio: LF/HF ratio.
        respiratory_rate: Estimated respiratory rate (breaths/min).
    """

    timestamp: datetime
    window_size_sec: float
    n_beats: int
    mean_hr: float
    sdnn: float
    rmssd: float
    pnn50: float
    coherence: float
    coherence_level: CoherenceLevel
    lf_power: float
    hf_power: float
    lf_hf_ratio: float
    respiratory_rate: float


@dataclass(slots=True)
class BiofeedbackSession:
    """Biofeedback session data.

    Attributes:
        session_id: Unique session identifier.
        start_time: Session start timestamp.
        end_time: Session end timestamp (None if ongoing).
        target_duration_sec: Target session duration.
        breathing_rate: Target breathing rate (breaths/min).
        state: Current session state.
        rr_samples: List of RR samples collected.
        hrv_history: List of HRV metrics computed during session.
        coherence_scores: List of coherence scores over time.
        achievement_pct: Percentage of time in high coherence.
    """

    session_id: str
    start_time: datetime
    end_time: datetime | None = None
    target_duration_sec: int = 1200  # 20 minutes default
    breathing_rate: float = 6.0  # breaths/min (resonance frequency)
    state: SessionState = SessionState.IDLE
    rr_samples: list[RRSample] = field(default_factory=list)
    hrv_history: list[RealtimeHRVMetrics] = field(default_factory=list)
    coherence_scores: list[tuple[datetime, float]] = field(default_factory=list)
    achievement_pct: float = 0.0


@dataclass(frozen=True, slots=True)
class DeviceInfo:
    """BLE device information.

    Attributes:
        name: Device name.
        address: BLE address.
        rssi: Signal strength (dBm).
        has_rr: Whether device supports RR intervals.
    """

    name: str
    address: str
    rssi: int
    has_rr: bool = True


# ---------------------------------------------------------------------------
# Real-time HRV Engine
# ---------------------------------------------------------------------------


class RealtimeHRVEngine:
    """Engine for real-time HRV computation and biofeedback.

    This class manages:
    - RR interval buffering and artifact detection
    - Sliding window HRV computation
    - Coherence calculation for biofeedback
    - Session management

    Example:
        engine = RealtimeHRVEngine(window_size_sec=60)
        engine.add_rr_sample(850)  # Add RR interval
        metrics = engine.compute_hrv()  # Get current HRV metrics
        coherence = engine.compute_coherence()  # Get coherence score
    """

    def __init__(
        self,
        window_size_sec: float = DEFAULT_WINDOW_SIZE,
        artifact_threshold: float = MAX_RR_CHANGE_PCT,
    ) -> None:
        """Initialize the real-time HRV engine.

        Args:
            window_size_sec: Sliding window size in seconds.
            artifact_threshold: Maximum beat-to-beat change for artifact detection.
        """
        self._window_size_sec = window_size_sec
        self._artifact_threshold = artifact_threshold
        self._rr_buffer: deque[RRSample] = deque(maxlen=MAX_RR_BUFFER)
        self._last_rr: int | None = None
        self._callbacks: list[Callable[[RealtimeHRVMetrics], None]] = []
        self._current_session: BiofeedbackSession | None = None

    @property
    def buffer_size(self) -> int:
        """Number of RR samples in buffer."""
        return len(self._rr_buffer)

    @property
    def current_session(self) -> BiofeedbackSession | None:
        """Current biofeedback session."""
        return self._current_session

    def add_callback(self, callback: Callable[[RealtimeHRVMetrics], None]) -> None:
        """Register a callback for HRV updates.

        Args:
            callback: Function to call with new HRV metrics.
        """
        self._callbacks.append(callback)

    def remove_callback(self, callback: Callable[[RealtimeHRVMetrics], None]) -> None:
        """Remove a registered callback.

        Args:
            callback: Previously registered callback function.
        """
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def add_rr_sample(self, rr_ms: int, timestamp: datetime | None = None) -> RRSample:
        """Add a new RR interval sample.

        Args:
            rr_ms: RR interval in milliseconds.
            timestamp: Sample timestamp (defaults to now).

        Returns:
            The created RRSample with artifact flag set.
        """
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)

        # Calculate instantaneous HR
        hr_bpm = 60000.0 / rr_ms if rr_ms > 0 else 0.0

        # Artifact detection
        is_artifact = self._detect_artifact(rr_ms)

        sample = RRSample(
            timestamp=timestamp,
            rr_ms=rr_ms,
            hr_bpm=hr_bpm,
            is_artifact=is_artifact,
        )

        self._rr_buffer.append(sample)
        self._last_rr = rr_ms

        # Add to current session if running
        if self._current_session and self._current_session.state == SessionState.RUNNING:
            self._current_session.rr_samples.append(sample)

        return sample

    def _detect_artifact(self, rr_ms: int) -> bool:
        """Detect if RR interval is an artifact.

        Args:
            rr_ms: RR interval in milliseconds.

        Returns:
            True if artifact detected.
        """
        # Check absolute bounds
        if rr_ms < MIN_RR_MS or rr_ms > MAX_RR_MS:
            return True

        # Check relative change from previous beat
        if self._last_rr is not None:
            change_pct = abs(rr_ms - self._last_rr) / self._last_rr
            if change_pct > self._artifact_threshold:
                return True

        return False

    def get_window_samples(self) -> list[RRSample]:
        """Get RR samples within the current window.

        Returns:
            List of RRSample objects in the window.
        """
        if not self._rr_buffer:
            return []

        now = datetime.now(timezone.utc)
        cutoff = now.timestamp() - self._window_size_sec

        return [
            s for s in self._rr_buffer
            if s.timestamp.timestamp() >= cutoff
        ]

    def get_clean_rr_intervals(self) -> np.ndarray:
        """Get clean (non-artifact) RR intervals from current window.

        Returns:
            NumPy array of RR intervals in milliseconds.
        """
        samples = self.get_window_samples()
        clean_rr = [s.rr_ms for s in samples if not s.is_artifact]
        return np.array(clean_rr, dtype=float)

    def compute_hrv(self) -> RealtimeHRVMetrics | None:
        """Compute HRV metrics from current window.

        Returns:
            RealtimeHRVMetrics if sufficient data, None otherwise.
        """
        rr = self.get_clean_rr_intervals()

        if len(rr) < MIN_RR_FOR_HRV:
            return None

        # Time-domain metrics
        mean_rr = float(np.mean(rr))
        mean_hr = 60000.0 / mean_rr if mean_rr > 0 else 0.0
        sdnn = float(np.std(rr, ddof=1))

        # Successive differences
        diff_rr = np.diff(rr)
        rmssd = float(np.sqrt(np.mean(diff_rr ** 2)))
        nn50 = int(np.sum(np.abs(diff_rr) > 50))
        pnn50 = 100.0 * nn50 / len(diff_rr) if len(diff_rr) > 0 else 0.0

        # Frequency-domain (simplified FFT-based)
        lf_power, hf_power, resp_rate = self._compute_frequency_metrics(rr)
        lf_hf_ratio = lf_power / hf_power if hf_power > 0 else 0.0

        # Coherence
        coherence = self._compute_coherence_score(rr)
        coherence_level = self._classify_coherence(coherence)

        # Compute window duration
        samples = self.get_window_samples()
        if len(samples) >= 2:
            window_sec = (samples[-1].timestamp - samples[0].timestamp).total_seconds()
        else:
            window_sec = 0.0

        metrics = RealtimeHRVMetrics(
            timestamp=datetime.now(timezone.utc),
            window_size_sec=window_sec,
            n_beats=len(rr),
            mean_hr=mean_hr,
            sdnn=sdnn,
            rmssd=rmssd,
            pnn50=pnn50,
            coherence=coherence,
            coherence_level=coherence_level,
            lf_power=lf_power,
            hf_power=hf_power,
            lf_hf_ratio=lf_hf_ratio,
            respiratory_rate=resp_rate,
        )

        # Notify callbacks
        for callback in self._callbacks:
            try:
                callback(metrics)
            except Exception as e:
                _LOGGER.warning("Callback error: %s", e)

        # Update session if running
        if self._current_session and self._current_session.state == SessionState.RUNNING:
            self._current_session.hrv_history.append(metrics)
            self._current_session.coherence_scores.append(
                (metrics.timestamp, metrics.coherence)
            )

        return metrics

    def _compute_frequency_metrics(
        self, rr: np.ndarray
    ) -> tuple[float, float, float]:
        """Compute frequency-domain metrics using FFT.

        Args:
            rr: Array of RR intervals in milliseconds.

        Returns:
            Tuple of (LF power, HF power, respiratory rate).
        """
        if len(rr) < 32:
            return 0.0, 0.0, 0.0

        # Interpolate to uniform sampling (4 Hz)
        fs = 4.0
        cumsum = np.cumsum(rr) / 1000.0  # Convert to seconds
        cumsum = cumsum - cumsum[0]  # Start from 0

        if cumsum[-1] < 10:  # Need at least 10 seconds
            return 0.0, 0.0, 0.0

        # Create uniform time base
        t_uniform = np.arange(0, cumsum[-1], 1.0 / fs)
        rr_interp = np.interp(t_uniform, cumsum, rr)

        # Detrend
        rr_detrend = rr_interp - np.mean(rr_interp)

        # Apply Hanning window
        window = np.hanning(len(rr_detrend))
        rr_windowed = rr_detrend * window

        # FFT
        n_fft = max(256, 2 ** int(np.ceil(np.log2(len(rr_windowed)))))
        fft_result = np.fft.rfft(rr_windowed, n=n_fft)
        psd = np.abs(fft_result) ** 2 / len(rr_windowed)
        freqs = np.fft.rfftfreq(n_fft, 1.0 / fs)

        # Band powers
        lf_mask = (freqs >= 0.04) & (freqs < 0.15)
        hf_mask = (freqs >= 0.15) & (freqs <= 0.40)

        lf_power = float(np.sum(psd[lf_mask]))
        hf_power = float(np.sum(psd[hf_mask]))

        # Estimate respiratory rate from HF peak
        if np.any(hf_mask) and hf_power > 0:
            hf_freqs = freqs[hf_mask]
            hf_psd = psd[hf_mask]
            peak_idx = np.argmax(hf_psd)
            resp_freq = hf_freqs[peak_idx]
            resp_rate = resp_freq * 60.0  # Convert to breaths/min
        else:
            resp_rate = 0.0

        return lf_power, hf_power, resp_rate

    def _compute_coherence_score(self, rr: np.ndarray) -> float:
        """Compute cardiac coherence score.

        Coherence measures the degree of synchronization between heart rhythm
        and respiration, reflecting vagal tone and autonomic balance.

        Higher coherence indicates more ordered, sine-wave-like HRV pattern
        typically achieved during slow, rhythmic breathing.

        Args:
            rr: Array of RR intervals in milliseconds.

        Returns:
            Coherence score (0-100).
        """
        if len(rr) < 32:
            return 0.0

        # Interpolate to uniform sampling
        fs = 4.0
        cumsum = np.cumsum(rr) / 1000.0
        cumsum = cumsum - cumsum[0]

        if cumsum[-1] < 10:
            return 0.0

        t_uniform = np.arange(0, cumsum[-1], 1.0 / fs)
        rr_interp = np.interp(t_uniform, cumsum, rr)

        # Detrend
        rr_detrend = rr_interp - np.mean(rr_interp)

        # FFT for power spectrum
        n_fft = max(256, 2 ** int(np.ceil(np.log2(len(rr_detrend)))))
        fft_result = np.fft.rfft(rr_detrend, n=n_fft)
        psd = np.abs(fft_result) ** 2
        freqs = np.fft.rfftfreq(n_fft, 1.0 / fs)

        # Coherence band (resonance frequency range: 0.04-0.26 Hz)
        coherence_mask = (freqs >= RESONANCE_FREQ_LOW) & (freqs <= RESONANCE_FREQ_HIGH)

        if not np.any(coherence_mask):
            return 0.0

        coherence_psd = psd[coherence_mask]
        total_power = np.sum(psd[freqs > 0.003])  # Exclude DC

        if total_power < 1e-9:
            return 0.0

        # Find peak in coherence band
        peak_power = float(np.max(coherence_psd))
        coherence_power = float(np.sum(coherence_psd))

        # Coherence ratio: peak power / total power
        # Normalized to 0-100 scale
        coherence_ratio = peak_power / total_power

        # Apply sigmoid-like scaling for better distribution
        # Typical coherence ratios range from 0.05 to 0.40
        scaled = 100.0 * (1.0 / (1.0 + math.exp(-10.0 * (coherence_ratio - 0.15))))

        return min(100.0, max(0.0, scaled))

    def _classify_coherence(self, coherence: float) -> CoherenceLevel:
        """Classify coherence score into levels.

        Args:
            coherence: Coherence score (0-100).

        Returns:
            CoherenceLevel classification.
        """
        if coherence >= 70:
            return CoherenceLevel.HIGH
        elif coherence >= 40:
            return CoherenceLevel.MEDIUM
        else:
            return CoherenceLevel.LOW

    # -------------------------------------------------------------------------
    # Session Management
    # -------------------------------------------------------------------------

    def start_session(
        self,
        session_id: str | None = None,
        duration_sec: int = 1200,
        breathing_rate: float = 6.0,
    ) -> BiofeedbackSession:
        """Start a new biofeedback session.

        Args:
            session_id: Optional session identifier.
            duration_sec: Target session duration (default 20 min).
            breathing_rate: Target breathing rate (default 6 breaths/min).

        Returns:
            The created BiofeedbackSession.
        """
        if session_id is None:
            session_id = f"session_{int(time.time())}"

        self._current_session = BiofeedbackSession(
            session_id=session_id,
            start_time=datetime.now(timezone.utc),
            target_duration_sec=duration_sec,
            breathing_rate=breathing_rate,
            state=SessionState.RUNNING,
        )

        _LOGGER.info("Started biofeedback session: %s", session_id)
        return self._current_session

    def pause_session(self) -> None:
        """Pause the current session."""
        if self._current_session:
            self._current_session.state = SessionState.PAUSED
            _LOGGER.info("Paused session: %s", self._current_session.session_id)

    def resume_session(self) -> None:
        """Resume a paused session."""
        if self._current_session and self._current_session.state == SessionState.PAUSED:
            self._current_session.state = SessionState.RUNNING
            _LOGGER.info("Resumed session: %s", self._current_session.session_id)

    def end_session(self) -> BiofeedbackSession | None:
        """End the current session and compute summary.

        Returns:
            The completed session with summary statistics.
        """
        if not self._current_session:
            return None

        session = self._current_session
        session.end_time = datetime.now(timezone.utc)
        session.state = SessionState.COMPLETED

        # Compute achievement percentage (time in high coherence)
        if session.coherence_scores:
            high_count = sum(
                1 for _, score in session.coherence_scores
                if score >= 70
            )
            session.achievement_pct = 100.0 * high_count / len(session.coherence_scores)

        _LOGGER.info(
            "Ended session: %s (achievement: %.1f%%)",
            session.session_id,
            session.achievement_pct,
        )

        self._current_session = None
        return session

    def clear_buffer(self) -> None:
        """Clear the RR interval buffer."""
        self._rr_buffer.clear()
        self._last_rr = None


# ---------------------------------------------------------------------------
# BLE Heart Rate Monitor Interface
# ---------------------------------------------------------------------------


class BLEHeartRateMonitor:
    """Bluetooth Low Energy heart rate monitor interface.

    This class provides:
    - Device scanning and connection
    - RR interval extraction from HR measurements
    - Automatic reconnection handling

    Requires the 'bleak' library for BLE communication.

    Example:
        monitor = BLEHeartRateMonitor()
        devices = await monitor.scan_devices()
        await monitor.connect(devices[0].address)
        monitor.set_rr_callback(lambda rr: print(f"RR: {rr}ms"))
        await monitor.start_streaming()
    """

    def __init__(self) -> None:
        """Initialize the BLE monitor."""
        self._client: Any = None
        self._state = ConnectionState.DISCONNECTED
        self._device_info: DeviceInfo | None = None
        self._rr_callback: Callable[[int], None] | None = None
        self._hr_callback: Callable[[int], None] | None = None

    @property
    def state(self) -> ConnectionState:
        """Current connection state."""
        return self._state

    @property
    def device_info(self) -> DeviceInfo | None:
        """Connected device information."""
        return self._device_info

    def set_rr_callback(self, callback: Callable[[int], None]) -> None:
        """Set callback for RR interval notifications.

        Args:
            callback: Function to call with RR interval in ms.
        """
        self._rr_callback = callback

    def set_hr_callback(self, callback: Callable[[int], None]) -> None:
        """Set callback for heart rate notifications.

        Args:
            callback: Function to call with heart rate in BPM.
        """
        self._hr_callback = callback

    async def scan_devices(self, timeout: float = 10.0) -> list[DeviceInfo]:
        """Scan for BLE heart rate monitors.

        Args:
            timeout: Scan timeout in seconds.

        Returns:
            List of discovered devices with HR service.
        """
        try:
            from bleak import BleakScanner
        except ImportError:
            _LOGGER.error("bleak library not installed. Run: pip install bleak")
            return []

        self._state = ConnectionState.SCANNING
        devices: list[DeviceInfo] = []

        try:
            discovered = await BleakScanner.discover(
                timeout=timeout,
                return_adv=True,
            )

            for device, adv_data in discovered.values():
                # Check for Heart Rate Service UUID
                service_uuids = adv_data.service_uuids or []
                has_hr = HR_SERVICE_UUID.lower() in [u.lower() for u in service_uuids]

                # Also check by name patterns
                name = device.name or ""
                is_hr_device = has_hr or any(
                    pattern in name.lower()
                    for pattern in ["polar", "heart", "hr", "h10", "h9", "oh1", "verity"]
                )

                if is_hr_device:
                    devices.append(
                        DeviceInfo(
                            name=name or "Unknown",
                            address=device.address,
                            rssi=adv_data.rssi or -100,
                            has_rr=True,  # Assume RR support for HR devices
                        )
                    )

            _LOGGER.info("Found %d HR devices", len(devices))

        except Exception as e:
            _LOGGER.error("Scan failed: %s", e)
            self._state = ConnectionState.ERROR

        self._state = ConnectionState.DISCONNECTED
        return devices

    async def connect(self, address: str) -> bool:
        """Connect to a BLE heart rate monitor.

        Args:
            address: BLE device address.

        Returns:
            True if connection successful.
        """
        try:
            from bleak import BleakClient
        except ImportError:
            _LOGGER.error("bleak library not installed")
            return False

        self._state = ConnectionState.CONNECTING

        try:
            self._client = BleakClient(address)
            await self._client.connect()

            if self._client.is_connected:
                self._state = ConnectionState.CONNECTED
                self._device_info = DeviceInfo(
                    name="Connected Device",
                    address=address,
                    rssi=-50,
                    has_rr=True,
                )
                _LOGGER.info("Connected to %s", address)
                return True

        except Exception as e:
            _LOGGER.error("Connection failed: %s", e)
            self._state = ConnectionState.ERROR

        return False

    async def disconnect(self) -> None:
        """Disconnect from the device."""
        if self._client:
            try:
                await self._client.disconnect()
            except Exception as e:
                _LOGGER.warning("Disconnect error: %s", e)

        self._state = ConnectionState.DISCONNECTED
        self._device_info = None
        self._client = None

    async def start_streaming(self) -> bool:
        """Start receiving HR/RR notifications.

        Returns:
            True if streaming started successfully.
        """
        if not self._client or not self._client.is_connected:
            _LOGGER.error("Not connected")
            return False

        try:
            await self._client.start_notify(
                HR_MEASUREMENT_UUID,
                self._handle_hr_notification,
            )
            _LOGGER.info("Started HR streaming")
            return True

        except Exception as e:
            _LOGGER.error("Failed to start streaming: %s", e)
            return False

    async def stop_streaming(self) -> None:
        """Stop receiving notifications."""
        if self._client and self._client.is_connected:
            try:
                await self._client.stop_notify(HR_MEASUREMENT_UUID)
            except Exception as e:
                _LOGGER.warning("Stop streaming error: %s", e)

    def _handle_hr_notification(
        self, _sender: Any, data: bytearray
    ) -> None:
        """Handle incoming HR measurement notification.

        Heart Rate Measurement characteristic format:
        - Byte 0: Flags
          - Bit 0: HR format (0=UINT8, 1=UINT16)
          - Bit 4: RR intervals present
        - Byte 1(-2): Heart Rate value
        - Remaining bytes: RR intervals (if present)

        Args:
            _sender: Notification sender (unused).
            data: Raw notification data.
        """
        if len(data) < 2:
            return

        flags = data[0]
        hr_format_16bit = bool(flags & 0x01)
        rr_present = bool(flags & 0x10)

        # Parse heart rate
        if hr_format_16bit:
            hr = int.from_bytes(data[1:3], byteorder="little")
            rr_start = 3
        else:
            hr = data[1]
            rr_start = 2

        # Notify HR callback
        if self._hr_callback:
            self._hr_callback(hr)

        # Parse RR intervals (if present)
        if rr_present and self._rr_callback:
            idx = rr_start
            while idx + 1 < len(data):
                # RR intervals are in 1/1024 seconds
                rr_raw = int.from_bytes(data[idx:idx + 2], byteorder="little")
                rr_ms = int(rr_raw * 1000 / 1024)  # Convert to milliseconds
                self._rr_callback(rr_ms)
                idx += 2


# ---------------------------------------------------------------------------
# Simulated Data Generator (for testing)
# ---------------------------------------------------------------------------


class SimulatedHRGenerator:
    """Generate simulated RR intervals for testing.

    Produces realistic RR intervals with configurable:
    - Mean heart rate
    - HRV amplitude
    - Respiratory modulation (RSA)
    - Random noise

    Example:
        generator = SimulatedHRGenerator(mean_hr=70, hrv_amplitude=50)
        async for rr_ms in generator.stream():
            process_rr(rr_ms)
    """

    def __init__(
        self,
        mean_hr: float = 70.0,
        hrv_amplitude: float = 50.0,
        respiratory_rate: float = 6.0,
        noise_level: float = 10.0,
    ) -> None:
        """Initialize the simulator.

        Args:
            mean_hr: Mean heart rate in BPM.
            hrv_amplitude: HRV amplitude in ms.
            respiratory_rate: Respiratory rate in breaths/min.
            noise_level: Random noise amplitude in ms.
        """
        self._mean_hr = mean_hr
        self._hrv_amplitude = hrv_amplitude
        self._resp_rate = respiratory_rate
        self._noise_level = noise_level
        self._phase = 0.0
        self._running = False

    async def stream(self, duration_sec: float | None = None) -> None:
        """Stream simulated RR intervals.

        Args:
            duration_sec: Optional duration limit.

        Yields:
            RR intervals in milliseconds.
        """
        self._running = True
        start_time = time.time()

        while self._running:
            if duration_sec and (time.time() - start_time) >= duration_sec:
                break

            rr_ms = self._generate_rr()
            yield rr_ms

            # Wait approximately one beat
            await asyncio.sleep(rr_ms / 1000.0)

    def stop(self) -> None:
        """Stop the simulation."""
        self._running = False

    def _generate_rr(self) -> int:
        """Generate a single RR interval.

        Returns:
            RR interval in milliseconds.
        """
        # Base RR from mean HR
        mean_rr = 60000.0 / self._mean_hr

        # Respiratory sinus arrhythmia (RSA) component
        resp_freq = self._resp_rate / 60.0  # Convert to Hz
        rsa = self._hrv_amplitude * math.sin(2 * math.pi * resp_freq * self._phase)

        # Random noise
        noise = np.random.normal(0, self._noise_level)

        # Combine components
        rr = mean_rr + rsa + noise

        # Update phase
        self._phase += rr / 1000.0

        # Clamp to valid range
        return int(max(MIN_RR_MS, min(MAX_RR_MS, rr)))


# ---------------------------------------------------------------------------
# Paced Breathing Guide
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class BreathingPhase:
    """Breathing phase definition.

    Attributes:
        name: Phase name (inhale, hold, exhale).
        duration_sec: Phase duration in seconds.
        instruction: User instruction text.
    """

    name: str
    duration_sec: float
    instruction: str


class PacedBreathingGuide:
    """Paced breathing guide for HRV biofeedback.

    Provides timed breathing cues at configurable rates,
    optimized for HRV coherence training.

    Common patterns:
    - 6 breaths/min (5s in, 5s out) - resonance frequency
    - 4 breaths/min (6s in, 2s hold, 7s out) - deep relaxation
    - 10 breaths/min (3s in, 3s out) - energizing

    Example:
        guide = PacedBreathingGuide(breaths_per_min=6)
        async for phase in guide.run_cycle():
            update_ui(phase)
    """

    def __init__(
        self,
        breaths_per_min: float = 6.0,
        inhale_ratio: float = 0.4,
        hold_ratio: float = 0.0,
        exhale_ratio: float = 0.6,
    ) -> None:
        """Initialize the breathing guide.

        Args:
            breaths_per_min: Target breathing rate.
            inhale_ratio: Fraction of cycle for inhale (0-1).
            hold_ratio: Fraction of cycle for hold (0-1).
            exhale_ratio: Fraction of cycle for exhale (0-1).
        """
        total_ratio = inhale_ratio + hold_ratio + exhale_ratio
        if abs(total_ratio - 1.0) > 0.01:
            # Normalize ratios
            inhale_ratio /= total_ratio
            hold_ratio /= total_ratio
            exhale_ratio /= total_ratio

        self._breaths_per_min = breaths_per_min
        self._inhale_ratio = inhale_ratio
        self._hold_ratio = hold_ratio
        self._exhale_ratio = exhale_ratio
        self._running = False

    @property
    def cycle_duration_sec(self) -> float:
        """Duration of one complete breath cycle."""
        return 60.0 / self._breaths_per_min

    @property
    def phases(self) -> list[BreathingPhase]:
        """Get the breathing phases for one cycle."""
        cycle = self.cycle_duration_sec
        phases = [
            BreathingPhase(
                name="inhale",
                duration_sec=cycle * self._inhale_ratio,
                instruction="Breathe in slowly...",
            ),
        ]

        if self._hold_ratio > 0:
            phases.append(
                BreathingPhase(
                    name="hold",
                    duration_sec=cycle * self._hold_ratio,
                    instruction="Hold...",
                )
            )

        phases.append(
            BreathingPhase(
                name="exhale",
                duration_sec=cycle * self._exhale_ratio,
                instruction="Breathe out slowly...",
            )
        )

        return phases

    async def run_cycle(self, num_cycles: int | None = None):
        """Run breathing cycles.

        Args:
            num_cycles: Number of cycles (None for infinite).

        Yields:
            BreathingPhase for each phase transition.
        """
        self._running = True
        cycle_count = 0

        while self._running:
            if num_cycles is not None and cycle_count >= num_cycles:
                break

            for phase in self.phases:
                if not self._running:
                    break
                yield phase
                await asyncio.sleep(phase.duration_sec)

            cycle_count += 1

    def stop(self) -> None:
        """Stop the breathing guide."""
        self._running = False


"""Polar H10 BLE RR Interval Recorder Module.

This module provides functionality to connect to a Polar H10 chest strap
via Bluetooth Low Energy (BLE) and record RR intervals to a text file.

The recorded file format matches the existing HRV analysis format:
- One RR interval (in milliseconds) per line
- Filename format: YYYY-MM-DD HH-MM-SS.txt

Author: Dr. Diego Malpica, MD
        Aerospace Medicine Specialist
        National University of Colombia

Supported Devices:
    - Polar H10 (primary)
    - Polar H9
    - Any BLE heart rate monitor with RR interval support

References:
    - Bluetooth SIG Heart Rate Service Specification (UUID: 0x180D)
    - Heart Rate Measurement Characteristic (UUID: 0x2A37)
    - Polar SDK: https://github.com/polarofficial/polar-ble-sdk
    - bleak library: https://github.com/hbldh/bleak

Note: Requires the `bleak` library: pip install bleak
"""

from __future__ import annotations

import asyncio
import logging
import struct
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Final, Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)

# BLE UUIDs
HEART_RATE_SERVICE_UUID: Final[str] = "0000180d-0000-1000-8000-00805f9b34fb"
HEART_RATE_MEASUREMENT_UUID: Final[str] = "00002a37-0000-1000-8000-00805f9b34fb"
BATTERY_SERVICE_UUID: Final[str] = "0000180f-0000-1000-8000-00805f9b34fb"
BATTERY_LEVEL_UUID: Final[str] = "00002a19-0000-1000-8000-00805f9b34fb"

# RR interval validation bounds (ms)
MIN_RR_MS: Final[float] = 200.0   # ~300 BPM max
MAX_RR_MS: Final[float] = 2500.0  # ~24 BPM min
MIN_HR_BPM: Final[float] = 20.0
MAX_HR_BPM: Final[float] = 250.0

# Default scan timeout
DEFAULT_SCAN_TIMEOUT: Final[float] = 10.0


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


class RecorderState(Enum):
    """State of the BLE recorder."""
    IDLE = "idle"
    SCANNING = "scanning"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECORDING = "recording"
    STOPPING = "stopping"
    ERROR = "error"


@dataclass
class ScannedDevice:
    """A discovered BLE device."""
    address: str
    name: str
    rssi: int
    is_polar: bool = False
    
    def __str__(self) -> str:
        polar_tag = " [Polar]" if self.is_polar else ""
        return f"{self.name}{polar_tag} ({self.address}) RSSI: {self.rssi}"


@dataclass
class RecordingStats:
    """Statistics for the current recording session."""
    start_time: datetime | None = None
    rr_count: int = 0
    hr_samples: int = 0
    last_hr: float = 0.0
    last_rr: float = 0.0
    avg_hr: float = 0.0
    duration_sec: float = 0.0
    file_path: str | None = None


# ---------------------------------------------------------------------------
# BLE Check
# ---------------------------------------------------------------------------


def is_bleak_available() -> bool:
    """Check if bleak library is available."""
    try:
        import bleak  # noqa: F401
        return True
    except ImportError:
        return False


# ---------------------------------------------------------------------------
# Polar H10 Recorder Class
# ---------------------------------------------------------------------------


class PolarH10Recorder:
    """Recorder for Polar H10 (and compatible) BLE heart rate monitors.
    
    This class handles:
    - BLE device scanning
    - Connection to Polar H10
    - RR interval streaming
    - Recording to text file
    
    Usage:
        recorder = PolarH10Recorder(output_dir="Diego_Malpica")
        
        # Scan for devices
        devices = await recorder.scan_devices()
        
        # Connect to a device
        await recorder.connect(devices[0])
        
        # Start recording
        await recorder.start_recording()
        
        # ... recording in progress ...
        
        # Stop recording
        await recorder.stop_recording()
        
        # Disconnect
        await recorder.disconnect()
    """
    
    def __init__(
        self,
        output_dir: str | Path = ".",
        on_state_change: Callable[[RecorderState], None] | None = None,
        on_data_received: Callable[[float, float], None] | None = None,
    ) -> None:
        """Initialize the recorder.
        
        Args:
            output_dir: Directory to save RR interval files.
            on_state_change: Callback when state changes.
            on_data_received: Callback when HR/RR data received (hr_bpm, rr_ms).
        """
        self._output_dir = Path(output_dir)
        self._on_state_change = on_state_change
        self._on_data_received = on_data_received
        
        # State
        self._state = RecorderState.IDLE
        self._client: Any = None
        self._device: ScannedDevice | None = None
        self._recording = False
        
        # Recording data
        self._rr_intervals: list[int] = []  # Store as integers (ms)
        self._hr_values: list[float] = []
        self._stats = RecordingStats()
        self._file_handle: Any = None
        self._record_start: datetime | None = None
        
        # Async event loop handling
        self._loop: asyncio.AbstractEventLoop | None = None
    
    @property
    def state(self) -> RecorderState:
        """Get current recorder state."""
        return self._state
    
    @property
    def stats(self) -> RecordingStats:
        """Get current recording statistics."""
        return self._stats
    
    @property
    def is_connected(self) -> bool:
        """Check if connected to a device."""
        return self._state in (RecorderState.CONNECTED, RecorderState.RECORDING)
    
    @property
    def is_recording(self) -> bool:
        """Check if currently recording."""
        return self._state == RecorderState.RECORDING
    
    def _set_state(self, new_state: RecorderState) -> None:
        """Update state and notify callback."""
        old_state = self._state
        self._state = new_state
        _LOGGER.debug("State change: %s -> %s", old_state, new_state)
        if self._on_state_change:
            try:
                self._on_state_change(new_state)
            except Exception as exc:
                _LOGGER.warning("State change callback error: %s", exc)
    
    async def scan_devices(self, timeout: float = DEFAULT_SCAN_TIMEOUT) -> list[ScannedDevice]:
        """Scan for BLE heart rate monitors.
        
        Args:
            timeout: Scan timeout in seconds.
            
        Returns:
            List of discovered devices (Polar devices first).
        """
        if not is_bleak_available():
            _LOGGER.error("bleak library not installed")
            self._set_state(RecorderState.ERROR)
            return []
        
        try:
            from bleak import BleakScanner
            
            self._set_state(RecorderState.SCANNING)
            _LOGGER.info("Scanning for BLE devices (timeout=%s sec)...", timeout)
            
            devices: list[ScannedDevice] = []
            discovered = await BleakScanner.discover(timeout=timeout)
            
            for d in discovered:
                name = d.name or "Unknown"
                name_lower = name.lower()
                
                # Filter for heart rate monitors (Polar, Garmin HRM, Wahoo, etc.)
                is_hrm = any(x in name_lower for x in [
                    "polar", "h10", "h9", "oh1", "verity",
                    "garmin", "hrm", "tickr", "wahoo",
                    "heart", "hr "
                ])
                
                if is_hrm or (d.rssi and d.rssi > -80):  # Strong signal
                    is_polar = "polar" in name_lower
                    devices.append(ScannedDevice(
                        address=d.address,
                        name=name,
                        rssi=d.rssi or -100,
                        is_polar=is_polar,
                    ))
            
            # Sort: Polar devices first, then by signal strength
            devices.sort(key=lambda x: (not x.is_polar, -x.rssi))
            
            _LOGGER.info("Found %d devices", len(devices))
            self._set_state(RecorderState.IDLE)
            return devices
            
        except Exception as exc:
            _LOGGER.error("BLE scan failed: %s", exc)
            self._set_state(RecorderState.ERROR)
            return []
    
    async def connect(self, device: ScannedDevice) -> bool:
        """Connect to a BLE device.
        
        Args:
            device: Device to connect to.
            
        Returns:
            True if connection successful.
        """
        if not is_bleak_available():
            _LOGGER.error("bleak library not installed")
            return False
        
        try:
            from bleak import BleakClient
            
            self._set_state(RecorderState.CONNECTING)
            _LOGGER.info("Connecting to %s (%s)...", device.name, device.address)
            
            self._client = BleakClient(device.address)
            connected = await self._client.connect()
            
            if connected:
                self._device = device
                self._set_state(RecorderState.CONNECTED)
                _LOGGER.info("Connected to %s", device.name)
                return True
            else:
                self._set_state(RecorderState.IDLE)
                _LOGGER.warning("Connection failed")
                return False
                
        except Exception as exc:
            _LOGGER.error("Connection error: %s", exc)
            self._set_state(RecorderState.ERROR)
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from the current device."""
        if self._recording:
            await self.stop_recording()
        
        if self._client:
            try:
                await self._client.disconnect()
                _LOGGER.info("Disconnected")
            except Exception as exc:
                _LOGGER.debug("Disconnect cleanup: %s", exc)
            self._client = None
        
        self._device = None
        self._set_state(RecorderState.IDLE)
    
    async def start_recording(self) -> bool:
        """Start recording RR intervals to file.
        
        Returns:
            True if recording started successfully.
        """
        if self._state != RecorderState.CONNECTED:
            _LOGGER.error("Cannot start recording: not connected")
            return False
        
        if self._client is None:
            _LOGGER.error("No BLE client available")
            return False
        
        try:
            # Create output directory if needed
            self._output_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate filename with timestamp
            self._record_start = datetime.now()
            filename = self._record_start.strftime("%Y-%m-%d %H-%M-%S") + ".txt"
            filepath = self._output_dir / filename
            
            # Open file for writing
            self._file_handle = open(filepath, "w", encoding="utf-8")
            
            # Reset stats
            self._rr_intervals = []
            self._hr_values = []
            self._stats = RecordingStats(
                start_time=self._record_start,
                file_path=str(filepath),
            )
            
            # Start BLE notifications
            self._recording = True
            
            await self._client.start_notify(
                HEART_RATE_MEASUREMENT_UUID,
                self._hr_notification_handler,
            )
            
            self._set_state(RecorderState.RECORDING)
            _LOGGER.info("Recording started: %s", filepath)
            return True
            
        except Exception as exc:
            _LOGGER.error("Failed to start recording: %s", exc)
            self._recording = False
            if self._file_handle:
                self._file_handle.close()
                self._file_handle = None
            self._set_state(RecorderState.ERROR)
            return False
    
    async def stop_recording(self) -> str | None:
        """Stop recording and save file.
        
        Returns:
            Path to the saved file, or None if error.
        """
        if not self._recording:
            return None
        
        self._set_state(RecorderState.STOPPING)
        self._recording = False
        
        try:
            # Stop BLE notifications
            if self._client:
                try:
                    await self._client.stop_notify(HEART_RATE_MEASUREMENT_UUID)
                except Exception as exc:
                    _LOGGER.debug("Stop notify cleanup: %s", exc)
            
            # Close file
            filepath = self._stats.file_path
            if self._file_handle:
                self._file_handle.close()
                self._file_handle = None
            
            # Update final stats
            if self._record_start:
                self._stats.duration_sec = (
                    datetime.now() - self._record_start
                ).total_seconds()
            
            if self._hr_values:
                self._stats.avg_hr = sum(self._hr_values) / len(self._hr_values)
            
            self._set_state(RecorderState.CONNECTED)
            _LOGGER.info(
                "Recording stopped: %d RR intervals saved to %s",
                self._stats.rr_count,
                filepath,
            )
            return filepath
            
        except Exception as exc:
            _LOGGER.error("Error stopping recording: %s", exc)
            self._set_state(RecorderState.ERROR)
            return None
    
    def _hr_notification_handler(self, sender: Any, data: bytes) -> None:
        """Handle incoming heart rate measurement notifications.
        
        This parses the BLE Heart Rate Measurement characteristic data
        according to Bluetooth SIG specification.
        
        Args:
            sender: BLE characteristic handle.
            data: Raw bytes from HR Measurement characteristic.
        """
        if not self._recording:
            return
        
        try:
            hr, rr_intervals = self._parse_hr_measurement(data)
            
            if hr > 0:
                self._hr_values.append(hr)
                self._stats.hr_samples += 1
                self._stats.last_hr = hr
            
            for rr_ms in rr_intervals:
                # Validate RR interval
                if MIN_RR_MS <= rr_ms <= MAX_RR_MS:
                    # Round to integer (matches file format)
                    rr_int = round(rr_ms)
                    self._rr_intervals.append(rr_int)
                    
                    # Write to file immediately
                    if self._file_handle:
                        self._file_handle.write(f"{rr_int}\n")
                        self._file_handle.flush()
                    
                    # Update stats
                    self._stats.rr_count += 1
                    self._stats.last_rr = rr_ms
                    
                    # Notify callback
                    if self._on_data_received:
                        try:
                            self._on_data_received(hr, rr_ms)
                        except Exception as exc:
                            _LOGGER.debug("Data callback error: %s", exc)
            
            # Update duration
            if self._record_start:
                self._stats.duration_sec = (
                    datetime.now() - self._record_start
                ).total_seconds()
                
        except Exception as exc:
            _LOGGER.warning("Error parsing HR data: %s", exc)
    
    def _parse_hr_measurement(self, data: bytes) -> tuple[float, list[float]]:
        """Parse BLE Heart Rate Measurement characteristic data.
        
        Format (Bluetooth SIG Heart Rate Service Spec):
        - Byte 0: Flags
          - Bit 0: HR value format (0=UINT8, 1=UINT16)
          - Bit 1-2: Sensor contact status
          - Bit 3: Energy expended present
          - Bit 4: RR intervals present
        - Byte 1(-2): Heart rate value
        - Remaining bytes: Energy expended (if present) + RR intervals
        
        Args:
            data: Raw characteristic data.
            
        Returns:
            Tuple of (heart_rate_bpm, [rr_intervals_ms]).
        """
        if len(data) < 2:
            return 0.0, []
        
        flags = data[0]
        
        # Bit 0: HR value format
        hr_format_16bit = bool(flags & 0x01)
        
        # Bit 3: Energy expended present
        energy_present = bool(flags & 0x08)
        
        # Bit 4: RR intervals present
        rr_present = bool(flags & 0x10)
        
        # Parse heart rate
        offset = 1
        if hr_format_16bit:
            if len(data) < 3:
                return 0.0, []
            heart_rate = struct.unpack_from("<H", data, offset)[0]
            offset += 2
        else:
            heart_rate = data[offset]
            offset += 1
        
        # Skip energy expended (2 bytes) if present
        if energy_present:
            offset += 2
        
        # Parse RR intervals
        rr_intervals: list[float] = []
        if rr_present:
            while offset + 1 < len(data):
                # RR intervals are in 1/1024 second units
                rr_raw = struct.unpack_from("<H", data, offset)[0]
                rr_ms = rr_raw / 1024.0 * 1000.0  # Convert to milliseconds
                rr_intervals.append(rr_ms)
                offset += 2
        
        return float(heart_rate), rr_intervals
    
    async def get_battery_level(self) -> int | None:
        """Read battery level from device.
        
        Returns:
            Battery level (0-100) or None if not available.
        """
        if not self._client or not self.is_connected:
            return None
        
        try:
            battery = await self._client.read_gatt_char(BATTERY_LEVEL_UUID)
            if battery:
                return battery[0]
        except Exception as exc:
            _LOGGER.debug("Battery read failed: %s", exc)
        
        return None


# ---------------------------------------------------------------------------
# Synchronous Wrapper for Streamlit
# ---------------------------------------------------------------------------


class PolarH10RecorderSync:
    """Synchronous wrapper for PolarH10Recorder.
    
    This provides a synchronous interface suitable for Streamlit,
    running async operations in a background thread.
    """
    
    def __init__(
        self,
        output_dir: str | Path = ".",
        on_state_change: Callable[[RecorderState], None] | None = None,
        on_data_received: Callable[[float, float], None] | None = None,
    ) -> None:
        """Initialize synchronous wrapper."""
        self._output_dir = Path(output_dir)
        self._on_state_change = on_state_change
        self._on_data_received = on_data_received
        
        self._recorder: PolarH10Recorder | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._devices: list[ScannedDevice] = []
    
    @property
    def state(self) -> RecorderState:
        """Get current state."""
        if self._recorder:
            return self._recorder.state
        return RecorderState.IDLE
    
    @property
    def stats(self) -> RecordingStats:
        """Get recording stats."""
        if self._recorder:
            return self._recorder.stats
        return RecordingStats()
    
    @property
    def is_connected(self) -> bool:
        """Check if connected."""
        return self._recorder.is_connected if self._recorder else False
    
    @property
    def is_recording(self) -> bool:
        """Check if recording."""
        return self._recorder.is_recording if self._recorder else False
    
    def _ensure_loop(self) -> None:
        """Ensure async event loop is running."""
        if self._loop is None or not self._loop.is_running():
            self._loop = asyncio.new_event_loop()
            
            def run_loop() -> None:
                asyncio.set_event_loop(self._loop)
                self._loop.run_forever()
            
            self._thread = threading.Thread(target=run_loop, daemon=True)
            self._thread.start()
            
            # Wait for loop to start
            time.sleep(0.1)
        
        if self._recorder is None:
            self._recorder = PolarH10Recorder(
                output_dir=self._output_dir,
                on_state_change=self._on_state_change,
                on_data_received=self._on_data_received,
            )
    
    def _run_async(self, coro: Any, timeout: float = 30.0) -> Any:
        """Run async coroutine synchronously."""
        self._ensure_loop()
        if self._loop is None:
            raise RuntimeError("Event loop not available")
        
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result(timeout=timeout)
    
    def scan_devices(self, timeout: float = DEFAULT_SCAN_TIMEOUT) -> list[ScannedDevice]:
        """Scan for BLE devices synchronously."""
        self._ensure_loop()
        if self._recorder is None:
            return []
        self._devices = self._run_async(
            self._recorder.scan_devices(timeout),
            timeout=timeout + 5,
        )
        return self._devices
    
    def connect(self, device: ScannedDevice) -> bool:
        """Connect to device synchronously."""
        if self._recorder is None:
            return False
        return self._run_async(self._recorder.connect(device))
    
    def disconnect(self) -> None:
        """Disconnect synchronously."""
        if self._recorder:
            self._run_async(self._recorder.disconnect())
    
    def start_recording(self) -> bool:
        """Start recording synchronously."""
        if self._recorder is None:
            return False
        return self._run_async(self._recorder.start_recording())
    
    def stop_recording(self) -> str | None:
        """Stop recording synchronously."""
        if self._recorder is None:
            return None
        return self._run_async(self._recorder.stop_recording())
    
    def get_battery_level(self) -> int | None:
        """Get battery level synchronously."""
        if self._recorder is None:
            return None
        return self._run_async(self._recorder.get_battery_level())
    
    def cleanup(self) -> None:
        """Clean up resources."""
        if self._recorder and self._recorder.is_connected:
            self.disconnect()
        
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
        
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        
        self._loop = None
        self._thread = None
        self._recorder = None


# ---------------------------------------------------------------------------
# Convenience Functions
# ---------------------------------------------------------------------------


def get_output_directory(username: str, base_path: str | Path | None = None) -> Path:
    """Get the output directory for a user's RR recordings.
    
    Args:
        username: User's name or identifier.
        base_path: Base directory (defaults to current working directory).
        
    Returns:
        Path to the user's recording directory.
    """
    if base_path is None:
        # Default to parent of app directory
        base_path = Path(__file__).parent.parent
    
    # Sanitize username for filesystem
    safe_name = "".join(c if c.isalnum() or c in " _-" else "_" for c in username)
    safe_name = safe_name.strip().replace(" ", "_")
    
    return Path(base_path) / safe_name


def list_recordings(directory: str | Path) -> list[Path]:
    """List all RR interval recordings in a directory.
    
    Args:
        directory: Directory to search.
        
    Returns:
        List of recording file paths, sorted by modification time (newest first).
    """
    dir_path = Path(directory)
    if not dir_path.exists():
        return []
    
    recordings = list(dir_path.glob("*.txt"))
    recordings.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return recordings


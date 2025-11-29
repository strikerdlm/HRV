"""User data persistence and session management module.

This module provides functionality for:
- User identification and session management
- Data persistence to disk (data folder)
- Automatic data loading from user folders
- Multi-day data aggregation
- Graceful handling of missing data

Design principles:
- Data is stored in data/{user_id}/ folder structure
- Files are JSON/CSV for portability
- Missing data gracefully ignored (no crashes)
- Thread-safe file operations

Author: Dr. Diego Malpica, MD - Aerospace Medicine Specialist
National University of Colombia | Colombian Aerospace Force
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import shutil
from dataclasses import dataclass, field, asdict
from datetime import datetime, date, timedelta, timezone
from pathlib import Path
from typing import Any, Final, TypedDict

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)

# Data folder structure
_DATA_ROOT: Final[str] = "data"
_USER_INFO_FILE: Final[str] = "user_info.json"
_RR_DATA_DIR: Final[str] = "rr_intervals"
_SLEEP_DATA_DIR: Final[str] = "sleep"
_ACTIVITY_DATA_DIR: Final[str] = "activity"
_HRV_RESULTS_DIR: Final[str] = "hrv_results"
_DEVICE_DATA_DIR: Final[str] = "device_imports"
_SESSION_FILE: Final[str] = "sessions.json"

# Maximum files to load per category
_MAX_FILES_PER_CATEGORY: Final[int] = 1000

# Valid file extensions by category
_RR_EXTENSIONS: Final[tuple[str, ...]] = (".txt", ".csv")
_SLEEP_EXTENSIONS: Final[tuple[str, ...]] = (".json", ".csv", ".edf")
_ACTIVITY_EXTENSIONS: Final[tuple[str, ...]] = (".json", ".csv", ".gt3x", ".agd")
_DEVICE_EXTENSIONS: Final[tuple[str, ...]] = (".zip", ".fit", ".edf", ".gt3x", ".agd")


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class UserInfo:
    """User identification and profile information.

    Attributes:
        user_id: Unique identifier (e.g., cedula, medical record number).
        name: Full name.
        age: Age in years (optional).
        sex: Biological sex (M/F/Other).
        email: Contact email (optional).
        created_at: Account creation timestamp.
        last_access: Last access timestamp.
        notes: Additional notes.
        preferences: User preferences dict.
    """

    user_id: str
    name: str
    age: int | None = None
    sex: str = "Other"
    email: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))
    last_access: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))
    notes: str = ""
    preferences: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SessionRecord:
    """Record of a single analysis session.

    Attributes:
        session_id: Unique session identifier.
        timestamp: Session timestamp.
        files_loaded: List of files loaded in session.
        metrics_computed: List of computed metrics.
        export_files: List of exported files.
        notes: Session notes.
    """

    session_id: str
    timestamp: datetime
    files_loaded: list[str] = field(default_factory=list)
    metrics_computed: list[str] = field(default_factory=list)
    export_files: list[str] = field(default_factory=list)
    notes: str = ""


@dataclass(slots=True)
class UserDataSummary:
    """Summary of user's stored data.

    Attributes:
        user_id: User identifier.
        name: User name.
        total_rr_files: Number of RR interval files.
        total_sleep_files: Number of sleep data files.
        total_activity_files: Number of activity data files.
        date_range_start: Earliest data date.
        date_range_end: Latest data date.
        total_sessions: Number of analysis sessions.
        last_session: Last session timestamp.
        data_size_mb: Total data size in MB.
    """

    user_id: str
    name: str
    total_rr_files: int = 0
    total_sleep_files: int = 0
    total_activity_files: int = 0
    date_range_start: date | None = None
    date_range_end: date | None = None
    total_sessions: int = 0
    last_session: datetime | None = None
    data_size_mb: float = 0.0


class LoadedDataBundle(TypedDict, total=False):
    """Bundle of loaded user data."""

    rr_files: dict[str, np.ndarray]
    sleep_data: list[dict[str, Any]]
    activity_data: list[dict[str, Any]]
    device_data: list[dict[str, Any]]
    hrv_results: list[dict[str, Any]]
    warnings: list[str]


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def sanitize_user_id(user_id: str) -> str:
    """Sanitize user ID for safe filesystem use.

    Args:
        user_id: Raw user ID input.

    Returns:
        Sanitized user ID safe for filesystem.
    """
    # Remove dangerous characters, keep alphanumeric and some safe chars
    sanitized = re.sub(r"[^\w\-.]", "_", str(user_id).strip())
    # Limit length
    if len(sanitized) > 50:
        # Use hash for long IDs
        hash_suffix = hashlib.md5(sanitized.encode()).hexdigest()[:8]
        sanitized = sanitized[:40] + "_" + hash_suffix
    return sanitized or "anonymous"


def get_user_data_path(user_id: str, base_path: Path | None = None) -> Path:
    """Get the data folder path for a user.

    Args:
        user_id: User identifier.
        base_path: Base data path (defaults to ./data).

    Returns:
        Path to user's data folder.
    """
    if base_path is None:
        base_path = Path(_DATA_ROOT)
    safe_id = sanitize_user_id(user_id)
    return base_path / safe_id


def ensure_user_directories(user_path: Path) -> dict[str, Path]:
    """Create user data directory structure.

    Args:
        user_path: Base user data path.

    Returns:
        Dictionary of category -> path mappings.
    """
    directories = {
        "root": user_path,
        "rr": user_path / _RR_DATA_DIR,
        "sleep": user_path / _SLEEP_DATA_DIR,
        "activity": user_path / _ACTIVITY_DATA_DIR,
        "hrv_results": user_path / _HRV_RESULTS_DIR,
        "device": user_path / _DEVICE_DATA_DIR,
    }

    for path in directories.values():
        path.mkdir(parents=True, exist_ok=True)

    return directories


def parse_filename_date(filename: str) -> date | None:
    """Extract date from filename using common patterns.

    Args:
        filename: Filename to parse.

    Returns:
        Extracted date or None if not found.
    """
    # Pattern: YYYY-MM-DD or YYYY_MM_DD
    patterns = [
        r"(\d{4})-(\d{2})-(\d{2})",
        r"(\d{4})_(\d{2})_(\d{2})",
        r"(\d{4})(\d{2})(\d{2})",  # YYYYMMDD
    ]

    for pattern in patterns:
        match = re.search(pattern, filename)
        if match:
            try:
                return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
            except ValueError:
                continue
    return None


# ---------------------------------------------------------------------------
# UserDataManager class
# ---------------------------------------------------------------------------


class UserDataManager:
    """Manager for user data persistence and retrieval."""

    def __init__(
        self,
        base_path: Path | None = None,
        auto_create_dirs: bool = True,
    ) -> None:
        """Initialize UserDataManager.

        Args:
            base_path: Base data folder path (default: ./data).
            auto_create_dirs: Automatically create directories.
        """
        self._base_path = Path(base_path) if base_path else Path(_DATA_ROOT)
        self._auto_create = auto_create_dirs
        self._current_user: UserInfo | None = None
        self._current_user_path: Path | None = None

        if self._auto_create:
            self._base_path.mkdir(parents=True, exist_ok=True)

    # -----------------------------------------------------------------------
    # User management
    # -----------------------------------------------------------------------

    def set_current_user(
        self,
        user_id: str,
        name: str = "",
        age: int | None = None,
        sex: str = "Other",
        create_if_missing: bool = True,
    ) -> UserInfo:
        """Set or create current user.

        Args:
            user_id: Unique user identifier.
            name: User's full name.
            age: User's age (optional).
            sex: User's sex (optional).
            create_if_missing: Create user if not exists.

        Returns:
            UserInfo for the current user.

        Raises:
            FileNotFoundError: If user doesn't exist and create_if_missing=False.
        """
        user_path = get_user_data_path(user_id, self._base_path)
        info_file = user_path / _USER_INFO_FILE

        if info_file.exists():
            # Load existing user
            user_info = self._load_user_info(info_file)
            user_info.last_access = datetime.now(tz=timezone.utc)
            # Update name/age/sex if provided
            if name:
                user_info.name = name
            if age is not None:
                user_info.age = age
            if sex != "Other":
                user_info.sex = sex
            self._save_user_info(user_info, info_file)
        elif create_if_missing:
            # Create new user
            if self._auto_create:
                ensure_user_directories(user_path)
            user_info = UserInfo(
                user_id=user_id,
                name=name or f"User {user_id}",
                age=age,
                sex=sex,
            )
            self._save_user_info(user_info, info_file)
            _LOGGER.info("Created new user: %s", user_id)
        else:
            msg = f"User not found: {user_id}"
            raise FileNotFoundError(msg)

        self._current_user = user_info
        self._current_user_path = user_path
        return user_info

    def get_current_user(self) -> UserInfo | None:
        """Get current user info."""
        return self._current_user

    def list_users(self) -> list[UserDataSummary]:
        """List all users with data summaries.

        Returns:
            List of UserDataSummary for each user.
        """
        summaries: list[UserDataSummary] = []

        if not self._base_path.exists():
            return summaries

        for user_dir in self._base_path.iterdir():
            if not user_dir.is_dir():
                continue

            info_file = user_dir / _USER_INFO_FILE
            if not info_file.exists():
                continue

            try:
                user_info = self._load_user_info(info_file)
                summary = self._compute_user_summary(user_info, user_dir)
                summaries.append(summary)
            except Exception as exc:
                _LOGGER.warning("Failed to load user %s: %s", user_dir.name, exc)

        return sorted(summaries, key=lambda s: s.last_session or datetime.min, reverse=True)

    def delete_user(self, user_id: str, confirm: bool = False) -> bool:
        """Delete user and all associated data.

        Args:
            user_id: User identifier to delete.
            confirm: Must be True to proceed with deletion.

        Returns:
            True if deleted, False otherwise.
        """
        if not confirm:
            _LOGGER.warning("Delete not confirmed for user %s", user_id)
            return False

        user_path = get_user_data_path(user_id, self._base_path)
        if not user_path.exists():
            return False

        try:
            shutil.rmtree(user_path)
            if self._current_user and self._current_user.user_id == user_id:
                self._current_user = None
                self._current_user_path = None
            _LOGGER.info("Deleted user: %s", user_id)
            return True
        except Exception as exc:
            _LOGGER.error("Failed to delete user %s: %s", user_id, exc)
            return False

    # -----------------------------------------------------------------------
    # Data storage
    # -----------------------------------------------------------------------

    def store_rr_intervals(
        self,
        rr_ms: np.ndarray,
        filename: str,
        recording_date: date | None = None,
        overwrite: bool = False,
    ) -> Path:
        """Store RR interval data for current user.

        Args:
            rr_ms: Array of RR intervals in milliseconds.
            filename: Original filename or descriptive name.
            recording_date: Date of recording (extracted from filename if None).
            overwrite: Overwrite existing file.

        Returns:
            Path to stored file.

        Raises:
            RuntimeError: If no current user set.
            FileExistsError: If file exists and overwrite=False.
        """
        if self._current_user_path is None:
            msg = "No current user set. Call set_current_user() first."
            raise RuntimeError(msg)

        rr_dir = self._current_user_path / _RR_DATA_DIR

        # Ensure directory exists
        rr_dir.mkdir(parents=True, exist_ok=True)

        # Parse or use provided date
        file_date = recording_date or parse_filename_date(filename) or date.today()

        # Create safe filename
        safe_name = sanitize_user_id(Path(filename).stem)
        target_file = rr_dir / f"{file_date.isoformat()}_{safe_name}.txt"

        if target_file.exists() and not overwrite:
            msg = f"File already exists: {target_file}"
            raise FileExistsError(msg)

        # Save as text file (one value per line)
        np.savetxt(target_file, rr_ms, fmt="%d")
        _LOGGER.info("Stored RR intervals: %s (%d values)", target_file, len(rr_ms))

        return target_file

    def store_sleep_data(
        self,
        sleep_data: dict[str, Any],
        recording_date: date,
        source: str = "unknown",
        overwrite: bool = False,
    ) -> Path:
        """Store sleep data for current user.

        Args:
            sleep_data: Dictionary with sleep metrics and staging.
            recording_date: Date of sleep (night starting).
            source: Data source identifier.
            overwrite: Overwrite existing file.

        Returns:
            Path to stored file.

        Raises:
            RuntimeError: If no current user set.
        """
        if self._current_user_path is None:
            msg = "No current user set. Call set_current_user() first."
            raise RuntimeError(msg)

        sleep_dir = self._current_user_path / _SLEEP_DATA_DIR
        sleep_dir.mkdir(parents=True, exist_ok=True)

        target_file = sleep_dir / f"{recording_date.isoformat()}_{source}.json"

        if target_file.exists() and not overwrite:
            # Append to existing
            _LOGGER.info("Sleep data already exists for %s, skipping", recording_date)
            return target_file

        # Add metadata
        sleep_data["_recording_date"] = recording_date.isoformat()
        sleep_data["_source"] = source
        sleep_data["_stored_at"] = datetime.now(tz=timezone.utc).isoformat()

        with open(target_file, "w", encoding="utf-8") as f:
            json.dump(sleep_data, f, indent=2, default=str)

        _LOGGER.info("Stored sleep data: %s", target_file)
        return target_file

    def store_activity_data(
        self,
        activity_data: dict[str, Any],
        recording_date: date,
        source: str = "unknown",
        overwrite: bool = False,
    ) -> Path:
        """Store activity data for current user.

        Args:
            activity_data: Dictionary with activity metrics.
            recording_date: Date of activity.
            source: Data source identifier.
            overwrite: Overwrite existing file.

        Returns:
            Path to stored file.
        """
        if self._current_user_path is None:
            msg = "No current user set. Call set_current_user() first."
            raise RuntimeError(msg)

        activity_dir = self._current_user_path / _ACTIVITY_DATA_DIR
        activity_dir.mkdir(parents=True, exist_ok=True)

        target_file = activity_dir / f"{recording_date.isoformat()}_{source}.json"

        if target_file.exists() and not overwrite:
            return target_file

        activity_data["_recording_date"] = recording_date.isoformat()
        activity_data["_source"] = source
        activity_data["_stored_at"] = datetime.now(tz=timezone.utc).isoformat()

        with open(target_file, "w", encoding="utf-8") as f:
            json.dump(activity_data, f, indent=2, default=str)

        _LOGGER.info("Stored activity data: %s", target_file)
        return target_file

    def store_hrv_results(
        self,
        hrv_metrics: dict[str, Any],
        recording_date: date,
        source_file: str = "",
    ) -> Path:
        """Store computed HRV results for current user.

        Args:
            hrv_metrics: Dictionary with computed HRV metrics.
            recording_date: Date of recording.
            source_file: Source filename.

        Returns:
            Path to stored file.
        """
        if self._current_user_path is None:
            msg = "No current user set. Call set_current_user() first."
            raise RuntimeError(msg)

        results_dir = self._current_user_path / _HRV_RESULTS_DIR
        results_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now(tz=timezone.utc).strftime("%H%M%S")
        target_file = results_dir / f"{recording_date.isoformat()}_{timestamp}_hrv.json"

        hrv_metrics["_recording_date"] = recording_date.isoformat()
        hrv_metrics["_source_file"] = source_file
        hrv_metrics["_computed_at"] = datetime.now(tz=timezone.utc).isoformat()

        with open(target_file, "w", encoding="utf-8") as f:
            json.dump(hrv_metrics, f, indent=2, default=str)

        _LOGGER.info("Stored HRV results: %s", target_file)
        return target_file

    def store_device_file(
        self,
        file_content: bytes,
        filename: str,
        device_type: str = "unknown",
    ) -> Path:
        """Store raw device file for current user.

        Args:
            file_content: Raw file bytes.
            filename: Original filename.
            device_type: Device type (garmin, actigraph, somfit).

        Returns:
            Path to stored file.
        """
        if self._current_user_path is None:
            msg = "No current user set. Call set_current_user() first."
            raise RuntimeError(msg)

        device_dir = self._current_user_path / _DEVICE_DATA_DIR / device_type
        device_dir.mkdir(parents=True, exist_ok=True)

        target_file = device_dir / filename

        # Don't overwrite - add timestamp if exists
        if target_file.exists():
            stem = Path(filename).stem
            suffix = Path(filename).suffix
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            target_file = device_dir / f"{stem}_{timestamp}{suffix}"

        with open(target_file, "wb") as f:
            f.write(file_content)

        _LOGGER.info("Stored device file: %s", target_file)
        return target_file

    # -----------------------------------------------------------------------
    # Data loading
    # -----------------------------------------------------------------------

    def load_all_user_data(
        self,
        date_start: date | None = None,
        date_end: date | None = None,
    ) -> LoadedDataBundle:
        """Load all available data for current user.

        Args:
            date_start: Optional start date filter.
            date_end: Optional end date filter.

        Returns:
            LoadedDataBundle with all available data.
        """
        if self._current_user_path is None:
            return LoadedDataBundle(warnings=["No current user set"])

        bundle: LoadedDataBundle = {
            "rr_files": {},
            "sleep_data": [],
            "activity_data": [],
            "device_data": [],
            "hrv_results": [],
            "warnings": [],
        }

        # Load RR interval files
        try:
            bundle["rr_files"] = self._load_rr_files(date_start, date_end)
        except Exception as exc:
            bundle["warnings"].append(f"Error loading RR files: {exc}")

        # Load sleep data
        try:
            bundle["sleep_data"] = self._load_json_data(
                self._current_user_path / _SLEEP_DATA_DIR,
                date_start,
                date_end,
            )
        except Exception as exc:
            bundle["warnings"].append(f"Error loading sleep data: {exc}")

        # Load activity data
        try:
            bundle["activity_data"] = self._load_json_data(
                self._current_user_path / _ACTIVITY_DATA_DIR,
                date_start,
                date_end,
            )
        except Exception as exc:
            bundle["warnings"].append(f"Error loading activity data: {exc}")

        # Load HRV results
        try:
            bundle["hrv_results"] = self._load_json_data(
                self._current_user_path / _HRV_RESULTS_DIR,
                date_start,
                date_end,
            )
        except Exception as exc:
            bundle["warnings"].append(f"Error loading HRV results: {exc}")

        return bundle

    def load_rr_files_as_dict(
        self,
        date_start: date | None = None,
        date_end: date | None = None,
    ) -> dict[str, np.ndarray]:
        """Load RR interval files for current user.

        Args:
            date_start: Optional start date filter.
            date_end: Optional end date filter.

        Returns:
            Dictionary of filename -> RR intervals array.
        """
        if self._current_user_path is None:
            return {}
        return self._load_rr_files(date_start, date_end)

    def get_device_files(self, device_type: str | None = None) -> list[Path]:
        """Get list of stored device files.

        Args:
            device_type: Filter by device type (garmin, actigraph, somfit).

        Returns:
            List of device file paths.
        """
        if self._current_user_path is None:
            return []

        device_dir = self._current_user_path / _DEVICE_DATA_DIR

        if not device_dir.exists():
            return []

        files: list[Path] = []

        if device_type:
            type_dir = device_dir / device_type
            if type_dir.exists():
                for ext in _DEVICE_EXTENSIONS:
                    files.extend(type_dir.glob(f"*{ext}"))
        else:
            for type_dir in device_dir.iterdir():
                if type_dir.is_dir():
                    for ext in _DEVICE_EXTENSIONS:
                        files.extend(type_dir.glob(f"*{ext}"))

        return sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)

    # -----------------------------------------------------------------------
    # Session management
    # -----------------------------------------------------------------------

    def record_session(
        self,
        files_loaded: list[str],
        metrics_computed: list[str] | None = None,
        notes: str = "",
    ) -> SessionRecord:
        """Record an analysis session.

        Args:
            files_loaded: List of files analyzed.
            metrics_computed: List of computed metrics.
            notes: Session notes.

        Returns:
            SessionRecord for this session.
        """
        if self._current_user_path is None:
            msg = "No current user set"
            raise RuntimeError(msg)

        session = SessionRecord(
            session_id=datetime.now().strftime("%Y%m%d_%H%M%S"),
            timestamp=datetime.now(tz=timezone.utc),
            files_loaded=files_loaded,
            metrics_computed=metrics_computed or [],
            notes=notes,
        )

        # Load existing sessions
        sessions_file = self._current_user_path / _SESSION_FILE
        sessions: list[dict[str, Any]] = []

        if sessions_file.exists():
            try:
                with open(sessions_file, encoding="utf-8") as f:
                    sessions = json.load(f)
            except json.JSONDecodeError:
                sessions = []

        # Add new session
        sessions.append({
            "session_id": session.session_id,
            "timestamp": session.timestamp.isoformat(),
            "files_loaded": session.files_loaded,
            "metrics_computed": session.metrics_computed,
            "notes": session.notes,
        })

        # Keep last 100 sessions
        sessions = sessions[-100:]

        with open(sessions_file, "w", encoding="utf-8") as f:
            json.dump(sessions, f, indent=2)

        return session

    def get_sessions(self, limit: int = 10) -> list[SessionRecord]:
        """Get recent analysis sessions.

        Args:
            limit: Maximum sessions to return.

        Returns:
            List of recent SessionRecords.
        """
        if self._current_user_path is None:
            return []

        sessions_file = self._current_user_path / _SESSION_FILE
        if not sessions_file.exists():
            return []

        try:
            with open(sessions_file, encoding="utf-8") as f:
                sessions_data = json.load(f)
        except json.JSONDecodeError:
            return []

        sessions: list[SessionRecord] = []
        for data in reversed(sessions_data[-limit:]):
            sessions.append(SessionRecord(
                session_id=data.get("session_id", ""),
                timestamp=datetime.fromisoformat(data.get("timestamp", "")),
                files_loaded=data.get("files_loaded", []),
                metrics_computed=data.get("metrics_computed", []),
                notes=data.get("notes", ""),
            ))

        return sessions

    # -----------------------------------------------------------------------
    # Private methods
    # -----------------------------------------------------------------------

    def _load_user_info(self, info_file: Path) -> UserInfo:
        """Load user info from JSON file."""
        with open(info_file, encoding="utf-8") as f:
            data = json.load(f)

        return UserInfo(
            user_id=data.get("user_id", "unknown"),
            name=data.get("name", "Unknown"),
            age=data.get("age"),
            sex=data.get("sex", "Other"),
            email=data.get("email", ""),
            created_at=datetime.fromisoformat(data.get("created_at", datetime.now(tz=timezone.utc).isoformat())),
            last_access=datetime.fromisoformat(data.get("last_access", datetime.now(tz=timezone.utc).isoformat())),
            notes=data.get("notes", ""),
            preferences=data.get("preferences", {}),
        )

    def _save_user_info(self, user_info: UserInfo, info_file: Path) -> None:
        """Save user info to JSON file."""
        info_file.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "user_id": user_info.user_id,
            "name": user_info.name,
            "age": user_info.age,
            "sex": user_info.sex,
            "email": user_info.email,
            "created_at": user_info.created_at.isoformat(),
            "last_access": user_info.last_access.isoformat(),
            "notes": user_info.notes,
            "preferences": user_info.preferences,
        }

        with open(info_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def _compute_user_summary(self, user_info: UserInfo, user_path: Path) -> UserDataSummary:
        """Compute summary statistics for a user."""
        summary = UserDataSummary(
            user_id=user_info.user_id,
            name=user_info.name,
        )

        # Count files
        rr_dir = user_path / _RR_DATA_DIR
        if rr_dir.exists():
            summary.total_rr_files = sum(1 for _ in rr_dir.glob("*.txt"))

        sleep_dir = user_path / _SLEEP_DATA_DIR
        if sleep_dir.exists():
            summary.total_sleep_files = sum(1 for _ in sleep_dir.glob("*.json"))

        activity_dir = user_path / _ACTIVITY_DATA_DIR
        if activity_dir.exists():
            summary.total_activity_files = sum(1 for _ in activity_dir.glob("*.json"))

        # Date range from filenames
        all_dates: list[date] = []
        for subdir in [rr_dir, sleep_dir, activity_dir]:
            if subdir.exists():
                for f in subdir.iterdir():
                    d = parse_filename_date(f.name)
                    if d:
                        all_dates.append(d)

        if all_dates:
            summary.date_range_start = min(all_dates)
            summary.date_range_end = max(all_dates)

        # Sessions
        sessions_file = user_path / _SESSION_FILE
        if sessions_file.exists():
            try:
                with open(sessions_file, encoding="utf-8") as f:
                    sessions = json.load(f)
                summary.total_sessions = len(sessions)
                if sessions:
                    summary.last_session = datetime.fromisoformat(sessions[-1].get("timestamp", ""))
            except Exception:
                pass

        # Data size
        total_size = sum(f.stat().st_size for f in user_path.rglob("*") if f.is_file())
        summary.data_size_mb = total_size / (1024 * 1024)

        return summary

    def _load_rr_files(
        self,
        date_start: date | None,
        date_end: date | None,
    ) -> dict[str, np.ndarray]:
        """Load RR interval files."""
        if self._current_user_path is None:
            return {}

        rr_dir = self._current_user_path / _RR_DATA_DIR
        if not rr_dir.exists():
            return {}

        result: dict[str, np.ndarray] = {}
        count = 0

        for ext in _RR_EXTENSIONS:
            for f in sorted(rr_dir.glob(f"*{ext}")):
                if count >= _MAX_FILES_PER_CATEGORY:
                    break

                # Check date filter
                file_date = parse_filename_date(f.name)
                if file_date:
                    if date_start and file_date < date_start:
                        continue
                    if date_end and file_date > date_end:
                        continue

                try:
                    rr_data = np.loadtxt(f, dtype=float)
                    # Filter valid RR values
                    rr_data = rr_data[(rr_data >= 300) & (rr_data <= 2000)]
                    if len(rr_data) >= 10:
                        result[f.name] = rr_data
                        count += 1
                except Exception as exc:
                    _LOGGER.warning("Failed to load %s: %s", f.name, exc)

        return result

    def _load_json_data(
        self,
        data_dir: Path,
        date_start: date | None,
        date_end: date | None,
    ) -> list[dict[str, Any]]:
        """Load JSON data files."""
        if not data_dir.exists():
            return []

        result: list[dict[str, Any]] = []
        count = 0

        for f in sorted(data_dir.glob("*.json")):
            if count >= _MAX_FILES_PER_CATEGORY:
                break

            # Check date filter
            file_date = parse_filename_date(f.name)
            if file_date:
                if date_start and file_date < date_start:
                    continue
                if date_end and file_date > date_end:
                    continue

            try:
                with open(f, encoding="utf-8") as fp:
                    data = json.load(fp)
                    data["_filename"] = f.name
                    result.append(data)
                    count += 1
            except Exception as exc:
                _LOGGER.warning("Failed to load %s: %s", f.name, exc)

        return result


# ---------------------------------------------------------------------------
# Convenience functions
# ---------------------------------------------------------------------------


def create_user_manager(base_path: str | Path | None = None) -> UserDataManager:
    """Create a UserDataManager instance.

    Args:
        base_path: Optional base path for data storage.

    Returns:
        Configured UserDataManager.
    """
    return UserDataManager(
        base_path=Path(base_path) if base_path else None,
        auto_create_dirs=True,
    )


def get_or_create_user(
    manager: UserDataManager,
    user_id: str,
    name: str = "",
    age: int | None = None,
    sex: str = "Other",
) -> UserInfo:
    """Get or create a user.

    Args:
        manager: UserDataManager instance.
        user_id: User identifier.
        name: User name.
        age: User age.
        sex: User sex.

    Returns:
        UserInfo for the user.
    """
    return manager.set_current_user(
        user_id=user_id,
        name=name,
        age=age,
        sex=sex,
        create_if_missing=True,
    )


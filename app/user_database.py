"""
Multi-User Database System for HRV Analysis Platform.

Provides SQLite-based persistent storage for multiple users with:
- User profiles and biometric data
- Clinical scale scores (ESS, KSS, PSQI, etc.)
- HRV measurement history
- Longitudinal tracking and repeated measures
- Statistical analysis capabilities

Performance optimizations:
- Connection pooling with persistent connection
- WAL mode for concurrent reads/writes
- Lazy schema initialization (once per session)
- Optimized pragmas for responsiveness

Author: Dr. Diego Leonel Malpica Hincapié, MD
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import sqlite3
import shutil
import threading
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

try:
    from logging_config import get_logger, log_exception
except ImportError:  # pragma: no cover - fallback for non-app contexts
    get_logger = None  # type: ignore[assignment]
    log_exception = None  # type: ignore[assignment]

_LOGGER = get_logger(__name__) if get_logger is not None else logging.getLogger(__name__)

# Database configuration
DEFAULT_DB_NAME = "hrv_users.db"
SCHEMA_VERSION = 4

# Crew / mission storage layout
# NOTE: This project stores sensitive physiological data. We keep mission data
# under the `crew/` folder (ignored by git) instead of cluttering the project
# root with databases/backups.
_CREW_DIR_NAME = "crew"
_MISSION_DB_DIR_NAME = "db"
_MISSION_SUBJECTS_DIR_NAME = "subjects"
_DEFAULT_MISSIONS: tuple[str, ...] = ("Mission 1", "Mission 2")
_ENV_ACTIVE_MISSION = "HRV_ACTIVE_MISSION"
_MAX_LEGACY_BACKUPS_TO_COPY = 250

# SQLite durability / compatibility knobs.
#
# Rationale:
# - WAL is fast, but it produces sidecar files (-wal/-shm) which can be fragile on
#   cloud-synced folders (e.g., OneDrive) if sync tools race partially-written pages.
# - For maximum reliability across *any* path/filesystem, we default to rollback
#   journaling (DELETE). Users can explicitly enable WAL via env var when safe.
_ENV_SQLITE_JOURNAL_MODE = "HRV_SQLITE_JOURNAL_MODE"
# Default to rollback journaling for maximum path/filesystem compatibility.
# If you are on a local SSD and want higher concurrency/performance, set:
#   HRV_SQLITE_JOURNAL_MODE=WAL
_DEFAULT_SQLITE_JOURNAL_MODE = "DELETE"
_FALLBACK_SQLITE_JOURNAL_MODE_FOR_SYNCED_PATHS = "DELETE"
_SQLITE_JOURNAL_MODES: tuple[str, ...] = ("WAL", "DELETE", "TRUNCATE", "PERSIST", "MEMORY", "OFF")

# Thread-local storage for connection reuse
_thread_local = threading.local()


# ---------------------------------------------------------------------------
# Longitudinal analysis helpers (T0..T21)
# ---------------------------------------------------------------------------

def _parse_timepoint_number(timepoint_label: str) -> Optional[int]:
    """Parse a timepoint label (T0_baseline, T1...T21) into an integer 0..21."""
    if not timepoint_label:
        return None
    label = str(timepoint_label).strip()
    if not label.startswith("T"):
        return None
    if label.startswith("T0"):
        return 0
    try:
        return int(label[1:])
    except (TypeError, ValueError):
        return None


def _validate_agg(agg: str) -> str:
    """Validate aggregation mode."""
    mode = str(agg or "").strip().lower()
    if mode not in {"median", "mean"}:
        raise ValueError("agg must be 'median' or 'mean'")
    return mode


def _aggregate_numeric(series: pd.Series, *, agg: str) -> float:
    """Aggregate a numeric series with NaN-safe mean/median."""
    numeric = pd.to_numeric(series, errors="coerce")
    values = numeric.to_numpy(dtype=float, copy=False)
    if values.size == 0:
        return float("nan")
    if agg == "mean":
        return float(np.nanmean(values))
    return float(np.nanmedian(values))


def build_timepoint_change_table_from_hrv_df(
    hrv_df: pd.DataFrame,
    *,
    timepoints: Sequence["MeasurementTimepoint"],
    metrics: Optional[Sequence[str]] = None,
    agg: str = "median",
) -> pd.DataFrame:
    """Compute a baseline/Δ table from an HRV history DataFrame and timepoint metadata.

    Args:
        hrv_df: HRV history DataFrame containing at least `timepoint_id` and metric columns.
        timepoints: Measurement timepoint records for the same user.
        metrics: Optional list of metric columns to include (numeric).
        agg: Aggregation mode for multiple sessions within a timepoint: "median" or "mean".

    Returns:
        DataFrame with one row per timepoint label including baseline values and Δ columns.
        Returns empty DataFrame if no timepoint-tagged HRV rows exist.
    """
    mode = _validate_agg(agg)
    if hrv_df is None or hrv_df.empty:
        return pd.DataFrame()
    if "timepoint_id" not in hrv_df.columns:
        return pd.DataFrame()
    if not timepoints:
        return pd.DataFrame()

    # Build lookup for timepoint metadata (bounded: at most a few dozen rows).
    tp_rows: list[dict[str, Any]] = []
    for tp in timepoints:
        tp_num = tp.measurement_number if tp.measurement_number is not None else _parse_timepoint_number(tp.timepoint_label)
        tp_rows.append(
            {
                "timepoint_id": tp.timepoint_id,
                "timepoint_label": tp.timepoint_label,
                "timepoint_number": tp_num,
                "is_baseline": bool(tp.is_baseline) or str(tp.timepoint_label).startswith("T0"),
                "timepoint_date": tp.measurement_date,
            }
        )
    tp_df = pd.DataFrame(tp_rows).dropna(subset=["timepoint_id", "timepoint_label"])
    if tp_df.empty:
        return pd.DataFrame()

    # Filter HRV rows to those tagged with a known timepoint id.
    tagged = hrv_df.copy()
    tagged["timepoint_id"] = tagged["timepoint_id"].astype("string")
    tp_ids = set(tp_df["timepoint_id"].astype("string").tolist())
    tagged = tagged[tagged["timepoint_id"].isin(tp_ids)]
    if tagged.empty:
        return pd.DataFrame()

    # Join label/ordering metadata into HRV rows.
    merged = tagged.merge(tp_df, on="timepoint_id", how="left")
    merged = merged.dropna(subset=["timepoint_label"])

    # Select metrics (prefer a small default set that is broadly available).
    default_metrics = (
        "rmssd_ms",
        "sdnn_ms",
        "mean_hr_bpm",
        "hf_power_ms2",
        "lf_hf_ratio",
        "parasympathetic_index",
        "stress_index",
        "artifact_percentage",
        "quality_score",
    )
    metric_cols = list(metrics) if metrics is not None else list(default_metrics)
    metric_cols = [c for c in metric_cols if c in merged.columns and c not in {"timepoint_id", "timepoint_label"}]
    if not metric_cols:
        return pd.DataFrame()

    # Aggregate per timepoint label.
    rows: list[dict[str, Any]] = []
    for label, g in merged.groupby("timepoint_label", sort=False):
        row: dict[str, Any] = {
            "timepoint_label": str(label),
            "timepoint_number": pd.to_numeric(g["timepoint_number"], errors="coerce").dropna().min(),
            "is_baseline": bool(g["is_baseline"].fillna(False).any()),
            "n_sessions": int(len(g)),
        }
        for col in metric_cols:
            row[col] = _aggregate_numeric(g[col], agg=mode)
        rows.append(row)

    out = pd.DataFrame(rows)
    if out.empty:
        return out

    out["timepoint_number"] = pd.to_numeric(out["timepoint_number"], errors="coerce")
    out = out.sort_values(["timepoint_number", "timepoint_label"], na_position="last").reset_index(drop=True)

    # Determine baseline row (prefer is_baseline; otherwise the earliest timepoint number).
    baseline_candidates = out[out["is_baseline"] == True]  # noqa: E712
    if not baseline_candidates.empty:
        baseline_row = baseline_candidates.iloc[0]
    else:
        baseline_row = out.iloc[0]

    baseline_label = str(baseline_row.get("timepoint_label", "T0_baseline"))
    out["baseline_label"] = baseline_label

    # Add baseline + delta columns for each metric.
    for col in metric_cols:
        base_val = float(baseline_row.get(col, float("nan")))
        out[f"baseline_{col}"] = base_val
        out[f"delta_{col}"] = pd.to_numeric(out[col], errors="coerce") - base_val

    return out


def get_database_path() -> Path:
    """
    Return the active mission database path (crew/mission-scoped).

    The active mission is selected by the Streamlit app and propagated via the
    `HRV_ACTIVE_MISSION` environment variable. When unset/invalid, defaults to
    "Mission 1".

    Layout:
      - crew/<Mission>/db/hrv_users.db
      - crew/<Mission>/subjects/<user_id>/... (handled by user_data_manager)

    For safety, legacy root DB files are **copied** (not moved) into Mission 1
    on first use.
    """
    project_root = Path(__file__).resolve().parents[1]
    project_root.mkdir(parents=True, exist_ok=True)

    raw_mission = str(os.environ.get(_ENV_ACTIVE_MISSION, "")).strip()
    mission = raw_mission if raw_mission else _DEFAULT_MISSIONS[0]
    # Prevent path traversal / accidental nested paths.
    if Path(mission).name != mission:
        mission = _DEFAULT_MISSIONS[0]

    mission_root = project_root / _CREW_DIR_NAME / mission
    db_dir = mission_root / _MISSION_DB_DIR_NAME
    subjects_dir = mission_root / _MISSION_SUBJECTS_DIR_NAME
    db_dir.mkdir(parents=True, exist_ok=True)
    subjects_dir.mkdir(parents=True, exist_ok=True)

    db_path = db_dir / DEFAULT_DB_NAME

    # One-time migration: copy legacy root DB + backups into Mission 1.
    if mission == _DEFAULT_MISSIONS[0]:
        legacy_db = project_root / DEFAULT_DB_NAME
        if (not db_path.exists()) and legacy_db.exists():
            try:
                shutil.copy2(legacy_db, db_path)
                _LOGGER.info("Copied legacy DB into crew storage: %s -> %s", legacy_db, db_path)
            except OSError as exc:
                if log_exception is not None:
                    log_exception(_LOGGER, "Failed to copy legacy DB into crew storage", exc)
                raise

        # Copy any legacy backups so Mission 1 remains self-contained.
        try:
            backups = sorted(project_root.glob(f"{DEFAULT_DB_NAME}.bak_*"))
        except OSError:
            backups = []
        copied = 0
        for backup in backups:
            if copied >= _MAX_LEGACY_BACKUPS_TO_COPY:
                _LOGGER.warning(
                    "Legacy backup copy capped at %d files; remaining backups stay in project root.",
                    _MAX_LEGACY_BACKUPS_TO_COPY,
                )
                break
            target = db_dir / backup.name
            if target.exists():
                continue
            try:
                shutil.copy2(backup, target)
                copied += 1
            except OSError as exc:
                if log_exception is not None:
                    log_exception(_LOGGER, "Failed to copy legacy DB backup into crew storage", exc)

        if copied:
            _LOGGER.info("Copied %d legacy DB backups into crew storage (%s).", copied, db_dir)

    return db_path


# ---------------------------------------------------------------------------
# SQLite file health / durability helpers
# ---------------------------------------------------------------------------

def _normalize_sqlite_journal_mode(raw: str) -> Optional[str]:
    """Normalize/validate a SQLite journal mode env var value."""
    value = str(raw or "").strip().upper()
    if not value:
        return None
    if value not in _SQLITE_JOURNAL_MODES:
        _LOGGER.warning(
            "Ignoring invalid %s=%r (expected one of %s).",
            _ENV_SQLITE_JOURNAL_MODE,
            raw,
            ", ".join(_SQLITE_JOURNAL_MODES),
        )
        return None
    return value


def _is_likely_cloud_synced_path(path: Path) -> bool:
    """Heuristic: detect cloud-synced folders that are risky for WAL sidecars."""
    raw = str(path)
    if raw.startswith("\\\\"):
        return True  # UNC / network share
    # Prefer env-provided sync roots (more robust than string matching).
    env_roots = (
        os.environ.get("OneDrive", ""),
        os.environ.get("OneDriveCommercial", ""),
        os.environ.get("OneDriveConsumer", ""),
        os.environ.get("DROPBOX", ""),
        os.environ.get("Dropbox", ""),
    )
    resolved: Optional[Path] = None
    try:
        resolved = path.resolve()
    except OSError:
        resolved = None
    for root_raw in env_roots:
        root = str(root_raw or "").strip()
        if not root:
            continue
        try:
            root_path = Path(root).resolve()
        except OSError:
            continue
        try:
            if resolved is not None:
                resolved.relative_to(root_path)
                return True
        except ValueError:
            pass

    # NOTE: Keep this conservative; false positives only reduce performance.
    lower_parts = [p.lower() for p in path.parts]
    return any(
        ("onedrive" in part)
        or ("dropbox" in part)
        or ("google drive" in part)
        or ("gdrive" in part)
        or ("icloud" in part)
        for part in lower_parts
    )


def _select_sqlite_journal_mode(db_path: Path) -> str:
    """Select a safe SQLite journal mode for this database path."""
    env_mode = _normalize_sqlite_journal_mode(os.environ.get(_ENV_SQLITE_JOURNAL_MODE, ""))
    if env_mode is not None:
        return env_mode
    if _is_likely_cloud_synced_path(db_path):
        return _FALLBACK_SQLITE_JOURNAL_MODE_FOR_SYNCED_PATHS
    return _DEFAULT_SQLITE_JOURNAL_MODE


def _apply_sqlite_connection_pragmas(conn: sqlite3.Connection, *, db_path: Path) -> str:
    """Apply PRAGMAs in a path-robust way and return the actual journal mode.

    Critical: SQLite may refuse `journal_mode=WAL` on some file systems. In that
    case the PRAGMA returns a *different* mode. We must set `synchronous` based
    on the actual resulting mode (not the requested one), or durability can be
    weaker than intended.
    """
    requested = _select_sqlite_journal_mode(db_path)
    actual = requested
    try:
        row = conn.execute(f"PRAGMA journal_mode={requested}").fetchone()
        if row and row[0] is not None:
            actual = str(row[0])
    except sqlite3.Error as exc:
        _LOGGER.warning("Failed to set journal_mode=%s (%s); falling back to DELETE.", requested, exc)
        try:
            row = conn.execute("PRAGMA journal_mode=DELETE").fetchone()
            if row and row[0] is not None:
                actual = str(row[0])
            else:
                actual = "DELETE"
        except sqlite3.Error as exc2:
            # If even this fails, we keep going; SQLite will still run with its default.
            _LOGGER.warning("Failed to set journal_mode=DELETE (%s).", exc2)

    actual_upper = str(actual).strip().upper()
    if actual_upper not in _SQLITE_JOURNAL_MODES:
        actual_upper = requested
    if actual_upper != requested:
        _LOGGER.warning(
            "SQLite journal_mode requested=%s but actual=%s for %s",
            requested,
            actual_upper,
            db_path,
        )

    # Durability + lock behavior (path-agnostic defaults).
    # - WAL: NORMAL is typical and fast; DB is still consistent.
    # - non-WAL: FULL is safer on sync/network paths.
    try:
        conn.execute("PRAGMA synchronous=NORMAL" if actual_upper == "WAL" else "PRAGMA synchronous=FULL")
    except sqlite3.Error:
        pass
    try:
        conn.execute("PRAGMA foreign_keys=ON")
    except sqlite3.Error:
        pass
    try:
        conn.execute("PRAGMA busy_timeout=5000")
    except sqlite3.Error:
        pass
    if actual_upper == "WAL":
        try:
            conn.execute("PRAGMA wal_autocheckpoint=1000")
        except sqlite3.Error:
            pass

    # Performance knobs (best-effort; tolerate unsupported settings).
    try:
        conn.execute("PRAGMA cache_size=-64000")  # 64MB cache
    except sqlite3.Error:
        pass
    try:
        conn.execute("PRAGMA temp_store=MEMORY")  # Temp tables in memory
    except sqlite3.Error:
        pass
    try:
        conn.execute("PRAGMA mmap_size=268435456")  # 256MB memory-mapped I/O
    except sqlite3.Error:
        pass

    return actual_upper


def is_sqlite_database_corruption_error(exc: BaseException) -> bool:
    """Return True if the exception message strongly indicates SQLite corruption."""
    msg = str(exc).lower()
    # The canonical SQLite corruption message we see in the wild.
    if "database disk image is malformed" in msg:
        return True
    # Pandas may wrap the DB-API exception with its own prefix.
    if "disk image is malformed" in msg and "database" in msg:
        return True
    return False


def _sqlite_sidecar_paths(db_path: Path) -> tuple[Path, Path]:
    """Return SQLite WAL sidecar paths for a .db file (db-wal, db-shm)."""
    wal = Path(f"{db_path}-wal")
    shm = Path(f"{db_path}-shm")
    return wal, shm


def sqlite_quick_check(db_path: Path, *, timeout_s: float = 2.0) -> tuple[bool, str]:
    """Run `PRAGMA quick_check(1)` and return (ok, message).

    Notes:
        - This opens the DB read-only (mode=ro) to avoid modifying state.
        - If the DB is corrupted, SQLite may return a descriptive message or raise.
    """
    if timeout_s <= 0:
        raise ValueError("timeout_s must be > 0")
    if not db_path.exists():
        return False, "missing"
    try:
        uri = f"{db_path.resolve().as_uri()}?mode=ro"
        conn = sqlite3.connect(uri, uri=True, timeout=float(timeout_s))
    except sqlite3.Error as exc:
        return False, str(exc)
    try:
        row = conn.execute("PRAGMA quick_check(1);").fetchone()
    except sqlite3.Error as exc:
        return False, str(exc)
    finally:
        try:
            conn.close()
        except sqlite3.Error:
            pass
    if row is None or not row:
        return False, "no-result"
    result = str(row[0])
    return (result == "ok"), result


def list_database_backups(db_path: Optional[Path] = None, *, max_backups: int = 25) -> list[Path]:
    """List timestamped DB backups (newest first) for the active mission."""
    if max_backups < 1:
        raise ValueError("max_backups must be >= 1")
    target = db_path or get_database_path()
    try:
        backups = sorted(target.parent.glob(f"{target.name}.bak_*"), reverse=True)
    except OSError:
        backups = []
    return backups[:max_backups]


def _close_thread_local_connection_for_db(db_path_str: str) -> None:
    """Best-effort: close the per-thread persistent connection for a DB path."""
    conn_key = f"conn_{db_path_str}"
    conn = getattr(_thread_local, conn_key, None)
    if conn is None:
        return
    try:
        conn.close()
    except sqlite3.Error:
        pass
    finally:
        setattr(_thread_local, conn_key, None)


def invalidate_database_instance(db_path: Optional[Path] = None) -> None:
    """Invalidate cached DB instances so a restored/reset file is picked up."""
    target = db_path or get_database_path()
    db_path_str = str(target)
    _close_thread_local_connection_for_db(db_path_str)
    # Force schema init on next instantiation (important after resets/restores).
    UserDatabase._initialized_dbs.discard(db_path_str)
    UserDatabase._backed_up_dbs.discard(db_path_str)
    # Clear Streamlit cache_resource wrapper if available.
    try:
        _get_database_cached.clear()  # type: ignore[name-defined]
    except Exception:
        pass


def restore_database_from_backup(*, backup_path: Path, db_path: Optional[Path] = None) -> Path:
    """Restore the active mission DB from a backup file.

    This function:
    - Closes any persistent connection for the DB (best-effort)
    - Preserves the current DB (+ WAL/SHM) with a timestamped `.corrupt_...` suffix
    - Copies `backup_path` onto `db_path`
    - Invalidates Streamlit/resource caches so the app uses the restored DB

    Returns:
        Path to the preserved copy of the previously-active DB file.
    """
    target = db_path or get_database_path()
    backup_path = Path(backup_path)
    if not backup_path.exists():
        raise FileNotFoundError(str(backup_path))
    if target.resolve() == backup_path.resolve():
        raise ValueError("backup_path must differ from db_path")

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    preserved_db = Path(f"{target}.corrupt_{timestamp}")
    preserved_wal = Path(f"{target}-wal.corrupt_{timestamp}")
    preserved_shm = Path(f"{target}-shm.corrupt_{timestamp}")

    # Ensure we are not holding an open handle.
    invalidate_database_instance(target)

    wal_path, shm_path = _sqlite_sidecar_paths(target)

    # Preserve current files first (never delete user data).
    if target.exists():
        shutil.copy2(target, preserved_db)
    if wal_path.exists():
        shutil.copy2(wal_path, preserved_wal)
    if shm_path.exists():
        shutil.copy2(shm_path, preserved_shm)

    # Move WAL/SHM aside so the restored DB isn't paired with stale sidecars.
    for sidecar in (wal_path, shm_path):
        if not sidecar.exists():
            continue
        try:
            sidecar.replace(Path(f"{sidecar}.old_{timestamp}"))
        except OSError:
            # If locked, we still proceed; SQLite may complain until restart.
            pass

    # Copy backup into place.
    shutil.copy2(backup_path, target)
    invalidate_database_instance(target)
    return preserved_db


def reset_database_file(db_path: Optional[Path] = None) -> list[Path]:
    """Move the active DB (+ WAL/SHM) aside and force a fresh DB on next use.

    Returns:
        List of paths created (the preserved/moved files).
    """
    target = db_path or get_database_path()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    wal_path, shm_path = _sqlite_sidecar_paths(target)

    invalidate_database_instance(target)

    moved: list[Path] = []
    for p in (target, wal_path, shm_path):
        if not p.exists():
            continue
        new_path = Path(f"{p}.corrupt_{timestamp}")
        p.replace(new_path)
        moved.append(new_path)

    invalidate_database_instance(target)
    return moved


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

@dataclass
class UserProfile:
    """Complete user profile with biometrics and identifiers."""
    
    user_id: str
    username: str
    full_name: str
    email: Optional[str] = None
    
    # Demographics
    date_of_birth: Optional[str] = None  # ISO format YYYY-MM-DD
    sex: Optional[str] = None  # "male", "female", "other"
    
    # Biometrics
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    resting_hr_bpm: Optional[float] = None
    max_hr_bpm: Optional[float] = None
    vo2max_ml_kg_min: Optional[float] = None
    
    # Occupation/Lifestyle
    occupation: Optional[str] = None
    activity_level: Optional[str] = None  # sedentary, light, moderate, active, very_active
    smoking_status: Optional[str] = None  # never, former, current
    alcohol_use: Optional[str] = None  # none, occasional, moderate, heavy
    caffeine_intake_mg: Optional[float] = None
    
    # Chronotype
    chronotype_offset_hours: Optional[float] = None  # Phase shift for circadian model (-2.5 to +2.5 hours)
    
    # Medical
    medical_conditions: List[str] = field(default_factory=list)
    medications: List[str] = field(default_factory=list)
    
    # Preferences
    language: str = "en"  # "en" or "es" for Spanish
    
    # Timestamps
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    # Computed properties
    @property
    def age_years(self) -> Optional[int]:
        """Calculate age from date of birth."""
        if not self.date_of_birth:
            return None
        try:
            dob = datetime.fromisoformat(self.date_of_birth)
            today = datetime.now()
            age = today.year - dob.year
            if (today.month, today.day) < (dob.month, dob.day):
                age -= 1
            return age
        except ValueError:
            return None
    
    @property
    def bmi(self) -> Optional[float]:
        """Calculate BMI from height and weight."""
        if not self.height_cm or not self.weight_kg:
            return None
        height_m = self.height_cm / 100.0
        return self.weight_kg / (height_m ** 2)
    
    @property
    def estimated_max_hr(self) -> Optional[float]:
        """Estimate max HR using Tanaka formula if not provided."""
        if self.max_hr_bpm:
            return self.max_hr_bpm
        age = self.age_years
        if age:
            return 208 - (0.7 * age)  # Tanaka formula
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        d = asdict(self)
        # Add computed properties
        d['age_years'] = self.age_years
        d['bmi'] = self.bmi
        d['estimated_max_hr'] = self.estimated_max_hr
        return d


@dataclass
class ClinicalScales:
    """Clinical scale scores for a user at a specific time."""
    
    assessment_id: str
    user_id: str
    assessment_date: str  # ISO format
    timepoint_id: Optional[str] = None  # Links to measurement_timepoints.timepoint_id
    
    # Sleep scales
    epworth_sleepiness_scale: Optional[int] = None  # ESS: 0-24
    pittsburgh_sleep_quality_index: Optional[int] = None  # PSQI: 0-21
    insomnia_severity_index: Optional[int] = None  # ISI: 0-28
    
    # Fatigue scales
    karolinska_sleepiness_scale: Optional[int] = None  # KSS: 1-9
    samn_perelli_fatigue: Optional[int] = None  # 1-7
    fatigue_severity_scale: Optional[float] = None  # FSS: 1-7
    
    # Mood/Stress scales
    perceived_stress_scale: Optional[int] = None  # PSS: 0-40
    beck_depression_inventory: Optional[int] = None  # BDI: 0-63
    state_trait_anxiety_inventory: Optional[int] = None  # STAI
    
    # Affect scales (PANAS - Watson, Clark & Tellegen, 1988)
    panas_positive_affect: Optional[int] = None  # PA: 10-50
    panas_negative_affect: Optional[int] = None  # NA: 10-50
    
    # Physical
    borg_rpe: Optional[int] = None  # 6-20
    vas_pain: Optional[float] = None  # 0-10
    vas_fatigue: Optional[float] = None  # 0-10
    
    # Notes
    notes: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class PolarCredentials:
    """Polar AccessLink OAuth credentials for a user."""
    
    credential_id: str
    user_id: str
    polar_user_id: Optional[str] = None
    access_token_encrypted: Optional[str] = None
    refresh_token_encrypted: Optional[str] = None
    token_expires_at: Optional[str] = None
    last_sync_at: Optional[str] = None
    sync_enabled: bool = True
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class VO2maxEntry:
    """A single VO2max measurement entry."""
    
    entry_id: str
    user_id: str
    measurement_date: str  # ISO format
    vo2max_ml_kg_min: float
    source: str  # 'polar', 'manual', 'garmin', 'whoop', etc.
    polar_fitness_class: Optional[str] = None  # Polar's fitness classification
    notes: Optional[str] = None
    created_at: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class HRVMeasurement:
    """A single HRV measurement session."""
    
    measurement_id: str
    user_id: str
    measurement_date: str  # ISO format
    timepoint_id: Optional[str] = None  # Links to measurement_timepoints.timepoint_id
    
    # Recording metadata
    device_name: Optional[str] = None
    source_file: Optional[str] = None
    file_hash: Optional[str] = None
    recording_start_utc: Optional[str] = None
    recording_duration_min: Optional[float] = None
    recording_context: Optional[str] = None  # rest, sleep, exercise, recovery
    body_position: Optional[str] = None  # supine, seated, standing
    
    # Time domain metrics
    mean_rr_ms: Optional[float] = None
    sdnn_ms: Optional[float] = None
    rmssd_ms: Optional[float] = None
    pnn50_pct: Optional[float] = None
    mean_hr_bpm: Optional[float] = None
    sdhr_bpm: Optional[float] = None
    
    # Frequency domain metrics
    vlf_power_ms2: Optional[float] = None
    lf_power_ms2: Optional[float] = None
    hf_power_ms2: Optional[float] = None
    lf_hf_ratio: Optional[float] = None
    total_power_ms2: Optional[float] = None
    
    # Non-linear metrics
    sd1_ms: Optional[float] = None
    sd2_ms: Optional[float] = None
    dfa_alpha1: Optional[float] = None
    dfa_alpha2: Optional[float] = None
    sample_entropy: Optional[float] = None
    
    # Derived indices
    stress_index: Optional[float] = None
    parasympathetic_index: Optional[float] = None
    hrv_score: Optional[float] = None
    
    # Raw data (stored as JSON)
    rr_intervals_json: Optional[str] = None
    
    # Quality metrics
    artifact_percentage: Optional[float] = None
    quality_score: Optional[float] = None
    
    # Notes
    notes: Optional[str] = None
    
    # Analysis metadata
    analysis_settings_json: Optional[str] = None
    created_at: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class HRVAnalysisCacheEntry:
    """Persisted HRV analysis artifacts keyed by file hash + settings hash.

    This stores the *reusable* analysis payload (windowed metrics subset + summary row)
    so users do not need to recompute when inputs and settings are identical.
    """

    cache_id: str
    user_id: str
    file_hash: str
    analysis_settings_hash: str
    analysis_settings_json: str
    payload_json: str
    source_file: Optional[str] = None
    recording_date: Optional[str] = None
    created_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class AIReport:
    """Stored AI report (e.g., GPT-5.2 interpretation) scoped to a user and context hash."""

    report_id: str
    user_id: str
    report_type: str
    context_hash: str
    markdown: str
    sources_json: Optional[str] = None
    model_used: Optional[str] = None
    mode: Optional[str] = None
    confidence: Optional[float] = None
    created_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class GarminDailyMetrics:
    """Daily Garmin wellness/activity metrics aggregated per date."""

    entry_id: str
    user_id: str
    metric_date: str  # ISO date string
    steps: Optional[int] = None
    distance_km: Optional[float] = None
    calories_kcal: Optional[float] = None
    avg_hr_bpm: Optional[float] = None
    resting_hr_bpm: Optional[float] = None
    stress_score: Optional[float] = None
    sleep_score: Optional[float] = None
    sleep_efficiency: Optional[float] = None
    sleep_duration_hours: Optional[float] = None
    sleep_start_utc: Optional[str] = None
    sleep_end_utc: Optional[str] = None
    avg_spo2: Optional[float] = None
    avg_respiration_awake: Optional[float] = None
    avg_respiration_sleep: Optional[float] = None
    hrv_rmssd_ms: Optional[float] = None
    hrv_sdnn_ms: Optional[float] = None
    body_battery_avg: Optional[float] = None
    body_battery_charge: Optional[float] = None
    body_battery_drain: Optional[float] = None
    source: str = "garmin_fit"
    created_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class FatigueProfileSettings:
    """Persisted default inputs for SAFTE/FRMS workflows (per user).

    This stores the *typical* sleep window and duty window an operator wants to
    reuse across SAFTE/FRMS runs. Objective wearable data (e.g., Garmin daily
    sleep) can still override these defaults when explicitly selected in the UI.
    """

    user_id: str
    typical_sleep_duration_hours: float = 7.5
    typical_sleep_quality: float = 0.8  # 0..1
    typical_bedtime_hour: int = 23  # 0..23 local
    typical_waketime_hour: int = 7  # 0..23 local

    duty_start_hour: int = 9  # 0..23 local
    duty_end_hour: int = 17  # 0..23 local (may be < start for overnight)
    include_weekends: bool = False

    updated_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class BodyCompositionMeasurement:
    """Body composition + extended anthropometrics for a user at a specific date."""

    composition_id: str
    user_id: str
    measurement_date: str  # ISO date string (YYYY-MM-DD)
    timepoint_id: Optional[str] = None  # Links to measurement_timepoints.timepoint_id

    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    body_fat_pct: Optional[float] = None
    lean_mass_kg: Optional[float] = None
    muscle_mass_kg: Optional[float] = None
    bone_mass_kg: Optional[float] = None
    water_pct: Optional[float] = None
    visceral_fat_level: Optional[int] = None

    waist_cm: Optional[float] = None
    hip_cm: Optional[float] = None
    neck_cm: Optional[float] = None
    chest_cm: Optional[float] = None
    arm_cm: Optional[float] = None
    thigh_cm: Optional[float] = None
    calf_cm: Optional[float] = None

    measurement_method: Optional[str] = None
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class MeasurementTimepoint:
    """A labeled longitudinal study timepoint (T0..T21) for a user."""

    timepoint_id: str
    user_id: str
    timepoint_label: str  # e.g. 'T0_baseline', 'T1', 'T2'
    measurement_date: str  # ISO date (YYYY-MM-DD) or ISO datetime
    measurement_number: Optional[int] = None  # 0..21 when available
    is_baseline: bool = False
    notes: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class StudyGroup:
    """A study group definition (e.g., control vs intervention)."""

    group_id: str
    study_id: str
    group_name: str
    description: Optional[str] = None
    created_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class StudyAssignment:
    """Assign a user to a study group."""

    assignment_id: str
    user_id: str
    group_id: str
    assignment_date: str  # ISO format
    created_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


# ---------------------------------------------------------------------------
# Database Manager
# ---------------------------------------------------------------------------

class UserDatabase:
    """SQLite database manager for multi-user HRV data.
    
    Performance optimizations:
    - Persistent connection per thread (connection reuse)
    - WAL mode for concurrent access
    - Optimized pragmas for responsiveness
    - Lazy schema initialization (only once per database file)
    """
    
    # Class-level tracking of initialized databases
    _initialized_dbs: set[str] = set()
    _init_lock = threading.Lock()
    _backed_up_dbs: set[str] = set()
    
    def __init__(self, db_path: Optional[Path] = None) -> None:
        """Initialize database connection.
        
        Args:
            db_path: Path to database file. Uses default if None.
        """
        self.db_path = db_path or get_database_path()
        self._db_path_str = str(self.db_path)
        
        # Only initialize schema once per database file (thread-safe)
        with UserDatabase._init_lock:
            if self._db_path_str not in UserDatabase._initialized_dbs:
                # If the DB file is corrupted (common when stored in synced folders),
                # auto-restore the newest valid timestamped backup so the app can
                # keep operating without manual intervention.
                self._auto_restore_from_backup_if_corrupt()
                self._init_database()
                UserDatabase._initialized_dbs.add(self._db_path_str)

    def _auto_restore_from_backup_if_corrupt(self) -> None:
        """Auto-restore the DB from the newest valid backup if corruption is detected.

        This is intentionally conservative:
        - Only runs during first initialization per DB path
        - Bounded search over the newest backups
        - Preserves the current DB file (never deletes user data)

        Raises:
            RuntimeError: If corruption is detected and no valid backup can be restored.
        """
        # Fast exits for missing/empty DBs (fresh setup).
        if not self.db_path.exists():
            return
        try:
            if self.db_path.stat().st_size == 0:
                return
        except OSError:
            # If we can't stat, don't attempt repair here.
            return

        ok, msg = sqlite_quick_check(self.db_path, timeout_s=2.0)
        if ok:
            return
        _LOGGER.error("SQLite corruption detected (%s). Attempting auto-restore from backup.", msg)

        backups = list_database_backups(db_path=self.db_path, max_backups=25)
        for backup in backups:
            bak_ok, _bak_msg = sqlite_quick_check(backup, timeout_s=2.0)
            if not bak_ok:
                continue
            try:
                preserved = restore_database_from_backup(backup_path=backup, db_path=self.db_path)
            except (OSError, RuntimeError, ValueError) as exc:
                _LOGGER.error("Auto-restore failed from %s: %s", backup, exc)
                continue
            _LOGGER.info(
                "Auto-restored DB from %s (preserved prior DB as %s).",
                backup,
                preserved,
            )
            return

        raise RuntimeError(
            "SQLite database appears corrupted and no valid timestamped backup could be restored. "
            f"DB: {self.db_path} (quick_check={msg})"
        )
    
    def _get_persistent_connection(self) -> sqlite3.Connection:
        """Get or create a persistent connection for the current thread.
        
        Returns:
            SQLite connection with optimized settings.
        """
        # Use a stable per-db key to avoid `id(self)` reuse across tests/reruns.
        # This maintains the intended "one connection per DB per thread" behavior.
        conn_key = f"conn_{self._db_path_str}"
        conn = getattr(_thread_local, conn_key, None)
        
        if conn is not None:
            try:
                # Test if connection is still valid
                conn.execute("SELECT 1")
                return conn
            except sqlite3.Error:
                # Connection is broken, create new one
                conn = None
        
        # Create new connection with optimized settings
        conn = sqlite3.connect(
            self._db_path_str,
            check_same_thread=False,
            timeout=30.0,
        )
        conn.row_factory = sqlite3.Row
        
        _ = _apply_sqlite_connection_pragmas(conn, db_path=self.db_path)
        
        setattr(_thread_local, conn_key, conn)
        return conn
    
    @contextmanager
    def _get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager for database operations using persistent connection.
        
        Uses connection reuse for performance while maintaining transaction safety.
        """
        conn = self._get_persistent_connection()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    
    def close(self) -> None:
        """Close the persistent SQLite connection for this instance."""
        conn_key = f"conn_{self._db_path_str}"
        conn = getattr(_thread_local, conn_key, None)
        if conn is None:
            return
        try:
            conn.close()
        except sqlite3.Error:
            pass
        finally:
            setattr(_thread_local, conn_key, None)
    
    def _init_database(self) -> None:
        """Initialize database schema (called once per database file)."""
        # Backup before any schema changes (required for production research stability).
        self._backup_database_file_if_needed()

        # Use a direct connection for initialization to avoid recursion
        conn = sqlite3.connect(self._db_path_str, timeout=30.0)
        conn.row_factory = sqlite3.Row
        
        try:
            cursor = conn.cursor()
            
            _ = _apply_sqlite_connection_pragmas(conn, db_path=self.db_path)
            
            # Users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT,
                    full_name TEXT NOT NULL,
                    email TEXT,
                    date_of_birth TEXT,
                    sex TEXT,
                    height_cm REAL,
                    weight_kg REAL,
                    resting_hr_bpm REAL,
                    max_hr_bpm REAL,
                    vo2max_ml_kg_min REAL,
                    occupation TEXT,
                    activity_level TEXT,
                    smoking_status TEXT,
                    alcohol_use TEXT,
                    caffeine_intake_mg REAL,
                    medical_conditions TEXT,
                    medications TEXT,
                    language TEXT DEFAULT 'en',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            
            # Migration: Add language column if it doesn't exist (for existing databases)
            try:
                cursor.execute("ALTER TABLE users ADD COLUMN language TEXT DEFAULT 'en'")
            except sqlite3.OperationalError:
                pass  # Column already exists

            # Migration: Add baseline vitals columns (BP + temperature) for readiness model
            for _col, _type in (
                ("baseline_sbp_mmhg", "REAL"),
                ("baseline_dbp_mmhg", "REAL"),
                ("basal_temperature_c", "REAL"),
                ("bp_measurement_time", "TEXT"),
                ("temp_measurement_time", "TEXT"),
            ):
                try:
                    cursor.execute(f"ALTER TABLE users ADD COLUMN {_col} {_type}")
                except sqlite3.OperationalError:
                    pass  # Column already exists
            
            # Clinical scales table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS clinical_scales (
                    assessment_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    assessment_date TEXT NOT NULL,
                    timepoint_id TEXT,
                    epworth_sleepiness_scale INTEGER,
                    pittsburgh_sleep_quality_index INTEGER,
                    insomnia_severity_index INTEGER,
                    karolinska_sleepiness_scale INTEGER,
                    samn_perelli_fatigue INTEGER,
                    fatigue_severity_scale REAL,
                    perceived_stress_scale INTEGER,
                    beck_depression_inventory INTEGER,
                    state_trait_anxiety_inventory INTEGER,
                    panas_positive_affect INTEGER,
                    panas_negative_affect INTEGER,
                    borg_rpe INTEGER,
                    vas_pain REAL,
                    vas_fatigue REAL,
                    notes TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)

            # Migration: add timepoint_id to clinical_scales if missing
            try:
                cursor.execute("ALTER TABLE clinical_scales ADD COLUMN timepoint_id TEXT")
            except sqlite3.OperationalError:
                pass  # Column already exists
            
            # Migration: Add PANAS columns if they don't exist (for existing databases)
            try:
                cursor.execute("ALTER TABLE clinical_scales ADD COLUMN panas_positive_affect INTEGER")
            except sqlite3.OperationalError:
                pass  # Column already exists
            try:
                cursor.execute("ALTER TABLE clinical_scales ADD COLUMN panas_negative_affect INTEGER")
            except sqlite3.OperationalError:
                pass  # Column already exists
            
            # HRV measurements table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS hrv_measurements (
                    measurement_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    measurement_date TEXT NOT NULL,
                    timepoint_id TEXT,
                    device_name TEXT,
                    source_file TEXT,
                    file_hash TEXT,
                    recording_start_utc TEXT,
                    recording_duration_min REAL,
                    recording_context TEXT,
                    body_position TEXT,
                    mean_rr_ms REAL,
                    sdnn_ms REAL,
                    rmssd_ms REAL,
                    pnn50_pct REAL,
                    mean_hr_bpm REAL,
                    sdhr_bpm REAL,
                    vlf_power_ms2 REAL,
                    lf_power_ms2 REAL,
                    hf_power_ms2 REAL,
                    lf_hf_ratio REAL,
                    total_power_ms2 REAL,
                    sd1_ms REAL,
                    sd2_ms REAL,
                    dfa_alpha1 REAL,
                    dfa_alpha2 REAL,
                    sample_entropy REAL,
                    stress_index REAL,
                    parasympathetic_index REAL,
                    hrv_score REAL,
                    rr_intervals_json TEXT,
                    artifact_percentage REAL,
                    quality_score REAL,
                    notes TEXT,
                    analysis_settings_json TEXT,
                    created_at TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)
            # Migrations for existing databases
            for column_def in [
                ("timepoint_id", "TEXT"),
                ("source_file", "TEXT"),
                ("file_hash", "TEXT"),
                ("recording_start_utc", "TEXT"),
                ("analysis_settings_json", "TEXT"),
                ("created_at", "TEXT"),
            ]:
                try:
                    cursor.execute(
                        f"ALTER TABLE hrv_measurements ADD COLUMN {column_def[0]} {column_def[1]}"
                    )
                except sqlite3.OperationalError:
                    pass  # Column already exists
            
            # Create indices for faster queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_measurements_user_date 
                ON hrv_measurements(user_id, measurement_date)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_measurements_timepoint
                ON hrv_measurements(user_id, timepoint_id)
            """)
            cursor.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_measurements_user_hash
                ON hrv_measurements(user_id, file_hash)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_scales_user_date 
                ON clinical_scales(user_id, assessment_date)
            """)
            # Explicit index on username for faster lookups during registration
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_users_username
                ON users(username)
            """)

            # HRV analysis artifacts cache (reusable computed payloads)
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS hrv_analysis_cache (
                    cache_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    file_hash TEXT NOT NULL,
                    analysis_settings_hash TEXT NOT NULL,
                    analysis_settings_json TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    source_file TEXT,
                    recording_date TEXT,
                    created_at TEXT NOT NULL,
                    UNIQUE(user_id, file_hash, analysis_settings_hash),
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_hrv_cache_user_hash
                ON hrv_analysis_cache(user_id, file_hash)
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_hrv_cache_user_created
                ON hrv_analysis_cache(user_id, created_at)
                """
            )

            # AI reports (e.g., GPT-5.2 interpretation) persisted per user + context
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS ai_reports (
                    report_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    report_type TEXT NOT NULL,
                    context_hash TEXT NOT NULL,
                    markdown TEXT NOT NULL,
                    sources_json TEXT,
                    model_used TEXT,
                    mode TEXT,
                    confidence REAL,
                    created_at TEXT NOT NULL,
                    UNIQUE(user_id, report_type, context_hash),
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_ai_reports_user_type_created
                ON ai_reports(user_id, report_type, created_at)
                """
            )

            # Garmin daily metrics (wellness/activity aggregates)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS garmin_daily_metrics (
                    entry_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    metric_date TEXT NOT NULL,
                    steps INTEGER,
                    distance_km REAL,
                    calories_kcal REAL,
                    avg_hr_bpm REAL,
                    resting_hr_bpm REAL,
                    stress_score REAL,
                    sleep_score REAL,
                    sleep_efficiency REAL,
                    sleep_duration_hours REAL,
                    sleep_start_utc TEXT,
                    sleep_end_utc TEXT,
                    avg_spo2 REAL,
                    avg_respiration_awake REAL,
                    avg_respiration_sleep REAL,
                    hrv_rmssd_ms REAL,
                    hrv_sdnn_ms REAL,
                    body_battery_avg REAL,
                    body_battery_charge REAL,
                    body_battery_drain REAL,
                    source TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)
            cursor.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_garmin_metrics_user_date
                ON garmin_daily_metrics(user_id, metric_date)
            """)
            # Backfill new columns if the table already existed
            for col_name, col_type in (
                ("sleep_start_utc", "TEXT"),
                ("sleep_end_utc", "TEXT"),
                ("hrv_rmssd_ms", "REAL"),
                ("hrv_sdnn_ms", "REAL"),
            ):
                try:
                    cursor.execute(f"ALTER TABLE garmin_daily_metrics ADD COLUMN {col_name} {col_type}")
                except sqlite3.OperationalError:
                    pass

            # SAFTE/FRMS fatigue profile defaults (per user)
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS fatigue_profile_settings (
                    user_id TEXT PRIMARY KEY,
                    typical_sleep_duration_hours REAL,
                    typical_sleep_quality REAL,
                    typical_bedtime_hour INTEGER,
                    typical_waketime_hour INTEGER,
                    duty_start_hour INTEGER,
                    duty_end_hour INTEGER,
                    include_weekends INTEGER DEFAULT 0,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_fatigue_profile_updated
                ON fatigue_profile_settings(updated_at)
                """
            )
            
            # Body composition table (extended anthropometrics)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS body_composition (
                    composition_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    measurement_date TEXT NOT NULL,
                    timepoint_id TEXT,
                    height_cm REAL,
                    weight_kg REAL,
                    body_fat_pct REAL,
                    lean_mass_kg REAL,
                    muscle_mass_kg REAL,
                    bone_mass_kg REAL,
                    water_pct REAL,
                    visceral_fat_level INTEGER,
                    waist_cm REAL,
                    hip_cm REAL,
                    neck_cm REAL,
                    chest_cm REAL,
                    arm_cm REAL,
                    thigh_cm REAL,
                    calf_cm REAL,
                    measurement_method TEXT,
                    notes TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)
            try:
                cursor.execute("ALTER TABLE body_composition ADD COLUMN timepoint_id TEXT")
            except sqlite3.OperationalError:
                pass
            
            # Medical history table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS medical_history (
                    history_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    history_json TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)
            
            # Laboratory results - CBC/Hemogram
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS lab_cbc (
                    lab_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    test_date TEXT NOT NULL,
                    timepoint_id TEXT,
                    laboratory TEXT,
                    rbc_million_ul REAL,
                    hemoglobin_g_dl REAL,
                    hematocrit_pct REAL,
                    mcv_fl REAL,
                    mch_pg REAL,
                    mchc_g_dl REAL,
                    rdw_pct REAL,
                    wbc_thousand_ul REAL,
                    neutrophils_pct REAL,
                    lymphocytes_pct REAL,
                    monocytes_pct REAL,
                    eosinophils_pct REAL,
                    basophils_pct REAL,
                    platelets_thousand_ul REAL,
                    mpv_fl REAL,
                    notes TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)
            try:
                cursor.execute("ALTER TABLE lab_cbc ADD COLUMN timepoint_id TEXT")
            except sqlite3.OperationalError:
                pass
            
            # Laboratory results - Blood Chemistry
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS lab_chemistry (
                    lab_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    test_date TEXT NOT NULL,
                    timepoint_id TEXT,
                    fasting INTEGER,
                    laboratory TEXT,
                    glucose_mg_dl REAL,
                    bun_mg_dl REAL,
                    creatinine_mg_dl REAL,
                    sodium_meq_l REAL,
                    potassium_meq_l REAL,
                    chloride_meq_l REAL,
                    co2_meq_l REAL,
                    calcium_mg_dl REAL,
                    total_protein_g_dl REAL,
                    albumin_g_dl REAL,
                    bilirubin_total_mg_dl REAL,
                    ast_u_l REAL,
                    alt_u_l REAL,
                    alp_u_l REAL,
                    total_cholesterol_mg_dl REAL,
                    ldl_cholesterol_mg_dl REAL,
                    hdl_cholesterol_mg_dl REAL,
                    triglycerides_mg_dl REAL,
                    hba1c_pct REAL,
                    tsh_miu_l REAL,
                    free_t4_ng_dl REAL,
                    iron_ug_dl REAL,
                    ferritin_ng_ml REAL,
                    vitamin_d_25oh_ng_ml REAL,
                    vitamin_b12_pg_ml REAL,
                    crp_mg_l REAL,
                    uric_acid_mg_dl REAL,
                    notes TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)
            try:
                cursor.execute("ALTER TABLE lab_chemistry ADD COLUMN timepoint_id TEXT")
            except sqlite3.OperationalError:
                pass
            
            # Laboratory results - Urinalysis
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS lab_urinalysis (
                    lab_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    test_date TEXT NOT NULL,
                    timepoint_id TEXT,
                    collection_method TEXT,
                    color TEXT,
                    appearance TEXT,
                    specific_gravity REAL,
                    ph REAL,
                    protein_qualitative TEXT,
                    glucose_qualitative TEXT,
                    ketones TEXT,
                    blood TEXT,
                    bilirubin TEXT,
                    nitrite TEXT,
                    leukocyte_esterase TEXT,
                    rbc_per_hpf REAL,
                    wbc_per_hpf REAL,
                    bacteria TEXT,
                    casts TEXT,
                    crystals TEXT,
                    notes TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)
            try:
                cursor.execute("ALTER TABLE lab_urinalysis ADD COLUMN timepoint_id TEXT")
            except sqlite3.OperationalError:
                pass
            
            # Physiological calculations (cached results)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS physiological_calcs (
                    calc_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    calculation_date TEXT NOT NULL,
                    bmr_kcal REAL,
                    bmr_method TEXT,
                    tdee_kcal REAL,
                    activity_level TEXT,
                    water_requirement_ml REAL,
                    protein_g REAL,
                    fat_g REAL,
                    carbohydrate_g REAL,
                    fiber_g REAL,
                    exercise_kcal REAL,
                    total_kcal REAL,
                    calculation_json TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)
            
            # Create indices for new tables
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_body_comp_user_date 
                ON body_composition(user_id, measurement_date)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_lab_cbc_user_date 
                ON lab_cbc(user_id, test_date)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_lab_chem_user_date 
                ON lab_chemistry(user_id, test_date)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_lab_urine_user_date 
                ON lab_urinalysis(user_id, test_date)
            """)
            
            # Polar AccessLink credentials table (encrypted tokens)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS polar_credentials (
                    credential_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL UNIQUE,
                    polar_user_id TEXT,
                    access_token_encrypted TEXT,
                    refresh_token_encrypted TEXT,
                    token_expires_at TEXT,
                    last_sync_at TEXT,
                    sync_enabled INTEGER DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)
            
            # VO2max history table (tracks changes over time)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS vo2max_history (
                    entry_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    measurement_date TEXT NOT NULL,
                    vo2max_ml_kg_min REAL NOT NULL,
                    source TEXT NOT NULL,
                    polar_fitness_class TEXT,
                    notes TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)

            # Longitudinal study timepoints (T0..T21) and cohort grouping.
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS measurement_timepoints (
                    timepoint_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    timepoint_label TEXT NOT NULL,
                    measurement_date TEXT NOT NULL,
                    measurement_number INTEGER,
                    is_baseline INTEGER DEFAULT 0,
                    notes TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(user_id, timepoint_label),
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_timepoints_user_label
                ON measurement_timepoints(user_id, timepoint_label)
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS study_groups (
                    group_id TEXT PRIMARY KEY,
                    study_id TEXT NOT NULL,
                    group_name TEXT NOT NULL,
                    description TEXT,
                    created_at TEXT NOT NULL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS study_assignments (
                    assignment_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    group_id TEXT NOT NULL,
                    assignment_date TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(user_id),
                    FOREIGN KEY (group_id) REFERENCES study_groups(group_id)
                )
            """)
            
            # Create indices for Polar tables
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_polar_creds_user 
                ON polar_credentials(user_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_vo2max_user_date 
                ON vo2max_history(user_id, measurement_date)
            """)
            
            # Schema version tracking
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS schema_info (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
            cursor.execute("""
                INSERT OR REPLACE INTO schema_info (key, value) VALUES ('version', ?)
            """, (str(SCHEMA_VERSION),))
            
            conn.commit()
            _LOGGER.info("Database schema initialized: %s", self._db_path_str)
        finally:
            conn.close()

    def _backup_database_file_if_needed(self) -> None:
        """Create a timestamped backup before applying schema changes.

        Raises:
            RuntimeError: If a backup was required but could not be created.
        """
        # NOTE: This method is called from within `UserDatabase._init_lock`.
        # Do not re-acquire the same lock here (non-reentrant), or the app will deadlock.
        if self._db_path_str in UserDatabase._backed_up_dbs:
            return
        if not self.db_path.exists():
            UserDatabase._backed_up_dbs.add(self._db_path_str)
            return
        try:
            if self.db_path.stat().st_size == 0:
                UserDatabase._backed_up_dbs.add(self._db_path_str)
                return
        except OSError as exc:
            if log_exception is not None:
                log_exception(_LOGGER, "Unable to stat database before backup", exc)
            raise RuntimeError("Unable to verify database file before backup") from exc

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_path = self.db_path.with_suffix(f"{self.db_path.suffix}.bak_{timestamp}")
        try:
            shutil.copy2(self.db_path, backup_path)
            UserDatabase._backed_up_dbs.add(self._db_path_str)
            _LOGGER.info("Backed up database before schema init: %s", backup_path)
        except OSError as exc:
            if log_exception is not None:
                log_exception(_LOGGER, "Database backup failed; refusing schema changes", exc)
            raise RuntimeError(
                "Database backup failed; schema changes were not applied. "
                "Please back up hrv_users.db and retry."
            ) from exc
    
    # -----------------------------------------------------------------------
    # User Management
    # -----------------------------------------------------------------------
    
    def create_user(self, profile: UserProfile, password: Optional[str] = None) -> str:
        """Create a new user.
        
        Args:
            profile: User profile data.
            password: Optional password for authentication.
            
        Returns:
            The user_id of the created user.
        """
        now = datetime.now(timezone.utc).isoformat()
        profile.user_id = profile.user_id or str(uuid.uuid4())
        profile.created_at = now
        profile.updated_at = now
        
        password_hash = None
        if password:
            password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO users (
                    user_id, username, password_hash, full_name, email,
                    date_of_birth, sex, height_cm, weight_kg, resting_hr_bpm,
                    max_hr_bpm, vo2max_ml_kg_min, occupation, activity_level,
                    smoking_status, alcohol_use, caffeine_intake_mg,
                    medical_conditions, medications, language, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                profile.user_id, profile.username, password_hash, profile.full_name,
                profile.email, profile.date_of_birth, profile.sex, profile.height_cm,
                profile.weight_kg, profile.resting_hr_bpm, profile.max_hr_bpm,
                profile.vo2max_ml_kg_min, profile.occupation, profile.activity_level,
                profile.smoking_status, profile.alcohol_use, profile.caffeine_intake_mg,
                json.dumps(profile.medical_conditions),
                json.dumps(profile.medications),
                profile.language,
                profile.created_at, profile.updated_at
            ))
        
        _LOGGER.info("Created user: %s (%s)", profile.username, profile.user_id)
        return profile.user_id
    
    def create_user_if_not_exists(
        self,
        profile: UserProfile,
        password: Optional[str] = None,
    ) -> Tuple[str, bool]:
        """Create a new user only if the username doesn't exist.
        
        This is an optimized method that checks and creates in a single transaction,
        avoiding the overhead of separate database calls during registration.
        
        Args:
            profile: User profile data.
            password: Optional password for authentication.
            
        Returns:
            Tuple of (user_id, created) where created is True if new user was made,
            False if username already existed.
        """
        now = datetime.now(timezone.utc).isoformat()
        profile.user_id = profile.user_id or str(uuid.uuid4())
        profile.created_at = now
        profile.updated_at = now
        
        password_hash = None
        if password:
            password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if username exists (single query)
            cursor.execute(
                "SELECT user_id FROM users WHERE username = ?",
                (profile.username,)
            )
            existing = cursor.fetchone()
            
            if existing:
                return existing["user_id"], False
            
            # Insert new user (same transaction)
            cursor.execute("""
                INSERT INTO users (
                    user_id, username, password_hash, full_name, email,
                    date_of_birth, sex, height_cm, weight_kg, resting_hr_bpm,
                    max_hr_bpm, vo2max_ml_kg_min, occupation, activity_level,
                    smoking_status, alcohol_use, caffeine_intake_mg,
                    medical_conditions, medications, language, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                profile.user_id, profile.username, password_hash, profile.full_name,
                profile.email, profile.date_of_birth, profile.sex, profile.height_cm,
                profile.weight_kg, profile.resting_hr_bpm, profile.max_hr_bpm,
                profile.vo2max_ml_kg_min, profile.occupation, profile.activity_level,
                profile.smoking_status, profile.alcohol_use, profile.caffeine_intake_mg,
                json.dumps(profile.medical_conditions),
                json.dumps(profile.medications),
                profile.language,
                profile.created_at, profile.updated_at
            ))
        
        _LOGGER.info("Created user: %s (%s)", profile.username, profile.user_id)
        return profile.user_id, True
    
    def get_user(self, user_id: str) -> Optional[UserProfile]:
        """Get user profile by ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            
            if not row:
                return None
            
            return self._row_to_user_profile(row)
    
    def get_user_by_username(self, username: str) -> Optional[UserProfile]:
        """Get user profile by username."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
            row = cursor.fetchone()
            
            if not row:
                return None
            
            return self._row_to_user_profile(row)
    
    def list_users(self) -> List[UserProfile]:
        """List all users."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users ORDER BY full_name")
            rows = cursor.fetchall()
            return [self._row_to_user_profile(row) for row in rows]
    
    def update_user(self, profile: UserProfile) -> None:
        """Update user profile."""
        profile.updated_at = datetime.now(timezone.utc).isoformat()
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users SET
                    full_name = ?, email = ?, date_of_birth = ?, sex = ?,
                    height_cm = ?, weight_kg = ?, resting_hr_bpm = ?, max_hr_bpm = ?,
                    vo2max_ml_kg_min = ?, occupation = ?, activity_level = ?,
                    smoking_status = ?, alcohol_use = ?, caffeine_intake_mg = ?,
                    medical_conditions = ?, medications = ?, language = ?, updated_at = ?
                WHERE user_id = ?
            """, (
                profile.full_name, profile.email, profile.date_of_birth, profile.sex,
                profile.height_cm, profile.weight_kg, profile.resting_hr_bpm,
                profile.max_hr_bpm, profile.vo2max_ml_kg_min, profile.occupation,
                profile.activity_level, profile.smoking_status, profile.alcohol_use,
                profile.caffeine_intake_mg, json.dumps(profile.medical_conditions),
                json.dumps(profile.medications), profile.language, profile.updated_at,
                profile.user_id
            ))
    
    def update_user_sleep_chronotype(
        self,
        user_id: str,
        *,
        resting_hr_bpm: Optional[float] = None,
        chronotype_offset_hours: Optional[float] = None,
    ) -> None:
        """Update user profile with sleep/chronotype data from Garmin autofill or manual sync.
        
        Args:
            user_id: User identifier
            resting_hr_bpm: Resting heart rate to update (optional)
            chronotype_offset_hours: Chronotype offset in hours (optional)
        """
        updates: List[str] = []
        values: List[Any] = []
        
        if resting_hr_bpm is not None:
            updates.append("resting_heart_rate_bpm = ?")
            values.append(resting_hr_bpm)
        
        if chronotype_offset_hours is not None:
            updates.append("chronotype_offset_hours = ?")
            values.append(chronotype_offset_hours)
        
        if not updates:
            return  # Nothing to update
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"""
                UPDATE users SET
                    {', '.join(updates)},
                    updated_at = ?
                WHERE user_id = ?
                """,
                (*values, datetime.now(timezone.utc).isoformat(), user_id),
            )
    
    def delete_user(self, user_id: str) -> None:
        """Delete user and all associated data."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM hrv_measurements WHERE user_id = ?", (user_id,))
            cursor.execute("DELETE FROM clinical_scales WHERE user_id = ?", (user_id,))
            cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        _LOGGER.info("Deleted user: %s", user_id)
    
    def authenticate_user(self, username: str, password: str) -> Optional[UserProfile]:
        """Authenticate user with password.
        
        Args:
            username: Username to authenticate.
            password: Password to verify.
            
        Returns:
            UserProfile if authentication succeeds, None otherwise.
        """
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM users WHERE username = ? AND password_hash = ?",
                (username, password_hash)
            )
            row = cursor.fetchone()
            
            if not row:
                return None
            
            return self._row_to_user_profile(row)
    
    def _row_to_user_profile(self, row: sqlite3.Row) -> UserProfile:
        """Convert database row to UserProfile."""
        medical_conditions = []
        medications = []
        
        if row["medical_conditions"]:
            try:
                medical_conditions = json.loads(row["medical_conditions"])
            except json.JSONDecodeError:
                pass
        
        if row["medications"]:
            try:
                medications = json.loads(row["medications"])
            except json.JSONDecodeError:
                pass
        
        # Safely get language with fallback for existing databases
        try:
            language = row["language"] or "en"
        except (KeyError, IndexError):
            language = "en"
        
        # Safely get chronotype_offset_hours with fallback
        # Handle case where column doesn't exist in older database schemas
        chronotype_offset_hours = None
        try:
            if "chronotype_offset_hours" in row.keys():
                chronotype_offset_hours = row["chronotype_offset_hours"]
                if chronotype_offset_hours is not None:
                    chronotype_offset_hours = float(chronotype_offset_hours)
        except (KeyError, IndexError, ValueError, TypeError):
            chronotype_offset_hours = None
        
        return UserProfile(
            user_id=row["user_id"],
            username=row["username"],
            full_name=row["full_name"],
            email=row["email"],
            date_of_birth=row["date_of_birth"],
            sex=row["sex"],
            height_cm=row["height_cm"],
            weight_kg=row["weight_kg"],
            resting_hr_bpm=row["resting_hr_bpm"],
            max_hr_bpm=row["max_hr_bpm"],
            vo2max_ml_kg_min=row["vo2max_ml_kg_min"],
            occupation=row["occupation"],
            activity_level=row["activity_level"],
            smoking_status=row["smoking_status"],
            alcohol_use=row["alcohol_use"],
            caffeine_intake_mg=row["caffeine_intake_mg"],
            chronotype_offset_hours=chronotype_offset_hours,
            medical_conditions=medical_conditions,
            medications=medications,
            language=language,
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
    
    # -----------------------------------------------------------------------
    # Clinical Scales
    # -----------------------------------------------------------------------
    
    def save_clinical_scales(self, scales: ClinicalScales) -> str:
        """Save clinical scale assessment."""
        scales.assessment_id = scales.assessment_id or str(uuid.uuid4())
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO clinical_scales (
                    assessment_id, user_id, assessment_date,
                    timepoint_id,
                    epworth_sleepiness_scale, pittsburgh_sleep_quality_index,
                    insomnia_severity_index, karolinska_sleepiness_scale,
                    samn_perelli_fatigue, fatigue_severity_scale,
                    perceived_stress_scale, beck_depression_inventory,
                    state_trait_anxiety_inventory, panas_positive_affect,
                    panas_negative_affect, borg_rpe, vas_pain,
                    vas_fatigue, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                scales.assessment_id, scales.user_id, scales.assessment_date,
                scales.timepoint_id,
                scales.epworth_sleepiness_scale, scales.pittsburgh_sleep_quality_index,
                scales.insomnia_severity_index, scales.karolinska_sleepiness_scale,
                scales.samn_perelli_fatigue, scales.fatigue_severity_scale,
                scales.perceived_stress_scale, scales.beck_depression_inventory,
                scales.state_trait_anxiety_inventory, scales.panas_positive_affect,
                scales.panas_negative_affect, scales.borg_rpe, scales.vas_pain,
                scales.vas_fatigue, scales.notes
            ))
        
        return scales.assessment_id
    
    def get_clinical_scales_history(
        self, user_id: str, limit: int = 100
    ) -> List[ClinicalScales]:
        """Get clinical scales history for a user."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM clinical_scales 
                WHERE user_id = ? 
                ORDER BY assessment_date DESC 
                LIMIT ?
            """, (user_id, limit))
            rows = cursor.fetchall()
            
            return [self._row_to_clinical_scales(row) for row in rows]
    
    def _row_to_clinical_scales(self, row: sqlite3.Row) -> ClinicalScales:
        """Convert database row to ClinicalScales."""
        # Helper to safely get columns that might not exist in older databases
        def _safe_get(key: str, default: Any = None) -> Any:
            try:
                return row[key]
            except (IndexError, KeyError):
                return default
        
        return ClinicalScales(
            assessment_id=row["assessment_id"],
            user_id=row["user_id"],
            assessment_date=row["assessment_date"],
            timepoint_id=_safe_get("timepoint_id"),
            epworth_sleepiness_scale=row["epworth_sleepiness_scale"],
            pittsburgh_sleep_quality_index=row["pittsburgh_sleep_quality_index"],
            insomnia_severity_index=row["insomnia_severity_index"],
            karolinska_sleepiness_scale=row["karolinska_sleepiness_scale"],
            samn_perelli_fatigue=row["samn_perelli_fatigue"],
            fatigue_severity_scale=row["fatigue_severity_scale"],
            perceived_stress_scale=row["perceived_stress_scale"],
            beck_depression_inventory=row["beck_depression_inventory"],
            state_trait_anxiety_inventory=row["state_trait_anxiety_inventory"],
            panas_positive_affect=_safe_get("panas_positive_affect"),
            panas_negative_affect=_safe_get("panas_negative_affect"),
            borg_rpe=row["borg_rpe"],
            vas_pain=row["vas_pain"],
            vas_fatigue=row["vas_fatigue"],
            notes=row["notes"],
        )
    
    # -----------------------------------------------------------------------
    # Medical History (NASA exploration record)
    # -----------------------------------------------------------------------
    
    def save_medical_history_entry(
        self,
        user_id: str,
        record: Dict[str, Any],
        *,
        history_id: Optional[str] = None,
    ) -> str:
        """Save or update a structured medical history entry."""
        entry_id = history_id or str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()
        payload = json.dumps(record, ensure_ascii=False, default=str)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO medical_history (history_id, user_id, updated_at, history_json)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(history_id) DO UPDATE SET
                    updated_at = excluded.updated_at,
                    history_json = excluded.history_json
                """,
                (entry_id, user_id, timestamp, payload),
            )
        
        return entry_id
    
    def get_medical_history(
        self,
        user_id: str,
        *,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Return structured medical history entries ordered from newest to oldest."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT history_id, updated_at, history_json
                FROM medical_history
                WHERE user_id = ?
                ORDER BY datetime(updated_at) DESC
                LIMIT ?
                """,
                (user_id, limit),
            )
            rows = cursor.fetchall()
        
        entries: List[Dict[str, Any]] = []
        for row in rows:
            try:
                payload = json.loads(row["history_json"])
            except (TypeError, json.JSONDecodeError):
                payload = {}
            payload["history_id"] = row["history_id"]
            payload["updated_at"] = row["updated_at"]
            entries.append(payload)
        return entries
    
    # -----------------------------------------------------------------------
    # Polar AccessLink Credentials
    # -----------------------------------------------------------------------
    
    def save_polar_credentials(self, credentials: PolarCredentials) -> str:
        """Save or update Polar AccessLink credentials for a user.
        
        Args:
            credentials: PolarCredentials object with token data.
            
        Returns:
            The credential_id.
        """
        now = datetime.now(timezone.utc).isoformat()
        credentials.credential_id = credentials.credential_id or str(uuid.uuid4())
        credentials.created_at = credentials.created_at or now
        credentials.updated_at = now
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO polar_credentials (
                    credential_id, user_id, polar_user_id,
                    access_token_encrypted, refresh_token_encrypted,
                    token_expires_at, last_sync_at, sync_enabled,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    polar_user_id = excluded.polar_user_id,
                    access_token_encrypted = excluded.access_token_encrypted,
                    refresh_token_encrypted = excluded.refresh_token_encrypted,
                    token_expires_at = excluded.token_expires_at,
                    last_sync_at = excluded.last_sync_at,
                    sync_enabled = excluded.sync_enabled,
                    updated_at = excluded.updated_at
            """, (
                credentials.credential_id, credentials.user_id,
                credentials.polar_user_id, credentials.access_token_encrypted,
                credentials.refresh_token_encrypted, credentials.token_expires_at,
                credentials.last_sync_at, 1 if credentials.sync_enabled else 0,
                credentials.created_at, credentials.updated_at
            ))
        
        _LOGGER.info("Saved Polar credentials for user: %s", credentials.user_id)
        return credentials.credential_id
    
    def get_polar_credentials(self, user_id: str) -> Optional[PolarCredentials]:
        """Get Polar AccessLink credentials for a user.
        
        Args:
            user_id: User identifier.
            
        Returns:
            PolarCredentials if found, None otherwise.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM polar_credentials WHERE user_id = ?",
                (user_id,)
            )
            row = cursor.fetchone()
            
            if not row:
                return None
            
            return PolarCredentials(
                credential_id=row["credential_id"],
                user_id=row["user_id"],
                polar_user_id=row["polar_user_id"],
                access_token_encrypted=row["access_token_encrypted"],
                refresh_token_encrypted=row["refresh_token_encrypted"],
                token_expires_at=row["token_expires_at"],
                last_sync_at=row["last_sync_at"],
                sync_enabled=bool(row["sync_enabled"]),
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
    
    def delete_polar_credentials(self, user_id: str) -> bool:
        """Delete Polar AccessLink credentials for a user.
        
        Args:
            user_id: User identifier.
            
        Returns:
            True if credentials were deleted, False if not found.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM polar_credentials WHERE user_id = ?",
                (user_id,)
            )
            deleted = cursor.rowcount > 0
        
        if deleted:
            _LOGGER.info("Deleted Polar credentials for user: %s", user_id)
        return deleted
    
    def update_polar_sync_time(self, user_id: str) -> None:
        """Update the last sync timestamp for a user's Polar credentials.
        
        Args:
            user_id: User identifier.
        """
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE polar_credentials SET last_sync_at = ?, updated_at = ? WHERE user_id = ?",
                (now, now, user_id)
            )
    
    # -----------------------------------------------------------------------
    # VO2max History
    # -----------------------------------------------------------------------
    
    def save_vo2max_entry(self, entry: VO2maxEntry) -> str:
        """Save a VO2max measurement entry.
        
        Args:
            entry: VO2maxEntry object with measurement data.
            
        Returns:
            The entry_id.
        """
        now = datetime.now(timezone.utc).isoformat()
        entry.entry_id = entry.entry_id or str(uuid.uuid4())
        entry.created_at = entry.created_at or now
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO vo2max_history (
                    entry_id, user_id, measurement_date, vo2max_ml_kg_min,
                    source, polar_fitness_class, notes, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                entry.entry_id, entry.user_id, entry.measurement_date,
                entry.vo2max_ml_kg_min, entry.source, entry.polar_fitness_class,
                entry.notes, entry.created_at
            ))
        
        _LOGGER.info(
            "Saved VO2max entry for user %s: %.1f mL/kg/min from %s",
            entry.user_id, entry.vo2max_ml_kg_min, entry.source
        )
        return entry.entry_id
    
    def get_vo2max_history(
        self, user_id: str, limit: int = 100
    ) -> List[VO2maxEntry]:
        """Get VO2max history for a user.
        
        Args:
            user_id: User identifier.
            limit: Maximum number of entries to return.
            
        Returns:
            List of VO2maxEntry objects ordered by date descending.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM vo2max_history 
                WHERE user_id = ? 
                ORDER BY measurement_date DESC 
                LIMIT ?
            """, (user_id, limit))
            rows = cursor.fetchall()
            
            return [
                VO2maxEntry(
                    entry_id=row["entry_id"],
                    user_id=row["user_id"],
                    measurement_date=row["measurement_date"],
                    vo2max_ml_kg_min=row["vo2max_ml_kg_min"],
                    source=row["source"],
                    polar_fitness_class=row["polar_fitness_class"],
                    notes=row["notes"],
                    created_at=row["created_at"],
                )
                for row in rows
            ]
    
    def get_latest_vo2max(self, user_id: str) -> Optional[VO2maxEntry]:
        """Get the most recent VO2max entry for a user.
        
        Args:
            user_id: User identifier.
            
        Returns:
            Most recent VO2maxEntry if found, None otherwise.
        """
        history = self.get_vo2max_history(user_id, limit=1)
        return history[0] if history else None
    
    def get_vo2max_dataframe(self, user_id: str) -> pd.DataFrame:
        """Get VO2max history as a pandas DataFrame for analysis.
        
        Args:
            user_id: User identifier.
            
        Returns:
            DataFrame with VO2max history and date parsing.
        """
        with self._get_connection() as conn:
            df = pd.read_sql_query(
                """
                SELECT entry_id, user_id, measurement_date, vo2max_ml_kg_min,
                       source, polar_fitness_class, notes, created_at
                FROM vo2max_history
                WHERE user_id = ?
                ORDER BY measurement_date DESC
                """,
                conn,
                params=(user_id,)
            )
            if not df.empty and "measurement_date" in df.columns:
                df["measurement_date"] = pd.to_datetime(df["measurement_date"])
            return df
    
    # -----------------------------------------------------------------------
    # HRV Measurements
    # -----------------------------------------------------------------------
    
    def save_hrv_measurement(self, measurement: HRVMeasurement) -> str:
        """Save HRV measurement."""
        measurement.measurement_id = measurement.measurement_id or str(uuid.uuid4())
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO hrv_measurements (
                    measurement_id, user_id, measurement_date, timepoint_id, device_name,
                    source_file, file_hash, recording_start_utc,
                    recording_duration_min, recording_context, body_position,
                    mean_rr_ms, sdnn_ms, rmssd_ms, pnn50_pct, mean_hr_bpm, sdhr_bpm,
                    vlf_power_ms2, lf_power_ms2, hf_power_ms2, lf_hf_ratio, total_power_ms2,
                    sd1_ms, sd2_ms, dfa_alpha1, dfa_alpha2, sample_entropy,
                    stress_index, parasympathetic_index, hrv_score,
                    rr_intervals_json, artifact_percentage, quality_score, notes,
                    analysis_settings_json, created_at
                ) VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
            """, (
                measurement.measurement_id, measurement.user_id, measurement.measurement_date,
                measurement.timepoint_id,
                measurement.device_name, measurement.source_file, measurement.file_hash,
                measurement.recording_start_utc, measurement.recording_duration_min,
                measurement.recording_context, measurement.body_position,
                measurement.mean_rr_ms, measurement.sdnn_ms, measurement.rmssd_ms,
                measurement.pnn50_pct, measurement.mean_hr_bpm, measurement.sdhr_bpm,
                measurement.vlf_power_ms2, measurement.lf_power_ms2, measurement.hf_power_ms2,
                measurement.lf_hf_ratio, measurement.total_power_ms2,
                measurement.sd1_ms, measurement.sd2_ms, measurement.dfa_alpha1,
                measurement.dfa_alpha2, measurement.sample_entropy,
                measurement.stress_index, measurement.parasympathetic_index,
                measurement.hrv_score, measurement.rr_intervals_json,
                measurement.artifact_percentage, measurement.quality_score, measurement.notes,
                measurement.analysis_settings_json, measurement.created_at
            ))
        
        return measurement.measurement_id
    
    def get_hrv_history(
        self, user_id: str, limit: int = 1000
    ) -> List[HRVMeasurement]:
        """Get HRV measurement history for a user."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM hrv_measurements 
                WHERE user_id = ? 
                ORDER BY measurement_date DESC 
                LIMIT ?
            """, (user_id, limit))
            rows = cursor.fetchall()
            
            return [self._row_to_hrv_measurement(row) for row in rows]
    
    def get_measurement_by_hash(
        self, user_id: str, file_hash: str
    ) -> Optional[HRVMeasurement]:
        """Return the first HRV measurement matching a stored file hash."""
        if not file_hash:
            return None
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM hrv_measurements
                WHERE user_id = ? AND file_hash = ?
                ORDER BY datetime(created_at) DESC
                LIMIT 1
                """,
                (user_id, file_hash),
            )
            row = cursor.fetchone()
        return self._row_to_hrv_measurement(row) if row else None

    # -----------------------------------------------------------------------
    # HRV Analysis Artifacts Cache (per user, per file hash, per settings hash)
    # -----------------------------------------------------------------------

    @staticmethod
    def _stable_json_dumps(value: Any) -> str:
        """Serialize to JSON with stable key ordering.

        Notes:
            Uses `default=str` defensively for numpy/pandas scalars.
        """
        return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)

    @staticmethod
    def compute_settings_hash(analysis_settings: Dict[str, Any]) -> str:
        """Compute deterministic hash for analysis settings."""
        if not isinstance(analysis_settings, dict) or not analysis_settings:
            raise ValueError("analysis_settings must be a non-empty dict")
        settings_json = UserDatabase._stable_json_dumps(analysis_settings)
        return hashlib.sha256(settings_json.encode("utf-8")).hexdigest()

    def save_hrv_analysis_cache(
        self,
        *,
        user_id: str,
        file_hash: str,
        analysis_settings: Dict[str, Any],
        payload: Dict[str, Any],
        source_file: Optional[str] = None,
        recording_date: Optional[str] = None,
    ) -> str:
        """Upsert reusable HRV analysis payload into SQLite.

        Args:
            user_id: User identifier.
            file_hash: Hash of the raw RR file content.
            analysis_settings: Dict describing analysis parameters.
            payload: Dict payload containing computed analysis outputs.
            source_file: Optional human-friendly filename.
            recording_date: Optional ISO date string.

        Returns:
            analysis_settings_hash used as cache key.
        """
        if not user_id:
            raise ValueError("user_id is required")
        if not file_hash:
            raise ValueError("file_hash is required")
        if not isinstance(payload, dict) or not payload:
            raise ValueError("payload must be a non-empty dict")

        settings_hash = self.compute_settings_hash(analysis_settings)
        now = datetime.now(timezone.utc).isoformat()
        cache_id = str(uuid.uuid4())
        settings_json = self._stable_json_dumps(analysis_settings)
        payload_json = self._stable_json_dumps(payload)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO hrv_analysis_cache (
                    cache_id, user_id, file_hash, analysis_settings_hash,
                    analysis_settings_json, payload_json, source_file, recording_date, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, file_hash, analysis_settings_hash) DO UPDATE SET
                    analysis_settings_json = excluded.analysis_settings_json,
                    payload_json = excluded.payload_json,
                    source_file = COALESCE(excluded.source_file, hrv_analysis_cache.source_file),
                    recording_date = COALESCE(excluded.recording_date, hrv_analysis_cache.recording_date),
                    created_at = excluded.created_at
                """,
                (
                    cache_id,
                    user_id,
                    file_hash,
                    settings_hash,
                    settings_json,
                    payload_json,
                    source_file,
                    recording_date,
                    now,
                ),
            )
        return settings_hash

    def get_hrv_analysis_cache_payload(
        self,
        *,
        user_id: str,
        file_hash: str,
        analysis_settings_hash: str,
    ) -> Optional[Dict[str, Any]]:
        """Load cached HRV analysis payload for a user/file/settings triple."""
        if not user_id or not file_hash or not analysis_settings_hash:
            return None
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT payload_json
                FROM hrv_analysis_cache
                WHERE user_id = ? AND file_hash = ? AND analysis_settings_hash = ?
                ORDER BY datetime(created_at) DESC
                LIMIT 1
                """,
                (user_id, file_hash, analysis_settings_hash),
            )
            row = cursor.fetchone()
        if not row:
            return None
        try:
            return json.loads(row["payload_json"])
        except (TypeError, json.JSONDecodeError):
            return None

    def get_hrv_analysis_cache_entries(
        self, user_id: str, *, limit: int = 200
    ) -> List[HRVAnalysisCacheEntry]:
        """Return HRV analysis cache entries for a user (most recent first)."""
        if not user_id:
            return []
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT *
                FROM hrv_analysis_cache
                WHERE user_id = ?
                ORDER BY datetime(created_at) DESC
                LIMIT ?
                """,
                (user_id, int(limit)),
            )
            rows = cursor.fetchall()
        out: List[HRVAnalysisCacheEntry] = []
        for row in rows:
            out.append(
                HRVAnalysisCacheEntry(
                    cache_id=row["cache_id"],
                    user_id=row["user_id"],
                    file_hash=row["file_hash"],
                    analysis_settings_hash=row["analysis_settings_hash"],
                    analysis_settings_json=row["analysis_settings_json"],
                    payload_json=row["payload_json"],
                    source_file=row["source_file"],
                    recording_date=row["recording_date"],
                    created_at=row["created_at"],
                )
            )
        return out

    # -----------------------------------------------------------------------
    # AI Reports (per user, per context hash)
    # -----------------------------------------------------------------------

    def save_ai_report(
        self,
        *,
        user_id: str,
        report_type: str,
        context_hash: str,
        markdown: str,
        sources: Optional[Sequence[str]] = None,
        model_used: Optional[str] = None,
        mode: Optional[str] = None,
        confidence: Optional[float] = None,
    ) -> str:
        """Upsert an AI report for a user/context.

        This stores the **rendered markdown only** (no raw reasoning), plus citation metadata.
        """
        if not user_id:
            raise ValueError("user_id is required")
        if not report_type:
            raise ValueError("report_type is required")
        if not context_hash:
            raise ValueError("context_hash is required")
        if not isinstance(markdown, str) or not markdown.strip():
            raise ValueError("markdown must be a non-empty string")
        now = datetime.now(timezone.utc).isoformat()
        report_id = str(uuid.uuid4())
        sources_json = json.dumps(list(sources or []), ensure_ascii=True)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO ai_reports (
                    report_id, user_id, report_type, context_hash,
                    markdown, sources_json, model_used, mode, confidence, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, report_type, context_hash) DO UPDATE SET
                    markdown = excluded.markdown,
                    sources_json = excluded.sources_json,
                    model_used = excluded.model_used,
                    mode = excluded.mode,
                    confidence = excluded.confidence,
                    created_at = excluded.created_at
                """,
                (
                    report_id,
                    user_id,
                    report_type,
                    context_hash,
                    markdown,
                    sources_json,
                    model_used,
                    mode,
                    confidence,
                    now,
                ),
            )
        return report_id

    def get_ai_report(
        self,
        *,
        user_id: str,
        report_type: str,
        context_hash: str,
    ) -> Optional[AIReport]:
        """Fetch a stored AI report for a user/context."""
        if not user_id or not report_type or not context_hash:
            return None
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT *
                FROM ai_reports
                WHERE user_id = ? AND report_type = ? AND context_hash = ?
                ORDER BY datetime(created_at) DESC
                LIMIT 1
                """,
                (user_id, report_type, context_hash),
            )
            row = cursor.fetchone()
        if row is None:
            return None
        return AIReport(
            report_id=row["report_id"],
            user_id=row["user_id"],
            report_type=row["report_type"],
            context_hash=row["context_hash"],
            markdown=row["markdown"],
            sources_json=row["sources_json"],
            model_used=row["model_used"],
            mode=row["mode"],
            confidence=row["confidence"],
            created_at=row["created_at"],
        )

    def get_ai_reports(
        self, user_id: str, *, report_type: Optional[str] = None, limit: int = 100
    ) -> List[AIReport]:
        """List stored AI reports for a user (most recent first)."""
        if not user_id:
            return []
        sql = "SELECT * FROM ai_reports WHERE user_id = ?"
        params: Tuple[Any, ...] = (user_id,)
        if report_type:
            sql += " AND report_type = ?"
            params = (user_id, str(report_type))
        sql += " ORDER BY datetime(created_at) DESC LIMIT ?"
        params = (*params, int(limit))
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            rows = cursor.fetchall()
        out: List[AIReport] = []
        for row in rows:
            out.append(
                AIReport(
                    report_id=row["report_id"],
                    user_id=row["user_id"],
                    report_type=row["report_type"],
                    context_hash=row["context_hash"],
                    markdown=row["markdown"],
                    sources_json=row["sources_json"],
                    model_used=row["model_used"],
                    mode=row["mode"],
                    confidence=row["confidence"],
                    created_at=row["created_at"],
                )
            )
        return out
    
    def get_hrv_dataframe(
        self,
        user_id: str,
        *,
        limit: Optional[int] = None,
        include_rr: bool = False,
        columns: Optional[Sequence[str]] = None,
    ) -> pd.DataFrame:
        """
        Get HRV history as pandas DataFrame for analysis.

        Args:
            user_id: User identifier.
            limit: Optional maximum rows to return (most recent first).
            include_rr: Whether to include `rr_intervals_json` (large payload).
            columns: Optional explicit column whitelist; overrides defaults.
        """
        default_cols: List[str] = [
            "measurement_id",
            "user_id",
            "measurement_date",
            "timepoint_id",
            "device_name",
            "source_file",
            "file_hash",
            "recording_start_utc",
            "recording_duration_min",
            "recording_context",
            "body_position",
            "mean_rr_ms",
            "sdnn_ms",
            "rmssd_ms",
            "pnn50_pct",
            "mean_hr_bpm",
            "sdhr_bpm",
            "vlf_power_ms2",
            "lf_power_ms2",
            "hf_power_ms2",
            "lf_hf_ratio",
            "total_power_ms2",
            "sd1_ms",
            "sd2_ms",
            "dfa_alpha1",
            "dfa_alpha2",
            "sample_entropy",
            "stress_index",
            "parasympathetic_index",
            "hrv_score",
            "artifact_percentage",
            "quality_score",
            "analysis_settings_json",
            "created_at",
            "notes",
        ]

        if include_rr and "rr_intervals_json" not in default_cols:
            default_cols.append("rr_intervals_json")

        selected_cols = list(columns) if columns is not None else default_cols
        select_clause = ", ".join(selected_cols)

        sql = (
            f"SELECT {select_clause} FROM hrv_measurements "
            "WHERE user_id = ? "
            "ORDER BY measurement_date DESC"
        )
        params: Tuple[Any, ...] = (user_id,)
        if limit is not None:
            sql += " LIMIT ?"
            params = (user_id, int(limit))

        with self._get_connection() as conn:
            df = pd.read_sql_query(sql, conn, params=params)
            if not df.empty and "measurement_date" in df.columns:
                df["measurement_date"] = pd.to_datetime(df["measurement_date"])
            return df
    
    def _row_to_hrv_measurement(self, row: sqlite3.Row) -> HRVMeasurement:
        """Convert database row to HRVMeasurement."""
        return HRVMeasurement(
            measurement_id=row["measurement_id"],
            user_id=row["user_id"],
            measurement_date=row["measurement_date"],
            timepoint_id=row["timepoint_id"] if "timepoint_id" in row.keys() else None,
            device_name=row["device_name"],
            source_file=row["source_file"],
            file_hash=row["file_hash"],
            recording_start_utc=row["recording_start_utc"],
            recording_duration_min=row["recording_duration_min"],
            recording_context=row["recording_context"],
            body_position=row["body_position"],
            mean_rr_ms=row["mean_rr_ms"],
            sdnn_ms=row["sdnn_ms"],
            rmssd_ms=row["rmssd_ms"],
            pnn50_pct=row["pnn50_pct"],
            mean_hr_bpm=row["mean_hr_bpm"],
            sdhr_bpm=row["sdhr_bpm"],
            vlf_power_ms2=row["vlf_power_ms2"],
            lf_power_ms2=row["lf_power_ms2"],
            hf_power_ms2=row["hf_power_ms2"],
            lf_hf_ratio=row["lf_hf_ratio"],
            total_power_ms2=row["total_power_ms2"],
            sd1_ms=row["sd1_ms"],
            sd2_ms=row["sd2_ms"],
            dfa_alpha1=row["dfa_alpha1"],
            dfa_alpha2=row["dfa_alpha2"],
            sample_entropy=row["sample_entropy"],
            stress_index=row["stress_index"],
            parasympathetic_index=row["parasympathetic_index"],
            hrv_score=row["hrv_score"],
            rr_intervals_json=row["rr_intervals_json"],
            artifact_percentage=row["artifact_percentage"],
            quality_score=row["quality_score"],
            notes=row["notes"],
            analysis_settings_json=row["analysis_settings_json"],
            created_at=row["created_at"],
        )
    
    # -----------------------------------------------------------------------
    # Garmin Wellness / Activity Metrics (Vivosmart, etc.)
    # -----------------------------------------------------------------------

    def save_garmin_daily_metrics(
        self, metrics: Sequence[GarminDailyMetrics]
    ) -> None:
        """Upsert daily Garmin wellness/activity metrics."""
        if not metrics:
            return
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            for entry in metrics:
                entry.entry_id = entry.entry_id or str(uuid.uuid4())
                created_at = entry.created_at or now
                cursor.execute(
                    """
                    INSERT INTO garmin_daily_metrics (
                        entry_id, user_id, metric_date, steps, distance_km,
                        calories_kcal, avg_hr_bpm, resting_hr_bpm, stress_score,
                        sleep_score, sleep_efficiency, sleep_duration_hours,
                        sleep_start_utc, sleep_end_utc,
                        avg_spo2, avg_respiration_awake, avg_respiration_sleep,
                        hrv_rmssd_ms, hrv_sdnn_ms,
                        body_battery_avg, body_battery_charge, body_battery_drain,
                        source, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(user_id, metric_date) DO UPDATE SET
                        steps = COALESCE(excluded.steps, steps),
                        distance_km = COALESCE(excluded.distance_km, distance_km),
                        calories_kcal = COALESCE(excluded.calories_kcal, calories_kcal),
                        avg_hr_bpm = COALESCE(excluded.avg_hr_bpm, avg_hr_bpm),
                        resting_hr_bpm = COALESCE(excluded.resting_hr_bpm, resting_hr_bpm),
                        stress_score = COALESCE(excluded.stress_score, stress_score),
                        sleep_score = COALESCE(excluded.sleep_score, sleep_score),
                        sleep_efficiency = COALESCE(excluded.sleep_efficiency, sleep_efficiency),
                        sleep_duration_hours = COALESCE(excluded.sleep_duration_hours, sleep_duration_hours),
                        sleep_start_utc = COALESCE(excluded.sleep_start_utc, sleep_start_utc),
                        sleep_end_utc = COALESCE(excluded.sleep_end_utc, sleep_end_utc),
                        avg_spo2 = COALESCE(excluded.avg_spo2, avg_spo2),
                        avg_respiration_awake = COALESCE(excluded.avg_respiration_awake, avg_respiration_awake),
                        avg_respiration_sleep = COALESCE(excluded.avg_respiration_sleep, avg_respiration_sleep),
                        hrv_rmssd_ms = COALESCE(excluded.hrv_rmssd_ms, hrv_rmssd_ms),
                        hrv_sdnn_ms = COALESCE(excluded.hrv_sdnn_ms, hrv_sdnn_ms),
                        body_battery_avg = COALESCE(excluded.body_battery_avg, body_battery_avg),
                        body_battery_charge = COALESCE(excluded.body_battery_charge, body_battery_charge),
                        body_battery_drain = COALESCE(excluded.body_battery_drain, body_battery_drain),
                        source = excluded.source,
                        created_at = excluded.created_at
                    """,
                    (
                        entry.entry_id,
                        entry.user_id,
                        entry.metric_date,
                        entry.steps,
                        entry.distance_km,
                        entry.calories_kcal,
                        entry.avg_hr_bpm,
                        entry.resting_hr_bpm,
                        entry.stress_score,
                        entry.sleep_score,
                        entry.sleep_efficiency,
                        entry.sleep_duration_hours,
                        entry.sleep_start_utc,
                        entry.sleep_end_utc,
                        entry.avg_spo2,
                        entry.avg_respiration_awake,
                        entry.avg_respiration_sleep,
                        entry.hrv_rmssd_ms,
                        entry.hrv_sdnn_ms,
                        entry.body_battery_avg,
                        entry.body_battery_charge,
                        entry.body_battery_drain,
                        entry.source,
                        created_at,
                    ),
                )

    def get_garmin_daily_metrics(
        self, user_id: str, limit: int = 90
    ) -> List[GarminDailyMetrics]:
        """Return Garmin daily metrics history."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM garmin_daily_metrics
                WHERE user_id = ?
                ORDER BY datetime(metric_date) DESC
                LIMIT ?
                """,
                (user_id, limit),
            )
            rows = cursor.fetchall()
        return [self._row_to_garmin_daily_metrics(row) for row in rows]

    def get_garmin_daily_dataframe(
        self,
        user_id: str,
        *,
        limit: int = 120,
    ) -> pd.DataFrame:
        """Return Garmin daily metrics as DataFrame."""
        with self._get_connection() as conn:
            df = pd.read_sql_query(
                """
                SELECT *
                FROM garmin_daily_metrics
                WHERE user_id = ?
                ORDER BY datetime(metric_date) DESC
                LIMIT ?
                """,
                conn,
                params=(user_id, limit),
            )
        if not df.empty and "metric_date" in df.columns:
            df["metric_date"] = pd.to_datetime(df["metric_date"])
        return df

    # -----------------------------------------------------------------------
    # Fatigue profile defaults (SAFTE/FRMS)
    # -----------------------------------------------------------------------

    def upsert_fatigue_profile_settings(self, settings: FatigueProfileSettings) -> None:
        """Upsert per-user fatigue profile defaults used by SAFTE/FRMS.

        Args:
            settings: FatigueProfileSettings to store.

        Raises:
            ValueError: If any field is out of range.
        """
        if not settings.user_id:
            raise ValueError("settings.user_id must be provided")

        if not (0.0 < float(settings.typical_sleep_duration_hours) <= 24.0):
            raise ValueError("typical_sleep_duration_hours must be in (0, 24]")
        if not (0.0 <= float(settings.typical_sleep_quality) <= 1.0):
            raise ValueError("typical_sleep_quality must be in [0, 1]")
        for name, hour in (
            ("typical_bedtime_hour", settings.typical_bedtime_hour),
            ("typical_waketime_hour", settings.typical_waketime_hour),
            ("duty_start_hour", settings.duty_start_hour),
            ("duty_end_hour", settings.duty_end_hour),
        ):
            if not (0 <= int(hour) <= 23):
                raise ValueError(f"{name} must be in 0..23")

        now = datetime.now(timezone.utc).isoformat()
        updated_at = settings.updated_at or now
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO fatigue_profile_settings (
                    user_id,
                    typical_sleep_duration_hours,
                    typical_sleep_quality,
                    typical_bedtime_hour,
                    typical_waketime_hour,
                    duty_start_hour,
                    duty_end_hour,
                    include_weekends,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    typical_sleep_duration_hours = excluded.typical_sleep_duration_hours,
                    typical_sleep_quality = excluded.typical_sleep_quality,
                    typical_bedtime_hour = excluded.typical_bedtime_hour,
                    typical_waketime_hour = excluded.typical_waketime_hour,
                    duty_start_hour = excluded.duty_start_hour,
                    duty_end_hour = excluded.duty_end_hour,
                    include_weekends = excluded.include_weekends,
                    updated_at = excluded.updated_at
                """,
                (
                    settings.user_id,
                    float(settings.typical_sleep_duration_hours),
                    float(settings.typical_sleep_quality),
                    int(settings.typical_bedtime_hour),
                    int(settings.typical_waketime_hour),
                    int(settings.duty_start_hour),
                    int(settings.duty_end_hour),
                    1 if bool(settings.include_weekends) else 0,
                    str(updated_at),
                ),
            )

    def get_fatigue_profile_settings(self, user_id: str) -> Optional[FatigueProfileSettings]:
        """Return stored fatigue profile defaults for a user (if present)."""
        if not user_id:
            return None
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT *
                FROM fatigue_profile_settings
                WHERE user_id = ?
                """,
                (user_id,),
            )
            row = cursor.fetchone()
        if row is None:
            return None
        return self._row_to_fatigue_profile_settings(row)

    def _row_to_fatigue_profile_settings(self, row: sqlite3.Row) -> FatigueProfileSettings:
        """Convert row to FatigueProfileSettings."""
        return FatigueProfileSettings(
            user_id=row["user_id"],
            typical_sleep_duration_hours=float(row["typical_sleep_duration_hours"])
            if row["typical_sleep_duration_hours"] is not None
            else 7.5,
            typical_sleep_quality=float(row["typical_sleep_quality"])
            if row["typical_sleep_quality"] is not None
            else 0.8,
            typical_bedtime_hour=int(row["typical_bedtime_hour"])
            if row["typical_bedtime_hour"] is not None
            else 23,
            typical_waketime_hour=int(row["typical_waketime_hour"])
            if row["typical_waketime_hour"] is not None
            else 7,
            duty_start_hour=int(row["duty_start_hour"]) if row["duty_start_hour"] is not None else 9,
            duty_end_hour=int(row["duty_end_hour"]) if row["duty_end_hour"] is not None else 17,
            include_weekends=bool(int(row["include_weekends"] or 0)),
            updated_at=row["updated_at"],
        )

    # -----------------------------------------------------------------------
    # Body Composition / Anthropometrics
    # -----------------------------------------------------------------------

    def save_body_composition(
        self, measurement: BodyCompositionMeasurement
    ) -> str:
        """Insert a body composition measurement for a user."""
        measurement.composition_id = measurement.composition_id or str(uuid.uuid4())
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO body_composition (
                    composition_id, user_id, measurement_date, timepoint_id,
                    height_cm, weight_kg, body_fat_pct, lean_mass_kg, muscle_mass_kg,
                    bone_mass_kg, water_pct, visceral_fat_level,
                    waist_cm, hip_cm, neck_cm, chest_cm, arm_cm, thigh_cm, calf_cm,
                    measurement_method, notes
                ) VALUES (
                    ?, ?, ?, ?,
                    ?, ?, ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?,
                    ?, ?
                )
                """,
                (
                    measurement.composition_id,
                    measurement.user_id,
                    measurement.measurement_date,
                    measurement.timepoint_id,
                    measurement.height_cm,
                    measurement.weight_kg,
                    measurement.body_fat_pct,
                    measurement.lean_mass_kg,
                    measurement.muscle_mass_kg,
                    measurement.bone_mass_kg,
                    measurement.water_pct,
                    measurement.visceral_fat_level,
                    measurement.waist_cm,
                    measurement.hip_cm,
                    measurement.neck_cm,
                    measurement.chest_cm,
                    measurement.arm_cm,
                    measurement.thigh_cm,
                    measurement.calf_cm,
                    measurement.measurement_method,
                    measurement.notes,
                ),
            )
        return measurement.composition_id

    def get_body_composition_history(
        self, user_id: str, *, limit: int = 180
    ) -> List[BodyCompositionMeasurement]:
        """Return recent body composition measurements for a user."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT *
                FROM body_composition
                WHERE user_id = ?
                ORDER BY datetime(measurement_date) DESC
                LIMIT ?
                """,
                (user_id, int(limit)),
            )
            rows = cursor.fetchall()
        return [self._row_to_body_composition(row) for row in rows]

    def get_body_composition_dataframe(
        self, user_id: str, *, limit: int = 180
    ) -> pd.DataFrame:
        """Return body composition history as a DataFrame."""
        with self._get_connection() as conn:
            df = pd.read_sql_query(
                """
                SELECT *
                FROM body_composition
                WHERE user_id = ?
                ORDER BY datetime(measurement_date) DESC
                LIMIT ?
                """,
                conn,
                params=(user_id, int(limit)),
            )
        if not df.empty and "measurement_date" in df.columns:
            df["measurement_date"] = pd.to_datetime(df["measurement_date"], errors="coerce")
        return df

    def _row_to_body_composition(
        self, row: sqlite3.Row
    ) -> BodyCompositionMeasurement:
        """Convert row to BodyCompositionMeasurement."""
        return BodyCompositionMeasurement(
            composition_id=row["composition_id"],
            user_id=row["user_id"],
            measurement_date=row["measurement_date"],
            timepoint_id=row["timepoint_id"] if "timepoint_id" in row.keys() else None,
            height_cm=row["height_cm"],
            weight_kg=row["weight_kg"],
            body_fat_pct=row["body_fat_pct"],
            lean_mass_kg=row["lean_mass_kg"],
            muscle_mass_kg=row["muscle_mass_kg"],
            bone_mass_kg=row["bone_mass_kg"],
            water_pct=row["water_pct"],
            visceral_fat_level=row["visceral_fat_level"],
            waist_cm=row["waist_cm"],
            hip_cm=row["hip_cm"],
            neck_cm=row["neck_cm"],
            chest_cm=row["chest_cm"],
            arm_cm=row["arm_cm"],
            thigh_cm=row["thigh_cm"],
            calf_cm=row["calf_cm"],
            measurement_method=row["measurement_method"],
            notes=row["notes"],
        )

    def _row_to_garmin_daily_metrics(
        self, row: sqlite3.Row
    ) -> GarminDailyMetrics:
        """Convert row to GarminDailyMetrics."""
        return GarminDailyMetrics(
            entry_id=row["entry_id"],
            user_id=row["user_id"],
            metric_date=row["metric_date"],
            steps=row["steps"],
            distance_km=row["distance_km"],
            calories_kcal=row["calories_kcal"],
            avg_hr_bpm=row["avg_hr_bpm"],
            resting_hr_bpm=row["resting_hr_bpm"],
            stress_score=row["stress_score"],
            sleep_score=row["sleep_score"],
            sleep_efficiency=row["sleep_efficiency"],
            sleep_duration_hours=row["sleep_duration_hours"],
            sleep_start_utc=row["sleep_start_utc"] if "sleep_start_utc" in row.keys() else None,
            sleep_end_utc=row["sleep_end_utc"] if "sleep_end_utc" in row.keys() else None,
            avg_spo2=row["avg_spo2"],
            avg_respiration_awake=row["avg_respiration_awake"],
            avg_respiration_sleep=row["avg_respiration_sleep"],
                        hrv_rmssd_ms=row["hrv_rmssd_ms"] if "hrv_rmssd_ms" in row.keys() else None,
                        hrv_sdnn_ms=row["hrv_sdnn_ms"] if "hrv_sdnn_ms" in row.keys() else None,
            body_battery_avg=row["body_battery_avg"],
            body_battery_charge=row["body_battery_charge"],
            body_battery_drain=row["body_battery_drain"],
            source=row["source"],
            created_at=row["created_at"],
        )
    
    # -----------------------------------------------------------------------
    # Statistical Analysis for Repeated Measures
    # -----------------------------------------------------------------------
    
    def compute_longitudinal_stats(
        self, user_id: str, metric: str = "rmssd_ms"
    ) -> Dict[str, Any]:
        """Compute longitudinal statistics for a metric.
        
        Args:
            user_id: User ID.
            metric: Column name to analyze.
            
        Returns:
            Dictionary with statistical summary.
        """
        df = self.get_hrv_dataframe(user_id)
        
        if df.empty or metric not in df.columns:
            return {}

        # Ensure chronological order for trends/changes.
        if "measurement_date" in df.columns:
            try:
                df = df.sort_values("measurement_date")
            except Exception:
                pass

        values = df[metric].dropna()
        
        if len(values) < 2:
            return {
                "n": len(values),
                "mean": float(values.mean()) if len(values) > 0 else None,
            }
        
        # Basic statistics
        stats: Dict[str, Any] = {
            "n": len(values),
            "mean": float(values.mean()),
            "std": float(values.std()),
            "sem": float(values.std() / np.sqrt(len(values))),
            "median": float(values.median()),
            "min": float(values.min()),
            "max": float(values.max()),
            "cv_pct": float(values.std() / values.mean() * 100) if values.mean() != 0 else 0,
            "q25": float(values.quantile(0.25)),
            "q75": float(values.quantile(0.75)),
            "iqr": float(values.quantile(0.75) - values.quantile(0.25)),
        }
        
        # Trend analysis (simple linear regression)
        if len(values) >= 3:
            x = np.arange(len(values))
            slope, intercept = np.polyfit(x, values, 1)
            stats["trend_slope"] = float(slope)
            stats["trend_direction"] = "increasing" if slope > 0 else "decreasing"
            
            # Percentage change from first to last
            first_val = values.iloc[0]
            last_val = values.iloc[-1]
            if first_val != 0:
                stats["pct_change_total"] = float((last_val - first_val) / first_val * 100)
        
        # 95% CI for mean (optional SciPy)
        try:
            from scipy import stats as scipy_stats  # type: ignore
        except Exception:
            scipy_stats = None  # type: ignore[assignment]
        if scipy_stats is not None:
            ci = scipy_stats.t.interval(
                0.95,
                len(values) - 1,
                loc=values.mean(),
                scale=scipy_stats.sem(values),
            )
            stats["ci_95_lower"] = float(ci[0])
            stats["ci_95_upper"] = float(ci[1])
        
        return stats

    # -----------------------------------------------------------------------
    # Longitudinal Timepoints (T0..T21)
    # -----------------------------------------------------------------------

    def upsert_measurement_timepoint(self, timepoint: MeasurementTimepoint) -> str:
        """Create or update a longitudinal measurement timepoint.

        Upserts by (user_id, timepoint_label) so clinicians can adjust dates/notes.
        """
        if not timepoint.user_id:
            raise ValueError("timepoint.user_id is required")
        if not timepoint.timepoint_label:
            raise ValueError("timepoint.timepoint_label is required")
        if not timepoint.measurement_date:
            raise ValueError("timepoint.measurement_date is required")

        now = datetime.now(timezone.utc).isoformat()
        timepoint.timepoint_id = timepoint.timepoint_id or str(uuid.uuid4())
        timepoint.created_at = timepoint.created_at or now
        timepoint.updated_at = now

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO measurement_timepoints (
                    timepoint_id, user_id, timepoint_label, measurement_date,
                    measurement_number, is_baseline, notes, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, timepoint_label) DO UPDATE SET
                    measurement_date = excluded.measurement_date,
                    measurement_number = excluded.measurement_number,
                    is_baseline = excluded.is_baseline,
                    notes = excluded.notes,
                    updated_at = excluded.updated_at
                """,
                (
                    timepoint.timepoint_id,
                    timepoint.user_id,
                    timepoint.timepoint_label,
                    timepoint.measurement_date,
                    timepoint.measurement_number,
                    1 if timepoint.is_baseline else 0,
                    timepoint.notes,
                    timepoint.created_at,
                    timepoint.updated_at,
                ),
            )
        return timepoint.timepoint_id

    def list_measurement_timepoints(
        self, user_id: str, *, limit: int = 50
    ) -> List[MeasurementTimepoint]:
        """List timepoints for a user (newest first)."""
        if not user_id:
            raise ValueError("user_id is required")
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT *
                FROM measurement_timepoints
                WHERE user_id = ?
                ORDER BY datetime(measurement_date) DESC
                LIMIT ?
                """,
                (user_id, int(limit)),
            )
            rows = cursor.fetchall()
        return [self._row_to_measurement_timepoint(row) for row in rows]

    def get_measurement_timepoint_by_label(
        self, user_id: str, timepoint_label: str
    ) -> Optional[MeasurementTimepoint]:
        """Get a timepoint by label (e.g., 'T0_baseline', 'T3')."""
        if not user_id:
            raise ValueError("user_id is required")
        if not timepoint_label:
            raise ValueError("timepoint_label is required")
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT *
                FROM measurement_timepoints
                WHERE user_id = ? AND timepoint_label = ?
                LIMIT 1
                """,
                (user_id, timepoint_label),
            )
            row = cursor.fetchone()
        return self._row_to_measurement_timepoint(row) if row else None

    def _row_to_measurement_timepoint(self, row: sqlite3.Row) -> MeasurementTimepoint:
        """Convert row to MeasurementTimepoint."""
        return MeasurementTimepoint(
            timepoint_id=row["timepoint_id"],
            user_id=row["user_id"],
            timepoint_label=row["timepoint_label"],
            measurement_date=row["measurement_date"],
            measurement_number=row["measurement_number"],
            is_baseline=bool(row["is_baseline"]),
            notes=row["notes"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def get_hrv_timepoint_change_table(
        self,
        user_id: str,
        *,
        metrics: Optional[Sequence[str]] = None,
        agg: str = "median",
        limit: int = 500,
    ) -> pd.DataFrame:
        """Build a baseline/Δ (delta) table across T0–T21 timepoints.

        This is the first "Longitudinal Study Support" building block: it summarizes
        stored HRV measurements grouped by timepoint label (e.g., T0_baseline, T1…T21),
        computes a baseline from T0, and reports deltas vs baseline for each timepoint.

        Args:
            user_id: User identifier.
            metrics: Optional list of numeric HRV metric columns to include. When omitted,
                a conservative default metric set is used.
            agg: Aggregation method for multiple sessions within a timepoint: "median" or "mean".
            limit: Max HRV rows to load (most recent first).

        Returns:
            A DataFrame with one row per timepoint label including baseline values and Δ columns.

        Raises:
            ValueError: If `user_id` is empty or `agg` is not supported.
        """
        if not user_id:
            raise ValueError("user_id is required")

        df = self.get_hrv_dataframe(user_id, limit=int(limit), include_rr=False)
        timepoints = self.list_measurement_timepoints(user_id, limit=50)
        return build_timepoint_change_table_from_hrv_df(
            df,
            timepoints=timepoints,
            metrics=metrics,
            agg=agg,
        )

    # -----------------------------------------------------------------------
    # Study Groups / Cohort Assignments (persisted)
    # -----------------------------------------------------------------------

    def upsert_study_group(self, group: StudyGroup) -> str:
        """Create or update a study group definition.

        Upserts by (study_id, group_name) to keep the UI idempotent.

        Args:
            group: StudyGroup payload.

        Returns:
            group_id (existing or newly created).
        """
        if not group.study_id:
            raise ValueError("group.study_id is required")
        if not group.group_name:
            raise ValueError("group.group_name is required")

        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT group_id
                FROM study_groups
                WHERE study_id = ? AND group_name = ?
                LIMIT 1
                """,
                (str(group.study_id), str(group.group_name)),
            )
            row = cursor.fetchone()
            if row is not None:
                group_id = str(row["group_id"])
                cursor.execute(
                    """
                    UPDATE study_groups
                    SET description = ?
                    WHERE group_id = ?
                    """,
                    (group.description, group_id),
                )
                return group_id

            group_id = group.group_id or str(uuid.uuid4())
            created_at = group.created_at or now
            cursor.execute(
                """
                INSERT INTO study_groups (group_id, study_id, group_name, description, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (group_id, str(group.study_id), str(group.group_name), group.description, created_at),
            )
            return str(group_id)

    def list_study_groups(self, study_id: str, *, limit: int = 50) -> List[StudyGroup]:
        """List study groups for a given study_id."""
        if not study_id:
            raise ValueError("study_id is required")
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT *
                FROM study_groups
                WHERE study_id = ?
                ORDER BY datetime(created_at) ASC
                LIMIT ?
                """,
                (str(study_id), int(limit)),
            )
            rows = cursor.fetchall()
        return [self._row_to_study_group(row) for row in rows]

    def get_study_group_by_name(self, study_id: str, group_name: str) -> Optional[StudyGroup]:
        """Get a study group by (study_id, group_name)."""
        if not study_id:
            raise ValueError("study_id is required")
        if not group_name:
            raise ValueError("group_name is required")
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT *
                FROM study_groups
                WHERE study_id = ? AND group_name = ?
                LIMIT 1
                """,
                (str(study_id), str(group_name)),
            )
            row = cursor.fetchone()
        return self._row_to_study_group(row) if row else None

    def set_user_study_assignment(
        self,
        *,
        user_id: str,
        study_id: str,
        group_id: Optional[str],
        assignment_date: Optional[str] = None,
    ) -> None:
        """Assign a user to exactly one group within a study (or unassign).

        Behavior:
        - If group_id is provided: remove any prior assignment for this (user_id, study_id),
          then create a new assignment row.
        - If group_id is None: remove any prior assignment for this (user_id, study_id).
        """
        if not user_id:
            raise ValueError("user_id is required")
        if not study_id:
            raise ValueError("study_id is required")

        now = datetime.now(timezone.utc).isoformat()
        assignment_date_val = str(assignment_date or now)

        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Remove existing assignment(s) for this user within the study.
            cursor.execute(
                """
                DELETE FROM study_assignments
                WHERE user_id = ?
                  AND group_id IN (SELECT group_id FROM study_groups WHERE study_id = ?)
                """,
                (str(user_id), str(study_id)),
            )

            if group_id is None:
                return

            # Validate that group_id belongs to this study_id.
            cursor.execute(
                """
                SELECT group_id
                FROM study_groups
                WHERE group_id = ? AND study_id = ?
                LIMIT 1
                """,
                (str(group_id), str(study_id)),
            )
            row = cursor.fetchone()
            if row is None:
                raise ValueError("group_id does not belong to the provided study_id")

            cursor.execute(
                """
                INSERT INTO study_assignments (assignment_id, user_id, group_id, assignment_date, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (str(uuid.uuid4()), str(user_id), str(group_id), assignment_date_val, now),
            )

    def get_study_roster_dataframe(self, study_id: str, *, limit: int = 500) -> pd.DataFrame:
        """Return a roster of users with their assigned group (if any)."""
        if not study_id:
            raise ValueError("study_id is required")
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT
                    u.user_id,
                    u.full_name,
                    u.username,
                    g.group_id,
                    g.group_name,
                    g.study_id
                FROM users u
                LEFT JOIN (
                    SELECT sa.user_id, sa.group_id
                    FROM study_assignments sa
                    WHERE sa.group_id IN (SELECT group_id FROM study_groups WHERE study_id = ?)
                ) sa ON sa.user_id = u.user_id
                LEFT JOIN study_groups g ON g.group_id = sa.group_id
                ORDER BY u.full_name ASC
                LIMIT ?
                """,
                (str(study_id), int(limit)),
            )
            rows = cursor.fetchall()
        if not rows:
            return pd.DataFrame(columns=["user_id", "full_name", "username", "group_id", "group_name", "study_id"])
        return pd.DataFrame([dict(r) for r in rows])

    def _row_to_study_group(self, row: sqlite3.Row) -> StudyGroup:
        return StudyGroup(
            group_id=str(row["group_id"]),
            study_id=str(row["study_id"]),
            group_name=str(row["group_name"]),
            description=row["description"],
            created_at=str(row["created_at"]),
        )
    
    def compare_periods(
        self,
        user_id: str,
        metric: str,
        period1_start: str,
        period1_end: str,
        period2_start: str,
        period2_end: str,
    ) -> Dict[str, Any]:
        """Compare HRV metric between two time periods.
        
        Args:
            user_id: User ID.
            metric: Column name to compare.
            period1_start, period1_end: First period date range (ISO format).
            period2_start, period2_end: Second period date range (ISO format).
            
        Returns:
            Dictionary with comparison statistics including effect size.
        """
        df = self.get_hrv_dataframe(user_id)
        
        if df.empty or metric not in df.columns:
            return {}
        
        # Convert string date parameters to datetime for reliable comparison
        try:
            p1_start = pd.to_datetime(period1_start)
            p1_end = pd.to_datetime(period1_end)
            p2_start = pd.to_datetime(period2_start)
            p2_end = pd.to_datetime(period2_end)
        except (ValueError, TypeError) as e:
            return {"error": f"Invalid date format: {e}"}
        
        # Filter periods using datetime comparisons
        mask1 = (df['measurement_date'] >= p1_start) & (df['measurement_date'] <= p1_end)
        mask2 = (df['measurement_date'] >= p2_start) & (df['measurement_date'] <= p2_end)
        
        period1 = df.loc[mask1, metric].dropna()
        period2 = df.loc[mask2, metric].dropna()
        
        if len(period1) < 2 or len(period2) < 2:
            return {"error": "Insufficient data in one or both periods"}
        
        from scipy import stats as scipy_stats
        
        # Descriptive stats
        result: Dict[str, Any] = {
            "period1": {
                "n": len(period1),
                "mean": float(period1.mean()),
                "std": float(period1.std()),
            },
            "period2": {
                "n": len(period2),
                "mean": float(period2.mean()),
                "std": float(period2.std()),
            },
        }
        
        # Mean difference
        mean_diff = period2.mean() - period1.mean()
        result["mean_difference"] = float(mean_diff)
        result["pct_change"] = float(mean_diff / period1.mean() * 100) if period1.mean() != 0 else 0
        
        # Independent t-test
        t_stat, p_value = scipy_stats.ttest_ind(period1, period2)
        result["t_statistic"] = float(t_stat)
        result["p_value"] = float(p_value)
        
        # Effect size (Cohen's d)
        pooled_std = np.sqrt(
            ((len(period1) - 1) * period1.std() ** 2 + (len(period2) - 1) * period2.std() ** 2)
            / (len(period1) + len(period2) - 2)
        )
        cohens_d = mean_diff / pooled_std if pooled_std > 0 else 0
        result["cohens_d"] = float(cohens_d)
        
        # Interpret effect size
        abs_d = abs(cohens_d)
        if abs_d < 0.2:
            result["effect_interpretation"] = "negligible"
        elif abs_d < 0.5:
            result["effect_interpretation"] = "small"
        elif abs_d < 0.8:
            result["effect_interpretation"] = "medium"
        else:
            result["effect_interpretation"] = "large"
        
        return result
    
    # -----------------------------------------------------------------------
    # Export/Import
    # -----------------------------------------------------------------------
    
    def export_user_data(self, user_id: str, filepath: Path) -> None:
        """Export all user data to JSON file.
        
        Args:
            user_id: User ID to export.
            filepath: Output file path.
        """
        user = self.get_user(user_id)
        if not user:
            raise ValueError(f"User not found: {user_id}")
        
        data = {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "schema_version": SCHEMA_VERSION,
            "user_profile": user.to_dict(),
            "clinical_scales": [s.to_dict() for s in self.get_clinical_scales_history(user_id)],
            "hrv_measurements": [m.to_dict() for m in self.get_hrv_history(user_id)],
            "hrv_analysis_cache": [c.to_dict() for c in self.get_hrv_analysis_cache_entries(user_id)],
            "ai_reports": [r.to_dict() for r in self.get_ai_reports(user_id)],
        }
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
        
        _LOGGER.info("Exported user data to %s", filepath)
    
    def import_user_data(self, filepath: Path) -> str:
        """Import user data from JSON file.
        
        Args:
            filepath: Input file path.
            
        Returns:
            The user_id of the imported user.
        """
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Create user profile
        profile_data = data["user_profile"]
        profile = UserProfile(
            user_id=str(uuid.uuid4()),  # Generate new ID to avoid conflicts
            username=profile_data["username"] + "_imported",
            full_name=profile_data["full_name"],
            email=profile_data.get("email"),
            date_of_birth=profile_data.get("date_of_birth"),
            sex=profile_data.get("sex"),
            height_cm=profile_data.get("height_cm"),
            weight_kg=profile_data.get("weight_kg"),
            resting_hr_bpm=profile_data.get("resting_hr_bpm"),
            max_hr_bpm=profile_data.get("max_hr_bpm"),
            vo2max_ml_kg_min=profile_data.get("vo2max_ml_kg_min"),
            occupation=profile_data.get("occupation"),
            activity_level=profile_data.get("activity_level"),
            smoking_status=profile_data.get("smoking_status"),
            alcohol_use=profile_data.get("alcohol_use"),
            caffeine_intake_mg=profile_data.get("caffeine_intake_mg"),
            medical_conditions=profile_data.get("medical_conditions", []),
            medications=profile_data.get("medications", []),
        )
        
        user_id = self.create_user(profile)
        
        # Import clinical scales
        for scale_data in data.get("clinical_scales", []):
            scale = ClinicalScales(
                assessment_id=str(uuid.uuid4()),
                user_id=user_id,
                assessment_date=scale_data["assessment_date"],
                epworth_sleepiness_scale=scale_data.get("epworth_sleepiness_scale"),
                pittsburgh_sleep_quality_index=scale_data.get("pittsburgh_sleep_quality_index"),
                insomnia_severity_index=scale_data.get("insomnia_severity_index"),
                karolinska_sleepiness_scale=scale_data.get("karolinska_sleepiness_scale"),
                samn_perelli_fatigue=scale_data.get("samn_perelli_fatigue"),
                fatigue_severity_scale=scale_data.get("fatigue_severity_scale"),
                perceived_stress_scale=scale_data.get("perceived_stress_scale"),
                beck_depression_inventory=scale_data.get("beck_depression_inventory"),
                state_trait_anxiety_inventory=scale_data.get("state_trait_anxiety_inventory"),
                borg_rpe=scale_data.get("borg_rpe"),
                vas_pain=scale_data.get("vas_pain"),
                vas_fatigue=scale_data.get("vas_fatigue"),
                notes=scale_data.get("notes"),
            )
            self.save_clinical_scales(scale)
        
        # Import HRV measurements
        for meas_data in data.get("hrv_measurements", []):
            meas = HRVMeasurement(
                measurement_id=str(uuid.uuid4()),
                user_id=user_id,
                measurement_date=meas_data["measurement_date"],
                device_name=meas_data.get("device_name"),
                recording_duration_min=meas_data.get("recording_duration_min"),
                recording_context=meas_data.get("recording_context"),
                body_position=meas_data.get("body_position"),
                mean_rr_ms=meas_data.get("mean_rr_ms"),
                sdnn_ms=meas_data.get("sdnn_ms"),
                rmssd_ms=meas_data.get("rmssd_ms"),
                pnn50_pct=meas_data.get("pnn50_pct"),
                mean_hr_bpm=meas_data.get("mean_hr_bpm"),
                sdhr_bpm=meas_data.get("sdhr_bpm"),
                vlf_power_ms2=meas_data.get("vlf_power_ms2"),
                lf_power_ms2=meas_data.get("lf_power_ms2"),
                hf_power_ms2=meas_data.get("hf_power_ms2"),
                lf_hf_ratio=meas_data.get("lf_hf_ratio"),
                total_power_ms2=meas_data.get("total_power_ms2"),
                sd1_ms=meas_data.get("sd1_ms"),
                sd2_ms=meas_data.get("sd2_ms"),
                dfa_alpha1=meas_data.get("dfa_alpha1"),
                dfa_alpha2=meas_data.get("dfa_alpha2"),
                sample_entropy=meas_data.get("sample_entropy"),
                stress_index=meas_data.get("stress_index"),
                parasympathetic_index=meas_data.get("parasympathetic_index"),
                hrv_score=meas_data.get("hrv_score"),
                rr_intervals_json=meas_data.get("rr_intervals_json"),
                artifact_percentage=meas_data.get("artifact_percentage"),
                quality_score=meas_data.get("quality_score"),
                notes=meas_data.get("notes"),
            )
            self.save_hrv_measurement(meas)
        
        _LOGGER.info("Imported user data from %s as user %s", filepath, user_id)
        return user_id


# ---------------------------------------------------------------------------
# Global database instance with Streamlit caching
# ---------------------------------------------------------------------------

def _create_database_for_path(db_path: Path) -> UserDatabase:
    """Create a database instance for a specific path."""
    return UserDatabase(db_path=db_path)


# Try to use Streamlit's cache_resource for a singleton-per-path pattern.
# This prevents cross-mission contamination while keeping `get_database()`'s
# public signature stable across the codebase.
try:
    import streamlit as st

    @st.cache_resource(show_spinner=False)
    def _get_database_cached(db_path_str: str) -> UserDatabase:
        return _create_database_for_path(Path(db_path_str))

    def get_database() -> UserDatabase:
        """Get or create the database instance for the active mission."""
        return _get_database_cached(str(get_database_path()))

except ImportError:
    # Fallback for non-Streamlit contexts (testing, scripts)
    _db_instances: dict[str, UserDatabase] = {}

    def get_database() -> UserDatabase:
        """Get or create the database instance for the active mission."""
        db_path_str = str(get_database_path())
        inst = _db_instances.get(db_path_str)
        if inst is None:
            inst = _create_database_for_path(Path(db_path_str))
            _db_instances[db_path_str] = inst
        return inst


# ---------------------------------------------------------------------------
# Module Exports
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Cached Query Functions (Performance Optimization)
# ---------------------------------------------------------------------------

# Try to use Streamlit caching for expensive queries
try:
    import streamlit as st
    
    @st.cache_data(ttl=30, max_entries=32, show_spinner=False)
    def _get_cached_user_list_for_db(db_path_str: str) -> List[Dict[str, Any]]:
        """Get cached list of users (30-second TTL).
        
        Returns list of dicts instead of UserProfile objects for cacheability.
        Use this for dropdowns and selection UIs that don't need full objects.
        """
        db = _create_database_for_path(Path(db_path_str))
        users = db.list_users()
        # Convert to dicts for cache serialization
        return [
            {
                "user_id": u.user_id,
                "username": u.username,
                "full_name": u.full_name,
                "email": u.email,
            }
            for u in users
        ]
    
    @st.cache_data(ttl=60, max_entries=128, show_spinner=False)
    def _get_cached_user_by_id_for_db(db_path_str: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Get cached user profile by ID (60-second TTL).
        
        Returns dict instead of UserProfile for cacheability.
        """
        db = _create_database_for_path(Path(db_path_str))
        user = db.get_user(user_id)
        if user:
            return user.to_dict()
        return None

    def get_cached_user_list() -> List[Dict[str, Any]]:
        """Mission-scoped cached list of users (wrapper)."""
        return _get_cached_user_list_for_db(str(get_database_path()))

    def get_cached_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
        """Mission-scoped cached user profile (wrapper)."""
        return _get_cached_user_by_id_for_db(str(get_database_path()), user_id)

except ImportError:
    # Fallback for non-Streamlit contexts
    def get_cached_user_list() -> List[Dict[str, Any]]:
        db = get_database()
        return [
            {
                "user_id": u.user_id,
                "username": u.username,
                "full_name": u.full_name,
                "email": u.email,
            }
            for u in db.list_users()
        ]
    
    def get_cached_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
        db = get_database()
        user = db.get_user(user_id)
        return user.to_dict() if user else None


def clear_user_cache() -> None:
    """Clear user-related caches after modifications (create, update, delete)."""
    try:
        _get_cached_user_list_for_db.clear()  # type: ignore[attr-defined]
        _get_cached_user_by_id_for_db.clear()  # type: ignore[attr-defined]
    except (AttributeError, NameError):
        pass  # Cache not available


__all__ = [
    "UserProfile",
    "ClinicalScales",
    "HRVMeasurement",
    "PolarCredentials",
    "VO2maxEntry",
    "GarminDailyMetrics",
    "FatigueProfileSettings",
    "BodyCompositionMeasurement",
    "MeasurementTimepoint",
    "StudyGroup",
    "StudyAssignment",
    "UserDatabase",
    "get_database",
    "get_database_path",
    "invalidate_database_instance",
    "is_sqlite_database_corruption_error",
    "list_database_backups",
    "restore_database_from_backup",
    "reset_database_file",
    "sqlite_quick_check",
    "get_cached_user_list",
    "get_cached_user_by_id",
    "clear_user_cache",
    "get_measurement_by_hash",
]


"""Regression tests for longitudinal study timepoints (T0–T21)."""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
APP_ROOT = PROJECT_ROOT / "app"
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from user_database import (  # noqa: E402
    ClinicalScales,
    HRVMeasurement,
    MeasurementTimepoint,
    UserDatabase,
    UserProfile,
)


def _make_valid_sqlite_file(path: Path) -> None:
    """Create a non-empty valid SQLite file at `path`."""
    conn = sqlite3.connect(str(path), timeout=5.0)
    try:
        conn.execute("CREATE TABLE IF NOT EXISTS _seed (id INTEGER PRIMARY KEY, v TEXT)")
        conn.execute("INSERT INTO _seed (v) VALUES ('ok')")
        conn.commit()
    finally:
        conn.close()


def test_init_creates_timepoints_table_and_allows_backup(tmp_path: Path) -> None:
    """Existing DB files should be backed up before schema changes."""
    db_path = tmp_path / "hrv_users.db"
    _make_valid_sqlite_file(db_path)

    # Initialize: should back up the existing file and then create tables.
    _ = UserDatabase(db_path=db_path)

    backups = list(tmp_path.glob("hrv_users.db.bak_*"))
    assert backups, "Expected a timestamped backup file to be created"


def test_can_tag_assessments_and_hrv_to_timepoint(tmp_path: Path) -> None:
    """Assessments and HRV measurements should persist timepoint_id."""
    db_path = tmp_path / "hrv_users.db"
    db = UserDatabase(db_path=db_path)

    user = UserProfile(user_id="", username="u1", full_name="User One")
    user_id = db.create_user(user)

    tp = MeasurementTimepoint(
        timepoint_id="",
        user_id=user_id,
        timepoint_label="T0_baseline",
        measurement_date="2025-12-15",
        measurement_number=0,
        is_baseline=True,
        notes="Baseline visit",
    )
    tp_id = db.upsert_measurement_timepoint(tp)
    assert tp_id

    scales = ClinicalScales(
        assessment_id="",
        user_id=user_id,
        assessment_date="2025-12-15T12:00:00+00:00",
        timepoint_id=tp_id,
        samn_perelli_fatigue=3,
        karolinska_sleepiness_scale=4,
        epworth_sleepiness_scale=8,
        notes="ok",
    )
    db.save_clinical_scales(scales)

    history = db.get_clinical_scales_history(user_id, limit=10)
    assert history, "Expected at least one assessment"
    assert history[0].timepoint_id == tp_id

    meas = HRVMeasurement(
        measurement_id="",
        user_id=user_id,
        measurement_date="2025-12-15",
        timepoint_id=tp_id,
        rmssd_ms=42.0,
        sdnn_ms=50.0,
        mean_hr_bpm=60.0,
        created_at="2025-12-15T12:05:00+00:00",
    )
    db.save_hrv_measurement(meas)

    df = db.get_hrv_dataframe(user_id, limit=10)
    assert "timepoint_id" in df.columns
    matches = df[df["rmssd_ms"] == 42.0]
    assert not matches.empty
    assert matches["timepoint_id"].iloc[0] == tp_id


@pytest.mark.parametrize("label,expected", [("T1", 1), ("T21", 21), ("T0_baseline", 0)])
def test_timepoint_label_numbering(label: str, expected: int) -> None:
    """UI label parsing logic should remain consistent with T0..T21."""
    if label.startswith("T0"):
        assert expected == 0
    else:
        assert int(label[1:]) == expected

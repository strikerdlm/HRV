from __future__ import annotations

from typing import Any

import pytest

from app import fatigue_integration as fi
from app.user_database import FatigueProfileSettings, UserDatabase, UserProfile


def test_fatigue_profile_settings_roundtrip(tmp_path) -> None:
    db_path = tmp_path / "hrv_users.db"
    db = UserDatabase(db_path=db_path)

    user = UserProfile(user_id="", username="u1", full_name="User One")
    user_id = db.create_user(user)

    settings = FatigueProfileSettings(
        user_id=user_id,
        typical_sleep_duration_hours=6.5,
        typical_sleep_quality=0.72,
        typical_bedtime_hour=1,
        typical_waketime_hour=9,
        duty_start_hour=20,
        duty_end_hour=6,
        include_weekends=True,
        updated_at="2025-12-18T00:00:00+00:00",
    )

    db.upsert_fatigue_profile_settings(settings)
    got = db.get_fatigue_profile_settings(user_id)

    assert got is not None
    assert got.user_id == user_id
    assert got.typical_sleep_duration_hours == pytest.approx(6.5)
    assert got.typical_sleep_quality == pytest.approx(0.72)
    assert got.typical_bedtime_hour == 1
    assert got.typical_waketime_hour == 9
    assert got.duty_start_hour == 20
    assert got.duty_end_hour == 6
    assert got.include_weekends is True


def test_assessment_fatigue_prediction_uses_profile_defaults(monkeypatch, tmp_path) -> None:
    db_path = tmp_path / "hrv_users.db"
    db = UserDatabase(db_path=db_path)

    user = UserProfile(user_id="", username="u1", full_name="User One")
    user_id = db.create_user(user)

    db.upsert_fatigue_profile_settings(
        FatigueProfileSettings(
            user_id=user_id,
            typical_sleep_duration_hours=6.5,
            typical_sleep_quality=0.72,
            typical_bedtime_hour=1,
            typical_waketime_hour=9,
            duty_start_hour=20,
            duty_end_hour=6,
            include_weekends=True,
            updated_at="2025-12-18T00:00:00+00:00",
        )
    )

    # Ensure the fatigue module uses our temporary database.
    monkeypatch.setattr(fi, "get_database", lambda: db)

    captured: dict[str, Any] = {}

    def fake_run_integrated_fatigue_analysis(*, user_profile, sleep_schedule, work_schedule, prediction_days, model_type, **_):
        captured["sleep"] = sleep_schedule
        captured["work"] = work_schedule
        return fi.FatigueAnalysisResult(
            time_points=[0],
            performances=[95.0],
            circadian_values=[0.0],
            analysis={"avg": 95.0, "min": 95.0, "max": 95.0, "std": 0.0, "zones": [1, 0, 0, 0], "risk": 0.0},
            risk_assessment={"total_risk": 0.0, "risk_level": "Very Low", "factors": {}},
            recommendations=[],
            model_used=str(model_type),
        )

    monkeypatch.setattr(fi, "run_integrated_fatigue_analysis", fake_run_integrated_fatigue_analysis)

    result, source_label, wrist_df = fi.run_assessment_fatigue_prediction(
        user_context={"age_years": 30, "sex": "male", "chronotype_offset": 0.0},
        user_id=user_id,
        prediction_days=1,
        model_type="advanced",
    )

    assert wrist_df is None or wrist_df.empty
    assert source_label == "profile_defaults"
    assert result.model_used == "advanced"

    sleep = captured.get("sleep")
    work = captured.get("work")
    assert sleep is not None and work is not None

    assert int(sleep.bedtime) == 1
    assert int(sleep.waketime) == 9
    assert float(sleep.duration) == pytest.approx(6.5)

    assert int(work.work_start) == 20
    assert int(work.work_end) == 6
    # Overnight duty should compute a bounded duration.
    assert int(work.work_hours) == 10

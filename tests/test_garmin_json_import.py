"""Regression tests for Garmin export JSON ingestion."""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
APP_ROOT = PROJECT_ROOT / "app"
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from garmin_import import get_daily_physiology_summary, import_garmin_data  # noqa: E402
from user_database import GarminDailyMetrics, UserDatabase, UserProfile  # noqa: E402


def test_import_garmin_sleep_json_new_schema(tmp_path: Path) -> None:
    """Sleep JSON with nested sleepScores should be parsed correctly."""
    payload = [
        {
            "sleepStartTimestampGMT": "2025-12-10T02:36:00.0",
            "sleepEndTimestampGMT": "2025-12-10T09:15:00.0",
            "calendarDate": "2025-12-10",
            "sleepWindowConfirmationType": "ENHANCED_CONFIRMED_FINAL",
            "deepSleepSeconds": 4200,
            "lightSleepSeconds": 13860,
            "remSleepSeconds": 4260,
            "awakeSleepSeconds": 1620,
            "unmeasurableSeconds": 0,
            "averageRespiration": 15.43,
            "spo2SleepSummary": {
                "averageSPO2": 85.81,
                "lowestSPO2": 74,
            },
            "sleepScores": {
                "overallScore": 75,
            },
        }
    ]

    json_path = tmp_path / "2025-12-09_2025-12-17_140089360_sleepData.json"
    json_path.write_text(json.dumps(payload), encoding="utf-8")

    data = import_garmin_data(json_path=json_path)
    assert not data.sleep_df.empty

    row = data.sleep_df.iloc[0]
    assert row["date"] == "2025-12-10"
    assert int(row["total_sleep_seconds"]) == 4200 + 13860 + 4260
    assert int(row["deep_sleep_seconds"]) == 4200
    assert int(row["light_sleep_seconds"]) == 13860
    assert int(row["rem_sleep_seconds"]) == 4260
    assert int(row["awake_seconds"]) == 1620
    assert float(row["avg_respiration"]) == 15.43
    assert float(row["avg_spo2"]) == 85.81
    assert int(row["lowest_spo2"]) == 74
    assert int(row["sleep_score"]) == 75

    # Metrics should be computed during import_garmin_data()
    assert "tst_minutes" in data.sleep_df.columns
    assert float(row["tst_minutes"]) == (4200 + 13860 + 4260) / 60.0


def test_import_garmin_sleep_json_temp_filename_is_inferred(tmp_path: Path) -> None:
    """Temp filenames (e.g., tmpXXXX.json) should still parse based on content."""
    payload = [
        {
            "sleepStartTimestampGMT": "2025-12-10T02:36:00.0",
            "sleepEndTimestampGMT": "2025-12-10T09:15:00.0",
            "calendarDate": "2025-12-10",
            "deepSleepSeconds": 4200,
            "lightSleepSeconds": 13860,
            "remSleepSeconds": 4260,
            "awakeSleepSeconds": 1620,
            "sleepScores": {"overallScore": 75},
        }
    ]

    json_path = tmp_path / "tmpcbl3yx51.json"
    json_path.write_text(json.dumps(payload), encoding="utf-8")

    data = import_garmin_data(json_path=json_path)
    assert not data.sleep_df.empty
    assert data.sleep_df.iloc[0]["date"] == "2025-12-10"


def test_import_garmin_udsfile_json_daily_summary(tmp_path: Path) -> None:
    """UDSFile daily summary should populate daily metrics (steps/stress/spo2/body battery)."""
    payload = [
        {
            "userProfilePK": 140089360,
            "calendarDate": "2025-12-09",
            "totalSteps": 1000,
            "totalDistanceMeters": 800,
            "activeKilocalories": 200.0,
            "totalKilocalories": 2400.0,
            "wellnessStartTimeGmt": "2025-12-09T05:00:00.0",
            "wellnessEndTimeGmt": "2025-12-10T05:00:00.0",
            "currentDayRestingHeartRate": 60,
            "minHeartRate": 55,
            "maxHeartRate": 120,
            "minAvgHeartRate": 58,
            "maxAvgHeartRate": 111,
            "allDayStress": {
                "aggregatorList": [
                    {"type": "TOTAL", "averageStressLevel": 43},
                    {"type": "ASLEEP", "averageStressLevel": -2},
                ]
            },
            "averageSpo2Value": 88.0,
            "lowestSpo2Value": 80,
            "latestSpo2Value": 89,
            "latestSpo2ValueReadingTimeGmt": "2025-12-10T04:15:00.0",
            "respiration": {
                "avgWakingRespirationValue": 14.0,
                "latestRespirationTimeGMT": "2025-12-10T05:00:00.0",
            },
            "bodyBattery": {
                "chargedValue": 10,
                "drainedValue": 20,
                "bodyBatteryStatList": [
                    {
                        "bodyBatteryStatType": "HIGHEST",
                        "statsValue": 90,
                        "bodyBatteryStatus": "MEASURED",
                        "statTimestamp": "2025-12-10T04:00:00.0",
                    },
                    {
                        "bodyBatteryStatType": "LOWEST",
                        "statsValue": 40,
                        "bodyBatteryStatus": "MEASURED",
                        "statTimestamp": "2025-12-09T06:00:00.0",
                    },
                ],
            },
        }
    ]

    json_path = tmp_path / "UDSFile_2025-12-09_2025-12-10.json"
    json_path.write_text(json.dumps(payload), encoding="utf-8")

    data = import_garmin_data(json_path=json_path)
    assert not data.daily_summary_df.empty
    assert not data.activity_df.empty
    assert not data.stress_df.empty
    assert not data.spo2_df.empty
    assert not data.respiration_df.empty
    assert not data.body_battery_df.empty

    daily = get_daily_physiology_summary(data)
    assert not daily.empty

    row = daily.iloc[0]
    assert str(pd.to_datetime(row["date"]).date()) == "2025-12-09"
    assert int(row["steps"]) == 1000
    assert float(row["distance_km"]) == 0.8
    assert float(row["calories_kcal"]) == 200.0
    assert float(row["avg_hr"]) == (58 + 111) / 2.0
    assert float(row["avg_stress"]) == 43
    assert float(row["avg_spo2"]) == 88.0
    assert float(row["avg_respiration_awake"]) == 14.0
    assert float(row["resting_hr_bpm"]) == 60

    # Charge/drain should come from the daily summary when available.
    assert float(row["body_battery_charge"]) == 10
    assert float(row["body_battery_drain"]) == 20


def test_garmin_daily_metrics_upsert_coalesces_nulls(tmp_path: Path) -> None:
    """Upserting partial GarminDailyMetrics should not wipe existing non-null fields."""
    db_path = tmp_path / "hrv_users.db"
    db = UserDatabase(db_path=db_path)

    user = UserProfile(user_id="", username="u1", full_name="User One")
    user_id = db.create_user(user)

    base = GarminDailyMetrics(
        entry_id="",
        user_id=user_id,
        metric_date="2025-12-10",
        steps=1234,
        distance_km=5.6,
        calories_kcal=789.0,
        stress_score=33.0,
        source="json:UDSFile",
    )
    db.save_garmin_daily_metrics([base])

    # Partial update: only sleep fields present.
    patch = GarminDailyMetrics(
        entry_id="",
        user_id=user_id,
        metric_date="2025-12-10",
        sleep_score=80.0,
        sleep_efficiency=90.0,
        sleep_duration_hours=7.5,
        source="json:sleepData",
    )
    db.save_garmin_daily_metrics([patch])

    df = db.get_garmin_daily_dataframe(user_id, limit=10)
    assert not df.empty
    row = df[df["metric_date"].dt.date == date(2025, 12, 10)].iloc[0]

    assert int(row["steps"]) == 1234
    assert float(row["distance_km"]) == 5.6
    assert float(row["calories_kcal"]) == 789.0
    assert float(row["stress_score"]) == 33.0

    assert float(row["sleep_score"]) == 80.0
    assert float(row["sleep_efficiency"]) == 90.0
    assert float(row["sleep_duration_hours"]) == 7.5

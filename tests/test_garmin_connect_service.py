from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

import app.garmin_connect_service as gcs


def test_fetch_garmin_daily_metrics_with_stub(monkeypatch) -> None:
    """Ensure normalization populates core fields without hitting the network."""

    class StubClient:
        def get_user_summary(self, day_iso: str):
            return {
                "totalSteps": 12345,
                "totalDistanceMeters": 3210,
                "totalKilocalories": 2100,
                "restingHeartRate": 52,
            }

        def get_sleep_data(self, day_iso: str):
            start = datetime(2025, 1, 1, 23, 0, tzinfo=timezone.utc).timestamp() * 1000
            end = datetime(2025, 1, 2, 7, 0, tzinfo=timezone.utc).timestamp() * 1000
            return {
                "sleepDurationInSeconds": 8 * 3600,
                "sleepEfficiency": 92,
                "overallScore": 78,
                "sleepStartTimestampGMT": start,
                "sleepEndTimestampGMT": end,
                "deepSleepSeconds": 90 * 60,
                "remSleepSeconds": 100 * 60,
                "lightSleepSeconds": 200 * 60,
                "awakeSleepSeconds": 30 * 60,
            }

        def get_all_day_stress(self, day_iso: str):
            return {"overallStressLevel": 28}

        def get_respiration_data(self, day_iso: str):
            return {"awakeRespirationAvg": 15, "sleepRespirationAvg": 13}

        def get_spo2_data(self, day_iso: str):
            return {"avgSpO2Value": 97}

        def get_body_battery(self, day_iso: str):
            return [{"bodyBatteryValue": 72, "charged": 12, "drained": 18}]

        def get_hrv_data(self, day_iso: str):
            return {"rmssd": 55, "sdnn": 88}

        def logout(self):
            return None

    class StubCtx:
        def __enter__(self):
            return StubClient()

        def __exit__(self, exc_type, exc, tb):
            return None

    monkeypatch.setenv("GARMIN_EMAIL", "stub@example.com")
    monkeypatch.setenv("GARMIN_PASSWORD", "pass123")
    monkeypatch.setattr(gcs, "GarminConnectClient", StubCtx)

    records = gcs.fetch_garmin_daily_metrics("user123", days=1)
    assert len(records) == 1
    rec = records[0]
    assert rec.metric_date is not None
    assert rec.steps == 12345
    assert rec.resting_hr_bpm == 52
    assert rec.sleep_duration_hours == 8.0
    assert rec.sleep_efficiency == 0.92
    assert rec.sleep_score == 78
    assert rec.sleep_start_utc and rec.sleep_end_utc
    assert rec.sleep_deep_minutes == 90
    assert rec.sleep_rem_minutes == 100
    assert rec.sleep_light_minutes == 200
    assert rec.sleep_awake_minutes == 30
    assert rec.hrv_rmssd_ms == 55
    assert rec.hrv_sdnn_ms == 88
    assert rec.avg_spo2 == 97


def test_summarize_garmin_daily() -> None:
    sample = [
        gcs.GarminDailyMetrics(  # type: ignore[attr-defined]
            entry_id="1",
            user_id="u",
            metric_date="2025-01-01",
            steps=1000,
        ),
        gcs.GarminDailyMetrics(  # type: ignore[attr-defined]
            entry_id="2",
            user_id="u",
            metric_date="2025-01-02",
            steps=2000,
        ),
    ]
    summary = gcs.summarize_garmin_daily(sample)
    assert summary["count"] == 2
    assert "2025-01-01" in summary["dates"]
    assert "2025-01-02" in summary["dates"]
    assert summary["steps_mean"] == 1500.0

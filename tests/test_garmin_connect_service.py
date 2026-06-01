from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd
import pytest

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
        def __init__(self, email=None, password=None):
            self.email = email
            self.password = password

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


# ---------------------------------------------------------------------------
# Credential resolution: explicit (UI-entered) creds take precedence over env,
# falling back to the environment/.env when not fully supplied.
# ---------------------------------------------------------------------------


def test_resolve_credentials_prefers_explicit_over_env(monkeypatch) -> None:
    monkeypatch.setattr(gcs, "_env_credentials", lambda **_kw: ("env@example.com", "envpass"))
    assert gcs._resolve_credentials("ui@example.com", "uipass") == ("ui@example.com", "uipass")


def test_resolve_credentials_falls_back_to_env_when_none(monkeypatch) -> None:
    monkeypatch.setattr(gcs, "_env_credentials", lambda **_kw: ("env@example.com", "envpass"))
    assert gcs._resolve_credentials() == ("env@example.com", "envpass")


def test_resolve_credentials_partial_explicit_falls_back_to_env(monkeypatch) -> None:
    """Only an email (no password) must not be treated as complete creds."""
    monkeypatch.setattr(gcs, "_env_credentials", lambda **_kw: ("env@example.com", "envpass"))
    assert gcs._resolve_credentials("ui@example.com", None) == ("env@example.com", "envpass")


def test_resolve_credentials_missing_raises(monkeypatch) -> None:
    def _raise(**_kw):
        raise gcs.GarminAuthError("missing")

    monkeypatch.setattr(gcs, "_env_credentials", _raise)
    with pytest.raises(gcs.GarminAuthError):
        gcs._resolve_credentials()


def test_fetch_passes_explicit_credentials_to_client(monkeypatch) -> None:
    """UI-entered creds must reach GarminConnectClient, not silently use env."""
    captured: dict = {}

    class StubClient:
        def get_stats(self, day_iso: str):
            return {"totalSteps": 999, "restingHeartRate": 50}

        def get_sleep_data(self, day_iso: str):
            return {}

        def logout(self):
            return None

    class StubCtx:
        def __init__(self, email=None, password=None):
            captured["email"] = email
            captured["password"] = password

        def __enter__(self):
            return StubClient()

        def __exit__(self, exc_type, exc, tb):
            return None

    # Ensure env is NOT what gets used.
    monkeypatch.delenv("GARMIN_EMAIL", raising=False)
    monkeypatch.delenv("GARMIN_PASSWORD", raising=False)
    monkeypatch.setattr(gcs, "GarminConnectClient", StubCtx)

    records = gcs.fetch_garmin_daily_metrics(
        "user123", days=1, email="ui@example.com", password="uipass"
    )
    assert captured["email"] == "ui@example.com"
    assert captured["password"] == "uipass"
    assert len(records) == 1
    assert records[0].steps == 999


def test_login_and_get_display_name(monkeypatch) -> None:
    class StubClient:
        def get_full_name(self):
            return "Diego Malpica"

        def logout(self):
            return None

    class StubCtx:
        def __init__(self, email=None, password=None):
            self.email = email
            self.password = password

        def __enter__(self):
            return StubClient()

        def __exit__(self, exc_type, exc, tb):
            return None

    monkeypatch.setattr(gcs, "GarminConnectClient", StubCtx)
    assert gcs.login_and_get_display_name("ui@example.com", "uipass") == "Diego Malpica"

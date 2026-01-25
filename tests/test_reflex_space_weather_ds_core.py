# Author: Dr Diego Malpica MD

from __future__ import annotations

from datetime import timezone

import pytest


def test_parse_timestamp_from_filename_parses_datetime() -> None:
    from reflex_app.hrv_reflex.services.space_weather_ds_core import parse_timestamp_from_filename

    ts, parsed = parse_timestamp_from_filename("2025-11-06 00-43-42.txt")
    assert parsed is True
    assert ts.tzinfo == timezone.utc


def test_compute_session_metrics_from_text_basic() -> None:
    from reflex_app.hrv_reflex.services.space_weather_ds_core import QCSettings, compute_session_metrics_from_text

    # Simple, bounded RR series (ms)
    content = "\n".join(["1000", "980", "1020", "990", "1010", "995", "1005", "1000", "990", "1010"])
    qc = QCSettings(method="threshold_median", max_deviation=0.2, median_window=11)

    out = compute_session_metrics_from_text(
        filename="2025-11-06 00-43-42.txt",
        content=content,
        qc=qc,
        include_advanced=False,
    )

    assert out["session_name"].endswith(".txt")
    assert "rmssd" in out or out.get("n_intervals", 0) > 0
    assert isinstance(out["artifact_pct"], float)
    assert isinstance(out["n_rr_intervals"], int)


def test_compute_session_metrics_from_text_rejects_empty() -> None:
    from reflex_app.hrv_reflex.services.space_weather_ds_core import QCSettings, compute_session_metrics_from_text

    qc = QCSettings(method="threshold_median", max_deviation=0.2, median_window=11)
    with pytest.raises(ValueError):
        _ = compute_session_metrics_from_text(
            filename="empty.txt",
            content="",
            qc=qc,
            include_advanced=False,
        )


from __future__ import annotations

import sys
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any
from pathlib import Path

import pandas as pd

# Ensure app modules are importable in tests
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from garmin_import import convert_fit_to_csv


class _FakeMsg:
    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    def get_value(self, key: str) -> Any:
        return self._data.get(key)


class _FakeFitFile:
    def __init__(self, path: str) -> None:
        self.path = path

    def get_messages(self, name: str):
        if name != "record":
            return []
        return [
            _FakeMsg(
                {
                    "timestamp": datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
                    "heart_rate": 61,
                    "cadence": 78,
                }
            )
        ]


def test_convert_fit_to_csv_with_fake_fitfile(monkeypatch, tmp_path: Path) -> None:
    """Ensure FIT→CSV conversion returns data when messages contain values."""
    fake_module = SimpleNamespace(FitFile=_FakeFitFile)
    monkeypatch.setitem(sys.modules, "fitparse", fake_module)

    fit_path = tmp_path / "sample.fit"
    fit_path.write_bytes(b"fake-fit-bytes")

    df, csv_bytes = convert_fit_to_csv(
        fit_path,
        allowed_fields=("timestamp", "heart_rate", "cadence"),
        max_records=10,
    )

    assert not df.empty
    assert "heart_rate" in df.columns
    assert isinstance(df.loc[0, "timestamp"], pd.Timestamp)
    assert csv_bytes.startswith(b"timestamp,heart_rate,cadence")


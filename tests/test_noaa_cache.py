from __future__ import annotations

import json
from pathlib import Path
import sys

import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import noaa_space


def _make_split_spec() -> noaa_space.NOAASourceSpec:
    return noaa_space.NOAASourceSpec(
        key="test_split",
        path="dummy.json",
        title="Test split",
        description="Synthetic split-by-column dataset",
        value_columns=("flux",),
        metadata_columns=("energy",),
        split_by_column="energy",
        preferred_time_columns=("time_tag",),
    )


def _use_tmp_cache(monkeypatch: pytest.MonkeyPatch, cache_dir: Path) -> None:
    monkeypatch.setattr(noaa_space, "NOAA_SPACE_CACHE_DIR", cache_dir, raising=False)


def test_split_dataset_cache_roundtrip(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    spec = _make_split_spec()
    cache_dir = tmp_path / "cache"
    _use_tmp_cache(monkeypatch, cache_dir)
    raw_df = pd.DataFrame(
        {
            "time_tag": pd.to_datetime(
                [
                    "2024-01-01T00:00:00Z",
                    "2024-01-01T00:00:00Z",
                    "2024-01-01T01:00:00Z",
                    "2024-01-01T01:00:00Z",
                ],
                utc=True,
            ),
            "energy": ["P>10", "P>50", "P>10", "P>50"],
            "flux": [1.0, 2.0, 3.0, 4.0],
        }
    )

    noaa_space._write_cache(spec, raw_df)
    cached = noaa_space._read_cache(spec)
    assert cached is not None

    bundle = noaa_space._prepare_frame(spec, cached)
    assert set(bundle.value_columns) == {"flux_pgt_10", "flux_pgt_50"}
    assert list(bundle.frame["flux_pgt_10"]) == [1.0, 3.0]
    assert list(bundle.frame["flux_pgt_50"]) == [2.0, 4.0]


def test_legacy_processed_cache_is_ignored(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    spec = _make_split_spec()
    cache_dir = tmp_path / "cache"
    _use_tmp_cache(monkeypatch, cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / f"{spec.key}.json"

    processed_df = pd.DataFrame(
        {
            "time_tag": pd.to_datetime(["2024-01-01T00:00:00Z"], utc=True),
            "flux_pgt_10": [1.0],
        }
    )
    legacy_payload = {
        "stored_at": pd.Timestamp.now(tz="UTC").isoformat(),
        "data": processed_df.to_json(orient="table", date_format="iso"),
    }
    cache_file.write_text(json.dumps(legacy_payload), encoding="utf-8")

    assert noaa_space._read_cache(spec) is None


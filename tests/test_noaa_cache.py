from __future__ import annotations

import json
import time
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


def test_slice_noaa_bundle_time_range_filters_rows() -> None:
    spec = noaa_space.NOAASourceSpec(
        key="test_slice",
        path="dummy.json",
        title="Test slice",
        description="Synthetic dataset for time slicing",
        value_columns=("x",),
        preferred_time_columns=("time_tag",),
    )
    raw_df = pd.DataFrame(
        {
            "time_tag": pd.to_datetime(
                [
                    "2024-01-01T00:00:00Z",
                    "2024-01-01T01:00:00Z",
                    "2024-01-01T02:00:00Z",
                ],
                utc=True,
            ),
            "x": [1.0, 2.0, 3.0],
        }
    )
    bundle = noaa_space._prepare_frame(spec, raw_df)
    sliced = noaa_space.slice_noaa_bundle_time_range(
        bundle,
        start_utc=pd.Timestamp("2024-01-01T00:30:00Z"),
        end_utc=pd.Timestamp("2024-01-01T01:30:00Z"),
    )
    assert list(sliced.frame["x"]) == [2.0]
    assert sliced.frame[sliced.time_column].min() == pd.Timestamp("2024-01-01T01:00:00Z")


def test_load_noaa_space_data_times_out(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Ensure overall timeout returns quickly and records an error."""
    monkeypatch.setattr(noaa_space, "NOAA_SPACE_CACHE_DIR", tmp_path, raising=False)

    def slow_download(_spec: noaa_space.NOAASourceSpec) -> pd.DataFrame:
        time.sleep(0.2)
        return pd.DataFrame(
            {
                "time_tag": pd.to_datetime(["2024-01-01T00:00:00Z"], utc=True),
                "flux": [1.0],
            }
        )

    monkeypatch.setattr(noaa_space, "_download_dataset", slow_download)
    t0 = time.monotonic()
    bundles, errors = noaa_space.load_noaa_space_data(
        keys=["f107_flux"],
        use_cache=False,
        max_workers=1,
        overall_timeout_s=0.05,
    )
    dt = time.monotonic() - t0
    assert dt < 0.2
    assert "f107_flux" in errors
    assert "Timed out" in errors["f107_flux"]
    assert bundles == {}



# Author: Dr Diego Malpica MD

"""Core helpers for the Reflex Space Weather DS MVP (Phase 1).

This module is UI-agnostic and is intended to be unit-tested.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import numpy as np


@dataclass(frozen=True, slots=True)
class QCSettings:
    method: str
    max_deviation: float
    median_window: int


def parse_timestamp_from_filename(filename: str) -> tuple[datetime, bool]:
    """Parse a timestamp from an RR filename, assuming local time GMT-5.

    The legacy app uses the same convention for RR text filenames.
    """

    if not isinstance(filename, str):
        raise TypeError("filename must be a string")

    patterns: list[tuple[str, int]] = [
        ("%Y-%m-%d %H-%M-%S", 19),
        ("%Y-%m-%d_%H-%M-%S", 19),
        ("%Y-%m-%d", 10),
    ]
    for pattern, length in patterns:
        try:
            parsed = datetime.strptime(filename[:length], pattern)
            local_tz = timezone(timedelta(hours=-5))
            return parsed.replace(tzinfo=local_tz).astimezone(timezone.utc), True
        except (ValueError, TypeError):
            continue
    return datetime.now(timezone.utc), False


def compute_session_metrics_from_text(
    *,
    filename: str,
    content: str,
    qc: QCSettings,
    include_advanced: bool,
) -> dict[str, Any]:
    """Compute core HRV/HRF session metrics from RR text content.

    Important: this function depends on the legacy computation package `app/`.
    The Reflex runtime should set `PYTHONPATH=..` (repo root) so `import app` works.
    """

    if not isinstance(content, str):
        raise TypeError("content must be a string")
    if qc.max_deviation <= 0 or qc.max_deviation > 1.0:
        raise ValueError("qc.max_deviation must be in (0, 1]")
    if qc.median_window < 3:
        raise ValueError("qc.median_window must be >= 3")
    if qc.method not in {"threshold_median", "threshold_prev"}:
        raise ValueError("qc.method must be 'threshold_median' or 'threshold_prev'")

    try:
        from app.hrv_core import clean_rr_intervals, compute_comprehensive_hrv, load_rr_intervals_from_text
    except Exception as exc:  # pragma: no cover
        raise ImportError(
            "Cannot import legacy core modules. Ensure the Reflex process has PYTHONPATH set "
            "to the repo root so `import app` works (PowerShell: `$env:PYTHONPATH=\"..\"`)."
        ) from exc

    rr_ms = load_rr_intervals_from_text(filename, content)
    if rr_ms.size == 0:
        raise ValueError("No valid RR intervals found (expected 300–2000 ms values).")

    cleaned, _valid_mask, qc_summary = clean_rr_intervals(
        rr_ms,
        method=qc.method,
        max_deviation=qc.max_deviation,
        median_window=qc.median_window,
    )

    metrics = compute_comprehensive_hrv(cleaned, include_advanced=bool(include_advanced))
    # Ensure numeric payload is JSON-friendly (floats/ints/bools/strings).
    out: dict[str, Any] = {}
    for key, value in metrics.items():
        if isinstance(value, (bool, str, int, float)) or value is None:
            out[key] = value
        elif isinstance(value, (np.floating,)):
            out[key] = float(value)
        elif isinstance(value, (np.integer,)):
            out[key] = int(value)
        else:
            # Drop complex/unexpected payloads for MVP.
            continue

    ts_utc, parsed = parse_timestamp_from_filename(filename)
    out.update(
        {
            "session_name": filename,
            "session_start_utc": ts_utc.isoformat(),
            "parsed_timestamp": bool(parsed),
            "artifact_pct": float(qc_summary.get("flagged_pct", 0.0)),
            "n_rr_intervals": int(cleaned.size),
        }
    )
    return out


from __future__ import annotations

import pytest

from app.fatigue_integration import compute_fatigue_analysis


def test_compute_fatigue_analysis_zone_boundaries() -> None:
    performances = [90.0, 89.0, 77.0, 77.1, 70.0, 70.1, 69.0]
    analysis = compute_fatigue_analysis(performances)

    # Zones are defined as:
    # - >= 90: low risk
    # - > 77 and < 90: caution
    # - > 70 and <= 77: high risk
    # - <= 70: severe
    assert analysis["zones"] == [1, 2, 2, 2]

    total = 7.0
    at_or_below_77 = 4.0
    assert pytest.approx(analysis["risk"], rel=1e-12) == at_or_below_77 / total * 100.0

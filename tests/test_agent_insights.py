"""Tests for agent-backed metric explanations."""

from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
APP_ROOT = PROJECT_ROOT / "app"
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from agent_insights import AgentInsightManager
from agent_runtime import AgentRuntime, build_default_agent_runtime_config


def _stub_runtime() -> AgentRuntime:
    """Create a runtime that skips OpenAI client initialization."""
    config = build_default_agent_runtime_config()
    sentinel_client = object()
    return AgentRuntime(config=config, client=sentinel_client)


def test_metric_insight_manager_classifies_values() -> None:
    """Local explainer should classify metrics relative to references."""
    df = pd.DataFrame(
        [
            {
                "source": "session_a",
                "sdnn": 30.0,  # below reference
                "rmssd": 70.0,  # above reference
                "pnn50": 15.0,  # within reference
                "lf_power": 800.0,
                "hf_power": 200.0,
                "lf_hf_ratio": 4.0,
                "mean_hr_bpm": 78.0,
            }
        ]
    )
    manager = AgentInsightManager(runtime=_stub_runtime())
    result = manager.generate_metric_insights(df, run_agent=False)

    assert result.explanations, "Expected at least one explanation"
    statuses = {expl.metric_key: expl.status for expl in result.explanations}
    assert statuses.get("sdnn") == "below_reference"
    assert statuses.get("rmssd") == "above_reference"
    assert statuses.get("pnn50") == "within_reference"
    assert result.agent_payload is not None
    assert result.agent_payload["metadata"]["persona"] == "metric_explainer"
    assert result.used_agent is False

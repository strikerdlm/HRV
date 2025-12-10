"""Regression tests for version metadata and the Agents SDK scaffold."""

from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
APP_ROOT = PROJECT_ROOT / "app"
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from agent_runtime import AgentRuntime, build_default_agent_runtime_config
from version_info import get_git_metadata, get_version_info


def test_version_info_matches_changelog_headline() -> None:
    """Ensure UI version badges stay synchronized with CHANGELOG.md."""
    version, release_date = get_version_info()

    changelog_path = PROJECT_ROOT / "CHANGELOG.md"
    lines = changelog_path.read_text(encoding="utf-8").splitlines()

    for line in lines:
        line = line.strip()
        if line.startswith("## ["):
            raw_version = line.split("]", maxsplit=1)[0][3:]
            expected_version = raw_version.strip("[] ").strip()
            expected_release = line.split("-", maxsplit=1)[1].strip()
            break
    else:  # pragma: no cover - malformed changelog
        raise AssertionError("Changelog headline not found")

    assert version == expected_version
    assert release_date == expected_release


def test_git_metadata_includes_branch_and_hash() -> None:
    """Git metadata should expose a branch name and short hash."""
    metadata = get_git_metadata()

    assert metadata.branch not in ("", "unknown")
    assert metadata.short_hash not in ("", "unknown")
    assert all(char in "0123456789abcdef" for char in metadata.short_hash.lower())


def test_agent_config_personas_and_tools_present() -> None:
    """Default agent runtime config should list all planned personas."""
    config = build_default_agent_runtime_config()

    assert "solar_physiology_correlator" in config.personas
    assert "wearable_recovery_concierge" in config.personas
    assert "environmental_threat_watcher" in config.personas
    correlator = config.personas["solar_physiology_correlator"]
    assert "code_interpreter" in correlator.tools
    assert any(server.identifier == "mcp://hrv-db" for server in config.mcp_servers)


def test_agent_runtime_payload_contains_context() -> None:
    """Payloads must carry mission context and tool specs."""
    config = build_default_agent_runtime_config()
    runtime = AgentRuntime(config=config)

    mission_context = {"user_id": "crew-1", "rr_files": 3}
    payload = runtime.build_request_payload(
        persona_name="wearable_recovery_concierge",
        mission_context=mission_context,
        user_prompt="Summarize readiness trends.",
    )

    assert payload["model"] == config.model
    assert payload["metadata"]["mission_context"]["user_id"] == "crew-1"
    assert payload["tools"], "At least one tool spec is required"

"""
Utilities for keeping application metadata in sync with the changelog.

The helpers derive the current version and release date from the top entry
in `CHANGELOG.md` so UI surfaces automatically reflect the latest release.
"""
# Author: Dr Diego Malpica MD

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple
import subprocess
import time

try:
    from app.logging_config import get_logger, log_exception
except ImportError:  # pragma: no cover - fallback for script execution
    from logging_config import get_logger, log_exception

_LOGGER = get_logger(__name__)
_CHANGELOG_PATH = Path(__file__).resolve().parents[1] / "CHANGELOG.md"
_REPO_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_VERSION = "1.8.15"
_DEFAULT_RELEASE_DATE = "2025-12-10"

_VERSION_CACHE: Optional[Tuple[str, str]] = None
_VERSION_SOURCE_MTIME: Optional[int] = None

_GIT_METADATA_CACHE: Optional["GitMetadata"] = None
_GIT_METADATA_EXPIRY_NS = 0
_GIT_METADATA_TTL_NS = 60 * 1_000_000_000  # 60 seconds
_GIT_FAILURE_BACKOFF_NS = 10 * 60 * 1_000_000_000  # 10 minutes
_GIT_CMD_TIMEOUT_SEC = 10
_GIT_DISABLED_UNTIL_NS = 0
_GIT_DIR = _REPO_ROOT / ".git"


@dataclass(frozen=True)
class GitMetadata:
    """Immutable representation of the current Git state."""

    branch: str
    short_hash: str
    commit_time: str
    is_dirty: bool


def get_version_info() -> Tuple[str, str]:
    """
    Return the current application version and release date.

    The values are parsed from the first version header in `CHANGELOG.md`
    following the pattern `## [x.y.z] - YYYY-MM-DD`. If parsing fails or the
    file is missing, default values are returned and the situation is logged.
    The function automatically refreshes when the changelog's modification
    timestamp changes, so Streamlit reruns always surface the latest release.
    """
    global _VERSION_CACHE, _VERSION_SOURCE_MTIME

    if not _CHANGELOG_PATH.exists():
        _LOGGER.warning(
            "CHANGELOG.md not found; using default version %s", _DEFAULT_VERSION
        )
        return _DEFAULT_VERSION, _DEFAULT_RELEASE_DATE

    try:
        current_mtime = _CHANGELOG_PATH.stat().st_mtime_ns
    except OSError as exc:  # pragma: no cover - filesystem edge case
        log_exception(_LOGGER, "Unable to read changelog metadata", exc)
        return _DEFAULT_VERSION, _DEFAULT_RELEASE_DATE

    if _VERSION_CACHE and _VERSION_SOURCE_MTIME == current_mtime:
        return _VERSION_CACHE

    try:
        lines = _CHANGELOG_PATH.read_text(encoding="utf-8").splitlines()
    except Exception as exc:  # pragma: no cover - defensive logging
        log_exception(_LOGGER, "Failed to read CHANGELOG.md for version lookup", exc)
        return _DEFAULT_VERSION, _DEFAULT_RELEASE_DATE

    parsed = _parse_version_from_lines(lines)
    if parsed:
        _VERSION_CACHE = parsed
        _VERSION_SOURCE_MTIME = current_mtime
        return parsed

    _LOGGER.warning(
        "No version header found in changelog; using default version %s",
        _DEFAULT_VERSION,
    )
    return _DEFAULT_VERSION, _DEFAULT_RELEASE_DATE


def _parse_version_from_lines(lines: list[str]) -> Optional[Tuple[str, str]]:
    """Extract the first valid version header from provided lines."""
    for raw_line in lines:
        line = raw_line.strip()
        if not line.startswith("## ["):
            continue

        closing_bracket = line.find("]")
        if closing_bracket == -1:
            continue

        version = line[3:closing_bracket].strip("[]").strip()
        if not version:
            continue

        if "-" in line:
            _, date_part = line.split("-", maxsplit=1)
            release_date = date_part.strip() or _DEFAULT_RELEASE_DATE
        else:
            release_date = _DEFAULT_RELEASE_DATE

        return version, release_date

    return None


def get_git_metadata(force_refresh: bool = False) -> GitMetadata:
    """
    Return cached Git metadata describing the current worktree.

    Args:
        force_refresh: When True, bypass the TTL cache and query Git directly.
    """
    global _GIT_METADATA_CACHE, _GIT_METADATA_EXPIRY_NS

    now = time.monotonic_ns()
    if (
        not force_refresh
        and _GIT_METADATA_CACHE is not None
        and now < _GIT_METADATA_EXPIRY_NS
    ):
        return _GIT_METADATA_CACHE

    metadata = _collect_git_metadata()
    _GIT_METADATA_CACHE = metadata
    _GIT_METADATA_EXPIRY_NS = now + _GIT_METADATA_TTL_NS
    return metadata


def _collect_git_metadata() -> GitMetadata:
    """Query Git for branch, short hash, and commit timestamp information."""
    branch = _run_git_command(["rev-parse", "--abbrev-ref", "HEAD"]) or "unknown"
    short_hash = _run_git_command(["rev-parse", "--short", "HEAD"]) or "unknown"
    commit_time = (
        _run_git_command(["show", "-s", "--format=%cI", "HEAD"]) or _DEFAULT_RELEASE_DATE
    )
    status_output = _run_git_command(["status", "--short"])
    is_dirty = bool(status_output.strip()) if status_output is not None else False

    return GitMetadata(
        branch=branch,
        short_hash=short_hash,
        commit_time=commit_time,
        is_dirty=is_dirty,
    )


def _run_git_command(args: list[str]) -> Optional[str]:
    """Run a git command in the repository root and return stripped stdout."""
    global _GIT_DISABLED_UNTIL_NS

    now = time.monotonic_ns()
    if now < _GIT_DISABLED_UNTIL_NS:
        return None

    if not _GIT_DIR.exists():
        _GIT_DISABLED_UNTIL_NS = now + _GIT_FAILURE_BACKOFF_NS
        _LOGGER.info("Git metadata lookup skipped; missing .git at %s", _GIT_DIR)
        return None

    try:
        result = subprocess.run(
            ["git", *args],
            cwd=_REPO_ROOT,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=_GIT_CMD_TIMEOUT_SEC,
        )
    except subprocess.TimeoutExpired as exc:
        joined_args = " ".join(args)
        backoff_seconds = _GIT_FAILURE_BACKOFF_NS // 1_000_000_000
        _GIT_DISABLED_UNTIL_NS = now + _GIT_FAILURE_BACKOFF_NS
        message = (
            f"Git metadata lookup timed out for command: git {joined_args}; "
            f"backing off git probes for {backoff_seconds} seconds"
        )
        log_exception(_LOGGER, message, exc)
        return None
    except (OSError, subprocess.SubprocessError) as exc:
        joined_args = " ".join(args)
        backoff_seconds = _GIT_FAILURE_BACKOFF_NS // 1_000_000_000
        _GIT_DISABLED_UNTIL_NS = now + _GIT_FAILURE_BACKOFF_NS
        message = (
            f"Git metadata lookup failed for command: git {joined_args}; "
            f"backing off git probes for {backoff_seconds} seconds"
        )
        log_exception(_LOGGER, message, exc)
        return None

    return result.stdout.strip()


def get_app_version() -> str:
    """Return the application version derived from the changelog."""
    version, _ = get_version_info()
    return version


def get_app_release_date() -> str:
    """Return the release date associated with the current version."""
    _, release_date = get_version_info()
    return release_date



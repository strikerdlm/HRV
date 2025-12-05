"""
Utilities for keeping application metadata in sync with the changelog.

The helpers derive the current version and release date from the top entry
in `CHANGELOG.md` so UI surfaces automatically reflect the latest release.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Tuple

try:
    from app.logging_config import get_logger, log_exception
except ImportError:  # pragma: no cover - fallback for script execution
    from logging_config import get_logger, log_exception

_LOGGER = get_logger(__name__)
_CHANGELOG_PATH = Path(__file__).resolve().parents[1] / "CHANGELOG.md"
_DEFAULT_VERSION = "1.8.3"
_DEFAULT_RELEASE_DATE = "2025-12-05"


@lru_cache(maxsize=1)
def get_version_info() -> Tuple[str, str]:
    """
    Return the current application version and release date.

    The values are parsed from the first version header in `CHANGELOG.md`
    following the pattern `## [x.y.z] - YYYY-MM-DD`. If parsing fails or the
    file is missing, default values are returned and the situation is logged.
    """
    if not _CHANGELOG_PATH.exists():
        _LOGGER.warning(
            "CHANGELOG.md not found; using default version %s", _DEFAULT_VERSION
        )
        return _DEFAULT_VERSION, _DEFAULT_RELEASE_DATE

    try:
        lines = _CHANGELOG_PATH.read_text(encoding="utf-8").splitlines()
    except Exception as exc:  # pragma: no cover - defensive logging
        log_exception(_LOGGER, "Failed to read CHANGELOG.md for version lookup", exc)
        return _DEFAULT_VERSION, _DEFAULT_RELEASE_DATE

    for raw_line in lines:
        line = raw_line.strip()
        if not line.startswith("## ["):
            continue

        closing_bracket = line.find("]")
        if closing_bracket == -1:
            continue

        version = line[3:closing_bracket].strip("[]").strip()
        date_part = line.split("-", maxsplit=1)[1].strip() if "-" in line else ""
        release_date = date_part or _DEFAULT_RELEASE_DATE

        if version:
            return version, release_date

    _LOGGER.warning(
        "No version header found in changelog; using default version %s",
        _DEFAULT_VERSION,
    )
    return _DEFAULT_VERSION, _DEFAULT_RELEASE_DATE


def get_app_version() -> str:
    """Return the application version derived from the changelog."""
    version, _ = get_version_info()
    return version


def get_app_release_date() -> str:
    """Return the release date associated with the current version."""
    _, release_date = get_version_info()
    return release_date



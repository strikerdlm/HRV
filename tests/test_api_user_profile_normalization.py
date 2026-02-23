# Author: Dr Diego Malpica MD
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_APP_DIR = _PROJECT_ROOT / "app"
if str(_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_DIR))
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import api.main as api_main
from app.user_database import UserProfile as DBUserProfile


def test_profile_to_dict_normalizes_missing_sex_and_language() -> None:
    profile = DBUserProfile(
        user_id="u-1",
        username="tester",
        full_name="Test User",
        sex=None,
        language=None,  # type: ignore[arg-type]
    )

    payload = api_main._profile_to_dict(profile)
    assert payload["sex"] == "other"
    assert payload["language"] == "en"


def test_profile_to_dict_normalizes_non_dataclass_profile_values() -> None:
    class _LegacyProfile:
        user_id = "u-legacy"
        username = "legacy"
        full_name = "Legacy User"
        sex = None
        language = None

    payload = api_main._profile_to_dict(_LegacyProfile())
    assert payload["sex"] == "other"
    assert payload["language"] == "en"


def test_list_users_works_when_db_profile_sex_is_null(monkeypatch) -> None:
    class _FakeDB:
        def list_users(self):
            return [
                DBUserProfile(
                    user_id="u-1",
                    username="tester",
                    full_name="Test User",
                    sex=None,
                    language=None,  # type: ignore[arg-type]
                )
            ]

    monkeypatch.setattr(api_main, "_get_user_database", lambda: _FakeDB())

    response = asyncio.run(api_main.list_users(limit=50, offset=0))
    assert response.total == 1
    assert len(response.users) == 1
    assert response.users[0].sex == "other"
    assert response.users[0].language == "en"

"""Tests for UI state management helpers."""

from __future__ import annotations

import streamlit as st

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
APP_ROOT = PROJECT_ROOT / "app"
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from ui_state_manager import CrossTabResultBroker


def _new_broker() -> CrossTabResultBroker:
    """Helper to create a broker with small limits for testing."""
    return CrossTabResultBroker(max_users=2, max_tabs=2, max_entries_per_tab=2)


def setup_function() -> None:
    """Reset session state before each test."""
    st.session_state.clear()


def test_publish_and_get_latest_returns_payload() -> None:
    broker = _new_broker()

    broker.publish("circadian", "user1", "summary", {"foo": 1})
    latest = broker.get_latest("circadian", "user1")

    assert latest is not None
    assert latest["payload"]["foo"] == 1
    assert latest["key"] == "summary"


def test_eviction_removes_oldest_entry_per_tab() -> None:
    broker = _new_broker()

    broker.publish("circadian", "user1", "k1", {"v": 1})
    broker.publish("circadian", "user1", "k2", {"v": 2})
    broker.publish("circadian", "user1", "k3", {"v": 3})

    # Oldest (k1) should be evicted when limit is 2
    assert broker.get_by_key("circadian", "user1", "k1") is None
    assert broker.get_by_key("circadian", "user1", "k3") is not None


def test_user_isolation_between_payloads() -> None:
    broker = _new_broker()

    broker.publish("circadian", "user1", "summary", {"v": 10})
    broker.publish("circadian", "user2", "summary", {"v": 20})

    result_user1 = broker.get_latest("circadian", "user1")
    result_user2 = broker.get_latest("circadian", "user2")

    assert result_user1 is not None and result_user1["payload"]["v"] == 10
    assert result_user2 is not None and result_user2["payload"]["v"] == 20
    # Ensure user1 cannot see user2 payload
    assert broker.get_by_key("circadian", "user1", "summary")["payload"]["v"] == 10


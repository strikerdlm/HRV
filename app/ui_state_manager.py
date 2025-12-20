"""
UI State Manager for HRV Analysis Platform.

This module manages:
- Data upload state tracking
- Conditional button enabling/disabling
- Tab accessibility state
- User session state management

Author: Dr. Diego L. Malpica, MD - Aerospace Medicine Specialist
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

import streamlit as st

try:
    from app.logging_config import get_logger
except ImportError:  # pragma: no cover - fallback for script execution
    from logging_config import get_logger


class DataType(Enum):
    """Types of data that can be uploaded/available."""
    RR_INTERVALS = "rr_intervals"
    SLEEP_DATA = "sleep_data"
    ACTIVITY_DATA = "activity_data"
    ECG_DATA = "ecg_data"
    BLOOD_PRESSURE = "blood_pressure"
    USER_PROFILE = "user_profile"
    SPACE_WEATHER = "space_weather"


@dataclass
class DataStatus:
    """Status of a particular data type."""
    data_type: DataType
    is_available: bool = False
    record_count: int = 0
    last_updated: Optional[datetime] = None
    source: str = ""
    quality_score: Optional[float] = None


class UIStateManager:
    """
    Manages UI state for the HRV Analysis Platform.
    
    Provides centralized tracking of:
    - Data availability across different data types
    - Tab accessibility state
    - Compute button enablement
    - Session persistence
    """
    
    # Session state keys
    _STATE_KEY = "ui_state_manager"
    _DATA_STATUS_KEY = "data_status"
    _COMPUTED_RESULTS_KEY = "computed_results"
    
    def __init__(self) -> None:
        """Initialize the UI state manager."""
        self._ensure_session_state()
    
    def _ensure_session_state(self) -> None:
        """Ensure all required session state keys exist."""
        if self._STATE_KEY not in st.session_state:
            st.session_state[self._STATE_KEY] = {
                self._DATA_STATUS_KEY: {},
                self._COMPUTED_RESULTS_KEY: {},
                "initialized_at": datetime.now(tz=timezone.utc).isoformat(),
            }
    
    @property
    def _state(self) -> Dict[str, Any]:
        """Access the internal state dictionary."""
        self._ensure_session_state()
        return st.session_state[self._STATE_KEY]
    
    def set_data_available(
        self,
        data_type: DataType,
        is_available: bool = True,
        record_count: int = 0,
        source: str = "",
        quality_score: Optional[float] = None,
    ) -> None:
        """
        Mark a data type as available or unavailable.
        
        Args:
            data_type: The type of data
            is_available: Whether data is available
            record_count: Number of records
            source: Source of the data (e.g., "Polar H10", "Garmin")
            quality_score: Optional quality assessment (0-1)
        """
        status = DataStatus(
            data_type=data_type,
            is_available=is_available,
            record_count=record_count,
            last_updated=datetime.now(tz=timezone.utc) if is_available else None,
            source=source,
            quality_score=quality_score,
        )
        self._state[self._DATA_STATUS_KEY][data_type.value] = {
            "is_available": status.is_available,
            "record_count": status.record_count,
            "last_updated": status.last_updated.isoformat() if status.last_updated else None,
            "source": status.source,
            "quality_score": status.quality_score,
        }
    
    def is_data_available(self, data_type: DataType) -> bool:
        """Check if a specific data type is available."""
        status = self._state[self._DATA_STATUS_KEY].get(data_type.value, {})
        return status.get("is_available", False)
    
    def get_data_status(self, data_type: DataType) -> Optional[Dict[str, Any]]:
        """Get full status for a data type."""
        return self._state[self._DATA_STATUS_KEY].get(data_type.value)
    
    def has_physiological_data(self) -> bool:
        """Check if any physiological data (RR, ECG, etc.) is available."""
        physio_types = [
            DataType.RR_INTERVALS,
            DataType.ECG_DATA,
            DataType.SLEEP_DATA,
            DataType.ACTIVITY_DATA,
        ]
        return any(self.is_data_available(dt) for dt in physio_types)
    
    def has_hrv_data(self) -> bool:
        """Check if HRV-specific data is available."""
        return self.is_data_available(DataType.RR_INTERVALS) or self.is_data_available(DataType.ECG_DATA)
    
    def clear_data(self, data_type: Optional[DataType] = None) -> None:
        """
        Clear data status.
        
        Args:
            data_type: Specific type to clear, or None to clear all
        """
        if data_type:
            self._state[self._DATA_STATUS_KEY].pop(data_type.value, None)
        else:
            self._state[self._DATA_STATUS_KEY].clear()
    
    def store_computed_result(self, key: str, result: Any) -> None:
        """Store a computed result for later access."""
        self._state[self._COMPUTED_RESULTS_KEY][key] = {
            "result": result,
            "computed_at": datetime.now(tz=timezone.utc).isoformat(),
        }
    
    def get_computed_result(self, key: str) -> Optional[Any]:
        """Retrieve a stored computed result."""
        stored = self._state[self._COMPUTED_RESULTS_KEY].get(key)
        return stored.get("result") if stored else None
    
    def get_all_data_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all data types."""
        return dict(self._state[self._DATA_STATUS_KEY])


class TabSettingsManager:
    """
    Persist per-tab UI settings on a per-user basis for the current session.

    Stored settings are bounded to avoid unbounded growth:
    - Max unique users tracked: `_max_users`
    - Max tabs per user: `_max_tabs`
    """

    _STATE_KEY = "tab_settings_manager"

    def __init__(self, max_users: int = 20, max_tabs: int = 8) -> None:
        self._max_users = max_users
        self._max_tabs = max_tabs
        self._ensure_state()

    def _ensure_state(self) -> None:
        """Ensure the tab settings container exists in session state."""
        if self._STATE_KEY not in st.session_state:
            st.session_state[self._STATE_KEY] = {
                "settings": {},
                "initialized_at": datetime.now(tz=timezone.utc).isoformat(),
            }

    @staticmethod
    def _user_key(user_id: Optional[str]) -> str:
        """Return a normalized user key for storage."""
        return str(user_id) if user_id else "guest"

    def _get_store(self) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """Internal accessor for the settings dictionary."""
        self._ensure_state()
        return st.session_state[self._STATE_KEY]["settings"]

    def get_settings(self, tab_id: str, user_id: Optional[str]) -> Dict[str, Any]:
        """
        Retrieve settings for a tab/user combination.

        Args:
            tab_id: Unique tab identifier (e.g., "fatigue", "circadian").
            user_id: User identifier or None for guest.

        Returns:
            A shallow copy of the stored settings; empty dict if none saved.
        """
        store = self._get_store()
        user_store = store.get(self._user_key(user_id), {})
        return dict(user_store.get(tab_id, {}))

    def save_settings(
        self,
        tab_id: str,
        user_id: Optional[str],
        settings: Dict[str, Any],
        allowed_keys: Optional[Tuple[str, ...]] = None,
    ) -> Dict[str, Any]:
        """
        Persist settings for a tab/user, enforcing storage bounds.

        Args:
            tab_id: Unique tab identifier.
            user_id: User identifier or None for guest.
            settings: Dictionary of settings to store.
            allowed_keys: Optional whitelist; only these keys are persisted.

        Returns:
            The filtered settings that were stored.
        """
        store = self._get_store()
        user_key = self._user_key(user_id)

        if user_key not in store and len(store) >= self._max_users:
            # Evict the oldest inserted user to bound memory usage.
            evict_key = next(iter(store))
            store.pop(evict_key, None)

        user_store = store.setdefault(user_key, {})
        if tab_id not in user_store and len(user_store) >= self._max_tabs:
            evict_tab = next(iter(user_store))
            user_store.pop(evict_tab, None)

        filtered = dict(settings)
        if allowed_keys is not None:
            filtered = {key: value for key, value in settings.items() if key in allowed_keys}

        user_store[tab_id] = filtered
        return dict(filtered)


class CrossTabResultBroker:
    """
    Lightweight broker to share computed results across Streamlit tabs.

    Stores per-user, per-tab payloads in `st.session_state` with bounded size to
    avoid unbounded growth during long sessions. Payloads should be small,
    JSON-serializable dictionaries.
    """

    _STATE_KEY = "cross_tab_results"

    def __init__(
        self,
        max_users: int = 20,
        max_tabs: int = 10,
        max_entries_per_tab: int = 6,
    ) -> None:
        self._max_users = max_users
        self._max_tabs = max_tabs
        self._max_entries_per_tab = max_entries_per_tab
        self._logger = get_logger(__name__)
        self._ensure_state()

    @staticmethod
    def _user_key(user_id: Optional[str]) -> str:
        """Normalize user identifiers for storage."""
        return str(user_id) if user_id else "guest"

    def _ensure_state(self) -> None:
        """Ensure storage container exists in session state."""
        if self._STATE_KEY not in st.session_state:
            st.session_state[self._STATE_KEY] = {
                "results": {},
                "initialized_at": datetime.now(tz=timezone.utc).isoformat(),
            }

    def _get_store(self) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
        """Return the underlying store dictionary."""
        self._ensure_state()
        return st.session_state[self._STATE_KEY]["results"]

    def publish(
        self,
        tab_id: str,
        user_id: Optional[str],
        key: str,
        payload: Dict[str, Any],
        *,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Publish a payload for a given tab/user combination.

        Args:
            tab_id: Logical tab identifier (e.g., "circadian", "fatigue").
            user_id: Active user id or None for guests.
            key: Logical key for the payload (e.g., "circadian_summary").
            payload: JSON-serializable dictionary.
            metadata: Optional metadata for diagnostics or provenance.

        Returns:
            The stored entry.
        """
        store = self._get_store()
        user_key = self._user_key(user_id)

        if user_key not in store and len(store) >= self._max_users:
            evict_user = next(iter(store))
            store.pop(evict_user, None)
            self._logger.warning("Evicted cross-tab cache for user %s", evict_user)

        user_store = store.setdefault(user_key, {})
        if tab_id not in user_store and len(user_store) >= self._max_tabs:
            evict_tab = next(iter(user_store))
            user_store.pop(evict_tab, None)
            self._logger.warning("Evicted cross-tab cache for tab %s", evict_tab)

        entries = [entry for entry in user_store.get(tab_id, []) if entry.get("key") != key]
        entry = {
            "key": key,
            "payload": dict(payload),
            "metadata": dict(metadata) if metadata else {},
            "stored_at": datetime.now(tz=timezone.utc).isoformat(),
        }
        entries.append(entry)
        if len(entries) > self._max_entries_per_tab:
            entries = entries[-self._max_entries_per_tab :]
        user_store[tab_id] = entries
        return entry

    def get_latest(self, tab_id: str, user_id: Optional[str]) -> Optional[Dict[str, Any]]:
        """Return the most recent entry for a tab/user combination."""
        store = self._get_store()
        user_store = store.get(self._user_key(user_id), {})
        entries = user_store.get(tab_id, [])
        if not entries:
            return None
        return dict(entries[-1])

    def get_by_key(
        self,
        tab_id: str,
        user_id: Optional[str],
        key: str,
    ) -> Optional[Dict[str, Any]]:
        """Return the most recent entry matching a key for a tab/user."""
        store = self._get_store()
        user_store = store.get(self._user_key(user_id), {})
        entries = user_store.get(tab_id, [])
        for entry in reversed(entries):
            if entry.get("key") == key:
                return dict(entry)
        return None

    def clear(self, tab_id: Optional[str] = None, user_id: Optional[str] = None) -> None:
        """Clear stored entries for a user/tab or everything."""
        store = self._get_store()
        if user_id is None and tab_id is None:
            store.clear()
            return
        if user_id is not None:
            store.pop(self._user_key(user_id), None)
            return
        # Clear tab for all users
        for user_key, tabs in store.items():
            if tab_id in tabs:
                tabs.pop(tab_id, None)


# =============================================================================
# STREAMLIT UI HELPERS
# =============================================================================

def get_state_manager() -> UIStateManager:
    """Get or create the singleton UI state manager."""
    return UIStateManager()


def get_tab_settings_manager() -> TabSettingsManager:
    """Get or create the tab settings manager."""
    return TabSettingsManager()


def get_cross_tab_broker() -> CrossTabResultBroker:
    """Get or create the cross-tab result broker."""
    return CrossTabResultBroker()


def render_data_status_badge() -> None:
    """Render a compact badge showing data availability status."""
    manager = get_state_manager()
    
    statuses = []
    
    if manager.is_data_available(DataType.RR_INTERVALS):
        status = manager.get_data_status(DataType.RR_INTERVALS)
        count = status.get("record_count", 0) if status else 0
        statuses.append(f"🫀 RR: {count:,}")
    
    if manager.is_data_available(DataType.SLEEP_DATA):
        statuses.append("😴 Sleep")
    
    if manager.is_data_available(DataType.SPACE_WEATHER):
        statuses.append("☀️ Space")
    
    if manager.is_data_available(DataType.USER_PROFILE):
        statuses.append("👤 Profile")
    
    if statuses:
        st.markdown(
            f"<div style='background: linear-gradient(135deg, #1a472a 0%, #2d5a3f 100%); "
            f"padding: 8px 12px; border-radius: 8px; font-size: 0.85rem; color: #90EE90;'>"
            f"<strong>✓ Data Loaded:</strong> {' | '.join(statuses)}</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            "<div style='background: linear-gradient(135deg, #4a3728 0%, #5a4838 100%); "
            "padding: 8px 12px; border-radius: 8px; font-size: 0.85rem; color: #FFB347;'>"
            "<strong>⚠️ No Data:</strong> Upload physiological data to enable computations</div>",
            unsafe_allow_html=True,
        )


def render_conditional_compute_button(
    label: str,
    key: str,
    required_data: List[DataType],
    help_text: str = "",
    on_click: Optional[Callable[[], None]] = None,
    button_type: str = "primary",
) -> bool:
    """
    Render a compute button that's disabled when required data is missing.
    
    Args:
        label: Button label
        key: Unique button key
        required_data: List of required data types
        help_text: Optional help text
        on_click: Optional callback function
        button_type: "primary" or "secondary"
        
    Returns:
        True if button was clicked (and enabled), False otherwise
    """
    manager = get_state_manager()
    
    # Check if all required data is available
    missing = [dt for dt in required_data if not manager.is_data_available(dt)]
    is_enabled = len(missing) == 0
    
    # Build help text with missing data info
    if missing and not help_text:
        missing_names = [dt.value.replace("_", " ").title() for dt in missing]
        help_text = f"Requires: {', '.join(missing_names)}"
    
    # Render button
    if button_type == "primary":
        clicked = st.button(
            label,
            key=key,
            disabled=not is_enabled,
            help=help_text,
            type="primary",
            width="stretch",
        )
    else:
        clicked = st.button(
            label,
            key=key,
            disabled=not is_enabled,
            help=help_text,
            width="stretch",
        )
    
    # Show warning for disabled state
    if not is_enabled:
        st.caption(f"⚠️ {help_text}")
    
    # Execute callback if clicked
    if clicked and on_click:
        on_click()
    
    return clicked and is_enabled


def render_tab_header(
    title: str,
    requires_data: bool = True,
    data_types: Optional[List[DataType]] = None,
) -> bool:
    """
    Render a tab header with optional data requirement indicator.
    
    Args:
        title: Tab title
        requires_data: Whether this tab requires data to function
        data_types: Specific data types required (optional)
        
    Returns:
        True if data requirements are met, False otherwise
    """
    manager = get_state_manager()
    
    # Check data availability
    if data_types:
        has_data = all(manager.is_data_available(dt) for dt in data_types)
    elif requires_data:
        has_data = manager.has_physiological_data()
    else:
        has_data = True
    
    # Render header
    if has_data:
        st.header(title)
        return True
    else:
        st.header(f"{title}")
        st.info(
            "📊 **Data Required**: This tab requires uploaded physiological data to perform computations. "
            "You can explore the interface, but calculation buttons will be disabled until data is available."
        )
        return False


def render_exploration_mode_notice() -> None:
    """Render a notice for exploration mode (no data loaded)."""
    st.markdown(
        """
        <div style="
            background: linear-gradient(135deg, #2a2a4a 0%, #3a3a5a 100%);
            border: 1px solid rgba(102, 126, 234, 0.3);
            border-radius: 12px;
            padding: 1rem;
            margin: 1rem 0;
        ">
            <h4 style="color: #667eea; margin: 0 0 0.5rem 0;">🔍 Exploration Mode</h4>
            <p style="color: #aaa; margin: 0; font-size: 0.9rem;">
                You're viewing this tab without uploaded data. All interface elements are visible,
                but computation features are disabled. Upload RR interval data or connect a device
                to enable full functionality.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_quick_start_guide() -> None:
    """Render a quick start guide for new users."""
    st.markdown(
        """
        <div style="
            background: linear-gradient(135deg, #1a2a3a 0%, #2a3a4a 100%);
            border-radius: 12px;
            padding: 1.5rem;
            margin: 1rem 0;
        ">
            <h3 style="color: #4ecdc4; margin: 0 0 1rem 0;">🚀 Quick Start Guide</h3>
            
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem;">
                <div style="background: rgba(255,255,255,0.05); padding: 1rem; border-radius: 8px;">
                    <h4 style="color: #ff6b6b; margin: 0 0 0.5rem 0;">Step 1: Upload Data</h4>
                    <p style="color: #aaa; font-size: 0.85rem; margin: 0;">
                        Use the sidebar to import RR interval data from your device 
                        (Polar, Garmin, ActiGraph, or generic text files).
                    </p>
                </div>
                
                <div style="background: rgba(255,255,255,0.05); padding: 1rem; border-radius: 8px;">
                    <h4 style="color: #4ecdc4; margin: 0 0 0.5rem 0;">Step 2: Set Profile</h4>
                    <p style="color: #aaa; font-size: 0.85rem; margin: 0;">
                        Enter your age, sex, and other details for personalized
                        analysis and population norm comparisons.
                    </p>
                </div>
                
                <div style="background: rgba(255,255,255,0.05); padding: 1rem; border-radius: 8px;">
                    <h4 style="color: #667eea; margin: 0 0 0.5rem 0;">Step 3: Analyze</h4>
                    <p style="color: #aaa; font-size: 0.85rem; margin: 0;">
                        Navigate to any tab to explore HRV metrics, circadian rhythms,
                        space weather correlations, and more.
                    </p>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_tab_navigation_cards() -> None:
    """Render navigation cards for quick access to all tabs."""
    manager = get_state_manager()
    has_data = manager.has_physiological_data()
    
    st.markdown("### 📑 Analysis Modules")
    
    # Define tab cards with their info
    tabs_info = [
        {
            "icon": "📊",
            "name": "Overview",
            "desc": "Summary statistics and key metrics",
            "requires_data": True,
            "color": "#667eea",
        },
        {
            "icon": "📈",
            "name": "Time Series",
            "desc": "RR intervals and temporal analysis",
            "requires_data": True,
            "color": "#4ecdc4",
        },
        {
            "icon": "🌊",
            "name": "Frequency",
            "desc": "Power spectral density analysis",
            "requires_data": True,
            "color": "#ff6b6b",
        },
        {
            "icon": "🔀",
            "name": "Nonlinear",
            "desc": "Poincaré plots and entropy metrics",
            "requires_data": True,
            "color": "#f7b731",
        },
        {
            "icon": "☀️",
            "name": "Circadian",
            "desc": "Circadian rhythm simulation",
            "requires_data": False,
            "color": "#fd9644",
        },
        {
            "icon": "🌍",
            "name": "Space Weather",
            "desc": "Solar activity correlations",
            "requires_data": False,
            "color": "#9b59b6",
        },
        {
            "icon": "😴",
            "name": "SAFTE/Fatigue",
            "desc": "Sleep and fatigue modeling",
            "requires_data": False,
            "color": "#3498db",
        },
        {
            "icon": "📋",
            "name": "Population Norms",
            "desc": "Compare against reference values",
            "requires_data": True,
            "color": "#1abc9c",
        },
    ]
    
    # Render in 4-column grid
    cols = st.columns(4)
    for i, tab in enumerate(tabs_info):
        with cols[i % 4]:
            status = "✓" if (not tab["requires_data"] or has_data) else "○"
            status_color = "#90EE90" if status == "✓" else "#888"
            
            st.markdown(
                f"""
                <div style="
                    background: linear-gradient(135deg, {tab['color']}22 0%, {tab['color']}11 100%);
                    border: 1px solid {tab['color']}44;
                    border-radius: 10px;
                    padding: 0.8rem;
                    margin-bottom: 0.5rem;
                    min-height: 100px;
                ">
                    <div style="font-size: 1.5rem; margin-bottom: 0.3rem;">{tab['icon']}</div>
                    <div style="color: {tab['color']}; font-weight: 600; font-size: 0.9rem;">
                        {tab['name']} <span style="color: {status_color}; font-size: 0.7rem;">{status}</span>
                    </div>
                    <div style="color: #888; font-size: 0.75rem; line-height: 1.3;">{tab['desc']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def update_data_status_from_session() -> None:
    """
    Sync UI state manager with existing session state data.
    
    Call this at app startup to detect data that may have been 
    loaded in previous interactions.
    """
    manager = get_state_manager()
    
    # Check for RR intervals in session state
    rr_keys = ["rr_intervals", "cleaned_rr", "rr_data"]
    for key in rr_keys:
        if key in st.session_state and st.session_state[key] is not None:
            data = st.session_state[key]
            count = len(data) if hasattr(data, "__len__") else 0
            if count > 0:
                manager.set_data_available(
                    DataType.RR_INTERVALS,
                    is_available=True,
                    record_count=count,
                    source="Session",
                )
                break
    
    # Check for user profile
    if "current_user_profile" in st.session_state and st.session_state["current_user_profile"]:
        manager.set_data_available(DataType.USER_PROFILE, is_available=True)
    
    # Check for space weather data
    if "space_weather_data" in st.session_state and st.session_state["space_weather_data"]:
        manager.set_data_available(DataType.SPACE_WEATHER, is_available=True)


__all__ = [
    "DataType",
    "DataStatus",
    "UIStateManager",
    "TabSettingsManager",
    "CrossTabResultBroker",
    "get_state_manager",
    "get_tab_settings_manager",
    "get_cross_tab_broker",
    "render_data_status_badge",
    "render_conditional_compute_button",
    "render_tab_header",
    "render_exploration_mode_notice",
    "render_quick_start_guide",
    "render_tab_navigation_cards",
    "update_data_status_from_session",
]


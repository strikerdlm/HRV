"""
Multi-User Session Manager for Mission Control - Flight Surgeon.

Provides support for up to 7 concurrent user sessions, allowing:
- Quick switching between users
- Per-user calculation caching
- Individual user context for all tabs
- Session persistence

Author: Dr. Diego Leonel Malpica Hincapié, MD
Version: 1.0.0
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, Final, List, Optional, Tuple

import streamlit as st

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)

# Constants
MAX_CONCURRENT_USERS: Final[int] = 7
SESSION_KEY_MULTI_USER: Final[str] = "multi_user_sessions"
SESSION_KEY_ACTIVE_USER_ID: Final[str] = "active_user_id"
SESSION_KEY_USER_CACHE: Final[str] = "user_calculation_cache"


@dataclass
class UserSession:
    """Represents an active user session."""
    
    user_id: str
    username: str
    full_name: str
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_active: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    calculation_cache: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserSession":
        """Create from dictionary."""
        return cls(**data)


class MultiUserSessionManager:
    """
    Manages multiple concurrent user sessions.
    
    Provides:
    - Add/remove users from active sessions
    - Quick switch between active users
    - Per-user calculation cache
    - Maximum of 7 concurrent users
    """
    
    def __init__(self) -> None:
        """Initialize the multi-user session manager."""
        self._ensure_session_state()
    
    def _ensure_session_state(self) -> None:
        """Ensure all required session state keys exist."""
        if SESSION_KEY_MULTI_USER not in st.session_state:
            st.session_state[SESSION_KEY_MULTI_USER] = {}  # user_id -> UserSession dict
        if SESSION_KEY_ACTIVE_USER_ID not in st.session_state:
            st.session_state[SESSION_KEY_ACTIVE_USER_ID] = None
        if SESSION_KEY_USER_CACHE not in st.session_state:
            st.session_state[SESSION_KEY_USER_CACHE] = {}
    
    @property
    def active_sessions(self) -> Dict[str, Dict[str, Any]]:
        """Get all active user sessions."""
        self._ensure_session_state()
        return st.session_state[SESSION_KEY_MULTI_USER]
    
    @property
    def active_user_id(self) -> Optional[str]:
        """Get the currently active user ID."""
        self._ensure_session_state()
        return st.session_state.get(SESSION_KEY_ACTIVE_USER_ID)
    
    @active_user_id.setter
    def active_user_id(self, user_id: Optional[str]) -> None:
        """Set the currently active user ID."""
        self._ensure_session_state()
        st.session_state[SESSION_KEY_ACTIVE_USER_ID] = user_id
    
    @property
    def session_count(self) -> int:
        """Get number of active sessions."""
        return len(self.active_sessions)
    
    @property
    def can_add_user(self) -> bool:
        """Check if we can add another user session."""
        return self.session_count < MAX_CONCURRENT_USERS
    
    def add_user_session(
        self,
        user_id: str,
        username: str,
        full_name: str,
        make_active: bool = True,
    ) -> bool:
        """
        Add a user to active sessions.
        
        Args:
            user_id: Unique user identifier
            username: User's username
            full_name: User's display name
            make_active: Whether to make this the active user
            
        Returns:
            True if user was added, False if at capacity or already exists
        """
        if user_id in self.active_sessions:
            # User already in session, just update last_active
            self.active_sessions[user_id]["last_active"] = datetime.now(timezone.utc).isoformat()
            if make_active:
                self.active_user_id = user_id
            return True
        
        if not self.can_add_user:
            _LOGGER.warning("Cannot add user %s: maximum %d sessions reached", username, MAX_CONCURRENT_USERS)
            return False
        
        session = UserSession(
            user_id=user_id,
            username=username,
            full_name=full_name,
        )
        self.active_sessions[user_id] = session.to_dict()
        
        if make_active:
            self.active_user_id = user_id
        
        _LOGGER.info("Added user session: %s (%s)", username, user_id)
        return True
    
    def remove_user_session(self, user_id: str) -> bool:
        """
        Remove a user from active sessions.
        
        Args:
            user_id: User ID to remove
            
        Returns:
            True if user was removed, False if not found
        """
        if user_id not in self.active_sessions:
            return False
        
        del self.active_sessions[user_id]
        
        # Clear user cache
        if user_id in st.session_state[SESSION_KEY_USER_CACHE]:
            del st.session_state[SESSION_KEY_USER_CACHE][user_id]
        
        # If removed user was active, switch to another or clear
        if self.active_user_id == user_id:
            remaining = list(self.active_sessions.keys())
            self.active_user_id = remaining[0] if remaining else None
        
        _LOGGER.info("Removed user session: %s", user_id)
        return True
    
    def switch_to_user(self, user_id: str) -> bool:
        """
        Switch to a different active user.
        
        Args:
            user_id: User ID to switch to
            
        Returns:
            True if switch succeeded, False if user not in sessions
        """
        if user_id not in self.active_sessions:
            return False
        
        self.active_sessions[user_id]["last_active"] = datetime.now(timezone.utc).isoformat()
        self.active_user_id = user_id
        return True
    
    def get_active_user_session(self) -> Optional[Dict[str, Any]]:
        """Get the active user's session data."""
        if self.active_user_id is None:
            return None
        return self.active_sessions.get(self.active_user_id)
    
    def get_user_cache(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get calculation cache for a user.
        
        Args:
            user_id: User ID, or None for active user
            
        Returns:
            User's calculation cache dictionary
        """
        uid = user_id or self.active_user_id
        if uid is None:
            return {}
        
        if uid not in st.session_state[SESSION_KEY_USER_CACHE]:
            st.session_state[SESSION_KEY_USER_CACHE][uid] = {}
        
        return st.session_state[SESSION_KEY_USER_CACHE][uid]
    
    def set_user_cache(self, key: str, value: Any, user_id: Optional[str] = None) -> None:
        """
        Set a cached value for a user.
        
        Args:
            key: Cache key
            value: Value to cache
            user_id: User ID, or None for active user
        """
        uid = user_id or self.active_user_id
        if uid is None:
            return
        
        cache = self.get_user_cache(uid)
        cache[key] = {
            "value": value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    
    def get_all_sessions_summary(self) -> List[Dict[str, str]]:
        """
        Get summary of all active sessions for display.
        
        Returns:
            List of session summaries with id, username, full_name, is_active
        """
        summaries = []
        for user_id, session in self.active_sessions.items():
            summaries.append({
                "user_id": user_id,
                "username": session["username"],
                "full_name": session["full_name"],
                "is_active": user_id == self.active_user_id,
                "last_active": session.get("last_active", ""),
            })
        return summaries
    
    def clear_all_sessions(self) -> None:
        """Clear all user sessions."""
        st.session_state[SESSION_KEY_MULTI_USER] = {}
        st.session_state[SESSION_KEY_ACTIVE_USER_ID] = None
        st.session_state[SESSION_KEY_USER_CACHE] = {}


# Singleton instance
_manager: Optional[MultiUserSessionManager] = None


def get_multi_user_manager() -> MultiUserSessionManager:
    """Get the singleton multi-user session manager."""
    global _manager
    if _manager is None:
        _manager = MultiUserSessionManager()
    return _manager


def render_user_switcher() -> None:
    """
    Render a compact user switcher widget for the sidebar or header.
    
    Displays active users as clickable buttons with quick switch functionality.
    """
    manager = get_multi_user_manager()
    sessions = manager.get_all_sessions_summary()
    
    if not sessions:
        st.caption("No active users")
        return
    
    st.markdown("**Active Users** ({}/{})".format(len(sessions), MAX_CONCURRENT_USERS))
    
    # Display user buttons
    cols = st.columns(min(len(sessions), 3))
    for i, session in enumerate(sessions):
        col_idx = i % 3
        with cols[col_idx]:
            is_active = session["is_active"]
            btn_type = "primary" if is_active else "secondary"
            label = f"{'✓ ' if is_active else ''}{session['username']}"
            
            if st.button(
                label,
                key=f"switch_user_{session['user_id']}",
                type=btn_type,
                use_container_width=True,
                help=session["full_name"],
            ):
                if not is_active:
                    manager.switch_to_user(session["user_id"])
                    st.rerun()


def render_user_session_manager() -> None:
    """
    Render a full user session management panel.
    
    Includes:
    - List of all active users
    - Add/remove user buttons
    - Session details
    """
    manager = get_multi_user_manager()
    sessions = manager.get_all_sessions_summary()
    
    st.markdown("### 👥 Active User Sessions")
    st.caption(f"Managing {len(sessions)} of {MAX_CONCURRENT_USERS} maximum users")
    
    if not sessions:
        st.info("No active user sessions. Log in to start a session.")
        return
    
    # Display sessions in a table-like format
    for session in sessions:
        with st.container():
            cols = st.columns([3, 2, 1])
            
            with cols[0]:
                icon = "✅" if session["is_active"] else "👤"
                st.write(f"{icon} **{session['full_name']}** (@{session['username']})")
            
            with cols[1]:
                if session["is_active"]:
                    st.caption("🟢 Active")
                else:
                    if st.button("Switch", key=f"switch_{session['user_id']}", type="secondary"):
                        manager.switch_to_user(session["user_id"])
                        st.rerun()
            
            with cols[2]:
                if st.button("✕", key=f"remove_{session['user_id']}", help="Close session"):
                    manager.remove_user_session(session["user_id"])
                    st.rerun()
        
        st.divider()
    
    # Add user button
    if manager.can_add_user:
        st.caption("💡 Log in with another account to add more users")
    else:
        st.warning(f"⚠️ Maximum {MAX_CONCURRENT_USERS} users reached. Close a session to add more.")


# ---------------------------------------------------------------------------
# Module Exports
# ---------------------------------------------------------------------------

__all__ = [
    "MultiUserSessionManager",
    "UserSession",
    "get_multi_user_manager",
    "render_user_switcher",
    "render_user_session_manager",
    "MAX_CONCURRENT_USERS",
]


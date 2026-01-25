# Author: Dr Diego Malpica MD

"""Operational route (Phase 2 baseline).

This page implements:
- Crew workspace selection (Mission 1 / Mission 2)
- Basic user profile list + creation (no authentication)

Scheduling and full profile tooling will be extended iteratively.
"""

from __future__ import annotations

import asyncio
import os
from typing import Any

import reflex as rx

from ..layout import app_shell
from ..theme import colors


class OperationalState(rx.State):
    """Operational state (mission workspace + user profiles)."""

    active_mission: str = "Mission 1"
    status: str = ""
    error: str = ""

    users: list[dict[str, Any]] = []

    # New user form (minimal; no passwords)
    new_username: str = ""
    new_full_name: str = ""
    new_sex: str = "other"

    @rx.event
    def set_active_mission(self, mission: str) -> None:
        value = str(mission).strip()
        if value not in {"Mission 1", "Mission 2"}:
            value = "Mission 1"
        self.active_mission = value
        os.environ["HRV_ACTIVE_MISSION"] = value
        self.status = f"Active mission set to {value}."
        self.error = ""

    @rx.event
    def set_new_username(self, value: str) -> None:
        """Set the new username form field."""
        self.new_username = str(value) if value else ""

    @rx.event
    def set_new_full_name(self, value: str) -> None:
        """Set the new full name form field."""
        self.new_full_name = str(value) if value else ""

    @rx.event
    def set_new_sex(self, value: str) -> None:
        """Set the new sex form field."""
        allowed = ("male", "female", "other")
        self.new_sex = str(value) if value in allowed else "other"

    async def _load_users_blocking(self) -> list[dict[str, Any]]:
        try:
            from app.user_database import UserDatabase  # type: ignore
        except Exception as exc:  # pragma: no cover
            raise ImportError(
                "Cannot import legacy `app.user_database`. Ensure Reflex is started with PYTHONPATH=.."
            ) from exc

        db = UserDatabase()
        items = db.list_users()
        rows: list[dict[str, Any]] = []
        for u in items[:500]:
            rows.append(
                {
                    "user_id": getattr(u, "user_id", ""),
                    "username": getattr(u, "username", ""),
                    "full_name": getattr(u, "full_name", ""),
                    "sex": getattr(u, "sex", ""),
                    "language": getattr(u, "language", ""),
                }
            )
        return rows

    @rx.event
    async def refresh_users(self) -> None:
        self.error = ""
        self.status = "Loading users..."
        try:
            rows = await asyncio.to_thread(self._load_users_blocking)
        except Exception as exc:
            self.users = []
            self.error = str(exc)
            self.status = ""
            return
        self.users = rows
        self.status = f"Loaded {len(rows)} user(s)."

    async def _create_user_blocking(self, username: str, full_name: str, sex: str) -> str:
        try:
            from app.user_database import UserDatabase, UserProfile  # type: ignore
        except Exception as exc:  # pragma: no cover
            raise ImportError(
                "Cannot import legacy `app.user_database`. Ensure Reflex is started with PYTHONPATH=.."
            ) from exc

        uname = username.strip()
        if not uname:
            raise ValueError("Username is required.")
        if len(uname) > 64:
            raise ValueError("Username too long (max 64).")

        profile = UserProfile(
            user_id="",
            username=uname,
            full_name=full_name.strip() or uname,
            email=None,
            date_of_birth=None,
            sex=sex.strip() or "other",
            height_cm=None,
            weight_kg=None,
            resting_hr_bpm=None,
            max_hr_bpm=None,
            vo2max_ml_kg_min=None,
            occupation=None,
            activity_level=None,
            smoking_status=None,
            alcohol_use=None,
            caffeine_intake_mg=None,
            medical_conditions=[],
            medications=[],
            language="en",
            created_at=None,
            updated_at=None,
        )
        db = UserDatabase()
        user_id = db.create_user(profile, password=None)
        return str(user_id)

    @rx.event
    async def create_user(self) -> None:
        self.error = ""
        self.status = "Creating user..."
        try:
            user_id = await asyncio.to_thread(
                self._create_user_blocking,
                self.new_username,
                self.new_full_name,
                self.new_sex,
            )
        except Exception as exc:
            self.error = str(exc)
            self.status = ""
            return

        self.status = f"User created: {user_id}"
        self.new_username = ""
        self.new_full_name = ""
        await self.refresh_users()


def _users_list(users: Any) -> rx.Component:
    c = colors()
    empty_view = rx.text("No users loaded yet.", color=c["text_secondary"])

    def _row(u: Any) -> rx.Component:
        if isinstance(u, dict):
            name = str(u.get("full_name") or u.get("username") or "User")
            username = str(u.get("username", ""))
            sex = str(u.get("sex", ""))
        else:
            full_name = u.get("full_name", "")
            username = u.get("username", "")
            name = rx.cond(full_name, full_name, rx.cond(username, username, "User"))
            sex = u.get("sex", "")

        return rx.box(
            rx.hstack(
                rx.vstack(
                    rx.heading(name, size="3", color=c["text_primary"]),
                    rx.text(username, color=c["text_secondary"], size="2"),
                    spacing="1",
                    align="start",
                ),
                rx.spacer(),
                rx.text(sex, color=c["text_secondary"], size="2"),
                width="100%",
                align="center",
            ),
            border=f"1px solid {c['border']}",
            border_radius="10px",
            padding="12px",
            width="100%",
        )

    rows_view = rx.vstack(rx.foreach(users, _row), spacing="3", width="100%")
    if isinstance(users, list):
        return rows_view if users else empty_view
    return rx.cond(users.length() > 0, rows_view, empty_view)


def operational_page() -> rx.Component:
    c = colors()
    body = rx.vstack(
        rx.callout(
            "Operational console (Reflex v2). Legacy Streamlit operational app remains at `app/operational_app.py`.",
            icon="info",
            color_scheme="blue",
        ),
        rx.heading("Crew workspace", size="4", color=c["text_primary"]),
        rx.hstack(
            rx.text("Active mission:", color=c["text_secondary"]),
            rx.select(
                ["Mission 1", "Mission 2"],
                value=OperationalState.active_mission,
                on_change=OperationalState.set_active_mission,
            ),
            rx.button("Load users", on_click=OperationalState.refresh_users),
            spacing="3",
            align="center",
            width="100%",
        ),
        rx.cond(
            OperationalState.error != "",
            rx.callout(OperationalState.error, icon="triangle_alert", color_scheme="red"),
            rx.text(OperationalState.status, color=c["text_secondary"]),
        ),
        rx.divider(),
        rx.heading("User profiles (no authentication)", size="4", color=c["text_primary"]),
        rx.vstack(
            rx.hstack(
                rx.input(
                    placeholder="Username (required)",
                    value=OperationalState.new_username,
                    on_change=OperationalState.set_new_username,
                    width="280px",
                ),
                rx.input(
                    placeholder="Full name (optional)",
                    value=OperationalState.new_full_name,
                    on_change=OperationalState.set_new_full_name,
                    width="340px",
                ),
                rx.select(
                    ["male", "female", "other"],
                    value=OperationalState.new_sex,
                    on_change=OperationalState.set_new_sex,
                ),
                rx.button("Create user", on_click=OperationalState.create_user),
                spacing="3",
                wrap="wrap",
                width="100%",
            ),
            _users_list(OperationalState.users),
            spacing="3",
            width="100%",
            max_width="1100px",
        ),
        rx.divider(),
        rx.heading("Scheduling (preview)", size="4", color=c["text_primary"]),
        rx.text(
            "Phase 2 will migrate the full scheduling dashboard and exports. For now, keep using the Streamlit operational app for scheduling workflows.",
            color=c["text_secondary"],
        ),
        rx.divider(),
        rx.heading("About", size="4", color=c["text_primary"]),
        rx.text("Author: Dr Diego Malpica MD", color=c["text_secondary"]),
        rx.text("Reflex v2 is a parallel UI track; no authentication by design.", color=c["text_secondary"]),
        spacing="4",
        align="start",
        width="100%",
        max_width="1100px",
    )
    return app_shell(title="Operational", body=body)


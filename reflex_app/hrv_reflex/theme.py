# Author: Dr Diego Malpica MD

"""Reflex UI theme primitives for Mission Control - Flight Surgeon (Reflex v2).

This file centralizes palette + typography decisions so the app stays consistent
and publication-grade.
"""

from __future__ import annotations

import reflex as rx


def colors() -> dict[str, str]:
    """Return the core semantic palette (aligned with Streamlit/ECharts rules)."""

    return {
        # Text (must be dark; avoid light grays)
        "text_primary": "#1a1a1a",
        "text_secondary": "#2c3e50",
        # Brand / accents
        "primary": "#2c3e50",  # dark blue-gray
        "accent": "#3498db",  # blue
        # Risk semantics
        "good": "#27ae60",
        "caution": "#f39c12",
        "poor": "#e74c3c",
        # Neutrals
        "bg": "#ffffff",
        "panel": "#ffffff",
        "border": "#2c3e50",
        "gridline": "rgba(44, 62, 80, 0.1)",
    }


def app_theme() -> rx.theme:
    """Create the Reflex theme object."""

    # Keep this intentionally minimal: Reflex theme props evolve across versions.
    # We enforce our publication-grade palette via per-component styles in the UI.
    return rx.theme(
        appearance="light",
        has_background=True,
        accent_color="blue",
    )


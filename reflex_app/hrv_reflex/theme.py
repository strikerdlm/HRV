# Author: Dr Diego Malpica MD

"""Reflex UI theme primitives for Mission Control - Flight Surgeon (Reflex v2).

This file centralizes palette + typography decisions so the app stays consistent
and publication-grade. Uses Radix theme system for modern, accessible UI.

Reference: https://reflex.dev/docs/styling/theming/
"""

from __future__ import annotations

import reflex as rx


def colors() -> dict[str, str]:
    """Return the core semantic palette (aligned with Streamlit/ECharts rules)."""

    return {
        # Text (must be dark; avoid light grays)
        "text_primary": "#1a1a1a",
        "text_secondary": "#475569",  # slate-600 for better contrast
        # Brand / accents
        "primary": "#0f172a",  # slate-900 for headers
        "accent": "#0ea5e9",  # sky-500 for interactive elements
        # Risk semantics (Radix color tokens)
        "good": "#10b981",  # emerald-500
        "caution": "#f59e0b",  # amber-500
        "poor": "#ef4444",  # red-500
        # Status
        "info": "#3b82f6",  # blue-500
        "success": "#22c55e",  # green-500
        "warning": "#eab308",  # yellow-500
        "error": "#dc2626",  # red-600
        # Neutrals
        "bg": "#ffffff",
        "panel": "#f8fafc",  # slate-50 for card backgrounds
        "border": "#e2e8f0",  # slate-200 for subtle borders
        "border_strong": "#94a3b8",  # slate-400 for strong borders
        "gridline": "rgba(15, 23, 42, 0.08)",
    }


def app_theme() -> rx.theme:
    """Create the Reflex theme object with modern, accessible styling.

    Uses Radix theme system for consistent, professional appearance.
    """
    return rx.theme(
        appearance="light",
        has_background=True,
        accent_color="sky",  # Modern blue accent
        gray_color="slate",  # Professional gray tones
        radius="medium",  # Rounded corners for modern look
        scaling="100%",  # Default scaling
        panel_background="translucent",  # Subtle panel backgrounds
    )


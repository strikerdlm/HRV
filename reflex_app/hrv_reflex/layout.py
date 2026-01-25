# Author: Dr Diego Malpica MD

"""Shared layout for the Reflex v2 UI."""

from __future__ import annotations

import reflex as rx

from .theme import colors


def _nav_link(label: str, href: str) -> rx.Component:
    c = colors()
    return rx.link(
        rx.button(
            label,
            variant="outline",
            border_color=c["border"],
            color=c["text_primary"],
        ),
        href=href,
        underline="none",
    )


def app_shell(*, title: str, body: rx.Component) -> rx.Component:
    """Wrap a page in the standard app chrome."""

    c = colors()
    header = rx.hstack(
        rx.vstack(
            rx.heading(title, size="6", color=c["text_primary"]),
            rx.text(
                "Mission Control - Flight Surgeon (Reflex v2) — no authentication.",
                size="2",
                color=c["text_secondary"],
            ),
            spacing="1",
            align="start",
        ),
        rx.spacer(),
        rx.hstack(
            _nav_link("Home", "/"),
            _nav_link("Space Weather DS", "/space-weather-ds"),
            _nav_link("Operational", "/operational"),
            _nav_link("Research", "/research"),
            _nav_link("ECharts demo", "/echarts-demo"),
            spacing="2",
        ),
        width="100%",
        padding_x="16px",
        padding_y="12px",
        border_bottom=f"1px solid {c['border']}",
        background=c["bg"],
        align="center",
    )

    return rx.vstack(
        header,
        rx.box(body, width="100%", padding="16px"),
        width="100%",
        min_height="100vh",
        background=c["bg"],
        spacing="0",
    )


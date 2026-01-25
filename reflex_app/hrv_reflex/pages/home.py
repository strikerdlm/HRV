# Author: Dr Diego Malpica MD

"""Home page for the Reflex v2 application."""

from __future__ import annotations

import reflex as rx

from ..layout import app_shell
from ..theme import colors


def home_page() -> rx.Component:
    c = colors()
    body = rx.vstack(
        rx.callout(
            "This is the new Reflex v2 app. The legacy Streamlit apps remain in `app/` unchanged.",
            icon="info",
            color_scheme="blue",
        ),
        rx.heading("Start here", size="5", color=c["text_primary"]),
        rx.text(
            "Phase 1 focuses on Space Weather Data Science for best performance on slow compute.",
            color=c["text_secondary"],
        ),
        rx.divider(),
        rx.vstack(
            rx.heading("Quick links", size="4", color=c["text_primary"]),
            rx.link("Space Weather DS", href="/space-weather-ds"),
            rx.link("Operational", href="/operational"),
            rx.link("Research", href="/research"),
            spacing="2",
            align="start",
        ),
        spacing="4",
        align="start",
        width="100%",
        max_width="1100px",
    )
    return app_shell(title="Mission Control — Reflex v2", body=body)


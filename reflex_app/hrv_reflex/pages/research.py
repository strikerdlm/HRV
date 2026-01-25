# Author: Dr Diego Malpica MD

"""Research route (Phase 3 baseline).

This is an intentionally lightweight research UI that prioritizes:
- fast, explicit analysis triggers
- background NOAA fetch
- ECharts-first visuals

Deep multi-tab parity with Streamlit Research is expanded iteratively.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import reflex as rx
from reflex_echarts import echarts

from ..layout import app_shell
from ..services.noaa_reflex import (
    build_noaa_chart_option,
    build_noaa_daily_series,
    fetch_noaa_bundles,
    get_noaa_source_keys,
)
from ..services.space_weather_ds_core import QCSettings, compute_session_metrics_from_text
from ..theme import colors


class ResearchState(rx.State):
    """Research baseline state (quick HRV + NOAA quicklook)."""

    rr_files: list[str] = []
    qc_method: str = "threshold_median"
    qc_max_deviation: float = 0.2
    qc_median_window: int = 11

    status: str = ""
    error: str = ""
    metrics: dict[str, Any] = {}

    # NOAA quicklook
    noaa_running: bool = False
    noaa_plot_key: str = "planetary_k_index_3h"
    noaa_plot_column: str = "Kp"
    noaa_plot_columns: list[str] = []
    noaa_option: dict[str, Any] = {}
    noaa_error: str = ""

    export_files: list[dict[str, str]] = []

    @rx.event
    def set_qc_method(self, value: str) -> None:
        """Set the QC method selection."""
        allowed = ("threshold_median", "threshold_prev")
        self.qc_method = str(value) if value in allowed else "threshold_median"

    @rx.event
    def set_noaa_plot_key(self, value: str) -> None:
        """Set the NOAA dataset key selection."""
        self.noaa_plot_key = str(value) if value else "planetary_k_index_3h"

    @rx.event
    def set_noaa_plot_column(self, value: str) -> None:
        """Set the NOAA value column selection."""
        self.noaa_plot_column = str(value) if value else "Kp"

    def _rr_dir(self) -> Path:
        base = rx.get_upload_dir() / "hrv_reflex" / "research_rr"
        base.mkdir(parents=True, exist_ok=True)
        return base

    def _export_dir(self) -> Path:
        base = rx.get_upload_dir() / "hrv_reflex" / "research_exports"
        base.mkdir(parents=True, exist_ok=True)
        return base

    @rx.event
    async def handle_rr_upload(self, files: list[Any]) -> None:
        self.error = ""
        self.status = ""
        if not isinstance(files, list) or not files:
            self.error = "No files received."
            return
        storage = self._rr_dir()
        saved: list[str] = []
        for item in files[:10]:
            name = str(getattr(item, "filename", "rr.txt")).replace("\\", "/").split("/")[-1]
            name = name[:120] or "rr.txt"
            path = storage / name
            try:
                data = await item.read()
            except Exception as exc:
                self.error = str(exc)
                continue
            if not isinstance(data, (bytes, bytearray)) or len(data) > 10_000_000:
                self.error = f"{name}: invalid or too large."
                continue
            with path.open("wb") as handle:
                handle.write(data)
            saved.append(name)
        self.rr_files = saved
        self.status = f"Uploaded {len(saved)} file(s)."

    @rx.event(background=True)
    async def run_quick_hrv(self) -> None:
        files = list(self.rr_files)[:1]
        if not files:
            async with self:
                self.error = "Upload an RR file first."
            return
        qc = QCSettings(
            method=str(self.qc_method),
            max_deviation=float(self.qc_max_deviation),
            median_window=int(self.qc_median_window),
        )
        path = self._rr_dir() / files[0]
        async with self:
            self.error = ""
            self.status = "Computing HRV..."
            self.metrics = {}

        try:
            raw = await asyncio.to_thread(path.read_bytes)
            content = raw.decode("utf-8", errors="ignore")
            out = await asyncio.to_thread(
                compute_session_metrics_from_text,
                filename=files[0],
                content=content,
                qc=qc,
                include_advanced=False,
            )
        except Exception as exc:
            async with self:
                self.error = str(exc)
                self.status = ""
            return

        async with self:
            self.metrics = out
            self.status = "Done."

    @rx.event(background=True)
    async def fetch_noaa(self) -> None:
        async with self:
            self.noaa_running = True
            self.noaa_error = ""
            self.noaa_option = {}
            self.noaa_plot_columns = []
        try:
            bundles, errors = await asyncio.to_thread(
                fetch_noaa_bundles,
                [str(self.noaa_plot_key)],
                use_cache=True,
                overall_timeout_s=30.0,
            )
        except Exception as exc:
            async with self:
                self.noaa_error = str(exc)
                self.noaa_running = False
            return
        if errors:
            async with self:
                self.noaa_error = "; ".join(f"{k}: {v}" for k, v in errors.items())
        bundle = bundles.get(str(self.noaa_plot_key))
        option: dict[str, Any] = {}
        cols: list[str] = []
        if bundle is not None:
            cols = list(getattr(bundle, "value_columns", ()) or ())
            col = self.noaa_plot_column if self.noaa_plot_column in cols else (cols[0] if cols else "")
            if col:
                try:
                    series = build_noaa_daily_series(bundle=bundle, value_column=col)
                    option = build_noaa_chart_option(series=series, value_column=col)
                except Exception as exc:
                    async with self:
                        self.noaa_error = str(exc)
        async with self:
            self.noaa_plot_columns = cols
            self.noaa_option = option
            self.noaa_running = False

    @rx.event
    async def export_quicklook(self) -> None:
        if not self.metrics:
            self.export_files = []
            return
        export_dir = self._export_dir()
        import json

        json_name = "research_quicklook_metrics.json"
        await asyncio.to_thread(
            (export_dir / json_name).write_text,
            json.dumps(self.metrics, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        self.export_files = [{"name": json_name, "url": rx.get_upload_url(f"hrv_reflex/research_exports/{json_name}")}]


def _metrics_summary_view(metrics: Any) -> rx.Component:
    c = colors()
    keys = ["rmssd", "sdnn", "mean_hr", "pnn50", "artifact_pct", "n_rr_intervals"]
    rows = [rx.text(k, ": ", metrics.get(k), color=c["text_secondary"]) for k in keys]
    box = rx.box(
        rx.vstack(*rows, spacing="1", align="start"),
        border=f"1px solid {c['border']}",
        border_radius="10px",
        padding="12px",
        width="100%",
        max_width="1100px",
    )
    empty_view = rx.text("", color=c["text_secondary"])
    if isinstance(metrics, dict):
        return box if metrics else empty_view
    return rx.cond(metrics.length() > 0, box, empty_view)


def research_page() -> rx.Component:
    c = colors()
    upload_id = "research_rr_upload"
    try:
        noaa_keys = get_noaa_source_keys()
    except Exception:
        noaa_keys = ["planetary_k_index_3h", "geospace_dst", "f107_flux"]

    body = rx.vstack(
        rx.callout(
            "Research (Reflex v2). This is a fast baseline: explicit actions, background NOAA fetch, ECharts-first.",
            icon="info",
            color_scheme="blue",
        ),
        rx.text("Legacy Streamlit research entrypoint remains at `app/research_app.py`.", color=c["text_secondary"]),
        rx.divider(),
        rx.heading("HRV quicklook (single file)", size="4", color=c["text_primary"]),
        rx.upload(
            rx.text("Upload RR file (TXT/CSV)."),
            id=upload_id,
            accept={"text/plain": [".txt", ".csv"]},
            multiple=False,
            max_files=1,
        ),
        rx.button(
            "Upload",
            on_click=ResearchState.handle_rr_upload(rx.upload_files(upload_id=upload_id)),
        ),
        rx.hstack(
            rx.text("QC method:", color=c["text_secondary"]),
            rx.select(
                ["threshold_median", "threshold_prev"],
                value=ResearchState.qc_method,
                on_change=ResearchState.set_qc_method,
            ),
            spacing="2",
            align="center",
        ),
        rx.button("Run HRV quicklook", on_click=ResearchState.run_quick_hrv),
        rx.cond(
            ResearchState.error != "",
            rx.callout(ResearchState.error, icon="triangle_alert", color_scheme="red"),
            rx.text(ResearchState.status, color=c["text_secondary"]),
        ),
        rx.cond(
            ResearchState.metrics.length() > 0,
            _metrics_summary_view(ResearchState.metrics),
            rx.text("", color=c["text_secondary"]),
        ),
        rx.divider(),
        rx.heading("NOAA quicklook", size="4", color=c["text_primary"]),
        rx.hstack(
            rx.text("Dataset:", color=c["text_secondary"]),
            rx.select(
                noaa_keys,
                value=ResearchState.noaa_plot_key,
                on_change=ResearchState.set_noaa_plot_key,
            ),
            rx.text("Value column:", color=c["text_secondary"]),
            rx.select(
                ResearchState.noaa_plot_columns,
                value=ResearchState.noaa_plot_column,
                on_change=ResearchState.set_noaa_plot_column,
            ),
            rx.button("Fetch", on_click=ResearchState.fetch_noaa, loading=ResearchState.noaa_running),
            spacing="2",
            wrap="wrap",
            align="center",
            width="100%",
        ),
        rx.cond(
            ResearchState.noaa_error != "",
            rx.callout(ResearchState.noaa_error, icon="triangle_alert", color_scheme="yellow"),
            rx.text("", color=c["text_secondary"]),
        ),
        rx.cond(
            ResearchState.noaa_option != {},
            rx.box(
                echarts(option=ResearchState.noaa_option),
                width="100%",
                max_width="1100px",
                border=f"1px solid {c['border']}",
                border_radius="10px",
                padding="8px",
            ),
            rx.text("Fetch NOAA feed to render chart.", color=c["text_secondary"]),
        ),
        rx.divider(),
        rx.heading("Export", size="4", color=c["text_primary"]),
        rx.button("Export quicklook metrics (JSON)", on_click=ResearchState.export_quicklook),
        rx.cond(
            ResearchState.export_files != [],
            rx.vstack(
                rx.foreach(
                    ResearchState.export_files,
                    lambda f: rx.link(f.get("name", "export"), href=f.get("url", "#")),
                ),
                spacing="2",
                align="start",
            ),
            rx.text("No exports yet.", color=c["text_secondary"]),
        ),
        spacing="4",
        align="start",
        width="100%",
        max_width="1100px",
    )
    return app_shell(title="Research", body=body)


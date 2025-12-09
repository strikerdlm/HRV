"""
Device-specific data import interfaces for Mission Control - Flight Surgeon.

This module provides the PRIMARY import interface for physiological data:
- Polar H10/H9 RR interval files (main import)
- Garmin Vivosmart 5 wellness exports
- ActiGraph GT3X accelerometer data
- Compumedics Somfit Pro sleep data
- Generic RR interval text files

Author: Dr. Diego L. Malpica, MD - Aerospace Medicine Specialist
"""

from __future__ import annotations

import io
import re
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import streamlit as st

try:
    from garmin_import import (
        extract_rr_intervals_from_garmin,
        get_daily_physiology_summary,
        import_garmin_data,
        parse_fit_file,
    )
    GARMIN_IMPORT_AVAILABLE = True
except ImportError:
    GARMIN_IMPORT_AVAILABLE = False


@dataclass(slots=True)
class ImportedRRData:
    """Container for imported RR interval data."""
    
    source_device: str
    filename: str
    rr_intervals_ms: np.ndarray
    timestamps: Optional[np.ndarray] = None
    recording_start: Optional[datetime] = None
    sample_count: int = 0
    duration_seconds: float = 0.0
    mean_hr_bpm: float = 0.0
    quality_score: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self) -> None:
        self.sample_count = len(self.rr_intervals_ms) if self.rr_intervals_ms is not None else 0
        if self.sample_count > 0:
            self.duration_seconds = float(np.sum(self.rr_intervals_ms) / 1000.0)
            mean_rr = float(np.mean(self.rr_intervals_ms))
            self.mean_hr_bpm = 60000.0 / mean_rr if mean_rr > 0 else 0.0


def _parse_timestamp_from_filename(filename: str) -> Optional[datetime]:
    """Extract timestamp from filename if present.
    
    Supports formats:
    - YYYY-MM-DD HH-MM-SS.txt
    - YYYY-MM-DD_HH-MM-SS.txt
    - YYYYMMDD_HHMMSS.txt
    """
    file_tz = timezone(timedelta(hours=-5))  # Treat filenames as local UTC-5 and convert to UTC
    patterns = [
        r"(\d{4})-(\d{2})-(\d{2})[\s_](\d{2})-(\d{2})-(\d{2})",
        r"(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, filename)
        if match:
            groups = match.groups()
            try:
                parsed = datetime(
                    year=int(groups[0]),
                    month=int(groups[1]),
                    day=int(groups[2]),
                    hour=int(groups[3]),
                    minute=int(groups[4]),
                    second=int(groups[5]),
                    tzinfo=file_tz,
                )
                return parsed.astimezone(timezone.utc)
            except ValueError:
                continue
    return None


def _build_rr_timestamps(
    rr_ms: np.ndarray, start_ts: datetime
) -> np.ndarray:
    """Build cumulative timestamps from RR intervals."""
    if rr_ms.size == 0:
        return np.array([], dtype="datetime64[ns]")
    rr_cum_s = np.cumsum(rr_ms) / 1000.0
    return start_ts + pd.to_timedelta(rr_cum_s, unit="s")


def _validate_rr_intervals(rr_ms: np.ndarray) -> Tuple[np.ndarray, float]:
    """Validate and filter RR intervals, returning cleaned data and quality score."""
    if len(rr_ms) == 0:
        return rr_ms, 0.0
    
    # Physiological bounds: 300ms (200bpm) to 2000ms (30bpm)
    valid_mask = (rr_ms >= 300) & (rr_ms <= 2000)
    valid_count = np.sum(valid_mask)
    quality_score = valid_count / len(rr_ms) if len(rr_ms) > 0 else 0.0
    
    return rr_ms[valid_mask], quality_score


def _render_import_stats(data: ImportedRRData) -> None:
    """Render import statistics using Streamlit metrics."""
    duration_min = data.duration_seconds / 60.0
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("RR Samples", f"{data.sample_count:,}")
        st.metric("Mean HR", f"{data.mean_hr_bpm:.1f} bpm")
    with col2:
        st.metric("Duration", f"{duration_min:.1f} min")
        st.metric("Quality", f"{data.quality_score:.0%}")


def render_primary_import_section() -> Dict[str, ImportedRRData]:
    """Render the primary device import section in sidebar.
    
    This replaces the old text file upload with a modern device-centric interface.
    
    Returns:
        Dictionary of device_name: ImportedRRData for all successful imports.
    """
    imported_data: Dict[str, ImportedRRData] = {}
    
    # Sidebar header
    st.sidebar.markdown(
        """
        <div style="
            background: linear-gradient(135deg, #667eea15 0%, #764ba215 100%);
            border-radius: 12px;
            padding: 1rem;
            margin-bottom: 0.5rem;
            border: 1px solid rgba(102, 126, 234, 0.2);
        ">
            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 0.5rem;">
                <span style="font-size: 1.5rem;">🫀</span>
                <div>
                    <div style="color: #667eea; font-weight: 700; font-size: 1rem;">Data Import</div>
                    <div style="color: #888; font-size: 0.75rem;">Load your physiological data</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # Primary: Polar H10/H9 Import
    polar_data = _render_polar_section()
    for name, data in polar_data.items():
        imported_data[f"Polar_{name}"] = data
    
    # Secondary: Garmin Import
    garmin_data = _render_garmin_section()
    if garmin_data is not None:
        imported_data[f"Garmin_{garmin_data.filename}"] = garmin_data
    
    # Tertiary: Generic RR file import (collapsed by default)
    generic_data = _render_generic_rr_section()
    for name, data in generic_data.items():
        imported_data[f"RR_{name}"] = data
    
    # ActiGraph (for activity context)
    actigraph_data = _render_actigraph_section()
    if actigraph_data is not None:
        imported_data[f"ActiGraph_{actigraph_data.filename}"] = actigraph_data
    
    # Somfit Pro (for sleep context)
    somfit_data = _render_somfit_section()
    if somfit_data is not None:
        imported_data[f"Somfit_{somfit_data.filename}"] = somfit_data
    
    return imported_data


def _render_polar_section() -> Dict[str, ImportedRRData]:
    """Render Polar H10/H9 import section (PRIMARY). Supports multiple files."""
    
    with st.sidebar.expander("❤️ Polar H10/H9 RR Data", expanded=True):
        st.markdown(
            """
            <div style="font-size: 0.8rem; color: #888; margin-bottom: 0.75rem;">
                Upload RR intervals from Polar Sensor Logger or Polar Beat app
            </div>
            """,
            unsafe_allow_html=True
        )
        
        uploaded_files = st.file_uploader(
            "Select Polar RR file(s)",
            type=["txt", "csv"],
            key="polar_rr_upload",
            help="One RR interval (ms) per line. Supports Polar Sensor Logger export.",
            label_visibility="collapsed",
            accept_multiple_files=True,
        )
        
        results: Dict[str, ImportedRRData] = {}
        if uploaded_files:
            max_files = 10
            for uploaded_file in uploaded_files[:max_files]:
                try:
                    content = uploaded_file.read().decode("utf-8")
                    lines = content.strip().split("\n")
                    
                    rr_values = []
                    for line in lines:
                        line = line.strip()
                        if not line:
                            continue
                        if line.lower().startswith(("rr", "interval", "time", "#")):
                            continue
                        try:
                            parts = line.replace(",", "\t").split("\t")
                            value = float(parts[0])
                            if 200 <= value <= 3000:  # Valid RR range
                                rr_values.append(value)
                        except (ValueError, IndexError):
                            continue
                    
                    if len(rr_values) > 10:
                        rr_array = np.array(rr_values, dtype=np.float64)
                        clean_rr, quality = _validate_rr_intervals(rr_array)
                        
                        start_ts = _parse_timestamp_from_filename(uploaded_file.name) or datetime.now(timezone.utc)
                        timestamps = _build_rr_timestamps(clean_rr, start_ts)
                        
                        data = ImportedRRData(
                            source_device="Polar H10/H9",
                            filename=uploaded_file.name,
                            rr_intervals_ms=clean_rr,
                            timestamps=timestamps,
                            recording_start=start_ts,
                            quality_score=quality,
                            metadata={"original_count": len(rr_values)},
                        )
                        
                        st.success(f"✅ Loaded {data.sample_count:,} RR intervals from {uploaded_file.name}")
                        _render_import_stats(data)
                        results[uploaded_file.name] = data
                    else:
                        st.warning(f"⚠️ Too few valid RR intervals found in {uploaded_file.name}")
                        
                except Exception as e:
                    st.error(f"❌ Error reading file {uploaded_file.name}: {e}")
            
            if len(uploaded_files) > max_files:
                st.warning(f"Processed first {max_files} files; please upload fewer files per batch.")
        
        return results


def _render_garmin_section() -> Optional[ImportedRRData]:
    """Render Garmin Vivosmart 5 import section."""
    
    with st.sidebar.expander("⌚ Garmin Vivosmart 5", expanded=False):
        st.markdown(
            """
            <div style="font-size: 0.8rem; color: #888; margin-bottom: 0.75rem;">
                Upload wellness data export from Garmin Connect
            </div>
            """,
            unsafe_allow_html=True
        )
        
        uploaded_file = st.file_uploader(
            "Select Garmin export file",
            type=["csv", "json", "zip", "fit"],
            key="garmin_upload",
            help="Export from Garmin Connect: Account → Export Your Data",
            label_visibility="collapsed"
        )
        
        if uploaded_file is not None:
            try:
                file_name = uploaded_file.name
                lower_name = file_name.lower()

                if lower_name.endswith(".fit"):
                    if not GARMIN_IMPORT_AVAILABLE:
                        st.error("Garmin FIT parser unavailable. Install fitparse and restart.")
                        return None
                    tmp_path: Optional[Path] = None
                    try:
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".fit") as tmp:
                            tmp.write(uploaded_file.read())
                            tmp_path = Path(tmp.name)
                        garmin_data = import_garmin_data(fit_path=tmp_path)
                        daily_df = get_daily_physiology_summary(garmin_data)
                        if not daily_df.empty:
                            st.session_state["garmin_daily_pending"] = daily_df.to_dict("records")
                        rr_array = extract_rr_intervals_from_garmin(garmin_data)
                        if rr_array.size == 0 and not garmin_data.hr_df.empty:
                            # Derive RR from HR if present (approximation)
                            hr_values = garmin_data.hr_df.get("heart_rate", pd.Series(dtype=float)).dropna()
                            if not hr_values.empty:
                                rr_array = 60000.0 / hr_values.values
                        if rr_array.size > 10:
                            clean_rr, quality = _validate_rr_intervals(rr_array.astype(np.float64))
                            data = ImportedRRData(
                                source_device="Garmin Vivosmart 5",
                                filename=file_name,
                                rr_intervals_ms=clean_rr,
                                quality_score=quality,
                                metadata={"source": garmin_data.source},
                            )
                            st.success(f"✅ Parsed FIT file {file_name} with {data.sample_count:,} RR intervals")
                            _render_import_stats(data)
                            return data
                        st.info("ℹ️ FIT file parsed but no RR intervals were present. Wellness metrics stored.")
                    finally:
                        if tmp_path and tmp_path.exists():
                            try:
                                tmp_path.unlink()
                            except OSError:
                                pass

                elif lower_name.endswith(".zip"):
                    if not GARMIN_IMPORT_AVAILABLE:
                        st.error("Garmin ZIP parser unavailable.")
                        return None
                    tmp_path = None
                    try:
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
                            tmp.write(uploaded_file.read())
                            tmp_path = Path(tmp.name)
                        garmin_data = import_garmin_data(zip_path=tmp_path)
                        daily_df = get_daily_physiology_summary(garmin_data)
                        if not daily_df.empty:
                            st.session_state["garmin_daily_pending"] = daily_df.to_dict("records")
                            st.success(f"✅ Parsed Garmin wellness ZIP {file_name}. Stored {len(daily_df)} day(s) of wrist metrics for the active profile.")
                        else:
                            st.info("ZIP parsed but no wellness metrics were detected.")
                    finally:
                        if tmp_path and tmp_path.exists():
                            try:
                                tmp_path.unlink()
                            except OSError:
                                pass
                    return None

                elif lower_name.endswith(".csv"):
                    df = pd.read_csv(uploaded_file)
                    
                    # Look for RR or HR columns
                    rr_col = None
                    for col in df.columns:
                        if "rr" in col.lower() or "interval" in col.lower():
                            rr_col = col
                            break
                    
                    if rr_col is not None:
                        rr_values = df[rr_col].dropna().values
                        if len(rr_values) > 10:
                            rr_array = np.array(rr_values, dtype=np.float64)
                            clean_rr, quality = _validate_rr_intervals(rr_array)
                            
                            data = ImportedRRData(
                                source_device="Garmin Vivosmart 5",
                                filename=uploaded_file.name,
                                rr_intervals_ms=clean_rr,
                                quality_score=quality,
                            )
                            
                            st.success(f"✅ Loaded {data.sample_count:,} RR intervals")
                            _render_import_stats(data)
                            return data
                    
                    # If no RR data, try to derive from HR
                    hr_col = None
                    for col in df.columns:
                        if "heart" in col.lower() or "hr" in col.lower():
                            hr_col = col
                            break
                    
                    if hr_col is not None:
                        hr_values = df[hr_col].dropna().values
                        if len(hr_values) > 10:
                            # Convert HR to approximate RR (not beat-to-beat)
                            rr_from_hr = 60000.0 / hr_values[hr_values > 30]
                            clean_rr, quality = _validate_rr_intervals(rr_from_hr)
                            
                            data = ImportedRRData(
                                source_device="Garmin Vivosmart 5 (HR-derived)",
                                filename=uploaded_file.name,
                                rr_intervals_ms=clean_rr,
                                quality_score=quality * 0.7,  # Lower quality for HR-derived
                            )
                            
                            st.warning("⚠️ Using HR-derived RR (less accurate)")
                            _render_import_stats(data)
                            return data
                    
                    st.info("ℹ️ No RR interval data found in file")
                    
            except Exception as e:
                st.error(f"❌ Error reading file: {e}")
    
    return None


def _render_generic_rr_section() -> Dict[str, ImportedRRData]:
    """Render generic RR interval file import (fallback). Supports multiple files."""
    
    with st.sidebar.expander("📄 Generic RR File", expanded=False):
        st.markdown(
            """
            <div style="font-size: 0.8rem; color: #888; margin-bottom: 0.75rem;">
                Upload any RR interval file (one value per line, in ms)
            </div>
            """,
            unsafe_allow_html=True
        )
        
        uploaded_files = st.file_uploader(
            "Select RR file(s)",
            type=["txt", "csv"],
            key="generic_rr_upload",
            help="One RR interval (milliseconds) per line",
            label_visibility="collapsed",
            accept_multiple_files=True,
        )
        
        results: Dict[str, ImportedRRData] = {}
        if uploaded_files:
            max_files = 10
            for uploaded_file in uploaded_files[:max_files]:
                try:
                    content = uploaded_file.read().decode("utf-8")
                    lines = content.strip().split("\n")
                    
                    rr_values = []
                    for line in lines:
                        line = line.strip()
                        if not line or line.startswith(("#", "RR", "rr", "time")):
                            continue
                        try:
                            parts = line.replace(",", "\t").replace(";", "\t").split("\t")
                            value = float(parts[0])
                            if 200 <= value <= 3000:
                                rr_values.append(value)
                        except (ValueError, IndexError):
                            continue
                    
                    if len(rr_values) > 10:
                        rr_array = np.array(rr_values, dtype=np.float64)
                        clean_rr, quality = _validate_rr_intervals(rr_array)
                        start_ts = _parse_timestamp_from_filename(uploaded_file.name) or datetime.now(timezone.utc)
                        timestamps = _build_rr_timestamps(clean_rr, start_ts)
                        
                        data = ImportedRRData(
                            source_device="Generic RR File",
                            filename=uploaded_file.name,
                            rr_intervals_ms=clean_rr,
                            timestamps=timestamps,
                            recording_start=start_ts,
                            quality_score=quality,
                        )
                        
                        st.success(f"✅ Loaded {data.sample_count:,} RR intervals from {uploaded_file.name}")
                        _render_import_stats(data)
                        results[uploaded_file.name] = data
                    else:
                        st.warning(f"⚠️ Too few valid RR intervals found in {uploaded_file.name}")
                        
                except Exception as e:
                    st.error(f"❌ Error processing {uploaded_file.name}: {e}")
            
            if len(uploaded_files) > max_files:
                st.warning(f"Processed first {max_files} files; please upload fewer files per batch.")
        
        return results


def _render_actigraph_section() -> Optional[ImportedRRData]:
    """Render ActiGraph GT3X import section."""
    
    with st.sidebar.expander("📊 ActiGraph GT3X", expanded=False):
        st.markdown(
            """
            <div style="font-size: 0.8rem; color: #888; margin-bottom: 0.75rem;">
                Upload ActiGraph accelerometer data for activity context
            </div>
            """,
            unsafe_allow_html=True
        )
        
        uploaded_file = st.file_uploader(
            "Select ActiGraph file",
            type=["csv", "gt3x", "agd"],
            key="actigraph_upload",
            help="Export from ActiLife software",
            label_visibility="collapsed"
        )
        
        if uploaded_file is not None:
            st.info("ℹ️ ActiGraph data loaded (activity context)")
            # ActiGraph doesn't provide RR data directly
            # This would be used for activity correlation
    
    return None


def _render_somfit_section() -> Optional[ImportedRRData]:
    """Render Somfit Pro import section."""
    
    with st.sidebar.expander("😴 Somfit Pro", expanded=False):
        st.markdown(
            """
            <div style="font-size: 0.8rem; color: #888; margin-bottom: 0.75rem;">
                Upload Somfit Pro sleep study data
            </div>
            """,
            unsafe_allow_html=True
        )
        
        uploaded_file = st.file_uploader(
            "Select Somfit file",
            type=["edf", "csv", "xml"],
            key="somfit_upload",
            help="Export from Profusion Nexus360",
            label_visibility="collapsed"
        )
        
        if uploaded_file is not None:
            st.info("ℹ️ Somfit data loaded (sleep context)")
            # Somfit provides sleep staging, not direct RR
    
    return None


# Legacy functions for backwards compatibility
def render_all_device_imports() -> Dict[str, ImportedRRData]:
    """Legacy function - redirects to primary import section."""
    return render_primary_import_section()


def render_polar_import_section() -> Optional[ImportedRRData]:
    """Legacy function for standalone Polar import."""
    # For backward compatibility, return the first imported dataset if present.
    polar_data = _render_polar_section()
    return next(iter(polar_data.values()), None)


def render_garmin_import_section() -> Optional[ImportedRRData]:
    """Legacy function for standalone Garmin import."""
    return _render_garmin_section()

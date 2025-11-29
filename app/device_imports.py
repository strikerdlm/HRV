"""
Device-specific data import interfaces for HRV Analysis Suite.

Provides clean, modern import interfaces for:
- Polar H10/H9 RR interval files
- Garmin Vivosmart 5 wellness exports
- ActiGraph GT3X accelerometer data
- Compumedics Somfit Pro sleep data

Author: Dr. Diego L. Malpica, MD - Aerospace Medicine Specialist
"""

from __future__ import annotations

import io
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import streamlit as st


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
    metadata: Dict[str, Any] = None
    
    def __post_init__(self) -> None:
        if self.metadata is None:
            self.metadata = {}
        self.sample_count = len(self.rr_intervals_ms)
        if self.sample_count > 0:
            self.duration_seconds = float(np.sum(self.rr_intervals_ms) / 1000.0)
            self.mean_hr_bpm = 60000.0 / float(np.mean(self.rr_intervals_ms))


def _render_import_success_card(data: ImportedRRData) -> None:
    """Render a success card after successful import."""
    duration_min = data.duration_seconds / 60.0
    
    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, rgba(32, 201, 151, 0.1) 0%, rgba(102, 126, 234, 0.1) 100%);
        border-radius: 12px;
        padding: 1rem;
        border: 1px solid rgba(32, 201, 151, 0.3);
        margin-top: 0.5rem;
    ">
        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 0.5rem;">
            <span style="font-size: 1.5rem;">✅</span>
            <span style="color: #20c997; font-weight: 600;">Import Successful</span>
        </div>
        <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 0.5rem;">
            <div style="background: rgba(0,0,0,0.2); padding: 0.5rem; border-radius: 8px;">
                <div style="color: #888; font-size: 0.75rem;">RR Samples</div>
                <div style="color: #fff; font-weight: 600;">{data.sample_count:,}</div>
            </div>
            <div style="background: rgba(0,0,0,0.2); padding: 0.5rem; border-radius: 8px;">
                <div style="color: #888; font-size: 0.75rem;">Duration</div>
                <div style="color: #fff; font-weight: 600;">{duration_min:.1f} min</div>
            </div>
            <div style="background: rgba(0,0,0,0.2); padding: 0.5rem; border-radius: 8px;">
                <div style="color: #888; font-size: 0.75rem;">Mean HR</div>
                <div style="color: #fff; font-weight: 600;">{data.mean_hr_bpm:.1f} bpm</div>
            </div>
            <div style="background: rgba(0,0,0,0.2); padding: 0.5rem; border-radius: 8px;">
                <div style="color: #888; font-size: 0.75rem;">Source</div>
                <div style="color: #fff; font-weight: 600;">{data.source_device}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_polar_import_section() -> Optional[ImportedRRData]:
    """Render Polar H10/H9 RR interval import interface.
    
    Returns:
        ImportedRRData if successful import, None otherwise.
    """
    with st.sidebar.expander("❤️ Polar H10/H9 RR Import", expanded=False):
        st.markdown("""
        <div style="
            background: linear-gradient(135deg, #e73c3e15 0%, #b7272815 100%);
            border-radius: 10px;
            padding: 0.75rem;
            margin-bottom: 0.75rem;
            border: 1px solid rgba(231, 60, 62, 0.3);
        ">
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 0.5rem;">
                <span style="font-size: 1.2rem;">❤️</span>
                <span style="color: #e73c3e; font-weight: 600; font-size: 0.9rem;">Polar Beat Export</span>
            </div>
            <p style="margin: 0; color: #888; font-size: 0.75rem;">
                Upload RR interval files (.txt) exported from Polar Beat or Elite HRV apps.
                Format: One RR interval (ms) per line.
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        polar_file = st.file_uploader(
            "Select Polar RR file",
            type=["txt", "csv", "hrm"],
            key="polar_rr_uploader",
            help="Upload .txt file with RR intervals in milliseconds (one per line)",
        )
        
        if polar_file is not None:
            try:
                content = polar_file.getvalue().decode("utf-8")
                lines = content.strip().split("\n")
                
                # Parse RR intervals
                rr_values = []
                for line in lines:
                    line = line.strip()
                    if not line or line.startswith("#") or line.startswith("RR"):
                        continue
                    try:
                        # Handle comma-separated values
                        if "," in line:
                            parts = line.split(",")
                            for part in parts:
                                val = float(part.strip())
                                if 200 <= val <= 3000:
                                    rr_values.append(val)
                        else:
                            val = float(line)
                            if 200 <= val <= 3000:
                                rr_values.append(val)
                    except ValueError:
                        continue
                
                if len(rr_values) < 10:
                    st.error("❌ Not enough valid RR intervals found. Ensure values are in milliseconds (200-3000 range).")
                    return None
                
                rr_ms = np.array(rr_values, dtype=np.float64)
                
                # Try to extract timestamp from filename
                recording_start = None
                try:
                    # Pattern: YYYY-MM-DD HH-MM-SS or similar
                    import re
                    match = re.search(r'(\d{4}[-_]\d{2}[-_]\d{2}[-_\s]\d{2}[-_]\d{2}[-_]\d{2})', polar_file.name)
                    if match:
                        dt_str = match.group(1).replace("_", "-").replace(" ", "-")
                        parts = dt_str.split("-")
                        if len(parts) >= 6:
                            recording_start = datetime(
                                int(parts[0]), int(parts[1]), int(parts[2]),
                                int(parts[3]), int(parts[4]), int(parts[5]),
                                tzinfo=timezone.utc
                            )
                except Exception:
                    pass
                
                result = ImportedRRData(
                    source_device="Polar H10/H9",
                    filename=polar_file.name,
                    rr_intervals_ms=rr_ms,
                    recording_start=recording_start,
                )
                
                _render_import_success_card(result)
                
                # Quick visualization
                with st.expander("📊 Preview RR Intervals"):
                    # Simple inline chart
                    time_cumsum = np.cumsum(rr_ms) / 1000.0 / 60.0  # Convert to minutes
                    chart_data = pd.DataFrame({
                        "Time (min)": time_cumsum[:500] if len(time_cumsum) > 500 else time_cumsum,
                        "RR (ms)": rr_ms[:500] if len(rr_ms) > 500 else rr_ms,
                    })
                    st.line_chart(chart_data.set_index("Time (min)"))
                    if len(rr_ms) > 500:
                        st.caption("Showing first 500 samples")
                
                return result
                
            except Exception as exc:
                st.error(f"❌ Failed to parse Polar file: {exc}")
                return None
    
    return None


def render_garmin_import_section() -> Optional[ImportedRRData]:
    """Render Garmin Vivosmart 5 import interface.
    
    Returns:
        ImportedRRData if successful import, None otherwise.
    """
    with st.sidebar.expander("⌚ Garmin Vivosmart 5 Import", expanded=False):
        st.markdown("""
        <div style="
            background: linear-gradient(135deg, #00a8e815 0%, #007acc15 100%);
            border-radius: 10px;
            padding: 0.75rem;
            margin-bottom: 0.75rem;
            border: 1px solid rgba(0, 168, 232, 0.3);
        ">
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 0.5rem;">
                <span style="font-size: 1.2rem;">⌚</span>
                <span style="color: #00a8e8; font-weight: 600; font-size: 0.9rem;">Garmin Connect Export</span>
            </div>
            <p style="margin: 0; color: #888; font-size: 0.75rem;">
                Upload wellness data exported from Garmin Connect. Supports ZIP bulk exports 
                and individual FIT/CSV files.
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        export_type = st.radio(
            "Export Type",
            ["Wellness Summary (CSV)", "Bulk Export (ZIP)", "FIT File"],
            key="garmin_export_type",
            horizontal=True,
        )
        
        if export_type == "Wellness Summary (CSV)":
            garmin_file = st.file_uploader(
                "Select Garmin wellness CSV",
                type=["csv"],
                key="garmin_csv_uploader",
            )
            
            if garmin_file is not None:
                try:
                    df = pd.read_csv(garmin_file)
                    
                    # Look for heart rate data columns
                    hr_columns = [c for c in df.columns if "heart" in c.lower() or "hr" in c.lower()]
                    resting_hr_cols = [c for c in hr_columns if "rest" in c.lower()]
                    
                    if resting_hr_cols:
                        hr_col = resting_hr_cols[0]
                    elif hr_columns:
                        hr_col = hr_columns[0]
                    else:
                        st.warning("No heart rate column found in CSV")
                        return None
                    
                    # Convert HR to estimated RR intervals
                    hr_values = pd.to_numeric(df[hr_col], errors="coerce").dropna()
                    valid_hr = hr_values[(hr_values >= 30) & (hr_values <= 200)]
                    
                    if len(valid_hr) < 5:
                        st.warning("Insufficient valid HR data found")
                        return None
                    
                    # Estimate RR from HR (approximation)
                    rr_ms = (60000.0 / valid_hr.values).astype(np.float64)
                    
                    result = ImportedRRData(
                        source_device="Garmin Vivosmart 5",
                        filename=garmin_file.name,
                        rr_intervals_ms=rr_ms,
                        metadata={"source_column": hr_col, "data_type": "HR_to_RR"},
                    )
                    
                    _render_import_success_card(result)
                    st.info("ℹ️ RR intervals estimated from heart rate data. For beat-to-beat accuracy, use chest strap data.")
                    
                    return result
                    
                except Exception as exc:
                    st.error(f"❌ Failed to parse Garmin CSV: {exc}")
        
        elif export_type == "Bulk Export (ZIP)":
            garmin_zip = st.file_uploader(
                "Select Garmin export ZIP",
                type=["zip"],
                key="garmin_zip_uploader",
            )
            
            if garmin_zip is not None:
                st.info("🔄 Processing ZIP export... This may take a moment.")
                try:
                    import zipfile
                    
                    with tempfile.TemporaryDirectory() as tmpdir:
                        zip_path = Path(tmpdir) / "garmin_export.zip"
                        zip_path.write_bytes(garmin_zip.getvalue())
                        
                        with zipfile.ZipFile(zip_path, 'r') as zf:
                            # Look for HRV or wellness files
                            hrv_files = [f for f in zf.namelist() if "hrv" in f.lower() and f.endswith(".json")]
                            wellness_files = [f for f in zf.namelist() if "wellness" in f.lower() and f.endswith(".csv")]
                            
                            all_rr = []
                            
                            # Try HRV JSON files first
                            import json
                            for hrv_file in hrv_files[:10]:  # Limit processing
                                try:
                                    with zf.open(hrv_file) as f:
                                        data = json.load(f)
                                        if isinstance(data, list):
                                            for entry in data:
                                                if "hrvValues" in entry:
                                                    all_rr.extend(entry["hrvValues"])
                                except Exception:
                                    continue
                            
                            if all_rr:
                                rr_ms = np.array(all_rr, dtype=np.float64)
                                # Filter valid values
                                rr_ms = rr_ms[(rr_ms >= 200) & (rr_ms <= 3000)]
                                
                                if len(rr_ms) > 10:
                                    result = ImportedRRData(
                                        source_device="Garmin Vivosmart 5",
                                        filename=garmin_zip.name,
                                        rr_intervals_ms=rr_ms,
                                        metadata={"source": "HRV JSON files"},
                                    )
                                    
                                    _render_import_success_card(result)
                                    return result
                            
                            st.warning("No usable HRV data found in ZIP export")
                            
                except Exception as exc:
                    st.error(f"❌ Failed to process ZIP: {exc}")
        
        else:  # FIT File
            garmin_fit = st.file_uploader(
                "Select Garmin FIT file",
                type=["fit"],
                key="garmin_fit_uploader",
            )
            
            if garmin_fit is not None:
                st.info("⚠️ FIT file parsing requires additional dependencies. Consider exporting as CSV from Garmin Connect instead.")
                # TODO: Implement FIT file parsing with fitparse library
    
    return None


def render_actigraph_import_section() -> Optional[ImportedRRData]:
    """Render ActiGraph GT3X import interface.
    
    Returns:
        ImportedRRData if successful import, None otherwise.
    """
    with st.sidebar.expander("📊 ActiGraph GT3X Import", expanded=False):
        st.markdown("""
        <div style="
            background: linear-gradient(135deg, #6c757d15 0%, #49505715 100%);
            border-radius: 10px;
            padding: 0.75rem;
            margin-bottom: 0.75rem;
            border: 1px solid rgba(108, 117, 125, 0.3);
        ">
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 0.5rem;">
                <span style="font-size: 1.2rem;">📊</span>
                <span style="color: #6c757d; font-weight: 600; font-size: 0.9rem;">ActiLife Export</span>
            </div>
            <p style="margin: 0; color: #888; font-size: 0.75rem;">
                Import accelerometer data from ActiGraph GT3X/GT3X+ devices. Supports .gt3x, 
                .agd (processed), and .csv exports.
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        actigraph_file = st.file_uploader(
            "Select ActiGraph file",
            type=["gt3x", "agd", "csv"],
            key="actigraph_import_uploader",
        )
        
        if actigraph_file is not None:
            st.info("📈 ActiGraph data imported. See main device import section for processing.")
            st.session_state["pending_actigraph_file"] = actigraph_file
    
    return None


def render_somfit_import_section() -> Optional[ImportedRRData]:
    """Render Somfit Pro import interface.
    
    Returns:
        ImportedRRData if successful import, None otherwise.
    """
    with st.sidebar.expander("😴 Somfit Pro Import", expanded=False):
        st.markdown("""
        <div style="
            background: linear-gradient(135deg, #9b59b615 0%, #8e44ad15 100%);
            border-radius: 10px;
            padding: 0.75rem;
            margin-bottom: 0.75rem;
            border: 1px solid rgba(155, 89, 182, 0.3);
        ">
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 0.5rem;">
                <span style="font-size: 1.2rem;">😴</span>
                <span style="color: #9b59b6; font-weight: 600; font-size: 0.9rem;">Compumedics Somfit</span>
            </div>
            <p style="margin: 0; color: #888; font-size: 0.75rem;">
                Import home sleep study data from Somfit/Somfit Pro devices. Supports EDF 
                and CSV exports from Profusion Nexus360.
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        somfit_file = st.file_uploader(
            "Select Somfit data file",
            type=["edf", "csv"],
            key="somfit_import_uploader",
        )
        
        somfit_annotations = st.file_uploader(
            "Optional: Scoring annotations",
            type=["xml"],
            key="somfit_annotations_uploader",
        )
        
        if somfit_file is not None:
            st.info("😴 Somfit data imported. See main device import section for processing.")
            st.session_state["pending_somfit_file"] = somfit_file
            if somfit_annotations:
                st.session_state["pending_somfit_annotations"] = somfit_annotations
    
    return None


def render_all_device_imports() -> Dict[str, ImportedRRData]:
    """Render all device import sections and collect results.
    
    Returns:
        Dictionary mapping device names to imported data.
    """
    results: Dict[str, ImportedRRData] = {}
    
    # Render device import header
    st.sidebar.markdown("""
    <div style="
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border-radius: 12px;
        padding: 1rem;
        margin: 1rem 0;
        border: 1px solid rgba(102, 126, 234, 0.2);
    ">
        <h3 style="margin: 0 0 0.5rem 0; color: #667eea; font-size: 1rem;">
            📱 Device Data Import
        </h3>
        <p style="margin: 0; color: #888; font-size: 0.8rem;">
            Import physiological data from your wearable devices
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Polar H10/H9
    polar_result = render_polar_import_section()
    if polar_result:
        results["polar"] = polar_result
    
    # Garmin Vivosmart 5
    garmin_result = render_garmin_import_section()
    if garmin_result:
        results["garmin"] = garmin_result
    
    # ActiGraph (placeholder - handled by main import section)
    render_actigraph_import_section()
    
    # Somfit Pro (placeholder - handled by main import section)
    render_somfit_import_section()
    
    return results


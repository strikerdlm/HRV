"""
Professional welcome header for HRV Analysis Suite.

Displays laboratory branding, version info, and contributor credits.
Uses Streamlit native components with minimal HTML for reliable rendering.

Author: Dr. Diego L. Malpica, MD - Aerospace Medicine Specialist
"""

from __future__ import annotations

import streamlit as st

# Application metadata
APP_VERSION = "1.6.3"
GITHUB_REPO = "https://github.com/strikerdlm/HRV"


def render_welcome_header() -> None:
    """Render the professional welcome header with laboratory branding."""
    
    # Inject CSS for custom styling
    st.markdown("""
    <style>
    .welcome-header-container {
        background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
        border-radius: 20px;
        padding: 2rem;
        margin-bottom: 1.5rem;
        border: 1px solid rgba(102, 126, 234, 0.3);
        box-shadow: 0 10px 40px rgba(0, 0, 0, 0.4);
    }
    .welcome-title {
        text-align: center;
        font-size: 2.4rem;
        font-weight: 800;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 40%, #f093fb 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin: 0.5rem 0;
    }
    .welcome-subtitle {
        text-align: center;
        color: #a0aec0;
        font-size: 1.1rem;
        margin-bottom: 0.5rem;
    }
    .welcome-version {
        display: inline-block;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 6px 16px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
    }
    .welcome-github {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: rgba(255,255,255,0.1);
        color: #fff !important;
        padding: 6px 14px;
        border-radius: 8px;
        text-decoration: none;
        font-size: 0.85rem;
        border: 1px solid rgba(255,255,255,0.2);
        margin-left: 10px;
    }
    .welcome-github:hover {
        background: rgba(255,255,255,0.2);
    }
    .contrib-card {
        background: rgba(102, 126, 234, 0.1);
        border: 1px solid rgba(102, 126, 234, 0.2);
        padding: 8px 12px;
        border-radius: 12px;
        text-align: center;
    }
    .contrib-title {
        color: #667eea;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .contrib-author {
        color: #888;
        font-size: 0.75rem;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Build the welcome container HTML
    welcome_html = f'''
    <div class="welcome-header-container">
        <div style="text-align: center; margin-bottom: 0.5rem;">
            <span style="font-size: 3rem;">🧬</span>
        </div>
        <div class="welcome-title">Physiological Laboratory</div>
        <div class="welcome-subtitle">
            <strong>Dr. Diego L. Malpica, MD</strong> — Aerospace Medicine Specialist
        </div>
        <div style="text-align: center; color: #888; font-size: 0.95rem; margin-bottom: 1rem;">
            Contributing to <span style="color: #667eea; font-weight: 600;">AsterPhysiology</span> Research Initiative
        </div>
        <div style="text-align: center; margin: 1rem 0;">
            <span class="welcome-version">v{APP_VERSION}</span>
            <a href="{GITHUB_REPO}" target="_blank" class="welcome-github">
                <svg width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
                    <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.012 8.012 0 0 0 16 8c0-4.42-3.58-8-8-8z"/>
                </svg>
                GitHub
            </a>
        </div>
        <hr style="margin: 1rem 0; border-color: rgba(102, 126, 234, 0.2);">
        <div style="text-align: center; color: #888; font-size: 0.85rem; margin-bottom: 0.75rem;">
            <strong>🔬 Contributing Modules</strong>
        </div>
        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.5rem;">
            <div class="contrib-card">
                <div style="font-size: 1.2rem;">🌙</div>
                <div class="contrib-title">Circadian</div>
                <div class="contrib-author">Arcascope</div>
            </div>
            <div class="contrib-card">
                <div style="font-size: 1.2rem;">😴</div>
                <div class="contrib-title">SAFTE</div>
                <div class="contrib-author">IBR/USAF</div>
            </div>
            <div class="contrib-card">
                <div style="font-size: 1.2rem;">🫀</div>
                <div class="contrib-title">HRV Core</div>
                <div class="contrib-author">Task Force 1996</div>
            </div>
            <div class="contrib-card">
                <div style="font-size: 1.2rem;">📊</div>
                <div class="contrib-title">ECharts</div>
                <div class="contrib-author">Apache</div>
            </div>
        </div>
    </div>
    '''
    
    # Render as single HTML block
    st.markdown(welcome_html, unsafe_allow_html=True)


def render_device_import_header() -> None:
    """Render device import section header in sidebar."""
    st.sidebar.markdown("""
    <div style="
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border-radius: 12px;
        padding: 1rem;
        margin-bottom: 1rem;
        border: 1px solid rgba(102, 126, 234, 0.2);
    ">
        <h3 style="margin: 0 0 0.5rem 0; color: #667eea; font-size: 1rem;">
            📱 Device Data Import
        </h3>
        <p style="margin: 0; color: #888; font-size: 0.8rem;">
            Import RR intervals and physiological data from your devices
        </p>
    </div>
    """, unsafe_allow_html=True)


def render_sidebar_branding() -> None:
    """Render compact branding in sidebar."""
    st.sidebar.markdown(
        f"""
        <div style="
            text-align: center;
            padding: 0.75rem;
            margin-bottom: 1rem;
            border-bottom: 1px solid rgba(102, 126, 234, 0.2);
        ">
            <div style="font-size: 1.5rem; margin-bottom: 0.25rem;">🧬</div>
            <div style="
                font-size: 0.9rem;
                font-weight: 700;
                color: #667eea;
            ">Physiological Lab</div>
            <div style="font-size: 0.7rem; color: #888;">v{APP_VERSION}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


def render_quick_access_grid(has_data: bool = False) -> None:
    """
    Render quick access grid for navigating to different analysis modules.
    
    Args:
        has_data: Whether physiological data is loaded
    """
    st.markdown("### 🔬 Analysis Modules")
    
    if not has_data:
        st.markdown(
            """
            <div style="
                background: linear-gradient(135deg, #1a472a 0%, #2d5a3f 100%);
                border: 1px solid rgba(46, 204, 113, 0.3);
                border-radius: 12px;
                padding: 1rem;
                margin-bottom: 1rem;
            ">
                <div style="color: #2ecc71; font-weight: 600; margin-bottom: 0.5rem;">
                    ✨ Explore Without Data
                </div>
                <div style="color: #90EE90; font-size: 0.9rem;">
                    Modules marked with ✓ are fully functional without uploading HRV data. 
                    Click any tab above to explore!
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    
    st.markdown("Select a tab above to explore each module. Modules marked with ✓ are available without data.")
    
    # Module definitions with categories
    modules = [
        # Data-independent modules (highlighted)
        {"icon": "🌍", "name": "Space Weather", "desc": "Solar activity, CME predictions & Polar H10 timing", "no_data": True, "color": "#9b59b6", "highlight": True},
        {"icon": "☀️", "name": "Circadian", "desc": "Circadian rhythm simulation & jet lag", "no_data": True, "color": "#fd9644", "highlight": True},
        {"icon": "😴", "name": "SAFTE Model", "desc": "Fatigue & cognitive performance", "no_data": True, "color": "#3498db", "highlight": True},
        {"icon": "🫀", "name": "Biofeedback", "desc": "Real-time coherence training demo", "no_data": True, "color": "#e74c3c", "highlight": True},
        # Data-dependent modules
        {"icon": "📊", "name": "Overview", "desc": "Summary statistics and key HRV metrics", "no_data": False, "color": "#667eea", "highlight": False},
        {"icon": "📈", "name": "Time Series", "desc": "RR interval time-domain analysis", "no_data": False, "color": "#4ecdc4", "highlight": False},
        {"icon": "🌊", "name": "Frequency", "desc": "Power spectral density (LF, HF, VLF)", "no_data": False, "color": "#ff6b6b", "highlight": False},
        {"icon": "🔀", "name": "Nonlinear", "desc": "Poincaré, entropy, DFA analysis", "no_data": False, "color": "#f7b731", "highlight": False},
        {"icon": "📉", "name": "Spectrogram", "desc": "Time-frequency analysis", "no_data": False, "color": "#a55eea", "highlight": False},
        {"icon": "🪟", "name": "Windowed", "desc": "Segmented HRV analysis", "no_data": False, "color": "#26de81", "highlight": False},
        {"icon": "📋", "name": "Population Norms", "desc": "Compare against reference values", "no_data": False, "color": "#1abc9c", "highlight": False},
        {"icon": "📄", "name": "Export", "desc": "Generate reports & export data", "no_data": False, "color": "#95a5a6", "highlight": False},
    ]
    
    # Render in 4-column grid
    cols = st.columns(4)
    for i, mod in enumerate(modules):
        with cols[i % 4]:
            # Determine availability
            available = mod["no_data"] or has_data
            status = "✓" if available else "○"
            status_color = "#90EE90" if available else "#666"
            opacity = "1" if available else "0.6"
            
            # Extra highlighting for available modules when no data
            border_glow = ""
            if mod.get("highlight") and not has_data:
                border_glow = f"box-shadow: 0 0 10px {mod['color']}55;"
            
            st.markdown(
                f"""
                <div style="
                    background: linear-gradient(135deg, {mod['color']}22 0%, {mod['color']}11 100%);
                    border: 1px solid {mod['color']}44;
                    border-radius: 10px;
                    padding: 0.75rem;
                    margin-bottom: 0.5rem;
                    min-height: 95px;
                    opacity: {opacity};
                    {border_glow}
                ">
                    <div style="font-size: 1.4rem; margin-bottom: 0.2rem;">{mod['icon']}</div>
                    <div style="color: {mod['color']}; font-weight: 600; font-size: 0.85rem;">
                        {mod['name']} 
                        <span style="color: {status_color}; font-size: 0.7rem;">{status}</span>
                    </div>
                    <div style="color: #888; font-size: 0.7rem; line-height: 1.3;">{mod['desc']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_data_status_panel(
    has_rr_data: bool = False,
    rr_count: int = 0,
    has_profile: bool = False,
    has_space_weather: bool = False,
) -> None:
    """
    Render a data status panel showing what data is loaded.
    
    Args:
        has_rr_data: Whether RR interval data is loaded
        rr_count: Number of RR intervals
        has_profile: Whether user profile is set
        has_space_weather: Whether space weather data is fetched
    """
    if has_rr_data or has_profile or has_space_weather:
        # Data loaded state
        items = []
        if has_rr_data:
            items.append(f"🫀 RR Intervals: {rr_count:,}")
        if has_profile:
            items.append("👤 Profile Set")
        if has_space_weather:
            items.append("☀️ Space Weather")
        
        st.markdown(
            f"""
            <div style="
                background: linear-gradient(135deg, #1a472a 0%, #2d5a3f 100%);
                border: 1px solid rgba(46, 204, 113, 0.3);
                border-radius: 12px;
                padding: 1rem;
                margin: 1rem 0;
            ">
                <div style="color: #2ecc71; font-weight: 600; margin-bottom: 0.5rem;">
                    ✓ Data Loaded
                </div>
                <div style="color: #90EE90; font-size: 0.9rem;">
                    {' | '.join(items)}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        # No data state
        st.markdown(
            """
            <div style="
                background: linear-gradient(135deg, #4a3728 0%, #5a4838 100%);
                border: 1px solid rgba(243, 156, 18, 0.3);
                border-radius: 12px;
                padding: 1rem;
                margin: 1rem 0;
            ">
                <div style="color: #f39c12; font-weight: 600; margin-bottom: 0.5rem;">
                    ⚠️ No Physiological Data Loaded
                </div>
                <div style="color: #FFB347; font-size: 0.9rem;">
                    Use the sidebar to import RR interval data from your device (Polar, Garmin, ActiGraph) 
                    or upload a text file. Some modules like Circadian and Space Weather work without data.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_getting_started_guide() -> None:
    """Render a getting started guide for new users."""
    with st.expander("🚀 Getting Started Guide", expanded=True):
        st.markdown(
            """
            ### Welcome to the Physiological Laboratory! 👋
            
            This platform provides comprehensive tools for **Heart Rate Variability (HRV)** analysis, 
            **circadian rhythm** modeling, **fatigue prediction**, and **space weather correlations**.
            
            ---
            
            #### 🎯 Start Exploring NOW (No Data Required!)
            
            **Click these tabs above** to see real space weather data and simulations:
            
            | Tab | What You Can Do |
            |-----|-----------------|
            | 🌍 **Space Weather** | Fetch live NASA/NOAA data, see CME arrival predictions, get Polar H10 timing |
            | ☀️ **Circadian** | Simulate your circadian rhythm with different light schedules |
            | 😴 **SAFTE/Fatigue** | Model how sleep debt affects cognitive performance |
            | 🫀 **Biofeedback** | Try the paced breathing demo |
            
            ---
            
            #### 📱 To Analyze Your Own HRV Data:
            
            1. **Import Data** using the sidebar:
               - **Polar H10/H9**: Export from Polar Sensor Logger
               - **Garmin**: Wellness data from Garmin Connect
               - **Generic**: Any text file with RR intervals (one per line, ms)
            
            2. **Set Your Profile** (optional) for personalized interpretation
            
            3. **Explore All Analysis Tabs** - they'll populate with your data
            
            4. **Export Results** as publication-ready reports
            
            ---
            
            #### 💡 Pro Tips:
            - Record 5-minute sessions, seated, at the same time daily
            - Uncheck "Minimal mode" in sidebar for full analysis
            - Enable "GPT-5.1 Interpretation" for doctoral-level insights
            
            📚 [GitHub Repository](https://github.com/strikerdlm/HRV) • 
            📖 [Documentation](https://github.com/strikerdlm/HRV/blob/main/docs/Manual.md)
            """
        )

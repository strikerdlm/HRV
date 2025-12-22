"""
Professional welcome header for Mission Control - Flight Surgeon.

Displays laboratory branding, version info, and contributor credits.
Uses Streamlit native components with minimal HTML for reliable rendering.

Author: Dr. Diego L. Malpica, MD - Aerospace Medicine Specialist
"""

from __future__ import annotations

import streamlit as st

from version_info import get_app_release_date, get_app_version, get_git_metadata

# Application metadata
APP_VERSION = get_app_version()
APP_RELEASE_DATE = get_app_release_date()
GIT_METADATA = get_git_metadata()
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
        display: inline-flex;
        gap: 4px;
        align-items: center;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 6px 16px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
    }
    .welcome-chip {
        display: inline-block;
        padding: 5px 14px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 500;
    }
    .welcome-chip-muted {
        background: rgba(255,255,255,0.08);
        color: #d1d5db;
    }
    .welcome-chip-outline {
        border: 1px solid rgba(255,255,255,0.2);
        color: #f3f4f6;
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
        <div class="welcome-title">Mission Control - Flight Surgeon</div>
        <div class="welcome-subtitle">
            <strong>Dr. Diego L. Malpica, MD</strong> — Aerospace Medicine Specialist
        </div>
        <div style="text-align: center; color: #888; font-size: 0.95rem; margin-bottom: 1rem;">
            Contributing to <span style="color: #667eea; font-weight: 600;">AsterPhysiology</span> Research Initiative
        </div>
        <div style="text-align: center; margin: 1rem 0;">
            <span class="welcome-version">v{APP_VERSION}</span>
        </div>
        <div style="text-align: center; margin-bottom: 1rem;">
            <span class="welcome-chip welcome-chip-muted">{APP_RELEASE_DATE}</span>
            <span class="welcome-chip welcome-chip-outline">
                {GIT_METADATA.branch} @ {GIT_METADATA.short_hash}{' • dirty' if GIT_METADATA.is_dirty else ''}
            </span>
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
            ">Mission Control Lab</div>
            <div style="font-size: 0.7rem; color: #888;">v{APP_VERSION}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


def render_quick_access_grid(has_data: bool = False) -> None:
    """
    Render quick access grid for navigating to different analysis modules.
    
    Uses glassmorphism design with frosted glass effects and smooth hover animations.
    
    Args:
        has_data: Whether physiological data is loaded
    """
    # Inject glassmorphism CSS styles
    st.markdown("""
    <style>
    @keyframes float {
        0%, 100% { transform: translateY(0px); }
        50% { transform: translateY(-5px); }
    }
    @keyframes glow {
        0%, 100% { box-shadow: 0 0 5px var(--glow-color), 0 8px 32px rgba(0,0,0,0.3); }
        50% { box-shadow: 0 0 20px var(--glow-color), 0 8px 32px rgba(0,0,0,0.4); }
    }
    @keyframes iconPulse {
        0%, 100% { transform: scale(1); }
        50% { transform: scale(1.1); }
    }
    .glass-card {
        background: linear-gradient(135deg, rgba(255,255,255,0.1) 0%, rgba(255,255,255,0.05) 100%);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border: 1px solid rgba(255,255,255,0.18);
        border-radius: 16px;
        padding: 1.2rem;
        margin-bottom: 0.8rem;
        min-height: 130px;
        cursor: pointer;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        position: relative;
        overflow: hidden;
    }
    .glass-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.1), transparent);
        transition: left 0.5s;
    }
    .glass-card:hover::before {
        left: 100%;
    }
    .glass-card:hover {
        transform: translateY(-8px) scale(1.02);
        border-color: rgba(255,255,255,0.3);
    }
    .glass-card.available:hover {
        animation: glow 2s ease-in-out infinite;
    }
    .glass-card.unavailable {
        opacity: 0.5;
        cursor: not-allowed;
    }
    .glass-card .card-icon {
        font-size: 2.5rem;
        margin-bottom: 0.5rem;
        display: block;
        transition: transform 0.3s ease;
    }
    .glass-card:hover .card-icon {
        animation: iconPulse 0.6s ease-in-out;
    }
    .glass-card .card-title {
        font-weight: 700;
        font-size: 1rem;
        margin-bottom: 0.4rem;
        letter-spacing: 0.5px;
    }
    .glass-card .card-desc {
        font-size: 0.75rem;
        line-height: 1.4;
        opacity: 0.85;
    }
    .glass-card .card-status {
        position: absolute;
        top: 0.8rem;
        right: 0.8rem;
        font-size: 0.65rem;
        padding: 0.2rem 0.5rem;
        border-radius: 20px;
        font-weight: 600;
    }
    .glass-card .card-tab {
        font-size: 0.65rem;
        opacity: 0.6;
        margin-top: 0.5rem;
        font-style: italic;
    }
    .module-section-title {
        background: linear-gradient(90deg, #667eea, #764ba2, #f093fb);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        font-size: 1.5rem;
        font-weight: 800;
        margin-bottom: 1rem;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="module-section-title">🔬 Analysis Modules</div>', unsafe_allow_html=True)
    
    if not has_data:
        st.markdown(
            """
            <div style="
                background: linear-gradient(135deg, rgba(46, 204, 113, 0.15) 0%, rgba(39, 174, 96, 0.1) 100%);
                backdrop-filter: blur(10px);
                border: 1px solid rgba(46, 204, 113, 0.3);
                border-radius: 16px;
                padding: 1.2rem;
                margin-bottom: 1.5rem;
            ">
                <div style="color: #2ecc71; font-weight: 700; margin-bottom: 0.5rem; font-size: 1.1rem;">
                    ✨ Explore Without Data
                </div>
                <div style="color: rgba(144, 238, 144, 0.9); font-size: 0.9rem; line-height: 1.5;">
                    Glowing cards below are <strong>fully functional</strong> without uploading HRV data!<br/>
                    Click any card to see which tab to navigate to.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    
    # Module definitions with gradient colors
    modules = [
        # Row 1: Data-independent (highlighted)
        {"icon": "👤", "name": "User Profile", "tab": "👤 User Profile", "desc": "Profiles, clinical assessments & Garmin sync", "no_data": True, "gradient": "linear-gradient(135deg, #667eea 0%, #764ba2 100%)", "glow": "#667eea"},
        {"icon": "🌍", "name": "Space Weather", "tab": "🌍 Space Weather", "desc": "Solar activity & geomagnetic correlations", "no_data": True, "gradient": "linear-gradient(135deg, #9b59b6 0%, #8e44ad 100%)", "glow": "#9b59b6"},
        {"icon": "🛰️", "name": "NOAA Space", "tab": "🛰️ NOAA Space", "desc": "NOAA feeds, Kp index & solar wind", "no_data": True, "gradient": "linear-gradient(135deg, #00d2d3 0%, #00a8a8 100%)", "glow": "#00d2d3"},
        {"icon": "☀️", "name": "Circadian", "tab": "☀️ Circadian", "desc": "Circadian simulation & jet lag planning", "no_data": True, "gradient": "linear-gradient(135deg, #f39c12 0%, #e67e22 100%)", "glow": "#f39c12"},
        # Row 2: Data-independent
        {"icon": "😴", "name": "SAFTE/Fatigue", "tab": "😴 SAFTE/Fatigue", "desc": "Fatigue forecasting & FRMS dashboard", "no_data": True, "gradient": "linear-gradient(135deg, #3498db 0%, #2980b9 100%)", "glow": "#3498db"},
        {"icon": "🫀", "name": "Biofeedback", "tab": "🫀 Biofeedback", "desc": "Coherence training & breathing exercises", "no_data": True, "gradient": "linear-gradient(135deg, #e74c3c 0%, #c0392b 100%)", "glow": "#e74c3c"},
        {"icon": "📚", "name": "References", "tab": "📚 References", "desc": "Scientific citations & documentation", "no_data": True, "gradient": "linear-gradient(135deg, #1abc9c 0%, #16a085 100%)", "glow": "#1abc9c"},
        {"icon": "ℹ️", "name": "About", "tab": "ℹ️ About", "desc": "Author info, changelog & manual", "no_data": True, "gradient": "linear-gradient(135deg, #7f8c8d 0%, #636e72 100%)", "glow": "#95a5a6"},
        # Row 3: Data-dependent
        {"icon": "📊", "name": "Overview", "tab": "Overview", "desc": "Summary statistics & key metrics", "no_data": False, "gradient": "linear-gradient(135deg, #667eea 0%, #764ba2 100%)", "glow": "#667eea"},
        {"icon": "📈", "name": "Time Series", "tab": "Time Series", "desc": "RR interval time-domain analysis", "no_data": False, "gradient": "linear-gradient(135deg, #4ecdc4 0%, #44a08d 100%)", "glow": "#4ecdc4"},
        {"icon": "🌊", "name": "Frequency", "tab": "Frequency", "desc": "Power spectral density (LF/HF/VLF)", "no_data": False, "gradient": "linear-gradient(135deg, #ff6b6b 0%, #ee5a5a 100%)", "glow": "#ff6b6b"},
        {"icon": "🔀", "name": "Nonlinear", "tab": "Nonlinear", "desc": "Poincaré, entropy & DFA", "no_data": False, "gradient": "linear-gradient(135deg, #f7b731 0%, #eb9b04 100%)", "glow": "#f7b731"},
        # Row 4: Data-dependent
        {"icon": "📉", "name": "Spectrogram", "tab": "Spectrogram", "desc": "Time-frequency wavelet analysis", "no_data": False, "gradient": "linear-gradient(135deg, #a55eea 0%, #8e44ad 100%)", "glow": "#a55eea"},
        {"icon": "🪟", "name": "Windowed", "tab": "Windowed", "desc": "Segmented HRV with baselines", "no_data": False, "gradient": "linear-gradient(135deg, #26de81 0%, #20bf6b 100%)", "glow": "#26de81"},
        {"icon": "📋", "name": "Norms", "tab": "📊 Population Norms", "desc": "Compare vs reference populations", "no_data": False, "gradient": "linear-gradient(135deg, #17a2b8 0%, #138496 100%)", "glow": "#17a2b8"},
        {"icon": "📄", "name": "Export", "tab": "📄 Export", "desc": "Download data & reports", "no_data": False, "gradient": "linear-gradient(135deg, #6c757d 0%, #5a6268 100%)", "glow": "#6c757d"},
    ]
    
    # Build HTML for all cards
    cards_html = '<div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem;">'
    
    for i, mod in enumerate(modules):
        available = mod["no_data"] or has_data
        availability_class = "available" if available else "unavailable"
        status_text = "✓ Ready" if available else "○ Needs Data"
        status_bg = "rgba(46, 204, 113, 0.3)" if available else "rgba(127, 140, 141, 0.3)"
        status_color = "#2ecc71" if available else "#95a5a6"
        
        # Glow effect for available cards
        glow_style = f"--glow-color: {mod['glow']};" if available else ""
        
        cards_html += f'''
        <a class="glass-card {availability_class}"
           style="{glow_style}"
           href="#analysis-modules"
           title="Tab: {mod['tab']}">
            <span class="card-status" style="background: {status_bg}; color: {status_color};">{status_text}</span>
            <span class="card-icon">{mod["icon"]}</span>
            <div class="card-title" style="background: {mod["gradient"]}; -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;">
                {mod["name"]}
            </div>
            <div class="card-desc" style="color: rgba(255,255,255,0.7);">{mod["desc"]}</div>
            <div class="card-tab">Tab: {mod["tab"]}</div>
        </a>
        '''
    
    cards_html += '</div>'
    
    st.markdown(cards_html, unsafe_allow_html=True)
    
    # Add a subtle helper text
    st.markdown(
        '<div style="text-align: center; color: rgba(255,255,255,0.5); font-size: 0.8rem; margin-top: 1rem;">'
        '💡 Click any card to see which tab to navigate to • Glowing cards work without data'
        '</div>',
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
                    ⚠️ No Mission Control Data Loaded
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
            ### Welcome to Mission Control - Flight Surgeon! 👋
            
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
            - Enable "GPT-5.2 Interpretation" for doctoral-level insights
            
            📚 [GitHub Repository](https://github.com/strikerdlm/HRV) • 
            📖 [Documentation](https://github.com/strikerdlm/HRV/blob/main/docs/Manual.md)
            """
        )

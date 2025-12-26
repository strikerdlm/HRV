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
        /* Custom palette (Flight Surgeon / Overview boxes only) */
        background: linear-gradient(135deg, #F2F1EF 0%, #D8CFD0 100%);
        border-radius: 20px;
        padding: 2rem;
        margin-bottom: 1.5rem;
        border: 1px solid rgba(177, 166, 164, 0.7);
        box-shadow: 0 10px 40px rgba(65, 63, 61, 0.14);
    }
    .welcome-title {
        text-align: center;
        font-size: 2.4rem;
        font-weight: 800;
        background: linear-gradient(135deg, #697184 0%, #413F3D 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin: 0.5rem 0;
    }
    .welcome-subtitle {
        text-align: center;
        color: rgba(65, 63, 61, 0.88);
        font-size: 1.1rem;
        margin-bottom: 0.5rem;
    }
    .welcome-version {
        display: inline-flex;
        gap: 4px;
        align-items: center;
        background: #697184;
        color: #F2F1EF;
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
        background: rgba(216, 207, 208, 0.65);
        color: #413F3D;
    }
    .welcome-chip-outline {
        border: 1px solid rgba(177, 166, 164, 0.85);
        color: #413F3D;
    }
    .welcome-github {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: rgba(216, 207, 208, 0.65);
        color: #413F3D !important;
        padding: 6px 14px;
        border-radius: 8px;
        text-decoration: none;
        font-size: 0.85rem;
        border: 1px solid rgba(177, 166, 164, 0.85);
        margin-left: 10px;
    }
    .welcome-github:hover {
        background: rgba(216, 207, 208, 0.85);
    }
    .contrib-card {
        background: rgba(242, 241, 239, 0.85);
        border: 1px solid rgba(177, 166, 164, 0.7);
        padding: 8px 12px;
        border-radius: 12px;
        text-align: center;
    }
    .contrib-title {
        color: #413F3D;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .contrib-author {
        color: rgba(105, 113, 132, 0.92);
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
        <div style="text-align: center; color: rgba(65, 63, 61, 0.78); font-size: 0.95rem; margin-bottom: 1rem;">
            Contributing to <span style="color: #697184; font-weight: 700;">AsterPhysiology</span> Research Initiative
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
        <hr style="margin: 1rem 0; border-color: rgba(177, 166, 164, 0.65);">
        <div style="text-align: center; color: rgba(65, 63, 61, 0.78); font-size: 0.85rem; margin-bottom: 0.75rem;">
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
        background: linear-gradient(135deg, #F2F1EF 0%, #D8CFD0 100%);
        border-radius: 12px;
        padding: 1rem;
        margin-bottom: 1rem;
        border: 1px solid rgba(177, 166, 164, 0.75);
    ">
        <h3 style="margin: 0 0 0.5rem 0; color: #413F3D; font-size: 1rem;">
            📱 Device Data Import
        </h3>
        <p style="margin: 0; color: #697184; font-size: 0.8rem;">
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
            border-bottom: 1px solid rgba(177, 166, 164, 0.65);
        ">
            <div style="font-size: 1.5rem; margin-bottom: 0.25rem;">🧬</div>
            <div style="
                font-size: 0.9rem;
                font-weight: 700;
                color: #413F3D;
            ">Mission Control Lab</div>
            <div style="font-size: 0.7rem; color: #697184;">v{APP_VERSION}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


def render_quick_access_grid(has_data: bool = False) -> None:
    """
    Render quick access grid for navigating to different analysis modules.
    
    Styled to match the main welcome header container with deep purple gradients.
    Cards show tab names - users click the tab bar above to navigate.
    
    Args:
        has_data: Whether physiological data is loaded
    """
    # Module definitions organized by category: (icon, name, tab_name, description, color, highlight_no_data)
    # highlight_no_data=True means this module should glow when user has no data loaded
    modules_available = [
        ("👤", "User Profile", "👤 User Profile", "Profiles & Garmin sync", "#667eea", False),
        ("🌍", "Space Weather", "🌍 Space Weather", "Solar correlations", "#9b59b6", True),
        ("🛰️", "NOAA Space", "🛰️ NOAA Space", "Kp index & solar wind", "#00d2d3", True),
        ("☀️", "Circadian", "☀️ Circadian", "Jet lag planning", "#f39c12", True),
        ("😴", "SAFTE/Fatigue", "😴 SAFTE/Fatigue", "Fatigue forecasting", "#3498db", True),
        ("🫀", "Biofeedback", "🫀 Biofeedback", "Coherence training", "#e74c3c", True),
        ("📚", "References", "📚 References", "Scientific citations", "#1abc9c", False),
        ("ℹ️", "About", "ℹ️ About", "Changelog & manual", "#95a5a6", False),
    ]
    
    modules_data_required = [
        ("📊", "Overview", "Overview", "Summary statistics", "#667eea"),
        ("📈", "Time Series", "Time Series", "RR interval analysis", "#4ecdc4"),
        ("🌊", "Frequency", "Frequency", "PSD (LF/HF/VLF)", "#ff6b6b"),
        ("🔀", "Nonlinear", "Nonlinear", "Poincaré & entropy", "#f7b731"),
        ("📉", "Spectrogram", "Spectrogram", "Time-frequency", "#a55eea"),
        ("🪟", "Windowed", "Windowed", "Segmented HRV", "#26de81"),
        ("📋", "Norms", "📊 Population Norms", "Reference compare", "#17a2b8"),
        ("📄", "Export", "📄 Export", "Download reports", "#6c757d"),
    ]
    
    def _build_card(
        icon: str,
        name: str,
        tab: str,
        desc: str,
        color: str,
        available: bool,
        *,
        glow: bool = False,
    ) -> str:
        """Build HTML for a single module card.
        
        Args:
            icon: Emoji icon for the card
            name: Module name
            tab: Tab name to display
            desc: Short description
            color: Hex color for theming
            available: Whether the module is accessible
            glow: Whether to apply glow effect (for highlighting explorable modules)
        """
        # Use the app's neutral palette for these cards (custom HTML only).
        # This does not affect Streamlit's default theme.
        opacity = "1" if available else "0.55"
        accent = "#697184"
        base_border = "rgba(177, 166, 164, 0.75)"
        bg_color = (
            "linear-gradient(135deg, #F2F1EF 0%, #D8CFD0 100%)"
            if available
            else "linear-gradient(135deg, rgba(216, 207, 208, 0.75) 0%, rgba(177, 166, 164, 0.55) 100%)"
        )
        border_color = base_border
        status_text = "✓ Ready" if available else "Needs Data"
        status_color = accent if available else "rgba(105, 113, 132, 0.9)"
        
        # Apply glow effect for highlighted modules (draws attention when no data loaded)
        if glow:
            box_shadow = "0 0 18px rgba(105, 113, 132, 0.45), 0 0 36px rgba(105, 113, 132, 0.25)"
            border_width = "2px"
            status_text = "★ Explore Now"
            status_color = "#413F3D"
        else:
            box_shadow = "0 8px 18px rgba(65, 63, 61, 0.08)"
            border_width = "1px"
        
        return (
            f'<div style="background: {bg_color}; '
            f'border: {border_width} solid {border_color}; border-radius: 14px; '
            f'padding: 1rem 0.8rem; text-align: center; opacity: {opacity}; '
            f'position: relative; box-shadow: {box_shadow}; '
            f'transition: box-shadow 0.3s ease, transform 0.2s ease;">'
            # Status badge
            f'<div style="position: absolute; top: 6px; right: 8px; font-size: 0.55rem; '
            f'color: {status_color}; font-weight: 600;">{status_text}</div>'
            # Icon
            f'<div style="font-size: 1.8rem; margin-bottom: 0.4rem;">{icon}</div>'
            # Name
            f'<div style="color: #413F3D; font-weight: 800; font-size: 0.85rem; '
            f'margin-bottom: 0.25rem;">{name}</div>'
            # Description
            f'<div style="color: rgba(65, 63, 61, 0.72); font-size: 0.7rem; line-height: 1.3; '
            f'margin-bottom: 0.4rem;">{desc}</div>'
            # Tab indicator
            f'<div style="background: rgba(105, 113, 132, 0.14); border-radius: 8px; '
            f'border: 1px solid rgba(177, 166, 164, 0.55); '
            f'padding: 0.3rem 0.5rem; font-size: 0.6rem; color: rgba(65, 63, 61, 0.85); '
            f'display: inline-block;">↑ Tab: <b>{tab}</b></div>'
            f'</div>'
        )
    
    # Build available modules grid
    # Apply glow effect to highlighted modules when user has no data loaded
    available_cards = "".join(
        _build_card(
            icon, name, tab, desc, color, True,
            glow=(highlight and not has_data),
        )
        for icon, name, tab, desc, color, highlight in modules_available
    )
    
    # Build data-required modules grid
    data_cards = "".join(
        _build_card(icon, name, tab, desc, color, has_data)
        for icon, name, tab, desc, color in modules_data_required
    )
    
    # Status indicator for data section
    data_dot_color = "#697184" if has_data else "#B1A6A4"
    data_dot_char = "●" if has_data else "○"
    data_label = "HRV Data Loaded — All Features Active" if has_data else "Requires HRV Data — Import via Sidebar"
    
    # Build HTML without leading whitespace (prevents Markdown code block interpretation)
    html_parts = [
        '<div style="background: linear-gradient(135deg, #F2F1EF 0%, #D8CFD0 100%); ',
        'border-radius: 20px; padding: 1.5rem; margin-bottom: 1.5rem; ',
        'border: 1px solid rgba(177, 166, 164, 0.75); box-shadow: 0 10px 40px rgba(65, 63, 61, 0.14);">',
        # Header
        '<div style="text-align: center; margin-bottom: 0.8rem;">',
        '<span style="font-size: 1.8rem;">🔬</span>',
        '<div style="font-size: 1.3rem; font-weight: 800; ',
        'background: linear-gradient(135deg, #697184 0%, #413F3D 100%); ',
        '-webkit-background-clip: text; -webkit-text-fill-color: transparent; ',
        'background-clip: text; margin-top: 0.3rem;">Analysis Modules</div>',
        '<div style="color: rgba(65, 63, 61, 0.72); font-size: 0.75rem; margin-top: 0.4rem;">',
        '↑ Click the <b style="color: #413F3D;">tab bar above</b> to navigate to each module</div>',
        '</div>',
        # Ready to Explore section
        '<div style="margin-bottom: 1rem;">',
        '<div style="display: flex; align-items: center; gap: 0.5rem; ',
        'margin-bottom: 0.6rem; padding-left: 0.3rem;">',
        '<span style="color: #697184; font-size: 0.8rem;">●</span>',
        '<span style="color: #413F3D; font-size: 0.85rem; font-weight: 700;">Ready to Explore</span>',
        '<span style="color: rgba(65, 63, 61, 0.72); font-size: 0.7rem; margin-left: auto;">No data required</span>',
        '</div>',
        '<div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.7rem;">',
        available_cards,
        '</div></div>',
        # Divider
        '<hr style="margin: 1.2rem 0; border: none; border-top: 1px solid rgba(177, 166, 164, 0.65);">',
        # Requires HRV Data section
        '<div>',
        '<div style="display: flex; align-items: center; gap: 0.5rem; ',
        'margin-bottom: 0.6rem; padding-left: 0.3rem;">',
        f'<span style="color: {data_dot_color}; font-size: 0.8rem;">{data_dot_char}</span>',
        f'<span style="color: #413F3D; font-size: 0.85rem; font-weight: 700;">{data_label}</span>',
        '</div>',
        '<div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.7rem;">',
        data_cards,
        '</div></div>',
        # Footer
        '<div style="text-align: center; margin-top: 1.2rem; padding-top: 0.8rem; ',
        'border-top: 1px solid rgba(177, 166, 164, 0.5);">',
        '<div style="color: rgba(65, 63, 61, 0.76); font-size: 0.75rem;">',
        '📱 <b>Import Data:</b> Sidebar → Polar H10 / Garmin / Text file</div>',
        '</div>',
        '</div>',
    ]
    
    st.markdown("".join(html_parts), unsafe_allow_html=True)


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
                background: linear-gradient(135deg, #F2F1EF 0%, #D8CFD0 100%);
                border: 1px solid rgba(177, 166, 164, 0.75);
                border-left: 6px solid #697184;
                border-radius: 12px;
                padding: 1rem;
                margin: 1rem 0;
            ">
                <div style="color: #413F3D; font-weight: 800; margin-bottom: 0.5rem;">
                    ✓ Data Loaded (Flight Surgeon workspace)
                </div>
                <div style="color: #697184; font-size: 0.9rem; font-weight: 600;">
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
                background: linear-gradient(135deg, #F2F1EF 0%, #D8CFD0 100%);
                border: 1px solid rgba(177, 166, 164, 0.75);
                border-left: 6px solid #B1A6A4;
                border-radius: 12px;
                padding: 1rem;
                margin: 1rem 0;
            ">
                <div style="color: #413F3D; font-weight: 800; margin-bottom: 0.5rem;">
                    ⚠️ No Mission Control Data Loaded
                </div>
                <div style="color: #697184; font-size: 0.9rem;">
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

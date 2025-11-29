"""
Professional About Tab for HRV Analysis Suite.

Provides a comprehensive, visually appealing About section with:
- Author information and credentials
- Version and changelog display
- Manual/documentation viewer
- Technology stack information
- Citation guidelines

Author: Dr. Diego L. Malpica, MD - Aerospace Medicine Specialist
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Optional

import streamlit as st

# Application metadata
APP_VERSION = "1.6.1"
APP_NAME = "HRV Analysis Suite"
APP_RELEASE_DATE = "2025-11-29"
APP_AUTHOR = "Dr. Diego Leonel Malpica Hincapié, MD"
APP_AUTHOR_TITLE = "Aerospace Medicine Specialist"
APP_INSTITUTION = "National University of Colombia"
APP_GITHUB = "https://github.com/strikerdlm/HRV"
APP_ORCID = "0000-0002-2257-4940"
APP_LINKEDIN = "https://www.linkedin.com/in/diegolmalpica/"


def _load_file_content(filename: str) -> str:
    """Load content from a file in the project root or docs folder.
    
    Args:
        filename: Name of the file to load.
        
    Returns:
        File content as string, or error message if not found.
    """
    # Try multiple possible locations
    base_paths = [
        Path(__file__).parent.parent,  # Project root
        Path(__file__).parent.parent / "docs",  # docs folder
        Path.cwd(),  # Current working directory
        Path.cwd() / "docs",
    ]
    
    for base in base_paths:
        filepath = base / filename
        if filepath.exists():
            try:
                return filepath.read_text(encoding="utf-8")
            except Exception as e:
                return f"Error reading {filename}: {e}"
    
    return f"File '{filename}' not found."


def _render_version_badge() -> str:
    """Create a styled version badge HTML."""
    return f"""
    <div style="display: inline-flex; align-items: center; gap: 8px; margin-bottom: 1rem;">
        <span style="
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: 600;
            letter-spacing: 0.5px;
        ">v{APP_VERSION}</span>
        <span style="
            background: rgba(32, 201, 151, 0.15);
            color: #20c997;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 500;
        ">Released {APP_RELEASE_DATE}</span>
    </div>
    """


def _render_author_card() -> str:
    """Create a professional author information card."""
    return f"""
    <div style="
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        border-radius: 16px;
        padding: 2rem;
        margin: 1rem 0;
        box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
        border: 1px solid rgba(102, 126, 234, 0.2);
    ">
        <div style="display: flex; align-items: flex-start; gap: 1.5rem; flex-wrap: wrap;">
            <div style="
                width: 100px;
                height: 100px;
                border-radius: 50%;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 2.5rem;
                color: white;
                flex-shrink: 0;
            ">👨‍⚕️</div>
            <div style="flex: 1; min-width: 250px;">
                <h2 style="
                    margin: 0 0 0.5rem 0;
                    color: #fff;
                    font-size: 1.5rem;
                    font-weight: 700;
                ">{APP_AUTHOR}</h2>
                <p style="
                    margin: 0 0 0.5rem 0;
                    color: #a0aec0;
                    font-size: 1rem;
                ">{APP_AUTHOR_TITLE}</p>
                <p style="
                    margin: 0 0 1rem 0;
                    color: #718096;
                    font-size: 0.9rem;
                ">📍 {APP_INSTITUTION}</p>
                <div style="display: flex; gap: 0.75rem; flex-wrap: wrap;">
                    <a href="{APP_GITHUB}" target="_blank" style="
                        display: inline-flex;
                        align-items: center;
                        gap: 6px;
                        background: rgba(255,255,255,0.1);
                        color: #fff;
                        padding: 6px 14px;
                        border-radius: 8px;
                        text-decoration: none;
                        font-size: 0.85rem;
                        transition: background 0.2s;
                    ">
                        <svg width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
                            <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.012 8.012 0 0 0 16 8c0-4.42-3.58-8-8-8z"/>
                        </svg>
                        GitHub
                    </a>
                    <a href="{APP_LINKEDIN}" target="_blank" style="
                        display: inline-flex;
                        align-items: center;
                        gap: 6px;
                        background: rgba(10, 102, 194, 0.3);
                        color: #0a66c2;
                        padding: 6px 14px;
                        border-radius: 8px;
                        text-decoration: none;
                        font-size: 0.85rem;
                    ">
                        <svg width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
                            <path d="M0 1.146C0 .513.526 0 1.175 0h13.65C15.474 0 16 .513 16 1.146v13.708c0 .633-.526 1.146-1.175 1.146H1.175C.526 16 0 15.487 0 14.854V1.146zm4.943 12.248V6.169H2.542v7.225h2.401zm-1.2-8.212c.837 0 1.358-.554 1.358-1.248-.015-.709-.52-1.248-1.342-1.248-.822 0-1.359.54-1.359 1.248 0 .694.521 1.248 1.327 1.248h.016zm4.908 8.212V9.359c0-.216.016-.432.08-.586.173-.431.568-.878 1.232-.878.869 0 1.216.662 1.216 1.634v3.865h2.401V9.25c0-2.22-1.184-3.252-2.764-3.252-1.274 0-1.845.7-2.165 1.193v.025h-.016a5.54 5.54 0 0 1 .016-.025V6.169h-2.4c.03.678 0 7.225 0 7.225h2.4z"/>
                        </svg>
                        LinkedIn
                    </a>
                    <a href="https://orcid.org/{APP_ORCID}" target="_blank" style="
                        display: inline-flex;
                        align-items: center;
                        gap: 6px;
                        background: rgba(166, 206, 57, 0.2);
                        color: #a6ce39;
                        padding: 6px 14px;
                        border-radius: 8px;
                        text-decoration: none;
                        font-size: 0.85rem;
                    ">
                        <svg width="16" height="16" viewBox="0 0 256 256" fill="currentColor">
                            <path d="M128 0C57.3 0 0 57.3 0 128s57.3 128 128 128 128-57.3 128-128S198.7 0 128 0zM70.7 193.3h-25v-96h25v96zm-12.5-109c-8.3 0-15-6.7-15-15s6.7-15 15-15 15 6.7 15 15-6.7 15-15 15zm129.8 109h-25v-50.3c0-12.3-.2-28.3-17.2-28.3-17.3 0-20 13.5-20 27.5v51h-25v-96h24v13.2h.3c3.3-6.3 11.5-13 23.7-13 25.3 0 30 16.7 30 38.3v57.5h.2z"/>
                        </svg>
                        ORCID
                    </a>
                </div>
            </div>
        </div>
    </div>
    """


def _render_tech_stack() -> str:
    """Create a technology stack visualization."""
    technologies = [
        ("Python 3.11+", "#3776ab", "Core Language"),
        ("Streamlit", "#ff4b4b", "Web Framework"),
        ("Apache ECharts", "#e43961", "Visualizations"),
        ("NumPy/SciPy", "#4dabcf", "Scientific Computing"),
        ("PostgreSQL", "#336791", "Database"),
        ("Docker", "#2496ed", "Containerization"),
    ]
    
    tech_html = '<div style="display: flex; flex-wrap: wrap; gap: 10px; margin: 1rem 0;">'
    for name, color, desc in technologies:
        tech_html += f"""
        <div style="
            background: {color}15;
            border: 1px solid {color}40;
            border-radius: 10px;
            padding: 10px 16px;
            display: flex;
            flex-direction: column;
            align-items: center;
            min-width: 100px;
        ">
            <span style="font-weight: 600; color: {color}; font-size: 0.9rem;">{name}</span>
            <span style="font-size: 0.75rem; color: #888; margin-top: 2px;">{desc}</span>
        </div>
        """
    tech_html += '</div>'
    return tech_html


def _render_citation_box() -> str:
    """Create a citation guideline box."""
    return """
    <div style="
        background: rgba(102, 126, 234, 0.1);
        border-left: 4px solid #667eea;
        border-radius: 0 10px 10px 0;
        padding: 1rem 1.25rem;
        margin: 1rem 0;
    ">
        <h4 style="margin: 0 0 0.5rem 0; color: #667eea; font-size: 1rem;">📝 How to Cite</h4>
        <code style="
            display: block;
            background: rgba(0,0,0,0.2);
            padding: 0.75rem;
            border-radius: 6px;
            font-size: 0.8rem;
            color: #a0aec0;
            white-space: pre-wrap;
            word-break: break-word;
        ">Malpica, D. L. (2025). HRV Analysis Suite: A comprehensive platform for heart rate variability analysis and physiological monitoring (Version 1.5.0) [Computer software]. https://github.com/strikerdlm/HRV</code>
    </div>
    """


def _render_stats_cards(manual_lines: int, changelog_lines: int) -> str:
    """Create statistics cards for documentation."""
    return f"""
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 1rem; margin: 1rem 0;">
        <div style="
            background: linear-gradient(135deg, #667eea20, #764ba220);
            border-radius: 12px;
            padding: 1.25rem;
            text-align: center;
            border: 1px solid rgba(102, 126, 234, 0.2);
        ">
            <div style="font-size: 2rem; font-weight: 700; color: #667eea;">15+</div>
            <div style="font-size: 0.8rem; color: #888;">Analysis Tabs</div>
        </div>
        <div style="
            background: linear-gradient(135deg, #20c99720, #17a58920);
            border-radius: 12px;
            padding: 1.25rem;
            text-align: center;
            border: 1px solid rgba(32, 201, 151, 0.2);
        ">
            <div style="font-size: 2rem; font-weight: 700; color: #20c997;">50+</div>
            <div style="font-size: 0.8rem; color: #888;">HRV Metrics</div>
        </div>
        <div style="
            background: linear-gradient(135deg, #f093fb20, #f5576c20);
            border-radius: 12px;
            padding: 1.25rem;
            text-align: center;
            border: 1px solid rgba(240, 147, 251, 0.2);
        ">
            <div style="font-size: 2rem; font-weight: 700; color: #f093fb;">6</div>
            <div style="font-size: 0.8rem; color: #888;">Device Integrations</div>
        </div>
        <div style="
            background: linear-gradient(135deg, #4facfe20, #00f2fe20);
            border-radius: 12px;
            padding: 1.25rem;
            text-align: center;
            border: 1px solid rgba(79, 172, 254, 0.2);
        ">
            <div style="font-size: 2rem; font-weight: 700; color: #4facfe;">{manual_lines:,}</div>
            <div style="font-size: 0.8rem; color: #888;">Manual Lines</div>
        </div>
    </div>
    """


def render_about_tab() -> None:
    """Render the complete About tab with professional styling."""
    # Custom CSS for the about page
    st.markdown("""
    <style>
    .about-container {
        max-width: 900px;
        margin: 0 auto;
    }
    .section-header {
        display: flex;
        align-items: center;
        gap: 10px;
        margin: 2rem 0 1rem 0;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid rgba(102, 126, 234, 0.3);
    }
    .section-header h3 {
        margin: 0;
        color: #667eea;
    }
    .manual-content {
        background: rgba(0,0,0,0.2);
        border-radius: 12px;
        padding: 1.5rem;
        max-height: 600px;
        overflow-y: auto;
    }
    .changelog-content {
        background: rgba(0,0,0,0.2);
        border-radius: 12px;
        padding: 1.5rem;
        max-height: 500px;
        overflow-y: auto;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Header with app name and version
    st.markdown(f"""
    <div style="text-align: center; margin-bottom: 2rem;">
        <h1 style="
            font-size: 2.5rem;
            font-weight: 800;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f093fb 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin: 0 0 0.5rem 0;
        ">🫀 {APP_NAME}</h1>
        <p style="color: #888; font-size: 1rem; margin-bottom: 1rem;">
            Comprehensive Heart Rate Variability Analysis & Physiological Monitoring Platform
        </p>
        {_render_version_badge()}
    </div>
    """, unsafe_allow_html=True)
    
    # Author card
    st.markdown(_render_author_card(), unsafe_allow_html=True)
    
    # Load documentation files
    manual_content = _load_file_content("Manual.md")
    changelog_content = _load_file_content("CHANGELOG.md")
    
    manual_lines = len(manual_content.split('\n')) if "not found" not in manual_content.lower() else 0
    changelog_lines = len(changelog_content.split('\n')) if "not found" not in changelog_content.lower() else 0
    
    # Statistics cards
    st.markdown(_render_stats_cards(manual_lines, changelog_lines), unsafe_allow_html=True)
    
    # Tabbed content for Manual and Changelog
    doc_tab1, doc_tab2, doc_tab3 = st.tabs(["📖 User Manual", "📋 Changelog", "⚙️ Technical Info"])
    
    with doc_tab1:
        st.markdown("""
        <div class="section-header">
            <span style="font-size: 1.5rem;">📖</span>
            <h3>Complete User Manual</h3>
        </div>
        """, unsafe_allow_html=True)
        
        if "not found" not in manual_content.lower() and "Error" not in manual_content:
            with st.expander("📋 Table of Contents", expanded=False):
                # Extract TOC from manual
                toc_lines = []
                in_toc = False
                for line in manual_content.split('\n'):
                    if '## Table of Contents' in line:
                        in_toc = True
                        continue
                    if in_toc:
                        if line.startswith('##'):
                            break
                        if line.strip().startswith(('1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.')):
                            toc_lines.append(line)
                st.markdown('\n'.join(toc_lines))
            
            st.markdown(f'<div class="manual-content">', unsafe_allow_html=True)
            st.markdown(manual_content)
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("📄 Manual documentation is being loaded from `docs/Manual.md`")
            st.markdown(manual_content)
    
    with doc_tab2:
        st.markdown("""
        <div class="section-header">
            <span style="font-size: 1.5rem;">📋</span>
            <h3>Version History & Changelog</h3>
        </div>
        """, unsafe_allow_html=True)
        
        if "not found" not in changelog_content.lower() and "Error" not in changelog_content:
            st.markdown(f'<div class="changelog-content">', unsafe_allow_html=True)
            st.markdown(changelog_content)
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("📄 Changelog is being loaded from `CHANGELOG.md`")
            st.markdown(changelog_content)
    
    with doc_tab3:
        st.markdown("""
        <div class="section-header">
            <span style="font-size: 1.5rem;">⚙️</span>
            <h3>Technology Stack</h3>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown(_render_tech_stack(), unsafe_allow_html=True)
        
        # System information
        st.markdown("""
        <div class="section-header">
            <span style="font-size: 1.5rem;">💻</span>
            <h3>System Requirements</h3>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("""
            **Minimum Requirements:**
            - Python 3.10+
            - 4 GB RAM
            - 500 MB Storage
            - Modern web browser (Chrome 90+)
            """)
        with col2:
            st.markdown("""
            **Recommended:**
            - Python 3.11+
            - 8 GB RAM
            - 1 GB Storage
            - Chrome/Edge latest
            """)
        
        # Dependencies info
        st.markdown("""
        <div class="section-header">
            <span style="font-size: 1.5rem;">📦</span>
            <h3>Key Dependencies</h3>
        </div>
        """, unsafe_allow_html=True)
        
        deps_data = {
            "Package": ["streamlit", "numpy", "scipy", "pandas", "matplotlib", "psycopg2", "python-dotenv"],
            "Purpose": ["Web UI Framework", "Numerical Computing", "Scientific Algorithms", "Data Analysis", "Plotting Backend", "PostgreSQL Driver", "Environment Config"],
            "Category": ["Frontend", "Core", "Core", "Core", "Visualization", "Database", "Configuration"]
        }
        st.dataframe(deps_data, use_container_width=True, hide_index=True)
    
    # Citation section
    st.markdown(_render_citation_box(), unsafe_allow_html=True)
    
    # Footer
    st.markdown(f"""
    <div style="
        text-align: center;
        margin-top: 3rem;
        padding: 1.5rem;
        border-top: 1px solid rgba(255,255,255,0.1);
        color: #666;
        font-size: 0.85rem;
    ">
        <p style="margin: 0;">
            © {datetime.now().year} {APP_AUTHOR} • {APP_INSTITUTION}
        </p>
        <p style="margin: 0.5rem 0 0 0; color: #555;">
            Made with ❤️ for the aerospace medicine and HRV research community
        </p>
    </div>
    """, unsafe_allow_html=True)


def get_app_version() -> str:
    """Return the current application version."""
    return APP_VERSION


def get_app_metadata() -> dict:
    """Return application metadata as a dictionary."""
    return {
        "name": APP_NAME,
        "version": APP_VERSION,
        "release_date": APP_RELEASE_DATE,
        "author": APP_AUTHOR,
        "author_title": APP_AUTHOR_TITLE,
        "institution": APP_INSTITUTION,
        "github": APP_GITHUB,
        "orcid": APP_ORCID,
        "linkedin": APP_LINKEDIN,
    }


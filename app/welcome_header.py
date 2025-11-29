"""
Professional welcome header for HRV Analysis Suite.

Displays laboratory branding, version info, and contributor credits.

Author: Dr. Diego L. Malpica, MD - Aerospace Medicine Specialist
"""

from __future__ import annotations

import streamlit as st

# Application metadata
APP_VERSION = "1.5.0"
GITHUB_REPO = "https://github.com/strikerdlm/HRV"


def render_welcome_header() -> None:
    """Render the professional welcome header with laboratory branding."""
    
    st.markdown("""
    <style>
    .welcome-container {
        background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
        border-radius: 20px;
        padding: 2rem;
        margin-bottom: 1.5rem;
        border: 1px solid rgba(102, 126, 234, 0.3);
        box-shadow: 0 10px 40px rgba(0, 0, 0, 0.4);
    }
    .lab-title {
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 40%, #f093fb 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin: 0 0 0.5rem 0;
        text-align: center;
    }
    .lab-subtitle {
        color: #a0aec0;
        font-size: 1.1rem;
        text-align: center;
        margin-bottom: 1rem;
    }
    .contributor-section {
        background: rgba(0,0,0,0.2);
        border-radius: 12px;
        padding: 1rem;
        margin-top: 1rem;
    }
    .contributor-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: rgba(102, 126, 234, 0.15);
        border: 1px solid rgba(102, 126, 234, 0.3);
        padding: 4px 12px;
        border-radius: 20px;
        margin: 4px;
        font-size: 0.8rem;
        color: #a0aec0;
    }
    .version-badge {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    .github-link {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: rgba(255,255,255,0.1);
        color: #fff;
        padding: 6px 14px;
        border-radius: 8px;
        text-decoration: none;
        font-size: 0.85rem;
        margin-left: 10px;
    }
    </style>
    
    <div class="welcome-container">
        <div style="display: flex; align-items: center; justify-content: center; gap: 15px; margin-bottom: 0.5rem;">
            <span style="font-size: 2.5rem;">🧬</span>
            <div>
                <h1 class="lab-title">Physiological Laboratory</h1>
            </div>
        </div>
        
        <p class="lab-subtitle">
            <strong>Dr. Diego L. Malpica, MD</strong> — Aerospace Medicine Specialist<br>
            <span style="color: #888;">Contributing to <span style="color: #667eea;">AsterPhysiology</span> Research Initiative</span>
        </p>
        
        <div style="text-align: center; margin: 1rem 0;">
            <span class="version-badge">v""" + APP_VERSION + """</span>
            <a href=\"""" + GITHUB_REPO + """\" target="_blank" class="github-link">
                <svg width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
                    <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.012 8.012 0 0 0 16 8c0-4.42-3.58-8-8-8z"/>
                </svg>
                GitHub Repository
            </a>
        </div>
        
        <div class="contributor-section">
            <div style="color: #888; font-size: 0.85rem; margin-bottom: 0.5rem;">
                <strong>🔬 Contributing Modules & Authors:</strong>
            </div>
            <div style="display: flex; flex-wrap: wrap; justify-content: center;">
                <span class="contributor-badge">
                    🌙 <strong>Circadian:</strong> F. Tavella, K. Hannay, O. Walch (Arcascope)
                </span>
                <span class="contributor-badge">
                    😴 <strong>SAFTE Model:</strong> S. Hursh et al. (IBR/USAF)
                </span>
                <span class="contributor-badge">
                    🫀 <strong>HRV Core:</strong> Task Force 1996, Shaffer & Ginsberg
                </span>
                <span class="contributor-badge">
                    📊 <strong>ECharts:</strong> Apache Foundation
                </span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


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


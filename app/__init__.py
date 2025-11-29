"""HRV analysis application package.

This package provides comprehensive heart rate variability analysis tools
including:
- Core HRV metrics computation (time, frequency, nonlinear domains)
- Advanced analytics (entropy, fragmentation, DFA)
- Machine learning features (anomaly detection, trend analysis)
- AI-powered interpretation (GPT integration with fallback)
- Publication-ready exports (statistical tables, LaTeX)
- Wearable device integration (Garmin, sleep metrics)
- Space weather correlation analysis (NOAA SWPC)
- Comprehensive statistical analysis for publications
- Multi-day longitudinal tracking
- Solar-physiology correlation analysis
- Scientific publication-ready visualizations
- SAFTE fatigue prediction and performance modeling
"""

from __future__ import annotations

__all__ = [
    # Core analysis
    "hrv_core",
    "echarts_component",
    # Advanced metrics
    "hrv_fragmentation",
    "sleep_metrics",
    # Machine learning
    "ml_enhancements",
    "ml_analytics",
    # AI interpretation
    "gpt_interpretation",
    # Export utilities
    "export_utils",
    "publication_export",
    # Visualization
    "gauge_builder",
    "scientific_charts",
    # Device integration
    "garmin_import",
    # External data
    "noaa_space",
    # Statistical analysis
    "statistical_analysis",
    # Multi-day tracking
    "multiday_tracker",
    # Solar-physiology correlation
    "solar_physiology_correlation",
    # Fatigue prediction (SAFTE model)
    "fatigue_integration",
    "fatigue_calculator",
]


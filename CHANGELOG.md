## Changelog

All notable changes to this project will be documented in this file.

### [0.2.1] - 2025-11-08
- Fixed a deviation detection regression where missing or constant windowed metrics were incorrectly escalated to alert-level status.
- Updated README guidance to explain the new guardrails for robust z-score calculations in windowed analyses.

### [0.2.0] - 2025-11-08
- Added advanced HRV analytics suite (heart rate fragmentation, DC/AC via PRSA, symbolic dynamics, permutation entropy, MFDFA, RQA, frequency-domain entropy, HR-normalized RMSSD).
- Surfaced novel metrics within the Streamlit metrics tab for quick inspection.
- Updated README with a dedicated 2025 advanced metrics overview.

### [0.1.0] - 2025-11-08
- Initial Streamlit + Apache ECharts app documented
- Added quick start, troubleshooting, security/key guidance in README
- Outlined science-driven roadmap (QC, expanded metrics, AR/wavelet, norms, ML, evidence panel)

Notes:
- No API keys are required for current features. If future features require keys, store them in a `.env` file and never commit secrets.



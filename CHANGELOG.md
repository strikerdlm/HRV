# Changelog

All notable changes to the HRV Analysis Suite are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.6.0] - 2025-11-29

### Added
- **Population Norms Tab**: Compare HRV metrics against scientifically validated population norms
  - Age and sex-stratified reference values from Nunan et al. (2010), Ortega et al. (2024), MESA Study
  - Percentile rankings and deviation categories (Very Low → Very High)
  - Full scientific citations with PMID links
- **Blood Pressure Variability (BPV) Module**: Comprehensive BPV analysis
  - Systolic/diastolic SD, CV, ARV (Average Real Variability), SV (Successive Variation)
  - Pulse pressure and MAP calculations
  - Risk assessment based on Parati et al. (2018), Rothwell et al. (2010) thresholds
  - HRV-BPV correlation analysis for autonomic assessment
- **Enhanced Welcome Page**: Professional laboratory branding with quick access
  - Data status panel showing loaded datasets
  - Quick access grid to all analysis modules
  - Getting started guide for new users
  - Contributing modules display (Circadian, SAFTE, HRV Core, ECharts)
- **UI State Manager**: Centralized data availability tracking
  - Conditional compute button enabling/disabling
  - Session persistence for data status
  - Multi-data-type awareness (RR, sleep, ECG, BP)
- **Device Import Reorganization**: Streamlined sidebar interface
  - Polar H10 RR data with professional interface
  - Garmin Vivosmart 5 integration
  - Generic RR file support
  - Unified data normalization pipeline

### Changed
- All tabs now accessible without data upload (navigation-first design)
- Compute buttons disabled until required data is uploaded
- Welcome header uses Streamlit native components for reliable rendering
- Sidebar reorganized with device-specific import sections

---

## [1.5.0] - 2025-11-28

### Added
- **Circadian Physiology Module**: Integrated circadian rhythm simulation with multiple mathematical models (Forger99, Jewett99, Hannay19, Hannay19TP)
- **User Profiles System**: Comprehensive biometric profiles with validated clinical scales (ESS, KSS, PSQI, Samn-Perelli)
- **Docker Support**: Full containerization with PostgreSQL/TimescaleDB for production deployment
- **Professional About Tab**: Complete documentation viewer with version info, changelog, and author details
- **Space Weather Persistence**: NOAA/NASA data stored in database for longitudinal correlation studies

### Changed
- Fixed wake validation logic in circadian models (Bug: `and` → `or` for proper range checking)
- Fixed CLI function calls in circadian module (`read_standard_json` → `load_json`, etc.)
- Improved cross-platform compatibility (Windows/Linux temp paths using `tempfile`)

### Fixed
- Chronic load calculation now uses proper daily average normalization
- Sample entropy range corrected to include all complete templates
- Fusion confidence now uses variance-based coefficient of variation instead of arbitrary scaling

---

## [1.4.0] - 2025-11-15

### Added
- **ECG R-Peak Detection**: Pan-Tompkins algorithm with template matching for research-grade beat detection
- **Multi-Modal Sensor Fusion**: Integration with Oura, WHOOP, Apple Health, Fitbit, and Garmin
- **Long-Term HRV Trending**: Baseline establishment, trend detection, and anomaly alerts
- **Exercise HRV Analysis**: Heart rate recovery (HRR), parasympathetic reactivation, TRIMP calculation
- **ML Predictions**: Atrial fibrillation risk, sudden cardiac death stratification, sleep apnea screening
- **Real-Time BLE Integration**: Live streaming from Polar H10/H9, Garmin HRM-Pro, Wahoo TICKR

### Changed
- Enhanced ECharts visualizations with modern two-ring gauge style
- Improved responsive chart sizing with ResizeObserver

---

## [1.3.0] - 2025-10-20

### Added
- **NOAA Space Weather Dashboard**: Comprehensive solar and geomagnetic data feeds
- **Fatigue Prediction (SAFTE Model)**: Sleep-based cognitive effectiveness modeling
- **Scientific Charts Module**: Publication-ready visualizations with unified physiological timelines
- **Biofeedback Mode**: Real-time coherence training with breathing guides

### Changed
- Reorganized tab structure for better workflow navigation
- Updated gauge builder with ECharts-based modern gauges

---

## [1.2.0] - 2025-09-15

### Added
- **ActiGraph GT3X Integration**: Research-grade accelerometer data import
- **Somfit Pro Integration**: Home sleep testing device support with EDF parsing
- **Publication Export**: APA-formatted tables and LaTeX export for journals
- **AI-Powered Interpretation**: GPT-5 integration for clinical narrative generation

### Changed
- Improved artifact detection algorithms
- Enhanced windowed analysis with configurable parameters

---

## [1.1.0] - 2025-08-01

### Added
- **Garmin Connect Integration**: Bulk export and FIT file support
- **Autonomic Function Tests**: Valsalva ratio, deep breathing E:I, 30:15 standing test
- **Readiness Assessment**: Morning HRV-based training readiness scoring
- **Multi-file Analysis**: Comparative analysis across multiple recordings

### Changed
- Redesigned sidebar configuration
- Improved PSD computation methods (Welch, Periodogram, AR)

---

## [1.0.0] - 2025-07-01

### Added
- **Core HRV Analysis**: Time-domain, frequency-domain, and nonlinear metrics
- **Poincaré Plots**: SD1/SD2 analysis with ellipse visualization
- **Spectrogram View**: Time-frequency analysis of HRV patterns
- **Quality Control**: Artifact detection with threshold-based filtering
- **Space Weather Correlation**: Integration with NASA DONKI and NOAA data
- **Export Functionality**: Markdown, CSV, and JSON export options

### Technical Foundation
- Streamlit-based web interface
- ECharts integration for interactive visualizations
- Modular architecture with separation of concerns
- Comprehensive type hints and documentation

---

## Version History Summary

| Version | Date | Highlights |
|---------|------|------------|
| 1.6.0 | 2025-11-29 | Population norms, BPV analysis, enhanced welcome |
| 1.5.0 | 2025-11-28 | Circadian module, user profiles, Docker |
| 1.4.0 | 2025-11-15 | ECG detection, sensor fusion, ML predictions |
| 1.3.0 | 2025-10-20 | NOAA space weather, SAFTE fatigue model |
| 1.2.0 | 2025-09-15 | ActiGraph, Somfit, publication export |
| 1.1.0 | 2025-08-01 | Garmin, ANS tests, readiness scoring |
| 1.0.0 | 2025-07-01 | Initial release with core HRV analysis |

---

## Roadmap

### Completed (Q4 2025)
- ✅ Population normative database with age/sex stratification
- ✅ Blood Pressure Variability (BPV) integration
- ✅ Circadian rhythm analysis module
- ✅ Docker containerization with TimescaleDB

### Planned Features (Q1-Q2 2026)
- Advanced nonlinear dynamics (MSE, RQA, Lyapunov)
- Mobile companion app for data collection
- RESTful API for third-party integration
- Cloud sync and multi-user support

### Under Research
- G-tolerance assessment for aerospace applications
- Altitude/hypoxia HRV analysis
- Spatial disorientation markers
- Baroreflex sensitivity from HRV-BPV coherence

---

## Contributors

**Lead Developer & Author:**  
Dr. Diego Leonel Malpica Hincapié, MD  
Aerospace Medicine Specialist  
National University of Colombia

**Circadian Module:**  
Original package by Arcascope (Franco Tavella, Kevin Hannay, Olivia Walch)  
UI updates and integration by Dr. Diego L. Malpica

---

*For detailed feature documentation, see `docs/Manual.md`*

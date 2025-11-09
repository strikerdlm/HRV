# Changelog

## [Unreleased]
### Added
- Space Weather tab with NOAA SWPC K‑index and F10.7 feeds (no key required).
- Open‑Meteo Archive integration for Bogotá weather covariates.
- Lag scan correlations (Pearson), p‑values (SciPy), FDR q‑values.
- Partial correlations controlling for temperature, humidity, pressure.
- OLS residual diagnostics: R², Durbin–Watson, normality test, residual plots.
- JSONL persistence of best correlations keyed by Cedula.

### Changed
- Tabs extended to include “Space Weather”.

### Notes
- P‑values computed when SciPy is installed.
- NOAA endpoints cached for 5 minutes.



---
alwaysApply: true
---

## Plotting policy (ECharts-first, publication-grade)

When adding or modifying any plot/visualization in this project, agents MUST:

- **Default library**: Use **Apache ECharts** by default. Use **Plotly only as a fallback** when ECharts cannot meet a requirement or cannot be integrated cleanly.
- **Professional, modern design**:
  - Include a clear **title** (and optional subtitle).
  - Always label axes with **variable name + unit**.
  - Ensure legends/series names match the terminology used elsewhere in the app.
  - Provide informative tooltips (with the same variable names + units).
  - Use consistent theming, high-contrast styling, and colorblind-safe palettes.
- **Automatic visualization coverage**:
  - The app should provide **many plots by default** to visualize key inputs, quality-control, derived metrics, and results without requiring manual scripting.
  - Prefer interactive exploration (zoom/pan, brushing, trace toggles, range sliders) when it improves comprehension.
- **Export — highest quality for publication**:
  - Every plot MUST support export at the **highest quality feasible** (vector when possible).
  - Provide export options in all relevant formats: **SVG, PDF, PNG (high DPI), HTML**, and **data/spec export (CSV/JSON)**. Add additional publication formats (e.g., TIFF/EPS) when feasible for the chosen library.
- **Explain what the user sees (mandatory caption/description)**:
  - Directly below each plot, include a short paragraph describing:
    - what the plot shows,
    - what the x/y axes represent (variables + units),
    - what each series/marker represents,
    - any preprocessing that affects interpretation (filtering, windowing, normalization, missing-data handling).
- **Dependencies + documentation stay in sync**:
  - If a plot/export feature needs new libraries, update **`requirements.txt`** accordingly (use versions consistent with the repo).
  - When introducing a new plot or new plotting-related feature, update **`README.md`**, **`docs/Manual.md`**, and **`CHANGELOG.md`** (for user-visible changes).

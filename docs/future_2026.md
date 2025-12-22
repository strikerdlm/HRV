---
layout: default
title: Future Performance Plan (2026)
---

## Goal

Improve **performance** (speed) and **smoothness** (UI responsiveness) of this Streamlit 1.36 app, without breaking scientific correctness or existing features.

This document answers:

- **Which “language” improves performance the most (for this project)?**
- **How to improve performance using Streamlit 1.36 capabilities**
- **If you need a “military-grade” deployable/compiled package, how to ship it**

---

## What usually makes Streamlit apps feel slow

- **Every widget change triggers a rerun**: if expensive computations or big DataFrames are rebuilt on rerun, UI feels “faded / always running”.
- **Too much data sent to the browser**: huge arrays, large tables, big chart configs (ECharts/Plotly) make the front-end stutter even if Python is fast.
- **Heavy computations on the main thread**: entropy, spectrograms, windowed analysis, correlations across many lags are CPU-expensive.
- **Cache misses due to unstable inputs**: if cache keys change often (timestamps, random seeds, mutable objects), caching won’t help.

Good news: this repo already includes key building blocks:

- Streamlit caching (`@st.cache_data`, `@st.cache_resource`)
- Session-state caching and hash invalidation (`app/hrv_cache.py`)
- Adaptive performance caps + downsampling (`app/performance_utils.py`)
- Optional GPU acceleration (`app/gpu_processing.py`, `app/gpu_accelerate.py`)
- Streamlit stability settings (`.streamlit/config.toml`, notably `fastReruns=false`)

---

## Which language will improve performance (best answer for THIS project)

### The short, practical answer

- **Keep the UI in Python (Streamlit)**.
- Move only the **compute hotspots** to a compiled language:
  - **Rust** (recommended) or **C++** for CPU kernels
  - **CUDA** for GPU kernels (already supported optionally via CuPy)

Why: Streamlit itself is **Python-first**. Rewriting the whole app in another language would also mean rewriting the UI framework (and losing Streamlit’s speed of development). The best performance-per-risk approach is a **hybrid**:

- Python = orchestration, caching, UI, I/O, and reproducible logging
- Rust/C++/CUDA = fast math kernels for the slowest computations

### Recommended language choice (2026)

- **Rust** is the best “next language” for this codebase because it offers:
  - High performance (native code)
  - Strong safety guarantees (memory-safe by default)
  - Great Python integration via **PyO3** (expose Rust functions as a Python module)
  - Easy distribution in wheels for common OS/architectures

### What *not* to do (unless you want a full rewrite)

- Switching from Python to JavaScript/TypeScript/Go **will not automatically speed up Streamlit**, because Streamlit isn’t built that way.
- A full rewrite only makes sense if you plan to replace Streamlit with a different UI stack (e.g., React + FastAPI, or a desktop UI).

---

## Streamlit 1.36 performance playbook (easy checklist)

### 1) Make reruns cheap

- **Batch inputs with `st.form`** so sliders/text inputs don’t trigger expensive work on every change.
- **Gate heavy work behind explicit buttons** (“Run HRV Analysis”, “Compute Spectrogram”, “Run Correlations”).
- **Use `st.session_state` as the “single source of truth”** for:
  - uploads
  - selected datasets
  - computed results
  - “last computed hash”

This repo already follows that pattern in multiple areas; expand it wherever you see “faded / always running” behavior.

### 2) Use caching correctly (Streamlit 1.36)

Use **two cache layers**:

- **`@st.cache_resource`** for long-lived resources (connect once, reuse):
  - database connections / database managers
  - GPU context / detected GPU info
  - loaded models (ML models, large reference tables)

- **`@st.cache_data`** for deterministic results (compute once, reuse):
  - parsed NOAA/SWPC feeds (with TTL)
  - derived feature matrices (with TTL)
  - precomputed “static” tables used in multiple tabs

Rules of thumb:

- Use **`ttl=`** + **`max_entries=`** (you already do) to prevent unbounded memory growth.
- Avoid caching massive objects when you can cache **compact summaries** or **hash-keyed slices**.
- Keep cache function inputs **stable and hashable** (avoid passing objects that change identity each rerun).

### 3) Reduce browser payload (this is often the #1 “smoothness” fix)

- **Downsample before chart building**:
  - build ECharts/Plotly configs from downsampled arrays, not full-resolution
  - avoid converting large NumPy arrays to huge Python lists unless absolutely necessary
- **Cap DataFrame display sizes**:
  - show summary tables by default
  - allow “expand to full table” only on demand

This repo already has caps like `max_plot_points` and `max_dataframe_rows`; the key is to apply those caps consistently in every tab.

### 4) Lazy-load the expensive tabs

Streamlit tabs render on rerun; if a tab contains expensive computations, make it lazy:

- First render: show summary + a button (“Load/Compute details”)
- Only compute heavy charts when the user explicitly asks

There is a helper for this style in `app/performance_utils.py` (`lazy_load_tab_content`). Use it broadly for spectrograms, long-window scans, and large correlation matrices.

### 5) Streamlit runtime configuration (already mostly correct)

In `.streamlit/config.toml` you already have settings that improve stability and smoothness:

- `fastReruns = false` (reduces racey rerun behavior)
- `client.caching = true`
- `browser.gatherUsageStats = false`

For production deployments, consider:

- `server.fileWatcherType = "none"` (fastest; best when code is not being edited live)
  - keep `"poll"` only when needed for network filesystems / sync folders

---

## Where “real speed” lives in this repo (hotspot map)

The compute-heavy areas that benefit most from compiled acceleration (Numba/Rust/CUDA):

- **Entropy and nonlinear metrics** (sample entropy, approximate entropy, DFA variants)
- **Spectrogram / time-frequency transforms**
- **Windowed analysis loops** across long recordings or many datasets
- **Correlation scans across many lags** (especially if you compute multiple metrics × multiple predictors)

Your current architecture already supports a clean split:

- Keep the public, validated API in `app/hrv_core.py`
- Put fast implementations behind the scenes (CPU optimized / GPU optimized / future Rust optimized)

---

## 2026 upgrade paths (from easiest to fastest)

### Path A — “Best ROI” (stay Python, make Streamlit smoother)

Do this if you want immediate smoothness with minimal risk:

- Ensure **Numba** is installed and used where supported (`numba` is already in `requirements.txt`)
- Continue pushing heavy work behind buttons + caching
- Aggressively downsample for plots and cap DataFrame rendering
- Prefer session-state caching for rapid UI interactions (avoid global cache churn)

Expected outcome: typically **2–10×** smoother UI for large files, mainly from fewer recomputes and smaller browser payloads.

### Path B — “Hybrid CPU acceleration” (Rust module for hotspots)

Do this if you want a noticeable compute speedup without changing the UI:

- Write Rust kernels for a few targeted functions (entropy, DFA, spectrogram binning, window loops)
- Expose them to Python via PyO3
- Add “fallback to pure Python/NumPy” when the Rust module is unavailable

Expected outcome: commonly **5–30×** faster on the hottest kernels (depends on which kernels you move).

### Path C — “GPU-first” (CUDA/CuPy)

You already support GPU as an optional accelerator. For long recordings and heavy transforms, GPU can be a large win, but it adds operational complexity (CUDA toolkit, driver compatibility, memory limits).

Expected outcome: **2–50×** on certain workloads (especially FFT-based operations), but requires the right GPU setup.

---

## “Military app to compile”: what it can mean, and how to do it

People use “compile” in two different ways. Here are the realistic options for a Streamlit app.

### Option 1 (recommended): Docker image (reproducible, auditable, easiest to harden)

This repo already includes `Dockerfile` and `docker-compose.yml`.

Why Docker fits “military-grade” needs:

- Reproducible runtime (same Python + pinned deps)
- Easy to scan (SBOM + vulnerability scanning)
- Easy to run **offline** and on a locked-down network
- Runs as **non-root** (already configured in Dockerfile)

Hardening checklist:

- **Pin base image** to a digest (for reproducibility)
- Use an internal package mirror / offline wheelhouse (no internet required during build)
- Disable outbound network egress at the host/firewall level if needed
- Store secrets in `.env` or secret manager (never in code)
- Turn off dev features in production (`developmentMode=false`, set `logger.level=warning` or `error`)

### Option 2: “Single executable” packaging (possible, but less ideal for Streamlit)

Tools like **PyInstaller** or **Nuitka** can package Python apps. For Streamlit:

- You usually end up with an executable that **launches a local Streamlit server**
- The UI still runs in a browser (or a thin wrapper)
- This does **not** truly “hide” code from a determined attacker

Use this when:

- You need a single-file deliverable for field laptops
- Docker is not allowed

### Option 3: Desktop wrapper (Tauri/Electron) + embedded server

This can feel like a “compiled app” to users:

- Your binary launches a local Python/Streamlit server
- A desktop window opens to the local URL

It’s operationally heavier (you now ship a desktop runtime too), but can be the best UX for “just run the app”.

---

## Deployment recommendation (simple decision)

- If your priority is **smoothness now**: stay on Streamlit 1.36, focus on rerun reduction + caching + downsampling (Path A).
- If your priority is **raw compute performance** in 2026: keep Streamlit UI, move hotspots to **Rust** (Path B), and keep GPU optional (Path C).
- If you need a **secure, auditable, offline deliverable**: prefer **Docker** (Option 1). “Single executable” is possible, but less robust and often harder to maintain.

---

## Security reminder (do this for every deployment)

- **Never** put API keys or secrets into code.
- Use `.env` (already supported) or a secrets manager.
- Treat “compiled” packages as **not a secrecy boundary**—assume secrets can be extracted if embedded.


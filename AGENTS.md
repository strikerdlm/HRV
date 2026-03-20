# AGENTS.md

## Cursor Cloud specific instructions

### Services Overview

This codebase has three independently runnable services sharing a common Python analysis core:

| Service | Command | Port | Notes |
|---|---|---|---|
| **Streamlit** (research UI) | `streamlit run app/research_app.py` | 8501 | Also: `app/operational_app.py`, `app/space_weather_ds_app.py` |
| **FastAPI** (REST backend) | `uvicorn api.main:app --reload --port 8180` | 8180 | Required for the Next.js frontend |
| **Next.js** (modern frontend) | `npm run dev` (in `frontend/`) | 3100 | Requires FastAPI running on 8180 |

The Streamlit app is fully self-contained (SQLite, no external services needed). The Next.js frontend requires the FastAPI backend.

### Running services

- Ensure `$HOME/.local/bin` is on `PATH` (pip installs tools there: `streamlit`, `uvicorn`, `pytest`, `ruff`, etc.).
- The frontend needs `frontend/.env.local` with `NEXT_PUBLIC_API_URL=http://localhost:8180` (copy from `frontend/.env.example` if missing).
- All API keys (OpenAI, NASA, Garmin, etc.) are optional; the app gracefully degrades without them.
- The Streamlit config at `.streamlit/config.toml` sets `headless = true` and `fileWatcherType = "none"` — this is intentional for stability.

### Testing

- **Python tests**: `pytest tests/ -v` (366 tests, all pass). No `pytest-timeout` plugin is installed — do not use `--timeout`.
- **Python linting**: `ruff check app/ tests/` (runs clean modulo existing E402 warnings in test files — those are expected due to `sys.path` manipulation).
- **Frontend lint**: `npx eslint .` (in `frontend/`).
- **Frontend build**: `npm run build` (in `frontend/`).
- See `README.md` for full code quality commands (`black`, `isort`, `mypy`, `bandit`).

### Gotchas

- The root `/workspace/node_modules/` contains only `echarts` (embedded JS bundle for Streamlit). The frontend `node_modules` is at `frontend/node_modules/`.
- Streamlit 1.36.0 is pinned for stability (later versions cause `@st.fragment` / SessionInfo race errors). Do not upgrade without testing.
- Tornado 6.4.2 is pinned to prevent WebSocket ping/timeout issues.
- `kaleido` (Plotly static export) can be slow to import on first use — this is normal.

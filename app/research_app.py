from __future__ import annotations

"""
Research Streamlit entrypoint (full dashboards).

This wrapper exists so the repo exposes two explicit entrypoints:
- Operational: `streamlit run app/operational_app.py`
- Research:    `streamlit run app/research_app.py`

The underlying implementation remains in `app/app.py` (historic entrypoint).
"""


def main() -> None:
    # IMPORTANT: when running Streamlit from inside `app/`, `import app` resolves
    # to `app/app.py` (not the package). That module defines `main()`.
    import app as research_app  # noqa: PLC0415

    research_app.main()


if __name__ == "__main__":
    main()



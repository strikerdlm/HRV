from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def main() -> None:
    parser = argparse.ArgumentParser(
        description="fatigue-calculator CLI: launch apps or run quick checks"
    )
    subparsers = parser.add_subparsers(dest="command", required=False)

    app_parser = subparsers.add_parser("app", help="Run the Streamlit app")
    app_parser.add_argument("--port", type=int, default=8501, help="Port to serve on")
    app_parser.add_argument(
        "--address", default="0.0.0.0", help="Address to bind (default: 0.0.0.0)"
    )

    check_parser = subparsers.add_parser(
        "check", help="Import package and print a confirmation"
    )

    args = parser.parse_args()

    if args.command in (None, "app"):
        # Default action: run the Streamlit app
        app_path = _repo_root() / "streamlit_app.py"
        if not app_path.exists():
            print(f"Could not find Streamlit app at {app_path}", file=sys.stderr)
            sys.exit(1)
        cmd = [
            "streamlit",
            "run",
            str(app_path),
            "--server.port=" + str(getattr(args, "port", 8501)),
            "--server.address=" + str(getattr(args, "address", "0.0.0.0")),
        ]
        sys.exit(subprocess.call(cmd))

    if args.command == "check":
        try:
            from fatigue_calculator import __version__  # noqa: F401
            print("fatigue_calculator import OK")
            sys.exit(0)
        except Exception as exc:  # pragma: no cover
            print(f"Import failed: {exc}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
"""
Centralized logging configuration for Mission Control - Flight Surgeon.

Provides persistent file logging for debugging, error tracking, and audit
trails.
Logs are written to the `logs/` directory with automatic rotation.

Usage:
    from app.logging_config import setup_logging, get_logger

    # Call once at app startup
    setup_logging()

    # Get module-specific logger
    logger = get_logger(__name__)
    logger.info("Processing started")

Author: Mission Control - Flight Surgeon
Version: 1.0.0
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Final

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_LOG_DIR: Final[Path] = Path(__file__).parent.parent / "logs"
_LOG_FORMAT: Final[str] = (
    "%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s"
)
_DATE_FORMAT: Final[str] = "%Y-%m-%d %H:%M:%S"

# Log file settings
_MAX_BYTES: Final[int] = 10 * 1024 * 1024  # 10 MB per file
_BACKUP_COUNT: Final[int] = 5  # Keep 5 rotated files
_LOG_LEVEL_FILE: Final[int] = logging.DEBUG  # Capture everything to file
_LOG_LEVEL_CONSOLE: Final[int] = logging.INFO  # Less verbose on console

# Track if logging has been set up
_logging_initialized: bool = False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


class _SuppressAsyncioWebSocketClosed(logging.Filter):
    """Suppress benign Tornado WebSocketClosedError noise from asyncio.

    Streamlit uses Tornado websockets. When a browser tab refreshes/closes,
    Tornado can schedule a websocket write that races with the client disconnect.
    In that case, Tornado raises WebSocketClosedError (or StreamClosedError) and
    asyncio logs: "Task exception was never retrieved" at ERROR level.

    This is typically benign and can spam `logs/errors.log`. We suppress only this
    exact pattern so real asyncio errors remain visible.
    """

    def filter(self, record: logging.LogRecord) -> bool:  # noqa: A003
        if record.levelno < logging.ERROR:
            return True
        if record.name != "asyncio":
            return True
        try:
            message = record.getMessage()
        except Exception:
            return True
        if "Task exception was never retrieved" not in message:
            return True

        exc_info = record.exc_info
        if not exc_info or exc_info[0] is None:
            return True
        exc_type = exc_info[0]
        exc_name = getattr(exc_type, "__name__", "")
        if exc_name in {"WebSocketClosedError", "StreamClosedError"}:
            return False
        return True


def setup_logging(
    *,
    log_level_file: int = _LOG_LEVEL_FILE,
    log_level_console: int = _LOG_LEVEL_CONSOLE,
    log_dir: Path | None = None,
) -> Path:
    """
    Initialize centralized logging with file and console handlers.

    Creates the logs directory if it doesn't exist. Sets up:
    - Rotating file handler for persistent debugging (app.log)
    - Separate error log for critical issues (errors.log)
    - Console handler for real-time feedback

    Args:
        log_level_file: Logging level for file output (default: DEBUG)
        log_level_console: Logging level for console output (default: INFO)
        log_dir: Custom log directory (default: project_root/logs/)

    Returns:
        Path to the log directory.

    Raises:
        OSError: If log directory cannot be created.
    """
    global _logging_initialized  # noqa: PLW0603

    if _logging_initialized:
        return _LOG_DIR if log_dir is None else log_dir

    target_dir = log_dir if log_dir is not None else _LOG_DIR

    # Create logs directory
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        # Fall back to console-only if we can't create logs dir
        sys.stderr.write(
            f"Warning: Cannot create log directory {target_dir}: {exc}\n"
        )
        _setup_console_only(log_level_console)
        _logging_initialized = True
        return target_dir

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # Capture all; handlers filter

    # Clear existing handlers to prevent duplicates on Streamlit rerun
    root_logger.handlers.clear()

    formatter = logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT)
    suppress_ws_closed = _SuppressAsyncioWebSocketClosed()

    # 1. Main application log (rotating)
    app_log_path = target_dir / "app.log"
    app_handler = RotatingFileHandler(
        app_log_path,
        maxBytes=_MAX_BYTES,
        backupCount=_BACKUP_COUNT,
        encoding="utf-8",
    )
    app_handler.setLevel(log_level_file)
    app_handler.setFormatter(formatter)
    app_handler.addFilter(suppress_ws_closed)
    root_logger.addHandler(app_handler)

    # 2. Error-only log (for critical issues)
    error_log_path = target_dir / "errors.log"
    error_handler = RotatingFileHandler(
        error_log_path,
        maxBytes=_MAX_BYTES,
        backupCount=_BACKUP_COUNT,
        encoding="utf-8",
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    error_handler.addFilter(suppress_ws_closed)
    root_logger.addHandler(error_handler)

    # 3. Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level_console)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(suppress_ws_closed)
    root_logger.addHandler(console_handler)

    # Log startup
    startup_msg = (
        f"Logging initialized | Dir: {target_dir} | "
        f"File level: {logging.getLevelName(log_level_file)} | "
        f"Console level: {logging.getLevelName(log_level_console)}"
    )
    root_logger.info(startup_msg)

    _logging_initialized = True
    return target_dir


def get_logger(name: str) -> logging.Logger:
    """
    Get a named logger for a module.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured Logger instance.
    """
    return logging.getLogger(name)


def log_exception(
    logger: logging.Logger,
    message: str,
    exc: BaseException,
    *,
    include_traceback: bool = True,
) -> None:
    """
    Log an exception with consistent formatting.

    Args:
        logger: Logger instance to use
        message: Context message
        exc: The exception to log
        include_traceback: Whether to include full traceback (default: True)
    """
    if include_traceback:
        logger.exception("%s: %s", message, exc)
    else:
        logger.error("%s: %s (%s)", message, exc, type(exc).__name__)


def get_session_log_path() -> Path:
    """
    Get path for a session-specific log file.

    Returns:
        Path for a timestamped session log.
    """
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return _LOG_DIR / f"session_{timestamp}.log"


def log_user_action(action: str, details: dict | None = None) -> None:
    """
    Log a user action for audit trail.

    Args:
        action: Description of the action (e.g., "uploaded_file" or "ran_analysis")
        details: Optional dictionary with action details
    """
    audit_logger = logging.getLogger("hrv_audit")
    detail_str = f" | {details}" if details else ""
    audit_logger.info("USER_ACTION: %s%s", action, detail_str)


# ---------------------------------------------------------------------------
# Internal Helpers
# ---------------------------------------------------------------------------


def _setup_console_only(level: int) -> None:
    """Set up console-only logging as fallback."""
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT))
    handler.addFilter(_SuppressAsyncioWebSocketClosed())
    root_logger.addHandler(handler)


# ---------------------------------------------------------------------------
# Auto-setup on import (optional - can be disabled)
# ---------------------------------------------------------------------------

# Uncomment to auto-initialize on import:
# setup_logging()


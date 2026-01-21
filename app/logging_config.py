"""
Centralized logging configuration for Mission Control - Flight Surgeon.

Provides persistent file logging for debugging, error tracking, and audit
trails. Includes comprehensive Streamlit-specific debugging capabilities.
Logs are written to the `logs/` directory with automatic rotation.

Usage:
    from app.logging_config import setup_logging, get_logger, enable_streamlit_debug

    # Call once at app startup
    setup_logging()

    # Enable Streamlit-specific debugging (optional, verbose)
    enable_streamlit_debug()

    # Get module-specific logger
    logger = get_logger(__name__)
    logger.info("Processing started")

Features:
    - Rotating file logs (app.log, errors.log, streamlit.log)
    - Streamlit component lifecycle tracking
    - Session state change monitoring
    - WebSocket event logging
    - Performance timing helpers

Author: Dr Diego Malpica MD
Version: 2.0.0
"""

from __future__ import annotations

import functools
import logging
import os
import sys
import time
import traceback
import warnings
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Callable, Final, TypeVar

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_ENV_LOG_DIR: Final[str] = "HRV_LOG_DIR"
_DEFAULT_LOG_DIR: Final[Path] = Path(__file__).parent.parent / "logs"
_ACTIVE_LOG_DIR: Path | None = None
_LOG_FORMAT: Final[str] = (
    "%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s"
)
_LOG_FORMAT_DETAILED: Final[str] = (
    "%(asctime)s.%(msecs)03d | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | "
    "%(message)s"
)
_DATE_FORMAT: Final[str] = "%Y-%m-%d %H:%M:%S"

# Log file settings
_MAX_BYTES: Final[int] = 10 * 1024 * 1024  # 10 MB per file
_BACKUP_COUNT: Final[int] = 5  # Keep 5 rotated files
_LOG_LEVEL_FILE: Final[int] = logging.DEBUG  # Capture everything to file
_LOG_LEVEL_CONSOLE: Final[int] = logging.INFO  # Less verbose on console
_ENV_LOG_CONSOLE_LEVEL: Final[str] = "HRV_LOG_CONSOLE_LEVEL"
_ENV_LOG_FILE_LEVEL: Final[str] = "HRV_LOG_FILE_LEVEL"
_ENV_LOG_RICH: Final[str] = "HRV_LOG_RICH"
_ENV_LOG_RICH_PATH: Final[str] = "HRV_LOG_RICH_SHOW_PATH"
_ENV_LOG_WARNINGS: Final[str] = "HRV_LOG_WARNINGS"
_ENV_LOG_FAULTHANDLER: Final[str] = "HRV_FAULTHANDLER"

# Track if logging has been set up
_logging_initialized: bool = False
_streamlit_debug_enabled: bool = False

# Type variable for decorators
F = TypeVar("F", bound=Callable[..., Any])


def _is_streamlit_runtime() -> bool:
    """Return True when running under a Streamlit app session."""
    if "streamlit" in sys.modules:
        return True
    env_markers = (
        "STREAMLIT_SERVER_PORT",
        "STREAMLIT_SERVER_HEADLESS",
        "STREAMLIT_RUNTIME",
    )
    return any(bool(os.environ.get(marker)) for marker in env_markers)


def _default_user_log_root() -> Path:
    """Return a per-user log root outside the repo (avoids Streamlit file watcher)."""
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        if isinstance(base, str) and base.strip():
            return Path(base) / "HRV"
    return Path.home() / ".hrv"


def _resolve_log_dir(explicit_dir: Path | None) -> Path:
    """Resolve the log directory with env override and Streamlit-safe default."""
    if explicit_dir is not None:
        return explicit_dir
    env_dir = os.environ.get(_ENV_LOG_DIR)
    if isinstance(env_dir, str) and env_dir.strip():
        return Path(env_dir.strip()).expanduser().absolute()
    if _is_streamlit_runtime():
        return (_default_user_log_root() / "logs").absolute()
    return _DEFAULT_LOG_DIR


def get_log_dir() -> Path:
    """Return the active log directory (resolved once logging is initialized)."""
    if _ACTIVE_LOG_DIR is not None:
        return _ACTIVE_LOG_DIR
    return _resolve_log_dir(None)


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
        if exc_info and exc_info[0] is not None:
            exc_type = exc_info[0]
            exc_name = getattr(exc_type, "__name__", "")
            if exc_name in {"WebSocketClosedError", "StreamClosedError"}:
                return False
            return True

        # Some asyncio error logs embed the exception type into the message text
        # without populating `record.exc_info`. Suppress only the known benign
        # websocket-close race that Streamlit/Tornado emits.
        benign_markers = (
            "WebSocketClosedError",
            "StreamClosedError",
            "tornado.websocket.WebSocketClosedError",
            "tornado.iostream.StreamClosedError",
        )
        if any(marker in message for marker in benign_markers):
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
        return get_log_dir()

    # Allow env vars to override levels without code changes.
    log_level_console = _parse_log_level_env(_ENV_LOG_CONSOLE_LEVEL, default=log_level_console)
    log_level_file = _parse_log_level_env(_ENV_LOG_FILE_LEVEL, default=log_level_file)

    target_dir = _resolve_log_dir(log_dir)

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
    if root_logger.handlers:
        for handler in list(root_logger.handlers):
            try:
                handler.close()
            except Exception:
                pass
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
    console_handler = _create_console_handler(
        log_level_console=log_level_console,
        fallback_formatter=formatter,
        suppress_ws_closed=suppress_ws_closed,
    )
    root_logger.addHandler(console_handler)

    # Route warnings to logging (helps console + app.log visibility).
    if _env_truthy(_ENV_LOG_WARNINGS, default=True):
        logging.captureWarnings(True)
        logging.getLogger("py.warnings").setLevel(logging.WARNING)

    # Ensure unhandled exceptions are logged (useful in containers/Streamlit).
    _install_unhandled_exception_hook()

    # Optional: emit tracebacks on fatal interpreter signals (segfaults, etc.)
    if _env_truthy(_ENV_LOG_FAULTHANDLER, default=False):
        try:
            import faulthandler

            faulthandler.enable(all_threads=True)
        except Exception:
            # Never fail logging setup due to faulthandler availability.
            pass

    # Log startup
    startup_msg = (
        f"Logging initialized | Dir: {target_dir} | "
        f"File level: {logging.getLevelName(log_level_file)} | "
        f"Console level: {logging.getLevelName(log_level_console)}"
    )
    root_logger.info(startup_msg)

    global _ACTIVE_LOG_DIR  # noqa: PLW0603
    _ACTIVE_LOG_DIR = target_dir
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
    return get_log_dir() / f"session_{timestamp}.log"


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
# Streamlit-Specific Debugging
# ---------------------------------------------------------------------------


def enable_streamlit_debug(*, verbose: bool = True) -> None:
    """
    Enable comprehensive Streamlit debugging.
    
    This sets up detailed logging for:
    - Streamlit internal operations
    - Session state changes
    - Component lifecycle events
    - WebSocket communications
    - Cache operations
    
    Args:
        verbose: If True, set all Streamlit loggers to DEBUG level.
                 If False, set to INFO level.
    
    Warning:
        This produces VERY verbose output. Use only for debugging.
    """
    global _streamlit_debug_enabled  # noqa: PLW0603
    
    level = logging.DEBUG if verbose else logging.INFO
    
    # Streamlit internal loggers
    streamlit_loggers = [
        "streamlit",
        "streamlit.runtime",
        "streamlit.runtime.scriptrunner",
        "streamlit.runtime.scriptrunner_utils",
        "streamlit.runtime.state",
        "streamlit.runtime.caching",
        "streamlit.runtime.websocket",
        "streamlit.watcher",
        "streamlit.web",
        "streamlit.web.server",
        "streamlit.components",
    ]
    
    for logger_name in streamlit_loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(level)
    
    # Also enable tornado/websocket debugging if verbose
    if verbose:
        logging.getLogger("tornado").setLevel(logging.INFO)
        logging.getLogger("tornado.access").setLevel(logging.WARNING)
        logging.getLogger("tornado.application").setLevel(logging.DEBUG)
        logging.getLogger("tornado.general").setLevel(logging.DEBUG)
    
    # Create dedicated streamlit log file
    if not _streamlit_debug_enabled:
        target_dir = get_log_dir()
        target_dir.mkdir(parents=True, exist_ok=True)
        
        streamlit_log_path = target_dir / "streamlit.log"
        handler = RotatingFileHandler(
            streamlit_log_path,
            maxBytes=_MAX_BYTES,
            backupCount=_BACKUP_COUNT,
            encoding="utf-8",
        )
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(logging.Formatter(_LOG_FORMAT_DETAILED, datefmt=_DATE_FORMAT))
        
        # Add to streamlit root logger
        streamlit_root = logging.getLogger("streamlit")
        streamlit_root.addHandler(handler)
    
    _streamlit_debug_enabled = True
    logging.getLogger(__name__).info(
        "Streamlit debug logging enabled | Level: %s | Log: logs/streamlit.log",
        logging.getLevelName(level)
    )


def log_session_state(context: str = "") -> None:
    """
    Log the current Streamlit session state for debugging.
    
    Args:
        context: Optional context string to identify where this was called.
    """
    try:
        import streamlit as st
        
        logger = logging.getLogger("hrv.session_state")
        state_dict = dict(st.session_state)
        
        # Redact sensitive keys
        redacted = {}
        sensitive_patterns = ("password", "token", "secret", "api_key", "credential")
        for key, value in state_dict.items():
            key_lower = str(key).lower()
            if any(pattern in key_lower for pattern in sensitive_patterns):
                redacted[key] = "[REDACTED]"
            elif isinstance(value, (str, int, float, bool, type(None))):
                redacted[key] = value
            else:
                redacted[key] = f"<{type(value).__name__}>"
        
        ctx_str = f" [{context}]" if context else ""
        logger.debug("Session state%s: %d keys | %s", ctx_str, len(redacted), redacted)
    except Exception as exc:
        logging.getLogger(__name__).warning("Failed to log session state: %s", exc)


def log_rerun_trigger(reason: str, **details: Any) -> None:
    """
    Log when and why a Streamlit rerun is triggered.
    
    Call this before st.rerun() to track rerun patterns.
    
    Args:
        reason: Description of why the rerun is happening.
        **details: Additional context as keyword arguments.
    """
    logger = logging.getLogger("hrv.rerun")
    detail_str = f" | {details}" if details else ""
    
    # Get caller info
    stack = traceback.extract_stack()
    if len(stack) >= 2:
        caller = stack[-2]
        location = f"{caller.filename}:{caller.lineno} in {caller.name}"
    else:
        location = "unknown"
    
    logger.info("RERUN triggered | Reason: %s | Location: %s%s", reason, location, detail_str)


def timed_operation(operation_name: str) -> Callable[[F], F]:
    """
    Decorator to log the execution time of a function.
    
    Usage:
        @timed_operation("compute_hrv")
        def compute_hrv(data):
            ...
    
    Args:
        operation_name: Name to use in log messages.
    
    Returns:
        Decorated function.
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            logger = logging.getLogger("hrv.timing")
            start = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                elapsed = time.perf_counter() - start
                logger.debug(
                    "TIMING | %s completed in %.3fs",
                    operation_name, elapsed
                )
                return result
            except Exception as exc:
                elapsed = time.perf_counter() - start
                logger.error(
                    "TIMING | %s failed after %.3fs | Error: %s",
                    operation_name, elapsed, exc
                )
                raise
        return wrapper  # type: ignore[return-value]
    return decorator


class StreamlitDebugContext:
    """
    Context manager for debugging a specific section of Streamlit code.
    
    Usage:
        with StreamlitDebugContext("loading_data"):
            # Your code here
            df = load_data()
    
    Logs entry, exit, timing, and any exceptions.
    """
    
    def __init__(self, name: str, log_session_state: bool = False) -> None:
        """
        Initialize debug context.
        
        Args:
            name: Name for this debug section.
            log_session_state: If True, log session state on entry/exit.
        """
        self.name = name
        self.log_state = log_session_state
        self.logger = logging.getLogger("hrv.debug_context")
        self.start_time: float = 0.0
    
    def __enter__(self) -> "StreamlitDebugContext":
        self.start_time = time.perf_counter()
        self.logger.debug("ENTER | %s", self.name)
        if self.log_state:
            log_session_state(f"entering {self.name}")
        return self
    
    def __exit__(
        self,
        exc_type: type | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> bool:
        elapsed = time.perf_counter() - self.start_time
        if exc_type is not None:
            self.logger.error(
                "EXIT | %s | FAILED after %.3fs | %s: %s",
                self.name, elapsed, exc_type.__name__, exc_val
            )
        else:
            self.logger.debug("EXIT | %s | OK in %.3fs", self.name, elapsed)
        if self.log_state:
            log_session_state(f"exiting {self.name}")
        return False  # Don't suppress exceptions


def get_debug_info() -> dict[str, Any]:
    """
    Collect comprehensive debug information about the current environment.
    
    Returns:
        Dictionary with debug information.
    """
    import platform
    
    info: dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "python_version": sys.version,
        "platform": platform.platform(),
        "cwd": os.getcwd(),
        "log_dir": str(get_log_dir()),
        "logging_initialized": _logging_initialized,
        "streamlit_debug_enabled": _streamlit_debug_enabled,
    }
    
    # Try to get Streamlit version
    try:
        import streamlit as st
        info["streamlit_version"] = st.__version__
    except ImportError:
        info["streamlit_version"] = "not installed"
    
    # Try to get session state size
    try:
        import streamlit as st
        info["session_state_keys"] = len(st.session_state)
    except Exception:
        info["session_state_keys"] = "unavailable"
    
    return info


def dump_debug_report(filepath: Path | None = None) -> Path:
    """
    Write a comprehensive debug report to a file.
    
    Args:
        filepath: Optional path for the report. Defaults to logs/debug_report_TIMESTAMP.txt
    
    Returns:
        Path to the generated report.
    """
    if filepath is None:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filepath = get_log_dir() / f"debug_report_{timestamp}.txt"
    
    info = get_debug_info()
    
    lines = [
        "=" * 80,
        "HRV Analysis Suite - Debug Report",
        f"Generated: {info['timestamp']}",
        "=" * 80,
        "",
        "ENVIRONMENT",
        "-" * 40,
        f"Python: {info['python_version']}",
        f"Platform: {info['platform']}",
        f"Streamlit: {info['streamlit_version']}",
        f"CWD: {info['cwd']}",
        "",
        "LOGGING",
        "-" * 40,
        f"Log directory: {info['log_dir']}",
        f"Logging initialized: {info['logging_initialized']}",
        f"Streamlit debug: {info['streamlit_debug_enabled']}",
        "",
        "SESSION",
        "-" * 40,
        f"Session state keys: {info['session_state_keys']}",
        "",
    ]
    
    # Add recent errors from error log
    error_log = get_log_dir() / "errors.log"
    if error_log.exists():
        lines.append("RECENT ERRORS (last 50 lines)")
        lines.append("-" * 40)
        try:
            with error_log.open("r", encoding="utf-8") as f:
                recent_errors = f.readlines()[-50:]
                lines.extend(line.rstrip() for line in recent_errors)
        except Exception as exc:
            lines.append(f"Failed to read error log: {exc}")
    
    lines.append("")
    lines.append("=" * 80)
    lines.append("END OF REPORT")
    lines.append("=" * 80)
    
    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.write_text("\n".join(lines), encoding="utf-8")
    
    logging.getLogger(__name__).info("Debug report written to: %s", filepath)
    return filepath


# ---------------------------------------------------------------------------
# Internal Helpers
# ---------------------------------------------------------------------------


def _setup_console_only(level: int) -> None:
    """Set up console-only logging as fallback."""
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers.clear()

    suppress_ws_closed = _SuppressAsyncioWebSocketClosed()
    handler = _create_console_handler(
        log_level_console=level,
        fallback_formatter=logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT),
        suppress_ws_closed=suppress_ws_closed,
    )
    root_logger.addHandler(handler)

    if _env_truthy(_ENV_LOG_WARNINGS, default=True):
        logging.captureWarnings(True)
        logging.getLogger("py.warnings").setLevel(logging.WARNING)
    _install_unhandled_exception_hook()


def _env_truthy(name: str, *, default: bool) -> bool:
    """Return True/False from env var values like 1/0, true/false, yes/no."""
    raw = os.environ.get(name)
    if raw is None:
        return default
    value = raw.strip().lower()
    if value in {"1", "true", "yes", "y", "on"}:
        return True
    if value in {"0", "false", "no", "n", "off"}:
        return False
    return default


def _parse_log_level_env(env_var: str, *, default: int) -> int:
    """Parse a logging level from env (e.g., DEBUG, INFO, 10)."""
    raw = os.environ.get(env_var)
    if raw is None:
        return default
    value = raw.strip()
    if not value:
        return default
    upper = value.upper()
    named = logging.getLevelName(upper)
    if isinstance(named, int):
        return named
    try:
        numeric = int(value)
    except ValueError:
        return default
    if numeric < 0 or numeric > 100:
        return default
    return numeric


def _create_console_handler(
    *,
    log_level_console: int,
    fallback_formatter: logging.Formatter,
    suppress_ws_closed: logging.Filter,
) -> logging.Handler:
    """Create the best available console handler (Rich if available/enabled)."""
    use_rich = _env_truthy(_ENV_LOG_RICH, default=False)
    if os.environ.get(_ENV_LOG_RICH) is None:
        # Auto-enable Rich only when stdout is an interactive terminal.
        use_rich = bool(sys.stdout.isatty())

    if use_rich:
        try:
            from rich.console import Console
            from rich.logging import RichHandler

            console = Console(
                file=sys.stdout,
                force_terminal=bool(sys.stdout.isatty()),
                color_system="auto",
                markup=False,
            )
            show_path = _env_truthy(_ENV_LOG_RICH_PATH, default=False)
            handler: logging.Handler = RichHandler(
                console=console,
                show_time=True,
                show_level=True,
                show_path=show_path,
                rich_tracebacks=True,
                tracebacks_show_locals=False,
            )
            handler.setLevel(log_level_console)
            # RichHandler renders its own fields; keep formatter message-focused.
            handler.setFormatter(logging.Formatter("%(name)s:%(lineno)d | %(message)s"))
            handler.addFilter(suppress_ws_closed)
            return handler
        except Exception:
            # Fall back to plain handler on any Rich import/config errors.
            pass

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level_console)
    handler.setFormatter(fallback_formatter)
    handler.addFilter(suppress_ws_closed)
    return handler


def _install_unhandled_exception_hook() -> None:
    """Ensure unhandled exceptions are logged (idempotent)."""
    existing = getattr(sys, "_hrv_prev_excepthook", None)
    if existing is not None:
        return
    sys._hrv_prev_excepthook = sys.excepthook  # type: ignore[attr-defined]

    def _hook(exc_type: type[BaseException], exc: BaseException, tb: Any) -> None:
        logger = logging.getLogger("hrv.unhandled")
        try:
            logger.critical("Unhandled exception", exc_info=(exc_type, exc, tb))
        except Exception:
            # As a last resort, write something to stderr.
            try:
                sys.stderr.write("Unhandled exception (logging failed)\n")
            except Exception:
                pass
        prev = getattr(sys, "_hrv_prev_excepthook", None)
        if callable(prev):
            try:
                prev(exc_type, exc, tb)
            except Exception:
                pass

    sys.excepthook = _hook


# ---------------------------------------------------------------------------
# Auto-setup on import (optional - can be disabled)
# ---------------------------------------------------------------------------

# Uncomment to auto-initialize on import:
# setup_logging()


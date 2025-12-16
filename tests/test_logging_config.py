from __future__ import annotations

import logging

from app.logging_config import _SuppressAsyncioWebSocketClosed


def _make_asyncio_error_record(
    message: str, *, exc_info: tuple[type[BaseException], BaseException, object] | None = None
) -> logging.LogRecord:
    record = logging.LogRecord(
        name="asyncio",
        level=logging.ERROR,
        pathname=__file__,
        lineno=1,
        msg=message,
        args=(),
        exc_info=exc_info,
    )
    return record


def test_suppress_ws_closed_when_excinfo_missing() -> None:
    """The benign Streamlit/Tornado websocket-close race should be suppressed."""
    filt = _SuppressAsyncioWebSocketClosed()
    record = _make_asyncio_error_record(
        "Task exception was never retrieved\nfuture: <Task finished exception=WebSocketClosedError()>"
    )
    assert filt.filter(record) is False


def test_do_not_suppress_other_asyncio_task_errors() -> None:
    """Unrelated asyncio task errors must remain visible."""
    filt = _SuppressAsyncioWebSocketClosed()
    record = _make_asyncio_error_record(
        "Task exception was never retrieved\nfuture: <Task finished exception=RuntimeError()>"
    )
    assert filt.filter(record) is True


def test_suppress_ws_closed_when_excinfo_present() -> None:
    """When exc_info is populated, suppression should be type-driven."""

    class WebSocketClosedError(Exception):
        pass

    exc = WebSocketClosedError("closed")
    filt = _SuppressAsyncioWebSocketClosed()
    record = _make_asyncio_error_record(
        "Task exception was never retrieved",
        exc_info=(WebSocketClosedError, exc, None),
    )
    assert filt.filter(record) is False



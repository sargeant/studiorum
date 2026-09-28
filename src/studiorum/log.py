"""Logging: stdlib loggers writing one line per event to stderr.

``setup_logging`` gives the root logger the only handler, as JSON (one object
per line) or text, and routes FastMCP's and uvicorn's loggers through it.
Extra fields passed with ``extra={...}`` appear as JSON keys or ``key=value``.
With STUDIORUM_TELEMETRY=true and LOGFIRE_TOKEN set, records also go to Logfire.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import UTC, datetime
from typing import Any, Literal, TextIO

LogFormat = Literal["auto", "text", "json"]

# Attributes every LogRecord has; anything else came from extra={...}.
# uvicorn adds color_message, its message with ANSI colours.
_RECORD_ATTRS = set(logging.makeLogRecord({}).__dict__) | {
    "message",
    "asctime",
    "color_message",
}

# Loggers that keep their own handlers unless routed to the root
_ROUTED = ("fastmcp", "uvicorn", "uvicorn.error", "uvicorn.access")

# Chatty at INFO: the MCP SDK logs every request it dispatches, httpx every request
_QUIET = (
    "mcp.server.lowlevel.server",
    "mcp.server.streamable_http",
    "mcp.server.streamable_http_manager",
    "httpx",
)


def _extras(record: logging.LogRecord) -> dict[str, Any]:
    return {k: v for k, v in record.__dict__.items() if k not in _RECORD_ATTRS}


class JsonFormatter(logging.Formatter):
    """One JSON object per record; a traceback is a string field."""

    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, UTC).isoformat(
                timespec="milliseconds"
            ),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            **_extras(record),
        }
        if record.exc_info:
            entry["exc"] = self.formatException(record.exc_info)
        return json.dumps(entry, default=str, ensure_ascii=False)


class TextFormatter(logging.Formatter):
    """``HH:MM:SS LEVEL logger: message key=value``, then any traceback."""

    def __init__(self) -> None:
        super().__init__(
            "%(asctime)s %(levelname)-7s %(name)s: %(message)s", "%H:%M:%S"
        )

    def format(self, record: logging.LogRecord) -> str:
        line = super().format(record)
        extras = " ".join(f"{k}={v}" for k, v in _extras(record).items())
        if not extras:
            return line
        head, sep, tail = line.partition("\n")
        return f"{head} {extras}{sep}{tail}"


class _StderrHandler(logging.StreamHandler[TextIO]):
    """The handler setup_logging installs, so a second call can replace it."""


def logfire_handler_type() -> type[logging.Handler]:
    from logfire import LogfireLoggingHandler

    return LogfireLoggingHandler


def setup_logging(level: str = "WARNING", log_format: LogFormat = "auto") -> None:
    """Send every record at ``level`` or above to stderr in one format.

    ``auto`` is JSON unless stderr is a terminal. Calling it again replaces its
    handlers and leaves others (pytest's, say) in place.
    """
    use_json = log_format == "json" or (
        log_format == "auto" and not sys.stderr.isatty()
    )
    handler = _StderrHandler(sys.stderr)
    handler.setFormatter(JsonFormatter() if use_json else TextFormatter())

    root = logging.getLogger()
    for existing in root.handlers[:]:
        if isinstance(existing, _StderrHandler | logfire_handler_type()):
            root.removeHandler(existing)
    root.addHandler(handler)
    root.setLevel(level.upper())

    route_libraries()

    if os.getenv("STUDIORUM_TELEMETRY", "").lower() == "true" and os.getenv(
        "LOGFIRE_TOKEN"
    ):
        import logfire

        logfire.configure(console=False, send_to_logfire=True)
        root.addHandler(logfire_handler_type()())


def route_libraries() -> None:
    """Send FastMCP's and uvicorn's records through the root handler.

    FastMCP installs its own handler when first imported, so a command that
    imports it after ``setup_logging`` calls this again.
    """
    for name in _ROUTED:
        logger = logging.getLogger(name)
        logger.handlers.clear()
        logger.propagate = True
        logger.setLevel(logging.NOTSET)
    for name in _QUIET:
        logging.getLogger(name).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """The stdlib logger for a module, usually ``get_logger(__name__)``."""
    return logging.getLogger(name)

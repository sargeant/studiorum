"""setup_logging: one handler on the root, one line per record."""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator

import pytest

from studiorum.log import JsonFormatter, TextFormatter, get_logger, setup_logging


@pytest.fixture(autouse=True)
def restore_logging() -> Iterator[None]:
    root = logging.getLogger()
    handlers, level = root.handlers[:], root.level
    yield
    root.handlers = handlers
    root.setLevel(level)


def _record(msg: str, **extra: object) -> logging.LogRecord:
    record = logging.makeLogRecord(
        {"name": "studiorum.x", "levelname": "INFO", "msg": msg}
    )
    record.__dict__.update(extra)
    return record


def test_setup_replaces_the_root_handlers() -> None:
    setup_logging("INFO", "json")
    setup_logging("DEBUG", "text")

    root = logging.getLogger()
    ours = [
        h
        for h in root.handlers
        if isinstance(h.formatter, JsonFormatter | TextFormatter)
    ]
    assert len(ours) == 1
    assert isinstance(ours[0].formatter, TextFormatter)
    assert root.level == logging.DEBUG


def test_auto_is_json_when_stderr_is_not_a_terminal() -> None:
    setup_logging("INFO", "auto")

    formatters = [h.formatter for h in logging.getLogger().handlers]
    assert any(isinstance(f, JsonFormatter) for f in formatters)


def test_fastmcp_and_uvicorn_log_through_the_root() -> None:
    logging.getLogger("fastmcp").addHandler(logging.NullHandler())
    logging.getLogger("fastmcp").propagate = False

    setup_logging("INFO", "json")

    for name in ("fastmcp", "uvicorn", "uvicorn.access"):
        assert logging.getLogger(name).handlers == []
        assert logging.getLogger(name).propagate


def test_json_is_one_line_with_extras_and_the_traceback() -> None:
    try:
        raise ValueError("bad")
    except ValueError:
        import sys

        record = _record("tools/call get_content", tool="get_content", duration_ms=1.5)
        record.exc_info = sys.exc_info()

    line = JsonFormatter().format(record)
    entry = json.loads(line)

    assert "\n" not in line
    assert entry["msg"] == "tools/call get_content"
    assert entry["logger"] == "studiorum.x"
    assert entry["tool"] == "get_content"
    assert entry["duration_ms"] == 1.5
    assert "ValueError: bad" in entry["exc"]


def test_text_puts_extras_after_the_message() -> None:
    line = TextFormatter().format(_record("tools/call", status="ok"))

    assert line.endswith("INFO    studiorum.x: tools/call status=ok")


def test_get_logger_is_the_stdlib_logger() -> None:
    assert get_logger("studiorum.y") is logging.getLogger("studiorum.y")

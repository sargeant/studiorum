"""Unit tests for the centralized logging utilities."""

from __future__ import annotations

import logging
from collections.abc import Generator
from typing import Any
from unittest.mock import patch

import pytest
from logfire import LogfireLoggingHandler

from dnd5e.core.logging.logger import get_logger, setup_logging  # type: ignore


@pytest.fixture(autouse=True)
def reset_logging() -> Generator[None, None, None]:
    """Fixture to reset the logging configuration before and after each test."""
    root_logger = logging.getLogger()
    original_handlers = root_logger.handlers[:]
    original_level = root_logger.level

    # Reset the DND5ELogger state for testing
    from dnd5e.core.logging.logger import DND5ELogger

    original_initialized = DND5ELogger._initialized
    DND5ELogger._initialized = False

    # Clear handlers for the test
    root_logger.handlers.clear()

    yield

    # Restore original state
    root_logger.handlers = original_handlers
    root_logger.setLevel(original_level)
    DND5ELogger._initialized = original_initialized


def test_setup_logging_configures_handler() -> None:
    """Verify that setup_logging adds a Logfire handler to the root logger."""
    root_logger = logging.getLogger()
    # Pytest adds its own handlers, so we clear them here for the test
    root_logger.handlers.clear()
    assert not root_logger.handlers
    setup_logging()
    assert len(root_logger.handlers) == 1
    assert isinstance(root_logger.handlers[0], LogfireLoggingHandler)


def test_setup_logging_sets_level() -> None:
    """Verify that setup_logging sets the correct level on the root logger."""
    logging.getLogger().handlers.clear()
    setup_logging(debug=True)  # debug=True sets DEBUG level
    assert logging.getLogger().level == logging.DEBUG

    # Reset for the next test
    from dnd5e.core.logging.logger import DND5ELogger

    DND5ELogger._initialized = False
    logging.getLogger().handlers.clear()

    setup_logging(debug=False)  # debug=False sets INFO level
    assert logging.getLogger().level == logging.INFO


def test_setup_logging_is_idempotent() -> None:
    """Verify that calling setup_logging multiple times doesn't add more handlers."""
    logging.getLogger().handlers.clear()
    setup_logging()
    assert len(logging.getLogger().handlers) == 1
    setup_logging()
    assert len(logging.getLogger().handlers) == 1


def test_get_logger_returns_logger_instance() -> None:
    """Verify that get_logger returns a Logfire logger instance."""
    import logfire

    logger: Any = get_logger("test_logger")
    # get_logger now returns the logfire module itself, which provides logging methods
    assert logger is logfire


def test_setup_logging_uses_logfire_handler() -> None:
    """Verify that the handler is a LogfireLoggingHandler."""
    logging.getLogger().handlers.clear()
    setup_logging()
    handler = logging.getLogger().handlers[0]
    assert isinstance(handler, LogfireLoggingHandler)

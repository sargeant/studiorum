"""Unit tests for the centralized logging utilities."""

from __future__ import annotations

import logging
from unittest.mock import patch

import colorlog
import pytest

from dnd5e.core.logging.logger import get_logger, setup_logging


@pytest.fixture(autouse=True)
def reset_logging():
    """Fixture to reset the logging configuration before and after each test."""
    root_logger = logging.getLogger()
    original_handlers = root_logger.handlers[:]
    original_level = root_logger.level

    # Clear handlers for the test
    root_logger.handlers.clear()

    yield

    # Restore original handlers and level
    root_logger.handlers = original_handlers
    root_logger.setLevel(original_level)


def test_setup_logging_configures_handler():
    """Verify that setup_logging adds a handler to the root logger."""
    root_logger = logging.getLogger()
    # Pytest adds its own handlers, so we clear them here for the test
    root_logger.handlers.clear()
    assert not root_logger.handlers
    setup_logging()
    assert len(root_logger.handlers) == 1
    assert isinstance(root_logger.handlers[0], colorlog.StreamHandler)


def test_setup_logging_sets_level():
    """Verify that setup_logging sets the correct level on the root logger."""
    logging.getLogger().handlers.clear()
    setup_logging(level="DEBUG")
    assert logging.getLogger().level == logging.DEBUG
    logging.getLogger().handlers.clear()
    setup_logging(level="INFO")
    assert logging.getLogger().level == logging.INFO


def test_setup_logging_is_idempotent():
    """Verify that calling setup_logging multiple times doesn't add more handlers."""
    logging.getLogger().handlers.clear()
    setup_logging()
    assert len(logging.getLogger().handlers) == 1
    setup_logging()
    assert len(logging.getLogger().handlers) == 1


def test_get_logger_returns_logger_instance():
    """Verify that get_logger returns a Logger instance."""
    logger = get_logger("test_logger")
    assert isinstance(logger, logging.Logger)
    assert logger.name == "test_logger"


@patch("colorlog.StreamHandler")
def test_setup_logging_uses_colorlog_formatter(mock_stream_handler):
    """Verify that the handler is configured with a ColoredFormatter."""
    logging.getLogger().handlers.clear()
    setup_logging()
    handler_instance = mock_stream_handler.return_value
    assert handler_instance.setFormatter.called
    formatter = handler_instance.setFormatter.call_args[0][0]
    assert isinstance(formatter, colorlog.ColoredFormatter)

"""
This module provides a centralized and structured logging setup for the application.

It ensures that all parts of the application use a consistent logging format
and configuration. The setup is based on the standard `logging` module
and uses `colorlog` for colored output in development environments.

Key functions:
- setup_logging: Configures the root logger. This should be called once at application startup.
- get_logger: Retrieves a logger instance for a specific module.

Example usage in a module:
```
from dnd5e.core.logging import get_logger

logger = get_logger(__name__)

logger.info("This is an informational message.")
logger.warning("This is a warning message.")
```

The logging level can be configured via the `LOG_LEVEL` environment variable.
"""

from __future__ import annotations

import logging

import colorlog


def setup_logging(level: str = "WARNING") -> None:
    """
    Configure the root logger for the application.

    This function sets up a handler with a colored formatter. It should be
    called once when the application starts.

    Args:
        level (str): The minimum logging level to output (e.g., "INFO", "DEBUG").
    """
    root_logger = logging.getLogger()
    if root_logger.handlers:
        # Logger is already configured
        return

    handler = colorlog.StreamHandler()
    formatter = colorlog.ColoredFormatter(
        "%(log_color)s%(levelname)-8s%(reset)s %(blue)s%(name)s%(reset)s: %(message)s",
        log_colors={
            "DEBUG": "cyan",
            "INFO": "green",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "red,bg_white",
        },
    )
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)
    root_logger.setLevel(level.upper())


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a specific module.

    This is a convenience function that simply calls `logging.getLogger`.
    It's intended to be the single point of entry for obtaining loggers
    throughout the application.

    Args:
        name (str): The name of the logger, typically `__name__`.

    Returns:
        logging.Logger: A logger instance.
    """
    return logging.getLogger(name)

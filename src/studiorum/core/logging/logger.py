"""
Unified logging interface using Pydantic Logfire.

This module provides a single point of entry for all logging throughout
the Studiorum application, using Logfire for structured observability.
"""

from __future__ import annotations

import os
import sys
from typing import Any

import logfire
from logfire import LogfireLoggingHandler


class StudiorumLogger:
    """Wrapper for Logfire that provides Studiorum-specific configuration."""

    _initialized = False
    _debug_mode = False

    @classmethod
    def initialize(
        cls,
        debug: bool = False,
        environment: str = "local",
        console_min_level: str = "info",
        enable_telemetry: bool = False,
    ) -> None:
        """Initialize Logfire with Studiorum-specific configuration."""
        if cls._initialized:
            return

        cls._debug_mode = debug

        # Configure Logfire with token from environment
        logfire_token = os.getenv("LOGFIRE_TOKEN")

        # Only send to Logfire if we have a token and telemetry is enabled
        send_to_logfire = enable_telemetry and logfire_token is not None

        if enable_telemetry and not logfire_token:
            import warnings

            warnings.warn(
                "Logfire telemetry enabled but LOGFIRE_TOKEN not set. "
                "Set LOGFIRE_TOKEN environment variable or disable telemetry.",
                UserWarning,
                stacklevel=2,
            )

        # Debug the send_to_logfire logic
        if debug:
            print(f"🐛 DEBUG: enable_telemetry={enable_telemetry}", file=sys.stderr)
            print(
                f"🐛 DEBUG: logfire_token present={logfire_token is not None}",
                file=sys.stderr,
            )
            print(f"🐛 DEBUG: send_to_logfire={send_to_logfire}", file=sys.stderr)

        # Configure Logfire
        logfire.configure(
            token=logfire_token,  # Pass token explicitly
            environment=environment,
            console=logfire.ConsoleOptions(
                min_log_level=console_min_level,  # type: ignore[arg-type]
                include_timestamps=True,
                colors="auto" if sys.stderr.isatty() else "never",
                # stdout carries command output, and MCP's stdio protocol
                output=sys.stderr,
            ),
            send_to_logfire=send_to_logfire,
        )

        # Enable Python standard library logging integration
        import logging

        logging.basicConfig(
            handlers=[LogfireLoggingHandler()],
            level=logging.DEBUG if debug else logging.INFO,
            format="%(message)s",  # Logfire handles formatting
        )

        # Instrument key libraries (optional)
        if enable_telemetry:
            try:
                logfire.instrument_httpx()
            except Exception as e:
                if debug:
                    print(
                        f"🐛 DEBUG: httpx instrumentation skipped: {e}", file=sys.stderr
                    )

            try:
                logfire.instrument_requests()
            except Exception as e:
                if debug:
                    print(
                        f"🐛 DEBUG: requests instrumentation skipped: {e}",
                        file=sys.stderr,
                    )

            try:
                logfire.instrument_system_metrics()
            except Exception as e:
                if debug:
                    print(
                        f"🐛 DEBUG: system metrics instrumentation skipped: {e}",
                        file=sys.stderr,
                    )

        cls._initialized = True
        logfire.debug(
            "Studiorum logging initialized", debug=debug, environment=environment
        )


def get_logger(name: str) -> Any:
    """
    Get a Logfire logger instance for a specific module.

    This replaces the standard logging.getLogger() throughout the application.
    Returns a Logfire logger that provides structured logging capabilities.

    Args:
        name (str): The name of the logger, typically `__name__`.

    Returns:
        logfire logger: A Logfire logger instance with structured logging.
    """
    # Ensure Logfire is initialized with sensible defaults
    if not StudiorumLogger._initialized:
        debug = os.getenv("STUDIORUM_DEBUG", "false").lower() == "true"
        environment = os.getenv("STUDIORUM_ENVIRONMENT", "local")

        # Check for telemetry environment variables
        enable_telemetry = (
            os.getenv("STUDIORUM_TELEMETRY", "false").lower() == "true"
            or os.getenv("STUDIORUM_OBSERVABILITY", "false").lower() == "true"
        )

        StudiorumLogger.initialize(
            debug=debug, environment=environment, enable_telemetry=enable_telemetry
        )

    # Return Logfire's logger - it handles module naming internally
    return logfire


def setup_logging(
    debug: bool = False,
    environment: str = "local",
    enable_telemetry: bool = False,
    console_min_level: str = "info",
    **kwargs: Any,
) -> None:
    """
    Set up logging for the Studiorum application.

    This is the main entry point for configuring logging across the application.
    """
    StudiorumLogger.initialize(
        debug=debug,
        environment=environment,
        enable_telemetry=enable_telemetry,
        console_min_level=console_min_level,
        **kwargs,
    )

"""
Unified logging interface using Pydantic Logfire.

This module provides a single point of entry for all logging throughout
the dnd5e application, using Logfire for structured observability.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from .mcp_debug import MCPDebugLogger

import logfire
from logfire import LogfireLoggingHandler


class DND5ELogger:
    """Wrapper for Logfire that provides dnd5e-specific configuration."""

    _initialized = False
    _debug_mode = False
    _mcp_debug_logger: MCPDebugLogger | None = None

    @classmethod
    def initialize(
        cls,
        debug: bool = False,
        environment: str = "local",
        console_min_level: str = "info",
        enable_telemetry: bool = False,
        mcp_debug: bool = False,
        mcp_debug_file: Path | None = None,
    ) -> None:
        """Initialize Logfire with dnd5e-specific configuration."""
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

        # Configure Logfire
        logfire.configure(
            token=logfire_token,  # Pass token explicitly
            environment=environment,
            console=logfire.ConsoleOptions(
                min_log_level=console_min_level,  # type: ignore[arg-type]
                include_timestamps=True,
                colors="auto" if sys.stderr.isatty() else "never",
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

        # Initialize MCP debug logging if requested
        if mcp_debug:
            from .mcp_debug import MCPDebugLogger

            cls._mcp_debug_logger = MCPDebugLogger(
                log_file=mcp_debug_file or cls._default_mcp_debug_file(),
                enable_logfire=True,
            )

        # Instrument key libraries
        if enable_telemetry:
            logfire.instrument_httpx()
            logfire.instrument_requests()
            logfire.instrument_system_metrics()

        cls._initialized = True
        logfire.info("dnd5e logging initialized", debug=debug, environment=environment)

    @classmethod
    def get_mcp_debug_logger(cls) -> MCPDebugLogger | None:
        """Get the MCP debug logger if available."""
        return cls._mcp_debug_logger

    @staticmethod
    def _default_mcp_debug_file() -> Path:
        """Get default MCP debug log file location."""
        import tempfile

        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")

        # Try ~/.dnd5e/logs/ first
        home_logs = Path.home() / ".dnd5e" / "logs"
        try:
            home_logs.mkdir(parents=True, exist_ok=True)
            return home_logs / f"mcp-debug-{timestamp}.log"
        except (OSError, PermissionError):
            # Secure fallback using system temp directory
            temp_dir = Path(tempfile.gettempdir())
            return temp_dir / f"dnd5e-mcp-debug-{timestamp}.log"


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
    if not DND5ELogger._initialized:
        debug = os.getenv("DND5E_DEBUG", "false").lower() == "true"
        environment = os.getenv("DND5E_ENVIRONMENT", "local")
        DND5ELogger.initialize(debug=debug, environment=environment)

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
    Set up logging for the dnd5e application.

    This is the main entry point for configuring logging across the application.
    """
    DND5ELogger.initialize(
        debug=debug,
        environment=environment,
        enable_telemetry=enable_telemetry,
        console_min_level=console_min_level,
        **kwargs,
    )

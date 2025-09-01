"""
MCP-specific debug logging implementation using Logfire.

Implements the debug logging architecture from private/mcp-impl/extra-logging.md
while leveraging Logfire's structured logging capabilities.
"""

from __future__ import annotations

import json
import time
from contextlib import contextmanager
from datetime import datetime
from logging import FileHandler
from pathlib import Path
from typing import Any, Optional, Union

import logfire
from logfire import LogfireLoggingHandler


class MCPDebugLogger:
    """
    Enhanced MCP debug logger implementing extra-logging.md plan with Logfire.

    Provides comprehensive debugging for MCP stdio transport including:
    - Protocol message logging
    - Tool execution tracking
    - Performance metrics
    - Error context capture
    """

    def __init__(
        self,
        log_file: Path,
        log_protocol: bool = False,
        level: str = "INFO",
        enable_logfire: bool = True,
    ):
        self.log_file = log_file
        self.log_protocol = log_protocol
        self.level = level
        self.enable_logfire = enable_logfire
        self._file_handler: FileHandler | None = None

        # Ensure log directory exists
        log_file.parent.mkdir(parents=True, exist_ok=True)

        # Set up file logging
        self._setup_file_logging()

        # Create Logfire logger with MCP context
        self.logger = logfire

        logfire.info(
            "MCP Debug Logger initialized",
            log_file=str(log_file),
            log_protocol=log_protocol,
            level=level,
        )

    def _setup_file_logging(self) -> None:
        """Set up file-based logging for MCP debug output."""
        import logging

        # Create file handler for detailed MCP logs
        self._file_handler = logging.FileHandler(self.log_file)
        self._file_handler.setLevel(getattr(logging, self.level))

        # Use structured format for file logs
        formatter = logging.Formatter(
            "[%(asctime)s.%(msecs)03d] [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        self._file_handler.setFormatter(formatter)

        # Add to root logger
        root_logger = logging.getLogger()
        root_logger.addHandler(self._file_handler)

    def log_startup(self, tools_count: int, config_summary: dict[str, Any]) -> None:
        """Log MCP server startup information."""
        with logfire.span("MCP Server Startup") as span:
            span.set_attributes(
                {
                    "mcp.tools.count": tools_count,
                    "mcp.config.summary": json.dumps(config_summary),
                    "mcp.transport": "stdio",
                }
            )

            logfire.info(
                "MCP Server starting with stdio transport",
                tools_count=tools_count,
                config_summary=config_summary,
                _tags=["mcp", "startup"],
            )

    def log_protocol_message(
        self,
        direction: str,
        message: dict[str, Any],
        timestamp: datetime | None = None,
    ) -> None:
        """Log JSON-RPC protocol messages if enabled."""
        if not self.log_protocol:
            return

        timestamp = timestamp or datetime.now()
        message_str = json.dumps(message, default=str)

        # Log to file in the specified format
        if self._file_handler:
            import logging

            file_logger = logging.getLogger("mcp.protocol")
            file_logger.info(f"[PROTOCOL] {direction}: {message_str}")

        # Log to Logfire with structured data
        logfire.debug(
            "MCP Protocol message: {direction} {method}",
            direction=direction,
            method=message.get("method", "response"),
            message_id=message.get("id"),
            message_size=len(message_str),
            protocol_version=message.get("jsonrpc", "2.0"),
            _tags=["mcp", "protocol"],
        )

    @contextmanager
    def log_tool_execution(self, tool_name: str, args: dict[str, Any]) -> Any:
        """Context manager for logging tool execution with timing."""
        start_time = time.perf_counter()

        with logfire.span(
            "MCP Tool: {tool_name}",
            tool_name=tool_name,
        ) as span:
            # Set initial attributes
            span.set_attributes(
                {
                    "mcp.tool.name": tool_name,
                    "mcp.tool.args_count": len(args),
                    "mcp.tool.args_keys": list(args.keys()),
                }
            )

            # Log tool start to file
            if self._file_handler:
                import logging

                file_logger = logging.getLogger("mcp.tool")
                file_logger.info(
                    f"[TOOL] Executing: {tool_name}({self._format_args(args)})"
                )

            try:
                # Yield control back to tool execution
                yield span

                # Tool completed successfully
                duration = time.perf_counter() - start_time
                span.set_attributes(
                    {
                        "mcp.tool.duration_ms": duration * 1000,
                        "mcp.tool.success": True,
                    }
                )

                logfire.info(
                    "MCP tool completed: {tool_name}",
                    tool_name=tool_name,
                    duration_ms=duration * 1000,
                    _tags=["mcp", "tool", "success"],
                )

            except Exception as e:
                # Tool failed
                duration = time.perf_counter() - start_time
                span.set_attributes(
                    {
                        "mcp.tool.duration_ms": duration * 1000,
                        "mcp.tool.success": False,
                        "mcp.tool.error_type": type(e).__name__,
                    }
                )

                self.log_error(e, f"Tool execution: {tool_name}")
                raise

    def log_tool_result(self, tool_name: str, result: Any, span: Any) -> None:
        """Log tool execution results."""
        try:
            # Determine result characteristics
            result_info = self._analyze_result(result)
            span.set_attributes(result_info)

            # Log to file
            if self._file_handler:
                import logging

                file_logger = logging.getLogger("mcp.tool")
                result_summary = result_info.get("summary", "completed")
                file_logger.info(f"[TOOL] Result: {result_summary}")

        except Exception as e:
            logfire.warning(
                "Failed to log tool result",
                tool_name=tool_name,
                error=str(e),
                _tags=["mcp", "logging", "error"],
            )

    def log_error(self, error: Exception, context: str) -> None:
        """Log errors with full context and stack traces."""
        logfire.error(
            "MCP Error in {context}: {error}",
            context=context,
            error=str(error),
            error_type=type(error).__name__,
            exc_info=error,
            _tags=["mcp", "error"],
        )

        # Also log to file
        if self._file_handler:
            import logging

            file_logger = logging.getLogger("mcp.error")
            file_logger.exception(f"[ERROR] {context}: {error}")

    def log_performance_metric(
        self,
        metric_name: str,
        value: int | float,
        unit: str = "",
        tags: dict[str, str] | None = None,
    ) -> None:
        """Log performance metrics."""
        # Build performance message with optional tags
        performance_tags = ["mcp", "performance"]
        if tags:
            # Add tag values to the performance_tags list
            performance_tags.extend([f"{k}:{v}" for k, v in tags.items()])

        logfire.info(
            "MCP Performance: {metric_name} = {value}{unit}",
            metric_name=metric_name,
            value=value,
            unit=unit,
            _tags=performance_tags,
        )

    def _format_args(self, args: dict[str, Any]) -> str:
        """Format arguments for logging (truncated)."""
        if not args:
            return ""

        formatted = []
        for key, value in args.items():
            value_str = str(value)
            if len(value_str) > 50:
                value_str = value_str[:47] + "..."
            formatted.append(f"{key}={value_str}")

        return ", ".join(formatted)

    def _analyze_result(self, result: Any) -> dict[str, Any]:
        """Analyze tool result for logging."""
        info = {}

        if result is None:
            info["summary"] = "None"
        elif isinstance(result, list | tuple):
            info["mcp.result.type"] = "list"
            info["mcp.result.count"] = str(len(result))
            info["summary"] = f"Found {len(result)} items"
        elif isinstance(result, dict):
            info["mcp.result.type"] = "dict"
            info["mcp.result.keys"] = str(list(result.keys()))
            if "content" in result and isinstance(result["content"], list):
                info["mcp.result.count"] = str(len(result["content"]))
                info["summary"] = f"Found {len(result['content'])} items"
            else:
                info["summary"] = "Dictionary result"
        elif isinstance(result, str):
            info["mcp.result.type"] = "string"
            info["mcp.result.length"] = str(len(result))
            info["summary"] = f"String result ({len(result)} chars)"
        else:
            info["mcp.result.type"] = type(result).__name__
            info["summary"] = f"{type(result).__name__} result"

        return info

    def cleanup(self) -> None:
        """Clean up resources."""
        if self._file_handler:
            import logging

            root_logger = logging.getLogger()
            root_logger.removeHandler(self._file_handler)
            self._file_handler.close()


class ProtocolDebugWrapper:
    """
    Wraps MCP protocol communication to capture messages for debugging.

    This implements the protocol message interceptor from extra-logging.md
    without interfering with the JSON-RPC protocol.
    """

    def __init__(self, debug_logger: MCPDebugLogger):
        self.debug_logger = debug_logger
        self._message_count = 0

    async def intercept_outbound(self, message: dict[str, Any]) -> dict[str, Any]:
        """Intercept outbound messages (to stdout)."""
        self._message_count += 1

        if self.debug_logger.log_protocol:
            self.debug_logger.log_protocol_message("→ STDOUT", message)

        return message

    async def intercept_inbound(self, message: dict[str, Any]) -> dict[str, Any]:
        """Intercept inbound messages (from stdin)."""
        self._message_count += 1

        if self.debug_logger.log_protocol:
            self.debug_logger.log_protocol_message("← STDIN", message)

        return message

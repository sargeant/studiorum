"""MCP server commands for the studiorum CLI.

This module provides MCP server commands that start the FastMCP server
with D&D 5e content tools and configuration capabilities.

Available Commands:
- 'mcp serve' - HTTP server for web-based MCP clients
- 'mcp run' - stdio transport server for Claude Desktop integration
- 'mcp tools' - list all available MCP tools
- 'mcp test' - test connection to an MCP server

Key Features:
- FastMCP server startup with multiple transport options
- Integration with existing CLI infrastructure
- Performance monitoring and logging
- Graceful shutdown handling
- Claude Desktop compatibility via stdio transport
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import sys
from pathlib import Path
from typing import Any, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from studiorum.core.logging import StudiorumLogger, get_logger

from ...core.config.unified_config import get_app_config
from ...mcp.server import create_mcp_server, get_mcp_app, list_registered_tools

logger = get_logger(__name__)
console = Console()

# Create the MCP command group
mcp_app = typer.Typer(
    name="mcp",
    help="MCP (Model Context Protocol) server commands",
    no_args_is_help=True,
)


@mcp_app.command(name="serve")
def serve_mcp(
    host: str = typer.Option(
        "localhost", "--host", "-h", help="Host to bind the MCP server to"
    ),
    port: int = typer.Option(
        8080, "--port", "-p", help="Port to bind the MCP server to"
    ),
    config_file: str | None = typer.Option(
        None, "--config", "-c", help="Path to configuration file"
    ),
    log_level: str = typer.Option(
        "INFO", "--log-level", "-l", help="Logging level (DEBUG, INFO, WARNING, ERROR)"
    ),
    enable_cors: bool = typer.Option(
        True, "--enable-cors/--disable-cors", help="Enable CORS for web clients"
    ),
    enable_metrics: bool = typer.Option(
        True,
        "--enable-metrics/--disable-metrics",
        help="Enable performance metrics collection",
    ),
    reload: bool = typer.Option(
        False, "--reload", help="Enable auto-reload for development"
    ),
) -> None:
    """Start the studiorum MCP server.

    The MCP server provides D&D 5e content search and configuration tools
    through the Model Context Protocol, enabling LLMs to access structured
    D&D data with natural language interfaces.

    Examples:
        # Start server on default port
        studiorum mcp serve

        # Start on specific host and port
        studiorum mcp serve --host 0.0.0.0 --port 9000

        # Start with custom configuration
        studiorum mcp serve --config custom-config.yaml

        # Start in development mode with auto-reload
        studiorum mcp serve --reload --log-level DEBUG
    """
    # Configure logging
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        console.print(f"[red]Invalid log level: {log_level}[/red]")
        raise typer.Exit(1)

    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Load configuration
    try:
        if config_file:
            # TODO: Implement custom config file loading
            console.print(
                "[yellow]Note: Custom config file support not yet implemented[/yellow]"
            )

        config = get_app_config()
        mcp_config = config.mcp

        # Override with CLI parameters
        actual_host = host
        actual_port = port

        # Validate configuration
        if not mcp_config:
            console.print("[red]MCP configuration not found in config[/red]")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"[red]Failed to load configuration: {e}[/red]")
        raise typer.Exit(1)

    # Display startup information
    console.print()
    console.print(
        Panel.fit(
            Text("🎲 Studiorum MCP Server", style="bold blue", justify="center"),
            border_style="blue",
        )
    )
    console.print()

    # Show configuration
    console.print("[bold]Server Configuration:[/bold]")
    console.print(f"  Host: {actual_host}")
    console.print(f"  Port: {actual_port}")
    console.print(f"  Log Level: {log_level}")
    console.print(f"  CORS Enabled: {enable_cors}")
    console.print(f"  Metrics Enabled: {enable_metrics}")
    console.print(f"  Auto-reload: {reload}")
    console.print()

    # Show registered tools
    tools = list_registered_tools()
    console.print(f"[bold]Registered Tools ({len(tools)}):[/bold]")
    for tool in sorted(tools):
        console.print(f"  • {tool}")
    console.print()

    # Start the server
    try:
        asyncio.run(
            _run_server(actual_host, actual_port, enable_cors, enable_metrics, reload)
        )
    except KeyboardInterrupt:
        console.print("\n[yellow]Server stopped by user[/yellow]")
    except Exception as e:
        console.print(f"[red]Server failed to start: {e}[/red]")
        logger.exception("Server startup failed")
        raise typer.Exit(1)


@mcp_app.command(name="tools")
def list_tools() -> None:
    """List all available MCP tools.

    Shows the complete list of tools registered with the studiorum MCP server,
    including content search tools and configuration tools.
    """
    console.print()
    console.print(
        Panel.fit(
            Text("🛠️  Available MCP Tools", style="bold green", justify="center"),
            border_style="green",
        )
    )
    console.print()

    tools = list_registered_tools()

    if not tools:
        console.print("[yellow]No tools registered[/yellow]")
        return

    # Group tools by category
    config_tools = [t for t in tools if "config" in t or "preference" in t]
    search_tools = [t for t in tools if "search" in t or "list" in t or "resolve" in t]
    other_tools = [t for t in tools if t not in config_tools and t not in search_tools]

    if config_tools:
        console.print("[bold]Configuration Tools:[/bold]")
        for tool in sorted(config_tools):
            console.print(f"  • {tool}")
        console.print()

    if search_tools:
        console.print("[bold]Content Search Tools:[/bold]")
        for tool in sorted(search_tools):
            console.print(f"  • {tool}")
        console.print()

    if other_tools:
        console.print("[bold]Other Tools:[/bold]")
        for tool in sorted(other_tools):
            console.print(f"  • {tool}")
        console.print()

    console.print(f"[bold]Total: {len(tools)} tools available[/bold]")


@mcp_app.command(name="run")
def run_mcp_stdio(
    # Debug logging options
    debug: bool = typer.Option(
        False, "--debug", help="Enable detailed debug logging for MCP operations"
    ),
    log_protocol: bool = typer.Option(
        False, "--log-protocol", help="Log full JSON-RPC protocol messages (verbose)"
    ),
    debug_log_file: str | None = typer.Option(
        None, "--debug-log-file", help="Custom debug log file location"
    ),
    debug_level: str = typer.Option(
        "INFO",
        "--debug-level",
        help="Debug logging level (DEBUG, INFO, WARNING, ERROR)",
    ),
    # Logfire observability options
    logfire_dev: bool = typer.Option(
        False,
        "--logfire-dev",
        help="Enable Logfire development token (requires LOGFIRE_TOKEN)",
    ),
    observability: bool = typer.Option(
        False, "--observability", help="Enable Logfire observability platform"
    ),
    telemetry: bool = typer.Option(
        False, "--telemetry", help="Enable telemetry and system metrics collection"
    ),
    environment: str = typer.Option(
        "local", "--environment", help="Deployment environment (local, dev, prod)"
    ),
) -> None:
    """Start the studiorum MCP server with stdio transport for Claude Desktop.

    This command starts the MCP server using stdio transport, which is the
    standard protocol for Claude Desktop integration. The server will run
    until terminated and communicate over stdin/stdout.

    This is different from 'serve' which starts an HTTP server - 'run' is
    specifically designed for local client integration like Claude Desktop.

    Examples:
        # Basic MCP server for Claude Desktop
        studiorum mcp run

        # Enable comprehensive debugging
        studiorum mcp run --debug --log-protocol

        # Custom debug log location
        studiorum mcp run --debug --debug-log-file ./mcp-debug.log

        # Enable Logfire observability (requires LOGFIRE_TOKEN)
        studiorum mcp run --observability --environment dev

        # Development mode with full debugging
        studiorum mcp run --logfire-dev --debug --log-protocol --telemetry

    Note: This command is meant to be called by MCP clients (like Claude Desktop)
    rather than run directly by users. The client manages the server lifecycle.

    Environment Variables:
        LOGFIRE_TOKEN: Required for --observability, --telemetry, and --logfire-dev
        STUDIORUM_DEBUG: Set to 'true' to enable debug logging by default
        STUDIORUM_ENVIRONMENT: Default environment name (overridden by --environment)
    """
    # Determine effective debug settings
    effective_debug = debug or os.getenv("STUDIORUM_DEBUG", "false").lower() == "true"
    effective_environment = (
        environment
        if environment != "local"
        else os.getenv("STUDIORUM_ENVIRONMENT", "local")
    )

    # Enable telemetry for Logfire options
    enable_telemetry = observability or telemetry or logfire_dev

    # Check for LOGFIRE_TOKEN if telemetry is enabled
    if enable_telemetry:
        logfire_token = os.getenv("LOGFIRE_TOKEN")
        if not logfire_token:
            # Write warning to stderr (not stdout which is used for MCP protocol)
            import warnings

            warnings.warn(
                "\n⚠️  Logfire observability enabled but LOGFIRE_TOKEN not set.\n"
                "   Set LOGFIRE_TOKEN environment variable to enable cloud logging.\n"
                "   See .env.example for setup instructions.",
                UserWarning,
                stacklevel=2,
            )

    # Initialize enhanced Logfire logging
    StudiorumLogger.initialize(
        debug=effective_debug,
        environment=effective_environment,
        enable_telemetry=enable_telemetry,
        console_min_level="debug" if effective_debug else "info",
        mcp_debug=effective_debug or log_protocol,
        mcp_debug_file=Path(debug_log_file) if debug_log_file else None,
    )

    # Log enhanced startup information
    mcp_debug_logger = StudiorumLogger.get_mcp_debug_logger()
    if effective_debug:
        logger.info(
            "MCP Debug logging enabled",
            debug_file=str(
                mcp_debug_logger.log_file if mcp_debug_logger else "default"
            ),
            log_protocol=log_protocol,
            debug_level=debug_level,
            _tags=["mcp", "debug", "startup"],
        )

    if enable_telemetry:
        logger.info(
            "Logfire observability enabled",
            environment=effective_environment,
            telemetry=telemetry,
            observability=observability,
            logfire_dev=logfire_dev,
            _tags=["logfire", "observability", "startup"],
        )

    # Configure minimal stderr logging (stdout reserved for MCP protocol)
    logging.basicConfig(
        level=logging.WARNING,  # Keep quiet for stdio transport
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stderr,  # Important: log to stderr, not stdout
    )

    try:
        # Load configuration
        config = get_app_config()
        mcp_config = config.mcp

        if not mcp_config:
            logger.error("MCP configuration not found in config")
            sys.exit(1)

        # Log comprehensive startup information to stderr for debugging
        tools_count = len(list_registered_tools())
        logger.info(
            "Starting studiorum MCP server with stdio transport",
            tools_count=tools_count,
            debug_enabled=effective_debug,
            protocol_logging=log_protocol,
            logfire_enabled=enable_telemetry,
            environment=effective_environment,
            _tags=["mcp", "server", "startup"],
        )

        # Log startup details to MCP debug logger if available
        if mcp_debug_logger:
            config_summary = {
                "debug_enabled": effective_debug,
                "protocol_logging": log_protocol,
                "logfire_enabled": enable_telemetry,
                "environment": effective_environment,
                "debug_level": debug_level,
            }
            mcp_debug_logger.log_startup(tools_count, config_summary)

        # Start the server with stdio transport (default)
        # This will block until the client closes the connection
        asyncio.run(_run_stdio_server())

    except KeyboardInterrupt:
        # Quiet exit on interrupt - client handles this
        sys.exit(0)
    except Exception as e:
        logger.error(f"MCP server failed to start: {e}")
        sys.exit(1)


@mcp_app.command(name="test")
def test_connection(
    host: str = typer.Option(
        "localhost", "--host", "-h", help="MCP server host to test"
    ),
    port: int = typer.Option(8080, "--port", "-p", help="MCP server port to test"),
) -> None:
    """Test connection to an MCP server.

    Attempts to connect to the specified MCP server and verify
    that it's responding correctly.
    """
    console.print()
    console.print(f"[bold]Testing connection to {host}:{port}...[/bold]")
    console.print()

    # TODO: Implement actual connection test
    console.print("[yellow]Connection testing not yet implemented[/yellow]")
    console.print("[dim]This command will test MCP server connectivity[/dim]")


async def _run_stdio_server() -> None:
    """Run the FastMCP server with stdio transport.

    This function starts the MCP server using stdio transport, which is
    the standard for Claude Desktop integration. The server communicates
    over stdin/stdout and runs until the client closes the connection.
    """
    try:
        # Create the MCP server
        mcp_server = await create_mcp_server()

        # Log to stderr for debugging (stdout is reserved for MCP protocol)
        logger.info("MCP server created successfully, starting stdio transport")

        # Start the server with stdio transport (default)
        # This blocks until the client closes the connection
        await mcp_server.run_async(transport="stdio")

    except Exception as e:
        logger.error(f"Failed to run stdio server: {e}")
        raise


async def _run_server(
    host: str, port: int, enable_cors: bool, enable_metrics: bool, reload: bool
) -> None:
    """Run the FastMCP server asynchronously.

    Args:
        host: Host to bind to
        port: Port to bind to
        enable_cors: Whether to enable CORS
        enable_metrics: Whether to enable metrics
        reload: Whether to enable auto-reload
    """
    try:
        # Create the MCP server
        mcp_server = await create_mcp_server()

        console.print("[green]✓[/green] MCP server created successfully")
        console.print(f"[bold]Starting server on {host}:{port}...[/bold]")
        console.print()
        console.print("[dim]Press Ctrl+C to stop the server[/dim]")
        console.print()

        # Configure server options
        server_config = {
            "host": host,
            "port": port,
            "log_level": "info" if logger.isEnabledFor(logging.INFO) else "warning",
        }

        if reload:
            server_config["reload"] = True
            console.print("[yellow]Auto-reload enabled for development[/yellow]")

        # Set up graceful shutdown
        shutdown_event = asyncio.Event()

        def signal_handler() -> None:
            console.print(
                "\n[yellow]Received shutdown signal, stopping server...[/yellow]"
            )
            shutdown_event.set()

        # Register signal handlers
        if hasattr(signal, "SIGTERM"):
            signal.signal(signal.SIGTERM, lambda s, f: signal_handler())
        if hasattr(signal, "SIGINT"):
            signal.signal(signal.SIGINT, lambda s, f: signal_handler())

        # Start the server using FastMCP's built-in server
        server_task = asyncio.create_task(
            _start_fastmcp_server(mcp_server, server_config)
        )

        console.print("[green]✓[/green] Server started successfully")
        console.print(f"[bold]MCP server running on {host}:{port}[/bold]")

        # Wait for shutdown signal or server completion
        done, pending = await asyncio.wait(
            [server_task, asyncio.create_task(shutdown_event.wait())],
            return_when=asyncio.FIRST_COMPLETED,
        )

        # Cancel pending tasks
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        # Check if server task completed with error
        if server_task in done:
            try:
                await server_task
            except Exception as e:
                logger.error(f"Server error: {e}")
                raise

        console.print("[green]✓[/green] Server stopped gracefully")

    except Exception as e:
        logger.error(f"Failed to run server: {e}")
        console.print(f"[red]✗[/red] Server failed: {e}")
        raise


async def _start_fastmcp_server(mcp_server: Any, config: dict[str, Any]) -> None:
    """Start the FastMCP server with the given configuration.

    Args:
        mcp_server: FastMCP server instance
        config: Server configuration dictionary
    """
    try:
        # Use FastMCP's native async HTTP server
        # FastMCP provides run_http_async for HTTP transport with JSON-RPC

        host = config["host"]
        port = config["port"]

        console.print(f"[green]✓[/green] Starting FastMCP HTTP server on {host}:{port}")

        # FastMCP server with HTTP transport
        await mcp_server.run_http_async(
            host=host,
            port=port,
            show_banner=False,  # We handle our own banner
        )

    except Exception as e:
        logger.error(f"FastMCP server failed: {e}")
        console.print(f"[red]FastMCP server error: {e}[/red]")
        raise


# Export the MCP app for registration with the main CLI
__all__ = ["mcp_app"]

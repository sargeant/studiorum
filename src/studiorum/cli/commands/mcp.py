"""`studiorum mcp`: run the MCP server, or list its tools."""

from __future__ import annotations

import asyncio
from typing import Annotated

import typer
from rich.console import Console

mcp_app = typer.Typer(
    name="mcp",
    help="MCP (Model Context Protocol) server commands",
    no_args_is_help=True,
)


@mcp_app.command(name="run")
def run(
    transport: Annotated[
        str,
        typer.Option(help="stdio for a local client such as Claude Desktop, or http"),
    ] = "stdio",
    host: Annotated[str, typer.Option(help="HTTP host")] = "127.0.0.1",
    port: Annotated[int, typer.Option(help="HTTP port")] = 8000,
    all_content: Annotated[
        bool,
        typer.Option(
            "--all-content",
            help="Content tools return everything unless a call asks for SRD only",
        ),
    ] = False,
    client_ip_header: Annotated[
        str | None,
        typer.Option(
            envvar="STUDIORUM_TRUSTED_CLIENT_IP_HEADER",
            help="HTTP: log the client address from this header, which the proxy "
            "in front must set (e.g. CF-Connecting-IP), not the TCP peer",
        ),
    ] = None,
) -> None:
    """Run the MCP server. It loads the data before answering the first call."""
    from studiorum.log import route_libraries
    from studiorum.mcp.server import mcp, options, request_log

    route_libraries()
    options.all_content = all_content
    request_log.client_ip_header = client_ip_header

    if transport == "stdio":
        mcp.run(transport="stdio", show_banner=False)
    elif transport == "http":
        mcp.run(
            transport="http",
            host=host,
            port=port,
            show_banner=False,
            # uvicorn logs through the root handler, with no access log: the
            # request log has a line per MCP request
            uvicorn_config={"log_config": None, "access_log": False},
        )
    else:
        raise typer.BadParameter("must be stdio or http", param_hint="--transport")


@mcp_app.command(name="tools")
def tools() -> None:
    """List the tools the server registers."""
    from studiorum.mcp.server import mcp

    console = Console()
    for tool in sorted(asyncio.run(mcp.list_tools()), key=lambda t: t.name):
        summary = (tool.description or "").splitlines()[0]
        console.print(f"[bold]{tool.name}[/bold]  {summary}")

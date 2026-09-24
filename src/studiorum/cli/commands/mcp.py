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
) -> None:
    """Run the MCP server. It loads the data before answering the first call."""
    from studiorum.mcp.server import mcp

    if transport == "stdio":
        mcp.run(transport="stdio", show_banner=False)
    elif transport == "http":
        mcp.run(transport="http", host=host, port=port)
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

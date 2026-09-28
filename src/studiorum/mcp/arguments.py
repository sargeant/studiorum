"""Rejecting a tool call's unknown arguments with the names the tool takes."""

from __future__ import annotations

from typing import Any

import mcp.types as mt
from fastmcp.server.middleware import CallNext, Middleware, MiddlewareContext
from fastmcp.tools import ToolResult

from studiorum.mcp.errors import ClientError


class UnknownArguments(Middleware):
    """A call with an argument the tool doesn't take fails naming the ones it does.

    Without this, pydantic's "Unexpected keyword argument" is all a client sees.
    """

    async def on_call_tool(
        self,
        context: MiddlewareContext[mt.CallToolRequestParams],
        call_next: CallNext[mt.CallToolRequestParams, ToolResult],
    ) -> ToolResult:
        server = context.fastmcp_context
        name = context.message.name
        tool = await server.fastmcp.get_tool(name) if server else None
        if tool is not None:
            known: dict[str, Any] = tool.parameters.get("properties", {})
            unknown = sorted(set(context.message.arguments or {}) - set(known))
            if unknown:
                raise ClientError(
                    f"{name} has no parameter {_names(unknown)}. "
                    f"Its parameters: {', '.join(known)}."
                )
        return await call_next(context)


def _names(names: list[str]) -> str:
    quoted = [f"'{n}'" for n in names]
    return (
        quoted[0] if len(quoted) == 1 else ", ".join(quoted[:-1]) + " or " + quoted[-1]
    )

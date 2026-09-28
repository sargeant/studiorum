"""Turning a tool call's bad arguments into one plain message."""

from __future__ import annotations

from typing import Any

import mcp.types as mt
from fastmcp.server.middleware import CallNext, Middleware, MiddlewareContext
from fastmcp.tools import ToolResult
from pydantic import ValidationError

from studiorum.mcp.errors import ClientError


class UnknownArguments(Middleware):
    """A call with an argument the tool doesn't take fails naming the ones it does.

    Without this, pydantic's "Unexpected keyword argument" is all a client sees.
    An argument out of range or of the wrong type fails with one line per
    argument, in place of pydantic's report with its types and doc links.
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
        try:
            return await call_next(context)
        except ValidationError as e:
            # Only the arguments' validation; a model built in a tool is a bug
            if e.title != f"call[{name}]":
                raise
            raise ClientError(f"Bad arguments to {name}. {_problems(e)}") from None


def _problems(error: ValidationError) -> str:
    """Each argument's problem, as "limit: Input should be ...", one sentence each."""
    lines = []
    for problem in error.errors(include_url=False):
        where = ".".join(str(part) for part in problem["loc"])
        message = (
            "Required" if problem["type"] == "missing_argument" else problem["msg"]
        )
        lines.append(f"{where}: {message}.")
    return " ".join(lines)


def _names(names: list[str]) -> str:
    quoted = [f"'{n}'" for n in names]
    return (
        quoted[0] if len(quoted) == 1 else ", ".join(quoted[:-1]) + " or " + quoted[-1]
    )

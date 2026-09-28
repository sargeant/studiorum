"""Turning a failed lookup into the error a client sees."""

from __future__ import annotations

import logging
from difflib import get_close_matches

from fastmcp.exceptions import ToolError


class ClientError(ToolError):
    """A bad call: the client sees the message, and FastMCP logs it only at DEBUG.

    The request log records it at INFO with the message.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message, log_level=logging.DEBUG)


def not_found(what: str, name: str, candidates: list[str]) -> ClientError:
    """A ToolError naming what wasn't found and the closest names that were."""
    suggestions = get_close_matches(name, sorted(set(candidates)), n=5, cutoff=0.6)
    message = f"No {what} named '{name}'."
    if suggestions:
        message += " Did you mean: " + ", ".join(suggestions) + "?"
    return ClientError(message)

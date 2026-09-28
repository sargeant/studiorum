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
    """A ToolError naming what wasn't found and the closest names that were.

    Names containing ``name`` come first, shortest first, then close spellings.
    """
    unique = sorted(set(candidates))
    needle = name.lower()
    containing = sorted((c for c in unique if needle in c.lower()), key=len)
    close = get_close_matches(name, unique, n=5, cutoff=0.6)
    suggestions = list(dict.fromkeys([*containing, *close]))[:5]
    message = f"No {what} named '{name}'."
    if suggestions:
        message += " Did you mean: " + ", ".join(suggestions) + "?"
    return ClientError(message)

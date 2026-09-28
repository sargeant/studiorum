"""Turning a failed lookup into the error a client sees."""

from __future__ import annotations

import logging
import re
from difflib import get_close_matches

from fastmcp.exceptions import ToolError

from studiorum.mcp.text import fold


class ClientError(ToolError):
    """A bad call: the client sees the message, and FastMCP logs it only at DEBUG.

    The request log records it at INFO with the message.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message, log_level=logging.DEBUG)


def not_found(
    what: str,
    name: str,
    candidates: list[str],
    fallback: list[str] | None = None,
    where: str | None = None,
) -> ClientError:
    """A ToolError naming what wasn't found and the closest names that were.

    Suggestions come from ``candidates``, or ``fallback`` when none of those
    is close. ``where`` names the place searched, e.g. a source.
    """
    found = suggestions(name, candidates) or suggestions(name, fallback or [])
    message = f"No {what} named '{name}'" + (f" in {where}." if where else ".")
    if found:
        message += " Did you mean: " + ", ".join(found) + "?"
    return ClientError(message)


def suggestions(name: str, candidates: list[str], n: int = 5) -> list[str]:
    """The names closest to ``name``.

    Names holding it as a word or at a word's start come first, then those
    holding it mid-word, each shortest first, then close spellings.
    """
    unique = sorted(set(candidates))
    needle = fold(name)
    at_word = re.compile(rf"\b{re.escape(needle)}")
    containing = sorted(
        (c for c in unique if needle in fold(c)),
        key=lambda c: (at_word.search(fold(c)) is None, len(c)),
    )
    close = get_close_matches(name, unique, n=n, cutoff=0.6)
    return list(dict.fromkeys([*containing, *close]))[:n]

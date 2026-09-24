"""Turning a failed lookup into the error a client sees."""

from __future__ import annotations

from difflib import get_close_matches

from fastmcp.exceptions import ToolError


def not_found(what: str, name: str, candidates: list[str]) -> ToolError:
    """A ToolError naming what wasn't found and the closest names that were."""
    suggestions = get_close_matches(name, sorted(set(candidates)), n=5, cutoff=0.6)
    message = f"No {what} named '{name}'."
    if suggestions:
        message += " Did you mean: " + ", ".join(suggestions) + "?"
    return ToolError(message)

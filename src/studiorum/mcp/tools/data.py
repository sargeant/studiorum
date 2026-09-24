"""MCP tool reporting where the data comes from.

The data directories and homebrew are set in the configuration file
(``data.dirs`` and ``data.homebrew``); this tool only reads them.
"""

from __future__ import annotations

from typing import Any, Literal

from studiorum.mcp.context import AsyncRequestContext


async def manage_data_sources(
    action: Literal["list", "status"],
    context: AsyncRequestContext | None = None,
) -> dict[str, Any]:
    """The configured data directories and homebrew, and any problems with them.

    Both actions return the same report. To change the data, edit data.dirs
    and data.homebrew in the configuration file.
    """
    if context is None:
        return {"error": "AsyncRequestContext required for data operations"}
    data = context.services.data
    return {
        "action": action,
        "data_dirs": [
            {"path": str(d.root), "exists": d.root.is_dir()} for d in data.dirs
        ],
        "homebrew": [{"path": str(p), "exists": p.exists()} for p in data.homebrew],
        "files": len(data.files()),
        "problems": data.problems(),
    }

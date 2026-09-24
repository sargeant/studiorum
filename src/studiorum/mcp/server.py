"""The FastMCP server: loads the data once, then serves read-only tools over it."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any

from fastmcp import FastMCP
from fastmcp.server.middleware.logging import LoggingMiddleware
from fastmcp.server.middleware.timing import TimingMiddleware

from studiorum.core.config.unified_config import get_app_config
from studiorum.mcp.tools.encounter import (
    calculate_encounter_budget,
    rate_encounter,
    suggest_creatures,
)
from studiorum.mcp.tools.lookup import get_content, list_publications
from studiorum.mcp.tools.reading import (
    get_table_of_contents,
    read_section,
    search_publication,
)
from studiorum.mcp.tools.rules import search_rules
from studiorum.mcp.tools.search import search_creatures, search_items, search_spells
from studiorum.services import build_services


@dataclass
class ServerOptions:
    """Set by `studiorum mcp run` before the server starts."""

    all_content: bool = False


options = ServerOptions()


@asynccontextmanager
async def lifespan(server: FastMCP[Any]) -> AsyncIterator[dict[str, Any]]:
    services = build_services(get_app_config())
    services.omnidexer  # noqa: B018 - load before the first call, not during it
    yield {"services": services, "srd_only": not options.all_content}


mcp: FastMCP[Any] = FastMCP(
    name="studiorum",
    instructions=(
        "Read-only 5e content from 5etools data. Search tools return summaries; "
        "get_content returns one entry in full. Books and adventures are read "
        "through get_table_of_contents and read_section. Content tools default "
        "to SRD content only (srd_only=true)."
    ),
    lifespan=lifespan,
    # Only ToolError messages reach the client; other exceptions are masked.
    mask_error_details=True,
)
# ErrorHandlingMiddleware is left out: it rewrites ToolError messages.
mcp.add_middleware(LoggingMiddleware())
mcp.add_middleware(TimingMiddleware())

for tool in (
    search_spells,
    search_creatures,
    search_items,
    search_rules,
    get_content,
    list_publications,
    calculate_encounter_budget,
    rate_encounter,
    suggest_creatures,
    get_table_of_contents,
    read_section,
    search_publication,
):
    mcp.tool(tool)

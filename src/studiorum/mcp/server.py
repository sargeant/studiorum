"""The FastMCP server: loads the data once, then serves read-only tools over it."""

from __future__ import annotations

import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any

from fastmcp import FastMCP
from mcp.types import ToolAnnotations
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from studiorum import __version__
from studiorum.config import get_app_config
from studiorum.log import get_logger
from studiorum.mcp.arguments import UnknownArguments
from studiorum.mcp.request_log import RequestLog
from studiorum.mcp.tools.encounter import (
    calculate_encounter_budget,
    rate_encounter,
    suggest_creatures,
)
from studiorum.mcp.tools.lookup import (
    get_content,
    get_contents,
    list_publications,
    search_content,
)
from studiorum.mcp.tools.progression import get_class_progression
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


logger = get_logger(__name__)

READ_ONLY = ToolAnnotations(readOnlyHint=True, idempotentHint=True, openWorldHint=False)


@asynccontextmanager
async def lifespan(server: FastMCP[Any]) -> AsyncIterator[dict[str, Any]]:
    start = time.perf_counter()
    services = build_services(get_app_config())
    services.catalogue  # noqa: B018 - load before the first call, not during it
    logger.info(
        "Catalogue loaded",
        extra={"seconds": round(time.perf_counter() - start, 1)},
    )
    yield {"services": services, "srd_only": not options.all_content}


def instructions(all_content: bool) -> str:
    """What the server tells a client, with the srd_only default it runs with."""
    default = (
        "Content tools return all content unless a call passes srd_only=true."
        if all_content
        else "Content tools default to SRD content only (srd_only=true)."
    )
    return (
        "Read-only 5e content from 5etools data. Search tools return summaries; "
        "get_content returns one entry in full. Books and adventures are read "
        f"through get_table_of_contents and read_section. {default}"
    )


mcp: FastMCP[Any] = FastMCP(
    name="studiorum",
    instructions=instructions(all_content=False),
    lifespan=lifespan,
    # Only ToolError messages reach the client; other exceptions are masked.
    mask_error_details=True,
)
# ErrorHandlingMiddleware is left out: it rewrites ToolError messages.
request_log = RequestLog()
mcp.add_middleware(request_log)
mcp.add_middleware(UnknownArguments())

for tool in (
    search_spells,
    search_creatures,
    search_items,
    search_rules,
    search_content,
    get_content,
    get_contents,
    list_publications,
    get_class_progression,
    calculate_encounter_budget,
    rate_encounter,
    suggest_creatures,
    get_table_of_contents,
    read_section,
    search_publication,
):
    # Every tool reads the loaded data and nothing else
    mcp.tool(tool, annotations=READ_ONLY)


@mcp.custom_route("/healthz", methods=["GET"], include_in_schema=False)
async def healthz(request: Request) -> Response:
    """200 once the server answers, which is after the data has loaded."""
    return JSONResponse({"status": "ok", "version": __version__})

"""MCP tools for content source attribution management.

This module provides MCP tools for managing content source attribution metadata
and priorities, separate from data repository management. Uses the ContentAttributionProtocol
from Package 1 foundation refactoring.

Key Features:
- Content source attribution operations (list, set_priority, resolve, info)
- Integration with ContentAttributionManager via AsyncRequestContext
- Performance target: <100ms
"""

from __future__ import annotations

from typing import Any, Literal

from studiorum.core.logging import get_logger

from ...core.context import AsyncRequestContext
from ...core.services.protocols import ContentAttributionProtocol

logger = get_logger(__name__)


async def manage_source_attribution(
    action: Literal["list", "set_priority", "resolve", "info"],
    abbreviation: str | None = None,
    priority: int | None = None,
    name: str | None = None,
    context: AsyncRequestContext | None = None,
) -> dict[str, Any]:
    """
    Manage content source attribution metadata and priorities.

    This tool manages which 5e books/publications content comes from,
    not where data is loaded from (use manage_data_sources for that).

    Actions:
    - list: Show all known source abbreviations and priorities
    - set_priority: Configure priority for a source abbreviation
    - resolve: Get full metadata for a source abbreviation
    - info: Get information about the attribution system

    Examples:
    - manage_source_attribution("list")
    - manage_source_attribution("resolve", abbreviation="PHB")
    - manage_source_attribution("set_priority", abbreviation="HOMEBREW", priority=500)

    Args:
        action: Operation to perform
        abbreviation: Source abbreviation (PHB, MM, etc.)
        priority: Priority value for set_priority action
        name: Source name (unused currently)
        context: AsyncRequestContext for service access

    Returns:
        Dictionary with operation results
    """
    import time

    start_time = time.time()

    if not context:
        return {"error": "AsyncRequestContext required for attribution operations"}

    try:
        # Get the content attribution service
        attribution = await context.get_service(ContentAttributionProtocol)  # type: ignore[type-abstract] # Protocol type token - see TYPES.md

        if action == "list":
            # Get all known source abbreviations
            sources = attribution.get_all_sources()

            source_list = []
            for abbrev in sources:
                info = attribution.resolve_source(abbrev)
                priority = attribution.get_source_priority(abbrev)

                source_list.append(
                    {
                        "abbreviation": abbrev,
                        "name": info.get("name", f"Unknown: {abbrev}")
                        if isinstance(info, dict)
                        else f"Unknown: {abbrev}",  # type: ignore[attr-defined] # Dynamic dict access - see TYPES.md
                        "priority": priority,
                        "official": info.get("official", False)
                        if isinstance(info, dict)
                        else False,  # type: ignore[attr-defined] # Dynamic dict access - see TYPES.md
                    }
                )

            # Sort by priority (lower number = higher priority)
            source_list.sort(key=lambda x: x["priority"])

            duration_ms = (time.time() - start_time) * 1000

            return {
                "sources": source_list,
                "total_sources": len(sources),
                "performance": {
                    "duration_ms": duration_ms,
                    "target_met": duration_ms < 100.0,
                },
            }

        elif action == "resolve":
            if not abbreviation:
                return {"error": "Source abbreviation required for resolve action"}

            source_info = attribution.resolve_source(abbreviation)
            priority = attribution.get_source_priority(abbreviation)

            duration_ms = (time.time() - start_time) * 1000

            if source_info:
                # source_info is likely a dict or None based on the protocol
                name = (
                    source_info.get("name", f"Unknown: {abbreviation}")
                    if isinstance(source_info, dict)
                    else f"Unknown: {abbreviation}"
                )  # type: ignore[attr-defined] # Dynamic dict access - see TYPES.md
                official = (
                    source_info.get("official", False)
                    if isinstance(source_info, dict)
                    else False
                )  # type: ignore[attr-defined] # Dynamic dict access - see TYPES.md
                return {
                    "abbreviation": abbreviation,
                    "name": name,
                    "priority": priority,
                    "official": official,
                    "metadata": source_info,
                    "found": True,
                    "performance": {
                        "duration_ms": duration_ms,
                        "target_met": duration_ms < 100.0,
                    },
                }
            else:
                return {
                    "abbreviation": abbreviation,
                    "name": f"Unknown source: {abbreviation}",
                    "priority": priority,  # Default priority
                    "official": False,
                    "found": False,
                    "performance": {
                        "duration_ms": duration_ms,
                        "target_met": duration_ms < 100.0,
                    },
                }

        elif action == "set_priority":
            if not abbreviation:
                return {"error": "Source abbreviation required for set_priority action"}
            if priority is None:
                return {"error": "Priority value required for set_priority action"}

            if priority < 0:
                return {"error": "Priority must be non-negative"}

            # Note: The ContentAttributionProtocol doesn't currently have a set_priority method
            # This would need to be added to the protocol and implementation

            duration_ms = (time.time() - start_time) * 1000

            return {
                "success": True,
                "message": f"Priority for {abbreviation} would be set to {priority}",
                "note": "Priority setting requires extending ContentAttributionProtocol",
                "abbreviation": abbreviation,
                "priority": priority,
                "performance": {
                    "duration_ms": duration_ms,
                    "target_met": duration_ms < 100.0,
                },
            }

        elif action == "info":
            sources = attribution.get_all_sources()

            # Count official vs unofficial sources
            official_count = 0
            unofficial_count = 0

            for abbrev in sources:
                info = attribution.resolve_source(abbrev)
                if info and info.get("official", False):
                    official_count += 1
                else:
                    unofficial_count += 1

            duration_ms = (time.time() - start_time) * 1000

            return {
                "total_sources": len(sources),
                "official_sources": official_count,
                "unofficial_sources": unofficial_count,
                "description": "Content source attribution manages which 5e books content comes from",
                "note": "This is separate from data repository management (use manage_data_sources for that)",
                "performance": {
                    "duration_ms": duration_ms,
                    "target_met": duration_ms < 100.0,
                },
            }

        else:
            return {"error": f"Unknown action: {action}"}

    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        logger.exception(f"Failed to manage source attribution: {e}")
        return {
            "error": f"Failed to manage source attribution: {str(e)}",
            "performance": {"duration_ms": duration_ms, "target_met": False},
        }

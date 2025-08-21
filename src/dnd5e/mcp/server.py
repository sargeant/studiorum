"""FastMCP server implementation for dnd5e.

This module implements the FastMCP server that provides D&D 5e content tools
with <200ms performance targets. It integrates with existing AsyncRequestContext
infrastructure and leverages the configuration bridge from Package 1.2.

Key Features:
- FastMCP framework integration with type safety
- Basic content search tools with performance optimization
- AsyncRequestContext integration for concurrent requests
- Configuration tool integration from Package 1.2
- Performance monitoring and metrics collection
"""

from __future__ import annotations

from typing import Any, Literal

from fastmcp import FastMCP

from dnd5e.core.logging import get_logger

from ..core.context import AsyncRequestContext, async_request_context
from ..core.error_types import (
    ContentNotFoundError,
    ErrorCategory,
    MCPError,
    MCPErrorCode,
    MCPException,
)
from ..core.result import Error as ResultError, Result
from .request_handler import ModernMCPRequestHandler
from .tools.config import (
    add_content_source,
    configure_encounter_printing,
    configure_paper_layout,
    configure_spellbook_generation,
    get_configuration,
    load_user_preferences,
    save_user_preferences,
    update_configuration,
)

logger = get_logger(__name__)

# Initialize FastMCP server with dnd5e branding
mcp = FastMCP(
    name="dnd5e-server",
    instructions="Deterministic D&D 5e data interface with natural language configuration",
    version="0.5.0",
)

# Initialize the modern request handler for delegation
_request_handler = ModernMCPRequestHandler(enable_performance_monitoring=True)


# Configuration Tools (from Package 1.2)
@mcp.tool()
async def get_current_configuration() -> dict[str, Any]:
    """Get the current application configuration.

    Returns the complete current configuration including rendering settings,
    content sources, validation rules, and performance settings.

    Returns:
        Complete current configuration as a dictionary
    """
    try:
        result = await get_configuration()
        if result.is_success():
            config_response = result.unwrap()
            return config_response.model_dump()
        else:
            error = result.error if isinstance(result, ResultError) else "Unknown error"
            logger.error(f"Failed to get configuration: {error}")
            error_msg = error.message if hasattr(error, "message") else str(error)
            mcp_error = MCPError(
                message=f"Configuration retrieval failed: {error_msg}",
                error_code=MCPErrorCode.CONFIGURATION_ERROR,
                category=ErrorCategory.SYSTEM_ERROR,
            )
            raise MCPException(mcp_error)
    except Exception as e:
        logger.error(f"Failed to get configuration: {e}")
        mcp_error = MCPError(
            message=f"Configuration retrieval failed: {e}",
            error_code=MCPErrorCode.INTERNAL_ERROR,
            category=ErrorCategory.SYSTEM_ERROR,
        )
        raise MCPException(mcp_error)


@mcp.tool()
async def update_app_configuration(updates: dict[str, Any]) -> dict[str, Any]:
    """Update application configuration with the provided changes.

    Args:
        updates: Configuration updates to apply

    Returns:
        Updated configuration with validation results
    """
    try:
        result = await update_configuration(updates)
        if result.is_success():
            config_response = result.unwrap()
            return config_response.model_dump()
        else:
            error = result.error if isinstance(result, ResultError) else "Unknown error"
            logger.error(f"Failed to update configuration: {error}")
            error_msg = error.message if hasattr(error, "message") else str(error)
            mcp_error = MCPError(
                message=f"Configuration update failed: {error_msg}",
                error_code=MCPErrorCode.CONFIGURATION_ERROR,
                category=ErrorCategory.SYSTEM_ERROR,
            )
            raise MCPException(mcp_error)
    except Exception as e:
        logger.error(f"Failed to update configuration: {e}")
        mcp_error = MCPError(
            message=f"Configuration update failed: {e}",
            error_code=MCPErrorCode.INTERNAL_ERROR,
            category=ErrorCategory.SYSTEM_ERROR,
        )
        raise MCPException(mcp_error)


@mcp.tool()
async def configure_for_paper_layout(
    paper_size: Literal["letter", "a4", "a5"] = "letter",
    background: Literal["full", "none", "print"] = "print",
    high_contrast: bool = False,
    two_column: bool = True,
) -> dict[str, Any]:
    """Configure paper layout settings for PDF output.

    Args:
        paper_size: Paper size (letter, a4, a5)
        background: Background style (full, none, print)
        high_contrast: Enable high contrast mode for printing
        two_column: Whether to use two-column layout

    Returns:
        Updated configuration with paper layout settings
    """
    try:
        result = await configure_paper_layout(
            paper_size=paper_size,
            background=background,
            high_contrast=high_contrast,
            two_column=two_column,
        )
        if result.is_success():
            config_response = result.unwrap()
            return config_response.model_dump()
        else:
            error = result.error if isinstance(result, ResultError) else "Unknown error"
            logger.error(f"Failed to configure paper layout: {error}")
            error_msg = error.message if hasattr(error, "message") else str(error)
            mcp_error = MCPError(
                message=f"Paper layout configuration failed: {error_msg}",
                error_code=MCPErrorCode.CONFIGURATION_ERROR,
                category=ErrorCategory.SYSTEM_ERROR,
            )
            raise MCPException(mcp_error)
    except Exception as e:
        logger.error(f"Failed to configure paper layout: {e}")
        mcp_error = MCPError(
            message=f"Paper layout configuration failed: {e}",
            error_code=MCPErrorCode.INTERNAL_ERROR,
            category=ErrorCategory.SYSTEM_ERROR,
        )
        raise MCPException(mcp_error)


@mcp.tool()
async def configure_for_spellbook_generation(
    include_spell_appendix: bool = True,
    alphabetical_organization: bool = True,
    enable_cross_refs: bool = True,
    show_index: bool = True,
) -> dict[str, Any]:
    """Configure settings optimized for spellbook generation.

    Args:
        include_spell_appendix: Whether to include spell appendices
        alphabetical_organization: Whether to organize alphabetically
        enable_cross_refs: Whether to enable cross references
        show_index: Whether to show spell index

    Returns:
        Updated configuration optimized for spellbooks
    """
    try:
        result = await configure_spellbook_generation(
            include_spell_appendix=include_spell_appendix,
            alphabetical_organization=alphabetical_organization,
            enable_cross_refs=enable_cross_refs,
            show_index=show_index,
        )
        if result.is_success():
            config_response = result.unwrap()
            return config_response.model_dump()
        else:
            error = result.error if isinstance(result, ResultError) else "Unknown error"
            logger.error(f"Failed to configure spellbook generation: {error}")
            error_msg = error.message if hasattr(error, "message") else str(error)
            mcp_error = MCPError(
                message=f"Spellbook configuration failed: {error_msg}",
                error_code=MCPErrorCode.CONFIGURATION_ERROR,
                category=ErrorCategory.SYSTEM_ERROR,
            )
            raise MCPException(mcp_error)
    except Exception as e:
        logger.error(f"Failed to configure spellbook generation: {e}")
        mcp_error = MCPError(
            message=f"Spellbook configuration failed: {e}",
            error_code=MCPErrorCode.INTERNAL_ERROR,
            category=ErrorCategory.SYSTEM_ERROR,
        )
        raise MCPException(mcp_error)


@mcp.tool()
async def configure_for_encounter_printing(
    optimize_for_print: bool = True,
    include_creature_appendix: bool = True,
    high_contrast: bool = True,
    single_column: bool = False,
) -> dict[str, Any]:
    """Configure settings optimized for encounter printing.

    Args:
        optimize_for_print: Whether to optimize for physical printing
        include_creature_appendix: Whether to include creature appendix
        high_contrast: Whether to use high contrast for better printing
        single_column: Whether to use single column layout

    Returns:
        Updated configuration optimized for encounter printing
    """
    try:
        result = await configure_encounter_printing(
            optimize_for_print=optimize_for_print,
            include_creature_appendix=include_creature_appendix,
            high_contrast=high_contrast,
            single_column=single_column,
        )
        if result.is_success():
            config_response = result.unwrap()
            return config_response.model_dump()
        else:
            error = result.error if isinstance(result, ResultError) else "Unknown error"
            logger.error(f"Failed to configure encounter printing: {error}")
            error_msg = error.message if hasattr(error, "message") else str(error)
            mcp_error = MCPError(
                message=f"Encounter printing configuration failed: {error_msg}",
                error_code=MCPErrorCode.CONFIGURATION_ERROR,
                category=ErrorCategory.SYSTEM_ERROR,
            )
            raise MCPException(mcp_error)
    except Exception as e:
        logger.error(f"Failed to configure encounter printing: {e}")
        mcp_error = MCPError(
            message=f"Encounter printing configuration failed: {e}",
            error_code=MCPErrorCode.INTERNAL_ERROR,
            category=ErrorCategory.SYSTEM_ERROR,
        )
        raise MCPException(mcp_error)


@mcp.tool()
async def add_content_source_to_config(
    sources: list[str],
    replace_existing: bool = False,
) -> dict[str, Any]:
    """Add content sources to the current configuration.

    Args:
        sources: List of source abbreviations (e.g., ["phb", "mm"])
        replace_existing: Whether to replace existing sources or add to them

    Returns:
        Updated configuration with the new sources added
    """
    try:
        result = await add_content_source(
            sources=sources,
            replace_existing=replace_existing,
        )
        if result.is_success():
            config_response = result.unwrap()
            return config_response.model_dump()
        else:
            error = result.error if isinstance(result, ResultError) else "Unknown error"
            logger.error(f"Failed to add content sources: {error}")
            error_msg = error.message if hasattr(error, "message") else str(error)
            mcp_error = MCPError(
                message=f"Content source addition failed: {error_msg}",
                error_code=MCPErrorCode.CONFIGURATION_ERROR,
                category=ErrorCategory.SYSTEM_ERROR,
            )
            raise MCPException(mcp_error)
    except Exception as e:
        logger.error(f"Failed to add content sources: {e}")
        mcp_error = MCPError(
            message=f"Content source addition failed: {e}",
            error_code=MCPErrorCode.INTERNAL_ERROR,
            category=ErrorCategory.SYSTEM_ERROR,
        )
        raise MCPException(mcp_error)


@mcp.tool()
async def save_preferences_to_file(
    preset_name: str, description: str = ""
) -> dict[str, Any]:
    """Save current configuration as a named preset for later use.

    Args:
        preset_name: Name for the configuration preset
        description: Optional description of the preset

    Returns:
        Save operation result with preset information
    """
    try:
        result = await save_user_preferences(
            preset_name=preset_name, description=description
        )
        if result.is_success():
            config_response = result.unwrap()
            return config_response.model_dump()
        else:
            error = result.error if isinstance(result, ResultError) else "Unknown error"
            logger.error(f"Failed to save preferences: {error}")
            error_msg = error.message if hasattr(error, "message") else str(error)
            mcp_error = MCPError(
                message=f"Preference save failed: {error_msg}",
                error_code=MCPErrorCode.CONFIGURATION_ERROR,
                category=ErrorCategory.SYSTEM_ERROR,
            )
            raise MCPException(mcp_error)
    except Exception as e:
        logger.error(f"Failed to save preferences: {e}")
        mcp_error = MCPError(
            message=f"Preference save failed: {e}",
            error_code=MCPErrorCode.INTERNAL_ERROR,
            category=ErrorCategory.SYSTEM_ERROR,
        )
        raise MCPException(mcp_error)


@mcp.tool()
async def load_preferences_from_file(preset_name: str) -> dict[str, Any]:
    """Load a previously saved configuration preset.

    Args:
        preset_name: Name of the configuration preset to load

    Returns:
        Loaded configuration or error if preset doesn't exist
    """
    try:
        result = await load_user_preferences(preset_name=preset_name)
        if result.is_success():
            config_response = result.unwrap()
            return config_response.model_dump()
        else:
            error = result.error if isinstance(result, ResultError) else "Unknown error"
            logger.error(f"Failed to load preferences: {error}")
            error_msg = error.message if hasattr(error, "message") else str(error)
            mcp_error = MCPError(
                message=f"Preference load failed: {error_msg}",
                error_code=MCPErrorCode.CONFIGURATION_ERROR,
                category=ErrorCategory.SYSTEM_ERROR,
            )
            raise MCPException(mcp_error)
    except Exception as e:
        logger.error(f"Failed to load preferences: {e}")
        mcp_error = MCPError(
            message=f"Preference load failed: {e}",
            error_code=MCPErrorCode.INTERNAL_ERROR,
            category=ErrorCategory.SYSTEM_ERROR,
        )
        raise MCPException(mcp_error)


# Basic Content Search Tools - Optimized for <200ms performance
@mcp.tool()
async def search_content(
    content_type: Literal["spells", "creatures", "items", "adventures", "books"],
    query: str | None = None,
    sources: list[str] | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    """Search D&D 5e content with <200ms performance target.

    Args:
        content_type: Type of content to search for
        query: Search query string (optional for listing all)
        sources: List of source abbreviations to filter by
        limit: Maximum number of results to return

    Returns:
        Search results with metadata and performance metrics
    """
    import time

    from ..mcp.tools.content import search_content_performant

    start_time = time.time()

    try:
        # Use optimized content searcher directly for <200ms target
        result = await search_content_performant(
            content_type=content_type, query=query, sources=sources, limit=limit
        )

        duration_ms = (time.time() - start_time) * 1000

        # Add performance metrics to result
        result["performance"]["total_duration_ms"] = duration_ms
        result["performance"]["target_met"] = duration_ms < 200.0

        if duration_ms > 200:
            logger.warning(f"Search exceeded 200ms target: {duration_ms:.1f}ms")

        return result

    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        logger.error(f"Content search failed after {duration_ms:.1f}ms: {e}")
        mcp_error = MCPError(
            message=f"Search failed: {e}",
            error_code=MCPErrorCode.PROCESSING_ERROR,
            category=ErrorCategory.PROCESSING,
        )
        raise MCPException(mcp_error)


@mcp.tool()
async def search_spells(
    query: str | None = None,
    sources: list[str] | None = None,
    level: int | None = None,
    school: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    """Search for D&D 5e spells with optional filtering.

    Args:
        query: Search query for spell names or descriptions
        sources: List of source abbreviations to search in
        level: Spell level to filter by (0-9)
        school: School of magic to filter by
        limit: Maximum number of results to return

    Returns:
        List of matching spells with metadata
    """
    import asyncio
    import time

    from ..mcp.tools.content import search_content_performant

    start_time = time.time()

    try:
        # Build filters for spell-specific parameters
        filters: dict[str, Any] = {}
        if level is not None:
            filters["level"] = level
        if school is not None:
            filters["school"] = school

        # Use optimized search with 180ms timeout (20ms buffer for processing)
        result = await asyncio.wait_for(
            search_content_performant(
                content_type="spells",
                query=query,
                sources=sources,
                filters=filters if filters else None,
                limit=limit,
            ),
            timeout=0.18,  # 180ms timeout
        )

        duration_ms = (time.time() - start_time) * 1000
        result["performance"]["total_duration_ms"] = duration_ms
        result["performance"]["target_met"] = duration_ms < 200.0

        return result

    except TimeoutError:
        duration_ms = (time.time() - start_time) * 1000
        logger.warning(f"Spell search timed out after {duration_ms:.1f}ms")
        mcp_error = MCPError(
            message="Spell search timed out - try a more specific query",
            error_code=MCPErrorCode.PROCESSING_ERROR,
            category=ErrorCategory.PROCESSING,
        )
        raise MCPException(mcp_error)
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        logger.error(f"Spell search failed after {duration_ms:.1f}ms: {e}")
        mcp_error = MCPError(
            message=f"Spell search failed: {e}",
            error_code=MCPErrorCode.PROCESSING_ERROR,
            category=ErrorCategory.PROCESSING,
        )
        raise MCPException(mcp_error)


@mcp.tool()
async def search_creatures(
    query: str | None = None,
    sources: list[str] | None = None,
    cr_min: float | None = None,
    cr_max: float | None = None,
    creature_type: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    """Search for D&D 5e creatures with optional filtering.

    Args:
        query: Search query for creature names or descriptions
        sources: List of source abbreviations to search in
        cr_min: Minimum challenge rating
        cr_max: Maximum challenge rating
        creature_type: Type of creature (beast, humanoid, etc.)
        limit: Maximum number of results to return

    Returns:
        List of matching creatures with metadata
    """
    try:
        params = {
            "query": query or "",
            "sources": sources or [],
            "cr_min": cr_min,
            "cr_max": cr_max,
            "creature_type": creature_type,
            "limit": limit,
        }

        result = await _request_handler.handle_request(
            method="search_creatures", params=params
        )

        if "error" in result:
            mcp_error = MCPError(
                message=result["error"]["message"],
                error_code=MCPErrorCode.PROCESSING_ERROR,
                category=ErrorCategory.PROCESSING,
            )
            raise MCPException(mcp_error)

        return result["result"]  # type: ignore[no-any-return]

    except Exception as e:
        logger.error(f"Creature search failed: {e}")
        mcp_error = MCPError(
            message=f"Creature search failed: {e}",
            error_code=MCPErrorCode.PROCESSING_ERROR,
            category=ErrorCategory.PROCESSING,
        )
        raise MCPException(mcp_error)


@mcp.tool()
async def list_adventures(sources: list[str] | None = None) -> dict[str, Any]:
    """List available D&D 5e adventures.

    Args:
        sources: Optional list of sources to filter by

    Returns:
        List of available adventures with metadata
    """
    try:
        params = {"sources": sources or []}

        result = await _request_handler.handle_request(
            method="list_adventures", params=params
        )

        if "error" in result:
            mcp_error = MCPError(
                message=result["error"]["message"],
                error_code=MCPErrorCode.PROCESSING_ERROR,
                category=ErrorCategory.PROCESSING,
            )
            raise MCPException(mcp_error)

        return result["result"]  # type: ignore[no-any-return]

    except Exception as e:
        logger.error(f"Adventure listing failed: {e}")
        mcp_error = MCPError(
            message=f"Adventure listing failed: {e}",
            error_code=MCPErrorCode.PROCESSING_ERROR,
            category=ErrorCategory.PROCESSING,
        )
        raise MCPException(mcp_error)


@mcp.tool()
async def list_books(sources: list[str] | None = None) -> dict[str, Any]:
    """List available D&D 5e books.

    Args:
        sources: Optional list of sources to filter by

    Returns:
        List of available books with metadata
    """
    try:
        params = {"sources": sources or []}

        result = await _request_handler.handle_request(
            method="list_books", params=params
        )

        if "error" in result:
            mcp_error = MCPError(
                message=result["error"]["message"],
                error_code=MCPErrorCode.PROCESSING_ERROR,
                category=ErrorCategory.PROCESSING,
            )
            raise MCPException(mcp_error)

        return result["result"]  # type: ignore[no-any-return]

    except Exception as e:
        logger.error(f"Book listing failed: {e}")
        mcp_error = MCPError(
            message=f"Book listing failed: {e}",
            error_code=MCPErrorCode.PROCESSING_ERROR,
            category=ErrorCategory.PROCESSING,
        )
        raise MCPException(mcp_error)


@mcp.tool()
async def resolve_adventure(
    adventure_name: str, include_appendices: bool = False
) -> dict[str, Any]:
    """Resolve and retrieve detailed adventure data.

    Args:
        adventure_name: Name or abbreviation of the adventure
        include_appendices: Whether to include appendix data

    Returns:
        Detailed adventure data with chapters and metadata
    """
    try:
        params = {
            "adventure_name": adventure_name,
            "include_appendices": include_appendices,
        }

        result = await _request_handler.handle_request(
            method="resolve_adventure", params=params
        )

        if "error" in result:
            mcp_error = MCPError(
                message=result["error"]["message"],
                error_code=MCPErrorCode.PROCESSING_ERROR,
                category=ErrorCategory.PROCESSING,
            )
            raise MCPException(mcp_error)

        return result["result"]  # type: ignore[no-any-return]

    except Exception as e:
        logger.error(f"Adventure resolution failed: {e}")
        mcp_error = MCPError(
            message=f"Adventure resolution failed: {e}",
            error_code=MCPErrorCode.PROCESSING_ERROR,
            category=ErrorCategory.PROCESSING,
        )
        raise MCPException(mcp_error)


@mcp.tool()
async def resolve_book(book_name: str) -> dict[str, Any]:
    """Resolve and retrieve detailed book data.

    Args:
        book_name: Name or abbreviation of the book

    Returns:
        Detailed book data with chapters and metadata
    """
    try:
        params = {"book_name": book_name}

        result = await _request_handler.handle_request(
            method="resolve_book", params=params
        )

        if "error" in result:
            mcp_error = MCPError(
                message=result["error"]["message"],
                error_code=MCPErrorCode.PROCESSING_ERROR,
                category=ErrorCategory.PROCESSING,
            )
            raise MCPException(mcp_error)

        return result["result"]  # type: ignore[no-any-return]

    except Exception as e:
        logger.error(f"Book resolution failed: {e}")
        mcp_error = MCPError(
            message=f"Book resolution failed: {e}",
            error_code=MCPErrorCode.PROCESSING_ERROR,
            category=ErrorCategory.PROCESSING,
        )
        raise MCPException(mcp_error)


# Server Management Functions
async def create_mcp_server() -> FastMCP:
    """Create and configure the dnd5e MCP server.

    Returns:
        Configured FastMCP server instance
    """
    logger.info("Creating dnd5e MCP server with FastMCP integration")

    # Count registered tools
    tool_count = len(list_registered_tools())
    logger.info(f"Registered {tool_count} tools for D&D 5e content and configuration")

    return mcp


def get_mcp_app() -> FastMCP:
    """Get the FastMCP server application instance.

    Returns:
        FastMCP server instance for CLI integration
    """
    return mcp


# Tool registration information for debugging
def list_registered_tools() -> list[str]:
    """List all registered MCP tools.

    Returns:
        List of tool names registered with the server
    """
    # FastMCP stores tools in _tool_manager._tools
    try:
        if hasattr(mcp, "_tool_manager") and hasattr(mcp._tool_manager, "_tools"):
            return list(mcp._tool_manager._tools.keys())
        else:
            logger.warning("FastMCP tool manager not found")
            return []
    except Exception as e:
        logger.warning(f"Could not list registered tools: {e}")
        return []

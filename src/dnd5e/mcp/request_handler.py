"""Modern MCP request handler with protocol-based async contexts.

This module provides the MCP request handler that uses async request contexts
for complete request isolation, protocol-validated services, and enhanced
error handling for MCP tool implementations.

Key Features:
- ModernMCPRequestHandler with protocol-based async contexts
- Concurrent async request isolation with performance monitoring
- Configuration override with hot-reload capabilities
- Enhanced structured error responses with performance metrics
- Protocol-based service access for all MCP tools
"""

from __future__ import annotations

import logging
from typing import Any

from ..core.api import ModernContextualAPI
from ..core.context import async_request_context, performance_monitored_context
from ..core.error_types import (
    ContentNotFoundError,
    MCPError,
    ProcessingError,
)
from ..core.services.protocols import OmnidexerProtocol

logger = logging.getLogger(__name__)


class ModernMCPRequestHandler:
    """Modern MCP request handler with protocol-based async contexts.

    This handler provides complete request isolation using async request contexts,
    enabling concurrent MCP requests with protocol-validated services and
    comprehensive performance monitoring.

    Features:
    - Async request contexts for complete isolation
    - Protocol-validated service access with runtime verification
    - Performance monitoring and metrics collection
    - Hot-reload configuration support
    - Structured error handling with JSON-RPC compatibility
    - Request-scoped error collection and propagation

    Examples:
        Basic MCP request handling:
        >>> handler = ModernMCPRequestHandler()
        >>> response = await handler.handle_request(
        ...     method="search_spells",
        ...     params={"query": "fireball", "sources": ["phb"]}
        ... )

        With performance monitoring:
        >>> handler = ModernMCPRequestHandler(enable_performance_monitoring=True)
        >>> response = await handler.handle_request(
        ...     method="resolve_adventure",
        ...     params={"adventure_name": "lost-mine-of-phandelver"},
        ...     enable_hot_reload=True
        ... )
    """

    def __init__(self, enable_performance_monitoring: bool = True) -> None:
        """Initialize MCP request handler.

        Args:
            enable_performance_monitoring: Whether to enable performance tracking
        """
        self.performance_monitoring = enable_performance_monitoring

    async def handle_request(
        self,
        method: str,
        params: dict[str, Any],
        config_overrides: dict[str, Any] | None = None,
        enable_hot_reload: bool = False,
    ) -> dict[str, Any]:
        """Handle MCP request with modern async context isolation.

        Args:
            method: MCP method name to handle
            params: Method parameters from MCP request
            config_overrides: Optional configuration overrides for this request
            enable_hot_reload: Whether to enable hot-reload for this request

        Returns:
            JSON-RPC compatible response with result or error
        """
        # Create request-specific configuration with hot-reload support
        config = None
        if config_overrides:
            try:
                from ..core.config.unified_config import get_app_config

                base_config = get_app_config()
                config = base_config.model_copy(update=config_overrides)
            except Exception as e:
                logger.warning(f"Failed to create config override: {e}")

        # Execute in modern async context with performance monitoring
        context_manager = (
            performance_monitored_context
            if self.performance_monitoring
            else async_request_context
        )

        async with context_manager(
            config_override=config,
            enable_hot_reload=enable_hot_reload,
            performance_tracking=self.performance_monitoring,
        ) as ctx:
            try:
                logger.info(
                    f"Handling MCP request {method} with context {ctx.request_id}"
                )

                # Route to appropriate async handler with protocol validation
                if method == "search_spells":
                    result = await self._handle_search_spells_async(params, ctx)
                elif method == "search_creatures":
                    result = await self._handle_search_creatures_async(params, ctx)
                elif method == "search_content":
                    result = await self._handle_search_content_async(params, ctx)
                elif method == "resolve_adventure":
                    result = await self._handle_resolve_adventure_async(params, ctx)
                elif method == "resolve_book":
                    result = await self._handle_resolve_book_async(params, ctx)
                elif method == "get_character_progression":
                    result = await self._handle_character_progression_async(params, ctx)
                elif method == "list_adventures":
                    result = await self._handle_list_adventures_async(params, ctx)
                elif method == "list_books":
                    result = await self._handle_list_books_async(params, ctx)
                else:
                    raise ValueError(f"Unknown method: {method}")

                # Enhanced error handling with performance metrics
                if ctx.has_errors():
                    error_data = [
                        error.to_json_rpc_error() for error in ctx.get_errors()
                    ]
                    if self.performance_monitoring:
                        error_data.append(
                            {
                                "performance_metrics": ctx.metrics.model_dump(),
                                "context_id": str(ctx.request_id),
                            }
                        )

                    return {
                        "error": {
                            "code": -32603,
                            "message": "Request completed with errors",
                            "data": error_data,
                        }
                    }

                # Success response with optional performance data
                response = {"result": result}
                if self.performance_monitoring and ctx.metrics:
                    response["_performance"] = {
                        "context_id": str(ctx.request_id),
                        "duration_ms": ctx.duration_ms,
                        "metrics": ctx.metrics.model_dump(),
                    }

                return response

            except Exception as e:
                logger.error(f"MCP request {method} failed: {e}", exc_info=True)
                error_data = {"context_id": str(ctx.request_id)}

                if self.performance_monitoring:
                    error_data["performance_metrics"] = ctx.metrics.model_dump()

                return {
                    "error": {
                        "code": -32603,
                        "message": f"Internal error: {e}",
                        "data": error_data,
                    }
                }

    async def _handle_search_spells_async(
        self, params: dict[str, Any], ctx
    ) -> dict[str, Any]:
        """Handle spell search with modern async context.

        Args:
            params: Search parameters from MCP request
            ctx: Async request context with protocol-validated services

        Returns:
            Search results with metadata
        """
        query = params.get("query", "")
        sources = params.get("sources", [])

        # Update context sources for filtering
        if sources:
            ctx.sources.extend(sources)

        # Use modern contextual API with protocol validation
        result = await ModernContextualAPI.search_spells_async(
            query, sources=ctx.sources if ctx.sources else None
        )

        if result.is_success():
            spells = result.unwrap()
            ctx.record_cache_hit()  # Performance tracking
            return {
                "spells": [
                    spell.model_dump()
                    if hasattr(spell, "model_dump")
                    else spell.__dict__
                    for spell in spells
                ],
                "total": len(spells),
                "sources_used": ctx.sources,
                "query": query,
            }
        else:
            error = result.error
            await ctx.add_async_error(error)
            ctx.record_cache_miss()
            return {
                "spells": [],
                "error": error.message,
                "suggestions": error.suggestions or [],
                "query": query,
            }

    async def _handle_search_creatures_async(
        self, params: dict[str, Any], ctx
    ) -> dict[str, Any]:
        """Handle creature search with async protocols.

        Args:
            params: Search parameters from MCP request
            ctx: Async request context

        Returns:
            Search results with metadata
        """
        query = params.get("query", "")
        sources = params.get("sources", [])

        if sources:
            ctx.sources.extend(sources)

        result = await ModernContextualAPI.search_creatures_async(
            query, sources=ctx.sources if ctx.sources else None
        )

        if result.is_success():
            creatures = result.unwrap()
            ctx.record_cache_hit()
            return {
                "creatures": [
                    creature.model_dump()
                    if hasattr(creature, "model_dump")
                    else creature.__dict__
                    for creature in creatures
                ],
                "total": len(creatures),
                "sources_used": ctx.sources,
                "query": query,
            }
        else:
            error = result.error
            await ctx.add_async_error(error)
            ctx.record_cache_miss()
            return {
                "creatures": [],
                "error": error.message,
                "suggestions": error.suggestions or [],
                "query": query,
            }

    async def _handle_search_content_async(
        self, params: dict[str, Any], ctx
    ) -> dict[str, Any]:
        """Handle generic content search with protocol validation.

        Args:
            params: Search parameters from MCP request
            ctx: Async request context

        Returns:
            Search results with metadata
        """
        query = params.get("query", "")
        content_type = params.get("content_type", "")
        sources = params.get("sources", [])

        if sources:
            ctx.sources.extend(sources)

        if not content_type:
            error = ProcessingError(message="content_type parameter is required")
            await ctx.add_async_error(error)
            return {
                "content": [],
                "error": error.message,
                "query": query,
            }

        result = await ModernContextualAPI.search_content_async(
            query, content_type, sources=ctx.sources if ctx.sources else None
        )

        if result.is_success():
            content = result.unwrap()
            ctx.record_cache_hit()
            return {
                "content": [
                    item.model_dump() if hasattr(item, "model_dump") else item.__dict__
                    for item in content
                ],
                "total": len(content),
                "content_type": content_type,
                "sources_used": ctx.sources,
                "query": query,
            }
        else:
            error = result.error
            await ctx.add_async_error(error)
            ctx.record_cache_miss()
            return {
                "content": [],
                "error": error.message,
                "suggestions": error.suggestions or [],
                "content_type": content_type,
                "query": query,
            }

    async def _handle_resolve_adventure_async(
        self, params: dict[str, Any], ctx
    ) -> dict[str, Any]:
        """Handle adventure resolution with async protocols.

        Args:
            params: Resolution parameters from MCP request
            ctx: Async request context

        Returns:
            Adventure data with metadata
        """
        adventure_name = params.get("adventure_name", "")
        include_appendices = params.get("include_appendices", False)

        if not adventure_name:
            error = ContentNotFoundError(message="adventure_name parameter is required")
            await ctx.add_async_error(error)
            return {
                "adventure": None,
                "error": error.message,
            }

        # Use modern async API
        result = await ModernContextualAPI.resolve_adventure_async(
            adventure_name, enable_performance_monitoring=self.performance_monitoring
        )

        if result.is_success():
            adventure = result.unwrap()

            # Enhanced response with protocol-based services
            response_data = {
                "adventure": adventure.model_dump()
                if hasattr(adventure, "model_dump")
                else adventure.__dict__,
                "source": adventure.source.abbreviation
                if hasattr(adventure, "source")
                else None,
                "chapters": (
                    len(adventure.contents) if hasattr(adventure, "contents") else 0
                ),
                "name": adventure_name,
            }

            # Add appendices if requested using protocol-based services
            if include_appendices:
                try:
                    # content_factory = await ctx.get_service(ContentFactoryProtocol)  # Placeholder
                    # Appendix generation would be implemented on the content factory
                    response_data["appendices"] = {
                        "note": "Appendix generation not yet implemented"
                    }
                except Exception as e:
                    logger.warning(f"Failed to get content factory for appendices: {e}")

            ctx.record_cache_hit()
            return response_data

        else:
            error = result.error
            await ctx.add_async_error(error)
            ctx.record_cache_miss()
            return {
                "adventure": None,
                "error": error.message,
                "suggestions": error.suggestions or [],
                "name": adventure_name,
            }

    async def _handle_resolve_book_async(
        self, params: dict[str, Any], ctx
    ) -> dict[str, Any]:
        """Handle book resolution with protocol validation.

        Args:
            params: Resolution parameters from MCP request
            ctx: Async request context

        Returns:
            Book data with metadata
        """
        book_name = params.get("book_name", "")

        if not book_name:
            error = ContentNotFoundError(message="book_name parameter is required")
            await ctx.add_async_error(error)
            return {
                "book": None,
                "error": error.message,
            }

        # Get protocol-validated omnidexer for book lookup
        omnidexer = await ctx.get_service(OmnidexerProtocol)

        # Search for the book
        ctx.record_async_operation()
        search_results = omnidexer.search(book_name)

        # Filter for books
        books = [
            result
            for result in search_results
            if hasattr(result, "book")
            or (hasattr(result, "type") and result.type == "book")
        ]

        if books:
            book = books[0]  # Take first match
            ctx.record_cache_hit()
            return {
                "book": book.model_dump()
                if hasattr(book, "model_dump")
                else book.__dict__,
                "source": book.source.abbreviation if hasattr(book, "source") else None,
                "name": book_name,
            }
        else:
            error = ContentNotFoundError(message=f"Book '{book_name}' not found")
            await ctx.add_async_error(error)
            ctx.record_cache_miss()
            return {
                "book": None,
                "error": error.message,
                "name": book_name,
            }

    async def _handle_character_progression_async(
        self, params: dict[str, Any], ctx
    ) -> dict[str, Any]:
        """Handle character progression queries with protocol validation.

        Args:
            params: Progression parameters from MCP request
            ctx: Async request context

        Returns:
            Character progression data
        """
        character_class = params.get("class", "")
        current_level = params.get("level", 1)
        subclass = params.get("subclass")

        if not character_class:
            error = ContentNotFoundError(message="class parameter is required")
            await ctx.add_async_error(error)
            return {
                "progression": None,
                "error": error.message,
            }

        # Use modern async API
        result = await ModernContextualAPI.get_character_progression_async(
            character_class, current_level, subclass
        )

        if result.is_success():
            progression_data = result.unwrap()
            ctx.record_cache_hit()
            return {
                "progression": progression_data,
                "class": character_class,
                "level": current_level,
                "subclass": subclass,
            }
        else:
            error = result.error
            await ctx.add_async_error(error)
            ctx.record_cache_miss()
            return {
                "progression": None,
                "error": error.message,
                "class": character_class,
                "level": current_level,
            }

    async def _handle_list_adventures_async(
        self, params: dict[str, Any], ctx
    ) -> dict[str, Any]:
        """Handle adventure listing with protocol validation.

        Args:
            params: Listing parameters from MCP request
            ctx: Async request context

        Returns:
            List of available adventures
        """
        sources = params.get("sources", [])

        if sources:
            ctx.sources.extend(sources)

        # Get protocol-validated omnidexer
        omnidexer = await ctx.get_service(OmnidexerProtocol)

        ctx.record_async_operation()

        # Get all content and filter for adventures
        all_content = omnidexer.search("")  # Get all content
        adventures = [
            content
            for content in all_content
            if hasattr(content, "adventure")
            or (hasattr(content, "type") and content.type == "adventure")
        ]

        # Apply source filtering if specified
        if ctx.sources:
            adventures = [
                adv
                for adv in adventures
                if hasattr(adv, "source") and adv.source.abbreviation in ctx.sources
            ]

        ctx.record_cache_hit()
        return {
            "adventures": [
                {
                    "name": adv.name if hasattr(adv, "name") else str(adv),
                    "source": adv.source.abbreviation
                    if hasattr(adv, "source")
                    else None,
                    "abbreviation": adv.source.abbreviation
                    if hasattr(adv, "source")
                    else None,
                }
                for adv in adventures
            ],
            "total": len(adventures),
            "sources_used": ctx.sources,
        }

    async def _handle_list_books_async(
        self, params: dict[str, Any], ctx
    ) -> dict[str, Any]:
        """Handle book listing with protocol validation.

        Args:
            params: Listing parameters from MCP request
            ctx: Async request context

        Returns:
            List of available books
        """
        sources = params.get("sources", [])

        if sources:
            ctx.sources.extend(sources)

        # Get protocol-validated omnidexer
        omnidexer = await ctx.get_service(OmnidexerProtocol)

        ctx.record_async_operation()

        # Get all content and filter for books
        all_content = omnidexer.search("")  # Get all content
        books = [
            content
            for content in all_content
            if hasattr(content, "book")
            or (hasattr(content, "type") and content.type == "book")
        ]

        # Apply source filtering if specified
        if ctx.sources:
            books = [
                book
                for book in books
                if hasattr(book, "source") and book.source.abbreviation in ctx.sources
            ]

        ctx.record_cache_hit()
        return {
            "books": [
                {
                    "name": book.name if hasattr(book, "name") else str(book),
                    "source": book.source.abbreviation
                    if hasattr(book, "source")
                    else None,
                    "abbreviation": book.source.abbreviation
                    if hasattr(book, "source")
                    else None,
                }
                for book in books
            ],
            "total": len(books),
            "sources_used": ctx.sources,
        }


# Legacy handler for backward compatibility
class MCPRequestHandler(ModernMCPRequestHandler):
    """Legacy alias for backward compatibility."""

    pass

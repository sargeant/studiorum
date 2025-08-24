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

from typing import Any

from studiorum.core.logging import get_logger

from ..core.api import ModernContextualAPI
from ..core.context import (
    AsyncRequestContext,
    async_request_context,
    performance_monitored_context,
)
from ..core.error_types import (
    ContentNotFoundError,
    ErrorCategory,
    ErrorSeverity,
    MCPError,
    MCPErrorCode,
    MCPException,
    ProcessingError,
)
from ..core.result import Error, Result, Success
from ..core.services.protocols import OmnidexerProtocol
from .async_service_bridge import (
    MCPServiceContext,
    create_mcp_service_context,
)

logger = get_logger(__name__)


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

        # Build metadata for context
        context_metadata = {
            "enable_hot_reload": enable_hot_reload,
            "performance_tracking": self.performance_monitoring,
        }

        async with context_manager(
            config_override=config,
            metadata=context_metadata,
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
                elif method == "analyze_level_progression":
                    result = await self._handle_analyze_level_progression_async(
                        params, ctx
                    )
                elif method == "compare_feat_options":
                    result = await self._handle_compare_feat_options_async(params, ctx)
                elif method == "analyze_multiclass_options":
                    result = await self._handle_analyze_multiclass_options_async(
                        params, ctx
                    )
                # Rules Intelligence Tools
                elif method == "find_rule_cross_references":
                    result = await self._handle_find_rule_cross_references_async(
                        params, ctx
                    )
                elif method == "validate_rule_combination":
                    result = await self._handle_validate_rule_combination_async(
                        params, ctx
                    )
                elif method == "search_rules_intelligent":
                    result = await self._handle_search_rules_intelligent_async(
                        params, ctx
                    )
                elif method == "get_rule_suggestions":
                    result = await self._handle_get_rule_suggestions_async(params, ctx)
                # Encounter Building Tools (Package 2.3)
                elif method == "calculate_encounter_budget":
                    result = await self._handle_calculate_encounter_budget_async(
                        params, ctx
                    )
                elif method == "search_creatures_for_encounter":
                    result = await self._handle_search_creatures_for_encounter_async(
                        params, ctx
                    )
                elif method == "build_balanced_encounter":
                    result = await self._handle_build_balanced_encounter_async(
                        params, ctx
                    )
                elif method == "rebalance_encounter":
                    result = await self._handle_rebalance_encounter_async(params, ctx)
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
                exception_data: dict[str, Any] = {"context_id": str(ctx.request_id)}

                if self.performance_monitoring and ctx.metrics:
                    exception_data["performance_metrics"] = ctx.metrics.model_dump()

                return {
                    "error": {
                        "code": -32603,
                        "message": f"Internal error: {e}",
                        "data": exception_data,
                    }
                }

    async def _handle_search_spells_async(
        self, params: dict[str, Any], ctx: AsyncRequestContext
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
            # Type narrowing: if not success, it must be Error type
            if not isinstance(result, Error):
                # This should never happen given the Result[T, E] pattern
                error = ContentNotFoundError(message="Unexpected result type")
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
        self, params: dict[str, Any], ctx: AsyncRequestContext
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
            # Type narrowing: if not success, it must be Error type
            if not isinstance(result, Error):
                # This should never happen given the Result[T, E] pattern
                error = ContentNotFoundError(message="Unexpected result type")
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
        self, params: dict[str, Any], ctx: AsyncRequestContext
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
            error = ContentNotFoundError(message="content_type parameter is required")
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
            # Type narrowing: if not success, it must be Error type
            if not isinstance(result, Error):
                # This should never happen given the Result[T, E] pattern
                error = ContentNotFoundError(message="Unexpected result type")
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
        self, params: dict[str, Any], ctx: AsyncRequestContext
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
            # Type narrowing: if not success, it must be Error type
            if not isinstance(result, Error):
                # This should never happen given the Result[T, E] pattern
                error = ContentNotFoundError(message="Unexpected result type")
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
        self, params: dict[str, Any], ctx: AsyncRequestContext
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
        omnidexer = await ctx.get_service(OmnidexerProtocol)  # type: ignore[type-abstract] # Protocol type token - see TYPES.md

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
        self, params: dict[str, Any], ctx: AsyncRequestContext
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
            # Type narrowing: if not success, it must be Error type
            if not isinstance(result, Error):
                # This should never happen given the Result[T, E] pattern
                error = ContentNotFoundError(message="Unexpected result type")
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
        self, params: dict[str, Any], ctx: AsyncRequestContext
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
        omnidexer = await ctx.get_service(OmnidexerProtocol)  # type: ignore[type-abstract] # Protocol type token - see TYPES.md

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
        self, params: dict[str, Any], ctx: AsyncRequestContext
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
        omnidexer = await ctx.get_service(OmnidexerProtocol)  # type: ignore[type-abstract] # Protocol type token - see TYPES.md

        ctx.record_async_operation()

        # Get books directly by content type
        from studiorum.core.models.content import ContentType

        books = omnidexer.get_all_by_type(ContentType.BOOK)

        # Apply source filtering if specified
        if ctx.sources:
            books = [
                book
                for book in books
                if hasattr(book, "source") and book.source.abbreviation in ctx.sources
            ]

        ctx.record_cache_hit()
        return {
            "content": [
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

    async def _handle_analyze_level_progression_async(
        self, params: dict[str, Any], ctx: AsyncRequestContext
    ) -> dict[str, Any]:
        """Handle character level progression analysis.

        Args:
            params: Progression analysis parameters from MCP request
            ctx: Async request context

        Returns:
            Character progression analysis results
        """
        character_class = params.get("class", "")
        level = params.get("level", 1)
        subclass = params.get("subclass")
        analysis_type = params.get("analysis_type", "basic")
        include_feat_analysis = params.get("include_feat_analysis", False)
        include_multiclass_options = params.get("include_multiclass_options", False)
        optimization_focus = params.get("optimization_focus")
        sources = params.get("sources", [])

        if not character_class:
            error = ContentNotFoundError(message="class parameter is required")
            await ctx.add_async_error(error)
            return {
                "progression": None,
                "error": error.message,
            }

        if sources:
            ctx.sources.extend(sources)

        try:
            # Import character progression tools
            from .tools.character.progression import analyze_level_progression

            # Perform progression analysis
            ctx.record_async_operation()
            result = await analyze_level_progression(
                character_class=character_class,
                level=level,
                subclass=subclass,
                analysis_type=analysis_type,
                include_feat_analysis=include_feat_analysis,
                include_multiclass_options=include_multiclass_options,
                optimization_focus=optimization_focus,
                sources=ctx.sources if ctx.sources else None,
            )

            ctx.record_cache_hit()
            return result

        except Exception as e:
            error = ContentNotFoundError(
                message=f"Character progression analysis failed: {e}"
            )
            await ctx.add_async_error(error)
            ctx.record_cache_miss()
            return {
                "progression": None,
                "error": error.message,
                "class": character_class,
                "level": level,
            }

    async def _handle_compare_feat_options_async(
        self, params: dict[str, Any], ctx: AsyncRequestContext
    ) -> dict[str, Any]:
        """Handle feat options comparison.

        Args:
            params: Feat comparison parameters from MCP request
            ctx: Async request context

        Returns:
            Feat comparison results
        """
        character_class = params.get("class", "")
        level = params.get("level", 1)
        subclass = params.get("subclass")
        optimization_focus = params.get("optimization_focus")
        sources = params.get("sources", [])
        limit = params.get("limit", 10)

        if not character_class:
            error = ContentNotFoundError(message="class parameter is required")
            await ctx.add_async_error(error)
            return {
                "feat_analysis": [],
                "error": error.message,
            }

        if sources:
            ctx.sources.extend(sources)

        try:
            # Import character progression tools
            from .tools.character.progression import compare_feat_options

            # Perform feat comparison
            ctx.record_async_operation()
            result = await compare_feat_options(
                character_class=character_class,
                level=level,
                subclass=subclass,
                optimization_focus=optimization_focus,
                sources=ctx.sources if ctx.sources else None,
                limit=limit,
            )

            ctx.record_cache_hit()
            return result

        except Exception as e:
            error = ContentNotFoundError(message=f"Feat comparison failed: {e}")
            await ctx.add_async_error(error)
            ctx.record_cache_miss()
            return {
                "feat_analysis": [],
                "error": error.message,
                "class": character_class,
                "level": level,
            }

    async def _handle_analyze_multiclass_options_async(
        self, params: dict[str, Any], ctx: AsyncRequestContext
    ) -> dict[str, Any]:
        """Handle multiclass options analysis.

        Args:
            params: Multiclass analysis parameters from MCP request
            ctx: Async request context

        Returns:
            Multiclass analysis results
        """
        current_class = params.get("current_class", "")
        level = params.get("level", 1)
        sources = params.get("sources", [])

        if not current_class:
            error = ContentNotFoundError(message="current_class parameter is required")
            await ctx.add_async_error(error)
            return {
                "multiclass_options": [],
                "error": error.message,
            }

        if sources:
            ctx.sources.extend(sources)

        try:
            # Import character progression tools
            from .tools.character.progression import analyze_multiclass_options

            # Perform multiclass analysis
            ctx.record_async_operation()
            result = await analyze_multiclass_options(
                current_class=current_class,
                level=level,
                sources=ctx.sources if ctx.sources else None,
            )

            ctx.record_cache_hit()
            return result

        except Exception as e:
            error = ContentNotFoundError(message=f"Multiclass analysis failed: {e}")
            await ctx.add_async_error(error)
            ctx.record_cache_miss()
            return {
                "multiclass_options": [],
                "error": error.message,
                "current_class": current_class,
                "level": level,
            }

    # Rules Intelligence Tools Handlers

    async def _handle_find_rule_cross_references_async(
        self, params: dict[str, Any], ctx: AsyncRequestContext
    ) -> dict[str, Any]:
        """Handle rule cross-reference discovery.

        Args:
            params: Cross-reference parameters from MCP request
            ctx: Async request context

        Returns:
            Cross-reference data with relationships and analysis
        """
        from .tools.rules import find_rule_cross_references

        rule_id = params.get("rule_id", "")
        max_depth = params.get("max_depth", 2)
        include_analysis = params.get("include_analysis", True)

        try:
            result = await find_rule_cross_references(
                rule_id=rule_id,
                max_depth=max_depth,
                include_analysis=include_analysis,
                ctx=ctx,
            )
            return result

        except Exception as e:
            error = ContentNotFoundError(
                message=f"Rule cross-reference discovery failed: {e}"
            )
            await ctx.add_async_error(error)
            ctx.record_cache_miss()
            return {
                "cross_references": {},
                "error": error.message,
                "rule_id": rule_id,
            }

    async def _handle_validate_rule_combination_async(
        self, params: dict[str, Any], ctx: AsyncRequestContext
    ) -> dict[str, Any]:
        """Handle rule combination validation.

        Args:
            params: Validation parameters from MCP request
            ctx: Async request context

        Returns:
            Validation results with conflicts and synergies
        """
        from .tools.rules import validate_rule_combination

        rule_ids = params.get("rule_ids", [])
        context = params.get("context", {})

        try:
            result = await validate_rule_combination(
                rule_ids=rule_ids,
                context=context,
                ctx=ctx,
            )
            return result

        except Exception as e:
            error = ContentNotFoundError(
                message=f"Rule combination validation failed: {e}"
            )
            await ctx.add_async_error(error)
            ctx.record_cache_miss()
            return {
                "validation": {},
                "error": error.message,
                "rule_ids": rule_ids,
            }

    async def _handle_search_rules_intelligent_async(
        self, params: dict[str, Any], ctx: AsyncRequestContext
    ) -> dict[str, Any]:
        """Handle intelligent rule search.

        Args:
            params: Search parameters from MCP request
            ctx: Async request context

        Returns:
            Enhanced search results with relationship analysis
        """
        from .tools.rules import search_rules_intelligent

        query = params.get("query", "")
        rule_types = params.get("rule_types", None)
        sources = params.get("sources", None)
        complexity_filter = params.get("complexity_filter", None)
        include_relationships = params.get("include_relationships", True)
        limit = params.get("limit", 20)

        try:
            result = await search_rules_intelligent(
                query=query,
                rule_types=rule_types,
                sources=sources,
                complexity_filter=complexity_filter,
                include_relationships=include_relationships,
                limit=limit,
                ctx=ctx,
            )
            return result

        except Exception as e:
            error = ContentNotFoundError(message=f"Intelligent rule search failed: {e}")
            await ctx.add_async_error(error)
            ctx.record_cache_miss()
            return {
                "search_results": {},
                "error": error.message,
                "query": query,
            }

    async def _handle_get_rule_suggestions_async(
        self, params: dict[str, Any], ctx: AsyncRequestContext
    ) -> dict[str, Any]:
        """Handle rule suggestion generation.

        Args:
            params: Suggestion parameters from MCP request
            ctx: Async request context

        Returns:
            Intelligent rule suggestions based on context
        """
        from .tools.rules import get_rule_suggestions

        context = params.get("context", {})
        limit = params.get("limit", 10)

        try:
            result = await get_rule_suggestions(
                context=context,
                limit=limit,
                ctx=ctx,
            )
            return result

        except Exception as e:
            error = ContentNotFoundError(
                message=f"Rule suggestion generation failed: {e}"
            )
            await ctx.add_async_error(error)
            ctx.record_cache_miss()
            return {
                "suggestions": [],
                "error": error.message,
                "context": context,
            }

    # Encounter Building Tools Handlers (Package 2.3)

    async def _handle_calculate_encounter_budget_async(
        self, params: dict[str, Any], ctx: AsyncRequestContext
    ) -> dict[str, Any]:
        """Handle encounter budget calculation.

        Args:
            params: Budget calculation parameters from MCP request
            ctx: Async request context

        Returns:
            Encounter budget details with recommendations
        """
        from .tools.encounter.tools import calculate_encounter_budget_mcp

        try:
            party_size = params.get("party_size")
            party_level = params.get("party_level")
            if party_size is None or party_level is None:
                error = MCPError(
                    message="party_size and party_level are required",
                    error_code=MCPErrorCode.INVALID_PARAMS,
                    category=ErrorCategory.VALIDATION,
                )
                raise MCPException(error)

            result = await calculate_encounter_budget_mcp(
                party_size=int(party_size),
                party_level=int(party_level),
                difficulty=str(params.get("difficulty", "medium")),
                individual_levels=params.get("individual_levels"),
            )
            ctx.record_cache_hit()
            return result

        except Exception as e:
            error = ContentNotFoundError(
                message=f"Encounter budget calculation failed: {e}"
            )
            await ctx.add_async_error(error)
            ctx.record_cache_miss()
            return {
                "budget": None,
                "error": error.message,
                "party_size": params.get("party_size"),
                "party_level": params.get("party_level"),
            }

    async def _handle_search_creatures_for_encounter_async(
        self, params: dict[str, Any], ctx: AsyncRequestContext
    ) -> dict[str, Any]:
        """Handle creature search for encounters.

        Args:
            params: Search parameters from MCP request
            ctx: Async request context

        Returns:
            Matching creatures with encounter metadata
        """
        from .tools.encounter.tools import search_creatures_for_encounter_mcp

        try:
            result = await search_creatures_for_encounter_mcp(
                constraints=params.get("constraints", {}),
                xp_budget=params.get("xp_budget"),
                environment=params.get("environment"),
                theme=params.get("theme"),
                sources=params.get("sources"),
            )
            ctx.record_cache_hit()
            return result

        except Exception as e:
            error = ContentNotFoundError(
                message=f"Creature search for encounter failed: {e}"
            )
            await ctx.add_async_error(error)
            ctx.record_cache_miss()
            return {
                "creatures": [],
                "error": error.message,
                "constraints": params.get("constraints", {}),
            }

    async def _handle_build_balanced_encounter_async(
        self, params: dict[str, Any], ctx: AsyncRequestContext
    ) -> dict[str, Any]:
        """Handle balanced encounter building.

        Args:
            params: Encounter building parameters from MCP request
            ctx: Async request context

        Returns:
            Complete balanced encounter with analysis
        """
        from .tools.encounter.tools import build_balanced_encounter_mcp

        try:
            party_size = params.get("party_size")
            party_level = params.get("party_level")
            difficulty = params.get("difficulty")
            if party_size is None or party_level is None or difficulty is None:
                error = MCPError(
                    message="party_size, party_level, and difficulty are required",
                    error_code=MCPErrorCode.INVALID_PARAMS,
                    category=ErrorCategory.VALIDATION,
                )
                raise MCPException(error)

            result = await build_balanced_encounter_mcp(
                party_size=int(party_size),
                party_level=int(party_level),
                difficulty=str(difficulty),
                constraints=params.get("constraints"),
                environment=params.get("environment"),
                theme=params.get("theme"),
                individual_levels=params.get("individual_levels"),
            )
            ctx.record_cache_hit()
            return result

        except Exception as e:
            error = ContentNotFoundError(
                message=f"Balanced encounter building failed: {e}"
            )
            await ctx.add_async_error(error)
            ctx.record_cache_miss()
            return {
                "encounter": None,
                "error": error.message,
                "party_size": params.get("party_size"),
                "party_level": params.get("party_level"),
                "difficulty": params.get("difficulty"),
            }

    async def _handle_rebalance_encounter_async(
        self, params: dict[str, Any], ctx: AsyncRequestContext
    ) -> dict[str, Any]:
        """Handle encounter rebalancing.

        Args:
            params: Rebalancing parameters from MCP request
            ctx: Async request context

        Returns:
            Rebalanced encounter with analysis
        """
        from .tools.encounter.tools import rebalance_encounter_mcp

        try:
            target_difficulty = params.get("target_difficulty")
            party_size = params.get("party_size")
            party_level = params.get("party_level")
            if target_difficulty is None or party_size is None or party_level is None:
                error = MCPError(
                    message="target_difficulty, party_size, and party_level are required",
                    error_code=MCPErrorCode.INVALID_PARAMS,
                    category=ErrorCategory.VALIDATION,
                )
                raise MCPException(error)

            result = await rebalance_encounter_mcp(
                encounter_data=params.get("encounter_data", {}),
                target_difficulty=str(target_difficulty),
                party_size=int(party_size),
                party_level=int(party_level),
                strategy=params.get("strategy", "precise"),
                max_iterations=params.get("max_iterations", 5),
            )
            ctx.record_cache_hit()
            return result

        except Exception as e:
            error = ContentNotFoundError(message=f"Encounter rebalancing failed: {e}")
            await ctx.add_async_error(error)
            ctx.record_cache_miss()
            return {
                "rebalanced_encounter": None,
                "error": error.message,
                "target_difficulty": params.get("target_difficulty"),
                "party_size": params.get("party_size"),
                "party_level": params.get("party_level"),
            }

    # Bridge Integration Patterns
    # These methods demonstrate how to use the AsyncServiceBridge for simplified MCP tool implementation

    async def handle_request_with_bridge(
        self,
        method: str,
        params: dict[str, Any],
        config_overrides: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Handle MCP request using the AsyncServiceBridge pattern.

        This method demonstrates the simplified approach for MCP tool implementation
        using the AsyncServiceBridge. It shows how the bridge eliminates much of the
        boilerplate code needed for service access and error handling.

        Args:
            method: MCP method name to handle
            params: Method parameters from MCP request
            config_overrides: Optional configuration overrides

        Returns:
            JSON-RPC compatible response

        Example:
            This replaces the complex context management with a simple pattern:
            >>> # Instead of complex async context management:
            >>> # async with async_request_context(...) as ctx:
            >>> #     omnidexer = await ctx.get_service(OmnidexerProtocol)
            >>> #     results = omnidexer.search(query)
            >>>
            >>> # Use the bridge pattern:
            >>> async with create_mcp_service_context(method) as ctx:
            ...     results = await ctx.search_spells(query)
        """
        try:
            # Create configuration from overrides
            config = None
            if config_overrides:
                try:
                    from ..core.config.unified_config import get_app_config

                    base_config = get_app_config()
                    config = base_config.model_copy(update=config_overrides)
                except Exception as e:
                    logger.warning(f"Failed to create config override: {e}")

            # Sources are handled by the bridge context

            # Use bridge to create tool context with simplified API
            # Convert ApplicationConfig to dict if needed
            config_dict = config.model_dump() if config else None

            async with create_mcp_service_context(
                operation_name=method,
                config_overrides=config_dict,
            ) as ctx:
                logger.info(
                    f"Handling MCP request {method} with bridge context {ctx.request_id}"
                )

                # Route to bridge-based handlers
                if method == "search_spells":
                    result = await self._handle_search_spells_bridge(params, ctx)
                elif method == "search_creatures":
                    result = await self._handle_search_creatures_bridge(params, ctx)
                elif method == "resolve_adventure":
                    result = await self._handle_resolve_adventure_bridge(params, ctx)
                elif method == "resolve_book":
                    result = await self._handle_resolve_book_bridge(params, ctx)
                else:
                    # Fall back to the full handler for methods not yet migrated
                    return await self.handle_request(method, params, config_overrides)

                # Handle errors from context
                if ctx.has_errors:
                    errors = ctx.get_errors()
                    return {
                        "error": {
                            "code": -32603,
                            "message": "Request completed with errors",
                            "data": [error.to_json_rpc_error() for error in errors],
                        }
                    }

                # Success response with optional performance data
                response = {"result": result}
                if self.performance_monitoring:
                    response["_performance"] = {
                        "context_id": str(ctx.request_id),
                        "metrics": ctx.request_context.metrics.model_dump(),
                    }

                return response

        except Exception as e:
            logger.error(
                f"Bridge-based MCP request {method} failed: {e}", exc_info=True
            )
            return {
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {e}",
                    "data": {"method": method},
                }
            }

    # Bridge-based handler examples
    # These show the simplified patterns using MCPServiceContext

    async def _handle_search_spells_bridge(
        self, params: dict[str, Any], ctx: MCPServiceContext
    ) -> dict[str, Any]:
        """Handle spell search using bridge patterns.

        This demonstrates how the bridge simplifies MCP tool implementation
        by providing high-level helpers and automatic error handling.
        """
        from .async_service_bridge import MCPServiceContext

        query = params.get("query", "")
        sources = params.get("sources")
        limit = params.get("limit", 20)  # Default to 20 if not provided

        # Ensure limit is an integer
        if not isinstance(limit, int):
            limit = 20

        # Use bridge helper - much simpler than manual service access
        result = await ctx.search_spells(query, sources=sources, limit=limit)

        # The bridge method returns a dict, not a list
        return result

    async def _handle_search_creatures_bridge(
        self, params: dict[str, Any], ctx: MCPServiceContext
    ) -> dict[str, Any]:
        """Handle creature search using bridge patterns."""
        from .async_service_bridge import MCPServiceContext

        query = params.get("query", "")
        sources = params.get("sources")
        limit = params.get("limit", 20)  # Default to 20 if not provided

        # Ensure limit is an integer
        if not isinstance(limit, int):
            limit = 20

        # Use bridge helper
        result = await ctx.search_creatures(query, sources=sources, limit=limit)

        # The bridge method returns a dict, not a list
        return result

    async def _handle_resolve_adventure_bridge(
        self, params: dict[str, Any], ctx: MCPServiceContext
    ) -> dict[str, Any]:
        """Handle adventure resolution using bridge patterns."""
        from .async_service_bridge import MCPServiceContext

        adventure_name = params.get("adventure_name", "")

        if not adventure_name:
            error = MCPError(
                message="adventure_name parameter is required",
                error_code=MCPErrorCode.INVALID_PARAMS,
                category=ErrorCategory.VALIDATION,
                severity=ErrorSeverity.ERROR,
            )
            await ctx.add_error(error)
            return {"adventure": None, "error": "adventure_name parameter is required"}

        # Use bridge helper
        adventure = await ctx.resolve_adventure(adventure_name)

        if adventure:
            return {
                "adventure": adventure.model_dump()
                if hasattr(adventure, "model_dump")
                else adventure.__dict__,
                "source": adventure.source.abbreviation
                if hasattr(adventure, "source")
                else None,
                "name": adventure_name,
            }
        else:
            return {
                "adventure": None,
                "error": f"Adventure '{adventure_name}' not found",
                "name": adventure_name,
            }

    async def _handle_resolve_book_bridge(
        self, params: dict[str, Any], ctx: MCPServiceContext
    ) -> dict[str, Any]:
        """Handle book resolution using bridge patterns."""
        from .async_service_bridge import MCPServiceContext

        book_name = params.get("book_name", "")

        if not book_name:
            error = MCPError(
                message="book_name parameter is required",
                error_code=MCPErrorCode.INVALID_PARAMS,
                category=ErrorCategory.VALIDATION,
                severity=ErrorSeverity.ERROR,
            )
            await ctx.add_error(error)
            return {"book": None, "error": "book_name parameter is required"}

        # Use bridge helper for book listing - resolve_book doesn't exist
        books_result = await ctx.list_books()

        # Find the specific book by name
        book = None
        for book_info in books_result.get("content", []):
            if book_info.get("name", "").lower() == book_name.lower():
                book = book_info
                break

        if book:
            return {
                "book": book,
                "source": book.get("source"),
                "name": book_name,
            }
        else:
            return {
                "book": None,
                "error": f"Book '{book_name}' not found",
                "name": book_name,
            }

    async def get_bridge_metrics(self) -> dict[str, Any]:
        """Get performance metrics from the service bridge.

        Returns:
            Metrics for bridge usage and performance
        """
        # Service bridge doesn't exist anymore - return empty metrics
        return {}

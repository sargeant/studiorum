"""
MCP-specific async service bridge for simplified tool development.

This module provides a simplified async service bridge specifically designed for MCP tool
development, building on the robust AsyncRequestContext infrastructure while providing
a more convenient interface for common MCP operations.

Key features:
- Simplified service access patterns for MCP tools
- Automatic error handling and conversion to MCP error formats
- Performance monitoring integration
- Request-scoped service containers
- Hot-reload configuration support

This bridge leverages the existing AsyncRequestContext infrastructure and serves as a
convenience layer to reduce boilerplate code in MCP tool implementations.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from ..core.context import AsyncRequestContext, async_request_context
from ..core.error_types import (
    ContentNotFoundError,
    ErrorCategory,
    ErrorSeverity,
    MCPError,
    MCPErrorCode,
    MCPException,
)
from ..core.logging import get_logger
from ..core.models.content import BaseContent
from ..core.result import Error, Result, Success

logger = get_logger(__name__)

T = TypeVar("T")


class MCPServiceContext(BaseModel):
    """
    Simplified MCP service context that wraps AsyncRequestContext.

    This context provides simplified access to services through the AsyncRequestContext
    infrastructure while offering high-level helper methods that reduce complexity
    full AsyncRequestContext to reduce complexity for MCP tool implementers.

    The context automatically handles:
    - Service resolution and caching
    - Error conversion to MCP-compatible formats
    - Performance monitoring
    - Request lifecycle management

    Examples:
        Basic usage:
        >>> async with create_mcp_service_context("search_spells") as ctx:
        ...     results = await ctx.search_spells("fireball")

        With configuration override:
        >>> async with create_mcp_service_context(
        ...     "search_creatures",
        ...     config_overrides={"sources": ["phb", "mm"]}
        ... ) as ctx:
        ...     results = await ctx.search_creatures("dragon")
    """

    # Context identification
    operation_name: str
    request_context: AsyncRequestContext

    # Configuration
    config_overrides: dict[str, Any] = Field(default_factory=dict)
    enable_hot_reload: bool = False

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def __init__(self, request_context: AsyncRequestContext, **data: Any) -> None:
        """Initialize MCP service context with request context."""
        super().__init__(request_context=request_context, **data)

    async def __aenter__(self) -> MCPServiceContext:
        """Async context manager entry."""
        await self.request_context.__aenter__()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.request_context.__aexit__(exc_type, exc_val, exc_tb)

    # High-level service operations for common MCP patterns

    async def search_spells(
        self,
        query: str,
        sources: list[str] | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        """
        Search for spells with automatic error handling.

        Args:
            query: Search query string
            sources: Optional list of source abbreviations to filter by
            limit: Maximum number of results to return

        Returns:
            Dictionary with search results and metadata

        Raises:
            MCPException: If search fails
        """
        try:
            from ..core.api import ModernContextualAPI

            if sources:
                self.request_context.sources.extend(sources)

            result = await ModernContextualAPI.search_spells_async(
                query,
                sources=self.request_context.sources
                if self.request_context.sources
                else None,
            )

            if result.is_success():
                spells = result.unwrap()
                self.request_context.record_cache_hit()
                return {
                    "spells": [
                        spell.model_dump()
                        if hasattr(spell, "model_dump")
                        else spell.__dict__
                        for spell in spells
                    ],
                    "total": len(spells),
                    "sources_used": self.request_context.sources,
                    "query": query,
                }
            else:
                error = (
                    result.error
                    if isinstance(result, Error)
                    else ContentNotFoundError(message="Unexpected result type")
                )
                await self.request_context.add_async_error(error)
                self.request_context.record_cache_miss()
                return {
                    "spells": [],
                    "error": error.message,
                    "suggestions": getattr(error, "suggestions", []) or [],
                    "query": query,
                }

        except Exception as e:
            error = MCPError(
                message=f"Spell search failed: {e}",
                error_code=MCPErrorCode.INTERNAL_ERROR,
                category=ErrorCategory.PROCESSING,
                severity=ErrorSeverity.ERROR,
            )
            await self.request_context.add_async_error(error)
            raise MCPException(error) from e

    async def search_creatures(
        self,
        query: str,
        sources: list[str] | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        """
        Search for creatures with automatic error handling.

        Args:
            query: Search query string
            sources: Optional list of source abbreviations to filter by
            limit: Maximum number of results to return

        Returns:
            Dictionary with search results and metadata

        Raises:
            MCPException: If search fails
        """
        try:
            from ..core.api import ModernContextualAPI

            if sources:
                self.request_context.sources.extend(sources)

            result = await ModernContextualAPI.search_creatures_async(
                query,
                sources=self.request_context.sources
                if self.request_context.sources
                else None,
            )

            if result.is_success():
                creatures = result.unwrap()
                self.request_context.record_cache_hit()
                return {
                    "creatures": [
                        creature.model_dump()
                        if hasattr(creature, "model_dump")
                        else creature.__dict__
                        for creature in creatures
                    ],
                    "total": len(creatures),
                    "sources_used": self.request_context.sources,
                    "query": query,
                }
            else:
                error = (
                    result.error
                    if isinstance(result, Error)
                    else ContentNotFoundError(message="Unexpected result type")
                )
                await self.request_context.add_async_error(error)
                self.request_context.record_cache_miss()
                return {
                    "creatures": [],
                    "error": error.message,
                    "suggestions": getattr(error, "suggestions", []) or [],
                    "query": query,
                }

        except Exception as e:
            error = MCPError(
                message=f"Creature search failed: {e}",
                error_code=MCPErrorCode.INTERNAL_ERROR,
                category=ErrorCategory.PROCESSING,
                severity=ErrorSeverity.ERROR,
            )
            await self.request_context.add_async_error(error)
            raise MCPException(error) from e

    async def search_content(
        self,
        query: str,
        content_type: str,
        sources: list[str] | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        """
        Search for any content type with automatic error handling.

        Args:
            query: Search query string
            content_type: Type of content to search for (e.g., "spell", "creature", "item")
            sources: Optional list of source abbreviations to filter by
            limit: Maximum number of results to return

        Returns:
            Dictionary with search results and metadata

        Raises:
            MCPException: If search fails or content_type is invalid
        """
        try:
            from ..core.api import ModernContextualAPI

            if not content_type:
                raise MCPException(
                    MCPError(
                        message="content_type parameter is required",
                        error_code=MCPErrorCode.INVALID_PARAMS,
                        category=ErrorCategory.VALIDATION,
                        severity=ErrorSeverity.ERROR,
                    )
                )

            if sources:
                self.request_context.sources.extend(sources)

            result = await ModernContextualAPI.search_content_async(
                query,
                content_type,
                sources=self.request_context.sources
                if self.request_context.sources
                else None,
            )

            if result.is_success():
                content = result.unwrap()
                self.request_context.record_cache_hit()
                return {
                    "content": [
                        item.model_dump()
                        if hasattr(item, "model_dump")
                        else item.__dict__
                        for item in content
                    ],
                    "total": len(content),
                    "content_type": content_type,
                    "sources_used": self.request_context.sources,
                    "query": query,
                }
            else:
                error = (
                    result.error
                    if isinstance(result, Error)
                    else ContentNotFoundError(message="Unexpected result type")
                )
                await self.request_context.add_async_error(error)
                self.request_context.record_cache_miss()
                return {
                    "content": [],
                    "error": error.message,
                    "suggestions": getattr(error, "suggestions", []) or [],
                    "content_type": content_type,
                    "query": query,
                }

        except MCPException:
            raise
        except Exception as e:
            error = MCPError(
                message=f"Content search failed: {e}",
                error_code=MCPErrorCode.INTERNAL_ERROR,
                category=ErrorCategory.PROCESSING,
                severity=ErrorSeverity.ERROR,
            )
            await self.request_context.add_async_error(error)
            raise MCPException(error) from e

    async def resolve_adventure(
        self,
        adventure_name: str,
        include_appendices: bool = False,
    ) -> dict[str, Any]:
        """
        Resolve adventure by name with automatic error handling.

        Args:
            adventure_name: Name or identifier of the adventure
            include_appendices: Whether to include appendix data

        Returns:
            Dictionary with adventure data and metadata

        Raises:
            MCPException: If adventure resolution fails
        """
        try:
            from ..core.api import ModernContextualAPI

            if not adventure_name:
                raise MCPException(
                    MCPError(
                        message="adventure_name parameter is required",
                        error_code=MCPErrorCode.INVALID_PARAMS,
                        category=ErrorCategory.VALIDATION,
                        severity=ErrorSeverity.ERROR,
                    )
                )

            result = await ModernContextualAPI.resolve_adventure_async(
                adventure_name, enable_performance_monitoring=True
            )

            if result.is_success():
                adventure = result.unwrap()
                self.request_context.record_cache_hit()

                response_data = {
                    "adventure": adventure.model_dump()
                    if hasattr(adventure, "model_dump")
                    else adventure.__dict__,
                    "source": adventure.source.abbreviation
                    if hasattr(adventure, "source")
                    else None,
                    "chapters": len(adventure.contents)
                    if hasattr(adventure, "contents")
                    else 0,
                    "name": adventure_name,
                }

                # Add appendices if requested
                if include_appendices:
                    try:
                        # Appendix generation would be implemented using the service container
                        response_data["appendices"] = {
                            "note": "Appendix generation not yet implemented"
                        }
                    except Exception as e:
                        logger.warning(f"Failed to generate appendices: {e}")

                return response_data
            else:
                error = (
                    result.error
                    if isinstance(result, Error)
                    else ContentNotFoundError(message="Unexpected result type")
                )
                await self.request_context.add_async_error(error)
                self.request_context.record_cache_miss()
                return {
                    "adventure": None,
                    "error": error.message,
                    "suggestions": getattr(error, "suggestions", []) or [],
                    "name": adventure_name,
                }

        except MCPException:
            raise
        except Exception as e:
            error = MCPError(
                message=f"Adventure resolution failed: {e}",
                error_code=MCPErrorCode.INTERNAL_ERROR,
                category=ErrorCategory.PROCESSING,
                severity=ErrorSeverity.ERROR,
            )
            await self.request_context.add_async_error(error)
            raise MCPException(error) from e

    async def list_books(self, sources: list[str] | None = None) -> dict[str, Any]:
        """
        List available books with automatic error handling.

        Args:
            sources: Optional list of source abbreviations to filter by

        Returns:
            Dictionary with book list and metadata

        Raises:
            MCPException: If book listing fails
        """
        try:
            from ..core.models.content import ContentType
            from ..core.services.protocols import OmnidexerProtocol

            if sources:
                self.request_context.sources.extend(sources)

            # Get omnidexer through service container
            omnidexer = await self.request_context.get_service(OmnidexerProtocol)  # type: ignore[type-abstract]
            self.request_context.record_async_operation()

            # Get books by content type
            books = omnidexer.get_all_by_type(ContentType.BOOK)

            # Apply source filtering if specified
            if self.request_context.sources:
                books = [
                    book
                    for book in books
                    if hasattr(book, "source")
                    and book.source.abbreviation in self.request_context.sources
                ]

            self.request_context.record_cache_hit()
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
                "sources_used": self.request_context.sources,
            }

        except Exception as e:
            error = MCPError(
                message=f"Book listing failed: {e}",
                error_code=MCPErrorCode.INTERNAL_ERROR,
                category=ErrorCategory.PROCESSING,
                severity=ErrorSeverity.ERROR,
            )
            await self.request_context.add_async_error(error)
            raise MCPException(error) from e

    # Service access methods (delegated to AsyncRequestContext)

    async def get_service(self, protocol: type[T]) -> T:
        """
        Get service from the underlying request context.

        Args:
            protocol: Service protocol type to get

        Returns:
            Service instance implementing the protocol
        """
        return await self.request_context.get_service(protocol)  # type: ignore[type-var]

    # Context properties and utilities

    @property
    def request_id(self) -> UUID:
        """Get the request ID from the underlying context."""
        return self.request_context.request_id

    @property
    def duration_ms(self) -> float | None:
        """Get request duration in milliseconds."""
        return self.request_context.duration_ms

    @property
    def has_errors(self) -> bool:
        """Check if the request context has any errors."""
        return self.request_context.has_errors()

    def get_errors(self) -> list[MCPError]:
        """Get all errors from the request context."""
        return self.request_context.get_errors()

    async def add_error(self, error: MCPError) -> None:
        """Add an error to the request context."""
        await self.request_context.add_async_error(error)


class MCPToolBase:
    """
    Base class for MCP tools with integrated service access.

    This base class provides a standard pattern for MCP tools that need to access
    services through the service container. It eliminates boilerplate code for
    service container integration and provides consistent error handling.

    Examples:
        Creating a custom MCP tool:
        >>> class MyCustomTool(MCPToolBase):
        ...     async def execute(self, **params: Any) -> dict[str, Any]:
        ...         async with self.create_context("my_tool") as ctx:
        ...             results = await ctx.search_spells(params["query"])
        ...             return {"results": results}

        With configuration overrides:
        >>> tool = MyCustomTool()
        >>> result = await tool.execute_with_config(
        ...     {"sources": ["phb"]},
        ...     query="fireball"
        ... )
    """

    def __init__(self, enable_performance_monitoring: bool = True) -> None:
        """
        Initialize MCP tool base.

        Args:
            enable_performance_monitoring: Whether to enable performance tracking
        """
        self.performance_monitoring = enable_performance_monitoring

    @asynccontextmanager
    async def create_context(
        self,
        operation_name: str,
        config_overrides: dict[str, Any] | None = None,
        enable_hot_reload: bool = False,
    ) -> AsyncIterator[MCPServiceContext]:
        """
        Create an MCP service context for this tool operation.

        Args:
            operation_name: Name of the operation for logging and metrics
            config_overrides: Optional configuration overrides
            enable_hot_reload: Whether to enable hot-reload for this operation

        Yields:
            MCPServiceContext ready for use
        """
        # Create underlying request context
        from ..core.config.unified_config import get_app_config

        base_config = None
        if config_overrides:
            try:
                base_config = get_app_config()
                request_config = base_config.model_copy(update=config_overrides)
            except Exception as e:
                logger.warning(f"Failed to create config override: {e}")
                request_config = None
        else:
            request_config = None

        # Build metadata for context
        context_metadata = {
            "operation_name": operation_name,
            "enable_hot_reload": enable_hot_reload,
            "performance_tracking": self.performance_monitoring,
        }

        async with async_request_context(
            config_override=request_config,
            metadata=context_metadata,
        ) as request_ctx:
            # Create MCP service context wrapper
            mcp_ctx = MCPServiceContext(
                operation_name=operation_name,
                request_context=request_ctx,
                config_overrides=config_overrides or {},
                enable_hot_reload=enable_hot_reload,
            )

            try:
                yield mcp_ctx
            except Exception as e:
                logger.error(f"MCP tool {operation_name} failed: {e}", exc_info=True)
                error = MCPError(
                    message=f"Tool execution failed: {e}",
                    error_code=MCPErrorCode.INTERNAL_ERROR,
                    category=ErrorCategory.PROCESSING,
                    severity=ErrorSeverity.ERROR,
                )
                await mcp_ctx.add_error(error)
                raise

    async def execute_with_config(
        self,
        config_overrides: dict[str, Any],
        **params: Any,
    ) -> dict[str, Any]:
        """
        Execute tool with configuration overrides.

        This is a convenience method for tools that need to run with specific
        configuration settings.

        Args:
            config_overrides: Configuration overrides to apply
            **params: Tool-specific parameters

        Returns:
            Tool execution results

        Note:
            Subclasses should override the `execute` method, not this one.
        """
        async with self.create_context(
            operation_name=self.__class__.__name__,
            config_overrides=config_overrides,
        ) as ctx:
            return await self.execute(ctx, **params)

    async def execute(self, ctx: MCPServiceContext, **params: Any) -> dict[str, Any]:
        """
        Execute the tool with the given context and parameters.

        This method should be overridden by subclasses to implement tool-specific logic.

        Args:
            ctx: MCP service context with access to services
            **params: Tool-specific parameters

        Returns:
            Tool execution results

        Raises:
            NotImplementedError: If not overridden by subclass
        """
        raise NotImplementedError("Subclasses must implement the execute method")


# Convenience functions for creating MCP service contexts


@asynccontextmanager
async def create_mcp_service_context(
    operation_name: str,
    config_overrides: dict[str, Any] | None = None,
    enable_hot_reload: bool = False,
    enable_performance_monitoring: bool = True,
) -> AsyncIterator[MCPServiceContext]:
    """
    Create an MCP service context for tool operations.

    This is the main entry point for MCP tools that need to access services
    through the service container. It provides a simplified interface over
    the AsyncRequestContext infrastructure.

    Args:
        operation_name: Name of the operation for logging and metrics
        config_overrides: Optional configuration overrides
        enable_hot_reload: Whether to enable hot-reload for this operation
        enable_performance_monitoring: Whether to enable performance tracking

    Yields:
        MCPServiceContext ready for use

    Examples:
        Basic usage:
        >>> async with create_mcp_service_context("search_spells") as ctx:
        ...     results = await ctx.search_spells("fireball")

        With configuration overrides:
        >>> async with create_mcp_service_context(
        ...     "search_creatures",
        ...     config_overrides={"sources": ["phb", "mm"]}
        ... ) as ctx:
        ...     results = await ctx.search_creatures("dragon")
    """
    # Services are automatically registered when global container is created

    # Create underlying request context
    from ..core.config.unified_config import get_app_config

    base_config = None
    if config_overrides:
        try:
            base_config = get_app_config()
            request_config = base_config.model_copy(update=config_overrides)
        except Exception as e:
            logger.warning(f"Failed to create config override: {e}")
            request_config = None
    else:
        request_config = None

    # Build metadata for context
    context_metadata = {
        "operation_name": operation_name,
        "enable_hot_reload": enable_hot_reload,
        "performance_tracking": enable_performance_monitoring,
    }

    async with async_request_context(
        config_override=request_config,
        metadata=context_metadata,
    ) as request_ctx:
        # Create MCP service context wrapper
        mcp_ctx = MCPServiceContext(
            operation_name=operation_name,
            request_context=request_ctx,
            config_overrides=config_overrides or {},
            enable_hot_reload=enable_hot_reload,
        )

        try:
            logger.info(f"Created MCP service context for {operation_name}")
            yield mcp_ctx
        except Exception as e:
            logger.error(f"MCP operation {operation_name} failed: {e}", exc_info=True)
            error = MCPError(
                message=f"Operation failed: {e}",
                error_code=MCPErrorCode.INTERNAL_ERROR,
                category=ErrorCategory.PROCESSING,
                severity=ErrorSeverity.ERROR,
            )
            await mcp_ctx.add_error(error)
            raise
        finally:
            logger.debug(f"MCP service context for {operation_name} completed")


async def create_direct_async_request_context(
    config_override: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> AsyncRequestContext:
    """
    Create a direct AsyncRequestContext for advanced use cases.

    This function provides direct access to the underlying AsyncRequestContext
    for tools that need more control or don't fit the standard MCP patterns.

    Args:
        config_override: Optional configuration overrides
        metadata: Optional metadata for the context

    Returns:
        AsyncRequestContext ready for use

    Note:
        Most MCP tools should use create_mcp_service_context instead, which
        provides a more convenient interface.
    """
    from ..core.config.unified_config import get_app_config

    request_config = None
    if config_override:
        try:
            base_config = get_app_config()
            request_config = base_config.model_copy(update=config_override)
        except Exception as e:
            logger.warning(f"Failed to create config override: {e}")

    return AsyncRequestContext(
        user_config=request_config,
        metadata=metadata or {},
    )

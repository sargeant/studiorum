"""Content search tools for the Studiorum MCP server.

This module provides content search functionality with <200ms performance targets,
leveraging the PerformanceOptimizedOmnidexer and AsyncRequestContext infrastructure.

Key Features:
- Unified content search with type safety
- Performance-optimized search with <200ms target
- Integration with existing omnidexer infrastructure
- Advanced filtering and pagination support
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Literal

from studiorum.core.logging import get_logger

from ...core.api import ModernContextualAPI
from ...core.context import AsyncRequestContext, async_request_context
from ...core.error_types import (
    ContentNotFoundError,
    ContentNotFoundExceptionError,
    ErrorCategory,
    MCPError,
    MCPErrorCode,
    MCPException,
    ProcessingError,
)
from ...core.models.content import BaseContent
from ...core.result import Result
from ...core.services.protocols import OmnidexerProtocol

logger = get_logger(__name__)


class ContentSearchResult:
    """Result container for content search operations."""

    def __init__(
        self,
        content: list[BaseContent],
        total: int,
        query: str,
        content_type: str,
        sources_used: list[str],
        duration_ms: float,
        cached: bool = False,
    ):
        self.content = content
        self.total = total
        self.query = query
        self.content_type = content_type
        self.sources_used = sources_used
        self.duration_ms = duration_ms
        self.cached = cached

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for MCP response."""
        return {
            "content": [
                item.model_dump() if hasattr(item, "model_dump") else item.__dict__
                for item in self.content
            ],
            "total": self.total,
            "query": self.query,
            "content_type": self.content_type,
            "sources_used": self.sources_used,
            "performance": {
                "duration_ms": self.duration_ms,
                "cached": self.cached,
                "target_met": self.duration_ms < 200.0,
            },
        }


class PerformantContentSearcher:
    """High-performance content search with <200ms targets."""

    def __init__(self) -> None:
        self._cache: dict[str, ContentSearchResult] = {}
        self._cache_ttl: dict[str, float] = {}
        self.cache_duration = 300  # 5 minutes

    async def search_content_async(
        self,
        content_type: Literal["spells", "creatures", "items", "adventures", "books"],
        query: str | None = None,
        sources: list[str] | None = None,
        filters: dict[str, Any] | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> ContentSearchResult:
        """Search content with performance monitoring.

        Args:
            content_type: Type of content to search
            query: Search query string
            sources: List of source abbreviations
            filters: Additional filtering criteria
            limit: Maximum results to return
            offset: Pagination offset

        Returns:
            ContentSearchResult with performance metrics

        Raises:
            MCPError: If search fails or times out
        """
        start_time = time.time()

        try:
            # Generate cache key
            cache_key = self._generate_cache_key(
                content_type, query, sources, filters, limit, offset
            )

            # Check cache first
            cached_result = self._get_cached_result(cache_key)
            if cached_result:
                duration_ms = (time.time() - start_time) * 1000
                cached_result.duration_ms = duration_ms
                cached_result.cached = True
                return cached_result

            # Perform search with timeout (60 seconds for initial cold start)
            # The first search may take longer while the omnidexer loads all data
            timeout_seconds = 60.0

            async def perform_search() -> list[BaseContent]:
                async with async_request_context() as ctx:
                    if sources:
                        ctx.sources.extend(sources)

                    # Route to appropriate search method
                    if content_type == "spells":
                        return await self._search_spells_async(
                            query, sources, filters, limit, offset, ctx
                        )
                    elif content_type == "creatures":
                        return await self._search_creatures_async(
                            query, sources, filters, limit, offset, ctx
                        )
                    elif content_type == "items":
                        return await self._search_items_async(
                            query, sources, filters, limit, offset, ctx
                        )
                    elif content_type == "adventures":
                        return await self._search_adventures_async(
                            query, sources, filters, limit, offset, ctx
                        )
                    elif content_type == "books":
                        return await self._search_books_async(
                            query, sources, filters, limit, offset, ctx
                        )
                    else:
                        raise ContentNotFoundError(
                            f"Unknown content type: {content_type}"
                        )

            # Apply timeout wrapper
            result = await asyncio.wait_for(perform_search(), timeout=timeout_seconds)

            duration_ms = (time.time() - start_time) * 1000

            # Create result object
            search_result = ContentSearchResult(
                content=result if isinstance(result, list) else [],
                total=len(result) if isinstance(result, list) else 0,
                query=query or "",
                content_type=content_type,
                sources_used=[],  # Will be populated by the search method
                duration_ms=duration_ms,
                cached=False,
            )

            # Cache the result
            self._cache_result(cache_key, search_result)

            # Log performance
            if duration_ms > 200:
                logger.warning(
                    f"Search exceeded 200ms target: {duration_ms:.1f}ms "
                    f"for {content_type} query '{query}'"
                )
            else:
                logger.debug(
                    f"Search completed in {duration_ms:.1f}ms "
                    f"for {content_type} query '{query}'"
                )

            return search_result

        except TimeoutError:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(f"Search timed out after {duration_ms:.1f}ms")
            mcp_error = MCPError(
                message=f"Search timed out for {content_type}",
                error_code=MCPErrorCode.PROCESSING_ERROR,
                category=ErrorCategory.PROCESSING,
            )
            raise MCPException(mcp_error)

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(f"Search failed after {duration_ms:.1f}ms: {e}")
            mcp_error = MCPError(
                message=f"Search failed: {e}",
                error_code=MCPErrorCode.PROCESSING_ERROR,
                category=ErrorCategory.PROCESSING,
            )
            raise MCPException(mcp_error)

    async def _search_spells_async(
        self,
        query: str | None,
        sources: list[str] | None,
        filters: dict[str, Any] | None,
        limit: int,
        offset: int,
        ctx: AsyncRequestContext,
    ) -> list[BaseContent]:
        """Search for spells with filtering."""
        result = await ModernContextualAPI.search_spells_async(
            query or "", sources=ctx.sources if ctx.sources else None
        )

        if result.is_success():
            spells = result.unwrap()

            # Apply additional filters
            if filters:
                spells = self._apply_spell_filters(spells, filters)

            # Apply pagination
            end_idx = offset + limit
            return spells[offset:end_idx]
        else:
            from ...core.result import Error as ResultError

            if isinstance(result, ResultError):
                error_msg = (
                    result.error.message
                    if hasattr(result.error, "message")
                    else str(result.error)
                )
            else:
                error_msg = "Unknown error"
            content_error = ContentNotFoundError(
                message=f"Spell search failed: {error_msg}",
                error_code=MCPErrorCode.CONTENT_NOT_FOUND,
                category=ErrorCategory.USER_ERROR,
            )
            raise ContentNotFoundExceptionError(content_error)

    async def _search_creatures_async(
        self,
        query: str | None,
        sources: list[str] | None,
        filters: dict[str, Any] | None,
        limit: int,
        offset: int,
        ctx: AsyncRequestContext,
    ) -> list[BaseContent]:
        """Search for creatures with filtering."""
        result = await ModernContextualAPI.search_creatures_async(
            query or "", sources=ctx.sources if ctx.sources else None
        )

        if result.is_success():
            creatures = result.unwrap()

            # Apply additional filters
            if filters:
                creatures = self._apply_creature_filters(creatures, filters)

            # Apply pagination
            end_idx = offset + limit
            return creatures[offset:end_idx]
        else:
            from ...core.result import Error as ResultError

            if isinstance(result, ResultError):
                error_msg = (
                    result.error.message
                    if hasattr(result.error, "message")
                    else str(result.error)
                )
            else:
                error_msg = "Unknown error"
            content_error = ContentNotFoundError(
                message=f"Creature search failed: {error_msg}",
                error_code=MCPErrorCode.CONTENT_NOT_FOUND,
                category=ErrorCategory.USER_ERROR,
            )
            raise ContentNotFoundExceptionError(content_error)

    async def _search_items_async(
        self,
        query: str | None,
        sources: list[str] | None,
        filters: dict[str, Any] | None,
        limit: int,
        offset: int,
        ctx: AsyncRequestContext,
    ) -> list[BaseContent]:
        """Search for items with filtering."""
        # Use generic content search for items
        result = await ModernContextualAPI.search_content_async(
            query or "", "items", sources=ctx.sources if ctx.sources else None
        )

        if result.is_success():
            items = result.unwrap()

            # Apply additional filters
            if filters:
                items = self._apply_item_filters(items, filters)

            # Apply pagination
            end_idx = offset + limit
            return items[offset:end_idx]
        else:
            from ...core.result import Error as ResultError

            if isinstance(result, ResultError):
                error_msg = (
                    result.error.message
                    if hasattr(result.error, "message")
                    else str(result.error)
                )
            else:
                error_msg = "Unknown error"
            content_error = ContentNotFoundError(
                message=f"Item search failed: {error_msg}",
                error_code=MCPErrorCode.CONTENT_NOT_FOUND,
                category=ErrorCategory.USER_ERROR,
            )
            raise ContentNotFoundExceptionError(content_error)

    async def _search_adventures_async(
        self,
        query: str | None,
        sources: list[str] | None,
        filters: dict[str, Any] | None,
        limit: int,
        offset: int,
        ctx: AsyncRequestContext,
    ) -> list[BaseContent]:
        """Search for adventures with filtering."""
        result = await ModernContextualAPI.search_content_async(
            query or "",
            content_type="adventure",
            sources=ctx.sources if ctx.sources else None,
        )

        if result.is_success():
            adventures = result.unwrap()

            # Apply additional filters
            if filters:
                adventures = self._apply_adventure_filters(adventures, filters)

            # Apply pagination
            end_idx = offset + limit
            return adventures[offset:end_idx]
        else:
            from ...core.result import Error as ResultError

            if isinstance(result, ResultError):
                error_msg = (
                    result.error.message
                    if hasattr(result.error, "message")
                    else str(result.error)
                )
            else:
                error_msg = "Unknown error"
            content_error = ContentNotFoundError(
                message=f"Adventure search failed: {error_msg}",
                error_code=MCPErrorCode.CONTENT_NOT_FOUND,
                category=ErrorCategory.USER_ERROR,
            )
            raise ContentNotFoundExceptionError(content_error)

    async def _search_books_async(
        self,
        query: str | None,
        sources: list[str] | None,
        filters: dict[str, Any] | None,
        limit: int,
        offset: int,
        ctx: AsyncRequestContext,
    ) -> list[BaseContent]:
        """Search for books with filtering."""
        result = await ModernContextualAPI.search_content_async(
            query or "",
            content_type="book",
            sources=ctx.sources if ctx.sources else None,
        )

        if result.is_success():
            books = result.unwrap()

            # Apply additional filters
            if filters:
                books = self._apply_book_filters(books, filters)

            # Apply pagination
            end_idx = offset + limit
            return books[offset:end_idx]
        else:
            from ...core.result import Error as ResultError

            if isinstance(result, ResultError):
                error_msg = (
                    result.error.message
                    if hasattr(result.error, "message")
                    else str(result.error)
                )
            else:
                error_msg = "Unknown error"
            content_error = ContentNotFoundError(
                message=f"Book search failed: {error_msg}",
                error_code=MCPErrorCode.CONTENT_NOT_FOUND,
                category=ErrorCategory.USER_ERROR,
            )
            raise ContentNotFoundExceptionError(content_error)

    def _apply_spell_filters(
        self, spells: list[BaseContent], filters: dict[str, Any]
    ) -> list[BaseContent]:
        """Apply spell-specific filters."""
        filtered = spells

        if "level" in filters:
            level = filters["level"]
            filtered = [
                spell
                for spell in filtered
                if hasattr(spell, "level") and spell.level == level
            ]

        if "school" in filters:
            school = filters["school"].lower()
            filtered = [
                spell
                for spell in filtered
                if (hasattr(spell, "school") and spell.school.lower() == school)
            ]

        if "ritual" in filters:
            is_ritual = filters["ritual"]
            filtered = [
                spell
                for spell in filtered
                if hasattr(spell, "ritual") and spell.ritual == is_ritual
            ]

        return filtered

    def _apply_creature_filters(
        self, creatures: list[BaseContent], filters: dict[str, Any]
    ) -> list[BaseContent]:
        """Apply creature-specific filters."""
        filtered = creatures

        if "cr_min" in filters:
            cr_min = filters["cr_min"]
            filtered = [
                creature
                for creature in filtered
                if (hasattr(creature, "cr") and self._parse_cr(creature.cr) >= cr_min)
            ]

        if "cr_max" in filters:
            cr_max = filters["cr_max"]
            filtered = [
                creature
                for creature in filtered
                if (hasattr(creature, "cr") and self._parse_cr(creature.cr) <= cr_max)
            ]

        if "creature_type" in filters:
            creature_type = filters["creature_type"].lower()
            filtered = [
                creature
                for creature in filtered
                if (
                    hasattr(creature, "type") and creature.type.lower() == creature_type
                )
            ]

        return filtered

    def _apply_item_filters(
        self, items: list[BaseContent], filters: dict[str, Any]
    ) -> list[BaseContent]:
        """Apply item-specific filters."""
        filtered = items

        if "rarity" in filters:
            rarity = filters["rarity"].lower()
            filtered = [
                item
                for item in filtered
                if (hasattr(item, "rarity") and item.rarity.lower() == rarity)
            ]

        if "type" in filters:
            item_type = filters["type"].lower()
            filtered = [
                item
                for item in filtered
                if (hasattr(item, "type") and item.type.lower() == item_type)
            ]

        return filtered

    def _apply_adventure_filters(
        self, adventures: list[BaseContent], filters: dict[str, Any]
    ) -> list[BaseContent]:
        """Apply adventure-specific filters."""
        # Adventure filters could include level range, setting, etc.
        return adventures

    def _apply_book_filters(
        self, books: list[BaseContent], filters: dict[str, Any]
    ) -> list[BaseContent]:
        """Apply book-specific filters."""
        # Book filters could include publication year, type, etc.
        return books

    def _parse_cr(self, cr_value: str | int | float) -> float:
        """Parse challenge rating to float for comparison."""
        if isinstance(cr_value, int | float):
            return float(cr_value)

        if isinstance(cr_value, str):
            if "/" in cr_value:
                # Handle fractional CR like "1/4"
                parts = cr_value.split("/")
                return float(parts[0]) / float(parts[1])
            else:
                return float(cr_value)

        return 0.0

    def _generate_cache_key(
        self,
        content_type: str,
        query: str | None,
        sources: list[str] | None,
        filters: dict[str, Any] | None,
        limit: int,
        offset: int,
    ) -> str:
        """Generate cache key for search parameters."""
        key_parts = [
            content_type,
            query or "",
            ",".join(sorted(sources or [])),
            str(filters) if filters else "",
            str(limit),
            str(offset),
        ]
        return "|".join(key_parts)

    def _get_cached_result(self, cache_key: str) -> ContentSearchResult | None:
        """Get cached search result if still valid."""
        if cache_key in self._cache:
            cache_time = self._cache_ttl.get(cache_key, 0)
            if time.time() - cache_time < self.cache_duration:
                return self._cache[cache_key]
            else:
                # Remove expired entry
                self._cache.pop(cache_key, None)
                self._cache_ttl.pop(cache_key, None)
        return None

    def _cache_result(self, cache_key: str, result: ContentSearchResult) -> None:
        """Cache search result with TTL."""
        self._cache[cache_key] = result
        self._cache_ttl[cache_key] = time.time()

        # Simple cache size management
        if len(self._cache) > 1000:
            # Remove oldest 100 entries
            sorted_keys = sorted(self._cache_ttl.items(), key=lambda x: x[1])[:100]
            for key, _ in sorted_keys:
                self._cache.pop(key, None)
                self._cache_ttl.pop(key, None)


# Global searcher instance
_content_searcher = PerformantContentSearcher()


# Public API functions
async def search_content_performant(
    content_type: Literal["spells", "creatures", "items", "adventures", "books"],
    query: str | None = None,
    sources: list[str] | None = None,
    filters: dict[str, Any] | None = None,
    limit: int = 20,
    offset: int = 0,
) -> dict[str, Any]:
    """High-level content search with performance monitoring.

    Args:
        content_type: Type of content to search
        query: Search query string
        sources: List of source abbreviations
        filters: Additional filtering criteria
        limit: Maximum results to return
        offset: Pagination offset

    Returns:
        Search results with performance metrics
    """
    result = await _content_searcher.search_content_async(
        content_type=content_type,
        query=query,
        sources=sources,
        filters=filters,
        limit=limit,
        offset=offset,
    )

    return result.to_dict()


def get_content_searcher() -> PerformantContentSearcher:
    """Get the global content searcher instance.

    Returns:
        PerformantContentSearcher instance
    """
    return _content_searcher

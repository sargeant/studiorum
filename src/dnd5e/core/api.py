"""Modern high-level API with async protocol-based contexts.

This module provides the modernized high-level API that leverages async request
contexts and protocol-based services for content operations. Designed to support
both CLI usage (with sync wrappers) and MCP server requirements (async-first).

Key Features:
- ModernContextualAPI with async protocol-based services
- Structured error handling with Result patterns
- Performance monitoring and hot-reload support
- Backward compatibility wrappers for existing CLI code
- Protocol validation and runtime compliance checking
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from .context import (
    AsyncRequestContext,
    RequestContext,
    async_request_context,
    performance_monitored_context,
    request_context,
)
from .error_types import (
    ContentNotFoundError,
    ErrorCategory,
    MCPError,
    MCPErrorCode,
)
from .result import Error, Result, Success
from .services.protocols import (
    ContentFactoryProtocol,
    OmnidexerProtocol,
    TagResolverProtocol,
)

if TYPE_CHECKING:
    from .config.unified_config import ApplicationConfig
    from .models.adventures import Adventure
    from .models.base import Content

logger = logging.getLogger(__name__)


class ModernContextualAPI:
    """Modern high-level API with async protocol-based contexts.

    This API provides high-level operations for content search, resolution,
    and processing using async request contexts and protocol-validated services.

    All methods follow the pattern:
    1. Create async request context with configuration/sources
    2. Get protocol-validated services from context
    3. Perform async operations with performance tracking
    4. Return Result objects with structured error handling

    Examples:
        Async content search:
        >>> result = await ModernContextualAPI.search_content_async(
        ...     query="fireball",
        ...     content_type="spell",
        ...     sources=["phb", "xge"]
        ... )
        >>> if result.is_success():
        ...     spells = result.unwrap()

        Adventure resolution with performance monitoring:
        >>> result = await ModernContextualAPI.resolve_adventure_async(
        ...     "lost-mine-of-phandelver",
        ...     enable_performance_monitoring=True
        ... )
    """

    @staticmethod
    async def search_content_async(
        query: str,
        content_type: str,
        sources: list[str] | None = None,
        config_override: ApplicationConfig | None = None,
        enable_hot_reload: bool = False,
    ) -> Result[list[Content], MCPError]:
        """Async search for content with protocol validation and performance monitoring.

        Args:
            query: Search query string
            content_type: Type of content to search for (e.g., "spell", "creature")
            sources: Optional list of content sources to search
            config_override: Optional configuration override for this request
            enable_hot_reload: Whether to enable hot-reload for this context

        Returns:
            Result containing list of matching content or error details
        """
        async with async_request_context(
            config_override=config_override, sources=sources
        ) as ctx:
            try:
                # Protocol-based service access - get resolver with validated services

                # Create resolver with protocol-validated services
                from .resolvers.content_resolver import ContentResolver

                resolver = await ContentResolver.from_context(ctx)

                # Perform async search with performance tracking
                ctx.record_async_operation()
                result = await resolver.search_content_async(query, content_type)

                return result

            except Exception as e:
                error = ContentNotFoundError(message=f"Content search failed: {e}")
                await ctx.add_async_error(error)
                return Error(error)

    @staticmethod
    async def resolve_adventure_async(
        adventure_name: str,
        config_override: ApplicationConfig | None = None,
        enable_performance_monitoring: bool = True,
        include_appendices: bool = False,
    ) -> Result[Adventure, MCPError]:
        """Async adventure resolution with enhanced error handling.

        Args:
            adventure_name: Name or identifier of the adventure
            config_override: Optional configuration override
            enable_performance_monitoring: Whether to enable performance tracking
            include_appendices: Whether to generate appendices for the adventure

        Returns:
            Result containing resolved adventure or error details
        """
        if enable_performance_monitoring:
            context_manager = performance_monitored_context(
                config_override=config_override,
                performance_tracking=enable_performance_monitoring,
            )
        else:
            context_manager = async_request_context(
                config_override=config_override,
            )

        async with context_manager as ctx:
            try:
                # Protocol-validated services
                omnidexer = await ctx.get_service(OmnidexerProtocol)  # type: ignore[type-abstract]

                # Async adventure resolution
                ctx.record_async_operation()

                # Use the omnidexer's search functionality to find the adventure
                search_results = omnidexer.search(adventure_name)

                # Filter for adventures
                adventures = [
                    result
                    for result in search_results
                    if hasattr(result, "adventure")
                    or (hasattr(result, "type") and result.type == "adventure")
                ]

                if not adventures:
                    # Try to get available adventures for suggestions
                    all_content = omnidexer.search("")  # Get all content
                    available_adventures = [
                        content.name if hasattr(content, "name") else str(content)
                        for content in all_content
                        if hasattr(content, "adventure")
                        or (hasattr(content, "type") and content.type == "adventure")
                    ][:5]  # Limit to 5 suggestions

                    error = ContentNotFoundError(
                        message=f"Adventure '{adventure_name}' not found"
                        if available_adventures
                        else f"Adventure '{adventure_name}' not found - no adventures available",
                    )
                    await ctx.add_async_error(error)
                    return Error(error)

                adventure = adventures[0]  # Take the first match

                # Type safety: ensure it's actually an adventure
                from .models.adventures import Adventure

                if not isinstance(adventure, Adventure):
                    # If it's not an Adventure instance, try to create one
                    error = ContentNotFoundError(
                        message=f"Adventure '{adventure_name}' found but invalid type"
                    )
                    await ctx.add_async_error(error)
                    return Error(error)

                # Add appendices if requested using protocol-based services
                if include_appendices:
                    # Appendix generation would be implemented on the content factory
                    # This is a placeholder for the actual implementation
                    pass

                return Success(adventure)

            except Exception as e:
                error = ContentNotFoundError(
                    message=f"Adventure resolution failed: {e}"
                )
                await ctx.add_async_error(error)
                return Error(error)

    @staticmethod
    async def search_spells_async(
        query: str,
        sources: list[str] | None = None,
        config_override: ApplicationConfig | None = None,
    ) -> Result[list[Content], MCPError]:
        """Async spell search convenience method.

        Args:
            query: Spell search query
            sources: Optional content sources to search
            config_override: Optional configuration override

        Returns:
            Result containing matching spells or error details
        """
        return await ModernContextualAPI.search_content_async(
            query=query,
            content_type="spell",
            sources=sources,
            config_override=config_override,
        )

    @staticmethod
    async def search_creatures_async(
        query: str,
        sources: list[str] | None = None,
        config_override: ApplicationConfig | None = None,
    ) -> Result[list[Content], MCPError]:
        """Async creature search convenience method.

        Args:
            query: Creature search query
            sources: Optional content sources to search
            config_override: Optional configuration override

        Returns:
            Result containing matching creatures or error details
        """
        return await ModernContextualAPI.search_content_async(
            query=query,
            content_type="creature",
            sources=sources,
            config_override=config_override,
        )

    @staticmethod
    async def get_character_progression_async(
        character_class: str,
        level: int,
        subclass: str | None = None,
        config_override: ApplicationConfig | None = None,
        analysis_type: str = "basic",
        include_feat_analysis: bool = False,
        include_multiclass_options: bool = False,
        optimization_focus: str | None = None,
    ) -> Result[dict[str, Any], MCPError]:
        """Async character progression lookup with enhanced analysis.

        Args:
            character_class: Name of the character class
            level: Character level
            subclass: Optional subclass name
            config_override: Optional configuration override
            analysis_type: Type of analysis ("basic", "detailed", "optimization")
            include_feat_analysis: Whether to include eligible feat analysis
            include_multiclass_options: Whether to include multiclass options
            optimization_focus: Focus for optimization analysis ("damage", "survivability", "utility", etc.)

        Returns:
            Result containing progression data with optional analysis or error details
        """
        async with async_request_context(config_override=config_override) as ctx:
            try:
                # Get protocol-validated omnidexer
                omnidexer = await ctx.get_service(OmnidexerProtocol)  # type: ignore[type-abstract]

                # Async character progression lookup
                ctx.record_async_operation()

                # Search for class data
                class_results = omnidexer.search(character_class)
                class_data = None

                for result in class_results:
                    if (hasattr(result, "type") and result.type == "class") or (
                        hasattr(result, "character_class")
                        and result.character_class == character_class
                    ):
                        class_data = result
                        break

                if not class_data:
                    error = ContentNotFoundError(
                        message=f"Class '{character_class}' not found"
                    )
                    await ctx.add_async_error(error)
                    return Error(error)

                # Extract basic progression data
                progression_data: dict[str, Any] = {
                    "class": character_class,
                    "level": level,
                    "subclass": subclass,
                    "features": [],  # Would be extracted from class_data
                    "hit_dice": getattr(class_data, "hit_dice", "d8"),
                    "proficiency_bonus": (level - 1) // 4
                    + 2,  # Standard 5e progression
                }

                # Enhanced analysis based on requested type
                if analysis_type in ("detailed", "optimization"):
                    # Get class progression data using enhanced omnidexer methods
                    if hasattr(omnidexer, "get_class_progression_data_async"):
                        class_progression = (
                            await omnidexer.get_class_progression_data_async(
                                character_class, level, subclass
                            )
                        )
                        if class_progression:
                            progression_data["class_progression"] = class_progression

                # Include feat analysis if requested
                if include_feat_analysis:
                    if hasattr(omnidexer, "get_eligible_feats_async"):
                        eligible_feats = await omnidexer.get_eligible_feats_async(
                            character_class, level, subclass
                        )
                        progression_data["eligible_feats"] = eligible_feats
                    else:
                        progression_data["eligible_feats"] = []

                # Include multiclass options if requested
                if include_multiclass_options:
                    if hasattr(omnidexer, "analyze_multiclass_eligibility_async"):
                        multiclass_options = (
                            await omnidexer.analyze_multiclass_eligibility_async(
                                character_class, level
                            )
                        )
                        progression_data["multiclass_options"] = multiclass_options
                    else:
                        progression_data["multiclass_options"] = []

                # Add optimization focus data if provided
                if optimization_focus and analysis_type == "optimization":
                    progression_data["optimization"] = {
                        "focus": optimization_focus,
                        "recommendations": f"Optimization recommendations for {optimization_focus} would be generated here",
                    }

                # Add analysis metadata
                progression_data["analysis"] = {
                    "type": analysis_type,
                    "feat_analysis": include_feat_analysis,
                    "multiclass_analysis": include_multiclass_options,
                    "optimization_focus": optimization_focus,
                }

                return Success(progression_data)

            except Exception as e:
                error = ContentNotFoundError(
                    message=f"Character progression lookup failed: {e}"
                )
                await ctx.add_async_error(error)
                return Error(error)

    # Backward compatibility layer for CLI
    @staticmethod
    def search_content(
        query: str,
        content_type: str,
        sources: list[str] | None = None,
        config_override: ApplicationConfig | None = None,
    ) -> Result[list[Content], MCPError]:
        """Sync wrapper for CLI compatibility."""
        return asyncio.run(
            ModernContextualAPI.search_content_async(
                query, content_type, sources, config_override
            )
        )

    @staticmethod
    def resolve_adventure(
        adventure_name: str,
        config_override: ApplicationConfig | None = None,
        include_appendices: bool = False,
    ) -> Result[Adventure, MCPError]:
        """Sync wrapper for CLI compatibility."""
        return asyncio.run(
            ModernContextualAPI.resolve_adventure_async(
                adventure_name, config_override, include_appendices=include_appendices
            )
        )

    @staticmethod
    def search_spells(
        query: str,
        sources: list[str] | None = None,
        config_override: ApplicationConfig | None = None,
    ) -> Result[list[Content], MCPError]:
        """Sync wrapper for spell search."""
        return asyncio.run(
            ModernContextualAPI.search_spells_async(query, sources, config_override)
        )

    @staticmethod
    def search_creatures(
        query: str,
        sources: list[str] | None = None,
        config_override: ApplicationConfig | None = None,
    ) -> Result[list[Content], MCPError]:
        """Sync wrapper for creature search."""
        return asyncio.run(
            ModernContextualAPI.search_creatures_async(query, sources, config_override)
        )

    @staticmethod
    def get_character_progression(
        character_class: str,
        level: int,
        subclass: str | None = None,
        config_override: ApplicationConfig | None = None,
        analysis_type: str = "basic",
        include_feat_analysis: bool = False,
        include_multiclass_options: bool = False,
        optimization_focus: str | None = None,
    ) -> Result[dict[str, Any], MCPError]:
        """Sync wrapper for character progression."""
        return asyncio.run(
            ModernContextualAPI.get_character_progression_async(
                character_class,
                level,
                subclass,
                config_override,
                analysis_type,
                include_feat_analysis,
                include_multiclass_options,
                optimization_focus,
            )
        )


# Legacy API for existing code
class ContextualAPI(ModernContextualAPI):
    """Legacy alias for backward compatibility."""

    pass


# Convenience functions for common operations
async def search_content_async(
    query: str,
    content_type: str,
    sources: list[str] | None = None,
) -> Result[list[Content], MCPError]:
    """Convenience function for async content search."""
    return await ModernContextualAPI.search_content_async(query, content_type, sources)


def search_content(
    query: str,
    content_type: str,
    sources: list[str] | None = None,
) -> Result[list[Content], MCPError]:
    """Convenience function for sync content search."""
    return ModernContextualAPI.search_content(query, content_type, sources)


async def resolve_adventure_async(adventure_name: str) -> Result[Adventure, MCPError]:
    """Convenience function for async adventure resolution."""
    return await ModernContextualAPI.resolve_adventure_async(adventure_name)


def resolve_adventure(adventure_name: str) -> Result[Adventure, MCPError]:
    """Convenience function for sync adventure resolution."""
    return ModernContextualAPI.resolve_adventure(adventure_name)

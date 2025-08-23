"""MCP tools for rules intelligence.

This module provides MCP tools for D&D 5e rules intelligence, including
cross-reference discovery, rule combination validation, and intelligent
rule search capabilities.
"""

from __future__ import annotations

import time
from typing import Any

from ....core.context import AsyncRequestContext
from ....core.error_types import (
    ContentNotFoundError,
    ErrorCategory,
    MCPError,
    MCPErrorCode,
    MCPException,
    ProcessingError,
)
from ....core.logging import get_logger
from ....core.result import Error, Result, Success
from ....core.services.protocols import OmnidexerProtocol
from ....core.text.tag_resolver import TagResolver
from .rule_intelligence_service import RuleIntelligenceConfig, RuleIntelligenceService

logger = get_logger(__name__)

# Global service instance (will be initialized on first use)
_rule_intelligence_service: RuleIntelligenceService | None = None


async def _get_rule_intelligence_service(
    ctx: AsyncRequestContext,
) -> RuleIntelligenceService:
    """Get or create the rule intelligence service."""
    global _rule_intelligence_service

    if _rule_intelligence_service is None:
        # Get required services from context
        omnidexer = await ctx.get_service(OmnidexerProtocol)  # type: ignore[type-abstract] # Protocol type token - see TYPES.md

        # Create tag resolver (assuming it's available as a singleton or can be created)
        # In a real implementation, this would also come from the service container
        tag_resolver = TagResolver(omnidexer=omnidexer)

        # Create service with default config
        config = RuleIntelligenceConfig()
        from typing import cast

        from studiorum.core.loaders.omnidexer import Omnidexer

        _rule_intelligence_service = RuleIntelligenceService(
            omnidexer=omnidexer,
            tag_resolver=tag_resolver,
            config=config,
        )

        logger.info("Initialized rule intelligence service")

    return _rule_intelligence_service


async def find_rule_cross_references(
    rule_id: str,
    max_depth: int = 2,
    include_analysis: bool = True,
    ctx: AsyncRequestContext | None = None,
) -> dict[str, Any]:
    """Find cross-references for a specific D&D 5e rule.

    This tool discovers relationships between rules, analyzes their interactions,
    and provides comprehensive cross-reference data with performance monitoring.

    Args:
        rule_id: Rule identifier to find references for
        max_depth: Maximum depth for recursive reference discovery (1-5)
        include_analysis: Whether to include complexity and tag analysis
        ctx: Async request context for service access

    Returns:
        Dictionary containing cross-reference data with relationships and analysis

    Raises:
        MCPException: If rule lookup fails or service is unavailable
    """
    start_time = time.time()

    try:
        if not ctx:
            raise MCPException(
                MCPError(
                    message="Request context is required",
                    error_code=MCPErrorCode.INVALID_PARAMS,
                    category=ErrorCategory.USER_ERROR,
                )
            )

        # Validate parameters
        if not rule_id or not rule_id.strip():
            raise MCPException(
                MCPError(
                    message="rule_id parameter is required and cannot be empty",
                    error_code=MCPErrorCode.INVALID_PARAMS,
                    category=ErrorCategory.USER_ERROR,
                )
            )

        if max_depth < 1 or max_depth > 5:
            raise MCPException(
                MCPError(
                    message="max_depth must be between 1 and 5",
                    error_code=MCPErrorCode.INVALID_PARAMS,
                    category=ErrorCategory.USER_ERROR,
                )
            )

        # Get rule intelligence service
        service = await _get_rule_intelligence_service(ctx)

        # Find cross-references
        result = await service.find_rule_cross_references(
            rule_id=rule_id.strip(),
            max_depth=max_depth,
            include_analysis=include_analysis,
        )

        if result.is_error():
            error = result.error if isinstance(result, Error) else result
            if isinstance(error, ProcessingError):
                raise MCPException(
                    MCPError(
                        message=error.message,
                        error_code=MCPErrorCode.CONTENT_NOT_FOUND,
                        category=ErrorCategory.USER_ERROR,
                    )
                )
            else:
                raise MCPException(
                    MCPError(
                        message=f"Cross-reference lookup failed: {error}",
                        error_code=MCPErrorCode.PROCESSING_ERROR,
                        category=ErrorCategory.PROCESSING,
                    )
                )

        cross_ref_data = result.unwrap()

        # Add MCP-specific metadata
        duration_ms = (time.time() - start_time) * 1000
        cross_ref_data["mcp_metadata"] = {
            "tool": "find_rule_cross_references",
            "version": "1.0",
            "request_duration_ms": duration_ms,
            "performance_target_met": duration_ms < 100.0,
            "parameters_used": {
                "rule_id": rule_id,
                "max_depth": max_depth,
                "include_analysis": include_analysis,
            },
        }

        # Record successful operation
        ctx.record_cache_hit() if duration_ms < 50 else ctx.record_cache_miss()

        logger.debug(
            f"Found cross-references for rule {rule_id} in {duration_ms:.1f}ms"
        )

        return cross_ref_data

    except MCPException:
        raise
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        logger.error(
            f"Unexpected error in find_rule_cross_references: {e}", exc_info=True
        )

        if ctx:
            ctx.record_cache_miss()

        raise MCPException(
            MCPError(
                message=f"Unexpected error finding cross-references: {e}",
                error_code=MCPErrorCode.INTERNAL_ERROR,
                category=ErrorCategory.SYSTEM_ERROR,
                data={"request_duration_ms": duration_ms},
            )
        )


async def validate_rule_combination(
    rule_ids: list[str],
    context: dict[str, Any] | None = None,
    ctx: AsyncRequestContext | None = None,
) -> dict[str, Any]:
    """Validate that a combination of D&D 5e rules can work together.

    This tool analyzes rule interactions, detects conflicts and synergies,
    and provides validation results with detailed explanations.

    Args:
        rule_ids: List of rule identifiers to validate together
        context: Optional context (character_class, level, situation, etc.)
        ctx: Async request context for service access

    Returns:
        Dictionary containing validation results with conflicts, synergies, and score

    Raises:
        MCPException: If validation fails or service is unavailable
    """
    start_time = time.time()

    try:
        if not ctx:
            raise MCPException(
                MCPError(
                    message="Request context is required",
                    error_code=MCPErrorCode.INVALID_PARAMS,
                    category=ErrorCategory.USER_ERROR,
                )
            )

        # Validate parameters
        if not rule_ids or not isinstance(rule_ids, list):
            raise MCPException(
                MCPError(
                    message="rule_ids parameter must be a non-empty list",
                    error_code=MCPErrorCode.INVALID_PARAMS,
                    category=ErrorCategory.USER_ERROR,
                )
            )

        if len(rule_ids) < 2:
            raise MCPException(
                MCPError(
                    message="At least 2 rule IDs are required for combination validation",
                    error_code=MCPErrorCode.INVALID_PARAMS,
                    category=ErrorCategory.USER_ERROR,
                )
            )

        if len(rule_ids) > 10:
            raise MCPException(
                MCPError(
                    message="Maximum of 10 rules can be validated at once",
                    error_code=MCPErrorCode.INVALID_PARAMS,
                    category=ErrorCategory.USER_ERROR,
                )
            )

        # Clean and validate rule IDs
        clean_rule_ids = [
            rule_id.strip() for rule_id in rule_ids if rule_id and rule_id.strip()
        ]
        if len(clean_rule_ids) != len(rule_ids):
            raise MCPException(
                MCPError(
                    message="All rule IDs must be non-empty strings",
                    error_code=MCPErrorCode.INVALID_PARAMS,
                    category=ErrorCategory.USER_ERROR,
                )
            )

        # Get rule intelligence service
        service = await _get_rule_intelligence_service(ctx)

        # Validate rule combination
        result = await service.validate_rule_combination(
            rule_ids=clean_rule_ids,
            context=context,
        )

        if result.is_error():
            error = result.error if isinstance(result, Error) else result
            if isinstance(error, ProcessingError):
                raise MCPException(
                    MCPError(
                        message=error.message,
                        error_code=MCPErrorCode.CONTENT_NOT_FOUND,
                        category=ErrorCategory.USER_ERROR,
                    )
                )
            else:
                raise MCPException(
                    MCPError(
                        message=f"Rule combination validation failed: {error}",
                        error_code=MCPErrorCode.PROCESSING_ERROR,
                        category=ErrorCategory.PROCESSING,
                    )
                )

        validation_data = result.unwrap()

        # Add MCP-specific metadata
        duration_ms = (time.time() - start_time) * 1000
        validation_data["mcp_metadata"] = {
            "tool": "validate_rule_combination",
            "version": "1.0",
            "request_duration_ms": duration_ms,
            "performance_target_met": duration_ms < 150.0,
            "parameters_used": {
                "rule_ids": clean_rule_ids,
                "context_provided": context is not None,
                "context_keys": list(context.keys()) if context else [],
            },
        }

        # Record successful operation
        ctx.record_cache_hit() if duration_ms < 75 else ctx.record_cache_miss()

        logger.debug(
            f"Validated rule combination of {len(clean_rule_ids)} rules in {duration_ms:.1f}ms"
        )

        return validation_data

    except MCPException:
        raise
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        logger.error(
            f"Unexpected error in validate_rule_combination: {e}", exc_info=True
        )

        if ctx:
            ctx.record_cache_miss()

        raise MCPException(
            MCPError(
                message=f"Unexpected error validating rule combination: {e}",
                error_code=MCPErrorCode.INTERNAL_ERROR,
                category=ErrorCategory.SYSTEM_ERROR,
                data={"request_duration_ms": duration_ms},
            )
        )


async def search_rules_intelligent(
    query: str,
    rule_types: list[str] | None = None,
    sources: list[str] | None = None,
    complexity_filter: dict[str, float] | None = None,
    include_relationships: bool = True,
    limit: int = 20,
    ctx: AsyncRequestContext | None = None,
) -> dict[str, Any]:
    """Perform intelligent search for D&D 5e rules with enhanced analysis.

    This tool searches for rules with intelligent filtering, relationship analysis,
    and complexity scoring to provide comprehensive rule discovery.

    Args:
        query: Search query string for rule names and content
        rule_types: Optional filter for rule types (action, condition, sense, hazard, status)
        sources: Optional source book filters (PHB, DMG, etc.)
        complexity_filter: Optional complexity range filter with 'min' and 'max' keys
        include_relationships: Whether to include relationship analysis
        limit: Maximum number of results to return (1-50)
        ctx: Async request context for service access

    Returns:
        Dictionary containing search results with intelligent analysis and relationships

    Raises:
        MCPException: If search fails or service is unavailable
    """
    start_time = time.time()

    try:
        if not ctx:
            raise MCPException(
                MCPError(
                    message="Request context is required",
                    error_code=MCPErrorCode.INVALID_PARAMS,
                    category=ErrorCategory.USER_ERROR,
                )
            )

        # Validate parameters
        if not query or not query.strip():
            raise MCPException(
                MCPError(
                    message="query parameter is required and cannot be empty",
                    error_code=MCPErrorCode.INVALID_PARAMS,
                    category=ErrorCategory.USER_ERROR,
                )
            )

        if limit < 1 or limit > 50:
            raise MCPException(
                MCPError(
                    message="limit must be between 1 and 50",
                    error_code=MCPErrorCode.INVALID_PARAMS,
                    category=ErrorCategory.USER_ERROR,
                )
            )

        # Validate rule types if provided
        valid_rule_types = {"action", "condition", "sense", "hazard", "status"}
        if rule_types:
            invalid_types = [
                rt for rt in rule_types if rt.lower() not in valid_rule_types
            ]
            if invalid_types:
                raise MCPException(
                    MCPError(
                        message=f"Invalid rule types: {invalid_types}. Valid types: {list(valid_rule_types)}",
                        error_code=MCPErrorCode.INVALID_PARAMS,
                        category=ErrorCategory.USER_ERROR,
                    )
                )

        # Parse complexity filter
        complexity_tuple = None
        if complexity_filter:
            try:
                min_complexity = complexity_filter.get("min", 0.0)
                max_complexity = complexity_filter.get("max", 1.0)

                if not (0.0 <= min_complexity <= 1.0) or not (
                    0.0 <= max_complexity <= 1.0
                ):
                    raise ValueError("Complexity values must be between 0.0 and 1.0")

                if min_complexity > max_complexity:
                    raise ValueError(
                        "min complexity cannot be greater than max complexity"
                    )

                complexity_tuple = (min_complexity, max_complexity)

            except (KeyError, ValueError, TypeError) as e:
                raise MCPException(
                    MCPError(
                        message=f"Invalid complexity_filter format: {e}",
                        error_code=MCPErrorCode.INVALID_PARAMS,
                        category=ErrorCategory.USER_ERROR,
                    )
                )

        # Get rule intelligence service
        service = await _get_rule_intelligence_service(ctx)

        # Perform intelligent search
        result = await service.search_rules_intelligent(
            query=query.strip(),
            rule_types=[rt.lower() for rt in rule_types] if rule_types else None,
            sources=sources,
            complexity_filter=complexity_tuple,
            include_relationships=include_relationships,
            limit=limit,
        )

        if result.is_error():
            error = result.error if isinstance(result, Error) else result
            if isinstance(error, ProcessingError):
                raise MCPException(
                    MCPError(
                        message=error.message,
                        error_code=MCPErrorCode.CONTENT_NOT_FOUND,
                        category=ErrorCategory.USER_ERROR,
                    )
                )
            else:
                raise MCPException(
                    MCPError(
                        message=f"Intelligent rule search failed: {error}",
                        error_code=MCPErrorCode.PROCESSING_ERROR,
                        category=ErrorCategory.PROCESSING,
                    )
                )

        search_result = result.unwrap()

        # Convert to dictionary with MCP metadata
        search_data = search_result.to_dict()

        duration_ms = (time.time() - start_time) * 1000
        search_data["mcp_metadata"] = {
            "tool": "search_rules_intelligent",
            "version": "1.0",
            "request_duration_ms": duration_ms,
            "performance_target_met": duration_ms < 200.0,
            "parameters_used": {
                "query": query.strip(),
                "rule_types": rule_types,
                "sources": sources,
                "complexity_filter": complexity_filter,
                "include_relationships": include_relationships,
                "limit": limit,
            },
        }

        # Add summary for better user experience
        if search_result.total > 0:
            search_data["search_summary"] = search_result.generate_summary()

        # Record successful operation
        ctx.record_cache_hit() if duration_ms < 100 else ctx.record_cache_miss()

        logger.debug(
            f"Intelligent rule search for '{query}' returned {search_result.total} results in {duration_ms:.1f}ms"
        )

        return search_data

    except MCPException:
        raise
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        logger.error(
            f"Unexpected error in search_rules_intelligent: {e}", exc_info=True
        )

        if ctx:
            ctx.record_cache_miss()

        raise MCPException(
            MCPError(
                message=f"Unexpected error performing intelligent rule search: {e}",
                error_code=MCPErrorCode.INTERNAL_ERROR,
                category=ErrorCategory.SYSTEM_ERROR,
                data={"request_duration_ms": duration_ms},
            )
        )


async def get_rule_suggestions(
    context: dict[str, Any],
    limit: int = 10,
    ctx: AsyncRequestContext | None = None,
) -> dict[str, Any]:
    """Get intelligent rule suggestions based on context.

    This tool provides contextual rule suggestions based on character information,
    current situation, or gameplay context.

    Args:
        context: Context dictionary with keys like character_class, level, situation
        limit: Maximum number of suggestions to return (1-20)
        ctx: Async request context for service access

    Returns:
        Dictionary containing rule suggestions with explanations and priorities

    Raises:
        MCPException: If suggestion generation fails or service is unavailable
    """
    start_time = time.time()

    try:
        if not ctx:
            raise MCPException(
                MCPError(
                    message="Request context is required",
                    error_code=MCPErrorCode.INVALID_PARAMS,
                    category=ErrorCategory.USER_ERROR,
                )
            )

        # Validate parameters
        if not context or not isinstance(context, dict):
            raise MCPException(
                MCPError(
                    message="context parameter must be a non-empty dictionary",
                    error_code=MCPErrorCode.INVALID_PARAMS,
                    category=ErrorCategory.USER_ERROR,
                )
            )

        if limit < 1 or limit > 20:
            raise MCPException(
                MCPError(
                    message="limit must be between 1 and 20",
                    error_code=MCPErrorCode.INVALID_PARAMS,
                    category=ErrorCategory.USER_ERROR,
                )
            )

        # Get rule intelligence service
        service = await _get_rule_intelligence_service(ctx)

        # Get rule suggestions
        result = await service.get_rule_suggestions(context=context)

        if result.is_error():
            error = result.error if isinstance(result, Error) else result
            if isinstance(error, ProcessingError):
                raise MCPException(
                    MCPError(
                        message=error.message,
                        error_code=MCPErrorCode.CONTENT_NOT_FOUND,
                        category=ErrorCategory.USER_ERROR,
                    )
                )
            else:
                raise MCPException(
                    MCPError(
                        message=f"Rule suggestion generation failed: {error}",
                        error_code=MCPErrorCode.PROCESSING_ERROR,
                        category=ErrorCategory.PROCESSING,
                    )
                )

        suggestions = result.unwrap()

        # Limit results
        limited_suggestions = suggestions[:limit]

        # Build response
        duration_ms = (time.time() - start_time) * 1000
        response_data = {
            "suggestions": limited_suggestions,
            "total_found": len(suggestions),
            "total_returned": len(limited_suggestions),
            "context_analyzed": context,
            "mcp_metadata": {
                "tool": "get_rule_suggestions",
                "version": "1.0",
                "request_duration_ms": duration_ms,
                "performance_target_met": duration_ms < 200.0,
                "parameters_used": {
                    "context_keys": list(context.keys()),
                    "limit": limit,
                },
            },
        }

        # Record successful operation
        ctx.record_cache_hit()

        logger.debug(
            f"Generated {len(limited_suggestions)} rule suggestions in {duration_ms:.1f}ms"
        )

        return response_data

    except MCPException:
        raise
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        logger.error(f"Unexpected error in get_rule_suggestions: {e}", exc_info=True)

        if ctx:
            ctx.record_cache_miss()

        raise MCPException(
            MCPError(
                message=f"Unexpected error generating rule suggestions: {e}",
                error_code=MCPErrorCode.INTERNAL_ERROR,
                category=ErrorCategory.SYSTEM_ERROR,
                data={"request_duration_ms": duration_ms},
            )
        )


# Tool metadata for MCP registration
RULE_INTELLIGENCE_TOOLS = {
    "find_rule_cross_references": {
        "function": find_rule_cross_references,
        "description": "Find cross-references and relationships for a specific D&D 5e rule",
        "parameters": {
            "rule_id": {
                "type": "string",
                "required": True,
                "description": "Rule identifier",
            },
            "max_depth": {
                "type": "integer",
                "default": 2,
                "description": "Maximum reference depth (1-5)",
            },
            "include_analysis": {
                "type": "boolean",
                "default": True,
                "description": "Include complexity analysis",
            },
        },
        "performance_target": "100ms",
    },
    "validate_rule_combination": {
        "function": validate_rule_combination,
        "description": "Validate that a combination of D&D 5e rules can work together",
        "parameters": {
            "rule_ids": {
                "type": "array",
                "required": True,
                "description": "List of rule identifiers",
            },
            "context": {
                "type": "object",
                "description": "Optional context (character_class, level, etc.)",
            },
        },
        "performance_target": "150ms",
    },
    "search_rules_intelligent": {
        "function": search_rules_intelligent,
        "description": "Perform intelligent search for D&D 5e rules with enhanced analysis",
        "parameters": {
            "query": {
                "type": "string",
                "required": True,
                "description": "Search query",
            },
            "rule_types": {"type": "array", "description": "Rule type filters"},
            "sources": {"type": "array", "description": "Source book filters"},
            "complexity_filter": {
                "type": "object",
                "description": "Complexity range filter",
            },
            "include_relationships": {
                "type": "boolean",
                "default": True,
                "description": "Include relationships",
            },
            "limit": {
                "type": "integer",
                "default": 20,
                "description": "Maximum results (1-50)",
            },
        },
        "performance_target": "200ms",
    },
    "get_rule_suggestions": {
        "function": get_rule_suggestions,
        "description": "Get intelligent rule suggestions based on context",
        "parameters": {
            "context": {
                "type": "object",
                "required": True,
                "description": "Context for suggestions",
            },
            "limit": {
                "type": "integer",
                "default": 10,
                "description": "Maximum suggestions (1-20)",
            },
        },
        "performance_target": "200ms",
    },
}

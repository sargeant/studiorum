"""Rule intelligence service implementation.

This module provides the core rule intelligence service that implements
the RuleIntelligenceProtocol, leveraging existing infrastructure for
D&D 5e rule analysis, relationship discovery, and intelligent search.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

from pydantic import BaseModel, Field

from ....core.error_types import (
    ContentNotFoundError,
    ErrorCategory,
    ErrorSeverity,
    ProcessingError,
    create_processing_error,
)
from ....core.logging import get_logger
from ....core.models.rule_types import Action, Condition, Hazard, Sense, Status
from ....core.result import Error, Result, Success
from ....core.services.protocols import OmnidexerProtocol
from ....core.text.tag_resolver import TagResolver
from .enhanced_cross_reference_manager import (
    EnhancedCrossReferenceManager,
    RuleRelationship,
)
from .rule_intelligence_protocol import RuleIntelligenceProtocol
from .rule_search_result import RuleSearchResult, create_rule_search_result

logger = get_logger(__name__)


class RuleIntelligenceConfig(BaseModel):
    """Configuration for rule intelligence service."""

    relationship_confidence_threshold: float = Field(
        default=0.3, ge=0.0, le=1.0, description="Minimum confidence for relationships"
    )
    complexity_weights: dict[str, float] = Field(
        default_factory=lambda: {
            "entry_count": 0.3,
            "text_length": 0.2,
            "tag_count": 0.2,
            "time_complexity": 0.2,
            "interaction_count": 0.1,
        },
        description="Weights for complexity calculation factors",
    )
    performance_targets: dict[str, float] = Field(
        default_factory=lambda: {
            "relationship_discovery": 200.0,
            "cross_reference_lookup": 100.0,
            "rule_combination_validation": 150.0,
            "intelligent_search": 200.0,
        },
        description="Performance targets in milliseconds",
    )
    caching_enabled: bool = Field(default=True, description="Enable caching")
    cache_ttl_seconds: float = Field(default=300.0, description="Cache TTL in seconds")
    max_search_results: int = Field(
        default=50, description="Maximum search results to return"
    )


class RuleIntelligenceService:
    """Rule intelligence service with enhanced analysis capabilities.

    This service provides intelligent analysis of D&D 5e rules using existing
    infrastructure components like the TagResolver and OmnidexerProtocol.
    """

    def __init__(
        self,
        omnidexer: OmnidexerProtocol,
        tag_resolver: TagResolver,
        config: RuleIntelligenceConfig | None = None,
    ) -> None:
        self.omnidexer = omnidexer
        self.tag_resolver = tag_resolver
        self.config = config or RuleIntelligenceConfig()

        # Initialize enhanced cross-reference manager
        self.cross_ref_manager = EnhancedCrossReferenceManager()

        # Performance tracking
        self._operation_times: dict[str, list[float]] = {}
        self._last_rebuild_time = 0.0

        # Initialize supported rule types
        self._supported_rule_types = [
            "action",
            "condition",
            "sense",
            "hazard",
            "status",
        ]

    def get_service_name(self) -> str:
        """Return the service name for debugging and logging."""
        return "RuleIntelligenceService"

    async def discover_rule_relationships(
        self, rule_ids: list[str] | None = None
    ) -> Result[list[RuleRelationship], ProcessingError]:
        """Discover relationships between rules using intelligent analysis."""
        start_time = time.time()

        try:
            # If no specific rule IDs provided, discover all relationships
            if rule_ids is None:
                # Get all rule content from omnidexer
                await self._ensure_rules_loaded()

                # Use the enhanced cross-reference manager for discovery
                result = self.cross_ref_manager.discover_rule_relationships(
                    self.tag_resolver
                )

                if result.is_error():
                    return result

                relationships = result.unwrap()
            else:
                # Discover relationships for specific rules
                relationships = []

                for rule_id in rule_ids:
                    if rule_id not in self.cross_ref_manager.rule_references:
                        continue

                    # Find relationships involving this rule
                    rule_relationships = [
                        rel
                        for rel in self.cross_ref_manager.rule_relationships
                        if rel.source_rule == rule_id or rel.target_rule == rule_id
                    ]
                    relationships.extend(rule_relationships)

                # Remove duplicates
                seen = set()
                unique_relationships = []
                for rel in relationships:
                    rel_key = (rel.source_rule, rel.target_rule, rel.relationship_type)
                    if rel_key not in seen:
                        seen.add(rel_key)
                        unique_relationships.append(rel)

                relationships = unique_relationships

            # Filter by confidence threshold
            filtered_relationships = [
                rel
                for rel in relationships
                if rel.confidence >= self.config.relationship_confidence_threshold
            ]

            duration_ms = (time.time() - start_time) * 1000
            self._record_operation_time("relationship_discovery", duration_ms)

            logger.debug(
                f"Discovered {len(filtered_relationships)} relationships in {duration_ms:.1f}ms"
            )

            # Check performance target
            target = self.config.performance_targets["relationship_discovery"]
            if duration_ms > target:
                logger.warning(
                    f"Relationship discovery exceeded {target}ms target: {duration_ms:.1f}ms"
                )

            return Success(filtered_relationships)

        except Exception as e:
            error = create_processing_error(
                message=f"Failed to discover rule relationships: {e}",
                severity=ErrorSeverity.ERROR,
            )
            return Error(error)

    async def find_rule_cross_references(
        self, rule_id: str, max_depth: int = 2, include_analysis: bool = True
    ) -> Result[dict[str, Any], ProcessingError]:
        """Find cross-references for a specific rule."""
        start_time = time.time()

        try:
            # Use enhanced cross-reference manager
            result = self.cross_ref_manager.find_cross_references(rule_id, max_depth)

            if result.is_error():
                return result

            cross_ref_data = result.unwrap()

            # Add additional analysis if requested
            if include_analysis:
                cross_ref_data["performance_analysis"] = {
                    "search_time_ms": (time.time() - start_time) * 1000,
                    "depth_analyzed": max_depth,
                    "relationship_confidence_avg": self._calculate_avg_confidence(
                        cross_ref_data.get("direct_relationships", [])
                    ),
                }

                # Add tag analysis using TagResolver
                if rule_id in self.cross_ref_manager.rule_references:
                    rule_ref = self.cross_ref_manager.rule_references[rule_id]
                    cross_ref_data["tag_analysis"] = {
                        "tags_found": rule_ref.tags_found,
                        "tag_types": list(
                            set(
                                tag.split()[0] if " " in tag else tag
                                for tag in rule_ref.tags_found
                            )
                        ),
                        "tag_resolution_supported": [
                            tag
                            for tag in rule_ref.tags_found
                            if self.tag_resolver.has_handler(tag)
                        ],
                    }

            duration_ms = (time.time() - start_time) * 1000
            self._record_operation_time("cross_reference_lookup", duration_ms)

            # Check performance target
            target = self.config.performance_targets["cross_reference_lookup"]
            if duration_ms > target:
                logger.warning(
                    f"Cross-reference lookup exceeded {target}ms target: {duration_ms:.1f}ms"
                )

            return Success(cross_ref_data)

        except Exception as e:
            error = create_processing_error(
                message=f"Failed to find cross-references for {rule_id}: {e}",
                severity=ErrorSeverity.ERROR,
            )
            return Error(error)

    async def validate_rule_combination(
        self, rule_ids: list[str], context: dict[str, Any] | None = None
    ) -> Result[dict[str, Any], ProcessingError]:
        """Validate that a combination of rules can work together."""
        start_time = time.time()

        try:
            # Use enhanced cross-reference manager for validation
            result = self.cross_ref_manager.validate_rule_combination(rule_ids)

            if result.is_error():
                return result

            validation_data = result.unwrap()

            # Add context-specific analysis if provided
            if context:
                validation_data[
                    "context_analysis"
                ] = await self._analyze_context_compatibility(rule_ids, context)

            # Add performance metrics
            duration_ms = (time.time() - start_time) * 1000
            validation_data["performance_metrics"] = {
                "validation_time_ms": duration_ms,
                "rules_processed": len(rule_ids),
                "context_provided": context is not None,
            }

            self._record_operation_time("rule_combination_validation", duration_ms)

            # Check performance target
            target = self.config.performance_targets["rule_combination_validation"]
            if duration_ms > target:
                logger.warning(
                    f"Rule combination validation exceeded {target}ms target: {duration_ms:.1f}ms"
                )

            return Success(validation_data)

        except Exception as e:
            error = create_processing_error(
                message=f"Failed to validate rule combination: {e}",
                severity=ErrorSeverity.ERROR,
            )
            return Error(error)

    async def search_rules_intelligent(
        self,
        query: str,
        rule_types: list[str] | None = None,
        sources: list[str] | None = None,
        complexity_filter: tuple[float, float] | None = None,
        include_relationships: bool = True,
        limit: int = 20,
    ) -> Result[RuleSearchResult, ProcessingError]:
        """Perform intelligent rule search with enhanced analysis."""
        start_time = time.time()

        try:
            # Limit to max configured results
            actual_limit = min(limit, self.config.max_search_results)

            # Search for rule content using omnidexer
            rule_content = []

            # Search for each supported rule type or specific types
            search_types = rule_types or self._supported_rule_types

            for rule_type in search_types:
                try:
                    # Use omnidexer async search
                    search_result = await self.omnidexer.search_content_async(
                        query=query,
                        content_type=rule_type,
                        limit=actual_limit,
                    )

                    if hasattr(search_result, "unwrap"):
                        content = (
                            search_result.unwrap() if search_result.is_success() else []
                        )
                    else:
                        content = (
                            search_result if isinstance(search_result, list) else []
                        )

                    rule_content.extend(content)

                except Exception as e:
                    logger.warning(f"Search failed for rule type {rule_type}: {e}")
                    continue

            # Apply source filtering if specified
            if sources:
                rule_content = [
                    rule
                    for rule in rule_content
                    if hasattr(rule, "source") and rule.source.abbreviation in sources
                ]

            # Apply complexity filtering if specified
            if complexity_filter:
                min_complexity, max_complexity = complexity_filter
                filtered_content = []

                for rule in rule_content:
                    rule_id = getattr(rule, "id", None) or getattr(rule, "name", "")
                    if rule_id in self.cross_ref_manager.rule_references:
                        rule_ref = self.cross_ref_manager.rule_references[rule_id]
                        if (
                            min_complexity
                            <= rule_ref.complexity_score
                            <= max_complexity
                        ):
                            filtered_content.append(rule)
                    else:
                        # If no complexity data, include by default
                        filtered_content.append(rule)

                rule_content = filtered_content

            # Limit results
            rule_content = rule_content[:actual_limit]

            duration_ms = (time.time() - start_time) * 1000

            # Create enhanced search result
            search_result = create_rule_search_result(
                content=rule_content,
                total=len(rule_content),
                query=query,
                content_type="rules",
                sources_used=sources or [],
                duration_ms=duration_ms,
                cached=False,
                enhanced_cross_ref_manager=self.cross_ref_manager
                if include_relationships
                else None,
            )

            self._record_operation_time("intelligent_search", duration_ms)

            # Check performance target
            target = self.config.performance_targets["intelligent_search"]
            if duration_ms > target:
                logger.warning(
                    f"Intelligent search exceeded {target}ms target: {duration_ms:.1f}ms"
                )

            return Success(search_result)

        except Exception as e:
            error = create_processing_error(
                message=f"Failed to perform intelligent rule search: {e}",
                severity=ErrorSeverity.ERROR,
            )
            return Error(error)

    async def analyze_rule_complexity(
        self, rule_id: str
    ) -> Result[dict[str, Any], ProcessingError]:
        """Analyze the complexity of a specific rule."""
        try:
            if rule_id not in self.cross_ref_manager.rule_references:
                error = create_processing_error(
                    message=f"Rule not found: {rule_id}",
                    severity=ErrorSeverity.WARNING,
                )
                return Error(error)

            rule_ref = self.cross_ref_manager.rule_references[rule_id]

            complexity_analysis = {
                "rule_id": rule_id,
                "complexity_score": rule_ref.complexity_score,
                "complexity_category": self.cross_ref_manager._categorize_complexity(
                    rule_ref.complexity_score
                ),
                "complexity_factors": self.cross_ref_manager._get_complexity_factors(
                    rule_ref
                ),
                "rule_type": rule_ref.rule_type,
                "tags_found": rule_ref.tags_found,
                "related_rules_count": len(rule_ref.related_rules),
                "analysis_metadata": {
                    "weights_used": self.config.complexity_weights,
                    "analysis_version": "1.0",
                },
            }

            return Success(complexity_analysis)

        except Exception as e:
            error = create_processing_error(
                message=f"Failed to analyze rule complexity for {rule_id}: {e}",
                severity=ErrorSeverity.ERROR,
            )
            return Error(error)

    async def get_rule_suggestions(
        self, context: dict[str, Any]
    ) -> Result[list[dict[str, Any]], ProcessingError]:
        """Get intelligent rule suggestions based on context."""
        try:
            suggestions = []

            # Extract context information
            character_class = context.get("character_class", "")
            situation = context.get("situation", "")

            # Generate suggestions based on context
            if character_class:
                # Search for rules relevant to the character class
                class_relevant_rules = []
                for rule_ref in self.cross_ref_manager.rule_references.values():
                    # Simple keyword matching for demonstration
                    rule_name = rule_ref.base_reference.name.lower()
                    if character_class.lower() in rule_name or any(
                        tag
                        for tag in rule_ref.tags_found
                        if character_class.lower() in tag.lower()
                    ):
                        class_relevant_rules.append(rule_ref)

                for rule_ref in class_relevant_rules[:5]:  # Top 5
                    suggestions.append(
                        {
                            "rule_id": rule_ref.base_reference.id,
                            "rule_name": rule_ref.base_reference.name,
                            "rule_type": rule_ref.rule_type,
                            "relevance_reason": f"Relevant to {character_class}",
                            "complexity_score": rule_ref.complexity_score,
                            "suggested_priority": "high"
                            if rule_ref.complexity_score < 0.5
                            else "medium",
                        }
                    )

            if situation:
                # Add situation-specific suggestions
                situation_keywords = situation.lower().split()
                for rule_ref in self.cross_ref_manager.rule_references.values():
                    rule_name = rule_ref.base_reference.name.lower()
                    if any(keyword in rule_name for keyword in situation_keywords):
                        suggestions.append(
                            {
                                "rule_id": rule_ref.base_reference.id,
                                "rule_name": rule_ref.base_reference.name,
                                "rule_type": rule_ref.rule_type,
                                "relevance_reason": f"Relevant to situation: {situation}",
                                "complexity_score": rule_ref.complexity_score,
                                "suggested_priority": "medium",
                            }
                        )

            # Remove duplicates and limit results
            seen_rules = set()
            unique_suggestions = []
            for suggestion in suggestions:
                rule_id = suggestion["rule_id"]
                if rule_id not in seen_rules:
                    seen_rules.add(rule_id)
                    unique_suggestions.append(suggestion)

            return Success(unique_suggestions[:10])  # Top 10 suggestions

        except Exception as e:
            error = create_processing_error(
                message=f"Failed to get rule suggestions: {e}",
                severity=ErrorSeverity.ERROR,
            )
            return Error(error)

    async def register_rule_content(
        self,
        rule_content: Action | Condition | Sense | Hazard | Status,
        source: str | None = None,
        page: str | None = None,
        section: str | None = None,
    ) -> Result[str, ProcessingError]:
        """Register rule content for analysis."""
        return self.cross_ref_manager.register_rule_content(
            rule_content, source, page, section
        )

    def supports_rule_type(self, rule_type: str) -> bool:
        """Check if the service supports a specific rule type."""
        return rule_type.lower() in self._supported_rule_types

    def get_supported_rule_types(self) -> list[str]:
        """Get list of all supported rule types."""
        return self._supported_rule_types.copy()

    def get_performance_statistics(self) -> dict[str, Any]:
        """Get performance statistics for the service."""
        stats = {
            "service_name": self.get_service_name(),
            "cross_reference_stats": self.cross_ref_manager.get_performance_statistics(),
            "operation_times": self._get_operation_time_stats(),
            "configuration": {
                "relationship_threshold": self.config.relationship_confidence_threshold,
                "caching_enabled": self.config.caching_enabled,
                "cache_ttl": self.config.cache_ttl_seconds,
                "max_search_results": self.config.max_search_results,
            },
            "performance_targets": self.config.performance_targets,
            "last_rebuild_time": self._last_rebuild_time,
        }
        return stats

    async def clear_analysis_cache(self) -> None:
        """Clear the analysis cache to free memory."""
        self.cross_ref_manager._performance_cache.clear()
        logger.info("Rule intelligence analysis cache cleared")

    async def rebuild_relationship_index(self) -> Result[int, ProcessingError]:
        """Rebuild the rule relationship index."""
        try:
            start_time = time.time()

            # Clear existing relationships
            self.cross_ref_manager.rule_relationships.clear()

            # Rebuild relationships
            result = await self.discover_rule_relationships()

            if result.is_error():
                return Error(result.error)

            relationships = result.unwrap()
            self._last_rebuild_time = time.time()

            duration_ms = (time.time() - start_time) * 1000
            logger.info(
                f"Rebuilt relationship index with {len(relationships)} relationships in {duration_ms:.1f}ms"
            )

            return Success(len(relationships))

        except Exception as e:
            error = create_processing_error(
                message=f"Failed to rebuild relationship index: {e}",
                severity=ErrorSeverity.ERROR,
            )
            return Error(error)

    # Private helper methods

    async def _ensure_rules_loaded(self) -> None:
        """Ensure all rule content is loaded into the cross-reference manager."""
        # This would typically load rules from the omnidexer
        # For now, we assume rules are already registered
        pass

    async def _analyze_context_compatibility(
        self, rule_ids: list[str], context: dict[str, Any]
    ) -> dict[str, Any]:
        """Analyze how rule combination fits with provided context."""
        analysis = {
            "context_compatibility": "neutral",
            "context_factors": [],
            "recommended_modifications": [],
        }

        # Analyze based on character level
        if "level" in context:
            level = context["level"]
            if level < 5:
                analysis["context_factors"].append("low_level_character")
            elif level > 15:
                analysis["context_factors"].append("high_level_character")

        # Analyze based on character class
        if "character_class" in context:
            char_class = context["character_class"].lower()

            # Check if rules are appropriate for the class
            for rule_id in rule_ids:
                if rule_id in self.cross_ref_manager.rule_references:
                    rule_ref = self.cross_ref_manager.rule_references[rule_id]
                    if char_class in rule_ref.base_reference.name.lower():
                        analysis["context_factors"].append(
                            f"class_synergy_{char_class}"
                        )

        return analysis

    def _calculate_avg_confidence(self, relationships: list[dict[str, Any]]) -> float:
        """Calculate average confidence score for relationships."""
        if not relationships:
            return 0.0

        total_confidence = sum(rel.get("confidence", 0.0) for rel in relationships)
        return total_confidence / len(relationships)

    def _record_operation_time(self, operation: str, duration_ms: float) -> None:
        """Record operation time for performance tracking."""
        if operation not in self._operation_times:
            self._operation_times[operation] = []

        self._operation_times[operation].append(duration_ms)

        # Keep only last 100 measurements
        if len(self._operation_times[operation]) > 100:
            self._operation_times[operation] = self._operation_times[operation][-100:]

    def _get_operation_time_stats(self) -> dict[str, dict[str, float]]:
        """Get operation time statistics."""
        stats = {}

        for operation, times in self._operation_times.items():
            if times:
                stats[operation] = {
                    "avg_ms": sum(times) / len(times),
                    "min_ms": min(times),
                    "max_ms": max(times),
                    "count": len(times),
                    "target_ms": self.config.performance_targets.get(operation, 0.0),
                }

        return stats

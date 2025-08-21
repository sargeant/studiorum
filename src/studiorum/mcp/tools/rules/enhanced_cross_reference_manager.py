"""Enhanced cross-reference manager for rules intelligence.

This module extends the existing CrossReferenceManager with rule-specific
functionality for discovering and tracking relationships between D&D 5e
rules, conditions, actions, and related content.

Key Features:
- Rule relationship discovery using existing TagResolver
- Cross-reference resolution <100ms with enhanced caching
- Integration with existing error handling patterns
- Performance monitoring and metrics collection
"""

from __future__ import annotations

import time
from typing import Any

from pydantic import BaseModel, Field

from ....core.error_types import (
    ErrorCategory,
    ErrorSeverity,
    ProcessingError,
    create_processing_error,
)
from ....core.logging import get_logger
from ....core.models.rule_types import Action, Condition, Hazard, Sense, Status
from ....core.references.cross_reference_manager import (
    CrossReference,
    CrossReferenceManager,
)
from ....core.result import Error, Result, Success

logger = get_logger(__name__)


class RuleRelationship(BaseModel):
    """Represents a relationship between rules or rule elements."""

    source_rule: str = Field(description="Source rule identifier")
    target_rule: str = Field(description="Target rule identifier")
    relationship_type: str = Field(description="Type of relationship")
    confidence: float = Field(
        ge=0.0, le=1.0, description="Confidence score for this relationship"
    )
    source_text: str | None = Field(
        None, description="Text where relationship was discovered"
    )
    rule_context: str | None = Field(
        None, description="Context where relationship applies"
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for MCP response."""
        return self.model_dump()


class RuleReference(BaseModel):
    """Enhanced cross-reference for rule content."""

    base_reference: CrossReference = Field(description="Base cross-reference data")
    rule_type: str = Field(description="Type of rule (action, condition, etc.)")
    related_rules: list[str] = Field(
        default_factory=list, description="Related rule identifiers"
    )
    tags_found: list[str] = Field(
        default_factory=list, description="Tags discovered in rule text"
    )
    complexity_score: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Rule complexity score"
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for MCP response."""
        return {
            "id": self.base_reference.id,
            "name": self.base_reference.name,
            "content_type": self.base_reference.content_type,
            "rule_type": self.rule_type,
            "source": self.base_reference.source,
            "page": self.base_reference.page,
            "related_rules": self.related_rules,
            "tags_found": self.tags_found,
            "complexity_score": self.complexity_score,
            "referenced_count": self.base_reference.referenced_count,
        }


class EnhancedCrossReferenceManager(CrossReferenceManager):
    """Enhanced cross-reference manager with rule intelligence capabilities.

    Extends the existing CrossReferenceManager with rule-specific functionality
    for discovering relationships, analyzing tag dependencies, and providing
    intelligent cross-reference resolution for D&D 5e rules content.
    """

    def __init__(self) -> None:
        super().__init__()
        self.rule_references: dict[str, RuleReference] = {}
        self.rule_relationships: list[RuleRelationship] = []
        self._performance_cache: dict[str, tuple[Any, float]] = {}
        self._cache_ttl = 300.0  # 5 minutes

    def register_rule_content(
        self,
        rule_content: Action | Condition | Sense | Hazard | Status,
        source: str | None = None,
        page: str | None = None,
        section: str | None = None,
    ) -> Result[str, ProcessingError]:
        """Register rule content for enhanced cross-referencing.

        Args:
            rule_content: Rule content object
            source: Source book abbreviation
            page: Page number in source
            section: Document section

        Returns:
            Result containing reference ID or error
        """
        try:
            start_time = time.time()

            # Get rule type from class name
            rule_type = rule_content.__class__.__name__.lower()

            # Register with base manager
            ref_id = self.register_content(
                content_type=rule_type,
                name=rule_content.name,
                source=source,
                page=page,
                section=section,
            )

            # Extract tags from entries if present
            tags_found = []
            if hasattr(rule_content, "entries") and rule_content.entries:
                tags_found = self._extract_tags_from_entries(rule_content.entries)

            # Calculate complexity score based on rule content
            complexity_score = self._calculate_complexity_score(rule_content)

            # Create enhanced rule reference
            base_ref = self.get_reference(ref_id)
            if not base_ref:
                error = create_processing_error(
                    message=f"Failed to create base reference for rule {rule_content.name}",
                    entry_type=rule_type,
                    source=source,
                )
                return Error(error)

            rule_ref = RuleReference(
                base_reference=base_ref,
                rule_type=rule_type,
                tags_found=tags_found,
                complexity_score=complexity_score,
            )

            self.rule_references[ref_id] = rule_ref

            duration_ms = (time.time() - start_time) * 1000
            logger.debug(f"Registered rule {rule_content.name} in {duration_ms:.1f}ms")

            return Success(ref_id)

        except Exception as e:
            error = create_processing_error(
                message=f"Failed to register rule content: {e}",
                entry_type=getattr(rule_content, "__class__", {}).get(
                    "__name__", "unknown"
                ),
                source=source,
                severity=ErrorSeverity.ERROR,
            )
            return Error(error)

    def discover_rule_relationships(
        self, tag_resolver: Any = None
    ) -> Result[list[RuleRelationship], ProcessingError]:
        """Discover relationships between rules using tag analysis.

        Args:
            tag_resolver: Optional TagResolver for enhanced tag parsing

        Returns:
            Result containing list of discovered relationships or error
        """
        try:
            start_time = time.time()
            relationships = []

            # Check cache first
            cache_key = "rule_relationships"
            cached_result = self._get_cached_result(cache_key)
            if cached_result is not None:
                duration_ms = (time.time() - start_time) * 1000
                logger.debug(f"Retrieved cached relationships in {duration_ms:.1f}ms")
                return Success(cached_result)

            # Analyze all rule references for relationships
            rule_refs = list(self.rule_references.values())

            for i, source_rule in enumerate(rule_refs):
                for target_rule in rule_refs[i + 1 :]:
                    relationship = self._analyze_rule_relationship(
                        source_rule, target_rule, tag_resolver
                    )
                    if relationship and relationship.confidence > 0.3:
                        relationships.append(relationship)

            # Cache results
            self._cache_result(cache_key, relationships)

            duration_ms = (time.time() - start_time) * 1000
            logger.debug(
                f"Discovered {len(relationships)} relationships in {duration_ms:.1f}ms"
            )

            if duration_ms > 100:
                logger.warning(
                    f"Rule relationship discovery exceeded 100ms target: {duration_ms:.1f}ms"
                )

            self.rule_relationships = relationships
            return Success(relationships)

        except Exception as e:
            error = create_processing_error(
                message=f"Failed to discover rule relationships: {e}",
                severity=ErrorSeverity.ERROR,
            )
            return Error(error)

    def find_cross_references(
        self, rule_id: str, max_depth: int = 2
    ) -> Result[dict[str, Any], ProcessingError]:
        """Find cross-references for a specific rule with depth control.

        Args:
            rule_id: Rule identifier to find references for
            max_depth: Maximum depth for recursive reference discovery

        Returns:
            Result containing cross-reference data or error
        """
        try:
            start_time = time.time()

            # Check if rule exists
            if rule_id not in self.rule_references:
                error = create_processing_error(
                    message=f"Rule not found: {rule_id}",
                    severity=ErrorSeverity.WARNING,
                )
                return Error(error)

            rule_ref = self.rule_references[rule_id]

            # Find direct relationships
            direct_relationships = [
                rel
                for rel in self.rule_relationships
                if rel.source_rule == rule_id or rel.target_rule == rule_id
            ]

            # Find indirect relationships up to max_depth
            indirect_relationships = []
            if max_depth > 1:
                indirect_relationships = self._find_indirect_relationships(
                    rule_id, max_depth - 1
                )

            # Compile cross-reference data
            cross_ref_data = {
                "rule": rule_ref.to_dict(),
                "direct_relationships": [rel.to_dict() for rel in direct_relationships],
                "indirect_relationships": [
                    rel.to_dict() for rel in indirect_relationships
                ],
                "total_relationships": len(direct_relationships)
                + len(indirect_relationships),
                "complexity_analysis": {
                    "score": rule_ref.complexity_score,
                    "category": self._categorize_complexity(rule_ref.complexity_score),
                    "factors": self._get_complexity_factors(rule_ref),
                },
            }

            duration_ms = (time.time() - start_time) * 1000
            logger.debug(f"Found cross-references for {rule_id} in {duration_ms:.1f}ms")

            if duration_ms > 100:
                logger.warning(
                    f"Cross-reference lookup exceeded 100ms target: {duration_ms:.1f}ms"
                )

            return Success(cross_ref_data)

        except Exception as e:
            error = create_processing_error(
                message=f"Failed to find cross-references for {rule_id}: {e}",
                severity=ErrorSeverity.ERROR,
            )
            return Error(error)

    def validate_rule_combination(
        self, rule_ids: list[str]
    ) -> Result[dict[str, Any], ProcessingError]:
        """Validate that a combination of rules can work together.

        Args:
            rule_ids: List of rule identifiers to validate

        Returns:
            Result containing validation results or error
        """
        try:
            start_time = time.time()

            # Check all rules exist
            missing_rules = [
                rule_id for rule_id in rule_ids if rule_id not in self.rule_references
            ]
            if missing_rules:
                error = create_processing_error(
                    message=f"Rules not found: {', '.join(missing_rules)}",
                    severity=ErrorSeverity.WARNING,
                )
                return Error(error)

            # Analyze rule compatibility
            conflicts = []
            synergies = []
            warnings = []

            for i, rule_id1 in enumerate(rule_ids):
                for rule_id2 in rule_ids[i + 1 :]:
                    compatibility = self._analyze_rule_compatibility(rule_id1, rule_id2)

                    if compatibility["type"] == "conflict":
                        conflicts.append(compatibility)
                    elif compatibility["type"] == "synergy":
                        synergies.append(compatibility)
                    elif compatibility["type"] == "warning":
                        warnings.append(compatibility)

            # Calculate overall combination score
            combination_score = self._calculate_combination_score(
                rule_ids, conflicts, synergies
            )

            validation_result = {
                "valid": len(conflicts) == 0,
                "combination_score": combination_score,
                "conflicts": conflicts,
                "synergies": synergies,
                "warnings": warnings,
                "rules_analyzed": len(rule_ids),
                "analysis_summary": self._generate_combination_summary(
                    rule_ids, conflicts, synergies, combination_score
                ),
            }

            duration_ms = (time.time() - start_time) * 1000
            logger.debug(f"Validated rule combination in {duration_ms:.1f}ms")

            return Success(validation_result)

        except Exception as e:
            error = create_processing_error(
                message=f"Failed to validate rule combination: {e}",
                severity=ErrorSeverity.ERROR,
            )
            return Error(error)

    def _extract_tags_from_entries(self, entries: list[Any]) -> list[str]:
        """Extract {@tag} references from rule entries."""
        tags = []

        for entry in entries:
            if isinstance(entry, str):
                # Simple regex-based tag extraction
                import re

                tag_pattern = r"\{@(\w+)(?:\s+([^}]+))?\}"
                matches = re.findall(tag_pattern, entry)
                for match in matches:
                    tag_type = match[0]
                    tags.append(tag_type)
            elif isinstance(entry, dict):
                # Recursive search in dict entries
                tags.extend(self._extract_tags_from_dict(entry))

        return list(set(tags))  # Remove duplicates

    def _extract_tags_from_dict(self, entry_dict: dict[str, Any]) -> list[str]:
        """Recursively extract tags from dictionary entries."""
        tags = []

        for value in entry_dict.values():
            if isinstance(value, str):
                import re

                tag_pattern = r"\{@(\w+)(?:\s+([^}]+))?\}"
                matches = re.findall(tag_pattern, value)
                for match in matches:
                    tag_type = match[0]
                    tags.append(tag_type)
            elif isinstance(value, list):
                tags.extend(self._extract_tags_from_entries(value))
            elif isinstance(value, dict):
                tags.extend(self._extract_tags_from_dict(value))

        return tags

    def _calculate_complexity_score(
        self, rule_content: Action | Condition | Sense | Hazard | Status
    ) -> float:
        """Calculate complexity score for a rule based on various factors."""
        score = 0.0

        # Base complexity from entry count
        if hasattr(rule_content, "entries") and rule_content.entries:
            entry_count = len(rule_content.entries)
            score += min(entry_count * 0.1, 0.3)  # Cap at 0.3

        # Additional complexity for time-based actions
        if isinstance(rule_content, Action) and hasattr(rule_content, "time"):
            if rule_content.time:
                score += 0.2

        # Text length complexity
        total_text_length = 0
        if hasattr(rule_content, "entries") and rule_content.entries:
            for entry in rule_content.entries:
                if isinstance(entry, str):
                    total_text_length += len(entry)

        # Normalize text length to score
        if total_text_length > 0:
            text_complexity = min(total_text_length / 1000, 0.3)
            score += text_complexity

        # Tag complexity
        if hasattr(rule_content, "entries"):
            tags = self._extract_tags_from_entries(rule_content.entries)
            tag_complexity = min(len(tags) * 0.05, 0.2)
            score += tag_complexity

        return min(score, 1.0)  # Cap at 1.0

    def _analyze_rule_relationship(
        self,
        source_rule: RuleReference,
        target_rule: RuleReference,
        tag_resolver: Any = None,
    ) -> RuleRelationship | None:
        """Analyze relationship between two rules."""
        confidence = 0.0
        relationship_type = "unknown"

        # Tag-based relationships
        common_tags = set(source_rule.tags_found) & set(target_rule.tags_found)
        if common_tags:
            confidence += len(common_tags) * 0.3
            relationship_type = "tag_reference"

        # Rule type relationships
        if source_rule.rule_type == target_rule.rule_type:
            confidence += 0.2
            relationship_type = "same_type"

        # Name similarity
        name_similarity = self._calculate_name_similarity(
            source_rule.base_reference.name, target_rule.base_reference.name
        )
        confidence += name_similarity * 0.3

        if confidence > 0.1:
            return RuleRelationship(
                source_rule=source_rule.base_reference.id,
                target_rule=target_rule.base_reference.id,
                relationship_type=relationship_type,
                confidence=min(confidence, 1.0),
            )

        return None

    def _calculate_name_similarity(self, name1: str, name2: str) -> float:
        """Calculate simple name similarity score."""
        # Simple word overlap similarity
        words1 = set(name1.lower().split())
        words2 = set(name2.lower().split())

        if not words1 or not words2:
            return 0.0

        overlap = len(words1 & words2)
        total = len(words1 | words2)

        return overlap / total if total > 0 else 0.0

    def _find_indirect_relationships(
        self, rule_id: str, max_depth: int
    ) -> list[RuleRelationship]:
        """Find indirect relationships up to specified depth."""
        if max_depth <= 0:
            return []

        indirect = []

        # Find rules directly related to this one
        direct_related = set()
        for rel in self.rule_relationships:
            if rel.source_rule == rule_id:
                direct_related.add(rel.target_rule)
            elif rel.target_rule == rule_id:
                direct_related.add(rel.source_rule)

        # Find relationships of those related rules
        for related_rule in direct_related:
            for rel in self.rule_relationships:
                if (
                    rel.source_rule == related_rule or rel.target_rule == related_rule
                ) and rule_id not in (rel.source_rule, rel.target_rule):
                    indirect.append(rel)

        return indirect

    def _analyze_rule_compatibility(
        self, rule_id1: str, rule_id2: str
    ) -> dict[str, Any]:
        """Analyze compatibility between two rules."""
        rule1 = self.rule_references[rule_id1]
        rule2 = self.rule_references[rule_id2]

        # Check for known conflicts
        if self._has_rule_conflict(rule1, rule2):
            return {
                "type": "conflict",
                "rule1": rule_id1,
                "rule2": rule_id2,
                "description": f"Conflict between {rule1.rule_type} and {rule2.rule_type}",
                "severity": "high",
            }

        # Check for synergies
        if self._has_rule_synergy(rule1, rule2):
            return {
                "type": "synergy",
                "rule1": rule_id1,
                "rule2": rule_id2,
                "description": f"Synergy between {rule1.rule_type} and {rule2.rule_type}",
                "benefit": "enhanced_effect",
            }

        # Default to neutral compatibility
        return {
            "type": "neutral",
            "rule1": rule_id1,
            "rule2": rule_id2,
            "description": "No significant interaction",
        }

    def _has_rule_conflict(self, rule1: RuleReference, rule2: RuleReference) -> bool:
        """Check if two rules have a known conflict."""
        # Example conflict detection logic
        # This would be expanded with actual D&D 5e rule conflict knowledge

        # Actions that require the same resource
        if rule1.rule_type == "action" and rule2.rule_type == "action":
            # Both are actions - potential action economy conflict
            return True

        return False

    def _has_rule_synergy(self, rule1: RuleReference, rule2: RuleReference) -> bool:
        """Check if two rules have beneficial synergy."""
        # Example synergy detection logic

        # Condition + Action synergies
        if (rule1.rule_type == "condition" and rule2.rule_type == "action") or (
            rule1.rule_type == "action" and rule2.rule_type == "condition"
        ):
            return True

        return False

    def _calculate_combination_score(
        self, rule_ids: list[str], conflicts: list[dict], synergies: list[dict]
    ) -> float:
        """Calculate overall score for rule combination."""
        base_score = 0.5  # Neutral starting point

        # Penalty for conflicts
        conflict_penalty = len(conflicts) * 0.2

        # Bonus for synergies
        synergy_bonus = len(synergies) * 0.15

        # Complexity penalty
        total_complexity = sum(
            self.rule_references[rule_id].complexity_score for rule_id in rule_ids
        )
        complexity_penalty = min(total_complexity / len(rule_ids) * 0.1, 0.2)

        final_score = base_score - conflict_penalty + synergy_bonus - complexity_penalty
        return max(0.0, min(1.0, final_score))

    def _generate_combination_summary(
        self,
        rule_ids: list[str],
        conflicts: list[dict],
        synergies: list[dict],
        score: float,
    ) -> str:
        """Generate human-readable summary of rule combination analysis."""
        summary_parts = []

        if score >= 0.8:
            summary_parts.append("Excellent rule combination")
        elif score >= 0.6:
            summary_parts.append("Good rule combination")
        elif score >= 0.4:
            summary_parts.append("Moderate rule combination")
        else:
            summary_parts.append("Problematic rule combination")

        if conflicts:
            summary_parts.append(f"{len(conflicts)} conflicts detected")

        if synergies:
            summary_parts.append(f"{len(synergies)} synergies found")

        return ". ".join(summary_parts) + "."

    def _categorize_complexity(self, score: float) -> str:
        """Categorize complexity score into readable categories."""
        if score >= 0.8:
            return "very_high"
        elif score >= 0.6:
            return "high"
        elif score >= 0.4:
            return "moderate"
        elif score >= 0.2:
            return "low"
        else:
            return "very_low"

    def _get_complexity_factors(self, rule_ref: RuleReference) -> list[str]:
        """Get list of factors contributing to rule complexity."""
        factors = []

        if rule_ref.complexity_score >= 0.3:
            factors.append("multiple_entries")

        if len(rule_ref.tags_found) > 3:
            factors.append("many_references")

        if rule_ref.rule_type == "action":
            factors.append("action_economy")

        if not factors:
            factors.append("simple_rule")

        return factors

    def _get_cached_result(self, cache_key: str) -> Any | None:
        """Get cached result if still valid."""
        if cache_key in self._performance_cache:
            result, timestamp = self._performance_cache[cache_key]
            if time.time() - timestamp < self._cache_ttl:
                return result
            else:
                # Remove expired cache entry
                del self._performance_cache[cache_key]
        return None

    def _cache_result(self, cache_key: str, result: Any) -> None:
        """Cache result with TTL."""
        self._performance_cache[cache_key] = (result, time.time())

        # Simple cache size management
        if len(self._performance_cache) > 100:
            # Remove oldest 20 entries
            sorted_items = sorted(
                self._performance_cache.items(), key=lambda x: x[1][1]
            )[:20]
            for key, _ in sorted_items:
                del self._performance_cache[key]

    def get_performance_statistics(self) -> dict[str, Any]:
        """Get performance statistics for the enhanced manager."""
        base_stats = self.get_reference_statistics()

        enhanced_stats = {
            **base_stats,
            "rule_references": len(self.rule_references),
            "rule_relationships": len(self.rule_relationships),
            "cache_entries": len(self._performance_cache),
            "avg_complexity_score": (
                sum(ref.complexity_score for ref in self.rule_references.values())
                / len(self.rule_references)
                if self.rule_references
                else 0.0
            ),
            "rule_types": {
                rule_type: sum(
                    1
                    for ref in self.rule_references.values()
                    if ref.rule_type == rule_type
                )
                for rule_type in set(
                    ref.rule_type for ref in self.rule_references.values()
                )
            },
        }

        return enhanced_stats

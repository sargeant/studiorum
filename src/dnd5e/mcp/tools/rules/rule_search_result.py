"""Rule search result extending ContentSearchResult.

This module provides enhanced search results specifically for rule content,
extending the existing ContentSearchResult with rule-specific metadata,
relationship information, and intelligent analysis.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from ....core.models.content import BaseContent
from ....mcp.tools.content import ContentSearchResult
from .enhanced_cross_reference_manager import RuleRelationship


class RuleAnalysis(BaseModel):
    """Analysis data for rule search results."""

    complexity_score: float = Field(ge=0.0, le=1.0, description="Rule complexity score")
    rule_category: str = Field(description="Categorized rule type")
    interaction_count: int = Field(
        ge=0, description="Number of rule interactions found"
    )
    tag_references: list[str] = Field(
        default_factory=list, description="Tags referenced in rule"
    )
    related_concepts: list[str] = Field(
        default_factory=list, description="Related D&D concepts"
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for MCP response."""
        return self.model_dump()


class RuleSearchResult(ContentSearchResult):
    """Enhanced search result container for rule operations.

    Extends ContentSearchResult with rule-specific analysis, relationship
    discovery, and intelligent categorization for D&D 5e rules content.
    """

    def __init__(
        self,
        content: list[BaseContent],
        total: int,
        query: str,
        content_type: str,
        sources_used: list[str],
        duration_ms: float,
        cached: bool = False,
        # Enhanced rule-specific fields
        rule_relationships: list[RuleRelationship] | None = None,
        rule_analysis: dict[str, RuleAnalysis] | None = None,
        interaction_matrix: dict[str, list[str]] | None = None,
        complexity_distribution: dict[str, int] | None = None,
    ):
        super().__init__(
            content=content,
            total=total,
            query=query,
            content_type=content_type,
            sources_used=sources_used,
            duration_ms=duration_ms,
            cached=cached,
        )

        # Rule-specific enhancements
        self.rule_relationships = rule_relationships or []
        self.rule_analysis = rule_analysis or {}
        self.interaction_matrix = interaction_matrix or {}
        self.complexity_distribution = complexity_distribution or {}

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for MCP response with rule enhancements."""
        base_dict = super().to_dict()

        # Add rule-specific data
        base_dict.update(
            {
                "rule_intelligence": {
                    "relationships": [rel.to_dict() for rel in self.rule_relationships],
                    "analysis": {
                        rule_id: analysis.to_dict()
                        for rule_id, analysis in self.rule_analysis.items()
                    },
                    "interaction_matrix": self.interaction_matrix,
                    "complexity_distribution": self.complexity_distribution,
                    "relationship_count": len(self.rule_relationships),
                    "average_complexity": self._calculate_average_complexity(),
                }
            }
        )

        return base_dict

    def add_rule_relationship(self, relationship: RuleRelationship) -> None:
        """Add a rule relationship to the search result."""
        self.rule_relationships.append(relationship)

    def add_rule_analysis(self, rule_id: str, analysis: RuleAnalysis) -> None:
        """Add rule analysis data for a specific rule."""
        self.rule_analysis[rule_id] = analysis

    def set_interaction_matrix(self, matrix: dict[str, list[str]]) -> None:
        """Set the rule interaction matrix."""
        self.interaction_matrix = matrix

    def set_complexity_distribution(self, distribution: dict[str, int]) -> None:
        """Set the complexity distribution data."""
        self.complexity_distribution = distribution

    def get_rules_by_complexity(self, min_complexity: float = 0.0) -> list[BaseContent]:
        """Get rules filtered by minimum complexity score."""
        filtered_rules = []

        for rule in self.content:
            rule_id = getattr(rule, "id", None) or getattr(rule, "name", "")
            if rule_id in self.rule_analysis:
                analysis = self.rule_analysis[rule_id]
                if analysis.complexity_score >= min_complexity:
                    filtered_rules.append(rule)

        return filtered_rules

    def get_rules_by_category(self, category: str) -> list[BaseContent]:
        """Get rules filtered by category."""
        filtered_rules = []

        for rule in self.content:
            rule_id = getattr(rule, "id", None) or getattr(rule, "name", "")
            if rule_id in self.rule_analysis:
                analysis = self.rule_analysis[rule_id]
                if analysis.rule_category == category:
                    filtered_rules.append(rule)

        return filtered_rules

    def get_related_rules(self, rule_id: str) -> list[str]:
        """Get rules related to a specific rule ID."""
        related = set()

        for relationship in self.rule_relationships:
            if relationship.source_rule == rule_id:
                related.add(relationship.target_rule)
            elif relationship.target_rule == rule_id:
                related.add(relationship.source_rule)

        return list(related)

    def get_rule_interactions(self, rule_id: str) -> list[str]:
        """Get rule interactions from the interaction matrix."""
        return self.interaction_matrix.get(rule_id, [])

    def generate_summary(self) -> dict[str, Any]:
        """Generate an intelligent summary of the rule search results."""
        return {
            "total_rules": self.total,
            "rule_types_found": self._get_rule_types_distribution(),
            "complexity_summary": {
                "average": self._calculate_average_complexity(),
                "distribution": self.complexity_distribution,
                "high_complexity_count": self._count_high_complexity_rules(),
            },
            "relationship_summary": {
                "total_relationships": len(self.rule_relationships),
                "relationship_types": self._get_relationship_types_distribution(),
                "most_connected_rule": self._find_most_connected_rule(),
            },
            "interaction_summary": {
                "total_interactions": sum(
                    len(interactions)
                    for interactions in self.interaction_matrix.values()
                ),
                "rules_with_interactions": len(self.interaction_matrix),
                "interaction_density": self._calculate_interaction_density(),
            },
            "performance_summary": {
                "search_duration_ms": self.duration_ms,
                "cached": self.cached,
                "target_met": self.duration_ms < 200.0,
            },
        }

    def _calculate_average_complexity(self) -> float:
        """Calculate average complexity score across all rules."""
        if not self.rule_analysis:
            return 0.0

        total_complexity = sum(
            analysis.complexity_score for analysis in self.rule_analysis.values()
        )
        return total_complexity / len(self.rule_analysis)

    def _get_rule_types_distribution(self) -> dict[str, int]:
        """Get distribution of rule types in the search results."""
        distribution: dict[str, int] = {}

        for rule in self.content:
            rule_type = getattr(rule, "__class__", {}).get("__name__", "unknown")
            rule_type = rule_type.lower()
            distribution[rule_type] = distribution.get(rule_type, 0) + 1

        return distribution

    def _count_high_complexity_rules(self) -> int:
        """Count rules with high complexity (>= 0.7)."""
        return sum(
            1
            for analysis in self.rule_analysis.values()
            if analysis.complexity_score >= 0.7
        )

    def _get_relationship_types_distribution(self) -> dict[str, int]:
        """Get distribution of relationship types."""
        distribution: dict[str, int] = {}

        for relationship in self.rule_relationships:
            rel_type = relationship.relationship_type
            distribution[rel_type] = distribution.get(rel_type, 0) + 1

        return distribution

    def _find_most_connected_rule(self) -> str | None:
        """Find the rule with the most relationships."""
        if not self.rule_relationships:
            return None

        connection_counts: dict[str, int] = {}

        for relationship in self.rule_relationships:
            source = relationship.source_rule
            target = relationship.target_rule

            connection_counts[source] = connection_counts.get(source, 0) + 1
            connection_counts[target] = connection_counts.get(target, 0) + 1

        if connection_counts:
            return max(connection_counts, key=lambda x: connection_counts[x])
        return None

    def _calculate_interaction_density(self) -> float:
        """Calculate the density of rule interactions."""
        if not self.content:
            return 0.0

        total_possible_interactions = len(self.content) * (len(self.content) - 1) / 2
        actual_interactions = (
            sum(len(interactions) for interactions in self.interaction_matrix.values())
            / 2
        )  # Divide by 2 to avoid double-counting

        if total_possible_interactions == 0:
            return 0.0

        return actual_interactions / total_possible_interactions


def create_rule_search_result(
    content: list[BaseContent],
    total: int,
    query: str,
    content_type: str,
    sources_used: list[str],
    duration_ms: float,
    cached: bool = False,
    enhanced_cross_ref_manager: Any = None,
) -> RuleSearchResult:
    """Create a RuleSearchResult with intelligent analysis.

    Args:
        content: Search result content
        total: Total number of results
        query: Original search query
        content_type: Type of content searched
        sources_used: Sources used in search
        duration_ms: Search duration in milliseconds
        cached: Whether result was cached
        enhanced_cross_ref_manager: Optional manager for relationship analysis

    Returns:
        RuleSearchResult with intelligent analysis
    """
    # Create base result
    result = RuleSearchResult(
        content=content,
        total=total,
        query=query,
        content_type=content_type,
        sources_used=sources_used,
        duration_ms=duration_ms,
        cached=cached,
    )

    # Add intelligent analysis if manager is provided
    if enhanced_cross_ref_manager:
        # Discover relationships between found rules
        rule_ids = [
            getattr(rule, "id", None) or getattr(rule, "name", "") for rule in content
        ]

        # Filter valid rule IDs
        valid_rule_ids = [
            rule_id
            for rule_id in rule_ids
            if rule_id and rule_id in enhanced_cross_ref_manager.rule_references
        ]

        # Find relationships between rules in the search results
        relationships = []
        for i, rule_id1 in enumerate(valid_rule_ids):
            for rule_id2 in valid_rule_ids[i + 1 :]:
                # Check if relationship exists
                existing_relationships = [
                    rel
                    for rel in enhanced_cross_ref_manager.rule_relationships
                    if (rel.source_rule == rule_id1 and rel.target_rule == rule_id2)
                    or (rel.source_rule == rule_id2 and rel.target_rule == rule_id1)
                ]
                relationships.extend(existing_relationships)

        result.rule_relationships = relationships

        # Add analysis for each rule
        for rule in content:
            rule_id = getattr(rule, "id", None) or getattr(rule, "name", "")
            if rule_id in enhanced_cross_ref_manager.rule_references:
                rule_ref = enhanced_cross_ref_manager.rule_references[rule_id]

                analysis = RuleAnalysis(
                    complexity_score=rule_ref.complexity_score,
                    rule_category=rule_ref.rule_type,
                    interaction_count=len(result.get_related_rules(rule_id))
                    if rule_id
                    else 0,
                    tag_references=rule_ref.tags_found,
                    related_concepts=_extract_related_concepts(rule),
                )

                if rule_id:
                    result.add_rule_analysis(rule_id, analysis)

        # Generate complexity distribution
        complexity_ranges = {"low": 0, "medium": 0, "high": 0, "very_high": 0}
        for analysis in result.rule_analysis.values():
            score = analysis.complexity_score
            if score < 0.25:
                complexity_ranges["low"] += 1
            elif score < 0.5:
                complexity_ranges["medium"] += 1
            elif score < 0.75:
                complexity_ranges["high"] += 1
            else:
                complexity_ranges["very_high"] += 1

        result.set_complexity_distribution(complexity_ranges)

        # Generate interaction matrix
        interaction_matrix = {}
        for rule_id in valid_rule_ids:
            related = result.get_related_rules(rule_id)
            if related:
                interaction_matrix[rule_id] = related

        result.set_interaction_matrix(interaction_matrix)

    return result


def _extract_related_concepts(rule: BaseContent) -> list[str]:
    """Extract related D&D concepts from rule content."""
    concepts = []

    # Extract from rule name
    name = getattr(rule, "name", "")
    if name:
        # Simple concept extraction based on common D&D terms
        dnd_terms = [
            "attack",
            "damage",
            "spell",
            "ability",
            "saving",
            "throw",
            "advantage",
            "disadvantage",
            "critical",
            "hit",
            "miss",
            "armor",
            "class",
            "weapon",
            "magic",
            "resistance",
            "immunity",
        ]

        name_lower = name.lower()
        for term in dnd_terms:
            if term in name_lower:
                concepts.append(term)

    return list(set(concepts))  # Remove duplicates

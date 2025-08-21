"""Protocol for rule intelligence services.

This module defines the protocol interface for rule intelligence services,
following the existing service pattern established in the codebase.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from ....core.error_types import ProcessingError
    from ....core.models.rule_types import Action, Condition, Hazard, Sense, Status
    from ....core.result import Result
    from .enhanced_cross_reference_manager import RuleRelationship
    from .rule_search_result import RuleSearchResult


@runtime_checkable
class RuleIntelligenceProtocol(Protocol):
    """Protocol for rule intelligence services.

    This protocol defines the interface for services that provide intelligent
    analysis of D&D 5e rules, including relationship discovery, cross-reference
    resolution, and rule combination validation.

    The service provides:
    - Rule relationship discovery using tag analysis
    - Cross-reference resolution with <100ms performance target
    - Rule combination validation with conflict detection
    - Intelligent rule search with enhanced metadata
    """

    def get_service_name(self) -> str:
        """Return the service name for debugging and logging.

        Returns:
            Human-readable service name for identification
        """
        ...

    async def discover_rule_relationships(
        self, rule_ids: list[str] | None = None
    ) -> Result[list[RuleRelationship], ProcessingError]:
        """Discover relationships between rules using intelligent analysis.

        Args:
            rule_ids: Optional list of specific rule IDs to analyze.
                     If None, analyzes all known rules.

        Returns:
            Result containing list of discovered relationships or error
        """
        ...

    async def find_rule_cross_references(
        self, rule_id: str, max_depth: int = 2, include_analysis: bool = True
    ) -> Result[dict[str, Any], ProcessingError]:
        """Find cross-references for a specific rule.

        Args:
            rule_id: Rule identifier to find references for
            max_depth: Maximum depth for recursive reference discovery
            include_analysis: Whether to include complexity analysis

        Returns:
            Result containing cross-reference data with analysis or error
        """
        ...

    async def validate_rule_combination(
        self, rule_ids: list[str], context: dict[str, Any] | None = None
    ) -> Result[dict[str, Any], ProcessingError]:
        """Validate that a combination of rules can work together.

        Args:
            rule_ids: List of rule identifiers to validate
            context: Optional context for validation (e.g., character level, class)

        Returns:
            Result containing validation results with conflicts/synergies or error
        """
        ...

    async def search_rules_intelligent(
        self,
        query: str,
        rule_types: list[str] | None = None,
        sources: list[str] | None = None,
        complexity_filter: tuple[float, float] | None = None,
        include_relationships: bool = True,
        limit: int = 20,
    ) -> Result[RuleSearchResult, ProcessingError]:
        """Perform intelligent rule search with enhanced analysis.

        Args:
            query: Search query string
            rule_types: Optional filter for specific rule types (action, condition, etc.)
            sources: Optional source filter
            complexity_filter: Optional (min, max) complexity score filter
            include_relationships: Whether to include relationship analysis
            limit: Maximum number of results

        Returns:
            Result containing enhanced search results or error
        """
        ...

    async def analyze_rule_complexity(
        self, rule_id: str
    ) -> Result[dict[str, Any], ProcessingError]:
        """Analyze the complexity of a specific rule.

        Args:
            rule_id: Rule identifier to analyze

        Returns:
            Result containing complexity analysis or error
        """
        ...

    async def get_rule_suggestions(
        self, context: dict[str, Any]
    ) -> Result[list[dict[str, Any]], ProcessingError]:
        """Get intelligent rule suggestions based on context.

        Args:
            context: Context for suggestions (e.g., character class, situation)

        Returns:
            Result containing list of suggested rules with explanations or error
        """
        ...

    async def register_rule_content(
        self,
        rule_content: Action | Condition | Sense | Hazard | Status,
        source: str | None = None,
        page: str | None = None,
        section: str | None = None,
    ) -> Result[str, ProcessingError]:
        """Register rule content for analysis.

        Args:
            rule_content: Rule content object
            source: Source book abbreviation
            page: Page number in source
            section: Document section

        Returns:
            Result containing rule reference ID or error
        """
        ...

    def supports_rule_type(self, rule_type: str) -> bool:
        """Check if the service supports a specific rule type.

        Args:
            rule_type: Rule type to check (action, condition, sense, hazard, status)

        Returns:
            True if the rule type is supported
        """
        ...

    def get_supported_rule_types(self) -> list[str]:
        """Get list of all supported rule types.

        Returns:
            List of supported rule type identifiers
        """
        ...

    def get_performance_statistics(self) -> dict[str, Any]:
        """Get performance statistics for the service.

        Returns:
            Dictionary with performance metrics, cache stats, and usage data
        """
        ...

    async def clear_analysis_cache(self) -> None:
        """Clear the analysis cache to free memory."""
        ...

    async def rebuild_relationship_index(self) -> Result[int, ProcessingError]:
        """Rebuild the rule relationship index.

        Returns:
            Result containing number of relationships discovered or error
        """
        ...


@runtime_checkable
class RuleIntelligenceConfigProtocol(Protocol):
    """Protocol for rule intelligence configuration.

    Defines configuration options for rule intelligence services.
    """

    def get_relationship_confidence_threshold(self) -> float:
        """Get minimum confidence threshold for rule relationships.

        Returns:
            Confidence threshold (0.0 to 1.0)
        """
        ...

    def get_complexity_weights(self) -> dict[str, float]:
        """Get weights for complexity calculation factors.

        Returns:
            Dictionary mapping factor names to weights
        """
        ...

    def get_performance_targets(self) -> dict[str, float]:
        """Get performance targets for operations.

        Returns:
            Dictionary mapping operation names to target times in milliseconds
        """
        ...

    def is_caching_enabled(self) -> bool:
        """Check if caching is enabled.

        Returns:
            True if caching should be used
        """
        ...

    def get_cache_ttl_seconds(self) -> float:
        """Get cache TTL in seconds.

        Returns:
            Cache time-to-live in seconds
        """
        ...


@runtime_checkable
class RuleAnalysisProtocol(Protocol):
    """Protocol for rule analysis components.

    Defines interface for specific rule analysis components that can be
    plugged into the rule intelligence service.
    """

    def analyze_rule_text(self, rule_text: str) -> dict[str, Any]:
        """Analyze rule text for complexity and features.

        Args:
            rule_text: Rule text to analyze

        Returns:
            Analysis results dictionary
        """
        ...

    def extract_rule_dependencies(
        self, rule_content: Any
    ) -> list[tuple[str, str, float]]:
        """Extract dependencies from rule content.

        Args:
            rule_content: Rule content object

        Returns:
            List of (dependency_type, dependency_target, confidence) tuples
        """
        ...

    def calculate_interaction_score(self, rule1: Any, rule2: Any) -> tuple[float, str]:
        """Calculate interaction score between two rules.

        Args:
            rule1: First rule object
            rule2: Second rule object

        Returns:
            Tuple of (score, interaction_type)
        """
        ...

    def get_analysis_version(self) -> str:
        """Get version identifier for this analysis component.

        Returns:
            Version string for compatibility tracking
        """
        ...

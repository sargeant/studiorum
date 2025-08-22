"""
Example usage of the new MCP async service bridge.

This module demonstrates how to use the simplified async service bridge for MCP tool
development, showing both the high-level convenience methods and the lower-level
service container access patterns.
"""

import asyncio
from typing import Any

from ..core.error_types import ErrorCategory, ErrorSeverity, MCPError, MCPErrorCode
from ..core.logging import get_logger
from ..core.services.protocols import OmnidexerProtocol, TagResolverProtocol
from .async_service_bridge import (
    MCPServiceContext,
    MCPToolBase,
    create_mcp_service_context,
)

logger = get_logger(__name__)


# Example 1: Using the high-level convenience functions
async def example_spell_search() -> None:
    """Example of using the simplified MCP service context for spell search."""
    print("=== Example 1: High-level spell search ===")

    async with create_mcp_service_context("example_spell_search") as ctx:
        # Simple spell search using the convenience method
        results = await ctx.search_spells("fireball")

        print(f"Found {results['total']} spells matching 'fireball'")
        print(f"Request ID: {ctx.request_id}")
        print(f"Duration: {ctx.duration_ms}ms")

        if results["spells"]:
            first_spell = results["spells"][0]
            print(f"First result: {first_spell.get('name', 'Unknown')}")


# Example 2: Using configuration overrides
async def example_creature_search_with_config() -> None:
    """Example of using configuration overrides for source filtering."""
    print("\n=== Example 2: Creature search with config overrides ===")

    config_overrides = {
        "sources": ["phb", "mm"]  # Only Player's Handbook and Monster Manual
    }

    async with create_mcp_service_context(
        "example_creature_search", config_overrides=config_overrides
    ) as ctx:
        results = await ctx.search_creatures("dragon")

        print(f"Found {results['total']} dragons in sources: {results['sources_used']}")
        print(f"Request ID: {ctx.request_id}")


# Example 3: Using the MCPToolBase for structured tool development
class ExampleSpellAnalyzer(MCPToolBase):
    """Example MCP tool that analyzes spell complexity."""

    async def execute(self, ctx: MCPServiceContext, **params: Any) -> dict[str, Any]:
        """Analyze spells and provide complexity metrics."""
        query = params.get("query", "")
        analysis_type = params.get("analysis_type", "basic")

        if not query:
            await ctx.add_error(
                MCPError(
                    message="query parameter is required",
                    error_code=MCPErrorCode.INVALID_PARAMS,
                    category=ErrorCategory.VALIDATION,
                    severity=ErrorSeverity.ERROR,
                )
            )
            return {"error": "Missing query parameter"}

        # Search for spells
        spell_results = await ctx.search_spells(query)

        if not spell_results["spells"]:
            return {"analysis": None, "message": f"No spells found matching '{query}'"}

        # Perform analysis
        analysis = await self._analyze_spells(
            spell_results["spells"], analysis_type, ctx
        )

        return {
            "query": query,
            "analysis_type": analysis_type,
            "analysis": analysis,
            "request_id": str(ctx.request_id),
            "performance": {
                "duration_ms": ctx.duration_ms,
                "spells_analyzed": len(spell_results["spells"]),
            },
        }

    async def _analyze_spells(
        self, spells: list[dict[str, Any]], analysis_type: str, ctx: MCPServiceContext
    ) -> dict[str, Any]:
        """Analyze spell complexity using service container access."""

        if analysis_type == "basic":
            return {
                "total_spells": len(spells),
                "level_distribution": self._get_level_distribution(spells),
                "school_distribution": self._get_school_distribution(spells),
            }
        elif analysis_type == "advanced":
            # Get tag resolver for advanced analysis
            tag_resolver = await ctx.get_service(TagResolverProtocol)  # type: ignore[type-abstract]

            # Perform tag-based analysis
            tag_analysis = await self._analyze_spell_tags(spells, tag_resolver)

            return {
                "total_spells": len(spells),
                "level_distribution": self._get_level_distribution(spells),
                "school_distribution": self._get_school_distribution(spells),
                "tag_analysis": tag_analysis,
                "complexity_score": self._calculate_complexity_score(spells),
            }
        else:
            return {"error": f"Unknown analysis type: {analysis_type}"}

    def _get_level_distribution(self, spells: list[dict[str, Any]]) -> dict[str, int]:
        """Get distribution of spell levels."""
        distribution: dict[str, int] = {}
        for spell in spells:
            level = spell.get("level", "unknown")
            key = f"level_{level}"
            distribution[key] = distribution.get(key, 0) + 1
        return distribution

    def _get_school_distribution(self, spells: list[dict[str, Any]]) -> dict[str, int]:
        """Get distribution of spell schools."""
        distribution: dict[str, int] = {}
        for spell in spells:
            school = spell.get("school", "unknown")
            if isinstance(school, dict):
                school = school.get("name", "unknown")
            distribution[school] = distribution.get(school, 0) + 1
        return distribution

    async def _analyze_spell_tags(
        self, spells: list[dict[str, Any]], tag_resolver: TagResolverProtocol
    ) -> dict[str, Any]:
        """Analyze spell descriptions for tag usage."""
        tag_count = 0
        unique_tags = set()

        for spell in spells:
            entries = spell.get("entries", [])
            for entry in entries:
                if isinstance(entry, str) and "@" in entry:
                    # Simple tag detection (real implementation would use tag_resolver)
                    import re

                    tags = re.findall(r"{@[^}]+}", entry)
                    tag_count += len(tags)
                    unique_tags.update(tags)

        return {
            "total_tags": tag_count,
            "unique_tags": len(unique_tags),
            "tag_density": tag_count / len(spells) if spells else 0,
        }

    def _calculate_complexity_score(self, spells: list[dict[str, Any]]) -> float:
        """Calculate average complexity score for spells."""
        total_score = 0
        for spell in spells:
            # Simple complexity calculation based on level and components
            level = spell.get("level", 0)
            components = spell.get("components", {})
            component_count = len(components) if isinstance(components, dict) else 0

            # Basic formula: level weight + component complexity
            complexity = (level * 2) + component_count
            total_score += complexity

        return total_score / len(spells) if spells else 0


# Example 4: Using direct service container access
async def example_direct_service_access() -> None:
    """Example of direct service container access for advanced scenarios."""
    print("\n=== Example 4: Direct service container access ===")

    async with create_mcp_service_context("example_direct_access") as ctx:
        # Get omnidexer directly from service container
        omnidexer = await ctx.get_service(OmnidexerProtocol)  # type: ignore[type-abstract]

        # Use omnidexer directly for advanced operations
        from ..core.models.content import ContentType

        all_spells = omnidexer.get_all_by_type(ContentType.SPELL)

        print(f"Direct access found {len(all_spells)} total spells")
        print(f"Service container request ID: {ctx.request_id}")

        # Get tag resolver for text processing
        tag_resolver = await ctx.get_service(TagResolverProtocol)  # type: ignore[type-abstract]

        print(f"Tag resolver service: {type(tag_resolver).__name__}")


# Example 5: Error handling and performance monitoring
async def example_error_handling() -> None:
    """Example of proper error handling and performance monitoring."""
    print("\n=== Example 5: Error handling and performance monitoring ===")

    async with create_mcp_service_context(
        "example_error_handling", enable_performance_monitoring=True
    ) as ctx:
        try:
            # Intentionally trigger an error
            results = await ctx.search_content("", "invalid_type")
            print(f"Unexpected success: {results}")
        except Exception as e:
            print(f"Caught expected error: {e}")

            # Check context for errors
            if ctx.has_errors:
                errors = ctx.get_errors()
                print(f"Context has {len(errors)} errors:")
                for error in errors:
                    print(f"  - {error.message} ({error.error_code})")

        # Check performance metrics
        print(f"Final duration: {ctx.duration_ms}ms")


# Main demonstration function
async def main() -> None:
    """Run all examples to demonstrate the async service bridge."""
    print("🚀 MCP Async Service Bridge Examples")
    print("=" * 50)

    try:
        # Example 1: Simple spell search
        await example_spell_search()

        # Example 2: Configuration overrides
        await example_creature_search_with_config()

        # Example 3: Structured tool development
        print("\n=== Example 3: Structured tool with MCPToolBase ===")
        analyzer = ExampleSpellAnalyzer()

        # Basic analysis
        basic_result = await analyzer.execute_with_config(
            config_overrides={}, query="healing", analysis_type="basic"
        )
        print(
            f"Basic analysis completed: {basic_result.get('analysis', {}).get('total_spells', 0)} spells"
        )

        # Advanced analysis
        advanced_result = await analyzer.execute_with_config(
            config_overrides={"sources": ["phb"]},
            query="fire",
            analysis_type="advanced",
        )
        print(
            f"Advanced analysis completed with complexity score: {advanced_result.get('analysis', {}).get('complexity_score', 0):.2f}"
        )

        # Example 4: Direct service access
        await example_direct_service_access()

        # Example 5: Error handling
        await example_error_handling()

        print("\n✅ All examples completed successfully!")

    except Exception as e:
        print(f"❌ Example failed: {e}")
        logger.exception("Example execution failed")


if __name__ == "__main__":
    asyncio.run(main())

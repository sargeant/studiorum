"""Tests for rules intelligence tools.

This module tests the rule intelligence functionality including cross-reference
discovery, rule combination validation, and intelligent search capabilities.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from dnd5e.core.context import AsyncRequestContext
from dnd5e.core.error_types import ContentNotFoundError, ProcessingError
from dnd5e.core.models.rule_types import Action, Condition
from dnd5e.core.result import Error, Success
from dnd5e.mcp.tools.rules import (
    find_rule_cross_references,
    get_rule_suggestions,
    search_rules_intelligent,
    validate_rule_combination,
)
from dnd5e.mcp.tools.rules.enhanced_cross_reference_manager import (
    EnhancedCrossReferenceManager,
    RuleRelationship,
)
from dnd5e.mcp.tools.rules.rule_intelligence_service import (
    RuleIntelligenceConfig,
    RuleIntelligenceService,
)
from dnd5e.mcp.tools.rules.rule_search_result import RuleSearchResult


class TestRulesIntelligence:
    """Test suite for rules intelligence functionality."""

    def setup_method(self) -> None:
        """Set up test environment for each test method."""
        # Import and call the test environment reset function
        from tests.test_helpers import reset_test_environment

        reset_test_environment()

    @pytest.fixture
    def mock_omnidexer(self) -> MagicMock:
        """Create a mock omnidexer for testing."""
        omnidexer = MagicMock()
        omnidexer.search_content_async = AsyncMock()
        omnidexer.get_content_async = AsyncMock()
        omnidexer.search = MagicMock(return_value=[])
        return omnidexer

    @pytest.fixture
    def mock_tag_resolver(self) -> MagicMock:
        """Create a mock tag resolver for testing."""
        tag_resolver = MagicMock()
        tag_resolver.has_handler = MagicMock(return_value=True)
        tag_resolver.process_text = MagicMock(return_value="processed_text")
        return tag_resolver

    @pytest.fixture
    def mock_context(self) -> MagicMock:
        """Create a mock async request context for testing."""
        context = MagicMock(spec=AsyncRequestContext)
        context.get_service = AsyncMock()
        context.record_cache_hit = MagicMock()
        context.record_cache_miss = MagicMock()
        context.record_async_operation = MagicMock()
        context.add_async_error = AsyncMock()
        context.request_id = "test-request-123"
        context.sources = []
        return context

    @pytest.fixture
    def sample_action(self) -> Action:
        """Create a sample action for testing."""
        from dnd5e.core.models.sources import Source

        return Action(
            name="Attack",
            source=Source(abbreviation="PHB", full_name="Player's Handbook"),
            entries=["Make a weapon attack against a target."],
            time=[{"number": 1, "unit": "action"}],
        )

    @pytest.fixture
    def sample_condition(self) -> Condition:
        """Create a sample condition for testing."""
        from dnd5e.core.models.sources import Source

        return Condition(
            name="Blinded",
            source=Source(abbreviation="PHB", full_name="Player's Handbook"),
            entries=[
                "A blinded creature can't see and automatically fails any ability check that requires sight."
            ],
        )

    def test_enhanced_cross_reference_manager_initialization(self) -> None:
        """Test that the enhanced cross-reference manager initializes correctly."""
        manager = EnhancedCrossReferenceManager()

        assert manager.rule_references == {}
        assert manager.rule_relationships == []
        assert manager._performance_cache == {}
        assert manager._cache_ttl == 300.0

    def test_rule_relationship_model(self) -> None:
        """Test the RuleRelationship model validation."""
        relationship = RuleRelationship(
            source_rule="action:attack",
            target_rule="condition:blinded",
            relationship_type="causes",
            confidence=0.75,
            source_text="Attack can cause blindness",
        )

        assert relationship.source_rule == "action:attack"
        assert relationship.target_rule == "condition:blinded"
        assert relationship.relationship_type == "causes"
        assert relationship.confidence == 0.75
        assert relationship.source_text == "Attack can cause blindness"

    def test_rule_intelligence_service_initialization(
        self, mock_omnidexer: MagicMock, mock_tag_resolver: MagicMock
    ) -> None:
        """Test rule intelligence service initialization."""
        config = RuleIntelligenceConfig()
        service = RuleIntelligenceService(
            omnidexer=mock_omnidexer,
            tag_resolver=mock_tag_resolver,
            config=config,
        )

        assert service.get_service_name() == "RuleIntelligenceService"
        assert service.omnidexer == mock_omnidexer
        assert service.tag_resolver == mock_tag_resolver
        assert service.config == config
        assert service.supports_rule_type("action")
        assert service.supports_rule_type("condition")
        assert not service.supports_rule_type("invalid_type")

    @pytest.mark.asyncio
    async def test_register_rule_content_success(
        self,
        mock_omnidexer: MagicMock,
        mock_tag_resolver: MagicMock,
        sample_action: Action,
    ) -> None:
        """Test successful rule content registration."""
        service = RuleIntelligenceService(
            omnidexer=mock_omnidexer,
            tag_resolver=mock_tag_resolver,
        )

        result = await service.register_rule_content(
            rule_content=sample_action,
            source="PHB",
            page="195",
        )

        assert result.is_success()
        rule_id = result.unwrap()
        assert rule_id.startswith("action:")
        assert rule_id in service.cross_ref_manager.rule_references

    @pytest.mark.asyncio
    async def test_discover_rule_relationships(
        self,
        mock_omnidexer: MagicMock,
        mock_tag_resolver: MagicMock,
        sample_action: Action,
        sample_condition: Condition,
    ) -> None:
        """Test rule relationship discovery."""
        service = RuleIntelligenceService(
            omnidexer=mock_omnidexer,
            tag_resolver=mock_tag_resolver,
        )

        # Register sample rules
        await service.register_rule_content(sample_action, source="PHB")
        await service.register_rule_content(sample_condition, source="PHB")

        # Discover relationships
        result = await service.discover_rule_relationships()

        assert result.is_success()
        relationships = result.unwrap()
        assert isinstance(relationships, list)

    @pytest.mark.asyncio
    async def test_find_rule_cross_references_success(
        self, mock_context: MagicMock
    ) -> None:
        """Test successful rule cross-reference discovery."""
        mock_context.get_service.return_value = MagicMock()

        # Mock the service creation and method calls
        with patch(
            "dnd5e.mcp.tools.rules.tools._get_rule_intelligence_service"
        ) as mock_get_service:
            mock_service = AsyncMock()
            mock_service.find_rule_cross_references.return_value = Success(
                {
                    "rule": {"id": "action:attack", "name": "Attack"},
                    "direct_relationships": [],
                    "indirect_relationships": [],
                    "total_relationships": 0,
                }
            )
            mock_get_service.return_value = mock_service

            result = await find_rule_cross_references(
                rule_id="action:attack",
                max_depth=2,
                include_analysis=True,
                ctx=mock_context,
            )

            assert "rule" in result
            assert "mcp_metadata" in result
            assert result["mcp_metadata"]["tool"] == "find_rule_cross_references"

    @pytest.mark.asyncio
    async def test_find_rule_cross_references_invalid_params(
        self, mock_context: MagicMock
    ) -> None:
        """Test rule cross-reference discovery with invalid parameters."""
        from dnd5e.core.error_types import MCPException

        # Test empty rule_id
        with pytest.raises(MCPException) as exc_info:
            await find_rule_cross_references(
                rule_id="",
                ctx=mock_context,
            )
        assert "rule_id parameter is required" in str(exc_info.value)

        # Test invalid max_depth
        with pytest.raises(MCPException) as exc_info:
            await find_rule_cross_references(
                rule_id="action:attack",
                max_depth=10,  # Too high
                ctx=mock_context,
            )
        assert "max_depth must be between 1 and 5" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_rule_combination_success(
        self, mock_context: MagicMock
    ) -> None:
        """Test successful rule combination validation."""
        mock_context.get_service.return_value = MagicMock()

        with patch(
            "dnd5e.mcp.tools.rules.tools._get_rule_intelligence_service"
        ) as mock_get_service:
            mock_service = AsyncMock()
            mock_service.validate_rule_combination.return_value = Success(
                {
                    "valid": True,
                    "combination_score": 0.8,
                    "conflicts": [],
                    "synergies": [],
                    "warnings": [],
                }
            )
            mock_get_service.return_value = mock_service

            result = await validate_rule_combination(
                rule_ids=["action:attack", "condition:blinded"],
                context={"character_class": "fighter", "level": 5},
                ctx=mock_context,
            )

            assert "valid" in result
            assert "mcp_metadata" in result
            assert result["mcp_metadata"]["tool"] == "validate_rule_combination"

    @pytest.mark.asyncio
    async def test_validate_rule_combination_invalid_params(
        self, mock_context: MagicMock
    ) -> None:
        """Test rule combination validation with invalid parameters."""
        from dnd5e.core.error_types import MCPException

        # Test empty rule_ids
        with pytest.raises(MCPException) as exc_info:
            await validate_rule_combination(
                rule_ids=[],
                ctx=mock_context,
            )
        assert "rule_ids parameter must be a non-empty list" in str(exc_info.value)

        # Test single rule (need at least 2)
        with pytest.raises(MCPException) as exc_info:
            await validate_rule_combination(
                rule_ids=["action:attack"],
                ctx=mock_context,
            )
        assert "At least 2 rule IDs are required" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_search_rules_intelligent_success(
        self, mock_context: MagicMock
    ) -> None:
        """Test successful intelligent rule search."""
        mock_context.get_service.return_value = MagicMock()

        with patch(
            "dnd5e.mcp.tools.rules.tools._get_rule_intelligence_service"
        ) as mock_get_service:
            mock_service = AsyncMock()

            # Create a mock RuleSearchResult
            mock_search_result = MagicMock(spec=RuleSearchResult)
            mock_search_result.to_dict.return_value = {
                "content": [],
                "total": 0,
                "query": "attack",
                "content_type": "rules",
                "sources_used": [],
                "performance": {"duration_ms": 50.0, "cached": False},
            }
            mock_search_result.total = 0
            mock_search_result.generate_summary.return_value = {
                "total_rules": 0,
                "complexity_summary": {"average": 0.0},
            }

            mock_service.search_rules_intelligent.return_value = Success(
                mock_search_result
            )
            mock_get_service.return_value = mock_service

            result = await search_rules_intelligent(
                query="attack",
                rule_types=["action"],
                limit=10,
                ctx=mock_context,
            )

            assert "content" in result
            assert "mcp_metadata" in result
            assert result["mcp_metadata"]["tool"] == "search_rules_intelligent"

    @pytest.mark.asyncio
    async def test_search_rules_intelligent_invalid_params(
        self, mock_context: MagicMock
    ) -> None:
        """Test intelligent rule search with invalid parameters."""
        from dnd5e.core.error_types import MCPException

        # Test empty query
        with pytest.raises(MCPException) as exc_info:
            await search_rules_intelligent(
                query="",
                ctx=mock_context,
            )
        assert "query parameter is required" in str(exc_info.value)

        # Test invalid limit
        with pytest.raises(MCPException) as exc_info:
            await search_rules_intelligent(
                query="attack",
                limit=100,  # Too high
                ctx=mock_context,
            )
        assert "limit must be between 1 and 50" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_rule_suggestions_success(self, mock_context: MagicMock) -> None:
        """Test successful rule suggestion generation."""
        mock_context.get_service.return_value = MagicMock()

        with patch(
            "dnd5e.mcp.tools.rules.tools._get_rule_intelligence_service"
        ) as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_rule_suggestions.return_value = Success(
                [
                    {
                        "rule_id": "action:attack",
                        "rule_name": "Attack",
                        "relevance_reason": "Relevant to fighter",
                        "complexity_score": 0.3,
                    }
                ]
            )
            mock_get_service.return_value = mock_service

            result = await get_rule_suggestions(
                context={"character_class": "fighter", "level": 5},
                limit=5,
                ctx=mock_context,
            )

            assert "suggestions" in result
            assert "mcp_metadata" in result
            assert result["mcp_metadata"]["tool"] == "get_rule_suggestions"

    @pytest.mark.asyncio
    async def test_get_rule_suggestions_invalid_params(
        self, mock_context: MagicMock
    ) -> None:
        """Test rule suggestion generation with invalid parameters."""
        from dnd5e.core.error_types import MCPException

        # Test empty context
        with pytest.raises(MCPException) as exc_info:
            await get_rule_suggestions(
                context={},
                ctx=mock_context,
            )
        assert "context parameter must be a non-empty dictionary" in str(exc_info.value)

        # Test invalid limit
        with pytest.raises(MCPException) as exc_info:
            await get_rule_suggestions(
                context={"character_class": "fighter"},
                limit=25,  # Too high
                ctx=mock_context,
            )
        assert "limit must be between 1 and 20" in str(exc_info.value)

    def test_performance_statistics(
        self, mock_omnidexer: MagicMock, mock_tag_resolver: MagicMock
    ) -> None:
        """Test performance statistics collection."""
        service = RuleIntelligenceService(
            omnidexer=mock_omnidexer,
            tag_resolver=mock_tag_resolver,
        )

        stats = service.get_performance_statistics()

        assert "service_name" in stats
        assert "cross_reference_stats" in stats
        assert "operation_times" in stats
        assert "configuration" in stats
        assert "performance_targets" in stats
        assert stats["service_name"] == "RuleIntelligenceService"

    @pytest.mark.asyncio
    async def test_clear_analysis_cache(
        self, mock_omnidexer: MagicMock, mock_tag_resolver: MagicMock
    ) -> None:
        """Test analysis cache clearing."""
        service = RuleIntelligenceService(
            omnidexer=mock_omnidexer,
            tag_resolver=mock_tag_resolver,
        )

        # Add something to cache
        service.cross_ref_manager._performance_cache["test"] = ("data", 123.0)
        assert len(service.cross_ref_manager._performance_cache) > 0

        # Clear cache
        await service.clear_analysis_cache()
        assert len(service.cross_ref_manager._performance_cache) == 0

    @pytest.mark.asyncio
    async def test_rebuild_relationship_index(
        self, mock_omnidexer: MagicMock, mock_tag_resolver: MagicMock
    ) -> None:
        """Test relationship index rebuilding."""
        service = RuleIntelligenceService(
            omnidexer=mock_omnidexer,
            tag_resolver=mock_tag_resolver,
        )

        # Mock the discover_rule_relationships method
        with patch.object(service, "discover_rule_relationships") as mock_discover:
            mock_discover.return_value = Success([])

            result = await service.rebuild_relationship_index()

            assert result.is_success()
            assert result.unwrap() == 0  # No relationships found
            mock_discover.assert_called_once()

    def test_rule_search_result_creation(self) -> None:
        """Test RuleSearchResult creation and methods."""
        from dnd5e.mcp.tools.rules.rule_search_result import create_rule_search_result

        # Create sample content
        content = []

        # Create search result
        result = create_rule_search_result(
            content=content,
            total=0,
            query="test",
            content_type="rules",
            sources_used=["PHB"],
            duration_ms=50.0,
            cached=False,
        )

        assert isinstance(result, RuleSearchResult)
        assert result.total == 0
        assert result.query == "test"
        assert result.content_type == "rules"
        assert result.duration_ms == 50.0

        # Test summary generation
        summary = result.generate_summary()
        assert "total_rules" in summary
        assert "complexity_summary" in summary
        assert "relationship_summary" in summary

    @pytest.mark.asyncio
    async def test_error_handling_in_tools(self, mock_context: MagicMock) -> None:
        """Test error handling in MCP tools."""
        from dnd5e.core.error_types import MCPException

        # Mock service to raise an exception
        with patch(
            "dnd5e.mcp.tools.rules.tools._get_rule_intelligence_service"
        ) as mock_get_service:
            mock_service = AsyncMock()
            mock_service.find_rule_cross_references.return_value = Error(
                ProcessingError(message="Test error", category="processing")
            )
            mock_get_service.return_value = mock_service

            with pytest.raises(MCPException) as exc_info:
                await find_rule_cross_references(
                    rule_id="action:attack",
                    ctx=mock_context,
                )

            assert "Test error" in str(exc_info.value)

    def test_rule_intelligence_config_validation(self) -> None:
        """Test rule intelligence configuration validation."""
        # Test default configuration
        config = RuleIntelligenceConfig()
        assert config.relationship_confidence_threshold == 0.3
        assert config.caching_enabled is True
        assert config.cache_ttl_seconds == 300.0

        # Test custom configuration
        custom_config = RuleIntelligenceConfig(
            relationship_confidence_threshold=0.5,
            caching_enabled=False,
            cache_ttl_seconds=600.0,
        )
        assert custom_config.relationship_confidence_threshold == 0.5
        assert custom_config.caching_enabled is False
        assert custom_config.cache_ttl_seconds == 600.0

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_performance_targets(self, mock_context: MagicMock) -> None:
        """Test that operations meet performance targets."""
        import time

        mock_context.get_service.return_value = MagicMock()

        with patch(
            "dnd5e.mcp.tools.rules.tools._get_rule_intelligence_service"
        ) as mock_get_service:
            mock_service = AsyncMock()
            mock_service.find_rule_cross_references.return_value = Success(
                {
                    "rule": {"id": "action:attack", "name": "Attack"},
                    "direct_relationships": [],
                    "total_relationships": 0,
                }
            )
            mock_get_service.return_value = mock_service

            start_time = time.time()
            result = await find_rule_cross_references(
                rule_id="action:attack",
                ctx=mock_context,
            )
            duration_ms = (time.time() - start_time) * 1000

            # Check that the operation completed within target time
            assert duration_ms < 200.0  # 200ms target for rule operations
            assert "mcp_metadata" in result
            assert "performance_target_met" in result["mcp_metadata"]

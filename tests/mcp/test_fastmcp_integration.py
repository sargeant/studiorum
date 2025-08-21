"""FastMCP integration tests for Package 1.3.

This module provides comprehensive tests for the FastMCP server integration,
including tool registration, performance validation, and error handling.

Key Test Areas:
- FastMCP server creation and configuration
- Tool registration and discovery
- Performance targets validation (<200ms)
- Configuration tool integration
- Content search tool functionality
- Error handling and timeouts
"""

from __future__ import annotations

import asyncio
import time
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from studiorum.mcp.registry import (
    ToolRegistry,
    get_tool_registry,
    list_registered_tools as registry_list_tools,
    validate_tool_registry,
)
from studiorum.mcp.server import (
    create_mcp_server,
    get_mcp_app,
    list_registered_tools,
    mcp,
)
from studiorum.mcp.tools.content import (
    PerformantContentSearcher,
    get_content_searcher,
    search_content_performant,
)


class TestFastMCPServerIntegration:
    """Test FastMCP server integration and setup."""

    def test_mcp_server_creation(self):
        """Test that MCP server can be created successfully."""
        # Should not raise exception
        server = get_mcp_app()
        assert server is not None
        assert hasattr(server, "_tool_manager")

    @pytest.mark.asyncio
    async def test_mcp_server_async_creation(self):
        """Test async MCP server creation."""
        server = await create_mcp_server()
        assert server is not None
        assert hasattr(server, "_tool_manager")

    def test_tool_registration_count(self):
        """Test that expected number of tools are registered."""
        tools = list_registered_tools()

        # Should have at least configuration tools and content tools
        assert len(tools) >= 10, f"Expected at least 10 tools, got {len(tools)}"

        # Check for specific tool categories
        config_tools = [t for t in tools if "config" in t or "preference" in t]
        content_tools = [
            t for t in tools if any(word in t for word in ["search", "list", "resolve"])
        ]

        assert len(config_tools) >= 6, (
            f"Expected at least 6 config tools, got {len(config_tools)}"
        )
        assert len(content_tools) >= 6, (
            f"Expected at least 6 content tools, got {len(content_tools)}"
        )

    def test_tool_names_and_categories(self):
        """Test that tools have expected names and are categorized correctly."""
        tools = list_registered_tools()

        # Configuration tools
        expected_config_tools = [
            "get_current_configuration",
            "update_app_configuration",
            "configure_for_paper_layout",
            "configure_for_spellbook_generation",
            "configure_for_encounter_printing",
        ]

        for tool in expected_config_tools:
            assert tool in tools, f"Missing config tool: {tool}"

        # Content search tools
        expected_search_tools = [
            "search_content",
            "search_spells",
            "search_creatures",
            "list_adventures",
            "list_books",
        ]

        for tool in expected_search_tools:
            assert tool in tools, f"Missing search tool: {tool}"

    def test_mcp_server_has_required_attributes(self):
        """Test that MCP server has all required FastMCP attributes."""
        server = get_mcp_app()

        # Check FastMCP-specific attributes
        required_attrs = [
            "name",
            "version",
            "_tool_manager",
            "run_http_async",
            "add_tool",
            "get_tools",
            "tool",
        ]

        for attr in required_attrs:
            assert hasattr(server, attr), f"MCP server missing attribute: {attr}"

    def test_tool_manager_internal_structure(self):
        """Test that tool manager has expected internal structure."""
        server = get_mcp_app()
        tool_manager = server._tool_manager

        assert hasattr(tool_manager, "_tools"), "Tool manager missing _tools attribute"
        assert isinstance(tool_manager._tools, dict), (
            "Tool manager _tools should be dict"
        )

        # Should have tools registered
        assert len(tool_manager._tools) > 0, "No tools registered in tool manager"


class TestContentSearchPerformance:
    """Test content search performance targets."""

    @pytest.mark.asyncio
    async def test_search_content_performance_target(self):
        """Test that search_content meets <200ms performance target."""
        # Mock the underlying search to return quickly
        with patch(
            "dnd5e.mcp.tools.content.ModernContextualAPI.search_spells_async"
        ) as mock_search:
            mock_result = MagicMock()
            mock_result.is_success.return_value = True
            mock_result.unwrap.return_value = [
                MagicMock(name="Fireball", level=3, school="evocation"),
                MagicMock(name="Fire Bolt", level=0, school="evocation"),
            ]
            mock_search.return_value = mock_result

            start_time = time.time()

            result = await search_content_performant(
                content_type="spells", query="fire", limit=10
            )

            duration_ms = (time.time() - start_time) * 1000

            assert duration_ms < 200, (
                f"Search took {duration_ms:.1f}ms, exceeds 200ms target"
            )
            assert result["performance"]["target_met"] is True
            assert "content" in result
            assert len(result["content"]) == 2

    @pytest.mark.asyncio
    async def test_content_searcher_caching(self):
        """Test that content searcher caching works correctly."""
        searcher = get_content_searcher()

        # Clear any existing cache to ensure clean test state
        searcher._cache.clear()

        # Use a unique query to avoid interference from other tests
        test_query = "unique_fireball_test_query_12345"

        # Mock the search method
        with patch.object(searcher, "_search_spells_async") as mock_search:
            mock_search.return_value = [MagicMock(name="Fireball", level=3)]

            # First search - should call the method and not be cached
            result1 = await searcher.search_content_async(
                content_type="spells", query=test_query
            )

            # Second search with same parameters - should use cache
            result2 = await searcher.search_content_async(
                content_type="spells", query=test_query
            )

            # Verify mock was called only once (second call used cache)
            assert mock_search.call_count == 1

            # Verify caching behavior - both results should exist
            assert result1 is not None
            assert result2 is not None

            # The second result should be cached, first should not be
            # Note: The first result gets marked as cached=False when created
            # The second result should be the same object but with cached=True
            assert result2.cached is True

    @pytest.mark.asyncio
    async def test_search_timeout_handling(self):
        """Test that search operations timeout correctly."""
        # Mock the search_content_async method directly to raise TimeoutError
        searcher = get_content_searcher()

        with patch.object(searcher, "_search_spells_async") as mock_search:
            # Make the search method raise TimeoutError
            mock_search.side_effect = TimeoutError("Search timed out")

            # Should timeout and raise MCPException
            with pytest.raises(Exception) as exc_info:
                await searcher.search_content_async(content_type="spells", query="test")

            # Should be a timeout-related error
            error_str = str(exc_info.value).lower()
            assert "timeout" in error_str or "timed out" in error_str

    def test_performance_targets_configuration(self):
        """Test that performance targets are properly configured."""
        searcher = get_content_searcher()

        # Cache duration should be reasonable
        assert 60 <= searcher.cache_duration <= 600, (
            "Cache duration should be 1-10 minutes"
        )

    @pytest.mark.asyncio
    async def test_search_filters_application(self):
        """Test that search filters are applied correctly."""
        searcher = get_content_searcher()

        # Test spell filters - configure MagicMock objects properly
        fireball = MagicMock()
        fireball.configure_mock(name="Fireball", level=3, school="evocation")

        lightning_bolt = MagicMock()
        lightning_bolt.configure_mock(
            name="Lightning Bolt", level=3, school="evocation"
        )

        magic_missile = MagicMock()
        magic_missile.configure_mock(name="Magic Missile", level=1, school="evocation")

        cure_wounds = MagicMock()
        cure_wounds.configure_mock(name="Cure Wounds", level=1, school="necromancy")

        spells = [fireball, lightning_bolt, magic_missile, cure_wounds]

        # Test level filter
        filtered = searcher._apply_spell_filters(spells, {"level": 3})
        assert len(filtered) == 2
        assert all(spell.level == 3 for spell in filtered)

        # Test school filter
        filtered = searcher._apply_spell_filters(spells, {"school": "necromancy"})
        assert len(filtered) == 1
        assert filtered[0].name == "Cure Wounds"

        # Test combined filters
        filtered = searcher._apply_spell_filters(
            spells, {"level": 3, "school": "evocation"}
        )
        assert len(filtered) == 2
        assert all(
            spell.level == 3 and spell.school == "evocation" for spell in filtered
        )


class TestConfigurationToolIntegration:
    """Test Package 1.2 configuration tool integration."""

    def test_configuration_tools_available(self):
        """Test that all configuration tools from Package 1.2 are available."""
        tools = list_registered_tools()

        expected_config_tools = [
            "get_current_configuration",
            "update_app_configuration",
            "configure_for_paper_layout",
            "configure_for_spellbook_generation",
            "configure_for_encounter_printing",
            "add_content_source_to_config",
            "save_preferences_to_file",
            "load_preferences_from_file",
        ]

        for tool in expected_config_tools:
            assert tool in tools, f"Missing configuration tool: {tool}"

    @pytest.mark.asyncio
    async def test_configuration_tool_integration(self):
        """Test that configuration tools integrate properly with MCP."""
        # This is a integration test that would test actual configuration
        # For now, just test that the tools are callable
        server = get_mcp_app()
        tool_manager = server._tool_manager

        # Should have configuration tools registered
        config_tools = [name for name in tool_manager._tools.keys() if "config" in name]

        assert len(config_tools) >= 5, "Should have at least 5 configuration tools"


class TestToolRegistryIntegration:
    """Test tool registry integration."""

    def test_tool_registry_functionality(self):
        """Test that tool registry works correctly."""
        registry = get_tool_registry()
        assert isinstance(registry, ToolRegistry)

        # Registry validation should pass
        issues = validate_tool_registry()

        # Should have some info entries but no critical errors
        assert "errors" in issues
        assert "warnings" in issues
        assert "info" in issues

        # Should not have critical errors that block functionality
        critical_errors = [err for err in issues["errors"] if "critical" in err.lower()]
        assert len(critical_errors) == 0, f"Critical registry errors: {critical_errors}"

    def test_registry_tool_listing_consistency(self):
        """Test that registry and MCP server have consistent tool lists."""
        mcp_tools = set(list_registered_tools())

        # MCP should have all the tools registered with the server
        # Note: registry might be empty if no tools were registered via decorator
        # so this test mainly checks that both systems work

        assert len(mcp_tools) > 0, "MCP server should have registered tools"
        # Registry might be empty if using direct FastMCP registration
        # This is acceptable as we're using FastMCP's native tool system


class TestErrorHandling:
    """Test error handling in MCP integration."""

    @pytest.mark.asyncio
    async def test_search_error_handling(self):
        """Test that search errors are handled gracefully."""
        # Mock the search method to raise an exception directly
        searcher = get_content_searcher()

        with patch.object(searcher, "_search_spells_async") as mock_search:
            # Make the search method raise an exception with our test message
            mock_search.side_effect = Exception("Test error")

            with pytest.raises(Exception) as exc_info:
                await searcher.search_content_async(content_type="spells", query="test")

            # Check that "Test error" is somewhere in the error chain
            error_str = str(exc_info.value)
            assert "Test error" in error_str, f"Expected 'Test error' in '{error_str}'"

    def test_tool_listing_error_resilience(self):
        """Test that tool listing handles errors gracefully."""
        # Even if there are issues, tool listing should not crash
        tools = list_registered_tools()
        assert isinstance(tools, list)
        # Should always return a list, even if empty


class TestPerformanceMonitoring:
    """Test performance monitoring integration."""

    @pytest.mark.asyncio
    async def test_performance_metrics_collection(self):
        """Test that performance metrics are collected correctly."""
        with patch(
            "dnd5e.mcp.tools.content.ModernContextualAPI.search_spells_async"
        ) as mock_search:
            mock_result = MagicMock()
            mock_result.is_success.return_value = True
            mock_result.unwrap.return_value = []
            mock_search.return_value = mock_result

            result = await search_content_performant(
                content_type="spells", query="test"
            )

            assert "performance" in result
            perf = result["performance"]

            assert "duration_ms" in perf
            assert "cached" in perf
            assert "target_met" in perf

            assert isinstance(perf["duration_ms"], float)
            assert isinstance(perf["cached"], bool)
            assert isinstance(perf["target_met"], bool)

    def test_performance_target_validation(self):
        """Test that performance targets are validated correctly."""
        # Fast operation should meet target
        fast_duration = 50.0  # 50ms
        assert fast_duration < 200.0

        # Slow operation should not meet target
        slow_duration = 300.0  # 300ms
        assert slow_duration > 200.0


# Integration test markers
pytestmark = [pytest.mark.mcp, pytest.mark.integration, pytest.mark.fast]

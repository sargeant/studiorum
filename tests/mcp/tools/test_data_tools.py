"""Tests for MCP data management tools.

This module tests the new MCP tools for data repository management
from Package 3 implementation.
"""

from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from studiorum.core.context import AsyncRequestContext
from studiorum.core.services.protocols import (
    ContentAttributionProtocol,
    SourceManagerProtocol,
)
from studiorum.mcp.tools.attribution import manage_source_attribution
from studiorum.mcp.tools.data import manage_data_sources


class TestDataSourcesMCPTool:
    """Test the manage_data_sources MCP tool."""

    def setup_method(self):
        """Set up test environment."""
        from studiorum.core.services.container import ServiceContainer

        ServiceContainer.reset_global_instance()

    @pytest.mark.asyncio
    async def test_list_action(self):
        """Test listing data repositories via MCP."""
        # Mock context and manager
        mock_context = AsyncMock(spec=AsyncRequestContext)
        mock_manager = Mock()
        mock_context.get_service = AsyncMock(return_value=mock_manager)

        # Mock statistics response
        mock_manager.get_source_statistics.return_value = {
            "repositories": [
                {
                    "name": "test-repo",
                    "type": "srd",
                    "enabled": True,
                    "description": "Test repository",
                    "path": "/test/path",
                },
                {
                    "name": "homebrew-repo",
                    "type": "extension",
                    "enabled": True,
                    "description": "Homebrew repository",
                    "source_path": "/homebrew/path",
                },
            ],
            "total_sources": 2,
            "active_sources": 2,
        }

        # Call tool
        result = await manage_data_sources(action="list", context=mock_context)

        # Verify result
        assert "repositories" in result
        assert len(result["repositories"]) == 2
        assert result["total_count"] == 2
        assert result["repositories"][0]["name"] == "test-repo"
        assert result["repositories"][0]["type"] == "srd"
        assert result["repositories"][1]["name"] == "homebrew-repo"
        assert result["repositories"][1]["type"] == "extension"

        # Check performance tracking
        assert "performance" in result
        assert "duration_ms" in result["performance"]
        assert "target_met" in result["performance"]

    @pytest.mark.asyncio
    async def test_status_action(self):
        """Test getting repository status via MCP."""
        # Mock context and manager
        mock_context = AsyncMock(spec=AsyncRequestContext)
        mock_manager = Mock()
        mock_context.get_service = AsyncMock(return_value=mock_manager)

        # Mock detailed statistics
        mock_manager.get_source_statistics.return_value = {
            "total_sources": 3,
            "active_sources": 2,
            "total_files": 1500,
            "last_sync": "2025-08-25T10:30:00",
            "sync_errors": ["Warning: slow network"],
            "repositories": [
                {
                    "name": "srd-data",
                    "type": "srd",
                    "enabled": True,
                    "file_count": 800,
                    "validation_errors": [],
                },
                {
                    "name": "primary-5etools",
                    "type": "primary",
                    "enabled": True,
                    "file_count": 700,
                    "validation_errors": ["Missing adventures.json"],
                },
                {
                    "name": "homebrew-disabled",
                    "type": "extension",
                    "enabled": False,
                    "file_count": 0,
                    "validation_errors": ["Path not accessible"],
                },
            ],
        }

        # Call tool
        result = await manage_data_sources(action="status", context=mock_context)

        # Verify result structure
        assert result["total_repositories"] == 3
        assert result["active_repositories"] == 2
        assert result["indexed_files"] == 1500
        assert result["last_index_time"] == "2025-08-25T10:30:00"
        assert result["errors"] == ["Warning: slow network"]
        assert len(result["repositories"]) == 3

        # Check specific repository details
        repos = {r["name"]: r for r in result["repositories"]}
        assert repos["srd-data"]["enabled"] is True
        assert repos["srd-data"]["file_count"] == 800
        assert repos["primary-5etools"]["validation_errors"] == [
            "Missing adventures.json"
        ]
        assert repos["homebrew-disabled"]["enabled"] is False

    @pytest.mark.asyncio
    async def test_add_primary_action_valid_path(self, tmp_path):
        """Test adding primary repository with valid path via MCP."""
        # Create test directory
        test_dir = tmp_path / "5etools-data"
        test_dir.mkdir()

        # Mock context and manager
        mock_context = AsyncMock(spec=AsyncRequestContext)
        mock_manager = Mock()
        mock_context.get_service = AsyncMock(return_value=mock_manager)

        # Call tool
        result = await manage_data_sources(
            action="add_primary", source=str(test_dir), context=mock_context
        )

        # Verify result
        assert result["success"] is True
        assert "Primary data source would be set" in result["message"]
        assert result["repository"]["name"] == "primary-override"
        assert result["repository"]["type"] == "primary"
        assert result["repository"]["source"] == str(test_dir.resolve())

        # Check performance target
        assert result["performance"]["target_met"] is True
        assert result["performance"]["duration_ms"] < 500.0

    @pytest.mark.asyncio
    async def test_add_primary_action_invalid_path(self):
        """Test adding primary with invalid path."""
        # Mock context
        mock_context = AsyncMock(spec=AsyncRequestContext)
        mock_manager = Mock()
        mock_context.get_service = AsyncMock(return_value=mock_manager)

        # Call tool with invalid path
        result = await manage_data_sources(
            action="add_primary", source="/nonexistent/path", context=mock_context
        )

        # Verify error
        assert "error" in result
        assert "does not exist" in result["error"]

    @pytest.mark.asyncio
    async def test_add_homebrew_action(self, tmp_path):
        """Test adding homebrew repository via MCP."""
        # Create test directory
        homebrew_dir = tmp_path / "my-homebrew"
        homebrew_dir.mkdir()

        # Mock context and manager
        mock_context = AsyncMock(spec=AsyncRequestContext)
        mock_manager = Mock()
        mock_context.get_service = AsyncMock(return_value=mock_manager)

        # Call tool
        result = await manage_data_sources(
            action="add_homebrew",
            source=str(homebrew_dir),
            name="custom-spells",
            description="My custom spell collection",
            context=mock_context,
        )

        # Verify result
        assert result["success"] is True
        assert "Homebrew repository would be added" in result["message"]
        assert result["repository"]["name"] == "custom-spells"
        assert result["repository"]["type"] == "extension"

    @pytest.mark.asyncio
    async def test_add_url_action(self):
        """Test adding URL repository via MCP."""
        # Mock context
        mock_context = AsyncMock(spec=AsyncRequestContext)
        mock_manager = Mock()
        mock_context.get_service = AsyncMock(return_value=mock_manager)

        # Call tool
        result = await manage_data_sources(
            action="add_url",
            source="https://example.com/homebrew.json",
            name="web-homebrew",
            context=mock_context,
        )

        # Verify result
        assert result["success"] is True
        assert "URL repository would be added" in result["message"]
        assert result["repository"]["name"] == "web-homebrew"
        assert result["repository"]["source"] == "https://example.com/homebrew.json"

    @pytest.mark.asyncio
    async def test_add_url_invalid_url(self):
        """Test adding URL with invalid scheme."""
        # Mock context
        mock_context = AsyncMock(spec=AsyncRequestContext)
        mock_manager = Mock()
        mock_context.get_service = AsyncMock(return_value=mock_manager)

        # Call tool with invalid URL
        result = await manage_data_sources(
            action="add_url", source="ftp://invalid.com/file.json", context=mock_context
        )

        # Verify error
        assert "error" in result
        assert "Invalid URL scheme" in result["error"]

    @pytest.mark.asyncio
    async def test_remove_action(self):
        """Test removing repository via MCP."""
        # Mock context
        mock_context = AsyncMock(spec=AsyncRequestContext)
        mock_manager = Mock()
        mock_context.get_service = AsyncMock(return_value=mock_manager)

        # Call tool
        result = await manage_data_sources(
            action="remove", name="old-homebrew", context=mock_context
        )

        # Verify result
        assert result["success"] is True
        assert "Repository would be removed" in result["message"]

    @pytest.mark.asyncio
    async def test_missing_context(self):
        """Test behavior when context is missing."""
        result = await manage_data_sources(action="list", context=None)

        assert "error" in result
        assert "AsyncRequestContext required" in result["error"]

    @pytest.mark.asyncio
    async def test_unknown_action(self):
        """Test behavior with unknown action."""
        mock_context = AsyncMock(spec=AsyncRequestContext)
        mock_manager = Mock()
        mock_context.get_service = AsyncMock(return_value=mock_manager)

        result = await manage_data_sources(
            action="invalid_action", context=mock_context
        )

        assert "error" in result
        assert "Unknown action" in result["error"]

    @pytest.mark.asyncio
    async def test_service_exception(self):
        """Test handling of service exceptions."""
        mock_context = AsyncMock(spec=AsyncRequestContext)
        mock_context.get_service = AsyncMock(
            side_effect=Exception("Service unavailable")
        )

        result = await manage_data_sources(action="list", context=mock_context)

        assert "error" in result
        assert "Failed to manage data sources" in result["error"]
        assert "Service unavailable" in result["error"]


class TestSourceAttributionMCPTool:
    """Test the manage_source_attribution MCP tool."""

    def setup_method(self):
        """Set up test environment."""
        from studiorum.core.services.container import ServiceContainer

        ServiceContainer.reset_global_instance()

    @pytest.mark.asyncio
    async def test_list_sources(self):
        """Test listing source attributions via MCP."""
        # Mock context and attribution manager
        mock_context = AsyncMock(spec=AsyncRequestContext)
        mock_attribution = Mock()
        mock_context.get_service = AsyncMock(return_value=mock_attribution)

        # Mock source data
        mock_attribution.get_all_sources.return_value = ["PHB", "MM", "DMG", "HOMEBREW"]

        def mock_resolve_source(abbrev):
            sources = {
                "PHB": {"name": "Player's Handbook", "official": True},
                "MM": {"name": "Monster Manual", "official": True},
                "DMG": {"name": "Dungeon Master's Guide", "official": True},
                "HOMEBREW": {"name": "Homebrew Content", "official": False},
            }
            return sources.get(abbrev)

        def mock_get_priority(abbrev):
            priorities = {"PHB": 10, "MM": 20, "DMG": 30, "HOMEBREW": 500}
            return priorities.get(abbrev, 999)

        mock_attribution.resolve_source.side_effect = mock_resolve_source
        mock_attribution.get_source_priority.side_effect = mock_get_priority

        # Call tool
        result = await manage_source_attribution(action="list", context=mock_context)

        # Verify result
        assert "sources" in result
        assert len(result["sources"]) == 4
        assert result["total_sources"] == 4

        # Check sorting by priority (lower number = higher priority)
        sources = result["sources"]
        assert sources[0]["abbreviation"] == "PHB"
        assert sources[0]["priority"] == 10
        assert sources[0]["official"] is True
        assert sources[-1]["abbreviation"] == "HOMEBREW"
        assert sources[-1]["priority"] == 500
        assert sources[-1]["official"] is False

        # Check performance target
        assert result["performance"]["target_met"] is True
        assert result["performance"]["duration_ms"] < 100.0

    @pytest.mark.asyncio
    async def test_resolve_known_source(self):
        """Test resolving a known source abbreviation."""
        mock_context = AsyncMock(spec=AsyncRequestContext)
        mock_attribution = Mock()
        mock_context.get_service = AsyncMock(return_value=mock_attribution)

        # Mock source resolution
        mock_attribution.resolve_source.return_value = {
            "name": "Player's Handbook",
            "official": True,
            "publisher": "WotC",
            "year": 2014,
        }
        mock_attribution.get_source_priority.return_value = 10

        # Call tool
        result = await manage_source_attribution(
            action="resolve", abbreviation="PHB", context=mock_context
        )

        # Verify result
        assert result["abbreviation"] == "PHB"
        assert result["name"] == "Player's Handbook"
        assert result["priority"] == 10
        assert result["official"] is True
        assert result["found"] is True
        assert "metadata" in result
        assert result["metadata"]["publisher"] == "WotC"

    @pytest.mark.asyncio
    async def test_resolve_unknown_source(self):
        """Test resolving an unknown source abbreviation."""
        mock_context = AsyncMock(spec=AsyncRequestContext)
        mock_attribution = Mock()
        mock_context.get_service = AsyncMock(return_value=mock_attribution)

        # Mock source resolution for unknown source
        mock_attribution.resolve_source.return_value = None
        mock_attribution.get_source_priority.return_value = 999  # Default priority

        # Call tool
        result = await manage_source_attribution(
            action="resolve", abbreviation="UNKNOWN", context=mock_context
        )

        # Verify result
        assert result["abbreviation"] == "UNKNOWN"
        assert result["name"] == "Unknown source: UNKNOWN"
        assert result["priority"] == 999
        assert result["official"] is False
        assert result["found"] is False

    @pytest.mark.asyncio
    async def test_set_priority_action(self):
        """Test setting source priority via MCP."""
        mock_context = AsyncMock(spec=AsyncRequestContext)
        mock_attribution = Mock()
        mock_context.get_service = AsyncMock(return_value=mock_attribution)

        # Call tool
        result = await manage_source_attribution(
            action="set_priority",
            abbreviation="HOMEBREW",
            priority=500,
            context=mock_context,
        )

        # Verify result (note: actual implementation would require protocol extension)
        assert result["success"] is True
        assert result["abbreviation"] == "HOMEBREW"
        assert result["priority"] == 500
        assert "Priority for HOMEBREW would be set" in result["message"]
        assert "extending ContentAttributionProtocol" in result["note"]

    @pytest.mark.asyncio
    async def test_set_priority_negative(self):
        """Test setting negative priority (should fail)."""
        mock_context = AsyncMock(spec=AsyncRequestContext)
        mock_attribution = Mock()
        mock_context.get_service = AsyncMock(return_value=mock_attribution)

        # Call tool with negative priority
        result = await manage_source_attribution(
            action="set_priority",
            abbreviation="TEST",
            priority=-1,
            context=mock_context,
        )

        # Verify error
        assert "error" in result
        assert "Priority must be non-negative" in result["error"]

    @pytest.mark.asyncio
    async def test_info_action(self):
        """Test getting attribution system info."""
        mock_context = AsyncMock(spec=AsyncRequestContext)
        mock_attribution = Mock()
        mock_context.get_service = AsyncMock(return_value=mock_attribution)

        # Mock sources with mix of official and unofficial
        mock_attribution.get_all_sources.return_value = [
            "PHB",
            "MM",
            "HOMEBREW1",
            "HOMEBREW2",
        ]

        def mock_resolve_source(abbrev):
            if abbrev in ["PHB", "MM"]:
                return {"name": f"Official {abbrev}", "official": True}
            else:
                return {"name": f"Homebrew {abbrev}", "official": False}

        mock_attribution.resolve_source.side_effect = mock_resolve_source

        # Call tool
        result = await manage_source_attribution(action="info", context=mock_context)

        # Verify result
        assert result["total_sources"] == 4
        assert result["official_sources"] == 2
        assert result["unofficial_sources"] == 2
        assert "Content source attribution manages" in result["description"]
        assert "separate from data repository management" in result["note"]

    @pytest.mark.asyncio
    async def test_missing_parameters(self):
        """Test behavior with missing required parameters."""
        mock_context = AsyncMock(spec=AsyncRequestContext)
        mock_attribution = Mock()
        mock_context.get_service = AsyncMock(return_value=mock_attribution)

        # Test resolve without abbreviation
        result = await manage_source_attribution(action="resolve", context=mock_context)

        assert "error" in result
        assert "abbreviation required" in result["error"]

        # Test set_priority without abbreviation
        result = await manage_source_attribution(
            action="set_priority", priority=100, context=mock_context
        )

        assert "error" in result
        assert "abbreviation required" in result["error"]

        # Test set_priority without priority
        result = await manage_source_attribution(
            action="set_priority", abbreviation="TEST", context=mock_context
        )

        assert "error" in result
        assert "Priority value required" in result["error"]

    @pytest.mark.asyncio
    async def test_missing_context(self):
        """Test behavior when context is missing."""
        result = await manage_source_attribution(action="list", context=None)

        assert "error" in result
        assert "AsyncRequestContext required" in result["error"]

    @pytest.mark.asyncio
    async def test_service_exception(self):
        """Test handling of service exceptions."""
        mock_context = AsyncMock(spec=AsyncRequestContext)
        mock_context.get_service = AsyncMock(
            side_effect=Exception("Attribution service failed")
        )

        result = await manage_source_attribution(action="list", context=mock_context)

        assert "error" in result
        assert "Failed to manage source attribution" in result["error"]
        assert "Attribution service failed" in result["error"]

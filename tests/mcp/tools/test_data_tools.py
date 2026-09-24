"""Tests for MCP data management tools.

This module tests the new MCP tools for data repository management
from Package 3 implementation.
"""

from unittest.mock import AsyncMock, Mock, PropertyMock

import pytest

from studiorum.core.loaders.data_dir import DataDir, DataSet
from studiorum.mcp.context import AsyncRequestContext
from studiorum.mcp.tools.attribution import manage_source_attribution
from studiorum.mcp.tools.data import manage_data_sources


class TestDataSourcesMCPTool:
    """manage_data_sources reports the configured data; it changes nothing."""

    @pytest.mark.asyncio
    async def test_list_reports_dirs_homebrew_and_problems(self, tmp_path):
        brew = tmp_path / "brew.json"
        brew.write_text('{"monster": [{"name": "X", "source": "Y"}]}')
        data = DataSet((DataDir(tmp_path / "gone"),), (brew,))
        context = AsyncMock(spec=AsyncRequestContext)
        context.services.data = data

        result = await manage_data_sources(action="list", context=context)

        assert result["data_dirs"] == [
            {"path": str(tmp_path / "gone"), "exists": False}
        ]
        assert result["homebrew"] == [{"path": str(brew), "exists": True}]
        assert result["files"] == 1
        assert result["problems"] == [f"Data directory not found: {tmp_path / 'gone'}"]

    @pytest.mark.asyncio
    async def test_missing_context(self):
        result = await manage_data_sources(action="list", context=None)

        assert "error" in result


class TestSourceAttributionMCPTool:
    """Test the manage_source_attribution MCP tool."""

    @pytest.mark.asyncio
    async def test_list_sources(self):
        """Test listing source attributions via MCP."""
        # Mock context and attribution manager
        mock_context = AsyncMock(spec=AsyncRequestContext)
        mock_attribution = Mock()
        mock_context.services.content_attribution = mock_attribution

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
        mock_context.services.content_attribution = mock_attribution

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
        mock_context.services.content_attribution = mock_attribution

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
        mock_context.services.content_attribution = mock_attribution

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
        mock_context.services.content_attribution = mock_attribution

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
        mock_context.services.content_attribution = mock_attribution

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
        mock_context.services.content_attribution = mock_attribution

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
        type(mock_context).services = PropertyMock(
            side_effect=Exception("Attribution service failed")
        )

        result = await manage_source_attribution(action="list", context=mock_context)

        assert "error" in result
        assert "Failed to manage source attribution" in result["error"]
        assert "Attribution service failed" in result["error"]

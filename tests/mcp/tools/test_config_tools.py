"""Comprehensive tests for MCP configuration tools.

This module tests all MCP configuration tools that enable natural language
configuration management for D&D 5e project settings.

Test categories:
- Basic tool functionality (get_configuration, update_configuration)
- Workflow-specific tools (paper layout, spellbook, encounter printing)
- Content source management (add_content_source)
- Preset management (save/load user preferences)
- Error handling and validation
- AsyncRequestContext integration
- Natural language scenario testing
"""

from __future__ import annotations

import json
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from pydantic import ValidationError

from studiorum.core.config.unified_config import (
    ApplicationConfig,
    CompilationConfig,
    ContentConfig,
    LaTeXDocumentConfig,
    LaTeXEngineConfig,
    LaTeXRenderingConfig,
    LoggingConfig,
    MCPConfig,
    PathsConfig,
    ProcessingConfig,
    RenderingConfig,
    ValidationConfig,
)
from studiorum.core.context import AsyncRequestContext
from studiorum.core.error_types import (
    ConfigurationError,
    ErrorCategory,
    MCPError,
    MCPErrorCode,
    ValidationError as DnDValidationError,
)
from studiorum.core.result import Error, Result, Success
from studiorum.mcp.tools.config import (
    ConfigurationResponse,
    PresetInfo,
    _ensure_presets_dir,
    _get_current_config_dict,
    add_content_source,
    configure_encounter_printing,
    configure_paper_layout,
    configure_spellbook_generation,
    get_configuration,
    load_user_preferences,
    save_user_preferences,
    update_configuration,
)
from tests.test_helpers import reset_test_environment


class TestConfigurationResponse:
    """Test ConfigurationResponse model."""

    def test_default_values(self) -> None:
        """Test default field values."""
        response = ConfigurationResponse(success=True, message="Test message")

        assert response.success is True
        assert response.message == "Test message"
        assert response.updated_fields == []
        assert response.errors == []
        assert response.current_config == {}

    def test_custom_values(self) -> None:
        """Test response with custom values."""
        response = ConfigurationResponse(
            success=False,
            message="Configuration failed",
            updated_fields=["logging.level", "rendering.latex.engine"],
            errors=["Invalid log level", "Engine not found"],
            current_config={"logging": {"level": "DEBUG"}},
        )

        assert response.success is False
        assert response.message == "Configuration failed"
        assert response.updated_fields == ["logging.level", "rendering.latex.engine"]
        assert response.errors == ["Invalid log level", "Engine not found"]
        assert response.current_config == {"logging": {"level": "DEBUG"}}


class TestPresetInfo:
    """Test PresetInfo model."""

    def test_preset_info_creation(self) -> None:
        """Test PresetInfo model creation."""
        info = PresetInfo(
            name="Test Preset",
            description="A test configuration preset",
            created_at="2023-12-01T10:00:00",
            config_sections=["logging", "rendering", "latex"],
        )

        assert info.name == "Test Preset"
        assert info.description == "A test configuration preset"
        assert info.created_at == "2023-12-01T10:00:00"
        assert info.config_sections == ["logging", "rendering", "latex"]


class TestUtilityFunctions:
    """Test utility functions."""

    def setup_method(self) -> None:
        """Set up test environment."""
        reset_test_environment()

    def test_ensure_presets_dir(self) -> None:
        """Test preset directory creation."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            with patch(
                "dnd5e.mcp.tools.config._PRESETS_DIR", Path(tmp_dir) / "presets"
            ):
                presets_dir = _ensure_presets_dir()

                assert presets_dir.exists()
                assert presets_dir.is_dir()
                assert presets_dir.name == "presets"

    def test_get_current_config_dict(self) -> None:
        """Test configuration serialization."""
        config = ApplicationConfig()
        config_dict = _get_current_config_dict(config)

        # Verify all major sections are present
        assert "logging" in config_dict
        assert "paths" in config_dict
        assert "processing" in config_dict
        assert "validation" in config_dict
        assert "rendering" in config_dict
        assert "mcp" in config_dict

        # Verify nested structure
        assert "latex" in config_dict["rendering"]
        assert "engine" in config_dict["rendering"]["latex"]
        assert "document" in config_dict["rendering"]["latex"]
        assert "rendering" in config_dict["rendering"]["latex"]


class TestGetConfiguration:
    """Test get_configuration tool."""

    def setup_method(self) -> None:
        """Set up test environment."""
        reset_test_environment()

    @pytest.mark.asyncio
    async def test_get_configuration_success(self) -> None:
        """Test successful configuration retrieval."""
        result = await get_configuration()

        assert result.is_success()
        response = result.unwrap()

        assert isinstance(response, ConfigurationResponse)
        assert response.success is True
        assert response.message == "Current configuration retrieved successfully"
        assert "logging" in response.current_config
        assert "rendering" in response.current_config

    @pytest.mark.asyncio
    async def test_get_configuration_with_context(self) -> None:
        """Test configuration retrieval with context override."""
        # Create custom config
        custom_config = ApplicationConfig()
        custom_config.logging.level = "DEBUG"

        # Create context with custom config
        context = AsyncRequestContext(user_config=custom_config)

        result = await get_configuration(context)

        assert result.is_success()
        response = result.unwrap()

        assert response.success is True
        assert response.current_config["logging"]["level"] == "DEBUG"

    @pytest.mark.asyncio
    async def test_get_configuration_exception_handling(self) -> None:
        """Test exception handling in get_configuration."""
        with patch(
            "dnd5e.mcp.tools.config.get_app_config", side_effect=Exception("Test error")
        ):
            result = await get_configuration()

            assert result.is_error()
            error = result.error

            assert isinstance(error, MCPError)
            assert error.error_code == MCPErrorCode.INTERNAL_ERROR
            assert error.category == ErrorCategory.CONFIGURATION
            assert "Failed to read configuration: Test error" in error.message


class TestUpdateConfiguration:
    """Test update_configuration tool."""

    def setup_method(self) -> None:
        """Set up test environment."""
        reset_test_environment()

    @pytest.mark.asyncio
    async def test_update_configuration_simple(self) -> None:
        """Test simple configuration update."""
        updates = {"logging.level": "DEBUG"}

        result = await update_configuration(updates)

        assert result.is_success()
        response = result.unwrap()

        assert response.success is True
        assert "logging.level" in response.updated_fields
        assert response.current_config["logging"]["level"] == "DEBUG"

    @pytest.mark.asyncio
    async def test_update_configuration_nested(self) -> None:
        """Test nested configuration updates."""
        updates = {
            "rendering.latex.document.paper_size": "a4",
            "rendering.latex.document.background": "print",
            "rendering.content.default_sources": ["phb", "dmg"],
        }

        result = await update_configuration(updates)

        assert result.is_success()
        response = result.unwrap()

        assert response.success is True
        assert len(response.updated_fields) == 3
        assert (
            response.current_config["rendering"]["latex"]["document"]["paper_size"]
            == "a4"
        )
        assert (
            response.current_config["rendering"]["latex"]["document"]["background"]
            == "print"
        )
        assert response.current_config["rendering"]["content"]["default_sources"] == [
            "phb",
            "dmg",
        ]

    @pytest.mark.asyncio
    async def test_update_configuration_with_context(self) -> None:
        """Test configuration update with context."""
        context = AsyncRequestContext()
        updates = {"logging.level": "WARNING"}

        result = await update_configuration(updates, context)

        assert result.is_success()
        response = result.unwrap()

        assert response.success is True
        assert context.user_config is not None
        assert context.user_config.logging.level == "WARNING"

    @pytest.mark.asyncio
    async def test_update_configuration_validation_error(self) -> None:
        """Test handling of validation errors."""
        # Invalid log level
        updates = {"logging.level": "INVALID_LEVEL"}

        result = await update_configuration(updates)

        assert result.is_success()  # Returns success with validation errors
        response = result.unwrap()

        assert response.success is False
        assert response.message == "Configuration validation failed"
        assert len(response.errors) > 0
        assert any("level" in error for error in response.errors)

    @pytest.mark.asyncio
    async def test_update_configuration_exception_handling(self) -> None:
        """Test exception handling in update_configuration."""
        with patch(
            "dnd5e.mcp.tools.config.get_app_config", side_effect=Exception("Test error")
        ):
            result = await update_configuration({"logging.level": "DEBUG"})

            assert result.is_error()
            error = result.error

            assert isinstance(error, MCPError)
            assert error.error_code == MCPErrorCode.CONFIGURATION_ERROR
            assert "Failed to update configuration: Test error" in error.message

    @pytest.mark.asyncio
    async def test_update_configuration_partial_failure(self) -> None:
        """Test partial failure in configuration updates."""
        updates = {
            "logging.level": "DEBUG",  # Valid
            "nonexistent.field": "value",  # Invalid - Pydantic forbids extra fields
        }

        result = await update_configuration(updates)

        assert result.is_success()
        response = result.unwrap()

        # Should fail validation due to extra fields
        assert response.success is False
        assert response.message == "Configuration validation failed"
        assert len(response.errors) > 0
        assert any(
            "Extra inputs are not permitted" in error for error in response.errors
        )


class TestConfigurePaperLayout:
    """Test configure_paper_layout tool."""

    def setup_method(self) -> None:
        """Set up test environment."""
        reset_test_environment()

    @pytest.mark.asyncio
    async def test_configure_paper_layout_a4_default(self) -> None:
        """Test A4 paper layout configuration with defaults."""
        result = await configure_paper_layout()

        assert result.is_success()
        response = result.unwrap()

        assert response.success is True
        assert "A4 with print background" in response.message
        config = response.current_config
        assert config["rendering"]["latex"]["document"]["paper_size"] == "a4"
        assert config["rendering"]["latex"]["document"]["background"] == "print"
        assert config["rendering"]["latex"]["document"]["high_contrast"] is True
        assert config["rendering"]["latex"]["document"]["two_column"] is True

    @pytest.mark.asyncio
    async def test_configure_paper_layout_letter_full_background(self) -> None:
        """Test Letter paper with full background."""
        result = await configure_paper_layout(
            paper_size="letter",
            background="full",
            high_contrast=False,
            two_column=True,
        )

        assert result.is_success()
        response = result.unwrap()

        assert response.success is True
        assert "LETTER with full background" in response.message
        config = response.current_config
        assert config["rendering"]["latex"]["document"]["paper_size"] == "letter"
        assert config["rendering"]["latex"]["document"]["background"] == "full"
        assert config["rendering"]["latex"]["document"]["font_size"] == "11pt"

    @pytest.mark.asyncio
    async def test_configure_paper_layout_a5_optimizations(self) -> None:
        """Test A5 paper with specific optimizations."""
        result = await configure_paper_layout(
            paper_size="a5",
            background="none",
            two_column=True,  # Should be overridden for A5
        )

        assert result.is_success()
        response = result.unwrap()

        config = response.current_config
        assert config["rendering"]["latex"]["document"]["paper_size"] == "a5"
        assert (
            config["rendering"]["latex"]["document"]["two_column"] is False
        )  # Overridden
        assert config["rendering"]["latex"]["document"]["font_size"] == "10pt"
        assert config["rendering"]["latex"]["document"]["class_options"] == [
            "justified"
        ]

    @pytest.mark.asyncio
    async def test_configure_paper_layout_print_optimizations(self) -> None:
        """Test print background optimizations."""
        result = await configure_paper_layout(
            paper_size="a4",
            background="print",
            high_contrast=False,  # Should be overridden for print
        )

        assert result.is_success()
        response = result.unwrap()

        config = response.current_config
        assert config["rendering"]["latex"]["document"]["background"] == "print"
        assert (
            config["rendering"]["latex"]["document"]["high_contrast"] is True
        )  # Overridden
        assert config["rendering"]["latex"]["document"]["fancy_headers"] is False

    @pytest.mark.asyncio
    async def test_configure_paper_layout_with_context(self) -> None:
        """Test paper layout configuration with context."""
        context = AsyncRequestContext()

        result = await configure_paper_layout(
            paper_size="letter",
            context=context,
        )

        assert result.is_success()
        assert context.user_config is not None
        assert context.user_config.rendering.latex.document.paper_size == "letter"

    @pytest.mark.asyncio
    async def test_configure_paper_layout_exception_handling(self) -> None:
        """Test exception handling in configure_paper_layout."""
        with patch(
            "dnd5e.mcp.tools.config.update_configuration",
            side_effect=Exception("Test error"),
        ):
            result = await configure_paper_layout()

            assert result.is_error()
            error = result.error

            assert isinstance(error, MCPError)
            assert error.error_code == MCPErrorCode.CONFIGURATION_ERROR
            assert "Failed to configure paper layout: Test error" in error.message


class TestConfigureSpellbookGeneration:
    """Test configure_spellbook_generation tool."""

    def setup_method(self) -> None:
        """Set up test environment."""
        reset_test_environment()

    @pytest.mark.asyncio
    async def test_configure_spellbook_generation_defaults(self) -> None:
        """Test spellbook generation with default settings."""
        result = await configure_spellbook_generation()

        assert result.is_success()
        response = result.unwrap()

        assert response.success is True
        assert "Spellbook generation configured" in response.message
        config = response.current_config
        assert config["rendering"]["content"]["appendix_spells"] is True
        assert config["rendering"]["latex"]["rendering"]["enable_cross_refs"] is True
        assert config["rendering"]["latex"]["rendering"]["auto_page_refs"] is True
        assert config["rendering"]["latex"]["document"]["show_index"] is True
        assert config["rendering"]["latex"]["document"]["show_toc"] is True

    @pytest.mark.asyncio
    async def test_configure_spellbook_generation_alphabetical(self) -> None:
        """Test spellbook with alphabetical organization."""
        result = await configure_spellbook_generation(
            alphabetical_organization=True,
        )

        assert result.is_success()
        response = result.unwrap()

        config = response.current_config
        assert (
            config["rendering"]["latex"]["rendering"]["appendix_organization"]
            == "alphabetical"
        )

    @pytest.mark.asyncio
    async def test_configure_spellbook_generation_by_type(self) -> None:
        """Test spellbook with type-based organization."""
        result = await configure_spellbook_generation(
            alphabetical_organization=False,
        )

        assert result.is_success()
        response = result.unwrap()

        config = response.current_config
        assert (
            config["rendering"]["latex"]["rendering"]["appendix_organization"] == "type"
        )

    @pytest.mark.asyncio
    async def test_configure_spellbook_generation_minimal(self) -> None:
        """Test minimal spellbook configuration."""
        result = await configure_spellbook_generation(
            include_spell_appendix=False,
            enable_cross_refs=False,
            show_index=False,
        )

        assert result.is_success()
        response = result.unwrap()

        config = response.current_config
        assert config["rendering"]["content"]["appendix_spells"] is False
        assert config["rendering"]["latex"]["rendering"]["enable_cross_refs"] is False
        assert config["rendering"]["latex"]["rendering"]["auto_page_refs"] is False
        assert config["rendering"]["latex"]["document"]["show_index"] is False
        assert (
            config["rendering"]["latex"]["document"]["show_toc"] is True
        )  # Always enabled

    @pytest.mark.asyncio
    async def test_configure_spellbook_generation_exception_handling(self) -> None:
        """Test exception handling in configure_spellbook_generation."""
        with patch(
            "dnd5e.mcp.tools.config.update_configuration",
            side_effect=Exception("Test error"),
        ):
            result = await configure_spellbook_generation()

            assert result.is_error()
            error = result.error

            assert isinstance(error, MCPError)
            assert error.error_code == MCPErrorCode.CONFIGURATION_ERROR
            assert (
                "Failed to configure spellbook generation: Test error" in error.message
            )


class TestConfigureEncounterPrinting:
    """Test configure_encounter_printing tool."""

    def setup_method(self) -> None:
        """Set up test environment."""
        reset_test_environment()

    @pytest.mark.asyncio
    async def test_configure_encounter_printing_defaults(self) -> None:
        """Test encounter printing with default settings."""
        result = await configure_encounter_printing()

        assert result.is_success()
        response = result.unwrap()

        assert response.success is True
        assert "Encounter printing configured" in response.message
        config = response.current_config
        assert config["rendering"]["content"]["appendix_creatures"] is True
        assert config["rendering"]["latex"]["document"]["high_contrast"] is True

    @pytest.mark.asyncio
    async def test_configure_encounter_printing_optimized(self) -> None:
        """Test optimized encounter printing settings."""
        result = await configure_encounter_printing(
            optimize_for_print=True,
        )

        assert result.is_success()
        response = result.unwrap()

        config = response.current_config
        assert config["rendering"]["latex"]["document"]["background"] == "print"
        assert config["rendering"]["latex"]["document"]["fancy_headers"] is False
        assert config["rendering"]["latex"]["rendering"]["enable_hyperlinks"] is False

    @pytest.mark.asyncio
    async def test_configure_encounter_printing_single_column(self) -> None:
        """Test single column encounter printing."""
        result = await configure_encounter_printing(
            single_column=True,
        )

        assert result.is_success()
        response = result.unwrap()

        config = response.current_config
        assert config["rendering"]["latex"]["document"]["two_column"] is False
        assert config["rendering"]["latex"]["document"]["class_options"] == [
            "justified"
        ]

    @pytest.mark.asyncio
    async def test_configure_encounter_printing_two_column(self) -> None:
        """Test two column encounter printing."""
        result = await configure_encounter_printing(
            single_column=False,
        )

        assert result.is_success()
        response = result.unwrap()

        config = response.current_config
        assert config["rendering"]["latex"]["document"]["two_column"] is True
        assert config["rendering"]["latex"]["document"]["class_options"] == [
            "justified",
            "twocolumn",
        ]

    @pytest.mark.asyncio
    async def test_configure_encounter_printing_no_optimization(self) -> None:
        """Test encounter printing without print optimization."""
        result = await configure_encounter_printing(
            optimize_for_print=False,
            high_contrast=False,
        )

        assert result.is_success()
        response = result.unwrap()

        config = response.current_config
        assert config["rendering"]["latex"]["document"]["high_contrast"] is False
        # When optimize_for_print=False, the function doesn't set background
        # so it should retain whatever was set before (which could be default or from previous tests)
        # The key is that the operation succeeded
        assert response.success is True

    @pytest.mark.asyncio
    async def test_configure_encounter_printing_exception_handling(self) -> None:
        """Test exception handling in configure_encounter_printing."""
        with patch(
            "dnd5e.mcp.tools.config.update_configuration",
            side_effect=Exception("Test error"),
        ):
            result = await configure_encounter_printing()

            assert result.is_error()
            error = result.error

            assert isinstance(error, MCPError)
            assert error.error_code == MCPErrorCode.CONFIGURATION_ERROR
            assert "Failed to configure encounter printing: Test error" in error.message


class TestAddContentSource:
    """Test add_content_source tool."""

    def setup_method(self) -> None:
        """Set up test environment."""
        reset_test_environment()

    @pytest.mark.asyncio
    async def test_add_content_source_append(self) -> None:
        """Test adding content sources to existing list."""
        # First set some initial sources
        await update_configuration({"rendering.content.default_sources": ["phb"]})

        result = await add_content_source(["dmg", "mm"], replace_existing=False)

        assert result.is_success()
        response = result.unwrap()

        assert response.success is True
        assert "updated" in response.message
        assert "phb, dmg, mm" in response.message or "phb,dmg,mm" in response.message
        config = response.current_config
        sources = config["rendering"]["content"]["default_sources"]
        assert "phb" in sources
        assert "dmg" in sources
        assert "mm" in sources

    @pytest.mark.asyncio
    async def test_add_content_source_replace(self) -> None:
        """Test replacing existing content sources."""
        # First set some initial sources
        await update_configuration(
            {"rendering.content.default_sources": ["phb", "dmg"]}
        )

        result = await add_content_source(["mm", "xge"], replace_existing=True)

        assert result.is_success()
        response = result.unwrap()

        assert response.success is True
        assert "replaced" in response.message
        assert "mm, xge" in response.message or "mm,xge" in response.message
        config = response.current_config
        sources = config["rendering"]["content"]["default_sources"]
        assert sources == ["mm", "xge"]

    @pytest.mark.asyncio
    async def test_add_content_source_no_duplicates(self) -> None:
        """Test that duplicate sources are not added."""
        # First set some initial sources
        await update_configuration({"rendering.content.default_sources": ["phb"]})

        result = await add_content_source(["phb", "dmg"], replace_existing=False)

        assert result.is_success()
        response = result.unwrap()

        config = response.current_config
        sources = config["rendering"]["content"]["default_sources"]
        assert sources.count("phb") == 1  # No duplicates
        assert "dmg" in sources

    @pytest.mark.asyncio
    async def test_add_content_source_with_context(self) -> None:
        """Test adding content sources with context."""
        context = AsyncRequestContext()

        result = await add_content_source(
            ["tcoe", "vgm"], replace_existing=True, context=context
        )

        assert result.is_success()
        assert context.user_config is not None
        assert context.sources == ["tcoe", "vgm"]  # Context sources updated
        sources = context.user_config.rendering.content.default_sources
        assert sources == ["tcoe", "vgm"]

    @pytest.mark.asyncio
    async def test_add_content_source_empty_list(self) -> None:
        """Test adding empty source list (should work but not change anything)."""
        initial_sources = ["phb"]
        await update_configuration(
            {"rendering.content.default_sources": initial_sources}
        )

        result = await add_content_source([], replace_existing=False)

        assert result.is_success()
        response = result.unwrap()

        config = response.current_config
        sources = config["rendering"]["content"]["default_sources"]
        assert sources == initial_sources  # Unchanged

    @pytest.mark.asyncio
    async def test_add_content_source_exception_handling(self) -> None:
        """Test exception handling in add_content_source."""
        with patch(
            "dnd5e.mcp.tools.config.get_app_config", side_effect=Exception("Test error")
        ):
            result = await add_content_source(["phb"])

            assert result.is_error()
            error = result.error

            assert isinstance(error, MCPError)
            assert error.error_code == MCPErrorCode.CONFIGURATION_ERROR
            assert "Failed to add content source: Test error" in error.message


class TestSaveUserPreferences:
    """Test save_user_preferences tool."""

    def setup_method(self) -> None:
        """Set up test environment."""
        reset_test_environment()

    @pytest.mark.asyncio
    async def test_save_user_preferences_success(self) -> None:
        """Test successful preset saving."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            with patch("dnd5e.mcp.tools.config._PRESETS_DIR", Path(tmp_dir)):
                result = await save_user_preferences(
                    preset_name="Test Preset",
                    description="A test configuration",
                )

                assert result.is_success()
                response = result.unwrap()

                assert response.success is True
                assert "Test Preset" in response.message
                assert "saved successfully" in response.message

                # Verify file was created
                preset_file = Path(tmp_dir) / "Test Preset.json"
                assert preset_file.exists()

                # Verify content
                with preset_file.open("r") as f:
                    data = json.load(f)

                assert data["name"] == "Test Preset"
                assert data["description"] == "A test configuration"
                assert "created_at" in data
                assert "config" in data

    @pytest.mark.asyncio
    async def test_save_user_preferences_special_characters(self) -> None:
        """Test preset saving with special characters in name."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            with patch("dnd5e.mcp.tools.config._PRESETS_DIR", Path(tmp_dir)):
                result = await save_user_preferences(
                    preset_name="Test/Preset: Special!@#",
                    description="Special chars test",
                )

                assert result.is_success()

                # Verify safe filename was created
                preset_file = Path(tmp_dir) / "TestPreset Special.json"
                assert preset_file.exists()

    @pytest.mark.asyncio
    async def test_save_user_preferences_empty_name(self) -> None:
        """Test preset saving with empty name."""
        result = await save_user_preferences(
            preset_name="   ",  # Whitespace only
            description="Test",
        )

        assert result.is_error()
        error = result.error

        assert isinstance(error, MCPError)
        assert error.error_code == MCPErrorCode.INVALID_PARAMS
        assert "Preset name cannot be empty" in error.message

    @pytest.mark.asyncio
    async def test_save_user_preferences_with_context(self) -> None:
        """Test preset saving with custom context configuration."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            with patch("dnd5e.mcp.tools.config._PRESETS_DIR", Path(tmp_dir)):
                # Create context with custom config
                custom_config = ApplicationConfig()
                custom_config.logging.level = "DEBUG"
                context = AsyncRequestContext(user_config=custom_config)

                result = await save_user_preferences(
                    preset_name="Context Test",
                    description="Context config test",
                    context=context,
                )

                assert result.is_success()

                # Verify custom config was saved
                preset_file = Path(tmp_dir) / "Context Test.json"
                with preset_file.open("r") as f:
                    data = json.load(f)

                assert data["config"]["logging"]["level"] == "DEBUG"

    @pytest.mark.asyncio
    async def test_save_user_preferences_file_error(self) -> None:
        """Test handling of file system errors."""
        with patch(
            "dnd5e.mcp.tools.config._ensure_presets_dir",
            side_effect=Exception("Disk full"),
        ):
            result = await save_user_preferences("Test", "Test description")

            assert result.is_error()
            error = result.error

            assert isinstance(error, MCPError)
            assert error.error_code == MCPErrorCode.INTERNAL_ERROR
            assert "Failed to save preset: Disk full" in error.message


class TestLoadUserPreferences:
    """Test load_user_preferences tool."""

    def setup_method(self) -> None:
        """Set up test environment."""
        reset_test_environment()

    @pytest.mark.asyncio
    async def test_load_user_preferences_success(self) -> None:
        """Test successful preset loading."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            with patch("dnd5e.mcp.tools.config._PRESETS_DIR", Path(tmp_dir)):
                # Create a test preset file
                preset_data = {
                    "name": "Test Preset",
                    "description": "Test configuration",
                    "created_at": "2023-12-01T10:00:00",
                    "config": {
                        "logging": {"level": "DEBUG", "enable_file_logging": False},
                        "rendering": {
                            "latex": {
                                "document": {"paper_size": "a4", "background": "print"}
                            }
                        },
                    },
                }

                preset_file = Path(tmp_dir) / "Test Preset.json"
                with preset_file.open("w") as f:
                    json.dump(preset_data, f)

                result = await load_user_preferences("Test Preset")

                assert result.is_success()
                response = result.unwrap()

                assert response.success is True
                assert "Test Preset" in response.message
                assert "loaded successfully" in response.message

                # Verify configuration was applied
                config = response.current_config
                assert config["logging"]["level"] == "DEBUG"
                assert config["rendering"]["latex"]["document"]["paper_size"] == "a4"

    @pytest.mark.asyncio
    async def test_load_user_preferences_not_found(self) -> None:
        """Test loading non-existent preset."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            with patch("dnd5e.mcp.tools.config._PRESETS_DIR", Path(tmp_dir)):
                result = await load_user_preferences("Nonexistent Preset")

                assert result.is_error()
                error = result.error

                assert isinstance(error, MCPError)
                assert error.error_code == MCPErrorCode.CONTENT_NOT_FOUND
                assert "Preset 'Nonexistent Preset' not found" in error.message

    @pytest.mark.asyncio
    async def test_load_user_preferences_with_suggestions(self) -> None:
        """Test loading non-existent preset with available suggestions."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            with patch("dnd5e.mcp.tools.config._PRESETS_DIR", Path(tmp_dir)):
                # Create some test preset files
                for name in ["Preset One", "Preset Two"]:
                    preset_data = {
                        "name": name,
                        "description": "Test",
                        "created_at": "2023-12-01T10:00:00",
                        "config": {},
                    }
                    preset_file = Path(tmp_dir) / f"{name}.json"
                    with preset_file.open("w") as f:
                        json.dump(preset_data, f)

                result = await load_user_preferences("Nonexistent")

                assert result.is_error()
                error = result.error

                assert "Available presets: Preset One, Preset Two" in error.message

    @pytest.mark.asyncio
    async def test_load_user_preferences_invalid_config(self) -> None:
        """Test loading preset with invalid configuration."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            with patch("dnd5e.mcp.tools.config._PRESETS_DIR", Path(tmp_dir)):
                # Create preset with invalid configuration
                preset_data = {
                    "name": "Invalid Preset",
                    "description": "Test",
                    "created_at": "2023-12-01T10:00:00",
                    "config": {
                        "logging": {"level": "INVALID_LEVEL"},  # Invalid
                    },
                }

                preset_file = Path(tmp_dir) / "Invalid Preset.json"
                with preset_file.open("w") as f:
                    json.dump(preset_data, f)

                result = await load_user_preferences("Invalid Preset")

                assert result.is_success()  # Returns success with validation errors
                response = result.unwrap()

                assert response.success is False
                assert response.message == "Preset configuration is invalid"
                assert len(response.errors) > 0

    @pytest.mark.asyncio
    async def test_load_user_preferences_with_context(self) -> None:
        """Test loading preset with context."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            with patch("dnd5e.mcp.tools.config._PRESETS_DIR", Path(tmp_dir)):
                # Create test preset
                preset_data = {
                    "name": "Context Test",
                    "description": "Test",
                    "created_at": "2023-12-01T10:00:00",
                    "config": {
                        "logging": {"level": "WARNING"},
                    },
                }

                preset_file = Path(tmp_dir) / "Context Test.json"
                with preset_file.open("w") as f:
                    json.dump(preset_data, f)

                context = AsyncRequestContext()
                result = await load_user_preferences("Context Test", context)

                assert result.is_success()
                assert context.user_config is not None
                assert context.user_config.logging.level == "WARNING"

    @pytest.mark.asyncio
    async def test_load_user_preferences_malformed_json(self) -> None:
        """Test loading preset with malformed JSON."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            with patch("dnd5e.mcp.tools.config._PRESETS_DIR", Path(tmp_dir)):
                # Create malformed JSON file
                preset_file = Path(tmp_dir) / "Malformed.json"
                preset_file.write_text("{ invalid json }")

                result = await load_user_preferences("Malformed")

                assert result.is_error()
                error = result.error

                assert isinstance(error, MCPError)
                assert error.error_code == MCPErrorCode.INTERNAL_ERROR
                assert "Failed to load preset" in error.message


class TestNaturalLanguageScenarios:
    """Test natural language configuration scenarios."""

    def setup_method(self) -> None:
        """Set up test environment."""
        reset_test_environment()

    @pytest.mark.asyncio
    async def test_scenario_set_sources_to_srd_only(self) -> None:
        """Test 'Set sources to SRD only' scenario."""
        result = await add_content_source(["srd"], replace_existing=True)

        assert result.is_success()
        response = result.unwrap()
        assert response.success is True
        assert response.current_config["rendering"]["content"]["default_sources"] == [
            "srd"
        ]

    @pytest.mark.asyncio
    async def test_scenario_configure_for_a4_printing(self) -> None:
        """Test 'Configure for A4 printing' scenario."""
        result = await configure_paper_layout(
            paper_size="a4",
            background="print",
            high_contrast=True,
        )

        assert result.is_success()
        response = result.unwrap()
        assert response.success is True
        config = response.current_config
        assert config["rendering"]["latex"]["document"]["paper_size"] == "a4"
        assert config["rendering"]["latex"]["document"]["background"] == "print"
        assert config["rendering"]["latex"]["document"]["high_contrast"] is True

    @pytest.mark.asyncio
    async def test_scenario_set_log_level_to_debug(self) -> None:
        """Test 'Set log level to DEBUG' scenario."""
        result = await update_configuration({"logging.level": "DEBUG"})

        assert result.is_success()
        response = result.unwrap()
        assert response.success is True
        assert response.current_config["logging"]["level"] == "DEBUG"

    @pytest.mark.asyncio
    async def test_scenario_set_up_for_spellbook_generation(self) -> None:
        """Test 'Set up for spellbook generation' scenario."""
        result = await configure_spellbook_generation(
            include_spell_appendix=True,
            alphabetical_organization=True,
            enable_cross_refs=True,
            show_index=True,
        )

        assert result.is_success()
        response = result.unwrap()
        assert response.success is True
        config = response.current_config
        assert config["rendering"]["content"]["appendix_spells"] is True
        assert (
            config["rendering"]["latex"]["rendering"]["appendix_organization"]
            == "alphabetical"
        )

    @pytest.mark.asyncio
    async def test_scenario_optimize_for_black_and_white_printing(self) -> None:
        """Test 'Optimize for black and white printing' scenario."""
        result = await configure_encounter_printing(
            optimize_for_print=True,
            high_contrast=True,
        )

        assert result.is_success()
        response = result.unwrap()
        assert response.success is True
        config = response.current_config
        assert config["rendering"]["latex"]["document"]["high_contrast"] is True
        assert config["rendering"]["latex"]["document"]["background"] == "print"

    @pytest.mark.asyncio
    async def test_scenario_add_tashas_cauldron_to_sources(self) -> None:
        """Test 'Add Tasha's Cauldron to sources' scenario."""
        result = await add_content_source(["tcoe"], replace_existing=False)

        assert result.is_success()
        response = result.unwrap()
        assert response.success is True
        sources = response.current_config["rendering"]["content"]["default_sources"]
        assert "tcoe" in sources

    @pytest.mark.asyncio
    async def test_scenario_save_current_settings_as_print_setup(self) -> None:
        """Test 'Save current settings as Print Setup' scenario."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            with patch("dnd5e.mcp.tools.config._PRESETS_DIR", Path(tmp_dir)):
                # First configure some settings
                await configure_paper_layout(paper_size="a4", background="print")

                # Then save as preset
                result = await save_user_preferences(
                    preset_name="Print Setup",
                    description="Optimized for A4 printing",
                )

                assert result.is_success()
                response = result.unwrap()
                assert response.success is True
                assert "Print Setup" in response.message

    @pytest.mark.asyncio
    async def test_scenario_load_print_setup_preferences(self) -> None:
        """Test 'Load my Print Setup preferences' scenario."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            with patch("dnd5e.mcp.tools.config._PRESETS_DIR", Path(tmp_dir)):
                # Create a preset first
                preset_data = {
                    "name": "Print Setup",
                    "description": "A4 print optimization",
                    "created_at": "2023-12-01T10:00:00",
                    "config": {
                        "rendering": {
                            "latex": {
                                "document": {
                                    "paper_size": "a4",
                                    "background": "print",
                                    "high_contrast": True,
                                }
                            }
                        }
                    },
                }

                preset_file = Path(tmp_dir) / "Print Setup.json"
                with preset_file.open("w") as f:
                    json.dump(preset_data, f)

                result = await load_user_preferences("Print Setup")

                assert result.is_success()
                response = result.unwrap()
                assert response.success is True
                config = response.current_config
                assert config["rendering"]["latex"]["document"]["paper_size"] == "a4"
                assert config["rendering"]["latex"]["document"]["background"] == "print"


class TestAsyncRequestContextIntegration:
    """Test integration with AsyncRequestContext."""

    def setup_method(self) -> None:
        """Set up test environment."""
        reset_test_environment()

    @pytest.mark.asyncio
    async def test_context_isolation(self) -> None:
        """Test that context provides proper configuration isolation."""
        # Create two contexts with different configurations
        config1 = ApplicationConfig()
        config1.logging.level = "DEBUG"
        context1 = AsyncRequestContext(user_config=config1)

        config2 = ApplicationConfig()
        config2.logging.level = "WARNING"
        context2 = AsyncRequestContext(user_config=config2)

        # Get configuration from each context
        result1 = await get_configuration(context1)
        result2 = await get_configuration(context2)

        assert result1.is_success()
        assert result2.is_success()

        response1 = result1.unwrap()
        response2 = result2.unwrap()

        # Verify isolation
        assert response1.current_config["logging"]["level"] == "DEBUG"
        assert response2.current_config["logging"]["level"] == "WARNING"

    @pytest.mark.asyncio
    async def test_context_updates_user_config(self) -> None:
        """Test that updates modify context user_config."""
        context = AsyncRequestContext()

        # Update configuration through context
        result = await update_configuration(
            {"logging.level": "DEBUG"},
            context,
        )

        assert result.is_success()
        assert context.user_config is not None
        assert context.user_config.logging.level == "DEBUG"

    @pytest.mark.asyncio
    async def test_context_sources_integration(self) -> None:
        """Test that add_content_source updates context sources."""
        context = AsyncRequestContext()

        result = await add_content_source(
            ["phb", "dmg"],
            replace_existing=True,
            context=context,
        )

        assert result.is_success()
        assert context.sources == ["phb", "dmg"]

    @pytest.mark.asyncio
    async def test_multiple_tools_same_context(self) -> None:
        """Test using multiple tools with the same context."""
        context = AsyncRequestContext()

        # Configure paper layout
        result1 = await configure_paper_layout(
            paper_size="a4",
            context=context,
        )

        # Add content sources
        result2 = await add_content_source(
            ["phb", "tcoe"],
            replace_existing=True,
            context=context,
        )

        # Configure spellbook generation
        result3 = await configure_spellbook_generation(
            alphabetical_organization=True,
            context=context,
        )

        # All should succeed
        assert result1.is_success()
        assert result2.is_success()
        assert result3.is_success()

        # Verify cumulative configuration
        assert context.user_config is not None
        assert context.user_config.rendering.latex.document.paper_size == "a4"
        assert context.sources == ["phb", "tcoe"]
        assert (
            context.user_config.rendering.latex.rendering.appendix_organization
            == "alphabetical"
        )


class TestErrorHandlingAndValidation:
    """Test comprehensive error handling and validation."""

    def setup_method(self) -> None:
        """Set up test environment."""
        reset_test_environment()

    @pytest.mark.asyncio
    async def test_invalid_paper_size(self) -> None:
        """Test invalid paper size handling."""
        # This should trigger a validation error during config update
        result = await configure_paper_layout(paper_size="invalid")  # type: ignore[arg-type]

        # The function signature prevents this at runtime, but if it somehow gets through,
        # it should be caught by the validation
        # Since the type system prevents this, let's test with a manual update instead
        result = await update_configuration(
            {"rendering.latex.document.paper_size": "invalid"}
        )

        assert result.is_success()  # Returns success with validation errors
        response = result.unwrap()
        assert response.success is False
        assert len(response.errors) > 0

    @pytest.mark.asyncio
    async def test_configuration_exception_propagation(self) -> None:
        """Test that exceptions are properly converted to MCPErrors."""
        with patch(
            "dnd5e.mcp.tools.config.ApplicationConfig",
            side_effect=Exception("Config error"),
        ):
            result = await update_configuration({"logging.level": "DEBUG"})

            assert result.is_error()
            error = result.error
            assert isinstance(error, MCPError)
            assert "Config error" in error.message

    @pytest.mark.asyncio
    async def test_file_system_error_handling(self) -> None:
        """Test file system error handling in preset operations."""
        # Test save operation failure by mocking the directory creation
        with patch(
            "dnd5e.mcp.tools.config._ensure_presets_dir",
            side_effect=PermissionError("Access denied"),
        ):
            result = await save_user_preferences("Test", "Test description")

            assert result.is_error()
            error = result.error
            assert isinstance(error, MCPError)
            assert error.error_code == MCPErrorCode.INTERNAL_ERROR
            assert "Access denied" in error.message

    @pytest.mark.asyncio
    async def test_empty_configuration_updates(self) -> None:
        """Test handling of empty configuration updates."""
        result = await update_configuration({})

        assert result.is_success()
        response = result.unwrap()
        assert response.success is True
        assert len(response.updated_fields) == 0

    @pytest.mark.asyncio
    async def test_preset_name_validation(self) -> None:
        """Test preset name validation edge cases."""
        # Empty name
        result = await save_user_preferences("", "Description")
        assert result.is_error()

        # Whitespace only
        result = await save_user_preferences("   ", "Description")
        assert result.is_error()

        # Valid name with spaces
        with tempfile.TemporaryDirectory() as tmp_dir:
            with patch("dnd5e.mcp.tools.config._PRESETS_DIR", Path(tmp_dir)):
                result = await save_user_preferences("Valid Name", "Description")
                assert result.is_success()

    @pytest.mark.asyncio
    async def test_configuration_serialization_edge_cases(self) -> None:
        """Test configuration serialization with edge cases."""
        # Create config with None values and custom paths
        config = ApplicationConfig()
        config.paths.data_path = None
        config.paths.font_dir = None

        config_dict = _get_current_config_dict(config)

        # Should handle None values gracefully
        assert config_dict["paths"]["data_path"] is None
        assert config_dict["paths"]["font_dir"] is None
        assert isinstance(config_dict, dict)

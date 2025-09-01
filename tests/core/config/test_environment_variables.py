"""Comprehensive tests for STUDIORUM_* environment variable configuration.

This module tests the environment variable system comprehensively across all
configuration sections of ApplicationConfig, including deeply nested configurations,
type conversions, error handling, and precedence rules.
"""

import json
import os
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from pydantic import ValidationError
from pydantic_settings import SettingsError

from studiorum.core.config.unified_config import (
    ApplicationConfig,
    get_app_config,
    reset_app_config,
)
from studiorum.core.services.container import ServiceContainer


class TestEnvironmentVariables:
    """Comprehensive tests for STUDIORUM_* environment variable configuration."""

    def setup_method(self) -> None:
        """Set up test environment with clean state."""
        # Reset both app config and service container for isolation
        reset_app_config()
        ServiceContainer.reset_global_instance()
        # Store original environment state
        self._original_env: dict[str, str | None] = {}

    def teardown_method(self) -> None:
        """Clean up environment after each test."""
        # Restore original environment state
        for key, original_value in self._original_env.items():
            if original_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = original_value

        # Reset configs again for clean slate
        reset_app_config()
        ServiceContainer.reset_global_instance()

    def _set_env_vars(self, env_vars: dict[str, str]) -> None:
        """Set environment variables and track original values."""
        for key, value in env_vars.items():
            self._original_env[key] = os.environ.get(key)
            os.environ[key] = value

    def test_logging_config_environment_variables(self) -> None:
        """Test STUDIORUM_LOGGING__* environment variables."""
        env_vars = {
            "STUDIORUM_LOGGING__LEVEL": "DEBUG",
            "STUDIORUM_LOGGING__FORMAT": "%(levelname)s: %(message)s",
        }
        self._set_env_vars(env_vars)

        config = ApplicationConfig()

        assert config.logging.level == "DEBUG"
        assert config.logging.format == "%(levelname)s: %(message)s"

    def test_logging_level_validation_via_env(self) -> None:
        """Test that invalid log levels are rejected via environment variables."""
        env_vars = {"STUDIORUM_LOGGING__LEVEL": "INVALID_LEVEL"}
        self._set_env_vars(env_vars)

        with pytest.raises(ValidationError):
            ApplicationConfig()

    def test_mcp_config_environment_variables(self) -> None:
        """Test STUDIORUM_MCP__* environment variables."""
        env_vars = {
            "STUDIORUM_MCP__ENABLED": "true",
            "STUDIORUM_MCP__HOST": "0.0.0.0",
            "STUDIORUM_MCP__PORT": "9090",
            "STUDIORUM_MCP__MAX_CONCURRENT_REQUESTS": "20",
            "STUDIORUM_MCP__REQUEST_TIMEOUT": "60",
            "STUDIORUM_MCP__MEMORY_LIMIT_MB": "2048",
            "STUDIORUM_MCP__CACHE_SIZE_MB": "512",
            "STUDIORUM_MCP__PRELOAD_CONTENT_TYPES": '["creatures", "spells", "items"]',
            "STUDIORUM_MCP__ENABLE_HOT_RELOAD": "true",
            "STUDIORUM_MCP__LOG_REQUESTS": "false",
        }
        self._set_env_vars(env_vars)

        config = ApplicationConfig()

        assert config.mcp.enabled is True
        assert config.mcp.host == "0.0.0.0"
        assert config.mcp.port == 9090
        assert config.mcp.max_concurrent_requests == 20
        assert config.mcp.request_timeout == 60
        assert config.mcp.memory_limit_mb == 2048
        assert config.mcp.cache_size_mb == 512
        assert config.mcp.preload_content_types == ["creatures", "spells", "items"]
        assert config.mcp.enable_hot_reload is True
        assert config.mcp.log_requests is False

    def test_paths_config_environment_variables(self) -> None:
        """Test STUDIORUM_PATHS__* environment variables."""
        import tempfile

        # Use temporary directories for writable paths
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            env_vars = {
                "STUDIORUM_PATHS__DATA_PATH": str(temp_path / "data"),
                "STUDIORUM_PATHS__ASSETS_PATH": str(temp_path / "assets"),
                "STUDIORUM_PATHS__OUTPUT_PATH": str(temp_path / "output"),
                "STUDIORUM_PATHS__BUILD_PATH": str(temp_path / "build"),
                "STUDIORUM_PATHS__FONT_DIR": str(temp_path / "fonts"),
            }
            self._set_env_vars(env_vars)

            config = ApplicationConfig()

            assert config.paths.data_path == temp_path / "data"
            assert config.paths.assets_path == temp_path / "assets"
            assert config.paths.output_path == temp_path / "output"
            assert config.paths.build_path == temp_path / "build"
            assert config.paths.font_dir == temp_path / "fonts"

    def test_processing_config_environment_variables(self) -> None:
        """Test STUDIORUM_PROCESSING__* environment variables."""
        env_vars = {
            "STUDIORUM_PROCESSING__MAX_WORKERS": "8",
            "STUDIORUM_PROCESSING__ENABLE_CACHING": "false",
            "STUDIORUM_PROCESSING__CACHE_TTL": "7200",
        }
        self._set_env_vars(env_vars)

        config = ApplicationConfig()

        assert config.processing.max_workers == 8
        assert config.processing.enable_caching is False
        assert config.processing.cache_ttl == 7200

    def test_validation_config_environment_variables(self) -> None:
        """Test STUDIORUM_VALIDATION__* environment variables."""
        env_vars = {
            "STUDIORUM_VALIDATION__STRICTNESS": "strict",
            "STUDIORUM_VALIDATION__ENABLE_SUMMARY": "true",
            "STUDIORUM_VALIDATION__MAX_DUPLICATE_ERRORS": "3",
        }
        self._set_env_vars(env_vars)

        config = ApplicationConfig()

        assert config.validation.strictness == "strict"
        assert config.validation.enable_summary is True
        assert config.validation.max_duplicate_errors == 3

    def test_rendering_content_config_environment_variables(self) -> None:
        """Test STUDIORUM_RENDERING__CONTENT__* environment variables."""
        env_vars = {
            "STUDIORUM_RENDERING__CONTENT__INCLUDE_IMAGES": "true",
            "STUDIORUM_RENDERING__CONTENT__APPENDIX_SPELLS": "true",
            "STUDIORUM_RENDERING__CONTENT__APPENDIX_ITEMS": "true",
            "STUDIORUM_RENDERING__CONTENT__APPENDIX_CREATURES": "true",
            "STUDIORUM_RENDERING__CONTENT__DEFAULT_SOURCES": '["phb", "mm", "dmg"]',
        }
        self._set_env_vars(env_vars)

        config = ApplicationConfig()

        assert config.rendering.content.include_images is True
        assert config.rendering.content.appendix_spells is True
        assert config.rendering.content.appendix_items is True
        assert config.rendering.content.appendix_creatures is True
        assert config.rendering.content.default_sources == ["phb", "mm", "dmg"]

    def test_rendering_latex_engine_config_environment_variables(self) -> None:
        """Test STUDIORUM_RENDERING__LATEX__ENGINE__* environment variables."""
        env_vars = {
            "STUDIORUM_RENDERING__LATEX__ENGINE__PRIMARY_ENGINE": "xelatex",
            "STUDIORUM_RENDERING__LATEX__ENGINE__FALLBACK_ENGINES": '["lualatex", "pdflatex"]',
            "STUDIORUM_RENDERING__LATEX__ENGINE__TIMEOUT": "600",
            "STUDIORUM_RENDERING__LATEX__ENGINE__MAX_PASSES": "5",
            "STUDIORUM_RENDERING__LATEX__ENGINE__SHOW_PROGRESS": "false",
            "STUDIORUM_RENDERING__LATEX__ENGINE__KEEP_TEMP_FILES": "true",
        }
        self._set_env_vars(env_vars)

        config = ApplicationConfig()

        assert config.rendering.latex.engine.primary_engine == "xelatex"
        assert config.rendering.latex.engine.fallback_engines == [
            "lualatex",
            "pdflatex",
        ]
        assert config.rendering.latex.engine.timeout == 600
        assert config.rendering.latex.engine.max_passes == 5
        assert config.rendering.latex.engine.show_progress is False
        assert config.rendering.latex.engine.keep_temp_files is True

    def test_rendering_latex_document_config_environment_variables(self) -> None:
        """Test STUDIORUM_RENDERING__LATEX__DOCUMENT__* environment variables."""
        env_vars = {
            "STUDIORUM_RENDERING__LATEX__DOCUMENT__DOCUMENT_CLASS": "article",
            "STUDIORUM_RENDERING__LATEX__DOCUMENT__CLASS_OPTIONS": '["onecolumn", "draft"]',
            "STUDIORUM_RENDERING__LATEX__DOCUMENT__PAPER_SIZE": "a4",
            "STUDIORUM_RENDERING__LATEX__DOCUMENT__FONT_SIZE": "12pt",
            "STUDIORUM_RENDERING__LATEX__DOCUMENT__FONT_SCHEME": "system",
            "STUDIORUM_RENDERING__LATEX__DOCUMENT__BACKGROUND": "none",
            "STUDIORUM_RENDERING__LATEX__DOCUMENT__HIGH_CONTRAST": "true",
            "STUDIORUM_RENDERING__LATEX__DOCUMENT__JUSTIFIED_TEXT": "true",
            "STUDIORUM_RENDERING__LATEX__DOCUMENT__FANCY_HEADERS": "false",
            "STUDIORUM_RENDERING__LATEX__DOCUMENT__TWO_COLUMN": "false",
            "STUDIORUM_RENDERING__LATEX__DOCUMENT__SHOW_TOC": "false",
            "STUDIORUM_RENDERING__LATEX__DOCUMENT__SHOW_INDEX": "false",
            "STUDIORUM_RENDERING__LATEX__DOCUMENT__FONTS": "wotc",
            "STUDIORUM_RENDERING__LATEX__DOCUMENT__NO_OUTLINE": "true",
        }
        self._set_env_vars(env_vars)

        config = ApplicationConfig()

        assert config.rendering.latex.document.document_class == "article"
        assert config.rendering.latex.document.class_options == ["onecolumn", "draft"]
        assert config.rendering.latex.document.paper_size == "a4"
        assert config.rendering.latex.document.font_size == "12pt"
        assert config.rendering.latex.document.font_scheme == "system"
        assert config.rendering.latex.document.background == "none"
        assert config.rendering.latex.document.high_contrast is True
        assert config.rendering.latex.document.justified_text is True
        assert config.rendering.latex.document.fancy_headers is False
        assert config.rendering.latex.document.two_column is False
        assert config.rendering.latex.document.show_toc is False
        assert config.rendering.latex.document.show_index is False
        assert config.rendering.latex.document.fonts == "wotc"
        assert config.rendering.latex.document.no_outline is True

    def test_rendering_latex_rendering_config_environment_variables(self) -> None:
        """Test STUDIORUM_RENDERING__LATEX__RENDERING__* environment variables."""
        env_vars = {
            "STUDIORUM_RENDERING__LATEX__RENDERING__ENABLE_HYPERLINKS": "false",
            "STUDIORUM_RENDERING__LATEX__RENDERING__ENABLE_CROSS_REFS": "false",
            "STUDIORUM_RENDERING__LATEX__RENDERING__AUTO_PAGE_REFS": "false",
            "STUDIORUM_RENDERING__LATEX__RENDERING__CROSS_REF_FORMAT": "page~\\pageref{{{label}}}",
            "STUDIORUM_RENDERING__LATEX__RENDERING__APPENDIX_ORGANIZATION": "source",
        }
        self._set_env_vars(env_vars)

        config = ApplicationConfig()

        assert config.rendering.latex.rendering.enable_hyperlinks is False
        assert config.rendering.latex.rendering.enable_cross_refs is False
        assert config.rendering.latex.rendering.auto_page_refs is False
        assert (
            config.rendering.latex.rendering.cross_ref_format
            == "page~\\pageref{{{label}}}"
        )
        assert config.rendering.latex.rendering.appendix_organization == "source"

    def test_image_config_basic_environment_variables(self) -> None:
        """Test basic STUDIORUM_IMAGE__* environment variables."""
        env_vars = {
            "STUDIORUM_IMAGE__ENABLED": "false",
            "STUDIORUM_IMAGE__CACHE_DIR": "/custom/cache",
            "STUDIORUM_IMAGE__DEFAULT_CACHE_TTL_HOURS": "48",
            "STUDIORUM_IMAGE__MAX_CACHE_SIZE_MB": "2048",
            "STUDIORUM_IMAGE__CLEANUP_INTERVAL_HOURS": "12",
        }
        self._set_env_vars(env_vars)

        config = ApplicationConfig()

        assert config.image.enabled is False
        assert config.image.cache_dir == Path("/custom/cache")
        assert config.image.default_cache_ttl_hours == 48
        assert config.image.max_cache_size_mb == 2048
        assert config.image.cleanup_interval_hours == 12

    def test_image_config_processing_environment_variables(self) -> None:
        """Test STUDIORUM_IMAGE__* processing environment variables."""
        env_vars = {
            "STUDIORUM_IMAGE__IMAGE_QUALITY": "high",
            "STUDIORUM_IMAGE__PLACEMENT_STRATEGY": "float",
            "STUDIORUM_IMAGE__GALLERY_LAYOUT": "showcase",
            "STUDIORUM_IMAGE__ENABLE_INTELLIGENT_PLACEMENT": "false",
            "STUDIORUM_IMAGE__ENABLE_CONTENT_ANALYSIS": "false",
            "STUDIORUM_IMAGE__ENABLE_LAYOUT_OPTIMIZATION": "false",
            "STUDIORUM_IMAGE__ENABLE_OUTPUT_OPTIMIZATION": "false",
        }
        self._set_env_vars(env_vars)

        config = ApplicationConfig()

        assert config.image.image_quality == "high"
        assert config.image.placement_strategy == "float"
        assert config.image.gallery_layout == "showcase"
        assert config.image.enable_intelligent_placement is False
        assert config.image.enable_content_analysis is False
        assert config.image.enable_layout_optimization is False
        assert config.image.enable_output_optimization is False

    def test_image_config_content_types_environment_variables(self) -> None:
        """Test STUDIORUM_IMAGE__* content type environment variables."""
        env_vars = {
            "STUDIORUM_IMAGE__BESTIARY_IMAGES": "false",
            "STUDIORUM_IMAGE__ITEM_IMAGES": "false",
            "STUDIORUM_IMAGE__ADVENTURE_IMAGES": "false",
            "STUDIORUM_IMAGE__CHAPTER_ART": "false",
        }
        self._set_env_vars(env_vars)

        config = ApplicationConfig()

        assert config.image.bestiary_images is False
        assert config.image.item_images is False
        assert config.image.adventure_images is False
        assert config.image.chapter_art is False

    def test_image_config_performance_environment_variables(self) -> None:
        """Test STUDIORUM_IMAGE__* performance environment variables."""
        env_vars = {
            "STUDIORUM_IMAGE__PRELOAD_IMAGES": "false",
            "STUDIORUM_IMAGE__USE_CACHE": "false",
            "STUDIORUM_IMAGE__SYNC_SOURCES_ON_STARTUP": "true",
            "STUDIORUM_IMAGE__PARALLEL_PROCESSING": "false",
            "STUDIORUM_IMAGE__MAX_CONCURRENT_DOWNLOADS": "10",
        }
        self._set_env_vars(env_vars)

        config = ApplicationConfig()

        assert config.image.preload_images is False
        assert config.image.use_cache is False
        assert config.image.sync_sources_on_startup is True
        assert config.image.parallel_processing is False
        assert config.image.max_concurrent_downloads == 10

    def test_image_config_advanced_environment_variables(self) -> None:
        """Test STUDIORUM_IMAGE__* advanced environment variables."""
        env_vars = {
            "STUDIORUM_IMAGE__ENABLED_SOURCES": '["source1", "source2"]',
            "STUDIORUM_IMAGE__FALLBACK_TO_PLACEHOLDERS": "false",
            "STUDIORUM_IMAGE__GENERATE_MISSING_ALT_TEXT": "false",
            "STUDIORUM_IMAGE__INCLUDE_IMAGES_DEFAULT": "true",
            "STUDIORUM_IMAGE__ENABLE_DEFAULT_5ETOOLS_SOURCE": "false",
        }
        self._set_env_vars(env_vars)

        config = ApplicationConfig()

        assert config.image.enabled_sources == ["source1", "source2"]
        assert config.image.fallback_to_placeholders is False
        assert config.image.generate_missing_alt_text is False
        assert config.image.include_images_default is True
        assert config.image.enable_default_5etools_source is False

    def test_type_conversion_boolean(self) -> None:
        """Test boolean type conversion from environment variables."""
        # Test various boolean representations
        boolean_tests = [
            ("true", True),
            ("True", True),
            ("TRUE", True),
            ("1", True),
            ("on", True),
            ("yes", True),
            ("false", False),
            ("False", False),
            ("FALSE", False),
            ("0", False),
            ("off", False),
            ("no", False),
        ]

        for str_value, expected_bool in boolean_tests:
            # Clean up any previous env var
            os.environ.pop("STUDIORUM_MCP__ENABLED", None)

            env_vars = {"STUDIORUM_MCP__ENABLED": str_value}
            self._set_env_vars(env_vars)

            config = ApplicationConfig()
            assert config.mcp.enabled == expected_bool, (
                f"Failed for '{str_value}', got {config.mcp.enabled}, expected {expected_bool}"
            )

    def test_type_conversion_integer(self) -> None:
        """Test integer type conversion from environment variables."""
        env_vars = {
            "STUDIORUM_MCP__PORT": "8443",
            "STUDIORUM_PROCESSING__MAX_WORKERS": "12",
        }
        self._set_env_vars(env_vars)

        config = ApplicationConfig()

        assert config.mcp.port == 8443
        assert config.processing.max_workers == 12
        assert isinstance(config.mcp.port, int)
        assert isinstance(config.processing.max_workers, int)

    def test_type_conversion_path(self) -> None:
        """Test Path type conversion from environment variables."""
        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            env_vars = {
                "STUDIORUM_PATHS__DATA_PATH": str(temp_path / "test_data"),
                "STUDIORUM_PATHS__OUTPUT_PATH": str(temp_path / "test_output"),
            }
            self._set_env_vars(env_vars)

            config = ApplicationConfig()

            assert config.paths.data_path == temp_path / "test_data"
            assert config.paths.output_path == temp_path / "test_output"
            assert isinstance(config.paths.data_path, Path)
            assert isinstance(config.paths.output_path, Path)

    def test_type_conversion_list(self) -> None:
        """Test list type conversion from JSON strings in environment variables."""
        env_vars = {
            "STUDIORUM_MCP__PRELOAD_CONTENT_TYPES": '["creatures", "spells", "items"]',
            "STUDIORUM_RENDERING__CONTENT__DEFAULT_SOURCES": '["phb", "mm"]',
        }
        self._set_env_vars(env_vars)

        config = ApplicationConfig()

        assert config.mcp.preload_content_types == ["creatures", "spells", "items"]
        assert config.rendering.content.default_sources == ["phb", "mm"]
        assert isinstance(config.mcp.preload_content_types, list)
        assert isinstance(config.rendering.content.default_sources, list)

    def test_invalid_type_conversion_integer(self) -> None:
        """Test that invalid integer values raise validation errors."""
        env_vars = {"STUDIORUM_MCP__PORT": "not_a_number"}
        self._set_env_vars(env_vars)

        with pytest.raises(ValidationError):
            ApplicationConfig()

    def test_invalid_enum_values(self) -> None:
        """Test that invalid enum values raise validation errors."""
        env_vars = {"STUDIORUM_VALIDATION__STRICTNESS": "invalid_strictness"}
        self._set_env_vars(env_vars)

        with pytest.raises(ValidationError):
            ApplicationConfig()

    def test_constraint_validation(self) -> None:
        """Test that constraint validation works with environment variables."""
        # Test negative port (should fail)
        env_vars = {"STUDIORUM_MCP__PORT": "-1"}
        self._set_env_vars(env_vars)

        with pytest.raises(ValidationError):
            ApplicationConfig()

        # Clean up and test valid port
        os.environ.pop("STUDIORUM_MCP__PORT")
        env_vars = {"STUDIORUM_MCP__PORT": "8080"}
        self._set_env_vars(env_vars)

        # Should not raise
        config = ApplicationConfig()
        assert config.mcp.port == 8080

    def test_range_constraint_validation(self) -> None:
        """Test that range constraints work with environment variables."""
        # Test max_workers out of range (should fail)
        env_vars = {"STUDIORUM_PROCESSING__MAX_WORKERS": "100"}
        self._set_env_vars(env_vars)

        with pytest.raises(ValidationError):
            ApplicationConfig()

        # Clean up and test valid max_workers
        os.environ.pop("STUDIORUM_PROCESSING__MAX_WORKERS")
        env_vars = {"STUDIORUM_PROCESSING__MAX_WORKERS": "8"}
        self._set_env_vars(env_vars)

        # Should not raise
        config = ApplicationConfig()
        assert config.processing.max_workers == 8

    def test_complex_nested_configuration(self) -> None:
        """Test deeply nested configuration with multiple levels."""
        env_vars = {
            # Test 4-level nesting
            "STUDIORUM_RENDERING__LATEX__DOCUMENT__PAPER_SIZE": "a4",
            "STUDIORUM_RENDERING__LATEX__ENGINE__PRIMARY_ENGINE": "xelatex",
            "STUDIORUM_RENDERING__LATEX__RENDERING__APPENDIX_ORGANIZATION": "type",
        }
        self._set_env_vars(env_vars)

        config = ApplicationConfig()

        assert config.rendering.latex.document.paper_size == "a4"
        assert config.rendering.latex.engine.primary_engine == "xelatex"
        assert config.rendering.latex.rendering.appendix_organization == "type"

    def test_partial_configuration_override(self) -> None:
        """Test that partial environment overrides don't break defaults."""
        # Only set one MCP field
        env_vars = {"STUDIORUM_MCP__ENABLED": "true"}
        self._set_env_vars(env_vars)

        config = ApplicationConfig()

        # Override field should change
        assert config.mcp.enabled is True

        # Default fields should remain unchanged
        assert config.mcp.host == "localhost"  # Default value
        assert config.mcp.port == 8080  # Default value
        assert config.mcp.max_concurrent_requests == 10  # Default value

    def test_empty_environment_variables(self) -> None:
        """Test behavior with empty environment variable values."""
        # Most empty values should use defaults or fail validation
        env_vars = {"STUDIORUM_PATHS__DATA_PATH": ""}
        self._set_env_vars(env_vars)

        config = ApplicationConfig()
        # Empty string for path should result in None (the default)
        assert config.paths.data_path is None or config.paths.data_path == Path("")

    def test_case_insensitive_environment_variables(self) -> None:
        """Test that environment variables are case insensitive according to Pydantic settings."""
        # Test mixed case - Pydantic should handle this based on case_sensitive=False
        env_vars = {
            "studiorum_mcp__enabled": "true",  # lowercase
            "STUDIORUM_MCP__PORT": "9000",  # uppercase
        }
        self._set_env_vars(env_vars)

        config = ApplicationConfig()

        assert config.mcp.enabled is True
        assert config.mcp.port == 9000

    def test_environment_variable_precedence_over_defaults(self) -> None:
        """Test that environment variables override default values."""
        # Set env vars that differ from defaults
        env_vars = {
            "STUDIORUM_MCP__ENABLED": "true",  # Default is False
            "STUDIORUM_PROCESSING__MAX_WORKERS": "10",  # Default is 5
            "STUDIORUM_VALIDATION__STRICTNESS": "lenient",  # Default is "normal"
        }
        self._set_env_vars(env_vars)

        config = ApplicationConfig()

        # Environment values should override defaults
        assert config.mcp.enabled is True  # Not default False
        assert config.processing.max_workers == 10  # Not default 5
        assert config.validation.strictness == "lenient"  # Not default "normal"

        # Unset values should still use defaults
        assert config.mcp.host == "localhost"  # Default value
        assert config.logging.level == "WARNING"  # Default value

    def test_json_parsing_in_environment_variables(self) -> None:
        """Test JSON parsing for complex data structures in environment variables."""
        env_vars = {
            # Test list parsing
            "STUDIORUM_MCP__PRELOAD_CONTENT_TYPES": '["creatures", "spells"]',
            # Test with spaces and special characters
            "STUDIORUM_RENDERING__CONTENT__DEFAULT_SOURCES": '["phb-2024", "mm-legacy"]',
        }
        self._set_env_vars(env_vars)

        config = ApplicationConfig()

        assert config.mcp.preload_content_types == ["creatures", "spells"]
        assert config.rendering.content.default_sources == ["phb-2024", "mm-legacy"]

    def test_invalid_json_in_environment_variables(self) -> None:
        """Test that invalid JSON in environment variables raises errors."""
        env_vars = {
            # Invalid JSON - missing closing bracket
            "STUDIORUM_MCP__PRELOAD_CONTENT_TYPES": '["creatures", "spells"',
        }
        self._set_env_vars(env_vars)

        with pytest.raises(SettingsError):
            ApplicationConfig()

    def test_complete_configuration_via_environment(self) -> None:
        """Test that a complete configuration can be specified via environment variables."""
        env_vars = {
            # Logging
            "STUDIORUM_LOGGING__LEVEL": "DEBUG",
            # MCP
            "STUDIORUM_MCP__ENABLED": "true",
            "STUDIORUM_MCP__PORT": "8443",
            # Paths (use relative paths to avoid permission issues)
            "STUDIORUM_PATHS__DATA_PATH": "test_data",
            "STUDIORUM_PATHS__OUTPUT_PATH": "test_output",
            # Processing
            "STUDIORUM_PROCESSING__MAX_WORKERS": "8",
            # Validation
            "STUDIORUM_VALIDATION__STRICTNESS": "strict",
            # Rendering - LaTeX document
            "STUDIORUM_RENDERING__LATEX__DOCUMENT__PAPER_SIZE": "a4",
            "STUDIORUM_RENDERING__LATEX__ENGINE__PRIMARY_ENGINE": "xelatex",
            # Image
            "STUDIORUM_IMAGE__ENABLED": "false",
        }
        self._set_env_vars(env_vars)

        config = ApplicationConfig()

        # Verify all sections are configured correctly
        assert config.logging.level == "DEBUG"
        assert config.mcp.enabled is True
        assert config.mcp.port == 8443
        assert config.paths.data_path == Path("test_data")
        assert config.paths.output_path == Path("test_output")
        assert config.processing.max_workers == 8
        assert config.validation.strictness == "strict"
        assert config.rendering.latex.document.paper_size == "a4"
        assert config.rendering.latex.engine.primary_engine == "xelatex"
        assert config.image.enabled is False


class TestEnvironmentVariableIntegration:
    """Integration tests for environment variables with the service container."""

    def setup_method(self) -> None:
        """Set up test environment."""
        reset_app_config()
        ServiceContainer.reset_global_instance()
        self._original_env: dict[str, str | None] = {}

    def teardown_method(self) -> None:
        """Clean up environment after each test."""
        for key, original_value in self._original_env.items():
            if original_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = original_value
        reset_app_config()
        ServiceContainer.reset_global_instance()

    def _set_env_vars(self, env_vars: dict[str, str]) -> None:
        """Set environment variables and track original values."""
        for key, value in env_vars.items():
            self._original_env[key] = os.environ.get(key)
            os.environ[key] = value

    def test_global_config_with_environment_variables(self) -> None:
        """Test that get_app_config() respects environment variables."""
        env_vars = {
            "STUDIORUM_LOGGING__LEVEL": "DEBUG",
            "STUDIORUM_MCP__ENABLED": "true",
        }
        self._set_env_vars(env_vars)

        # Reset to ensure fresh config
        reset_app_config()

        config = get_app_config()

        assert config.logging.level == "DEBUG"
        assert config.mcp.enabled is True

    def test_config_isolation_between_tests(self) -> None:
        """Test that configuration changes don't leak between tests."""
        # First test with specific config
        env_vars = {"STUDIORUM_LOGGING__LEVEL": "DEBUG"}
        self._set_env_vars(env_vars)

        config1 = get_app_config()
        assert config1.logging.level == "DEBUG"

        # Clear environment and reset
        os.environ.pop("STUDIORUM_LOGGING__LEVEL")
        reset_app_config()

        # Second test should have defaults
        config2 = get_app_config()
        assert config2.logging.level == "WARNING"  # Default value

    def test_environment_changes_dont_affect_existing_config(self) -> None:
        """Test that changing environment variables doesn't affect already-loaded config."""
        # Load config with default values
        config = get_app_config()
        original_level = config.logging.level

        # Change environment variable
        env_vars = {"STUDIORUM_LOGGING__LEVEL": "DEBUG"}
        self._set_env_vars(env_vars)

        # Existing config should be unchanged
        assert config.logging.level == original_level

        # New config should reflect environment change
        reset_app_config()
        new_config = get_app_config()
        assert new_config.logging.level == "DEBUG"

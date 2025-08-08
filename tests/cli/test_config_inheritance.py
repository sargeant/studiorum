"""Test that CLI parameters properly inherit from configuration."""

import pytest

from dnd5e.cli.config_factory import (
    get_background_default,
    get_cli_defaults,
    get_compile_pdf_default,
    get_concurrent_limit_default,
    get_config_default,
    get_document_class_default,
    get_font_size_default,
    get_justified_default,
    get_two_column_default,
    get_with_creatures_default,
    get_with_images_default,
    get_with_index_default,
    get_with_items_default,
)
from dnd5e.core.config.unified_config import get_app_config, reset_app_config
from tests.test_helpers import reset_test_environment


class TestCliConfigInheritance:
    """Test CLI configuration inheritance from unified config."""

    def setup_method(self) -> None:
        """Reset config before each test."""
        # Reset global state for complete isolation
        reset_test_environment()

        reset_app_config()

    def test_cli_defaults_match_config(self) -> None:
        """Test that CLI defaults come from config system."""
        config = get_app_config()
        cli_defaults = get_cli_defaults()

        # Document structure parameters
        assert (
            cli_defaults["document_class"]
            == config.rendering.latex.document.document_class
        )
        assert cli_defaults["font_size"] == config.rendering.latex.document.font_size
        assert cli_defaults["background"] == config.rendering.latex.document.background
        assert cli_defaults["two_column"] == config.rendering.latex.document.two_column
        assert (
            cli_defaults["justified"] == config.rendering.latex.document.justified_text
        )

        # Content inclusion parameters
        assert cli_defaults["with_images"] == config.rendering.content.include_images
        assert cli_defaults["with_items"] == config.rendering.content.include_items
        assert (
            cli_defaults["with_creatures"] == config.rendering.content.include_creatures
        )
        assert cli_defaults["with_index"] == config.rendering.latex.document.show_index

        # Compilation parameters
        assert (
            cli_defaults["compile_pdf"] == config.rendering.compilation.auto_compile_pdf
        )

        # Processing parameters
        assert cli_defaults["concurrent_limit"] == config.processing.max_workers

    def test_individual_default_functions(self) -> None:
        """Test individual default getter functions."""
        config = get_app_config()

        # Document structure
        assert (
            get_document_class_default()
            == config.rendering.latex.document.document_class
        )
        assert get_font_size_default() == config.rendering.latex.document.font_size
        assert get_background_default() == config.rendering.latex.document.background
        assert get_two_column_default() == config.rendering.latex.document.two_column
        assert get_justified_default() == config.rendering.latex.document.justified_text

        # Content inclusion
        assert get_with_images_default() == config.rendering.content.include_images
        assert get_with_items_default() == config.rendering.content.include_items
        assert (
            get_with_creatures_default() == config.rendering.content.include_creatures
        )
        assert get_with_index_default() == config.rendering.latex.document.show_index

        # Compilation
        assert (
            get_compile_pdf_default() == config.rendering.compilation.auto_compile_pdf
        )

        # Processing
        assert get_concurrent_limit_default() == config.processing.max_workers

    def test_config_default_by_name(self) -> None:
        """Test getting config defaults by field name."""
        config = get_app_config()

        assert (
            get_config_default("document_class")
            == config.rendering.latex.document.document_class
        )
        assert (
            get_config_default("with_images") == config.rendering.content.include_images
        )
        assert (
            get_config_default("compile_pdf")
            == config.rendering.compilation.auto_compile_pdf
        )
        assert get_config_default("concurrent_limit") == config.processing.max_workers

        # Test unknown field returns None
        assert get_config_default("unknown_field") is None

    def test_expected_default_values(self) -> None:
        """Test that default values match expected values."""
        cli_defaults = get_cli_defaults()

        # Document structure - these are the standard defaults
        assert cli_defaults["document_class"] == "dndbook"
        assert cli_defaults["font_size"] == "11pt"
        assert cli_defaults["background"] is None
        assert cli_defaults["two_column"] is True
        assert cli_defaults["justified"] is False  # Aligned to CLI preference

        # Content inclusion - conservative defaults
        assert cli_defaults["with_images"] is False
        assert cli_defaults["with_items"] is True
        assert cli_defaults["with_creatures"] is True
        assert cli_defaults["with_index"] is True  # Aligned to CLI preference

        # Compilation - safe default
        assert cli_defaults["compile_pdf"] is False

        # Processing - reasonable default
        assert cli_defaults["concurrent_limit"] == 5

    def test_config_consistency(self) -> None:
        """Test that config values are internally consistent."""
        config = get_app_config()

        # Verify that conflicting defaults have been resolved
        assert config.rendering.latex.document.justified_text is False
        assert config.rendering.latex.document.show_index is True

        # Verify new config sections exist
        assert hasattr(config.rendering, "content")
        assert hasattr(config.rendering, "compilation")
        assert hasattr(config.rendering.content, "include_images")
        assert hasattr(config.rendering.compilation, "auto_compile_pdf")

    def test_config_factory_imports(self) -> None:
        """Test that all factory functions can be imported and called."""
        # This tests that our imports work correctly in CLI modules
        from dnd5e.cli.config_factory import (
            get_background_default,
            get_compile_pdf_default,
            get_concurrent_limit_default,
            get_document_class_default,
            get_font_size_default,
            get_justified_default,
            get_two_column_default,
            get_with_creatures_default,
            get_with_images_default,
            get_with_index_default,
            get_with_items_default,
        )

        # All functions should return values without error
        assert isinstance(get_document_class_default(), str)
        assert isinstance(get_font_size_default(), str)
        assert get_background_default() is None  # Can be None
        assert isinstance(get_two_column_default(), bool)
        assert isinstance(get_justified_default(), bool)
        assert isinstance(get_with_images_default(), bool)
        assert isinstance(get_with_items_default(), bool)
        assert isinstance(get_with_creatures_default(), bool)
        assert isinstance(get_with_index_default(), bool)
        assert isinstance(get_compile_pdf_default(), bool)
        assert isinstance(get_concurrent_limit_default(), int)

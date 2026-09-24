"""Test that CLI parameters properly inherit from configuration."""

import pytest

from studiorum.cli.config_factory import (
    get_appendix_creatures_default,
    get_appendix_items_default,
    get_appendix_spells_default,
    get_compile_pdf_default,
    get_concurrent_limit_default,
    get_document_class_default,
    get_with_images_default,
    get_with_index_default,
)
from studiorum.core.config.unified_config import get_app_config, reset_app_config


@pytest.mark.cli
class TestCliConfigInheritance:
    """Test CLI configuration inheritance from unified config."""

    def setup_method(self) -> None:
        """Reset config before each test."""

        reset_app_config()

    def test_individual_default_functions(self) -> None:
        """Test individual default getter functions."""
        config = get_app_config()

        # Document structure
        assert (
            get_document_class_default()
            == config.rendering.latex.document.document_class
        )

        # Content inclusion
        assert get_with_images_default() == config.rendering.content.include_images
        assert get_with_index_default() == config.rendering.latex.document.show_index

        # Appendix generation
        assert get_appendix_spells_default() == config.rendering.content.appendix_spells
        assert get_appendix_items_default() == config.rendering.content.appendix_items
        assert (
            get_appendix_creatures_default()
            == config.rendering.content.appendix_creatures
        )

        # Compilation
        assert (
            get_compile_pdf_default() == config.rendering.compilation.auto_compile_pdf
        )

        # Processing
        assert get_concurrent_limit_default() == config.processing.max_workers

    def test_config_consistency(self) -> None:
        """Test that config values are internally consistent."""
        config = get_app_config()

        # Verify that conflicting defaults have been resolved
        assert config.rendering.latex.document.justified_text is False
        assert config.rendering.latex.document.show_index is False

        # Verify new config sections exist
        assert hasattr(config.rendering, "content")
        assert hasattr(config.rendering, "compilation")
        assert hasattr(config.rendering.content, "include_images")
        assert hasattr(config.rendering.compilation, "auto_compile_pdf")

    def test_config_factory_imports(self) -> None:
        """Test that all factory functions can be imported and called."""
        # This tests that our imports work correctly in CLI modules
        from studiorum.cli.config_factory import (
            get_appendix_creatures_default,
            get_appendix_items_default,
            get_appendix_spells_default,
            get_compile_pdf_default,
            get_concurrent_limit_default,
            get_document_class_default,
            get_with_images_default,
            get_with_index_default,
        )

        # All functions should return values without error
        assert isinstance(get_document_class_default(), str)
        assert isinstance(get_with_images_default(), bool)
        assert isinstance(get_with_index_default(), bool)
        assert isinstance(get_appendix_spells_default(), bool)
        assert isinstance(get_appendix_items_default(), bool)
        assert isinstance(get_appendix_creatures_default(), bool)
        assert isinstance(get_compile_pdf_default(), bool)
        assert isinstance(get_concurrent_limit_default(), int)

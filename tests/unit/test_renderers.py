"""Tests for rendering system."""

from typing import Any

import pytest

from studiorum.latex_engine.core.template_engine import LaTeXTemplateEngine
from studiorum.renderers.context import RenderingContext


class TestRenderingContext:
    """Tests for RenderingContext class."""

    def test_render_context_creation(self) -> None:
        """Test basic render context creation."""
        context: Any = RenderingContext(
            output_format="latex",
            metadata={
                "include_images": False,
                "include_toc": True,
                "include_items": True,
            },
        )
        assert context.metadata.get("include_images") is False
        assert context.metadata.get("include_toc") is True
        assert context.metadata.get("include_items") is True

    def test_render_context_with_options(self) -> None:
        """Test render context with custom options."""
        context: Any = RenderingContext(
            output_format="latex",
            metadata={
                "title": "Test Document",
                "include_images": True,
                "include_toc": False,
                "page_size": "a4paper",
            },
        )

        assert context.metadata.get("title") == "Test Document"
        assert context.metadata.get("include_images") is True
        assert context.metadata.get("include_toc") is False
        assert context.metadata.get("page_size") == "a4paper"

    def test_should_include_content_type(self) -> None:
        """Test content type inclusion filtering via metadata."""
        context: Any = RenderingContext(
            output_format="latex",
            metadata={
                "include_items": False,
                "include_creatures": True,
                "include_spells": True,
            },
        )

        # Test that metadata stores the content type inclusion flags
        assert not context.metadata.get("include_items")
        assert context.metadata.get("include_creatures")
        assert context.metadata.get("include_spells")

    def test_context_copy(self) -> None:
        """Test context copying with updates."""
        original: Any = RenderingContext(
            output_format="latex",
            metadata={"title": "Original", "include_images": False},
        )
        copy = original.model_copy(
            update={
                "metadata": {
                    **original.metadata,
                    "title": "Updated",
                    "include_images": True,
                }
            }
        )

        assert original.metadata.get("title") == "Original"
        assert original.metadata.get("include_images") is False
        assert copy.metadata.get("title") == "Updated"
        assert copy.metadata.get("include_images") is True

    def test_get_image_path(self, tmp_path: Any) -> None:
        """Test image path resolution via metadata."""
        images_dir = tmp_path / "images"
        images_dir.mkdir()

        context: Any = RenderingContext(
            output_format="latex", metadata={"images_dir": images_dir}
        )

        # Test that images_dir is properly stored in metadata
        assert context.metadata.get("images_dir") == images_dir

        # Test path resolution (would typically be handled by image service)
        stored_dir = context.metadata.get("images_dir")
        if stored_dir:
            image_path = stored_dir / "test.png"
            assert image_path == images_dir / "test.png"

        # Test with no images_dir
        context_no_dir: Any = RenderingContext(output_format="latex")
        assert context_no_dir.metadata.get("images_dir") is None


class TestLaTeXTemplateEngine:
    """Tests for LaTeX template engine."""

    def test_template_engine_creation(self) -> None:
        """Test template engine creation."""
        engine: Any = LaTeXTemplateEngine()
        assert engine is not None
        assert engine.templates_dir is not None

    def test_builtin_templates_loaded(self) -> None:
        """Test that built-in templates are available."""
        engine: Any = LaTeXTemplateEngine()

        required_templates = [
            "_content",
            "base",
            "book",
        ]

        for template_name in required_templates:
            assert engine.template_exists(template_name)

    def test_render_simple_template(self) -> None:
        """Test rendering template with variables."""
        engine: Any = LaTeXTemplateEngine()

        # Create a simple test template
        test_template = engine.templates_dir / "test.tex.j2"
        test_template.write_text("Hello <# name #>, you are <# age #> years old.")

        try:
            result = engine.render_template("test", {"name": "Alice", "age": 25})
            assert result == "Hello Alice, you are 25 years old."
        finally:
            test_template.unlink(missing_ok=True)

    def test_render_template_with_conditionals(self) -> None:
        """Test template with conditional blocks."""
        engine: Any = LaTeXTemplateEngine()

        # Create a conditional test template
        conditional_template = engine.templates_dir / "conditional.tex.j2"
        conditional_template.write_text("""Name: <# name #>
<@ if age @>
Age: <# age #>
<@ endif @>""")

        try:
            # With age
            result1 = engine.render_template(
                "conditional", {"name": "Alice", "age": 25}
            )
            assert "Age: 25" in result1

            # Without age
            result2 = engine.render_template(
                "conditional", {"name": "Bob", "age": None}
            )
            assert "Age:" not in result2
        finally:
            conditional_template.unlink(missing_ok=True)

    def test_unknown_template(self) -> None:
        """Test error handling for unknown template."""
        engine: Any = LaTeXTemplateEngine()

        with pytest.raises(
            FileNotFoundError, match="Template 'unknown.tex.j2' not found"
        ):
            engine.render_template("unknown", {})

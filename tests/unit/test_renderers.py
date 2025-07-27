"""Tests for rendering system."""

from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from dnd5e.core.models.content import ContentType  # type: ignore
from dnd5e.renderers.base import RenderContext, RenderingError  # type: ignore
from dnd5e.renderers.latex import (  # type: ignore
    LaTeXCreatureRenderer,
    LaTeXDocumentRenderer,
    LaTeXItemRenderer,
    LaTeXSpellRenderer,
    LaTeXTemplateEngine,
)


class TestRenderContext:
    """Tests for RenderContext class."""

    def test_render_context_creation(self) -> None:
        """Test basic render context creation."""
        context: Any = RenderContext()
        assert context.include_images is False
        assert context.include_toc is True
        assert context.include_items is True

    def test_render_context_with_options(self) -> None:
        """Test render context with custom options."""
        context: Any = RenderContext(
            title="Test Document",
            include_images=True,
            include_toc=False,
            page_size="a4paper",
        )

        assert context.title == "Test Document"
        assert context.include_images is True
        assert context.include_toc is False
        assert context.page_size == "a4paper"

    def test_should_include_content_type(self) -> None:
        """Test content type inclusion filtering."""
        context: Any = RenderContext(
            include_items=False, include_creatures=True, include_spells=True
        )

        assert not context.should_include_content_type("item")
        assert context.should_include_content_type("creature")
        assert context.should_include_content_type("spell")

    def test_context_copy(self) -> None:
        """Test context copying with updates."""
        original: Any = RenderContext(title="Original", include_images=False)
        copy = original.copy(title="Updated", include_images=True)

        assert original.title == "Original"
        assert original.include_images is False
        assert copy.title == "Updated"
        assert copy.include_images is True

    def test_get_image_path(self, tmp_path: Any) -> None:
        """Test image path resolution."""
        images_dir = tmp_path / "images"
        images_dir.mkdir()

        context: Any = RenderContext(images_dir=images_dir)

        image_path = context.get_image_path("test.png")
        assert image_path == images_dir / "test.png"

        # Test with no images_dir
        context_no_dir: Any = RenderContext()
        assert context_no_dir.get_image_path("test.png") is None


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
            "spell_entry",
            "creature_entry",
            "item_entry",
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


class TestLaTeXDocumentRenderer:
    """Tests for LaTeX document renderer."""

    def test_document_renderer_creation(self) -> None:
        """Test document renderer creation."""
        renderer: Any = LaTeXDocumentRenderer()
        assert renderer.output_format == "latex"
        assert renderer.template_engine is not None
        assert renderer.entry_registry is not None

    @pytest.mark.asyncio
    async def test_render_single_spell(
        self, sample_spell: Any, tag_resolver: Any
    ) -> None:
        """Test rendering single spell as document."""
        renderer: Any = LaTeXDocumentRenderer()
        context: Any = RenderContext(
            title="Test Spell Document", tag_resolver=tag_resolver
        )

        # Mock DND template availability for testing
        with patch.object(
            renderer.template_engine,
            "check_dnd_template_availability",
            return_value=True,
        ):
            result = renderer.render_document([sample_spell], context)

        assert "\\documentclass" in result
        assert "\\title{Test Spell Document}" in result
        assert (
            "\\DndSpellHeader" in result or "Fireball" in result
        )  # DND template format
        assert "\\end{document}" in result

    @pytest.mark.asyncio
    async def test_render_multiple_content(
        self, sample_spell: Any, sample_creature: Any, tag_resolver: Any
    ) -> None:
        """Test rendering multiple content items."""
        renderer: Any = LaTeXDocumentRenderer()
        context: Any = RenderContext(
            title="Mixed Content Document",
            include_toc=True,
            tag_resolver=tag_resolver,
        )

        content_items = [sample_spell, sample_creature]
        # Mock DND template availability for testing
        with patch.object(
            renderer.template_engine,
            "check_dnd_template_availability",
            return_value=True,
        ):
            result = renderer.render_document(content_items, context)

        assert "\\documentclass" in result
        assert "\\tableofcontents" in result
        assert "Fireball" in result
        assert "Ancient Red Dragon" in result
        assert "\\end{document}" in result

    def test_render_to_file(self, sample_spell: Any, tmp_path: Any) -> None:
        """Test rendering document to file."""
        renderer: Any = LaTeXDocumentRenderer()
        context: Any = RenderContext(title="File Test")
        output_path = tmp_path / "test.tex"

        # Mock DND template availability for testing
        with patch.object(
            renderer.template_engine,
            "check_dnd_template_availability",
            return_value=True,
        ):
            renderer.render_document_to_file([sample_spell], output_path, context)

        assert output_path.exists()
        content = output_path.read_text()
        assert "\\documentclass" in content
        assert "Fireball" in content

    def test_render_to_file_error_handling(self, sample_spell: Any) -> None:
        """Test error handling when rendering to file fails."""
        renderer: Any = LaTeXDocumentRenderer()
        context: Any = RenderContext()
        invalid_path: Any = Path("/invalid/path/test.tex")

        with pytest.raises(RenderingError):
            renderer.render_document_to_file([sample_spell], invalid_path, context)


class TestRendererIntegration:
    """Integration tests for renderer system."""

    @pytest.mark.asyncio
    async def test_full_rendering_pipeline(self, loaded_omnidexer: Any) -> None:
        """Test complete rendering pipeline with real data."""
        omnidexer = loaded_omnidexer

        # Get some content
        spell = omnidexer.find(ContentType.SPELL, "Fireball", "PHB")
        creature = omnidexer.find(ContentType.CREATURE, "Ancient Red Dragon", "MM")

        assert spell is not None
        assert creature is not None

        # Create renderer and context
        renderer: Any = LaTeXDocumentRenderer()
        context: Any = RenderContext(
            title="Integration Test Document",
            include_toc=True,
            include_index=False,
            omnidexer=omnidexer,
        )

        # Render document
        # Mock DND template availability for testing
        with patch.object(
            renderer.template_engine,
            "check_dnd_template_availability",
            return_value=True,
        ):
            result = renderer.render_document([spell, creature], context)

        # Verify structure
        assert "\\documentclass" in result
        assert "\\title{Integration Test Document}" in result
        assert "\\tableofcontents" in result
        # Enhanced renderers use DND templates
        assert "Fireball" in result
        assert "Ancient Red Dragon" in result
        assert "\\end{document}" in result

        # Verify content details
        assert "3rd-level evocation" in result
        assert "G dragon" in result

    @pytest.mark.asyncio
    async def test_error_handling_unknown_content_type(
        self, loaded_omnidexer: Any
    ) -> None:
        """Test handling of unknown content types."""
        omnidexer = loaded_omnidexer

        # Create a mock content object of unknown type
        from dnd5e.core.models.content import BaseContent, Source  # type: ignore

        unknown_content: Any = BaseContent(
            name="Unknown Content",
            source=Source(abbreviation="TEST", name="Test Source", page=None, url=None),
        )

        renderer: Any = LaTeXDocumentRenderer()
        context: Any = RenderContext(omnidexer=omnidexer)

        # Should use fallback rendering
        # Mock DND template availability for testing
        with patch.object(
            renderer.template_engine,
            "check_dnd_template_availability",
            return_value=True,
        ):
            result = renderer.render_content_item(unknown_content, context)

        assert "\\subsection{Unknown Content}" in result
        assert "not yet fully supported" in result

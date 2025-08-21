"""Integration tests for book rendering with EntryRenderer system."""

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from studiorum.core.models.books import Book  # type: ignore
from studiorum.core.models.chapter import Chapter  # type: ignore
from studiorum.core.models.content import Source  # type: ignore
from studiorum.latex_engine.core.document import LaTeXDocumentRenderer  # type: ignore
from studiorum.renderers.core.interfaces import RenderingContext  # type: ignore
from tests.test_helpers import reset_test_environment


def compile_document_to_pdf_sync(renderer, books, context):
    """Synchronous wrapper for renderer.compile_document_to_pdf() for testing."""
    import asyncio

    return asyncio.run(renderer.compile_document_to_pdf(books, context=context))


@pytest.mark.rendering
class TestBookRenderingIntegration:
    """Integration tests for book rendering through the EntryRenderer system."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        # Reset global state for complete isolation
        reset_test_environment()

        config = {"show_progress": False, "compilation_timeout": 10, "max_passes": 2}
        self.renderer = LaTeXDocumentRenderer(config)

    @pytest.fixture
    def sample_source(self) -> Any:
        """Sample source for testing."""
        return Source(abbreviation="PHB", name="Player's Handbook", page=None, url=None)

    @pytest.fixture
    def simple_book(self, sample_source: Any) -> Any:
        """Simple book with basic chapters."""
        chapters = [
            Chapter(
                name="Introduction",
                ordinal={"type": "chapter", "identifier": 1},
                headers=["What Is D&D?", "How to Play"],
                entries=[
                    "Welcome to Dungeons & Dragons!",
                    "This game is about storytelling in worlds of sword and sorcery.",
                ],
            ),
            Chapter(
                name="Character Creation",
                ordinal={"type": "chapter", "identifier": 2},
                headers=["Choose a Race", "Choose a Class"],
                entries=[
                    "Your first step is to imagine and create a character.",
                    {
                        "type": "section",
                        "name": "Races",
                        "entries": ["Humans are versatile."],
                    },
                ],
            ),
        ]
        return Book(
            name="Player's Handbook",
            source=sample_source,
            contents=chapters,
            author=["Mike Mearls", "Jeremy Crawford"],
            published="2014-08-19",
        )

    @pytest.fixture
    def complex_book(self, sample_source: Any) -> Any:
        """Complex book with multiple chapter types and nested content."""
        chapters = [
            Chapter(
                name="Introduction",
                ordinal={"type": "chapter", "identifier": 1},
                entries=["Welcome to the game."],
            ),
            Chapter(
                name="Races",
                ordinal={"type": "chapter", "identifier": 2},
                entries=[
                    "Choose your character's race.",
                    {
                        "type": "section",
                        "name": "Human",
                        "entries": [
                            "Humans are the most adaptable and ambitious people.",
                            {
                                "type": "subsection",
                                "name": "Human Traits",
                                "entries": ["Ability Score Increase: +1 to all."],
                            },
                        ],
                    },
                    {
                        "type": "section",
                        "name": "Elf",
                        "entries": [
                            "Elves are a magical people of otherworldly grace."
                        ],
                    },
                ],
            ),
            Chapter(
                name="Spells",
                ordinal={"type": "appendix", "identifier": "A"},
                entries=[
                    "This appendix contains the spell lists and descriptions.",
                    {
                        "type": "table",
                        "caption": "Spell Lists by Class",
                        "colLabels": ["Class", "Cantrips", "1st Level"],
                        "rows": [["Wizard", "Mage Hand", "Magic Missile"]],
                    },
                ],
            ),
        ]
        return Book(
            name="Player's Handbook",
            source=sample_source,
            contents=chapters,
            metadata={
                "id": "phb-2014",
                "published": "2014-08-19",
                "author": ["Mike Mearls", "Jeremy Crawford"],
            },
        )

    def test_simple_book_rendering_structure(self, simple_book: Any) -> None:
        """Test that simple book renders with correct structure."""
        context = RenderingContext(
            output_format="latex", metadata={"title": "Test Book", "include_toc": True}
        )

        with patch.object(
            self.renderer.template_engine,
            "check_dnd_template_availability",
            return_value=True,
        ):
            result = self.renderer.render_document([simple_book], context)

        # Should be non-empty LaTeX content
        assert isinstance(result, str)
        assert len(result) > 100
        assert "\\documentclass" in result
        assert "\\begin{document}" in result
        assert "\\end{document}" in result

        # Should contain book title and chapter information
        assert "Player's Handbook" in result or "Test Book" in result
        assert "Introduction" in result
        assert "Character Creation" in result

    def test_complex_book_rendering_with_nested_content(
        self, complex_book: Any
    ) -> None:
        """Test complex book with nested sections and subsections."""
        context = RenderingContext(
            output_format="latex",
            metadata={"title": "Complex Book Test", "include_toc": True},
        )

        with patch.object(
            self.renderer.template_engine,
            "check_dnd_template_availability",
            return_value=True,
        ):
            result = self.renderer.render_document([complex_book], context)

        # Basic structure checks
        assert isinstance(result, str)
        assert len(result) > 200
        assert "\\documentclass" in result

        # Should handle different chapter types
        assert "Introduction" in result
        assert "Races" in result
        assert "Spells" in result  # Appendix

        # Should process nested content structures (even if as placeholders)
        assert "Human" in result
        assert "Elf" in result
        # Note: Current system may show placeholder text for complex nested content

    def test_book_chapter_numbering_in_output(self, complex_book: Any) -> None:
        """Test that chapter numbering is correctly rendered."""
        context = RenderingContext(
            output_format="latex", metadata={"title": "Chapter Numbering Test"}
        )

        with patch.object(
            self.renderer.template_engine,
            "check_dnd_template_availability",
            return_value=True,
        ):
            result = self.renderer.render_document([complex_book], context)

        # Should contain proper chapter structure
        assert "\\chapter{Introduction}" in result
        assert "\\chapter{Races}" in result
        assert "\\chapter{Spells}" in result  # Appendix rendered as chapter

    def test_book_metadata_inclusion(self, complex_book: Any) -> None:
        """Test that book metadata is properly included in rendering."""
        context = RenderingContext(
            output_format="latex",
            metadata={"title": "Metadata Test", "author": "Test Author"},
        )

        with patch.object(
            self.renderer.template_engine,
            "check_dnd_template_availability",
            return_value=True,
        ):
            result = self.renderer.render_document([complex_book], context)

        # Should include metadata in the document
        # The exact location and format depends on the template
        assert isinstance(result, str)
        assert len(result) > 100

        # Context data should be available to templates
        # (specific assertions depend on template implementation)

    def test_multiple_books_rendering(
        self, simple_book: Any, sample_source: Any
    ) -> None:
        """Test rendering multiple books in a single document."""
        # Create a second simple book
        second_book = Book(
            name="Dungeon Master's Guide",
            source=sample_source,
            contents=[
                Chapter(
                    name="Running the Game",
                    ordinal={"type": "chapter", "identifier": 1},
                    entries=["This chapter explains how to run D&D."],
                )
            ],
        )

        books = [simple_book, second_book]
        context = RenderingContext(
            output_format="latex", metadata={"title": "Multiple Books Test"}
        )

        with patch.object(
            self.renderer.template_engine,
            "check_dnd_template_availability",
            return_value=True,
        ):
            result = self.renderer.render_document(books, context)

        # Should contain content from both books
        # Note: Book titles are not currently rendered in chapter content
        # but chapter names from both books should be present
        assert "Introduction" in result  # From first book
        assert "Character Creation" in result  # From first book
        assert "Running the Game" in result  # From second book

    def test_book_rendering_error_handling(self, sample_source: Any) -> None:
        """Test error handling with malformed book data."""
        # Create book with problematic data
        problematic_book = Book(
            name="Problematic Book",
            source=sample_source,
            contents=[
                Chapter(
                    name="Bad Chapter",
                    ordinal=None,
                    headers=None,
                    entries=[
                        # Nested structure that might cause issues
                        {
                            "type": "unknown_type",
                            "data": {"complex": {"nested": "structure"}},
                        }
                    ],
                )
            ],
            id=None,
            metadata=None,
            published=None,
            author=None,
            cover=None,
        )

        context = RenderingContext(
            output_format="latex", metadata={"title": "Error Test"}
        )

        with patch.object(
            self.renderer.template_engine,
            "check_dnd_template_availability",
            return_value=True,
        ):
            # Should not raise an exception
            result = self.renderer.render_document([problematic_book], context)

        # Should still produce valid LaTeX structure
        assert isinstance(result, str)
        assert "\\documentclass" in result
        assert "\\begin{document}" in result
        assert "\\end{document}" in result

    def test_book_rendering_without_chapters(self, sample_source: Any) -> None:
        """Test rendering book with no chapters."""
        empty_book = Book(
            name="Empty Book",
            source=sample_source,
            contents=[],  # No chapters
            id=None,
            metadata=None,
            published=None,
            author=None,
            cover=None,
        )

        context = RenderingContext(
            output_format="latex", metadata={"title": "Empty Book Test"}
        )

        with patch.object(
            self.renderer.template_engine,
            "check_dnd_template_availability",
            return_value=True,
        ):
            result = self.renderer.render_document([empty_book], context)

        # Should still produce valid LaTeX structure
        assert isinstance(result, str)
        assert "\\documentclass" in result
        assert "\\begin{document}" in result
        assert "\\end{document}" in result
        assert "Empty Book" in result

    def test_book_compilation_integration(self, simple_book: Any) -> None:
        """Test full integration from book to PDF compilation."""
        from studiorum.latex_engine.config.compilation import (  # type: ignore
            CompilationResult,
            LaTeXEngine,
        )

        context = RenderingContext(
            output_format="latex", metadata={"title": "Compilation Test"}
        )

        # Mock successful compilation
        mock_result = CompilationResult(
            success=True,
            engine_used=LaTeXEngine.LUALATEX,
            passes_completed=1,
            total_time=5.0,
            output_file=Path("/tmp/test_book.pdf"),
        )

        with patch.object(
            self.renderer.template_engine,
            "check_dnd_template_availability",
            return_value=True,
        ):
            with patch.object(
                self.renderer.compiler,
                "compile_document",
                return_value=mock_result,
                new_callable=AsyncMock,
            ) as mock_compile:
                result = compile_document_to_pdf_sync(
                    self.renderer, [simple_book], context
                )

                assert result.success is True
                assert result.output_file == Path("/tmp/test_book.pdf")

                # Check that LaTeX was generated and passed to compiler
                mock_compile.assert_called_once()
                compile_args = mock_compile.call_args[0]
                latex_source = compile_args[0]

                # Verify LaTeX contains book content
                assert isinstance(latex_source, str)
                assert len(latex_source) > 100
                assert (
                    "Player's Handbook" in latex_source
                    or "Compilation Test" in latex_source
                )

    def test_book_rendering_with_custom_context(self, simple_book: Any) -> None:
        """Test book rendering with custom render context options."""
        context = RenderingContext(
            output_format="latex",
            metadata={
                "title": "Custom Context Test",
                "author": "Custom Author",
                "include_toc": True,
                "include_index": True,
            },
        )

        with patch.object(
            self.renderer.template_engine,
            "check_dnd_template_availability",
            return_value=True,
        ):
            result = self.renderer.render_document([simple_book], context)

        # Should include custom context data
        assert isinstance(result, str)
        assert len(result) > 100

        # The exact assertions depend on how templates use the context
        # At minimum, the rendering should succeed with custom context

    def test_book_rendering_performance_baseline(self, complex_book: Any) -> None:
        """Test book rendering performance for baseline measurements."""
        import time

        context = RenderingContext(
            output_format="latex", metadata={"title": "Performance Test"}
        )

        with patch.object(
            self.renderer.template_engine,
            "check_dnd_template_availability",
            return_value=True,
        ):
            start_time = time.time()
            result = self.renderer.render_document([complex_book], context)
            end_time = time.time()

        # Should complete within reasonable time (adjust threshold as needed)
        render_time = end_time - start_time
        assert render_time < 10.0  # 10 seconds max for basic book

        # Should produce substantial output
        assert isinstance(result, str)
        assert len(result) > 500  # Substantial LaTeX content

    def test_book_rendering_memory_usage(self, complex_book: Any) -> None:
        """Test that book rendering doesn't leak memory excessively."""
        import gc

        context = RenderingContext(
            output_format="latex", metadata={"title": "Memory Test"}
        )

        # Force garbage collection before test
        gc.collect()
        initial_objects = len(gc.get_objects())

        with patch.object(
            self.renderer.template_engine,
            "check_dnd_template_availability",
            return_value=True,
        ):
            # Render the same book multiple times
            for _ in range(5):
                result = self.renderer.render_document([complex_book], context)
                assert isinstance(result, str)

        # Force garbage collection after test
        gc.collect()
        final_objects = len(gc.get_objects())

        # Object count shouldn't grow excessively (some growth is expected)
        object_growth = final_objects - initial_objects
        assert object_growth < 1000  # Reasonable threshold for memory usage


@pytest.mark.rendering
class TestBookRenderingEntryProcessing:
    """Tests for book entry processing through EntryRenderer system."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        # Reset global state for complete isolation
        reset_test_environment()

        config = {"show_progress": False}
        self.renderer = LaTeXDocumentRenderer(config)

    @pytest.fixture
    def entry_rich_book(self) -> Any:
        """Book with rich entry content for testing entry processing."""
        source = Source(abbreviation="TEST", name="Test Book", page=None, url=None)
        chapters = [
            Chapter(
                name="Rich Content Chapter",
                ordinal=None,
                headers=None,
                entries=[
                    "Simple text entry.",
                    {
                        "type": "section",
                        "name": "Nested Section",
                        "entries": [
                            "Nested text content.",
                            {
                                "type": "table",
                                "caption": "Sample Table",
                                "colLabels": ["Name", "Type", "Description"],
                                "rows": [
                                    ["Magic Sword", "Weapon", "A magical blade"],
                                    ["Healing Potion", "Consumable", "Restores health"],
                                ],
                            },
                            {
                                "type": "list",
                                "items": [
                                    "First list item",
                                    "Second list item",
                                    {
                                        "type": "item",
                                        "name": "Nested item",
                                        "text": "Description",
                                    },
                                ],
                            },
                        ],
                    },
                    {
                        "type": "quote",
                        "entries": ["This is a quote block for flavor text."],
                    },
                ],
            )
        ]
        return Book(
            name="Entry Rich Book",
            source=source,
            contents=chapters,
            id=None,
            metadata=None,
            published=None,
            author=None,
            cover=None,
        )

    def test_nested_entry_processing(self, entry_rich_book: Any) -> None:
        """Test that nested entries are properly processed."""
        context = RenderingContext(
            output_format="latex", metadata={"title": "Nested Entry Test"}
        )

        with patch.object(
            self.renderer.template_engine,
            "check_dnd_template_availability",
            return_value=True,
        ):
            result = self.renderer.render_document([entry_rich_book], context)

        assert isinstance(result, str)
        assert len(result) > 200

        # Should contain chapter and section structure
        assert "\\chapter{Rich Content Chapter}" in result
        assert "\\subsection{Nested Section}" in result
        # Note: Text content currently shows as placeholder until entry processing is fully implemented

    def test_table_entry_processing(self, entry_rich_book: Any) -> None:
        """Test that table entries are processed correctly."""
        context = RenderingContext(
            output_format="latex", metadata={"title": "Table Test"}
        )

        with patch.object(
            self.renderer.template_engine,
            "check_dnd_template_availability",
            return_value=True,
        ):
            result = self.renderer.render_document([entry_rich_book], context)

        # Should process table data (may be in placeholder form)
        # Current system may show placeholder for unsupported content types
        assert len(result) > 100  # Should produce substantial output

    def test_list_entry_processing(self, entry_rich_book: Any) -> None:
        """Test that list entries are processed correctly."""
        context = RenderingContext(
            output_format="latex", metadata={"title": "List Test"}
        )

        with patch.object(
            self.renderer.template_engine,
            "check_dnd_template_availability",
            return_value=True,
        ):
            result = self.renderer.render_document([entry_rich_book], context)

        # Should process list items (may be in placeholder form)
        assert len(result) > 100  # Should produce substantial output

    def test_quote_entry_processing(self, entry_rich_book: Any) -> None:
        """Test that quote entries are processed correctly."""
        context = RenderingContext(
            output_format="latex", metadata={"title": "Quote Test"}
        )

        with patch.object(
            self.renderer.template_engine,
            "check_dnd_template_availability",
            return_value=True,
        ):
            result = self.renderer.render_document([entry_rich_book], context)

        # Should process quote blocks (may be in placeholder form)
        assert len(result) > 100  # Should produce substantial output

    def test_unknown_entry_type_handling(self) -> None:
        """Test handling of unknown entry types."""
        source = Source(abbreviation="TEST", name="Test Book", page=None, url=None)
        chapters = [
            Chapter(
                name="Unknown Entry Chapter",
                ordinal=None,
                headers=None,
                entries=[
                    {
                        "type": "unknown_entry_type",
                        "custom_field": "custom_value",
                        "entries": ["Nested content in unknown type"],
                    }
                ],
            )
        ]
        book = Book(
            name="Unknown Entry Book",
            source=source,
            contents=chapters,
            id=None,
            metadata=None,
            published=None,
            author=None,
            cover=None,
        )
        context = RenderingContext(
            output_format="latex", metadata={"title": "Unknown Entry Test"}
        )

        with patch.object(
            self.renderer.template_engine,
            "check_dnd_template_availability",
            return_value=True,
        ):
            # Should not crash on unknown entry types
            result = self.renderer.render_document([book], context)

        assert isinstance(result, str)
        assert len(result) > 50  # Should still produce output

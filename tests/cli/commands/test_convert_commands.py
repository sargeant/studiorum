"""Comprehensive tests for convert CLI commands."""

import json
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest
from typer.testing import CliRunner

from dnd5e.cli.commands.convert import _compile_pdf, app
from dnd5e.core.indexer.tag_resolver import TagResolver
from dnd5e.core.loaders.omnidexer import Omnidexer
from dnd5e.core.models.books import Book
from dnd5e.core.models.content import Source


class TestConvertAdventureCommand:
    """Test adventure conversion command."""

    def setup_method(self):
        """Set up test fixtures."""
        # Reset global state for test isolation using service container
        from dnd5e.core.cache import CacheManager
        from dnd5e.core.container import reset_all_services

        CacheManager.reset()
        reset_all_services()

        self.runner = CliRunner()
        self.mock_adventure_data = {
            "adventure": [
                {
                    "name": "Test Adventure",
                    "source": {"abbreviation": "TEST", "name": "Test Source"},
                    "id": "test",
                    "metadata": {},
                    "published": None,
                    "author": None,
                    "cover": None,
                    "contents": [],
                }
            ]
        }

    @patch("dnd5e.cli.commands.convert.get_omnidexer")
    @patch("dnd5e.cli.commands.convert.get_tag_resolver")
    @patch("dnd5e.cli.commands.convert.LaTeXDocumentRenderer")
    @patch("dnd5e.cli.commands.convert.display_manager")
    @patch("aiofiles.open")
    @patch("pathlib.Path.mkdir")
    def test_convert_adventure_with_file_path(
        self,
        mock_mkdir,
        mock_aiofiles_open,
        mock_display,
        mock_renderer_class,
        mock_tag_resolver,
        mock_omnidexer,
    ):
        """Test converting adventure from file path."""
        # Mock file operations
        mock_file = AsyncMock()
        mock_file.read.return_value = json.dumps(self.mock_adventure_data)
        mock_aiofiles_open.return_value.__aenter__.return_value = mock_file

        # Mock dependencies - create a mock that passes isinstance checks
        mock_omnidexer_instance = Mock(spec=Omnidexer)
        mock_omnidexer.return_value = mock_omnidexer_instance
        mock_tag_resolver.return_value = TagResolver(omnidexer=None)

        # Mock renderer
        mock_renderer = Mock()
        mock_renderer.render_document.return_value = (
            "\\documentclass{article}\\begin{document}Test\\end{document}"
        )
        mock_renderer_class.return_value = mock_renderer

        # Mock display manager
        mock_display.progress.return_value.__enter__ = Mock()
        mock_display.progress.return_value.__exit__ = Mock()
        mock_display.add_task.return_value = "task_id"
        mock_display.update_task = Mock()

        # Create temporary file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(self.mock_adventure_data, f)
            file_path = f.name

        try:
            # Test command
            result = self.runner.invoke(app, ["adventure", file_path])

            # Verify success
            assert result.exit_code == 0
            assert "Adventure converted" in result.stdout

            # Verify file operations
            mock_aiofiles_open.assert_called()
            mock_mkdir.assert_called()

        finally:
            Path(file_path).unlink()

    @patch("dnd5e.cli.commands.convert.get_omnidexer")
    @patch("dnd5e.cli.commands.convert.get_tag_resolver")
    @patch("dnd5e.cli.commands.convert.ContentResolver")
    @patch("dnd5e.cli.commands.convert.LaTeXDocumentRenderer")
    @patch("dnd5e.cli.commands.convert.display_manager")
    @patch("aiofiles.open")
    @patch("pathlib.Path.mkdir")
    def test_convert_adventure_with_abbreviation(
        self,
        mock_mkdir,
        mock_aiofiles_open,
        mock_display,
        mock_renderer_class,
        mock_resolver_class,
        mock_tag_resolver,
        mock_omnidexer,
    ):
        """Test converting adventure from abbreviation."""
        # Mock file operations
        mock_file = AsyncMock()
        mock_aiofiles_open.return_value.__aenter__.return_value = mock_file

        # Mock dependencies
        mock_omnidexer.return_value = Omnidexer()
        mock_tag_resolver.return_value = TagResolver(omnidexer=None)

        # Mock resolver
        mock_resolver = Mock()

        # Create a proper Adventure instance instead of Mock
        from dnd5e.core.models.adventures import Adventure
        from dnd5e.core.models.content import Source

        mock_adventure = Adventure(
            name="Curse of Strahd",
            source=Source(abbreviation="CoS", name="Curse of Strahd"),
        )

        from dnd5e.core.resolvers.content_resolver import (
            ContentResolutionResult,
            ResolutionStatus,
        )

        mock_result = ContentResolutionResult(
            status=ResolutionStatus.EXACT_MATCH, content=mock_adventure, query="cos"
        )
        # Make the mock async
        mock_resolver.resolve_adventure = AsyncMock(return_value=mock_result)
        mock_resolver_class.return_value = mock_resolver

        # Mock renderer
        mock_renderer = Mock()
        mock_renderer.render_document.return_value = (
            "\\documentclass{article}\\begin{document}Test\\end{document}"
        )
        mock_renderer_class.return_value = mock_renderer

        # Mock display manager
        mock_display.progress.return_value.__enter__ = Mock()
        mock_display.progress.return_value.__exit__ = Mock()
        mock_display.add_task.return_value = "task_id"
        mock_display.update_task = Mock()

        # Test command
        result = self.runner.invoke(app, ["adventure", "cos"])

        # Verify success
        assert result.exit_code == 0
        assert "Adventure converted" in result.stdout

    def test_convert_adventure_nonexistent_file(self):
        """Test error handling for nonexistent file."""
        result = self.runner.invoke(app, ["adventure", "/nonexistent/file.json"])

        # Should exit with error
        assert result.exit_code == 1
        assert "Error:" in result.stdout

    @patch("dnd5e.cli.commands.convert.get_omnidexer")
    @patch("dnd5e.cli.commands.convert.ContentResolver")
    def test_convert_adventure_resolution_failure(
        self, mock_resolver_class, mock_omnidexer
    ):
        """Test error handling when content resolution fails."""
        # Mock dependencies
        mock_omnidexer.return_value = Omnidexer()

        # Mock failed resolution
        mock_resolver = Mock()
        from dnd5e.core.resolvers.content_resolver import (
            ContentResolutionResult,
            ResolutionStatus,
        )

        mock_result = ContentResolutionResult(
            status=ResolutionStatus.NO_MATCH, query="nonexistent"
        )
        # Make the mock async
        mock_resolver.resolve_adventure = AsyncMock(return_value=mock_result)
        mock_resolver_class.return_value = mock_resolver

        # Test command
        result = self.runner.invoke(app, ["adventure", "nonexistent"])

        # Should exit with error
        assert result.exit_code == 1
        assert "Error:" in result.stdout

    @patch("dnd5e.cli.commands.convert.get_omnidexer")
    @patch("dnd5e.cli.commands.convert.get_tag_resolver")
    @patch("dnd5e.cli.commands.convert.LaTeXDocumentRenderer")
    @patch("dnd5e.cli.commands.convert.display_manager")
    @patch("aiofiles.open")
    @patch("pathlib.Path.mkdir")
    @patch("dnd5e.cli.commands.convert._compile_pdf")
    def test_convert_adventure_with_pdf_compilation(
        self,
        mock_compile_pdf,
        mock_mkdir,
        mock_aiofiles_open,
        mock_display,
        mock_renderer_class,
        mock_tag_resolver,
        mock_omnidexer,
    ):
        """Test adventure conversion with PDF compilation."""
        # Mock file operations
        mock_file = AsyncMock()
        mock_file.read.return_value = json.dumps(self.mock_adventure_data)
        mock_aiofiles_open.return_value.__aenter__.return_value = mock_file

        # Mock dependencies
        mock_omnidexer.return_value = Omnidexer()
        mock_tag_resolver.return_value = TagResolver(omnidexer=None)

        # Mock renderer
        mock_renderer = Mock()
        mock_renderer.render_document.return_value = (
            "\\documentclass{article}\\begin{document}Test\\end{document}"
        )
        mock_renderer_class.return_value = mock_renderer

        # Mock display manager
        mock_display.progress.return_value.__enter__ = Mock()
        mock_display.progress.return_value.__exit__ = Mock()
        mock_display.add_task.return_value = "task_id"
        mock_display.update_task = Mock()

        # Mock PDF compilation
        mock_compile_pdf.return_value = None

        # Create temporary file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(self.mock_adventure_data, f)
            file_path = f.name

        try:
            # Test command with PDF flag
            result = self.runner.invoke(app, ["adventure", file_path, "--pdf"])

            # Verify success and PDF compilation called
            assert result.exit_code == 0
            mock_compile_pdf.assert_called_once()

        finally:
            Path(file_path).unlink()


class TestConvertBookCommand:
    """Test book conversion command."""

    def setup_method(self):
        """Set up test fixtures."""
        # Reset global state for test isolation using service container
        from dnd5e.core.cache import CacheManager
        from dnd5e.core.container import reset_all_services

        CacheManager.reset()
        reset_all_services()

        self.runner = CliRunner()
        self.mock_book_data = {
            "data": [
                {
                    "type": "section",
                    "name": "Chapter 1",
                    "entries": ["This is chapter 1 content."],
                }
            ]
        }

    @patch("dnd5e.cli.commands.convert.get_omnidexer")
    @patch("dnd5e.cli.commands.convert.get_tag_resolver")
    @patch("dnd5e.cli.commands.convert.LaTeXDocumentRenderer")
    @patch("dnd5e.cli.commands.convert.display_manager")
    @patch("aiofiles.open")
    @patch("pathlib.Path.mkdir")
    def test_convert_book_with_file_path(
        self,
        mock_mkdir,
        mock_aiofiles_open,
        mock_display,
        mock_renderer_class,
        mock_tag_resolver,
        mock_omnidexer,
    ):
        """Test converting book from file path."""
        # Mock file operations
        mock_file = AsyncMock()
        mock_file.read.return_value = json.dumps(self.mock_book_data)
        mock_aiofiles_open.return_value.__aenter__.return_value = mock_file

        # Mock dependencies
        mock_omnidexer.return_value = Omnidexer()
        mock_tag_resolver.return_value = TagResolver(omnidexer=None)

        # Mock renderer
        mock_renderer = Mock()
        mock_renderer.render_document.return_value = (
            "\\documentclass{article}\\begin{document}Test\\end{document}"
        )
        mock_renderer_class.return_value = mock_renderer

        # Mock display manager
        mock_display.progress.return_value.__enter__ = Mock()
        mock_display.progress.return_value.__exit__ = Mock()
        mock_display.add_task.return_value = "task_id"
        mock_display.update_task = Mock()

        # Create temporary file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(self.mock_book_data, f)
            file_path = f.name

        try:
            # Test command
            result = self.runner.invoke(app, ["book", file_path])

            # Verify success
            assert result.exit_code == 0
            assert "Book converted" in result.stdout

        finally:
            Path(file_path).unlink()

    @patch("dnd5e.cli.commands.convert.get_omnidexer")
    @patch("dnd5e.cli.commands.convert.get_tag_resolver")
    @patch("dnd5e.cli.commands.convert.LaTeXDocumentRenderer")
    @patch("dnd5e.cli.commands.convert.display_manager")
    @patch("aiofiles.open")
    @patch("pathlib.Path.mkdir")
    def test_convert_book_with_custom_options(
        self,
        mock_mkdir,
        mock_aiofiles_open,
        mock_display,
        mock_renderer_class,
        mock_tag_resolver,
        mock_omnidexer,
    ):
        """Test book conversion with custom options."""
        # Mock file operations
        mock_file = AsyncMock()
        mock_file.read.return_value = json.dumps(self.mock_book_data)
        mock_aiofiles_open.return_value.__aenter__.return_value = mock_file

        # Mock dependencies
        mock_omnidexer.return_value = Omnidexer()
        mock_tag_resolver.return_value = TagResolver(omnidexer=None)

        # Mock renderer
        mock_renderer = Mock()
        mock_renderer.render_document.return_value = (
            "\\documentclass{article}\\begin{document}Test\\end{document}"
        )
        mock_renderer_class.return_value = mock_renderer

        # Mock display manager
        mock_display.progress.return_value.__enter__ = Mock()
        mock_display.progress.return_value.__exit__ = Mock()
        mock_display.add_task.return_value = "task_id"
        mock_display.update_task = Mock()

        # Create temporary file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(self.mock_book_data, f)
            file_path = f.name

        try:
            # Test command with options
            result = self.runner.invoke(
                app,
                [
                    "book",
                    file_path,
                    "--title",
                    "Custom Title",
                    "--images",
                    "--no-index",
                    "--output",
                    "custom_output.tex",
                ],
            )

            # Verify success
            assert result.exit_code == 0
            assert "Book converted" in result.stdout

        finally:
            Path(file_path).unlink()


class TestConvertSupplementCommand:
    """Test supplement conversion command."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
        self.mock_supplement_data = {
            "spell": [
                {
                    "name": "Test Spell",
                    "source": {"abbreviation": "TEST", "name": "Test Source"},
                    "level": 1,
                    "school": "A",
                    "time": [{"number": 1, "unit": "action"}],
                    "range": {
                        "type": "point",
                        "distance": {"type": "feet", "amount": 30},
                    },
                    "components": {"v": True},
                    "duration": [{"type": "instant"}],
                    "entries": ["Test spell description"],
                }
            ]
        }

    @patch("dnd5e.cli.commands.convert.get_omnidexer")
    @patch("dnd5e.cli.commands.convert.get_tag_resolver")
    @patch("dnd5e.cli.commands.convert.LaTeXDocumentRenderer")
    @patch("dnd5e.cli.commands.convert.display_manager")
    @patch("aiofiles.open")
    @patch("pathlib.Path.mkdir")
    def test_convert_supplement_with_spells(
        self,
        mock_mkdir,
        mock_aiofiles_open,
        mock_display,
        mock_renderer_class,
        mock_tag_resolver,
        mock_omnidexer,
    ):
        """Test converting supplement with spells."""
        # Mock file operations
        mock_file = AsyncMock()
        mock_file.read.return_value = json.dumps(self.mock_supplement_data)
        mock_aiofiles_open.return_value.__aenter__.return_value = mock_file

        # Mock dependencies
        mock_omnidexer.return_value = Omnidexer()
        mock_tag_resolver.return_value = TagResolver(omnidexer=None)

        # Mock renderer
        mock_renderer = Mock()
        mock_renderer.render_document.return_value = (
            "\\documentclass{article}\\begin{document}Test\\end{document}"
        )
        mock_renderer_class.return_value = mock_renderer

        # Mock display manager
        mock_display.progress.return_value.__enter__ = Mock()
        mock_display.progress.return_value.__exit__ = Mock()
        mock_display.add_task.return_value = "task_id"
        mock_display.update_task = Mock()

        # Create temporary file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(self.mock_supplement_data, f)
            file_path = f.name

        try:
            # Test command
            result = self.runner.invoke(app, ["supplement", file_path])

            # Verify success
            assert result.exit_code == 0
            assert "Supplement converted" in result.stdout

        finally:
            Path(file_path).unlink()

    def test_convert_supplement_nonexistent_file(self):
        """Test error handling for nonexistent supplement file."""
        result = self.runner.invoke(app, ["supplement", "/nonexistent/file.json"])

        # Should exit with error
        assert result.exit_code == 1
        assert "Error:" in result.stdout

    @patch("dnd5e.cli.commands.convert.get_omnidexer")
    @patch("dnd5e.cli.commands.convert.get_tag_resolver")
    @patch("dnd5e.cli.commands.convert.display_manager")
    @patch("aiofiles.open")
    def test_convert_supplement_empty_content(
        self,
        mock_aiofiles_open,
        mock_display,
        mock_tag_resolver,
        mock_omnidexer,
    ):
        """Test error handling for supplement with no valid content."""
        # Mock file operations - empty content
        mock_file = AsyncMock()
        mock_file.read.return_value = json.dumps({"unknown": []})
        mock_aiofiles_open.return_value.__aenter__.return_value = mock_file

        # Mock dependencies
        mock_omnidexer.return_value = Omnidexer()
        mock_tag_resolver.return_value = TagResolver(omnidexer=None)

        # Mock display manager
        mock_display.progress.return_value.__enter__ = Mock()
        mock_display.progress.return_value.__exit__ = Mock()
        mock_display.add_task.return_value = "task_id"
        mock_display.update_task = Mock()

        # Create temporary file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"unknown": []}, f)
            file_path = f.name

        try:
            # Test command
            result = self.runner.invoke(app, ["supplement", file_path])

            # Should exit with error
            assert result.exit_code == 1
            assert "Error:" in result.stdout

        finally:
            Path(file_path).unlink()


class TestPDFCompilation:
    """Test PDF compilation functionality."""

    @pytest.mark.asyncio
    @patch("aiofiles.open")
    @patch("dnd5e.cli.commands.convert._create_latex_compiler")
    @patch("dnd5e.cli.commands.convert.display_manager")
    async def test_compile_pdf_success(
        self, mock_display, mock_create_compiler, mock_aiofiles_open
    ):
        """Test successful PDF compilation."""
        # Mock file reading
        mock_file = AsyncMock()
        mock_file.read.return_value = (
            "\\documentclass{article}\\begin{document}Test\\end{document}"
        )
        mock_aiofiles_open.return_value.__aenter__.return_value = mock_file

        # Mock LaTeX compiler
        mock_compiler = Mock()
        mock_result = Mock()
        mock_result.success = True
        mock_result.output_file = Path("/tmp/test.pdf")
        mock_compiler.compile_document.return_value = mock_result
        mock_create_compiler.return_value = mock_compiler

        # Mock display manager
        mock_display.progress.return_value.__enter__ = Mock()
        mock_display.progress.return_value.__exit__ = Mock()
        mock_display.add_task.return_value = "task_id"
        mock_display.update_task = Mock()

        # Test compilation
        latex_path = Path("/tmp/test.tex")
        await _compile_pdf(latex_path)

        # Verify LaTeX compiler was used correctly
        mock_create_compiler.assert_called_once()
        mock_compiler.compile_document.assert_called_once()

    @pytest.mark.asyncio
    @patch("aiofiles.open")
    @patch("dnd5e.cli.commands.convert._create_latex_compiler")
    @patch("dnd5e.cli.commands.convert.display_manager")
    async def test_compile_pdf_failure(
        self, mock_display, mock_create_compiler, mock_aiofiles_open
    ):
        """Test PDF compilation failure handling."""
        # Mock file reading
        mock_file = AsyncMock()
        mock_file.read.return_value = (
            "\\documentclass{article}\\begin{document}Test\\end{document}"
        )
        mock_aiofiles_open.return_value.__aenter__.return_value = mock_file

        # Mock failed LaTeX compiler
        mock_compiler = Mock()
        mock_compiler.compile_document.side_effect = Exception("LaTeX error")
        mock_create_compiler.return_value = mock_compiler

        # Mock display manager
        mock_display.progress.return_value.__enter__ = Mock()
        mock_display.progress.return_value.__exit__ = Mock()
        mock_display.add_task.return_value = "task_id"
        mock_display.update_task = Mock()

        # Test compilation - should not raise exception
        latex_path = Path("/tmp/test.tex")
        await _compile_pdf(latex_path)

        # Verify LaTeX compiler was called
        mock_create_compiler.assert_called_once()
        mock_compiler.compile_document.assert_called_once()

    @pytest.mark.asyncio
    @patch("aiofiles.open")
    @patch("dnd5e.cli.commands.convert._create_latex_compiler")
    @patch("dnd5e.cli.commands.convert.display_manager")
    async def test_compile_pdf_latex_not_found(
        self, mock_display, mock_create_compiler, mock_aiofiles_open
    ):
        """Test handling when LaTeX engine is not installed."""
        # Mock file reading
        mock_file = AsyncMock()
        mock_file.read.return_value = (
            "\\documentclass{article}\\begin{document}Test\\end{document}"
        )
        mock_aiofiles_open.return_value.__aenter__.return_value = mock_file

        # Mock FileNotFoundError (LaTeX engine not found)
        mock_compiler = Mock()
        mock_compiler.compile_document.side_effect = FileNotFoundError(
            "lualatex not found"
        )
        mock_create_compiler.return_value = mock_compiler

        # Mock display manager
        mock_display.progress.return_value.__enter__ = Mock()
        mock_display.progress.return_value.__exit__ = Mock()
        mock_display.add_task.return_value = "task_id"
        mock_display.update_task = Mock()

        # Test compilation - should not raise exception
        latex_path = Path("/tmp/test.tex")
        await _compile_pdf(latex_path)

        # Verify LaTeX compiler was called
        mock_create_compiler.assert_called_once()
        mock_compiler.compile_document.assert_called_once()


class TestErrorHandlingPaths:
    """Test error handling in various scenarios."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    @patch("dnd5e.cli.commands.convert.get_omnidexer")
    @patch("dnd5e.cli.commands.convert.get_tag_resolver")
    @patch("aiofiles.open")
    def test_json_decode_error(
        self, mock_aiofiles_open, mock_tag_resolver, mock_omnidexer
    ):
        """Test handling of invalid JSON files."""
        # Mock file operations - invalid JSON
        mock_file = AsyncMock()
        mock_file.read.return_value = "invalid json content {"
        mock_aiofiles_open.return_value.__aenter__.return_value = mock_file

        # Mock dependencies
        mock_omnidexer.return_value = Omnidexer()
        mock_tag_resolver.return_value = TagResolver(omnidexer=None)

        # Create temporary file with invalid JSON
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("invalid json content {")
            file_path = f.name

        try:
            # Test command
            result = self.runner.invoke(app, ["adventure", file_path])

            # Should exit with error
            assert result.exit_code == 1
            assert "Error:" in result.stdout

        finally:
            Path(file_path).unlink()

    @patch("dnd5e.cli.commands.convert.get_omnidexer")
    @patch("dnd5e.cli.commands.convert.get_tag_resolver")
    @patch("dnd5e.cli.commands.convert.LaTeXDocumentRenderer")
    @patch("aiofiles.open")
    def test_renderer_exception(
        self, mock_aiofiles_open, mock_renderer_class, mock_tag_resolver, mock_omnidexer
    ):
        """Test handling of renderer exceptions."""
        # Mock file operations
        mock_file = AsyncMock()
        mock_file.read.return_value = json.dumps(
            {
                "adventure": [
                    {
                        "name": "Test Adventure",
                        "source": {"abbreviation": "TEST", "name": "Test Source"},
                        "id": "test",
                        "metadata": {},
                        "published": None,
                        "author": None,
                        "cover": None,
                        "contents": [],
                    }
                ]
            }
        )
        mock_aiofiles_open.return_value.__aenter__.return_value = mock_file

        # Mock dependencies
        mock_omnidexer.return_value = Omnidexer()
        mock_tag_resolver.return_value = TagResolver(omnidexer=None)

        # Mock renderer to raise exception
        mock_renderer = Mock()
        mock_renderer.render_document.side_effect = Exception("Renderer error")
        mock_renderer_class.return_value = mock_renderer

        # Create temporary file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"test": "data"}, f)
            file_path = f.name

        try:
            # Test command
            result = self.runner.invoke(app, ["adventure", file_path])

            # Should exit with error
            assert result.exit_code == 1
            assert "Error:" in result.stdout

        finally:
            Path(file_path).unlink()


class TestSpecialCases:
    """Test special cases and edge conditions."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    @patch("dnd5e.cli.commands.convert.get_omnidexer")
    @patch("dnd5e.cli.commands.convert.get_tag_resolver")
    @patch("dnd5e.cli.commands.convert.ContentResolver")
    @patch("dnd5e.cli.commands.convert.LaTeXDocumentRenderer")
    @patch("dnd5e.cli.commands.convert.display_manager")
    @patch("aiofiles.open")
    @patch("pathlib.Path.mkdir")
    def test_phb_abbreviation_fallback(
        self,
        mock_mkdir,
        mock_aiofiles_open,
        mock_display,
        mock_renderer_class,
        mock_resolver_class,
        mock_tag_resolver,
        mock_omnidexer,
    ):
        """Test PHB abbreviation fallback to content resolver."""
        # Mock file operations
        mock_file = AsyncMock()
        mock_file.read.return_value = json.dumps(
            {
                "data": [
                    {
                        "type": "section",
                        "name": "Chapter 1",
                        "entries": ["Content"],
                    }
                ]
            }
        )
        mock_aiofiles_open.return_value.__aenter__.return_value = mock_file

        # Mock dependencies
        mock_omnidexer.return_value = Omnidexer()
        mock_tag_resolver.return_value = TagResolver(omnidexer=None)

        # Mock resolver with successful book resolution
        mock_resolver = Mock()
        # Create a proper Book instance instead of Mock
        test_source = Source(
            abbreviation="PHB", name="Player's Handbook", url="https://example.com"
        )
        mock_book = Book(name="Player's Handbook", source=test_source, data=[])

        from dnd5e.core.resolvers.content_resolver import (
            ContentResolutionResult,
            ResolutionStatus,
        )

        mock_result = ContentResolutionResult(
            status=ResolutionStatus.EXACT_MATCH, content=mock_book, query="phb"
        )
        # Make the mock async
        mock_resolver.resolve_book = AsyncMock(return_value=mock_result)
        mock_resolver_class.return_value = mock_resolver

        # Mock renderer
        mock_renderer = Mock()
        mock_renderer.render_document.return_value = (
            "\\documentclass{article}\\begin{document}Test\\end{document}"
        )
        mock_renderer_class.return_value = mock_renderer

        # Mock display manager
        mock_display.progress.return_value.__enter__ = Mock()
        mock_display.progress.return_value.__exit__ = Mock()
        mock_display.add_task.return_value = "task_id"
        mock_display.update_task = Mock()

        # Test PHB abbreviation (assuming special file doesn't exist)
        result = self.runner.invoke(app, ["book", "phb"])

        # Should succeed via resolver fallback
        assert result.exit_code == 0


class TestLaTeXDocumentOptions:
    """Test LaTeX document class options in CLI commands."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
        self.mock_adventure_data = {
            "adventure": [
                {
                    "name": "Test Adventure",
                    "source": {"abbreviation": "TEST", "name": "Test Source"},
                    "id": "test",
                    "metadata": {},
                    "published": None,
                    "author": None,
                    "cover": None,
                    "contents": [],
                }
            ]
        }

    @patch("dnd5e.cli.commands.convert.get_omnidexer")
    @patch("dnd5e.cli.commands.convert.get_tag_resolver")
    @patch("dnd5e.cli.commands.convert.LaTeXDocumentRenderer")
    @patch("dnd5e.cli.commands.convert.display_manager")
    @patch("aiofiles.open")
    @patch("pathlib.Path.mkdir")
    def test_adventure_with_latex_options(
        self,
        mock_mkdir,
        mock_aiofiles_open,
        mock_display,
        mock_renderer_class,
        mock_tag_resolver,
        mock_omnidexer,
    ):
        """Test adventure command with LaTeX document options."""
        # Mock file operations
        mock_file = AsyncMock()
        mock_file.read.return_value = json.dumps(self.mock_adventure_data)
        mock_aiofiles_open.return_value.__aenter__.return_value = mock_file

        # Mock dependencies
        mock_omnidexer.return_value = Omnidexer()
        mock_tag_resolver.return_value = TagResolver(omnidexer=None)

        # Mock renderer
        mock_renderer = Mock()
        mock_renderer.render_document.return_value = (
            "\\documentclass{article}\\begin{document}Test\\end{document}"
        )
        mock_renderer_class.return_value = mock_renderer

        # Mock display manager
        mock_display.progress.return_value.__enter__ = Mock()
        mock_display.progress.return_value.__exit__ = Mock()
        mock_display.add_task.return_value = "task_id"
        mock_display.update_task = Mock()

        # Create temporary file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(self.mock_adventure_data, f)
            file_path = f.name

        try:
            # Test command with LaTeX options
            result = self.runner.invoke(
                app,
                [
                    "adventure",
                    file_path,
                    "--document-class",
                    "dndarticle",
                    "--paper-size",
                    "a4paper",
                    "--font-size",
                    "12pt",
                    "--background",
                    "print",
                    "--one-column",
                    "--not-justified",
                ],
            )

            # Verify success
            assert result.exit_code == 0
            assert "Adventure converted" in result.stdout

            # Verify renderer was called with context containing latex_config
            mock_renderer.render_document.assert_called_once()
            call_args = mock_renderer.render_document.call_args
            context = call_args[0][1]  # Second argument is the context

            # Verify latex_config was passed and has correct values
            assert context.latex_config is not None
            assert context.latex_config.document.document_class == "dndarticle"
            assert context.latex_config.document.paper_size == "a4paper"
            assert context.latex_config.document.font_size == "12pt"
            assert context.latex_config.document.background == "print"
            assert context.latex_config.document.two_column is False
            assert context.latex_config.document.justified_text is False

        finally:
            Path(file_path).unlink()

    @patch("dnd5e.cli.commands.convert.get_omnidexer")
    @patch("dnd5e.cli.commands.convert.get_tag_resolver")
    @patch("dnd5e.cli.commands.convert.LaTeXDocumentRenderer")
    @patch("dnd5e.cli.commands.convert.display_manager")
    @patch("aiofiles.open")
    @patch("pathlib.Path.mkdir")
    def test_book_with_default_latex_options(
        self,
        mock_mkdir,
        mock_aiofiles_open,
        mock_display,
        mock_renderer_class,
        mock_tag_resolver,
        mock_omnidexer,
    ):
        """Test book command with default LaTeX options."""
        # Mock book data
        mock_book_data = {
            "data": [
                {
                    "type": "section",
                    "name": "Chapter 1",
                    "entries": ["This is chapter 1 content."],
                }
            ]
        }

        # Mock file operations
        mock_file = AsyncMock()
        mock_file.read.return_value = json.dumps(mock_book_data)
        mock_aiofiles_open.return_value.__aenter__.return_value = mock_file

        # Mock dependencies
        mock_omnidexer.return_value = Omnidexer()
        mock_tag_resolver.return_value = TagResolver(omnidexer=None)

        # Mock renderer
        mock_renderer = Mock()
        mock_renderer.render_document.return_value = (
            "\\documentclass{article}\\begin{document}Test\\end{document}"
        )
        mock_renderer_class.return_value = mock_renderer

        # Mock display manager
        mock_display.progress.return_value.__enter__ = Mock()
        mock_display.progress.return_value.__exit__ = Mock()
        mock_display.add_task.return_value = "task_id"
        mock_display.update_task = Mock()

        # Create temporary file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(mock_book_data, f)
            file_path = f.name

        try:
            # Test command with default options
            result = self.runner.invoke(app, ["book", file_path])

            # Verify success
            assert result.exit_code == 0
            assert "Book converted" in result.stdout

            # Verify default LaTeX config values
            mock_renderer.render_document.assert_called_once()
            call_args = mock_renderer.render_document.call_args
            context = call_args[0][1]  # Second argument is the context

            assert context.latex_config is not None
            assert context.latex_config.document.document_class == "dndbook"
            assert (
                context.latex_config.document.paper_size == "letterpaper"
            )  # default from settings
            assert context.latex_config.document.font_size == "11pt"
            assert (
                context.latex_config.document.background is None
            )  # default no background
            assert context.latex_config.document.two_column is True
            assert context.latex_config.document.justified_text is True

        finally:
            Path(file_path).unlink()

    @patch("dnd5e.cli.commands.convert.get_omnidexer")
    @patch("dnd5e.cli.commands.convert.get_tag_resolver")
    @patch("dnd5e.cli.commands.convert.LaTeXDocumentRenderer")
    @patch("dnd5e.cli.commands.convert.display_manager")
    @patch("aiofiles.open")
    @patch("pathlib.Path.mkdir")
    @patch("dnd5e.cli.commands.convert.get_app_config")
    def test_supplement_with_paper_size_from_settings(
        self,
        mock_get_app_config,
        mock_mkdir,
        mock_aiofiles_open,
        mock_display,
        mock_renderer_class,
        mock_tag_resolver,
        mock_omnidexer,
    ):
        """Test supplement command uses paper size from settings when not specified."""
        # Mock supplement data
        mock_supplement_data = {
            "spell": [
                {
                    "name": "Test Spell",
                    "source": {"abbreviation": "TEST", "name": "Test Source"},
                    "level": 1,
                    "school": "A",
                    "time": [{"number": 1, "unit": "action"}],
                    "range": {
                        "type": "point",
                        "distance": {"type": "feet", "amount": 30},
                    },
                    "components": {"v": True},
                    "duration": [{"type": "instant"}],
                    "entries": ["Test spell description"],
                }
            ]
        }

        # Mock app config with custom paper size
        mock_config = Mock()
        mock_config.rendering.latex.document.paper_size = "a5paper"
        mock_get_app_config.return_value = mock_config

        # Mock file operations
        mock_file = AsyncMock()
        mock_file.read.return_value = json.dumps(mock_supplement_data)
        mock_aiofiles_open.return_value.__aenter__.return_value = mock_file

        # Mock dependencies
        mock_omnidexer.return_value = Omnidexer()
        mock_tag_resolver.return_value = TagResolver(omnidexer=None)

        # Mock renderer
        mock_renderer = Mock()
        mock_renderer.render_document.return_value = (
            "\\documentclass{article}\\begin{document}Test\\end{document}"
        )
        mock_renderer_class.return_value = mock_renderer

        # Mock display manager
        mock_display.progress.return_value.__enter__ = Mock()
        mock_display.progress.return_value.__exit__ = Mock()
        mock_display.add_task.return_value = "task_id"
        mock_display.update_task = Mock()

        # Create temporary file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(mock_supplement_data, f)
            file_path = f.name

        try:
            # Test command without --paper-size flag
            result = self.runner.invoke(app, ["supplement", file_path])

            # Verify success
            assert result.exit_code == 0
            assert "Supplement converted" in result.stdout

            # Verify settings paper size was used
            mock_renderer.render_document.assert_called_once()
            call_args = mock_renderer.render_document.call_args
            context = call_args[0][1]  # Second argument is the context

            assert context.latex_config is not None
            assert context.latex_config.document.paper_size == "a5paper"

        finally:
            Path(file_path).unlink()

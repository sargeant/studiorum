"""Comprehensive tests for convert CLI commands."""

import json
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from typer.testing import CliRunner

from dnd5e.cli.commands.convert import _compile_pdf
from dnd5e.cli.main import app
from dnd5e.core.loaders.omnidexer import Omnidexer
from dnd5e.core.models.books import Book
from dnd5e.core.models.content import Source
from dnd5e.core.text.tag_resolver import TagResolver
from tests.test_helpers import reset_test_environment


@pytest.mark.cli
class TestConvertAdventureCommand:
    """Test adventure conversion command."""

    def setup_method(self):
        """Set up test fixtures."""
        # Reset global state for complete isolation
        reset_test_environment()

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
    @patch("builtins.open")
    @patch("pathlib.Path.mkdir")
    def test_convert_adventure_with_file_path(
        self,
        mock_mkdir,
        mock_builtin_open,
        mock_display,
        mock_renderer_class,
        mock_tag_resolver,
        mock_omnidexer,
    ):
        """Test converting adventure from file path."""
        # Mock file operations
        mock_file = Mock()
        mock_file.read.return_value = json.dumps(self.mock_adventure_data)
        mock_builtin_open.return_value.__enter__.return_value = mock_file

        # Mock dependencies - create a mock that passes isinstance checks
        mock_omnidexer_instance = Mock(spec=Omnidexer)
        mock_omnidexer.return_value = mock_omnidexer_instance
        mock_tag_resolver_instance = Mock(spec=TagResolver)
        mock_tag_resolver.return_value = mock_tag_resolver_instance

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
            result = self.runner.invoke(app, ["convert", "adventure", file_path])

            # Verify success
            if result.exit_code != 0:
                print(f"Command failed with output: {result.stdout}")
                print(f"Command stderr: {result.stderr}")
            assert result.exit_code == 0
            assert "Adventure converted" in result.stdout

            # Verify file operations
            mock_builtin_open.assert_called()
            mock_mkdir.assert_called()

        finally:
            Path(file_path).unlink()

    @patch("dnd5e.cli.commands.convert.get_omnidexer")
    @patch("dnd5e.cli.commands.convert.get_tag_resolver")
    @patch("dnd5e.cli.commands.convert.get_app_config")
    @patch("dnd5e.core.config.sources.get_content_config")
    @patch(
        "dnd5e.core.resolvers.content_resolver.ContentResolver._enrich_content_if_needed"
    )
    @patch("dnd5e.cli.commands.convert.LaTeXDocumentRenderer")
    @patch("dnd5e.cli.commands.convert.display_manager")
    @patch("pathlib.Path.mkdir")
    def test_convert_adventure_with_abbreviation(
        self,
        mock_mkdir,
        mock_display,
        mock_renderer_class,
        mock_enrich_content,
        mock_user_config,
        mock_app_config,
        mock_tag_resolver,
        mock_omnidexer,
    ):
        """Test converting adventure from abbreviation."""
        # Create a proper Adventure instance instead of Mock
        from dnd5e.core.models.adventures import Adventure
        from dnd5e.core.models.content import Source

        mock_adventure = Adventure(
            name="Test Adventure",
            source=Source(
                abbreviation="test", name="Test Source"
            ),  # lowercase "test" to match CLI input
            id="test-adventure",
            contents=[],
        )

        # Mock dependencies
        mock_omnidexer_instance = Mock(spec=Omnidexer)
        mock_omnidexer_instance.get_all_by_type.return_value = [mock_adventure]

        # Mock the source_manager to avoid file loading
        mock_source_manager = Mock()
        mock_omnidexer_instance.source_manager = mock_source_manager
        mock_omnidexer.return_value = mock_omnidexer_instance

        # Mock content enrichment to return content unchanged (avoid file loading)
        mock_enrich_content.side_effect = lambda content, content_type: content

        mock_tag_resolver_instance = Mock(spec=TagResolver)
        mock_tag_resolver.return_value = mock_tag_resolver_instance

        # Mock app config with complete structure
        mock_config = Mock()
        mock_config.rendering.latex.document.paper_size = "letter"
        mock_config.rendering.latex.document.fonts = None
        mock_config.rendering.latex.document.font_size = "10pt"
        mock_config.rendering.latex.document.background = "full"
        mock_config.rendering.latex.document.high_contrast = False
        mock_config.rendering.latex.document.two_column = False
        mock_config.rendering.latex.document.justified_text = False
        mock_config.rendering.latex.document.no_outline = (
            False  # Add the missing no_outline field
        )
        mock_app_config.return_value = mock_config

        # Mock user config with defaults (all None to use app config defaults)
        mock_latex = Mock()
        mock_latex.paper_size = None
        mock_latex.fonts = None
        mock_latex.font_size = None
        mock_latex.background = None
        mock_latex.no_outline = None
        mock_latex.high_contrast = None
        mock_latex.two_column = None
        mock_latex.justified = None

        mock_user_config_obj = Mock()
        mock_user_config_obj.latex = mock_latex
        mock_user_config.return_value = mock_user_config_obj

        # Mock resolver - no longer needed since we're using the real resolver with mocked omnidexer
        # The ContentResolver will be instantiated with our mocked omnidexer
        # and will find the mock_adventure through get_all_by_type

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

        # Configure mkdir mock to actually create the directory structure
        def create_dir_side_effect(*args, **kwargs):
            # Create the actual directory structure when mkdir is called
            import os

            os.makedirs("output/adventures", exist_ok=True)

        mock_mkdir.side_effect = create_dir_side_effect

        # Test command
        result = self.runner.invoke(app, ["convert", "adventure", "test"])

        # Verify success
        assert result.exit_code == 0
        assert "Adventure converted" in result.stdout

        # Cleanup created directories
        import shutil

        if Path("output").exists():
            shutil.rmtree("output")

    def test_convert_adventure_nonexistent_file(self):
        """Test error handling for nonexistent file."""
        result = self.runner.invoke(
            app, ["convert", "adventure", "/nonexistent/file.json"]
        )

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
        mock_resolver.resolve_adventure = Mock(return_value=mock_result)
        mock_resolver_class.return_value = mock_resolver

        # Test command
        result = self.runner.invoke(app, ["convert", "adventure", "nonexistent"])

        # Should exit with error
        assert result.exit_code == 1
        assert "Error:" in result.stdout

    @patch("dnd5e.cli.commands.convert.get_omnidexer")
    @patch("dnd5e.cli.commands.convert.get_tag_resolver")
    @patch("dnd5e.cli.commands.convert.LaTeXDocumentRenderer")
    @patch("dnd5e.cli.commands.convert.display_manager")
    @patch("builtins.open")
    @patch("pathlib.Path.mkdir")
    @patch("dnd5e.cli.commands.convert._compile_pdf")
    def test_convert_adventure_with_pdf_compilation(
        self,
        mock_compile_pdf,
        mock_mkdir,
        mock_builtin_open,
        mock_display,
        mock_renderer_class,
        mock_tag_resolver,
        mock_omnidexer,
    ):
        """Test adventure conversion with PDF compilation."""
        # Mock file operations
        mock_file = Mock()
        mock_file.read.return_value = json.dumps(self.mock_adventure_data)
        mock_builtin_open.return_value.__enter__.return_value = mock_file

        # Mock dependencies
        mock_omnidexer.return_value = Omnidexer()
        mock_tag_resolver_instance = Mock(spec=TagResolver)
        mock_tag_resolver.return_value = mock_tag_resolver_instance

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
            result = self.runner.invoke(
                app, ["convert", "adventure", file_path, "--pdf"]
            )

            # Verify success and PDF compilation called
            assert result.exit_code == 0
            mock_compile_pdf.assert_called_once()

        finally:
            Path(file_path).unlink()


@pytest.mark.cli
class TestConvertBookCommand:
    """Test book conversion command."""

    def setup_method(self):
        """Set up test fixtures."""
        # Reset global state for complete isolation
        reset_test_environment()

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
    @patch("builtins.open")
    @patch("pathlib.Path.mkdir")
    def test_convert_book_with_file_path(
        self,
        mock_mkdir,
        mock_builtin_open,
        mock_display,
        mock_renderer_class,
        mock_tag_resolver,
        mock_omnidexer,
    ):
        """Test converting book from file path."""
        # Mock file operations
        mock_file = Mock()
        mock_file.read.return_value = json.dumps(self.mock_book_data)
        mock_builtin_open.return_value.__enter__.return_value = mock_file

        # Mock dependencies
        mock_omnidexer.return_value = Omnidexer()
        mock_tag_resolver_instance = Mock(spec=TagResolver)
        mock_tag_resolver.return_value = mock_tag_resolver_instance

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
            result = self.runner.invoke(app, ["convert", "book", file_path])

            # Verify success
            assert result.exit_code == 0
            assert "Book converted" in result.stdout

        finally:
            Path(file_path).unlink()

    @patch("dnd5e.cli.commands.convert.get_omnidexer")
    @patch("dnd5e.cli.commands.convert.get_tag_resolver")
    @patch("dnd5e.cli.commands.convert.get_app_config")
    @patch("dnd5e.core.config.sources.get_content_config")
    @patch("dnd5e.cli.commands.convert.LaTeXDocumentRenderer")
    @patch("dnd5e.cli.commands.convert.display_manager")
    @patch("builtins.open")
    @patch("pathlib.Path.mkdir")
    def test_convert_book_with_custom_options(
        self,
        mock_mkdir,
        mock_builtin_open,
        mock_display,
        mock_renderer_class,
        mock_user_config,
        mock_app_config,
        mock_tag_resolver,
        mock_omnidexer,
    ):
        """Test book conversion with custom options."""
        # Mock file operations
        mock_file = Mock()
        mock_file.read.return_value = json.dumps(self.mock_book_data)
        mock_builtin_open.return_value.__enter__.return_value = mock_file

        # Mock dependencies
        mock_omnidexer.return_value = Omnidexer()
        mock_tag_resolver_instance = Mock(spec=TagResolver)
        mock_tag_resolver.return_value = mock_tag_resolver_instance

        # Mock app config with complete structure
        mock_config = Mock()
        mock_config.rendering.latex.document.paper_size = "a5"
        mock_config.rendering.latex.document.fonts = None
        mock_config.rendering.latex.document.no_outline = False
        mock_config.rendering.latex.document.background = "full"
        mock_config.rendering.latex.document.high_contrast = False
        mock_config.rendering.latex.document.font_size = "11pt"
        mock_config.rendering.latex.document.two_column = False
        mock_config.rendering.latex.document.justified_text = False
        mock_config.rendering.latex.document.no_outline = (
            False  # Add the missing no_outline field
        )
        mock_app_config.return_value = mock_config

        # Mock user config with defaults (all None to use app config defaults)
        mock_user_config_obj = Mock()
        mock_user_config_obj.latex.paper_size = None
        mock_user_config_obj.latex.fonts = None
        mock_user_config_obj.latex.font_size = None
        mock_user_config_obj.latex.background = None
        mock_user_config_obj.latex.no_outline = None
        mock_user_config_obj.latex.high_contrast = None
        mock_user_config_obj.latex.two_column = None
        mock_user_config_obj.latex.justified = None
        mock_user_config.return_value = mock_user_config_obj

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
                    "convert",
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


@pytest.mark.cli
class TestConvertSupplementCommand:
    """Test supplement conversion command."""

    def setup_method(self):
        """Set up test fixtures."""
        # Reset global state for complete isolation
        reset_test_environment()

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
    @patch("builtins.open")
    @patch("pathlib.Path.mkdir")
    def test_convert_supplement_with_spells(
        self,
        mock_mkdir,
        mock_builtin_open,
        mock_display,
        mock_renderer_class,
        mock_tag_resolver,
        mock_omnidexer,
    ):
        """Test converting supplement with spells."""
        # Mock file operations
        mock_file = Mock()
        mock_file.read.return_value = json.dumps(self.mock_supplement_data)
        mock_builtin_open.return_value.__enter__.return_value = mock_file

        # Mock dependencies
        mock_omnidexer.return_value = Omnidexer()
        mock_tag_resolver_instance = Mock(spec=TagResolver)
        mock_tag_resolver.return_value = mock_tag_resolver_instance

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
            result = self.runner.invoke(app, ["convert", "supplement", file_path])

            # Verify success
            assert result.exit_code == 0
            assert "Supplement converted" in result.stdout

        finally:
            Path(file_path).unlink()

    def test_convert_supplement_nonexistent_file(self):
        """Test error handling for nonexistent supplement file."""
        result = self.runner.invoke(
            app, ["convert", "supplement", "/nonexistent/file.json"]
        )

        # Should exit with error
        assert result.exit_code == 1
        assert "Error:" in result.stdout

    @patch("dnd5e.cli.commands.convert.get_omnidexer")
    @patch("dnd5e.cli.commands.convert.get_tag_resolver")
    @patch("dnd5e.cli.commands.convert.display_manager")
    @patch("builtins.open")
    def test_convert_supplement_empty_content(
        self,
        mock_builtin_open,
        mock_display,
        mock_tag_resolver,
        mock_omnidexer,
    ):
        """Test error handling for supplement with no valid content."""
        # Mock file operations - empty content
        mock_file = Mock()
        mock_file.read.return_value = json.dumps({"unknown": []})
        mock_builtin_open.return_value.__enter__.return_value = mock_file

        # Mock dependencies
        mock_omnidexer.return_value = Omnidexer()
        mock_tag_resolver_instance = Mock(spec=TagResolver)
        mock_tag_resolver.return_value = mock_tag_resolver_instance

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
            result = self.runner.invoke(app, ["convert", "supplement", file_path])

            # Should exit with error
            assert result.exit_code == 1
            assert "Error:" in result.stdout

        finally:
            Path(file_path).unlink()


@pytest.mark.cli
class TestPDFCompilation:
    """Test PDF compilation functionality."""

    @pytest.mark.asyncio
    @patch("builtins.open")
    @patch("dnd5e.cli.commands.convert._create_latex_compiler")
    @patch("dnd5e.cli.commands.convert.display_manager")
    async def test_compile_pdf_success(
        self, mock_display, mock_create_compiler, mock_builtin_open
    ):
        """Test successful PDF compilation."""
        # Mock file reading
        mock_file = Mock()
        mock_file.read.return_value = (
            "\\documentclass{article}\\begin{document}Test\\end{document}"
        )
        mock_builtin_open.return_value.__enter__.return_value = mock_file

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
    @patch("builtins.open")
    @patch("dnd5e.cli.commands.convert._create_latex_compiler")
    @patch("dnd5e.cli.commands.convert.display_manager")
    async def test_compile_pdf_failure(
        self, mock_display, mock_create_compiler, mock_builtin_open
    ):
        """Test PDF compilation failure handling."""
        # Mock file reading
        mock_file = Mock()
        mock_file.read.return_value = (
            "\\documentclass{article}\\begin{document}Test\\end{document}"
        )
        mock_builtin_open.return_value.__enter__.return_value = mock_file

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
    @patch("builtins.open")
    @patch("dnd5e.cli.commands.convert._create_latex_compiler")
    @patch("dnd5e.cli.commands.convert.display_manager")
    async def test_compile_pdf_latex_not_found(
        self, mock_display, mock_create_compiler, mock_builtin_open
    ):
        """Test handling when LaTeX engine is not installed."""
        # Mock file reading
        mock_file = Mock()
        mock_file.read.return_value = (
            "\\documentclass{article}\\begin{document}Test\\end{document}"
        )
        mock_builtin_open.return_value.__enter__.return_value = mock_file

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


@pytest.mark.cli
class TestErrorHandlingPaths:
    """Test error handling in various scenarios."""

    def setup_method(self):
        """Set up test fixtures."""
        # Reset global state for complete isolation
        reset_test_environment()

        self.runner = CliRunner()

    @patch("dnd5e.cli.commands.convert.get_omnidexer")
    @patch("dnd5e.cli.commands.convert.get_tag_resolver")
    @patch("builtins.open")
    def test_json_decode_error(
        self, mock_builtin_open, mock_tag_resolver, mock_omnidexer
    ):
        """Test handling of invalid JSON files."""
        # Mock file operations - invalid JSON
        mock_file = Mock()
        mock_file.read.return_value = "invalid json content {"
        mock_builtin_open.return_value.__enter__.return_value = mock_file

        # Mock dependencies
        mock_omnidexer.return_value = Omnidexer()
        mock_tag_resolver_instance = Mock(spec=TagResolver)
        mock_tag_resolver.return_value = mock_tag_resolver_instance

        # Create temporary file with invalid JSON
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("invalid json content {")
            file_path = f.name

        try:
            # Test command
            result = self.runner.invoke(app, ["convert", "adventure", file_path])

            # Should exit with error
            assert result.exit_code == 1
            assert "Error:" in result.stdout

        finally:
            Path(file_path).unlink()

    @patch("dnd5e.cli.commands.convert.get_omnidexer")
    @patch("dnd5e.cli.commands.convert.get_tag_resolver")
    @patch("dnd5e.cli.commands.convert.LaTeXDocumentRenderer")
    @patch("builtins.open")
    def test_renderer_exception(
        self, mock_builtin_open, mock_renderer_class, mock_tag_resolver, mock_omnidexer
    ):
        """Test handling of renderer exceptions."""
        # Mock file operations
        mock_file = Mock()
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
        mock_builtin_open.return_value.__enter__.return_value = mock_file

        # Mock dependencies
        mock_omnidexer.return_value = Omnidexer()
        mock_tag_resolver_instance = Mock(spec=TagResolver)
        mock_tag_resolver.return_value = mock_tag_resolver_instance

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
            result = self.runner.invoke(app, ["convert", "adventure", file_path])

            # Should exit with error
            assert result.exit_code == 1
            assert "Error:" in result.stdout

        finally:
            Path(file_path).unlink()


@pytest.mark.cli
class TestSpecialCases:
    """Test special cases and edge conditions."""

    def setup_method(self):
        """Set up test fixtures."""
        # Reset global state for complete isolation
        reset_test_environment()

        self.runner = CliRunner()

    @patch("dnd5e.cli.commands.convert.get_omnidexer")
    @patch("dnd5e.cli.commands.convert.get_tag_resolver")
    @patch("dnd5e.cli.commands.convert.ContentResolver")
    @patch("dnd5e.cli.commands.convert.LaTeXDocumentRenderer")
    @patch("dnd5e.cli.commands.convert.display_manager")
    @patch("builtins.open")
    @patch("pathlib.Path.mkdir")
    def test_phb_abbreviation_fallback(
        self,
        mock_mkdir,
        mock_builtin_open,
        mock_display,
        mock_renderer_class,
        mock_resolver_class,
        mock_tag_resolver,
        mock_omnidexer,
    ):
        """Test PHB abbreviation fallback to content resolver."""
        # Mock file operations
        mock_file = Mock()
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
        mock_builtin_open.return_value.__enter__.return_value = mock_file

        # Mock dependencies
        mock_omnidexer.return_value = Omnidexer()
        mock_tag_resolver_instance = Mock(spec=TagResolver)
        mock_tag_resolver.return_value = mock_tag_resolver_instance

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
        mock_resolver.resolve_book = Mock(return_value=mock_result)
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
        result = self.runner.invoke(app, ["convert", "book", "phb"])

        # Should succeed via resolver fallback
        assert result.exit_code == 0


@pytest.mark.cli
class TestLaTeXDocumentOptions:
    """Test LaTeX document class options in CLI commands."""

    def setup_method(self):
        """Set up test fixtures."""
        # Reset global state for complete isolation
        reset_test_environment()

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
    @patch("dnd5e.cli.commands.convert.get_app_config")
    @patch("dnd5e.core.config.sources.get_content_config")
    @patch("dnd5e.cli.commands.convert.LaTeXDocumentRenderer")
    @patch("dnd5e.cli.commands.convert.display_manager")
    @patch("builtins.open")
    @patch("pathlib.Path.mkdir")
    def test_adventure_with_latex_options(
        self,
        mock_mkdir,
        mock_builtin_open,
        mock_display,
        mock_renderer_class,
        mock_user_config,
        mock_app_config,
        mock_tag_resolver,
        mock_omnidexer,
    ):
        """Test adventure command with LaTeX document options."""
        # Mock file operations
        mock_file = Mock()
        mock_file.read.return_value = json.dumps(self.mock_adventure_data)
        mock_builtin_open.return_value.__enter__.return_value = mock_file

        # Mock dependencies
        mock_omnidexer.return_value = Omnidexer()
        mock_tag_resolver_instance = Mock(spec=TagResolver)
        mock_tag_resolver.return_value = mock_tag_resolver_instance

        # Mock app config with complete structure
        mock_config = Mock()
        mock_config.rendering.latex.document.paper_size = "letter"
        mock_config.rendering.latex.document.fonts = None
        mock_config.rendering.latex.document.font_size = "10pt"
        mock_config.rendering.latex.document.background = "full"
        mock_config.rendering.latex.document.high_contrast = False
        mock_config.rendering.latex.document.two_column = False
        mock_config.rendering.latex.document.justified_text = False
        mock_config.rendering.latex.document.no_outline = (
            False  # Add the missing no_outline field
        )
        mock_app_config.return_value = mock_config

        # Mock user config with defaults (all None to use app config defaults)
        mock_user_config_obj = Mock()
        mock_user_config_obj.latex.paper_size = None
        mock_user_config_obj.latex.fonts = None
        mock_user_config_obj.latex.font_size = None
        mock_user_config_obj.latex.background = None
        mock_user_config_obj.latex.no_outline = None
        mock_user_config_obj.latex.high_contrast = None
        mock_user_config_obj.latex.two_column = None
        mock_user_config_obj.latex.justified = None
        mock_user_config.return_value = mock_user_config_obj

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
                    "convert",
                    "adventure",
                    file_path,
                    "--document-class",
                    "dndarticle",
                    "--paper",
                    "a4",
                    "--font-size",
                    "12pt",
                    "--background",
                    "print",
                    "--high-contrast",
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
            latex_config = context.metadata.get("latex_config")
            assert latex_config is not None
            assert latex_config.document.document_class == "dndarticle"
            assert latex_config.document.paper_size == "a4"
            assert latex_config.document.font_size == "12pt"
            assert latex_config.document.background == "print"
            assert latex_config.document.high_contrast is True
            assert latex_config.document.two_column is False
            assert latex_config.document.justified_text is False

        finally:
            Path(file_path).unlink()

    @patch("dnd5e.cli.commands.convert.get_omnidexer")
    @patch("dnd5e.cli.commands.convert.get_tag_resolver")
    @patch("dnd5e.cli.commands.convert.LaTeXDocumentRenderer")
    @patch("dnd5e.cli.commands.convert.display_manager")
    @patch("builtins.open")
    @patch("pathlib.Path.mkdir")
    def test_book_with_default_latex_options(
        self,
        mock_mkdir,
        mock_builtin_open,
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
        mock_file = Mock()
        mock_file.read.return_value = json.dumps(mock_book_data)
        mock_builtin_open.return_value.__enter__.return_value = mock_file

        # Mock dependencies
        mock_omnidexer.return_value = Omnidexer()
        mock_tag_resolver_instance = Mock(spec=TagResolver)
        mock_tag_resolver.return_value = mock_tag_resolver_instance

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
            result = self.runner.invoke(app, ["convert", "book", file_path])

            # Verify success
            assert result.exit_code == 0
            assert "Book converted" in result.stdout

            # Verify default LaTeX config values
            mock_renderer.render_document.assert_called_once()
            call_args = mock_renderer.render_document.call_args
            context = call_args[0][1]  # Second argument is the context

            latex_config = context.metadata.get("latex_config")
            assert latex_config is not None
            assert latex_config.document.document_class == "dndbook"
            assert latex_config.document.paper_size == "letter"  # default from settings
            assert latex_config.document.font_size == "11pt"
            assert latex_config.document.background == "full"  # new default background
            assert latex_config.document.two_column is True
            assert latex_config.document.justified_text is False

        finally:
            Path(file_path).unlink()

    @patch("dnd5e.cli.commands.convert.get_omnidexer")
    @patch("dnd5e.cli.commands.convert.get_tag_resolver")
    @patch("dnd5e.cli.commands.convert.LaTeXDocumentRenderer")
    @patch("dnd5e.cli.commands.convert.display_manager")
    @patch("builtins.open")
    @patch("pathlib.Path.mkdir")
    @patch("dnd5e.core.config.sources.get_content_config")
    @patch("dnd5e.cli.commands.convert.get_app_config")
    def test_supplement_with_paper_size_from_settings(
        self,
        mock_get_app_config,
        mock_get_content_config,
        mock_mkdir,
        mock_builtin_open,
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
        mock_config.rendering.latex.document.paper_size = "a5"
        mock_config.rendering.latex.document.fonts = None
        mock_config.rendering.latex.document.no_outline = False
        mock_config.rendering.latex.document.background = "full"
        mock_config.rendering.latex.document.high_contrast = False
        mock_config.rendering.latex.document.font_size = "11pt"
        mock_config.rendering.latex.document.two_column = False
        mock_config.rendering.latex.document.justified_text = False
        mock_config.rendering.latex.document.no_outline = (
            False  # Add the missing no_outline field
        )
        mock_get_app_config.return_value = mock_config

        # Mock user config (should return None values to test fallback to app config)
        mock_user_config = Mock()
        mock_user_config.latex.paper_size = None
        mock_user_config.latex.fonts = None
        mock_user_config.latex.no_outline = None
        mock_user_config.latex.background = None
        mock_user_config.latex.high_contrast = None
        mock_user_config.latex.font_size = None
        mock_user_config.latex.two_column = None
        mock_user_config.latex.justified = None
        mock_get_content_config.return_value = mock_user_config

        # Mock file operations
        mock_file = Mock()
        mock_file.read.return_value = json.dumps(mock_supplement_data)
        mock_builtin_open.return_value.__enter__.return_value = mock_file

        # Mock dependencies
        mock_omnidexer.return_value = Omnidexer()
        mock_tag_resolver_instance = Mock(spec=TagResolver)
        mock_tag_resolver.return_value = mock_tag_resolver_instance

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
            # Test command without --paper flag
            result = self.runner.invoke(app, ["convert", "supplement", file_path])

            # Verify success
            assert result.exit_code == 0
            assert "Supplement converted" in result.stdout

            # Verify settings paper size was used
            mock_renderer.render_document.assert_called_once()
            call_args = mock_renderer.render_document.call_args
            context = call_args[0][1]  # Second argument is the context

            latex_config = context.metadata.get("latex_config")
            assert latex_config is not None
            assert latex_config.document.paper_size == "a5"

        finally:
            Path(file_path).unlink()


@pytest.mark.cli
class TestConvertSpellsCommand:
    """Test spell conversion command."""

    def setup_method(self):
        """Set up test fixtures."""
        # Reset global state for complete isolation
        reset_test_environment()

        self.runner = CliRunner()
        self.mock_spell_data = [
            {
                "name": "Fireball",
                "source": {"abbreviation": "PHB", "name": "Player's Handbook"},
                "level": 3,
                "school": "V",
                "time": [{"number": 1, "unit": "action"}],
                "range": {
                    "type": "point",
                    "distance": {"type": "feet", "amount": 150},
                },
                "components": {
                    "v": True,
                    "s": True,
                    "m": "a tiny ball of bat guano and sulfur",
                },
                "duration": [{"type": "instant"}],
                "entries": ["A bright streak flashes from your pointing finger..."],
                "damageInflict": ["fire"],
                "savingThrow": ["dexterity"],
                "classes": {
                    "fromClassList": [
                        {"name": "Sorcerer", "source": "PHB"},
                        {"name": "Wizard", "source": "PHB"},
                    ]
                },
            },
            {
                "name": "Magic Missile",
                "source": {"abbreviation": "PHB", "name": "Player's Handbook"},
                "level": 1,
                "school": "V",
                "time": [{"number": 1, "unit": "action"}],
                "range": {
                    "type": "point",
                    "distance": {"type": "feet", "amount": 120},
                },
                "components": {"v": True, "s": True},
                "duration": [{"type": "instant"}],
                "entries": ["You create three glowing darts of magical force..."],
                "damageInflict": ["force"],
                "classes": {
                    "fromClassList": [
                        {"name": "Sorcerer", "source": "PHB"},
                        {"name": "Wizard", "source": "PHB"},
                    ]
                },
            },
            {
                "name": "Cure Light Wounds",
                "source": {"abbreviation": "PHB", "name": "Player's Handbook"},
                "level": 1,
                "school": "V",
                "time": [{"number": 1, "unit": "action"}],
                "range": {"type": "touch"},
                "components": {"v": True, "s": True},
                "duration": [{"type": "instant"}],
                "entries": ["A creature you touch regains hit points..."],
                "classes": {
                    "fromClassList": [
                        {"name": "Cleric", "source": "PHB"},
                        {"name": "Paladin", "source": "PHB"},
                    ]
                },
            },
        ]

    @patch("dnd5e.cli.commands.convert.get_omnidexer")
    @patch("dnd5e.cli.commands.convert.get_tag_resolver")
    @patch("dnd5e.cli.commands.convert.get_app_config")
    @patch("dnd5e.core.config.sources.get_content_config")
    @patch("dnd5e.core.services.spell_collector.SpellCollector")
    @patch("dnd5e.cli.commands.convert._render_spellbook")
    @patch("dnd5e.cli.commands.convert.display_manager")
    @patch("pathlib.Path.mkdir")
    def test_convert_spells_with_spell_names(
        self,
        mock_mkdir,
        mock_display,
        mock_render_spellbook,
        mock_spell_collector_class,
        mock_user_config,
        mock_app_config,
        mock_tag_resolver,
        mock_omnidexer,
    ):
        """Test converting specific spells by name."""
        # Mock dependencies
        mock_omnidexer_instance = Mock(spec=Omnidexer)
        mock_omnidexer.return_value = mock_omnidexer_instance
        mock_tag_resolver_instance = Mock(spec=TagResolver)
        mock_tag_resolver.return_value = mock_tag_resolver_instance

        # Mock app config with complete structure
        mock_config = Mock()
        mock_config.rendering.latex.document.paper_size = "letter"
        mock_config.rendering.latex.document.fonts = None
        mock_config.rendering.latex.document.font_size = "11pt"
        mock_config.rendering.latex.document.background = "full"
        mock_config.rendering.latex.document.no_outline = False
        mock_config.rendering.latex.document.high_contrast = False
        mock_config.rendering.latex.document.two_column = True
        mock_config.rendering.latex.document.justified_text = False
        mock_config.rendering.latex.document.no_outline = (
            False  # Add the missing no_outline field
        )
        mock_app_config.return_value = mock_config

        # Mock user config with defaults (all None to use app config defaults)
        mock_user_config_obj = Mock()
        mock_user_config_obj.latex.paper_size = None
        mock_user_config_obj.latex.fonts = None
        mock_user_config_obj.latex.font_size = None
        mock_user_config_obj.latex.background = None
        mock_user_config_obj.latex.no_outline = None
        mock_user_config_obj.latex.high_contrast = None
        mock_user_config_obj.latex.two_column = None
        mock_user_config_obj.latex.justified = None
        mock_user_config.return_value = mock_user_config_obj

        # Mock spell collector
        mock_collector = Mock()
        mock_result = Mock()
        mock_result.spells = [
            Mock(name="Fireball", level=3),
            Mock(name="Magic Missile", level=1),
        ]
        mock_result.total_count = 2
        mock_result.unresolved_names = []
        mock_result.suggestions = {}
        mock_result.sources_used = {"PHB"}
        mock_result.get_level_summary.return_value = "2 spells (1st: 1, 3rd: 1)"

        mock_collector.collect_spells.return_value = mock_result
        mock_spell_collector_class.return_value = mock_collector

        # Mock spellbook renderer
        mock_render_spellbook.return_value = (
            "\\documentclass{dndbook}\\begin{document}Spells\\end{document}"
        )

        # Mock display manager
        mock_display.progress.return_value.__enter__ = Mock()
        mock_display.progress.return_value.__exit__ = Mock()
        mock_display.add_task.return_value = "task_id"
        mock_display.update_task = Mock()

        # Configure mkdir mock to actually create the directory structure
        def create_dir_side_effect(*args, **kwargs):
            # Create the actual directory structure when mkdir is called
            import os

            os.makedirs("output/spells", exist_ok=True)

        mock_mkdir.side_effect = create_dir_side_effect

        # Test command with spell names
        result = self.runner.invoke(
            app, ["convert", "spells", "fireball", "magic missile"]
        )

        # Verify success
        assert result.exit_code == 0
        assert "Spellbook generated" in result.stdout

        # Verify spell collector was called with correct criteria
        mock_collector.collect_spells.assert_called_once()
        criteria = mock_collector.collect_spells.call_args[0][0]
        assert criteria.spell_names == ["fireball", "magic missile"]

        # Verify file operations
        mock_mkdir.assert_called()

        # Cleanup created directories
        import shutil
        from pathlib import Path

        if Path("output").exists():
            shutil.rmtree("output")

    @patch("dnd5e.cli.commands.convert.get_omnidexer")
    @patch("dnd5e.cli.commands.convert.get_tag_resolver")
    @patch("dnd5e.cli.commands.convert.get_app_config")
    @patch("dnd5e.core.config.sources.get_content_config")
    @patch("dnd5e.core.services.spell_collector.SpellCollector")
    @patch("dnd5e.cli.commands.convert._render_spellbook")
    @patch("dnd5e.cli.commands.convert.display_manager")
    @patch("dnd5e.core.parsers.spell_input.SpellInputParser")
    @patch("pathlib.Path.mkdir")
    @patch("builtins.open")
    def test_convert_spells_from_file(
        self,
        mock_builtin_open,
        mock_mkdir,
        mock_input_parser,
        mock_display,
        mock_render_spellbook,
        mock_spell_collector_class,
        mock_user_config,
        mock_app_config,
        mock_tag_resolver,
        mock_omnidexer,
    ):
        """Test converting spells from file."""
        # Mock dependencies
        mock_omnidexer.return_value = Mock(spec=Omnidexer)
        mock_tag_resolver.return_value = Mock(spec=TagResolver)

        # Mock app config with complete structure
        mock_config = Mock()
        mock_config.rendering.latex.document.paper_size = "letter"
        mock_config.rendering.latex.document.fonts = None
        mock_config.rendering.latex.document.font_size = "11pt"
        mock_config.rendering.latex.document.background = "full"
        mock_config.rendering.latex.document.no_outline = False
        mock_config.rendering.latex.document.high_contrast = False
        mock_config.rendering.latex.document.two_column = True
        mock_config.rendering.latex.document.justified_text = False
        mock_config.rendering.latex.document.no_outline = (
            False  # Add the missing no_outline field
        )
        mock_app_config.return_value = mock_config

        # Mock user config with defaults (all None to use app config defaults)
        mock_user_config_obj = Mock()
        mock_user_config_obj.latex.paper_size = None
        mock_user_config_obj.latex.fonts = None
        mock_user_config_obj.latex.font_size = None
        mock_user_config_obj.latex.background = None
        mock_user_config_obj.latex.no_outline = None
        mock_user_config_obj.latex.high_contrast = None
        mock_user_config_obj.latex.two_column = None
        mock_user_config_obj.latex.justified = None
        mock_user_config.return_value = mock_user_config_obj

        # Mock file parsing
        mock_input_parser.parse_spell_names_from_file.return_value = [
            "fireball",
            "magic missile",
        ]

        # Mock spell collector
        mock_collector = Mock()
        mock_result = Mock()
        mock_result.spells = [
            Mock(name="Fireball", level=3),
            Mock(name="Magic Missile", level=1),
        ]
        mock_result.total_count = 2
        mock_result.unresolved_names = []
        mock_result.suggestions = {}
        mock_result.sources_used = {"PHB"}
        mock_result.get_level_summary.return_value = "2 spells"

        mock_collector.collect_spells.return_value = mock_result
        mock_spell_collector_class.return_value = mock_collector

        # Mock renderer
        mock_render_spellbook.return_value = (
            "\\documentclass{dndbook}\\begin{document}Spells\\end{document}"
        )

        # Mock display manager
        mock_display.progress.return_value.__enter__ = Mock()
        mock_display.progress.return_value.__exit__ = Mock()
        mock_display.add_task.return_value = "task_id"
        mock_display.update_task = Mock()

        # Create temporary file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("fireball\nmagic missile\n")
            file_path = f.name

        try:
            # Test command with file input
            result = self.runner.invoke(
                app, ["convert", "spells", "--from-file", file_path]
            )

            # Verify success
            assert result.exit_code == 0
            assert "Loaded 2 spells from" in result.stdout
            assert "Spellbook generated" in result.stdout

            # Verify file parser was called
            mock_input_parser.parse_spell_names_from_file.assert_called_once()

        finally:
            Path(file_path).unlink()

    @patch("dnd5e.cli.commands.convert.get_omnidexer")
    @patch("dnd5e.cli.commands.convert.get_tag_resolver")
    @patch("dnd5e.cli.commands.convert.get_app_config")
    @patch("dnd5e.core.config.sources.get_content_config")
    @patch("dnd5e.core.services.spell_collector.SpellCollector")
    @patch("dnd5e.cli.commands.convert._render_spellbook")
    @patch("dnd5e.cli.commands.convert.display_manager")
    @patch("dnd5e.core.parsers.spell_input.SpellInputParser")
    @patch("pathlib.Path.mkdir")
    @patch("builtins.open")
    def test_convert_spells_with_class_filtering(
        self,
        mock_builtin_open,
        mock_mkdir,
        mock_input_parser,
        mock_display,
        mock_render_spellbook,
        mock_spell_collector_class,
        mock_user_config,
        mock_app_config,
        mock_tag_resolver,
        mock_omnidexer,
    ):
        """Test converting spells with class-based filtering."""
        # Mock dependencies
        mock_omnidexer.return_value = Mock(spec=Omnidexer)
        mock_tag_resolver.return_value = Mock(spec=TagResolver)

        # Mock app config with complete structure
        mock_config = Mock()
        mock_config.rendering.latex.document.paper_size = "letter"
        mock_config.rendering.latex.document.fonts = None
        mock_config.rendering.latex.document.font_size = "11pt"
        mock_config.rendering.latex.document.background = "full"
        mock_config.rendering.latex.document.no_outline = False
        mock_config.rendering.latex.document.high_contrast = False
        mock_config.rendering.latex.document.two_column = True
        mock_config.rendering.latex.document.justified_text = False
        mock_config.rendering.latex.document.no_outline = (
            False  # Add the missing no_outline field
        )
        mock_app_config.return_value = mock_config

        # Mock user config with defaults (all None to use app config defaults)
        mock_user_config_obj = Mock()
        mock_user_config_obj.latex.paper_size = None
        mock_user_config_obj.latex.fonts = None
        mock_user_config_obj.latex.font_size = None
        mock_user_config_obj.latex.background = None
        mock_user_config_obj.latex.no_outline = None
        mock_user_config_obj.latex.high_contrast = None
        mock_user_config_obj.latex.two_column = None
        mock_user_config_obj.latex.justified = None
        mock_user_config.return_value = mock_user_config_obj

        # Mock class parsing and level range parsing
        mock_input_parser.parse_class_list.return_value = ["wizard"]
        mock_input_parser.parse_level_range.return_value = (1, 3)

        # Mock spell collector
        mock_collector = Mock()
        mock_result = Mock()
        mock_result.spells = [
            Mock(name="Fireball", level=3),
            Mock(name="Magic Missile", level=1),
        ]
        mock_result.total_count = 2
        mock_result.unresolved_names = []
        mock_result.suggestions = {}
        mock_result.sources_used = {"PHB"}
        mock_result.get_level_summary.return_value = "2 wizard spells"

        mock_collector.collect_spells.return_value = mock_result
        mock_spell_collector_class.return_value = mock_collector

        # Mock renderer
        mock_render_spellbook.return_value = (
            "\\documentclass{dndbook}\\begin{document}Wizard Spells\\end{document}"
        )

        # Mock display manager
        mock_display.progress.return_value.__enter__ = Mock()
        mock_display.progress.return_value.__exit__ = Mock()
        mock_display.add_task.return_value = "task_id"
        mock_display.update_task = Mock()

        # Mock file operations
        mock_file = Mock()
        mock_builtin_open.return_value.__enter__.return_value = mock_file

        # Test command with class filtering
        result = self.runner.invoke(
            app, ["convert", "spells", "--class", "wizard", "--level", "1-3"]
        )

        # Verify success
        assert result.exit_code == 0
        assert "Spellbook generated" in result.stdout

        # Verify spell collector was called with correct criteria
        mock_collector.collect_spells.assert_called_once()
        criteria = mock_collector.collect_spells.call_args[0][0]
        assert criteria.classes == ["wizard"]

    @patch("dnd5e.cli.commands.convert.get_omnidexer")
    @patch("dnd5e.cli.commands.convert.get_tag_resolver")
    @patch("dnd5e.cli.commands.convert.get_app_config")
    @patch("dnd5e.core.config.sources.get_content_config")
    @patch("dnd5e.core.services.spell_collector.SpellCollector")
    @patch("dnd5e.cli.commands.convert._render_spellbook")
    @patch("dnd5e.cli.commands.convert.display_manager")
    @patch("pathlib.Path.mkdir")
    @patch("builtins.open")
    def test_convert_spells_with_sorting_modes(
        self,
        mock_builtin_open,
        mock_mkdir,
        mock_display,
        mock_render_spellbook,
        mock_spell_collector_class,
        mock_user_config,
        mock_app_config,
        mock_tag_resolver,
        mock_omnidexer,
    ):
        """Test spell conversion with different sorting modes."""
        # Mock dependencies
        mock_omnidexer.return_value = Mock(spec=Omnidexer)
        mock_tag_resolver.return_value = Mock(spec=TagResolver)

        # Mock app config with complete structure
        mock_config = Mock()
        mock_config.rendering.latex.document.paper_size = "letter"
        mock_config.rendering.latex.document.fonts = None
        mock_config.rendering.latex.document.font_size = "11pt"
        mock_config.rendering.latex.document.background = "full"
        mock_config.rendering.latex.document.no_outline = False
        mock_config.rendering.latex.document.high_contrast = False
        mock_config.rendering.latex.document.two_column = True
        mock_config.rendering.latex.document.justified_text = False
        mock_config.rendering.latex.document.no_outline = (
            False  # Add the missing no_outline field
        )
        mock_app_config.return_value = mock_config

        # Mock user config with defaults (all None to use app config defaults)
        mock_user_config_obj = Mock()
        mock_user_config_obj.latex.paper_size = None
        mock_user_config_obj.latex.fonts = None
        mock_user_config_obj.latex.font_size = None
        mock_user_config_obj.latex.background = None
        mock_user_config_obj.latex.no_outline = None
        mock_user_config_obj.latex.high_contrast = None
        mock_user_config_obj.latex.two_column = None
        mock_user_config_obj.latex.justified = None
        mock_user_config.return_value = mock_user_config_obj

        # Mock spell collector
        mock_collector = Mock()
        mock_result = Mock()

        # Create mock spells with proper attributes
        mock_spell1 = Mock()
        mock_spell1.name = "Fireball"
        mock_spell1.level = 3

        mock_spell2 = Mock()
        mock_spell2.name = "Magic Missile"
        mock_spell2.level = 1

        mock_spells = [mock_spell1, mock_spell2]
        mock_result.spells = mock_spells
        mock_result.total_count = 2
        mock_result.unresolved_names = []
        mock_result.suggestions = {}
        mock_result.sources_used = {"PHB"}
        mock_result.get_level_summary.return_value = "2 spells"

        mock_collector.collect_spells.return_value = mock_result
        mock_spell_collector_class.return_value = mock_collector

        # Mock renderer
        mock_render_spellbook.return_value = (
            "\\documentclass{dndbook}\\begin{document}Spells\\end{document}"
        )

        # Mock display manager
        mock_display.progress.return_value.__enter__ = Mock()
        mock_display.progress.return_value.__exit__ = Mock()
        mock_display.add_task.return_value = "task_id"
        mock_display.update_task = Mock()

        # Mock file operations
        mock_file = Mock()
        mock_builtin_open.return_value.__enter__.return_value = mock_file

        # Test level sorting (default)
        result = self.runner.invoke(
            app, ["convert", "spells", "fireball", "magic missile", "--sort", "level"]
        )
        assert result.exit_code == 0

        # Test name sorting
        result = self.runner.invoke(
            app, ["convert", "spells", "fireball", "magic missile", "--sort", "name"]
        )
        assert result.exit_code == 0

        # Verify renderer was called for both
        assert mock_render_spellbook.call_count == 2

    @patch("dnd5e.cli.commands.convert.get_omnidexer")
    @patch("dnd5e.cli.commands.convert.get_tag_resolver")
    @patch("dnd5e.cli.commands.convert.get_app_config")
    @patch("dnd5e.core.config.sources.get_content_config")
    @patch("dnd5e.core.services.spell_collector.SpellCollector")
    @patch("dnd5e.cli.commands.convert._render_spellbook")
    @patch("dnd5e.cli.commands.convert.display_manager")
    @patch("pathlib.Path.mkdir")
    @patch("builtins.open")
    def test_convert_spells_with_optional_spells_flag(
        self,
        mock_builtin_open,
        mock_mkdir,
        mock_display,
        mock_render_spellbook,
        mock_spell_collector_class,
        mock_user_config,
        mock_app_config,
        mock_tag_resolver,
        mock_omnidexer,
    ):
        """Test spell conversion with --optional-spells flag."""
        # Mock dependencies
        mock_omnidexer.return_value = Mock(spec=Omnidexer)
        mock_tag_resolver.return_value = Mock(spec=TagResolver)

        # Mock app config with complete structure
        mock_config = Mock()
        mock_config.rendering.latex.document.paper_size = "letter"
        mock_config.rendering.latex.document.fonts = None
        mock_config.rendering.latex.document.font_size = "11pt"
        mock_config.rendering.latex.document.background = "full"
        mock_config.rendering.latex.document.no_outline = False
        mock_config.rendering.latex.document.high_contrast = False
        mock_config.rendering.latex.document.two_column = True
        mock_config.rendering.latex.document.justified_text = False
        mock_config.rendering.latex.document.no_outline = (
            False  # Add the missing no_outline field
        )
        mock_app_config.return_value = mock_config

        # Mock user config with defaults (all None to use app config defaults)
        mock_user_config_obj = Mock()
        mock_user_config_obj.latex.paper_size = None
        mock_user_config_obj.latex.fonts = None
        mock_user_config_obj.latex.font_size = None
        mock_user_config_obj.latex.background = None
        mock_user_config_obj.latex.no_outline = None
        mock_user_config_obj.latex.high_contrast = None
        mock_user_config_obj.latex.two_column = None
        mock_user_config_obj.latex.justified = None
        mock_user_config.return_value = mock_user_config_obj

        # Mock spell collector
        mock_collector = Mock()
        mock_result = Mock()
        mock_result.spells = [Mock(name="Fireball", level=3)]
        mock_result.total_count = 1
        mock_result.unresolved_names = []
        mock_result.suggestions = {}
        mock_result.sources_used = {"PHB"}
        mock_result.get_level_summary.return_value = "1 spell"

        mock_collector.collect_spells.return_value = mock_result
        mock_spell_collector_class.return_value = mock_collector

        # Mock renderer
        mock_render_spellbook.return_value = (
            "\\documentclass{dndbook}\\begin{document}Spells\\end{document}"
        )

        # Mock display manager
        mock_display.progress.return_value.__enter__ = Mock()
        mock_display.progress.return_value.__exit__ = Mock()
        mock_display.add_task.return_value = "task_id"
        mock_display.update_task = Mock()

        # Test command with optional spells flag
        result = self.runner.invoke(
            app, ["convert", "spells", "--class", "wizard", "--optional-spells"]
        )

        # Verify success
        assert result.exit_code == 0
        assert "Spellbook generated" in result.stdout

        # Verify spell collector was called with include_optional=True
        mock_collector.collect_spells.assert_called_once()
        criteria = mock_collector.collect_spells.call_args[0][0]
        assert criteria.include_optional is True

    @patch("dnd5e.cli.commands.convert.get_omnidexer")
    @patch("dnd5e.cli.commands.convert.get_tag_resolver")
    @patch("dnd5e.cli.commands.convert.get_app_config")
    @patch("dnd5e.core.config.sources.get_content_config")
    @patch("dnd5e.core.services.spell_collector.SpellCollector")
    @patch("dnd5e.cli.commands.convert._render_spellbook")
    @patch("dnd5e.cli.commands.convert.display_manager")
    @patch("pathlib.Path.mkdir")
    @patch("builtins.open")
    def test_convert_spells_with_toc_control(
        self,
        mock_builtin_open,
        mock_mkdir,
        mock_display,
        mock_render_spellbook,
        mock_spell_collector_class,
        mock_user_config,
        mock_app_config,
        mock_tag_resolver,
        mock_omnidexer,
    ):
        """Test spell conversion with TOC control flags."""
        # Mock dependencies
        mock_omnidexer.return_value = Mock(spec=Omnidexer)
        mock_tag_resolver.return_value = Mock(spec=TagResolver)

        # Mock app config with complete structure
        mock_config = Mock()
        mock_config.rendering.latex.document.paper_size = "letter"
        mock_config.rendering.latex.document.fonts = None
        mock_config.rendering.latex.document.font_size = "11pt"
        mock_config.rendering.latex.document.background = "full"
        mock_config.rendering.latex.document.no_outline = False
        mock_config.rendering.latex.document.high_contrast = False
        mock_config.rendering.latex.document.two_column = True
        mock_config.rendering.latex.document.justified_text = False
        mock_config.rendering.latex.document.no_outline = (
            False  # Add the missing no_outline field
        )
        mock_app_config.return_value = mock_config

        # Mock user config with defaults (all None to use app config defaults)
        mock_user_config_obj = Mock()
        mock_user_config_obj.latex.paper_size = None
        mock_user_config_obj.latex.fonts = None
        mock_user_config_obj.latex.font_size = None
        mock_user_config_obj.latex.background = None
        mock_user_config_obj.latex.no_outline = None
        mock_user_config_obj.latex.high_contrast = None
        mock_user_config_obj.latex.two_column = None
        mock_user_config_obj.latex.justified = None
        mock_user_config.return_value = mock_user_config_obj

        # Mock spell collector
        mock_collector = Mock()
        mock_result = Mock()
        mock_result.spells = [Mock(name="Fireball", level=3)]
        mock_result.total_count = 1
        mock_result.unresolved_names = []
        mock_result.suggestions = {}
        mock_result.sources_used = {"PHB"}
        mock_result.get_level_summary.return_value = "1 spell"

        mock_collector.collect_spells.return_value = mock_result
        mock_spell_collector_class.return_value = mock_collector

        # Mock renderer
        mock_render_spellbook.return_value = (
            "\\documentclass{dndbook}\\begin{document}Spells\\end{document}"
        )

        # Mock display manager
        mock_display.progress.return_value.__enter__ = Mock()
        mock_display.progress.return_value.__exit__ = Mock()
        mock_display.add_task.return_value = "task_id"
        mock_display.update_task = Mock()

        # Mock file operations
        mock_file = Mock()
        mock_builtin_open.return_value.__enter__.return_value = mock_file

        # Test with TOC enabled (default)
        result = self.runner.invoke(app, ["convert", "spells", "fireball", "--toc"])
        assert result.exit_code == 0

        # Test with TOC disabled
        result = self.runner.invoke(app, ["convert", "spells", "fireball", "--no-toc"])
        assert result.exit_code == 0

        # Verify renderer was called with correct show_toc parameter
        assert mock_render_spellbook.call_count == 2
        # First call should have show_toc=True, second should have show_toc=False
        first_call_show_toc = mock_render_spellbook.call_args_list[0][0][
            5
        ]  # show_toc parameter
        second_call_show_toc = mock_render_spellbook.call_args_list[1][0][5]
        assert first_call_show_toc is True
        assert second_call_show_toc is False

    def test_convert_spells_file_not_found(self):
        """Test error handling when spell file is not found."""
        result = self.runner.invoke(
            app, ["convert", "spells", "--from-file", "/nonexistent/spells.txt"]
        )

        # Should exit with error
        assert result.exit_code == 1
        assert "Spell file not found" in result.stdout

    @patch("dnd5e.cli.commands.convert.get_omnidexer")
    @patch("dnd5e.cli.commands.convert.get_tag_resolver")
    @patch("dnd5e.core.services.spell_collector.SpellCollector")
    @patch("dnd5e.cli.commands.convert.display_manager")
    def test_convert_spells_no_spells_found(
        self,
        mock_display,
        mock_spell_collector_class,
        mock_tag_resolver,
        mock_omnidexer,
    ):
        """Test error handling when no spells are found."""
        # Mock dependencies
        mock_omnidexer.return_value = Mock(spec=Omnidexer)
        mock_tag_resolver.return_value = Mock(spec=TagResolver)

        # Mock spell collector with no results
        mock_collector = Mock()
        mock_result = Mock()
        mock_result.spells = []
        mock_result.total_count = 0
        mock_result.unresolved_names = ["nonexistent"]
        mock_result.suggestions = {"nonexistent": ["fireball", "magic missile"]}

        mock_collector.collect_spells.return_value = mock_result
        mock_spell_collector_class.return_value = mock_collector

        # Mock display manager
        mock_display.progress.return_value.__enter__ = Mock()
        mock_display.progress.return_value.__exit__ = Mock()
        mock_display.add_task.return_value = "task_id"
        mock_display.update_task = Mock()

        # Test command with nonexistent spell
        result = self.runner.invoke(app, ["convert", "spells", "nonexistent"])

        # Should exit with error
        assert result.exit_code == 1
        assert "No spells found matching criteria" in result.stdout
        assert "could not be found" in result.stdout
        assert "Suggestions" in result.stdout

    @patch("dnd5e.cli.commands.convert.get_omnidexer")
    @patch("dnd5e.cli.commands.convert.get_tag_resolver")
    @patch("dnd5e.cli.commands.convert.get_app_config")
    @patch("dnd5e.core.config.sources.get_content_config")
    @patch("dnd5e.core.services.spell_collector.SpellCollector")
    @patch("dnd5e.cli.commands.convert._render_spellbook")
    @patch("dnd5e.cli.commands.convert.display_manager")
    @patch("pathlib.Path.mkdir")
    @patch("builtins.open")
    def test_convert_spells_with_latex_options(
        self,
        mock_builtin_open,
        mock_mkdir,
        mock_display,
        mock_render_spellbook,
        mock_spell_collector_class,
        mock_user_config,
        mock_app_config,
        mock_tag_resolver,
        mock_omnidexer,
    ):
        """Test spell conversion with LaTeX document options."""
        # Mock dependencies
        mock_omnidexer.return_value = Mock(spec=Omnidexer)
        mock_tag_resolver.return_value = Mock(spec=TagResolver)

        # Mock app config with complete structure
        mock_config = Mock()
        mock_config.rendering.latex.document.paper_size = "letter"
        mock_config.rendering.latex.document.fonts = None
        mock_config.rendering.latex.document.font_size = "11pt"
        mock_config.rendering.latex.document.background = "full"
        mock_config.rendering.latex.document.no_outline = False
        mock_config.rendering.latex.document.high_contrast = False
        mock_config.rendering.latex.document.two_column = True
        mock_config.rendering.latex.document.justified_text = False
        mock_config.rendering.latex.document.no_outline = (
            False  # Add the missing no_outline field
        )
        mock_app_config.return_value = mock_config

        # Mock user config with defaults (all None to use app config defaults)
        mock_user_config_obj = Mock()
        mock_user_config_obj.latex.paper_size = None
        mock_user_config_obj.latex.fonts = None
        mock_user_config_obj.latex.font_size = None
        mock_user_config_obj.latex.background = None
        mock_user_config_obj.latex.no_outline = None
        mock_user_config_obj.latex.high_contrast = None
        mock_user_config_obj.latex.two_column = None
        mock_user_config_obj.latex.justified = None
        mock_user_config.return_value = mock_user_config_obj

        # Mock spell collector
        mock_collector = Mock()
        mock_result = Mock()
        mock_result.spells = [Mock(name="Fireball", level=3)]
        mock_result.total_count = 1
        mock_result.unresolved_names = []
        mock_result.suggestions = {}
        mock_result.sources_used = {"PHB"}
        mock_result.get_level_summary.return_value = "1 spell"

        mock_collector.collect_spells.return_value = mock_result
        mock_spell_collector_class.return_value = mock_collector

        # Mock renderer
        mock_render_spellbook.return_value = (
            "\\documentclass{dndarticle}\\begin{document}Spells\\end{document}"
        )

        # Mock display manager
        mock_display.progress.return_value.__enter__ = Mock()
        mock_display.progress.return_value.__exit__ = Mock()
        mock_display.add_task.return_value = "task_id"
        mock_display.update_task = Mock()

        # Mock file operations
        mock_file = Mock()
        mock_builtin_open.return_value.__enter__.return_value = mock_file

        # Test command with LaTeX options
        result = self.runner.invoke(
            app,
            [
                "convert",
                "spells",
                "fireball",
                "--document-class",
                "dndarticle",
                "--paper",
                "a4",
                "--font-size",
                "12pt",
                "--background",
                "print",
                "--high-contrast",
                "--one-column",
                "--not-justified",
            ],
        )

        # Verify success
        assert result.exit_code == 0
        assert "Spellbook generated" in result.stdout

        # Verify renderer was called with correct LaTeX config
        mock_render_spellbook.assert_called_once()
        call_args = mock_render_spellbook.call_args
        latex_config = call_args[0][2]  # Third argument is latex_config

        assert latex_config.document.document_class == "dndarticle"
        assert latex_config.document.paper_size == "a4"
        assert latex_config.document.font_size == "12pt"
        assert latex_config.document.background == "print"
        assert latex_config.document.high_contrast is True
        assert latex_config.document.two_column is False
        assert latex_config.document.justified_text is False

    @patch("dnd5e.cli.commands.convert.get_omnidexer")
    @patch("dnd5e.cli.commands.convert.get_tag_resolver")
    @patch("dnd5e.cli.commands.convert.get_app_config")
    @patch("dnd5e.core.config.sources.get_content_config")
    @patch("dnd5e.core.services.spell_collector.SpellCollector")
    @patch("dnd5e.cli.commands.convert.display_manager")
    @patch("dnd5e.core.parsers.spell_input.SpellInputParser")
    def test_convert_spells_invalid_level_range(
        self,
        mock_input_parser,
        mock_display,
        mock_spell_collector_class,
        mock_user_config,
        mock_app_config,
        mock_tag_resolver,
        mock_omnidexer,
    ):
        """Test error handling for invalid level range."""
        # Mock dependencies
        mock_omnidexer.return_value = Mock(spec=Omnidexer)
        mock_tag_resolver.return_value = Mock(spec=TagResolver)

        # Mock app config with complete structure
        mock_config = Mock()
        mock_config.rendering.latex.document.paper_size = "letter"
        mock_config.rendering.latex.document.fonts = None
        mock_config.rendering.latex.document.font_size = "11pt"
        mock_config.rendering.latex.document.background = "full"
        mock_config.rendering.latex.document.no_outline = False
        mock_config.rendering.latex.document.high_contrast = False
        mock_config.rendering.latex.document.two_column = True
        mock_config.rendering.latex.document.justified_text = False
        mock_config.rendering.latex.document.no_outline = (
            False  # Add the missing no_outline field
        )
        mock_app_config.return_value = mock_config

        # Mock user config with defaults (all None to use app config defaults)
        mock_user_config_obj = Mock()
        mock_user_config_obj.latex.paper_size = None
        mock_user_config_obj.latex.fonts = None
        mock_user_config_obj.latex.font_size = None
        mock_user_config_obj.latex.background = None
        mock_user_config_obj.latex.no_outline = None
        mock_user_config_obj.latex.high_contrast = None
        mock_user_config_obj.latex.two_column = None
        mock_user_config_obj.latex.justified = None
        mock_user_config.return_value = mock_user_config_obj

        # Mock level range parsing error
        mock_input_parser.parse_level_range.side_effect = ValueError(
            "Invalid level range"
        )

        # Mock display manager
        mock_display.progress.return_value.__enter__ = Mock()
        mock_display.progress.return_value.__exit__ = Mock()
        mock_display.add_task.return_value = "task_id"
        mock_display.update_task = Mock()

        # Test command with invalid level range
        result = self.runner.invoke(
            app, ["convert", "spells", "--class", "wizard", "--level", "invalid"]
        )

        # Should exit with error
        assert result.exit_code == 1
        assert "Invalid level range" in result.stdout

    @patch("dnd5e.cli.commands.convert.get_omnidexer")
    @patch("dnd5e.cli.commands.convert.get_tag_resolver")
    @patch("dnd5e.cli.commands.convert.get_app_config")
    @patch("dnd5e.core.config.sources.get_content_config")
    @patch("dnd5e.core.services.spell_collector.SpellCollector")
    @patch("dnd5e.cli.commands.convert._render_spellbook")
    @patch("dnd5e.cli.commands.convert.display_manager")
    @patch("pathlib.Path.mkdir")
    @patch("builtins.open")
    def test_convert_spells_advanced_filtering(
        self,
        mock_builtin_open,
        mock_mkdir,
        mock_display,
        mock_render_spellbook,
        mock_spell_collector_class,
        mock_user_config,
        mock_app_config,
        mock_tag_resolver,
        mock_omnidexer,
    ):
        """Test spell conversion with advanced filtering options."""
        # Mock dependencies
        mock_omnidexer.return_value = Mock(spec=Omnidexer)
        mock_tag_resolver.return_value = Mock(spec=TagResolver)

        # Mock app config with complete structure
        mock_config = Mock()
        mock_config.rendering.latex.document.paper_size = "letter"
        mock_config.rendering.latex.document.fonts = None
        mock_config.rendering.latex.document.font_size = "11pt"
        mock_config.rendering.latex.document.background = "full"
        mock_config.rendering.latex.document.no_outline = False
        mock_config.rendering.latex.document.high_contrast = False
        mock_config.rendering.latex.document.two_column = True
        mock_config.rendering.latex.document.justified_text = False
        mock_config.rendering.latex.document.no_outline = (
            False  # Add the missing no_outline field
        )
        mock_app_config.return_value = mock_config

        # Mock user config with defaults (all None to use app config defaults)
        mock_user_config_obj = Mock()
        mock_user_config_obj.latex.paper_size = None
        mock_user_config_obj.latex.fonts = None
        mock_user_config_obj.latex.font_size = None
        mock_user_config_obj.latex.background = None
        mock_user_config_obj.latex.no_outline = None
        mock_user_config_obj.latex.high_contrast = None
        mock_user_config_obj.latex.two_column = None
        mock_user_config_obj.latex.justified = None
        mock_user_config.return_value = mock_user_config_obj

        # Mock spell collector
        mock_collector = Mock()
        mock_result = Mock()
        mock_result.spells = [Mock(name="Fireball", level=3)]
        mock_result.total_count = 1
        mock_result.unresolved_names = []
        mock_result.suggestions = {}
        mock_result.sources_used = {"PHB"}
        mock_result.get_level_summary.return_value = "1 evocation spell"

        mock_collector.collect_spells.return_value = mock_result
        mock_spell_collector_class.return_value = mock_collector

        # Mock renderer
        mock_render_spellbook.return_value = (
            "\\documentclass{dndbook}\\begin{document}Evocation Spells\\end{document}"
        )

        # Mock display manager
        mock_display.progress.return_value.__enter__ = Mock()
        mock_display.progress.return_value.__exit__ = Mock()
        mock_display.add_task.return_value = "task_id"
        mock_display.update_task = Mock()

        # Mock file operations
        mock_file = Mock()
        mock_builtin_open.return_value.__enter__.return_value = mock_file

        # Test command with advanced filtering
        result = self.runner.invoke(
            app,
            [
                "convert",
                "spells",
                "--class",
                "wizard",
                "--school",
                "evocation",
                "--damage-type",
                "fire",
                "--max-level",
                "5",
                "--verbal",
                "--somatic",
                "--no-material",
                "--sources",
                "PHB,XGE",
            ],
        )

        # Verify success
        assert result.exit_code == 0
        assert "Spellbook generated" in result.stdout

        # Verify spell collector was called with correct advanced criteria
        mock_collector.collect_spells.assert_called_once()
        criteria = mock_collector.collect_spells.call_args[0][0]
        assert criteria.schools == ["evocation"]
        assert criteria.damage_types == ["fire"]
        assert criteria.max_level == 5
        assert criteria.has_verbal is True
        assert criteria.has_somatic is True
        assert criteria.no_material is True

    @patch("dnd5e.cli.commands.convert.get_omnidexer")
    @patch("dnd5e.cli.commands.convert.get_tag_resolver")
    @patch("dnd5e.cli.commands.convert.get_app_config")
    @patch("dnd5e.core.config.sources.get_content_config")
    @patch("dnd5e.core.services.spell_collector.SpellCollector")
    @patch("dnd5e.cli.commands.convert._render_spellbook")
    @patch("dnd5e.cli.commands.convert.display_manager")
    @patch("pathlib.Path.mkdir")
    @patch("builtins.open")
    def test_convert_spells_custom_title(
        self,
        mock_builtin_open,
        mock_mkdir,
        mock_display,
        mock_render_spellbook,
        mock_spell_collector_class,
        mock_user_config,
        mock_app_config,
        mock_tag_resolver,
        mock_omnidexer,
    ):
        """Test spell conversion with custom title."""
        # Mock dependencies
        mock_omnidexer.return_value = Mock(spec=Omnidexer)
        mock_tag_resolver.return_value = Mock(spec=TagResolver)

        # Mock app config with complete structure
        mock_config = Mock()
        mock_config.rendering.latex.document.paper_size = "letter"
        mock_config.rendering.latex.document.fonts = None
        mock_config.rendering.latex.document.font_size = "11pt"
        mock_config.rendering.latex.document.background = "full"
        mock_config.rendering.latex.document.no_outline = False
        mock_config.rendering.latex.document.high_contrast = False
        mock_config.rendering.latex.document.two_column = True
        mock_config.rendering.latex.document.justified_text = False
        mock_config.rendering.latex.document.no_outline = (
            False  # Add the missing no_outline field
        )
        mock_app_config.return_value = mock_config

        # Mock user config with defaults (all None to use app config defaults)
        mock_user_config_obj = Mock()
        mock_user_config_obj.latex.paper_size = None
        mock_user_config_obj.latex.fonts = None
        mock_user_config_obj.latex.font_size = None
        mock_user_config_obj.latex.background = None
        mock_user_config_obj.latex.no_outline = None
        mock_user_config_obj.latex.high_contrast = None
        mock_user_config_obj.latex.two_column = None
        mock_user_config_obj.latex.justified = None
        mock_user_config.return_value = mock_user_config_obj

        # Mock spell collector
        mock_collector = Mock()
        mock_result = Mock()
        mock_result.spells = [Mock(name="Fireball", level=3)]
        mock_result.total_count = 1
        mock_result.unresolved_names = []
        mock_result.suggestions = {}
        mock_result.sources_used = {"PHB"}
        mock_result.get_level_summary.return_value = "1 spell"

        mock_collector.collect_spells.return_value = mock_result
        mock_spell_collector_class.return_value = mock_collector

        # Mock renderer
        mock_render_spellbook.return_value = (
            "\\documentclass{dndbook}\\begin{document}My Spellbook\\end{document}"
        )

        # Mock display manager
        mock_display.progress.return_value.__enter__ = Mock()
        mock_display.progress.return_value.__exit__ = Mock()
        mock_display.add_task.return_value = "task_id"
        mock_display.update_task = Mock()

        # Mock file operations
        mock_file = Mock()
        mock_builtin_open.return_value.__enter__.return_value = mock_file

        # Test command with custom title
        result = self.runner.invoke(
            app, ["convert", "spells", "fireball", "--title", "My Custom Spellbook"]
        )

        # Verify success
        assert result.exit_code == 0
        assert "Spellbook generated" in result.stdout

        # Verify renderer was called with correct title
        mock_render_spellbook.assert_called_once()
        call_args = mock_render_spellbook.call_args
        context = call_args[0][1]  # Second argument is the context
        assert context.metadata["title"] == "My Custom Spellbook"

"""Tests for adventure conversion CLI commands."""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, PropertyMock, patch

import pytest
from typer.testing import CliRunner

from studiorum.cli.main import app
from studiorum.core.loaders.omnidexer import Omnidexer


@pytest.mark.cli
class TestConvertAdventureCommand:
    """Test adventure conversion command."""

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

    @patch("studiorum.services.Services.omnidexer", new_callable=PropertyMock)
    @patch("studiorum.cli.commands.convert.adventure.create_latex_engine")
    @patch("studiorum.cli.commands.convert.adventure.display_manager")
    def test_convert_adventure_with_file_path(
        self,
        mock_display,
        mock_engine_factory,
        mock_omnidexer,
    ):
        """Test converting adventure from file path."""
        # Mock dependencies - create a mock that passes isinstance checks
        mock_omnidexer_instance = Mock(spec=Omnidexer)
        mock_omnidexer.return_value = mock_omnidexer_instance

        # Mock LaTeX engine
        mock_engine = Mock()
        mock_engine.render_document.return_value = (
            "\\documentclass{article}\\begin{document}Test\\end{document}"
        )
        mock_engine_factory.return_value = mock_engine

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
            output = Path(file_path).with_suffix(".tex")
            result = self.runner.invoke(
                app, ["convert", "adventure", file_path, "--output", str(output)]
            )

            assert result.exit_code == 0, result.output
            assert "Adventure converted" in result.stdout
            assert output.read_text().startswith("\\documentclass")
            output.unlink()

        finally:
            Path(file_path).unlink()

    @patch("studiorum.services.Services.omnidexer", new_callable=PropertyMock)
    @patch(
        "studiorum.core.resolvers.content_resolver.ContentResolver._enrich_content_if_needed"
    )
    @patch("studiorum.cli.commands.convert.adventure.create_latex_engine")
    @patch("studiorum.cli.commands.convert.adventure.display_manager")
    @patch("pathlib.Path.mkdir")
    def test_convert_adventure_with_abbreviation(
        self,
        mock_mkdir,
        mock_display,
        mock_engine_factory,
        mock_enrich_content,
        mock_omnidexer,
    ):
        """Test converting adventure from abbreviation."""
        # Create a proper Adventure instance instead of Mock
        from studiorum.core.models.adventures import Adventure
        from studiorum.core.models.content import Source

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

        # Mock resolver - no longer needed since we're using the real resolver with mocked omnidexer
        # The ContentResolver will be instantiated with our mocked omnidexer
        # and will find the mock_adventure through get_all_by_type

        # Mock LaTeX engine
        mock_engine = Mock()
        mock_engine.render_document.return_value = (
            "\\documentclass{article}\\begin{document}Test\\end{document}"
        )
        mock_engine_factory.return_value = mock_engine

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

    @patch("studiorum.services.Services.omnidexer", new_callable=PropertyMock)
    @patch("studiorum.core.resolvers.ContentResolver")
    def test_convert_adventure_resolution_failure(
        self, mock_resolver_class, mock_omnidexer
    ):
        """Test error handling when content resolution fails."""
        # Mock dependencies
        mock_omnidexer_instance = Mock(spec=Omnidexer)
        mock_omnidexer.return_value = mock_omnidexer_instance

        # Mock failed resolution
        mock_resolver = Mock()
        from studiorum.core.resolvers.content_resolver import (
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
        assert "Error:" in result.stdout or "Did you mean?" in result.stdout

    @patch("studiorum.services.Services.omnidexer", new_callable=PropertyMock)
    @patch("studiorum.services.Services.load_omnidexer")
    @patch("studiorum.cli.commands.convert.adventure.create_latex_engine")
    @patch("studiorum.cli.commands.convert.adventure.display_manager")
    @patch("studiorum.cli.commands.convert.run.compile_pdf")
    def test_convert_adventure_with_pdf_compilation(
        self,
        mock_compile_pdf,
        mock_display,
        mock_engine_factory,
        mock_shared_omnidexer,
        mock_omnidexer,
    ):
        """Test adventure conversion with PDF compilation."""
        # Mock dependencies
        mock_omnidexer_instance = Mock(spec=Omnidexer)
        mock_omnidexer.return_value = mock_omnidexer_instance
        mock_shared_omnidexer.return_value = (
            mock_omnidexer_instance  # Use same mock instance
        )

        # Mock LaTeX engine
        mock_engine = Mock()
        mock_engine.render_document.return_value = (
            "\\documentclass{article}\\begin{document}Test\\end{document}"
        )
        mock_engine_factory.return_value = mock_engine

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
            output = Path(file_path).with_suffix(".tex")
            result = self.runner.invoke(
                app,
                ["convert", "adventure", file_path, "--pdf", "--output", str(output)],
            )

            # Verify success and PDF compilation called
            assert result.exit_code == 0, result.output
            mock_compile_pdf.assert_called_once_with(output, False)
            output.unlink()

        finally:
            Path(file_path).unlink()

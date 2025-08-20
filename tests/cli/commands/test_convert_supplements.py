"""Tests for supplement conversion CLI commands."""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from typer.testing import CliRunner

from dnd5e.cli.main import app
from dnd5e.core.loaders.omnidexer import Omnidexer
from dnd5e.core.text.tag_resolver import TagResolver
from tests.test_helpers import reset_test_environment


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

    @patch("dnd5e.cli.commands.convert.supplement.get_omnidexer")
    @patch("dnd5e.cli.commands.convert.supplement.get_tag_resolver")
    @patch("dnd5e.cli.commands.convert.supplement.create_latex_engine")
    @patch("dnd5e.cli.commands.convert.supplement.display_manager")
    @patch("builtins.open")
    @patch("pathlib.Path.mkdir")
    def test_convert_supplement_with_spells(
        self,
        mock_mkdir,
        mock_builtin_open,
        mock_display,
        mock_engine_factory,
        mock_tag_resolver,
        mock_omnidexer,
    ):
        """Test converting supplement with spells."""
        # Mock file operations
        mock_file = Mock()
        mock_file.read.return_value = json.dumps(self.mock_supplement_data)
        mock_builtin_open.return_value.__enter__.return_value = mock_file

        # Mock dependencies
        mock_omnidexer_instance = Mock(spec=Omnidexer)
        mock_omnidexer.return_value = mock_omnidexer_instance
        mock_tag_resolver_instance = Mock(spec=TagResolver)
        mock_tag_resolver.return_value = mock_tag_resolver_instance

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

    @patch("dnd5e.cli.commands.convert.supplement.get_omnidexer")
    @patch("dnd5e.cli.commands.convert.supplement.get_tag_resolver")
    @patch("dnd5e.cli.commands.convert.supplement.display_manager")
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
        mock_omnidexer_instance = Mock(spec=Omnidexer)
        mock_omnidexer.return_value = mock_omnidexer_instance
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

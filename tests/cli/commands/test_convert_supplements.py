"""Tests for supplement conversion CLI commands."""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, PropertyMock, patch

import pytest
from typer.testing import CliRunner

from studiorum.cli.main import app
from studiorum.core.loaders.omnidexer import Omnidexer
from studiorum.renderers.tags import TagResolver


@pytest.mark.cli
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

    @patch("studiorum.services.Services.omnidexer", new_callable=PropertyMock)
    @patch("studiorum.services.Services.tag_resolver", new_callable=PropertyMock)
    @patch("studiorum.cli.commands.convert.adventure.create_latex_engine")
    @patch("studiorum.cli.commands.convert.adventure.display_manager")
    def test_convert_supplement_with_spells(
        self,
        mock_display,
        mock_engine_factory,
        mock_tag_resolver,
        mock_omnidexer,
    ):
        """Test converting supplement with spells."""
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
            output = Path(file_path).with_suffix(".tex")
            result = self.runner.invoke(
                app, ["convert", "supplement", file_path, "--output", str(output)]
            )

            assert result.exit_code == 0, result.output
            assert "Supplement converted" in result.stdout
            output.unlink()

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

    @patch("studiorum.services.Services.omnidexer", new_callable=PropertyMock)
    @patch("studiorum.services.Services.tag_resolver", new_callable=PropertyMock)
    @patch("studiorum.cli.commands.convert.adventure.display_manager")
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

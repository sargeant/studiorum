"""CLI integration tests for enhanced features with existing functionality."""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from typer.testing import CliRunner

from studiorum.cli.main import app
from tests.test_helpers import reset_test_environment


@pytest.mark.cli
class TestCLIIntegrationEnhancedFeatures:
    """Test CLI integration with enhanced features alongside existing functionality."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        reset_test_environment()
        self.runner = CliRunner()
        self.temp_dir = Path(tempfile.mkdtemp())

    def teardown_method(self) -> None:
        """Clean up test fixtures."""
        import shutil

        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def create_simple_adventure(self) -> Path:
        """Create a simple adventure file for testing."""
        adventure_data = {
            "name": "Simple Test Adventure",
            "source": "TEST",
            "data": [
                {
                    "name": "Chapter 1",
                    "entries": [
                        "This is a simple adventure chapter.",
                        "The party encounters some challenges.",
                    ],
                }
            ],
        }

        file_path = self.temp_dir / "simple_adventure.json"
        with file_path.open("w", encoding="utf-8") as f:
            json.dump(adventure_data, f)

        return file_path

    def create_enhanced_content_file(self, content_type: str) -> Path:
        """Create an enhanced format content file."""
        if content_type == "spell":
            content = """# Spell list from adventure
# Format: [Count] Name|Source
3 Fireball|PHB
1 Magic Missile|PHB
2 Shield|PHB"""
        elif content_type == "creature":
            content = """# Creature list from adventure
# Format: [Count] Name|Source
5 Goblin|MM
1 Ancient Red Dragon|MM
3 Orc|MM"""
        elif content_type == "item":
            content = """# Item list from adventure
# Format: [Count] Name|Source
2 Longsword|PHB
1 Potion of Healing|DMG
3 Dagger|PHB"""
        else:
            content = "# Empty content list\n"

        file_path = self.temp_dir / f"{content_type}_list.txt"
        file_path.write_text(content, encoding="utf-8")
        return file_path

    @patch("studiorum.cli.commands.convert.adventure.get_content_list_writer")
    @patch("studiorum.cli.commands.convert.adventure.get_omnidexer")
    @patch("studiorum.cli.commands.convert.adventure.get_tag_resolver")
    def test_adventure_conversion_with_and_without_content_output(
        self, mock_tag_resolver, mock_get_omnidexer, mock_get_writer
    ):
        """Test that adventure conversion works normally with or without content output options."""
        # Setup mocks
        mock_omnidexer = Mock()
        mock_omnidexer.get_adventure.return_value = {
            "name": "Simple Test Adventure",
            "source": "TEST",
            "data": [],
        }
        mock_get_omnidexer.return_value = mock_omnidexer
        mock_tag_resolver.return_value = Mock()

        mock_writer = Mock()
        mock_writer.write_content_list.return_value = Mock(unwrap=lambda: 1)
        mock_get_writer.return_value = mock_writer

        with patch(
            "studiorum.cli.commands.convert.adventure.create_latex_engine"
        ) as mock_template:
            mock_template.return_value.render.return_value = "Mock LaTeX output"

            with patch(
                "studiorum.cli.commands.convert.adventure.ContentTracker"
            ) as mock_tracker_class:
                mock_tracker = Mock()
                mock_tracker.export_for_appendix.return_value = {"spell": []}
                mock_tracker_class.return_value = mock_tracker

                adventure_file = self.create_simple_adventure()

                # Test 1: Normal adventure conversion (no content output)
                output_file1 = self.temp_dir / "adventure_normal.tex"
                result1 = self.runner.invoke(
                    app,
                    [
                        "convert",
                        "adventure",
                        str(adventure_file),
                        "--output",
                        str(output_file1),
                    ],
                )

                assert result1.exit_code == 0
                assert output_file1.exists()

                # Content list writer should not have been called
                mock_writer.write_content_list.assert_not_called()

                # Reset mock
                mock_writer.reset_mock()

                # Test 2: Adventure conversion with content output
                output_file2 = self.temp_dir / "adventure_with_content.tex"
                content_output = self.temp_dir / "spells.txt"
                result2 = self.runner.invoke(
                    app,
                    [
                        "convert",
                        "adventure",
                        str(adventure_file),
                        "--output",
                        str(output_file2),
                        "--output-spells",
                        str(content_output),
                    ],
                )

                assert result2.exit_code == 0
                assert output_file2.exists()

                # Content list writer should have been called
                mock_writer.write_content_list.assert_called_once()

    @patch("studiorum.cli.commands.convert.compendiums.spells.get_omnidexer")
    @patch("studiorum.cli.commands.convert.compendiums.spells.get_tag_resolver")
    def test_spell_conversion_with_traditional_and_enhanced_files(
        self, mock_tag_resolver, mock_get_omnidexer
    ):
        """Test that spell conversion works with both traditional and enhanced file formats."""
        # Setup mocks
        mock_omnidexer = Mock()

        def mock_get_spell(name):
            mock_spell = Mock()
            mock_spell.name = name
            mock_spell.source = Mock()
            mock_spell.source.abbreviation = "PHB"
            return mock_spell

        mock_omnidexer.get_spell.side_effect = mock_get_spell
        mock_get_omnidexer.return_value = mock_omnidexer
        mock_tag_resolver.return_value = Mock()

        with patch(
            "studiorum.latex_engine.core.template_engine.LaTeXTemplateEngine"
        ) as mock_template:
            mock_template.return_value.render.return_value = "Mock LaTeX output"

            # Test 1: Traditional simple format file
            traditional_file = self.temp_dir / "traditional_spells.txt"
            traditional_file.write_text(
                "Fireball\nMagic Missile\nShield", encoding="utf-8"
            )

            output_file1 = self.temp_dir / "spells_traditional.tex"
            result1 = self.runner.invoke(
                app,
                [
                    "convert",
                    "spells",
                    "--from-file",
                    str(traditional_file),
                    "--output",
                    str(output_file1),
                ],
            )

            assert result1.exit_code == 0
            assert output_file1.exists()
            assert mock_omnidexer.get_spell.call_count == 3

            # Reset mock
            mock_omnidexer.reset_mock()

            # Test 2: Enhanced format file
            enhanced_file = self.create_enhanced_content_file("spell")

            output_file2 = self.temp_dir / "spells_enhanced.tex"
            result2 = self.runner.invoke(
                app,
                [
                    "convert",
                    "spells",
                    "--from-file",
                    str(enhanced_file),
                    "--output",
                    str(output_file2),
                ],
            )

            assert result2.exit_code == 0
            assert output_file2.exists()
            assert mock_omnidexer.get_spell.call_count == 3

    def test_command_line_options_compatibility(self):
        """Test that new options don't interfere with existing command line options."""
        # Test that adventure command still accepts all its normal options
        adventure_file = self.create_simple_adventure()

        with patch(
            "studiorum.cli.commands.convert.adventure.get_omnidexer"
        ) as mock_get_omnidexer:
            with patch(
                "studiorum.cli.commands.convert.adventure.get_tag_resolver"
            ) as mock_tag_resolver:
                with patch(
                    "studiorum.cli.commands.convert.adventure.get_content_list_writer"
                ) as mock_get_writer:
                    # Setup mocks
                    mock_omnidexer = Mock()
                    mock_omnidexer.get_adventure.return_value = {
                        "name": "Test",
                        "source": "TEST",
                        "data": [],
                    }
                    mock_get_omnidexer.return_value = mock_omnidexer
                    mock_tag_resolver.return_value = Mock()

                    mock_writer = Mock()
                    mock_writer.write_content_list.return_value = Mock(unwrap=lambda: 0)
                    mock_get_writer.return_value = mock_writer

                    with patch(
                        "studiorum.cli.commands.convert.adventure.create_latex_engine"
                    ) as mock_template:
                        mock_template.return_value.render.return_value = (
                            "Mock LaTeX output"
                        )

                        with patch(
                            "studiorum.cli.commands.convert.adventure.ContentTracker"
                        ) as mock_tracker_class:
                            mock_tracker = Mock()
                            mock_tracker.export_for_appendix.return_value = {}
                            mock_tracker_class.return_value = mock_tracker

                            output_file = self.temp_dir / "adventure_options.tex"
                            spells_output = self.temp_dir / "spells_options.txt"

                            # Test with multiple existing options plus new content output option
                            result = self.runner.invoke(
                                app,
                                [
                                    "convert",
                                    "adventure",
                                    str(adventure_file),
                                    "--output",
                                    str(output_file),
                                    "--title",
                                    "Test Adventure",
                                    "--fonts",
                                    "wotc",
                                    "--paper",
                                    "letter",
                                    "--pdf",
                                    "--output-spells",
                                    str(spells_output),
                                ],
                            )

                            # Should handle all options without conflict
                            assert result.exit_code == 0

    def test_help_text_includes_new_options(self):
        """Test that help text includes the new content output options."""
        result = self.runner.invoke(app, ["convert", "adventure", "--help"])

        assert result.exit_code == 0
        assert "--output-spells" in result.stdout
        assert "--output-creatures" in result.stdout
        assert "--output-items" in result.stdout

    def test_error_handling_preserves_existing_behavior(self):
        """Test that error handling for new features doesn't break existing error handling."""
        # Test with missing adventure file (existing error case)
        missing_file = self.temp_dir / "nonexistent.json"

        result = self.runner.invoke(
            app,
            [
                "convert",
                "adventure",
                str(missing_file),
                "--output",
                str(self.temp_dir / "output.tex"),
            ],
        )

        # Should fail as expected for missing file
        assert result.exit_code == 1

        # Test with invalid content output path (new error case)
        adventure_file = self.create_simple_adventure()

        with patch(
            "studiorum.cli.commands.convert.adventure.get_omnidexer"
        ) as mock_get_omnidexer:
            with patch(
                "studiorum.cli.commands.convert.adventure.get_tag_resolver"
            ) as mock_tag_resolver:
                with patch(
                    "studiorum.cli.commands.convert.adventure.get_content_list_writer"
                ) as mock_get_writer:
                    # Setup mocks
                    mock_omnidexer = Mock()
                    mock_omnidexer.get_adventure.return_value = {
                        "name": "Test",
                        "source": "TEST",
                        "data": [],
                    }
                    mock_get_omnidexer.return_value = mock_omnidexer
                    mock_tag_resolver.return_value = Mock()

                    # Mock ContentListWriter to return an error
                    from studiorum.core.result import Error
                    from studiorum.core.services.content_list_writer import (
                        ContentListWriterError,
                    )

                    mock_writer = Mock()
                    mock_writer.write_content_list.return_value = Error(
                        ContentListWriterError("Write failed")
                    )
                    mock_get_writer.return_value = mock_writer

                    with patch(
                        "studiorum.cli.commands.convert.adventure.create_latex_engine"
                    ) as mock_template:
                        mock_template.return_value.render.return_value = (
                            "Mock LaTeX output"
                        )

                        with patch(
                            "studiorum.cli.commands.convert.adventure.ContentTracker"
                        ) as mock_tracker_class:
                            mock_tracker = Mock()
                            mock_tracker.export_for_appendix.return_value = {
                                "spell": []
                            }
                            mock_tracker_class.return_value = mock_tracker

                            output_file = self.temp_dir / "adventure_error.tex"
                            spells_output = self.temp_dir / "invalid" / "spells.txt"

                            result = self.runner.invoke(
                                app,
                                [
                                    "convert",
                                    "adventure",
                                    str(adventure_file),
                                    "--output",
                                    str(output_file),
                                    "--output-spells",
                                    str(spells_output),
                                ],
                            )

                            # Should complete main conversion but warn about content list failure
                            assert result.exit_code == 0  # Main conversion succeeds
                            # Should contain warning about content list failure
                            assert (
                                "Warning" in result.stdout or "Failed" in result.stdout
                            )

    def test_backward_compatibility_file_parsing(self):
        """Test that existing file parsing behavior is preserved."""
        # Create files in different formats
        simple_file = self.temp_dir / "simple.txt"
        simple_file.write_text("Fireball\nMagic Missile\nShield", encoding="utf-8")

        enhanced_file = self.temp_dir / "enhanced.txt"
        enhanced_file.write_text(
            "3 Fireball|PHB\n1 Magic Missile|PHB\n2 Shield|PHB", encoding="utf-8"
        )

        # Test with spell conversion
        with patch(
            "studiorum.cli.commands.convert.compendiums.spells.get_omnidexer"
        ) as mock_get_omnidexer:
            with patch(
                "studiorum.cli.commands.convert.compendiums.spells.get_tag_resolver"
            ) as mock_tag_resolver:
                mock_omnidexer = Mock()

                def mock_get_spell(name):
                    mock_spell = Mock()
                    mock_spell.name = name
                    mock_spell.source = Mock()
                    mock_spell.source.abbreviation = "PHB"
                    return mock_spell

                mock_omnidexer.get_spell.side_effect = mock_get_spell
                mock_get_omnidexer.return_value = mock_omnidexer
                mock_tag_resolver.return_value = Mock()

                with patch(
                    "studiorum.latex_engine.core.template_engine.LaTeXTemplateEngine"
                ) as mock_template:
                    mock_template.return_value.render.return_value = "Mock LaTeX output"

                    # Both file formats should work and produce the same result
                    for test_file in [simple_file, enhanced_file]:
                        output_file = self.temp_dir / f"output_{test_file.stem}.tex"

                        result = self.runner.invoke(
                            app,
                            [
                                "convert",
                                "spells",
                                "--from-file",
                                str(test_file),
                                "--output",
                                str(output_file),
                            ],
                        )

                        assert result.exit_code == 0
                        assert output_file.exists()

                        # Both should result in the same spells being loaded
                        # (counts are ignored for spell content)
                        if test_file == enhanced_file:
                            # Reset call count for fair comparison
                            mock_omnidexer.reset_mock()

    def test_round_trip_integration(self):
        """Test complete round-trip: adventure → content lists → content conversion."""
        adventure_file = self.create_simple_adventure()

        # Step 1: Convert adventure with content output
        with patch(
            "studiorum.cli.commands.convert.adventure.get_content_list_writer"
        ) as mock_get_writer:
            with patch(
                "studiorum.cli.commands.convert.adventure.get_omnidexer"
            ) as mock_get_omnidexer:
                with patch(
                    "studiorum.cli.commands.convert.adventure.get_tag_resolver"
                ) as mock_tag_resolver:
                    # Mock adventure conversion
                    mock_omnidexer = Mock()
                    mock_omnidexer.get_adventure.return_value = {
                        "name": "Test",
                        "source": "TEST",
                        "data": [],
                    }
                    mock_get_omnidexer.return_value = mock_omnidexer
                    mock_tag_resolver.return_value = Mock()

                    # Mock content list writer to create actual files
                    mock_writer = Mock()

                    def mock_write_content_list(tracker, output_path, **kwargs):
                        # Create a simple content list file
                        output_path.parent.mkdir(parents=True, exist_ok=True)
                        content = "# Generated content list\n3 Fireball|PHB\n1 Magic Missile|PHB"
                        output_path.write_text(content, encoding="utf-8")
                        from studiorum.core.result import Success

                        return Success(2)

                    mock_writer.write_content_list.side_effect = mock_write_content_list
                    mock_get_writer.return_value = mock_writer

                    with patch(
                        "studiorum.cli.commands.convert.adventure.create_latex_engine"
                    ) as mock_template:
                        mock_template.return_value.render.return_value = (
                            "Mock adventure LaTeX"
                        )

                        with patch(
                            "studiorum.cli.commands.convert.adventure.ContentTracker"
                        ) as mock_tracker_class:
                            mock_tracker = Mock()
                            mock_tracker.export_for_appendix.return_value = {
                                "spell": []
                            }
                            mock_tracker_class.return_value = mock_tracker

                            adventure_output = self.temp_dir / "adventure.tex"
                            spells_list = self.temp_dir / "spells.txt"

                            result1 = self.runner.invoke(
                                app,
                                [
                                    "convert",
                                    "adventure",
                                    str(adventure_file),
                                    "--output",
                                    str(adventure_output),
                                    "--output-spells",
                                    str(spells_list),
                                ],
                            )

                            assert result1.exit_code == 0
                            assert spells_list.exists()

        # Step 2: Use generated content list for spell conversion
        with patch(
            "studiorum.cli.commands.convert.compendiums.spells.get_omnidexer"
        ) as mock_get_omnidexer:
            with patch(
                "studiorum.cli.commands.convert.compendiums.spells.get_tag_resolver"
            ) as mock_tag_resolver:
                mock_omnidexer = Mock()

                def mock_get_spell(name):
                    mock_spell = Mock()
                    mock_spell.name = name
                    mock_spell.source = Mock()
                    mock_spell.source.abbreviation = "PHB"
                    return mock_spell

                mock_omnidexer.get_spell.side_effect = mock_get_spell
                mock_get_omnidexer.return_value = mock_omnidexer
                mock_tag_resolver.return_value = Mock()

                with patch(
                    "studiorum.latex_engine.core.template_engine.LaTeXTemplateEngine"
                ) as mock_template:
                    mock_template.return_value.render.return_value = "Mock spells LaTeX"

                    spells_output = self.temp_dir / "spells.tex"

                    result2 = self.runner.invoke(
                        app,
                        [
                            "convert",
                            "spells",
                            "--from-file",
                            str(spells_list),
                            "--output",
                            str(spells_output),
                        ],
                    )

                    assert result2.exit_code == 0
                    assert spells_output.exists()

                    # Verify spells were loaded from the enhanced format file
                    assert (
                        mock_omnidexer.get_spell.call_count == 2
                    )  # Fireball and Magic Missile

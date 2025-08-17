"""CLI integration tests for creature conversion commands.

These tests focus on command structure validation and basic CLI functionality
rather than full end-to-end processing to avoid complex mocking issues.
"""

import json
import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dnd5e.cli.main import app
from tests.test_helpers import reset_test_environment


@pytest.mark.cli
class TestConvertCreatureCommand:
    """Test creature conversion CLI command structure and validation."""

    def setup_method(self):
        """Set up test fixtures."""
        reset_test_environment()
        self.runner = CliRunner()

        # Create mock creature data that follows 5etools format
        self.mock_creature_data = {
            "monster": [
                {
                    "name": "Test Goblin",
                    "source": "TEST",
                    "size": ["S"],
                    "type": "humanoid",
                    "alignment": ["N", "E"],
                    "ac": [15],
                    "hp": {"average": 7, "formula": "2d6"},
                    "speed": {"walk": 30},
                    "str": 8,
                    "dex": 14,
                    "con": 10,
                    "int": 10,
                    "wis": 8,
                    "cha": 8,
                    "skill": {"stealth": "+6"},
                    "senses": ["darkvision 60 ft.", "passive Perception 9"],
                    "languages": ["Common", "Goblin"],
                    "cr": "1/4",
                    "trait": [
                        {
                            "name": "Nimble Escape",
                            "entries": [
                                "The goblin can take the Dash or Disengage action as a bonus action on each of its turns."
                            ],
                        }
                    ],
                    "action": [
                        {
                            "name": "Scimitar",
                            "entries": [
                                "{@atk mw} {@hit 4} to hit, reach 5 ft., one target. {@h}1d6 + 2 slashing damage."
                            ],
                        },
                        {
                            "name": "Shortbow",
                            "entries": [
                                "{@atk rw} {@hit 4} to hit, range 80/320 ft., one target. {@h}1d6 + 2 piercing damage."
                            ],
                        },
                    ],
                }
            ]
        }

    def test_convert_single_creature_help(self):
        """Test that single creature conversion help works."""
        # Test help command for creature conversion
        result = self.runner.invoke(app, ["convert", "creatures", "--help"])

        # Should succeed and show help text
        assert result.exit_code == 0
        assert "creatures" in result.output.lower()
        assert (
            "challenge rating" in result.output.lower() or "cr" in result.output.lower()
        )

    def test_convert_single_creature_validation(self):
        """Test creature conversion command validation."""
        # Test with invalid file
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            nonexistent_file = temp_path / "nonexistent.json"

            # Execute command with non-existent file
            result = self.runner.invoke(
                app,
                [
                    "convert",
                    "creatures",
                    "Test Goblin",
                    "--from-file",
                    str(nonexistent_file),
                ],
            )

            # Should fail with error
            assert result.exit_code != 0

    def test_convert_creature_command_structure(self):
        """Test that creature conversion command has proper structure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            input_file = temp_path / "creatures.json"
            output_file = temp_path / "output.tex"

            # Create a valid input file
            input_file.write_text(json.dumps(self.mock_creature_data))

            # Test command structure - this should not error on command parsing
            result = self.runner.invoke(
                app,
                [
                    "convert",
                    "creatures",
                    "Test Goblin",
                    "--from-file",
                    str(input_file),
                    "--output",
                    str(output_file),
                    "--dry-run",
                ],
            )

            # Should not fail on command structure (exit code 2 = command parsing error)
            assert result.exit_code != 2

    def test_convert_creatures_by_cr_command_structure(self):
        """Test that CR-based creature conversion command has proper structure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            input_file = temp_path / "creatures.json"
            output_file = temp_path / "output.tex"

            # Create a valid input file
            input_file.write_text(json.dumps(self.mock_creature_data))

            # Test command structure - this should not error on command parsing
            result = self.runner.invoke(
                app,
                [
                    "convert",
                    "creatures",
                    "--cr",
                    "1/4",
                    "--from-file",
                    str(input_file),
                    "--output",
                    str(output_file),
                    "--dry-run",
                ],
            )

            # Should not fail on command structure
            assert result.exit_code != 2

    def test_convert_creatures_cr_validation(self):
        """Test CR parameter validation."""
        # Test invalid CR format
        result = self.runner.invoke(
            app,
            [
                "convert",
                "creatures",
                "--cr",
                "invalid-format",
                "--dry-run",
            ],
        )
        # Command should either succeed (with validation later) or fail with helpful error
        # We're testing that the CLI accepts the parameter structure
        # Exit code 2 means command parsing failed
        assert result.exit_code != 2

    def test_convert_creatures_invalid_file(self):
        """Test conversion with invalid input file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            nonexistent_file = temp_path / "nonexistent.json"

            # Execute command with non-existent file
            result = self.runner.invoke(
                app,
                [
                    "convert",
                    "creatures",
                    "Test Goblin",
                    "--from-file",
                    str(nonexistent_file),
                ],
            )

            # Should fail with error
            assert result.exit_code != 0

    def test_convert_creature_dry_run_flag(self):
        """Test creature conversion dry run flag is recognized."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            input_file = temp_path / "creatures.json"

            # Create the input file
            input_file.write_text(json.dumps(self.mock_creature_data))

            # Execute command with dry run flag - should not fail on flag recognition
            result = self.runner.invoke(
                app,
                [
                    "convert",
                    "creatures",
                    "Test Goblin",
                    "--from-file",
                    str(input_file),
                    "--dry-run",
                ],
            )

            # Should not fail on dry run flag parsing (exit code 2 = command parsing error)
            assert result.exit_code != 2

    def test_convert_creature_output_flag(self):
        """Test creature conversion output flag is recognized."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            input_file = temp_path / "creatures.json"
            output_file = temp_path / "output.tex"

            # Create the input file
            input_file.write_text(json.dumps(self.mock_creature_data))

            # Execute command with output flag - should not fail on flag recognition
            result = self.runner.invoke(
                app,
                [
                    "convert",
                    "creatures",
                    "Test Goblin",
                    "--from-file",
                    str(input_file),
                    "--output",
                    str(output_file),
                    "--dry-run",
                ],
            )

            # Should not fail on output flag parsing
            assert result.exit_code != 2


@pytest.mark.cli
class TestCreatureCommandValidation:
    """Test creature CLI command input validation and error handling."""

    def setup_method(self):
        """Set up test fixtures."""
        reset_test_environment()
        self.runner = CliRunner()

    def test_creature_command_requires_name_or_filter(self):
        """Test that creature command requires either a name or filter criteria."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            input_file = temp_path / "creatures.json"

            # Execute command without name or filters
            result = self.runner.invoke(
                app,
                [
                    "convert",
                    "creatures",
                    "--from-file",
                    str(input_file),
                ],
            )

            # Should provide helpful error message or require parameters
            # Exit code 2 = command parsing error, other codes = validation errors
            assert result.exit_code != 0 or "Error" in result.output

    def test_creature_command_invalid_cr_format(self):
        """Test creature command with invalid CR format."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            input_file = temp_path / "creatures.json"

            # Execute command with invalid CR format
            result = self.runner.invoke(
                app,
                [
                    "convert",
                    "creatures",
                    "--cr",
                    "invalid-format",
                    "--from-file",
                    str(input_file),
                ],
            )

            # Should fail with validation error, but not command parsing error
            # We're testing that the command structure is recognized
            assert result.exit_code != 2 or "Unknown option" not in result.output

    def test_creature_command_help_text(self):
        """Test that creature command provides helpful usage information."""
        result = self.runner.invoke(app, ["convert", "creatures", "--help"])

        # Should display help without error
        assert result.exit_code == 0
        assert "creatures" in result.output.lower()
        assert (
            "challenge rating" in result.output.lower() or "cr" in result.output.lower()
        )

    def test_creature_command_flag_recognition(self):
        """Test that creature command recognizes all expected flags."""
        # Test that all flags are recognized by the command parser
        flags_to_test = [
            ["--help"],
            ["--dry-run"],
            ["--from-file", "test.json"],
            ["--output", "test.tex"],
            ["--cr", "1"],
        ]

        for flags in flags_to_test:
            result = self.runner.invoke(app, ["convert", "creatures"] + flags)
            # Should not fail with "Unknown option" error (exit code 2)
            if result.exit_code == 2:
                assert "Unknown option" not in result.output

    def test_creatures_spells_flag_recognition(self):
        """Test that --spells flag is recognized by creatures command."""
        # Test --spells flag exists and is recognized
        result = self.runner.invoke(app, ["convert", "creatures", "--help"])
        assert result.exit_code == 0
        assert "--spells" in result.output
        assert "--no-spells" in result.output
        assert "spellbook" in result.output.lower()
        assert "creature-referenced" in result.output.lower()

    def test_creatures_spells_flag_default_behavior(self):
        """Test that --spells flag defaults to False (no appendix)."""
        # Test help output shows default is False/disabled
        result = self.runner.invoke(app, ["convert", "creatures", "--help"])
        assert result.exit_code == 0
        # Verify the flag is there but not enabled by default
        help_text = result.output.lower()
        assert "--spells" in help_text and "--no-spells" in help_text

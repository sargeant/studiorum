"""Tests for spell conversion CLI commands."""

from pathlib import Path
from unittest.mock import Mock, PropertyMock, patch

import pytest
from typer.testing import CliRunner

from studiorum.cli.main import app
from studiorum.core.loaders.omnidexer import Omnidexer


@pytest.mark.cli
class TestConvertSpellsCommand:
    """Test spell conversion command."""

    def setup_method(self):
        """Set up test fixtures."""

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

    @patch("studiorum.services.Services.omnidexer", new_callable=PropertyMock)
    @patch("studiorum.core.services.spell_collector.SpellCollector")
    @patch("studiorum.cli.commands.convert.spells._render_spellbook")
    @patch("studiorum.cli.commands.convert.spells.display_manager")
    @patch("pathlib.Path.mkdir")
    def test_convert_spells_with_spell_names(
        self,
        mock_mkdir,
        mock_display,
        mock_render_spellbook,
        mock_spell_collector_class,
        mock_omnidexer,
    ):
        """Test converting specific spells by name."""
        # Mock dependencies
        mock_omnidexer_instance = Mock(spec=Omnidexer)
        mock_omnidexer.return_value = mock_omnidexer_instance

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

        if Path("output").exists():
            shutil.rmtree("output")

    def test_convert_spells_file_not_found(self):
        """Test error handling when spell file is not found."""
        result = self.runner.invoke(
            app, ["convert", "spells", "--from-file", "/nonexistent/spells.txt"]
        )

        # Should exit with error
        assert result.exit_code == 1
        assert "File does not exist" in result.stdout

    @patch("studiorum.services.Services.omnidexer", new_callable=PropertyMock)
    @patch("studiorum.core.services.spell_collector.SpellCollector")
    @patch("studiorum.cli.commands.convert.spells.display_manager")
    def test_convert_spells_no_spells_found(
        self,
        mock_display,
        mock_spell_collector_class,
        mock_omnidexer,
    ):
        """Test error handling when no spells are found."""
        # Mock dependencies
        mock_omnidexer.return_value = Mock(spec=Omnidexer)

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


@pytest.mark.parametrize(
    ("flag", "has_material"), [("--material", True), ("--no-material", False)]
)
def test_material_flag_filters_both_ways(
    flag: str, has_material: bool, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """--material and --no-material set one tri-state filter."""
    from studiorum.core.services.spell_collector import SpellCollector

    monkeypatch.chdir(Path(__file__).resolve().parents[3])
    collected = []
    original = SpellCollector.collect_spells

    def spy(self, criteria):
        result = original(self, criteria)
        collected.append((criteria, result.spells))
        return result

    with patch.object(SpellCollector, "collect_spells", spy):
        result = CliRunner().invoke(
            app,
            [
                "convert",
                "spells",
                "--level",
                "3",
                "--sources",
                "SRD",
                flag,
                "--output",
                str(tmp_path / "spells.tex"),
            ],
        )

    assert result.exit_code == 0, result.output
    criteria, spells = collected[0]
    assert criteria.has_material is has_material
    assert spells
    assert all(spell.has_material_components() is has_material for spell in spells)

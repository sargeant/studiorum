"""Tests for enhanced --from-file support in CLI commands."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from typer.testing import CliRunner

from studiorum.cli.main import app
from tests.test_helpers import reset_test_environment


@pytest.mark.cli
class TestEnhancedFromFileSupport:
    """Test enhanced --from-file support across CLI commands."""

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

    def create_test_file(self, content: str, filename: str = "test_list.txt") -> Path:
        """Create a test file with the given content."""
        file_path = self.temp_dir / filename
        file_path.write_text(content, encoding="utf-8")
        return file_path

    def create_mock_omnidexer(self):
        """Create a mock omnidexer with test data."""
        mock_omnidexer = Mock()

        # Mock spell data
        mock_spell_fireball = Mock()
        mock_spell_fireball.name = "Fireball"
        mock_spell_fireball.source = Mock()
        mock_spell_fireball.source.abbreviation = "PHB"

        mock_spell_magic_missile = Mock()
        mock_spell_magic_missile.name = "Magic Missile"
        mock_spell_magic_missile.source = Mock()
        mock_spell_magic_missile.source.abbreviation = "PHB"

        # Mock creature data
        mock_creature_goblin = Mock()
        mock_creature_goblin.name = "Goblin"
        mock_creature_goblin.source = Mock()
        mock_creature_goblin.source.abbreviation = "MM"

        mock_creature_orc = Mock()
        mock_creature_orc.name = "Orc"
        mock_creature_orc.source = Mock()
        mock_creature_orc.source.abbreviation = "MM"

        # Mock item data
        mock_item_longsword = Mock()
        mock_item_longsword.name = "Longsword"
        mock_item_longsword.source = Mock()
        mock_item_longsword.source.abbreviation = "PHB"

        # Set up omnidexer methods
        def mock_get_spell(name):
            if name == "Fireball":
                return mock_spell_fireball
            elif name == "Magic Missile":
                return mock_spell_magic_missile
            return None

        def mock_get_creature(name):
            if name == "Goblin":
                return mock_creature_goblin
            elif name == "Orc":
                return mock_creature_orc
            return None

        def mock_get_item(name):
            if name == "Longsword":
                return mock_item_longsword
            return None

        mock_omnidexer.get_spell.side_effect = mock_get_spell
        mock_omnidexer.get_creature.side_effect = mock_get_creature
        mock_omnidexer.get_item.side_effect = mock_get_item

        return mock_omnidexer

    @patch("studiorum.cli.commands.convert.compendiums.spells.get_omnidexer")
    @patch("studiorum.cli.commands.convert.compendiums.spells.get_tag_resolver")
    def test_spells_simple_format_backward_compatibility(
        self, mock_tag_resolver, mock_get_omnidexer
    ):
        """Test spells command with simple format (backward compatibility)."""
        # Create test file with simple format
        content = "Fireball\nMagic Missile\nShield"
        file_path = self.create_test_file(content, "spells_simple.txt")

        # Mock dependencies
        mock_omnidexer = self.create_mock_omnidexer()
        mock_get_omnidexer.return_value = mock_omnidexer
        mock_tag_resolver.return_value = Mock()

        with patch(
            "studiorum.latex_engine.core.template_engine.LaTeXTemplateEngine"
        ) as mock_template_class:
            mock_template = Mock()
            mock_template.render_template.return_value = "Mock LaTeX output"
            mock_template_class.return_value = mock_template

            output_file = self.temp_dir / "spells_output.tex"
            result = self.runner.invoke(
                app,
                [
                    "convert",
                    "spells",
                    "--from-file",
                    str(file_path),
                    "--output",
                    str(output_file),
                ],
            )

            assert result.exit_code == 0
            assert output_file.exists()

    @patch("studiorum.cli.commands.convert.compendiums.spells.get_omnidexer")
    @patch("studiorum.cli.commands.convert.compendiums.spells.get_tag_resolver")
    def test_spells_enhanced_format_with_counts(
        self, mock_tag_resolver, mock_get_omnidexer
    ):
        """Test spells command with enhanced format including counts."""
        # Create test file with enhanced format
        content = "3 Fireball|PHB\n1 Magic Missile|PHB\n2 Shield"
        file_path = self.create_test_file(content, "spells_enhanced.txt")

        # Mock dependencies
        mock_omnidexer = self.create_mock_omnidexer()
        mock_get_omnidexer.return_value = mock_omnidexer
        mock_tag_resolver.return_value = Mock()

        with patch(
            "studiorum.latex_engine.core.template_engine.LaTeXTemplateEngine"
        ) as mock_template_class:
            mock_template = Mock()
            mock_template.render_template.return_value = "Mock LaTeX output"
            mock_template_class.return_value = mock_template

            output_file = self.temp_dir / "spells_enhanced_output.tex"
            result = self.runner.invoke(
                app,
                [
                    "convert",
                    "spells",
                    "--from-file",
                    str(file_path),
                    "--output",
                    str(output_file),
                ],
            )

            assert result.exit_code == 0
            assert output_file.exists()

            # For spells, counts should be ignored (spells are unique content)
            # Verify the omnidexer was called for each unique spell
            assert mock_omnidexer.get_spell.call_count == 3

    @patch("studiorum.cli.commands.convert.compendiums.spells.get_omnidexer")
    @patch("studiorum.cli.commands.convert.compendiums.spells.get_tag_resolver")
    def test_spells_enhanced_format_with_sources(
        self, mock_tag_resolver, mock_get_omnidexer
    ):
        """Test spells command respects source specifications."""
        # Create test file with source specifications
        content = "Fireball|PHB\nMagic Missile|XGE\nShield"
        file_path = self.create_test_file(content, "spells_sources.txt")

        # Mock dependencies
        mock_omnidexer = self.create_mock_omnidexer()
        mock_get_omnidexer.return_value = mock_omnidexer
        mock_tag_resolver.return_value = Mock()

        with patch(
            "studiorum.latex_engine.core.template_engine.LaTeXTemplateEngine"
        ) as mock_template_class:
            mock_template = Mock()
            mock_template.render_template.return_value = "Mock LaTeX output"
            mock_template_class.return_value = mock_template

            output_file = self.temp_dir / "spells_sources_output.tex"
            result = self.runner.invoke(
                app,
                [
                    "convert",
                    "spells",
                    "--from-file",
                    str(file_path),
                    "--output",
                    str(output_file),
                ],
            )

            assert result.exit_code == 0
            assert output_file.exists()

    @patch("studiorum.cli.commands.convert.compendiums.creatures.get_omnidexer")
    @patch("studiorum.cli.commands.convert.compendiums.creatures.get_tag_resolver")
    def test_creatures_enhanced_format_with_counts(
        self, mock_tag_resolver, mock_get_omnidexer
    ):
        """Test creatures command with enhanced format and counts for statblocks."""
        # Create test file with counts (relevant for creatures as statblocks)
        content = "3 Goblin|MM\n1 Orc|MM\n5 Kobold"
        file_path = self.create_test_file(content, "creatures_enhanced.txt")

        # Mock dependencies
        mock_omnidexer = self.create_mock_omnidexer()
        mock_get_omnidexer.return_value = mock_omnidexer
        mock_tag_resolver.return_value = Mock()

        with patch(
            "studiorum.latex_engine.core.template_engine.LaTeXTemplateEngine"
        ) as mock_template_class:
            mock_template = Mock()
            mock_template.render_template.return_value = "Mock LaTeX output"
            mock_template_class.return_value = mock_template

            output_file = self.temp_dir / "creatures_enhanced_output.tex"
            result = self.runner.invoke(
                app,
                [
                    "convert",
                    "creatures",
                    "--from-file",
                    str(file_path),
                    "--output",
                    str(output_file),
                ],
            )

            assert result.exit_code == 0
            assert output_file.exists()

            # For creatures with counts, should still load each unique creature once
            # (counts are metadata for statblock generation, not duplication)
            assert mock_omnidexer.get_creature.call_count == 3

    @patch("studiorum.cli.commands.convert.compendiums.items.get_omnidexer")
    @patch("studiorum.cli.commands.convert.compendiums.items.get_tag_resolver")
    def test_items_enhanced_format_with_counts(
        self, mock_tag_resolver, mock_get_omnidexer
    ):
        """Test items command with enhanced format and counts."""
        # Create test file with counts
        content = "2 Longsword|PHB\n1 Shortsword|PHB\n3 Dagger"
        file_path = self.create_test_file(content, "items_enhanced.txt")

        # Mock dependencies
        mock_omnidexer = self.create_mock_omnidexer()
        mock_get_omnidexer.return_value = mock_omnidexer
        mock_tag_resolver.return_value = Mock()

        with patch(
            "studiorum.latex_engine.core.template_engine.LaTeXTemplateEngine"
        ) as mock_template_class:
            mock_template = Mock()
            mock_template.render_template.return_value = "Mock LaTeX output"
            mock_template_class.return_value = mock_template

            output_file = self.temp_dir / "items_enhanced_output.tex"
            result = self.runner.invoke(
                app,
                [
                    "convert",
                    "items",
                    "--from-file",
                    str(file_path),
                    "--output",
                    str(output_file),
                ],
            )

            assert result.exit_code == 0
            assert output_file.exists()

    def test_file_format_validation_error(self):
        """Test error handling for invalid file formats."""
        # Create invalid file (empty)
        file_path = self.create_test_file("", "empty.txt")

        result = self.runner.invoke(
            app,
            [
                "convert",
                "spells",
                "--from-file",
                str(file_path),
                "--output",
                str(self.temp_dir / "output.tex"),
            ],
        )

        assert result.exit_code == 1
        assert "No names found in file" in result.stdout or "Error" in result.stdout

    def test_missing_file_error(self):
        """Test error handling for missing file."""
        missing_file = self.temp_dir / "nonexistent.txt"

        result = self.runner.invoke(
            app,
            [
                "convert",
                "spells",
                "--from-file",
                str(missing_file),
                "--output",
                str(self.temp_dir / "output.tex"),
            ],
        )

        assert result.exit_code == 1
        assert "does not exist" in result.stdout or "Error" in result.stdout

    def test_mixed_format_handling(self):
        """Test handling of mixed format lines in same file."""
        content = """# Mixed format test
Fireball
3 Magic Missile|PHB
Shield|PHB
2 Counterspell
Haste|PHB"""
        file_path = self.create_test_file(content, "mixed_format.txt")

        with patch(
            "studiorum.cli.commands.convert.compendiums.spells.get_omnidexer"
        ) as mock_get_omnidexer:
            with patch(
                "studiorum.cli.commands.convert.compendiums.spells.get_tag_resolver"
            ) as mock_tag_resolver:
                mock_omnidexer = self.create_mock_omnidexer()
                mock_get_omnidexer.return_value = mock_omnidexer
                mock_tag_resolver.return_value = Mock()

                with patch(
                    "studiorum.cli.commands.convert.compendiums.spells.TemplateService"
                ) as mock_template:
                    mock_template.return_value.render.return_value = "Mock LaTeX output"

                    output_file = self.temp_dir / "mixed_output.tex"
                    result = self.runner.invoke(
                        app,
                        [
                            "convert",
                            "spells",
                            "--from-file",
                            str(file_path),
                            "--output",
                            str(output_file),
                        ],
                    )

                    assert result.exit_code == 0
                    assert output_file.exists()

    def test_comments_and_whitespace_handling(self):
        """Test proper handling of comments and whitespace."""
        content = """# This is a spell list

   Fireball   |   PHB   # A fireball spell

# Another comment
3   Magic Missile  |  PHB  # Multiple magic missiles

   Shield   # A shield spell
"""
        file_path = self.create_test_file(content, "comments_whitespace.txt")

        with patch(
            "studiorum.cli.commands.convert.compendiums.spells.get_omnidexer"
        ) as mock_get_omnidexer:
            with patch(
                "studiorum.cli.commands.convert.compendiums.spells.get_tag_resolver"
            ) as mock_tag_resolver:
                mock_omnidexer = self.create_mock_omnidexer()
                mock_get_omnidexer.return_value = mock_omnidexer
                mock_tag_resolver.return_value = Mock()

                with patch(
                    "studiorum.cli.commands.convert.compendiums.spells.TemplateService"
                ) as mock_template:
                    mock_template.return_value.render.return_value = "Mock LaTeX output"

                    output_file = self.temp_dir / "comments_output.tex"
                    result = self.runner.invoke(
                        app,
                        [
                            "convert",
                            "spells",
                            "--from-file",
                            str(file_path),
                            "--output",
                            str(output_file),
                        ],
                    )

                    assert result.exit_code == 0
                    assert output_file.exists()

    def test_zero_count_handling(self):
        """Test handling of zero counts in enhanced format."""
        content = "0 Fireball|PHB\n3 Magic Missile|PHB\n0 Shield"
        file_path = self.create_test_file(content, "zero_counts.txt")

        with patch(
            "studiorum.cli.commands.convert.compendiums.spells.get_omnidexer"
        ) as mock_get_omnidexer:
            with patch(
                "studiorum.cli.commands.convert.compendiums.spells.get_tag_resolver"
            ) as mock_tag_resolver:
                mock_omnidexer = self.create_mock_omnidexer()
                mock_get_omnidexer.return_value = mock_omnidexer
                mock_tag_resolver.return_value = Mock()

                with patch(
                    "studiorum.cli.commands.convert.compendiums.spells.TemplateService"
                ) as mock_template:
                    mock_template.return_value.render.return_value = "Mock LaTeX output"

                    output_file = self.temp_dir / "zero_counts_output.tex"
                    result = self.runner.invoke(
                        app,
                        [
                            "convert",
                            "spells",
                            "--from-file",
                            str(file_path),
                            "--output",
                            str(output_file),
                        ],
                    )

                    assert result.exit_code == 0
                    assert output_file.exists()

                    # Should still load all spells, including those with 0 count
                    assert mock_omnidexer.get_spell.call_count == 3

    def test_large_count_handling(self):
        """Test handling of large counts."""
        content = "100 Fireball|PHB\n999 Magic Missile|PHB"
        file_path = self.create_test_file(content, "large_counts.txt")

        with patch(
            "studiorum.cli.commands.convert.compendiums.spells.get_omnidexer"
        ) as mock_get_omnidexer:
            with patch(
                "studiorum.cli.commands.convert.compendiums.spells.get_tag_resolver"
            ) as mock_tag_resolver:
                mock_omnidexer = self.create_mock_omnidexer()
                mock_get_omnidexer.return_value = mock_omnidexer
                mock_tag_resolver.return_value = Mock()

                with patch(
                    "studiorum.cli.commands.convert.compendiums.spells.TemplateService"
                ) as mock_template:
                    mock_template.return_value.render.return_value = "Mock LaTeX output"

                    output_file = self.temp_dir / "large_counts_output.tex"
                    result = self.runner.invoke(
                        app,
                        [
                            "convert",
                            "spells",
                            "--from-file",
                            str(file_path),
                            "--output",
                            str(output_file),
                        ],
                    )

                    assert result.exit_code == 0
                    assert output_file.exists()

    def test_complex_names_with_special_characters(self):
        """Test handling of complex names with special characters."""
        content = """Bigby's Hand|PHB
3 Tasha's Hideous Laughter|PHB
Mordenkainen's Magnificent Mansion|PHB"""
        file_path = self.create_test_file(content, "complex_names.txt")

        with patch(
            "studiorum.cli.commands.convert.compendiums.spells.get_omnidexer"
        ) as mock_get_omnidexer:
            with patch(
                "studiorum.cli.commands.convert.compendiums.spells.get_tag_resolver"
            ) as mock_tag_resolver:
                # Create more specific mock for complex names
                mock_omnidexer = Mock()

                def mock_get_spell(name):
                    # Return a mock spell for any name
                    mock_spell = Mock()
                    mock_spell.name = name
                    mock_spell.source = Mock()
                    mock_spell.source.abbreviation = "PHB"
                    return mock_spell

                mock_omnidexer.get_spell.side_effect = mock_get_spell
                mock_get_omnidexer.return_value = mock_omnidexer
                mock_tag_resolver.return_value = Mock()

                with patch(
                    "studiorum.cli.commands.convert.compendiums.spells.TemplateService"
                ) as mock_template:
                    mock_template.return_value.render.return_value = "Mock LaTeX output"

                    output_file = self.temp_dir / "complex_names_output.tex"
                    result = self.runner.invoke(
                        app,
                        [
                            "convert",
                            "spells",
                            "--from-file",
                            str(file_path),
                            "--output",
                            str(output_file),
                        ],
                    )

                    assert result.exit_code == 0
                    assert output_file.exists()

                    # Verify all complex names were processed
                    assert mock_omnidexer.get_spell.call_count == 3

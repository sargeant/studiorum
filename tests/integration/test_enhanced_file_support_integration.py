"""Integration tests for enhanced file support workflow."""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from typer.testing import CliRunner

from studiorum.cli.main import app
from tests.test_helpers import reset_test_environment


@pytest.mark.integration
class TestEnhancedFileSupportIntegration:
    """Test end-to-end workflow for enhanced file support."""

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

    def create_test_adventure(self) -> Path:
        """Create a test adventure with inline content."""
        adventure_data = {
            "name": "The Goblin Hideout",
            "source": "TEST",
            "data": [
                {
                    "name": "Chapter 1: The Ambush",
                    "entries": [
                        "As the party travels through the forest, they encounter...",
                        {
                            "type": "statblock",
                            "data": {
                                "name": "Goblin",
                                "source": "MM",
                                "type": "humanoid (goblinoid)",
                                "cr": "1/4",
                            },
                        },
                        "The goblins cast {@spell magic missile} before attacking.",
                        "They wield {@item shortsword|PHB|shortswords}.",
                    ],
                },
                {
                    "name": "Chapter 2: The Hideout",
                    "entries": [
                        "Inside the hideout, the party finds...",
                        {
                            "type": "statblock",
                            "data": {
                                "name": "Hobgoblin Captain",
                                "source": "MM",
                                "type": "humanoid (goblinoid)",
                                "cr": "3",
                            },
                        },
                        "The captain knows {@spell fireball} and carries a {@item longsword}.",
                    ],
                },
            ],
        }

        file_path = self.temp_dir / "goblin_hideout.json"
        with file_path.open("w", encoding="utf-8") as f:
            json.dump(adventure_data, f, indent=2)

        return file_path

    def verify_enhanced_file_format(
        self, file_path: Path, expected_entries: list[tuple[int, str, str | None]]
    ) -> None:
        """Verify a file contains the expected enhanced format entries."""
        assert file_path.exists(), f"File {file_path} should exist"

        content = file_path.read_text(encoding="utf-8")
        lines = [
            line.strip()
            for line in content.split("\n")
            if line.strip() and not line.startswith("#")
        ]

        assert len(lines) == len(expected_entries), (
            f"Expected {len(expected_entries)} entries, got {len(lines)}"
        )

        for i, (expected_count, expected_name, expected_source) in enumerate(
            expected_entries
        ):
            line = lines[i]
            if expected_source:
                expected_line = f"{expected_count} {expected_name}|{expected_source}"
            else:
                expected_line = f"{expected_count} {expected_name}|Unknown"

            assert line == expected_line, (
                f"Line {i}: expected '{expected_line}', got '{line}'"
            )

    @patch("studiorum.cli.commands.convert.adventure.get_content_list_writer")
    @patch("studiorum.cli.commands.convert.adventure.get_omnidexer")
    @patch("studiorum.cli.commands.convert.adventure.get_tag_resolver")
    def test_adventure_to_content_lists_workflow(
        self, mock_tag_resolver, mock_get_omnidexer, mock_get_writer
    ):
        """Test complete workflow from adventure conversion to content list generation."""
        # Setup mocks
        mock_omnidexer = Mock()
        mock_omnidexer.get_adventure.return_value = {
            "name": "The Goblin Hideout",
            "source": "TEST",
            "data": [],
        }
        mock_get_omnidexer.return_value = mock_omnidexer
        mock_tag_resolver.return_value = Mock()

        # Mock ContentListWriter to simulate real file writing
        mock_writer = Mock()

        def mock_write_content_list(tracker, output_path, **kwargs):
            """Mock implementation that writes actual files."""
            content_type_filter = kwargs.get("content_type_filter")
            title = kwargs.get("title", "Test Adventure")

            # Simulate different content based on filter
            if content_type_filter == "spell":
                entries = ["2 Fireball|PHB", "1 Magic Missile|PHB"]
            elif content_type_filter == "creature":
                entries = ["3 Goblin|MM", "1 Hobgoblin Captain|MM"]
            elif content_type_filter == "item":
                entries = ["2 Shortsword|PHB", "1 Longsword|PHB"]
            else:
                entries = []

            # Write file with header
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with output_path.open("w", encoding="utf-8") as f:
                f.write(f"# Generated content list for adventure: {title}\n")
                f.write("# Format: [Count] Name|Source\n")
                f.write("# Generated: 2025-09-15 14:30:00\n")
                f.write("#\n")
                for entry in entries:
                    f.write(f"{entry}\n")

            # Return success with entry count
            from studiorum.core.result import Success

            return Success(len(entries))

        mock_writer.write_content_list.side_effect = mock_write_content_list
        mock_get_writer.return_value = mock_writer

        with patch(
            "studiorum.cli.commands.convert.adventure.create_latex_engine"
        ) as mock_template:
            # Mock the LaTeX engine properly
            mock_engine = Mock()
            mock_engine.render.return_value = "Mock LaTeX output"
            mock_template.return_value = mock_engine

            with patch(
                "studiorum.cli.commands.convert.adventure.ContentTracker"
            ) as mock_tracker_class:
                mock_tracker = Mock()
                mock_tracker_class.return_value = mock_tracker

                # Create test adventure
                adventure_file = self.create_test_adventure()

                # Define output paths
                adventure_output = self.temp_dir / "adventure.tex"
                spells_output = self.temp_dir / "content" / "spells.txt"
                creatures_output = self.temp_dir / "content" / "creatures.txt"
                items_output = self.temp_dir / "content" / "items.txt"

                # Run adventure conversion with content output
                result = self.runner.invoke(
                    app,
                    [
                        "convert",
                        "adventure",
                        str(adventure_file),
                        "--output",
                        str(adventure_output),
                        "--title",
                        "The Goblin Hideout",
                        "--output-spells",
                        str(spells_output),
                        "--output-creatures",
                        str(creatures_output),
                        "--output-items",
                        str(items_output),
                    ],
                )

                assert result.exit_code == 0, (
                    f"Adventure conversion failed: {result.stdout}"
                )

                # Verify all content list files were created
                assert spells_output.exists()
                assert creatures_output.exists()
                assert items_output.exists()

                # Verify content format
                self.verify_enhanced_file_format(
                    spells_output, [(2, "Fireball", "PHB"), (1, "Magic Missile", "PHB")]
                )

                self.verify_enhanced_file_format(
                    creatures_output,
                    [(3, "Goblin", "MM"), (1, "Hobgoblin Captain", "MM")],
                )

                self.verify_enhanced_file_format(
                    items_output, [(2, "Shortsword", "PHB"), (1, "Longsword", "PHB")]
                )

    @patch("studiorum.cli.commands.convert.compendiums.spells.get_omnidexer")
    @patch("studiorum.cli.commands.convert.compendiums.spells.get_tag_resolver")
    @patch("studiorum.cli.config_factory.get_default_sources")
    def test_content_list_to_spells_conversion_workflow(
        self, mock_get_default_sources, mock_tag_resolver, mock_get_omnidexer
    ):
        """Test workflow from content list file to spell conversion."""
        # Create enhanced format content list
        spells_content = """# Generated content list for adventure: The Goblin Hideout
# Format: [Count] Name|Source
# Generated: 2025-09-15 14:30:00
#
2 Fireball|PHB
1 Magic Missile|PHB
3 Shield|PHB"""

        spells_file = self.temp_dir / "spells.txt"
        spells_file.write_text(spells_content, encoding="utf-8")

        # Mock omnidexer
        mock_omnidexer = Mock()

        def mock_get_spell(name):
            from studiorum.core.models.spells import Spell

            # Create a more realistic mock that behaves like a Spell
            mock_spell = Mock(spec=Spell)
            mock_spell.name = name
            mock_spell.source = Mock()
            mock_spell.source.abbreviation = "PHB"
            mock_spell.level = 3 if name == "Fireball" else 1
            # Add other common spell attributes
            mock_spell.school = "evocation"
            mock_spell.time = "1 action"
            mock_spell.range = "150 feet"
            mock_spell.components = "V, S, M"
            mock_spell.duration = "Instantaneous"
            mock_spell.entries = [f"A mock {name} spell for testing."]
            return mock_spell

        def mock_find_all(content_type, name):
            # Return a list containing one mock spell for the given name
            return [mock_get_spell(name)]

        mock_omnidexer.get_spell.side_effect = mock_get_spell
        mock_omnidexer.find_all.side_effect = mock_find_all
        mock_get_omnidexer.return_value = mock_omnidexer
        mock_tag_resolver.return_value = Mock()

        # Mock default sources to return a list of source abbreviations
        mock_get_default_sources.return_value = ["PHB", "MM", "XGE"]

        with patch(
            "studiorum.cli.commands.convert.compendiums.spells._render_spellbook"
        ) as mock_render_spellbook:
            # Mock the render spellbook function to return a simple string
            mock_render_spellbook.return_value = "Mock LaTeX output for spells"

            output_file = self.temp_dir / "spells_compendium.tex"

            # Convert spells using enhanced file format
            result = self.runner.invoke(
                app,
                [
                    "convert",
                    "spells",
                    "--from-file",
                    str(spells_file),
                    "--output",
                    str(output_file),
                    "--title",
                    "Spells from The Goblin Hideout",
                ],
            )

            assert result.exit_code == 0, f"Spell conversion failed: {result.stdout}"
            assert output_file.exists()

            # Verify all spells were loaded (counts ignored for spells)
            # SpellCollector uses find_all, not get_spell
            assert mock_omnidexer.find_all.call_count == 3

    @patch("studiorum.cli.commands.convert.compendiums.creatures.get_omnidexer")
    @patch("studiorum.cli.commands.convert.compendiums.creatures.get_tag_resolver")
    @patch("studiorum.cli.config_factory.get_default_sources")
    def test_content_list_to_creatures_conversion_workflow(
        self, mock_get_default_sources, mock_tag_resolver, mock_get_omnidexer
    ):
        """Test workflow from content list file to creature conversion."""
        # Create enhanced format content list
        creatures_content = """# Generated content list for adventure: The Goblin Hideout
# Format: [Count] Name|Source
# Generated: 2025-09-15 14:30:00
#
5 Goblin|MM
1 Hobgoblin Captain|MM
2 Orc|MM"""

        creatures_file = self.temp_dir / "creatures.txt"
        creatures_file.write_text(creatures_content, encoding="utf-8")

        # Mock omnidexer
        mock_omnidexer = Mock()

        def mock_get_creature(name):
            from studiorum.core.models.creatures import Creature

            mock_creature = Mock(spec=Creature)
            mock_creature.name = name
            mock_creature.source = Mock()
            mock_creature.source.abbreviation = "MM"
            mock_creature.cr = "1/4" if "Goblin" in name else "1"
            return mock_creature

        def mock_find_all_creatures(content_type, name):
            # Return a list containing one mock creature for the given name
            # Only return creatures if the name matches our test data
            test_creatures = ["Goblin", "Hobgoblin Captain", "Orc"]
            if name in test_creatures:
                return [mock_get_creature(name)]
            return []

        def mock_find_creature(content_type, name, source=None):
            # Mock for omnidexer.find() method - this is used when specific sources are provided
            test_creatures = ["Goblin", "Hobgoblin Captain", "Orc"]
            if name in test_creatures and (source is None or source == "MM"):
                return mock_get_creature(name)
            return None

        mock_omnidexer.get_creature.side_effect = mock_get_creature
        mock_omnidexer.find_all.side_effect = mock_find_all_creatures
        mock_omnidexer.find.side_effect = mock_find_creature

        # Mock get_all_by_type and get_all_by_source methods that CreatureCollector uses
        mock_omnidexer.get_all_by_type.return_value = [
            mock_get_creature("Goblin"),
            mock_get_creature("Hobgoblin Captain"),
            mock_get_creature("Orc"),
        ]
        mock_omnidexer.get_all_by_source.return_value = [
            mock_get_creature("Goblin"),
            mock_get_creature("Hobgoblin Captain"),
            mock_get_creature("Orc"),
        ]

        mock_get_omnidexer.return_value = mock_omnidexer
        mock_tag_resolver.return_value = Mock()

        # Mock default sources to return a list of source abbreviations
        mock_get_default_sources.return_value = ["PHB", "MM", "XGE"]

        with patch(
            "studiorum.cli.commands.convert.compendiums.creatures._render_bestiary"
        ) as mock_render_creatures:
            # Mock the render bestiary function to return a simple string
            mock_render_creatures.return_value = "Mock LaTeX output for creatures"

            output_file = self.temp_dir / "creatures_statblocks.tex"

            # Convert creatures using enhanced file format
            result = self.runner.invoke(
                app,
                [
                    "convert",
                    "creatures",
                    "--from-file",
                    str(creatures_file),
                    "--output",
                    str(output_file),
                    "--title",
                    "Creatures from The Goblin Hideout",
                ],
            )

            assert result.exit_code == 0, f"Creature conversion failed: {result.stdout}"
            assert output_file.exists()

            # Verify all creatures were loaded
            # CreatureCollector uses find() when specific sources are provided (like "Goblin|MM")
            assert mock_omnidexer.find.call_count == 3

    @patch("studiorum.cli.commands.convert.compendiums.items.get_omnidexer")
    @patch("studiorum.cli.commands.convert.compendiums.items.get_tag_resolver")
    @patch("studiorum.cli.config_factory.get_default_sources")
    def test_content_list_to_items_conversion_workflow(
        self, mock_get_default_sources, mock_tag_resolver, mock_get_omnidexer
    ):
        """Test workflow from content list file to item conversion."""
        # Create enhanced format content list
        items_content = """# Generated content list for adventure: The Goblin Hideout
# Format: [Count] Name|Source
# Generated: 2025-09-15 14:30:00
#
3 Shortsword|PHB
1 Longsword|PHB
2 Dagger|PHB"""

        items_file = self.temp_dir / "items.txt"
        items_file.write_text(items_content, encoding="utf-8")

        # Mock omnidexer
        mock_omnidexer = Mock()

        def mock_get_item(name):
            # Copy the exact pattern from spells test but for items
            from studiorum.core.models.items import Item

            # Create a more realistic mock that behaves like an Item
            mock_item = Mock(spec=Item)
            mock_item.name = name
            mock_item.source = Mock()
            mock_item.source.abbreviation = "PHB"
            mock_item.type = "weapon"
            # Add other common item attributes (like spells test adds spell attributes)
            mock_item.weight = 1.0
            mock_item.value = 200
            mock_item.rarity = "common"
            mock_item.is_magic_item.return_value = False
            return mock_item

        def mock_find_all_items(content_type, name):
            # Return a list containing one mock item for the given name
            test_items = ["Shortsword", "Longsword", "Dagger"]
            if name in test_items:
                return [mock_get_item(name)]
            return []

        def mock_find_item(content_type, name, source=None):
            # Mock for omnidexer.find() method - not actually used by ItemCollector
            test_items = ["Shortsword", "Longsword", "Dagger"]
            if name in test_items and (source is None or source == "PHB"):
                return mock_get_item(name)
            return None

        mock_omnidexer.get_item.side_effect = mock_get_item
        mock_omnidexer.find_all.side_effect = mock_find_all_items
        mock_omnidexer.find.side_effect = mock_find_item

        # Mock get_all_by_type and get_all_by_source methods that ItemCollector uses
        mock_omnidexer.get_all_by_type.return_value = [
            mock_get_item("Shortsword"),
            mock_get_item("Longsword"),
            mock_get_item("Dagger"),
        ]
        mock_omnidexer.get_all_by_source.return_value = [
            mock_get_item("Shortsword"),
            mock_get_item("Longsword"),
            mock_get_item("Dagger"),
        ]

        mock_get_omnidexer.return_value = mock_omnidexer
        mock_tag_resolver.return_value = Mock()

        # Mock default sources to return a list of source abbreviations
        mock_get_default_sources.return_value = ["PHB", "MM", "XGE"]

        with (
            patch(
                "studiorum.cli.commands.convert.compendiums.items._render_itemcompendium"
            ) as mock_render_items,
            patch(
                "studiorum.core.services.item_collector.ItemCollector._get_item_value_in_gp"
            ) as mock_get_value,
        ):
            # Mock the render itemcompendium function to return a simple string
            mock_render_items.return_value = "Mock LaTeX output for items"
            # Mock the value getter to avoid Mock comparison issues
            mock_get_value.return_value = 2.0  # 2 GP

            output_file = self.temp_dir / "items_compendium.tex"

            # Convert items using enhanced file format
            result = self.runner.invoke(
                app,
                [
                    "convert",
                    "items",
                    "--from-file",
                    str(items_file),
                    "--output",
                    str(output_file),
                    "--title",
                    "Items from The Goblin Hideout",
                ],
            )

            assert result.exit_code == 0, f"Item conversion failed: {result.stdout}"
            assert output_file.exists()

            # Verify all items were loaded
            # ItemCollector uses find_all(), not find() like CreatureCollector does
            assert mock_omnidexer.find_all.call_count == 3

    def test_round_trip_workflow_without_mocks(self):
        """Test round-trip workflow without heavy mocking (file format only)."""
        # This test focuses on file format parsing without requiring omnidexer

        # Step 1: Create a content list in enhanced format
        original_content = """# Adventure content list
# Format: [Count] Name|Source
#
3 Goblin|MM
1 Ancient Red Dragon|MM
2 Fireball|PHB
5 Magic Missile|PHB
1 Longsword|PHB
2 Potion of Healing|DMG"""

        content_file = self.temp_dir / "mixed_content.txt"
        content_file.write_text(original_content, encoding="utf-8")

        # Step 2: Test that the file can be parsed correctly
        from studiorum.core.loaders.content_sources import NameListFileSource
        from studiorum.core.models.content import ContentType

        # Test parsing as different content types
        for content_type in [ContentType.CREATURE, ContentType.SPELL, ContentType.ITEM]:
            source = NameListFileSource(content_file, content_type)

            # Validate the source
            validation = source.validate()
            assert validation.is_valid, (
                f"Validation failed for {content_type}: {validation.errors}"
            )

            # Load structured data
            structured_data = source.load_structured()
            assert len(structured_data) == 6, f"Expected 6 entries for {content_type}"

            # Verify first entry
            count, name, source_abbr = structured_data[0]
            assert count == 3
            assert name == "Goblin"
            assert source_abbr == "MM"

            # Load regular names (backward compatibility)
            names = source.load()
            expected_names = [
                "Goblin",
                "Ancient Red Dragon",
                "Fireball",
                "Magic Missile",
                "Longsword",
                "Potion of Healing",
            ]
            assert names == expected_names

    def test_error_handling_integration(self):
        """Test error handling in integrated workflow."""
        # Test with invalid file format
        invalid_content = """This is not a valid format
No counts or sources here
Just random text"""

        invalid_file = self.temp_dir / "invalid.txt"
        invalid_file.write_text(invalid_content, encoding="utf-8")

        # Should handle parsing gracefully
        from studiorum.core.loaders.content_sources import NameListFileSource
        from studiorum.core.models.content import ContentType

        source = NameListFileSource(invalid_file, ContentType.SPELL)

        # Should be able to parse as simple names (backward compatibility)
        structured_data = source.load_structured()
        assert len(structured_data) == 3

        # All should have count=1 and source=None
        for count, name, source_abbr in structured_data:
            assert count == 1
            assert source_abbr is None
            assert name in [
                "This is not a valid format",
                "No counts or sources here",
                "Just random text",
            ]

    def test_mixed_content_type_workflow(self):
        """Test workflow with mixed content types in various combinations."""
        # Create content lists with different formats
        formats = {
            "simple": "Goblin\nFireball\nLongsword",
            "counts": "3 Goblin\n2 Fireball\n1 Longsword",
            "sources": "Goblin|MM\nFireball|PHB\nLongsword|PHB",
            "full": "3 Goblin|MM\n2 Fireball|PHB\n1 Longsword|PHB",
        }

        for format_name, content in formats.items():
            file_path = self.temp_dir / f"{format_name}_format.txt"
            file_path.write_text(content, encoding="utf-8")

            # Test parsing with each format
            from studiorum.core.loaders.content_sources import NameListFileSource
            from studiorum.core.models.content import ContentType

            source = NameListFileSource(file_path, ContentType.CREATURE)

            # Should always parse successfully
            validation = source.validate()
            assert validation.is_valid, (
                f"{format_name} format failed validation: {validation.errors}"
            )

            structured_data = source.load_structured()
            assert len(structured_data) == 3, (
                f"{format_name} format should have 3 entries"
            )

            # Verify names are always present
            names = [name for _, name, _ in structured_data]
            assert "Goblin" in names
            assert "Fireball" in names
            assert "Longsword" in names

"""Tests for Omnidexer system."""

from typing import Any

import pytest

from dnd5e.core.loaders.json_loader import JsonDataLoader  # type: ignore
from dnd5e.core.loaders.omnidexer import IndexEntry, Omnidexer  # type: ignore
from dnd5e.core.loaders.source_manager import FileSystemSourceManager  # type: ignore
from dnd5e.core.models.classes import (  # type: ignore
    Class,
    ClassFeature,
    SubclassFeature,
)
from dnd5e.core.models.content import ContentType  # type: ignore


class TestIndexEntry:
    """Tests for IndexEntry class."""

    def test_index_entry_creation(self, sample_spell: Any) -> None:
        """Test IndexEntry creation."""
        entry = IndexEntry.create(sample_spell, ContentType.SPELL)

        assert entry.content == sample_spell
        assert entry.content_type == ContentType.SPELL
        assert entry.hash_id is not None
        assert len(entry.hash_id) == 8  # MD5 hash truncated to 8 chars
        assert entry.lookup_key == "fireball|phb"


class TestOmnidexer:
    """Tests for Omnidexer class."""

    def test_omnidexer_creation(self) -> None:
        """Test basic omnidexer creation."""
        omnidexer: Any = Omnidexer()
        assert omnidexer is not None
        assert len(omnidexer._loaders) > 0  # Should have default loaders

    def test_loader_registration(self) -> None:
        """Test registering custom loaders."""
        omnidexer: Any = Omnidexer()
        loader = JsonDataLoader.create_for_type(ContentType.SPELL)
        omnidexer.register_loader(ContentType.SPELL, loader)

        assert ContentType.SPELL in omnidexer._loaders
        assert omnidexer._loaders[ContentType.SPELL] == loader

    @pytest.mark.asyncio
    async def test_empty_data_loading(self, temp_data_dir: Any) -> None:
        """Test loading with no data files."""
        source_manager: Any = FileSystemSourceManager(temp_data_dir.parent)
        source_manager.path_config.data_path = temp_data_dir

        omnidexer: Any = Omnidexer(source_manager)
        stats = await omnidexer.load_all_data()

        # Should handle empty directories gracefully
        assert isinstance(stats, dict)

    @pytest.mark.asyncio
    async def test_data_loading_and_indexing(self, loaded_omnidexer: Any) -> None:
        """Test data loading and indexing."""
        omnidexer = loaded_omnidexer
        stats = omnidexer.get_statistics()

        assert stats["total_items"] > 0
        assert ContentType.SPELL.value in stats["by_type"]
        assert ContentType.CREATURE.value in stats["by_type"]

    @pytest.mark.asyncio
    async def test_find_by_type_and_name(self, loaded_omnidexer: Any) -> None:
        """Test finding content by type and name."""
        omnidexer = loaded_omnidexer

        # Find spell
        spell = omnidexer.find(ContentType.SPELL, "Fireball", "PHB")
        assert spell is not None
        assert spell.name == "Fireball"

        # Find creature
        creature = omnidexer.find(ContentType.CREATURE, "Ancient Red Dragon", "MM")
        assert creature is not None
        assert creature.name == "Ancient Red Dragon"

        # Test not found
        not_found = omnidexer.find(ContentType.SPELL, "Nonexistent Spell", "PHB")
        assert not_found is None

    @pytest.mark.asyncio
    async def test_find_without_source(self, loaded_omnidexer: Any) -> None:
        """Test finding content without specifying source."""
        omnidexer = loaded_omnidexer
        spell = omnidexer.find(ContentType.SPELL, "Fireball")
        assert spell is not None
        assert spell.name == "Fireball"

    @pytest.mark.asyncio
    async def test_find_all_by_name(self, loaded_omnidexer: Any) -> None:
        """Test finding all content with same name."""
        omnidexer = loaded_omnidexer
        spells = omnidexer.find_all(ContentType.SPELL, "Fireball")
        assert len(spells) >= 1
        assert all(spell.name == "Fireball" for spell in spells)

    @pytest.mark.asyncio
    async def test_get_all_by_type(self, loaded_omnidexer: Any) -> None:
        """Test getting all content of a specific type."""
        omnidexer = loaded_omnidexer
        all_spells = omnidexer.get_all_by_type(ContentType.SPELL)
        assert len(all_spells) >= 1
        assert all(
            hasattr(spell, "level") for spell in all_spells
        )  # Spell-specific check

        all_creatures = omnidexer.get_all_by_type(ContentType.CREATURE)
        assert len(all_creatures) >= 1
        assert all(
            hasattr(creature, "strength") for creature in all_creatures
        )  # Creature-specific check

    @pytest.mark.asyncio
    async def test_get_all_by_source(self, loaded_omnidexer: Any) -> None:
        """Test getting all content from a specific source."""
        omnidexer = loaded_omnidexer
        phb_content = omnidexer.get_all_by_source("PHB")
        assert len(phb_content) >= 1
        assert all(content.source.abbreviation == "PHB" for content in phb_content)

        mm_content = omnidexer.get_all_by_source("MM")
        assert len(mm_content) >= 1
        assert all(content.source.abbreviation == "MM" for content in mm_content)

    @pytest.mark.asyncio
    async def test_search_functionality(self, loaded_omnidexer: Any) -> None:
        """Test search functionality."""
        omnidexer = loaded_omnidexer

        # Search across all types
        results = omnidexer.search("Fire")
        assert len(results) >= 1
        assert any("Fire" in result.name for result in results)

        # Search within specific type
        spell_results = omnidexer.search("Fire", ContentType.SPELL)
        assert len(spell_results) >= 1
        assert all(hasattr(result, "level") for result in spell_results)

    @pytest.mark.asyncio
    async def test_search_by_name_prefix(self, loaded_omnidexer: Any) -> None:
        """Test prefix-based search."""
        omnidexer = loaded_omnidexer
        results = omnidexer.search_by_name_prefix("Fire")
        assert len(results) >= 1
        assert any(result.name.startswith("Fire") for result in results)

    @pytest.mark.asyncio
    async def test_is_loaded_check(self, loaded_omnidexer: Any) -> None:
        """Test checking if content types are loaded."""
        omnidexer = loaded_omnidexer
        assert omnidexer.is_loaded(ContentType.SPELL)
        assert omnidexer.is_loaded(ContentType.CREATURE)

        # Test unloaded type
        assert not omnidexer.is_loaded(ContentType.SPELL_FLUFF)

    @pytest.mark.asyncio
    async def test_statistics(self, loaded_omnidexer: Any) -> None:
        """Test statistics generation."""
        omnidexer = loaded_omnidexer
        stats = omnidexer.get_statistics()

        assert "total_items" in stats
        assert "by_type" in stats
        assert "by_source" in stats
        assert "loaded_types" in stats

        assert stats["total_items"] > 0
        assert len(stats["by_type"]) >= 2  # At least spells and creatures
        assert len(stats["by_source"]) >= 2  # At least PHB and MM


class TestDeepIndexing:
    """Tests for DeepIndexable protocol and deep indexing functionality."""

    @pytest.mark.asyncio
    async def test_deep_indexing_enabled_by_default(self) -> None:
        """Test that deep indexing is enabled by default."""
        omnidexer = Omnidexer()
        assert omnidexer.enable_deep_indexing is True

    @pytest.mark.asyncio
    async def test_deep_indexing_can_be_disabled(self) -> None:
        """Test that deep indexing can be disabled."""
        omnidexer = Omnidexer(enable_deep_indexing=False)
        assert omnidexer.enable_deep_indexing is False

    @pytest.mark.asyncio
    async def test_class_feature_parsing(self) -> None:
        """Test parsing of class feature references."""
        # Create a sample Class with classFeatures
        class_data = {
            "name": "Fighter",
            "source": {"abbreviation": "PHB", "name": "Player's Handbook"},
            "hd": {"number": 1, "faces": 10},
            "proficiency": ["str", "con"],
            "classFeatures": [
                "Fighting Style|Fighter||1",
                "Second Wind|Fighter||1",
                "Action Surge|Fighter||2",
                {
                    "classFeature": "Martial Archetype|Fighter||3",
                    "gainSubclassFeature": True,
                },
            ],
            "subclasses": [],
        }

        fighter_class = Class(**class_data)
        omnidexer = Omnidexer()

        # Get deep index entries
        nested_content = fighter_class.get_deep_index_entries(omnidexer)

        # Should have 4 class features
        assert len(nested_content) == 4
        assert all(isinstance(item, ClassFeature) for item in nested_content)

        # Check specific features
        feature_names = [item.name for item in nested_content]
        assert "Fighting Style" in feature_names
        assert "Second Wind" in feature_names
        assert "Action Surge" in feature_names
        assert "Martial Archetype" in feature_names

    @pytest.mark.asyncio
    async def test_subclass_feature_parsing(self) -> None:
        """Test parsing of subclass feature references."""
        # Create a sample Class with subclass features
        class_data = {
            "name": "Fighter",
            "source": {"abbreviation": "PHB", "name": "Player's Handbook"},
            "hd": {"number": 1, "faces": 10},
            "proficiency": ["str", "con"],
            "classFeatures": [],
            "subclasses": [
                {
                    "name": "Champion",
                    "shortName": "Champion",
                    "source": "PHB",
                    "className": "Fighter",
                    "classSource": "PHB",
                    "subclassFeatures": [
                        "Champion|Fighter||Champion||3",
                        "Remarkable Athlete|Fighter||Champion||7",
                        "Superior Critical|Fighter||Champion||15",
                    ],
                }
            ],
        }

        fighter_class = Class(**class_data)
        omnidexer = Omnidexer()

        # Get deep index entries
        nested_content = fighter_class.get_deep_index_entries(omnidexer)

        # Should have 3 subclass features
        assert len(nested_content) == 3
        assert all(isinstance(item, SubclassFeature) for item in nested_content)

        # Check specific features
        feature_names = [item.name for item in nested_content]
        assert "Champion" in feature_names
        assert "Remarkable Athlete" in feature_names
        assert "Superior Critical" in feature_names

        # Check subclass specific fields
        champion_feature = next(
            item for item in nested_content if item.name == "Champion"
        )
        assert isinstance(champion_feature, SubclassFeature)
        assert champion_feature.subclass_short_name == "Champion"
        assert champion_feature.level == 3

    @pytest.mark.asyncio
    async def test_deep_indexing_integration(self, temp_data_dir: Any) -> None:
        """Test that deep indexing works with the full omnidexer system."""
        # Create a simple class data file
        import json
        from pathlib import Path

        # Create the class subdirectory
        class_dir = temp_data_dir / "class"
        class_dir.mkdir(exist_ok=True)
        class_file = class_dir / "test-classes.json"
        class_data = {
            "class": [
                {
                    "name": "Fighter",
                    "source": "PHB",
                    "hd": {"number": 1, "faces": 10},
                    "proficiency": ["str", "con"],
                    "classFeatures": [
                        "Fighting Style|Fighter||1",
                        "Second Wind|Fighter||1",
                    ],
                    "subclasses": [
                        {
                            "name": "Champion",
                            "shortName": "Champion",
                            "source": "PHB",
                            "className": "Fighter",
                            "classSource": "PHB",
                            "subclassFeatures": ["Champion|Fighter||Champion||3"],
                        }
                    ],
                }
            ]
        }

        with open(class_file, "w") as f:
            json.dump(class_data, f)

        # Set up omnidexer with temp directory
        source_manager = FileSystemSourceManager(temp_data_dir.parent)
        source_manager.path_config.data_path = temp_data_dir
        omnidexer = Omnidexer(source_manager)

        # Load data and check indexing
        await omnidexer.load_all_data()

        # Should have indexed the class
        fighter = omnidexer.find(ContentType.CLASS, "Fighter", "PHB")
        assert fighter is not None
        assert fighter.name == "Fighter"

        # Should have indexed the class features due to deep indexing
        fighting_style = omnidexer.find(
            ContentType.CLASS_FEATURE, "Fighting Style", "PHB"
        )
        assert fighting_style is not None
        assert fighting_style.name == "Fighting Style"
        assert isinstance(fighting_style, ClassFeature)
        assert fighting_style.level == 1

        second_wind = omnidexer.find(ContentType.CLASS_FEATURE, "Second Wind", "PHB")
        assert second_wind is not None
        assert second_wind.name == "Second Wind"

        # Should have indexed the subclass features
        champion = omnidexer.find(ContentType.SUBCLASS_FEATURE, "Champion", "PHB")
        assert champion is not None
        assert champion.name == "Champion"
        assert isinstance(champion, SubclassFeature)
        assert champion.level == 3

    @pytest.mark.asyncio
    async def test_deep_indexing_cycle_prevention(self) -> None:
        """Test that deep indexing prevents infinite cycles."""
        omnidexer = Omnidexer()

        # Create a class
        class_data = {
            "name": "Fighter",
            "source": {"abbreviation": "PHB", "name": "Player's Handbook"},
            "hd": {"number": 1, "faces": 10},
            "proficiency": ["str", "con"],
            "classFeatures": ["Fighting Style|Fighter||1"],
            "subclasses": [],
        }
        fighter_class = Class(**class_data)

        # Index the class (which should trigger deep indexing)
        omnidexer._add_to_index(fighter_class, ContentType.CLASS)

        # Try to index the same class again - should be prevented
        initial_count = len(omnidexer._index)
        omnidexer._add_to_index(fighter_class, ContentType.CLASS)
        final_count = len(omnidexer._index)

        # Count should not increase (no duplicates)
        assert final_count == initial_count

        # Should still be able to find the class and its features
        found_class = omnidexer.find(ContentType.CLASS, "Fighter", "PHB")
        assert found_class is not None

        found_feature = omnidexer.find(
            ContentType.CLASS_FEATURE, "Fighting Style", "PHB"
        )
        assert found_feature is not None

    @pytest.mark.asyncio
    async def test_deep_indexing_disabled(self, temp_data_dir: Any) -> None:
        """Test that when deep indexing is disabled, nested content is not indexed."""
        import json
        from pathlib import Path

        # Create the class subdirectory
        class_dir = temp_data_dir / "class"
        class_dir.mkdir(exist_ok=True)
        class_file = class_dir / "test-classes.json"
        class_data = {
            "class": [
                {
                    "name": "Fighter",
                    "source": "PHB",
                    "hd": {"number": 1, "faces": 10},
                    "proficiency": ["str", "con"],
                    "classFeatures": [
                        "Fighting Style|Fighter||1",
                        "Second Wind|Fighter||1",
                    ],
                }
            ]
        }

        with open(class_file, "w") as f:
            json.dump(class_data, f)

        # Set up omnidexer with deep indexing disabled
        source_manager = FileSystemSourceManager(temp_data_dir.parent)
        source_manager.path_config.data_path = temp_data_dir
        omnidexer = Omnidexer(source_manager, enable_deep_indexing=False)

        # Load data
        await omnidexer.load_all_data()

        # Should have indexed the class
        fighter = omnidexer.find(ContentType.CLASS, "Fighter", "PHB")
        assert fighter is not None

        # Should NOT have indexed the class features
        fighting_style = omnidexer.find(
            ContentType.CLASS_FEATURE, "Fighting Style", "PHB"
        )
        assert fighting_style is None

        second_wind = omnidexer.find(ContentType.CLASS_FEATURE, "Second Wind", "PHB")
        assert second_wind is None

    @pytest.mark.asyncio
    async def test_malformed_feature_references_handling(self) -> None:
        """Test that malformed feature references are handled gracefully."""
        # Create a class with malformed feature references
        class_data = {
            "name": "TestClass",
            "source": {"abbreviation": "TEST", "name": "Test Source"},
            "hd": {"number": 1, "faces": 8},
            "proficiency": ["int", "wis"],
            "classFeatures": [
                "Valid Feature|TestClass||1",  # Valid
                "Invalid Feature",  # Missing parts
                "Another|Invalid",  # Missing parts
                "",  # Empty string
                "Too|Many|Parts|Here|1|Extra|Stuff",  # Too many parts
                "Non Numeric Level|TestClass||ABC",  # Invalid level
            ],
            "subclasses": [],
        }

        test_class = Class(**class_data)
        omnidexer = Omnidexer()

        # Should only parse the valid feature
        nested_content = test_class.get_deep_index_entries(omnidexer)

        # Should have only 1 valid feature
        assert len(nested_content) == 1
        assert nested_content[0].name == "Valid Feature"
        assert isinstance(nested_content[0], ClassFeature)
        assert nested_content[0].level == 1

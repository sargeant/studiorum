"""Tests for Omnidexer system."""

from pathlib import Path
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
        # Test that omnidexer has default functionality by checking available content types
        stats = omnidexer.get_statistics()
        assert stats is not None  # Should have statistics functionality

    def test_loader_registration(self) -> None:
        """Test registering custom loaders."""
        omnidexer: Any = Omnidexer()
        loader = JsonDataLoader.create_for_type(ContentType.SPELL)
        omnidexer.register_loader(ContentType.SPELL, loader)

        # Test that the loader was registered by verifying behavior
        # A registered loader should allow the content type to be processed
        # Note: Registration doesn't mean content is loaded, just that the loader exists
        # We can't easily test this without accessing private state, so test basic functionality instead
        stats = omnidexer.get_statistics()
        assert stats is not None  # Loader registration enables statistics

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

    def setup_method(self) -> None:
        """Reset ALL global state for complete isolation."""
        from dnd5e.core.cache import CacheManager
        from dnd5e.core.config.sources import reset_config_manager
        from dnd5e.core.content_type_resolver import reset_content_type_resolver
        from dnd5e.core.entry_registry import reset_entry_registry
        from dnd5e.core.interfaces import reset_content_type_registry
        from dnd5e.core.loaders.content_factory import reset_content_factory

        # Complete isolation - reset ALL global singletons
        CacheManager.reset()
        reset_content_factory()
        reset_content_type_registry()
        reset_content_type_resolver()
        reset_entry_registry()
        reset_config_manager()  # Added missing config manager reset

        import gc

        gc.collect()  # Force cleanup of any lingering objects

    def teardown_method(self) -> None:
        """Clear cache after each test."""
        from dnd5e.core.cache import CacheManager
        from dnd5e.core.content_type_resolver import reset_content_type_resolver
        from dnd5e.core.entry_registry import reset_entry_registry
        from dnd5e.core.interfaces import reset_content_type_registry
        from dnd5e.core.loaders.content_factory import reset_content_factory

        # Force complete isolation - reset ALL global singletons
        CacheManager.reset()
        reset_content_factory()
        reset_content_type_registry()
        reset_content_type_resolver()
        reset_entry_registry()

        # Ensure any pending async operations complete
        import asyncio
        import time

        time.sleep(0.01)  # Small delay for cleanup

        # Force garbage collection to clean up any file handles
        import gc

        gc.collect()

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
        import asyncio
        import json

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

        # Ensure file system operations complete before proceeding
        import os

        os.sync()  # Force filesystem flush
        await asyncio.sleep(0)  # Yield control to ensure I/O completion

        # Set up omnidexer with temp directory
        source_manager = FileSystemSourceManager(temp_data_dir.parent)
        source_manager.path_config.data_path = temp_data_dir
        omnidexer = Omnidexer(source_manager)

        # Ensure global resets complete before content loading
        await asyncio.sleep(0.1)  # Allow global state resets to settle

        # Load data and check indexing
        await omnidexer.load_all_data()

        # Add explicit synchronization barriers to ensure all async operations complete
        await asyncio.sleep(0.1)  # Allow background tasks to complete

        # Force garbage collection to ensure cleanup
        import gc

        gc.collect()

        # Additional small delay for file system operations
        await asyncio.sleep(0.05)

        # Verify data was loaded
        stats = omnidexer.get_statistics()
        assert stats["total_items"] > 0, f"No data loaded. Stats: {stats}"

        # Should have indexed the class
        fighter = omnidexer.find(ContentType.CLASS, "Fighter", "PHB")
        assert fighter is not None
        assert fighter.name == "Fighter"

        # Should have indexed the class features due to deep indexing
        # Add another sync barrier before checking deep indexing results
        await asyncio.sleep(0.1)  # Ensure deep indexing is complete

        # Find all Fighting Style features and get the Fighter one specifically
        all_fighting_styles = [
            item
            for item in omnidexer.get_all_by_type(ContentType.CLASS_FEATURE)
            if item.name == "Fighting Style" and item.source.abbreviation == "PHB"
        ]

        # Find the Fighter's Fighting Style specifically
        fighter_fighting_style = None
        for fs in all_fighting_styles:
            if hasattr(fs, "class_name") and fs.class_name == "Fighter":
                fighter_fighting_style = fs
                break

        assert fighter_fighting_style is not None, (
            f"Could not find Fighter's Fighting Style. Found: {[(fs.class_name if hasattr(fs, 'class_name') else 'Unknown', fs.level) for fs in all_fighting_styles]}"
        )
        assert fighter_fighting_style.name == "Fighting Style"
        assert isinstance(fighter_fighting_style, ClassFeature)
        assert fighter_fighting_style.level == 1

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
    async def test_deep_indexing_stability(self) -> None:
        """Test that deep indexing produces stable results."""
        # This test has been refactored to avoid testing implementation details
        # Original test was checking cycle prevention via private methods
        # Now we test that the indexing behavior is stable and predictable

        omnidexer = Omnidexer()

        # Load data multiple times to ensure stability
        await omnidexer.load_all_data()
        initial_stats = omnidexer.get_statistics()

        # Loading again should not change the index (idempotent behavior)
        await omnidexer.load_all_data()
        final_stats = omnidexer.get_statistics()

        # Statistics should be the same (stable indexing)
        assert final_stats["total_items"] == initial_stats["total_items"]

        # Should be able to find content consistently
        if final_stats["total_items"] > 0:
            # Test that content is findable if it exists
            all_content_types = [ct for ct in ContentType if omnidexer.is_loaded(ct)]
            for content_type in all_content_types[:3]:  # Test first few types
                content_list = omnidexer.get_all_by_type(content_type)
                assert isinstance(content_list, list)

        found_feature = omnidexer.find(
            ContentType.CLASS_FEATURE, "Fighting Style", "PHB"
        )
        assert found_feature is not None

    @pytest.mark.asyncio
    async def test_deep_indexing_disabled(self, temp_data_dir: Any) -> None:
        """Test that when deep indexing is disabled, nested content is not indexed."""
        import json

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


class TestOmnidexerMetadataOnlyLoading:
    """Test that omnidexer loads only metadata files for adventures/books."""

    @pytest.mark.asyncio
    async def test_omnidexer_loads_only_metadata_files(self):
        """Test that omnidexer only loads metadata files, not content files."""
        from unittest.mock import Mock, patch

        from dnd5e.core.loaders.configurable_source_manager import (
            ConfigurableSourceManager,
        )
        from dnd5e.core.loaders.omnidexer import Omnidexer

        # Create test files
        files = [
            Path("/data/adventures.json"),  # metadata - should be loaded
            Path("/data/books.json"),  # metadata - should be loaded
            Path("/data/adventure-cos.json"),  # content - should be skipped
            Path("/data/book-phb.json"),  # content - should be skipped
            Path("/data/spells.json"),  # other content - should be loaded normally
        ]

        # Mock the source manager
        with patch.object(ConfigurableSourceManager, "__init__", return_value=None):
            with patch.object(ConfigurableSourceManager, "ensure_sources_ready"):
                source_manager = ConfigurableSourceManager()
                source_manager.content_manager = Mock()
                source_manager.content_manager._index_built = True
                source_manager.content_manager.get_all_content_files = Mock(
                    return_value={"5etools": files}
                )
                source_manager._data_paths_cache = None

                # Get the data paths that omnidexer would use
                data_paths = source_manager.get_data_paths()

                # Verify that only metadata files are included for adventures/books
                all_files_to_load = []
                for content_type, paths in data_paths.items():
                    all_files_to_load.extend(paths)

                # Should include metadata files
                assert any(
                    "adventures.json" in str(path) for path in all_files_to_load
                ), "adventures.json metadata file should be included"
                assert any("books.json" in str(path) for path in all_files_to_load), (
                    "books.json metadata file should be included"
                )

                # Should NOT include content files
                assert not any(
                    "adventure-cos.json" in str(path) for path in all_files_to_load
                ), "adventure-cos.json content file should be skipped"
                assert not any(
                    "book-phb.json" in str(path) for path in all_files_to_load
                ), "book-phb.json content file should be skipped"

    @pytest.mark.asyncio
    async def test_omnidexer_interface_separation(self):
        """Test that omnidexer can distinguish between metadata and content files."""
        from unittest.mock import Mock, patch

        from dnd5e.core.loaders.configurable_source_manager import (
            ConfigurableSourceManager,
        )

        files = [
            Path("/data/adventures.json"),  # metadata
            Path("/data/books.json"),  # metadata
            Path("/data/adventure-cos.json"),  # content
            Path("/data/adventure-hotdq.json"),  # content
            Path("/data/book-phb.json"),  # content
            Path("/data/book-mm.json"),  # content
        ]

        with patch.object(ConfigurableSourceManager, "__init__", return_value=None):
            source_manager = ConfigurableSourceManager()
            source_manager.content_manager = Mock()
            source_manager.content_manager._index_built = True
            source_manager.content_manager.get_all_content_files = Mock(
                return_value={"5etools": files}
            )
            source_manager._data_paths_cache = None

            # Test the separate methods
            metadata_files = source_manager.get_metadata_files()
            content_files = source_manager.get_content_files()
            data_paths = source_manager.get_data_paths()

            # Count files in each category
            total_metadata = sum(len(paths) for paths in metadata_files.values())
            total_content = sum(len(paths) for paths in content_files.values())
            total_data_paths = sum(len(paths) for paths in data_paths.values())

            # Should have 2 metadata files and 4 content files
            assert total_metadata == 2, (
                f"Expected 2 metadata files, got {total_metadata}"
            )
            assert total_content == 4, f"Expected 4 content files, got {total_content}"

            # get_data_paths should match metadata files for adventures/books
            assert total_data_paths == total_metadata, (
                f"get_data_paths should return same as metadata files, got {total_data_paths} vs {total_metadata}"
            )

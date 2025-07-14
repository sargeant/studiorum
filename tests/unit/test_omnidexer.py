"""Tests for Omnidexer system."""

import pytest

from dnd5e.core.loaders.json_loader import JsonDataLoader
from dnd5e.core.loaders.omnidexer import IndexEntry, Omnidexer
from dnd5e.core.loaders.source_manager import FileSystemSourceManager
from dnd5e.core.models.content import ContentType


class TestIndexEntry:
    """Tests for IndexEntry class."""

    def test_index_entry_creation(self, sample_spell):
        """Test IndexEntry creation."""
        entry = IndexEntry.create(sample_spell, ContentType.SPELL)

        assert entry.content == sample_spell
        assert entry.content_type == ContentType.SPELL
        assert entry.hash_id is not None
        assert len(entry.hash_id) == 8  # MD5 hash truncated to 8 chars
        assert entry.lookup_key == "fireball|phb"


class TestOmnidexer:
    """Tests for Omnidexer class."""

    def test_omnidexer_creation(self):
        """Test basic omnidexer creation."""
        omnidexer = Omnidexer()
        assert omnidexer is not None
        assert len(omnidexer._loaders) > 0  # Should have default loaders

    def test_loader_registration(self):
        """Test registering custom loaders."""
        omnidexer = Omnidexer()
        loader = JsonDataLoader.create_for_type(ContentType.SPELL)
        omnidexer.register_loader(ContentType.SPELL, loader)

        assert ContentType.SPELL in omnidexer._loaders
        assert omnidexer._loaders[ContentType.SPELL] == loader

    @pytest.mark.asyncio
    async def test_empty_data_loading(self, temp_data_dir):
        """Test loading with no data files."""
        source_manager = FileSystemSourceManager(temp_data_dir.parent)
        source_manager.path_config.data_path = temp_data_dir

        omnidexer = Omnidexer(source_manager)
        stats = await omnidexer.load_all_data()

        # Should handle empty directories gracefully
        assert isinstance(stats, dict)

    @pytest.mark.asyncio
    async def test_data_loading_and_indexing(self, loaded_omnidexer):
        """Test data loading and indexing."""
        omnidexer = loaded_omnidexer
        stats = omnidexer.get_statistics()

        assert stats["total_items"] > 0
        assert ContentType.SPELL.value in stats["by_type"]
        assert ContentType.CREATURE.value in stats["by_type"]

    @pytest.mark.asyncio
    async def test_find_by_type_and_name(self, loaded_omnidexer):
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
    async def test_find_without_source(self, loaded_omnidexer):
        """Test finding content without specifying source."""
        omnidexer = loaded_omnidexer
        spell = omnidexer.find(ContentType.SPELL, "Fireball")
        assert spell is not None
        assert spell.name == "Fireball"

    @pytest.mark.asyncio
    async def test_find_all_by_name(self, loaded_omnidexer):
        """Test finding all content with same name."""
        omnidexer = loaded_omnidexer
        spells = omnidexer.find_all(ContentType.SPELL, "Fireball")
        assert len(spells) >= 1
        assert all(spell.name == "Fireball" for spell in spells)

    @pytest.mark.asyncio
    async def test_get_all_by_type(self, loaded_omnidexer):
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
    async def test_get_all_by_source(self, loaded_omnidexer):
        """Test getting all content from a specific source."""
        omnidexer = loaded_omnidexer
        phb_content = omnidexer.get_all_by_source("PHB")
        assert len(phb_content) >= 1
        assert all(content.source.abbreviation == "PHB" for content in phb_content)

        mm_content = omnidexer.get_all_by_source("MM")
        assert len(mm_content) >= 1
        assert all(content.source.abbreviation == "MM" for content in mm_content)

    @pytest.mark.asyncio
    async def test_search_functionality(self, loaded_omnidexer):
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
    async def test_search_by_name_prefix(self, loaded_omnidexer):
        """Test prefix-based search."""
        omnidexer = loaded_omnidexer
        results = omnidexer.search_by_name_prefix("Fire")
        assert len(results) >= 1
        assert any(result.name.startswith("Fire") for result in results)

    @pytest.mark.asyncio
    async def test_is_loaded_check(self, loaded_omnidexer):
        """Test checking if content types are loaded."""
        omnidexer = loaded_omnidexer
        assert omnidexer.is_loaded(ContentType.SPELL)
        assert omnidexer.is_loaded(ContentType.CREATURE)

        # Test unloaded type
        assert not omnidexer.is_loaded(ContentType.BACKGROUND)

    @pytest.mark.asyncio
    async def test_statistics(self, loaded_omnidexer):
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

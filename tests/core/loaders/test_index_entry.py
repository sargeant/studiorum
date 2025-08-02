"""Comprehensive tests for IndexEntry Pydantic model."""

from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from dnd5e.core.loaders.omnidexer import IndexEntry
from dnd5e.core.models.content import BaseContent, ContentType, Source
from dnd5e.core.models.creatures import Creature
from dnd5e.core.models.spells import Spell


class TestIndexEntry:
    """Tests for IndexEntry Pydantic model."""

    @pytest.fixture
    def sample_source(self) -> Source:
        """Create sample source for testing."""
        return Source(abbreviation="PHB", name="Player's Handbook")

    @pytest.fixture
    def sample_spell(self, sample_source: Source) -> Spell:
        """Create sample spell for testing."""
        return Spell(
            name="Fireball",
            source=sample_source,
            level=3,
            school="evocation",
            time=[{"number": 1, "unit": "action"}],
            range={"type": "point", "distance": {"type": "feet", "amount": 150}},
            duration=[{"type": "instant"}],
            components={
                "v": True,
                "s": True,
                "m": "A tiny ball of bat guano and sulfur",
            },
            entries=["A bright streak flashes from your pointing finger..."],
        )

    @pytest.fixture
    def sample_creature(self, sample_source: Source) -> Creature:
        """Create sample creature for testing."""
        return Creature(
            name="Ancient Red Dragon",
            source=sample_source,
            size=["Gargantuan"],
            type="dragon",
            alignment=["chaotic", "evil"],
            hp={"average": 546},
            ac=[{"ac": 22}],
            speed={"walk": 40, "climb": 40, "fly": 80},
            str=30,
            dex=10,
            con=29,
            int=18,
            wis=15,
            cha=23,
        )

    def test_index_entry_direct_creation(self, sample_spell: Spell) -> None:
        """Test creating IndexEntry directly with all fields."""
        entry = IndexEntry(
            content=sample_spell,
            content_type=ContentType.SPELL,
            hash_id="12345678",
            lookup_key="fireball|phb",
        )

        assert entry.content == sample_spell
        assert entry.content_type == ContentType.SPELL
        assert entry.hash_id == "12345678"
        assert entry.lookup_key == "fireball|phb"

    def test_index_entry_hash_id_validation(self, sample_spell: Spell) -> None:
        """Test hash_id field validation."""
        # Valid 8-character alphanumeric hash
        entry = IndexEntry(
            content=sample_spell,
            content_type=ContentType.SPELL,
            hash_id="abc12345",
            lookup_key="fireball|phb",
        )
        assert entry.hash_id == "abc12345"

        # Hash ID gets normalized to lowercase
        entry = IndexEntry(
            content=sample_spell,
            content_type=ContentType.SPELL,
            hash_id="ABC12345",
            lookup_key="fireball|phb",
        )
        assert entry.hash_id == "abc12345"

        # Too short hash ID should fail
        with pytest.raises(ValidationError) as exc_info:
            IndexEntry(
                content=sample_spell,
                content_type=ContentType.SPELL,
                hash_id="1234567",  # 7 characters
                lookup_key="fireball|phb",
            )
        assert "at least 8 characters" in str(exc_info.value)

        # Too long hash ID should fail
        with pytest.raises(ValidationError) as exc_info:
            IndexEntry(
                content=sample_spell,
                content_type=ContentType.SPELL,
                hash_id="123456789",  # 9 characters
                lookup_key="fireball|phb",
            )
        assert "at most 8 characters" in str(exc_info.value)

        # Non-alphanumeric hash ID should fail
        with pytest.raises(ValidationError) as exc_info:
            IndexEntry(
                content=sample_spell,
                content_type=ContentType.SPELL,
                hash_id="abc123-@",  # Contains special characters
                lookup_key="fireball|phb",
            )
        assert "Hash ID must contain only alphanumeric characters" in str(
            exc_info.value
        )

    def test_index_entry_lookup_key_validation(self, sample_spell: Spell) -> None:
        """Test lookup_key field validation."""
        # Valid lookup key with pipe separator
        entry = IndexEntry(
            content=sample_spell,
            content_type=ContentType.SPELL,
            hash_id="12345678",
            lookup_key="fireball|phb",
        )
        assert entry.lookup_key == "fireball|phb"

        # Lookup key gets normalized to lowercase
        entry = IndexEntry(
            content=sample_spell,
            content_type=ContentType.SPELL,
            hash_id="12345678",
            lookup_key="Fireball|PHB",
        )
        assert entry.lookup_key == "fireball|phb"

        # Lookup key with whitespace gets stripped and normalized
        entry = IndexEntry(
            content=sample_spell,
            content_type=ContentType.SPELL,
            hash_id="12345678",
            lookup_key="  Fireball|PHB  ",
        )
        assert entry.lookup_key == "fireball|phb"

        # Missing pipe separator should fail
        with pytest.raises(ValidationError) as exc_info:
            IndexEntry(
                content=sample_spell,
                content_type=ContentType.SPELL,
                hash_id="12345678",
                lookup_key="fireball_phb",  # No pipe separator
            )
        assert "must contain '|' separator" in str(exc_info.value)

        # Empty lookup key should fail
        with pytest.raises(ValidationError) as exc_info:
            IndexEntry(
                content=sample_spell,
                content_type=ContentType.SPELL,
                hash_id="12345678",
                lookup_key="",
            )
        assert "at least 1 character" in str(exc_info.value)

    def test_index_entry_create_classmethod_spell(self, sample_spell: Spell) -> None:
        """Test IndexEntry.create() classmethod with spell."""
        entry = IndexEntry.create(sample_spell, ContentType.SPELL)

        assert entry.content == sample_spell
        assert entry.content_type == ContentType.SPELL
        assert len(entry.hash_id) == 8
        assert entry.hash_id.isalnum()
        assert entry.lookup_key == "fireball|phb"

        # Hash should be deterministic
        entry2 = IndexEntry.create(sample_spell, ContentType.SPELL)
        assert entry.hash_id == entry2.hash_id
        assert entry.lookup_key == entry2.lookup_key

    def test_index_entry_create_classmethod_creature(
        self, sample_creature: Creature
    ) -> None:
        """Test IndexEntry.create() classmethod with creature."""
        entry = IndexEntry.create(sample_creature, ContentType.CREATURE)

        assert entry.content == sample_creature
        assert entry.content_type == ContentType.CREATURE
        assert len(entry.hash_id) == 8
        assert entry.hash_id.isalnum()
        assert entry.lookup_key == "ancient red dragon|phb"

    def test_index_entry_create_with_dict_source(self) -> None:
        """Test IndexEntry.create() with content that has dict source."""
        # Create mock content with dict-style source
        mock_content = Mock(spec=BaseContent)
        mock_content.name = "Test Content"
        mock_content.source = {"abbreviation": "TEST", "name": "Test Source"}

        entry = IndexEntry.create(mock_content, ContentType.SPELL)

        assert entry.content == mock_content
        assert entry.content_type == ContentType.SPELL
        assert entry.lookup_key == "test content|test"

    def test_index_entry_create_with_string_source(self) -> None:
        """Test IndexEntry.create() with content that has string source."""
        # Create mock content with string source
        mock_content = Mock(spec=BaseContent)
        mock_content.name = "Test Content"
        mock_content.source = "TEST_SOURCE"

        entry = IndexEntry.create(mock_content, ContentType.SPELL)

        assert entry.content == mock_content
        assert entry.content_type == ContentType.SPELL
        assert entry.lookup_key == "test content|test_source"

    def test_index_entry_create_with_object_source_no_abbreviation(self) -> None:
        """Test IndexEntry.create() with source object without abbreviation."""
        # Create mock content with object source that doesn't have abbreviation
        mock_source = Mock()
        mock_source.name = "Test Source"
        # No abbreviation attribute

        mock_content = Mock(spec=BaseContent)
        mock_content.name = "Test Content"
        mock_content.source = mock_source

        entry = IndexEntry.create(mock_content, ContentType.SPELL)

        assert entry.content == mock_content
        assert entry.content_type == ContentType.SPELL
        # Should use string representation of source
        assert entry.lookup_key.startswith("test content|")

    def test_index_entry_hash_consistency(
        self, sample_spell: Spell, sample_creature: Creature
    ) -> None:
        """Test that hash generation is consistent and unique."""
        # Same content should produce same hash
        entry1 = IndexEntry.create(sample_spell, ContentType.SPELL)
        entry2 = IndexEntry.create(sample_spell, ContentType.SPELL)
        assert entry1.hash_id == entry2.hash_id

        # Different content should produce different hashes
        spell_entry = IndexEntry.create(sample_spell, ContentType.SPELL)
        creature_entry = IndexEntry.create(sample_creature, ContentType.CREATURE)
        assert spell_entry.hash_id != creature_entry.hash_id

        # Same content with different type should produce different hashes
        # (This is a bit artificial but tests the hash generation logic)
        spell_as_spell = IndexEntry.create(sample_spell, ContentType.SPELL)
        spell_as_item = IndexEntry.create(sample_spell, ContentType.ITEM)
        assert spell_as_spell.hash_id != spell_as_item.hash_id

    def test_index_entry_lookup_key_generation(self) -> None:
        """Test lookup key generation with various content names."""
        test_cases = [
            ("Fireball", "PHB", "fireball|phb"),
            ("Ancient Red Dragon", "MM", "ancient red dragon|mm"),
            ("Bag of Holding", "DMG", "bag of holding|dmg"),
            ("UPPERCASE", "lowercase", "uppercase|lowercase"),
            ("Mixed-Case_Name", "Mixed.Source", "mixed-case_name|mixed.source"),
        ]

        for name, source_abbrev, expected_key in test_cases:
            mock_content = Mock(spec=BaseContent)
            mock_content.name = name
            mock_content.source = Mock()
            mock_content.source.abbreviation = source_abbrev

            entry = IndexEntry.create(mock_content, ContentType.SPELL)
            assert entry.lookup_key == expected_key

    def test_index_entry_arbitrary_types_allowed(self, sample_spell: Spell) -> None:
        """Test that IndexEntry allows arbitrary types for content."""
        # Should accept any BaseContent subclass
        entry = IndexEntry.create(sample_spell, ContentType.SPELL)
        assert entry.content == sample_spell

        # Should also work with mock objects
        mock_content = Mock(spec=BaseContent)
        mock_content.name = "Mock Content"
        mock_content.source = Mock()
        mock_content.source.abbreviation = "MOCK"

        entry = IndexEntry(
            content=mock_content,
            content_type=ContentType.SPELL,
            hash_id="12345678",
            lookup_key="mock|mock",
        )
        assert entry.content == mock_content

    def test_index_entry_content_type_validation(self, sample_spell: Spell) -> None:
        """Test that content_type must be a valid ContentType."""
        # Valid ContentType
        entry = IndexEntry.create(sample_spell, ContentType.SPELL)
        assert entry.content_type == ContentType.SPELL

        # Should work with all ContentType values
        for content_type in ContentType:
            entry = IndexEntry.create(sample_spell, content_type)
            assert entry.content_type == content_type

    def test_index_entry_unicode_handling(self) -> None:
        """Test IndexEntry with Unicode content names."""
        mock_content = Mock(spec=BaseContent)
        mock_content.name = "Fíréball"  # Unicode characters
        mock_content.source = Mock()
        mock_content.source.abbreviation = "PHß"  # Unicode in source

        entry = IndexEntry.create(mock_content, ContentType.SPELL)

        assert entry.content == mock_content
        assert entry.lookup_key == "fíréball|phß"  # Unicode preserved in lowercase

    def test_index_entry_very_long_names(self) -> None:
        """Test IndexEntry with very long content names."""
        long_name = "A" * 1000  # Very long name
        long_source = "B" * 100  # Very long source

        mock_content = Mock(spec=BaseContent)
        mock_content.name = long_name
        mock_content.source = Mock()
        mock_content.source.abbreviation = long_source

        entry = IndexEntry.create(mock_content, ContentType.SPELL)

        assert entry.content == mock_content
        assert entry.lookup_key == f"{long_name.lower()}|{long_source.lower()}"
        assert len(entry.hash_id) == 8  # Hash should still be 8 characters

    def test_index_entry_empty_source_abbreviation(self) -> None:
        """Test IndexEntry with empty source abbreviation."""
        mock_content = Mock(spec=BaseContent)
        mock_content.name = "Test Spell"
        mock_content.source = Mock()
        mock_content.source.abbreviation = ""

        entry = IndexEntry.create(mock_content, ContentType.SPELL)

        assert entry.content == mock_content
        assert entry.lookup_key == "test spell|"  # Empty source part

    def test_index_entry_special_characters_in_names(self) -> None:
        """Test IndexEntry with special characters in names."""
        test_cases = [
            ("Bag of Holding +1", "bag of holding +1"),
            ("Sphere of Annihilation (Greater)", "sphere of annihilation (greater)"),
            ("Flame Tongue Sword / Scimitar", "flame tongue sword / scimitar"),
            ("Ring of X-ray Vision", "ring of x-ray vision"),
            ("Cloak of Elvenkind [Rare]", "cloak of elvenkind [rare]"),
        ]

        for original_name, expected_lower in test_cases:
            mock_content = Mock(spec=BaseContent)
            mock_content.name = original_name
            mock_content.source = Mock()
            mock_content.source.abbreviation = "DMG"

            entry = IndexEntry.create(mock_content, ContentType.ITEM)
            assert entry.lookup_key == f"{expected_lower}|dmg"

    def test_index_entry_none_handling(self) -> None:
        """Test IndexEntry behavior with None values where allowed."""
        # None source should be handled gracefully in create method
        mock_content = Mock(spec=BaseContent)
        mock_content.name = "Test Content"
        mock_content.source = None

        entry = IndexEntry.create(mock_content, ContentType.SPELL)

        assert entry.content == mock_content
        assert entry.lookup_key == "test content|none"  # str(None) = "None"

    def test_index_entry_model_validation_edge_cases(self, sample_spell: Spell) -> None:
        """Test various validation edge cases."""
        # Test minimum valid values
        entry = IndexEntry(
            content=sample_spell,
            content_type=ContentType.SPELL,
            hash_id="a" * 8,  # Minimum 8 chars
            lookup_key="a|b",  # Minimum with separator
        )
        assert entry.hash_id == "a" * 8
        assert entry.lookup_key == "a|b"

        # Test maximum valid values (no upper limit on lookup_key)
        very_long_key = "a" * 1000 + "|" + "b" * 1000
        entry = IndexEntry(
            content=sample_spell,
            content_type=ContentType.SPELL,
            hash_id="z" * 8,  # Maximum 8 chars
            lookup_key=very_long_key,
        )
        assert entry.hash_id == "z" * 8
        assert entry.lookup_key == very_long_key

    def test_index_entry_immutability(self, sample_spell: Spell) -> None:
        """Test that IndexEntry instances are immutable if frozen config is used."""
        entry = IndexEntry.create(sample_spell, ContentType.SPELL)

        # Note: IndexEntry doesn't have frozen=True in its Config, so this test
        # documents the current behavior. If immutability is desired, the Config
        # would need to be updated to include frozen=True.

        # These should work (not frozen)
        entry.hash_id = "newvalue"  # This would work if not frozen
        assert entry.hash_id == "newvalue"

        # Reset for next test
        entry = IndexEntry.create(sample_spell, ContentType.SPELL)
        original_hash = entry.hash_id

        # Verify the hash is what we expect
        assert len(original_hash) == 8
        assert original_hash.isalnum()

    def test_index_entry_create_deterministic_hashing(self) -> None:
        """Test that IndexEntry.create produces deterministic hashes."""
        # Create identical content objects
        source = Source(abbreviation="TEST", name="Test Source")

        content1 = Mock(spec=BaseContent)
        content1.name = "Test Content"
        content1.source = source

        content2 = Mock(spec=BaseContent)
        content2.name = "Test Content"
        content2.source = source

        # Create entries
        entry1 = IndexEntry.create(content1, ContentType.SPELL)
        entry2 = IndexEntry.create(content2, ContentType.SPELL)

        # Should have identical hashes and lookup keys
        assert entry1.hash_id == entry2.hash_id
        assert entry1.lookup_key == entry2.lookup_key

        # But different content objects
        assert entry1.content is not entry2.content

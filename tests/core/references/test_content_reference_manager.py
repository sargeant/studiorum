"""Tests for ContentReferenceManager."""

from unittest.mock import Mock, patch

import pytest

from studiorum.core.interfaces import DeepIndexable
from studiorum.core.models.content import BaseContent, ContentType
from studiorum.core.references.content_reference_manager import (
    ContentReference,
    ContentReferenceManager,
    ReferenceSource,
    ReferenceTrackingTagResolver,
)
from studiorum.core.references.content_tracker import TrackedContent
from tests.test_helpers import reset_test_environment


class TestReferenceSource:
    """Test ReferenceSource model."""

    def test_creation(self):
        """Test ReferenceSource creation."""
        source = ReferenceSource(
            type="tag",
            location="template.tex.j2",
            context="Template tag: {@spell Fireball|PHB}",
        )

        assert source.type == "tag"
        assert source.location == "template.tex.j2"
        assert source.context == "Template tag: {@spell Fireball|PHB}"

    def test_creation_minimal(self):
        """Test ReferenceSource creation with minimal data."""
        source = ReferenceSource(type="manual", location="unknown")

        assert source.type == "manual"
        assert source.location == "unknown"
        assert source.context is None


class TestContentReference:
    """Test ContentReference model."""

    def test_creation(self):
        """Test ContentReference creation."""
        ref_source = ReferenceSource(type="tag", location="test.tex")
        reference = ContentReference(
            content_type="spell",
            name="Fireball",
            source="PHB",
            page="241",
            reference_source=ref_source,
        )

        assert reference.content_type == "spell"
        assert reference.name == "Fireball"
        assert reference.source == "PHB"
        assert reference.page == "241"
        assert reference.reference_source == ref_source

    def test_to_tracked_content(self):
        """Test conversion to TrackedContent."""
        ref_source = ReferenceSource(type="deep_index", location="creature.json")
        reference = ContentReference(
            content_type="spell",
            name="Magic Missile",
            source="PHB",
            page="257",
            reference_source=ref_source,
        )

        tracked = reference.to_tracked_content()

        assert isinstance(tracked, TrackedContent)
        assert tracked.content_type == "spell"
        assert tracked.name == "Magic Missile"
        assert tracked.source == "PHB"
        assert tracked.page == "257"


class TestContentReferenceManager:
    """Test ContentReferenceManager class."""

    def setup_method(self):
        """Set up test fixtures."""
        reset_test_environment()

    def test_init(self):
        """Test ContentReferenceManager initialization."""
        mock_omnidexer = Mock()
        manager = ContentReferenceManager(mock_omnidexer)

        assert manager.omnidexer == mock_omnidexer
        assert manager._references == []
        assert manager._reference_counts == {}
        assert manager._reference_keys == set()

    def test_init_without_omnidexer(self):
        """Test initialization without omnidexer."""
        manager = ContentReferenceManager()

        assert manager.omnidexer is None
        assert manager._references == []

    def test_track_reference_basic(self):
        """Test basic reference tracking."""
        manager = ContentReferenceManager()

        manager.track_reference(
            content_type="spell",
            name="Fireball",
            source="PHB",
            page="241",
            reference_source_type="manual",
            location="test location",
            context="test context",
        )

        assert len(manager._references) == 1
        reference = manager._references[0]
        assert reference.content_type == "spell"
        assert reference.name == "Fireball"
        assert reference.source == "PHB"
        assert reference.page == "241"
        assert reference.reference_source.type == "manual"
        assert reference.reference_source.location == "test location"
        assert reference.reference_source.context == "test context"

    def test_track_reference_deduplication(self):
        """Test reference deduplication."""
        manager = ContentReferenceManager()

        # Add same reference twice
        manager.track_reference("spell", "Fireball", "PHB")
        manager.track_reference("spell", "Fireball", "PHB")

        # Should only store one unique reference
        assert len(manager._references) == 1

        # But count should be 2
        assert manager.get_reference_count("spell", "Fireball", "PHB") == 2

    def test_track_reference_case_insensitive_deduplication(self):
        """Test case-insensitive deduplication."""
        manager = ContentReferenceManager()

        manager.track_reference("Spell", "Fireball", "PHB")
        manager.track_reference("spell", "FIREBALL", "PHB")

        # Should deduplicate despite case differences
        assert len(manager._references) == 1
        assert manager.get_reference_count("spell", "fireball", "PHB") == 2

    def test_track_tag_reference(self):
        """Test tag reference tracking."""
        manager = ContentReferenceManager()

        manager.track_tag_reference(
            tag_type="spell",
            name="Magic Missile",
            source="PHB",
            template_location="spells.tex.j2",
        )

        assert len(manager._references) == 1
        reference = manager._references[0]
        assert reference.content_type == "spell"
        assert reference.name == "Magic Missile"
        assert reference.source == "PHB"
        assert reference.reference_source.type == "tag"
        assert reference.reference_source.location == "spells.tex.j2"
        assert "Template tag:" in reference.reference_source.context

    def test_track_deep_index_references_no_omnidexer(self):
        """Test deep index tracking without omnidexer."""
        manager = ContentReferenceManager()  # No omnidexer

        mock_content = Mock(spec=["name"])
        mock_content.name = "Test Content"

        # Should not raise exception
        manager.track_deep_index_references(mock_content)

        # Should not add any references
        assert len(manager._references) == 0

    def test_track_deep_index_references_with_omnidexer(self):
        """Test deep index tracking with omnidexer."""
        mock_omnidexer = Mock()
        manager = ContentReferenceManager(mock_omnidexer)

        # Mock content that implements DeepIndexable
        mock_spell = Mock()
        mock_spell.name = "Fireball"
        mock_spell.source.abbreviation = "PHB"

        mock_creature = Mock()
        mock_creature.name = "Dragon"
        mock_creature.source = None

        mock_content = Mock(spec=["name", "get_deep_index_entries"])
        mock_content.name = "Test Creature"
        mock_content.get_deep_index_entries.return_value = [mock_spell, mock_creature]

        # Mock _infer_content_type
        with patch.object(manager, "_infer_content_type") as mock_infer:
            mock_infer.side_effect = ["spell", "creature"]

            manager.track_deep_index_references(mock_content, "testing")

        assert len(manager._references) == 2

        # Check first reference (spell)
        spell_ref = manager._references[0]
        assert spell_ref.content_type == "spell"
        assert spell_ref.name == "Fireball"
        assert spell_ref.source == "PHB"
        assert spell_ref.reference_source.type == "deep_index"
        assert "Test Creature" in spell_ref.reference_source.location

        # Check second reference (creature)
        creature_ref = manager._references[1]
        assert creature_ref.content_type == "creature"
        assert creature_ref.name == "Dragon"
        assert creature_ref.source is None

    def test_track_deep_index_references_with_error(self):
        """Test deep index tracking with error handling."""
        mock_omnidexer = Mock()
        manager = ContentReferenceManager(mock_omnidexer)

        mock_content = Mock(spec=["name", "get_deep_index_entries"])
        mock_content.name = "Test Content"
        mock_content.get_deep_index_entries.side_effect = Exception("Deep index failed")

        # Should not raise exception, but log warning
        with patch("studiorum.core.logging.logger.get_logger") as mock_logger:
            mock_log = Mock()
            mock_logger.return_value = mock_log

            manager.track_deep_index_references(mock_content)

            mock_log.warning.assert_called_once()

        assert len(manager._references) == 0

    def test_infer_content_type(self):
        """Test content type inference."""
        manager = ContentReferenceManager()

        # Test basic type mappings
        mock_spell = Mock()
        mock_spell.__class__.__name__ = "Spell"
        assert manager._infer_content_type(mock_spell) == "spell"

        mock_creature = Mock()
        mock_creature.__class__.__name__ = "Creature"
        assert manager._infer_content_type(mock_creature) == "creature"

        mock_monster = Mock()
        mock_monster.__class__.__name__ = "Monster"
        assert manager._infer_content_type(mock_monster) == "creature"

        mock_item = Mock()
        mock_item.__class__.__name__ = "MagicItem"
        assert manager._infer_content_type(mock_item) == "item"

        # Test unknown type
        mock_unknown = Mock()
        mock_unknown.__class__.__name__ = "UnknownType"
        assert manager._infer_content_type(mock_unknown) == "unknowntype"

    def test_get_references_by_type(self):
        """Test getting references by type."""
        manager = ContentReferenceManager()

        manager.track_reference("spell", "Fireball", "PHB")
        manager.track_reference("spell", "Magic Missile", "PHB")
        manager.track_reference("creature", "Dragon", "MM")

        spell_refs = manager.get_references_by_type("spell")
        assert len(spell_refs) == 2
        assert all(ref.content_type == "spell" for ref in spell_refs)

        creature_refs = manager.get_references_by_type("creature")
        assert len(creature_refs) == 1
        assert creature_refs[0].content_type == "creature"

    def test_get_references_by_type_case_insensitive(self):
        """Test case-insensitive type retrieval."""
        manager = ContentReferenceManager()

        manager.track_reference("Spell", "Fireball", "PHB")

        refs = manager.get_references_by_type("spell")
        assert len(refs) == 1

        refs = manager.get_references_by_type("SPELL")
        assert len(refs) == 1

    def test_get_unique_references_by_type(self):
        """Test getting unique references by type."""
        manager = ContentReferenceManager()

        # Add duplicate references
        manager.track_reference("spell", "Fireball", "PHB")
        manager.track_reference("spell", "Fireball", "PHB")  # Duplicate
        manager.track_reference("spell", "Magic Missile", "PHB")

        unique_refs = manager.get_unique_references_by_type("spell")
        assert len(unique_refs) == 2

        names = [ref.name for ref in unique_refs]
        assert "Fireball" in names
        assert "Magic Missile" in names

    def test_get_content_tracker(self):
        """Test getting backward-compatible ContentTracker."""
        manager = ContentReferenceManager()

        manager.track_reference("spell", "Fireball", "PHB", "241")

        tracker = manager.get_content_tracker()

        # Should have one tracked content item
        tracked_content = tracker.get_tracked_content()
        assert len(tracked_content) == 1

        tracked = tracked_content[0]
        assert tracked.content_type == "spell"
        assert tracked.name == "Fireball"
        assert tracked.source == "PHB"
        assert tracked.page == "241"

    def test_get_reference_count(self):
        """Test reference counting."""
        manager = ContentReferenceManager()

        # Add same reference multiple times
        manager.track_reference("spell", "Fireball", "PHB")
        manager.track_reference("spell", "Fireball", "PHB")
        manager.track_reference("spell", "Fireball", "PHB")

        count = manager.get_reference_count("spell", "Fireball", "PHB")
        assert count == 3

        # Non-existent reference should return 0
        count = manager.get_reference_count("spell", "Nonexistent", "PHB")
        assert count == 0

    def test_get_all_references(self):
        """Test getting all references."""
        manager = ContentReferenceManager()

        manager.track_reference("spell", "Fireball", "PHB")
        manager.track_reference("creature", "Dragon", "MM")

        all_refs = manager.get_all_references()
        assert len(all_refs) == 2

        # Should return a copy
        all_refs.append(Mock())
        assert len(manager._references) == 2

    def test_clear(self):
        """Test clearing all references."""
        manager = ContentReferenceManager()

        manager.track_reference("spell", "Fireball", "PHB")
        manager.track_reference("creature", "Dragon", "MM")

        assert len(manager._references) == 2
        assert len(manager._reference_counts) > 0
        assert len(manager._reference_keys) > 0

        manager.clear()

        assert len(manager._references) == 0
        assert len(manager._reference_counts) == 0
        assert len(manager._reference_keys) == 0


class TestReferenceTrackingTagResolver:
    """Test ReferenceTrackingTagResolver wrapper."""

    def setup_method(self):
        """Set up test fixtures."""
        reset_test_environment()

    def test_init(self):
        """Test ReferenceTrackingTagResolver initialization."""
        mock_tag_resolver = Mock()
        mock_ref_manager = Mock()

        wrapper = ReferenceTrackingTagResolver(mock_tag_resolver, mock_ref_manager)

        assert wrapper.tag_resolver == mock_tag_resolver
        assert wrapper.reference_manager == mock_ref_manager

    def test_resolve_tag_simple(self):
        """Test tag resolution without reference tracking."""
        mock_tag_resolver = Mock()
        mock_tag_resolver.resolve_tag.return_value = "Resolved content"
        mock_ref_manager = Mock()

        wrapper = ReferenceTrackingTagResolver(mock_tag_resolver, mock_ref_manager)

        result = wrapper.resolve_tag("simple tag", "test.tex")

        assert result == "Resolved content"
        mock_tag_resolver.resolve_tag.assert_called_once_with("simple tag")
        mock_ref_manager.track_tag_reference.assert_not_called()

    def test_resolve_tag_with_tracking(self):
        """Test tag resolution with reference tracking."""
        mock_tag_resolver = Mock()
        mock_tag_resolver.resolve_tag.return_value = "Resolved content"
        mock_ref_manager = Mock()

        wrapper = ReferenceTrackingTagResolver(mock_tag_resolver, mock_ref_manager)

        result = wrapper.resolve_tag("{@spell Fireball|PHB}", "spells.tex")

        assert result == "Resolved content"
        mock_tag_resolver.resolve_tag.assert_called_once_with("{@spell Fireball|PHB}")
        mock_ref_manager.track_tag_reference.assert_called_once_with(
            tag_type="spell",
            name="Fireball",
            source="PHB",
            template_location="spells.tex",
        )

    def test_resolve_tag_malformed(self):
        """Test tag resolution with malformed tag."""
        mock_tag_resolver = Mock()
        mock_tag_resolver.resolve_tag.return_value = "Resolved content"
        mock_ref_manager = Mock()

        wrapper = ReferenceTrackingTagResolver(mock_tag_resolver, mock_ref_manager)

        # Malformed tag should not break resolution
        result = wrapper.resolve_tag("{@malformed", "test.tex")

        assert result == "Resolved content"
        mock_tag_resolver.resolve_tag.assert_called_once()
        mock_ref_manager.track_tag_reference.assert_not_called()

    def test_resolve_tag_parsing_error(self):
        """Test tag resolution with parsing error."""
        mock_tag_resolver = Mock()
        mock_tag_resolver.resolve_tag.return_value = "Resolved content"
        mock_ref_manager = Mock()
        mock_ref_manager.track_tag_reference.side_effect = Exception("Tracking failed")

        wrapper = ReferenceTrackingTagResolver(mock_tag_resolver, mock_ref_manager)

        # Should not raise exception even if tracking fails
        result = wrapper.resolve_tag("{@spell Fireball|PHB}", "test.tex")

        assert result == "Resolved content"

    def test_getattr_delegation(self):
        """Test attribute delegation to wrapped resolver."""
        mock_tag_resolver = Mock()
        mock_tag_resolver.some_attribute = "test_value"
        mock_tag_resolver.some_method.return_value = "method_result"
        mock_ref_manager = Mock()

        wrapper = ReferenceTrackingTagResolver(mock_tag_resolver, mock_ref_manager)

        # Test attribute access
        assert wrapper.some_attribute == "test_value"

        # Test method call
        result = wrapper.some_method("arg1", kwarg="value")
        assert result == "method_result"
        mock_tag_resolver.some_method.assert_called_once_with("arg1", kwarg="value")


@pytest.mark.integration
class TestContentReferenceManagerIntegration:
    """Integration tests for ContentReferenceManager."""

    def setup_method(self):
        """Set up test fixtures."""
        reset_test_environment()

    def test_full_reference_tracking_workflow(self):
        """Test complete reference tracking workflow."""
        mock_omnidexer = Mock()
        manager = ContentReferenceManager(mock_omnidexer)

        # Track references from various sources
        manager.track_tag_reference("spell", "Fireball", "PHB", "spells.tex")
        manager.track_reference(
            "creature", "Dragon", "MM", reference_source_type="manual"
        )

        # Mock deep indexing
        mock_spell = Mock()
        mock_spell.name = "Magic Missile"
        mock_spell.source.abbreviation = "PHB"

        mock_content = Mock(spec=["name", "get_deep_index_entries"])
        mock_content.name = "Test Adventure"
        mock_content.get_deep_index_entries.return_value = [mock_spell]

        with patch.object(manager, "_infer_content_type", return_value="spell"):
            manager.track_deep_index_references(mock_content)

        # Verify all references tracked
        all_refs = manager.get_all_references()
        assert len(all_refs) == 3

        # Verify by type
        spell_refs = manager.get_references_by_type("spell")
        assert len(spell_refs) == 2

        creature_refs = manager.get_references_by_type("creature")
        assert len(creature_refs) == 1

        # Verify backward compatibility
        tracker = manager.get_content_tracker()
        tracked_content = tracker.get_tracked_content()
        assert len(tracked_content) == 3

    def test_reference_deduplication_across_sources(self):
        """Test deduplication works across different reference sources."""
        manager = ContentReferenceManager()

        # Same spell referenced from different sources
        manager.track_tag_reference("spell", "Fireball", "PHB", "template1.tex")
        manager.track_reference(
            "spell", "Fireball", "PHB", reference_source_type="manual"
        )
        manager.track_reference(
            "spell", "Fireball", "PHB", reference_source_type="deep_index"
        )

        # Should only have one unique reference
        unique_refs = manager.get_unique_references_by_type("spell")
        assert len(unique_refs) == 1

        # But count should be 3
        count = manager.get_reference_count("spell", "Fireball", "PHB")
        assert count == 3

"""Unit tests for FluffDeduplicator service."""

import pytest

from studiorum.core.models.content import Source
from studiorum.core.models.fluff import BaseFluff, FluffEntry
from studiorum.core.references.content_tracker import ContentTracker
from studiorum.core.services.fluff_deduplicator import (
    DeduplicationStrategy,
    FluffDeduplicator,
    create_fluff_deduplicator_service,
)


class TestFluffDeduplicator:
    """Unit tests for FluffDeduplicator service."""

    def create_test_fluff(
        self, name: str, content: str, source_abbrev: str = "MM"
    ) -> BaseFluff:
        """Create a test fluff entry with specified content."""
        source = Source(abbreviation=source_abbrev, full_name="Monster Manual")
        entry = FluffEntry(content=content)

        return BaseFluff(name=name, source=source, entries=[entry], images=[])

    def test_initialization_with_defaults(self) -> None:
        """Test FluffDeduplicator initialization with default parameters."""
        deduplicator = FluffDeduplicator()

        assert deduplicator.strategy == DeduplicationStrategy.STRICT
        assert deduplicator.content_tracker is None
        assert len(deduplicator._seen_hashes) == 0
        assert len(deduplicator._hash_to_content) == 0
        assert len(deduplicator._duplicate_references) == 0

    def test_initialization_with_custom_parameters(self) -> None:
        """Test FluffDeduplicator initialization with custom parameters."""
        tracker = ContentTracker()
        deduplicator = FluffDeduplicator(
            strategy=DeduplicationStrategy.LOOSE, content_tracker=tracker
        )

        assert deduplicator.strategy == DeduplicationStrategy.LOOSE
        assert deduplicator.content_tracker is tracker

    def test_should_include_first_unique_content(self) -> None:
        """Test that first occurrence of content is always included."""
        deduplicator = FluffDeduplicator(strategy=DeduplicationStrategy.STRICT)
        fluff = self.create_test_fluff("Test Monster", "Unique content here")

        assert deduplicator.should_include(fluff) is True

    def test_should_exclude_duplicate_content(self) -> None:
        """Test that duplicate content is excluded."""
        deduplicator = FluffDeduplicator(strategy=DeduplicationStrategy.STRICT)

        fluff1 = self.create_test_fluff("Monster A", "Identical content")
        fluff2 = self.create_test_fluff("Monster B", "Identical content")

        assert deduplicator.should_include(fluff1) is True
        assert deduplicator.should_include(fluff2) is False

    def test_should_include_different_content(self) -> None:
        """Test that different content is always included."""
        deduplicator = FluffDeduplicator(strategy=DeduplicationStrategy.STRICT)

        fluff1 = self.create_test_fluff("Monster A", "First content")
        fluff2 = self.create_test_fluff("Monster B", "Second content")

        assert deduplicator.should_include(fluff1) is True
        assert deduplicator.should_include(fluff2) is True

    def test_none_strategy_includes_everything(self) -> None:
        """Test that NONE strategy includes all content regardless of duplication."""
        deduplicator = FluffDeduplicator(strategy=DeduplicationStrategy.NONE)

        fluff1 = self.create_test_fluff("Monster A", "Identical content")
        fluff2 = self.create_test_fluff("Monster B", "Identical content")

        assert deduplicator.should_include(fluff1) is True
        assert deduplicator.should_include(fluff2) is True

    def test_hash_fluff_content_consistent(self) -> None:
        """Test that content hashing is consistent for identical content."""
        deduplicator = FluffDeduplicator(strategy=DeduplicationStrategy.STRICT)

        fluff1 = self.create_test_fluff("Monster A", "Test content")
        fluff2 = self.create_test_fluff("Monster B", "Test content")

        hash1 = deduplicator._hash_fluff_content(fluff1)
        hash2 = deduplicator._hash_fluff_content(fluff2)

        assert hash1 == hash2

    def test_hash_fluff_content_different_for_different_content(self) -> None:
        """Test that different content produces different hashes."""
        deduplicator = FluffDeduplicator(strategy=DeduplicationStrategy.STRICT)

        fluff1 = self.create_test_fluff("Monster A", "First content")
        fluff2 = self.create_test_fluff("Monster B", "Second content")

        hash1 = deduplicator._hash_fluff_content(fluff1)
        hash2 = deduplicator._hash_fluff_content(fluff2)

        assert hash1 != hash2

    def test_get_duplicate_references_empty_for_unique(self) -> None:
        """Test that unique content has no duplicate references."""
        deduplicator = FluffDeduplicator(strategy=DeduplicationStrategy.STRICT)
        fluff = self.create_test_fluff("Test Monster", "Unique content")

        deduplicator.should_include(fluff)  # Process the fluff
        refs = deduplicator.get_duplicate_references(fluff)

        assert len(refs) == 0

    def test_get_duplicate_references_tracks_duplicates(self) -> None:
        """Test that duplicate references are properly tracked."""
        deduplicator = FluffDeduplicator(strategy=DeduplicationStrategy.STRICT)

        fluff1 = self.create_test_fluff("Monster A", "Identical content")
        fluff2 = self.create_test_fluff("Monster B", "Identical content")
        fluff3 = self.create_test_fluff("Monster C", "Identical content")

        deduplicator.should_include(fluff1)  # Include first
        deduplicator.should_include(fluff2)  # Exclude as duplicate
        deduplicator.should_include(fluff3)  # Exclude as duplicate

        refs = deduplicator.get_duplicate_references(fluff1)
        assert len(refs) == 2
        assert "Monster B (MM)" in refs
        assert "Monster C (MM)" in refs

    def test_get_statistics_accurate(self) -> None:
        """Test that statistics accurately reflect processing state."""
        deduplicator = FluffDeduplicator(strategy=DeduplicationStrategy.STRICT)

        fluff1 = self.create_test_fluff("Monster A", "Content A")
        fluff2 = self.create_test_fluff("Monster B", "Content B")
        fluff3 = self.create_test_fluff("Monster C", "Content A")  # Duplicate of fluff1
        fluff4 = self.create_test_fluff("Monster D", "Content B")  # Duplicate of fluff2

        deduplicator.should_include(fluff1)  # Include
        deduplicator.should_include(fluff2)  # Include
        deduplicator.should_include(fluff3)  # Exclude
        deduplicator.should_include(fluff4)  # Exclude

        stats = deduplicator.get_statistics()
        assert stats["unique_fluff_included"] == 2
        assert stats["duplicate_fluff_detected"] == 2
        assert stats["total_fluff_processed"] == 4
        assert stats["deduplication_savings"] == 2

    def test_reset_clears_all_state(self) -> None:
        """Test that reset properly clears all internal state."""
        deduplicator = FluffDeduplicator(strategy=DeduplicationStrategy.STRICT)

        fluff1 = self.create_test_fluff("Monster A", "Content A")
        fluff2 = self.create_test_fluff("Monster B", "Content A")

        # Process some fluff
        deduplicator.should_include(fluff1)
        deduplicator.should_include(fluff2)

        # Verify state exists
        assert len(deduplicator._seen_hashes) > 0
        assert len(deduplicator._hash_to_content) > 0
        assert len(deduplicator._duplicate_references) > 0

        # Reset and verify state is cleared
        deduplicator.reset()
        assert len(deduplicator._seen_hashes) == 0
        assert len(deduplicator._hash_to_content) == 0
        assert len(deduplicator._duplicate_references) == 0

    def test_content_tracker_integration(self) -> None:
        """Test that content tracker integration works correctly."""
        tracker = ContentTracker()
        deduplicator = FluffDeduplicator(
            strategy=DeduplicationStrategy.STRICT, content_tracker=tracker
        )

        fluff1 = self.create_test_fluff("Monster A", "Shared content")
        fluff2 = self.create_test_fluff("Monster B", "Shared content")

        deduplicator.should_include(fluff1)  # Include
        deduplicator.should_include(fluff2)  # Exclude, but track reference

        # Check that content tracker recorded the cross-reference
        tracked = tracker.get_tracked_content()
        fluff_refs = [c for c in tracked if c.content_type == "fluff_reference"]
        assert len(fluff_refs) >= 1

    def test_get_service_name(self) -> None:
        """Test service name method."""
        deduplicator = FluffDeduplicator()
        assert deduplicator.get_service_name() == "FluffDeduplicator"

    def test_loose_strategy_includes_metadata_in_hash(self) -> None:
        """Test that loose strategy considers entry metadata in hashing."""
        strict_deduplicator = FluffDeduplicator(strategy=DeduplicationStrategy.STRICT)
        loose_deduplicator = FluffDeduplicator(strategy=DeduplicationStrategy.LOOSE)

        # Create fluff with same text content but different entry metadata
        # Create two fluff entries with identical text but different metadata
        # The key is to ensure get_text() returns the same value
        fluff1 = self.create_test_fluff("Monster A", "Same content text")
        fluff2 = self.create_test_fluff("Monster B", "Same content text")

        # Modify entry metadata after creation to ensure content is identical
        fluff1.entries[0].type = "section"
        fluff1.entries[0].name = "Section A"
        fluff2.entries[0].type = "variant"
        fluff2.entries[0].name = "Section B"

        # Verify content text is identical
        assert fluff1.get_text() == fluff2.get_text()

        # Strict should produce same hash (ignores metadata)
        strict_hash1 = strict_deduplicator._hash_fluff_content(fluff1)
        strict_hash2 = strict_deduplicator._hash_fluff_content(fluff2)
        assert strict_hash1 == strict_hash2

        # Loose should produce different hash (includes metadata)
        loose_hash1 = loose_deduplicator._hash_fluff_content(fluff1)
        loose_hash2 = loose_deduplicator._hash_fluff_content(fluff2)
        assert loose_hash1 != loose_hash2


class TestFluffDeduplicatorFactory:
    """Test FluffDeduplicator factory function."""

    def test_create_fluff_deduplicator_service(self) -> None:
        """Test the factory function creates a proper service instance."""
        service = create_fluff_deduplicator_service()

        assert isinstance(service, FluffDeduplicator)
        assert service.strategy == DeduplicationStrategy.STRICT
        assert service.content_tracker is None

    def test_create_fluff_deduplicator_service_with_params(self) -> None:
        """Test factory function with custom parameters."""
        tracker = ContentTracker()
        service = create_fluff_deduplicator_service(
            strategy=DeduplicationStrategy.LOOSE, content_tracker=tracker
        )

        assert isinstance(service, FluffDeduplicator)
        assert service.strategy == DeduplicationStrategy.LOOSE
        assert service.content_tracker is tracker

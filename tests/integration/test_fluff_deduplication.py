"""Integration tests for fluff deduplication functionality."""

import pytest

from studiorum.core.models.content import Source
from studiorum.core.models.fluff import CreatureFluff
from studiorum.core.references.content_tracker import ContentTracker
from studiorum.core.services.fluff_deduplicator import (
    DeduplicationStrategy,
    FluffDeduplicator,
)


class TestFluffDeduplication:
    """Test fluff deduplication with realistic dragon lair scenarios."""

    def setup_method(self) -> None:
        """Reset service container for each test."""
        from tests.test_helpers import reset_test_environment

        reset_test_environment()

    def create_test_dragon_lair_fluff(
        self, creature_name: str, source_abbrev: str = "MM"
    ) -> CreatureFluff:
        """Create test fluff with dragon lair content (shared across multiple dragons)."""
        source = Source(abbreviation=source_abbrev, full_name="Monster Manual")

        # This represents the typical shared lair description found across multiple dragon types
        shared_lair_content = [
            {
                "type": "entries",
                "name": "Lair Actions",
                "entries": [
                    "On initiative count 20 (losing initiative ties), the dragon takes a lair action to cause one of the following effects; the dragon can't use the same lair action two rounds in a row:",
                    {
                        "type": "list",
                        "items": [
                            "Magma erupts from a point on the ground the dragon can see within 120 feet of it, creating a 20-foot-high, 5-foot-radius geyser.",
                            "The dragon chooses a 10-foot-square area of ground that it can see within 120 feet of it.",
                            "Volcanic gases form a cloud in a 20-foot-radius sphere centered on a point the dragon can see within 120 feet of it.",
                        ],
                    },
                ],
            },
            {
                "type": "entries",
                "name": "Regional Effects",
                "entries": [
                    "The region containing a legendary dragon's lair is warped by the dragon's magic, which creates one or more of the following effects:",
                    {
                        "type": "list",
                        "items": [
                            "Volcanic fissures form beneath the lair, increasing temperature within 6 miles.",
                            "Rocky fissures and caves within 1 mile of the dragon's lair form portals to the Elemental Plane of Fire.",
                            "Air within 1 mile of the lair is hot and humid, and thunderstorms are common.",
                        ],
                    },
                ],
            },
        ]

        return CreatureFluff(
            name=creature_name, source=source, entries=shared_lair_content, images=[]
        )

    def create_test_unique_dragon_fluff(
        self, creature_name: str, source_abbrev: str = "MM"
    ) -> CreatureFluff:
        """Create test fluff with unique dragon content."""
        source = Source(abbreviation=source_abbrev, full_name="Monster Manual")

        unique_content = [
            {
                "type": "entries",
                "name": "Ecology",
                "entries": [
                    f"The {creature_name.lower()} is known for its unique hunting patterns.",
                    "Unlike other dragons, this creature prefers to hunt alone.",
                ],
            }
        ]

        return CreatureFluff(
            name=creature_name, source=source, entries=unique_content, images=[]
        )

    def test_strict_deduplication_prevents_duplicates(self) -> None:
        """Test that strict deduplication prevents identical fluff content."""
        deduplicator = FluffDeduplicator(strategy=DeduplicationStrategy.STRICT)

        # Create identical fluff for different dragons (common scenario)
        red_dragon_fluff = self.create_test_dragon_lair_fluff("Ancient Red Dragon")
        gold_dragon_fluff = self.create_test_dragon_lair_fluff("Ancient Gold Dragon")

        # First fluff should be included
        assert deduplicator.should_include(red_dragon_fluff) is True

        # Second identical fluff should be excluded
        assert deduplicator.should_include(gold_dragon_fluff) is False

        # Check statistics
        stats = deduplicator.get_statistics()
        assert stats["unique_fluff_included"] == 1
        assert stats["duplicate_fluff_detected"] == 1
        assert stats["deduplication_savings"] == 1

    def test_unique_content_is_included(self) -> None:
        """Test that unique fluff content is always included."""
        deduplicator = FluffDeduplicator(strategy=DeduplicationStrategy.STRICT)

        red_dragon_fluff = self.create_test_dragon_lair_fluff("Ancient Red Dragon")
        unique_dragon_fluff = self.create_test_unique_dragon_fluff("Silver Dragon")

        # Both should be included as they have different content
        assert deduplicator.should_include(red_dragon_fluff) is True
        assert deduplicator.should_include(unique_dragon_fluff) is True

        # Check statistics
        stats = deduplicator.get_statistics()
        assert stats["unique_fluff_included"] == 2
        assert stats["duplicate_fluff_detected"] == 0

    def test_loose_strategy_includes_metadata_in_hash(self) -> None:
        """Test that loose strategy considers metadata differences."""
        strict_deduplicator = FluffDeduplicator(strategy=DeduplicationStrategy.STRICT)
        loose_deduplicator = FluffDeduplicator(strategy=DeduplicationStrategy.LOOSE)

        # Create similar content with different metadata
        red_dragon_fluff = self.create_test_dragon_lair_fluff("Ancient Red Dragon")
        # Modify one entry to have different metadata (type/name)
        gold_dragon_data = self.create_test_dragon_lair_fluff("Ancient Gold Dragon")
        # Add a different entry type to make metadata differ
        gold_dragon_data.entries[0].type = "variant_entries"

        # Strict should treat as duplicates (same content text)
        assert strict_deduplicator.should_include(red_dragon_fluff) is True
        assert strict_deduplicator.should_include(gold_dragon_data) is False

        # Reset and test loose strategy
        loose_deduplicator.reset()

        # Loose should treat as different (different metadata)
        assert loose_deduplicator.should_include(red_dragon_fluff) is True
        assert loose_deduplicator.should_include(gold_dragon_data) is True

    def test_none_strategy_disables_deduplication(self) -> None:
        """Test that NONE strategy disables all deduplication."""
        deduplicator = FluffDeduplicator(strategy=DeduplicationStrategy.NONE)

        red_dragon_fluff = self.create_test_dragon_lair_fluff("Ancient Red Dragon")
        gold_dragon_fluff = self.create_test_dragon_lair_fluff("Ancient Gold Dragon")

        # Both should be included regardless of duplication
        assert deduplicator.should_include(red_dragon_fluff) is True
        assert deduplicator.should_include(gold_dragon_fluff) is True

        # No deduplication should occur
        stats = deduplicator.get_statistics()
        assert stats["duplicate_fluff_detected"] == 0

    def test_duplicate_references_tracking(self) -> None:
        """Test that duplicate references are properly tracked."""
        deduplicator = FluffDeduplicator(strategy=DeduplicationStrategy.STRICT)

        red_dragon_fluff = self.create_test_dragon_lair_fluff("Ancient Red Dragon")
        gold_dragon_fluff = self.create_test_dragon_lair_fluff("Ancient Gold Dragon")
        bronze_dragon_fluff = self.create_test_dragon_lair_fluff(
            "Ancient Bronze Dragon"
        )

        # Include first, exclude duplicates
        assert deduplicator.should_include(red_dragon_fluff) is True
        assert deduplicator.should_include(gold_dragon_fluff) is False
        assert deduplicator.should_include(bronze_dragon_fluff) is False

        # Check duplicate references for the original fluff
        duplicate_refs = deduplicator.get_duplicate_references(red_dragon_fluff)
        assert len(duplicate_refs) == 2
        assert "Ancient Gold Dragon (MM)" in duplicate_refs
        assert "Ancient Bronze Dragon (MM)" in duplicate_refs

    def test_content_tracker_integration(self) -> None:
        """Test integration with ContentTracker for cross-reference tracking."""
        content_tracker = ContentTracker()
        deduplicator = FluffDeduplicator(
            strategy=DeduplicationStrategy.STRICT, content_tracker=content_tracker
        )

        red_dragon_fluff = self.create_test_dragon_lair_fluff("Ancient Red Dragon")
        gold_dragon_fluff = self.create_test_dragon_lair_fluff("Ancient Gold Dragon")

        # Process fluff with content tracker
        assert deduplicator.should_include(red_dragon_fluff) is True
        assert deduplicator.should_include(gold_dragon_fluff) is False

        # Check that cross-reference was tracked
        tracked_content = content_tracker.get_tracked_content()
        fluff_refs = [c for c in tracked_content if c.content_type == "fluff_reference"]
        assert len(fluff_refs) == 1
        assert "shared with Ancient Gold Dragon" in fluff_refs[0].name

    def test_reset_clears_state(self) -> None:
        """Test that reset properly clears deduplicator state."""
        deduplicator = FluffDeduplicator(strategy=DeduplicationStrategy.STRICT)

        red_dragon_fluff = self.create_test_dragon_lair_fluff("Ancient Red Dragon")
        gold_dragon_fluff = self.create_test_dragon_lair_fluff("Ancient Gold Dragon")

        # First round
        assert deduplicator.should_include(red_dragon_fluff) is True
        assert deduplicator.should_include(gold_dragon_fluff) is False

        # Reset and test again
        deduplicator.reset()

        # After reset, both should be included again
        assert deduplicator.should_include(red_dragon_fluff) is True
        assert (
            deduplicator.should_include(gold_dragon_fluff) is False
        )  # Still duplicate

        # But after second reset
        deduplicator.reset()
        assert deduplicator.should_include(gold_dragon_fluff) is True  # Now first again

    def test_realistic_dragon_compendium_scenario(self) -> None:
        """Test realistic scenario with multiple dragons sharing lair descriptions."""
        content_tracker = ContentTracker()
        deduplicator = FluffDeduplicator(
            strategy=DeduplicationStrategy.STRICT, content_tracker=content_tracker
        )

        # Create fluff for multiple dragon types with shared lair content
        dragons_with_shared_lairs = [
            "Ancient Red Dragon",
            "Ancient Gold Dragon",
            "Ancient Bronze Dragon",
            "Ancient Copper Dragon",
            "Adult Red Dragon",
        ]

        unique_dragons = [
            "Ancient Silver Dragon",
            "Ancient Black Dragon",
        ]

        included_count = 0
        duplicate_count = 0

        # Process shared lair dragons
        for dragon_name in dragons_with_shared_lairs:
            dragon_fluff = self.create_test_dragon_lair_fluff(dragon_name)
            if deduplicator.should_include(dragon_fluff):
                included_count += 1
            else:
                duplicate_count += 1

        # Process unique dragons
        for dragon_name in unique_dragons:
            dragon_fluff = self.create_test_unique_dragon_fluff(dragon_name)
            if deduplicator.should_include(dragon_fluff):
                included_count += 1

        # Verify results: 1 shared lair + 2 unique = 3 included, 4 duplicates
        assert included_count == 3
        assert duplicate_count == 4

        # Verify statistics match expectations
        stats = deduplicator.get_statistics()
        assert stats["unique_fluff_included"] == 3
        assert stats["duplicate_fluff_detected"] == 4
        assert stats["deduplication_savings"] == 4

        # Verify content tracker recorded the cross-references
        tracked_content = content_tracker.get_tracked_content()
        fluff_refs = [c for c in tracked_content if c.content_type == "fluff_reference"]
        # Should have tracked cross-references for the shared content
        assert len(fluff_refs) > 0

    def test_service_name_for_debugging(self) -> None:
        """Test that service provides proper name for debugging."""
        deduplicator = FluffDeduplicator()
        assert deduplicator.get_service_name() == "FluffDeduplicator"

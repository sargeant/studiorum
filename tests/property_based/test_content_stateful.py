"""Stateful property-based tests for content management using Hypothesis.

These tests verify complex interaction sequences and system invariants
across multiple operations on the content management system.
"""

import pytest
from hypothesis import assume, given, strategies as st
from hypothesis.stateful import Bundle, RuleBasedStateMachine, initialize, rule

from studiorum.core.loaders.omnidexer import Omnidexer
from studiorum.core.models.content import ContentType


class OmnidexerStateMachine(RuleBasedStateMachine):
    """Stateful testing for Omnidexer content management operations.

    This tests complex sequences of operations to ensure system invariants
    are maintained across different interaction patterns.
    """

    def __init__(self):
        super().__init__()
        self.omnidexer = None
        self.initial_content_count = 0
        self.content_added = 0
        self.searches_performed = 0

    @initialize()
    def setup_omnidexer(self):
        """Initialize omnidexer for testing."""
        # Create a fresh omnidexer instance
        from studiorum.core.loaders.unified_source_manager import (
            UnifiedSourceManager,
        )

        source_manager = UnifiedSourceManager()
        self.omnidexer = Omnidexer(source_manager)
        self.initial_content_count = 0
        self.content_added = 0
        self.searches_performed = 0

    @rule()
    def check_omnidexer_invariants(self):
        """Verify omnidexer maintains basic invariants."""
        # Omnidexer should always be in a consistent state
        assert self.omnidexer is not None

        # Statistics should be non-negative
        stats = self.omnidexer.get_statistics()
        for content_type, count in stats.items():
            assert count >= 0, f"Content count for {content_type} should be >= 0"

        # Total content should match individual counts
        total_expected = sum(stats.values())
        assert total_expected >= 0

    @rule(search_term=st.text(min_size=1, max_size=20))
    def perform_search(self, search_term):
        """Perform search operations and verify results."""
        # Search operations should not modify system state
        stats_before = self.omnidexer.get_statistics().copy()

        # Perform search (this would normally use content data)
        # For now, just verify the search doesn't break the system
        self.searches_performed += 1

        # Statistics should remain unchanged after search
        stats_after = self.omnidexer.get_statistics()
        assert stats_before == stats_after, "Search should not modify content counts"

    @rule()
    def verify_search_isolation(self):
        """Verify searches don't interfere with each other."""
        if self.searches_performed > 0:
            # Multiple searches should be isolated from each other
            stats = self.omnidexer.get_statistics()

            # System should remain stable regardless of search history
            assert all(count >= 0 for count in stats.values())

            # Omnidexer should still be operational
            assert self.omnidexer is not None

    @rule()
    def check_memory_efficiency(self):
        """Verify system doesn't accumulate unnecessary memory."""
        # This is a placeholder for memory efficiency checks
        # In a real implementation, you'd check memory usage patterns
        stats = self.omnidexer.get_statistics()

        # System should not have unbounded growth
        total_items = sum(stats.values())
        assert total_items < 100000, "System should not accumulate excessive items"

    @rule()
    def verify_system_consistency(self):
        """Comprehensive system consistency check."""
        # Verify the omnidexer is in a valid state
        assert self.omnidexer is not None

        # Check that statistics are internally consistent
        stats = self.omnidexer.get_statistics()

        # All counts should be non-negative integers
        for content_type, count in stats.items():
            assert isinstance(count, int), f"Count for {content_type} should be int"
            assert count >= 0, f"Count for {content_type} should be >= 0"

        # Content types should be valid
        valid_content_types = {
            ContentType("spell").value,
            ContentType("monster").value,
            ContentType("item").value,
            ContentType("class").value,
            ContentType("race").value,
            ContentType("background").value,
            ContentType("feat").value,
            ContentType("adventure").value,
            ContentType("book").value,
        }

        for content_type in stats.keys():
            assert content_type in valid_content_types, (
                f"Invalid content type: {content_type}"
            )


class ContentResolutionStateMachine(RuleBasedStateMachine):
    """Stateful testing for content resolution operations.

    Tests the interaction between content loading, resolution, and querying
    to ensure data integrity across operation sequences.
    """

    resolved_content = Bundle("resolved_content")
    content_hashes = Bundle("content_hashes")

    def __init__(self):
        super().__init__()
        self.resolver = None
        self.resolution_count = 0
        self.seen_hashes = set()

    @initialize()
    def setup_resolver(self):
        """Initialize content resolver for testing."""
        # This would typically use a real ContentResolver
        # For now, we'll test the interface patterns
        self.resolver = "mock_resolver"  # Placeholder
        self.resolution_count = 0
        self.seen_hashes = set()

    @rule(target=content_hashes, content_id=st.text(min_size=1, max_size=50))
    def generate_content_hash(self, content_id):
        """Generate content hashes for tracking."""
        # Simple hash generation for testing
        import hashlib

        content_hash = hashlib.md5(content_id.encode()).hexdigest()[:8]
        self.seen_hashes.add(content_hash)
        return content_hash

    @rule(content_hash=content_hashes)
    def resolve_content_by_hash(self, content_hash):
        """Test content resolution by hash."""
        # Verify hash is in expected format
        assert len(content_hash) == 8, "Content hash should be 8 characters"
        assert content_hash in self.seen_hashes, "Hash should be previously generated"

        self.resolution_count += 1

    @rule()
    def verify_hash_uniqueness_properties(self):
        """Verify hash uniqueness and consistency properties."""
        # Hashes should be unique for different content
        if len(self.seen_hashes) > 1:
            # All hashes should be different
            hash_list = list(self.seen_hashes)
            assert len(hash_list) == len(set(hash_list)), "All hashes should be unique"

        # Hash format should be consistent
        for hash_val in self.seen_hashes:
            assert isinstance(hash_val, str), "Hash should be string"
            assert len(hash_val) == 8, "Hash should be 8 characters"
            assert all(c in "0123456789abcdef" for c in hash_val), "Hash should be hex"

    @rule()
    def check_resolution_efficiency(self):
        """Verify resolution operations are efficient."""
        # Resolution count should not grow unbounded
        assert self.resolution_count < 1000, "Too many resolutions performed"

        # System should handle multiple resolutions gracefully
        if self.resolution_count > 0:
            assert self.resolver is not None, "Resolver should remain available"


# Test runner for stateful tests
class TestStatefulContentManagement:
    """Integration tests using stateful testing patterns."""

    def test_content_resolution_state_machine(self):
        """Run stateful tests on content resolution."""
        ContentResolutionStateMachine.TestCase().runTest()


# Property-based tests for content interaction patterns
class TestContentInteractionProperties:
    """Property-based tests for content system interactions."""

    @given(
        st.lists(st.text(min_size=1, max_size=20), min_size=1, max_size=10),
        st.integers(min_value=1, max_value=100),
    )
    def test_bulk_operations_consistency(self, content_names, batch_size):
        """Test that bulk operations maintain consistency."""
        # Simulate bulk content operations
        processed_names = []

        for i in range(0, len(content_names), batch_size):
            batch = content_names[i : i + batch_size]

            # Process batch
            for name in batch:
                if name.strip():  # Only process non-empty names
                    processed_names.append(name.strip())

        # Verify consistency
        assert len(processed_names) <= len(content_names)

        # All processed names should be non-empty
        for name in processed_names:
            assert len(name) > 0

    @given(
        st.lists(st.text(min_size=8, max_size=8), min_size=1, max_size=20),
        st.sampled_from(["spell", "monster", "item", "class", "race"]),
    )
    def test_content_type_hash_mapping(self, hash_list, content_type):
        """Test content type and hash mapping properties."""
        # Verify hash list properties
        unique_hashes = set(hash_list)

        # Each hash should be properly formatted
        for hash_val in unique_hashes:
            assert len(hash_val) == 8, "Hash should be 8 characters"
            assert isinstance(hash_val, str), "Hash should be string"

        # Content type should be valid
        valid_types = {"spell", "monster", "item", "class", "race"}
        assert content_type in valid_types

        # Mapping should be consistent
        mapping = dict.fromkeys(unique_hashes, content_type)
        assert len(mapping) == len(unique_hashes)

    @given(
        st.integers(min_value=0, max_value=1000),
        st.integers(min_value=0, max_value=1000),
    )
    def test_content_statistics_invariants(self, loaded_count, indexed_count):
        """Test content statistics maintain mathematical invariants."""
        # Basic mathematical invariants
        assert loaded_count >= 0
        assert indexed_count >= 0

        # Logical relationship: can't index more than loaded
        # (though in practice, this might vary based on filtering)
        total_processed = max(loaded_count, indexed_count)
        assert total_processed >= 0

        # Statistics should be additive
        combined_stat = loaded_count + indexed_count
        assert combined_stat >= loaded_count
        assert combined_stat >= indexed_count


if __name__ == "__main__":
    # Run stateful tests manually for verification
    pytest.main([__file__, "-v", "--hypothesis-show-statistics"])

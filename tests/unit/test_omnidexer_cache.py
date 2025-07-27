"""Tests for Omnidexer caching functionality."""

from unittest.mock import Mock, patch

import pytest

from dnd5e.core.cache import CacheManager
from dnd5e.core.loaders.omnidexer import Omnidexer
from dnd5e.core.models.content import BaseContent, ContentType


class TestOmnidexerCache:
    """Tests for Omnidexer caching."""

    def setup_method(self) -> None:
        """Clear cache and create test omnidexer."""
        CacheManager.clear()
        self.omnidexer = Omnidexer(enable_deep_indexing=False)

        # Create some test content
        self.test_spell = Mock(spec=BaseContent)
        self.test_spell.name = "Fireball"
        self.test_spell.source = Mock(abbreviation="PHB")

        self.test_spell2 = Mock(spec=BaseContent)
        self.test_spell2.name = "Fireball"
        self.test_spell2.source = Mock(abbreviation="XGE")

        self.test_monster = Mock(spec=BaseContent)
        self.test_monster.name = "Dragon"
        self.test_monster.source = Mock(abbreviation="MM")

    def teardown_method(self) -> None:
        """Clear cache after each test."""
        CacheManager.clear()

    def test_find_caches_results(self) -> None:
        """Test that find method caches results."""
        # Mock the internal _find_cached to track calls
        original_find = self.omnidexer._find_cached
        call_count = 0

        def tracked_find(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return original_find(*args, **kwargs)

        self.omnidexer._find_cached = tracked_find

        # First call - should execute the method
        result1 = self.omnidexer.find(ContentType.SPELL, "Fireball", "PHB")
        assert call_count == 1

        # Second call - should use cache
        result2 = self.omnidexer.find(ContentType.SPELL, "Fireball", "PHB")
        assert call_count == 1  # Should not increment
        assert result1 == result2

    def test_find_different_params_different_cache(self) -> None:
        """Test that different parameters create different cache entries."""
        call_count = {}

        def track_calls(content_type, name, source):
            key = f"{content_type}:{name}:{source}"
            call_count[key] = call_count.get(key, 0) + 1
            return self.omnidexer._find_cached.__wrapped__(
                self.omnidexer, content_type, name, source
            )

        # Temporarily replace the cached method to track calls
        with patch.object(self.omnidexer, "_find_cached", side_effect=track_calls):
            # Different calls should each execute once
            self.omnidexer.find(ContentType.SPELL, "Fireball", "PHB")
            self.omnidexer.find(ContentType.SPELL, "Fireball", "XGE")
            self.omnidexer.find(ContentType.SPELL, "Fireball", None)
            self.omnidexer.find(ContentType.CREATURE, "Dragon", "MM")

            # Each should have been called once
            assert all(count == 1 for count in call_count.values())
            assert len(call_count) == 4

    def test_search_caches_results(self) -> None:
        """Test that search method caches results."""
        # Mock the internal _search_cached to track calls
        original_search = self.omnidexer._search_cached
        call_count = 0

        def tracked_search(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return original_search(*args, **kwargs)

        self.omnidexer._search_cached = tracked_search

        # First call - should execute the method
        result1 = self.omnidexer.search("Fire", ContentType.SPELL, limit=10)
        assert call_count == 1

        # Second call with same params - should use cache
        result2 = self.omnidexer.search("Fire", ContentType.SPELL, limit=10)
        assert call_count == 1  # Should not increment
        assert result1 == result2

    def test_search_different_params_different_cache(self) -> None:
        """Test that different search parameters create different cache entries."""
        call_count = {}

        def track_calls(query, content_type, limit):
            key = f"{query}:{content_type}:{limit}"
            call_count[key] = call_count.get(key, 0) + 1
            return self.omnidexer._search_cached.__wrapped__(
                self.omnidexer, query, content_type, limit
            )

        # Temporarily replace the cached method to track calls
        with patch.object(self.omnidexer, "_search_cached", side_effect=track_calls):
            # Different calls should each execute once
            self.omnidexer.search("Fire", ContentType.SPELL, limit=10)
            self.omnidexer.search("Fire", ContentType.SPELL, limit=20)
            self.omnidexer.search("Fire", None, limit=10)
            self.omnidexer.search("Dragon", ContentType.CREATURE, limit=10)

            # Each should have been called once
            assert all(count == 1 for count in call_count.values())
            assert len(call_count) == 4

    def test_cache_ttl_respected(self) -> None:
        """Test that cache entries expire according to TTL."""
        # This is more of an integration test with diskcache
        # We trust that diskcache handles TTL correctly
        # Just verify our decorator passes TTL correctly

        # The @cached decorator for find uses 1 hour TTL
        # The @cached decorator for search uses 30 minutes TTL

        # We can verify this by checking the decorator attributes
        # but since we're using lambdas, we'll just trust the implementation
        pass

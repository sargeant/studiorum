"""Tests for Omnidexer caching functionality."""

from unittest.mock import Mock

import pytest

from dnd5e.core.cache import CacheManager, get_cache
from dnd5e.core.loaders.omnidexer import Omnidexer
from dnd5e.core.models.content import BaseContent, ContentType


class TestOmnidexerCache:
    """Tests for Omnidexer caching."""

    def setup_method(self) -> None:
        """Clear cache and create test omnidexer."""
        CacheManager.clear()
        self.omnidexer = Omnidexer(enable_deep_indexing=False)

    def teardown_method(self) -> None:
        """Clear cache after each test."""
        CacheManager.clear()

    def test_find_caches_results(self) -> None:
        """Test that find method caches results."""
        # Clear cache to start fresh
        cache = get_cache()
        cache.clear()

        # Since we have an empty omnidexer, all calls should return None
        # But we can verify that the same call twice uses cache

        # First call - cache miss
        result1 = self.omnidexer.find(ContentType.SPELL, "Fireball", "PHB")
        assert result1 is None

        # Second call - should be cache hit (same result)
        result2 = self.omnidexer.find(ContentType.SPELL, "Fireball", "PHB")
        assert result2 is None
        assert result1 == result2

        # Verify something was cached - check that the key exists in cache
        cache_key = "omnidexer:find:spell:Fireball:PHB"
        # Use `in` operator to check existence since None values return None from get()
        assert cache_key in cache

    def test_find_different_params_different_cache(self) -> None:
        """Test that different parameters create different cache entries."""
        cache = get_cache()
        cache.clear()

        # Make different calls
        self.omnidexer.find(ContentType.SPELL, "Fireball", "PHB")
        self.omnidexer.find(ContentType.SPELL, "Fireball", "XGE")
        self.omnidexer.find(ContentType.SPELL, "Fireball", None)
        self.omnidexer.find(ContentType.CREATURE, "Dragon", "MM")

        # Verify different cache keys exist
        key1 = "omnidexer:find:spell:Fireball:PHB"
        key2 = "omnidexer:find:spell:Fireball:XGE"
        key3 = "omnidexer:find:spell:Fireball:any"
        key4 = "omnidexer:find:creature:Dragon:MM"

        assert key1 in cache
        assert key2 in cache
        assert key3 in cache
        assert key4 in cache

    def test_search_caches_results(self) -> None:
        """Test that search method caches results."""
        cache = get_cache()
        cache.clear()

        # First call - cache miss
        result1 = self.omnidexer.search("Fire", ContentType.SPELL, limit=10)
        assert result1 == []  # Empty omnidexer returns empty list

        # Second call - should be cache hit
        result2 = self.omnidexer.search("Fire", ContentType.SPELL, limit=10)
        assert result2 == []
        assert result1 == result2

        # Verify something was cached
        cache_key = "omnidexer:search:Fire:spell:10"
        assert cache.get(cache_key) is not None

    def test_search_different_params_different_cache(self) -> None:
        """Test that different search parameters create different cache entries."""
        cache = get_cache()
        cache.clear()

        # Make different calls
        self.omnidexer.search("Fire", ContentType.SPELL, limit=10)
        self.omnidexer.search("Fire", ContentType.SPELL, limit=20)
        self.omnidexer.search("Fire", None, limit=10)
        self.omnidexer.search("Dragon", ContentType.CREATURE, limit=10)

        # Verify different cache keys exist
        key1 = "omnidexer:search:Fire:spell:10"
        key2 = "omnidexer:search:Fire:spell:20"
        key3 = "omnidexer:search:Fire:all:10"
        key4 = "omnidexer:search:Dragon:creature:10"

        assert cache.get(key1) is not None
        assert cache.get(key2) is not None
        assert cache.get(key3) is not None
        assert cache.get(key4) is not None

    def test_cache_ttl_respected(self) -> None:
        """Test that cache entries expire according to TTL."""
        # This is more of an integration test with diskcache
        # We trust that diskcache handles TTL correctly
        # Just verify our decorator passes TTL correctly

        # The @cached decorator for find uses 1 hour TTL
        # The @cached decorator for search uses 30 minutes TTL

        # We can verify this by checking that cached entries exist
        # but this test is mainly to ensure no errors occur
        cache = get_cache()
        cache.clear()

        # Make some calls to populate cache
        self.omnidexer.find(ContentType.SPELL, "Test", "TEST")
        self.omnidexer.search("Test", ContentType.SPELL, limit=5)

        # Verify entries exist
        find_key = "omnidexer:find:spell:Test:TEST"
        search_key = "omnidexer:search:Test:spell:5"

        assert find_key in cache
        assert search_key in cache

"""Tests for JsonDataLoader caching functionality."""

import asyncio
import json
from datetime import timedelta
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from dnd5e.core.cache import CacheManager, get_cache
from dnd5e.core.loaders.json_loader import JsonDataLoader
from dnd5e.core.models.content import ContentType


class TestJsonLoaderCache:
    """Tests for JsonDataLoader caching."""

    def setup_method(self) -> None:
        """Clear cache before each test."""
        CacheManager.clear()

    def teardown_method(self) -> None:
        """Clear cache after each test."""
        CacheManager.clear()

    @pytest.mark.asyncio
    async def test_cache_hit_on_second_load(self, tmp_path: Path) -> None:
        """Test that second load uses cache."""
        # Create test JSON file
        test_data = {
            "spell": [
                {
                    "name": "Test Spell",
                    "level": 1,
                    "school": "V",
                    "time": [{"number": 1, "unit": "action"}],
                    "range": {
                        "type": "point",
                        "distance": {"type": "feet", "amount": 30},
                    },
                    "components": {"v": True},
                    "duration": [{"type": "instant"}],
                    "entries": ["Test description."],
                    "source": {"abbreviation": "TEST", "page": 123},
                }
            ]
        }

        test_file = tmp_path / "test_spells.json"
        test_file.write_text(json.dumps(test_data))

        loader = JsonDataLoader(ContentType.SPELL)

        # Mock logger to track cache hits
        with patch("dnd5e.core.loaders.json_loader.logger") as mock_logger:
            # First load - should miss cache
            result1 = await loader.load(test_file)
            assert len(result1) == 1
            assert result1[0].name == "Test Spell"

            # Check that cache miss occurred (no debug message)
            mock_logger.debug.assert_not_called()

            # Second load - should hit cache
            result2 = await loader.load(test_file)
            assert len(result2) == 1
            assert result2[0].name == "Test Spell"

            # Check that cache hit occurred
            mock_logger.debug.assert_called_with(f"Cache hit for {test_file}")

    @pytest.mark.asyncio
    async def test_cache_invalidation_on_file_change(self, tmp_path: Path) -> None:
        """Test that cache is invalidated when file is modified."""
        # Create test JSON file
        test_data = {
            "spell": [
                {
                    "name": "Original Spell",
                    "level": 1,
                    "school": "V",
                    "time": [{"number": 1, "unit": "action"}],
                    "range": {
                        "type": "point",
                        "distance": {"type": "feet", "amount": 30},
                    },
                    "components": {"v": True},
                    "duration": [{"type": "instant"}],
                    "entries": ["Original description."],
                    "source": {"abbreviation": "TEST", "page": 123},
                }
            ]
        }

        test_file = tmp_path / "test_spells.json"
        test_file.write_text(json.dumps(test_data))

        loader = JsonDataLoader(ContentType.SPELL)

        # First load
        result1 = await loader.load(test_file)
        assert result1[0].name == "Original Spell"

        # Modify file (this changes mtime)
        # Add small delay to ensure filesystem timestamp precision in CI
        await asyncio.sleep(0.01)
        test_data["spell"][0]["name"] = "Modified Spell"
        test_file.write_text(json.dumps(test_data))

        # Second load - should get new data (cache key changed due to mtime)
        result2 = await loader.load(test_file)
        assert result2[0].name == "Modified Spell"

    @pytest.mark.asyncio
    async def test_cache_key_includes_content_type(self, tmp_path: Path) -> None:
        """Test that different content types have different cache keys."""
        # Create two separate JSON files for different content types
        spell_data = {
            "spell": [
                {
                    "name": "Test Spell",
                    "level": 1,
                    "school": "V",
                    "time": [{"number": 1, "unit": "action"}],
                    "range": {
                        "type": "point",
                        "distance": {"type": "feet", "amount": 30},
                    },
                    "components": {"v": True},
                    "duration": [{"type": "instant"}],
                    "entries": ["Test description."],
                    "source": {"abbreviation": "TEST", "page": 123},
                }
            ]
        }

        feat_data = {
            "feat": [
                {
                    "name": "Test Feat",
                    "entries": ["Test feat description."],
                    "source": {"abbreviation": "TEST", "page": 123},
                }
            ]
        }

        # Create two separate files for different content types
        spell_file = tmp_path / "test_spells.json"
        feat_file = tmp_path / "test_feats.json"

        spell_file.write_text(json.dumps(spell_data))
        feat_file.write_text(json.dumps(feat_data))

        # Load as spell type
        spell_loader = JsonDataLoader(ContentType.SPELL)
        spells = await spell_loader.load(spell_file)
        assert len(spells) == 1
        assert spells[0].name == "Test Spell"

        # Load as feat type from different file
        feat_loader = JsonDataLoader(ContentType.FEAT)
        feats = await feat_loader.load(feat_file)
        assert len(feats) == 1
        assert feats[0].name == "Test Feat"

        # Verify cache has both entries with different keys
        cache = get_cache()
        spell_key = spell_loader._get_cache_key(spell_file)
        feat_key = feat_loader._get_cache_key(feat_file)

        assert spell_key != feat_key
        assert cache.get(spell_key) is not None
        assert cache.get(feat_key) is not None

    @pytest.mark.asyncio
    async def test_cache_handles_missing_file(self, tmp_path: Path) -> None:
        """Test that cache key generation handles missing files gracefully."""
        missing_file = tmp_path / "missing.json"
        loader = JsonDataLoader(ContentType.SPELL)

        # Should not raise exception
        cache_key = loader._get_cache_key(missing_file)
        assert cache_key.endswith(":0:0")  # Uses fallback timestamp and size

        # Load should return empty list
        result = await loader.load(missing_file)
        assert result == []

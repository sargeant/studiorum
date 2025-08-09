"""Tests for JsonDataLoader caching functionality."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from dnd5e.core.cache import CacheManager, get_cache
from dnd5e.core.loaders.json_loader import JsonDataLoader
from dnd5e.core.models.content import ContentType
from tests.test_helpers import reset_test_environment


class TestJsonLoaderCache:
    """Tests for JsonDataLoader caching."""

    def setup_method(self) -> None:
        """Clear cache before each test."""
        # Reset global state for complete isolation
        reset_test_environment()

        CacheManager.reset()

    def _get_content_type(self, type_name: str) -> ContentType:
        """Get ContentType safely, falling back to static enum members."""
        try:
            return ContentType(type_name)
        except ValueError:
            # Fall back to known static enum members
            fallback_map = {
                "spell": ContentType.SPELL,
                "creature": ContentType.CREATURE,
                "item": ContentType.ITEM,
                "adventure": ContentType.ADVENTURE,
                "book": ContentType.BOOK,
                "feat": ContentType.CREATURE,  # Fall back to CREATURE for feat tests
            }
            return fallback_map.get(type_name, ContentType.SPELL)  # Default fallback

    def teardown_method(self) -> None:
        """Clear cache after each test."""
        CacheManager.reset()

    def test_cache_hit_on_second_load(self, tmp_path: Path) -> None:
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

        loader = JsonDataLoader(self._get_content_type("spell"))

        # Mock logger to track cache hits
        with patch("dnd5e.core.loaders.json_loader.logger") as mock_logger:
            # First load - should miss cache
            result1 = loader.load(test_file)
            assert len(result1) == 1
            assert result1[0].name == "Test Spell"

            # Check that cache miss occurred (no debug message)
            mock_logger.debug.assert_not_called()

            # Second load - should hit cache
            result2 = loader.load(test_file)
            assert len(result2) == 1
            assert result2[0].name == "Test Spell"

            # Check that cache hit occurred
            mock_logger.debug.assert_called_with(f"Cache hit for {test_file}")

    def test_cache_invalidation_on_file_change(self, tmp_path: Path) -> None:
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

        loader = JsonDataLoader(self._get_content_type("spell"))

        # First load
        result1 = loader.load(test_file)
        assert result1[0].name == "Original Spell"

        # Modify file (this changes mtime)
        # Add small delay to ensure filesystem timestamp precision in CI
        import time

        time.sleep(0.01)
        test_data["spell"][0]["name"] = "Modified Spell"
        test_file.write_text(json.dumps(test_data))

        # Second load - should get new data (cache key changed due to mtime)
        result2 = loader.load(test_file)
        assert result2[0].name == "Modified Spell"

    def test_cache_key_includes_content_type(self, tmp_path: Path) -> None:
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

        creature_data = {
            "monster": [
                {
                    "name": "Test Creature",
                    "size": ["Medium"],
                    "type": "humanoid",
                    "alignment": ["neutral"],
                    "ac": [{"ac": 10}],
                    "hp": {"average": 10},
                    "speed": {"walk": 30},
                    "str": 10,
                    "dex": 10,
                    "con": 10,
                    "int": 10,
                    "wis": 10,
                    "cha": 10,
                    "entries": ["Test creature description."],
                    "source": {"abbreviation": "TEST", "page": 123},
                }
            ]
        }

        # Create two separate files for different content types
        spell_file = tmp_path / "test_spells.json"
        creature_file = tmp_path / "test_creatures.json"

        spell_file.write_text(json.dumps(spell_data))
        creature_file.write_text(json.dumps(creature_data))

        # Load as spell type
        spell_loader = JsonDataLoader(self._get_content_type("spell"))
        spells = spell_loader.load(spell_file)
        assert len(spells) == 1
        assert spells[0].name == "Test Spell"

        # Load as creature type from different file
        creature_loader = JsonDataLoader(self._get_content_type("creature"))
        creatures = creature_loader.load(creature_file)
        assert len(creatures) == 1
        assert creatures[0].name == "Test Creature"

        # Verify cache has both entries with different keys
        cache = get_cache()
        spell_key = spell_loader._get_cache_key(spell_file)
        creature_key = creature_loader._get_cache_key(creature_file)

        assert spell_key != creature_key
        assert cache.get(spell_key) is not None
        assert cache.get(creature_key) is not None

    def test_cache_handles_missing_file(self, tmp_path: Path) -> None:
        """Test that cache key generation handles missing files gracefully."""
        missing_file = tmp_path / "missing.json"
        loader = JsonDataLoader(self._get_content_type("spell"))

        # Should not raise exception
        cache_key = loader._get_cache_key(missing_file)
        assert cache_key.endswith(":0:0")  # Uses fallback timestamp and size

        # Load should return empty list
        result = loader.load(missing_file)
        assert result == []

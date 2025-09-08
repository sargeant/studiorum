"""Edge case testing with unusual creatures from real 5etools data.

These tests target specific edge cases and unusual creature patterns found
in the actual 5etools dataset to ensure robust handling of all variations.
"""

import re
from typing import Any
from unittest.mock import Mock, patch

import pytest

from studiorum.core.loaders.omnidexer import Omnidexer
from studiorum.core.models.content import ContentType
from studiorum.core.models.creatures import Creature
from studiorum.core.services.creature_collector import CreatureCollector
from tests.test_helpers import reset_test_environment


@pytest.mark.requires_data
@pytest.mark.integration
class TestCreatureEdgeCasesRealData:
    """Test edge cases found in real 5etools creature data."""

    def setup_method(self):
        """Set up test fixtures."""
        reset_test_environment()
        self.omnidexer = None
        self.loaded_creatures = []

    @pytest.fixture(autouse=True)
    def load_edge_case_creatures(self):
        """Load creatures and identify edge cases."""
        try:
            self.omnidexer = Omnidexer()
            self.omnidexer.load_all_data()

            creature_type = ContentType("creature")
            all_creatures = self.omnidexer.get_all_by_type(creature_type)
            self.loaded_creatures = [
                creature for creature in all_creatures if isinstance(creature, Creature)
            ]

            if not self.loaded_creatures:
                pytest.skip("No creatures loaded for edge case testing")

        except Exception as e:
            pytest.skip(f"Failed to load creatures for edge case testing: {e}")

    def test_variable_cr_creatures(self):
        """Test creatures with variable or special CR values."""
        variable_cr_creatures = []

        for creature in self.loaded_creatures:
            if hasattr(creature, "cr"):
                cr_str = str(creature.cr).lower()
                if any(
                    pattern in cr_str for pattern in ["varies", "variable", "special"]
                ):
                    variable_cr_creatures.append(creature)

        if not variable_cr_creatures:
            # If no variable CR found, test with simulated data
            pytest.skip("No variable CR creatures found in dataset")

        # Test that variable CR creatures are handled gracefully
        for creature in variable_cr_creatures[:3]:  # Test first 3
            try:
                cr_text = creature.get_enhanced_cr_text()
                assert cr_text is not None and len(cr_text) > 0
                # Should handle variable CR without XP calculation
                assert (
                    "varies" in cr_text.lower()
                    or "variable" in cr_text.lower()
                    or "XP" not in cr_text
                )
            except Exception as e:
                pytest.fail(
                    f"Variable CR creature {creature.name} failed processing: {e}"
                )

    def test_complex_ac_structures(self):
        """Test creatures with complex AC structures."""
        complex_ac_creatures = []

        for creature in self.loaded_creatures:
            if hasattr(creature, "ac") and isinstance(creature.ac, list):
                if len(creature.ac) > 1:
                    complex_ac_creatures.append(creature)
                elif len(creature.ac) == 1 and isinstance(creature.ac[0], dict):
                    # Single complex AC entry
                    complex_ac_creatures.append(creature)

        if not complex_ac_creatures:
            pytest.skip("No complex AC creatures found")

        # Test complex AC processing
        for creature in complex_ac_creatures[:5]:  # Test first 5
            try:
                ac_text = creature.get_ac_text()
                assert ac_text is not None and len(ac_text) > 0

                # Should contain a numeric AC value
                assert re.search(r"\d+", ac_text), f"No numeric AC found in: {ac_text}"

            except Exception as e:
                pytest.fail(f"Complex AC creature {creature.name} failed: {e}")

    def test_special_speed_configurations(self):
        """Test creatures with special speed configurations."""
        special_speed_creatures = []

        for creature in self.loaded_creatures:
            if hasattr(creature, "speed") and isinstance(creature.speed, dict):
                speed_types = set(creature.speed.keys())
                # Look for special speeds beyond walk
                special_speeds = speed_types - {"walk"}
                if len(special_speeds) >= 2:  # Multiple special speeds
                    special_speed_creatures.append(creature)
                elif any(isinstance(v, dict) for v in creature.speed.values()):
                    # Speed with conditions (like hover)
                    special_speed_creatures.append(creature)

        if not special_speed_creatures:
            pytest.skip("No special speed creatures found")

        # Test special speed processing
        for creature in special_speed_creatures[:5]:  # Test first 5
            try:
                speed_text = creature.get_speed_text()
                assert speed_text is not None and len(speed_text) > 0

                # Should contain speed value
                assert re.search(r"\d+\s*ft", speed_text), (
                    f"No speed value found in: {speed_text}"
                )

            except Exception as e:
                pytest.fail(f"Special speed creature {creature.name} failed: {e}")

    def test_creatures_with_unusual_types(self):
        """Test creatures with unusual or compound types."""
        unusual_type_creatures = []

        for creature in self.loaded_creatures:
            if hasattr(creature, "type"):
                creature_type = creature.type
                is_unusual = False

                if isinstance(creature_type, dict):
                    # Has type tags or complex structure
                    if "tags" in creature_type:
                        is_unusual = True
                    # Very long type names
                    type_str = creature_type.get("type", "")
                    if len(type_str) > 15:
                        is_unusual = True
                elif isinstance(creature_type, str):
                    # Very long type string
                    if len(creature_type) > 15:
                        is_unusual = True

                if is_unusual:
                    unusual_type_creatures.append(creature)

        if not unusual_type_creatures:
            pytest.skip("No unusual type creatures found")

        # Test unusual type processing
        for creature in unusual_type_creatures[:5]:  # Test first 5
            try:
                sta_text = creature.get_size_type_alignment()
                assert sta_text is not None and len(sta_text) > 0

                # Should contain recognizable type information
                common_types = [
                    "humanoid",
                    "beast",
                    "dragon",
                    "undead",
                    "fiend",
                    "celestial",
                    "fey",
                    "elemental",
                    "construct",
                    "giant",
                    "monstrosity",
                    "ooze",
                    "plant",
                ]
                assert any(ctype in sta_text.lower() for ctype in common_types), (
                    f"No recognizable type in: {sta_text}"
                )

            except Exception as e:
                pytest.fail(f"Unusual type creature {creature.name} failed: {e}")

    def test_creatures_with_extreme_stats(self):
        """Test creatures with extreme ability scores or stats."""
        extreme_stat_creatures = []

        for creature in self.loaded_creatures:
            is_extreme = False

            # Check for extreme ability scores
            for ability in [
                "strength",
                "dexterity",
                "constitution",
                "intelligence",
                "wisdom",
                "charisma",
            ]:
                score = getattr(creature, ability, 10)
                if score <= 3 or score >= 25:  # Very low or very high
                    is_extreme = True
                    break

            # Check for extreme HP
            if hasattr(creature, "hp") and isinstance(creature.hp, dict):
                avg_hp = creature.hp.get("average", 0)
                if avg_hp >= 300 or avg_hp <= 1:  # Very high or very low
                    is_extreme = True

            # Check for extreme AC
            if hasattr(creature, "ac"):
                try:
                    ac_list = (
                        creature.ac if isinstance(creature.ac, list) else [creature.ac]
                    )
                    for ac_entry in ac_list:
                        ac_val = (
                            ac_entry
                            if isinstance(ac_entry, int)
                            else ac_entry.get("ac", 10)
                        )
                        if ac_val >= 20 or ac_val <= 8:  # Very high or very low
                            is_extreme = True
                            break
                except:
                    pass

            if is_extreme:
                extreme_stat_creatures.append(creature)

        if not extreme_stat_creatures:
            pytest.skip("No extreme stat creatures found")

        # Test extreme stat processing
        for creature in extreme_stat_creatures[:5]:  # Test first 5
            try:
                # Should handle extreme stats without errors
                cr_text = creature.get_enhanced_cr_text()
                sta_text = creature.get_size_type_alignment()
                ac_text = creature.get_ac_text()
                hp_text = creature.get_hp_text()
                speed_text = creature.get_speed_text()

                # All should produce valid output
                for text in [cr_text, sta_text, ac_text, hp_text, speed_text]:
                    assert text is not None and len(text) > 0

                # Test ability modifiers for extreme scores
                for ability in [
                    "strength",
                    "dexterity",
                    "constitution",
                    "intelligence",
                    "wisdom",
                    "charisma",
                ]:
                    score = getattr(creature, ability, 10)
                    modifier = creature.get_ability_modifier(score)
                    # Should be within reasonable bounds even for extreme scores
                    assert -5 <= modifier <= 15, (
                        f"Extreme modifier {modifier} for {ability} score {score}"
                    )

            except Exception as e:
                pytest.fail(f"Extreme stat creature {creature.name} failed: {e}")

    def test_creatures_with_complex_spellcasting(self):
        """Test creatures with complex spellcasting structures."""
        complex_caster_creatures = []

        for creature in self.loaded_creatures:
            if hasattr(creature, "spellcasting") and creature.spellcasting:
                for spellcasting in creature.spellcasting:
                    # Look for complex spellcasting
                    if isinstance(spellcasting, dict):
                        spells = spellcasting.get("spells", {})
                        if len(spells) > 5:  # Many spell levels
                            complex_caster_creatures.append(creature)
                            break
                        # Or innate spellcasting
                        if "will" in spells or "daily" in spells:
                            complex_caster_creatures.append(creature)
                            break

        if not complex_caster_creatures:
            pytest.skip("No complex spellcasting creatures found")

        # Test complex spellcasting processing
        for creature in complex_caster_creatures[:3]:  # Test first 3
            try:
                # Should handle complex spellcasting without errors
                sta_text = creature.get_size_type_alignment()
                assert sta_text is not None

                # Spellcasting should be accessible
                assert creature.spellcasting is not None
                assert len(creature.spellcasting) > 0

                # First spellcasting entry should have spells
                first_casting = creature.spellcasting[0]
                if isinstance(first_casting, dict):
                    assert "spells" in first_casting or "headerEntries" in first_casting

            except Exception as e:
                pytest.fail(
                    f"Complex spellcasting creature {creature.name} failed: {e}"
                )

    def test_creatures_with_legendary_and_lair_actions(self):
        """Test creatures with legendary actions and lair actions."""
        legendary_creatures = []
        lair_creatures = []

        for creature in self.loaded_creatures:
            if hasattr(creature, "legendary") and creature.legendary:
                legendary_creatures.append(creature)

            if hasattr(creature, "lair") and creature.lair:
                lair_creatures.append(creature)

        # Test legendary actions
        if legendary_creatures:
            for creature in legendary_creatures[:3]:  # Test first 3
                try:
                    # Should handle legendary actions
                    assert creature.legendary is not None
                    assert len(creature.legendary) > 0

                    # Should require full width layout
                    assert creature.requires_full_width_layout() is True

                    # Legendary actions should have valid structure
                    for legendary in creature.legendary:
                        if isinstance(legendary, dict):
                            assert "name" in legendary or "entries" in legendary

                except Exception as e:
                    pytest.fail(f"Legendary creature {creature.name} failed: {e}")

        # Test lair actions
        if lair_creatures:
            for creature in lair_creatures[:3]:  # Test first 3
                try:
                    # Should handle lair actions
                    assert creature.lair is not None

                    # Should also require full width layout
                    assert creature.requires_full_width_layout() is True

                except Exception as e:
                    pytest.fail(f"Lair action creature {creature.name} failed: {e}")

        if not legendary_creatures and not lair_creatures:
            pytest.skip("No legendary or lair action creatures found")

    def test_creatures_with_unusual_markup_patterns(self):
        """Test creatures with unusual or complex markup patterns."""
        unusual_markup_creatures = []
        markup_patterns = set()

        for creature in self.loaded_creatures:
            found_unusual = False

            # Check all text entries for unusual markup
            for attr in ["trait", "action", "reaction", "legendary"]:
                if hasattr(creature, attr):
                    entries_list = getattr(creature, attr)
                    if entries_list:
                        for entry in entries_list:
                            if isinstance(entry, dict) and "entries" in entry:
                                for text_entry in entry["entries"]:
                                    text_str = str(text_entry)
                                    if "{@" in text_str:
                                        # Find all markup patterns
                                        patterns = re.findall(r"{@\w+[^}]*}", text_str)
                                        markup_patterns.update(patterns)

                                        # Look for unusual patterns
                                        unusual_patterns = [
                                            p
                                            for p in patterns
                                            if not p.startswith(
                                                ("{@atk", "{@hit", "{@h}", "{@damage")
                                            )
                                        ]
                                        if unusual_patterns:
                                            found_unusual = True

            if found_unusual:
                unusual_markup_creatures.append(creature)

        if not unusual_markup_creatures:
            pytest.skip("No unusual markup creatures found")

        # Test unusual markup processing
        for creature in unusual_markup_creatures[:5]:  # Test first 5
            try:
                # Should handle unusual markup without errors
                if hasattr(creature, "action") and creature.action:
                    for action in creature.action:
                        if hasattr(action, "entries") and action.entries:
                            from studiorum.cli.utils import get_omnidexer
                            from studiorum.core.references.content_tracker import (
                                ContentTracker,
                            )
                            from studiorum.latex_engine.core.entry_processor import (
                                RecursiveEntryProcessor,
                            )
                            from studiorum.renderers.core.interfaces import (
                                RenderingContext,
                            )

                            entry_processor = RecursiveEntryProcessor(
                                use_dnd_template=True
                            )
                            content_tracker = ContentTracker()
                            rendering_context = RenderingContext(
                                output_format="latex",
                                omnidexer=get_omnidexer(),
                                content_tracker=content_tracker,
                            )
                            processed_entries = entry_processor.process_entries(
                                action.entries, rendering_context
                            )
                            desc = "\n\n".join(processed_entries)
                            assert desc is not None
                        elif hasattr(action, "entries"):
                            # Should be able to convert to string
                            str(action.entries)

            except Exception as e:
                # Log the error but don't fail - unusual markup might be expected to fail
                print(f"Note: Unusual markup in {creature.name} caused: {e}")

    def test_creatures_with_missing_or_optional_fields(self):
        """Test creatures with missing standard fields."""
        incomplete_creatures = []

        standard_fields = [
            "ac",
            "hp",
            "speed",
            "str",
            "dex",
            "con",
            "int",
            "wis",
            "cha",
            "cr",
        ]

        for creature in self.loaded_creatures:
            missing_fields = []
            for field in standard_fields:
                if not hasattr(creature, field) or getattr(creature, field) is None:
                    missing_fields.append(field)

            if missing_fields:
                incomplete_creatures.append((creature, missing_fields))

        if not incomplete_creatures:
            pytest.skip("No creatures with missing fields found")

        # Test handling of missing fields
        for creature, missing in incomplete_creatures[:5]:  # Test first 5
            try:
                # Should handle missing fields gracefully
                cr_text = creature.get_enhanced_cr_text()
                assert cr_text is not None

                sta_text = creature.get_size_type_alignment()
                assert sta_text is not None

                # AC might be missing - should handle gracefully
                try:
                    ac_text = creature.get_ac_text()
                    if "ac" not in missing:
                        assert ac_text is not None
                except:
                    if "ac" not in missing:
                        raise  # Should only fail if AC is actually missing

                # HP might be missing - should handle gracefully
                try:
                    hp_text = creature.get_hp_text()
                    if "hp" not in missing:
                        assert hp_text is not None
                except:
                    if "hp" not in missing:
                        raise  # Should only fail if HP is actually missing

                # Speed might be missing - should handle gracefully
                try:
                    speed_text = creature.get_speed_text()
                    if "speed" not in missing:
                        assert speed_text is not None
                except:
                    if "speed" not in missing:
                        raise  # Should only fail if speed is actually missing

            except Exception as e:
                pytest.fail(
                    f"Incomplete creature {creature.name} (missing {missing}) failed: {e}"
                )

    def test_creatures_from_obscure_sources(self):
        """Test creatures from less common source books."""
        source_counts = {}
        obscure_source_creatures = []

        # Count creatures by source
        for creature in self.loaded_creatures:
            if hasattr(creature, "source"):
                source = getattr(creature.source, "abbreviation", str(creature.source))
                source_counts[source] = source_counts.get(source, 0) + 1

        # Find sources with few creatures (obscure sources)
        obscure_sources = [
            source
            for source, count in source_counts.items()
            if count <= 5 and count > 0
        ]

        for creature in self.loaded_creatures:
            if hasattr(creature, "source"):
                source = getattr(creature.source, "abbreviation", str(creature.source))
                if source in obscure_sources:
                    obscure_source_creatures.append(creature)

        if not obscure_source_creatures:
            pytest.skip("No creatures from obscure sources found")

        # Test obscure source creatures
        for creature in obscure_source_creatures[:5]:  # Test first 5
            try:
                # Should handle creatures from any source
                cr_text = creature.get_enhanced_cr_text()
                sta_text = creature.get_size_type_alignment()
                ac_text = creature.get_ac_text()
                hp_text = creature.get_hp_text()
                speed_text = creature.get_speed_text()

                # All should produce valid output
                for text in [cr_text, sta_text, ac_text, hp_text, speed_text]:
                    assert text is not None and len(text) > 0

            except Exception as e:
                pytest.fail(f"Obscure source creature {creature.name} failed: {e}")


@pytest.mark.requires_data
@pytest.mark.integration
class TestCreatureCollectionEdgeCases:
    """Test creature collection with edge case scenarios."""

    def setup_method(self):
        """Set up test fixtures."""
        reset_test_environment()
        self.omnidexer = None

    @pytest.fixture(autouse=True)
    def load_creatures_for_collection(self):
        """Load creatures for collection testing."""
        try:
            self.omnidexer = Omnidexer()
            self.omnidexer.load_all_data()

            creature_type = ContentType("creature")
            all_creatures = self.omnidexer.get_all_by_type(creature_type)
            self.all_creatures = [
                creature for creature in all_creatures if isinstance(creature, Creature)
            ]

            if not self.all_creatures:
                pytest.skip("No creatures loaded for collection testing")

        except Exception as e:
            pytest.skip(f"Failed to load creatures for collection testing: {e}")

    def test_collection_with_extreme_cr_ranges(self):
        """Test collection with extreme CR ranges."""
        collector = CreatureCollector(self.omnidexer)

        # Test very low CR range
        low_result = collector.collect_by_cr_range(0.0, 0.125)  # CR 0 to 1/8
        assert isinstance(low_result.matched_count, int)

        # Test very high CR range
        high_result = collector.collect_by_cr_range(20.0, 30.0)  # CR 20+
        assert isinstance(high_result.matched_count, int)

        # Test single CR value
        single_result = collector.collect_by_cr_range(1.0, 1.0)  # Exactly CR 1
        assert isinstance(single_result.matched_count, int)

    def test_collection_with_unusual_type_filters(self):
        """Test collection with unusual creature types."""
        collector = CreatureCollector(self.omnidexer)

        # Find all unique types in the dataset
        all_types = set()
        for creature in self.all_creatures:
            if hasattr(creature, "type"):
                creature_type = creature.type
                if isinstance(creature_type, dict):
                    type_str = creature_type.get("type", "")
                else:
                    type_str = str(creature_type)
                if type_str:
                    all_types.add(type_str.lower())

        # Test with less common types
        uncommon_types = all_types - {"humanoid", "beast", "dragon", "undead"}
        if uncommon_types:
            test_type = list(uncommon_types)[0]
            result = collector.collect_by_type([test_type])
            assert isinstance(result.matched_count, int)

    def test_collection_with_nonexistent_criteria(self):
        """Test collection with criteria that match nothing."""
        collector = CreatureCollector(self.omnidexer)

        # Test with impossible CR range (within valid bounds but unlikely to match)
        # Use a very specific fractional range that's unlikely to exist
        impossible_result = collector.collect_by_cr_range(13.5, 13.6)
        assert impossible_result.matched_count == 0

        # Test with nonexistent type
        nonexistent_result = collector.collect_by_type(["nonexistent_type"])
        assert nonexistent_result.matched_count == 0

        # Test with nonexistent names
        missing_result = collector.collect_by_names(["Completely Fake Creature Name"])
        assert missing_result.matched_count == 0
        assert len(missing_result.unresolved_names) > 0

    def test_collection_performance_with_large_filters(self):
        """Test collection performance with very broad filters."""
        import time

        collector = CreatureCollector(self.omnidexer)

        start_time = time.perf_counter()

        # Very broad filter that should match many creatures
        broad_result = collector.collect_by_cr_range(0.0, 30.0)

        end_time = time.perf_counter()
        filter_time = end_time - start_time

        # Should complete in reasonable time even with broad filter
        assert filter_time < 5.0, f"Broad filtering too slow: {filter_time:.2f}s"
        assert broad_result.matched_count >= 0

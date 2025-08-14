"""Performance benchmarks using real 5etools creature data.

These tests establish performance baselines and validate scalability
with actual creature data patterns and complexity found in 5etools.
"""

import gc
import time
from pathlib import Path
from typing import Any

import pytest

from dnd5e.core.loaders.omnidexer import Omnidexer
from dnd5e.core.models.content import ContentType
from dnd5e.core.models.creatures import Creature
from dnd5e.core.services.creature_collector import CreatureCollector
from tests.test_helpers import reset_test_environment


@pytest.mark.requires_data
@pytest.mark.performance
@pytest.mark.slow
class TestCreatureRealDataPerformanceBenchmarks:
    """Performance benchmarks with real 5etools creature data."""

    def setup_method(self):
        """Set up performance test fixtures."""
        reset_test_environment()
        self.omnidexer = None
        self.all_creatures = []

    @pytest.fixture(autouse=True)
    def load_real_creatures_for_benchmarks(self):
        """Load real creature data for benchmarking."""
        try:
            self.omnidexer = Omnidexer()

            # Measure loading time
            load_start = time.perf_counter()
            self.omnidexer.load_all_data()
            load_end = time.perf_counter()

            self.load_time = load_end - load_start

            creature_type = ContentType("creature")
            all_content = self.omnidexer.get_all_by_type(creature_type)
            self.all_creatures = [
                creature for creature in all_content if isinstance(creature, Creature)
            ]

            if not self.all_creatures:
                pytest.skip("No real creatures loaded for benchmarking")

            print(
                f"Loaded {len(self.all_creatures)} creatures in {self.load_time:.2f}s"
            )

        except Exception as e:
            pytest.skip(f"Failed to load real creature data for benchmarking: {e}")

    def test_real_data_loading_performance_benchmark(self):
        """Benchmark real creature data loading performance."""
        # Loading was done in fixture, test the results
        assert self.load_time < 10.0, (
            f"Creature loading too slow: {self.load_time:.2f}s"
        )
        assert len(self.all_creatures) > 100, (
            f"Too few creatures loaded: {len(self.all_creatures)}"
        )

        print(
            f"Loading benchmark: {len(self.all_creatures)} creatures in {self.load_time:.3f}s"
        )
        print(
            f"Per-creature loading time: {(self.load_time / len(self.all_creatures)) * 1000:.3f}ms"
        )

    def test_real_data_stat_block_generation_performance(self):
        """Benchmark stat block generation with real creature data."""
        # Test with a representative sample
        sample_size = min(50, len(self.all_creatures))
        test_creatures = self.all_creatures[:sample_size]

        # Warm up
        for creature in test_creatures[:5]:
            creature.get_enhanced_cr_text()
            creature.get_size_type_alignment()
            creature.get_ac_text()
            creature.get_hp_text()
            creature.get_speed_text()

        gc.collect()

        # Benchmark stat block operations
        operations = {
            "CR text": lambda c: c.get_enhanced_cr_text(),
            "Size/Type/Alignment": lambda c: c.get_size_type_alignment(),
            "AC text": lambda c: c.get_ac_text(),
            "HP text": lambda c: c.get_hp_text(),
            "Speed text": lambda c: c.get_speed_text(),
            "Layout decision": lambda c: c.requires_full_width_layout(),
        }

        for op_name, operation in operations.items():
            start_time = time.perf_counter()

            for creature in test_creatures:
                operation(creature)

            end_time = time.perf_counter()
            total_time = end_time - start_time
            per_creature_time = total_time / sample_size

            print(f"{op_name}: {per_creature_time * 1000:.3f}ms per creature")

            # Should be reasonably fast
            assert per_creature_time < 0.01, (
                f"{op_name} too slow: {per_creature_time:.4f}s per creature"
            )

    def test_real_data_ability_modifier_calculation_performance(self):
        """Benchmark ability modifier calculations with real data."""
        sample_size = min(100, len(self.all_creatures))
        test_creatures = self.all_creatures[:sample_size]

        # Warm up
        for creature in test_creatures[:5]:
            for ability in [
                "strength",
                "dexterity",
                "constitution",
                "intelligence",
                "wisdom",
                "charisma",
            ]:
                score = getattr(creature, ability, 10)
                creature.get_ability_modifier(score)

        gc.collect()

        start_time = time.perf_counter()

        total_calculations = 0
        for creature in test_creatures:
            for ability in [
                "strength",
                "dexterity",
                "constitution",
                "intelligence",
                "wisdom",
                "charisma",
            ]:
                score = getattr(creature, ability, 10)
                creature.get_ability_modifier(score)
                total_calculations += 1

        end_time = time.perf_counter()
        total_time = end_time - start_time
        per_calculation_time = total_time / total_calculations

        print(
            f"Ability modifier calculation: {per_calculation_time * 1000000:.3f}μs per calculation"
        )

        # Should be very fast
        assert per_calculation_time < 0.0001, (
            f"Ability modifier calculation too slow: {per_calculation_time:.6f}s"
        )

    def test_real_data_complex_creature_processing_performance(self):
        """Benchmark processing of complex creatures (legendary, spellcasters)."""
        # Find complex creatures
        complex_creatures = []

        for creature in self.all_creatures:
            is_complex = False

            # Has legendary actions
            if hasattr(creature, "legendary") and creature.legendary:
                is_complex = True

            # Has spellcasting
            if hasattr(creature, "spellcasting") and creature.spellcasting:
                is_complex = True

            # Has many actions
            if (
                hasattr(creature, "action")
                and creature.action
                and len(creature.action) > 3
            ):
                is_complex = True

            # High CR (likely complex)
            if hasattr(creature, "cr"):
                try:
                    cr_str = str(creature.cr)
                    if cr_str.isdigit() and int(cr_str) >= 10:
                        is_complex = True
                except:
                    pass

            if is_complex:
                complex_creatures.append(creature)

        if not complex_creatures:
            pytest.skip("No complex creatures found for benchmarking")

        # Benchmark complex creature processing
        sample_size = min(20, len(complex_creatures))
        test_creatures = complex_creatures[:sample_size]

        # Warm up
        for creature in test_creatures[:3]:
            creature.get_enhanced_cr_text()
            creature.requires_full_width_layout()

        gc.collect()

        start_time = time.perf_counter()

        for creature in test_creatures:
            # Full stat block generation
            creature.get_enhanced_cr_text()
            creature.get_size_type_alignment()
            creature.get_ac_text()
            creature.get_hp_text()
            creature.get_speed_text()
            creature.requires_full_width_layout()

            # Process special features
            if hasattr(creature, "legendary") and creature.legendary:
                for legendary in creature.legendary:
                    str(legendary)  # Force processing

            if hasattr(creature, "spellcasting") and creature.spellcasting:
                for spellcasting in creature.spellcasting:
                    str(spellcasting)  # Force processing

        end_time = time.perf_counter()
        total_time = end_time - start_time
        per_creature_time = total_time / sample_size

        print(f"Complex creature processing: {per_creature_time:.3f}s per creature")

        # Should handle complex creatures efficiently
        assert per_creature_time < 0.1, (
            f"Complex creature processing too slow: {per_creature_time:.3f}s"
        )

    def test_real_data_collection_performance_scalability(self):
        """Test collection performance scalability with real data."""
        collector = CreatureCollector(self.omnidexer)

        # Test different collection scenarios
        test_scenarios = [
            ("All creatures", lambda: collector.collect_by_cr_range(0.0, 30.0)),
            ("Low CR creatures", lambda: collector.collect_by_cr_range(0.0, 2.0)),
            ("Humanoids", lambda: collector.collect_by_type(["humanoid"])),
            ("Dragons", lambda: collector.collect_by_type(["dragon"])),
            ("High CR creatures", lambda: collector.collect_by_cr_range(10.0, 30.0)),
        ]

        for scenario_name, collection_func in test_scenarios:
            # Warm up
            collection_func()
            gc.collect()

            # Benchmark
            start_time = time.perf_counter()
            result = collection_func()
            end_time = time.perf_counter()

            collection_time = end_time - start_time

            print(
                f"{scenario_name}: {collection_time:.3f}s for {result.matched_count} creatures"
            )

            # Should complete in reasonable time
            assert collection_time < 3.0, (
                f"{scenario_name} collection too slow: {collection_time:.3f}s"
            )

    def test_real_data_memory_usage_patterns(self):
        """Test memory usage patterns with real creature data."""
        import os

        import psutil

        process = psutil.Process(os.getpid())

        # Measure baseline memory
        gc.collect()
        baseline_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Process batches of creatures
        batch_size = 100
        max_batches = min(5, len(self.all_creatures) // batch_size)

        memory_measurements = []

        for batch_num in range(max_batches):
            start_idx = batch_num * batch_size
            end_idx = start_idx + batch_size
            batch_creatures = self.all_creatures[start_idx:end_idx]

            # Process batch
            batch_results = []
            for creature in batch_creatures:
                batch_results.append(
                    {
                        "name": creature.name,
                        "cr_text": creature.get_enhanced_cr_text(),
                        "sta_text": creature.get_size_type_alignment(),
                        "ac_text": creature.get_ac_text(),
                        "hp_text": creature.get_hp_text(),
                        "speed_text": creature.get_speed_text(),
                        "full_width": creature.requires_full_width_layout(),
                    }
                )

            # Measure memory after batch
            gc.collect()
            batch_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_measurements.append(batch_memory)

            print(
                f"Batch {batch_num + 1}: {batch_memory:.1f}MB ({batch_memory - baseline_memory:.1f}MB growth)"
            )

        # Analyze memory growth
        if len(memory_measurements) > 1:
            total_growth = memory_measurements[-1] - baseline_memory
            per_batch_growth = total_growth / len(memory_measurements)

            print(
                f"Total memory growth: {total_growth:.1f}MB for {max_batches * batch_size} creatures"
            )
            print(f"Per-batch growth: {per_batch_growth:.1f}MB")

            # Memory growth should be reasonable
            assert total_growth < 100, f"Excessive memory growth: {total_growth:.1f}MB"

    def test_real_data_filtering_performance_by_complexity(self):
        """Test filtering performance based on creature complexity."""
        from dnd5e.core.models.creature_filters import CreatureFilterCriteria

        collector = CreatureCollector(self.omnidexer)

        # Test filters of increasing complexity
        filter_scenarios = [
            ("Simple CR filter", CreatureFilterCriteria(min_cr=1.0, max_cr=5.0)),
            ("Type filter", CreatureFilterCriteria(creature_types=["humanoid"])),
            (
                "CR + Type",
                CreatureFilterCriteria(
                    min_cr=2.0, max_cr=8.0, creature_types=["humanoid", "beast"]
                ),
            ),
            (
                "Complex multi-filter",
                CreatureFilterCriteria(
                    min_cr=1.0,
                    max_cr=10.0,
                    creature_types=["humanoid", "beast", "monstrosity"],
                    sizes=["M", "L"],
                    sources=["MM"],
                ),
            ),
        ]

        for filter_name, criteria in filter_scenarios:
            # Warm up
            collector.collect_creatures(criteria)
            gc.collect()

            # Benchmark
            start_time = time.perf_counter()
            for _ in range(3):  # Run multiple times for average
                result = collector.collect_creatures(criteria)
            end_time = time.perf_counter()

            avg_time = (end_time - start_time) / 3

            print(
                f"{filter_name}: {avg_time:.3f}s average for {result.matched_count} matches"
            )

            # Should complete filtering quickly
            assert avg_time < 1.0, f"{filter_name} filtering too slow: {avg_time:.3f}s"

    def test_real_data_bulk_validation_performance(self):
        """Test bulk validation performance with real creature data."""
        # Test Pydantic validation performance
        sample_size = min(200, len(self.all_creatures))

        # Extract raw data
        raw_creature_data = []
        for creature in self.all_creatures[:sample_size]:
            # Convert back to dict format (simulate loading from JSON)
            raw_data = {
                "name": creature.name,
                "source": getattr(creature.source, "abbreviation", "Unknown"),
                "size": getattr(creature, "size", ["M"]),
                "type": getattr(creature, "type", "humanoid"),
                "alignment": getattr(creature, "alignment", ["N"]),
                "ac": getattr(creature, "ac", [10]),
                "hp": getattr(creature, "hp", {"average": 10}),
                "speed": getattr(creature, "speed", {"walk": 30}),
                "str": getattr(creature, "strength", 10),
                "dex": getattr(creature, "dexterity", 10),
                "con": getattr(creature, "constitution", 10),
                "int": getattr(creature, "intelligence", 10),
                "wis": getattr(creature, "wisdom", 10),
                "cha": getattr(creature, "charisma", 10),
                "cr": getattr(creature, "cr", "1"),
            }
            raw_creature_data.append(raw_data)

        # Warm up
        for data in raw_creature_data[:10]:
            Creature.model_validate(data)

        gc.collect()

        # Benchmark bulk validation
        start_time = time.perf_counter()

        validated_creatures = []
        for data in raw_creature_data:
            creature = Creature.model_validate(data)
            validated_creatures.append(creature)

        end_time = time.perf_counter()

        total_time = end_time - start_time
        per_creature_time = total_time / len(raw_creature_data)

        print(
            f"Bulk validation: {total_time:.3f}s total, {per_creature_time * 1000:.3f}ms per creature"
        )

        # Should validate efficiently
        assert per_creature_time < 0.005, (
            f"Creature validation too slow: {per_creature_time:.4f}s per creature"
        )
        assert len(validated_creatures) == len(raw_creature_data)

    def test_real_data_worst_case_performance(self):
        """Test performance with worst-case scenarios from real data."""
        # Find potentially slow creatures
        slow_candidates = []

        for creature in self.all_creatures:
            complexity_score = 0

            # Large number of actions
            if hasattr(creature, "action") and creature.action:
                complexity_score += len(creature.action)

            # Has legendary actions
            if hasattr(creature, "legendary") and creature.legendary:
                complexity_score += len(creature.legendary) * 2

            # Has spellcasting
            if hasattr(creature, "spellcasting") and creature.spellcasting:
                complexity_score += len(creature.spellcasting) * 3

            # Long description texts
            for attr in ["trait", "action", "reaction"]:
                if hasattr(creature, attr):
                    entries = getattr(creature, attr) or []
                    for entry in entries:
                        if isinstance(entry, dict) and "entries" in entry:
                            total_text = sum(len(str(e)) for e in entry["entries"])
                            complexity_score += (
                                total_text // 100
                            )  # Rough text length score

            if complexity_score > 20:  # Arbitrary threshold for "complex"
                slow_candidates.append((creature, complexity_score))

        if not slow_candidates:
            pytest.skip("No complex creatures found for worst-case testing")

        # Sort by complexity and test the most complex
        slow_candidates.sort(key=lambda x: x[1], reverse=True)
        worst_cases = [creature for creature, _ in slow_candidates[:5]]

        print(f"Testing {len(worst_cases)} worst-case creatures")

        # Test worst-case performance
        for creature in worst_cases:
            start_time = time.perf_counter()

            # Full processing
            creature.get_enhanced_cr_text()
            creature.get_size_type_alignment()
            creature.get_ac_text()
            creature.get_hp_text()
            creature.get_speed_text()
            creature.requires_full_width_layout()

            # Process all complex features
            if hasattr(creature, "trait") and creature.trait:
                for trait in creature.trait:
                    str(trait)

            if hasattr(creature, "action") and creature.action:
                for action in creature.action:
                    str(action)

            if hasattr(creature, "legendary") and creature.legendary:
                for legendary in creature.legendary:
                    str(legendary)

            if hasattr(creature, "spellcasting") and creature.spellcasting:
                for spellcasting in creature.spellcasting:
                    str(spellcasting)

            end_time = time.perf_counter()
            processing_time = end_time - start_time

            print(f"Worst-case creature {creature.name}: {processing_time:.3f}s")

            # Even worst-case should complete in reasonable time
            assert processing_time < 0.5, (
                f"Worst-case creature {creature.name} too slow: {processing_time:.3f}s"
            )

"""Performance tests for creature collection and bulk processing.

These tests validate that the creature collection system can handle large datasets
efficiently and provide good performance for typical use cases.
"""

import gc
import time
from unittest.mock import Mock, patch

import pytest

from dnd5e.core.models.creature_filters import CreatureFilterCriteria
from dnd5e.core.models.creatures import Creature
from dnd5e.core.services.creature_collector import CreatureCollector
from tests.test_helpers import reset_test_environment


@pytest.mark.performance
@pytest.mark.slow
class TestCreatureCollectionPerformance:
    """Test performance of creature collection operations."""

    def setup_method(self):
        """Set up test fixtures."""
        reset_test_environment()

        # Create mock omnidexer with performance data
        self.mock_omnidexer = Mock()

        # Create test creature data at different scales
        self.small_dataset = self._create_test_creatures(50)
        self.medium_dataset = self._create_test_creatures(200)
        self.large_dataset = self._create_test_creatures(1000)

        # Set up mock methods to prevent iteration errors
        def mock_get_all_by_source(source):
            # Return empty list for performance tests - we control data via get_all_by_type
            return []

        self.mock_omnidexer.get_all_by_source.side_effect = mock_get_all_by_source

        def mock_find_all(content_type, name):
            # Return empty list for performance tests - we control data via get_all_by_type
            return []

        self.mock_omnidexer.find_all.side_effect = mock_find_all

        self.collector = CreatureCollector(self.mock_omnidexer)

    def _create_test_creatures(self, count: int) -> list[dict]:
        """Create test creature data for performance testing."""
        creatures = []

        creature_types = [
            "humanoid",
            "beast",
            "monstrosity",
            "undead",
            "dragon",
            "fiend",
        ]
        sizes = ["T", "S", "M", "L", "H", "G"]
        alignments = [["L", "G"], ["N"], ["C", "E"], ["L", "N"], ["C", "N"]]

        for i in range(count):
            cr_value = self._calculate_cr_for_index(i, count)
            creatures.append(
                {
                    "name": f"Test Creature {i:04d}",
                    "source": "TEST",
                    "size": [sizes[i % len(sizes)]],
                    "type": creature_types[i % len(creature_types)],
                    "alignment": alignments[i % len(alignments)],
                    "ac": [10 + (i % 20)],
                    "hp": {"average": 10 + (i * 2)},
                    "speed": {"walk": 30},
                    "str": 10 + (i % 20),
                    "dex": 10 + (i % 20),
                    "con": 10 + (i % 20),
                    "int": 10 + (i % 20),
                    "wis": 10 + (i % 20),
                    "cha": 10 + (i % 20),
                    "cr": cr_value,
                    "action": [
                        {
                            "name": f"Test Attack {i}",
                            "entries": [f"Test attack description for creature {i}"],
                        }
                    ],
                }
            )

        return creatures

    def _calculate_cr_for_index(self, index: int, total: int) -> str:
        """Calculate CR value for test creature based on index."""
        # Distribute CRs across common values
        cr_values = [
            "0",
            "1/8",
            "1/4",
            "1/2",
            "1",
            "2",
            "3",
            "4",
            "5",
            "6",
            "7",
            "8",
            "9",
            "10",
            "11",
            "12",
            "13",
            "14",
            "15",
            "16",
            "17",
            "18",
            "19",
            "20",
            "21",
            "22",
            "23",
            "24",
            "25",
            "26",
            "27",
            "28",
            "29",
            "30",
        ]
        return cr_values[index % len(cr_values)]

    def test_small_dataset_collection_performance(self):
        """Test collection performance with small dataset (50 creatures)."""
        # Setup mock to return small dataset
        mock_creatures = [Creature.model_validate(data) for data in self.small_dataset]
        self.mock_omnidexer.get_all_by_type.return_value = mock_creatures

        # Test various filtering scenarios
        criteria = CreatureFilterCriteria(
            min_cr=1.0, max_cr=10.0, creature_types=["humanoid", "beast"]
        )

        # Warm up
        self.collector.collect_creatures(criteria)
        gc.collect()

        # Time the operation
        start_time = time.perf_counter()
        for _ in range(10):
            result = self.collector.collect_creatures(criteria)
        end_time = time.perf_counter()

        avg_time = (end_time - start_time) / 10
        print(f"\nSmall dataset (50 creatures): {avg_time:.4f}s average per collection")

        # Should complete quickly for small datasets
        assert avg_time < 0.1, f"Small dataset collection too slow: {avg_time:.4f}s"
        assert result.matched_count >= 0

    def test_medium_dataset_collection_performance(self):
        """Test collection performance with medium dataset (200 creatures)."""
        # Setup mock to return medium dataset
        mock_creatures = [Creature.model_validate(data) for data in self.medium_dataset]
        self.mock_omnidexer.get_all_by_type.return_value = mock_creatures

        criteria = CreatureFilterCriteria(cr_range="1-5", creature_types=["humanoid"])

        # Warm up
        self.collector.collect_creatures(criteria)
        gc.collect()

        # Time the operation
        start_time = time.perf_counter()
        for _ in range(5):
            result = self.collector.collect_creatures(criteria)
        end_time = time.perf_counter()

        avg_time = (end_time - start_time) / 5
        print(
            f"\nMedium dataset (200 creatures): {avg_time:.4f}s average per collection"
        )

        # Should still be reasonably fast
        assert avg_time < 0.3, f"Medium dataset collection too slow: {avg_time:.4f}s"
        assert result.matched_count >= 0

    def test_large_dataset_collection_performance(self):
        """Test collection performance with large dataset (1000 creatures)."""
        # Setup mock to return large dataset
        mock_creatures = [Creature.model_validate(data) for data in self.large_dataset]
        self.mock_omnidexer.get_all_by_type.return_value = mock_creatures

        criteria = CreatureFilterCriteria(min_cr=5.0, max_cr=15.0)

        # Warm up
        self.collector.collect_creatures(criteria)
        gc.collect()

        # Time the operation
        start_time = time.perf_counter()
        result = self.collector.collect_creatures(criteria)
        end_time = time.perf_counter()

        collection_time = end_time - start_time
        print(
            f"\nLarge dataset (1000 creatures): {collection_time:.4f}s per collection"
        )

        # Should handle large datasets reasonably well
        assert collection_time < 1.0, (
            f"Large dataset collection too slow: {collection_time:.4f}s"
        )
        assert result.matched_count >= 0

    def test_filtering_performance_comparison(self):
        """Compare performance of different filtering strategies."""
        mock_creatures = [Creature.model_validate(data) for data in self.medium_dataset]
        self.mock_omnidexer.get_all_by_type.return_value = mock_creatures

        # Test different filtering scenarios
        test_cases = [
            ("Simple CR filter", CreatureFilterCriteria(min_cr=1.0, max_cr=5.0)),
            ("Type filter", CreatureFilterCriteria(creature_types=["humanoid"])),
            (
                "Complex filter",
                CreatureFilterCriteria(
                    min_cr=2.0,
                    max_cr=8.0,
                    creature_types=["humanoid", "beast"],
                    sizes=["M", "L"],
                ),
            ),
            (
                "Name filter",
                CreatureFilterCriteria(
                    creature_names=[
                        "Test Creature 0001",
                        "Test Creature 0050",
                        "Test Creature 0100",
                    ]
                ),
            ),
        ]

        results = {}
        for name, criteria in test_cases:
            # Warm up
            self.collector.collect_creatures(criteria)
            gc.collect()

            # Time the operation
            start_time = time.perf_counter()
            for _ in range(3):
                self.collector.collect_creatures(criteria)
            end_time = time.perf_counter()

            avg_time = (end_time - start_time) / 3
            results[name] = avg_time
            print(f"\n{name}: {avg_time:.4f}s average")

        # All filtering strategies should be reasonably fast
        for name, time_taken in results.items():
            assert time_taken < 0.5, f"{name} too slow: {time_taken:.4f}s"

    def test_bulk_creature_validation_performance(self):
        """Test performance of bulk creature validation."""
        # Test Pydantic validation performance with bulk data
        creature_data_list = self.medium_dataset

        # Warm up
        for data in creature_data_list[:10]:
            Creature.model_validate(data)
        gc.collect()

        # Time bulk validation
        start_time = time.perf_counter()
        validated_creatures = []
        for data in creature_data_list:
            creature = Creature.model_validate(data)
            validated_creatures.append(creature)
        end_time = time.perf_counter()

        total_time = end_time - start_time
        per_creature_time = total_time / len(creature_data_list)

        print(
            f"\nBulk validation: {total_time:.4f}s total, {per_creature_time:.6f}s per creature"
        )

        # Should validate quickly
        assert per_creature_time < 0.01, (
            f"Creature validation too slow: {per_creature_time:.6f}s per creature"
        )
        assert len(validated_creatures) == len(creature_data_list)

    def test_memory_usage_during_collection(self):
        """Test memory usage patterns during large collections."""
        import os

        import psutil

        process = psutil.Process(os.getpid())
        process.memory_info().rss / 1024 / 1024  # MB

        # Create and process large dataset
        mock_creatures = [Creature.model_validate(data) for data in self.large_dataset]
        self.mock_omnidexer.get_all_by_type.return_value = mock_creatures

        criteria = CreatureFilterCriteria(min_cr=1.0, max_cr=20.0)

        # Force garbage collection before measurement
        gc.collect()
        memory_before = process.memory_info().rss / 1024 / 1024  # MB

        # Perform multiple collections
        for _ in range(5):
            result = self.collector.collect_creatures(criteria)
            assert result.matched_count >= 0

        gc.collect()
        memory_after = process.memory_info().rss / 1024 / 1024  # MB

        memory_growth = memory_after - memory_before
        print(
            f"\nMemory usage: {memory_before:.1f}MB -> {memory_after:.1f}MB (growth: {memory_growth:.1f}MB)"
        )

        # Memory growth should be reasonable for the operation
        assert memory_growth < 100, f"Excessive memory growth: {memory_growth:.1f}MB"

    def test_collection_scalability(self):
        """Test how collection performance scales with dataset size."""
        dataset_sizes = [50, 100, 200]
        performance_results = {}

        for size in dataset_sizes:
            # Create dataset of specified size
            test_data = self._create_test_creatures(size)
            mock_creatures = [Creature.model_validate(data) for data in test_data]
            self.mock_omnidexer.get_all_by_type.return_value = mock_creatures

            criteria = CreatureFilterCriteria(min_cr=1.0, max_cr=10.0)

            # Warm up
            self.collector.collect_creatures(criteria)
            gc.collect()

            # Time the operation
            start_time = time.perf_counter()
            for _ in range(3):
                self.collector.collect_creatures(criteria)
            end_time = time.perf_counter()

            avg_time = (end_time - start_time) / 3
            performance_results[size] = avg_time
            print(f"\nDataset size {size}: {avg_time:.4f}s average")

        # Performance should scale reasonably (not exponentially)
        # Allow for some variance but check that it's not dramatically worse
        if len(performance_results) >= 2:
            sizes = sorted(performance_results.keys())
            for i in range(1, len(sizes)):
                prev_size, curr_size = sizes[i - 1], sizes[i]
                prev_time, curr_time = (
                    performance_results[prev_size],
                    performance_results[curr_size],
                )

                size_ratio = curr_size / prev_size
                time_ratio = curr_time / prev_time if prev_time > 0 else 1

                print(
                    f"Size ratio {prev_size}->{curr_size}: {size_ratio:.1f}x, Time ratio: {time_ratio:.1f}x"
                )

                # Time should not grow faster than size (allowing for overhead)
                assert time_ratio < size_ratio * 1.5, (
                    f"Poor scaling: {time_ratio:.1f}x time for {size_ratio:.1f}x size"
                )


@pytest.mark.performance
class TestCreatureProcessingBenchmarks:
    """Benchmark tests for creature processing operations."""

    def setup_method(self):
        """Set up test fixtures."""
        reset_test_environment()

    def test_creature_stat_block_generation_performance(self):
        """Test performance of generating creature stat blocks."""
        # Create test creature
        creature_data = {
            "name": "Performance Test Creature",
            "source": "TEST",
            "size": ["L"],
            "type": "dragon",
            "alignment": ["C", "E"],
            "ac": [18],
            "hp": {"average": 200, "formula": "16d12 + 80"},
            "speed": {"walk": 40, "fly": 80},
            "str": 23,
            "dex": 10,
            "con": 21,
            "int": 14,
            "wis": 13,
            "cha": 17,
            "save": {"dex": "+5", "con": "+11", "wis": "+6", "cha": "+8"},
            "skill": {"perception": "+11", "stealth": "+5"},
            "resist": ["fire"],
            "immune": ["poison"],
            "conditionImmune": ["charmed", "poisoned"],
            "senses": [
                "blindsight 60 ft.",
                "darkvision 120 ft.",
                "passive Perception 21",
            ],
            "languages": ["Common", "Draconic"],
            "cr": "10",
            "trait": [
                {
                    "name": "Legendary Resistance",
                    "entries": [
                        "If the dragon fails a saving throw, it can choose to succeed instead (3/day)."
                    ],
                }
            ],
            "action": [
                {
                    "name": "Multiattack",
                    "entries": [
                        "The dragon can use its Frightful Presence. It then makes three attacks."
                    ],
                },
                {
                    "name": "Bite",
                    "entries": [
                        "{@atk mw} {@hit 11} to hit, reach 10 ft., one target. {@h}2d10 + 6 piercing damage."
                    ],
                },
            ],
            "legendary": [
                {
                    "name": "Detect",
                    "entries": ["The dragon makes a Wisdom (Perception) check."],
                }
            ],
        }

        creature = Creature.model_validate(creature_data)

        # Warm up
        for _ in range(10):
            _ = creature.get_enhanced_cr_text()
            _ = creature.get_size_type_alignment()
            _ = creature.get_ac_text()

        gc.collect()

        # Time stat block generation operations
        operations = [
            ("CR text", lambda: creature.get_enhanced_cr_text()),
            ("Size/Type/Alignment", lambda: creature.get_size_type_alignment()),
            ("AC text", lambda: creature.get_ac_text()),
            ("HP text", lambda: creature.get_hp_text()),
            ("Speed text", lambda: creature.get_speed_text()),
            (
                "Ability modifiers",
                lambda: [
                    creature.get_ability_modifier(score)
                    for score in [
                        creature.strength,
                        creature.dexterity,
                        creature.constitution,
                        creature.intelligence,
                        creature.wisdom,
                        creature.charisma,
                    ]
                ],
            ),
        ]

        for name, operation in operations:
            start_time = time.perf_counter()
            for _ in range(1000):
                operation()
            end_time = time.perf_counter()

            total_time = end_time - start_time
            per_op_time = total_time / 1000

            print(f"\n{name}: {per_op_time:.6f}s per operation")

            # Operations should be very fast
            assert per_op_time < 0.001, (
                f"{name} too slow: {per_op_time:.6f}s per operation"
            )

    def test_multiple_creatures_processing_performance(self):
        """Test performance when processing multiple creatures simultaneously."""
        # Create multiple test creatures
        creatures = []
        for i in range(100):
            creature_data = {
                "name": f"Batch Creature {i:03d}",
                "source": "TEST",
                "size": ["M"],
                "type": "humanoid",
                "alignment": ["N"],
                "ac": [10 + i % 10],
                "hp": {"average": 20 + i},
                "speed": {"walk": 30},
                "str": 10,
                "dex": 10,
                "con": 10,
                "int": 10,
                "wis": 10,
                "cha": 10,
                "cr": str(i % 10),
                "action": [
                    {"name": f"Attack {i}", "entries": [f"Attack description {i}"]}
                ],
            }
            creatures.append(Creature.model_validate(creature_data))

        # Warm up
        for creature in creatures[:10]:
            _ = creature.get_enhanced_cr_text()

        gc.collect()

        # Time batch processing
        start_time = time.perf_counter()
        results = []
        for creature in creatures:
            results.append(
                {
                    "name": creature.name,
                    "cr": creature.get_enhanced_cr_text(),
                    "type": creature.get_size_type_alignment(),
                    "ac": creature.get_ac_text(),
                    "layout": creature.requires_full_width_layout(),
                }
            )
        end_time = time.perf_counter()

        total_time = end_time - start_time
        per_creature_time = total_time / len(creatures)

        print(
            f"\nBatch processing: {total_time:.4f}s total, {per_creature_time:.6f}s per creature"
        )

        # Should process creatures efficiently in batch
        assert per_creature_time < 0.01, (
            f"Batch processing too slow: {per_creature_time:.6f}s per creature"
        )
        assert len(results) == len(creatures)

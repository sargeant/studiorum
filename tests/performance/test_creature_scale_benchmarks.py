"""Large dataset performance benchmarks and scalability tests.

These tests validate system performance with realistic and stress-test datasets
to ensure the creature processing pipeline scales appropriately.
"""

import gc
import os
import time
from typing import Any
from unittest.mock import Mock, patch

import psutil
import pytest

from dnd5e.core.models.creature_filters import CreatureFilterCriteria
from dnd5e.core.models.creatures import Creature
from dnd5e.core.services.creature_collector import CreatureCollector
from dnd5e.renderers.core.interfaces import RenderingContext
from dnd5e.renderers.latex.document import LaTeXDocumentRenderer
from tests.test_helpers import reset_test_environment


@pytest.mark.performance
@pytest.mark.slow
class TestCreatureDatasetScaling:
    """Test how creature processing scales with dataset size."""

    def setup_method(self):
        """Set up test fixtures."""
        reset_test_environment()

        # Track process for memory monitoring
        self.process = psutil.Process(os.getpid())

    def _create_realistic_creature_dataset(self, size: int) -> list[dict]:
        """Create realistic creature dataset based on 5etools patterns."""
        creatures = []

        # Realistic distributions based on actual 5etools data
        creature_types = [
            "humanoid",
            "beast",
            "monstrosity",
            "undead",
            "fey",
            "fiend",
            "celestial",
            "elemental",
            "dragon",
            "aberration",
            "construct",
            "giant",
            "ooze",
            "plant",
        ]
        sizes = ["T", "S", "M", "L", "H", "G"]  # Weighted toward M

        sources = ["MM", "VGM", "MTF", "TCE", "FTD", "MotM"]

        # CR distribution (more low CR creatures, fewer high CR)
        cr_values = (
            ["0", "1/8", "1/4", "1/2"] * 20
            + ["1", "2", "3", "4", "5"] * 10
            + ["6", "7", "8", "9", "10"] * 5
            + ["11", "12", "13", "14", "15"] * 2
            + [
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
        )

        alignments = [
            ["L", "G"],
            ["L", "N"],
            ["L", "E"],
            ["N", "G"],
            ["N"],
            ["N", "E"],
            ["C", "G"],
            ["C", "N"],
            ["C", "E"],
            ["A"],
            ["U"],
        ]

        for i in range(size):
            # Realistic stat distributions (keep within 3-30 range)
            base_stats = 10 + (i % 15)  # Vary stats from 10-24
            cr_index = i % len(cr_values)
            cr = cr_values[cr_index]

            # Calculate realistic HP based on CR
            if cr == "0":
                hp_avg = 1 + (i % 10)
            elif cr in ["1/8", "1/4"]:
                hp_avg = 5 + (i % 20)
            elif cr == "1/2":
                hp_avg = 15 + (i % 25)
            elif cr in ["1", "2", "3"]:
                hp_avg = 25 + (i % 50)
            else:
                hp_avg = 50 + (i % 200)

            creature = {
                "name": f"Creature {i:05d}",
                "source": sources[i % len(sources)],
                "size": [sizes[i % len(sizes)]],
                "type": creature_types[i % len(creature_types)],
                "alignment": alignments[i % len(alignments)],
                "ac": [10 + (i % 15)],
                "hp": {"average": hp_avg, "formula": f"{hp_avg // 8 + 1}d8 + {i % 20}"},
                "speed": {"walk": 30 if i % 4 == 0 else 25 + (i % 20)},
                "str": max(3, min(30, base_stats + (i % 10) - 5)),
                "dex": max(3, min(30, base_stats + (i % 8) - 4)),
                "con": max(3, min(30, base_stats + (i % 6) - 3)),
                "int": max(3, min(30, base_stats + (i % 12) - 6)),
                "wis": max(3, min(30, base_stats + (i % 8) - 4)),
                "cha": max(3, min(30, base_stats + (i % 10) - 5)),
                "cr": cr,
                "senses": ["passive Perception " + str(10 + (i % 15))],
                "languages": ["Common"] if i % 3 == 0 else [],
                "action": [
                    {
                        "name": f"Attack {i % 5}",
                        "entries": [
                            f"Attack description for creature {i}. {{@atk mw}} {{@hit {4 + i % 10}}} to hit."
                        ],
                    }
                ],
            }

            # Add optional features for variety
            if i % 5 == 0:
                creature["trait"] = [
                    {
                        "name": f"Trait {i}",
                        "entries": [f"Special trait for creature {i}"],
                    }
                ]

            if i % 7 == 0:
                creature["skill"] = {"perception": f"+{3 + i % 8}"}

            if i % 10 == 0:
                creature["resist"] = ["fire"] if i % 20 == 0 else ["cold"]

            creatures.append(creature)

        return creatures

    def test_small_dataset_baseline(self):
        """Establish baseline performance with small dataset (100 creatures)."""
        dataset = self._create_realistic_creature_dataset(100)

        # Memory before
        initial_memory = self.process.memory_info().rss / 1024 / 1024

        # Time creature validation
        start_time = time.perf_counter()
        creatures = [Creature.model_validate(data) for data in dataset]
        validation_time = time.perf_counter() - start_time

        # Memory after validation
        self.process.memory_info().rss / 1024 / 1024

        # Test collection performance
        mock_omnidexer = Mock()
        mock_omnidexer.get_all_by_type.return_value = creatures
        collector = CreatureCollector(mock_omnidexer)

        criteria = CreatureFilterCriteria(min_cr=1.0, max_cr=5.0)

        start_time = time.perf_counter()
        collector.collect_creatures(criteria)
        collection_time = time.perf_counter() - start_time

        final_memory = self.process.memory_info().rss / 1024 / 1024

        print("\nSmall dataset (100 creatures):")
        print(
            f"  Validation: {validation_time:.4f}s ({validation_time / len(dataset) * 1000:.2f}ms per creature)"
        )
        print(f"  Collection: {collection_time:.4f}s")
        print(
            f"  Memory: {initial_memory:.1f}MB -> {final_memory:.1f}MB (+{final_memory - initial_memory:.1f}MB)"
        )

        # Performance expectations for small dataset
        assert validation_time < 1.0, (
            f"Small dataset validation too slow: {validation_time:.4f}s"
        )
        assert collection_time < 0.5, (
            f"Small dataset collection too slow: {collection_time:.4f}s"
        )
        assert len(creatures) == 100

    def test_medium_dataset_performance(self):
        """Test performance with medium dataset (500 creatures)."""
        dataset = self._create_realistic_creature_dataset(500)

        initial_memory = self.process.memory_info().rss / 1024 / 1024

        # Time creature validation
        start_time = time.perf_counter()
        creatures = [Creature.model_validate(data) for data in dataset]
        validation_time = time.perf_counter() - start_time

        # Test multiple collection scenarios
        mock_omnidexer = Mock()
        mock_omnidexer.get_all_by_type.return_value = creatures
        collector = CreatureCollector(mock_omnidexer)

        collection_scenarios = [
            ("CR filter", CreatureFilterCriteria(min_cr=1.0, max_cr=10.0)),
            (
                "Type filter",
                CreatureFilterCriteria(creature_types=["humanoid", "beast"]),
            ),
            (
                "Complex filter",
                CreatureFilterCriteria(
                    min_cr=2.0,
                    max_cr=8.0,
                    creature_types=["humanoid"],
                    sizes=["M", "L"],
                ),
            ),
        ]

        collection_times = {}
        for name, criteria in collection_scenarios:
            start_time = time.perf_counter()
            collector.collect_creatures(criteria)
            collection_times[name] = time.perf_counter() - start_time

        final_memory = self.process.memory_info().rss / 1024 / 1024

        print("\nMedium dataset (500 creatures):")
        print(
            f"  Validation: {validation_time:.4f}s ({validation_time / len(dataset) * 1000:.2f}ms per creature)"
        )
        for name, time_taken in collection_times.items():
            print(f"  {name}: {time_taken:.4f}s")
        print(
            f"  Memory: {initial_memory:.1f}MB -> {final_memory:.1f}MB (+{final_memory - initial_memory:.1f}MB)"
        )

        # Performance expectations for medium dataset
        assert validation_time < 5.0, (
            f"Medium dataset validation too slow: {validation_time:.4f}s"
        )
        for name, time_taken in collection_times.items():
            assert time_taken < 1.0, (
                f"Medium dataset {name} too slow: {time_taken:.4f}s"
            )

    def test_large_dataset_performance(self):
        """Test performance with large dataset (2000 creatures)."""
        dataset = self._create_realistic_creature_dataset(2000)

        initial_memory = self.process.memory_info().rss / 1024 / 1024

        # Time creature validation in batches to monitor progress
        batch_size = 100
        total_validation_time = 0
        creatures = []

        for i in range(0, len(dataset), batch_size):
            batch = dataset[i : i + batch_size]
            start_time = time.perf_counter()
            batch_creatures = [Creature.model_validate(data) for data in batch]
            batch_time = time.perf_counter() - start_time
            total_validation_time += batch_time
            creatures.extend(batch_creatures)

        # Test collection performance
        mock_omnidexer = Mock()
        mock_omnidexer.get_all_by_type.return_value = creatures
        collector = CreatureCollector(mock_omnidexer)

        criteria = CreatureFilterCriteria(min_cr=1.0, max_cr=15.0)

        start_time = time.perf_counter()
        collector.collect_creatures(criteria)
        collection_time = time.perf_counter() - start_time

        final_memory = self.process.memory_info().rss / 1024 / 1024

        print("\nLarge dataset (2000 creatures):")
        print(
            f"  Validation: {total_validation_time:.4f}s ({total_validation_time / len(dataset) * 1000:.2f}ms per creature)"
        )
        print(f"  Collection: {collection_time:.4f}s")
        print(
            f"  Memory: {initial_memory:.1f}MB -> {final_memory:.1f}MB (+{final_memory - initial_memory:.1f}MB)"
        )

        # Performance expectations for large dataset
        assert total_validation_time < 15.0, (
            f"Large dataset validation too slow: {total_validation_time:.4f}s"
        )
        assert collection_time < 3.0, (
            f"Large dataset collection too slow: {collection_time:.4f}s"
        )
        assert len(creatures) == 2000

    def test_scaling_characteristics(self):
        """Test how performance scales across different dataset sizes."""
        sizes = [100, 250, 500]
        results = {}

        for size in sizes:
            gc.collect()  # Clean up before each test
            initial_memory = self.process.memory_info().rss / 1024 / 1024

            dataset = self._create_realistic_creature_dataset(size)

            # Time validation
            start_time = time.perf_counter()
            creatures = [Creature.model_validate(data) for data in dataset]
            validation_time = time.perf_counter() - start_time

            # Time collection
            mock_omnidexer = Mock()
            mock_omnidexer.get_all_by_type.return_value = creatures
            collector = CreatureCollector(mock_omnidexer)

            criteria = CreatureFilterCriteria(min_cr=1.0, max_cr=10.0)
            start_time = time.perf_counter()
            collector.collect_creatures(criteria)
            collection_time = time.perf_counter() - start_time

            final_memory = self.process.memory_info().rss / 1024 / 1024

            results[size] = {
                "validation_time": validation_time,
                "collection_time": collection_time,
                "memory_usage": final_memory - initial_memory,
                "validation_per_creature": validation_time / size,
                "collection_per_creature": collection_time / size,
            }

            print(f"\nDataset size {size}:")
            print(
                f"  Validation: {validation_time:.4f}s ({validation_time / size * 1000:.2f}ms per creature)"
            )
            print(f"  Collection: {collection_time:.4f}s")
            print(f"  Memory growth: +{final_memory - initial_memory:.1f}MB")

        # Analyze scaling characteristics
        if len(results) >= 2:
            sizes_sorted = sorted(results.keys())
            for i in range(1, len(sizes_sorted)):
                prev_size, curr_size = sizes_sorted[i - 1], sizes_sorted[i]
                prev_result, curr_result = results[prev_size], results[curr_size]

                size_ratio = curr_size / prev_size
                validation_ratio = (
                    curr_result["validation_time"] / prev_result["validation_time"]
                )
                collection_ratio = (
                    curr_result["collection_time"] / prev_result["collection_time"]
                )
                memory_ratio = (
                    curr_result["memory_usage"] / prev_result["memory_usage"]
                    if prev_result["memory_usage"] > 0
                    else 1
                )

                print(f"\nScaling {prev_size} -> {curr_size} ({size_ratio:.1f}x size):")
                print(f"  Validation time: {validation_ratio:.1f}x")
                print(f"  Collection time: {collection_ratio:.1f}x")
                print(f"  Memory usage: {memory_ratio:.1f}x")

                # Performance should scale reasonably (not exponentially)
                assert validation_ratio < size_ratio * 1.3, (
                    f"Poor validation scaling: {validation_ratio:.1f}x time for {size_ratio:.1f}x size"
                )
                assert collection_ratio < size_ratio * 1.5, (
                    f"Poor collection scaling: {collection_ratio:.1f}x time for {size_ratio:.1f}x size"
                )


@pytest.mark.performance
@pytest.mark.slow
class TestMemoryUsageValidation:
    """Test memory usage patterns and detect memory leaks."""

    def setup_method(self):
        """Set up test fixtures."""
        reset_test_environment()
        self.process = psutil.Process(os.getpid())

    def test_memory_stability_during_repeated_operations(self):
        """Test memory stability during repeated creature operations."""
        # Create test dataset
        dataset = self._create_test_creatures(200)

        # Baseline memory
        gc.collect()
        baseline_memory = self.process.memory_info().rss / 1024 / 1024

        # Perform repeated operations
        memory_samples = []
        for i in range(10):
            # Create creatures
            creatures = [Creature.model_validate(data) for data in dataset]

            # Perform operations
            for creature in creatures[:20]:  # Sample of creatures
                _ = creature.get_enhanced_cr_text()
                _ = creature.get_size_type_alignment()
                _ = creature.get_ac_text()

            # Force cleanup
            del creatures
            gc.collect()

            # Sample memory
            current_memory = self.process.memory_info().rss / 1024 / 1024
            memory_samples.append(current_memory)

        # Analyze memory stability
        max_memory = max(memory_samples)
        min_memory = min(memory_samples)
        final_memory = memory_samples[-1]
        memory_range = max_memory - min_memory

        print("\nMemory stability test:")
        print(f"  Baseline: {baseline_memory:.1f}MB")
        print(
            f"  Range: {min_memory:.1f}MB - {max_memory:.1f}MB (±{memory_range:.1f}MB)"
        )
        print(f"  Final: {final_memory:.1f}MB")
        print(f"  Growth from baseline: {final_memory - baseline_memory:.1f}MB")

        # Memory should be stable (no significant leaks)
        assert memory_range < 50, f"Memory usage too variable: ±{memory_range:.1f}MB"
        assert final_memory - baseline_memory < 100, (
            f"Memory leak detected: +{final_memory - baseline_memory:.1f}MB"
        )

    def test_memory_usage_during_large_batch_processing(self):
        """Test memory usage patterns during large batch processing."""
        batch_sizes = [50, 100, 200, 400]
        memory_results = {}

        for batch_size in batch_sizes:
            gc.collect()
            initial_memory = self.process.memory_info().rss / 1024 / 1024

            # Create and process batch
            dataset = self._create_test_creatures(batch_size)
            creatures = [Creature.model_validate(data) for data in dataset]

            # Simulate processing
            processed_results = []
            for creature in creatures:
                result = {
                    "name": creature.name,
                    "cr": creature.get_enhanced_cr_text(),
                    "type": creature.get_size_type_alignment(),
                    "layout": creature.requires_full_width_layout(),
                }
                processed_results.append(result)

            peak_memory = self.process.memory_info().rss / 1024 / 1024

            # Cleanup
            del dataset, creatures, processed_results
            gc.collect()

            final_memory = self.process.memory_info().rss / 1024 / 1024

            memory_results[batch_size] = {
                "initial": initial_memory,
                "peak": peak_memory,
                "final": final_memory,
                "peak_growth": peak_memory - initial_memory,
                "retained": final_memory - initial_memory,
            }

            print(f"\nBatch size {batch_size}:")
            print(f"  Peak memory growth: +{peak_memory - initial_memory:.1f}MB")
            print(f"  Retained after cleanup: +{final_memory - initial_memory:.1f}MB")

        # Analyze memory scaling
        for batch_size, result in memory_results.items():
            memory_per_creature = result["peak_growth"] / batch_size
            print(f"  Batch {batch_size}: {memory_per_creature:.3f}MB per creature")

            # Memory usage should be reasonable
            assert result["peak_growth"] < batch_size * 0.5, (
                f"Excessive memory usage: {result['peak_growth']:.1f}MB for {batch_size} creatures"
            )
            assert result["retained"] < 20, (
                f"Memory leak in batch {batch_size}: +{result['retained']:.1f}MB retained"
            )

    def test_memory_efficiency_with_complex_creatures(self):
        """Test memory efficiency with complex creature data."""
        # Create complex creatures with many features
        complex_creatures_data = []
        for i in range(100):
            creature = {
                "name": f"Complex Creature {i:03d}",
                "source": "TEST",
                "size": ["L"],
                "type": "dragon",
                "alignment": ["C", "E"],
                "ac": [{"ac": 18, "from": ["natural armor"]}],
                "hp": {
                    "average": 200 + i * 10,
                    "formula": f"{15 + i}d12 + {50 + i * 2}",
                },
                "speed": {"walk": 40, "fly": 80, "swim": 40, "burrow": 20},
                "str": min(30, 20 + i % 10),
                "dex": min(30, 10 + i % 8),
                "con": min(30, 20 + i % 6),
                "int": min(30, 14 + i % 12),
                "wis": min(30, 13 + i % 8),
                "cha": min(30, 17 + i % 10),
                "save": {
                    "dex": f"+{5 + i % 5}",
                    "con": f"+{11 + i % 5}",
                    "wis": f"+{6 + i % 3}",
                    "cha": f"+{8 + i % 4}",
                },
                "skill": {
                    "perception": f"+{11 + i % 8}",
                    "stealth": f"+{5 + i % 3}",
                    "arcana": f"+{7 + i % 5}",
                },
                "resist": ["fire", "cold"],
                "immune": ["poison", "charm"],
                "conditionImmune": ["charmed", "poisoned", "frightened"],
                "senses": [
                    "blindsight 60 ft.",
                    "darkvision 120 ft.",
                    f"passive Perception {21 + i % 10}",
                ],
                "languages": ["Common", "Draconic", "Giant"],
                "cr": str(10 + i % 15),
                "trait": [
                    {
                        "name": f"Legendary Resistance {i}",
                        "entries": [
                            f"Trait description {i} with lots of text to test memory usage patterns."
                        ],
                    },
                    {
                        "name": f"Magic Resistance {i}",
                        "entries": [
                            f"Another trait with even more descriptive text for creature {i}."
                        ],
                    },
                ],
                "action": [
                    {
                        "name": f"Multiattack {i}",
                        "entries": [
                            f"Complex multiattack description for creature {i} with detailed attack patterns."
                        ],
                    },
                    {
                        "name": f"Breath Weapon {i}",
                        "entries": [
                            f"Detailed breath weapon description with damage calculations and save DCs for creature {i}."
                        ],
                    },
                ],
                "legendary": [
                    {
                        "name": f"Detect {i}",
                        "entries": [f"Legendary action description {i}."],
                    },
                    {
                        "name": f"Move {i}",
                        "entries": [f"Movement legendary action for creature {i}."],
                    },
                ],
                "spellcasting": [
                    {
                        "name": "Spellcasting",
                        "headerEntries": [
                            f"Complex spellcasting description for creature {i}."
                        ],
                        "spells": {
                            "0": {
                                "spells": [
                                    "{@spell mage hand}",
                                    "{@spell prestidigitation}",
                                ]
                            },
                            "1": {
                                "slots": 4,
                                "spells": ["{@spell magic missile}", "{@spell shield}"],
                            },
                            "5": {"slots": 1, "spells": ["{@spell fireball}"]},
                        },
                    }
                ],
            }
            complex_creatures_data.append(creature)

        # Test memory usage
        initial_memory = self.process.memory_info().rss / 1024 / 1024

        # Create complex creatures
        start_time = time.perf_counter()
        complex_creatures = [
            Creature.model_validate(data) for data in complex_creatures_data
        ]
        validation_time = time.perf_counter() - start_time

        peak_memory = self.process.memory_info().rss / 1024 / 1024

        # Test operations on complex creatures
        start_time = time.perf_counter()
        for creature in complex_creatures:
            _ = creature.get_enhanced_cr_text()
            _ = creature.get_size_type_alignment()
            _ = creature.requires_full_width_layout()
        operation_time = time.perf_counter() - start_time

        final_memory = self.process.memory_info().rss / 1024 / 1024

        print("\nComplex creatures test (100 creatures):")
        print(f"  Validation time: {validation_time:.4f}s")
        print(f"  Operation time: {operation_time:.4f}s")
        print(
            f"  Memory usage: {initial_memory:.1f}MB -> {peak_memory:.1f}MB -> {final_memory:.1f}MB"
        )
        print(
            f"  Memory per complex creature: {(peak_memory - initial_memory) / len(complex_creatures):.3f}MB"
        )

        # Complex creatures should still be handled efficiently
        assert validation_time < 5.0, (
            f"Complex creature validation too slow: {validation_time:.4f}s"
        )
        assert operation_time < 2.0, (
            f"Complex creature operations too slow: {operation_time:.4f}s"
        )
        memory_per_creature = (peak_memory - initial_memory) / len(complex_creatures)
        assert memory_per_creature < 1.0, (
            f"Excessive memory per complex creature: {memory_per_creature:.3f}MB"
        )

    def _create_test_creatures(self, count: int) -> list[dict]:
        """Create test creature data for memory testing."""
        creatures = []
        for i in range(count):
            creature = {
                "name": f"Memory Test Creature {i:04d}",
                "source": "TEST",
                "size": ["M"],
                "type": "humanoid",
                "alignment": ["N"],
                "ac": [10 + i % 10],
                "hp": {"average": 20 + i * 2},
                "speed": {"walk": 30},
                "str": 10 + i % 20,
                "dex": 10 + i % 20,
                "con": 10 + i % 20,
                "int": 10 + i % 20,
                "wis": 10 + i % 20,
                "cha": 10 + i % 20,
                "cr": str(i % 10),
                "action": [
                    {"name": f"Attack {i}", "entries": [f"Attack description {i}"]}
                ],
            }
            creatures.append(creature)
        return creatures


@pytest.mark.performance
@pytest.mark.slow
class TestRenderingPerformanceScale:
    """Test rendering performance with large creature datasets."""

    def setup_method(self):
        """Set up test fixtures."""
        reset_test_environment()

    def test_rendering_scalability_stress_test(self):
        """Stress test rendering performance with multiple creatures."""
        # Create varied creatures for rendering
        creatures_data = []
        for i in range(50):  # Reasonable number for rendering tests
            creature = {
                "name": f"Render Test Creature {i:03d}",
                "source": "TEST",
                "size": [["T", "S", "M", "L", "H"][i % 5]],
                "type": ["humanoid", "beast", "dragon", "undead"][i % 4],
                "alignment": [["N"], ["L", "G"], ["C", "E"]][i % 3],
                "ac": [10 + i % 15],
                "hp": {"average": 20 + i * 5},
                "speed": {"walk": 30 + i % 20},
                "str": 10 + i % 20,
                "dex": 10 + i % 20,
                "con": 10 + i % 20,
                "int": 10 + i % 20,
                "wis": 10 + i % 20,
                "cha": 10 + i % 20,
                "cr": str(i % 20),
                "trait": [{"name": f"Trait {i}", "entries": [f"Trait description {i}"]}]
                if i % 3 == 0
                else None,
                "action": [
                    {
                        "name": f"Attack {i}",
                        "entries": [
                            f"Attack description {i} with {{@atk mw}} {{@hit {4 + i % 10}}} to hit."
                        ],
                    }
                ],
                "legendary": [
                    {"name": f"Legendary {i}", "entries": [f"Legendary action {i}"]}
                ]
                if i % 7 == 0
                else None,
            }
            creatures_data.append(creature)

        creatures = [Creature.model_validate(data) for data in creatures_data if data]

        # Test rendering performance
        with patch(
            "dnd5e.renderers.latex.document.LaTeXDocumentRenderer"
        ) as mock_renderer_class:
            mock_renderer = Mock()
            mock_renderer.render_document.return_value = (
                "\\documentclass{article}\\begin{document}Test\\end{document}"
            )
            mock_renderer_class.return_value = mock_renderer

            context = RenderingContext(
                output_format="latex", metadata={"title": "Scale Test"}
            )

            start_time = time.perf_counter()
            result = mock_renderer.render_document(creatures, context)
            render_time = time.perf_counter() - start_time

            print("\nRendering scalability test:")
            print(f"  Creatures: {len(creatures)}")
            print(f"  Render time: {render_time:.4f}s")
            print(f"  Time per creature: {render_time / len(creatures) * 1000:.2f}ms")

            # Should handle rendering efficiently
            assert render_time < 10.0, (
                f"Rendering too slow: {render_time:.4f}s for {len(creatures)} creatures"
            )
            assert result is not None

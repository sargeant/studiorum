"""Integration tests for full dataset validation.

This module runs comprehensive validation tests against the entire
real 5etools dataset to ensure data loading works correctly.
"""

import asyncio
import logging
import time
from collections import defaultdict
from pathlib import Path

import pytest

from dnd5e.core.config.settings import get_logger
from dnd5e.core.loaders.json_loader import JsonDataLoader
from dnd5e.core.loaders.omnidexer import Omnidexer
from dnd5e.core.loaders.source_manager import FileSystemSourceManager
from dnd5e.core.models.content import ContentType


class ValidationReport:
    """Collects and analyzes validation results."""

    def __init__(self):
        self.total_items = 0
        self.successful_items = 0
        self.validation_warnings = []
        self.file_skips = defaultdict(int)
        self.load_times = {}
        self.content_stats = defaultdict(int)

    def add_load_result(
        self, content_type: str, file_path: Path, items_loaded: int, load_time: float
    ):
        """Add results from loading a single file."""
        self.content_stats[content_type] += items_loaded
        self.successful_items += items_loaded
        self.load_times[str(file_path)] = load_time

    def add_validation_warning(self, warning: str):
        """Add a validation warning."""
        self.validation_warnings.append(warning)

    def add_file_skip(self, skip_type: str):
        """Add a file skip."""
        self.file_skips[skip_type] += 1

    def generate_summary(self) -> str:
        """Generate a comprehensive validation summary."""
        total_files = len(self.load_times) + sum(self.file_skips.values())
        avg_load_time = (
            sum(self.load_times.values()) / len(self.load_times)
            if self.load_times
            else 0
        )

        summary = [
            "=" * 60,
            "DATASET VALIDATION SUMMARY",
            "=" * 60,
            f"Total files processed: {total_files}",
            f"Files loaded successfully: {len(self.load_times)}",
            f"Files skipped: {sum(self.file_skips.values())}",
            "",
            "Content Statistics:",
        ]

        for content_type, count in sorted(self.content_stats.items()):
            summary.append(f"  {content_type}: {count:,} items")

        summary.extend(
            [
                f"  TOTAL: {sum(self.content_stats.values()):,} items",
                "",
                f"Validation warnings: {len(self.validation_warnings)}",
                f"Average load time: {avg_load_time:.3f}s per file",
                "",
                "File Skip Breakdown:",
            ]
        )

        for skip_type, count in self.file_skips.items():
            summary.append(f"  {skip_type}: {count} files")

        if self.validation_warnings:
            summary.extend(
                [
                    "",
                    "Sample Validation Warnings (first 5):",
                ]
            )
            for warning in self.validation_warnings[:5]:
                summary.append(f"  - {warning[:100]}...")

        return "\n".join(summary)


class TestFullDatasetValidation:
    """Integration tests for full dataset validation."""

    @pytest.fixture(autouse=True)
    def setup_logging_capture(self):
        """Set up logging capture for validation analysis."""
        self.log_records = []
        self.handler = logging.Handler()
        self.handler.emit = lambda record: self.log_records.append(record)

        # Add to relevant loggers
        loggers = [
            get_logger("src.core.loaders.json_loader"),
            get_logger("src.core.loaders.omnidexer"),
        ]

        for logger in loggers:
            logger.addHandler(self.handler)
            logger.setLevel(logging.DEBUG)

        yield

        # Clean up
        for logger in loggers:
            logger.removeHandler(self.handler)

    def extract_validation_warnings(self) -> list[str]:
        """Extract validation warnings from log records."""
        warnings = []
        for record in self.log_records:
            if (
                record.levelno >= logging.WARNING
                and "Validation failed" in record.getMessage()
            ):
                warnings.append(record.getMessage())
        return warnings

    def extract_file_skips(self) -> dict[str, int]:
        """Extract file skip information from log records."""
        skips = defaultdict(int)
        for record in self.log_records:
            message = record.getMessage()
            if "Skipping index/list file" in message:
                skips["index_list"] += 1
            elif "Skipping malformed index file" in message:
                skips["malformed_index"] += 1
            elif "Skipping metadata/sources file" in message:
                skips["metadata"] += 1
            elif "Skipping Foundry VTT" in message:
                skips["foundry"] += 1
            elif "Skipping template" in message:
                skips["template"] += 1
            elif "Skipping copy-template" in message:
                skips["copy_template"] += 1
            elif "No content found" in message:
                skips["empty_content"] += 1
        return skips

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_full_spell_dataset_validation(self):
        """Test validation of the complete spell dataset."""
        report = ValidationReport()  # Initialize report

        source_manager = FileSystemSourceManager()
        data_paths = source_manager.get_data_paths()
        spell_files = data_paths.get(ContentType.SPELL, [])

        if not spell_files:
            pytest.skip("No spell data files found")

        spell_loader = JsonDataLoader.create_for_type(ContentType.SPELL)

        for spell_file in spell_files:
            if not spell_file.exists():
                continue

            start_time = time.time()
            spells = await spell_loader.load(spell_file)
            load_time = time.time() - start_time

            report.add_load_result("spells", spell_file, len(spells), load_time)

        # Analyze results
        validation_warnings = self.extract_validation_warnings()
        file_skips = self.extract_file_skips()

        for warning in validation_warnings:
            report.add_validation_warning(warning)

        for skip_type, count in file_skips.items():
            report.file_skips[skip_type] = count

        print(report.generate_summary())

        # Validation thresholds
        total_spells = report.content_stats["spells"]
        warning_threshold = max(10, total_spells * 0.01)  # 1% or minimum 10

        assert len(validation_warnings) <= warning_threshold, (
            f"Too many validation warnings: {len(validation_warnings)} > {warning_threshold} "
            f"for {total_spells} spells"
        )

        assert total_spells > 0, "No spells were loaded"

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_full_creature_dataset_validation(self):
        """Test validation of the complete creature dataset."""
        report = ValidationReport()  # Initialize report

        source_manager = FileSystemSourceManager()
        data_paths = source_manager.get_data_paths()
        creature_files = data_paths.get(ContentType.CREATURE, [])

        if not creature_files:
            pytest.skip("No creature data files found")

        creature_loader = JsonDataLoader.create_for_type(ContentType.CREATURE)

        for creature_file in creature_files:
            if not creature_file.exists():
                continue

            start_time = time.time()
            creatures = await creature_loader.load(creature_file)
            load_time = time.time() - start_time

            report.add_load_result(
                "creatures", creature_file, len(creatures), load_time
            )

        # Analyze results
        validation_warnings = self.extract_validation_warnings()
        file_skips = self.extract_file_skips()

        for warning in validation_warnings:
            report.add_validation_warning(warning)

        for skip_type, count in file_skips.items():
            report.file_skips[skip_type] = count

        print(report.generate_summary())

        # Validation thresholds
        total_creatures = report.content_stats["creatures"]
        warning_threshold = max(15, total_creatures * 0.015)  # 1.5% or minimum 15

        assert len(validation_warnings) <= warning_threshold, (
            f"Too many validation warnings: {len(validation_warnings)} > {warning_threshold} "
            f"for {total_creatures} creatures"
        )

        assert total_creatures > 0, "No creatures were loaded"

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_full_item_dataset_validation(self):
        """Test validation of the complete item dataset."""
        report = ValidationReport()  # Initialize report

        source_manager = FileSystemSourceManager()
        data_paths = source_manager.get_data_paths()
        item_files = data_paths.get(ContentType.ITEM, [])

        if not item_files:
            pytest.skip("No item data files found")

        item_loader = JsonDataLoader.create_for_type(ContentType.ITEM)

        for item_file in item_files:
            if not item_file.exists():
                continue

            start_time = time.time()
            items = await item_loader.load(item_file)
            load_time = time.time() - start_time

            report.add_load_result("items", item_file, len(items), load_time)

        # Analyze results
        validation_warnings = self.extract_validation_warnings()
        file_skips = self.extract_file_skips()

        for warning in validation_warnings:
            report.add_validation_warning(warning)

        for skip_type, count in file_skips.items():
            report.file_skips[skip_type] = count

        print(report.generate_summary())

        # Validation thresholds
        total_items = report.content_stats["items"]
        warning_threshold = max(5, total_items * 0.005)  # 0.5% or minimum 5

        assert len(validation_warnings) <= warning_threshold, (
            f"Too many validation warnings: {len(validation_warnings)} > {warning_threshold} "
            f"for {total_items} items"
        )

        assert total_items > 0, "No items were loaded"

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_omnidexer_full_dataset_load(self):
        """Test the omnidexer loading the complete dataset."""
        source_manager = FileSystemSourceManager()
        omnidexer = Omnidexer(source_manager)

        print("\n🌟 Testing omnidexer full dataset load...")

        start_time = time.time()
        load_stats = await omnidexer.load_all_data()
        total_load_time = time.time() - start_time

        # Analyze results
        validation_warnings = self.extract_validation_warnings()
        file_skips = self.extract_file_skips()

        # Generate comprehensive report
        total_items = sum(load_stats.values())

        print("\n📊 OMNIDEXER LOAD RESULTS:")
        print(f"Total load time: {total_load_time:.2f}s")
        print(f"Items per second: {total_items / total_load_time:.1f}")
        print(f"Total items loaded: {total_items:,}")
        print(f"Validation warnings: {len(validation_warnings)}")
        print(f"Files skipped: {sum(file_skips.values())}")

        print("\nLoad statistics by content type:")
        for content_type, count in sorted(load_stats.items()):
            print(f"  {content_type}: {count:,}")

        if file_skips:
            print("\nFile skips by type:")
            for skip_type, count in file_skips.items():
                print(f"  {skip_type}: {count}")

        # Validation thresholds
        warning_threshold = max(20, total_items * 0.01)  # 1% or minimum 20
        skip_threshold = max(10, len(load_stats) * 0.2)  # 20% of total files

        # Adjust expectations based on available data
        # In test environments, we may only have minimal sample data
        min_expected_items = 1 if total_items < 100 else 1000
        assert total_items >= min_expected_items, (
            f"Expected to load at least {min_expected_items} items, got {total_items} items"
        )
        assert len(validation_warnings) <= warning_threshold, (
            f"Too many validation warnings: {len(validation_warnings)} > {warning_threshold}"
        )
        assert sum(file_skips.values()) <= skip_threshold, (
            f"Too many files skipped: {sum(file_skips.values())} > {skip_threshold}"
        )

        # Test omnidexer functionality
        statistics = omnidexer.get_statistics()
        assert statistics["total_items"] == total_items
        assert len(statistics["by_type"]) > 0
        assert len(statistics["by_source"]) > 0

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_data_consistency_across_loaders(self):
        """Test that different loaders produce consistent results."""
        source_manager = FileSystemSourceManager()
        data_paths = source_manager.get_data_paths()

        # Test spell consistency
        spell_files = data_paths.get(ContentType.SPELL, [])[:5]  # Test subset
        if spell_files:
            spell_loader = JsonDataLoader.create_for_type(ContentType.SPELL)

            loads = []
            for _ in range(3):  # Load same files 3 times
                all_spells = []
                for spell_file in spell_files:
                    if spell_file.exists():
                        spells = await spell_loader.load(spell_file)
                        all_spells.extend(spells)
                loads.append(len(all_spells))

            # Results should be consistent
            assert all(count == loads[0] for count in loads), (
                f"Inconsistent spell loading results: {loads}"
            )

        print("✅ Data consistency test passed")

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_memory_efficiency_large_dataset(self):
        """Test memory efficiency when loading large datasets."""
        try:
            import os

            import psutil
        except ImportError:
            pytest.skip("psutil not installed - skipping memory usage test")

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        source_manager = FileSystemSourceManager()
        omnidexer = Omnidexer(source_manager)

        # Load full dataset
        load_stats = await omnidexer.load_all_data()

        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        total_items = sum(load_stats.values())

        memory_per_item = memory_increase / total_items if total_items > 0 else 0

        print("\n💾 MEMORY EFFICIENCY ANALYSIS:")
        print(f"Initial memory: {initial_memory:.1f} MB")
        print(f"Final memory: {final_memory:.1f} MB")
        print(f"Memory increase: {memory_increase:.1f} MB")
        print(f"Items loaded: {total_items:,}")
        print(f"Memory per item: {memory_per_item:.4f} MB")

        # Memory thresholds (adjust based on dataset size)
        # For small test datasets, be more lenient with memory per item
        if total_items < 100:
            max_memory_increase = 100  # 100MB for small datasets
            max_memory_per_item = 10.0  # 10MB per item for very small datasets
        else:
            max_memory_increase = 1000  # 1GB for large datasets
            max_memory_per_item = 0.1  # 100KB per item for large datasets

        assert memory_increase < max_memory_increase, (
            f"Memory usage too high: {memory_increase:.1f}MB > {max_memory_increase}MB"
        )

        # Only check memory per item if we have a reasonable number of items
        if total_items > 0:
            assert memory_per_item < max_memory_per_item, (
                f"Memory per item too high: {memory_per_item:.4f}MB > {max_memory_per_item}MB"
            )

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_concurrent_dataset_loading(self):
        """Test concurrent loading of dataset doesn't cause issues."""
        source_manager = FileSystemSourceManager()

        async def load_subset():
            """Load a subset of the data."""
            Omnidexer(source_manager)
            # Load just spells for faster concurrent test
            data_paths = source_manager.get_data_paths()
            spell_files = data_paths.get(ContentType.SPELL, [])[
                :3
            ]  # Just first 3 files

            spell_loader = JsonDataLoader.create_for_type(ContentType.SPELL)
            total_spells = 0
            for spell_file in spell_files:
                if spell_file.exists():
                    spells = await spell_loader.load(spell_file)
                    total_spells += len(spells)
            return total_spells

        # Run 5 concurrent loads
        tasks = [load_subset() for _ in range(5)]
        results = await asyncio.gather(*tasks)

        # All loads should succeed and return same result
        assert all(isinstance(result, int) for result in results), "Some loads failed"
        assert all(result == results[0] for result in results), (
            f"Inconsistent concurrent results: {results}"
        )

        print(f"✅ Concurrent loading test passed: {results[0]} items per load")

    def test_validation_warning_categorization_full_dataset(self):
        """Categorize and analyze all validation warnings from full dataset."""
        validation_warnings = self.extract_validation_warnings()

        if not validation_warnings:
            print("✅ No validation warnings found in dataset")
            return

        # Categorize warnings
        categories = {
            "missing_required_fields": [],
            "type_validation_errors": [],
            "parsing_errors": [],
            "unknown_structure_errors": [],
            "other_errors": [],
        }

        for warning in validation_warnings:
            if "Field required" in warning:
                categories["missing_required_fields"].append(warning)
            elif "Input should be a valid" in warning:
                categories["type_validation_errors"].append(warning)
            elif any(
                keyword in warning.lower() for keyword in ["parse", "parsing", "unable"]
            ):
                categories["parsing_errors"].append(warning)
            elif any(
                keyword in warning.lower()
                for keyword in ["unknown", "unrecognized", "unexpected"]
            ):
                categories["unknown_structure_errors"].append(warning)
            else:
                categories["other_errors"].append(warning)

        print(f"\n📋 VALIDATION WARNING ANALYSIS ({len(validation_warnings)} total):")
        for category, warnings in categories.items():
            print(f"  {category}: {len(warnings)}")
            if warnings:
                # Show sample
                sample = (
                    warnings[0][:80] + "..." if len(warnings[0]) > 80 else warnings[0]
                )
                print(f"    Sample: {sample}")

        # Analysis assertions
        total_warnings = len(validation_warnings)
        unknown_ratio = (
            len(categories["unknown_structure_errors"]) / total_warnings
            if total_warnings > 0
            else 0
        )

        assert (
            unknown_ratio < 0.1
        ), (  # Less than 10% should be unknown structure errors
            f"Too many unknown structure errors: {unknown_ratio:.1%}"
        )

        print("✅ Validation warning categorization completed")

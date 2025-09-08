"""Comprehensive stress tests for data validation.

This module contains tests to validate that the data loading system
can handle all available data without warnings or unknown data structures.
"""

import asyncio
from collections.abc import Generator
from typing import Any

import pytest
from logfire.testing import CaptureLogfire

from studiorum.cli.services import get_cli_template_service
from studiorum.core.loaders.json_loader import JsonDataLoader  # type: ignore
from studiorum.core.loaders.omnidexer import Omnidexer  # type: ignore
from studiorum.core.loaders.source_manager import (
    FileSystemSourceManager,  # type: ignore
)
from studiorum.core.logging import get_logger  # type: ignore
from studiorum.core.models.content import ContentType  # type: ignore
from studiorum.core.references.content_tracker import ContentTracker


class TestDataValidationStress:
    """Stress tests for data validation across all available content."""

    @pytest.fixture(autouse=True)
    def setup_log_capture(self, capfire: CaptureLogfire) -> Generator[None, None, None]:
        """Set up log capture for each test."""
        self.capfire = capfire
        yield

    def get_validation_warnings(self) -> list[str]:
        """Extract validation warning messages."""
        warnings: list[str] = []
        for span in self.capfire.exporter.exported_spans:
            if hasattr(span, "attributes") and span.attributes:
                msg = span.attributes.get("logfire.msg", "")
                if "Validation failed" in msg:
                    warnings.append(msg)
        return warnings

    def get_unknown_data_warnings(self) -> list[str]:
        """Extract warnings about unknown or unhandled data."""
        unknown_warnings: list[str] = []
        for span in self.capfire.exporter.exported_spans:
            if hasattr(span, "attributes") and span.attributes:
                message = span.attributes.get("logfire.msg", "")
                # Skip "already indexed" messages as these are normal duplicate handling
                if "already indexed" in message.lower():
                    continue
                if any(
                    keyword in message.lower()
                    for keyword in [
                        "unknown",
                        "unrecognized",
                        "unexpected",
                        "not supported",
                        "skipping",
                        "failed to parse",
                        "unable to handle",
                    ]
                ):
                    unknown_warnings.append(message)
        return unknown_warnings

    def test_load_all_spells_no_validation_errors(self) -> None:
        """Test loading all spell data without validation errors."""
        source_manager: Any = FileSystemSourceManager()
        spell_loader = JsonDataLoader.create_for_type(ContentType("spell"))
        data_paths = source_manager.get_data_paths()
        spell_files = data_paths.get(ContentType("spell"), [])

        if not spell_files:
            pytest.skip("No spell data files found")

        total_spells = 0

        for spell_file in spell_files:
            if not spell_file.exists():
                continue

            spells = spell_loader.load(spell_file)
            total_spells += len(spells)

        # Check for validation warnings
        validation_warnings = self.get_validation_warnings()

        # Allow a small percentage of validation warnings for edge cases
        warning_threshold: Any = max(1, total_spells * 0.02)  # 2% threshold

        assert len(validation_warnings) <= warning_threshold, (
            f"Too many validation warnings ({len(validation_warnings)} > {warning_threshold}) "
            f"for {total_spells} spells. Warnings: {validation_warnings[:5]}"
        )

        print(
            f"✅ Successfully loaded {total_spells} spells with {len(validation_warnings)} warnings"
        )

    def test_load_all_creatures_no_validation_errors(self) -> None:
        """Test loading all creature data without validation errors."""
        source_manager: Any = FileSystemSourceManager()
        creature_loader = JsonDataLoader.create_for_type(ContentType("creature"))
        data_paths = source_manager.get_data_paths()
        creature_files = data_paths.get(ContentType("creature"), [])

        if not creature_files:
            pytest.skip("No creature data files found")

        total_creatures = 0

        for creature_file in creature_files:
            if not creature_file.exists():
                continue

            creatures = creature_loader.load(creature_file)
            total_creatures += len(creatures)

        # Check for validation warnings
        validation_warnings = self.get_validation_warnings()

        # Allow a small percentage of validation warnings for edge cases
        warning_threshold: Any = max(1, total_creatures * 0.02)  # 2% threshold

        assert len(validation_warnings) <= warning_threshold, (
            f"Too many validation warnings ({len(validation_warnings)} > {warning_threshold}) "
            f"for {total_creatures} creatures. Warnings: {validation_warnings[:5]}"
        )

        print(
            f"✅ Successfully loaded {total_creatures} creatures with {len(validation_warnings)} warnings"
        )

    def test_load_all_items_no_validation_errors(self) -> None:
        """Test loading all item data without validation errors."""
        source_manager: Any = FileSystemSourceManager()
        item_loader = JsonDataLoader.create_for_type(ContentType("item"))
        data_paths = source_manager.get_data_paths()
        item_files = data_paths.get(ContentType("item"), [])

        if not item_files:
            pytest.skip("No item data files found")

        total_items = 0

        for item_file in item_files:
            if not item_file.exists():
                continue

            items = item_loader.load(item_file)
            total_items += len(items)

        # Check for validation warnings
        validation_warnings = self.get_validation_warnings()

        # Allow a small percentage of validation warnings for edge cases
        warning_threshold: Any = max(1, total_items * 0.02)  # 2% threshold

        assert len(validation_warnings) <= warning_threshold, (
            f"Too many validation warnings ({len(validation_warnings)} > {warning_threshold}) "
            f"for {total_items} items. Warnings: {validation_warnings[:5]}"
        )

        print(
            f"✅ Successfully loaded {total_items} items with {len(validation_warnings)} warnings"
        )

    def test_omnidexer_full_data_load(self) -> None:
        """Test loading all available data through the omnidexer."""
        source_manager: Any = FileSystemSourceManager()
        omnidexer: Any = Omnidexer(source_manager)

        # Load all data
        load_stats = omnidexer.load_all_data()

        # Verify data was loaded
        assert load_stats, "No data was loaded"

        total_items: Any = sum(load_stats.values())
        assert total_items > 0, "No items were loaded"

        # Check for validation warnings
        validation_warnings = self.get_validation_warnings()
        unknown_warnings = self.get_unknown_data_warnings()

        # Calculate acceptable warning thresholds
        validation_threshold: Any = max(5, total_items * 0.01)  # 1% threshold, min 5
        unknown_threshold: Any = max(2, total_items * 0.005)  # 0.5% threshold, min 2

        assert len(validation_warnings) <= validation_threshold, (
            f"Too many validation warnings ({len(validation_warnings)} > {validation_threshold}) "
            f"for {total_items} total items. Sample warnings: {validation_warnings[:3]}"
        )

        assert len(unknown_warnings) <= unknown_threshold, (
            f"Too many unknown data warnings ({len(unknown_warnings)} > {unknown_threshold}) "
            f"for {total_items} total items. Sample warnings: {unknown_warnings[:3]}"
        )

        print(f"✅ Successfully loaded {total_items} total items via omnidexer")
        print(f"   Validation warnings: {len(validation_warnings)}")
        print(f"   Unknown data warnings: {len(unknown_warnings)}")
        print(f"   Load stats: {load_stats}")

    def test_complex_data_structures_validation(self) -> None:
        """Test that complex data structures are properly handled."""
        complex_spell_data = {
            "name": "Complex Test Spell",
            "source": {"abbreviation": "TEST", "name": "Test Source"},
            "level": 1,
            "school": "A",
            "time": [{"number": 1, "unit": "action"}],
            "range": {"type": "point", "distance": {"type": "feet", "amount": 30}},
            "components": {"v": True, "s": True},
            "duration": [{"type": "instant"}],
            # Complex entries structure
            "entries": [
                "Simple text entry",
                {
                    "type": "entries",
                    "name": "Special Effect",
                    "entries": [
                        "Nested text",
                        {"type": "list", "items": ["List item 1", "List item 2"]},
                    ],
                },
            ],
            # Complex higher level entries
            "entriesHigherLevel": [
                {
                    "type": "entries",
                    "name": "At Higher Levels",
                    "entries": ["When cast at higher level..."],
                }
            ],
        }

        complex_creature_data = {
            "name": "Complex Test Creature",
            "source": {"abbreviation": "TEST", "name": "Test Source"},
            "size": ["M"],
            "type": {
                "type": "humanoid",
                "tags": [{"tag": "elf", "prefix": "High"}, "wizard"],
            },
            "alignment": [{"alignment": ["L", "N"]}, "G"],
            "ac": [{"special": "15 + Dex modifier"}],
            "hp": {"special": "50 + (5 × level)"},
            "speed": {"walk": 30},
            "str": 10,
            "dex": 14,
            "con": 12,
            "int": 16,
            "wis": 13,
            "cha": 15,
            "skill": {
                "arcana": "+5",
                "other": [{"oneOf": {"history": "+5", "investigation": "+5"}}],
            },
            "passive": "12 + prof bonus",
            "cr": "1",
            # Complex abilities
            "trait": [
                {
                    "name": "Test Trait",
                    "entries": [
                        "Simple description",
                        {
                            "type": "list",
                            "items": [
                                "Complex list item",
                                {"text": "Nested text item"},
                            ],
                        },
                    ],
                }
            ],
        }

        # Test spell validation
        from studiorum.core.models.spells import Spell  # type: ignore

        spell = Spell.model_validate(complex_spell_data)
        assert spell.name == "Complex Test Spell"

        # Use template service for description extraction
        template_service = get_cli_template_service()
        content_tracker = ContentTracker()
        bound = template_service.bind_context(content_tracker)
        description_text = bound.render_entry(spell.entries)
        assert description_text  # Should extract text from complex structure

        # Use template service for higher level text extraction
        if spell.higher_level:
            higher_level_text = bound.render_entry(spell.higher_level)
            assert higher_level_text  # Should extract text from complex structure

        # Test creature validation
        from studiorum.core.models.creatures import Creature  # type: ignore

        creature = Creature.model_validate(complex_creature_data)
        assert creature.name == "Complex Test Creature"
        assert creature.get_size_type_alignment()  # Should handle complex alignment

        print("✅ Complex data structures validated successfully")

    def test_file_format_detection_accuracy(self) -> None:
        """Test that file format detection correctly identifies different file types."""
        source_manager: Any = FileSystemSourceManager()
        spell_loader = JsonDataLoader.create_for_type(ContentType("spell"))

        # Get all data files
        data_paths = source_manager.get_data_paths()
        all_files: list[Any] = []
        for file_list in data_paths.values():
            all_files.extend(file_list)

        if not all_files:
            pytest.skip("No data files found")

        # Test a sample of files
        sample_files = all_files[:20]  # Test first 20 files

        format_detection_stats = {
            "foundry_detected": 0,
            "template_detected": 0,
            "fluff_detected": 0,
            "copy_template_detected": 0,
            "processed_normally": 0,
        }

        for file_path in sample_files:
            if not file_path.exists():
                continue

            # Use spell loader as representative loader
            spell_loader.load(file_path)

            # Check log messages for detection from Logfire spans
            log_messages = [
                span.attributes.get("logfire.msg", "")
                for span in self.capfire.exporter.exported_spans
                if span.attributes.get("logfire.msg")
            ]

            if any("Skipping Foundry VTT" in msg for msg in log_messages):
                format_detection_stats["foundry_detected"] += 1
            elif any("Skipping template" in msg for msg in log_messages):
                format_detection_stats["template_detected"] += 1
            elif any("fluff" in msg.lower() for msg in log_messages):
                format_detection_stats["fluff_detected"] += 1
            elif any("copy-template" in msg for msg in log_messages):
                format_detection_stats["copy_template_detected"] += 1
            else:
                format_detection_stats["processed_normally"] += 1

            # Note: With Logfire, spans accumulate across iterations
            # We could track initial counts if needed for isolation

        print(f"✅ File format detection stats: {format_detection_stats}")

        # At least some files should be processed normally
        assert format_detection_stats["processed_normally"] > 0, (
            "No files were processed normally - format detection may be too aggressive"
        )

    def test_edge_case_data_structures(self) -> None:
        """Test validation of edge case data structures."""
        from studiorum.core.models.creatures import Creature  # type: ignore
        from studiorum.core.models.items import Item  # type: ignore
        from studiorum.core.models.spells import Spell  # type: ignore

        # Test spell with minimal data
        minimal_spell = {
            "name": "Minimal Spell",
            "source": "TEST",
            "level": 0,
            "school": "T",
            "time": [{"number": 1, "unit": "action"}],
            "range": {"type": "self"},
            "components": {"v": True},
            "duration": [{"type": "instant"}],
            "entries": ["Minimal description"],
        }

        spell = Spell.model_validate(minimal_spell)
        assert spell.name == "Minimal Spell"

        # Test creature with special formats
        special_creature = {
            "name": "Special Creature",
            "source": "TEST",
            "size": ["L"],
            "type": {"choose": ["celestial", "fiend"]},
            "alignment": ["N"],
            "ac": [{"special": "Variable AC"}],
            "hp": {"special": "Variable HP"},
            "speed": {"walk": 30},
            "str": 10,
            "dex": 10,
            "con": 10,
            "int": 10,
            "wis": 10,
            "cha": 10,
            "cr": "Variable",
        }

        creature = Creature.model_validate(special_creature)
        assert creature.name == "Special Creature"
        assert "celestial or fiend" in str(creature.type)

        # Test item with complex entries
        complex_item = {
            "name": "Complex Item",
            "source": "TEST",
            "type": "G",
            "entries": [
                {
                    "type": "list",
                    "style": "list-hang-notitle",
                    "items": [
                        "Complex item property",
                        "Special property with additional text",
                    ],
                }
            ],
        }

        item = Item.model_validate(complex_item)
        assert item.name == "Complex Item"
        # Use modern RecursiveEntryProcessor for item description extraction
        from studiorum.cli.utils import get_omnidexer
        from studiorum.core.references.content_tracker import ContentTracker
        from studiorum.latex_engine.core.entry_processor import RecursiveEntryProcessor
        from studiorum.renderers.core.interfaces import RenderingContext

        entry_processor = RecursiveEntryProcessor(use_dnd_template=True)
        content_tracker = ContentTracker()
        rendering_context = RenderingContext(
            output_format="latex",
            omnidexer=get_omnidexer(),
            content_tracker=content_tracker,
        )
        processed_entries = entry_processor.process_entries(
            item.entries, rendering_context
        )
        assert processed_entries  # Should extract text from complex structure

        print("✅ Edge case data structures validated successfully")

    @pytest.mark.slow
    def test_memory_usage_during_full_load(self) -> None:
        """Test memory usage doesn't grow excessively during full data load."""
        try:
            import os

            import psutil  # type: ignore
        except ImportError:
            pytest.skip("psutil not installed - skipping memory usage test")

        # Skip when running with pytest-xdist to avoid resource contention
        if os.getenv("PYTEST_XDIST_WORKER"):
            pytest.skip("Memory monitoring tests incompatible with parallel execution")

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        source_manager: Any = FileSystemSourceManager()
        omnidexer: Any = Omnidexer(source_manager)

        # Load all data
        load_stats = omnidexer.load_all_data()

        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory

        total_items: Any = sum(load_stats.values())

        # Memory shouldn't increase by more than 500MB for reasonable datasets
        # Adjust this threshold based on your dataset size
        memory_threshold = 500  # MB

        assert memory_increase < memory_threshold, (
            f"Memory usage increased by {memory_increase:.1f}MB (>{memory_threshold}MB) "
            f"when loading {total_items} items"
        )

        print(
            f"✅ Memory usage: {initial_memory:.1f}MB → {final_memory:.1f}MB "
            f"(+{memory_increase:.1f}MB) for {total_items} items"
        )

    @pytest.mark.slow
    def test_concurrent_data_loading(self) -> None:
        """Test that concurrent data loading works without issues."""
        source_manager: Any = FileSystemSourceManager()

        # Create multiple omnidexers to test concurrent loading
        def load_data() -> Any:
            omnidexer: Any = Omnidexer(source_manager)
            return omnidexer.load_all_data()

        # Run 3 concurrent loads using ThreadPoolExecutor
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(load_data) for _ in range(3)]
            results = [
                future.result() for future in concurrent.futures.as_completed(futures)
            ]

        # All loads should succeed and return similar results
        assert len(results) == 3
        assert all(results), "Some concurrent loads failed"

        # Results should be consistent (within small variance for non-deterministic loading)
        first_total: Any = sum(results[0].values())
        for i, result in enumerate(results[1:], 1):
            total: Any = sum(result.values())
            variance: Any = (
                abs(total - first_total) / first_total if first_total > 0 else 0
            )
            assert variance < 0.1, (  # 10% variance allowed
                f"Concurrent load {i} had {variance:.1%} variance from first load "
                f"({total} vs {first_total} items)"
            )

        print(
            f"✅ Concurrent loading successful: {[sum(r.values()) for r in results]} items"
        )

    def test_validation_error_categorization(self) -> None:
        """Test that validation errors are properly categorized."""
        validation_warnings = self.get_validation_warnings()

        if not validation_warnings:
            pytest.skip("No validation warnings to categorize")

        # Categorize validation errors
        categories: dict[str, list[Any]] = {
            "missing_fields": [],
            "type_errors": [],
            "format_errors": [],
            "unknown_errors": [],
        }

        for warning in validation_warnings:
            if "Field required" in warning:
                categories["missing_fields"].append(warning)
            elif "Input should be a valid" in warning:
                categories["type_errors"].append(warning)
            elif "unable to parse" in warning.lower():
                categories["format_errors"].append(warning)
            else:
                categories["unknown_errors"].append(warning)

        # Report categorization
        print("📊 Validation Error Categories:")
        for category, errors in categories.items():
            print(f"  {category}: {len(errors)} errors")
            if errors:
                print(f"    Sample: {errors[0][:100]}...")

        # Most errors should be categorizable
        unknown_ratio: Any = len(categories["unknown_errors"]) / len(
            validation_warnings
        )
        assert unknown_ratio < 0.2, (  # Less than 20% should be unknown
            f"Too many unknown validation errors ({unknown_ratio:.1%})"
        )

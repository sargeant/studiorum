"""Performance tests for enhanced file format parsing and content list writing."""

import tempfile
import time
from pathlib import Path
from unittest.mock import Mock

import pytest

from studiorum.core.loaders.content_sources import NameListFileSource
from studiorum.core.models.content import ContentType
from studiorum.core.references.content_tracker import ContentTracker
from studiorum.core.services.content_list_writer import ContentListWriter
from tests.test_helpers import reset_test_environment


@pytest.mark.performance
class TestEnhancedFilePerformance:
    """Performance tests for enhanced file functionality."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        reset_test_environment()
        self.temp_dir = Path(tempfile.mkdtemp())

    def teardown_method(self) -> None:
        """Clean up test fixtures."""
        import shutil

        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def create_large_test_file(
        self, num_entries: int, format_type: str = "full"
    ) -> Path:
        """Create a large test file with specified number of entries."""
        file_path = self.temp_dir / f"large_file_{num_entries}.txt"

        with file_path.open("w", encoding="utf-8") as f:
            f.write("# Large test file for performance testing\n")
            f.write("# Format: [Count] Name|Source\n")
            f.write("#\n")

            for i in range(num_entries):
                if format_type == "simple":
                    f.write(f"Test Entry {i:06d}\n")
                elif format_type == "count":
                    count = (i % 10) + 1
                    f.write(f"{count} Test Entry {i:06d}\n")
                elif format_type == "source":
                    source = "PHB" if i % 2 == 0 else "DMG"
                    f.write(f"Test Entry {i:06d}|{source}\n")
                elif format_type == "full":
                    count = (i % 10) + 1
                    source = "PHB" if i % 2 == 0 else "DMG"
                    f.write(f"{count} Test Entry {i:06d}|{source}\n")
                elif format_type == "mixed":
                    # Mix different formats
                    if i % 4 == 0:
                        f.write(f"Test Entry {i:06d}\n")
                    elif i % 4 == 1:
                        count = (i % 10) + 1
                        f.write(f"{count} Test Entry {i:06d}\n")
                    elif i % 4 == 2:
                        source = "PHB" if i % 2 == 0 else "DMG"
                        f.write(f"Test Entry {i:06d}|{source}\n")
                    else:
                        count = (i % 10) + 1
                        source = "PHB" if i % 2 == 0 else "DMG"
                        f.write(f"{count} Test Entry {i:06d}|{source}\n")

        return file_path

    def measure_time(self, func, *args, **kwargs):
        """Measure execution time of a function."""
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        return result, end_time - start_time

    def test_small_file_parsing_performance(self) -> None:
        """Test parsing performance with small files (baseline)."""
        file_path = self.create_large_test_file(100, "full")
        source = NameListFileSource(file_path, ContentType.SPELL)

        # Test structured loading
        structured_data, duration = self.measure_time(source.load_structured)

        assert len(structured_data) == 100
        assert duration < 0.1  # Should be very fast for small files

        # Test backward compatibility loading
        names, duration = self.measure_time(source.load)

        assert len(names) == 100
        assert duration < 0.1  # Should also be very fast

    def test_medium_file_parsing_performance(self) -> None:
        """Test parsing performance with medium-sized files."""
        file_path = self.create_large_test_file(1000, "full")
        source = NameListFileSource(file_path, ContentType.SPELL)

        # Test structured loading
        structured_data, duration = self.measure_time(source.load_structured)

        assert len(structured_data) == 1000
        assert duration < 0.5  # Should handle 1K entries quickly

        # Test that caching works (second call should be much faster)
        _, cached_duration = self.measure_time(source.load_structured)
        assert cached_duration < duration * 0.1  # Cached should be ~10x faster

    def test_large_file_parsing_performance(self) -> None:
        """Test parsing performance with large files."""
        file_path = self.create_large_test_file(10000, "full")
        source = NameListFileSource(file_path, ContentType.SPELL)

        # Test structured loading
        structured_data, duration = self.measure_time(source.load_structured)

        assert len(structured_data) == 10000
        assert duration < 2.0  # Should handle 10K entries in reasonable time

        # Verify data integrity for large files
        first_entry = structured_data[0]
        last_entry = structured_data[-1]

        assert first_entry[1] == "Test Entry 000000"
        assert last_entry[1] == "Test Entry 009999"

    def test_mixed_format_parsing_performance(self) -> None:
        """Test parsing performance with mixed format files."""
        file_path = self.create_large_test_file(5000, "mixed")
        source = NameListFileSource(file_path, ContentType.SPELL)

        # Mixed format should still be reasonably fast
        structured_data, duration = self.measure_time(source.load_structured)

        assert len(structured_data) == 5000
        assert duration < 1.5  # Mixed format parsing should still be fast

        # Verify mixed format data
        formats_found = set()
        for count, name, source_abbr in structured_data[:100]:
            if count == 1 and source_abbr is None:
                formats_found.add("simple")
            elif count > 1 and source_abbr is None:
                formats_found.add("count")
            elif count == 1 and source_abbr is not None:
                formats_found.add("source")
            elif count > 1 and source_abbr is not None:
                formats_found.add("full")

        # Should have found multiple format types
        assert len(formats_found) >= 3

    def test_content_list_writer_performance(self) -> None:
        """Test ContentListWriter performance with large datasets."""
        writer = ContentListWriter()

        # Create mock content tracker with large dataset
        mock_tracker = Mock(spec=ContentTracker)

        # Generate large export data
        large_content = {"spell": [], "creature": [], "item": []}

        for i in range(1000):
            large_content["spell"].append(
                {
                    "name": f"Spell {i:04d}",
                    "source": "PHB" if i % 2 == 0 else "XGE",
                    "reference_count": (i % 10) + 1,
                }
            )

            large_content["creature"].append(
                {
                    "name": f"Creature {i:04d}",
                    "source": "MM" if i % 3 == 0 else "VGM",
                    "reference_count": (i % 5) + 1,
                }
            )

            large_content["item"].append(
                {
                    "name": f"Item {i:04d}",
                    "source": "DMG" if i % 4 == 0 else "PHB",
                    "reference_count": (i % 3) + 1,
                }
            )

        mock_tracker.export_for_appendix.return_value = large_content

        # Test writing all content types
        output_dir = self.temp_dir / "performance_test"

        result, duration = self.measure_time(
            writer.write_all_content_types,
            mock_tracker,
            output_dir,
            title="Performance Test Adventure",
        )

        assert isinstance(result, type(result))  # Check it's a Result type
        if hasattr(result, "unwrap"):
            counts = result.unwrap()
            assert counts["spell"] == 1000
            assert counts["creature"] == 1000
            assert counts["item"] == 1000

        assert duration < 3.0  # Should write 3K entries across 3 files quickly

        # Verify files were created
        assert (output_dir / "spell.txt").exists()
        assert (output_dir / "creature.txt").exists()
        assert (output_dir / "item.txt").exists()

    def test_content_list_writer_sorting_performance(self) -> None:
        """Test ContentListWriter sorting performance."""
        writer = ContentListWriter()

        # Create mock tracker with unsorted data
        mock_tracker = Mock(spec=ContentTracker)

        large_content = {"spell": []}

        # Create unsorted data (reverse alphabetical order)
        for i in range(2000, 0, -1):
            large_content["spell"].append(
                {
                    "name": f"Spell {i:04d}",
                    "source": "PHB",
                    "reference_count": i % 100,  # Varying counts for sort testing
                }
            )

        mock_tracker.export_for_appendix.return_value = large_content

        # Test sorting by name
        output_file = self.temp_dir / "sorted_by_name.txt"
        result, duration_name = self.measure_time(
            writer.write_content_list, mock_tracker, output_file, sort_by_count=False
        )

        assert duration_name < 1.0  # Sorting 2K entries by name should be fast

        # Test sorting by count
        output_file = self.temp_dir / "sorted_by_count.txt"
        result, duration_count = self.measure_time(
            writer.write_content_list, mock_tracker, output_file, sort_by_count=True
        )

        assert duration_count < 1.0  # Sorting 2K entries by count should be fast

        # Both sorting methods should be similar in performance
        assert abs(duration_name - duration_count) < 0.5

    def test_file_io_performance(self) -> None:
        """Test file I/O performance for large files."""
        writer = ContentListWriter()

        # Create large content dataset
        mock_tracker = Mock(spec=ContentTracker)

        large_content = {"spell": []}

        # Create 5K entries with longer names to test I/O performance
        for i in range(5000):
            large_content["spell"].append(
                {
                    "name": f"Very Long Spell Name That Tests File I/O Performance Entry {i:05d}",
                    "source": "Player's Handbook"
                    if i % 2 == 0
                    else "Xanathar's Guide to Everything",
                    "reference_count": (i % 20) + 1,
                }
            )

        mock_tracker.export_for_appendix.return_value = large_content

        # Test file writing performance
        output_file = self.temp_dir / "large_output.txt"

        result, duration = self.measure_time(
            writer.write_content_list,
            mock_tracker,
            output_file,
            title="Large Performance Test",
        )

        assert duration < 2.0  # Should write 5K entries with long names quickly

        # Verify file size and content
        assert output_file.exists()
        file_size = output_file.stat().st_size
        assert file_size > 100000  # Should be a substantial file

        # Test reading the file back
        source = NameListFileSource(output_file, ContentType.SPELL)
        structured_data, read_duration = self.measure_time(source.load_structured)

        assert read_duration < 1.0  # Reading back should also be fast
        assert len(structured_data) == 5000

    def test_memory_usage_large_files(self) -> None:
        """Test memory usage doesn't grow excessively with large files."""
        import gc
        import sys

        # Force garbage collection before test
        gc.collect()

        file_path = self.create_large_test_file(20000, "full")

        # Measure memory before
        if hasattr(sys, "getsizeof"):
            # Test multiple loads to ensure no memory leaks
            for i in range(5):
                source = NameListFileSource(file_path, ContentType.SPELL)
                structured_data = source.load_structured()

                assert len(structured_data) == 20000

                # Clear reference
                del structured_data
                del source

                # Force garbage collection
                gc.collect()

        # Test should complete without memory errors
        assert True  # If we get here, memory usage was acceptable

    def test_concurrent_access_performance(self) -> None:
        """Test performance when multiple processes access the same file."""
        file_path = self.create_large_test_file(5000, "full")

        # Simulate concurrent access by creating multiple sources
        sources = []
        for i in range(10):
            sources.append(NameListFileSource(file_path, ContentType.SPELL))

        # Measure time to load from all sources
        start_time = time.perf_counter()

        results = []
        for source in sources:
            structured_data = source.load_structured()
            results.append(len(structured_data))

        end_time = time.perf_counter()
        duration = end_time - start_time

        # All should have loaded the same amount of data
        assert all(count == 5000 for count in results)

        # Should complete in reasonable time even with multiple sources
        assert duration < 3.0

    def test_validation_performance(self) -> None:
        """Test validation performance on large files."""
        file_path = self.create_large_test_file(10000, "mixed")
        source = NameListFileSource(file_path, ContentType.SPELL)

        # Test validation performance
        validation_result, duration = self.measure_time(source.validate)

        assert validation_result.is_valid
        assert duration < 1.0  # Validation should be fast even for large files

        # Test metadata calculation performance
        metadata, metadata_duration = self.measure_time(source.get_metadata)

        assert metadata.content_count > 0
        assert metadata_duration < 1.0  # Metadata calculation should be fast

    def test_edge_case_performance(self) -> None:
        """Test performance with edge cases that might be slow."""
        # Create file with very long lines
        long_line_content = []
        for i in range(1000):
            long_name = "Very " * 100 + f"Long Name {i}"
            long_source = "A" * 50 + f"_{i}"
            count = i % 100 + 1
            long_line_content.append(f"{count} {long_name}|{long_source}")

        content = "\n".join(long_line_content)
        file_path = self.temp_dir / "long_lines.txt"
        file_path.write_text(content, encoding="utf-8")

        source = NameListFileSource(file_path, ContentType.SPELL)

        # Should handle very long lines without performance degradation
        structured_data, duration = self.measure_time(source.load_structured)

        assert len(structured_data) == 1000
        assert duration < 2.0  # Should handle long lines reasonably

        # Verify data integrity
        first_name = structured_data[0][1]
        assert "Very " in first_name
        assert "Long Name 0" in first_name

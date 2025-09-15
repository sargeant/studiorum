"""
Integration tests for book conversion regression testing.

This module tests that book conversion still works correctly after the
loader architecture changes, ensuring no regressions in functionality.
"""

import os
import subprocess
import tempfile
from pathlib import Path

import pytest

from studiorum.core.loaders.omnidexer import Omnidexer
from studiorum.core.loaders.unified_source_manager import UnifiedSourceManager
from studiorum.core.resolvers.content_resolver import ContentResolver
from tests.test_helpers import reset_test_environment


def load_all_data_sync(omnidexer):
    """Synchronous wrapper for omnidexer.load_all_data() for testing."""
    import asyncio

    return omnidexer.load_all_data()


def resolve_book_sync(resolver, book_id):
    """Synchronous wrapper for resolver.resolve_book() for testing."""
    import asyncio

    return resolver.resolve_book(book_id)


@pytest.mark.integration
class TestBookConversion:
    """Test book conversion functionality for regression."""

    def setup_method(self) -> None:
        """Reset global state for complete isolation using service container."""
        reset_test_environment()

        # Note: reset_test_environment() now handles both container systems
        # via reset_all_containers() for proper parallel execution isolation

    def _get_test_env(self) -> dict[str, str]:
        """Get environment with test configuration override."""

        env = os.environ.copy()
        env["STUDIORUM_CONFIG_FILE"] = "test-config.yaml"
        return env

    def test_book_conversion_produces_content(self):
        """Test that book conversion produces LaTeX with actual content."""
        # Use a temporary output file
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "TEST.tex"

            # Run the conversion command with test config
            result = subprocess.run(
                [
                    "uv",
                    "run",
                    "studiorum",
                    "convert",
                    "book",
                    "test",
                    "--output",
                    str(output_file),
                ],
                capture_output=True,
                text=True,
                cwd=Path.cwd(),
                env=self._get_test_env(),
            )

            # Check that the command succeeded
            if result.returncode != 0:
                if (
                    "not found" in result.stderr.lower()
                    or "not found" in result.stdout.lower()
                ):
                    pytest.skip("Test book not available in data sources")
                elif (
                    "DND-5e-LaTeX-Template is not available" in result.stderr
                    or "DND-5e-LaTeX-Template is not available" in result.stdout
                ):
                    pytest.skip(
                        "DND LaTeX template not available - cannot test book conversion"
                    )
                else:
                    raise AssertionError(
                        f"Test book conversion failed: {result.stderr}"
                    )

            # Check that the output file was created
            assert output_file.exists(), (
                f"Test book output file not created: {output_file}"
            )

            # Read the output file
            content = output_file.read_text()

            # Verify the file has substantial content (test book)
            assert len(content) > 2000, "Generated test book LaTeX file is too short"

            # Verify it contains expected test book content
            assert "Test Sourcebook" in content, "Missing test book title"
            assert "5e" in content, "Missing 5e branding"

            # Verify it has content structure - chapters should be present
            assert "\\chapter{" in content, "Missing chapter structure"

            # Count lines to ensure substantial content
            line_count = len(content.splitlines())
            assert line_count > 50, (
                f"Too few lines in test book: {line_count}, expected >50"
            )

    def test_multiple_books_work(self):
        """Test that multiple different books can be converted."""
        books_to_test = ["test"]  # Test book sample

        for book_id in books_to_test:
            with tempfile.TemporaryDirectory() as temp_dir:
                output_file = Path(temp_dir) / f"{book_id}.tex"

                # Try to convert the book with test config
                result = subprocess.run(
                    [
                        "uv",
                        "run",
                        "studiorum",
                        "convert",
                        "book",
                        book_id,
                        "--output",
                        str(output_file),
                    ],
                    capture_output=True,
                    text=True,
                    cwd=Path.cwd(),
                    env=self._get_test_env(),
                )

                # Some books might not be available in test data
                if result.returncode != 0:
                    if (
                        "not found" in result.stderr.lower()
                        or "not found" in result.stdout.lower()
                    ):
                        pytest.skip(f"Book {book_id} not available in test data")
                    elif (
                        "DND-5e-LaTeX-Template is not available" in result.stderr
                        or "DND-5e-LaTeX-Template is not available" in result.stdout
                    ):
                        pytest.skip(
                            f"DND LaTeX template not available - cannot test {book_id} conversion"
                        )
                    else:
                        pytest.fail(f"Conversion of {book_id} failed: {result.stderr}")

                # If successful, verify basic output
                if output_file.exists():
                    content = output_file.read_text()
                    assert len(content) > 5000, (
                        f"Book {book_id} produced minimal content"
                    )

    @pytest.mark.slow
    def test_book_conversion_performance(self):
        """Test that book conversion completes in reasonable time."""
        import time

        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "TEST.tex"
            start_time = time.time()

            result = subprocess.run(
                [
                    "uv",
                    "run",
                    "studiorum",
                    "convert",
                    "book",
                    "test",
                    "--output",
                    str(output_file),
                ],
                capture_output=True,
                text=True,
                cwd=Path.cwd(),
                env=self._get_test_env(),
            )

            end_time = time.time()
            conversion_time = end_time - start_time

            if result.returncode != 0:
                if (
                    "not found" in result.stderr.lower()
                    or "not found" in result.stdout.lower()
                ):
                    pytest.skip("Test content not available in data sources")
                elif (
                    "DND-5e-LaTeX-Template is not available" in result.stderr
                    or "DND-5e-LaTeX-Template is not available" in result.stdout
                ):
                    pytest.skip(
                        "DND LaTeX template not available - cannot test book conversion"
                    )
                else:
                    raise AssertionError(
                        f"Test book conversion failed: {result.stderr}"
                    )

            # Test book conversion should complete within 1 minute
            assert conversion_time < 60, (
                f"Test book conversion took too long: {conversion_time:.2f}s"
            )

    def test_book_omnidexer_loading(self, test_data_omnidexer):
        """Verify omnidexer loads books correctly."""
        omnidexer = test_data_omnidexer

        # Get book count
        books = omnidexer.get_all_by_type("book")

        # Should have books loaded
        assert len(books) > 0, f"Expected books to be loaded, got {len(books)}"

        # Verify test book exists and has proper structure
        test_books = [b for b in books if b.source.abbreviation == "TEST"]
        assert len(test_books) >= 1, (
            f"Expected at least 1 TEST book, got {len(test_books)}"
        )

        # Find the metadata version (should have proper name)
        test_metadata = None
        for book in test_books:
            if "Test Sourcebook" in book.name:
                test_metadata = book
                break

        assert test_metadata is not None, "Could not find test book with proper name"
        assert str(test_metadata.source.abbreviation) == "TEST", (
            f"Unexpected test source: {test_metadata.source}"
        )

    def test_book_content_resolver_enrichment(self, test_data_omnidexer):
        """Test that ContentResolver properly enriches books with content."""
        omnidexer = test_data_omnidexer

        resolver = ContentResolver(omnidexer)

        # Resolve test book
        resolution_result = resolve_book_sync(resolver, "test")

        assert resolution_result is not None, "Could not get resolution result"
        assert resolution_result.is_success, "Resolution should be successful"

        result = resolution_result.content
        assert result is not None, "Could not resolve test book"

        # Should have substantial content after enrichment
        assert result.has_content(), "Test book should have content after enrichment"
        assert not result.is_metadata_only(), (
            "Test book should not be metadata-only after enrichment"
        )

        # Verify content structure
        assert len(result.contents) > 0, "Test book should have contents sections"

        # At least some sections should have entries (content)
        sections_with_content = [
            section
            for section in result.contents
            if hasattr(section, "entries") and section.entries
        ]
        assert len(sections_with_content) > 0, (
            "Test book should have sections with content (found empty sections)"
        )

    def test_book_content_loading_caching(self, test_data_omnidexer):
        """Test that book content loading uses caching effectively."""
        omnidexer = test_data_omnidexer

        resolver = ContentResolver(omnidexer)

        # Resolve the same book twice
        resolution_result1 = resolve_book_sync(resolver, "test")
        resolution_result2 = resolve_book_sync(resolver, "test")

        # Both should succeed
        assert resolution_result1 is not None, "First test book resolution failed"
        assert resolution_result2 is not None, "Second test book resolution failed"
        assert resolution_result1.is_success, "First resolution not successful"
        assert resolution_result2.is_success, "Second resolution not successful"

        result1 = resolution_result1.content
        result2 = resolution_result2.content

        # Both should have content
        assert result1.has_content(), "First test book result missing content"
        assert result2.has_content(), "Second test book result missing content"

        # Check cache statistics if available and caching is enabled
        content_merger = resolver.content_merger
        if hasattr(content_merger, "get_cache_stats"):
            stats = content_merger.get_cache_stats()
            # Only check for cache performance if caching is enabled
            if stats.get("cache_enabled", False):
                # Accept either cache hits or evidence of caching (cached items)
                assert stats.get("hits", 0) > 0 or stats.get("cached_items", 0) > 0, (
                    f"Expected cache activity from repeated book resolution. Stats: {stats}"
                )

    def test_book_latex_output_quality(self):
        """Test that generated book LaTeX follows expected patterns and quality."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "TEST.tex"

            result = subprocess.run(
                [
                    "uv",
                    "run",
                    "studiorum",
                    "convert",
                    "book",
                    "test",
                    "--output",
                    str(output_file),
                ],
                capture_output=True,
                text=True,
                cwd=Path.cwd(),
                env=self._get_test_env(),
            )

            if result.returncode != 0:
                if (
                    "not found" in result.stderr.lower()
                    or "not found" in result.stdout.lower()
                ):
                    pytest.skip("Test content not available in data sources")
                elif (
                    "DND-5e-LaTeX-Template is not available" in result.stderr
                    or "DND-5e-LaTeX-Template is not available" in result.stdout
                ):
                    pytest.skip(
                        "DND LaTeX template not available - cannot test book conversion"
                    )
                else:
                    raise AssertionError(
                        f"Test book conversion failed: {result.stderr}"
                    )

            content = output_file.read_text()

            # Check LaTeX document structure
            assert "\\documentclass" in content, "Missing document class"
            assert "\\begin{document}" in content, "Missing document begin"
            assert "\\end{document}" in content, "Missing document end"

            # Check for proper book structure
            assert "\\chapter{" in content, "Missing chapter structure"
            assert "\\section{" in content, "Missing section structure"

            # Check for book-specific content patterns
            assert "Test Sourcebook" in content, "Missing test book title"

            # Check for proper LaTeX escaping (focus on content, not LaTeX syntax)
            lines_with_problematic_chars = []
            for i, line in enumerate(
                content.splitlines()[:1000]
            ):  # Check first 1000 lines for performance
                # Skip LaTeX commands, comments, and common LaTeX environments
                if (
                    line.strip().startswith("\\")
                    or line.strip().startswith("%")
                    or line.strip().startswith("    {\\")  # LaTeX formatting blocks
                    or "\\textit{" in line
                    or "\\textbf{" in line  # Text formatting
                    or "\\chapter{" in line
                    or "\\section{" in line  # Sectioning
                    or "pdfsubject=" in line
                    or "pdfkeywords=" in line
                ):  # PDF metadata
                    continue

                # Look for potentially problematic unescaped characters in content
                problematic_patterns = [
                    ("&", "\\&"),  # & should be \& in regular text
                    ("$", "\\$"),  # $ should be \$ in regular text (outside math mode)
                    ("#", "\\#"),  # # should be \# in regular text
                ]

                for char, escape in problematic_patterns:
                    if char in line and escape not in line:
                        # Additional check: skip if it's in a clear LaTeX context
                        if not any(
                            ctx in line for ctx in ["{", "}", "\\", "begin{", "end{"]
                        ):
                            lines_with_problematic_chars.append(
                                f"Line {i + 1}: {line[:100]}"
                            )
                            break  # Only report once per line

            # Allow some unescaped characters but check that we don't have excessive issues
            # Note: Some legitimate content like "5e" may not be escaped - this is a known issue
            assert len(lines_with_problematic_chars) < 50, (
                f"Too many potentially problematic unescaped characters: {lines_with_problematic_chars[:5]}"
            )

    def test_no_hardcoded_phb_paths(self):
        """Test that test book works without hardcoded file paths."""
        # This test verifies that the hardcoded special case was properly removed
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "TEST.tex"

            # Run test book conversion
            result = subprocess.run(
                [
                    "uv",
                    "run",
                    "studiorum",
                    "convert",
                    "book",
                    "test",
                    "--output",
                    str(output_file),
                ],
                capture_output=True,
                text=True,
                cwd=Path.cwd(),
                env=self._get_test_env(),
            )

            # Should work without hardcoded paths
            if result.returncode != 0:
                if (
                    "not found" in result.stderr.lower()
                    or "not found" in result.stdout.lower()
                ):
                    pytest.skip("Test content not available in data sources")
                elif (
                    "DND-5e-LaTeX-Template is not available" in result.stderr
                    or "DND-5e-LaTeX-Template is not available" in result.stdout
                ):
                    pytest.skip(
                        "DND LaTeX template not available - cannot test book conversion"
                    )
                else:
                    raise AssertionError(
                        f"Test book conversion failed without hardcoded paths: {result.stderr}"
                    )

            # Should produce substantial content
            content = output_file.read_text()
            assert len(content) > 2000, (
                "Test book should produce substantial content without hardcoding"
            )

            # Verify it's the correct content
            assert "Test Sourcebook" in content, (
                "Test book should have correct title without hardcoding"
            )

    def test_book_error_handling(self):
        """Test that book conversion handles errors gracefully."""
        # Test with a non-existent book
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "nonexistent.tex"

            result = subprocess.run(
                [
                    "uv",
                    "run",
                    "studiorum",
                    "convert",
                    "book",
                    "nonexistent",
                    "--output",
                    str(output_file),
                ],
                capture_output=True,
                text=True,
                cwd=Path.cwd(),
                env=self._get_test_env(),
            )

            # Should fail gracefully with appropriate error message
            assert result.returncode != 0, "Should fail for non-existent book"
            assert (
                "not found" in result.stdout.lower()
                or "could not resolve" in result.stdout.lower()
                or "not found" in result.stderr.lower()
                or "could not resolve" in result.stderr.lower()
                or "did you mean?" in result.stdout.lower()
                or "see all available content" in result.stdout.lower()
            ), (
                f"Unexpected error message - stdout: {result.stdout}, stderr: {result.stderr}"
            )

    @pytest.mark.slow
    @pytest.mark.xdist_incompatible
    def test_book_memory_usage_reasonable(self):
        """Test that book conversion doesn't use excessive memory."""
        import psutil

        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "TEST.tex"

            result = subprocess.run(
                [
                    "uv",
                    "run",
                    "studiorum",
                    "convert",
                    "book",
                    "test",
                    "--output",
                    str(output_file),
                ],
                capture_output=True,
                text=True,
                cwd=Path.cwd(),
                env=self._get_test_env(),
            )

            if result.returncode != 0:
                if (
                    "not found" in result.stderr.lower()
                    or "not found" in result.stdout.lower()
                ):
                    pytest.skip("Test content not available in data sources")
                elif (
                    "DND-5e-LaTeX-Template is not available" in result.stderr
                    or "DND-5e-LaTeX-Template is not available" in result.stdout
                ):
                    pytest.skip(
                        "DND LaTeX template not available - cannot test book conversion"
                    )
                else:
                    raise AssertionError(
                        f"Test book conversion failed: {result.stderr}"
                    )

        # Check memory usage after conversion
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory

        # Memory increase should be reasonable (less than 500MB for test book)
        assert memory_increase < 500, (
            f"Excessive memory usage for test book: {memory_increase:.2f} MB increase"
        )

    def test_book_vs_adventure_consistency(self, test_data_omnidexer):
        """Test that books and adventures follow the same architectural patterns."""
        # This test ensures both content types work through the same dual-file architecture
        omnidexer = test_data_omnidexer

        def check_content_type(content_type, item_id, expected_name_substring):
            resolver = ContentResolver(omnidexer)

            # Get all items of this type
            all_items = omnidexer.get_all_by_type(content_type)
            assert len(all_items) > 0, f"Should have {content_type}s loaded"

            # Resolve specific item
            if content_type == "book":
                resolution_result = resolver.resolve_book(item_id)
            else:
                resolution_result = resolver.resolve_adventure(item_id)

            assert resolution_result is not None, (
                f"Should be able to get resolution result for {content_type} {item_id}"
            )
            assert resolution_result.is_success, (
                f"Resolution should be successful for {content_type} {item_id}"
            )

            result = resolution_result.content
            assert result is not None, (
                f"Should be able to resolve {content_type} {item_id}"
            )
            assert expected_name_substring in result.name, (
                f"Should have correct name for {content_type} {item_id}"
            )

            return result

        # Test both books and adventures
        book_result = check_content_type("book", "test", "Test Sourcebook")
        adventure_result = check_content_type("adventure", "test", "Test Adventure")

        # Both should have content after resolution
        assert book_result.has_content(), "Book should have content after resolution"
        assert adventure_result.has_content(), (
            "Adventure should have content after resolution"
        )

        # Both should have similar API structure
        assert hasattr(book_result, "contents"), "Book should have contents structure"
        assert hasattr(adventure_result, "contents"), (
            "Adventure should have contents structure"
        )

        # Both should support the same debugging methods
        assert hasattr(book_result, "is_metadata_only"), (
            "Book should have is_metadata_only method"
        )
        assert hasattr(adventure_result, "is_metadata_only"), (
            "Adventure should have is_metadata_only method"
        )

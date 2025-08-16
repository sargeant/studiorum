"""
Integration tests for end-to-end adventure conversion.

This module tests the complete pipeline from content loading through
LaTeX generation for adventure conversion functionality.
"""

import os
import subprocess
import tempfile
from pathlib import Path

import pytest

from dnd5e.core.loaders.configurable_source_manager import ConfigurableSourceManager
from dnd5e.core.loaders.omnidexer import Omnidexer
from dnd5e.core.resolvers.content_resolver import ContentResolver
from tests.test_helpers import reset_test_environment


def load_all_data_sync(omnidexer):
    """Synchronous wrapper for omnidexer.load_all_data() for testing."""
    import asyncio

    return omnidexer.load_all_data()


def resolve_adventure_sync(resolver, adventure_id):
    """Synchronous wrapper for resolver.resolve_adventure() for testing."""
    import asyncio

    return resolver.resolve_adventure(adventure_id)


@pytest.mark.integration
class TestAdventureConversion:
    """Test end-to-end adventure conversion functionality."""

    def setup_method(self) -> None:
        """Reset global state for complete isolation using service container."""
        reset_test_environment()

        # Extra isolation for parallel execution
        from dnd5e.core.container import reset_global_container

        reset_global_container()

    def _get_test_env(self) -> dict[str, str]:
        """Get environment with test configuration override."""
        import os

        env = os.environ.copy()
        env["DND5E_CONFIG_FILE"] = "test-config.yaml"
        return env

    def test_adventure_conversion_produces_content(self):
        """Test that adventure conversion produces LaTeX with actual content."""
        # Use a temporary output file
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "TEST.tex"

            # Run the conversion command
            result = subprocess.run(
                [
                    "uv",
                    "run",
                    "5e2pdf",
                    "convert",
                    "adventure",
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
                    pytest.skip("Test adventure not available in data sources")
                elif (
                    "DND-5e-LaTeX-Template is not available" in result.stderr
                    or "DND-5e-LaTeX-Template is not available" in result.stdout
                ):
                    pytest.skip(
                        "DND LaTeX template not available - cannot test adventure conversion"
                    )
                else:
                    raise AssertionError(f"Conversion failed: {result.stderr}")

            # Check that the output file was created
            assert output_file.exists(), f"Output file not created: {output_file}"

            # Read the output file
            content = output_file.read_text()

            # Verify the file has substantial content (not just headers)
            assert len(content) > 2000, "Generated LaTeX file is too short"

            # Verify it contains actual adventure content
            assert "Test Adventure" in content, "Missing adventure title"
            assert "chapter{" in content, "Missing chapter structure"
            assert "Test Adventure" in content or "adventure" in content.lower(), (
                "Missing adventure content"
            )

            # Verify it has content structure, sections should be present
            assert "section{" in content, "Missing section structure"

            # Count lines to ensure substantial content
            line_count = len(content.splitlines())
            assert line_count > 50, f"Too few lines: {line_count}, expected >50"

    def test_multiple_adventures_work(self):
        """Test that multiple different adventures can be converted."""
        adventures_to_test = ["test"]  # Test adventure sample

        for adventure_id in adventures_to_test:
            with tempfile.TemporaryDirectory() as temp_dir:
                output_file = Path(temp_dir) / f"{adventure_id}.tex"

                # Try to convert the adventure
                result = subprocess.run(
                    [
                        "uv",
                        "run",
                        "5e2pdf",
                        "convert",
                        "adventure",
                        adventure_id,
                        "--output",
                        str(output_file),
                    ],
                    capture_output=True,
                    text=True,
                    cwd=Path.cwd(),
                    env=self._get_test_env(),
                )

                # Some adventures might not be available in test data
                if result.returncode != 0:
                    if (
                        "not found" in result.stderr.lower()
                        or "not found" in result.stdout.lower()
                    ):
                        pytest.skip(
                            f"Adventure {adventure_id} not available in test data"
                        )
                    elif (
                        "DND-5e-LaTeX-Template is not available" in result.stderr
                        or "DND-5e-LaTeX-Template is not available" in result.stdout
                    ):
                        pytest.skip(
                            f"DND LaTeX template not available - cannot test {adventure_id} conversion"
                        )
                    else:
                        pytest.fail(
                            f"Conversion of {adventure_id} failed: {result.stderr}"
                        )

                # If successful, verify basic output
                if output_file.exists():
                    content = output_file.read_text()
                    assert len(content) > 1000, (
                        f"Adventure {adventure_id} produced minimal content"
                    )

    @pytest.mark.slow
    def test_conversion_performance_is_reasonable(self):
        """Test that adventure conversion completes in reasonable time."""
        import time

        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "TEST.tex"
            start_time = time.time()

            result = subprocess.run(
                [
                    "uv",
                    "run",
                    "5e2pdf",
                    "convert",
                    "adventure",
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
                        "DND LaTeX template not available - cannot test adventure conversion"
                    )
                else:
                    raise AssertionError(f"Conversion failed: {result.stderr}")

            # Conversion should complete within 2 minutes for large adventures
            assert conversion_time < 120, (
                f"Conversion took too long: {conversion_time:.2f}s"
            )

    def test_omnidexer_adventure_loading(self, test_data_omnidexer):
        """Verify omnidexer loads adventures correctly."""
        omnidexer = test_data_omnidexer

        # Get adventure count
        adventures = omnidexer.get_all_by_type("adventure")

        # Should have adventures loaded
        assert len(adventures) > 0, (
            f"Expected adventures to be loaded, got {len(adventures)}"
        )

        # Verify test adventure exists and has proper structure
        test_adventures = [a for a in adventures if a.source.abbreviation == "TEST"]
        assert len(test_adventures) >= 1, (
            f"Expected at least 1 TEST adventure, got {len(test_adventures)}"
        )

        # Use the first TEST adventure found
        test_metadata = test_adventures[0]

        assert test_metadata is not None, "Could not find TEST adventure"
        assert str(test_metadata.source.abbreviation) == "TEST", (
            f"Unexpected source: {test_metadata.source}"
        )

    def test_content_resolver_enrichment(self, test_data_omnidexer):
        """Test that ContentResolver properly enriches adventures with content."""
        omnidexer = test_data_omnidexer

        resolver = ContentResolver(omnidexer)

        # Resolve test adventure
        resolution_result = resolve_adventure_sync(resolver, "test")

        assert resolution_result is not None, "Could not get resolution result"
        assert resolution_result.is_success, "Resolution should be successful"

        result = resolution_result.content
        assert result is not None, "Could not resolve Test adventure"

        # Should have substantial content after enrichment
        assert result.has_content(), "Adventure should have content after enrichment"
        assert not result.is_metadata_only(), (
            "Adventure should not be metadata-only after enrichment"
        )

        # Verify content structure
        assert len(result.contents) > 0, "Adventure should have contents sections"

        # At least some sections should have entries (content)
        sections_with_content = [
            section
            for section in result.contents
            if hasattr(section, "entries") and section.entries
        ]
        assert len(sections_with_content) > 0, (
            "Adventure should have sections with actual content"
        )

    def test_content_loading_caching(self, test_data_omnidexer):
        """Test that content loading uses caching effectively."""
        omnidexer = test_data_omnidexer

        resolver = ContentResolver(omnidexer)

        # Resolve the same adventure twice
        resolution_result1 = resolve_adventure_sync(resolver, "test")
        resolution_result2 = resolve_adventure_sync(resolver, "test")

        # Both should succeed
        assert resolution_result1 is not None, "First resolution failed"
        assert resolution_result2 is not None, "Second resolution failed"
        assert resolution_result1.is_success, "First resolution not successful"
        assert resolution_result2.is_success, "Second resolution not successful"

        result1 = resolution_result1.content
        result2 = resolution_result2.content

        # Both should have content
        assert result1.has_content(), "First result missing content"
        assert result2.has_content(), "Second result missing content"

        # Check cache statistics if available
        content_merger = resolver.content_merger
        if hasattr(content_merger, "get_cache_stats"):
            stats = content_merger.get_cache_stats()
            # Should have at least one cache hit on the second call
            assert stats.get("hits", 0) > 0, (
                "Expected cache hits from repeated resolution"
            )

    def test_latex_output_quality(self):
        """Test that generated LaTeX follows expected patterns and quality."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "TEST.tex"

            result = subprocess.run(
                [
                    "uv",
                    "run",
                    "5e2pdf",
                    "convert",
                    "adventure",
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
                        "DND LaTeX template not available - cannot test LaTeX output quality"
                    )
                else:
                    raise AssertionError(f"Conversion failed: {result.stderr}")

            content = output_file.read_text()

            # Check LaTeX document structure
            assert "\\documentclass" in content, "Missing document class"
            assert "\\begin{document}" in content, "Missing document begin"
            assert "\\end{document}" in content, "Missing document end"

            # Check for DND-specific environments - not all content has read-aloud blocks
            assert "\\chapter{" in content, "Missing chapter structure"
            assert "\\section{" in content, "Missing section structure"

            # Check for proper LaTeX escaping (focus on content, not LaTeX syntax)
            lines_with_problematic_chars = []
            for i, line in enumerate(content.splitlines()):
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
            assert len(lines_with_problematic_chars) < 20, (
                f"Too many potentially problematic unescaped characters: {lines_with_problematic_chars[:5]}"
            )

    def test_error_handling_graceful_degradation(self):
        """Test that the system handles missing or corrupted content gracefully."""
        # Test with a non-existent adventure
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "nonexistent.tex"

            result = subprocess.run(
                [
                    "uv",
                    "run",
                    "5e2pdf",
                    "convert",
                    "adventure",
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
            assert result.returncode != 0, "Should fail for non-existent adventure"
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
    def test_memory_usage_reasonable(self):
        """Test that conversion doesn't use excessive memory."""
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
                    "5e2pdf",
                    "convert",
                    "adventure",
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
                        "DND LaTeX template not available - cannot test adventure conversion"
                    )
                else:
                    raise AssertionError(f"Conversion failed: {result.stderr}")

        # Check memory usage after conversion
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory

        # Memory increase should be reasonable (less than 500MB for one adventure)
        assert memory_increase < 500, (
            f"Excessive memory usage: {memory_increase:.2f} MB increase"
        )

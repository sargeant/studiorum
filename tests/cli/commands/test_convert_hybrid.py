"""Tests for hybrid parameter detection in convert commands."""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from studiorum.cli.commands.convert import (
    _handle_resolution_result,
    resolve_content_or_file,
)
from studiorum.core.models.adventures import Adventure
from studiorum.core.models.content import ContentType, Source
from studiorum.core.resolvers.content_resolver import (
    ContentResolutionResult,
    ResolutionStatus,
)


@pytest.mark.cli
class TestHybridParameterDetection:
    """Test hybrid parameter detection functionality."""

    def test_resolve_content_or_file_with_existing_file(self):
        """Test that existing files are detected and loaded."""
        # Create a temporary file with adventure data
        adventure_data = {
            "adventure": [
                {
                    "name": "Test Adventure",
                    "source": {"abbreviation": "TEST", "name": "Test Source"},
                    "id": "test",
                    "metadata": {},
                    "published": None,
                    "author": None,
                    "cover": None,
                    "contents": [],
                }
            ]
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(adventure_data, f)
            file_path = f.name

        try:
            # Should detect as file and load content
            content_items, source_desc = resolve_content_or_file(
                file_path, ContentType.ADVENTURE
            )

            assert len(content_items) == 1
            assert content_items[0].name == "Test Adventure"
            assert "file:" in source_desc
            assert file_path in source_desc

        finally:
            Path(file_path).unlink()  # Clean up

    @patch("studiorum.cli.commands.convert.shared.get_omnidexer")
    def test_resolve_content_or_file_with_abbreviation(self, mock_get_omnidexer):
        """Test that non-file strings are treated as abbreviations."""
        # Create a proper Adventure instance instead of Mock
        mock_adventure = Adventure(
            name="Curse of Strahd",
            id="cos",  # Add ID to prevent loading issues
            source=Source(abbreviation="CoS", name="Curse of Strahd"),
        )

        # Mock omnidexer with comprehensive mocking for enrichment
        mock_omnidexer = Mock()
        # Mock all methods that might be called during enrichment
        mock_omnidexer.get_all_by_type.return_value = []  # Return empty list for enrichment calls
        mock_omnidexer.find.return_value = None  # No cross-references found
        mock_get_omnidexer.return_value = mock_omnidexer

        # Mock successful resolution
        with patch(
            "studiorum.cli.commands.convert.shared.ContentResolver"
        ) as mock_resolver_class:
            mock_resolver = Mock()
            mock_resolver_class.return_value = mock_resolver

            # Mock successful adventure resolution
            mock_result = ContentResolutionResult(
                status=ResolutionStatus.EXACT_MATCH, content=mock_adventure, query="cos"
            )
            # Mock sync resolver method
            mock_resolver.resolve_adventure = Mock(return_value=mock_result)

            content_items, source_desc = resolve_content_or_file(
                "cos", ContentType.ADVENTURE
            )

            assert len(content_items) == 1
            assert content_items[0] == mock_adventure
            assert "abbreviation:" in source_desc
            assert "cos" in source_desc
            mock_resolver.resolve_adventure.assert_called_once_with("cos")

    def test_load_from_file_adventure(self):
        """Test loading adventure from file."""
        adventure_data = {
            "adventure": [
                {
                    "name": "Test Adventure",
                    "source": {"abbreviation": "TEST", "name": "Test Source"},
                    "id": "test",
                    "metadata": {},
                    "published": None,
                    "author": None,
                    "cover": None,
                    "contents": [],
                }
            ]
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(adventure_data, f)
            file_path = Path(f.name)

        try:
            content_items, source_desc = resolve_content_or_file(
                str(file_path), ContentType.ADVENTURE
            )

            assert len(content_items) == 1
            assert content_items[0].name == "Test Adventure"
            assert "file:" in source_desc

        finally:
            file_path.unlink()

    def test_load_from_file_book(self):
        """Test loading book from file."""
        book_data = {
            "data": [
                {
                    "type": "section",
                    "name": "Chapter 1",
                    "entries": ["This is chapter 1 content."],
                }
            ]
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(book_data, f)
            file_path = Path(f.name)

        try:
            content_items, source_desc = resolve_content_or_file(
                str(file_path), ContentType.BOOK
            )

            assert len(content_items) == 1
            assert "Book:" in content_items[0].name
            assert "file:" in source_desc

        finally:
            file_path.unlink()

    def test_handle_resolution_result_success(self):
        """Test handling successful resolution result."""
        mock_content = Adventure(
            name="Test Content", source=Source(abbreviation="TEST", name="Test Source")
        )

        result = ContentResolutionResult(
            status=ResolutionStatus.EXACT_MATCH, content=mock_content, query="test"
        )

        content_items, source_desc = _handle_resolution_result(
            result, "test", ContentType.ADVENTURE
        )

        assert len(content_items) == 1
        assert content_items[0] == mock_content
        assert "abbreviation:" in source_desc
        assert "test" in source_desc

    def test_handle_resolution_result_multiple_matches(self):
        """Test handling multiple matches result."""
        mock_content1 = Adventure(
            name="Test 1", source=Source(abbreviation="TEST1", name="Test Source 1")
        )

        mock_content2 = Adventure(
            name="Test 2", source=Source(abbreviation="TEST2", name="Test Source 2")
        )

        result = ContentResolutionResult(
            status=ResolutionStatus.MULTIPLE_MATCHES,
            matches=[mock_content1, mock_content2],
            query="test",
        )

        # Import the correct exception type
        import typer

        with pytest.raises(typer.Exit):
            _handle_resolution_result(result, "test", ContentType.ADVENTURE)

    def test_handle_resolution_result_no_match_with_suggestions(self):
        """Test handling no match with suggestions."""
        result = ContentResolutionResult(
            status=ResolutionStatus.NO_MATCH, suggestions=["cos", "lmop"], query="co"
        )

        import typer

        with pytest.raises(typer.Exit):
            _handle_resolution_result(result, "co", ContentType.ADVENTURE)

    def test_handle_resolution_result_no_match_no_suggestions(self):
        """Test handling no match without suggestions."""
        result = ContentResolutionResult(status=ResolutionStatus.NO_MATCH, query="xyz")

        import typer

        with pytest.raises(typer.Exit):
            _handle_resolution_result(result, "xyz", ContentType.ADVENTURE)


@pytest.mark.cli
class TestFileVsAbbreviationDetection:
    """Test detection logic for file vs abbreviation inputs."""

    def test_file_detection_absolute_path(self):
        """Test that absolute file paths are detected correctly."""
        with tempfile.NamedTemporaryFile() as f:
            file_path = Path(f.name)
            assert file_path.is_file()

    def test_file_detection_relative_path(self):
        """Test that relative file paths are detected correctly."""
        with tempfile.NamedTemporaryFile() as f:
            file_path = Path(f.name)
            # Get relative path from current directory
            try:
                rel_path = file_path.relative_to(Path.cwd())
                assert rel_path.is_file()
            except ValueError:
                # File is not relative to cwd, skip this test
                pass

    def test_abbreviation_detection(self):
        """Test that non-file strings are not detected as files."""
        test_cases = [
            "cos",
            "phb",
            "lmop",
            "dmg",
            "nonexistent",
            "file_that_does_not_exist.json",
        ]

        for case in test_cases:
            file_path = Path(case)
            # These should not be detected as existing files
            assert not file_path.is_file()


@pytest.mark.cli
class TestErrorHandling:
    """Test error handling in hybrid parameter detection."""

    def test_invalid_json_file(self):
        """Test handling of invalid JSON files."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("invalid json content {")
            file_path = Path(f.name)

        try:
            import typer

            with pytest.raises(typer.Exit):
                resolve_content_or_file(str(file_path), ContentType.ADVENTURE)
        finally:
            file_path.unlink()

    def test_empty_adventure_file(self):
        """Test handling of adventure file with empty adventure list - should succeed with ContentLoader."""
        adventure_data = {"adventure": []}  # Empty adventure list

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(adventure_data, f)
            file_path = Path(f.name)

        try:
            # ContentLoader now creates default adventure for empty files
            content_items, source_desc = resolve_content_or_file(
                str(file_path), ContentType.ADVENTURE
            )

            # Should create a default adventure with generated name and source
            assert len(content_items) == 1
            assert "Adventure:" in content_items[0].name
            assert "file:" in source_desc
        finally:
            file_path.unlink()

    def test_unsupported_content_type_for_file(self):
        """Test handling of unsupported content type for file loading."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"test": "data"}, f)
            file_path = Path(f.name)

        try:
            import typer

            with pytest.raises(typer.Exit):
                resolve_content_or_file(
                    str(file_path), ContentType.SPELL
                )  # Unsupported for file loading
        finally:
            file_path.unlink()

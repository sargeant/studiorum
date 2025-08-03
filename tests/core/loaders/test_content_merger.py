"""Tests for ContentMerger class."""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock

import pytest

from dnd5e.core.loaders.content_merger import ContentMerger
from dnd5e.core.models.content import ContentType

# Ensure async tests work properly
pytestmark = pytest.mark.asyncio


class TestContentMerger:
    """Test cases for ContentMerger class."""

    @pytest.fixture
    def mock_source_manager(self):
        """Create mock source manager."""
        mock_sm = Mock()
        mock_sm.get_content_files.return_value = {
            ContentType.ADVENTURE: [],
            ContentType.BOOK: [],
        }
        return mock_sm

    @pytest.fixture
    def content_merger(self, mock_source_manager):
        """Create ContentMerger instance."""
        return ContentMerger(mock_source_manager)

    def test_init(self, mock_source_manager):
        """Test ContentMerger initialization."""
        merger = ContentMerger(mock_source_manager)
        assert merger.source_manager is mock_source_manager
        assert merger._content_cache == {}

    def test_normalize_id_to_filename_adventure(self, content_merger):
        """Test ID normalization for adventures."""
        assert (
            content_merger._normalize_id_to_filename(ContentType.ADVENTURE, "CoS")
            == "adventure-cos.json"
        )
        assert (
            content_merger._normalize_id_to_filename(ContentType.ADVENTURE, "LMoP")
            == "adventure-lmop.json"
        )
        assert (
            content_merger._normalize_id_to_filename(
                ContentType.ADVENTURE, "DrDe-ACfaS"
            )
            == "adventure-drde-acfas.json"
        )

    def test_normalize_id_to_filename_book(self, content_merger):
        """Test ID normalization for books."""
        assert (
            content_merger._normalize_id_to_filename(ContentType.BOOK, "PHB")
            == "book-phb.json"
        )
        assert (
            content_merger._normalize_id_to_filename(ContentType.BOOK, "MM")
            == "book-mm.json"
        )
        assert (
            content_merger._normalize_id_to_filename(ContentType.BOOK, "DMG")
            == "book-dmg.json"
        )

    def test_normalize_id_to_filename_unsupported_type(self, content_merger):
        """Test normalization with unsupported content type."""
        with pytest.raises(ValueError, match="Unsupported content type"):
            content_merger._normalize_id_to_filename(ContentType.SPELL, "test")

    async def test_load_content_file_unsupported_type(self, content_merger):
        """Test loading content file with unsupported type."""
        with pytest.raises(
            ValueError, match="Content type.*not supported for dual-file loading"
        ):
            await content_merger.load_content_file(ContentType.SPELL, "test")

    async def test_load_content_file_not_found(
        self, content_merger, mock_source_manager
    ):
        """Test loading content file that doesn't exist."""
        mock_source_manager.get_content_files.return_value = {
            ContentType.ADVENTURE: [],
            ContentType.BOOK: [],
        }

        result = await content_merger.load_content_file(
            ContentType.ADVENTURE, "nonexistent"
        )
        assert result is None

    async def test_load_content_file_success(self, content_merger, mock_source_manager):
        """Test successful content file loading."""
        # Create temporary content file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as tmp_file:
            test_content = {
                "data": [
                    {
                        "type": "section",
                        "name": "Chapter 1",
                        "entries": ["Test content"],
                    }
                ]
            }
            json.dump(test_content, tmp_file)
            tmp_path = Path(tmp_file.name)

        try:
            # Rename file to match expected pattern
            expected_path = tmp_path.parent / "adventure-cos.json"
            tmp_path.rename(expected_path)

            # Mock source manager to return our test file
            mock_source_manager.get_content_files.return_value = {
                ContentType.ADVENTURE: [expected_path],
                ContentType.BOOK: [],
            }

            result = await content_merger.load_content_file(
                ContentType.ADVENTURE, "CoS"
            )
            assert result == test_content

            # Test caching - second call should return cached result
            result2 = await content_merger.load_content_file(
                ContentType.ADVENTURE, "CoS"
            )
            assert result2 == test_content

        finally:
            # Clean up
            if expected_path.exists():
                expected_path.unlink()

    async def test_load_content_file_malformed_json(
        self, content_merger, mock_source_manager
    ):
        """Test loading malformed JSON file."""
        # Create temporary malformed JSON file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as tmp_file:
            tmp_file.write("{ invalid json")
            tmp_path = Path(tmp_file.name)

        try:
            # Rename file to match expected pattern
            expected_path = tmp_path.parent / "adventure-cos.json"
            tmp_path.rename(expected_path)

            # Mock source manager to return our test file
            mock_source_manager.get_content_files.return_value = {
                ContentType.ADVENTURE: [expected_path],
                ContentType.BOOK: [],
            }

            result = await content_merger.load_content_file(
                ContentType.ADVENTURE, "CoS"
            )
            assert result is None

        finally:
            # Clean up
            if expected_path.exists():
                expected_path.unlink()

    def test_clear_cache(self, content_merger):
        """Test cache clearing."""
        # Add something to cache
        content_merger._content_cache["test:key"] = {"data": "test"}
        assert len(content_merger._content_cache) == 1

        content_merger.clear_cache()
        assert len(content_merger._content_cache) == 0

    def test_get_cache_stats(self, content_merger):
        """Test cache statistics."""
        # Empty cache
        stats = content_merger.get_cache_stats()
        assert stats["cached_items"] == 0
        assert stats["cache_keys"] == []
        assert stats["memory_usage_estimate"] == 0

        # Add test data to cache
        test_data = {"data": ["test"]}
        content_merger._content_cache["adventure:cos"] = test_data

        stats = content_merger.get_cache_stats()
        assert stats["cached_items"] == 1
        assert stats["cache_keys"] == ["adventure:cos"]
        assert stats["memory_usage_estimate"] > 0

    async def test_case_insensitive_file_matching(
        self, content_merger, mock_source_manager
    ):
        """Test that file matching is case insensitive."""
        # Create temporary content file with different case
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as tmp_file:
            test_content = {"data": []}
            json.dump(test_content, tmp_file)
            tmp_path = Path(tmp_file.name)

        try:
            # Rename file to uppercase pattern
            expected_path = tmp_path.parent / "ADVENTURE-COS.JSON"
            tmp_path.rename(expected_path)

            # Mock source manager to return our test file
            mock_source_manager.get_content_files.return_value = {
                ContentType.ADVENTURE: [expected_path],
                ContentType.BOOK: [],
            }

            # Should find file despite case mismatch
            result = await content_merger.load_content_file(
                ContentType.ADVENTURE, "CoS"
            )
            assert result == test_content

        finally:
            # Clean up
            if expected_path.exists():
                expected_path.unlink()


class TestContentMergerMerging:
    """Test cases for metadata-content merging functionality."""

    @pytest.fixture
    def content_merger(self):
        """Create ContentMerger instance."""
        mock_sm = Mock()
        return ContentMerger(mock_sm)

    @pytest.fixture
    def sample_metadata_entry(self):
        """Sample adventure metadata entry."""
        return {
            "name": "Test Adventure",
            "id": "TestAdv",
            "source": "TestSource",
            "contents": [
                {"name": "Introduction", "headers": ["Overview", "Setup"]},
                {"name": "Chapter 1: The Beginning", "headers": ["Scene 1", "Scene 2"]},
                {"name": "Epilogue", "headers": []},
            ],
        }

    @pytest.fixture
    def sample_content_data(self):
        """Sample adventure content data."""
        return {
            "data": [
                {
                    "type": "section",
                    "name": "Introduction",
                    "id": "000",
                    "entries": [
                        "Welcome to the adventure.",
                        "This is the introduction content.",
                    ],
                },
                {
                    "type": "section",
                    "name": "Chapter 1: The Beginning",
                    "id": "001",
                    "entries": [
                        "The adventure begins here.",
                        "The party finds themselves in a tavern.",
                        "A mysterious figure approaches.",
                    ],
                },
                {
                    "type": "section",
                    "name": "Epilogue",
                    "id": "099",
                    "entries": ["The adventure concludes.", "The heroes return home."],
                },
            ]
        }

    def test_merge_metadata_content_success(
        self, content_merger, sample_metadata_entry, sample_content_data
    ):
        """Test successful merging of metadata and content."""
        result = content_merger.merge_metadata_content(
            sample_metadata_entry, sample_content_data
        )

        # Check that base metadata is preserved
        assert result["name"] == "Test Adventure"
        assert result["id"] == "TestAdv"
        assert result["source"] == "TestSource"

        # Check merged contents
        assert len(result["contents"]) == 3

        # Check first section (Introduction)
        intro = result["contents"][0]
        assert intro["name"] == "Introduction"
        assert intro["headers"] == ["Overview", "Setup"]
        assert len(intro["entries"]) == 2
        assert intro["entries"][0] == "Welcome to the adventure."
        assert intro["entries"][1] == "This is the introduction content."
        assert intro["ordinal"]["type"] == "section"
        assert intro["ordinal"]["identifier"] == "000"

        # Check second section (Chapter 1)
        chapter1 = result["contents"][1]
        assert chapter1["name"] == "Chapter 1: The Beginning"
        assert len(chapter1["entries"]) == 3
        assert chapter1["entries"][0] == "The adventure begins here."
        assert chapter1["ordinal"]["identifier"] == "001"

        # Check third section (Epilogue)
        epilogue = result["contents"][2]
        assert epilogue["name"] == "Epilogue"
        assert len(epilogue["entries"]) == 2
        assert epilogue["ordinal"]["identifier"] == "099"

    def test_merge_metadata_content_no_content_data(
        self, content_merger, sample_metadata_entry
    ):
        """Test merging when content data is None."""
        result = content_merger.merge_metadata_content(sample_metadata_entry, None)

        # Should preserve metadata structure
        assert result["name"] == "Test Adventure"
        assert result["id"] == "TestAdv"

        # Contents should have empty entries
        assert len(result["contents"]) == 3
        for content in result["contents"]:
            assert content["entries"] == []

    def test_merge_metadata_content_invalid_content_data(
        self, content_merger, sample_metadata_entry
    ):
        """Test merging with invalid content data."""
        invalid_content = {"data": "not a list"}

        result = content_merger.merge_metadata_content(
            sample_metadata_entry, invalid_content
        )

        # Should fallback to metadata-only result
        assert result["name"] == "Test Adventure"
        assert len(result["contents"]) == 3
        for content in result["contents"]:
            assert content["entries"] == []

    def test_merge_metadata_content_missing_content_sections(
        self, content_merger, sample_metadata_entry
    ):
        """Test merging when some content sections are missing."""
        partial_content = {
            "data": [
                {
                    "type": "section",
                    "name": "Introduction",
                    "id": "000",
                    "entries": ["Only the introduction has content."],
                }
            ]
        }

        result = content_merger.merge_metadata_content(
            sample_metadata_entry, partial_content
        )

        assert len(result["contents"]) == 3

        # Introduction should have content
        intro = result["contents"][0]
        assert len(intro["entries"]) == 1
        assert intro["entries"][0] == "Only the introduction has content."

        # Other sections should have empty entries
        chapter1 = result["contents"][1]
        assert chapter1["entries"] == []

        epilogue = result["contents"][2]
        assert epilogue["entries"] == []

    def test_merge_metadata_content_extra_content_sections(
        self, content_merger, sample_metadata_entry, sample_content_data
    ):
        """Test merging when content has extra sections not in metadata."""
        # Add extra section to content
        extra_content = dict(sample_content_data)
        extra_content["data"].append(
            {
                "type": "section",
                "name": "Bonus Chapter",
                "id": "bonus",
                "entries": ["This is a bonus chapter not in metadata."],
            }
        )

        result = content_merger.merge_metadata_content(
            sample_metadata_entry, extra_content
        )

        # Should have 4 sections now (3 from metadata + 1 extra)
        assert len(result["contents"]) == 4

        # Last section should be the bonus chapter
        bonus = result["contents"][3]
        assert bonus["name"] == "Bonus Chapter"
        assert len(bonus["entries"]) == 1
        assert bonus["entries"][0] == "This is a bonus chapter not in metadata."
        assert bonus["ordinal"]["identifier"] == "bonus"

    def test_merge_metadata_content_non_section_content_ignored(
        self, content_merger, sample_metadata_entry
    ):
        """Test that non-section content types are ignored."""
        content_with_non_sections = {
            "data": [
                {
                    "type": "section",
                    "name": "Introduction",
                    "entries": ["Valid section content."],
                },
                {
                    "type": "table",
                    "name": "Some Table",
                    "entries": ["This should be ignored."],
                },
            ]
        }

        result = content_merger.merge_metadata_content(
            sample_metadata_entry, content_with_non_sections
        )

        # Only the Introduction section should be processed
        intro = result["contents"][0]
        assert len(intro["entries"]) == 1
        assert intro["entries"][0] == "Valid section content."

        # Other sections should have empty entries
        assert result["contents"][1]["entries"] == []
        assert result["contents"][2]["entries"] == []

    def test_create_metadata_only_result(self, content_merger, sample_metadata_entry):
        """Test creating metadata-only result."""
        result = content_merger._create_metadata_only_result(sample_metadata_entry)

        # Should preserve all metadata
        assert result["name"] == "Test Adventure"
        assert result["id"] == "TestAdv"
        assert result["source"] == "TestSource"

        # All contents should have empty entries
        assert len(result["contents"]) == 3
        for content in result["contents"]:
            assert content["entries"] == []
            # Should preserve other metadata fields
            assert "name" in content

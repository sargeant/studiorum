"""Tests for chapter filtering utilities."""

import pytest

from studiorum.core.models.adventures import Adventure, AdventureMetadata
from studiorum.core.models.chapter import Chapter
from studiorum.core.utils.chapters import (
    extract_chapter_number,
    filter_adventure_chapters,
    parse_chapter_spec,
)


class TestParseChapterSpec:
    """Tests for chapter specification parsing."""

    def test_single_chapter(self):
        assert parse_chapter_spec("5") == [5]

    def test_multiple_chapters_sorted(self):
        assert parse_chapter_spec("9,1,5") == [1, 5, 9]

    def test_range(self):
        assert parse_chapter_spec("8-10") == [8, 9, 10]

    def test_combined(self):
        assert parse_chapter_spec("1,5,8-10") == [1, 5, 8, 9, 10]

    def test_duplicates_removed(self):
        assert parse_chapter_spec("5,5,3-5") == [3, 4, 5]

    def test_whitespace_handling(self):
        assert parse_chapter_spec(" 1 , 5 , 8 - 10 ") == [1, 5, 8, 9, 10]

    def test_invalid_range_reversed(self):
        with pytest.raises(ValueError, match="Invalid range '10-8'"):
            parse_chapter_spec("10-8")

    def test_invalid_non_numeric(self):
        with pytest.raises(ValueError, match="Invalid chapter number 'foo'"):
            parse_chapter_spec("foo")

    def test_invalid_range_non_numeric(self):
        with pytest.raises(ValueError, match="Invalid range 'a-b'"):
            parse_chapter_spec("a-b")

    def test_empty_spec(self):
        with pytest.raises(ValueError, match="No valid chapter numbers"):
            parse_chapter_spec("")


class TestExtractChapterNumber:
    """Tests for chapter number extraction."""

    def test_extract_from_ordinal_chapter(self):
        chapter = Chapter(
            name="Chapter 5: Title",
            ordinal={"type": "chapter", "identifier": "5"},
            entries=[],
        )
        assert extract_chapter_number(chapter) == 5

    def test_extract_from_name_standard(self):
        chapter = Chapter(name="Chapter 5: Title", entries=[])
        assert extract_chapter_number(chapter) == 5

    def test_extract_from_name_ch_with_dot(self):
        chapter = Chapter(name="Ch. 5: Title", entries=[])
        assert extract_chapter_number(chapter) == 5

    def test_extract_from_name_ch_without_dot(self):
        chapter = Chapter(name="Ch 5: Title", entries=[])
        assert extract_chapter_number(chapter) == 5

    def test_extract_case_insensitive(self):
        chapter = Chapter(name="CHAPTER 5: Title", entries=[])
        assert extract_chapter_number(chapter) == 5

    def test_extract_introduction(self):
        chapter = Chapter(name="Introduction", entries=[])
        assert extract_chapter_number(chapter) is None

    def test_extract_appendix(self):
        chapter = Chapter(name="Appendix A: Creatures", entries=[])
        assert extract_chapter_number(chapter) is None

    def test_ordinal_section_ignored(self):
        chapter = Chapter(
            name="Introduction",
            ordinal={"type": "section", "identifier": "000"},
            entries=[],
        )
        assert extract_chapter_number(chapter) is None


class TestFilterAdventureChapters:
    """Tests for adventure chapter filtering."""

    @pytest.fixture
    def mock_adventure(self):
        from studiorum.core.models.content import Source

        chapters = [
            Chapter(name="Introduction", entries=["intro"]),
            Chapter(name="Chapter 1: First", entries=["ch1"]),
            Chapter(name="Chapter 2: Second", entries=["ch2"]),
            Chapter(name="Chapter 5: Fifth", entries=["ch5"]),
            Chapter(name="Appendix A: Creatures", entries=["appa"]),
        ]
        return Adventure(
            name="Test Adventure",
            source=Source(abbreviation="TEST", name="Test Source"),
            contents=chapters,
        )

    def test_filter_single_chapter(self, mock_adventure):
        filtered, warnings = filter_adventure_chapters(mock_adventure, [5])
        assert len(filtered.contents) == 1
        assert filtered.contents[0].name == "Chapter 5: Fifth"
        assert not warnings

    def test_filter_multiple_chapters(self, mock_adventure):
        filtered, warnings = filter_adventure_chapters(mock_adventure, [1, 2])
        assert len(filtered.contents) == 2
        assert filtered.contents[0].name == "Chapter 1: First"
        assert filtered.contents[1].name == "Chapter 2: Second"
        assert not warnings

    def test_filter_with_introduction(self, mock_adventure):
        filtered, warnings = filter_adventure_chapters(
            mock_adventure, [5], include_introduction=True
        )
        assert len(filtered.contents) == 2
        assert filtered.contents[0].name == "Introduction"
        assert filtered.contents[1].name == "Chapter 5: Fifth"

    def test_filter_missing_chapters_warns(self, mock_adventure):
        filtered, warnings = filter_adventure_chapters(mock_adventure, [1, 3, 5])
        assert len(warnings) == 1
        assert "3" in warnings[0]
        assert "Available: [1, 2, 5]" in warnings[0]

    def test_filter_no_matches_raises(self, mock_adventure):
        with pytest.raises(ValueError, match="No chapters found matching"):
            filter_adventure_chapters(mock_adventure, [99])

    def test_chapter_number_map_stored(self, mock_adventure):
        filtered, _ = filter_adventure_chapters(mock_adventure, [1, 5])

        chapter_map = filtered.metadata.custom_fields["chapter_number_map"]
        assert chapter_map == {0: 1, 1: 5}

    def test_preserves_content(self, mock_adventure):
        filtered, _ = filter_adventure_chapters(mock_adventure, [1])
        assert filtered.contents[0].entries == ["ch1"]

    def test_chapter_order_by_index(self, mock_adventure):
        filtered, _ = filter_adventure_chapters(mock_adventure, [5, 1])
        assert filtered.contents[0].name == "Chapter 1: First"
        assert filtered.contents[1].name == "Chapter 5: Fifth"

    def test_creates_metadata_if_missing(self):
        from studiorum.core.models.content import Source

        adventure_no_metadata = Adventure(
            name="Test",
            source=Source(abbreviation="TEST", name="Test Source"),
            contents=[Chapter(name="Chapter 1: Test", entries=["test"])],
        )
        filtered, _ = filter_adventure_chapters(adventure_no_metadata, [1])

        assert filtered.metadata is not None
        assert "chapter_number_map" in filtered.metadata.custom_fields

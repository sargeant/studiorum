"""Tests for chapter filtering utilities."""

import pytest

from studiorum.core.models.adventures import Adventure
from studiorum.core.models.chapter import Chapter
from studiorum.core.utils.chapters import (
    chapter_number,
    filter_adventure_chapters,
    numbered_kind,
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


def _ch(name: str, kind: str | None = None, identifier: object = None) -> Chapter:
    ordinal = {"type": kind, "identifier": identifier} if kind else None
    return Chapter(name=name, ordinal=ordinal, entries=[name])


def _adventure(*chapters: Chapter) -> Adventure:
    from studiorum.core.models.content import Source

    return Adventure(
        name="Test Adventure",
        source=Source(abbreviation="TEST", name="Test Source"),
        contents=list(chapters),
    )


class TestNumberedKind:
    def test_the_kind_used_most(self):
        chapters = [_ch("Orrery", "chapter", 1)] + [
            _ch(f"Episode {i}", "episode", i) for i in (1, 2)
        ]
        assert numbered_kind(chapters) == "episode"

    def test_appendices_are_not_numbered(self):
        assert numbered_kind([_ch("Intro"), _ch("Lore", "appendix", "A")]) is None

    def test_chapter_number_reads_identifiers(self):
        assert chapter_number(_ch("A", "part", 2), "part") == 2
        assert chapter_number(_ch("A", "part", "3"), "part") == 3
        assert chapter_number(_ch("A", "part", 2), "chapter") is None
        assert chapter_number(_ch("A"), "chapter") is None


class TestFilterAdventureChapters:
    """Tests for adventure chapter filtering."""

    @pytest.fixture
    def mock_adventure(self):
        return _adventure(
            _ch("Introduction"),
            _ch("First", "chapter", 1),
            _ch("Second", "chapter", 2),
            _ch("Fifth", "chapter", 5),
            _ch("Creatures", "appendix", "A"),
        )

    def test_filter_single_chapter(self, mock_adventure):
        filtered, warnings = filter_adventure_chapters(mock_adventure, [5])
        assert [c.name for c in filtered.contents] == ["Fifth"]
        assert not warnings

    def test_filter_multiple_chapters(self, mock_adventure):
        filtered, warnings = filter_adventure_chapters(mock_adventure, [1, 2])
        assert [c.name for c in filtered.contents] == ["First", "Second"]
        assert not warnings

    def test_filter_with_introduction(self, mock_adventure):
        filtered, _ = filter_adventure_chapters(
            mock_adventure, [5], include_introduction=True
        )
        assert [c.name for c in filtered.contents] == ["Introduction", "Fifth"]

    def test_filter_missing_chapters_warns(self, mock_adventure):
        filtered, warnings = filter_adventure_chapters(mock_adventure, [1, 3, 5])
        assert len(warnings) == 1
        assert "3" in warnings[0]
        assert "Available: [1, 2, 5]" in warnings[0]

    def test_filter_no_matches_raises(self, mock_adventure):
        with pytest.raises(ValueError, match="No chapters found matching"):
            filter_adventure_chapters(mock_adventure, [99])

    def test_filtered_chapters_keep_their_ordinals(self, mock_adventure):
        filtered, _ = filter_adventure_chapters(mock_adventure, [5])
        assert filtered.contents[0].label == "Chapter 5"

    def test_preserves_content(self, mock_adventure):
        filtered, _ = filter_adventure_chapters(mock_adventure, [1])
        assert filtered.contents[0].entries == ["First"]

    def test_chapter_order_by_index(self, mock_adventure):
        filtered, _ = filter_adventure_chapters(mock_adventure, [5, 1])
        assert [c.name for c in filtered.contents] == ["First", "Fifth"]

    def test_episodes_are_numbered_when_most_common(self):
        adventure = _adventure(
            _ch("Orrery", "chapter", 1),
            _ch("Right Place", "episode", 1),
            _ch("Fun in Phandalin", "episode", 2),
            _ch("Credits"),
        )
        filtered, _ = filter_adventure_chapters(adventure, [2])
        assert [c.name for c in filtered.contents] == ["Fun in Phandalin"]


class TestPositionalChapterFallback:
    """Adventures with no numbered chapters are numbered by position."""

    @pytest.fixture
    def anthology_adventure(self):
        return _adventure(
            _ch("First Story"),
            _ch("Second Story"),
            _ch("Third Story"),
            _ch("Creatures", "appendix", "A"),
        )

    def test_positional_fallback_selects_nth_chapter(self, anthology_adventure):
        filtered, warnings = filter_adventure_chapters(anthology_adventure, [2])
        assert [c.name for c in filtered.contents] == ["Second Story"]
        assert any("positional numbering" in w for w in warnings)

    def test_positional_fallback_out_of_range_raises(self, anthology_adventure):
        with pytest.raises(ValueError, match="No chapters found matching"):
            filter_adventure_chapters(anthology_adventure, [99])

    def test_positional_fallback_not_used_for_numbered_mix(self):
        adventure = _adventure(
            _ch("Foreword"), _ch("Real", "chapter", 1), _ch("Side Story")
        )
        with pytest.raises(ValueError, match="No chapters found matching"):
            filter_adventure_chapters(adventure, [2])

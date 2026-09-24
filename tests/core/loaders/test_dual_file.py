"""merge_metadata_content fills an adventure's or book's chapters from its text."""

from studiorum.core.loaders.dual_file import merge_metadata_content

ADVENTURE = {
    "name": "A",
    "id": "A",
    "source": "A",
    "level": {"start": 1, "end": 5},
    "contents": [
        {"name": "Intro"},
        {"name": "Lore", "ordinal": {"type": "appendix", "identifier": "A"}},
        {"name": "Not Written"},
    ],
}


def _section(name: str, *entries: str, **extra: object) -> dict:
    return {"type": "section", "name": name, "entries": list(entries), **extra}


def test_chapters_pair_with_sections_by_position() -> None:
    text = {
        "data": [
            _section("Dramatis Personae", "Hello.", id="001"),
            _section("Appendix A: Lore", "Old things."),
            {"type": "entries", "name": "Unwritten", "entries": ["Later."]},
        ]
    }

    merged = merge_metadata_content(ADVENTURE, text)

    assert merged["contents"] == [
        {
            "name": "Intro",
            "entries": ["Hello."],
            "ordinal": {"type": "section", "identifier": "001"},
        },
        {
            "name": "Lore",
            "ordinal": {"type": "appendix", "identifier": "A"},
            "entries": ["Old things."],
        },
        {
            "name": "Not Written",
            "entries": [
                {"type": "entries", "name": "Unwritten", "entries": ["Later."]}
            ],
        },
    ]
    assert merged["level"] == ADVENTURE["level"]


def test_sections_keep_their_names_when_the_counts_differ() -> None:
    text = {"data": [_section("Only", "Text.")]}

    merged = merge_metadata_content(ADVENTURE, text)

    assert merged["contents"] == [{"name": "Only", "entries": ["Text."]}]


def test_no_text_leaves_empty_chapters() -> None:
    merged = merge_metadata_content(ADVENTURE, None)

    assert [c["entries"] for c in merged["contents"]] == [[], [], []]


def test_books_take_their_chapters_from_the_text() -> None:
    book = {
        "name": "B",
        "id": "B",
        "source": "B",
        "author": "Someone",
        "published": "2020-01-01",
        "contents": [{"name": "Ignored header"}],
    }
    text = {"data": [_section("One", "First.", page=3), _section("Two", "Second.")]}

    merged = merge_metadata_content(book, text)

    assert merged == {
        "name": "B",
        "source": "B",
        "id": "B",
        "published": "2020-01-01",
        "contents": [
            {"name": "One", "entries": ["First."], "page": 3},
            {"name": "Two", "entries": ["Second."]},
        ],
    }

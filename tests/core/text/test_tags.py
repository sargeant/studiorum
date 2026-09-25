"""Splitting 5etools tag markup."""

from __future__ import annotations

import pytest

from studiorum.core.text.tags import display_part, split_by_pipe, split_by_tags


def test_split_by_tags_keeps_nested_tags_inside_their_parent() -> None:
    text = "The {@creature goblin|MM|the {@i sneaky} goblin} {@b hides}."
    assert split_by_tags(text) == [
        "The ",
        "{@creature goblin|MM|the {@i sneaky} goblin}",
        " ",
        "{@b hides}",
        ".",
    ]


def test_split_by_tags_leaves_other_braces_as_text() -> None:
    assert split_by_tags("a {b} {@i c}") == ["a {b} ", "{@i c}"]


def test_split_by_pipe_ignores_pipes_in_nested_tags_and_escaped_pipes() -> None:
    assert split_by_pipe(r"a|{@spell b|PHB}|c\|d") == ["a", "{@spell b|PHB}", r"c\|d"]


@pytest.mark.parametrize(
    ("tag", "parts", "expected"),
    [
        ("vehicle", ["Ship", "GoS"], "Ship"),
        ("vehicle", ["Ship", "GoS", "the ship"], "the ship"),
        ("deity", ["Tyr", "Faerûnian", "SCAG", "the god"], "the god"),
        ("font", ["text", "fontname"], "text"),
        ("classFeature", ["Rage", "Barbarian", "", "1", "", "raging"], "raging"),
    ],
)
def test_display_part(tag: str, parts: list[str], expected: str) -> None:
    assert display_part(tag, parts) == expected

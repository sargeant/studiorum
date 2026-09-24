"""5etools tags rendered to LaTeX."""

from __future__ import annotations

import pytest

from studiorum.renderers.core.tag_resolver import TagResolver


@pytest.fixture
def resolver() -> TagResolver:
    return TagResolver()


@pytest.mark.xfail(strict=True, reason="nested display text renders as a repr")
def test_nested_display_text_renders_recursively(resolver: TagResolver) -> None:
    text = "{@creature goblin|MM|the {@i sneaky} goblin}"
    assert resolver.process_text(text) == r"\textbf{the \textit{sneaky} goblin}"


@pytest.mark.xfail(strict=True, reason="an unknown tag returns the raw input")
def test_unhandled_tag_renders_escaped_display_text(resolver: TagResolver) -> None:
    text = "Ride the {@vehicle Ship of the Line|GoS} & go"
    assert resolver.process_text(text) == r"Ride the Ship of the Line \& go"

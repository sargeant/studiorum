"""Plain text escaped for LaTeX."""

from __future__ import annotations

import pytest

from studiorum.renderers.escape import escape, escape_url


@pytest.mark.parametrize(
    ("text", "latex"),
    [
        ("", ""),
        ("plain text", "plain text"),
        ("{}$&%#_", r"\{\}\$\&\%\#\_"),
        ("a\\b", r"a\textbackslash{}b"),
        ("~x^2", r"\textasciitilde{}x\textasciicircum{}2"),
        ("a\u2014b\u2013c\u2026", r"a---b--c\ldots{}"),
        (
            "\u00b0 \u00a9 \u00ae \u2122",
            r"\textdegree{} \copyright{} \textregistered{} \texttrademark{}",
        ),
        ("adds\u00a04", "adds~4"),
        ('Player\'s "quote"', 'Player\'s "quote"'),
        (
            "caf\u00e9 \u00d7 \u00bd \u2019 \u2020",
            "caf\u00e9 \u00d7 \u00bd \u2019 \u2020",
        ),
        ("Faeru\u0302n", "Faer\u00fbn"),
        ("\\input{/etc/passwd}", r"\textbackslash{}input\{/etc/passwd\}"),
        # The game's name in small caps
        ("D&D", r"\textsc{d\&d}"),
        ("the d&d rules", r"the \textsc{d\&d} rules"),
        ("Dungeons & Dragons", r"\textsc{Dungeons \& Dragons}"),
        ("Dungeons  &  dragons®", r"\textsc{Dungeons \& Dragons}\textregistered{}"),
        ("first edition AD&D", r"first edition AD\&D"),
    ],
)
def test_escape(text: str, latex: str) -> None:
    assert escape(text) == latex


def test_escape_url() -> None:
    assert escape_url("https://x.y/p_q?a=1&b=2%20#c~d") == (
        r"https://x.y/p_q?a=1\&b=2\%20\#c~d"
    )

"""Documents assembled from chapters opened by their 5etools ordinals."""

from typing import Any
from unittest.mock import Mock

from studiorum.core.models.adventures import Adventure
from studiorum.core.models.chapter import Chapter
from studiorum.core.models.content import Source
from studiorum.core.models.creatures import Creature
from studiorum.core.models.document_metadata import DocumentMetadata, DocumentType
from studiorum.core.models.spells import Spell
from studiorum.core.references.content_tracker import ContentTracker
from studiorum.core.services.appendix_generator import AppendixFlags
from studiorum.latex_engine.document import (
    DocumentChapter,
    appendix_chapters,
    render_document,
    render_models,
)
from studiorum.renderers.context import RenderingContext, Style


def _chapter(name: str, kind: str | None = None, identifier: Any = None) -> Chapter:
    ordinal = {"type": kind, "identifier": identifier} if kind else None
    return Chapter(
        name=name, id=name[:3].lower(), ordinal=ordinal, entries=[f"{name} text."]
    )


def _render(*chapters: Chapter) -> str:
    adventure = Adventure(
        name="Test", source=Source(abbreviation="T", name="Test"), contents=chapters
    )
    return render_document(
        [adventure],
        RenderingContext(),
        DocumentMetadata(title="Test", document_type=DocumentType.ADVENTURE),
    )


def _body(latex: str) -> list[str]:
    """The chapter commands and chapter text, in order."""
    body = latex.split("\\mainmatter", 1)[1]
    return [line for line in body.splitlines() if line and not line.startswith("%")]


def test_chapters_open_from_their_ordinals() -> None:
    latex = _render(
        _chapter("Introduction"),
        _chapter("Road", "chapter", 1),
        _chapter("Castle", "chapter", 2),
        _chapter("Creatures", "appendix", "A"),
        _chapter("Maps", "appendix", "B"),
        _chapter("Credits"),
    )

    assert _body(latex)[:21] == [
        "\\chapter*{Introduction}",
        "\\addcontentsline{toc}{chapter}{Introduction}",
        "\\label{ch:int}",
        "Introduction text.",
        "\\setcounter{chapter}{0}",
        "\\chapter{Road}\\label{ch:roa}",
        "Road text.",
        "\\setcounter{chapter}{1}",
        "\\chapter{Castle}\\label{ch:cas}",
        "Castle text.",
        "\\appendix",
        "\\setcounter{chapter}{0}",
        "\\chapter{Creatures}\\label{ch:cre}",
        "Creatures text.",
        "\\setcounter{chapter}{1}",
        "\\chapter{Maps}\\label{ch:map}",
        "Maps text.",
        "\\chapter*{Credits}",
        "\\addcontentsline{toc}{chapter}{Credits}",
        "\\label{ch:cre}",
        "Credits text.",
    ]


def test_numbers_come_from_the_identifiers() -> None:
    latex = _render(_chapter("Late", "chapter", 5), _chapter("Letter", "appendix", "C"))

    assert "\\setcounter{chapter}{4}\n\\chapter{Late}" in latex
    assert "\\setcounter{chapter}{2}\n\\chapter{Letter}" in latex


def test_parts_and_episodes_rename_the_chapter() -> None:
    latex = _render(
        _chapter("Orrery", "chapter", 1),
        _chapter("Heroes", "episode", 1),
        _chapter("Phandalin", "episode", 2),
    )

    body = _body(latex)
    rename = "\\renewcommand{\\chaptername}{Episode}"
    assert body.count(rename) == 1
    assert body.index("\\chapter{Orrery}\\label{ch:orr}") < body.index(rename)
    assert "\\addtocontents{toc}{\\protect\\def\\protect\\tocchapapp{Ep.}}" in body


def test_an_appendix_without_a_letter_is_lettered_by_latex() -> None:
    latex = _render(_chapter("Spirit Board", "appendix"))

    assert "\\appendix\n\\chapter{Spirit Board}" in latex


def test_consecutive_entries_are_separate_paragraphs() -> None:
    chapter = Chapter(name="One", ordinal=None, entries=["First.", "Second."])

    assert "First.\n\nSecond." in _render(chapter)


def test_titles_are_escaped() -> None:
    assert "\\chapter*{Rock \\& Roll}" in _render(_chapter("Rock & Roll"))


def test_loose_content_gets_a_chapter_per_type() -> None:
    spell = Spell.model_validate(
        {
            "name": "Blink",
            "source": "PHB",
            "level": 3,
            "school": "T",
            "time": [{"number": 1, "unit": "action"}],
            "range": {"type": "point", "distance": {"type": "self"}},
            "components": {"v": True, "s": True},
            "duration": [
                {"type": "timed", "duration": {"type": "minute", "amount": 1}}
            ],
            "entries": ["Roll a d20."],
        }
    )
    latex = render_document(
        [spell], RenderingContext(), DocumentMetadata(title="Loose")
    )

    assert "\\chapter{Spells}\\label{ch:spell}" in latex
    assert "{Blink}" in latex


def test_counter_reads_numbers_and_letters() -> None:
    def counter(kind: Any, identifier: Any) -> int | None:
        return DocumentChapter("T", kind, identifier, "ch:t", "").counter

    assert counter("chapter", 3) == 2
    assert counter("part", "2") == 1
    assert counter("appendix", "B") == 1
    assert counter("appendix", None) is None


def test_the_statblock_style_places_saving_throws() -> None:
    creature = Creature.model_validate(
        {
            "name": "Sentry",
            "source": "MM",
            "size": ["M"],
            "type": "construct",
            "alignment": ["U"],
            "ac": [15],
            "hp": {"average": 30, "formula": "4d8 + 12"},
            "speed": {"walk": 30},
            "str": 14,
            "dex": 10,
            "con": 16,
            "int": 3,
            "wis": 12,
            "cha": 1,
            "save": {"con": "+5"},
            "cr": "2",
        }
    )

    def latex(statblock: Any) -> str:
        context = RenderingContext(style=Style(statblock=statblock))
        return render_models("creature", [creature], context)

    assert "con save = +5" in latex("2024")
    assert "saving-throws" not in latex("2024")
    assert "saving-throws = {Con +5}" in latex("2014")
    assert "con save" not in latex("2014")


def test_recursive_appendices_add_what_appendix_entries_refer_to() -> None:
    mage = Creature.model_validate(
        {
            "name": "Mage",
            "source": "MM",
            "size": ["M"],
            "type": "humanoid",
            "alignment": ["A"],
            "ac": [12],
            "hp": {"average": 40, "formula": "9d8"},
            "speed": {"walk": 30},
            "str": 9,
            "dex": 14,
            "con": 11,
            "int": 17,
            "wis": 12,
            "cha": 11,
            "cr": "6",
            "trait": [{"name": "Wards", "entries": ["It casts {@spell shield}."]}],
        }
    )
    shield = Spell.model_validate(
        {
            "name": "Shield",
            "source": "PHB",
            "level": 1,
            "school": "A",
            "time": [{"number": 1, "unit": "reaction"}],
            "range": {"type": "point", "distance": {"type": "self"}},
            "components": {"v": True, "s": True},
            "duration": [{"type": "timed", "duration": {"type": "round", "amount": 1}}],
            "entries": ["An invisible barrier."],
        }
    )
    content = {"mage": mage, "shield": shield}
    omnidexer = Mock(
        find=Mock(side_effect=lambda _type, name, _source: content.get(name.lower()))
    )

    def titles(recursive: bool) -> list[str]:
        tracker = ContentTracker()
        tracker.add_content("creature", "Mage", "MM")
        context = RenderingContext(content_tracker=tracker, omnidexer=omnidexer)
        flags = AppendixFlags(creatures=True, spells=True, recursive=recursive)
        return [chapter.title for chapter in appendix_chapters(context, flags)]

    assert titles(recursive=False) == ["Creatures"]
    assert titles(recursive=True) == ["Creatures", "Spells"]

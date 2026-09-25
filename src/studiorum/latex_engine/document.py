"""Documents made of chapters: adventures, books and supplements.

Each chapter's body is rendered before the document template runs, and
``book.tex.j2`` opens each one from its 5etools ordinal. Appendices of the
creatures, items and spells the document refers to come last, as chapters
rendered through the creature, item and spell macros.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, replace
from typing import Any

from studiorum.core.config.unified_config import LaTeXConfig
from studiorum.core.models.adventures import Adventure
from studiorum.core.models.books import Book
from studiorum.core.models.chapter import NUMBERED_KINDS, OrdinalType
from studiorum.core.models.content_models import content_type_of
from studiorum.core.models.document_metadata import DocumentMetadata
from studiorum.core.services.appendix_generator import (
    Appendix,
    AppendixFlags,
    AppendixGenerator,
)
from studiorum.renderers.context import RenderingContext

from .core.template_engine import LaTeXTemplateEngine, environment
from .entries import EntryRenderer

# 5etools' table of contents abbreviations (Parser.bookOrdinalToAbv)
TOC_WORDS = {"chapter": "Ch.", "part": "Part", "episode": "Ep.", "level": "Level"}

# Chapter titles for supplements, by content type
CONTENT_TITLES = {
    "spell": "Spells",
    "creature": "Creatures and NPCs",
    "item": "Magic Items and Equipment",
}


@dataclass(frozen=True)
class DocumentChapter:
    """A chapter as the document opens it, with its body already in LaTeX.

    ``kind`` is the 5etools ordinal type, or None for an unnumbered chapter
    such as an introduction or the credits. ``identifier`` is the ordinal's
    number or letter; without one LaTeX counts. Appendices are lettered.
    """

    title: str
    kind: OrdinalType | None
    identifier: int | str | None
    label: str
    body: str

    @property
    def opening(self) -> str:
        """How the chapter opens: "numbered", "appendix" or "unnumbered"."""
        if self.kind in NUMBERED_KINDS:
            return "numbered"
        return "appendix" if self.kind == "appendix" else "unnumbered"

    @property
    def word(self) -> str:
        """What LaTeX calls the chapter: Chapter, Part, Episode or Level."""
        return (self.kind or "chapter").title()

    @property
    def toc_word(self) -> str:
        return TOC_WORDS.get(self.kind or "chapter", "Ch.")

    @property
    def counter(self) -> int | None:
        """The chapter counter before the chapter opens, if it is set."""
        identifier = self.identifier
        if isinstance(identifier, str) and identifier.isdigit():
            identifier = int(identifier)
        if isinstance(identifier, int):
            return identifier - 1
        if isinstance(identifier, str) and re.fullmatch(r"[A-Z]", identifier):
            return ord(identifier) - ord("A")
        return None


def render_document(
    content: Sequence[Any],
    context: RenderingContext,
    metadata: DocumentMetadata,
    *,
    appendices: AppendixFlags | None = None,
    latex_config: LaTeXConfig | None = None,
) -> str:
    """The LaTeX document for adventures, books or loose content.

    ``appendices`` says which appendices of referenced content to add.
    """
    context = replace(context, style=replace(context.style, book=True))
    renderer = EntryRenderer.from_context(context)
    chapters: list[DocumentChapter] = []
    loose: list[Any] = []
    for item in content:
        if isinstance(item, Adventure | Book):
            chapters.extend(publication_chapters(item, renderer))
        else:
            loose.append(item)
    chapters.extend(content_chapters(loose, context))

    engine = LaTeXTemplateEngine()
    if latex_config is not None:
        engine.update_latex_config(latex_config)
    flags = appendices or AppendixFlags()
    return engine.render_dnd_template(
        "book",
        metadata.document_type.value,
        metadata=metadata,
        chapters=chapters,
        appendices=lambda: appendix_chapters(context, flags),
        show_title_page=True,
        use_frontmatter=True,
    )


def publication_chapters(
    publication: Adventure | Book, renderer: EntryRenderer
) -> list[DocumentChapter]:
    """An adventure's or book's chapters, each opened from its ordinal."""
    chapters = []
    for i, chapter in enumerate(publication.contents):
        ordinal = chapter.ordinal
        chapters.append(
            DocumentChapter(
                title=chapter.name,
                kind=ordinal.type if ordinal else None,
                identifier=ordinal.identifier if ordinal else None,
                label=f"ch:{chapter.id or i}",
                body=renderer.render(chapter.entries) if chapter.entries else "",
            )
        )
    return chapters


def content_chapters(
    items: Sequence[Any], context: RenderingContext
) -> list[DocumentChapter]:
    """A chapter for each content type, in the order the types first appear."""
    by_type: dict[str, list[Any]] = {}
    for item in items:
        by_type.setdefault(content_type_of(item).value, []).append(item)
    return [
        DocumentChapter(
            title=CONTENT_TITLES.get(kind, kind.title()),
            kind="chapter",
            identifier=None,
            label=f"ch:{kind}",
            body=render_models(kind, members, context),
        )
        for kind, members in by_type.items()
    ]


def appendix_chapters(
    context: RenderingContext, flags: AppendixFlags
) -> list[DocumentChapter]:
    """Appendices of what the document refers to, as the flags ask.

    Call it once the rest of the document is rendered, so the tracker holds
    every reference.
    """
    tracker, omnidexer = context.content_tracker, context.omnidexer
    if not flags.has_any_enabled() or tracker is None or omnidexer is None:
        return []
    appendices = AppendixGenerator(omnidexer).generate_appendices(tracker, flags)
    return appendices_as_chapters(appendices, context)


def appendices_as_chapters(
    appendices: list[Appendix], context: RenderingContext
) -> list[DocumentChapter]:
    return [
        DocumentChapter(
            title=appendix.title,
            kind="appendix",
            identifier=None,
            label=appendix.label,
            body=render_models(appendix.kind, appendix.items, context, barriers=True),
        )
        for appendix in appendices
    ]


def render_models(
    kind: str,
    items: Sequence[Any],
    context: RenderingContext,
    *,
    barriers: bool = False,
) -> str:
    """Creatures, items or spells through their render macros.

    ``barriers`` adds a float barrier every ten items and at the end, for
    appendices of statblocks.
    """
    if kind not in CONTENT_TITLES:
        raise ValueError(f"Cannot render {kind} content in a document")
    # Spells and items nest their headings deeper; creatures take the document's
    content_type = kind if kind in ("spell", "item") else None
    context = replace(context, style=replace(context.style, content_type=content_type))
    template = environment().get_template("_content.tex.j2")
    return template.render(
        kind=kind, items=items, barriers=barriers, rendering_context=context
    ).strip()

"""Reading tools: a book or adventure's table of contents, then one section at a time."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Annotated, Any

from fastmcp.dependencies import Depends
from fastmcp.exceptions import ToolError
from pydantic import Field

from studiorum.core.models.adventures import Adventure
from studiorum.core.models.books import Book
from studiorum.core.models.content import ContentType
from studiorum.mcp import markdown
from studiorum.mcp.deps import get_services
from studiorum.mcp.errors import not_found
from studiorum.mcp.models import Contents, SectionRef, SectionText
from studiorum.services import Services

PAGE_CHARS = 24_000

Publication = Annotated[
    str, Field(description="A book or adventure id from list_publications, e.g. LMoP")
]

type Node = dict[str, Any]


async def get_table_of_contents(
    publication: Publication,
    section_id: Annotated[
        str | None, Field(description="List inside this section; else the whole")
    ] = None,
    depth: Annotated[int, Field(ge=1, le=4, description="Levels of sections")] = 1,
    services: Services = Depends(get_services),
) -> Contents:
    """The chapters and sections of a book or adventure, with ids for read_section.

    Each section's size is in Markdown characters; read_section returns up to
    24,000 a page.
    """
    pub = _publication(services, publication)
    lifted: set[str] = set()
    if section_id is None:
        roots = []
        for chapter in _chapters(pub):
            # 5etools shows a section nested in a chapter at the chapter's level
            nested = [n for n in _subsections(chapter) if n.get("type") == "section"]
            lifted |= {str(n["id"]) for n in nested}
            roots += [chapter, *nested]
    else:
        roots = _subsections(_find(pub, _chapters(pub), section_id)[0])
    return Contents(
        id=pub.source.abbreviation,
        name=pub.name,
        kind="book" if isinstance(pub, Book) else "adventure",
        sections=[
            SectionRef(id=n["id"], name=_name(n), depth=d, chars=_chars(n))
            for n, d in _walk(roots, depth, lifted)
        ],
    )


async def read_section(
    publication: Publication,
    section_id: Annotated[str, Field(description="An id from get_table_of_contents")],
    page: Annotated[int, Field(ge=1)] = 1,
    services: Services = Depends(get_services),
) -> SectionText:
    """One chapter or section as Markdown, with its subsections' ids.

    Tags such as {@creature goblin} are reduced to their text, and statblocks
    to a line naming the creature; get_content returns one in full. A section
    too long for one page comes in pages; a subsection too long for a page is
    left as a pointer to read on its own.
    """
    pub = _publication(services, publication)
    node, path = _find(pub, _chapters(pub), section_id)
    pages = _pages(node)
    if page > len(pages):
        raise ToolError(f"Section {section_id} has {len(pages)} page(s).")
    return SectionText(
        publication=pub.source.abbreviation,
        id=section_id,
        name=_name(node),
        path=path,
        page=page,
        pages=len(pages),
        text=pages[page - 1],
        sections=[
            SectionRef(id=n["id"], name=_name(n), depth=1, chars=_chars(n))
            for n in _subsections(node)
        ],
    )


def _publication(services: Services, wanted: str) -> Adventure | Book:
    omnidexer = services.omnidexer
    found = [
        p
        for ctype in (ContentType.ADVENTURE, ContentType.BOOK)
        for p in omnidexer.get_all_by_type(ctype)
        if isinstance(p, Adventure | Book)
    ]
    key = wanted.lower()
    for p in found:
        if key in (p.source.abbreviation.lower(), (p.id or "").lower(), p.name.lower()):
            hydrated = omnidexer.hydrate(p)
            return hydrated if isinstance(hydrated, Adventure | Book) else p
    raise not_found(
        "book or adventure",
        wanted,
        [p.source.abbreviation for p in found] + [p.name for p in found],
    )


def _chapters(pub: Adventure | Book) -> list[Node]:
    """Chapters as 5etools sections; the merge keeps each one's id in its ordinal."""
    return [
        {
            "id": str((c.ordinal or {}).get("identifier", f"ch{i}")),
            "name": c.name,
            "entries": c.entries,
        }
        for i, c in enumerate(pub.contents)
    ]


def _subsections(node: Node) -> list[Node]:
    """The nearest named entries with an id under a node, in order."""
    found: list[Node] = []

    def visit(entry: Any) -> None:
        if not isinstance(entry, dict):
            return
        if entry.get("id") and entry.get("name") and entry is not node:
            found.append(entry)
            return
        for key in ("entries", "items"):
            for child in entry.get(key) or []:
                visit(child)

    visit(node)
    return found


def _walk(
    roots: list[Node], depth: int, skip: set[str], level: int = 1
) -> Iterator[tuple[Node, int]]:
    for node in roots:
        yield node, level
        if level < depth:
            children = [n for n in _subsections(node) if str(n["id"]) not in skip]
            yield from _walk(children, depth, skip, level + 1)


def _find(
    pub: Adventure | Book, roots: list[Node], wanted: str
) -> tuple[Node, list[str]]:
    """The node with this id and the names of the sections around it."""

    def search(nodes: list[Node], path: list[str]) -> tuple[Node, list[str]] | None:
        for node in nodes:
            if str(node["id"]) == wanted:
                return node, path
            if hit := search(_subsections(node), [*path, _name(node)]):
                return hit
        return None

    if hit := search(roots, []):
        return hit
    raise ToolError(
        f"No section {wanted!r} in {pub.source.abbreviation}; "
        "get_table_of_contents lists the ids."
    )


def _pages(node: Node) -> list[str]:
    parts = [f"# {_name(node)}"]
    for child in node.get("entries", []):
        block = markdown.render(child, 2)
        if not block:
            continue
        if len(block) <= PAGE_CHARS:
            parts.append(block)
        elif isinstance(child, dict) and child.get("id") and child.get("name"):
            parts.append(
                f"## {_name(child)}\n\n*[Section {child['id']}, {_chars(child):,} "
                "characters: read it with read_section.]*"
            )
        else:
            parts += _split(block)
    pages, current = [], ""
    for part in parts:
        if current and len(current) + len(part) + 2 > PAGE_CHARS:
            pages.append(current)
            current = ""
        current = f"{current}\n\n{part}" if current else part
    return [*pages, current] if current else pages or [""]


def _split(block: str) -> list[str]:
    """A block too long for a page, in paragraphs, and long paragraphs in pieces."""
    return [
        para[i : i + PAGE_CHARS]
        for para in block.split("\n\n")
        for i in range(0, len(para), PAGE_CHARS)
    ]


def _name(node: Node) -> str:
    return markdown.strip_tags(str(node.get("name", "")))


def _chars(node: Node) -> int:
    return len(markdown.render(node))

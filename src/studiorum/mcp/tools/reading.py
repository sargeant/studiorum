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
from studiorum.mcp.models import (
    Contents,
    Reference,
    SectionMatch,
    SectionMatches,
    SectionRef,
    SectionText,
)
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
    roots = _chapters(pub)
    if section_id is not None:
        roots = _subsections(_find(pub, roots, section_id)[0])
    return Contents(
        id=_pub_id(pub),
        name=pub.name,
        kind="book" if isinstance(pub, Book) else "adventure",
        sections=[
            SectionRef(
                id=n["id"],
                name=_name(n),
                depth=d,
                chars=_chars(n),
                statblocks=_statblocks(n),
            )
            for n, d in _walk(roots, depth)
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
        publication=_pub_id(pub),
        id=section_id,
        name=_name(node),
        path=path,
        page=page,
        pages=len(pages),
        text=pages[page - 1][0],
        references=[Reference(**r) for r in markdown.references(pages[page - 1][1])],
        sections=[
            SectionRef(id=n["id"], name=_name(n), depth=1, chars=_chars(n))
            for n in _subsections(node)
        ],
    )


async def search_publication(
    publication: Publication,
    query: Annotated[
        str,
        Field(min_length=2, description="Words to find in a section's name or text"),
    ],
    limit: Annotated[int, Field(ge=1, le=50)] = 10,
    offset: Annotated[
        int, Field(ge=0, description="Skip this many matches, to page")
    ] = 0,
    services: Services = Depends(get_services),
) -> SectionMatches:
    """Find the sections of a book or adventure that mention something, for read_section.

    Every word must appear in the section's name or its own text (not its
    subsections'). Sections named for the words come first, then the rest in
    book order.
    """
    pub = _publication(services, publication)
    words = query.lower().split()
    named: list[SectionMatch] = []
    mentioned: list[SectionMatch] = []
    for node, path in _every_section(_chapters(pub)):
        name = _name(node).lower()
        text = markdown.render(_own(node))
        if not all(w in name or w in text.lower() for w in words):
            continue
        match = SectionMatch(
            id=str(node["id"]),
            name=_name(node),
            path=path,
            chars=_chars(node),
            snippet=markdown.snippet(text, words),
        )
        (named if all(w in name for w in words) else mentioned).append(match)
    found = named + mentioned
    return SectionMatches(
        publication=_pub_id(pub),
        total=len(found),
        results=found[offset : offset + limit],
    )


def _every_section(
    nodes: list[Node], path: list[str] | None = None
) -> Iterator[tuple[Node, list[str]]]:
    for node in nodes:
        yield node, path or []
        yield from _every_section(_subsections(node), [*(path or []), _name(node)])


def _own(node: Node) -> Node:
    """A section without its subsections, which are searched on their own."""

    def prune(entry: Any) -> Any:
        if not isinstance(entry, dict):
            return entry
        if entry is not node and entry.get("id") and entry.get("name"):
            return None
        out = dict(entry)
        for key in ("entries", "items"):
            if isinstance(entry.get(key), list):
                out[key] = [c for c in map(prune, entry[key]) if c is not None]
        return out

    return prune(node)


def _publication(services: Services, wanted: str) -> Adventure | Book:
    omnidexer = services.omnidexer
    found = [
        p
        for ctype in (ContentType.ADVENTURE, ContentType.BOOK)
        for p in omnidexer.get_all_by_type(ctype)
        if isinstance(p, Adventure | Book)
    ]
    key = wanted.lower()
    # An adventure can share its source with a book (MOT-NSS in MOT), so ids come first
    for field in (_pub_id, lambda p: p.name, lambda p: p.source.abbreviation):
        for p in found:
            if field(p).lower() == key:
                hydrated = omnidexer.hydrate(p)
                return hydrated if isinstance(hydrated, Adventure | Book) else p
    raise not_found(
        "book or adventure",
        wanted,
        [_pub_id(p) for p in found] + [p.name for p in found],
    )


def _pub_id(pub: Adventure | Book) -> str:
    """The id list_publications gives: 5etools' id, else the source."""
    return pub.id or pub.source.abbreviation


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


def _walk(roots: list[Node], depth: int, level: int = 1) -> Iterator[tuple[Node, int]]:
    for node in roots:
        yield node, level
        if level < depth:
            yield from _walk(_subsections(node), depth, level + 1)


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
        f"No section {wanted!r} in {_pub_id(pub)}; get_table_of_contents lists the ids."
    )


def _pages(node: Node) -> list[tuple[str, list[Any]]]:
    """Pages of Markdown, each with the 5etools data it came from (for references)."""
    parts: list[tuple[str, Any]] = [(f"# {_name(node)}", None)]
    for child in node.get("entries", []):
        block = markdown.render(child, 2)
        if not block:
            continue
        if len(block) <= PAGE_CHARS:
            parts.append((block, child))
        elif isinstance(child, dict) and child.get("id") and child.get("name"):
            pointer = (
                f"## {_name(child)}\n\n*[Section {child['id']}, {_chars(child):,} "
                "characters: read it with read_section.]*"
            )
            # Read as an area link, so the subsection shows up in references
            parts.append((pointer, f"{{@area {child['name']}|{child['id']}}}"))
        else:
            pieces = _split(block)
            parts += [(pieces[0], child), *((p, None) for p in pieces[1:])]
    pages: list[tuple[str, list[Any]]] = []
    current = ""
    sources: list[Any] = []
    for text, source in parts:
        if current and len(current) + len(text) + 2 > PAGE_CHARS:
            pages.append((current, sources))
            current, sources = "", []
        current = f"{current}\n\n{text}" if current else text
        if source is not None:
            sources.append(source)
    return [*pages, (current, sources)] if current else pages or [("", [])]


def _split(block: str) -> list[str]:
    """A block too long for a page, in paragraphs, and long paragraphs in pieces."""
    return [
        para[i : i + PAGE_CHARS]
        for para in block.split("\n\n")
        for i in range(0, len(para), PAGE_CHARS)
    ]


def _statblocks(node: Node) -> list[str] | None:
    """The statblocks a section holds, if it holds nothing else but images."""
    names: list[str] = []

    def only_statblocks(entry: Any) -> bool:
        if isinstance(entry, dict):
            if entry.get("type") == "statblock":
                if not str(entry.get("prop", "")).endswith("Fluff"):
                    names.append(str(entry.get("name", "")))
                return True
            if entry.get("type") in ("image", "gallery"):
                return True
            children = entry.get("entries")
            return isinstance(children, list) and all(map(only_statblocks, children))
        return False

    return list(dict.fromkeys(names)) if only_statblocks(node) and names else None


def _name(node: Node) -> str:
    return markdown.strip_tags(str(node.get("name", "")))


def _chars(node: Node) -> int:
    return len(markdown.render(node))

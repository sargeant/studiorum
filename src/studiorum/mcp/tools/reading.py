"""Reading tools: a book or adventure's table of contents, then one section at a time."""

from __future__ import annotations

import re
from collections.abc import Iterator
from functools import cached_property
from typing import Annotated, Any
from weakref import WeakKeyDictionary

from fastmcp.dependencies import Depends
from pydantic import Field

from studiorum.data.catalogue import Catalogue
from studiorum.data.models.adventures import Adventure
from studiorum.data.models.books import Book
from studiorum.data.models.content import ContentType
from studiorum.data.models.content_models import FLUFF_TYPES, content_type_of
from studiorum.data.statblocks import find_statblock, statblock_type
from studiorum.mcp import markdown
from studiorum.mcp.deps import get_services
from studiorum.mcp.errors import ClientError, not_found
from studiorum.mcp.layouts import entry_data, to_markdown
from studiorum.mcp.models import (
    PAGE_CHARS,
    Contents,
    SectionMatch,
    SectionMatches,
    SectionRef,
    SectionText,
    next_offset,
)
from studiorum.mcp.text import fold
from studiorum.mcp.tools.lookup import resolve_references
from studiorum.services import Services

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
    limit: Annotated[int, Field(ge=1, le=500)] = 100,
    offset: Annotated[
        int, Field(ge=0, description="Skip this many sections, to page")
    ] = 0,
    services: Services = Depends(get_services),
) -> Contents:
    """The chapters and sections of a book or adventure, with ids for read_section.

    Each section's size is in Markdown characters; read_section returns up to
    24,000 a page. A deep listing of a long book comes in pages of limit
    sections; section_id lists one part instead.
    """
    pub = _publication(services, publication)
    roots = _chapters(pub)
    if section_id is not None:
        roots = _subsections(_find(pub, roots, section_id)[0])
    walked = list(_walk(roots, depth))
    return Contents(
        id=_pub_id(pub),
        name=pub.name,
        kind="book" if isinstance(pub, Book) else "adventure",
        total=len(walked),
        next_offset=next_offset(len(walked), offset, limit),
        sections=[
            SectionRef(
                id=n["id"],
                name=_name(n),
                depth=d,
                chars=_chars(n),
                statblocks=_statblocks(n),
            )
            for n, d in walked[offset : offset + limit]
        ],
    )


async def read_section(
    publication: Publication,
    section_id: Annotated[str, Field(description="An id from get_table_of_contents")],
    page: Annotated[
        int, Field(ge=1, description="A page of text, from 1; the reply gives pages")
    ] = 1,
    expand_statblocks: Annotated[
        bool,
        Field(
            description="Each statblock in full, as get_content lays it out, "
            "instead of a line naming it; the section may take more pages"
        ),
    ] = False,
    include_references: Annotated[
        bool | None,
        Field(
            description="List what the page links to: entries to read with "
            "get_content, sections with read_section. "
            "Default: true, but false with expand_statblocks, whose text holds them"
        ),
    ] = None,
    services: Services = Depends(get_services),
) -> SectionText:
    """One chapter or section as Markdown, with its subsections' ids.

    Tags such as {@creature goblin} are reduced to their text, and statblocks
    to a line naming the creature (get_content returns one in full) unless
    expand_statblocks. A section too long for one page comes in pages; a
    subsection too long for a page is left as a pointer to read on its own.
    """
    pub = _publication(services, publication)
    node, path = _find(pub, _chapters(pub), section_id)
    pages, pointed = _pages(_expanded(services, node) if expand_statblocks else node)
    if page > len(pages):
        raise ClientError(f"Section {section_id} has {len(pages)} page(s).")
    if include_references is None:
        include_references = not expand_statblocks
    return SectionText(
        publication=_pub_id(pub),
        id=section_id,
        name=_name(node),
        path=path,
        page=page,
        pages=len(pages),
        text=pages[page - 1][0],
        references=resolve_references(services, markdown.references(pages[page - 1][1]))
        if include_references
        else [],
        sections=[
            SectionRef(id=n["id"], name=_name(n), depth=1, chars=_chars(n))
            for n in _subsections(node)
            if str(n["id"]) in pointed
        ],
    )


async def search_publication(
    query: Annotated[
        str,
        Field(min_length=2, description="Words to find in a section's name or text"),
    ],
    publication: Annotated[
        str | None,
        Field(description="A book or adventure id, e.g. LMoP; else every one"),
    ] = None,
    names_only: Annotated[
        bool,
        Field(
            description="Match section names only, not their text; "
            "results then leave out snippet and chars"
        ),
    ] = False,
    limit: Annotated[int, Field(ge=1, le=50)] = 10,
    offset: Annotated[
        int, Field(ge=0, description="Skip this many matches, to page")
    ] = 0,
    services: Services = Depends(get_services),
) -> SectionMatches:
    """Find the sections of books and adventures that mention something, for read_section.

    Every word must appear in the section's name or its own text (not its
    subsections'), even inside a longer word. Sections named exactly the
    query come first, then names holding the words whole, then other names;
    then sections with a statblock named the query, then a heading or table
    cell named it, then whole words in the text, then parts of words. Ties go in book order,
    oldest publication first.
    """
    pubs = (
        [_publication(services, publication)]
        if publication
        else _publications(services)
    )
    words = fold(query).split()
    ranked = [
        (rank, section)
        for pub in pubs
        for section in _sections(services, pub)
        if (rank := _rank(section, words, names_only)) is not None
    ]
    # Stable, so book order breaks ties
    ranked.sort(key=lambda r: r[0])
    found = [section for _, section in ranked]
    return SectionMatches(
        publication=_pub_id(pubs[0]) if publication else None,
        total=len(found),
        next_offset=next_offset(len(found), offset, limit),
        results=[
            SectionMatch(
                publication=s.publication,
                id=str(s.node["id"]),
                name=s.name,
                path=s.path,
                chars=None if names_only else _chars(s.node),
                snippet=None if names_only else markdown.snippet(s.text, words),
            )
            for s in found[offset : offset + limit]
        ],
    )


def _rank(section: _Section, words: list[str], names_only: bool) -> int | None:
    """How well a section matches, best 0; None if it doesn't."""
    name = fold(section.name)
    if all(w in name for w in words):
        if _plain(section.name) == " ".join(words):
            return 0
        return 1 if all(_whole(w, name) for w in words) else 2
    if names_only:
        return None
    text = fold(section.text)
    if not all(w in name or w in text for w in words):
        return None
    phrase = " ".join(words)
    if phrase in section.statblock_names:
        return 3
    if phrase in section.inner_names:
        return 4
    return 5 if all(_whole(w, name) or _whole(w, text) for w in words) else 6


def _whole(word: str, text: str) -> bool:
    """Whether the word is in the text as a word of its own, or its plural."""
    return re.search(rf"\b{re.escape(word)}(?:e?s)?\b", text) is not None


def _plain(name: str) -> str:
    """A name without an area key ("15. ", "B12: ") or end punctuation, lower case."""
    name = re.sub(r"^[A-Z]{0,2}\d+[a-z]?[.:]\s+", "", name.strip())
    return " ".join(re.sub(r"^\W+|\W+$", "", fold(name)).split())


class _Section:
    """A section with an id, and its own text as Markdown once asked for."""

    def __init__(self, publication: str, node: Node, path: list[str]) -> None:
        self.publication = publication
        self.node = node
        self.path = path
        self.name = _name(node)

    @cached_property
    def text(self) -> str:
        return markdown.render(_own(self.node))

    @cached_property
    def statblock_names(self) -> set[str]:
        """The names of the statblocks in its own text."""
        found: set[str] = set()

        def visit(entry: Any) -> None:
            if isinstance(entry, list):
                for e in entry:
                    visit(e)
            elif isinstance(entry, dict):
                if entry.get("type") == "statblock" and entry.get("name"):
                    found.add(_plain(markdown.strip_tags(str(entry["name"]))))
                for key in ("entries", "items"):
                    visit(entry.get(key))

        visit(_own(self.node))
        return found

    @cached_property
    def inner_names(self) -> set[str]:
        """The names of the headings, statblocks and table cells in its own text."""
        found: set[str] = set()

        def visit(entry: Any, cell: bool = False) -> None:
            if isinstance(entry, list):
                for e in entry:
                    visit(e, cell)
            elif isinstance(entry, dict):
                if entry is not self.node and entry.get("name"):
                    found.add(_plain(markdown.strip_tags(str(entry["name"]))))
                for key in ("entries", "items"):
                    visit(entry.get(key))
                visit(entry.get("rows"), cell=True)
            elif cell and isinstance(entry, str):
                found.add(_plain(markdown.strip_tags(entry)))

        visit(_own(self.node))
        return found


# Per catalogue, each publication's sections, so later searches skip rendering
_SECTIONS: WeakKeyDictionary[Catalogue, dict[str, list[_Section]]] = WeakKeyDictionary()


def _sections(services: Services, pub: Adventure | Book) -> list[_Section]:
    by_pub = _SECTIONS.setdefault(services.catalogue, {})
    key = _pub_id(pub)
    if key not in by_pub:
        by_pub[key] = [
            _Section(key, node, path) for node, path in _every_section(_chapters(pub))
        ]
    return by_pub[key]


def _expanded(services: Services, node: Node) -> Node:
    """A copy of a section with each statblock laid out as get_content does.

    Lore (fluff) and statblocks that name nothing loaded stay as they are.
    """

    def expand(entry: Any) -> Any:
        if isinstance(entry, list):
            return [expand(e) for e in entry]
        if not isinstance(entry, dict):
            return entry
        if entry.get("type") == "statblock":
            return _statblock_markdown(services, entry) or entry
        return {k: expand(v) for k, v in entry.items()}

    expanded: Node = expand(node)
    return expanded


def _statblock_markdown(services: Services, entry: Node) -> Node | None:
    """A statblock as Markdown, keeping the entry and its data for references."""
    content_type = statblock_type(entry)
    if content_type is None or content_type in FLUFF_TYPES:
        return None
    found = find_statblock(services.catalogue, entry, content_type)
    if found is None:
        return None
    data = entry_data(found)
    if entry.get("displayName"):
        data["name"] = entry["displayName"]
    return {
        "type": "studiorumMarkdown",
        "markdown": to_markdown(content_type_of(found).value, data),
        "statblock": entry,
        "data": data,
    }


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


def _publications(services: Services) -> list[Adventure | Book]:
    """Every book and adventure with its text, oldest first."""
    catalogue = services.catalogue
    found = sorted(
        (
            p
            for ctype in (ContentType.ADVENTURE, ContentType.BOOK)
            for p in catalogue.get_all_by_type(ctype)
            if isinstance(p, Adventure | Book)
        ),
        key=lambda p: (p.published or "", p.name),
    )
    hydrated = [catalogue.hydrate(p) for p in found]
    return [
        h if isinstance(h, Adventure | Book) else p
        for h, p in zip(hydrated, found, strict=True)
    ]


def _publication(services: Services, wanted: str) -> Adventure | Book:
    catalogue = services.catalogue
    found = [
        p
        for ctype in (ContentType.ADVENTURE, ContentType.BOOK)
        for p in catalogue.get_all_by_type(ctype)
        if isinstance(p, Adventure | Book)
    ]
    key = wanted.lower()
    # An adventure can share its source with a book (MOT-NSS in MOT), so ids come first
    for field in (_pub_id, lambda p: p.name, lambda p: p.source.abbreviation):
        for p in found:
            if field(p).lower() == key:
                hydrated = catalogue.hydrate(p)
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
    """Chapters as 5etools sections, with the id of each one's section."""
    return [
        {
            "id": c.id or f"ch{i}",
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
    raise ClientError(
        f"No section {wanted!r} in {_pub_id(pub)}; get_table_of_contents lists the ids."
    )


def _pages(node: Node) -> tuple[list[tuple[str, list[Any]]], set[str]]:
    """Pages of Markdown, each with the 5etools data it came from (for references).

    Also the ids of the subsections too long to hold, which the pages point to.
    """
    parts: list[tuple[str, Any]] = [(f"# {_name(node)}", None)]
    pointed: set[str] = set()
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
            pointed.add(str(child["id"]))
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
    return [*pages, (current, sources)] if current else pages or [("", [])], pointed


def _split(block: str) -> list[str]:
    """A block too long for a page, in paragraphs, and long paragraphs in pieces."""
    return [
        para[i : i + PAGE_CHARS]
        for para in block.split("\n\n")
        for i in range(0, len(para), PAGE_CHARS)
    ]


def _statblocks(node: Node) -> list[str]:
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

    return list(dict.fromkeys(names)) if only_statblocks(node) else []


def _name(node: Node) -> str:
    return markdown.strip_tags(str(node.get("name", "")))


def _chars(node: Node) -> int:
    return len(markdown.render(node))

"""Merge an adventure's or book's metadata with the text from its content file.

``adventures.json`` and ``books.json`` hold each adventure's and book's
metadata and table of contents; ``adventure/adventure-<id>.json`` and
``book/book-<id>.json`` hold the sections. These functions combine the two.
"""

from __future__ import annotations

from typing import Any

_BOOK_KEYS = ("published", "isbn", "image", "tags")


def merge_metadata_content(
    metadata: dict[str, Any], content: dict[str, Any] | None
) -> dict[str, Any]:
    """The metadata with its ``contents`` filled from ``content["data"]``."""
    sections = (content or {}).get("data")
    if not isinstance(sections, list):
        return _metadata_only(metadata)
    if _is_book(metadata):
        return _merge_book(metadata, sections)

    by_name = {
        section.get("name", ""): section
        for section in sections
        if isinstance(section, dict) and section.get("type") == "section"
    }
    matched: set[str] = set()
    merged_contents = []
    for chapter in metadata.get("contents", []):
        if not isinstance(chapter, dict):
            continue
        name = chapter.get("name", "")
        match, matched_name = by_name.get(name), name
        ordinal = chapter.get("ordinal")
        if (
            match is None
            and isinstance(ordinal, dict)
            and ordinal.get("type") == "appendix"
        ):
            matched_name = f"Appendix {ordinal.get('identifier', '')}: {name}"
            match = by_name.get(matched_name)
        # Chapters with no text are left out rather than rendered empty
        if match is not None:
            merged = dict(chapter)
            merged["entries"] = match.get("entries", [])
            if "id" in match:
                merged["ordinal"] = {"type": "section", "identifier": match["id"]}
            merged_contents.append(merged)
            matched.add(matched_name)

    for name, section in by_name.items():
        if name not in matched:
            extra: dict[str, Any] = {
                "name": name,
                "entries": section.get("entries", []),
            }
            if "id" in section:
                extra["ordinal"] = {"type": "section", "identifier": section["id"]}
            merged_contents.append(extra)

    return {**metadata, "contents": merged_contents}


def _metadata_only(metadata: dict[str, Any]) -> dict[str, Any]:
    contents = [
        {**chapter, "entries": []}
        for chapter in metadata.get("contents", [])
        if isinstance(chapter, dict)
    ]
    return {**metadata, "contents": contents}


def _is_book(metadata: dict[str, Any]) -> bool:
    """Adventures have a level or storyline; books have an author and contents."""
    if "level" in metadata or "storyline" in metadata:
        return False
    return bool(metadata.get("contents")) and "author" in metadata


def _merge_book(metadata: dict[str, Any], sections: list[Any]) -> dict[str, Any]:
    """Books take their chapters straight from the content file's sections."""
    book: dict[str, Any] = {
        "name": metadata.get("name", "Unknown Book"),
        "source": metadata.get("source", "Unknown"),
        "id": metadata.get("id", "unknown"),
    }
    book.update({k: metadata[k] for k in _BOOK_KEYS if k in metadata})
    chapters = []
    for section in sections:
        if isinstance(section, dict) and section.get("type") == "section":
            chapter: dict[str, Any] = {
                "name": section.get("name", "Unnamed Chapter"),
                "entries": section.get("entries", []),
            }
            if "id" in section:
                chapter["ordinal"] = {"type": "section", "identifier": section["id"]}
            if "page" in section:
                chapter["page"] = section["page"]
            chapters.append(chapter)
    book["contents"] = chapters
    return book

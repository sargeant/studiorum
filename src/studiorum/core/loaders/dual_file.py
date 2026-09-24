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

    chapters = [c for c in metadata.get("contents", []) if isinstance(c, dict)]
    if len(chapters) != len(sections):
        chapters = [{} for _ in sections]
    # 5etools pairs contents[i] with data[i]; the text's own name is the fallback
    merged_contents = []
    for chapter, section in zip(chapters, sections, strict=True):
        if not isinstance(section, dict):
            continue
        merged = dict(chapter)
        merged.setdefault("name", section.get("name", "Unnamed Chapter"))
        merged["entries"] = (
            section.get("entries", [])
            if section.get("type") == "section"
            else [section]
        )
        if "id" in section:
            merged["ordinal"] = {"type": "section", "identifier": section["id"]}
        merged_contents.append(merged)

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

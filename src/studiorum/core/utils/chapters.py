"""Chapter filtering utilities for adventures and books."""

import re
from typing import Any

from studiorum.core.models.adventures import Adventure, AdventureMetadata
from studiorum.core.models.chapter import Chapter, ChapterType


def extract_chapter_number(chapter: Chapter) -> int | None:
    """Extract chapter number from Chapter object.

    Uses structured ordinal field first, falls back to name regex.

    Args:
        chapter: Chapter object from Adventure

    Returns:
        Chapter number or None if not a numbered chapter

    Examples:
        >>> ch = Chapter(name="Chapter 5: Title", ordinal=None, entries=[])
        >>> extract_chapter_number(ch)
        5
        >>> ch = Chapter(name="Introduction", ordinal=None, entries=[])
        >>> extract_chapter_number(ch)
        None
    """
    if chapter.ordinal and isinstance(chapter.ordinal, dict):
        if chapter.ordinal.get("type") == "chapter":
            identifier = chapter.ordinal.get("identifier")
            if identifier:
                try:
                    return int(identifier)
                except (ValueError, TypeError):
                    pass

    pattern = r"(?:Chapter|Ch\.?)\s*(\d+):"
    match = re.search(pattern, chapter.name, re.IGNORECASE)
    if match:
        return int(match.group(1))

    return None


def parse_chapter_spec(spec: str) -> list[int]:
    """Parse chapter specification like '1,5,8-9' into sorted list of chapter numbers.

    User-specified order is ignored; output is always sorted for determinism.

    Args:
        spec: Chapter specification string

    Returns:
        Sorted list of chapter numbers

    Raises:
        ValueError: If specification is invalid

    Examples:
        >>> parse_chapter_spec("5")
        [5]
        >>> parse_chapter_spec("4,6,3")
        [3, 4, 6]
        >>> parse_chapter_spec("1,5,8-9")
        [1, 5, 8, 9]
    """
    chapters: set[int] = set()

    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue

        if "-" in part:
            try:
                start, end = part.split("-", 1)
                start_num = int(start.strip())
                end_num = int(end.strip())
                if start_num > end_num:
                    raise ValueError(
                        f"Invalid range '{part}': start ({start_num}) > end ({end_num})"
                    )
                chapters.update(range(start_num, end_num + 1))
            except ValueError as e:
                if "invalid literal" in str(e):
                    raise ValueError(f"Invalid range '{part}': must be numeric")
                raise
        else:
            try:
                chapters.add(int(part))
            except ValueError:
                raise ValueError(f"Invalid chapter number '{part}': must be an integer")

    if not chapters:
        raise ValueError("No valid chapter numbers provided")

    return sorted(chapters)


def filter_adventure_chapters(
    adventure: Adventure,
    chapter_numbers: list[int],
    include_introduction: bool = False,
) -> tuple[Adventure, list[str]]:
    """Filter adventure to only specified chapters.

    Returns data + warnings (no printing); caller handles display.

    Args:
        adventure: Full adventure object
        chapter_numbers: Sorted list of chapter numbers to include
        include_introduction: If True, include introduction chapters

    Returns:
        Tuple of (filtered_adventure, warnings)

    Raises:
        ValueError: If no matching chapters found
    """
    chapter_map: dict[int, tuple[int, int]] = {}
    introduction_indices: list[int] = []

    for idx, chapter in enumerate(adventure.contents):
        chapter_num = extract_chapter_number(chapter)
        if chapter_num is not None:
            chapter_map[chapter_num] = (idx, chapter_num)
        else:
            chapter_type = chapter.get_chapter_type()
            if chapter_type == ChapterType.INTRODUCTION:
                introduction_indices.append(idx)

    filtered_data: list[tuple[int, Chapter, int | None]] = []
    missing_chapters = []

    for num in chapter_numbers:
        if num in chapter_map:
            idx, original_num = chapter_map[num]
            filtered_data.append((idx, adventure.contents[idx], original_num))
        else:
            missing_chapters.append(num)

    if include_introduction:
        for idx in introduction_indices:
            filtered_data.insert(0, (idx, adventure.contents[idx], None))

    if not filtered_data:
        available = sorted(chapter_map.keys())
        raise ValueError(
            f"No chapters found matching: {chapter_numbers}. "
            f"Available numbered chapters: {available}"
        )

    warnings = []
    if missing_chapters:
        available = sorted(chapter_map.keys())
        warnings.append(
            f"Chapters not found: {missing_chapters}. Available: {available}"
        )

    filtered_data.sort(key=lambda x: x[0])

    filtered_adventure = adventure.model_copy(deep=True)
    filtered_adventure.contents = [chapter for _, chapter, _ in filtered_data]

    chapter_number_map: dict[int, int] = {}
    for new_idx, item in enumerate(filtered_data):
        chapter_num_value: int | None = item[2]
        if chapter_num_value is not None:
            chapter_number_map[new_idx] = chapter_num_value

    if not filtered_adventure.metadata:
        filtered_adventure.metadata = AdventureMetadata()

    filtered_adventure.metadata.custom_fields["chapter_number_map"] = chapter_number_map

    return filtered_adventure, warnings

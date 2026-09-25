"""Chapter filtering utilities for adventures and books."""

from collections import Counter

from studiorum.core.models.adventures import Adventure
from studiorum.core.models.chapter import NUMBERED_KINDS, Chapter, OrdinalType


def numbered_kind(chapters: list[Chapter]) -> OrdinalType | None:
    """The numbered ordinal type the chapters use most, such as OoW's episodes."""
    counts: Counter[OrdinalType] = Counter(
        c.ordinal.type
        for c in chapters
        if c.ordinal is not None and c.ordinal.type in NUMBERED_KINDS
    )
    if not counts:
        return None
    return max(NUMBERED_KINDS, key=counts.__getitem__)


def chapter_number(chapter: Chapter, kind: OrdinalType | None) -> int | None:
    """The chapter's number if its ordinal is of ``kind``."""
    if chapter.ordinal is None or chapter.ordinal.type != kind:
        return None
    identifier = chapter.ordinal.identifier
    if isinstance(identifier, int):
        return identifier
    return int(identifier) if identifier and identifier.isdigit() else None


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
    """The adventure with only the chosen chapters, and any warnings.

    Numbers match the identifiers of the numbered kind the adventure uses
    most (chapters, parts, episodes or levels). The introduction is the
    unnumbered chapters before the first numbered one. An adventure with no
    numbered chapters is numbered by position, with a warning.

    Raises:
        ValueError: If no chapter matches
    """
    contents = adventure.contents
    kind = numbered_kind(contents)
    chapter_map: dict[int, int] = {}
    for idx, chapter in enumerate(contents):
        number = chapter_number(chapter, kind)
        if number is not None:
            chapter_map.setdefault(number, idx)
    first = next((i for i, c in enumerate(contents) if c.ordinal is not None), 0)
    introduction_indices = list(range(first))

    warnings = []
    if not chapter_map and contents:
        chapter_map = {i + 1: i for i in range(len(contents))}
        introduction_indices = []
        warnings.append(
            "No numbered chapters detected; falling back to positional numbering "
            f"(1..{len(contents)}) based on chapter order."
        )

    indices = {chapter_map[n] for n in chapter_numbers if n in chapter_map}
    missing = [n for n in chapter_numbers if n not in chapter_map]
    if include_introduction:
        indices.update(introduction_indices)
    available = sorted(chapter_map)
    if not indices:
        raise ValueError(
            f"No chapters found matching: {chapter_numbers}. "
            f"Available numbered chapters: {available}"
        )
    if missing:
        warnings.append(f"Chapters not found: {missing}. Available: {available}")

    filtered = adventure.model_copy(deep=True)
    filtered.contents = [filtered.contents[i] for i in sorted(indices)]
    return filtered, warnings

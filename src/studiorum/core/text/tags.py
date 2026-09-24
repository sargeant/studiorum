"""Splitting 5etools ``{@tag ...}`` markup, ported from 5etools' ``js/render.js``.

``split_by_tags`` is ``Renderer.splitByTags`` and ``split_by_pipe`` is
``Renderer.splitTagByPipe``. ``display_part`` is the generic display text
rule of ``Renderer.stripTags``, for tags with no rule of their own.
"""

from __future__ import annotations

# Tags whose display text is the first part, and which part it is for the rest
_FIRST_PART = {
    "5etools", "5etoolsImg", "5etoolsAudio", "adventure", "book", "filter",
    "footnote", "link", "loader", "color", "highlight", "help", "note", "tip",
    "code", "kbd", "sup", "sub", "style", "font", "s", "strike", "s2",
    "strikeDouble", "u", "underline", "u2", "underlineDouble", "comic",
    "comicH1", "comicH2", "comicH3", "comicH4", "comicNote",
}  # fmt: skip
_DISPLAY_PART = {
    "card": 3,
    "deity": 3,
    "subclass": 4,
    "quickref": 4,
    "classFeature": 5,
    "subclassFeature": 7,
}


def split_by_tags(text: str) -> list[str]:
    """Plain runs and whole ``{@tag ...}`` runs, nested tags kept inside their parent."""
    out: list[str] = []
    current, depth, i = "", 0, 0
    while i < len(text):
        char = text[i]
        if char == "{" and text[i + 1 : i + 2] in ("@", "="):
            if depth == 0:
                if current:
                    out.append(current)
                current = ""
            depth += 1
            current += text[i : i + 2]
            i += 2
            continue
        current += char
        if char == "}" and depth and (depth := depth - 1) == 0:
            out.append(current)
            current = ""
        i += 1
    if current:
        out.append(current)
    return out


def split_by_pipe(text: str) -> list[str]:
    """Split a tag's arguments on ``|``, leaving pipes inside nested tags alone."""
    out: list[str] = []
    current, depth = "", 0
    for i, char in enumerate(text):
        if char == "{" and text[i + 1 : i + 2] == "@":
            depth += 1
        elif char == "}" and depth:
            depth -= 1
        elif char == "|" and not depth and text[i - 1 : i] != "\\":
            out.append(current)
            current = ""
            continue
        current += char
    if current:
        out.append(current)
    return out


def is_tag(part: str) -> bool:
    """Whether a ``split_by_tags`` part is a whole ``{@tag ...}``."""
    return part.startswith("{@") and part.endswith("}")


def split_tag(part: str) -> tuple[str, str]:
    """``{@creature goblin|MM}`` as ``("creature", "goblin|MM")``."""
    tag, _, args = part[2:-1].partition(" ")
    return tag, args


def display_part(tag: str, parts: list[str]) -> str:
    """The part 5etools shows for a tag with no display rule of its own."""
    first = parts[0] if parts else ""
    if tag in _FIRST_PART:
        return first
    index = _DISPLAY_PART.get(tag, 2)
    return parts[index] if len(parts) > index and parts[index] else first

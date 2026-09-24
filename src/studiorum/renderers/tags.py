"""5etools ``{@tag ...}`` markup as LaTeX.

``TAGS`` maps each tag name to a function from the tag's parts (its arguments
split on ``|``) to LaTeX. Display text is markup too, so functions render it
with ``Render.text``, which recurses. Any other tag renders its display text,
escaped, and a tag name 5etools doesn't have is logged once.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from studiorum.core.latex_utils import escape_latex_text
from studiorum.core.logging import get_logger
from studiorum.core.text.tags import (
    display_part,
    is_tag,
    plain_text,
    split_by_pipe,
    split_by_tags,
    split_tag,
)

if TYPE_CHECKING:
    from studiorum.core.references.content_tracker import ContentTracker

logger = get_logger(__name__)


@dataclass(frozen=True)
class Render:
    """What a tag function gets besides its parts."""

    tracker: ContentTracker | None = None

    def text(self, markup: str) -> str:
        return render(markup, self.tracker)

    def track(self, kind: str, name: str, source: str = "", page: str = "") -> None:
        if self.tracker is not None and name:
            self.tracker.add_content(
                kind, plain_text(name), source or None, page or None
            )


TagFn = Callable[[list[str], Render], str]


def render(text: str, tracker: ContentTracker | None = None) -> str:
    """LaTeX for a string of 5etools markup, tracking content it names."""
    if not text:
        return text
    context = Render(tracker)
    out = []
    for part in split_by_tags(text):
        if is_tag(part):
            tag, args = split_tag(part)
            parts = [p.strip() for p in split_by_pipe(args)] or [""]
            fn = TAGS.get(tag)
            out.append(fn(parts, context) if fn else _plain_tag(tag, parts, context))
        else:
            out.append(escape_latex_text(part))
    return "".join(out)


class TagResolver:
    """``render`` behind the interface the entry processor calls."""

    def process_text(self, text: str, context: Any = None) -> str:
        return render(text, getattr(context, "content_tracker", None))


def _part(parts: list[str], index: int) -> str:
    return parts[index] if len(parts) > index else ""


def _bold(latex: str) -> str:
    return f"\\textbf{{{latex}}}"


def _italic(latex: str) -> str:
    return f"\\textit{{{latex}}}"


def _int(value: str) -> int | None:
    try:
        return int(value)
    except ValueError:
        return None


# Content references and their style; the tag name is the kind tracked for appendices
_REFERENCES: dict[str, Callable[[str], str]] = {
    "creature": _bold,
    "class": _bold,
    "feat": _bold,
    "spell": _italic,
    "item": _italic,
    "action": _italic,
    "deck": _italic,
    "disease": _italic,
    "hazard": _italic,
    "recipe": _italic,
    "reward": _italic,
    "sense": _italic,
    "skill": _italic,
    "status": _italic,
    "background": str,
    "deity": str,
    "race": str,
    "table": str,
    "variantrule": str,
}


def _reference(tag: str, style: Callable[[str], str]) -> TagFn:
    def fn(parts: list[str], r: Render) -> str:
        r.track(tag, parts[0], _part(parts, 1), _part(parts, 3))
        return style(r.text(display_part(tag, parts)))

    return fn


def _condition(parts: list[str], r: Render) -> str:
    r.track("condition", parts[0])
    return r.text(display_part("condition", parts))


def _publication(tag: str) -> TagFn:
    def fn(parts: list[str], r: Render) -> str:
        r.track(tag, parts[0], _part(parts, 1))
        return r.text(parts[0])

    return fn


_DND = re.compile(r"^(Dungeons\s*\\?&\s*Dragons|D\\?&D)$", re.IGNORECASE)


def _format(style: Callable[[str], str], bold: bool = False) -> TagFn:
    def fn(parts: list[str], r: Render) -> str:
        content = (_part(parts, 2) or parts[0]).strip()
        if not content:
            return ""
        if bold and _DND.match(content):
            name = "Dungeons \\& Dragons" if len(content) > 4 else "d\\&d"
            return f"\\textsc{{{name}}}"
        return style(r.text(content))

    return fn


def _signed(value: str) -> str:
    number = _int(value)
    if number is not None:
        return f"{number:+d}"
    return value if value.startswith(("+", "-")) else f"+{value}"


def _roll(parts: list[str], r: Render) -> str:
    return escape_latex_text(_part(parts, 1) or parts[0].replace(";", "/"))


def _bonus(parts: list[str], r: Render) -> str:
    number = _int(parts[0])
    shown = _part(parts, 1) or (f"{number:+d}" if number is not None else parts[0])
    return escape_latex_text(shown)


def _ability(parts: list[str], r: Render) -> str:
    shown = _part(parts, 1)
    if shown:
        keep = shown.startswith(("+", "-")) or _int(shown) is None
        return escape_latex_text(shown if keep else _signed(shown))
    words = parts[0].split()
    score = _int(words[-1]) if len(words) >= 2 else None
    return _signed(str((score - 10) // 2)) if score is not None else "+0"


def _modifier(parts: list[str], r: Render) -> str:
    words = parts[0].split()
    number = _int(words[-1]) if len(words) >= 2 else None
    return f"{number:+d}" if number is not None else "+0"


def _chance(parts: list[str], r: Render) -> str:
    if not parts[0]:
        return "[Chance]"
    return escape_latex_text(_part(parts, 1) or f"{parts[0]} percent")


def _recharge(parts: list[str], r: Render) -> str:
    number = _int(parts[0] or "6")
    number = 6 if number is None else number
    shown = f"Recharge {number}--6" if number < 6 else f"Recharge {number}"
    return shown if "m" in _part(parts, 1) else f"({shown})"


_KINDS = {"m": "Melee", "r": "Ranged", "g": "Magical", "a": "Area"}
_METHODS = {"w": "Weapon", "s": "Spell", "p": "Power"}


def _attack(roll: bool) -> TagFn:
    def fn(parts: list[str], r: Render) -> str:
        groups = [list(g.strip()) for g in parts[0].lower().split(",") if g.strip()]
        # A letter shared with a later group is dropped: "mw,rw" is "Melee or Ranged Weapon"
        seen: set[str] = set(groups[-1]) if groups else set()
        for i in range(len(groups) - 2, -1, -1):
            kept = [c for c in groups[i] if c not in seen]
            seen.update(groups[i])
            groups[i] = kept
        names = []
        for group in groups:
            kind = next((_KINDS[c] for c in _KINDS if c in group), "")
            method = next((_METHODS[c] for c in _METHODS if c in group), "")
            names.append(" ".join(w for w in (kind, method) if w))
        label = "Attack Roll:" if roll else "Attack:"
        joined = " or ".join(names).strip()
        return f"{joined} {label}" if joined else label

    return fn


_ABILITIES = {
    "str": "Strength",
    "dex": "Dexterity",
    "con": "Constitution",
    "int": "Intelligence",
    "wis": "Wisdom",
    "cha": "Charisma",
}
_ORDINALS = [
    "First",
    "Second",
    "Third",
    "Fourth",
    "Fifth",
    "Sixth",
    "Seventh",
    "Eighth",
    "Ninth",
    "Tenth",
]


def _act_save(parts: list[str], r: Render) -> str:
    if not parts[0]:
        return _italic("Saving Throw:")
    ability = _ABILITIES.get(parts[0].lower(), parts[0].title())
    return _italic(escape_latex_text(f"{ability} Saving Throw:"))


def _act_save_fail(parts: list[str], r: Render) -> str:
    if not parts[0]:
        return _italic("Failure:")
    n = _int(parts[0])
    if n is not None:
        word = _ORDINALS[n - 1] if 1 <= n <= 10 else f"{n}th"
        return _italic(f"{word} Failure:")
    return _italic(escape_latex_text(f"{parts[0]} Failure:"))


def _act_save_fail_by(parts: list[str], r: Render) -> str:
    if not parts[0]:
        return _italic("Failure:")
    return _italic(escape_latex_text(f"Failure by {parts[0]} or More:"))


def _fixed(latex: str) -> TagFn:
    return lambda parts, r: latex


def _note(parts: list[str], r: Render) -> str:
    return _italic(r.text(parts[0])) if parts[0] else ""


def _link(parts: list[str], r: Render) -> str:
    title, url = parts[0], _part(parts, 1)
    if not (title and url):
        return escape_latex_text(title)
    url = url.replace("#", "\\#").replace("%", "\\%").replace("&", "\\&")
    return f"\\href{{{url}}}{{{escape_latex_text(title)}}}"


def _area(parts: list[str], r: Render) -> str:
    flags = _part(parts, 2)
    if "x" in flags:
        return r.text(parts[0])
    return f"{'A' if 'u' in flags else 'a'}rea {r.text(parts[0])}"


def _scaling(parts: list[str], r: Render) -> str:
    return escape_latex_text(_part(parts, 4) or _part(parts, 2))


def _default(text: str) -> TagFn:
    return lambda parts, r: r.text(parts[0]) if parts[0] else text


def _or(fallback: str) -> TagFn:
    return lambda parts, r: escape_latex_text(parts[0]) if parts[0] else fallback


TAGS: dict[str, TagFn] = {
    **{tag: _reference(tag, style) for tag, style in _REFERENCES.items()},
    "condition": _condition,
    "adventure": _publication("adventure"),
    "book": _publication("book"),
    "b": _format(_bold, bold=True),
    "bold": _format(_bold, bold=True),
    "i": _format(_italic),
    "italic": _format(_italic),
    "code": _fixed(""),
    "tt": _fixed(""),
    "dice": _roll,
    "damage": _roll,
    "autodice": _roll,
    "dc": lambda parts, r: f"DC {parts[0]}" if parts[0] else "",
    "hit": _bonus,
    "d20": _bonus,
    "initiative": _bonus,
    "ability": _ability,
    "savingThrow": _modifier,
    "skillCheck": _modifier,
    "chance": _chance,
    "recharge": _recharge,
    "atk": _attack(roll=False),
    "atkr": _attack(roll=True),
    "h": _fixed("Hit: "),
    "m": _fixed("Miss: "),
    "hom": _fixed(_italic("Hit or Miss:")),
    "actSave": _act_save,
    "actSaveFail": _act_save_fail,
    "actSaveFailBy": _act_save_fail_by,
    "actSaveSuccess": _fixed(_italic("Success:")),
    "actSaveSuccessOrFail": _fixed(_italic("Failure or Success:")),
    "actTrigger": _fixed(_italic("Trigger:")),
    "actResponse": lambda parts, r: _italic(
        "Response---" if "d" in parts[0] else "Response:"
    ),
    "hitYourSpellAttack": _default("your spell attack modifier"),
    "dcYourSpellSave": _default("your spell save DC"),
    "coinflip": _default("flip a coin"),
    "note": _note,
    "link": _link,
    "quickref": lambda parts, r: _italic(r.text(display_part("quickref", parts))),
    "area": _area,
    "style": lambda parts, r: escape_latex_text(parts[0]),
    "filter": lambda parts, r: r.text(parts[0]),
    "scaledamage": _scaling,
    "scaledice": _scaling,
    "card": lambda parts, r: r.text(display_part("card", parts)),
    "homebrew": lambda parts, r: _italic(escape_latex_text(parts[0])),
}

# Tags 5etools has that render as their display text
_PLAIN = {
    "s", "strike", "s2", "strikeDouble", "u", "underline", "u2",
    "underlineDouble", "sup", "sub", "kbd", "font", "comic", "comicH1",
    "comicH2", "comicH3", "comicH4", "comicNote", "tip", "unit", "5etools",
    "5etoolsImg", "5etoolsAudio", "footnote", "loader", "color", "highlight",
    "help", "boon", "charoption", "creatureFluff", "cult", "facility",
    "itemProperty", "itemMastery", "language", "legroup", "object",
    "optfeature", "psionic", "raceFluff", "crochet", "crochetFluff", "vehicle",
    "vehupgrade", "trap", "cite", "subclass", "classFeature",
    "subclassFeature", "itemEntry",
}  # fmt: skip
_warned: set[str] = set()


def _plain_tag(tag: str, parts: list[str], r: Render) -> str:
    if tag not in _PLAIN and tag not in _warned:
        _warned.add(tag)
        logger.warning(f"Unknown tag @{tag}; rendering its display text")
    return r.text(display_part(tag, parts))

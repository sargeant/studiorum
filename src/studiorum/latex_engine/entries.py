"""5etools entries to LaTeX.

``EntryRenderer`` walks an entry tree with one function per entry type. Strings
go through the tag renderer; environments (lists, tables, insets, quotes, the
monster spell block) are macros in ``_entries.tex.j2``. A failure raises
``EntryError`` naming where in the tree it happened.
"""

from __future__ import annotations

import dataclasses
import re
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import replace
from functools import cache
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

from studiorum.core.compact import compact_entries
from studiorum.core.entry_registry import KNOWN_ENTRY_TYPES
from studiorum.core.loaders.magic_variants import generic_item
from studiorum.core.logging import get_logger
from studiorum.core.models.content import ContentType
from studiorum.core.models.content_models import (
    FLUFF_TYPES,
    PROP_TYPES,
    content_type_of,
)
from studiorum.core.models.creatures import ArmorClass, Creature
from studiorum.core.models.magicvariant import MagicVariant
from studiorum.renderers.context import Style
from studiorum.renderers.escape import escape
from studiorum.renderers.tags import render

from .core.images import emit
from .core.images.resolve import ImageResolver

if TYPE_CHECKING:
    from studiorum.core.loaders.omnidexer import Omnidexer
    from studiorum.core.references.content_tracker import ContentTracker
    from studiorum.renderers.context import RenderingContext

logger = get_logger(__name__)

ABILITIES = {
    "str": "Strength",
    "dex": "Dexterity",
    "con": "Constitution",
    "int": "Intelligence",
    "wis": "Wisdom",
    "cha": "Charisma",
}

# What a statblock's tag looks up, and the source when it gives none: 5etools'
# Parser.TAG_TO_PROPS and each tag's defaultSource. An item may also be a
# generic variant, which renders as an item.
STATBLOCK_TAGS: dict[str, tuple[ContentType, str]] = {
    "action": (ContentType.ACTION, "PHB"),
    "background": (ContentType.BACKGROUND, "PHB"),
    "charoption": (ContentType.CHAROPTION, "MOT"),
    "class": (ContentType.CLASS, "PHB"),
    "condition": (ContentType.CONDITION, "PHB"),
    "creature": (ContentType.CREATURE, "MM"),
    "deck": (ContentType.DECK, "DMG"),
    "deity": (ContentType.DEITY, "PHB"),
    "disease": (ContentType.DISEASE, "DMG"),
    "facility": (ContentType.FACILITY, "XDMG"),
    "feat": (ContentType.FEAT, "PHB"),
    "hazard": (ContentType.HAZARD, "DMG"),
    "item": (ContentType.ITEM, "DMG"),
    "object": (ContentType.OBJECT, "DMG"),
    "optfeature": (ContentType.OPTIONALFEATURE, "PHB"),
    "race": (ContentType.RACE, "PHB"),
    "recipe": (ContentType.RECIPE, "HF"),
    "reward": (ContentType.REWARD, "DMG"),
    "sense": (ContentType.SENSE, "PHB"),
    "spell": (ContentType.SPELL, "PHB"),
    "status": (ContentType.STATUS, "PHB"),
    "subclass": (ContentType.SUBCLASS, "PHB"),
    "table": (ContentType.TABLE, "DMG"),
    "trap": (ContentType.TRAP, "DMG"),
    "variantrule": (ContentType.VARIANTRULE, "DMG"),
    "vehicle": (ContentType.VEHICLE, "GoS"),
}

# Content that statblocks render through its own macro (render_models)
MODEL_KINDS = frozenset({"creature", "spell", "item"})

_warned_types: set[str] = set()
_warned_statblocks: set[str] = set()


class EntryError(Exception):
    """An entry that could not be rendered, with its place in the tree."""


@cache
def _macros() -> Any:
    from .core.template_engine import environment

    return environment().get_template("_entries.tex.j2").module


class EntryRenderer:
    """Renders 5etools entries to LaTeX for one document."""

    def __init__(
        self,
        tracker: ContentTracker | None = None,
        omnidexer: Omnidexer | None = None,
        style: Style | None = None,
        images: ImageResolver | None = None,
        context: RenderingContext | None = None,
    ) -> None:
        self.tracker = tracker
        self.omnidexer = omnidexer
        self.style = style or Style()
        self._images = images
        # Statblocks render creatures and items through their templates
        self._context = context
        self._depth = 0
        self._path: list[str] = []
        self._wide_float = False

    @classmethod
    def from_context(cls, context: RenderingContext) -> EntryRenderer:
        return cls(
            tracker=context.content_tracker,
            omnidexer=context.omnidexer,
            style=context.style,
            context=context,
        )

    def render(self, value: Any) -> str:
        """LaTeX for an entry, a list of them, or anything with ``entries``."""
        if isinstance(value, str | dict):
            inner = value.get("entries") if isinstance(value, dict) else None
        elif isinstance(value, list | tuple):
            return "\n\n".join(self.entries(list(value)))
        else:
            inner = getattr(value, "entries", None)
        return "\n\n".join(self.entries(inner if inner else [value]))

    def entries(self, entries: list[Any]) -> list[str]:
        """LaTeX for each entry in a list."""
        return [self.entry(entry) for entry in entries]

    def entry(self, entry: Any) -> str:
        """LaTeX for one entry: a string, a dict or a model of one."""
        if isinstance(entry, str):
            return self.text(entry)
        if isinstance(entry, BaseModel):
            entry = entry.model_dump(exclude_none=True)
        elif dataclasses.is_dataclass(entry) and not isinstance(entry, type):
            entry = dataclasses.asdict(entry)
        if isinstance(entry, int | float):
            return str(entry)
        if not isinstance(entry, dict):
            raise EntryError(
                f"Cannot render a {type(entry).__name__} as an entry{self._where()}"
            )
        entry_type = entry.get("type", "")
        self._path.append(str(entry.get("name") or entry_type or "entry"))
        try:
            return self._dispatch(entry_type)(self, entry)
        except EntryError:
            raise
        except Exception as e:
            raise EntryError(
                f"Cannot render {entry_type or 'an'} entry{self._where()}: {e}"
            ) from e
        finally:
            self._path.pop()

    def text(self, text: str) -> str:
        """A 5etools string with its tags rendered and the rest escaped."""
        if not text:
            return escape(text)
        return render(text, self.tracker)

    def _where(self) -> str:
        return f" at {' › '.join(self._path)}" if self._path else ""

    def _dispatch(
        self, entry_type: str
    ) -> Callable[[EntryRenderer, dict[str, Any]], str]:
        handler = HANDLERS.get(entry_type)
        if handler is not None:
            return handler
        if entry_type and entry_type not in KNOWN_ENTRY_TYPES | _warned_types:
            _warned_types.add(entry_type)
            logger.warning(f"Unknown entry type '{entry_type}', rendered generically")
        return EntryRenderer._generic

    @contextmanager
    def _deeper(self) -> Iterator[None]:
        self._depth += 1
        try:
            yield
        finally:
            self._depth -= 1

    @contextmanager
    def _styled(self, **changes: Any) -> Iterator[None]:
        style = self.style
        self.style = replace(style, **changes)
        try:
            yield
        finally:
            self.style = style

    def _heading(self, depth: int, name: str) -> str:
        headings = self.style.headings
        command = headings[min(depth, len(headings) - 1)]
        return f"\\{command}{{{self.text(name)}}}"

    def _image_resolver(self) -> ImageResolver:
        if self._images is None:
            from studiorum.core.config.unified_config import get_app_config

            self._images = ImageResolver.from_config(get_app_config().image)
        return self._images

    # Entry types, in the order 5etools' renderer lists them

    def _section(self, entry: dict[str, Any]) -> str:
        return self._named_block(entry, self._depth)

    def _entries(self, entry: dict[str, Any]) -> str:
        return self._named_block(entry, self._depth + 1)

    def _named_block(self, entry: dict[str, Any], heading_depth: int) -> str:
        result = []
        if name := entry.get("name", ""):
            result.append(self._heading(heading_depth, name))
        if entries := entry.get("entries", []):
            with self._deeper():
                result.extend(self.entries(entries))
        if name and self._wide_float:
            result.append("\\FloatBarrier")
            self._wide_float = False
        return "\n\n".join(result)

    def _inset_read_aloud(self, entry: dict[str, Any]) -> str:
        with self._styled(sidebar=True):
            body = "\n\n".join(self.entries(entry.get("entries", [])))
        return str(_macros().read_aloud(body))

    def _inset(self, entry: dict[str, Any]) -> str:
        with self._styled(sidebar=True):
            body = "\n\n".join(self.entries(entry.get("entries", [])))
        name = entry.get("name", "")
        return str(_macros().sidebar(escape(name) if name else "", body))

    def _image(self, entry: dict[str, Any]) -> str:
        return emit.image(entry, self.style.images, self._image_resolver(), self.text)

    def _gallery(self, entry: dict[str, Any]) -> str:
        return emit.gallery(entry, self.style.images, self._image_resolver(), self.text)

    def _list(self, entry: dict[str, Any]) -> str:
        items = entry.get("items", [])
        if not items:
            return ""
        style = entry.get("style", "unordered")
        if style == "ordered":
            env = "enumerate"
        elif style in ("list-hang-notitle", "list-hang", "list-hang-subtrait"):
            env = "description"
        else:
            env = "itemize"

        # Credits: a list followed by named blocks, with no list around them
        is_credits = (
            env == "description"
            and len(items) > 1
            and isinstance(items[0], dict)
            and items[0].get("type") == "list"
            and all(
                isinstance(item, dict) and item.get("type") == "entries"
                for item in items[1:]
            )
        )
        out: list[str] = []
        run: list[tuple[str | None, str]] | None = None if is_credits else []
        for i, item in enumerate(items):
            if is_credits and i == 0:
                out.append(self.entry(item))
                continue
            if (
                env == "description"
                and isinstance(item, dict)
                and item.get("type") == "entries"
                and not item.get("name")
            ):
                # An unnamed block breaks out of the list
                if run is not None:
                    out.append(str(_macros().list_env(env, run)))
                    run = None
                out.append(self.entry(item))
                if any(
                    isinstance(rest, str)
                    or (isinstance(rest, dict) and rest.get("type") != "entries")
                    for rest in items[i + 1 :]
                ):
                    run = []
                continue
            if run is None:
                run = []
            run.append(self._list_item(env, item))
        if run is not None:
            out.append(str(_macros().list_env(env, run)))
        return "\n".join(out)

    def _list_item(self, env: str, item: Any) -> tuple[str | None, str]:
        """An item's label (None for none, '' for an empty one) and body."""
        empty = "" if env == "description" else None
        if isinstance(item, str):
            return empty, self.text(item)
        if not isinstance(item, dict):
            return empty, str(item)
        named_block = item.get("type") in ("item", "itemSub", "entries")
        if (
            not item.get("name")
            or item.get("type") == "list"
            or not (env == "description" or named_block)
        ):
            return empty, self.entry(item)
        name = item["name"]
        if named_block:
            # A named entries item (a feature in a list) runs in like an item
            if text := item.get("entry", "") or item.get("text", ""):
                body = self.text(text)
            elif entries := item.get("entries", []):
                body = "\n\n".join(self.entries(entries))
            else:
                body = ""
        else:
            body = self.entry(item)
        label = self.text(name)
        if not name.rstrip().endswith((".", ":", ";")):
            label += "."
        if env != "description":
            return empty, f"\\textbf{{{label}}} {body}"
        return label, body

    def _table(self, entry: dict[str, Any]) -> str:
        caption = entry.get("caption", "")
        labels = entry.get("colLabels", [])
        col_styles = entry.get("colStyles", [])
        rows = entry.get("rows", [])
        if not rows:
            return f"% Empty table: {caption}" if caption else "% Empty table"
        if labels:
            count = len(labels)
        elif col_styles:
            count = len(col_styles)
        else:
            count = len(_row_cells(rows[0])) or 2
        cells = [
            [self.entry(c) if isinstance(c, dict) else self.text(str(c)) for c in row]
            for row in map(_row_cells, rows)
        ]
        # "wide" is Studiorum's own, on tables it builds (a class table)
        wide = bool(entry.get("wide"))
        table = _macros().table(
            escape(caption) if caption else "",
            column_spec(col_styles, count, stretch=not wide),
            [self.text(str(label)) for label in labels],
            cells,
            wide,
        )
        return f"% Table: {caption}\n{table}" if caption else str(table)

    def _quote(self, entry: dict[str, Any]) -> str:
        body = "\n\n".join(self.entries(entry.get("entries", [])))
        by = entry.get("by", "")
        return str(_macros().quote(body, escape(by) if by else ""))

    def _generic(self, entry: dict[str, Any]) -> str:
        name = entry.get("name", "")
        entries = entry.get("entries", [])
        content = entry.get("content", "")
        text = entry.get("text", "")
        result = []
        if name:
            result.append(self._heading(self._depth + 1, name))
        if entries:
            with self._deeper():
                result.extend(self.entries(entries))
        elif content:
            result.append(self.text(content))
        elif text:
            result.append(self.text(text))
        # A name with text gets the text twice
        if name and text and not entries and not content:
            result.append(self.text(text))
        return "\n\n".join(result)

    def _actions(self, entry: dict[str, Any]) -> str:
        return self._run_in(entry, "\\textbf{{{}.}}")

    def _attack(self, entry: dict[str, Any]) -> str:
        return self._run_in(entry, "\\textit{{{}.}}")

    def _variant_sub(self, entry: dict[str, Any]) -> str:
        return self._run_in(entry, "\\textit{{{}:}}")

    def _run_in(self, entry: dict[str, Any], label: str) -> str:
        """The name as a run-in label, then the entries on the same line."""
        result = []
        if name := entry.get("name", ""):
            result.append(label.format(escape(name)))
        if entries := entry.get("entries", []):
            result.extend(self.entries(entries))
        return " ".join(result)

    def _options(self, entry: dict[str, Any]) -> str:
        """5etools' _renderOptions: named options first, by name; a list if hanging."""
        entries = entry.get("entries", [])
        if not entries:
            return ""
        named = sorted(
            (e for e in entries if isinstance(e, dict) and e.get("name")),
            key=lambda e: str(e["name"]).lower(),
        )
        entries = named + [
            e for e in entries if not (isinstance(e, dict) and e.get("name"))
        ]
        if entry.get("style") == "list-hang-notitle":
            return self._list(
                {"type": "list", "style": "list-hang-notitle", "items": entries}
            )
        return "\n\n".join(self.entries(entries))

    def _variant(self, entry: dict[str, Any]) -> str:
        name = entry.get("name", "")
        result = [
            f"\\textbf{{Variant: {escape(name)}}}" if name else "\\textbf{Variant:}"
        ]
        if entries := entry.get("entries", []):
            result.extend(self.entries(entries))
        return "\n\n".join(result)

    def _ability_dc(self, entry: dict[str, Any]) -> str:
        return self._ability(entry, "Save DC", "8 + proficiency bonus + {} modifier")

    def _ability_attack_mod(self, entry: dict[str, Any]) -> str:
        return self._ability(entry, "Attack Bonus", "proficiency bonus + {} modifier")

    def _ability(self, entry: dict[str, Any], default: str, formula: str) -> str:
        attributes = entry.get("attributes", [])
        ability = (
            ABILITIES.get(attributes[0], attributes[0].capitalize())
            if attributes
            else "ability"
        )
        name = escape(entry.get("name", default))
        return f"\\textbf{{{name}:}} {formula.format(ability)}"

    def _ability_generic(self, entry: dict[str, Any]) -> str:
        result = []
        if name := entry.get("name", ""):
            result.append(f"\\textbf{{{escape(name)}:}}")
        if text := entry.get("text", ""):
            result.append(self.text(text))
        return " ".join(result)

    def _spellcasting(self, entry: dict[str, Any]) -> str:
        return spellcasting(self, entry)

    def _bonus(self, entry: dict[str, Any]) -> str:
        value = entry.get("value", 0)
        return f"+{value}" if value >= 0 else str(value)

    def _bonus_speed(self, entry: dict[str, Any]) -> str:
        value = entry.get("value", 0)
        return f"+{value} ft." if value >= 0 else f"{value} ft."

    def _dice(self, entry: dict[str, Any]) -> str:
        rolls = []
        for roll in entry.get("toRoll", []):
            dice = f"{roll.get('number', 1)}d{roll.get('faces', 6)}"
            modifier = roll.get("modifier", 0)
            if modifier > 0:
                dice += f"+{modifier}"
            elif modifier < 0:
                dice += str(modifier)
            rolls.append(dice)
        return ", ".join(rolls)

    def _item(self, entry: dict[str, Any]) -> str:
        result = []
        if name := entry.get("name", ""):
            label = self.text(name)
            punctuated = name.rstrip().endswith((".", ":", ";"))
            result.append(
                f"\\textbf{{{label}}}" if punctuated else f"\\textbf{{{label}.}}"
            )
        if text := entry.get("entry", "") or entry.get("text", ""):
            result.append(self.text(text))
        elif entries := entry.get("entries", []):
            result.extend(self.entries(entries))
        return " ".join(result)

    def _cell(self, entry: dict[str, Any]) -> str:
        roll = entry.get("roll", {})
        roll_text = ""
        if roll:
            if "exact" in roll:
                roll_text = str(roll["exact"])
            elif "min" in roll and "max" in roll:
                low, high = roll["min"], roll["max"]
                roll_text = str(low) if low == high else f"{low}–{high}"
        if content := entry.get("entry", ""):
            text = self.text(content)
            return f"{roll_text} {text}" if roll_text else text
        return roll_text

    def _ingredient(self, entry: dict[str, Any]) -> str:
        return self.entry(entry.get("entry", ""))

    def _statblock(self, entry: dict[str, Any]) -> str:
        """What the statblock points to, looked up as 5etools does."""
        name = entry.get("name", "")
        found = self._statblock_content(entry)
        if found is None:
            return self._heading(self._depth, name)
        if display := entry.get("displayName"):
            found = found.model_copy(update={"name": display})
        content_type = content_type_of(found)
        if content_type.value in MODEL_KINDS:
            return self._render_model(content_type.value, found)
        if content_type in FLUFF_TYPES:
            return self._fluff(entry, found)
        inset = entry.get("style", "") == "inset"
        entries = compact_entries(found, self.omnidexer)
        if not entries:
            return self.text(name) if inset else self._heading(self._depth, name)
        body = "\n\n".join(self.entries(entries))
        # A wide table (a class's) floats; the section around it ends with a barrier
        if "\\begin{table*}" in body and self.style.book:
            self._wide_float = True
        if inset:
            return str(_macros().sidebar(self.text(name), body))
        return f"{self._heading(self._depth, name)}\n\n{body}"

    def _fluff(self, entry: dict[str, Any], fluff: Any) -> str:
        """Fluff in the text, as 5etools' getCompactRenderedFluffString."""
        entries = fluff.model_dump(exclude_none=True).get("entries") or []
        render_compact = entry.get("data", {}).get("renderCompact", {})
        if (
            entries
            and isinstance(entries[0], dict)
            and render_compact.get("isSkipRootName")
        ):
            entries[0] = {k: v for k, v in entries[0].items() if k != "name"}
        return "\n\n".join(self.entries(entries))

    def _statblock_content(self, entry: dict[str, Any]) -> Any:
        """The content a statblock names by its prop, or else its tag."""
        name = entry.get("name", "")
        tag, prop = entry.get("tag", ""), entry.get("prop", "")
        known = STATBLOCK_TAGS.get(tag)
        content_type = PROP_TYPES.get(prop) if prop else known and known[0]
        if content_type is None:
            kind = prop or tag
            if kind not in _warned_statblocks:
                _warned_statblocks.add(kind)
                logger.warning(f"Statblocks of '{kind}' are not supported")
            return None
        source = entry.get("source") or (known[1] if known else "")
        found = self._find(content_type, entry, source)
        if found is None and content_type == ContentType.ITEM:
            found = self._find(ContentType.MAGICVARIANT, entry, source)
        if isinstance(found, MagicVariant):
            found = generic_item(found)
        if found is None:
            logger.warning(
                f"Could not resolve statblock reference: {prop or tag} '{name}' "
                f"from {source}"
            )
        return found

    def _find(
        self, content_type: ContentType, entry: dict[str, Any], source: str
    ) -> Any:
        """Content by name and source, or a subclass by its 5etools uid."""
        if self.omnidexer is None:
            return None
        if content_type == ContentType.SUBCLASS and entry.get("shortName"):
            uid = "|".join(
                (
                    entry["shortName"],
                    entry.get("className", ""),
                    entry.get("classSource", ""),
                    source,
                )
            )
            return self.omnidexer.find_uid(content_type, uid)
        return self.omnidexer.find(content_type, entry.get("name", ""), source)

    def _render_model(self, kind: str, content: Any) -> str:
        """A creature, spell or item through its macro, in the text."""
        from studiorum.renderers.context import RenderingContext

        from .document import render_models

        context = self._context or RenderingContext(
            content_tracker=self.tracker, omnidexer=self.omnidexer
        )
        latex = render_models(kind, [content], context, floating=False)
        # A wide statblock still floats; its section ends with a float barrier
        if "[float*" in latex and self.style.book:
            self._wide_float = True
        return latex


def spellcasting(renderer: EntryRenderer, entry: dict[str, Any]) -> str:
    """A creature's spellcasting: header, spells by level or frequency, footer.

    Levels whose spells render with formatting (spell tags are italic) get a
    bold label; the rest use DndMonsterSpells macros in statblocks.
    """
    macros = renderer.style.monster_spells
    result: list[str] = []
    name = entry.get("name", "Spellcasting")
    if entry.get("renderHeader", True) and name:
        result.append(f"\\textbf{{{escape(name)}.}}")
    result.extend(renderer.entries(entry.get("headerEntries") or []))

    # Each line and whether it is a DndMonsterSpells macro
    lines: list[tuple[str, bool]] = []

    def formatted(spells: list[str]) -> bool:
        return any("\\textit{" in s for s in spells)

    if will := entry.get("will", []):
        spells = renderer.entries(will)
        if formatted(spells) or not macros:
            lines.append(("\\textbf{At will:} " + ", ".join(spells), False))
        else:
            lines.append((f"  \\DndInnateSpellLevel{{{', '.join(spells)}}}", True))
    if daily := entry.get("daily", {}):
        for freq in sorted(daily, key=_leading_int):
            spells = renderer.entries(daily.get(freq, []))
            count = re.match(r"(\d+)", str(freq).strip())
            if formatted(spells):
                lines.append(
                    (f"\\textbf{{{escape(str(freq))}:}} " + ", ".join(spells), False)
                )
            elif not count:
                lines.append(
                    (f"  \\textbf{{{escape(str(freq))}:}} {', '.join(spells)}", False)
                )
            elif macros:
                lines.append(
                    (
                        f"  \\DndInnateSpellLevel[{count.group(1)}]{{{', '.join(spells)}}}",
                        True,
                    )
                )
            else:
                lines.append(
                    (f"\\textbf{{{count.group(1)}/day:}} " + ", ".join(spells), False)
                )
    if constant := entry.get("constant", []):
        lines.append(
            ("  \\textbf{Constant:} " + ", ".join(renderer.entries(constant)), False)
        )
    levels = entry.get("spells") or {}
    for level, data in sorted(
        levels.items(), key=lambda x: int(x[0]) if str(x[0]).isdigit() else 999
    ):
        if isinstance(data, dict):
            spell_list, slots = data.get("spells", []), data.get("slots")
        else:
            spell_list, slots = (
                getattr(data, "spells", []),
                getattr(data, "slots", None),
            )
        if not spell_list:
            continue
        lines.append(
            _spell_level(renderer.entries(spell_list), str(level), slots, macros)
        )

    if any(is_macro for _, is_macro in lines):
        first = next(i for i, (_, is_macro) in enumerate(lines) if is_macro)
        result.extend(line for line, _ in lines[:first])
        result.append(
            str(_macros().monster_spells([line for line, _ in lines[first:]]))
        )
    else:
        result.extend(line for line, _ in lines)
    result.extend(renderer.entries(entry.get("footerEntries") or []))
    return "\n".join(result)


def _spell_level(
    spells: list[str], level: str, slots: Any, macros: bool
) -> tuple[str, bool]:
    text = ", ".join(spells)
    if any("\\textit{" in s for s in spells):
        if level == "0":
            header = "\\textbf{Cantrips (at will):}"
        else:
            suffix = {"1": "st", "2": "nd", "3": "rd"}.get(level, "th")
            slot_text = f" ({slots} slots)" if slots else ""
            header = f"\\textbf{{{level}{suffix} level{slot_text}:}}"
        return f"{header} {text}", False
    if level == "0":
        if macros:
            return f"  \\DndMonsterSpellLevel{{{text}}}", True
        return "\\textbf{Cantrips (at will):} " + text, False
    if not level.isdigit():
        return f"  {text}", False
    suffix = {"1": "st", "2": "nd", "3": "rd"}.get(level, "th")
    if slots is not None:
        if macros:
            return f"  \\DndMonsterSpellLevel[{level}][{slots}]{{{text}}}", True
        return f"\\textbf{{{level}{suffix} level ({slots} slots):}} " + text, False
    if macros:
        return f"  \\DndMonsterSpellLevel[{level}]{{{text}}}", True
    return f"\\textbf{{{level}{suffix} level:}} " + text, False


def _leading_int(key: str) -> int:
    match = re.match(r"(\d+)", str(key))
    return int(match.group(1)) if match else 999


def _row_cells(row: Any) -> list[Any]:
    """A table row's cells: a list, or a 5etools ``{"type": "row", "row": [...]}``."""
    if isinstance(row, dict):
        return list(row.get("row", []))
    return list(row) if isinstance(row, list) else [row]


def column_spec(col_styles: list[str], count: int, *, stretch: bool = True) -> str:
    """A DndTable column specification from 5etools' Bootstrap colStyles.

    Wide columns (col-8 and up) stretch as X; with ``stretch``, tables of four
    or more columns with three or more fixed ones stretch some centred columns
    too.
    """
    if not col_styles:
        return "l" * count
    specs = []
    for style in col_styles:
        width = None
        alignment = "l"
        for cls in style.split():
            if cls.startswith("col-"):
                try:
                    width = int(cls.split("-")[1])
                except (IndexError, ValueError):
                    continue
            elif cls == "text-center":
                alignment = "c"
            elif cls == "text-right":
                alignment = "r"
        if width is None:
            specs.append("l")
        elif width >= 8:
            specs.append("X")
        elif width <= 2 and alignment == "c":
            specs.append("c")
        elif alignment == "r":
            specs.append("r")
        else:
            specs.append("l")
    # 5etools gives some tables fewer styles than columns
    specs += ["l"] * (count - len(specs))
    if stretch and count >= 4:
        fixed = [i for i, spec in enumerate(specs) if spec in ("c", "l", "r")]
        if len(fixed) >= 3:
            converted = 0
            for i in reversed(fixed[1:]):
                if specs[i] == "c" and converted < len(fixed) - 2:
                    specs[i] = "X"
                    converted += 1
    return "".join(specs)


# Creature statblock fields that carry markup; references in them are not tracked


def armor_class_text(armor_class: ArmorClass) -> str:
    """An AC value with its armour sources and condition."""
    if armor_class.special:
        return render(armor_class.special)
    if armor_class.ac is None:
        return "Unknown"
    result = str(armor_class.ac)
    if armor_class.from_:
        result += f" ({', '.join(render(source) for source in armor_class.from_)})"
    if armor_class.condition:
        result += f" {render(armor_class.condition)}"
    return result


def creature_ac_text(creature: Creature) -> str:
    """The creature's AC line, one part per AC entry."""
    if not isinstance(creature.ac, list):
        return str(creature.ac)
    return ", ".join(
        str(item) if isinstance(item, int) else armor_class_text(item)
        for item in creature.ac
    )


def creature_senses_text(creature: Creature) -> str | None:
    """The creature's senses, or None if it has none."""
    if not creature.senses:
        return None
    senses = creature.senses
    return render(", ".join(senses) if isinstance(senses, list) else str(senses))


HANDLERS: dict[str, Callable[[EntryRenderer, dict[str, Any]], str]] = {
    "section": EntryRenderer._section,
    "entries": EntryRenderer._entries,
    "insetReadaloud": EntryRenderer._inset_read_aloud,
    "inset": EntryRenderer._inset,
    "image": EntryRenderer._image,
    "gallery": EntryRenderer._gallery,
    "list": EntryRenderer._list,
    "table": EntryRenderer._table,
    "quote": EntryRenderer._quote,
    "actions": EntryRenderer._actions,
    "attack": EntryRenderer._attack,
    "options": EntryRenderer._options,
    "variant": EntryRenderer._variant,
    "variantSub": EntryRenderer._variant_sub,
    "abilityDc": EntryRenderer._ability_dc,
    "abilityAttackMod": EntryRenderer._ability_attack_mod,
    "abilityGeneric": EntryRenderer._ability_generic,
    "spellcasting": EntryRenderer._spellcasting,
    "bonus": EntryRenderer._bonus,
    "bonusSpeed": EntryRenderer._bonus_speed,
    "dice": EntryRenderer._dice,
    "item": EntryRenderer._item,
    "cell": EntryRenderer._cell,
    "ingredient": EntryRenderer._ingredient,
    "statblock": EntryRenderer._statblock,
}

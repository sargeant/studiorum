"""LaTeX text for creature fields that carry 5etools markup.

Armour class notes, senses and ability names can hold tags such as
{@item plate armor|phb} or {@recharge 5}. These functions turn them into
LaTeX. They take the tag resolver as an argument and fall back to the raw
text when it is missing or processing fails. LaTeXTemplateEngine exposes
them to templates as filters.
"""

import asyncio
import re
from typing import Any

from studiorum.core.models.creatures import Ability, ArmorClass, Creature, Spellcasting
from studiorum.latex_engine.entries import EntryRenderer


def process_markup(
    text: str,
    tag_resolver: Any,
    omnidexer: Any = None,
    source_name: Any = "unknown",
) -> str:
    """Render one string of 5etools markup."""
    return EntryRenderer().text(text)


def _resolve_or_raw(text: str, tag_resolver: Any) -> str:
    """Resolve tags in text, or return it unchanged."""
    if tag_resolver is None:
        return text
    try:
        return str(tag_resolver.process_text(text))
    except Exception:
        return text


def armor_class_text(armor_class: ArmorClass, tag_resolver: Any) -> str:
    """AC value with its armour sources and condition, tags resolved."""
    if armor_class.special:
        return _resolve_or_raw(armor_class.special, tag_resolver)
    if armor_class.ac is None:
        return "Unknown"

    result = str(armor_class.ac)
    if armor_class.from_:
        sources = [
            _resolve_or_raw(source, tag_resolver) for source in armor_class.from_
        ]
        result += f" ({', '.join(sources)})"
    if armor_class.condition:
        result += f" {_resolve_or_raw(armor_class.condition, tag_resolver)}"
    return result


def creature_ac_text(creature: Creature, tag_resolver: Any) -> str:
    """The creature's AC line, one part per AC entry."""
    if not isinstance(creature.ac, list):
        return str(creature.ac)
    parts = [
        str(item) if isinstance(item, int) else armor_class_text(item, tag_resolver)
        for item in creature.ac
    ]
    return ", ".join(parts)


def creature_senses_text(creature: Creature, tag_resolver: Any) -> str | None:
    """The creature's senses with tags resolved.

    Without a resolver, or if processing fails, tags are stripped to their
    display text instead.
    """
    if not creature.senses:
        return None

    try:
        if tag_resolver is None:
            raise LookupError("no tag resolver")
        senses = creature.senses
        senses_text = ", ".join(senses) if isinstance(senses, list) else str(senses)
        return process_markup(
            senses_text, tag_resolver, source_name=creature.source or "unknown"
        )
    except Exception:
        formatted = creature.get_formatted_senses()
        if formatted:
            return re.sub(r"\{@\w+\s+([^}]+)\}", r"\1", formatted)
        return formatted


def ability_name_text(
    entry: Ability | Spellcasting, omnidexer: Any, tag_resolver: Any
) -> str:
    """An ability or spellcasting name with tags resolved."""
    if isinstance(entry, Ability):
        # Processing an Ability name inside a running event loop is not safe,
        # so it keeps the raw name there.
        try:
            asyncio.get_running_loop()
            return entry.name
        except RuntimeError:
            pass

    if tag_resolver is None:
        return entry.name
    try:
        return process_markup(entry.name, tag_resolver, omnidexer) if entry.name else ""
    except Exception:
        return entry.name

"""Appendices of the creatures, items and spells a document refers to."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, Field

from studiorum.data.loaders.omnidexer import Omnidexer
from studiorum.data.models.content_models import TAG_TYPES
from studiorum.data.references.content_tracker import ContentTracker
from studiorum.log import get_logger

logger = get_logger(__name__)

# Each appendix's title and label
APPENDICES = {
    "creature": ("Creatures", "ch:appendix-creatures"),
    "item": ("Magic Items", "ch:appendix-items"),
    "spell": ("Spells", "ch:appendix-spells"),
}


@dataclass(frozen=True)
class Appendix:
    """An appendix of the creatures, items or spells a document refers to."""

    title: str
    label: str
    kind: str  # "creature", "item" or "spell"
    items: list[Any]


class AppendixFlags(BaseModel):
    """Configuration flags for appendix generation."""

    spells: bool = Field(default=False, description="Generate spells appendix")
    items: bool = Field(default=False, description="Generate items appendix")
    creatures: bool = Field(default=False, description="Generate creatures appendix")
    recursive: bool = Field(
        default=False,
        description="Add what appendix entries refer to, as well as the document",
    )

    def has_any_enabled(self) -> bool:
        """Check if any appendix flags are enabled."""
        return self.spells or self.items or self.creatures


class AppendixGenerator:
    """Builds appendices from the references a ContentTracker holds."""

    def __init__(self, omnidexer: Omnidexer):
        self.omnidexer = omnidexer

    def generate_appendices(
        self, content_tracker: ContentTracker, flags: AppendixFlags
    ) -> list[Appendix]:
        """The appendices the flags ask for: creatures, then items, then spells."""
        tracked = content_tracker.export_for_appendix()
        wanted = {
            "creature": flags.creatures,
            "item": flags.items,
            "spell": flags.spells,
        }
        appendices = []
        for kind, (title, label) in APPENDICES.items():
            if wanted[kind] and (items := self._resolve(kind, tracked.get(kind, []))):
                appendices.append(Appendix(title, label, kind, items))
        return appendices

    def _resolve(self, kind: str, tracked: list[dict[str, Any]]) -> list[Any]:
        """One entry per name, sorted by name.

        A name is looked up with the source a reference gave, else 5etools'
        default source for the tag, else by name alone.
        """
        content_type, default_source = TAG_TYPES[kind]
        sources: dict[str, tuple[str, str]] = {}
        for ref in tracked:
            name = str(ref["name"])
            source = str(ref.get("source") or "")
            known = sources.get(name.lower())
            if known is None or (source and not known[1]):
                sources[name.lower()] = (name, source)
        found = []
        for name, source in sources.values():
            item = self.omnidexer.find(content_type, name, source or default_source)
            if item is None:
                item = next(iter(self.omnidexer.find_all(content_type, name)), None)
            if item is None:
                logger.warning(f"No {kind} named {name!r} for the appendix")
                continue
            found.append(item)
        return sorted(found, key=lambda item: item.name.lower())

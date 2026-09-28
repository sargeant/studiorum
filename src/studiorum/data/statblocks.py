"""What a 5etools ``statblock`` entry points to, looked up as 5etools does."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from studiorum.data.loaders.magic_variants import generic_item
from studiorum.data.models.content import ContentType
from studiorum.data.models.content_models import PROP_TYPES, TAG_TYPES
from studiorum.data.models.magicvariant import MagicVariant

if TYPE_CHECKING:
    from studiorum.data.catalogue import Catalogue
    from studiorum.data.models.content import BaseContent


def statblock_type(entry: dict[str, Any]) -> ContentType | None:
    """The content type a statblock names by its prop, or else its tag."""
    tag, prop = entry.get("tag", ""), entry.get("prop", "")
    known = TAG_TYPES.get(tag)
    return PROP_TYPES.get(prop) if prop else known and known[0]


def statblock_source(entry: dict[str, Any]) -> str:
    """The statblock's source, else its tag's default."""
    known = TAG_TYPES.get(entry.get("tag", ""))
    return str(entry.get("source") or (known[1] if known else ""))


def find_statblock(
    catalogue: Catalogue, entry: dict[str, Any], content_type: ContentType
) -> BaseContent | None:
    """The content a statblock names; a generic variant comes back as its item."""
    source = statblock_source(entry)
    found = _find(catalogue, content_type, entry, source)
    if found is None and content_type == ContentType.ITEM:
        found = _find(catalogue, ContentType.MAGICVARIANT, entry, source)
    if isinstance(found, MagicVariant):
        return generic_item(found)
    return found


def _find(
    catalogue: Catalogue, content_type: ContentType, entry: dict[str, Any], source: str
) -> BaseContent | None:
    """Content by name and source, or a subclass by its 5etools uid."""
    if content_type == ContentType.SUBCLASS and entry.get("shortName"):
        uid = "|".join(
            (
                entry["shortName"],
                entry.get("className", ""),
                entry.get("classSource", ""),
                source,
            )
        )
        return catalogue.find_uid(content_type, uid)
    return catalogue.find(content_type, entry.get("name", ""), source)

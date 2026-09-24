"""Item types and base items by ``ABBREVIATION|SOURCE``, as items' ``type`` names them.

The loader registers them from ``items-base.json`` (``itemType`` and
``baseitem``). Code that asks before any data is loaded gets them read from
the configured data directories.
"""

from __future__ import annotations

from typing import Any

from ..logging import get_logger

logger = get_logger(__name__)

_item_types: dict[str, dict[str, Any]] | None = None


def register(entities: list[dict[str, Any]]) -> None:
    """Record entities with an abbreviation and source; the first one per key wins."""
    global _item_types
    table: dict[str, dict[str, Any]] = {}
    for ent in entities:
        if "abbreviation" in ent and "source" in ent:
            table.setdefault(f"{ent['abbreviation']}|{ent['source']}", ent)
    _item_types = table


def get(type_id: str) -> dict[str, Any] | None:
    """The item type or base item a type such as ``"$G|DMG"`` names."""
    if _item_types is None:
        _load_from_config()
    return (_item_types or {}).get(type_id)


def reset() -> None:
    global _item_types
    _item_types = None


def _load_from_config() -> None:
    from ..config.unified_config import get_app_config
    from .data_dir import DataSet, read_json

    entities: list[dict[str, Any]] = []
    for path in DataSet.from_config(get_app_config().data).files():
        if path.name != "items-base.json":
            continue
        data = read_json(path)
        entities += data.get("baseitem", []) + data.get("itemType", [])
    register(entities)

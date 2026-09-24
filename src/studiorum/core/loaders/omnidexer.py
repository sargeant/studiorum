"""The index of every loaded 5e entity, by type, name and source.

``Omnidexer.load_all_data()`` reads each file of a ``DataSet`` once with
orjson, gathers the entities by their 5etools property, resolves ``_copy``
with ``merge_copy`` (as 5etools does), then validates each content type's
entities with one ``TypeAdapter``. Adventures and books load their metadata;
their text is merged in the first time one is asked for.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pydantic import TypeAdapter, ValidationError

from ..config.unified_config import get_app_config
from ..interfaces import DeepIndexable
from ..logging import get_logger
from ..models.content import BaseContent, ContentType, Reprint
from ..models.content_models import (
    CONTENT_MODELS,
    FLUFF_TYPES,
    PROP_TYPES,
    content_type_of,
    create_content,
)
from ..models.fluff import BaseFluff
from ..validation.error_tracker import ErrorContext, ValidationErrorTracker
from . import item_types, magic_variants
from .data_dir import DataSet, read_json
from .dual_file import merge_metadata_content
from .merge_copy import resolve_copies

if TYPE_CHECKING:
    from ..protocols.progress import ProgressCallback

logger = get_logger(__name__)

_DUAL_FILE_TYPES = {ContentType.ADVENTURE, ContentType.BOOK}
# Read so copies and item types resolve, but not indexed
_SUPPORT_PROPS = ("itemType",)
# Homebrew keeps adventure and book text inline under these props
_HOMEBREW_TEXT = {"adventureData": ContentType.ADVENTURE, "bookData": ContentType.BOOK}

Raw = dict[str, Any]


class Omnidexer:
    """Every entity of a data set, looked up by type, name and source.

    Each type is keyed as 5etools keys it: by name and source, and for class
    and subclass features, subclasses, subraces and deities by what else
    tells them apart (``_IDENTITY``). When two entities share a key, the first
    loaded wins. Content that holds other content (``DeepIndexable``) has its
    nested entities indexed too, and reprints are indexed under the source
    they were reprinted in.
    """

    def __init__(
        self, data: DataSet | None = None, enable_deep_indexing: bool = True
    ) -> None:
        """Index ``data``, by default the data set the configuration names."""
        self.data = (
            data if data is not None else DataSet.from_config(get_app_config().data)
        )
        self.enable_deep_indexing = enable_deep_indexing
        self._by_type: dict[ContentType, dict[Identity, BaseContent]] = defaultdict(
            dict
        )
        self._by_name: dict[ContentType, dict[str, list[BaseContent]]] = defaultdict(
            lambda: defaultdict(list)
        )
        self._by_source: dict[str, list[BaseContent]] = defaultdict(list)
        self._loaded_types: set[ContentType] = set()
        self._homebrew_text: dict[tuple[ContentType, str], Raw] = {}
        self._hydrated: set[tuple[ContentType, str]] = set()
        # Reprint aliases wait until every real entity is indexed, so an alias
        # is only added for a reprint that isn't loaded
        self._aliases: list[tuple[BaseContent, ContentType, UidFields]] | None = None
        self._errors = ValidationErrorTracker()

    # region Loading

    def load_all_data(
        self, *, progress_callback: ProgressCallback | None = None
    ) -> dict[str, int]:
        """Load every file of the data set and index its entities.

        Returns the number of entities indexed per content type.
        """
        files = self.data.files()
        operation = None
        if progress_callback:
            operation = progress_callback.start_operation(
                "Loading 5e content types",
                total=len(files),
                metadata={"component": "omnidexer"},
            )

        raw: dict[str, list[Raw]] = defaultdict(list)
        origins: dict[int, Path] = {}
        for i, path in enumerate(files):
            if progress_callback and operation:
                progress_callback.update_progress(
                    operation, completed=i, description=f"Reading {path.name}"
                )
            self._read_file(path, raw, origins)

        for failure in resolve_copies(raw, self.data.templates()):
            logger.warning(
                f"Could not resolve _copy for {failure.prop} {failure.name} "
                f"({failure.source}): {failure.message}"
            )
        item_types.register(raw.get("baseitem", []) + raw.get("itemType", []))
        self._add_specific_variants(raw)

        by_type: dict[ContentType, list[Raw]] = defaultdict(list)
        for prop, entities in raw.items():
            content_type = PROP_TYPES.get(prop)
            if content_type is not None:
                by_type[content_type] += [e for e in entities if "_copy" not in e]

        stats: dict[str, int] = {}
        self._aliases = []
        for content_type in CONTENT_MODELS:
            items = self._validate(content_type, by_type.get(content_type, []), origins)
            if content_type == ContentType.SPELL:
                items = self._with_spell_classes(items)
            for item in items:
                self._add_to_index(item, content_type)
            if items:
                self._loaded_types.add(content_type)
                stats[content_type.value] = len(items)
        aliases, self._aliases = self._aliases, None
        for alias, content_type, fields in aliases:
            self._add_alias(alias, content_type, fields)

        if progress_callback and operation:
            progress_callback.complete_operation(
                operation,
                result=f"Loaded {sum(stats.values())} items across {len(stats)} content types",
            )
        if not stats:
            logger.warning("No data files found to load")
        return stats

    def _read_file(
        self, path: Path, raw: dict[str, list[Raw]], origins: dict[int, Path]
    ) -> None:
        try:
            data = read_json(path)
        except (OSError, ValueError) as e:
            logger.warning(f"Could not read {path}: {e}")
            return
        if not isinstance(data, dict):
            return
        for prop, entities in data.items():
            if not isinstance(entities, list):
                continue
            if prop in _HOMEBREW_TEXT:
                for text in entities:
                    if isinstance(text, dict) and isinstance(text.get("id"), str):
                        key = (_HOMEBREW_TEXT[prop], text["id"].lower())
                        self._homebrew_text.setdefault(key, text)
            elif prop in PROP_TYPES or prop in _SUPPORT_PROPS:
                for entity in entities:
                    if isinstance(entity, dict):
                        raw[prop].append(entity)
                        origins[id(entity)] = path

    def _validate(
        self, content_type: ContentType, entities: list[Raw], origins: dict[int, Path]
    ) -> list[BaseContent]:
        """Validate all at once; on any error, one at a time so the rest still load."""
        model = CONTENT_MODELS[content_type]
        if content_type in FLUFF_TYPES:
            entities = [e for e in entities if e.get("name")]
        if content_type == ContentType.CREATURE:
            entities = [e for e in entities if not _is_reference_stub(e)]
        if content_type == ContentType.SUBRACE:
            entities = [e for e in entities if not _is_race_default(e)]
        prepared = [_prepare(e, content_type) for e in entities]
        try:
            return list(TypeAdapter(list[model]).validate_python(prepared))  # type: ignore[valid-type]
        except ValidationError:
            pass
        items: list[BaseContent] = []
        for entity, original in zip(prepared, entities, strict=True):
            try:
                items.append(model.model_validate(entity))
            except ValidationError as e:
                if content_type in FLUFF_TYPES:
                    items.append(_liberal_fluff(entity, model))
                else:
                    self._record_error(
                        e, entity, content_type, origins.get(id(original))
                    )
        return items

    def _record_error(
        self,
        error: ValidationError,
        entity: Raw,
        content_type: ContentType,
        path: Path | None,
    ) -> None:
        strictness = get_app_config().validation.strictness
        if strictness == "strict":
            raise error
        context: ErrorContext = {
            "file": str(path),
            "item_name": entity.get("name", "unknown"),
            "content_type": content_type.value,
        }
        if strictness == "normal" and self._errors.should_log_error(error, context):
            message = self._errors.format_error_message(error, context)
            logger.warning(message.replace("{", "{{").replace("}", "}}"))
        self._errors.record_error(error, context)

    def _with_spell_classes(self, items: list[BaseContent]) -> list[BaseContent]:
        from ..models.spells import Spell
        from ..services.spell_class_lookup import get_spell_class_lookup_service

        lookup = get_spell_class_lookup_service()
        try:
            return [
                lookup.enhance_spell(i) if isinstance(i, Spell) else i for i in items
            ]
        except Exception as e:
            logger.warning(f"Failed to enhance spells with class data: {e}")
            return items

    # endregion

    # region Adventure and book text

    def hydrate(self, content: BaseContent) -> BaseContent:
        """An adventure or book with its text merged in; other content unchanged.

        The first call reads the content file (or the homebrew's inline text)
        and replaces the metadata-only entry in the index.
        """
        content_type = content_type_of(content)
        content_id = getattr(content, "id", None)
        if content_type not in _DUAL_FILE_TYPES or not isinstance(content_id, str):
            return content
        key = (content_type, content_id.lower())
        if key in self._hydrated or _has_full_text(content):
            return content

        path = self.data.content_file(content_type, content_id)
        text = read_json(path) if path else self._homebrew_text.get(key)
        self._hydrated.add(key)
        if text is None:
            logger.debug(f"No text found for {content_type.value} {content_id}")
            return content
        try:
            merged = create_content(
                merge_metadata_content(content.model_dump(), text), content_type
            )
        except ValidationError as e:
            logger.error(f"Failed to merge {content_type.value} {content_id}: {e}")
            return content
        self._replace(content, merged, content_type)
        return merged

    def _replace(
        self, old: BaseContent, new: BaseContent, content_type: ContentType
    ) -> None:
        """Put ``new`` where ``old`` was, then index what ``new`` holds."""
        self._by_type[content_type][_identity(old, content_type)] = new
        for group in (
            self._by_name[content_type][old.name.lower()],
            self._by_source[_source(old)],
        ):
            group[:] = [new if c is old else c for c in group]
        if self.enable_deep_indexing and isinstance(new, DeepIndexable):
            self._index_nested(new, content_type)

    # endregion

    # region Indexing

    def _add_to_index(self, content: BaseContent, content_type: ContentType) -> None:
        identity = _identity(content, content_type)
        type_index = self._by_type[content_type]
        if identity in type_index:
            return
        type_index[identity] = content
        self._by_name[content_type][content.name.lower()].append(content)
        source = _source(content)
        self._by_source[source].append(content)
        self._index_reprints(content, content_type)
        if self.enable_deep_indexing and isinstance(content, DeepIndexable):
            self._index_nested(content, content_type)

    def _index_reprints(self, content: BaseContent, content_type: ContentType) -> None:
        """Index a copy under each uid it was reprinted as (5etools' reprintedAs).

        A reprint tagged as another kind of content (a fighting style
        reprinted as a feat) is left to that type. Subraces are reprinted as
        races, so they have no aliases.
        """
        if content_type == ContentType.SUBRACE:
            return
        reprints = getattr(content, "reprinted_as", None) or getattr(
            content, "reprintedAs", None
        )
        if not isinstance(reprints, list):
            return
        for reprint in reprints:
            if isinstance(reprint, Reprint):
                uid, tag = reprint.uid, reprint.tag
            elif isinstance(reprint, dict):
                # Models without a reprintedAs field keep the raw JSON
                uid, tag = str(reprint.get("uid", "")), reprint.get("tag")
            else:
                uid, tag = str(reprint), None
            if tag and PROP_TYPES.get(tag) != content_type:
                continue
            fields = parse_uid(content_type, uid)
            if not fields or not fields.get("source"):
                continue
            alias = _reprint_alias(content, fields)
            if alias is None:
                continue
            if self._aliases is not None:
                self._aliases.append((alias, content_type, fields))
            else:
                self._add_alias(alias, content_type, fields)

    def _add_alias(
        self, alias: BaseContent, content_type: ContentType, fields: UidFields
    ) -> None:
        if self._match_uid(content_type, fields) is not None:
            return
        # An item reprinted as a generic variant ("... (*)|XDMG") is that variant
        if content_type == ContentType.ITEM and (
            self._match_uid(ContentType.MAGICVARIANT, fields) is not None
        ):
            return
        self._add_to_index(alias, content_type)

    @staticmethod
    def _add_specific_variants(raw: dict[str, list[Raw]]) -> None:
        """Add the items 5etools makes from generic variants, unless an item already has the name."""
        have = {
            (str(i.get("name", "")).lower(), str(i.get("source", "")).lower())
            for i in raw.get("item", [])
        }
        generics = [g for g in raw.get("magicvariant", []) if "_copy" not in g]
        for item in magic_variants.expand(raw.get("baseitem", []), generics):
            if (item["name"].lower(), item["source"].lower()) not in have:
                raw["item"].append(item)

    def _index_nested(self, content: DeepIndexable, content_type: ContentType) -> None:
        try:
            nested = content.get_deep_index_entries(self)  # type: ignore[arg-type]
        except Exception as e:
            logger.warning(
                f"Failed to deep index nested content for {content_type.value} "
                f"'{getattr(content, 'name', '?')}': {e}"
            )
            return
        for item in nested:
            try:
                nested_type = content_type_of(item)
            except ValueError:
                # Sections, tables and insets inside content have no content type
                continue
            self._add_to_index(item, nested_type)

    # endregion

    # region Lookup

    def find(
        self, content_type: ContentType, name: str, source: str | None = None
    ) -> BaseContent | None:
        """Content by type, name and optionally source (else the first loaded).

        Class features and the like can share a name and source; this returns
        the first loaded. Use ``find_uid`` or ``find_all`` to tell them apart.
        """
        found = next(iter(self._named(content_type, name, source)), None)
        return self.hydrate(found) if found is not None else None

    def find_all(self, content_type: ContentType, name: str) -> list[BaseContent]:
        """Content of a type with this name, from every source."""
        return [self.hydrate(c) for c in self._named(content_type, name)]

    def find_uid(self, content_type: ContentType, uid: str) -> BaseContent | None:
        """Content by a 5etools uid, as in tags and ``classFeatures``.

        "Ability Score Improvement|Fighter|PHB|4" is a class feature (name,
        class, class source, level, source); subclass features, subclasses
        and deities have their own layouts (``_UID_LAYOUTS``), with 5etools'
        defaults for the parts left out. Any other type takes "name|source",
        and without a source this is ``find``.
        """
        fields = parse_uid(content_type, uid)
        found = self._match_uid(content_type, fields) if fields else None
        return self.hydrate(found) if found is not None else None

    def _match_uid(
        self, content_type: ContentType, fields: UidFields
    ) -> BaseContent | None:
        if content_type in _UID_FIRST:
            candidates = list(self._by_type.get(content_type, {}).values())
        else:
            candidates = self._named(content_type, fields["name"] or "")
        return next(
            (
                content
                for content in candidates
                if all(
                    _norm(_field(content, key)) == _norm(value)
                    for key, value in fields.items()
                    if value is not None
                )
            ),
            None,
        )

    def _named(
        self, content_type: ContentType, name: str, source: str | None = None
    ) -> list[BaseContent]:
        named = self._by_name.get(content_type, {}).get(name.lower(), [])
        if source:
            source = source.lower()
            return [c for c in named if _source(c).lower() == source]
        return list(named)

    def get_all_by_type(self, content_type: ContentType | str) -> list[BaseContent]:
        """All content of a type. Adventures and books come without their text."""
        if isinstance(content_type, str):
            try:
                content_type = ContentType(content_type)
            except ValueError:
                return []
        return list(self._by_type.get(content_type, {}).values())

    def get_all_by_source(self, source: str) -> list[BaseContent]:
        return list(self._by_source.get(source, []))

    def search(
        self, query: str, content_type: ContentType | None = None, limit: int = 50
    ) -> list[BaseContent]:
        """Content whose name contains ``query``."""
        query_lower = query.lower()
        return self._match(lambda n: query_lower in n, content_type, limit)

    def search_by_name_prefix(
        self, prefix: str, content_type: ContentType | None = None, limit: int = 20
    ) -> list[BaseContent]:
        prefix_lower = prefix.lower()
        return self._match(lambda n: n.startswith(prefix_lower), content_type, limit)

    def _match(
        self, test: Any, content_type: ContentType | None, limit: int
    ) -> list[BaseContent]:
        results: list[BaseContent] = []
        for ctype in [content_type] if content_type else list(ContentType):
            for content in self._by_type.get(ctype, {}).values():
                if test(content.name.lower()):
                    results.append(content)
                    if len(results) >= limit:
                        return results
        return results

    def get_statistics(self) -> dict[str, Any]:
        return {
            "total_items": sum(len(v) for v in self._by_type.values()),
            "by_type": {ct.value: len(v) for ct, v in self._by_type.items()},
            "by_source": {s: len(v) for s, v in self._by_source.items()},
            "loaded_types": list(self._loaded_types),
        }

    def is_loaded(self, content_type: ContentType) -> bool:
        return content_type in self._loaded_types

    def get_supported_types(self) -> list[ContentType]:
        return list(CONTENT_MODELS)

    def get_fluff_for_content(
        self, content: BaseContent, content_type: ContentType
    ) -> BaseFluff | None:
        """The fluff entry for ``content``, if one matches."""
        if content is None:
            return None
        fluff_type = _FLUFF_FOR.get(content_type)
        if fluff_type is None:
            return None
        fluff = [
            f for f in self.get_all_by_type(fluff_type) if isinstance(f, BaseFluff)
        ]
        if not fluff:
            return None
        from ..services.fluff_matcher import FluffMatcher

        try:
            return FluffMatcher(self).match_fluff_for_content(content, fluff)
        except Exception:
            logger.debug(f"Error finding fluff for {content.name}", exc_info=True)
            return None

    # endregion


_FLUFF_FOR = {
    ContentType.CREATURE: ContentType.CREATURE_FLUFF,
    ContentType.SPELL: ContentType.SPELL_FLUFF,
    ContentType.ITEM: ContentType.ITEM_FLUFF,
    ContentType.RACE: ContentType.RACE_FLUFF,
    ContentType.FEAT: ContentType.FEAT_FLUFF,
    ContentType.CLASS: ContentType.CLASS_FLUFF,
    ContentType.BACKGROUND: ContentType.BACKGROUND_FLUFF,
    ContentType.OPTIONALFEATURE: ContentType.OPTIONALFEATURE_FLUFF,
    ContentType.VEHICLE: ContentType.VEHICLE_FLUFF,
    ContentType.OBJECT: ContentType.OBJECT_FLUFF,
    ContentType.REWARD: ContentType.REWARD_FLUFF,
    ContentType.RECIPE: ContentType.RECIPE_FLUFF,
    ContentType.CHAROPTION: ContentType.CHAROPTION_FLUFF,
}


def _source(content: BaseContent) -> str:
    source = content.source
    if hasattr(source, "abbreviation"):
        return str(source.abbreviation)
    if isinstance(source, dict):
        return str(source.get("abbreviation", source))
    return str(source)


Identity = tuple[str, ...]

# What tells apart entities of a type that share a name and source, as
# 5etools keys them (``KEYS`` in merge_copy, ``UrlUtil.URL_TO_HASH_BUILDER``)
_IDENTITY: dict[ContentType, tuple[str, ...]] = {
    ContentType.CLASS_FEATURE: ("className", "classSource", "level"),
    ContentType.SUBCLASS_FEATURE: (
        "className",
        "classSource",
        "subclassShortName",
        "subclassSource",
        "level",
    ),
    ContentType.SUBCLASS: ("className", "classSource"),
    ContentType.SUBRACE: ("raceName", "raceSource"),
    ContentType.DEITY: ("pantheon",),
}

# The parts of a uid after the name, with 5etools' default for each part left
# empty (DataUtil.class.unpackUid*); a callable default reads an earlier part
UidFields = dict[str, str | None]
# Types whose uid starts with something other than the name
_UID_FIRST = {
    ContentType.SUBCLASS: "shortName",
    ContentType.ITEM_PROPERTY: "abbreviation",
}
_Default = str | Callable[[UidFields], str | None] | None
_UID_LAYOUTS: dict[ContentType, tuple[tuple[str, _Default], ...]] = {
    ContentType.CLASS_FEATURE: (
        ("className", None),
        ("classSource", "PHB"),
        ("level", None),
        ("source", lambda f: f["classSource"]),
    ),
    ContentType.SUBCLASS_FEATURE: (
        ("className", None),
        ("classSource", "PHB"),
        ("subclassShortName", None),
        ("subclassSource", "PHB"),
        ("level", None),
        ("source", lambda f: f["subclassSource"]),
    ),
    ContentType.SUBCLASS: (
        ("className", None),
        ("classSource", "PHB"),
        ("source", "PHB"),
    ),
    ContentType.DEITY: (("pantheon", None), ("source", None)),
}


def parse_uid(content_type: ContentType, uid: str) -> UidFields | None:
    """The fields a 5etools uid names, by their 5etools names.

    A subclass uid starts with the short name ("Alchemist|Artificer|EFA|EFA")
    and an item property's with its abbreviation ("2H|XPHB").
    """
    parts = [p.strip() for p in uid.split("|")]
    if not parts[0]:
        return None
    first = _UID_FIRST.get(content_type, "name")
    fields: UidFields = {first: parts[0]}
    layout = _UID_LAYOUTS.get(content_type, (("source", None),))
    for i, (key, default) in enumerate(layout, start=1):
        value = parts[i] if i < len(parts) and parts[i] else None
        if value is None:
            value = default(fields) if callable(default) else default
        fields[key] = value
    return fields


def _field(content: BaseContent, key: str) -> Any:
    """A field of ``content`` by its 5etools name."""
    if key == "source":
        return _source(content)
    for attr, info in type(content).model_fields.items():
        if key in (attr, info.alias):
            return getattr(content, attr)
    return (content.model_extra or {}).get(key)


def _norm(value: Any) -> str:
    return str(value).lower() if value is not None else ""


def _identity(content: BaseContent, content_type: ContentType) -> Identity:
    return (
        content.name.lower(),
        _source(content).lower(),
        *(_norm(_field(content, key)) for key in _IDENTITY.get(content_type, ())),
    )


def _reprint_alias(content: BaseContent, fields: UidFields) -> BaseContent | None:
    """A copy of ``content`` with the name, source and so on of its reprint."""
    alias = content.model_copy(deep=True)
    try:
        for field in ("reprinted_as", "reprintedAs"):
            if hasattr(alias, field):
                setattr(alias, field, [])
        alias.name = fields.get("name") or content.name
        alias.source.abbreviation = fields.get("source") or _source(content)
        alias.source.name = alias.source.abbreviation
        for key, value in fields.items():
            if key in ("name", "source") or value is None:
                continue
            for attr, info in type(alias).model_fields.items():
                if key in (attr, info.alias):
                    current = getattr(alias, attr)
                    setattr(
                        alias, attr, int(value) if isinstance(current, int) else value
                    )
    except (AttributeError, ValueError):
        logger.debug(f"Could not make a reprint alias of {content.name}", exc_info=True)
        return None
    return alias


def _prepare(entity: Raw, content_type: ContentType) -> Raw:
    """The fixes 5etools applies when it reads an entity, on a shallow copy."""
    entity = dict(entity)
    if "source" not in entity and isinstance(entity.get("inherits"), dict):
        entity["source"] = entity["inherits"].get("source")
    if content_type == ContentType.ITEM:
        _inherit_type_entries(entity)
    if content_type == ContentType.ITEM_PROPERTY and "name" not in entity:
        # 5etools names a property after its first entry ("Two-Handed")
        entries = entity.get("entries")
        if entries and isinstance(entries[0], dict) and entries[0].get("name"):
            entity["name"] = entries[0]["name"]
    return entity


def _inherit_type_entries(item: Raw) -> None:
    """An item with no entries of its own takes them from its type (e.g. "$G|DMG")."""
    item_type = item.get("type")
    if item.get("entries") or not isinstance(item_type, str) or "|" not in item_type:
        return
    base = item_types.get(item_type)
    if base and base.get("entries"):
        item["entries"] = base["entries"]


def _is_reference_stub(creature: Raw) -> bool:
    """An NPC entry with no stat block, only a name for other entries to point at."""
    if "ac" in creature or "hp" in creature:
        return False
    logger.debug(f"Skipping creature with no stat block: {creature.get('name')}")
    return True


def _is_race_default(subrace: Raw) -> bool:
    """A nameless subrace holds its race's defaults, for merging into the race."""
    if subrace.get("name"):
        return False
    logger.debug(
        f"Skipping nameless subrace of {subrace.get('raceName')} ({subrace.get('source')})"
    )
    return True


def _has_full_text(content: BaseContent) -> bool:
    """Homebrew can hold an adventure's text inline; don't replace it."""
    contents = getattr(content, "contents", None)
    if not contents:
        return False
    entries = getattr(contents[0], "entries", None)
    return bool(entries) and len(entries) > 3


def _liberal_fluff(entity: Raw, model: type[BaseContent]) -> BaseContent:
    """Keep what can be kept of a fluff entry that fails validation."""
    parsed: Raw = {
        "name": entity.get("name", "Unknown"),
        "source": entity.get("source", "Unknown"),
    }
    for key in ("entries", "entry", "text", "description"):
        if key in entity:
            parsed["entries"] = entity[key]
            break
    if "images" in entity:
        parsed["images"] = entity["images"]
    extra = {
        k: v
        for k, v in entity.items()
        if k not in ("name", "source", "entries", "images")
    }
    if extra:
        parsed["extra_data"] = extra
    try:
        return model.model_validate(parsed)
    except ValidationError:
        return model(name=parsed["name"], source=parsed["source"])  # type: ignore[call-arg]

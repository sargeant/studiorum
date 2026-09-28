"""Spell class lookup service for integrating gendata lookup with spell objects."""

from typing import TYPE_CHECKING, Any

from studiorum.data.models.spells import ClassReference, SpellClassList
from studiorum.log import get_logger

if TYPE_CHECKING:
    from studiorum.data.models.spells import Spell

logger = get_logger(__name__)

LOOKUP_FILE = "gendata-spell-source-lookup.json"


class SpellClassLookupService:
    """Service for looking up spell class information from gendata files."""

    def __init__(self) -> None:
        self._lookup_data: dict[str, dict[str, Any]] = {}
        self._loaded = False

    def _load_lookup_data(self) -> None:
        """Load 5etools' spell source lookup from each configured data directory."""
        if self._loaded:
            return
        self._loaded = True

        from studiorum.config import get_app_config
        from studiorum.data.loaders.data_dir import DataSet, read_json

        found = False
        for data_dir in DataSet.from_config(get_app_config().data).dirs:
            path = data_dir.root / "generated" / LOOKUP_FILE
            if not path.is_file():
                continue
            found = True
            try:
                data = read_json(path)
            except Exception as e:
                logger.error(f"Failed to load spell class lookup data from {path}: {e}")
                continue
            # The first directory wins, as for entities
            for source, spells in data.items():
                merged = self._lookup_data.setdefault(source, {})
                for name, info in spells.items():
                    merged.setdefault(name, info)
            logger.info(f"Loaded spell class lookup data from {path}")

        if not found:
            logger.warning(
                f"No data directory has generated/{LOOKUP_FILE}; "
                "spell class filtering will not work"
            )

    def get_spell_classes(
        self, spell_name: str, source: str, include_optional: bool = False
    ) -> SpellClassList | None:
        """Get class information for a spell from lookup data.

        Args:
            spell_name: Name of the spell
            source: Source abbreviation (e.g., "PHB", "XPHB")
            include_optional: Whether to include optional/variant class spells

        Returns:
            SpellClassList with class information, or None if not found
        """
        self._load_lookup_data()

        if not self._lookup_data:
            return None

        # Normalize inputs for lookup
        source_key = source.lower()
        spell_key = spell_name.lower()

        # Find the spell in the lookup data
        source_data = self._lookup_data.get(source_key, {})
        spell_data = source_data.get(spell_key, {})

        if not spell_data:
            return None

        # Extract class information
        class_data = spell_data.get("class", {})
        class_refs = []

        # Add standard class assignments
        if class_data:
            for source_book, classes in class_data.items():
                for class_name in classes.keys():
                    class_refs.append(
                        ClassReference(name=class_name, source=source_book)
                    )

        # Add optional/variant class assignments if requested
        if include_optional:
            class_variant_data = spell_data.get("classVariant", {})
            if class_variant_data:
                for source_book, classes in class_variant_data.items():
                    for class_name in classes.keys():
                        class_refs.append(
                            ClassReference(name=class_name, source=source_book)
                        )

        if not class_refs:
            return None

        return SpellClassList(fromClassList=class_refs)

    def enhance_spell(self, spell: "Spell", include_optional: bool = False) -> "Spell":
        """Enhance a spell object with class information from lookup data.

        Args:
            spell: Spell object to enhance
            include_optional: Whether to include optional/variant class spells

        Returns:
            Enhanced spell object
        """
        if not hasattr(spell, "name") or not hasattr(spell, "source"):
            return spell

        # Skip if spell already has class information
        if spell.classes is not None:
            return spell

        # Get source abbreviation
        source_abbrev = getattr(spell.source, "abbreviation", str(spell.source))

        # Look up class information
        class_list = self.get_spell_classes(spell.name, source_abbrev, include_optional)

        if class_list:
            try:
                # Try to directly set the classes attribute if possible
                if hasattr(spell, "__dict__") and "classes" in spell.__dict__:
                    spell.classes = class_list
                    return spell

                # Fallback: try to create a new object with the class information
                if hasattr(spell, "model_copy"):
                    # Pydantic v2 approach
                    return spell.model_copy(update={"classes": class_list})
                if hasattr(spell, "copy"):
                    # Pydantic v1 approach
                    return spell.copy(update={"classes": class_list})
                # Last resort: try model_validate with existing data plus classes
                spell_dict = (
                    spell.model_dump()
                    if hasattr(spell, "model_dump")
                    else spell.__dict__.copy()
                )
                spell_dict["classes"] = class_list.model_dump()

                spell_class = type(spell)
                return spell_class.model_validate(spell_dict)

            except Exception as e:
                logger.debug(
                    f"Failed to enhance spell {spell.name} with class data: {e}"
                )
                return spell

        return spell


# Global service instance
_spell_class_lookup_service: SpellClassLookupService | None = None


def get_spell_class_lookup_service() -> SpellClassLookupService:
    """Get the global spell class lookup service instance."""
    global _spell_class_lookup_service
    if _spell_class_lookup_service is None:
        _spell_class_lookup_service = SpellClassLookupService()
    return _spell_class_lookup_service


def reset() -> None:
    global _spell_class_lookup_service
    _spell_class_lookup_service = None

"""Spell class lookup service for integrating gendata lookup with spell objects."""

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ..logging import get_logger
from ..models.spells import ClassReference, SpellClassList

if TYPE_CHECKING:
    from ..models.spells import Spell

logger = get_logger(__name__)


class SpellClassLookupService:
    """Service for looking up spell class information from gendata files."""

    def __init__(self) -> None:
        self._lookup_data: dict[str, dict[str, Any]] = {}
        self._loaded = False

    def _load_lookup_data(self) -> None:
        """Load the spell class lookup data from gendata files."""
        if self._loaded:
            return

        # Try to find the gendata file in common locations
        possible_paths = [
            # 5etools-src repo location
            Path(
                "~/Code/5etools-src/data/generated/gendata-spell-source-lookup.json"
            ).expanduser(),
            # Cache location
            Path(
                "~/.cache/5e2pdf/5etools/data/generated/gendata-spell-source-lookup.json"
            ).expanduser(),
        ]

        lookup_file = None
        for path in possible_paths:
            if path.exists():
                lookup_file = path
                break

        if not lookup_file:
            logger.warning(
                "Spell class lookup file not found. Class filtering will not work."
            )
            self._loaded = True
            return

        try:
            with lookup_file.open("r", encoding="utf-8") as f:
                self._lookup_data = json.load(f)
            logger.info(f"Loaded spell class lookup data from {lookup_file}")
        except Exception as e:
            logger.error(f"Failed to load spell class lookup data: {e}")

        self._loaded = True

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
                elif hasattr(spell, "copy"):
                    # Pydantic v1 approach
                    return spell.copy(update={"classes": class_list})
                else:
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

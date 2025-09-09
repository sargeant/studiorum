"""FluffMatcher service for matching content with their corresponding fluff entries."""

import re
from typing import TYPE_CHECKING, Any, TypeVar, cast

if TYPE_CHECKING:
    from ..loaders.omnidexer import Omnidexer

from ..logging import get_logger
from ..models.content import BaseContent
from ..models.creatures import Creature
from ..models.fluff import (
    BaseFluff,
    CreatureFluff,
    ItemFluff,
    SpellFluff,
)
from ..models.items import Item
from ..models.spells import Spell

logger = get_logger(__name__)

T = TypeVar("T", bound=BaseContent)
F = TypeVar("F", bound=BaseFluff)


class FluffMatcher:
    """Service for matching 5e content with their fluff entries.

    This service handles the complex task of matching game content
    (creatures, spells, items) with their narrative fluff entries,
    including handling name variations, source preferences, and
    5etools _copy references.

    Phase 5 features:
    - Selective section filtering for fluff content
    - Source filtering options
    - Enhanced image extraction capabilities
    """

    def __init__(self, omnidexer: "Omnidexer") -> None:
        """Initialize the FluffMatcher with an omnidexer instance.

        Args:
            omnidexer: The omnidexer instance for content lookup
        """
        self.omnidexer = omnidexer
        self._copy_cache: dict[str, BaseFluff] = {}

    def match_creature_fluff(
        self,
        creature: Creature,
        fluff_entries: list[CreatureFluff] | None = None,
        allowed_sections: list[str] | None = None,
        allowed_sources: list[str] | None = None,
    ) -> CreatureFluff | None:
        """Match a creature to its fluff entry with optional filtering.

        Args:
            creature: The creature to find fluff for
            fluff_entries: Optional list of fluff entries to search in.
                          If None, will retrieve all creature fluff from omnidexer.
            allowed_sections: Optional list of section names to include (e.g., ['lair', 'tactics'])
            allowed_sources: Optional list of source abbreviations to filter by

        Returns:
            The matching CreatureFluff entry, or None if no match found
        """
        if fluff_entries is None:
            all_fluff = self.omnidexer.get_all_by_type("creatureFluff")
            fluff_entries = [f for f in all_fluff if isinstance(f, CreatureFluff)]

        # Apply source filtering if requested
        if allowed_sources:
            fluff_entries = [
                f
                for f in fluff_entries
                if f.source.abbreviation.upper() in [s.upper() for s in allowed_sources]
            ]

        logger.debug(
            f"Matching creature fluff for '{creature.name}' from {creature.source.abbreviation}"
        )

        matched_fluff = cast(
            CreatureFluff | None, self.match_fluff_for_content(creature, fluff_entries)
        )

        # Apply section filtering if requested
        if matched_fluff and allowed_sections:
            matched_fluff = self._filter_fluff_sections(matched_fluff, allowed_sections)

        return matched_fluff

    def match_spell_fluff(
        self,
        spell: Spell,
        fluff_entries: list[SpellFluff] | None = None,
        allowed_sections: list[str] | None = None,
        allowed_sources: list[str] | None = None,
    ) -> SpellFluff | None:
        """Match a spell to its fluff entry with optional filtering.

        Args:
            spell: The spell to find fluff for
            fluff_entries: Optional list of fluff entries to search in.
                          If None, will retrieve all spell fluff from omnidexer.
            allowed_sections: Optional list of section names to include
            allowed_sources: Optional list of source abbreviations to filter by

        Returns:
            The matching SpellFluff entry, or None if no match found
        """
        if fluff_entries is None:
            all_fluff = self.omnidexer.get_all_by_type("spellFluff")
            fluff_entries = [f for f in all_fluff if isinstance(f, SpellFluff)]

        # Apply source filtering if requested
        if allowed_sources:
            fluff_entries = [
                f
                for f in fluff_entries
                if f.source.abbreviation.upper() in [s.upper() for s in allowed_sources]
            ]

        logger.debug(
            f"Matching spell fluff for '{spell.name}' from {spell.source.abbreviation}"
        )

        matched_fluff = cast(
            SpellFluff | None, self.match_fluff_for_content(spell, fluff_entries)
        )

        # Apply section filtering if requested
        if matched_fluff and allowed_sections:
            matched_fluff = self._filter_fluff_sections(matched_fluff, allowed_sections)

        return matched_fluff

    def match_item_fluff(
        self,
        item: Item,
        fluff_entries: list[ItemFluff] | None = None,
        allowed_sections: list[str] | None = None,
        allowed_sources: list[str] | None = None,
    ) -> ItemFluff | None:
        """Match an item to its fluff entry with optional filtering.

        Args:
            item: The item to find fluff for
            fluff_entries: Optional list of fluff entries to search in.
                          If None, will retrieve all item fluff from omnidexer.
            allowed_sections: Optional list of section names to include
            allowed_sources: Optional list of source abbreviations to filter by

        Returns:
            The matching ItemFluff entry, or None if no match found
        """
        if fluff_entries is None:
            all_fluff = self.omnidexer.get_all_by_type("itemFluff")
            fluff_entries = [f for f in all_fluff if isinstance(f, ItemFluff)]

        # Apply source filtering if requested
        if allowed_sources:
            fluff_entries = [
                f
                for f in fluff_entries
                if f.source.abbreviation.upper() in [s.upper() for s in allowed_sources]
            ]

        logger.debug(
            f"Matching item fluff for '{item.name}' from {item.source.abbreviation}"
        )

        matched_fluff = cast(
            ItemFluff | None, self.match_fluff_for_content(item, fluff_entries)
        )

        # Apply section filtering if requested
        if matched_fluff and allowed_sections:
            matched_fluff = self._filter_fluff_sections(matched_fluff, allowed_sections)

        return matched_fluff

    def match_fluff_for_content(self, content: T, fluff_entries: list[F]) -> F | None:
        """Generic method to match any content type with its fluff entries.

        Args:
            content: The content to find fluff for
            fluff_entries: List of fluff entries to search in

        Returns:
            The matching fluff entry, or None if no match found
        """
        if not fluff_entries:
            logger.debug(f"No fluff entries provided for {content.name}")
            return None

        # Strategy 1: Exact name + source match (highest priority)
        match = self._find_exact_match(content, fluff_entries)
        if match:
            logger.debug(
                f"Found exact match for {content.name} ({content.source.abbreviation})"
            )
            return self._resolve_copy_reference(match)

        # Strategy 2: Exact name, any source (fallback)
        match = self._find_name_only_match(content, fluff_entries)
        if match:
            logger.debug(
                f"Found name-only match for {content.name} from {match.source.abbreviation}"
            )
            return self._resolve_copy_reference(match)

        # Strategy 3: Fuzzy name matching with source preference
        match = self._find_fuzzy_match(content, fluff_entries)
        if match:
            logger.debug(
                f"Found fuzzy match for {content.name}: '{match.name}' from {match.source.abbreviation}"
            )
            return self._resolve_copy_reference(match)

        logger.debug(
            f"No fluff match found for {content.name} ({content.source.abbreviation})"
        )
        return None

    def _find_exact_match(self, content: T, fluff_entries: list[F]) -> F | None:
        """Find exact name and source match."""
        content_name = self._normalize_name(content.name)
        content_source = content.source.abbreviation

        for fluff in fluff_entries:
            if (
                self._normalize_name(fluff.name) == content_name
                and fluff.source.abbreviation == content_source
            ):
                return fluff

        return None

    def _find_name_only_match(self, content: T, fluff_entries: list[F]) -> F | None:
        """Find exact name match from any source, preferring same source."""
        content_name = self._normalize_name(content.name)
        content_source = content.source.abbreviation

        matches = []
        for fluff in fluff_entries:
            if self._normalize_name(fluff.name) == content_name:
                matches.append(fluff)

        if not matches:
            return None

        # Prefer same source if available
        same_source_matches = [
            m for m in matches if m.source.abbreviation == content_source
        ]
        if same_source_matches:
            return same_source_matches[0]

        # Return first match from any source
        return matches[0]

    def _find_fuzzy_match(self, content: T, fluff_entries: list[F]) -> F | None:
        """Find fuzzy name match with common variations."""
        content_name = self._normalize_name(content.name)
        content_source = content.source.abbreviation

        # Generate name variations
        variations = self._generate_name_variations(content_name)

        # Find all fuzzy matches
        matches = []
        for fluff in fluff_entries:
            fluff_name = self._normalize_name(fluff.name)
            fluff_variations = self._generate_name_variations(fluff_name)

            # Check if any variation matches
            if any(var in fluff_variations for var in variations):
                matches.append(fluff)

        if not matches:
            return None

        # Prefer same source if available
        same_source_matches = [
            m for m in matches if m.source.abbreviation == content_source
        ]
        if same_source_matches:
            return same_source_matches[0]

        # Return first match from any source
        return matches[0]

    def _normalize_name(self, name: str) -> str:
        """Normalize a name for comparison."""
        # Convert to lowercase and remove extra whitespace
        normalized = re.sub(r"\s+", " ", name.strip().lower())

        # Remove common formatting characters
        normalized = normalized.replace("'", "").replace('"', "")

        return normalized

    def _generate_name_variations(self, name: str) -> set[str]:
        """Generate common name variations for fuzzy matching."""
        variations = {name}

        # Remove "the" prefix
        if name.startswith("the "):
            variations.add(name[4:])
        else:
            variations.add(f"the {name}")

        # Handle plural variations
        if name.endswith("s") and len(name) > 1:
            # Remove potential plural
            singular = name[:-1]
            variations.add(singular)
            # Handle "ies" -> "y" pattern
            if singular.endswith("ie"):
                variations.add(singular[:-2] + "y")
        else:
            # Add potential plural
            if name.endswith("y"):
                variations.add(name[:-1] + "ies")
            else:
                variations.add(name + "s")

        # Handle common abbreviations and expansions
        # This could be expanded with more domain-specific patterns
        common_expansions = {
            "dr": "doctor",
            "st": "saint",
            "&": "and",
        }

        for abbrev, expansion in common_expansions.items():
            if abbrev in name:
                variations.add(name.replace(abbrev, expansion))
            if expansion in name:
                variations.add(name.replace(expansion, abbrev))

        return variations

    def _resolve_copy_reference(self, fluff: F) -> F:
        """Resolve _copy references in fluff entries.

        Args:
            fluff: The fluff entry that may contain a _copy reference

        Returns:
            The resolved fluff entry (either the original or the referenced entry)
        """
        # Check if this fluff has a _copy reference
        if not hasattr(fluff, "__dict__") or not hasattr(fluff, "extra_data"):
            return fluff

        # Check for _copy in the raw dict or extra_data
        copy_ref = None
        if hasattr(fluff, "__pydantic_extra__"):
            copy_ref = getattr(fluff, "__pydantic_extra__", {}).get("_copy")

        if not copy_ref and hasattr(fluff, "extra_data"):
            copy_ref = fluff.extra_data.get("_copy")

        # Try to access _copy directly if no extra data mechanism
        if not copy_ref:
            try:
                copy_ref = getattr(fluff, "_copy", None)
            except AttributeError:
                pass

        if not copy_ref:
            return fluff

        # Prevent infinite recursion
        cache_key = f"{fluff.name}:{fluff.source.abbreviation}"
        if cache_key in self._copy_cache:
            return cast(F, self._copy_cache[cache_key])

        # Add to cache early to prevent cycles
        self._copy_cache[cache_key] = fluff

        # Extract reference info
        if not isinstance(copy_ref, dict):
            logger.debug(f"Invalid _copy reference format in {fluff.name}")
            return fluff

        ref_name = copy_ref.get("name")
        ref_source = copy_ref.get("source")

        if not ref_name or not ref_source:
            logger.debug(f"Incomplete _copy reference in {fluff.name}")
            return fluff

        logger.debug(
            f"Resolving _copy reference: {fluff.name} -> {ref_name} ({ref_source})"
        )

        # Find the referenced fluff entry
        # Get the appropriate fluff type based on the current fluff's type
        fluff_type = type(fluff).__name__.replace("Fluff", "").lower() + "Fluff"

        try:
            all_fluff = self.omnidexer.get_all_by_type(fluff_type)
            referenced_fluff_candidates = [
                f
                for f in all_fluff
                if isinstance(f, type(fluff))
                and self._normalize_name(f.name) == self._normalize_name(ref_name)
                and f.source.abbreviation == ref_source
            ]

            if referenced_fluff_candidates:
                referenced_fluff = referenced_fluff_candidates[0]
                # Recursively resolve in case the referenced entry also has _copy
                resolved = self._resolve_copy_reference(cast(F, referenced_fluff))
                self._copy_cache[cache_key] = resolved
                return cast(F, resolved)
            else:
                logger.debug(
                    f"Referenced fluff not found: {ref_name} ({ref_source}) for {fluff.name}"
                )

        except Exception as e:
            logger.debug(f"Error resolving _copy reference for {fluff.name}: {e}")

        # Return original if reference resolution fails
        return fluff

    def _filter_fluff_sections(self, fluff: F, allowed_sections: list[str]) -> F:
        """Filter fluff entries to only include specified sections.

        Args:
            fluff: The fluff entry to filter
            allowed_sections: List of section names to include

        Returns:
            A copy of the fluff with only the allowed sections
        """
        if not allowed_sections:
            return fluff

        # Convert allowed sections to lowercase for comparison
        allowed_lower = {section.lower() for section in allowed_sections}

        # Filter entries based on section names/types
        filtered_entries = []
        for entry in fluff.entries:
            # Check if entry has a name that matches allowed sections
            if entry.name:
                entry_name = entry.name.lower()
                if any(allowed in entry_name for allowed in allowed_lower):
                    filtered_entries.append(entry)
            # Check if entry has a type that matches allowed sections
            elif entry.type:
                entry_type = entry.type.lower()
                if entry_type in allowed_lower:
                    filtered_entries.append(entry)
            # For entries without specific names/types, check content for section keywords
            elif entry.content:
                content_lower = str(entry.content).lower()
                if any(allowed in content_lower for allowed in allowed_lower):
                    filtered_entries.append(entry)

        # Create a copy of the fluff with filtered entries
        # Use model_copy to preserve all other attributes
        if hasattr(fluff, "model_copy"):
            filtered_fluff = fluff.model_copy(update={"entries": filtered_entries})
        else:
            # Fallback for older Pydantic versions
            fluff_data = fluff.model_dump()
            if isinstance(fluff_data, dict):
                fluff_data["entries"] = filtered_entries
                # Use cast to help pyright understand the type is correct
                filtered_fluff = cast(F, fluff.__class__(**fluff_data))
            else:
                # If model_dump doesn't return a dict, fall back to basic construction
                # Build kwargs safely with proper types
                constructor_kwargs: dict[str, Any] = {
                    "name": fluff.name,
                    "source": fluff.source,
                    "entries": filtered_entries,
                }

                # Add optional fields if they exist
                if hasattr(fluff, "images"):
                    constructor_kwargs["images"] = fluff.images

                # Add any extra fields that exist in the original model
                extra_data = getattr(fluff, "extra_data", {})
                if isinstance(extra_data, dict):
                    constructor_kwargs.update(extra_data)

                # Use cast to help pyright understand we're creating the right type
                filtered_fluff = cast(F, fluff.__class__(**constructor_kwargs))

        return cast(F, filtered_fluff)

    def get_fluff_sections(self, fluff: BaseFluff) -> list[str]:
        """Extract available section names from a fluff entry.

        Args:
            fluff: The fluff entry to analyze

        Returns:
            List of available section names/types
        """
        sections = set()

        for entry in fluff.entries:
            if entry.name:
                sections.add(entry.name.lower())
            elif entry.type:
                sections.add(entry.type.lower())

        return sorted(list(sections))

    def extract_fluff_images(self, fluff: BaseFluff) -> list[dict[str, Any]]:
        """Extract image information from fluff content.

        Args:
            fluff: The fluff entry to extract images from

        Returns:
            List of image information dictionaries with path, credit, etc.
        """
        images = []

        # Extract images from the images field
        for img in fluff.images:
            image_info = {
                "type": img.type,
                "path": img.get_path(),
                "credit": img.credit,
                "source_fluff": fluff.name,
                "source_abbreviation": fluff.source.abbreviation,
            }
            if image_info["path"]:  # Only include if we have a valid path
                images.append(image_info)

        # Also check entries for embedded image references
        for entry in fluff.entries:
            if entry.type == "image" and hasattr(entry, "href"):
                # Handle entries that might reference images
                entry_dict = (
                    entry.model_dump()
                    if hasattr(entry, "model_dump")
                    else entry.__dict__
                )
                if "href" in entry_dict:
                    image_info = {
                        "type": "image",
                        "path": entry_dict.get("href", {}).get("path")
                        if isinstance(entry_dict.get("href"), dict)
                        else None,
                        "credit": entry_dict.get("credit"),
                        "source_fluff": fluff.name,
                        "source_abbreviation": fluff.source.abbreviation,
                    }
                    if image_info["path"]:
                        images.append(image_info)

        return images

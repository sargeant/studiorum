"""Copy reference resolver for 5etools _copy templates."""

import copy
import re
from typing import Any

from ..logging import get_logger
from ..models.content import ContentType

logger = get_logger(__name__)


class CopyResolver:
    """Resolves _copy references after all data has been loaded."""

    def __init__(self, omnidexer):
        """Initialize with an omnidexer for finding copy sources."""
        self._omnidexer = omnidexer

    def resolve_copies_in_omnidexer(self) -> None:
        """Resolve all pending copy references in the omnidexer."""
        # Get all content that needs copy resolution
        items_needing_resolution = []

        for content_type in [
            ContentType.CREATURE,
            ContentType.ITEM,
            ContentType.SPELL,
        ]:  # Add other types as needed
            try:
                all_items = self._omnidexer.get_all_by_type(content_type)
                for item in all_items:
                    if hasattr(item, "_needsCopyResolution") or (
                        hasattr(item, "__dict__")
                        and item.__dict__.get("_needsCopyResolution")
                    ):
                        items_needing_resolution.append((content_type, item))
            except Exception as e:
                logger.debug(f"Could not get items of type {content_type}: {e}")
                continue

        logger.info(
            f"Found {len(items_needing_resolution)} items needing copy resolution"
        )

        # Resolve each item
        resolved_count = 0
        for content_type, item in items_needing_resolution:
            try:
                item_name = getattr(item, "name", "unknown")
                if item_name == "Zastra":
                    logger.info("Processing Zastra for copy resolution...")
                if self._resolve_copy_for_item(item):
                    resolved_count += 1
                    if item_name == "Zastra":
                        logger.info("Successfully resolved Zastra")
            except Exception as e:
                item_name = getattr(item, "name", "unknown")
                logger.warning(f"Failed to resolve copy for {item_name}: {e}")
                if item_name == "Zastra":
                    logger.error(f"Zastra resolution failed: {e}")

        logger.info(f"Successfully resolved {resolved_count} copy references")

    def _resolve_copy_for_item(self, item) -> bool:
        """Resolve copy reference for a single item."""
        # Get the raw _copy data
        copy_ref = None
        if hasattr(item, "_copy"):
            copy_ref = item._copy
        elif hasattr(item, "__dict__") and "_copy" in item.__dict__:
            copy_ref = item.__dict__["_copy"]

        if not copy_ref or not isinstance(copy_ref, dict):
            return False

        item_name = getattr(item, "name", "unknown")

        # Find the source item to copy from
        source_item = self._find_copy_source(copy_ref, item_name)
        if not source_item:
            return False

        # Convert items to dicts for processing
        source_dict = self._item_to_dict(source_item)
        target_dict = self._item_to_dict(item)

        # Create base copy (source properties as base, target properties override)
        # For copy operations, most fields should come from source (base creature)
        # Only specific fields from target should override (like alignment, specific traits)
        resolved_dict = source_dict.copy()

        # Override with specific target properties, but exclude placeholder fields
        placeholder_fields = {
            "ac",
            "hp",
            "speed",
            "strength",
            "dexterity",
            "constitution",
            "intelligence",
            "wisdom",
            "charisma",
            "save",
            "skill",
            "resist",
            "immune",
            "conditionImmune",
            "senses",
            "passive",
            "cr",
            "trait",
            "action",
            "reaction",
            "legendary",
            "mythic",
            "spellcasting",
        }

        for key, value in target_dict.items():
            # Include copy metadata and specific overrides, but skip placeholder stats
            # Also exclude copy processing attributes that should be cleaned up
            if (
                key.startswith("_")
                and key
                not in {"_copy", "_needsCopyResolution"}  # Exclude cleanup attributes
                or key
                in {
                    "name",
                    "source",
                    "alignment",
                    "isNpc",
                    "isNamedCreature",
                    "hasToken",
                }
                or key not in placeholder_fields
            ):
                resolved_dict[key] = value

        # Apply _mod transformations if present
        if "_mod" in copy_ref:
            try:
                resolved_dict = self._apply_mod_transformations(
                    resolved_dict, copy_ref["_mod"], item_name
                )
            except Exception as e:
                logger.warning(
                    f"Failed to apply _mod transformations for {item_name}: {e}"
                )

        # TODO: Handle _templates if present

        # Update the item with resolved data
        self._update_item_from_dict(item, resolved_dict)

        # IMMEDIATE cleanup after update - explicit removal of copy processing attributes
        # Do this by setting them to None and then deleting
        for attr in ["_copy", "_needsCopyResolution"]:
            if hasattr(item, attr):
                setattr(item, attr, None)  # Clear the value
                delattr(item, attr)  # Remove the attribute

        # Remove from __dict__ as well if present
        if hasattr(item, "__dict__"):
            item.__dict__.pop("_copy", None)
            item.__dict__.pop("_needsCopyResolution", None)

        # Mark as copy
        item._isCopy = True

        # CRITICAL: Update omnidexer index to reflect the resolved item
        # The omnidexer creates new instances on each find(), so we need to
        # update the indexed content to ensure future finds return the resolved version
        self._update_omnidexer_index(item)

        logger.debug(f"Resolved copy for {item_name}")
        return True

    def _find_copy_source(self, copy_ref: dict[str, Any], item_name: str):
        """Find the source item to copy from."""
        if "name" in copy_ref and "source" in copy_ref:
            # Creature-to-creature copy
            source_name = copy_ref["name"]
            source_source = copy_ref["source"]

            # Try creature first
            source_item = self._omnidexer.find(
                ContentType.CREATURE, source_name, source_source
            )
            if source_item:
                return source_item

            # Try other content types if needed
            for content_type in [ContentType.ITEM, ContentType.SPELL]:
                source_item = self._omnidexer.find(
                    content_type, source_name, source_source
                )
                if source_item:
                    return source_item

            logger.warning(
                f"Could not find copy source {source_name}|{source_source} for {item_name}"
            )
            return None
        else:
            logger.warning(f"Invalid copy reference format for {item_name}")
            return None

    def _item_to_dict(self, item) -> dict[str, Any]:
        """Convert an item to a dictionary for processing."""
        if isinstance(item, dict):
            return item.copy()
        elif hasattr(item, "model_dump"):
            return item.model_dump()
        elif hasattr(item, "__dict__"):
            return item.__dict__.copy()
        else:
            # Fallback
            try:
                return dict(item)
            except (TypeError, ValueError):
                logger.warning(f"Could not convert item to dict: {type(item)}")
                return {}

    def _update_item_from_dict(self, item, data: dict[str, Any]) -> None:
        """Update an item with data from a dictionary."""
        # Remove the copy markers from the data
        data = data.copy()
        data.pop("_copy", None)
        data.pop("_needsCopyResolution", None)

        if hasattr(item, "__dict__"):
            # Update the item's attributes
            for key, value in data.items():
                setattr(item, key, value)
        else:
            logger.warning(f"Could not update item of type {type(item)}")

    def _apply_mod_transformations(
        self, item: dict[str, Any], mod_data: dict[str, Any], item_name: str
    ) -> dict[str, Any]:
        """Apply _mod transformations to a copied item."""
        # Create a deep copy to avoid modifying the original
        modified_item = copy.deepcopy(item)

        for prop_path, transformations in mod_data.items():
            # Ensure transformations is a list
            if isinstance(transformations, dict):
                transformations = [transformations]
            elif not isinstance(transformations, list):
                logger.warning(
                    f"Invalid _mod format for {item_name}: {prop_path} should be dict or list"
                )
                continue

            for transform in transformations:
                if not isinstance(transform, dict):
                    continue

                mode = transform.get("mode")
                if mode == "replaceTxt":
                    self._apply_replace_txt_transformation(
                        modified_item, prop_path, transform, item_name
                    )
                elif mode == "appendArr":
                    self._apply_append_arr_transformation(
                        modified_item, prop_path, transform, item_name
                    )
                else:
                    logger.debug(f"Unsupported _mod mode '{mode}' for {item_name}")

        return modified_item

    def _apply_replace_txt_transformation(
        self,
        item: dict[str, Any],
        prop_path: str,
        transform: dict[str, Any],
        item_name: str,
    ) -> None:
        """Apply replaceTxt transformation to an item."""
        replace_text = transform.get("replace", "")
        with_text = transform.get("with", "")
        flags_str = transform.get("flags", "")

        # Convert flags string to re flags
        flags = 0
        if "i" in flags_str:
            flags |= re.IGNORECASE
        if "m" in flags_str:
            flags |= re.MULTILINE
        if "s" in flags_str:
            flags |= re.DOTALL

        pattern = re.compile(replace_text, flags)

        if prop_path == "*":
            # Apply to all string properties recursively
            self._replace_text_recursive(item, pattern, with_text)
        else:
            # Apply to specific property
            self._replace_text_in_property(item, prop_path, pattern, with_text)

    def _replace_text_recursive(
        self, obj: Any, pattern: re.Pattern, replacement: str
    ) -> None:
        """Recursively replace text in all string values."""
        if isinstance(obj, str):
            # This shouldn't happen as we're called on containers, but handle it
            return pattern.sub(replacement, obj)
        elif isinstance(obj, dict):
            for key, value in obj.items():
                if isinstance(value, str):
                    obj[key] = pattern.sub(replacement, value)
                elif isinstance(value, dict | list):
                    self._replace_text_recursive(value, pattern, replacement)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                if isinstance(item, str):
                    obj[i] = pattern.sub(replacement, item)
                elif isinstance(item, dict | list):
                    self._replace_text_recursive(item, pattern, replacement)

    def _replace_text_in_property(
        self,
        item: dict[str, Any],
        prop_path: str,
        pattern: re.Pattern,
        replacement: str,
    ) -> None:
        """Replace text in a specific property path."""
        # Navigate to the property
        path_parts = prop_path.split(".")
        current = item

        # Navigate to the parent of the target property
        for part in path_parts[:-1]:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return  # Property path doesn't exist

        # Apply replacement to the final property
        final_prop = path_parts[-1]
        if isinstance(current, dict) and final_prop in current:
            target = current[final_prop]
            if isinstance(target, str):
                current[final_prop] = pattern.sub(replacement, target)
            elif isinstance(target, dict | list):
                self._replace_text_recursive(target, pattern, replacement)

    def _apply_append_arr_transformation(
        self,
        item: dict[str, Any],
        prop_path: str,
        transform: dict[str, Any],
        item_name: str,
    ) -> None:
        """Apply appendArr transformation to an item."""
        items_to_append = transform.get("items")
        if not items_to_append:
            return

        # Navigate to the property
        path_parts = prop_path.split(".")
        current = item

        # Navigate to the parent of the target property
        for part in path_parts[:-1]:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return  # Property path doesn't exist

        # Append to the final property
        final_prop = path_parts[-1]
        if isinstance(current, dict):
            if final_prop not in current:
                current[final_prop] = []
            elif not isinstance(current[final_prop], list):
                return  # Property exists but is not a list

            if isinstance(items_to_append, list):
                current[final_prop].extend(items_to_append)
            else:
                current[final_prop].append(items_to_append)

    def _update_omnidexer_index(self, resolved_item) -> None:
        """Update the omnidexer index with the resolved item.

        This is critical because the omnidexer creates new instances on each find(),
        so we need to replace the indexed content with the resolved version.
        """
        try:
            # Get the item's lookup information
            item_name = getattr(resolved_item, "name", None)
            item_source = getattr(resolved_item, "source", None)

            if not item_name or not item_source:
                logger.warning(
                    f"Cannot update index: missing name or source for {resolved_item}"
                )
                return

            # Extract source abbreviation (source can be a Source object or dict)
            if hasattr(item_source, "abbreviation"):
                source_abbrev = item_source.abbreviation
            elif isinstance(item_source, dict) and "abbreviation" in item_source:
                source_abbrev = item_source["abbreviation"]
            elif isinstance(item_source, str):
                source_abbrev = item_source
            else:
                logger.warning(f"Cannot extract source abbreviation from {item_source}")
                return

            # Find the content type
            content_type = None
            # Try to determine content type from the item
            from ..models.content import ContentType

            if hasattr(resolved_item, "__class__"):
                class_name = resolved_item.__class__.__name__.lower()
                if "creature" in class_name:
                    content_type = ContentType.CREATURE
                elif "item" in class_name:
                    content_type = ContentType.ITEM
                elif "spell" in class_name:
                    content_type = ContentType.SPELL

            if not content_type:
                logger.warning(f"Cannot determine content type for {item_name}")
                return

            # Access omnidexer internal structures to update the index
            # This is a direct manipulation of internal state, but necessary
            # to ensure the resolved item is returned by future find() calls

            # Create lookup key (matches omnidexer format)
            lookup_key = f"{item_name}|{source_abbrev}".lower()

            # Update the type-based index
            if content_type in self._omnidexer._by_type:
                type_index = self._omnidexer._by_type[content_type]
                if lookup_key in type_index:
                    index_entry = type_index[lookup_key]
                    # Replace the content in the index entry
                    old_ac = getattr(index_entry.content, "ac", "unknown")
                    index_entry.content = resolved_item
                    new_ac = getattr(index_entry.content, "ac", "unknown")
                    logger.info(
                        f"Updated omnidexer index for {item_name} ({content_type}): AC {old_ac} -> {new_ac}"
                    )

                    # Clear cache for this specific item to ensure fresh lookups
                    self._clear_omnidexer_cache_for_item(
                        item_name, source_abbrev, content_type
                    )

                else:
                    logger.warning(
                        f"Lookup key {lookup_key} not found in {content_type} index"
                    )
            else:
                logger.warning(f"Content type {content_type} not found in omnidexer")

        except Exception as e:
            item_name = getattr(resolved_item, "name", "unknown")
            logger.warning(f"Failed to update omnidexer index for {item_name}: {e}")

    def _clear_omnidexer_cache_for_item(
        self, name: str, source: str, content_type
    ) -> None:
        """Clear omnidexer cache entries for a specific item.

        The omnidexer uses @cached decorator on _find_cached, so we need to
        clear the cache to ensure updated items are returned.
        """
        try:
            from ..cache import CacheManager

            # The cache key format matches the one in omnidexer._find_cached
            cache_key_exact = f"omnidexer:find:{content_type.value}:{name}:{source}:deep={self._omnidexer.enable_deep_indexing}"
            cache_key_any = f"omnidexer:find:{content_type.value}:{name}:any:deep={self._omnidexer.enable_deep_indexing}"

            cache = CacheManager.get_instance()

            # Clear both exact and 'any' source lookups
            if cache_key_exact in cache:
                del cache[cache_key_exact]
                logger.debug(f"Cleared cache for {name}|{source}")

            if cache_key_any in cache:
                del cache[cache_key_any]
                logger.debug(f"Cleared cache for {name}|any")

        except Exception as e:
            logger.warning(f"Failed to clear cache for {name}: {e}")

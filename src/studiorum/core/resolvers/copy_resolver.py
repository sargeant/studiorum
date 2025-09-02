"""Copy reference resolver for 5etools _copy templates."""

import copy
import re
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from ..loaders.omnidexer import Omnidexer

from ..logging import get_logger
from ..models.content import ContentType

logger = get_logger(__name__)


class CopyResolver:
    """Resolves _copy references after all data has been loaded."""

    def __init__(self, omnidexer: "Omnidexer") -> None:
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
                    needs_resolution = False
                    # Check in __pydantic_extra__ first (proper way for pydantic models)
                    if (
                        hasattr(item, "__pydantic_extra__")
                        and item.__pydantic_extra__
                        and item.__pydantic_extra__.get("_needsCopyResolution")
                    ):
                        needs_resolution = True
                    # Fallback to direct attribute check
                    elif hasattr(item, "_needsCopyResolution") or (
                        hasattr(item, "__dict__")
                        and item.__dict__.get("_needsCopyResolution")
                    ):
                        needs_resolution = True

                    if needs_resolution:
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
                if self._resolve_copy_for_item(item):
                    resolved_count += 1
            except Exception as e:
                item_name = getattr(item, "name", "unknown")
                logger.warning(f"Failed to resolve copy for {item_name}: {e}")

        logger.info(f"Successfully resolved {resolved_count} copy references")

    def _resolve_copy_for_item(self, item: Any) -> bool:
        """Resolve copy reference for a single item."""
        # Get the raw _copy data
        copy_ref = None
        # Check in __pydantic_extra__ first (proper way for pydantic models)
        if (
            hasattr(item, "__pydantic_extra__")
            and item.__pydantic_extra__
            and "_copy" in item.__pydantic_extra__
        ):
            copy_ref = item.__pydantic_extra__["_copy"]
        # Fallback to direct attribute check
        elif hasattr(item, "_copy"):
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

        # Apply copy resolution directly to preserve typed objects
        # This approach avoids dictionary conversion that would lose type information
        self._apply_copy_resolution_direct(item, source_item, copy_ref, item_name)

        # IMMEDIATE cleanup after update - explicit removal of copy processing attributes
        # Remove from __pydantic_extra__ first (proper way for pydantic models)
        if hasattr(item, "__pydantic_extra__"):
            item.__pydantic_extra__.pop("_copy", None)
            item.__pydantic_extra__.pop("_needsCopyResolution", None)

        # Fallback cleanup for direct attributes
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

    def _find_copy_source(self, copy_ref: dict[str, Any], item_name: str) -> Any | None:
        """Find the source item to copy from with enhanced fallback strategies."""
        if "name" in copy_ref and "source" in copy_ref:
            # Creature-to-creature copy
            source_name = copy_ref["name"]
            source_source = copy_ref["source"]

            # Strategy 1: Try exact lookup first
            source_item = self._try_exact_lookup(source_name, source_source)
            if source_item:
                return source_item

            # Log warning and fail cleanly when exact lookup fails
            logger.warning(
                f"Could not find copy source {source_name}|{source_source} for {item_name} (exact lookup failed)"
            )
            return None
        else:
            logger.warning(f"Invalid copy reference format for {item_name}")
            return None

    def _try_exact_lookup(self, source_name: str, source_source: str) -> Any | None:
        """Try exact lookup across content types."""
        # Try creature first
        source_item = self._omnidexer.find(
            ContentType.CREATURE, source_name, source_source
        )
        if source_item:
            return source_item

        # Try other content types if needed
        for content_type in [ContentType.ITEM, ContentType.SPELL]:
            source_item = self._omnidexer.find(content_type, source_name, source_source)
            if source_item:
                return source_item

        return None

    def _update_omnidexer_index(self, resolved_item: Any) -> None:
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
                    index_entry.content = resolved_item
                    logger.debug(
                        f"Updated omnidexer index for {item_name} ({content_type})"
                    )

                    # Clear cache for this specific item to ensure fresh lookups
                    self._clear_omnidexer_cache_for_item(
                        item_name, source_abbrev, content_type
                    )

                else:
                    logger.debug(
                        f"Lookup key {lookup_key} not found in {content_type} index"
                    )
            else:
                logger.warning(f"Content type {content_type} not found in omnidexer")

        except Exception as e:
            item_name = getattr(resolved_item, "name", "unknown")
            logger.warning(f"Failed to update omnidexer index for {item_name}: {e}")

    def _clear_omnidexer_cache_for_item(
        self, name: str, source: str, content_type: ContentType
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

    def _apply_copy_resolution_direct(
        self,
        target_item: Any,
        source_item: Any,
        copy_ref: dict[str, Any],
        item_name: str,
    ) -> None:
        """Apply copy resolution directly to objects to preserve typed properties.

        This method copies properties from source to target while maintaining
        object types and applying _mod transformations.
        """
        # Define which fields should come from source (base creature stats)
        # vs target (specific overrides like name, source, alignment)
        source_fields = {
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
            "size",
            "type",  # Basic creature properties from source
        }

        target_fields = {
            "name",
            "source",
            "alignment",
            "isNpc",
            "isNamedCreature",
            "hasToken",
        }

        # Copy source properties (main creature stats)
        for field in source_fields:
            if hasattr(source_item, field):
                source_value = getattr(source_item, field)
                if source_value is not None:
                    setattr(target_item, field, source_value)

        # Preserve target properties (specific overrides)
        # These are already set on target_item, so no action needed

        # Copy any additional properties from target that aren't placeholders
        # This handles custom properties specific to the copied creature
        if hasattr(target_item, "__dict__") and hasattr(source_item, "__dict__"):
            for key, value in target_item.__dict__.items():
                # Skip known source fields and copy processing attributes
                if (
                    key not in source_fields
                    and key not in {"_copy", "_needsCopyResolution"}
                    and not key.startswith("_")
                    or key in target_fields
                ):
                    # This preserves target-specific properties
                    pass  # Already set on target

        # Apply _mod transformations if present
        if "_mod" in copy_ref:
            try:
                self._apply_mod_transformations_direct(
                    target_item, copy_ref["_mod"], item_name
                )
            except Exception as e:
                logger.warning(
                    f"Failed to apply _mod transformations for {item_name}: {e}"
                )

    def _apply_mod_transformations_direct(
        self, item: Any, mod_data: dict[str, Any], item_name: str
    ) -> None:
        """Apply _mod transformations directly to the object to preserve types."""
        for prop_path, transformations in mod_data.items():
            # Normalize transformations to list (following 5etools _normaliseMods pattern)
            if isinstance(transformations, dict | str):
                transformations = [transformations]
            elif not isinstance(transformations, list):
                logger.warning(
                    f"Invalid _mod format for {item_name}: {prop_path} should be dict, string, or list"
                )
                continue

            for transform in transformations:
                # Handle string transformations (following 5etools pattern)
                if isinstance(transform, str):
                    if transform == "remove":
                        # Remove the property entirely
                        if hasattr(item, prop_path):
                            delattr(item, prop_path)
                        elif hasattr(item, "__dict__") and prop_path in item.__dict__:
                            del item.__dict__[prop_path]
                        logger.debug(f"Removed property '{prop_path}' from {item_name}")
                    else:
                        logger.debug(
                            f"Unsupported string _mod operation '{transform}' for {item_name}"
                        )
                    continue

                if not isinstance(transform, dict):
                    logger.debug(
                        f"Skipping invalid _mod transformation type for {item_name}: {type(transform)}"
                    )
                    continue

                mode = transform.get("mode")
                if mode == "replaceTxt":
                    self._apply_replace_txt_transformation_direct(
                        item, prop_path, transform, item_name
                    )
                elif mode == "appendArr":
                    self._apply_append_arr_transformation_direct(
                        item, prop_path, transform, item_name
                    )
                else:
                    logger.debug(f"Unsupported _mod mode '{mode}' for {item_name}")

    def _apply_replace_txt_transformation_direct(
        self, item: Any, prop_path: str, transform: dict[str, Any], item_name: str
    ) -> None:
        """Apply replaceTxt transformation directly to object properties."""
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
            # Apply to all string properties recursively on the object
            self._replace_text_recursive_direct(item, pattern, with_text)
        else:
            # Apply to specific property
            self._replace_text_in_property_direct(item, prop_path, pattern, with_text)

    def _replace_text_recursive_direct(
        self, obj: Any, pattern: re.Pattern, replacement: str
    ) -> None:
        """Recursively replace text in all string values of an object."""
        if hasattr(obj, "__dict__"):
            for key, value in obj.__dict__.items():
                if isinstance(value, str):
                    setattr(obj, key, pattern.sub(replacement, value))
                elif hasattr(value, "__dict__") or isinstance(value, dict | list):
                    self._replace_text_recursive_direct(value, pattern, replacement)
        elif isinstance(obj, dict):
            for key, value in obj.items():
                if isinstance(value, str):
                    obj[key] = pattern.sub(replacement, value)
                elif isinstance(value, dict | list):
                    self._replace_text_recursive_direct(value, pattern, replacement)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                if isinstance(item, str):
                    obj[i] = pattern.sub(replacement, item)
                elif isinstance(item, dict | list) or hasattr(item, "__dict__"):
                    self._replace_text_recursive_direct(item, pattern, replacement)

    def _replace_text_in_property_direct(
        self, item: Any, prop_path: str, pattern: re.Pattern, replacement: str
    ) -> None:
        """Replace text in a specific property path on an object."""
        # Navigate to the property
        path_parts = prop_path.split(".")
        current = item

        # Navigate to the parent of the target property
        for part in path_parts[:-1]:
            if hasattr(current, part):
                current = getattr(current, part)
            elif isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return  # Property path doesn't exist

        # Apply replacement to the final property
        final_prop = path_parts[-1]
        if hasattr(current, final_prop):
            target = getattr(current, final_prop)
            if isinstance(target, str):
                setattr(current, final_prop, pattern.sub(replacement, target))
            elif isinstance(target, dict | list) or hasattr(target, "__dict__"):
                self._replace_text_recursive_direct(target, pattern, replacement)
        elif isinstance(current, dict) and final_prop in current:
            target = current[final_prop]
            if isinstance(target, str):
                current[final_prop] = pattern.sub(replacement, target)
            elif isinstance(target, dict | list) or hasattr(target, "__dict__"):
                self._replace_text_recursive_direct(target, pattern, replacement)

    def _apply_append_arr_transformation_direct(
        self, item: Any, prop_path: str, transform: dict[str, Any], item_name: str
    ) -> None:
        """Apply appendArr transformation directly to object properties."""
        items_to_append = transform.get("items")
        if not items_to_append:
            return

        # Navigate to the property
        path_parts = prop_path.split(".")
        current = item

        # Navigate to the parent of the target property
        for part in path_parts[:-1]:
            if hasattr(current, part):
                current = getattr(current, part)
            elif isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return  # Property path doesn't exist

        # Append to the final property
        final_prop = path_parts[-1]
        if hasattr(current, final_prop):
            target_list = getattr(current, final_prop)
            if target_list is None:
                setattr(current, final_prop, [])
                target_list = getattr(current, final_prop)
            elif not isinstance(target_list, list):
                return  # Property exists but is not a list

            if isinstance(items_to_append, list):
                target_list.extend(items_to_append)
            else:
                target_list.append(items_to_append)
        elif isinstance(current, dict):
            if final_prop not in current:
                current[final_prop] = []
            elif not isinstance(current[final_prop], list):
                return  # Property exists but is not a list

            if isinstance(items_to_append, list):
                current[final_prop].extend(items_to_append)
            else:
                current[final_prop].append(items_to_append)

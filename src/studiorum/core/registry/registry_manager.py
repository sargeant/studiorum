"""Registry manager for applying content type registrations to existing systems."""

from __future__ import annotations

from typing import TYPE_CHECKING

from studiorum.core.logging import get_logger

from ..models.content import BaseContent, ContentType
from .content_type_registry import ContentTypeMetadata

if TYPE_CHECKING:
    from ..loaders.unified_source_manager import UnifiedSourceManager

logger = get_logger(__name__)


class RegistryManager:
    """Manages application of content type registrations to existing systems."""

    def apply_registrations(self, metadata: dict[str, ContentTypeMetadata]) -> None:
        """Apply all content type registrations to existing systems."""
        logger.info("Applying content type registrations")

        # 1. Update configurable source manager
        self._update_source_manager(metadata)

        # 2. Update omnidexer
        self._update_omnidexer(metadata)

        # 3. Update content factory
        self._update_content_factory(metadata)

        # 4. Update content type resolver
        self._update_content_type_resolver(metadata)

        # 5. Update entry processor (for statblock tags)
        self._update_entry_processor(metadata)

    def _update_source_manager(self, metadata: dict[str, ContentTypeMetadata]) -> None:
        """Replace source manager patterns with registry-based patterns."""
        try:
            from ..loaders.unified_source_manager import UnifiedSourceManager

            # Replace the entire content_patterns dict
            new_patterns: dict[ContentType, list[str]] = {}
            for enum_value, meta in metadata.items():
                # Try to create enum instance from value
                try:
                    content_type = ContentType(enum_value)
                    new_patterns[content_type] = meta.file_patterns
                except ValueError:
                    # Should not happen after enum extension, but be defensive
                    logger.warning(
                        f"Cannot create ContentType for {enum_value}, skipping"
                    )
                    continue

            # Replace the class attribute completely
            UnifiedSourceManager.content_patterns = new_patterns  # type: ignore[attr-defined]
            logger.debug(
                f"Replaced content_patterns with {len(new_patterns)} registry-based patterns"
            )
        except ImportError:
            logger.warning("UnifiedSourceManager not available for pattern replacement")

    def _update_omnidexer(self, metadata: dict[str, ContentTypeMetadata]) -> None:
        """Update omnidexer to use registry-based content type resolution."""
        try:
            from ..loaders.omnidexer import Omnidexer

            # The Omnidexer now uses dynamic resolution through _get_json_content_types()
            # and _get_fluff_content_types() methods, so no static updates needed.
            # The registry integration happens automatically when loaders are registered.

            logger.debug(
                "Omnidexer uses dynamic registry-based content type resolution"
            )

        except ImportError:
            logger.warning("Omnidexer not available for content types replacement")

    def _update_content_factory(self, metadata: dict[str, ContentTypeMetadata]) -> None:
        """Replace content factory mappings with registry-based mappings."""
        try:
            from ..loaders.content_factory import ContentFactory

            # Replace the entire class map - ensure all model_class are subclasses of BaseContent
            new_class_map: dict[ContentType, type[BaseContent]] = {}
            for enum_value, meta in metadata.items():
                # Try to find existing enum by value first (most reliable)
                content_type = None
                try:
                    content_type = ContentType(enum_value)
                except ValueError:
                    # If enum doesn't exist by value, skip this entry
                    logger.warning(
                        f"Cannot create ContentType for {enum_value}, skipping"
                    )
                    continue

                # Verify that model_class is a subclass of BaseContent
                if not issubclass(meta.model_class, BaseContent):
                    logger.warning(
                        f"Model class {meta.model_class} is not a subclass of BaseContent, skipping"
                    )
                    continue
                new_class_map[content_type] = meta.model_class

            ContentFactory._class_map = new_class_map
            logger.debug(
                f"Replaced _class_map with {len(new_class_map)} registry-based mappings"
            )
        except ImportError:
            logger.warning("ContentFactory not available for class map replacement")

    def _update_content_type_resolver(
        self, metadata: dict[str, ContentTypeMetadata]
    ) -> None:
        """Replace content type resolver registrations with registry-based ones."""
        try:
            # Update the service container's interface registry
            from ..interfaces import get_content_type_registry

            interface_registry = get_content_type_registry()

            for enum_value, meta in metadata.items():
                # Always use ContentType constructor to get proper enum instances
                # Don't use getattr as it may find dynamically added string attributes
                try:
                    content_type = ContentType(enum_value)
                except ValueError:
                    logger.warning(
                        f"Cannot create ContentType for {enum_value}, skipping resolver"
                    )
                    continue

                # Verify that model_class is a subclass of BaseContent
                if not issubclass(meta.model_class, BaseContent):
                    logger.warning(
                        f"Model class {meta.model_class} is not a subclass of BaseContent, skipping resolver registration"
                    )
                    continue

                # Register with the interface registry
                interface_registry.register(meta.model_class, content_type)
                logger.debug(
                    f"Registered with interface registry: {content_type} -> {meta.model_class.__name__}"
                )

        except ImportError:
            logger.warning(
                "ContentTypeResolver not available for registration replacement"
            )

    def _update_entry_processor(self, metadata: dict[str, ContentTypeMetadata]) -> None:
        """Replace entry processor statblock mappings with registry-based ones."""
        try:
            # The correct class name is RecursiveEntryProcessor, not EntryProcessor
            from ...latex_engine.core.entry_processor import RecursiveEntryProcessor

            # Replace the entire statblock mappings
            # Maps statblock tag -> ContentType enum name string (as expected by entry processor)
            new_statblock_tags: dict[str, str] = {}
            for enum_value, meta in metadata.items():
                if meta.statblock_tags:
                    # ✅ Always use ContentType constructor for validation (Phase 3 pattern)
                    try:
                        ContentType(enum_value)
                    except ValueError:
                        # Skip test-only registrations that aren't valid enum members
                        logger.debug(f"Skipping test-only content type: {enum_value}")
                        continue

                    enum_name = enum_value.upper()  # Convert to enum name string
                    for tag in meta.statblock_tags:
                        new_statblock_tags[tag] = enum_name

            # Try different possible attribute names for statblock mappings
            if hasattr(RecursiveEntryProcessor, "statblock_tags"):
                RecursiveEntryProcessor.statblock_tags = new_statblock_tags  # type: ignore[attr-defined]
            elif hasattr(RecursiveEntryProcessor, "_statblock_tags"):
                RecursiveEntryProcessor._statblock_tags = new_statblock_tags  # type: ignore[attr-defined]
            else:
                # Add the attribute if it doesn't exist
                RecursiveEntryProcessor._statblock_tags = new_statblock_tags  # type: ignore[attr-defined]

            logger.debug(
                f"Replaced statblock tags with {len(new_statblock_tags)} registry-based mappings"
            )
        except ImportError:
            logger.warning(
                "RecursiveEntryProcessor not available for statblock tags replacement"
            )

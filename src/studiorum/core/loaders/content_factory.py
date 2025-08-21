"""Content factory for creating content instances without tight coupling."""

from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from ..interfaces import ContentTypeRegistry
from ..models.content import BaseContent, ContentType


class ContentFactory:
    """Factory for creating content instances based on content type."""

    def __init__(self, registry: "ContentTypeRegistry | None" = None) -> None:
        if registry is None:
            # For backward compatibility, create registry directly
            from ..registry import get_content_type_registry

            self._registry = cast("ContentTypeRegistry", get_content_type_registry())
        else:
            self._registry = registry
        self._class_map: dict[ContentType, type[BaseContent]] = {}
        self._initialized = False

    def _ensure_initialized(self) -> None:
        """Ensure the factory is initialized with all content classes."""
        if self._initialized:
            return

        self._initialize_class_map()
        self._initialized = True

    def _initialize_class_map(self) -> None:
        """Initialize the content class mapping from registry manager."""
        # Registry manager should populate class map during initialization
        if hasattr(self.__class__, "_class_map") and self.__class__._class_map:
            self._class_map = self.__class__._class_map.copy()
            return

        # For test environments, try initializing the registry if not already done
        try:
            from ..registry import initialize_content_types

            initialize_content_types()

            # Check again after initialization
            if hasattr(self.__class__, "_class_map") and self.__class__._class_map:
                self._class_map = self.__class__._class_map.copy()
                return
        except ImportError:
            pass

        # If registry manager hasn't populated class map, something is wrong
        raise RuntimeError(
            "ContentFactory class map not initialized by registry manager. "
            "Ensure initialize_content_types() is called before creating ContentFactory instances."
        )

    def create_content(
        self, data: dict[str, Any], content_type: ContentType
    ) -> BaseContent:
        """Create content instance from data.

        Args:
            data: Raw data dictionary
            content_type: Type of content to create

        Returns:
            Created content instance

        Raises:
            ValueError: If content type is not supported
        """
        self._ensure_initialized()

        if content_type not in self._class_map:
            raise ValueError(f"Unsupported content type: {content_type}")

        content_class = self._class_map[content_type]
        return content_class.model_validate(data)

    def get_supported_types(self) -> list[ContentType]:
        """Get list of supported content types.

        Returns:
            List of supported content types
        """
        self._ensure_initialized()
        return list(self._class_map.keys())

    def register_content_class(
        self, content_type: ContentType, content_class: type[BaseContent]
    ) -> None:
        """Register a content class for a content type.

        Args:
            content_type: Content type to register
            content_class: Content class to register
        """
        self._class_map[content_type] = content_class
        # Note: Registry registration is handled elsewhere in the initialization process
        # The ContentTypeRegistry.register() method expects ContentTypeMetadata objects
        # which are created during the content type discovery process

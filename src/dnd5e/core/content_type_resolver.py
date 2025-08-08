"""Content type resolution without circular dependencies."""

from .interfaces import ContentTypeResolver, get_content_type_registry
from .models.content import BaseContent, ContentType


class RegistryBasedContentTypeResolver:
    """Content type resolver using registry pattern to avoid circular imports."""

    def __init__(self) -> None:
        self._registry = get_content_type_registry()
        self._initialized = False

    def _ensure_initialized(self) -> None:
        """Ensure the registry is initialized with all content types."""
        if self._initialized:
            return

        # Import and register all content types
        # This is done lazily to avoid circular imports
        self._register_all_types()
        self._initialized = True

    def _register_all_types(self) -> None:
        """Register all content types with the resolver.

        Content types are automatically registered via the @content_type decorator system.
        This method is now a no-op as registration happens automatically during module import.
        """
        # Content types are now registered automatically via decorators during
        # module import. No manual registration needed.
        pass

    def resolve_type(self, content: BaseContent) -> ContentType:
        """Resolve content type from content instance.

        Args:
            content: Content instance to analyze

        Returns:
            Resolved content type
        """
        self._ensure_initialized()
        result = self._registry.get_type(content)
        if result is None:
            raise ValueError(f"Unknown content type for {type(content).__name__}")
        return result

    def register_type(
        self, content_class: type[BaseContent], content_type: ContentType
    ) -> None:
        """Register a content class with its type.

        Args:
            content_class: Content class to register
            content_type: Associated content type
        """
        self._registry.register(content_class, content_type)


# Global resolver instance
_content_type_resolver = RegistryBasedContentTypeResolver()


def get_content_type_resolver() -> ContentTypeResolver:
    """Get the global content type resolver.

    Returns:
        Global content type resolver instance
    """
    return _content_type_resolver


def reset_content_type_resolver() -> None:
    """Reset the global content type resolver (for testing).

    This recreates the global resolver instance to ensure clean state.
    """
    global _content_type_resolver
    _content_type_resolver = RegistryBasedContentTypeResolver()

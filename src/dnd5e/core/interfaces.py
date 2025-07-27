"""Protocol interfaces for breaking circular dependencies and tight coupling."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Optional, Protocol, runtime_checkable

from .models.content import BaseContent, ContentType

if TYPE_CHECKING:
    from .loaders.omnidexer import Omnidexer


@runtime_checkable
class ContentLoader(Protocol):
    """Protocol for content loading functionality."""

    def load_content(
        self, data: dict[str, Any], content_type: ContentType
    ) -> BaseContent:
        """Load content from data dictionary.

        Args:
            data: Raw data dictionary
            content_type: Type of content to load

        Returns:
            Loaded content instance
        """
        ...

    def get_supported_types(self) -> list[ContentType]:
        """Get list of supported content types.

        Returns:
            List of supported content types
        """
        ...


@runtime_checkable
class ContentTypeResolver(Protocol):
    """Protocol for resolving content types without circular imports."""

    def resolve_type(self, content: BaseContent) -> ContentType:
        """Resolve content type from content instance.

        Args:
            content: Content instance to analyze

        Returns:
            Resolved content type
        """
        ...

    def register_type(
        self, content_class: type[BaseContent], content_type: ContentType
    ) -> None:
        """Register a content class with its type.

        Args:
            content_class: Content class to register
            content_type: Associated content type
        """
        ...


@runtime_checkable
class ContentIndexer(Protocol):
    """Protocol for content indexing functionality."""

    def find(self, content_type: ContentType, name: str) -> BaseContent | None:
        """Find content by type and name.

        Args:
            content_type: Type of content to find
            name: Name of content to find

        Returns:
            Found content or None
        """
        ...

    def find_all(self, content_type: ContentType) -> list[BaseContent]:
        """Find all content of a given type.

        Args:
            content_type: Type of content to find

        Returns:
            List of found content
        """
        ...

    def add_content(self, content: BaseContent) -> None:
        """Add content to index.

        Args:
            content: Content to add
        """
        ...


@runtime_checkable
class TagResolver(Protocol):
    """Protocol for tag resolution functionality."""

    def resolve_tag(self, tag: str) -> str | None:
        """Resolve a tag to its content.

        Args:
            tag: Tag to resolve

        Returns:
            Resolved tag content or None
        """
        ...

    def register_resolver(self, tag_pattern: str, resolver_func: Any) -> None:
        """Register a tag resolver function.

        Args:
            tag_pattern: Pattern to match tags
            resolver_func: Function to resolve tags
        """
        ...


@runtime_checkable
class DeepIndexable(Protocol):
    """Protocol for content that can expose nested content for deep indexing."""

    def get_deep_index_entries(self, omnidexer: "Omnidexer") -> list[BaseContent]:
        """Return a list of nested content items that should be indexed.

        This method allows content objects to expose their nested sub-entities
        (like class features, creature spells, adventure sections) for indexing
        by the Omnidexer system.

        Args:
            omnidexer: The omnidexer instance doing the indexing
                      (can be used to resolve references)

        Returns:
            List of BaseContent objects that should be individually indexed

        Note:
            - Implementation should avoid infinite recursion
            - Should only return immediate children, not deeply nested content
            - The omnidexer will handle recursive deep indexing automatically
        """
        ...


class ContentTypeRegistry:
    """Registry for content types to break circular dependencies."""

    def __init__(self) -> None:
        self._type_map: dict[type[BaseContent], ContentType] = {}

    def register(
        self, content_class: type[BaseContent], content_type: ContentType
    ) -> None:
        """Register a content class with its type.

        Args:
            content_class: Content class to register
            content_type: Associated content type
        """
        self._type_map[content_class] = content_type

    def get_type(self, content: BaseContent) -> ContentType:
        """Get content type for a content instance.

        Args:
            content: Content instance to analyze

        Returns:
            Content type

        Raises:
            ValueError: If content type cannot be determined
        """
        content_class = type(content)
        if content_class in self._type_map:
            return self._type_map[content_class]

        # Check inheritance chain
        for registered_class, content_type in self._type_map.items():
            if isinstance(content, registered_class):
                return content_type

        raise ValueError(f"Unknown content type for {content_class}")

    def get_all_types(self) -> list[ContentType]:
        """Get all registered content types.

        Returns:
            List of registered content types
        """
        return list(self._type_map.values())


# Global registry instance
_content_type_registry = ContentTypeRegistry()


def get_content_type_registry() -> ContentTypeRegistry:
    """Get the global content type registry.

    Returns:
        Global content type registry instance
    """
    return _content_type_registry

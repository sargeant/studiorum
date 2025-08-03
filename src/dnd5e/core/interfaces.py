"""Protocol interfaces for breaking circular dependencies and tight coupling."""

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

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
    """
    Protocol for content that can expose nested content for deep indexing.

    The DeepIndexable protocol enables the Omnidexer to discover and index nested
    content within complex data structures. This includes class features within
    classes, adventure sections within adventures, spell references in creature
    abilities, and other hierarchical content.

    Implementation Guidelines:
        - Return only immediate children, not deeply nested content
        - Handle errors gracefully with logging, don't fail completely
        - Use the omnidexer parameter for reference resolution
        - Validate content structure before processing

    Examples:
        >>> class Adventure(BaseContent, DeepIndexable):
        ...     def get_deep_index_entries(self, omnidexer: "Omnidexer") -> list[BaseContent]:
        ...         nested_content = []
        ...         for chapter in self.contents:
        ...             parser = EntryParser(source=self.source, parent_name=f"{self.name} > {chapter.name}")
        ...             for content_item in parser.parse_entries(chapter.entries, "adventure"):
        ...                 nested_content.append(content_item)
        ...         return nested_content

    See Also:
        - docs/omnidexer-deep-indexing.md for comprehensive implementation guide
        - docs/api/omnidexer.md for API documentation
    """

    def get_deep_index_entries(self, omnidexer: "Omnidexer") -> list[BaseContent]:
        """
        Return immediate child content items that should be indexed.

        This method allows content objects to expose their nested sub-entities
        for indexing by the Omnidexer system. The omnidexer will recursively
        process returned items if they also implement DeepIndexable.

        Args:
            omnidexer: The omnidexer instance performing the indexing.
                      Can be used to resolve references during parsing.

        Returns:
            List of BaseContent objects that should be individually indexed.
            Should contain only immediate children, not deeply nested content.

        Implementation Notes:
            - Return empty list rather than None if no nested content exists
            - Handle parsing errors gracefully with logging
            - Only return immediate children - recursion is handled automatically
            - Use omnidexer parameter for reference resolution when needed

        Example:
            >>> def get_deep_index_entries(self, omnidexer: "Omnidexer") -> list[BaseContent]:
            ...     nested_content = []
            ...     try:
            ...         for item in self.nested_items:
            ...             try:
            ...                 parsed_item = self._parse_item(item, omnidexer)
            ...                 if parsed_item:
            ...                     nested_content.append(parsed_item)
            ...             except Exception as e:
            ...                 logger.warning(f"Failed to parse item {item}: {e}")
            ...                 continue
            ...     except Exception as e:
            ...         logger.error(f"Failed to extract nested content: {e}")
            ...     return nested_content
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


def reset_content_type_registry() -> None:
    """Reset the global content type registry (for testing).

    This recreates the global registry instance to ensure clean state.
    """
    global _content_type_registry
    _content_type_registry = ContentTypeRegistry()

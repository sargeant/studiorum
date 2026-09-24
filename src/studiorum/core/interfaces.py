"""The protocol for content that holds other indexable content."""

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from .models.content import BaseContent

if TYPE_CHECKING:
    from .loaders.omnidexer import Omnidexer


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

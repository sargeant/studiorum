"""Unified reference system for content resolution and formatting.

This module provides a generic Reference[T] pattern that consolidates the various
reference and resolution patterns used throughout the codebase, while maintaining
backward compatibility with existing systems.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Protocol, TypeVar, cast

from pydantic import BaseModel, Field

from dnd5e.core.base_context import BaseContext

if TYPE_CHECKING:
    from dnd5e.core.models.content import BaseContent

T = TypeVar("T")


class ReferenceType(str, Enum):
    """Types of references supported by the unified system."""

    CONTENT = "content"  # References to game content (spells, items, etc.)
    SECTION = "section"  # Document section references
    PAGE = "page"  # Page references
    EXTERNAL = "external"  # External document references
    CROSS_REF = "cross_ref"  # Cross-references within document
    HYPERLINK = "hyperlink"  # Web/external hyperlinks


class ReferenceFormat(str, Enum):
    """Output formats for reference rendering."""

    LATEX = "latex"  # LaTeX markup for PDF generation
    HTML = "html"  # HTML markup for web output
    MARKDOWN = "markdown"  # Markdown format
    PLAIN_TEXT = "plain_text"  # Plain text representation


@dataclass(frozen=True)
class Reference[T]:
    """Generic reference to content of type T.

    This unified reference structure captures all the information needed
    for parsing, resolving, and formatting references across different
    content types and output formats.
    """

    # Core identity - these fields uniquely identify what is being referenced
    source: str = Field(description="Text/tag that created this reference")
    target: str = Field(description="Target identifier (name, ID, etc.)")
    content_type: type[T] = Field(description="Type of content being referenced")

    # Optional metadata for enhanced resolution and display
    source_book: str | None = Field(None, description="Source book abbreviation")
    display_text: str | None = Field(None, description="Custom display text")
    context: str = Field(default="", description="Surrounding text context")
    reference_type: ReferenceType = Field(default=ReferenceType.CONTENT)

    # Processing metadata for debugging and caching
    original_text: str = Field(default="", description="Original reference text")
    parsed_at: datetime = Field(default_factory=datetime.now)

    # LaTeX-specific metadata (for backward compatibility)
    latex_label: str | None = Field(None, description="Generated LaTeX label")
    section: str | None = Field(None, description="Document section")
    page: int | None = Field(None, description="Page number if known")

    def get_cache_key(self) -> str:
        """Generate a cache key for this reference."""
        return f"{self.content_type.__name__}:{self.target}:{self.source_book or ''}"

    def with_latex_info(
        self, label: str, section: str | None = None, page: int | None = None
    ) -> Reference[T]:
        """Create a copy with LaTeX-specific information added."""
        return Reference(
            source=self.source,
            target=self.target,
            content_type=self.content_type,
            source_book=self.source_book,
            display_text=self.display_text,
            context=self.context,
            reference_type=self.reference_type,
            original_text=self.original_text,
            parsed_at=self.parsed_at,
            latex_label=label,
            section=section,
            page=page,
        )


class ReferenceParser[T](ABC):
    """Abstract base class for extracting references from text.

    Each parser is responsible for identifying and extracting references
    of a specific type from text content.
    """

    @abstractmethod
    def extract_references(
        self, text: str, context: BaseContext | None = None
    ) -> list[Reference[T]]:
        """Extract all references of type T from the given text.

        Args:
            text: The text to parse for references
            context: Optional context for enhanced parsing

        Returns:
            List of extracted references
        """
        pass

    @abstractmethod
    def can_parse(self, text: str) -> bool:
        """Check if this parser can handle the given text.

        Args:
            text: The text to check

        Returns:
            True if this parser can extract references from the text
        """
        pass

    @property
    @abstractmethod
    def supported_content_type(self) -> type[T]:
        """The content type this parser handles."""
        pass


class ReferenceResolver[T](ABC):
    """Abstract base class for resolving references to actual content.

    Each resolver is responsible for taking a reference and finding
    the actual content object it refers to.
    """

    @abstractmethod
    def resolve(
        self, ref: Reference[T], context: BaseContext | None = None
    ) -> T | None:
        """Resolve reference to actual content object.

        Args:
            ref: The reference to resolve
            context: Optional context for resolution

        Returns:
            The resolved content object, or None if not found
        """
        pass

    @abstractmethod
    def format_reference(
        self,
        ref: Reference[T],
        format_type: ReferenceFormat,
        resolved_content: T | None = None,
        context: BaseContext | None = None,
    ) -> str:
        """Format reference for output in the specified format.

        Args:
            ref: The reference to format
            format_type: The desired output format
            resolved_content: The resolved content (if available)
            context: Optional context for formatting

        Returns:
            Formatted reference string
        """
        pass

    @property
    @abstractmethod
    def supported_content_type(self) -> type[T]:
        """The content type this resolver handles."""
        pass


class ReferenceCache:
    """Type-safe cache for resolved references to improve performance."""

    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self._cache: dict[str, tuple[Any, datetime]] = {}
        self._access_times: dict[str, datetime] = {}

    def get[T](self, key: str) -> T | None:
        """Get cached value by key with proper typing."""
        if key in self._cache:
            self._access_times[key] = datetime.now()
            value = self._cache[key][0]
            # Use cast since the caller knows what type they expect
            return cast(T | None, value)
        return None

    def set[T](self, key: str, value: T) -> None:
        """Set cached value with type information."""
        now = datetime.now()

        # Evict oldest entries if cache is full
        if len(self._cache) >= self.max_size:
            oldest_key = min(
                self._access_times.keys(), key=lambda k: self._access_times[k]
            )
            self._cache.pop(oldest_key, None)
            self._access_times.pop(oldest_key, None)

        self._cache[key] = (value, now)
        self._access_times[key] = now

    def clear(self) -> None:
        """Clear all cached values."""
        self._cache.clear()
        self._access_times.clear()


class ReferenceManager:
    """Unified manager for parsing, resolving, and formatting references.

    This class coordinates multiple parsers and resolvers to provide
    a single interface for all reference operations.
    """

    def __init__(self, cache_size: int = 1000):
        self._parsers: list[ReferenceParser] = []
        # Use string keys for content type names instead of type objects
        self._resolvers: dict[str, ReferenceResolver] = {}
        self._cache = ReferenceCache(cache_size)

    def register_parser(self, parser: ReferenceParser[T]) -> None:
        """Register a reference parser.

        Args:
            parser: The parser to register
        """
        self._parsers.append(parser)

    def register_resolver(self, resolver: ReferenceResolver[T]) -> None:
        """Register a reference resolver.

        Args:
            resolver: The resolver to register
        """
        # Use the content type name as the key
        content_type_name = resolver.supported_content_type.__name__
        self._resolvers[content_type_name] = resolver

    def parse_references(
        self, text: str, context: BaseContext | None = None
    ) -> list[Reference]:
        """Parse all references from text using registered parsers.

        Args:
            text: The text to parse
            context: Optional context for parsing

        Returns:
            List of all extracted references
        """
        all_refs: list[Reference] = []

        for parser in self._parsers:
            if parser.can_parse(text):
                refs = parser.extract_references(text, context)
                all_refs.extend(refs)

        return all_refs

    def resolve_reference[U](
        self, ref: Reference[U], context: BaseContext | None = None
    ) -> U | None:
        """Resolve a single reference to its content.

        Args:
            ref: The reference to resolve
            context: Optional context for resolution

        Returns:
            The resolved content, or None if not found
        """
        # Check cache first
        cache_key = ref.get_cache_key()
        cached: U | None = self._cache.get(cache_key)
        if cached is not None:
            return cached

        # Find appropriate resolver using content type name
        content_type_name = ref.content_type.__name__
        resolver = self._resolvers.get(content_type_name)
        if not resolver:
            return None

        # Resolve and cache result
        resolved = resolver.resolve(ref, context)
        if resolved is not None:
            self._cache.set(cache_key, resolved)

        # Use cast to tell the type checker this is the right type
        # This is safe because we matched by content type name
        return cast(U | None, resolved)

    def format_reference[U](
        self,
        ref: Reference[U],
        format_type: ReferenceFormat,
        context: BaseContext | None = None,
    ) -> str:
        """Format a reference for output.

        Args:
            ref: The reference to format
            format_type: The desired output format
            context: Optional context for formatting

        Returns:
            Formatted reference string
        """
        content_type_name = ref.content_type.__name__
        resolver = self._resolvers.get(content_type_name)
        if not resolver:
            return ref.display_text or ref.target

        resolved = self.resolve_reference(ref, context)
        return resolver.format_reference(ref, format_type, resolved, context)

    def resolve_and_format(
        self,
        text: str,
        format_type: ReferenceFormat,
        context: BaseContext | None = None,
    ) -> str:
        """Parse, resolve, and format all references in text.

        Args:
            text: The text containing references
            format_type: The desired output format
            context: Optional context for processing

        Returns:
            Text with all references formatted
        """
        refs = self.parse_references(text, context)
        result = text

        # Replace references in reverse order to preserve string positions
        for ref in reversed(refs):
            formatted = self.format_reference(ref, format_type, context)
            result = result.replace(ref.original_text, formatted)

        return result

    def get_statistics(self) -> dict[str, Any]:
        """Get statistics about registered parsers and resolvers.

        Returns:
            Dictionary with system statistics
        """
        return {
            "parsers_count": len(self._parsers),
            "resolvers_count": len(self._resolvers),
            "cache_size": len(self._cache._cache),
            "supported_content_types": list(self._resolvers.keys()),
        }

    def clear_cache(self) -> None:
        """Clear the resolution cache."""
        self._cache.clear()


# Compatibility functions for existing systems


def create_spell_reference(
    name: str,
    source: str | None = None,
    display_text: str | None = None,
    original_text: str = "",
) -> Reference[BaseContent]:
    """Create a spell reference compatible with existing SpellReference system.

    Args:
        name: Spell name
        source: Source book
        display_text: Custom display text
        original_text: Original reference text

    Returns:
        Unified Reference object
    """
    from dnd5e.core.models.content import BaseContent

    return Reference(
        source=original_text,
        target=name,
        content_type=BaseContent,
        source_book=source,
        display_text=display_text,
        reference_type=ReferenceType.CONTENT,
        original_text=original_text,
    )


def create_cross_reference(
    content_type: str,
    name: str,
    source: str | None = None,
    latex_label: str | None = None,
    section: str | None = None,
    page: int | None = None,
) -> Reference[BaseContent]:
    """Create a cross-reference compatible with existing CrossReference system.

    Args:
        content_type: Type of content being referenced
        name: Content name
        source: Source book
        latex_label: LaTeX label for the reference
        section: Document section
        page: Page number

    Returns:
        Unified Reference object
    """
    from dnd5e.core.models.content import BaseContent

    ref = Reference(
        source="",
        target=name,
        content_type=BaseContent,
        source_book=source,
        reference_type=ReferenceType.CROSS_REF,
    )

    return ref.with_latex_info(latex_label or f"{content_type}:{name}", section, page)


def reset_reference_manager() -> None:
    """Reset the reference manager (for testing).

    This is now handled by the service container reset mechanism.
    """
    # This function is maintained for backward compatibility
    # but the actual reset is handled by the service container
    pass

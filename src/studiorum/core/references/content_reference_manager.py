"""Unified content reference management system.

This module provides a unified approach to tracking content references from both
template-level tags ({@spell Name|Source}) and deep indexing (creature spells).
It eliminates the need for manual bridges between systems.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

from pydantic import BaseModel, Field

from ..interfaces import DeepIndexable
from ..models.content import BaseContent, ContentType
from .content_tracker import ContentTracker, TrackedContent

if TYPE_CHECKING:
    from ..loaders.omnidexer import Omnidexer


class ReferenceSource(BaseModel):
    """Represents the source of a content reference."""

    type: str = Field(description="Type of reference source (tag, deep_index, manual)")
    location: str = Field(description="Where the reference was found")
    context: str | None = Field(
        None, description="Additional context about the reference"
    )


class ContentReference(BaseModel):
    """Enhanced content reference with source tracking."""

    content_type: str = Field(description="Type of content being referenced")
    name: str = Field(description="Name of the referenced content")
    source: str | None = Field(None, description="Source abbreviation")
    page: str | None = Field(None, description="Page reference")
    reference_source: ReferenceSource = Field(
        description="How this reference was discovered"
    )

    def to_tracked_content(self) -> TrackedContent:
        """Convert to TrackedContent for backward compatibility."""
        return TrackedContent(
            content_type=self.content_type,
            name=self.name,
            source=self.source,
            page=self.page,
        )


class ContentReferenceManager:
    """Unified manager for all content references.

    This class provides a single point of reference tracking that can be used by:
    - TagResolver during template processing
    - Deep indexing systems during content analysis
    - Manual reference additions

    It automatically manages deduplication and provides unified appendix generation.
    """

    def __init__(self, omnidexer: Omnidexer | None = None) -> None:
        self.omnidexer = omnidexer
        self._references: list[ContentReference] = []
        self._reference_counts: dict[tuple[str, str, str | None], int] = {}

        # Performance optimization: Use sets for fast deduplication
        self._reference_keys: set[tuple[str, str, str | None]] = set()

        # Keep ContentTracker for backward compatibility
        self._content_tracker = ContentTracker()

    def track_reference(
        self,
        content_type: str,
        name: str,
        source: str | None = None,
        page: str | None = None,
        reference_source_type: str = "manual",
        location: str = "unknown",
        context: str | None = None,
    ) -> None:
        """Track a content reference from any source.

        Args:
            content_type: Type of content (spell, creature, item, etc.)
            name: Name of the content
            source: Source abbreviation (optional)
            page: Page reference (optional)
            reference_source_type: How the reference was discovered (tag, deep_index, manual)
            location: Where the reference was found
            context: Additional context about the reference
        """
        reference_source = ReferenceSource(
            type=reference_source_type, location=location, context=context
        )

        reference = ContentReference(
            content_type=content_type,
            name=name,
            source=source,
            page=page,
            reference_source=reference_source,
        )

        # Performance optimization: Check for duplicates before adding
        key = (content_type.lower(), name.lower(), source)

        # Always increment reference count
        self._reference_counts[key] = self._reference_counts.get(key, 0) + 1

        # Only add to tracking if not already seen (for first occurrence tracking)
        if key not in self._reference_keys:
            self._reference_keys.add(key)
            self._references.append(reference)

            # Add to ContentTracker (only once per unique reference)
            self._content_tracker.add_content(
                content_type=content_type, name=name, source=source, page=page
            )

    def track_tag_reference(
        self,
        tag_type: str,
        name: str,
        source: str | None = None,
        template_location: str = "unknown template",
    ) -> None:
        """Track a reference discovered during tag resolution.

        Args:
            tag_type: Type of tag (creature, spell, item, etc.)
            name: Name from the tag
            source: Source from the tag (if provided)
            template_location: Which template the tag was found in
        """
        self.track_reference(
            content_type=tag_type,
            name=name,
            source=source,
            reference_source_type="tag",
            location=template_location,
            context=f"Template tag: {{@{tag_type} {name}|{source or 'default'}}}",
        )

    def track_deep_index_references(
        self, content: Any, context: str = "deep indexing"
    ) -> None:
        """Track all references from deep indexing a piece of content.

        Args:
            content: Content that implements DeepIndexable
            context: Context description for tracking
        """
        if not self.omnidexer:
            return

        try:
            deep_entries = content.get_deep_index_entries(self.omnidexer)

            for entry in deep_entries:
                # Determine content type from the entry
                content_type = self._infer_content_type(entry)

                # Extract source information
                source_str = (
                    entry.source.abbreviation
                    if hasattr(entry, "source") and entry.source
                    else None
                )

                self.track_reference(
                    content_type=content_type,
                    name=entry.name,
                    source=source_str,
                    reference_source_type="deep_index",
                    location=f"{content.name} ({type(content).__name__})",
                    context=context,
                )

        except Exception as e:
            # Log but don't fail - graceful degradation
            from ..logging.logger import get_logger

            logger = get_logger(__name__)
            logger.warning(
                f"Failed to extract deep index references from {content.name}: {e}"
            )

    def _infer_content_type(self, content: BaseContent) -> str:
        """Infer content type from a BaseContent instance."""
        # Use the class name to infer type, converting to lowercase
        class_name = type(content).__name__.lower()

        # Handle common mappings
        type_mappings = {
            "spell": "spell",
            "creature": "creature",
            "monster": "creature",
            "item": "item",
            "magicitem": "item",
            "feat": "feat",
            "background": "background",
            "class": "class",
            "subclass": "subclass",
            "race": "race",
            "subrace": "race",
        }

        return type_mappings.get(class_name, class_name)

    def get_references_by_type(self, content_type: str) -> list[ContentReference]:
        """Get all references of a specific type.

        Args:
            content_type: Type of content to retrieve

        Returns:
            List of references for that content type
        """
        content_type = content_type.lower()
        return [
            ref for ref in self._references if ref.content_type.lower() == content_type
        ]

    def get_unique_references_by_type(
        self, content_type: str
    ) -> list[ContentReference]:
        """Get unique references of a specific type (deduplicated).

        Args:
            content_type: Type of content to retrieve

        Returns:
            List of unique references for that content type
        """
        references = self.get_references_by_type(content_type)
        seen = set()
        unique_refs = []

        for ref in references:
            key = (ref.content_type.lower(), ref.name.lower(), ref.source)
            if key not in seen:
                seen.add(key)
                unique_refs.append(ref)

        return unique_refs

    def get_content_tracker(self) -> ContentTracker:
        """Get the backward-compatible ContentTracker instance.

        Returns:
            ContentTracker instance with all tracked references
        """
        return self._content_tracker

    def get_reference_count(
        self, content_type: str, name: str, source: str | None = None
    ) -> int:
        """Get the number of times a specific content item was referenced.

        Args:
            content_type: Type of content
            name: Name of content
            source: Source abbreviation

        Returns:
            Number of times this content was referenced
        """
        key = (content_type.lower(), name.lower(), source)
        return self._reference_counts.get(key, 0)

    def get_all_references(self) -> list[ContentReference]:
        """Get all tracked references.

        Returns:
            List of all content references
        """
        return self._references.copy()

    def clear(self) -> None:
        """Clear all tracked references."""
        self._references.clear()
        self._reference_counts.clear()
        self._reference_keys.clear()
        self._content_tracker = ContentTracker()


class ReferenceTrackingTagResolver:
    """Wrapper around TagResolver that automatically tracks references.

    This class wraps the existing TagResolver and automatically tracks
    any references discovered during tag resolution.
    """

    def __init__(
        self, tag_resolver: Any, reference_manager: ContentReferenceManager
    ) -> None:
        self.tag_resolver = tag_resolver
        self.reference_manager = reference_manager

    def resolve_tag(self, tag: str, template_location: str = "unknown") -> Any:
        """Resolve a tag and track the reference.

        Args:
            tag: Tag string to resolve
            template_location: Where the tag was found

        Returns:
            Resolved tag content
        """
        # Resolve the tag using the wrapped resolver
        resolved = self.tag_resolver.resolve_tag(tag)

        # Extract reference information from the tag
        # This is a simplified parser - in reality would use proper tag parsing
        try:
            if tag.startswith("{@") and "|" in tag:
                # Parse {@type Name|Source} format
                tag_content = tag[2:-1]  # Remove {@ and }
                parts = tag_content.split("|", 1)
                if len(parts) == 2:
                    type_and_name = parts[0].strip()
                    source = parts[1].strip()

                    # Split type and name
                    if " " in type_and_name:
                        tag_type, name = type_and_name.split(" ", 1)
                        self.reference_manager.track_tag_reference(
                            tag_type=tag_type,
                            name=name,
                            source=source,
                            template_location=template_location,
                        )
        # Optional reference tracking, graceful degradation for malformed content
        except Exception:  # nosec B110
            # If parsing fails, continue without tracking
            pass

        return resolved

    def __getattr__(self, name: str) -> Any:
        """Delegate all other attributes to the wrapped resolver."""
        return getattr(self.tag_resolver, name)

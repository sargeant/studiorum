"""Reference indexing system for cross-references and citations."""

from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from ..config.settings import get_logger
from ..models.content import BaseContent, ContentType

logger = get_logger(__name__)


@dataclass
class Reference:
    """Represents a reference to content from another piece of content."""

    source_content: BaseContent
    target_type: ContentType
    target_name: str
    target_source: str | None
    context: str  # The text context where the reference appears


class ReferenceIndex:
    """Indexes cross-references between content for generating lists and citations."""

    def __init__(self):
        # Forward references: content -> what it references
        self._forward_refs: dict[str, list[Reference]] = defaultdict(list)

        # Backward references: content -> what references it
        self._backward_refs: dict[str, list[Reference]] = defaultdict(list)

        # Referenced content by type (for generating lists)
        self._referenced_by_type: dict[ContentType, set[str]] = defaultdict(set)

    def add_reference(
        self,
        source: BaseContent,
        target_type: ContentType,
        target_name: str,
        target_source: str | None = None,
        context: str = "",
    ):
        """Add a reference from source content to target content."""

        source_key = self._get_content_key(source)
        target_key = f"{target_type.value}:{target_name}:{target_source or 'any'}"

        reference = Reference(
            source_content=source,
            target_type=target_type,
            target_name=target_name,
            target_source=target_source,
            context=context,
        )

        # Add to forward references
        self._forward_refs[source_key].append(reference)

        # Add to backward references
        self._backward_refs[target_key].append(reference)

        # Track referenced content by type
        self._referenced_by_type[target_type].add(
            f"{target_name}|{target_source or 'any'}"
        )

        logger.debug(
            f"Added reference: {source.name} -> {target_type.value}:{target_name}"
        )

    def get_references_from(self, content: BaseContent) -> list[Reference]:
        """Get all references made by the given content."""
        content_key = self._get_content_key(content)
        return self._forward_refs.get(content_key, [])

    def get_references_to(
        self, content_type: ContentType, name: str, source: str | None = None
    ) -> list[Reference]:
        """Get all references to the specified content."""
        target_key = f"{content_type.value}:{name}:{source or 'any'}"
        return self._backward_refs.get(target_key, [])

    def get_referenced_content(self, content_type: ContentType) -> list[str]:
        """Get list of all content names that are referenced for a given type."""
        referenced = self._referenced_by_type.get(content_type, set())
        return [ref.split("|")[0] for ref in referenced]

    def get_reference_statistics(self) -> dict[str, Any]:
        """Get statistics about references in the index."""
        stats = {
            "total_references": sum(len(refs) for refs in self._forward_refs.values()),
            "content_with_references": len(self._forward_refs),
            "referenced_content": len(self._backward_refs),
            "by_type": {},
        }

        for content_type, referenced in self._referenced_by_type.items():
            stats["by_type"][content_type.value] = len(referenced)

        return stats

    def _get_content_key(self, content: BaseContent) -> str:
        """Generate a unique key for content."""
        return f"{content.__class__.__name__.lower()}:{content.name}:{content.source.abbreviation}"

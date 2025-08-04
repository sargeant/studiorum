"""Reference indexing system for cross-references and citations."""

from collections import defaultdict
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..logging import get_logger
from ..models.content import BaseContent, ContentType

logger = get_logger(__name__)


class Reference(BaseModel):
    """Represents a reference to content from another piece of content."""

    source_content: BaseContent = Field(description="Content that makes the reference")
    target_type: ContentType = Field(description="Type of content being referenced")
    target_name: str = Field(min_length=1, description="Name of target content")
    target_source: str | None = Field(None, description="Source of target content")
    context: str = Field(
        default="", description="Text context where the reference appears"
    )

    @field_validator("target_name")
    @classmethod
    def normalize_target_name(cls, v: str) -> str:
        """Normalize target name by trimming whitespace."""
        return v.strip()

    @field_validator("context")
    @classmethod
    def validate_context(cls, v: str) -> str:
        """Validate and limit context length."""
        cleaned = v.strip()
        if len(cleaned) > 200:  # Reasonable limit for context
            cleaned = cleaned[:197] + "..."
        return cleaned

    model_config = ConfigDict(arbitrary_types_allowed=True)


class ReferenceIndex:
    """Indexes cross-references between content for generating lists and citations."""

    def __init__(self) -> None:
        # Forward references: content -> what it references
        self._forward_refs: dict[str, list[Reference]] = defaultdict(list)

        # Reverse references: content -> what references it
        self._reverse_refs: dict[str, list[Reference]] = defaultdict(list)

        # Referenced content by type (for generating lists)
        self._referenced_by_type: dict[ContentType, set[str]] = defaultdict(set)

    def add_reference(
        self,
        source: BaseContent,
        target_type: ContentType,
        target_name: str,
        target_source: str | None = None,
        context: str = "",
    ) -> None:
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

        # Add to reverse references
        self._reverse_refs[target_key].append(reference)

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
        return self._reverse_refs.get(target_key, [])

    def get_referenced_content(self, content_type: ContentType) -> list[str]:
        """Get list of all content names that are referenced for a given type."""
        referenced = self._referenced_by_type.get(content_type, set())
        return [ref.split("|")[0] for ref in referenced]

    def get_reference_statistics(self) -> dict[str, Any]:
        """Get statistics about references in the index."""
        stats: dict[str, Any] = {
            "total_references": sum(len(refs) for refs in self._forward_refs.values()),
            "content_with_references": len(self._forward_refs),
            "referenced_content": len(self._reverse_refs),
            "by_type": {},
        }

        for content_type, referenced in self._referenced_by_type.items():
            stats["by_type"][content_type.value] = len(referenced)

        return stats

    def _get_content_key(self, content: BaseContent) -> str:
        """Generate a unique key for content."""
        return f"{content.__class__.__name__.lower()}:{content.name}:{content.source.abbreviation}"

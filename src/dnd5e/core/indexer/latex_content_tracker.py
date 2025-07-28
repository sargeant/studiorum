"""Enhanced content tracker with LaTeX-specific metadata and appendix generation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from dnd5e.core.logging import get_logger

from .content_tracker import ContentTracker, TrackedContent

logger = get_logger(__name__)


@dataclass
class LaTeXTrackedContent(TrackedContent):
    """Enhanced tracked content with LaTeX-specific metadata."""

    # LaTeX-specific fields
    ref_id: str | None = None  # Cross-reference ID
    latex_label: str | None = None  # LaTeX label for \\ref commands
    hyperlink_target: bool = False  # Whether this is a hyperlink target
    appendix_section: str | None = None  # Which appendix section this belongs to
    usage_count: int = 0  # Number of times referenced
    first_reference_page: int | None = None  # Page of first reference
    definition_page: int | None = None  # Page where content is defined

    # Additional metadata
    metadata: dict[str, Any] = field(default_factory=dict)


class LaTeXContentTracker(ContentTracker):
    """Enhanced content tracker with LaTeX-specific features."""

    def __init__(self) -> None:
        super().__init__()
        self.latex_content: dict[str, LaTeXTrackedContent] = {}
        self.reference_counts: dict[str, int] = {}
        self.appendix_sections: dict[str, list[str]] = {}
        self.cross_references: dict[str, str] = {}  # ref_id -> content_key mapping

    def track_latex_content(
        self,
        content_type: str,
        name: str,
        source: str | None = None,
        page: str | None = None,
        ref_id: str | None = None,
        latex_label: str | None = None,
        hyperlink_target: bool = False,
        appendix_section: str | None = None,
        **metadata: Any,
    ) -> str:
        """Track content with LaTeX-specific metadata."""
        # Use parent tracking for basic functionality
        self.add_content(content_type, name, source, page)

        # Create or update LaTeX content entry
        content_key = self._create_content_key(content_type, name, source)

        if content_key in self.latex_content:
            # Update existing entry
            latex_content = self.latex_content[content_key]
            latex_content.usage_count += 1
            if ref_id and not latex_content.ref_id:
                latex_content.ref_id = ref_id
            if latex_label and not latex_content.latex_label:
                latex_content.latex_label = latex_label
            if hyperlink_target:
                latex_content.hyperlink_target = True
            if appendix_section and not latex_content.appendix_section:
                latex_content.appendix_section = appendix_section
            latex_content.metadata.update(metadata)
        else:
            # Create new entry
            latex_content = LaTeXTrackedContent(
                content_type=content_type,
                name=name,
                source=source,
                page=page,
                ref_id=ref_id,
                latex_label=latex_label,
                hyperlink_target=hyperlink_target,
                appendix_section=appendix_section,
                usage_count=1,
                metadata=metadata,
            )
            self.latex_content[content_key] = latex_content

        # Track cross-reference mapping
        if ref_id:
            self.cross_references[ref_id] = content_key

        # Track reference count
        self.reference_counts[content_key] = latex_content.usage_count

        # Organize by appendix section
        if appendix_section:
            if appendix_section not in self.appendix_sections:
                self.appendix_sections[appendix_section] = []
            if content_key not in self.appendix_sections[appendix_section]:
                self.appendix_sections[appendix_section].append(content_key)

        logger.debug(f"Tracked LaTeX content: {content_key} (ref_id: {ref_id})")
        return content_key

    def get_latex_content(self, content_key: str) -> LaTeXTrackedContent | None:
        """Get LaTeX-specific content by key."""
        return self.latex_content.get(content_key)

    def get_content_by_ref_id(self, ref_id: str) -> LaTeXTrackedContent | None:
        """Get content by reference ID."""
        content_key = self.cross_references.get(ref_id)
        return self.latex_content.get(content_key) if content_key else None

    def set_definition_page(self, content_key: str, page: int) -> None:
        """Set the page where content is defined."""
        if content_key in self.latex_content:
            self.latex_content[content_key].definition_page = page

    def set_first_reference_page(self, content_key: str, page: int) -> None:
        """Set the page of first reference."""
        latex_content = self.latex_content.get(content_key)
        if latex_content and latex_content.first_reference_page is None:
            latex_content.first_reference_page = page

    def get_most_referenced_content(self, limit: int = 10) -> list[LaTeXTrackedContent]:
        """Get most frequently referenced content."""
        sorted_content = sorted(
            self.latex_content.values(), key=lambda c: c.usage_count, reverse=True
        )
        return sorted_content[:limit]

    def get_unreferenced_content(self) -> list[LaTeXTrackedContent]:
        """Get content that hasn't been referenced."""
        return [
            content
            for content in self.latex_content.values()
            if content.usage_count == 0
        ]

    def get_content_by_type(self, content_type: str) -> list[LaTeXTrackedContent]:
        """Get all content of a specific type."""
        return [
            content
            for content in self.latex_content.values()
            if content.content_type == content_type
        ]

    def get_appendix_content(
        self, section: str | None = None
    ) -> dict[str, list[LaTeXTrackedContent]]:
        """Get content organized for appendix generation."""
        if section:
            # Get specific section
            content_keys = self.appendix_sections.get(section, [])
            return {
                section: [
                    self.latex_content[key]
                    for key in content_keys
                    if key in self.latex_content
                ]
            }
        else:
            # Get all sections
            result = {}
            for section_name, content_keys in self.appendix_sections.items():
                result[section_name] = [
                    self.latex_content[key]
                    for key in content_keys
                    if key in self.latex_content
                ]
            return result

    def export_for_latex_appendix(self) -> dict[str, Any]:
        """Export content in format optimized for LaTeX appendix generation."""
        # Group content by type and sort by name
        by_type: dict[str, list[dict[str, Any]]] = {}

        for content in self.latex_content.values():
            content_type = content.content_type
            if content_type not in by_type:
                by_type[content_type] = []

            # Create appendix entry
            entry: dict[str, Any] = {
                "name": content.name,
                "source": content.source,
                "page": content.page,
                "ref_id": content.ref_id,
                "latex_label": content.latex_label,
                "usage_count": content.usage_count,
                "first_reference_page": content.first_reference_page,
                "definition_page": content.definition_page,
                "hyperlink_target": content.hyperlink_target,
            }

            # Add metadata
            if content.metadata:
                entry["metadata"] = content.metadata

            by_type[content_type].append(entry)

        # Sort each type by name
        for content_list in by_type.values():
            content_list.sort(key=lambda x: x["name"])

        return {
            "content_by_type": by_type,
            "appendix_sections": self.appendix_sections,
            "reference_counts": self.reference_counts,
            "total_unique_content": len(self.latex_content),
            "total_references": sum(self.reference_counts.values()),
            "statistics": self.get_latex_statistics(),
        }

    def get_latex_statistics(self) -> dict[str, Any]:
        """Get comprehensive statistics about tracked content."""
        stats = super().get_statistics()

        # Add LaTeX-specific statistics
        hyperlink_targets = sum(
            1 for content in self.latex_content.values() if content.hyperlink_target
        )

        with_definitions = sum(
            1
            for content in self.latex_content.values()
            if content.definition_page is not None
        )

        orphaned_references = sum(
            1
            for content in self.latex_content.values()
            if content.usage_count > 0 and content.definition_page is None
        )

        stats.update(
            {
                "hyperlink_targets": hyperlink_targets,
                "content_with_definitions": with_definitions,
                "orphaned_references": orphaned_references,
                "appendix_sections": len(self.appendix_sections),
                "cross_references": len(self.cross_references),
            }
        )

        return stats

    def generate_latex_appendix_structure(self) -> dict[str, Any]:
        """Generate structure for LaTeX appendix compilation."""
        structure: dict[str, Any] = {
            "sections": {},
            "indices": {},
            "cross_references": {},
        }

        # Group content by type for appendix sections
        content_types = {
            "creature": {"title": "Creatures", "order": 1},
            "spell": {"title": "Spells", "order": 2},
            "item": {"title": "Magic Items", "order": 3},
            "class": {"title": "Classes", "order": 4},
            "race": {"title": "Races", "order": 5},
            "background": {"title": "Backgrounds", "order": 6},
            "feat": {"title": "Feats", "order": 7},
            "condition": {"title": "Conditions", "order": 8},
            "adventure": {"title": "Adventures", "order": 9},
            "book": {"title": "Source Books", "order": 10},
        }

        for content_type, info in content_types.items():
            content_list = self.get_content_by_type(content_type)
            if content_list:
                # Sort by name
                content_list.sort(key=lambda c: c.name)

                structure["sections"][content_type] = {
                    "title": info["title"],
                    "order": info["order"],
                    "content": [
                        {
                            "name": content.name,
                            "source": content.source,
                            "page": content.page,
                            "latex_label": content.latex_label,
                            "ref_id": content.ref_id,
                        }
                        for content in content_list
                    ],
                }

        # Generate alphabetical index
        all_content = sorted(self.latex_content.values(), key=lambda c: c.name)
        structure["indices"]["alphabetical"] = [
            {
                "name": content.name,
                "type": content.content_type,
                "ref_id": content.ref_id,
                "latex_label": content.latex_label,
            }
            for content in all_content
        ]

        # Generate cross-reference mapping
        structure["cross_references"] = {
            ref_id: {
                "content_key": content_key,
                "name": self.latex_content[content_key].name,
                "type": self.latex_content[content_key].content_type,
            }
            for ref_id, content_key in self.cross_references.items()
            if content_key in self.latex_content
        }

        return structure

    def validate_cross_references(self) -> list[dict[str, str]]:
        """Validate cross-references and return any issues."""
        issues = []

        # Check for orphaned cross-references
        for ref_id, content_key in self.cross_references.items():
            if content_key not in self.latex_content:
                issues.append(
                    {
                        "type": "orphaned_cross_reference",
                        "ref_id": ref_id,
                        "content_key": content_key,
                        "message": f"Cross-reference {ref_id} points to non-existent content {content_key}",
                    }
                )

        # Check for content without definitions
        for content in self.latex_content.values():
            if content.usage_count > 0 and content.definition_page is None:
                issues.append(
                    {
                        "type": "missing_definition",
                        "name": content.name,
                        "content_type": content.content_type,
                        "message": f"{content.content_type.title()} '{content.name}' is referenced but not defined",
                    }
                )

        # Check for duplicate reference IDs
        ref_id_counts: dict[str, int] = {}
        for content in self.latex_content.values():
            if content.ref_id:
                ref_id_counts[content.ref_id] = ref_id_counts.get(content.ref_id, 0) + 1

        for ref_id, count in ref_id_counts.items():
            if count > 1:
                issues.append(
                    {
                        "type": "duplicate_ref_id",
                        "ref_id": ref_id,
                        "count": str(count),
                        "message": f"Reference ID {ref_id} is used {count} times",
                    }
                )

        return issues

    def clear(self) -> None:
        """Clear all tracked content including LaTeX metadata."""
        super().clear()
        self.latex_content.clear()
        self.reference_counts.clear()
        self.appendix_sections.clear()
        self.cross_references.clear()

    def _create_content_key(
        self, content_type: str, name: str, source: str | None = None
    ) -> str:
        """Create a unique key for content."""
        if source:
            return f"{content_type}:{name}:{source}"
        return f"{content_type}:{name}"

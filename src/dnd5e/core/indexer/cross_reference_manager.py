"""Cross-reference management for LaTeX document generation."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from dnd5e.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class CrossReference:
    """Represents a cross-reference in the document."""

    id: str  # Unique identifier (e.g., "creature:ancient-red-dragon")
    content_type: str  # Type of content ("creature", "spell", etc.)
    name: str  # Display name ("Ancient Red Dragon")
    source: str | None = None  # Source book ("MM", "PHB", etc.)
    page: str | None = None  # Page in source book
    latex_label: str | None = None  # Generated LaTeX label
    section: str | None = None  # Document section where defined
    referenced_count: int = 0  # Number of times referenced


class CrossReferenceManager:
    """Manages cross-references and LaTeX label generation for documents."""

    def __init__(self) -> None:
        self.references: dict[str, CrossReference] = {}
        self.reference_format = "page"  # "page", "section", "name", "full"
        self.label_prefix = ""  # Optional prefix for all labels
        self.auto_page_refs = True  # Automatically add page references

    def register_content(
        self,
        content_type: str,
        name: str,
        ref_id: str | None = None,
        source: str | None = None,
        page: str | None = None,
        section: str | None = None,
    ) -> str:
        """Register content for cross-referencing and return the reference ID."""
        # Generate reference ID if not provided
        if ref_id is None:
            ref_id = self.generate_reference_id(content_type, name)

        # Generate LaTeX label
        latex_label = self.generate_latex_label(ref_id)

        # Create or update reference
        if ref_id in self.references:
            # Update existing reference
            ref = self.references[ref_id]
            ref.referenced_count += 1
            if source and not ref.source:
                ref.source = source
            if page and not ref.page:
                ref.page = page
            if section and not ref.section:
                ref.section = section
        else:
            # Create new reference
            ref = CrossReference(
                id=ref_id,
                content_type=content_type,
                name=name,
                source=source,
                page=page,
                latex_label=latex_label,
                section=section,
                referenced_count=1,
            )
            self.references[ref_id] = ref

        logger.debug(f"Registered cross-reference: {ref_id} -> {name}")
        return ref_id

    def generate_reference_id(self, content_type: str, name: str) -> str:
        """Generate a unique reference ID for content."""
        # Sanitize name for use in IDs
        safe_name = self._sanitize_for_id(name)
        return f"{content_type}:{safe_name}"

    def generate_latex_label(self, ref_id: str) -> str:
        """Generate a LaTeX label from reference ID."""
        # Apply prefix if set
        if self.label_prefix:
            return f"{self.label_prefix}:{ref_id}"
        return ref_id

    def _sanitize_for_id(self, text: str) -> str:
        """Sanitize text for use in reference IDs and LaTeX labels."""
        # Convert to lowercase
        text = text.lower()

        # Replace problematic characters with hyphens
        text = re.sub(r"[^a-z0-9]+", "-", text)

        # Remove leading/trailing hyphens
        text = text.strip("-")

        # Ensure it's not empty
        return text if text else "unnamed"

    def get_reference(self, ref_id: str) -> CrossReference | None:
        """Get reference by ID."""
        return self.references.get(ref_id)

    def get_reference_by_name(
        self, content_type: str, name: str
    ) -> CrossReference | None:
        """Get reference by content type and name."""
        ref_id = self.generate_reference_id(content_type, name)
        return self.references.get(ref_id)

    def create_latex_reference(
        self,
        ref_id: str,
        display_text: str | None = None,
        include_page_ref: bool | None = None,
        ref_type: str = "hyperref",
    ) -> str:
        """Create a LaTeX reference command."""
        ref = self.get_reference(ref_id)
        if not ref:
            logger.warning(f"Reference not found: {ref_id}")
            return display_text or ref_id

        # Use display text or reference name
        text = display_text or ref.name
        label = ref.latex_label

        # Determine if page reference should be included
        if include_page_ref is None:
            include_page_ref = self.auto_page_refs and self._should_include_page_ref(
                ref
            )

        # Generate appropriate LaTeX command
        if ref_type == "hyperref":
            # Create hyperlinked reference
            latex_ref = f"\\hyperref[{label}]{{{text}}}"
            if include_page_ref:
                latex_ref += f" (p. \\pageref{{{label}}})"
        elif ref_type == "ref":
            # Simple reference
            latex_ref = f"\\ref{{{label}}}"
        elif ref_type == "pageref":
            # Page reference only
            latex_ref = f"\\pageref{{{label}}}"
        elif ref_type == "nameref":
            # Name reference
            latex_ref = f"\\nameref{{{label}}}"
        else:
            # Custom or unknown type
            latex_ref = f"\\{ref_type}{{{label}}}"

        return latex_ref

    def _should_include_page_ref(self, ref: CrossReference) -> bool:
        """Determine if page reference should be included for this content type."""
        # Include page refs for major content types that appear in appendices
        major_types = {
            "creature",
            "spell",
            "item",
            "class",
            "race",
            "background",
            "feat",
        }
        return ref.content_type in major_types

    def create_latex_label(self, ref_id: str) -> str:
        """Create a LaTeX label command for placement in the document."""
        ref = self.get_reference(ref_id)
        if not ref:
            logger.warning(f"Cannot create label for unknown reference: {ref_id}")
            return ""

        return f"\\label{{{ref.latex_label}}}"

    def get_all_references(self) -> dict[str, CrossReference]:
        """Get all registered references."""
        return self.references.copy()

    def get_references_by_type(self, content_type: str) -> list[CrossReference]:
        """Get all references of a specific content type."""
        return [
            ref for ref in self.references.values() if ref.content_type == content_type
        ]

    def get_reference_statistics(self) -> dict[str, Any]:
        """Get statistics about references."""
        stats: dict[str, Any] = {
            "total_references": len(self.references),
            "by_type": {},
            "most_referenced": [],
            "unreferenced": [],
        }

        # Count by type
        for ref in self.references.values():
            if ref.content_type not in stats["by_type"]:
                stats["by_type"][ref.content_type] = 0
            stats["by_type"][ref.content_type] += 1

        # Most referenced content
        sorted_refs = sorted(
            self.references.values(), key=lambda r: r.referenced_count, reverse=True
        )
        stats["most_referenced"] = [
            {"name": ref.name, "type": ref.content_type, "count": ref.referenced_count}
            for ref in sorted_refs[:10]
        ]

        # Unreferenced content
        stats["unreferenced"] = [
            {"name": ref.name, "type": ref.content_type}
            for ref in self.references.values()
            if ref.referenced_count == 0
        ]

        return stats

    def export_for_latex_document(self) -> dict[str, Any]:
        """Export references in format suitable for LaTeX document generation."""
        return {
            "references": {
                ref_id: {
                    "label": ref.latex_label,
                    "name": ref.name,
                    "type": ref.content_type,
                    "source": ref.source,
                    "page": ref.page,
                    "section": ref.section,
                }
                for ref_id, ref in self.references.items()
            },
            "labels": [ref.latex_label for ref in self.references.values()],
            "by_type": {
                content_type: [
                    {
                        "id": ref.id,
                        "name": ref.name,
                        "label": ref.latex_label,
                        "source": ref.source,
                        "page": ref.page,
                    }
                    for ref in refs
                ]
                for content_type, refs in self._group_by_type().items()
            },
        }

    def _group_by_type(self) -> dict[str, list[CrossReference]]:
        """Group references by content type."""
        groups: dict[str, list[CrossReference]] = {}
        for ref in self.references.values():
            if ref.content_type not in groups:
                groups[ref.content_type] = []
            groups[ref.content_type].append(ref)

        # Sort each group by name
        for refs in groups.values():
            refs.sort(key=lambda r: r.name)

        return groups

    def validate_references(self) -> list[dict[str, str | None]]:
        """Validate all references and return any issues."""
        issues = []

        for ref_id, ref in self.references.items():
            # Check for valid LaTeX labels
            if not self._is_valid_latex_label(ref.latex_label):
                issues.append(
                    {
                        "type": "invalid_label",
                        "ref_id": ref_id,
                        "label": ref.latex_label,
                        "message": f"Invalid LaTeX label: {ref.latex_label}",
                    }
                )

            # Check for duplicate names within types
            duplicates = [
                other_ref
                for other_ref in self.references.values()
                if (
                    other_ref.content_type == ref.content_type
                    and other_ref.name == ref.name
                    and other_ref.id != ref.id
                )
            ]
            if duplicates:
                issues.append(
                    {
                        "type": "duplicate_name",
                        "ref_id": ref_id,
                        "name": ref.name,
                        "message": f"Duplicate name '{ref.name}' in type '{ref.content_type}'",
                    }
                )

        return issues

    def _is_valid_latex_label(self, label: str | None) -> bool:
        """Check if a string is a valid LaTeX label."""
        if not label:
            return False

        # LaTeX labels should only contain letters, numbers, hyphens, and underscores
        return bool(re.match(r"^[a-zA-Z0-9_:-]+$", label))

    def set_reference_format(self, ref_format: str) -> None:
        """Set the default format for generating references."""
        valid_formats = {"page", "section", "name", "full"}
        if ref_format in valid_formats:
            self.reference_format = ref_format
        else:
            raise ValueError(
                f"Invalid reference format: {ref_format}. Must be one of {valid_formats}"
            )

    def set_label_prefix(self, prefix: str) -> None:
        """Set a prefix for all LaTeX labels."""
        self.label_prefix = self._sanitize_for_id(prefix) if prefix else ""

    def clear_references(self) -> None:
        """Clear all registered references."""
        self.references.clear()
        logger.info("Cleared all cross-references")

    def merge_references(self, other: CrossReferenceManager) -> None:
        """Merge references from another manager."""
        for ref_id, ref in other.references.items():
            if ref_id in self.references:
                # Merge reference counts
                self.references[ref_id].referenced_count += ref.referenced_count
            else:
                # Add new reference
                self.references[ref_id] = ref

        logger.info(f"Merged {len(other.references)} references")

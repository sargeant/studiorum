"""Reference resolution system for LaTeX document generation."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator

from dnd5e.core.base_context import DocumentContext
from dnd5e.core.logging import get_logger

logger = get_logger(__name__)


class ReferenceContext(DocumentContext):
    """Context for reference resolution with validation.

    Inherits from DocumentContext to provide standardized document state management
    while maintaining backward compatibility with existing reference resolution code.
    """

    # Additional reference-specific configuration
    cross_ref_enabled: bool = Field(
        True, description="Whether cross-references are enabled"
    )
    hyperlinks_enabled: bool = Field(True, description="Whether hyperlinks are enabled")

    @field_validator("document_type")
    @classmethod
    def validate_document_type(cls, v: str) -> str:
        """Validate document type values."""
        valid_types = {"general", "adventure", "reference", "supplement"}
        cleaned = v.strip().lower()
        if cleaned not in valid_types:
            raise ValueError(
                f"Document type must be one of {valid_types}, got '{cleaned}'"
            )
        return cleaned

    @field_validator("current_section")
    @classmethod
    def validate_current_section(cls, v: str) -> str:
        """Validate and normalize section name."""
        return v.strip()

    @property
    def is_cross_ref_active(self) -> bool:
        """Check if cross-references should be actively generated."""
        return self.cross_ref_enabled and not self.appendix_mode

    @property
    def is_hyperlink_active(self) -> bool:
        """Check if hyperlinks should be actively generated."""
        return self.hyperlinks_enabled and self.cross_ref_enabled


class ReferenceResolver:
    """Resolves and manages references in LaTeX documents."""

    def __init__(self, tag_integration: Any) -> None:
        """Initialize with tag integration system."""
        self.tag_integration = tag_integration
        self.reference_cache: dict[str, str] = {}
        self.forward_references: dict[str, list[str]] = {}
        self.reverse_references: dict[str, list[str]] = {}
        self.unresolved_references: set[str] = set()

    def resolve_content_reference(
        self,
        content_type: str,
        name: str,
        context: ReferenceContext,
        display_text: str | None = None,
        force_hyperlink: bool = False,
    ) -> str:
        """Resolve a content reference with appropriate formatting."""
        # Create cache key
        cache_key = f"{content_type}:{name}:{context.document_type}"

        if cache_key in self.reference_cache and not force_hyperlink:
            return self.reference_cache[cache_key]

        # Get cross-reference manager
        cross_ref_mgr = self.tag_integration.cross_ref_manager
        hyperlink_mgr = self.tag_integration.hyperlink_manager

        if not cross_ref_mgr:
            # No cross-reference support, return basic formatting
            formatted = self._apply_basic_formatting(content_type, display_text or name)
            self.reference_cache[cache_key] = formatted
            return formatted

        # Register content and get reference ID
        ref_id = cross_ref_mgr.register_content(content_type, name)

        # Determine if we should create hyperlink
        should_hyperlink = (
            context.hyperlinks_enabled
            and hyperlink_mgr
            and (force_hyperlink or hyperlink_mgr.should_create_hyperlink(content_type))
        )

        if should_hyperlink:
            # Create hyperlinked reference
            base_text = self._apply_basic_formatting(content_type, display_text or name)
            result = hyperlink_mgr.create_hyperlink(
                text=base_text,
                ref_id=ref_id,
                content_type=content_type,
                include_page_ref=self._should_include_page_ref(content_type, context),
            )
        else:
            # Create basic cross-reference without hyperlink
            result = cross_ref_mgr.create_latex_reference(
                ref_id=ref_id,
                display_text=self._apply_basic_formatting(
                    content_type, display_text or name
                ),
                include_page_ref=self._should_include_page_ref(content_type, context),
                ref_type="ref" if context.cross_ref_enabled else "text",
            )

        # Track reference relationship
        self._track_reference_relationship(ref_id, context)

        # Cache result
        self.reference_cache[cache_key] = result
        return str(result)

    def _apply_basic_formatting(self, content_type: str, text: str) -> str:
        """Apply basic LaTeX formatting based on content type."""
        formatting_map = {
            "creature": "\\textbf{{{text}}}",
            "spell": "\\textit{{{text}}}",
            "item": "\\textit{{{text}}}",
            "class": "\\textbf{{{text}}}",
            "feat": "\\textbf{{{text}}}",
            "condition": "\\textit{{{text}}}",
            "adventure": "\\textit{{{text}}}",
            "book": "\\textit{{{text}}}",
        }

        template = formatting_map.get(content_type, "{text}")
        return template.format(text=text)

    def _should_include_page_ref(
        self, content_type: str, context: ReferenceContext
    ) -> bool:
        """Determine if page reference should be included."""
        # Don't include page refs in appendix mode (circular references)
        if context.appendix_mode:
            return False

        # Include for major content types in adventures and supplements
        major_types = {"creature", "spell", "item", "class", "race", "feat"}
        return content_type in major_types and context.document_type in {
            "adventure",
            "supplement",
        }

    def _track_reference_relationship(
        self, ref_id: str, context: ReferenceContext
    ) -> None:
        """Track forward/backward reference relationships."""
        current_location = f"{context.current_section}:{context.current_page}"

        # Track forward reference (from current location to target)
        if current_location not in self.forward_references:
            self.forward_references[current_location] = []
        if ref_id not in self.forward_references[current_location]:
            self.forward_references[current_location].append(ref_id)

        # Track backward reference (from target to current location)
        if ref_id not in self.reverse_references:
            self.reverse_references[ref_id] = []
        if current_location not in self.reverse_references[ref_id]:
            self.reverse_references[ref_id].append(current_location)

    def create_definition_label(
        self, content_type: str, name: str, context: ReferenceContext
    ) -> str:
        """Create a LaTeX label for content definition."""
        cross_ref_mgr = self.tag_integration.cross_ref_manager
        if not cross_ref_mgr:
            return ""

        ref_id = cross_ref_mgr.register_content(content_type, name)
        label = cross_ref_mgr.create_latex_label(ref_id)

        # Track that this content is defined here
        self.tag_integration.content_tracker.set_definition_page(
            f"{content_type}:{name}", context.current_page
        )

        return str(label)

    def resolve_adventure_reference(
        self,
        adventure_name: str,
        chapter: str | None = None,
        page: str | None = None,
        context: ReferenceContext | None = None,
    ) -> str:
        """Resolve adventure reference with chapter and page information."""
        context = context or ReferenceContext()

        # Build display text
        if chapter and page:
            display_text = f'{adventure_name}, "{chapter}" (p. {page})'
        elif chapter:
            display_text = f'{adventure_name}, "{chapter}"'
        elif page:
            display_text = f"{adventure_name} (p. {page})"
        else:
            display_text = adventure_name

        return self.resolve_content_reference(
            content_type="adventure",
            name=adventure_name,
            context=context,
            display_text=display_text,
        )

    def resolve_book_reference(
        self,
        book_name: str,
        page: str | None = None,
        context: ReferenceContext | None = None,
    ) -> str:
        """Resolve book reference with page information."""
        context = context or ReferenceContext()

        # Build display text
        if page:
            display_text = f"{book_name}, p. {page}"
        else:
            display_text = book_name

        return self.resolve_content_reference(
            content_type="book",
            name=book_name,
            context=context,
            display_text=display_text,
        )

    def resolve_section_reference(
        self,
        section_name: str,
        ref_type: str = "nameref",
        context: ReferenceContext | None = None,
    ) -> str:
        """Resolve reference to document section."""
        hyperlink_mgr = self.tag_integration.hyperlink_manager
        if not hyperlink_mgr:
            return section_name

        # Create section label (sanitized)
        section_label = self._sanitize_section_label(section_name)

        return str(
            hyperlink_mgr.create_section_reference(
                text=section_name,
                section_label=section_label,
                ref_type=ref_type,
            )
        )

    def _sanitize_section_label(self, section_name: str) -> str:
        """Sanitize section name for use as LaTeX label."""
        import re

        sanitized = re.sub(r"[^a-zA-Z0-9]+", "-", section_name.lower())
        return sanitized.strip("-")

    def generate_forward_reference_list(self, ref_id: str) -> list[str]:
        """Generate list of locations that reference this content."""
        return self.reverse_references.get(ref_id, [])

    def generate_reverse_reference_list(self, location: str) -> list[str]:
        """Generate list of content referenced from this location."""
        return self.forward_references.get(location, [])

    def find_unresolved_references(self) -> list[dict[str, str]]:
        """Find references that couldn't be resolved."""
        issues: list[dict[str, str]] = []
        cross_ref_mgr = self.tag_integration.cross_ref_manager

        if not cross_ref_mgr:
            return issues

        # Check for references without definitions
        all_refs = cross_ref_mgr.get_all_references()
        content_tracker = self.tag_integration.content_tracker

        for ref_id, ref_data in all_refs.items():
            # Check if content has a definition
            content_key = f"{ref_data.content_type}:{ref_data.name}"
            latex_content = content_tracker.get_latex_content(content_key)

            if not latex_content or latex_content.definition_page is None:
                issues.append(
                    {
                        "type": "unresolved_reference",
                        "ref_id": ref_id,
                        "content_type": ref_data.content_type,
                        "name": ref_data.name,
                        "message": f"Referenced {ref_data.content_type} '{ref_data.name}' has no definition",
                    }
                )

        return issues

    def generate_reference_report(self) -> dict[str, Any]:
        """Generate comprehensive reference report."""
        cross_ref_mgr = self.tag_integration.cross_ref_manager
        content_tracker = self.tag_integration.content_tracker

        report: dict[str, Any] = {
            "total_references": len(self.reference_cache),
            "forward_references": len(self.forward_references),
            "reverse_references": len(self.reverse_references),
            "unresolved": len(self.unresolved_references),
        }

        if cross_ref_mgr:
            report["cross_reference_stats"] = cross_ref_mgr.get_reference_statistics()

        if content_tracker:
            report["content_stats"] = content_tracker.get_latex_statistics()

        # Most referenced content
        if content_tracker:
            most_referenced = content_tracker.get_most_referenced_content(10)
            report["most_referenced"] = [
                {
                    "name": content.name,
                    "type": content.content_type,
                    "usage_count": content.usage_count,
                }
                for content in most_referenced
            ]

        return report

    def clear_cache(self) -> None:
        """Clear reference resolution cache."""
        self.reference_cache.clear()
        self.forward_references.clear()
        self.reverse_references.clear()
        self.unresolved_references.clear()

    def export_reference_data_for_compilation(self) -> dict[str, Any]:
        """Export reference data needed for LaTeX compilation."""
        data = {
            "required_packages": self.tag_integration.get_required_latex_packages(),
            "preamble_commands": self.tag_integration.get_latex_preamble_commands(),
            "cross_references": {},
            "appendix_data": {},
        }

        # Export cross-reference data
        if self.tag_integration.cross_ref_manager:
            data["cross_references"] = (
                self.tag_integration.export_cross_reference_data()
            )

        # Export appendix data
        data["appendix_data"] = self.tag_integration.export_appendix_data()

        return data


# Rebuild models that use forward references from base_context
def _rebuild_reference_models() -> None:
    """Rebuild reference models after base context models are available."""
    try:
        from dnd5e.core.loaders.omnidexer import Omnidexer  # noqa: F401

        ReferenceContext.model_rebuild()
    except ImportError:
        # Dependencies not yet available, rebuilds will happen later
        pass


# Trigger rebuild immediately if possible
_rebuild_reference_models()

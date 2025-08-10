"""Enhanced content tracker with LaTeX-specific metadata and appendix generation."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from dnd5e.core.logging import get_logger

from .content_tracker import ContentTracker, TrackedContent

logger = get_logger(__name__)


class LaTeXMetadata(BaseModel):
    """Structured LaTeX-specific metadata for content tracking."""

    compilation_target: str | None = Field(None, description="LaTeX compilation target")
    section_depth: int | None = Field(None, description="Nesting depth in document")
    table_format: str | None = Field(None, description="Table formatting options")
    image_options: str | None = Field(None, description="Image rendering options")
    custom_commands: list[str] = Field(
        default_factory=list, description="Custom LaTeX commands"
    )

    # Allow additional metadata fields for flexibility
    model_config = {"extra": "allow"}

    @field_validator("custom_commands", mode="before")
    @classmethod
    def parse_custom_commands(cls, v: Any) -> list[str]:
        """Parse custom commands from various formats."""
        if isinstance(v, list):
            return [str(cmd) for cmd in v]
        elif isinstance(v, str):
            return [v]
        elif v is None:
            return []
        return [str(v)]


class PageReference(BaseModel):
    """Page reference tracking for LaTeX cross-references."""

    first_reference: int | None = Field(None, description="Page of first reference")
    definition: int | None = Field(None, description="Page where content is defined")
    last_reference: int | None = Field(None, description="Page of last reference")
    total_references: int = Field(0, description="Total number of references")


class LaTeXReference(BaseModel):
    """Cross-reference tracking for LaTeX content."""

    ref_id: str = Field(..., description="Cross-reference ID")
    content_key: str = Field(..., description="Internal content key")
    target_type: str = Field(..., description="Type of referenced content")
    latex_label: str | None = Field(None, description="LaTeX label for \\ref commands")


class AppendixEntry(BaseModel):
    """Structured entry for LaTeX appendix generation."""

    name: str = Field(..., description="Content name")
    source: str | None = Field(None, description="Source book/file")
    page: str | None = Field(None, description="Page reference")
    ref_id: str | None = Field(None, description="Cross-reference ID")
    latex_label: str | None = Field(None, description="LaTeX label")
    usage_count: int = Field(0, description="Number of references")
    first_reference_page: int | None = Field(None, description="First reference page")
    definition_page: int | None = Field(None, description="Definition page")
    hyperlink_target: bool = Field(False, description="Is hyperlink target")
    metadata: LaTeXMetadata | None = Field(None, description="Additional metadata")

    @field_validator("metadata", mode="before")
    @classmethod
    def parse_metadata(cls, v: Any) -> LaTeXMetadata | None:
        """Parse metadata from dict or existing model."""
        if v is None:
            return None
        if isinstance(v, dict):
            return LaTeXMetadata.model_validate(v)
        if isinstance(v, LaTeXMetadata):
            return v
        # Convert other types to dict and try parsing
        return LaTeXMetadata.model_validate({"custom_data": str(v)})


class ContentTypeInfo(BaseModel):
    """Configuration for content type in appendix generation."""

    title: str = Field(..., description="Display title for appendix section")
    order: int = Field(..., description="Sort order in appendix")
    include_in_index: bool = Field(True, description="Include in alphabetical index")
    section_prefix: str | None = Field(None, description="LaTeX section prefix")


class AppendixSection(BaseModel):
    """Structured section for LaTeX appendix."""

    title: str = Field(..., description="Section title")
    order: int = Field(..., description="Section order")
    content: list[AppendixEntry] = Field(
        default_factory=list, description="Section content"
    )
    include_in_index: bool = Field(True, description="Include in index")
    section_prefix: str | None = Field(None, description="LaTeX prefix")


class ContentIndex(BaseModel):
    """Alphabetical and type-based content index."""

    name: str = Field(..., description="Content name")
    content_type: str = Field(..., alias="type", description="Content type")
    ref_id: str | None = Field(None, description="Cross-reference ID")
    latex_label: str | None = Field(None, description="LaTeX label")


class CrossReferenceIssue(BaseModel):
    """Validation issue for cross-references."""

    issue_type: Literal[
        "orphaned_cross_reference", "missing_definition", "duplicate_ref_id"
    ] = Field(..., alias="type", description="Type of validation issue")
    message: str = Field(..., description="Human-readable issue description")
    ref_id: str | None = Field(None, description="Reference ID involved")
    content_key: str | None = Field(None, description="Content key involved")
    name: str | None = Field(None, description="Content name")
    content_type: str | None = Field(None, description="Content type")
    count: int | None = Field(None, description="Count for duplicate issues")


class LaTeXStatistics(BaseModel):
    """Comprehensive statistics for LaTeX content tracking."""

    total_unique_content: int = Field(0, description="Total unique content items")
    total_references: int = Field(0, description="Total reference count")
    hyperlink_targets: int = Field(0, description="Number of hyperlink targets")
    content_with_definitions: int = Field(
        0, description="Content with definition pages"
    )
    orphaned_references: int = Field(0, description="References without definitions")
    appendix_sections: int = Field(0, description="Number of appendix sections")
    cross_references: int = Field(0, description="Number of cross-references")

    # Additional statistics from parent ContentTracker
    content_by_type: dict[str, int] = Field(
        default_factory=dict, description="Content counts by type"
    )
    source_distribution: dict[str, int] = Field(
        default_factory=dict, description="Content by source"
    )


class ValidationResult(BaseModel):
    """Complete validation results for cross-references."""

    issues: list[CrossReferenceIssue] = Field(
        default_factory=list, description="Validation issues found"
    )
    total_issues: int = Field(0, description="Total number of issues")
    orphaned_cross_references: int = Field(
        0, description="Count of orphaned cross-references"
    )
    missing_definitions: int = Field(0, description="Count of missing definitions")
    duplicate_ref_ids: int = Field(0, description="Count of duplicate reference IDs")
    is_valid: bool = Field(True, description="Whether validation passed")

    def model_post_init(self, __context: Any) -> None:
        """Calculate summary statistics after model creation."""
        self.total_issues = len(self.issues)
        self.orphaned_cross_references = sum(
            1 for issue in self.issues if issue.issue_type == "orphaned_cross_reference"
        )
        self.missing_definitions = sum(
            1 for issue in self.issues if issue.issue_type == "missing_definition"
        )
        self.duplicate_ref_ids = sum(
            1 for issue in self.issues if issue.issue_type == "duplicate_ref_id"
        )
        self.is_valid = len(self.issues) == 0


class AppendixStructure(BaseModel):
    """Complete structure for LaTeX appendix generation."""

    sections: dict[str, AppendixSection] = Field(
        default_factory=dict, description="Appendix sections"
    )
    indices: dict[str, list[ContentIndex]] = Field(
        default_factory=dict, description="Content indices"
    )
    cross_references: dict[str, LaTeXReference] = Field(
        default_factory=dict, description="Cross-reference mapping"
    )
    content_by_type: dict[str, list[AppendixEntry]] = Field(
        default_factory=dict, description="Content grouped by type"
    )
    appendix_sections: dict[str, list[str]] = Field(
        default_factory=dict, description="Section organization"
    )
    reference_counts: dict[str, int] = Field(
        default_factory=dict, description="Reference count tracking"
    )
    statistics: LaTeXStatistics | None = Field(
        None, description="Processing statistics"
    )


class LaTeXTrackedContent(BaseModel):
    """Enhanced tracked content with LaTeX-specific metadata."""

    # Core content fields (from TrackedContent)
    content_type: str = Field(..., description="Type of content")
    name: str = Field(..., description="Content name")
    source: str | None = Field(None, description="Source book/file")
    page: str | None = Field(None, description="Page reference")

    # LaTeX-specific fields
    ref_id: str | None = Field(None, description="Cross-reference ID")
    latex_label: str | None = Field(None, description="LaTeX label for \\ref commands")
    hyperlink_target: bool = Field(
        False, description="Whether this is a hyperlink target"
    )
    appendix_section: str | None = Field(
        None, description="Which appendix section this belongs to"
    )
    usage_count: int = Field(0, description="Number of times referenced")
    first_reference_page: int | None = Field(
        None, description="Page of first reference"
    )
    definition_page: int | None = Field(
        None, description="Page where content is defined"
    )

    # Enhanced metadata with structure
    metadata: LaTeXMetadata = Field(
        default_factory=LaTeXMetadata, description="Additional LaTeX metadata"
    )

    @field_validator("metadata", mode="before")
    @classmethod
    def parse_metadata(cls, v: Any) -> LaTeXMetadata:
        """Parse metadata from dict or existing model."""
        if v is None:
            return LaTeXMetadata()
        if isinstance(v, dict):
            return LaTeXMetadata.model_validate(v)
        if isinstance(v, LaTeXMetadata):
            return v
        # Convert other types to LaTeXMetadata with custom data
        return LaTeXMetadata(custom_data=str(v))


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
            # Update metadata by merging with existing metadata
            if metadata:
                new_metadata_dict = latex_content.metadata.model_dump()
                new_metadata_dict.update(metadata)
                latex_content.metadata = LaTeXMetadata.model_validate(new_metadata_dict)
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
                metadata=LaTeXMetadata.model_validate(metadata)
                if metadata
                else LaTeXMetadata(),
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

    def export_for_latex_appendix(self) -> AppendixStructure:
        """Export content in format optimized for LaTeX appendix generation."""
        # Group content by type and sort by name
        by_type: dict[str, list[AppendixEntry]] = {}

        for content in self.latex_content.values():
            content_type = content.content_type
            if content_type not in by_type:
                by_type[content_type] = []

            # Create structured appendix entry
            entry = AppendixEntry(
                name=content.name,
                source=content.source,
                page=content.page,
                ref_id=content.ref_id,
                latex_label=content.latex_label,
                usage_count=content.usage_count,
                first_reference_page=content.first_reference_page,
                definition_page=content.definition_page,
                hyperlink_target=content.hyperlink_target,
                metadata=content.metadata if content.metadata else None,
            )

            by_type[content_type].append(entry)

        # Sort each type by name
        for content_list in by_type.values():
            content_list.sort(key=lambda x: x.name)

        return AppendixStructure(
            content_by_type=by_type,
            appendix_sections=self.appendix_sections,
            reference_counts=self.reference_counts,
            statistics=self.get_latex_statistics(),
        )

    def get_latex_statistics(self) -> LaTeXStatistics:
        """Get comprehensive statistics about tracked content."""
        base_stats = super().get_statistics()

        # Calculate LaTeX-specific statistics
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

        return LaTeXStatistics(
            total_unique_content=len(self.latex_content),
            total_references=sum(self.reference_counts.values()),
            hyperlink_targets=hyperlink_targets,
            content_with_definitions=with_definitions,
            orphaned_references=orphaned_references,
            appendix_sections=len(self.appendix_sections),
            cross_references=len(self.cross_references),
            content_by_type=base_stats.get("content_by_type", {}),
            source_distribution=base_stats.get("source_distribution", {}),
        )

    def generate_latex_appendix_structure(self) -> AppendixStructure:
        """Generate structure for LaTeX appendix compilation."""
        # Define content type configurations
        content_type_configs = {
            "creature": ContentTypeInfo(title="Creatures", order=1),
            "spell": ContentTypeInfo(title="Spells", order=2),
            "item": ContentTypeInfo(title="Magic Items", order=3),
            "class": ContentTypeInfo(title="Classes", order=4),
            "race": ContentTypeInfo(title="Races", order=5),
            "background": ContentTypeInfo(title="Backgrounds", order=6),
            "feat": ContentTypeInfo(title="Feats", order=7),
            "condition": ContentTypeInfo(title="Conditions", order=8),
            "adventure": ContentTypeInfo(title="Adventures", order=9),
            "book": ContentTypeInfo(title="Source Books", order=10),
        }

        sections: dict[str, AppendixSection] = {}
        for content_type, config in content_type_configs.items():
            content_list = self.get_content_by_type(content_type)
            if content_list:
                # Sort by name
                content_list.sort(key=lambda c: c.name)

                # Convert to AppendixEntry objects
                appendix_entries = [
                    AppendixEntry(
                        name=content.name,
                        source=content.source,
                        page=content.page,
                        latex_label=content.latex_label,
                        ref_id=content.ref_id,
                        usage_count=content.usage_count,
                        first_reference_page=content.first_reference_page,
                        definition_page=content.definition_page,
                        hyperlink_target=content.hyperlink_target,
                        metadata=content.metadata if content.metadata else None,
                    )
                    for content in content_list
                ]

                sections[content_type] = AppendixSection(
                    title=config.title,
                    order=config.order,
                    content=appendix_entries,
                    include_in_index=config.include_in_index,
                    section_prefix=config.section_prefix,
                )

        # Generate alphabetical index
        all_content = sorted(self.latex_content.values(), key=lambda c: c.name)
        alphabetical_index = [
            ContentIndex(
                name=content.name,
                type=content.content_type,
                ref_id=content.ref_id,
                latex_label=content.latex_label,
            )
            for content in all_content
        ]

        # Generate cross-reference mapping
        cross_refs = {
            ref_id: LaTeXReference(
                ref_id=ref_id,
                content_key=content_key,
                target_type=self.latex_content[content_key].content_type,
                latex_label=self.latex_content[content_key].latex_label,
            )
            for ref_id, content_key in self.cross_references.items()
            if content_key in self.latex_content
        }

        return AppendixStructure(
            sections=sections,
            indices={"alphabetical": alphabetical_index},
            cross_references=cross_refs,
            appendix_sections=self.appendix_sections,
            reference_counts=self.reference_counts,
            statistics=self.get_latex_statistics(),
        )

    def validate_cross_references(self) -> ValidationResult:
        """Validate cross-references and return structured results."""
        issues: list[CrossReferenceIssue] = []

        # Check for orphaned cross-references
        for ref_id, content_key in self.cross_references.items():
            if content_key not in self.latex_content:
                issues.append(
                    CrossReferenceIssue(
                        type="orphaned_cross_reference",
                        ref_id=ref_id,
                        content_key=content_key,
                        message=f"Cross-reference {ref_id} points to non-existent content {content_key}",
                    )
                )

        # Check for content without definitions
        for content in self.latex_content.values():
            if content.usage_count > 0 and content.definition_page is None:
                issues.append(
                    CrossReferenceIssue(
                        type="missing_definition",
                        name=content.name,
                        content_type=content.content_type,
                        message=f"{content.content_type.title()} '{content.name}' is referenced but not defined",
                    )
                )

        # Check for duplicate reference IDs
        ref_id_counts: dict[str, int] = {}
        for content in self.latex_content.values():
            if content.ref_id:
                ref_id_counts[content.ref_id] = ref_id_counts.get(content.ref_id, 0) + 1

        for ref_id, count in ref_id_counts.items():
            if count > 1:
                issues.append(
                    CrossReferenceIssue(
                        type="duplicate_ref_id",
                        ref_id=ref_id,
                        count=count,
                        message=f"Reference ID {ref_id} is used {count} times",
                    )
                )

        return ValidationResult(issues=issues)

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

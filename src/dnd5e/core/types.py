"""Common type definitions for the dnd5e package.

This module defines reusable TypedDict schemas to replace dict[str, Any] usage
throughout the codebase. These provide better type safety while maintaining
flexibility for JSON-like data structures.
"""

from __future__ import annotations

from typing import Any, TypedDict


# Configuration Types
class RendererConfig(TypedDict, total=False):
    """Base configuration for renderers."""

    template_dir: str
    output_format: str
    debug: bool
    strict_mode: bool


class LaTeXConfig(TypedDict, total=False):
    """LaTeX-specific configuration options."""

    template_dir: str
    output_format: str
    debug: bool
    strict_mode: bool
    compiler: str
    passes: int
    extra_args: list[str]
    paper_size: str
    font_size: str
    document_class: str
    # Integration-specific options
    hyperlink_styles: dict[str, dict[str, Any]]
    cross_ref_format: str
    appendix_organization: str
    enable_hyperlinks: bool
    enable_cross_refs: bool
    auto_page_refs: bool


class LayoutConfig(TypedDict, total=False):
    """Layout configuration for rendering."""

    columns: int
    spacing: str
    margins: dict[str, str]
    float_placement: str


# Content Processing Types
class ProcessingContext(TypedDict, total=False):
    """Context information for content processing."""

    content_type: str
    source: str
    file_path: str
    item_name: str
    debug: bool


class RenderContext(TypedDict, total=False):
    """Context for rendering operations."""

    content_type: str
    source: str
    template_vars: dict[str, Any]
    layout_hints: dict[str, Any]
    debug: bool


# Data Structure Types
class EntryData(TypedDict, total=False):
    """Common structure for 5e content entries."""

    type: str
    name: str
    entries: list[str | dict[str, Any]]
    source: str


class SourceData(TypedDict, total=False):
    """Source book information."""

    name: str
    abbreviation: str
    page: int | str
    url: str


class MetadataDict(TypedDict, total=False):
    """Generic metadata dictionary."""

    title: str
    description: str
    author: str
    version: str
    tags: list[str]
    properties: dict[str, Any]


# Template and Content Types
class TemplateData(TypedDict, total=False):
    """Data passed to template engines."""

    title: str
    content: str
    metadata: MetadataDict
    variables: dict[str, Any]
    # Allow additional keys for template flexibility
    config: Any
    latex_config: Any
    document_class: str
    class_options: str
    content_type: str
    use_dnd_template: bool
    dnd_template_available: bool
    font_scheme: str
    paper_size: str
    font_size: str
    background: str
    enable_background: bool
    high_contrast: bool
    justified_text: bool
    fancy_headers: bool
    two_column: bool
    show_toc: bool
    show_index: bool
    enable_index: bool


class ContentData(TypedDict, total=False):
    """Processed content data."""

    type: str
    name: str
    rendered_content: str
    metadata: MetadataDict
    processing_info: dict[str, Any]


# Statistics and Summary Types
class ProcessingStats(TypedDict):
    """Statistics for processing operations."""

    total_items: int
    processed_items: int
    failed_items: int
    warnings: int
    errors: int


class ValidationSummary(TypedDict):
    """Summary of validation results."""

    total_validated: int
    validation_errors: int
    validation_warnings: int
    error_categories: dict[str, int]


# Export and Result Types
class ExportResult(TypedDict):
    """Result of an export operation."""

    success: bool
    output_path: str | None
    error_message: str | None
    stats: ProcessingStats


class CompilationResult(TypedDict):
    """Result of a compilation operation."""

    success: bool
    output_files: list[str]
    log_content: str
    errors: list[str]
    warnings: list[str]


# Creature-specific Types
class SpeedDict(TypedDict, total=False):
    """Dict structure for complex speed values."""

    number: int
    condition: str


class DamageDict(TypedDict, total=False):
    """Dict structure for damage resistance/immunity/vulnerability."""

    type: str
    note: str
    preNote: str
    resist: list[str]
    immune: list[str]
    vulnerable: list[str]
    special: str


class CreatureTypeDict(TypedDict, total=False):
    """Dict structure for complex creature types."""

    type: str
    note: str
    prefix: str
    suffix: str
    choose: list[str]
    tag: str
    special: str


class AlignmentDict(TypedDict, total=False):
    """Dict structure for complex alignment values."""

    alignment: list[str]
    chance: int
    note: str


class ChallengeRatingDict(TypedDict, total=False):
    """Dict structure for complex challenge ratings."""

    cr: str
    lair: str
    coven: str
    special: str


class SkillValue(TypedDict, total=False):
    """Dict structure for complex skill values."""

    value: str
    proficiency: str
    expertise: bool


# JSON Processing Types
class SourceRef(TypedDict, total=False):
    """Source reference in JSON data."""

    abbreviation: str
    name: str
    url: str
    page: int

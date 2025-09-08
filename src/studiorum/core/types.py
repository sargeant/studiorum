"""Common type definitions for the studiorum package.

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
    # Compilation-specific options
    latex_engine: str
    compilation_timeout: int
    max_passes: int
    show_progress: bool
    keep_temp_files: bool
    output_dir: str


# Content Processing Types
class ProcessingContext(TypedDict, total=False):
    """Context information for content processing."""

    content_type: str
    source: str
    file_path: str
    item_name: str
    debug: bool


class RenderContextDict(TypedDict, total=False):
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
    text: str
    entries: list[str | dict[str, Any]]
    source: str
    items: list[str | dict[str, Any]]


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
    resist: list[str | dict[str, Any]]
    immune: list[str | dict[str, Any]]
    vulnerable: list[str | dict[str, Any]]
    special: str
    cond: bool


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
    """Dict structure for complex challenge ratings.

    Supports various CR formats from 5etools:
    - Base CR with optional XP override
    - Lair variant with optional xpLair
    - Coven variant with optional xpCoven
    - Special text for custom displays
    """

    cr: str  # Base challenge rating (e.g., "24", "1/4")
    xp: int | None  # Optional base XP override
    lair: str | None  # Lair CR value (e.g., "24" for same CR in lair)
    xpLair: int | None  # Lair XP override (e.g., 75000 for Ancient Red Dragon)
    coven: str | None  # Coven CR value (e.g., "5" for Green Hag)
    xpCoven: int | None  # Coven XP override
    special: str | None  # Special text override for entire CR display


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


# Content Merger Types
class CacheMetadata(TypedDict):
    """Metadata for content cache entries."""

    mtime: float
    file_path: Any  # Path object
    access_time: float


class CacheStats(TypedDict):
    """Cache statistics for monitoring."""

    cached_items: int
    cache_keys: list[str]
    memory_usage_estimate: int
    max_cache_size: int
    hits: int
    misses: int
    evictions: int
    invalidations: int
    hit_rate: float
    total_requests: int
    cache_enabled: bool
    cache_ttl: float


class ContentFileData(TypedDict, total=False):
    """Structure for 5e.tools content files."""

    data: list[dict[str, Any]]  # Content sections
    _meta: dict[str, Any]


class MetadataEntry(TypedDict, total=False):
    """Adventure/book metadata entry from metadata files."""

    id: str
    name: str
    source: str
    contents: list[dict[str, Any]]
    published: str
    storyline: str
    level: dict[str, int]
    group: str


class ContentSection(TypedDict, total=False):
    """Content section from content files."""

    type: str
    name: str
    id: str
    entries: list[Any]


class MergedContent(TypedDict, total=False):
    """Merged metadata and content structure."""

    id: str
    name: str
    source: str
    contents: list[dict[str, Any]]
    published: str
    storyline: str
    level: dict[str, int]
    group: str


# Entry Parser Types
class EntryDict(TypedDict, total=False):
    """Base structure for 5e.tools entry dictionaries."""

    type: str
    name: str
    entries: list[Any]  # Recursive structure
    id: str
    page: int


class SectionEntry(EntryDict, total=False):
    """Section entry structure."""

    # Inherits type, name, entries, id, page from EntryDict
    pass


class TableEntry(EntryDict, total=False):
    """Table entry structure."""

    caption: str
    colLabels: list[str]
    rows: list[list[str]]


class InsetEntry(EntryDict, total=False):
    """Inset/sidebar entry structure."""

    # type is typically "inset" or "insetReadaloud"
    pass


class NestedEntriesEntry(EntryDict, total=False):
    """Nested entries structure (variant rules, subsections)."""

    # type is typically "entries"
    pass


class ParsingStatistics(TypedDict):
    """Statistics for entry parsing operations."""

    entries_processed: int
    errors_encountered: int
    source: str
    parent_name: str
    registry_statistics: dict[str, int]
    unknown_types: list[str]

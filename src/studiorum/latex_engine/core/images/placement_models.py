"""Comprehensive Pydantic models for intelligent image placement system.

This module provides the foundational data structures for Phase 2 of the image
enhancement system, including context analysis, placement decisions, and
optimization configurations.
"""

from __future__ import annotations

import time
from enum import Enum
from pathlib import Path
from typing import Any, Protocol

from pydantic import BaseModel, Field

from studiorum.latex_engine.core.images.image_placer import ImagePlacement, ImageSize


class ContentType(str, Enum):
    """Types of content for context-aware placement."""

    BESTIARY = "bestiary"
    ADVENTURE = "adventure"
    ITEM_COLLECTION = "item_collection"
    SPELL_COLLECTION = "spell_collection"
    BACKGROUND = "background"
    CLASS_FEATURE = "class_feature"
    CHAPTER_INTRO = "chapter_intro"
    SIDEBAR = "sidebar"
    TABLE = "table"
    APPENDIX = "appendix"
    UNKNOWN = "unknown"


class ImageCharacteristic(str, Enum):
    """Characteristics of images for placement decisions."""

    PORTRAIT = "portrait"
    LANDSCAPE = "landscape"
    SQUARE = "square"
    ICON = "icon"
    DECORATIVE = "decorative"
    INFORMATIONAL = "informational"
    ARTISTIC = "artistic"
    TECHNICAL = "technical"


class PlacementFactor(BaseModel):
    """Individual factor contributing to placement decision."""

    name: str = Field(description="Name of the placement factor")
    weight: float = Field(
        ge=0.0, le=1.0, description="Weight of this factor (0.0 - 1.0)"
    )
    score: float = Field(
        ge=0.0, le=1.0, description="Calculated score for this factor (0.0 - 1.0)"
    )
    reasoning: str = Field(description="Explanation of how this score was calculated")


class PlacementDecision(BaseModel):
    """Complete decision result from intelligent placement analysis."""

    placement: ImagePlacement = Field(description="Recommended image placement")
    size: ImageSize = Field(description="Recommended image size")
    confidence: float = Field(
        ge=0.0, le=1.0, description="Confidence in this decision (0.0 - 1.0)"
    )
    factors: list[PlacementFactor] = Field(
        description="Individual factors that contributed to this decision"
    )
    overall_score: float = Field(
        ge=0.0, le=1.0, description="Overall weighted score for this decision"
    )
    alternative_placements: list[tuple[ImagePlacement, float]] = Field(
        default_factory=list,
        description="Alternative placements with their scores",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata about the decision process",
    )


class ImageDimensions(BaseModel):
    """Dimensions and aspect ratio information for an image."""

    width: int = Field(ge=1, description="Image width in pixels")
    height: int = Field(ge=1, description="Image height in pixels")
    aspect_ratio: float = Field(ge=0.1, le=10.0, description="Width/height ratio")
    is_portrait: bool = Field(description="True if height > width")
    is_landscape: bool = Field(description="True if width > height")
    is_square: bool = Field(description="True if width ≈ height")

    @classmethod
    def from_dimensions(cls, width: int, height: int) -> ImageDimensions:
        """Create ImageDimensions from width and height."""
        aspect_ratio = width / height
        tolerance = 0.1

        return cls(
            width=width,
            height=height,
            aspect_ratio=aspect_ratio,
            is_portrait=height > width,
            is_landscape=width > height,
            is_square=abs(aspect_ratio - 1.0) <= tolerance,
        )


class ImageMetadata(BaseModel):
    """Comprehensive metadata about an image for placement decisions."""

    path: str = Field(description="Path to the image file")
    local_path: Path | None = Field(default=None, description="Local file system path")
    dimensions: ImageDimensions | None = Field(
        default=None, description="Image dimensions and aspect ratio"
    )
    file_size_bytes: int = Field(default=0, description="File size in bytes")
    characteristics: list[ImageCharacteristic] = Field(
        default_factory=list, description="Identified image characteristics"
    )
    alt_text: str | None = Field(default=None, description="Alt text or caption")
    title: str | None = Field(default=None, description="Image title")
    content_hints: list[str] = Field(
        default_factory=list,
        description="Hints about content (creature, item, map, etc.)",
    )
    quality_score: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Estimated image quality (0.0 - 1.0)",
    )
    source_context: dict[str, Any] = Field(
        default_factory=dict, description="Context from the image source"
    )


class ContentContext(BaseModel):
    """Context about the content where an image will be placed."""

    content_type: ContentType = Field(description="Type of content")
    section_title: str | None = Field(default=None, description="Current section title")
    subsection_title: str | None = Field(
        default=None, description="Current subsection title"
    )
    surrounding_text: str = Field(
        default="", description="Text immediately surrounding the image"
    )
    word_count: int = Field(default=0, description="Approximate word count in section")
    text_density: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Text density in the surrounding area",
    )
    has_other_images: bool = Field(
        default=False, description="Whether other images are nearby"
    )
    nearby_images: list[str] = Field(
        default_factory=list, description="Paths of nearby images"
    )
    structural_elements: list[str] = Field(
        default_factory=list,
        description="Nearby structural elements (tables, lists, etc.)",
    )
    reading_flow_position: str = Field(
        default="middle",
        description="Position in reading flow (start, middle, end)",
    )


class DocumentContext(BaseModel):
    """Context about the overall document and current position."""

    total_pages: int = Field(default=1, description="Total estimated pages")
    current_page: int = Field(default=1, description="Current page estimate")
    page_position: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Position on current page (0.0 = top, 1.0 = bottom)",
    )
    chapter_number: int | None = Field(default=None, description="Current chapter")
    section_depth: int = Field(
        default=1, description="Nesting depth of current section"
    )
    document_style: str = Field(
        default="standard", description="Document style (academic, narrative, etc.)"
    )
    target_format: str = Field(
        default="pdf", description="Target output format (pdf, epub, etc.)"
    )
    column_layout: str = Field(
        default="single", description="Page layout (single, double, multi)"
    )
    margin_size: str = Field(
        default="normal", description="Margin size (narrow, normal, wide)"
    )


class PageContext(BaseModel):
    """Context about the current page layout and space."""

    available_width: float = Field(
        description="Available width for content (in points or relative units)"
    )
    available_height: float = Field(
        description="Available height for content (in points or relative units)"
    )
    column_width: float = Field(description="Width of text column")
    margin_width: float = Field(description="Width of page margins")
    current_fill: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="How full the current page is (0.0 - 1.0)",
    )
    remaining_space: float = Field(description="Estimated remaining space on page")
    has_header: bool = Field(default=True, description="Whether page has header")
    has_footer: bool = Field(default=True, description="Whether page has footer")
    is_chapter_start: bool = Field(
        default=False, description="Whether this is the first page of a chapter"
    )


class BreakPoint(BaseModel):
    """Information about a potential or actual page break."""

    position: float = Field(
        ge=0.0,
        le=1.0,
        description="Relative position in content where break occurs",
    )
    break_type: str = Field(description="Type of break (natural, forced, avoided)")
    content_before: str = Field(
        default="", description="Brief description of content before break"
    )
    content_after: str = Field(
        default="", description="Brief description of content after break"
    )
    quality_score: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Quality of this break point (higher is better)",
    )
    reasoning: str = Field(
        default="", description="Explanation of why this break point was chosen"
    )


class ContentFlow(BaseModel):
    """Information about content flow and structure."""

    total_length: int = Field(description="Total content length (characters or words)")
    sections: list[dict[str, Any]] = Field(
        default_factory=list, description="Information about content sections"
    )
    image_positions: list[int] = Field(
        default_factory=list, description="Positions where images appear"
    )
    structural_breaks: list[int] = Field(
        default_factory=list, description="Positions of structural breaks"
    )
    reading_difficulty: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Estimated reading difficulty (0.0 = easy, 1.0 = hard)",
    )


class SpaceAnalysis(BaseModel):
    """Analysis of available space on a page."""

    total_space: float = Field(description="Total available space")
    used_space: float = Field(description="Already used space")
    remaining_space: float = Field(description="Remaining available space")
    current_fill: float = Field(
        ge=0.0, le=1.0, description="Current page fill ratio (0.0 - 1.0)"
    )
    largest_contiguous_space: float = Field(
        description="Largest single block of available space"
    )
    space_fragments: list[float] = Field(
        default_factory=list,
        description="List of available space fragments",
    )
    optimal_image_sizes: list[tuple[ImageSize, float]] = Field(
        default_factory=list,
        description="Recommended image sizes with fit scores",
    )


class OptimizationTarget(str, Enum):
    """Target optimization for image output."""

    DIGITAL = "digital"
    PRINT = "print"
    HYBRID = "hybrid"
    ACCESSIBILITY = "accessibility"
    BANDWIDTH = "bandwidth"


class OptimizationConfig(BaseModel):
    """Configuration for image output optimization."""

    target: OptimizationTarget = Field(description="Primary optimization target")
    quality_priority: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Priority of quality vs file size (0.0 = size, 1.0 = quality)",
    )
    target_dpi: int = Field(
        default=150, ge=72, le=600, description="Target DPI for output"
    )
    max_file_size_mb: float = Field(
        default=5.0, ge=0.1, le=50.0, description="Maximum file size in MB"
    )
    colour_profile: str = Field(default="sRGB", description="Target colour profile")
    compression_level: float = Field(
        default=0.8,
        ge=0.1,
        le=1.0,
        description="Compression level (0.1 = high compression, 1.0 = minimal)",
    )
    preserve_transparency: bool = Field(
        default=True, description="Whether to preserve image transparency"
    )
    fallback_format: str = Field(
        default="png", description="Fallback format if original can't be used"
    )


class ProcessedImage(BaseModel):
    """Information about a processed and optimized image."""

    original_metadata: ImageMetadata = Field(description="Original image metadata")
    processed_path: Path = Field(description="Path to processed image")
    optimization_config: OptimizationConfig = Field(
        description="Configuration used for processing"
    )
    final_dimensions: ImageDimensions = Field(description="Final image dimensions")
    final_file_size_bytes: int = Field(description="Final file size")
    format: str = Field(description="Final image format")
    processing_time_seconds: float = Field(description="Time taken to process")
    quality_metrics: dict[str, float] = Field(
        default_factory=dict, description="Quality assessment metrics"
    )
    optimization_notes: list[str] = Field(
        default_factory=list, description="Notes about optimizations applied"
    )


class HybridImage(BaseModel):
    """Image optimized for both digital and print usage."""

    digital_version: ProcessedImage = Field(
        description="Version optimized for digital display"
    )
    print_version: ProcessedImage = Field(
        description="Version optimized for print output"
    )
    shared_metadata: ImageMetadata = Field(description="Shared metadata")
    usage_recommendations: dict[str, str] = Field(
        default_factory=dict,
        description="Recommendations for when to use each version",
    )


class OptimizedPlacement(BaseModel):
    """Optimized placement result with layout considerations."""

    decision: PlacementDecision = Field(description="Base placement decision")
    layout_adjustments: list[str] = Field(
        default_factory=list, description="Layout adjustments made"
    )
    sequence_position: int = Field(description="Position in optimized image sequence")
    page_impact: dict[str, float] = Field(
        default_factory=dict, description="Impact on page layout metrics"
    )
    neighbor_interactions: list[dict[str, Any]] = Field(
        default_factory=list, description="Interactions with neighboring images"
    )
    final_latex_command: str = Field(description="Final LaTeX command to use")
    required_packages: list[str] = Field(
        default_factory=list, description="LaTeX packages required"
    )


# Protocol definitions for loose coupling


class ImageAnalyzer(Protocol):
    """Protocol for analyzing image characteristics."""

    async def analyze_image(self, image_path: Path) -> ImageMetadata:
        """Analyze an image and return comprehensive metadata."""
        ...


class ContentAnalyzer(Protocol):
    """Protocol for analyzing content context."""

    def analyze_content_context(
        self, content: str, content_type: ContentType
    ) -> ContentContext:
        """Analyze content and return context information."""
        ...


class LayoutPredictor(Protocol):
    """Protocol for predicting layout impacts."""

    def predict_layout_impact(
        self, placement: PlacementDecision, context: PageContext
    ) -> dict[str, float]:
        """Predict the impact of a placement on page layout."""
        ...


# Factory functions


def create_default_optimization_config(
    target: OptimizationTarget,
) -> OptimizationConfig:
    """Create a default optimization configuration for a target.

    Args:
        target: The optimization target

    Returns:
        Optimized configuration for the target
    """
    configs = {
        OptimizationTarget.DIGITAL: OptimizationConfig(
            target=target,
            quality_priority=0.6,
            target_dpi=96,
            max_file_size_mb=2.0,
            compression_level=0.7,
        ),
        OptimizationTarget.PRINT: OptimizationConfig(
            target=target,
            quality_priority=0.9,
            target_dpi=300,
            max_file_size_mb=10.0,
            compression_level=0.9,
        ),
        OptimizationTarget.HYBRID: OptimizationConfig(
            target=target,
            quality_priority=0.8,
            target_dpi=150,
            max_file_size_mb=5.0,
            compression_level=0.8,
        ),
        OptimizationTarget.ACCESSIBILITY: OptimizationConfig(
            target=target,
            quality_priority=0.7,
            target_dpi=150,
            max_file_size_mb=3.0,
            compression_level=0.8,
            preserve_transparency=True,
        ),
        OptimizationTarget.BANDWIDTH: OptimizationConfig(
            target=target,
            quality_priority=0.4,
            target_dpi=96,
            max_file_size_mb=1.0,
            compression_level=0.5,
        ),
    }

    return configs.get(target, OptimizationConfig(target=target))


def create_placement_factor(
    name: str, weight: float, score: float, reasoning: str
) -> PlacementFactor:
    """Create a placement factor with validation.

    Args:
        name: Name of the factor
        weight: Weight of the factor (0.0-1.0)
        score: Score for the factor (0.0-1.0)
        reasoning: Explanation of the score

    Returns:
        Validated PlacementFactor instance
    """
    return PlacementFactor(
        name=name,
        weight=max(0.0, min(1.0, weight)),
        score=max(0.0, min(1.0, score)),
        reasoning=reasoning,
    )

"""Phase 2 intelligent image placement system.

This module provides a unified interface to the comprehensive image enhancement
system, including intelligent placement, layout analysis, and output optimization.

Main Components:
- ContentAwarePlacementStrategy: Multi-factor placement analysis
- Specialized strategies: Bestiary, Adventure, Item Collection optimizations
- LayoutAnalyzer: Page space analysis and break prediction
- OutputOptimizer: Digital vs print optimization
- EnhancedImagePlacer: Backward-compatible enhanced placer

Usage:
    # Basic usage with enhanced features
    from studiorum.latex_engine.core.images import create_enhanced_placer

    placer = create_enhanced_placer()
    result = await placer.place_image_enhanced(image_path, image_entry, context)

    # Specialized strategy usage
    from studiorum.latex_engine.core.images import create_specialized_strategy
    from studiorum.latex_engine.core.images.placement_models import ContentType

    strategy = create_specialized_strategy(ContentType.BESTIARY)
    decision = await strategy.determine_placement(image, content_ctx, doc_ctx)

    # Layout analysis
    from studiorum.latex_engine.core.images import LayoutAnalyzer

    analyzer = LayoutAnalyzer()
    space_analysis = analyzer.analyze_page_space(page_context)
    break_points = analyzer.predict_page_breaks(content_flow)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from studiorum.core.result import Error

# Phase 2 intelligent placement system imports
from .content_aware_strategy import (
    ContentAwarePlacementStrategy,
    PlacementWeights,
    UserPreferences,
)
from .enhanced_image_placer import (
    EnhancedImagePlacer,
    EnhancedPlacementConfig,
    EnhancedPlacementResult,
)
from .format_converter import FormatConverter

# Phase 3 content integration and registry imports
from .gallery_processor import (
    GalleryConfig,
    GalleryLayout,
    GalleryProcessor,
    ProcessedGallery,
)
from .image_optimizer import ImageOptimizer
from .image_placer import (
    ImagePlacement,
    ImagePlacer,
    ImageSize,
    PlacementConfig,
    PlacementResult,
)
from .image_processor import ImageProcessingConfig, ImageProcessor
from .layout_analyzer import (
    LayoutAnalyzer,
    LayoutConstraints,
    LayoutMetrics,
)
from .output_optimizer import (
    OptimizationProfile,
    OutputOptimizer,
)
from .placement_models import (
    ContentContext,
    ContentType,
    DocumentContext,
    ImageMetadata,
    OptimizationConfig,
    OptimizationTarget,
    PageContext,
    PlacementDecision,
)
from .specialized_strategies import (
    AdventurePlacementStrategy,
    BestiaryPlacementStrategy,
    ItemCollectionPlacementStrategy,
    SpellCollectionPlacementStrategy,
    create_specialized_strategy,
)

__all__ = [
    # Gallery processing
    "GalleryProcessor",
    "GalleryConfig",
    "GalleryLayout",
    "ProcessedGallery",
    # Legacy components (backward compatibility)
    "ImageProcessor",
    "ImageProcessingConfig",
    "FormatConverter",
    "ImageOptimizer",
    "ImagePlacer",
    # Core placement functionality
    "EnhancedImagePlacer",
    "create_enhanced_placer",
    # Placement strategies
    "ContentAwarePlacementStrategy",
    "BestiaryPlacementStrategy",
    "AdventurePlacementStrategy",
    "ItemCollectionPlacementStrategy",
    "SpellCollectionPlacementStrategy",
    "create_specialized_strategy",
    # Layout analysis
    "LayoutAnalyzer",
    "LayoutConstraints",
    "LayoutMetrics",
    # Output optimization
    "OutputOptimizer",
    "OptimizationProfile",
    # Configuration and results
    "PlacementConfig",
    "EnhancedPlacementConfig",
    "PlacementResult",
    "EnhancedPlacementResult",
    "PlacementWeights",
    "UserPreferences",
    # Data models
    "ImageMetadata",
    "ContentContext",
    "DocumentContext",
    "PageContext",
    "PlacementDecision",
    "OptimizationConfig",
    # Enums
    "ImagePlacement",
    "ImageSize",
    "ContentType",
    "OptimizationTarget",
    # Factory functions
    "create_enhanced_placer",
    "create_layout_analyzer",
    "create_output_optimizer",
    "analyze_and_place_image",
    "create_content_context_from_hint",
]


def create_enhanced_placer(
    config: EnhancedPlacementConfig | None = None,
    enable_all_features: bool = True,
) -> EnhancedImagePlacer:
    """Create an enhanced image placer with optimal default configuration.

    Args:
        config: Optional custom configuration
        enable_all_features: Whether to enable all Phase 2 features by default

    Returns:
        Configured EnhancedImagePlacer instance
    """
    if config is None:
        config = EnhancedPlacementConfig(
            enable_intelligent_placement=enable_all_features,
            enable_content_analysis=enable_all_features,
            enable_layout_optimization=enable_all_features,
            enable_output_optimization=enable_all_features,
            use_specialized_strategies=enable_all_features,
            cache_placement_decisions=True,
            optimization_target=OptimizationTarget.HYBRID,
            enable_text_wrapping=True,
            enable_margin_images=False,
        )

    return EnhancedImagePlacer(config)


def create_layout_analyzer(
    constraints: LayoutConstraints | None = None,
) -> LayoutAnalyzer:
    """Create a layout analyzer with reasonable defaults.

    Args:
        constraints: Optional custom layout constraints

    Returns:
        Configured LayoutAnalyzer instance
    """
    if constraints is None:
        constraints = LayoutConstraints(
            min_text_block_size=200,
            max_images_per_page=4,
            min_space_between_images=0.1,
            avoid_orphan_widows=True,
            prefer_section_breaks=True,
            maintain_image_groups=True,
        )

    return LayoutAnalyzer(constraints)


def create_output_optimizer(cache_dir: str | None = None) -> OutputOptimizer:
    """Create an output optimizer with default configuration.

    Args:
        cache_dir: Optional custom cache directory path

    Returns:
        Configured OutputOptimizer instance
    """
    from pathlib import Path

    cache_path = Path(cache_dir) if cache_dir else None
    return OutputOptimizer(cache_path)


# Convenience functions for common workflows


async def analyze_and_place_image(
    image_path: str | Path,
    image_entry: dict,
    content_type: ContentType,
    content_context: dict | None = None,
    document_context: dict | None = None,
    optimization_target: OptimizationTarget = OptimizationTarget.HYBRID,
) -> EnhancedPlacementResult:
    """Complete image analysis and placement workflow.

    Args:
        image_path: Path to the image file
        image_entry: Image entry data from 5etools
        content_type: Type of content for specialized strategy
        content_context: Optional content context information
        document_context: Optional document context information
        optimization_target: Target optimization for output

    Returns:
        Complete placement result with analysis

    Raises:
        ValueError: If placement analysis fails
    """
    from pathlib import Path

    # Create enhanced placer
    config = EnhancedPlacementConfig(
        optimization_target=optimization_target,
        use_specialized_strategies=True,
    )
    placer = EnhancedImagePlacer(config)

    # Add content type to context
    if content_context is None:
        content_context = {}
    content_context["type"] = content_type.value

    # Perform enhanced placement
    result = await placer.place_image_enhanced(
        Path(image_path), image_entry, content_context, document_context
    )

    if isinstance(result, Error):
        raise ValueError(f"Placement analysis failed: {result.error}")

    return result.unwrap()


def create_content_context_from_hint(
    context_hint: str,
    additional_context: dict | None = None,
) -> dict[str, Any]:
    """Create content context dictionary from simple hint string.

    This provides backward compatibility with the original context_hint
    parameter while enabling Phase 2 features.

    Args:
        context_hint: Simple context hint (creature, item, chapter-art, etc.)
        additional_context: Optional additional context information

    Returns:
        Content context dictionary suitable for enhanced placement
    """
    context: dict[str, Any] = {
        "type": context_hint,
        "word_count": 500,  # Default estimate
        "text_density": 0.6,
        "reading_flow_position": "middle",
    }

    # Add context-specific defaults
    if context_hint == "creature":
        context["word_count"] = 300  # Creature statblocks are usually shorter
        context["structural_elements"] = ["statblock", "table"]
    elif context_hint == "chapter-art":
        context["reading_flow_position"] = "start"
        context["text_density"] = 0.3  # Chapter starts often have more whitespace
    elif context_hint == "item":
        context["word_count"] = 150  # Item descriptions are brief
        context["has_other_images"] = True  # Items often appear in collections

    # Merge additional context
    if additional_context:
        context.update(additional_context)

    return context

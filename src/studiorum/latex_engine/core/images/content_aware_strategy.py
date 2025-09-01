"""Content-aware placement strategy with multi-factor weighted decision making.

This module implements the core intelligent placement strategy that analyzes
multiple factors to determine optimal image placement, including image
characteristics, content flow, document context, and user preferences.
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field

from studiorum.core.logging import get_logger
from studiorum.core.result import Error, Result, Success
from studiorum.latex_engine.core.images.image_placer import ImagePlacement, ImageSize
from studiorum.latex_engine.core.images.placement_models import (
    ContentContext,
    ContentType,
    DocumentContext,
    ImageCharacteristic,
    ImageDimensions,
    ImageMetadata,
    OptimizationTarget,
    PageContext,
    PlacementDecision,
    PlacementFactor,
    create_placement_factor,
)

logger = get_logger(__name__)


class PlacementWeights(BaseModel):
    """Configurable weights for different placement factors."""

    image_characteristics: float = Field(
        default=0.25,
        ge=0.0,
        le=1.0,
        description="Weight for image characteristics analysis",
    )
    content_flow: float = Field(
        default=0.20,
        ge=0.0,
        le=1.0,
        description="Weight for content flow analysis",
    )
    page_position: float = Field(
        default=0.15,
        ge=0.0,
        le=1.0,
        description="Weight for page position analysis",
    )
    surrounding_context: float = Field(
        default=0.20,
        ge=0.0,
        le=1.0,
        description="Weight for surrounding content analysis",
    )
    user_preferences: float = Field(
        default=0.10,
        ge=0.0,
        le=1.0,
        description="Weight for user preferences",
    )
    technical_constraints: float = Field(
        default=0.10,
        ge=0.0,
        le=1.0,
        description="Weight for technical constraints",
    )

    def normalize(self) -> PlacementWeights:
        """Normalize weights to sum to 1.0."""
        total = (
            self.image_characteristics
            + self.content_flow
            + self.page_position
            + self.surrounding_context
            + self.user_preferences
            + self.technical_constraints
        )

        if total == 0:
            # If all weights are 0, set equal weights
            return PlacementWeights(
                image_characteristics=1 / 6,
                content_flow=1 / 6,
                page_position=1 / 6,
                surrounding_context=1 / 6,
                user_preferences=1 / 6,
                technical_constraints=1 / 6,
            )

        return PlacementWeights(
            image_characteristics=self.image_characteristics / total,
            content_flow=self.content_flow / total,
            page_position=self.page_position / total,
            surrounding_context=self.surrounding_context / total,
            user_preferences=self.user_preferences / total,
            technical_constraints=self.technical_constraints / total,
        )


class UserPreferences(BaseModel):
    """User preferences for image placement."""

    prefer_inline: bool = Field(default=False, description="Prefer inline placement")
    prefer_wrapped: bool = Field(default=True, description="Allow text wrapping")
    prefer_margins: bool = Field(default=False, description="Allow margin placement")
    max_image_width: float = Field(
        default=0.8, ge=0.1, le=1.0, description="Maximum image width as fraction"
    )
    min_image_width: float = Field(
        default=0.2, ge=0.1, le=1.0, description="Minimum image width as fraction"
    )
    optimization_target: OptimizationTarget = Field(
        default=OptimizationTarget.HYBRID, description="Optimization target"
    )
    accessibility_mode: bool = Field(
        default=False, description="Enable accessibility optimizations"
    )
    preserve_aspect_ratio: bool = Field(
        default=True, description="Always preserve image aspect ratio"
    )


class PlacementStrategy(ABC):
    """Abstract base class for placement strategies."""

    @abstractmethod
    async def determine_placement(
        self,
        image: ImageMetadata,
        content_context: ContentContext,
        document_context: DocumentContext,
        page_context: PageContext | None = None,
        user_prefs: UserPreferences | None = None,
    ) -> Result[PlacementDecision, str]:
        """Determine optimal placement for an image."""
        ...


class ContentAwarePlacementStrategy(PlacementStrategy):
    """Advanced content-aware placement strategy with multi-factor analysis.

    This strategy analyzes multiple factors to make intelligent placement decisions:
    - Image characteristics (dimensions, type, quality)
    - Content flow and structure
    - Page position and layout constraints
    - Surrounding content context
    - User preferences
    - Technical constraints
    """

    def __init__(
        self,
        weights: PlacementWeights | None = None,
        enable_caching: bool = True,
    ) -> None:
        """Initialize the content-aware placement strategy.

        Args:
            weights: Custom weights for placement factors
            enable_caching: Whether to cache analysis results
        """
        self.weights = (weights or PlacementWeights()).normalize()
        self.enable_caching = enable_caching
        self._analysis_cache: dict[str, Any] = {}

        logger.debug(
            f"Initialized ContentAwarePlacementStrategy with weights: "
            f"image_characteristics={self.weights.image_characteristics:.3f}, "
            f"content_flow={self.weights.content_flow:.3f}, "
            f"page_position={self.weights.page_position:.3f}, "
            f"surrounding_context={self.weights.surrounding_context:.3f}, "
            f"user_preferences={self.weights.user_preferences:.3f}, "
            f"technical_constraints={self.weights.technical_constraints:.3f}"
        )

    async def determine_placement(
        self,
        image: ImageMetadata,
        content_context: ContentContext,
        document_context: DocumentContext,
        page_context: PageContext | None = None,
        user_prefs: UserPreferences | None = None,
    ) -> Result[PlacementDecision, str]:
        """Determine optimal placement using multi-factor analysis.

        Args:
            image: Metadata about the image to place
            content_context: Context about surrounding content
            document_context: Context about the overall document
            page_context: Optional context about current page layout
            user_prefs: Optional user preferences

        Returns:
            Placement decision with detailed reasoning or error message
        """
        try:
            user_prefs = user_prefs or UserPreferences()

            logger.debug(
                f"Analyzing placement for image: {image.path} "
                f"(content_type: {content_context.content_type}, "
                f"dimensions: {image.dimensions})"
            )

            # Analyze each factor concurrently for better performance
            analysis_tasks = [
                self._analyze_image_characteristics(image, user_prefs),
                self._analyze_content_flow(content_context, document_context),
                self._analyze_page_position(document_context, page_context),
                self._analyze_surrounding_context(content_context, image),
                self._analyze_user_preferences(user_prefs, image),
                self._analyze_technical_constraints(image, document_context),
            ]

            factors = await asyncio.gather(*analysis_tasks, return_exceptions=True)

            # Check for any exceptions in the analysis and filter valid factors
            valid_factors: list[PlacementFactor] = []
            for i, factor in enumerate(factors):
                if isinstance(factor, Exception):
                    logger.error(f"Factor analysis {i} failed: {str(factor)}")
                    return Error(f"Factor analysis failed: {str(factor)}")
                elif isinstance(factor, PlacementFactor):
                    valid_factors.append(factor)

            # Calculate overall scores for each placement option
            placement_scores = self._calculate_placement_scores(
                valid_factors, user_prefs
            )

            # Select best placement
            best_placement, best_score = max(
                placement_scores.items(), key=lambda x: x[1]
            )

            # Determine optimal size
            optimal_size = self._determine_optimal_size(
                image, best_placement, content_context, user_prefs
            )

            # Calculate confidence based on score distribution
            confidence = self._calculate_confidence(placement_scores, best_score)

            # Generate alternative placements
            alternatives = sorted(
                [(p, s) for p, s in placement_scores.items() if p != best_placement],
                key=lambda x: x[1],
                reverse=True,
            )[:3]  # Top 3 alternatives

            decision = PlacementDecision(
                placement=best_placement,
                size=optimal_size,
                confidence=confidence,
                factors=valid_factors,
                overall_score=best_score,
                alternative_placements=alternatives,
                metadata={
                    "strategy": "ContentAwarePlacementStrategy",
                    "analysis_method": "multi_factor_weighted",
                    "weights_used": self.weights.model_dump(),
                    "content_type": content_context.content_type.value,
                    "image_characteristics": [c.value for c in image.characteristics],
                },
            )

            logger.info(
                f"Placement decision for {image.path}: {best_placement.value} "
                f"(size: {optimal_size.value}, confidence: {confidence:.3f})"
            )

            return Success(decision)

        except Exception as e:
            logger.error(f"Placement analysis failed for {image.path}: {str(e)}")
            return Error(f"Placement analysis failed: {str(e)}")

    async def _analyze_image_characteristics(
        self, image: ImageMetadata, user_prefs: UserPreferences
    ) -> PlacementFactor:
        """Analyze image characteristics to determine placement preferences."""
        score = 0.5  # Base score
        reasoning_parts = []

        # Analyze dimensions if available
        if image.dimensions:
            if image.dimensions.is_portrait:
                # Portrait images work well wrapped or as floats
                score += 0.2
                reasoning_parts.append(
                    "portrait orientation favours wrapped/float placement"
                )
            elif image.dimensions.is_landscape:
                # Landscape images work well as full-width or floats
                score += 0.1
                reasoning_parts.append(
                    "landscape orientation is versatile for placement"
                )

            # Very wide images prefer full-width
            if image.dimensions.aspect_ratio > 2.0:
                score += 0.2
                reasoning_parts.append("wide aspect ratio favours full-width placement")

        # Analyze characteristics
        if ImageCharacteristic.ARTISTIC in image.characteristics:
            score += 0.15
            reasoning_parts.append("artistic images benefit from prominent placement")

        if ImageCharacteristic.DECORATIVE in image.characteristics:
            score += 0.1
            reasoning_parts.append("decorative images are flexible in placement")

        if ImageCharacteristic.ICON in image.characteristics:
            score -= 0.1  # Icons often work better inline
            reasoning_parts.append("icons typically work better inline")

        # Consider quality
        if image.quality_score > 0.8:
            score += 0.1
            reasoning_parts.append("high quality image deserves prominent placement")
        elif image.quality_score < 0.4:
            score -= 0.1
            reasoning_parts.append("lower quality suggests less prominent placement")

        # Normalize score
        score = max(0.0, min(1.0, score))

        reasoning = (
            "; ".join(reasoning_parts) if reasoning_parts else "standard image analysis"
        )

        return create_placement_factor(
            name="Image Characteristics",
            weight=self.weights.image_characteristics,
            score=score,
            reasoning=reasoning,
        )

    async def _analyze_content_flow(
        self, content_context: ContentContext, document_context: DocumentContext
    ) -> PlacementFactor:
        """Analyze content flow to determine placement impact."""
        score = 0.5
        reasoning_parts = []

        # Analyze content type
        if content_context.content_type == ContentType.BESTIARY:
            score += 0.2
            reasoning_parts.append(
                "bestiary content benefits from wrapped creature images"
            )
        elif content_context.content_type == ContentType.ADVENTURE:
            score += 0.1
            reasoning_parts.append("adventure content allows flexible image placement")
        elif content_context.content_type == ContentType.CHAPTER_INTRO:
            score += 0.3
            reasoning_parts.append(
                "chapter introductions benefit from prominent imagery"
            )

        # Consider text density
        if content_context.text_density > 0.8:
            score -= 0.1
            reasoning_parts.append("high text density suggests careful image placement")
        elif content_context.text_density < 0.3:
            score += 0.1
            reasoning_parts.append("low text density allows more flexible placement")

        # Consider other images nearby
        if content_context.has_other_images:
            score -= 0.15
            reasoning_parts.append("nearby images require coordinated placement")

        # Consider reading flow position
        if content_context.reading_flow_position == "start":
            score += 0.1
            reasoning_parts.append("start position allows attention-grabbing placement")
        elif content_context.reading_flow_position == "end":
            score += 0.05
            reasoning_parts.append("end position allows summary/conclusion imagery")

        score = max(0.0, min(1.0, score))
        reasoning = (
            "; ".join(reasoning_parts) if reasoning_parts else "standard flow analysis"
        )

        return create_placement_factor(
            name="Content Flow",
            weight=self.weights.content_flow,
            score=score,
            reasoning=reasoning,
        )

    async def _analyze_page_position(
        self, document_context: DocumentContext, page_context: PageContext | None
    ) -> PlacementFactor:
        """Analyze page position and layout constraints."""
        score = 0.5
        reasoning_parts = []

        if page_context:
            # Analyze page fullness
            if page_context.current_fill > 0.8:
                score -= 0.2
                reasoning_parts.append(
                    "page is nearly full, limiting placement options"
                )
            elif page_context.current_fill < 0.3:
                score += 0.1
                reasoning_parts.append(
                    "page has plenty of space for flexible placement"
                )

            # Consider chapter start
            if page_context.is_chapter_start:
                score += 0.2
                reasoning_parts.append("chapter start allows prominent image placement")

        # Consider document position
        if document_context.current_page == 1:
            score += 0.15
            reasoning_parts.append("first page allows attention-grabbing placement")

        # Consider section depth
        if document_context.section_depth > 3:
            score -= 0.1
            reasoning_parts.append("deep section nesting suggests simpler placement")

        score = max(0.0, min(1.0, score))
        reasoning = (
            "; ".join(reasoning_parts)
            if reasoning_parts
            else "standard position analysis"
        )

        return create_placement_factor(
            name="Page Position",
            weight=self.weights.page_position,
            score=score,
            reasoning=reasoning,
        )

    async def _analyze_surrounding_context(
        self, content_context: ContentContext, image: ImageMetadata
    ) -> PlacementFactor:
        """Analyze surrounding content context."""
        score = 0.5
        reasoning_parts = []

        # Analyze structural elements
        if "table" in content_context.structural_elements:
            score -= 0.15
            reasoning_parts.append("nearby tables require careful image positioning")

        if "list" in content_context.structural_elements:
            score -= 0.1
            reasoning_parts.append("nearby lists may conflict with wrapped images")

        # Analyze word count
        if content_context.word_count < 100:
            score -= 0.1
            reasoning_parts.append("short content section limits placement options")
        elif content_context.word_count > 500:
            score += 0.15
            reasoning_parts.append("long content section allows flexible placement")

        # Consider content hints from image
        if "creature" in image.content_hints:
            if content_context.content_type == ContentType.BESTIARY:
                score += 0.2
                reasoning_parts.append("creature image matches bestiary content")

        if "map" in image.content_hints:
            if content_context.content_type == ContentType.ADVENTURE:
                score += 0.2
                reasoning_parts.append("map image enhances adventure content")

        score = max(0.0, min(1.0, score))
        reasoning = (
            "; ".join(reasoning_parts)
            if reasoning_parts
            else "standard context analysis"
        )

        return create_placement_factor(
            name="Surrounding Context",
            weight=self.weights.surrounding_context,
            score=score,
            reasoning=reasoning,
        )

    async def _analyze_user_preferences(
        self, user_prefs: UserPreferences, image: ImageMetadata
    ) -> PlacementFactor:
        """Analyze user preferences for placement."""
        score = 0.5
        reasoning_parts = []

        # Apply user preferences
        if user_prefs.prefer_inline:
            score += 0.2
            reasoning_parts.append("user prefers inline placement")

        if not user_prefs.prefer_wrapped:
            score -= 0.1
            reasoning_parts.append("user avoids text wrapping")

        if user_prefs.prefer_margins and image.dimensions:
            if image.dimensions.width < 200:  # Small images work in margins
                score += 0.15
                reasoning_parts.append(
                    "small image suitable for margin placement preference"
                )

        # Consider optimization target
        if user_prefs.optimization_target == OptimizationTarget.PRINT:
            score += 0.1
            reasoning_parts.append(
                "print optimization allows more placement flexibility"
            )
        elif user_prefs.optimization_target == OptimizationTarget.DIGITAL:
            score += 0.05
            reasoning_parts.append("digital optimization considered")

        if user_prefs.accessibility_mode:
            score -= 0.05
            reasoning_parts.append("accessibility mode favours simpler placement")

        score = max(0.0, min(1.0, score))
        reasoning = (
            "; ".join(reasoning_parts)
            if reasoning_parts
            else "standard preference analysis"
        )

        return create_placement_factor(
            name="User Preferences",
            weight=self.weights.user_preferences,
            score=score,
            reasoning=reasoning,
        )

    async def _analyze_technical_constraints(
        self, image: ImageMetadata, document_context: DocumentContext
    ) -> PlacementFactor:
        """Analyze technical constraints that might affect placement."""
        score = 0.5
        reasoning_parts = []

        # File size constraints
        if image.file_size_bytes > 5 * 1024 * 1024:  # > 5MB
            score -= 0.2
            reasoning_parts.append("large file size may require size optimization")
        elif image.file_size_bytes < 100 * 1024:  # < 100KB
            score += 0.1
            reasoning_parts.append("small file size allows flexible placement")

        # Format constraints
        if image.path.lower().endswith(".svg"):
            score += 0.1
            reasoning_parts.append("SVG format scales well at any size")
        elif image.path.lower().endswith(".gif"):
            score -= 0.1
            reasoning_parts.append("GIF format has limited placement options")

        # Column layout constraints
        if document_context.column_layout == "double":
            score -= 0.1
            reasoning_parts.append("double-column layout limits placement options")
        elif document_context.column_layout == "single":
            score += 0.1
            reasoning_parts.append("single-column layout allows flexible placement")

        score = max(0.0, min(1.0, score))
        reasoning = (
            "; ".join(reasoning_parts)
            if reasoning_parts
            else "no technical constraints"
        )

        return create_placement_factor(
            name="Technical Constraints",
            weight=self.weights.technical_constraints,
            score=score,
            reasoning=reasoning,
        )

    def _calculate_placement_scores(
        self, factors: list[PlacementFactor], user_prefs: UserPreferences
    ) -> dict[ImagePlacement, float]:
        """Calculate weighted scores for each placement option."""
        # Base scores for each placement type
        base_scores = {
            ImagePlacement.INLINE: 0.3,
            ImagePlacement.FLOAT_HERE: 0.7,
            ImagePlacement.FLOAT_TOP: 0.6,
            ImagePlacement.FLOAT_BOTTOM: 0.6,
            ImagePlacement.FLOAT_PAGE: 0.4,
            ImagePlacement.WRAP_LEFT: 0.8,
            ImagePlacement.WRAP_RIGHT: 0.8,
            ImagePlacement.MARGIN: 0.3,
            ImagePlacement.FULL_WIDTH: 0.5,
        }

        # Apply user preference modifiers
        if user_prefs.prefer_inline:
            base_scores[ImagePlacement.INLINE] += 0.3

        if not user_prefs.prefer_wrapped:
            base_scores[ImagePlacement.WRAP_LEFT] -= 0.3
            base_scores[ImagePlacement.WRAP_RIGHT] -= 0.3

        if not user_prefs.prefer_margins:
            base_scores[ImagePlacement.MARGIN] -= 0.5

        # Calculate weighted scores
        final_scores = {}
        total_factor_score = sum(f.weight * f.score for f in factors)

        for placement, base_score in base_scores.items():
            # Combine base score with factor analysis
            combined_score = (base_score * 0.4) + (total_factor_score * 0.6)
            final_scores[placement] = max(0.0, min(1.0, combined_score))

        return final_scores

    def _determine_optimal_size(
        self,
        image: ImageMetadata,
        placement: ImagePlacement,
        content_context: ContentContext,
        user_prefs: UserPreferences,
    ) -> ImageSize:
        """Determine optimal size based on placement and context."""
        # Size preferences by placement type
        placement_size_map = {
            ImagePlacement.INLINE: ImageSize.SMALL,
            ImagePlacement.FLOAT_HERE: ImageSize.MEDIUM,
            ImagePlacement.FLOAT_TOP: ImageSize.LARGE,
            ImagePlacement.FLOAT_BOTTOM: ImageSize.LARGE,
            ImagePlacement.FLOAT_PAGE: ImageSize.FULL_COLUMN,
            ImagePlacement.WRAP_LEFT: ImageSize.MEDIUM,
            ImagePlacement.WRAP_RIGHT: ImageSize.MEDIUM,
            ImagePlacement.MARGIN: ImageSize.SMALL,
            ImagePlacement.FULL_WIDTH: ImageSize.FULL_WIDTH,
        }

        base_size = placement_size_map.get(placement, ImageSize.MEDIUM)

        # Adjust based on image characteristics
        if image.dimensions:
            if image.dimensions.is_portrait and base_size == ImageSize.MEDIUM:
                base_size = ImageSize.PORTRAIT
            elif image.dimensions.aspect_ratio > 2.0:
                base_size = ImageSize.FULL_WIDTH

        # Adjust based on content type
        if content_context.content_type == ContentType.BESTIARY:
            if placement in {ImagePlacement.WRAP_LEFT, ImagePlacement.WRAP_RIGHT}:
                base_size = ImageSize.PORTRAIT
        elif content_context.content_type == ContentType.CHAPTER_INTRO:
            if base_size == ImageSize.MEDIUM:
                base_size = ImageSize.LARGE

        return base_size

    def _calculate_confidence(
        self, placement_scores: dict[ImagePlacement, float], best_score: float
    ) -> float:
        """Calculate confidence based on score distribution."""
        scores = list(placement_scores.values())
        scores.sort(reverse=True)

        if len(scores) < 2:
            return 0.5

        # Confidence is higher when best score is significantly better than others
        best_score = scores[0]
        second_best = scores[1]

        # Large gap = high confidence, small gap = low confidence
        gap = best_score - second_best
        confidence = 0.5 + (gap * 0.5)  # Scale gap to 0.0-0.5 range

        return max(0.1, min(0.95, confidence))

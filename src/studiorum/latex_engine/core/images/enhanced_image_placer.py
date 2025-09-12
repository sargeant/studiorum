"""Enhanced ImagePlacer with Phase 2 intelligent placement integration.

This module upgrades the existing ImagePlacer with the new intelligent placement
systems while maintaining backward compatibility with the existing API.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from studiorum.core.logging import get_logger
from studiorum.core.result import Error, Result, Success
from studiorum.latex_engine.core.images.content_aware_strategy import (
    ContentAwarePlacementStrategy,
    UserPreferences,
)
from studiorum.latex_engine.core.images.image_placer import (
    ImagePlacer,
    PlacementConfig,
    PlacementResult,
)
from studiorum.latex_engine.core.images.layout_analyzer import (
    LayoutAnalyzer,
    LayoutConstraints,
)
from studiorum.latex_engine.core.images.output_optimizer import OutputOptimizer
from studiorum.latex_engine.core.images.placement_models import (
    ContentContext,
    ContentType,
    DocumentContext,
    ImageCharacteristic,
    ImageDimensions,
    ImageMetadata,
    OptimizationTarget,
    PageContext,
)
from studiorum.latex_engine.core.images.specialized_strategies import (
    create_specialized_strategy,
)

logger = get_logger(__name__)


class EnhancedPlacementConfig(PlacementConfig):
    """Enhanced configuration extending the original PlacementConfig."""

    enable_intelligent_placement: bool = Field(
        default=True, description="Enable Phase 2 intelligent placement"
    )
    enable_content_analysis: bool = Field(
        default=True, description="Enable content-aware analysis"
    )
    enable_layout_optimization: bool = Field(
        default=True, description="Enable layout optimization"
    )
    enable_output_optimization: bool = Field(
        default=False, description="Enable output format optimization"
    )
    optimization_target: OptimizationTarget = Field(
        default=OptimizationTarget.HYBRID,
        description="Target optimization for output",
    )
    use_specialized_strategies: bool = Field(
        default=True, description="Use content-type-specific strategies"
    )
    cache_placement_decisions: bool = Field(
        default=True, description="Cache placement analysis for performance"
    )


class EnhancedPlacementResult(PlacementResult):
    """Enhanced placement result with additional Phase 2 information."""

    confidence: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Confidence in placement decision",
    )
    reasoning: list[str] = Field(
        default_factory=list, description="Human-readable reasoning for placement"
    )
    alternative_placements: list[str] = Field(
        default_factory=list, description="Alternative placement options considered"
    )
    optimization_applied: bool = Field(
        default=False, description="Whether output optimization was applied"
    )
    layout_impact: dict[str, float] = Field(
        default_factory=dict, description="Impact on page layout metrics"
    )
    processing_metadata: dict[str, Any] = Field(
        default_factory=dict, description="Metadata about the placement process"
    )


class EnhancedImagePlacer(ImagePlacer):
    """Enhanced ImagePlacer with Phase 2 intelligent placement capabilities.

    Maintains backward compatibility with the original ImagePlacer API while
    adding sophisticated intelligent placement, layout analysis, and output
    optimization capabilities.
    """

    def __init__(self, config: EnhancedPlacementConfig | None = None) -> None:
        """Initialize the enhanced image placer.

        Args:
            config: Enhanced placement configuration
        """
        logger.warning(
            "EnhancedImagePlacer is deprecated; use --placement-mode=manual to emit macros instead."
        )
        # Initialize base class with compatible config
        base_config = PlacementConfig()
        if config:
            # Copy compatible fields from enhanced config
            for field_name in PlacementConfig.model_fields:
                if hasattr(config, field_name):
                    setattr(base_config, field_name, getattr(config, field_name))

        super().__init__(base_config)

        self.enhanced_config = config or EnhancedPlacementConfig()

        # Initialize Phase 2 components if enabled
        self.content_aware_strategy: ContentAwarePlacementStrategy | None = None
        self.layout_analyzer: LayoutAnalyzer | None = None
        self.output_optimizer: OutputOptimizer | None = None
        self._placement_cache: dict[str, Any] = {}

        if self.enhanced_config.enable_intelligent_placement:
            self._initialize_intelligent_components()

        logger.info(
            f"Initialized EnhancedImagePlacer "
            f"(intelligent_placement={self.enhanced_config.enable_intelligent_placement}, "
            f"content_analysis={self.enhanced_config.enable_content_analysis}, "
            f"layout_optimization={self.enhanced_config.enable_layout_optimization})"
        )

    def _initialize_intelligent_components(self) -> None:
        """Initialize Phase 2 intelligent placement components."""
        try:
            # Initialize content-aware strategy
            if self.enhanced_config.enable_content_analysis:
                self.content_aware_strategy = ContentAwarePlacementStrategy(
                    enable_caching=self.enhanced_config.cache_placement_decisions
                )
                logger.debug("Initialized ContentAwarePlacementStrategy")

            # Initialize layout analyzer
            if self.enhanced_config.enable_layout_optimization:
                layout_constraints = LayoutConstraints()
                self.layout_analyzer = LayoutAnalyzer(constraints=layout_constraints)
                logger.debug("Initialized LayoutAnalyzer")

            # Initialize output optimizer
            if self.enhanced_config.enable_output_optimization:
                self.output_optimizer = OutputOptimizer()
                logger.debug("Initialized OutputOptimizer")

        except Exception as e:
            logger.error(f"Failed to initialize intelligent components: {str(e)}")
            # Fallback to base functionality by creating a disabled config
            self.enhanced_config = self.enhanced_config.model_copy(
                update={"enable_intelligent_placement": False}
            )
            logger.warning(
                "Disabled intelligent placement due to initialization failure"
            )

    async def place_image_enhanced(
        self,
        image_path: Path,
        image_entry: dict[str, Any],
        content_context: dict[str, Any] | None = None,
        document_context: dict[str, Any] | None = None,
        page_context: dict[str, Any] | None = None,
    ) -> Result[EnhancedPlacementResult, str]:
        """Place image using enhanced intelligent placement system.

        This method provides the full Phase 2 intelligent placement capabilities
        with detailed analysis and optimization.

        Args:
            image_path: Path to processed image file
            image_entry: Original image entry data
            content_context: Context about surrounding content
            document_context: Context about the overall document
            page_context: Context about current page layout

        Returns:
            Enhanced placement result with detailed information
        """
        logger.warning(
            "place_image_enhanced is deprecated; prefer manual placement macros."
        )
        try:
            # Create image metadata
            image_metadata = await self._create_image_metadata(image_path, image_entry)

            # If intelligent placement is disabled, fall back to base method
            if not self.enhanced_config.enable_intelligent_placement:
                return await self._fallback_to_base_placement(
                    image_path, image_entry, image_metadata
                )

            # Create context objects
            content_ctx = self._create_content_context(content_context, image_entry)
            document_ctx = self._create_document_context(document_context)
            page_ctx = self._create_page_context(page_context) if page_context else None

            # Select appropriate placement strategy
            strategy = self._select_placement_strategy(content_ctx)
            strategy_name = strategy.__class__.__name__

            # Get placement decision
            user_prefs = self._create_user_preferences()
            try:
                decision_result = await strategy.determine_placement(
                    image_metadata, content_ctx, document_ctx, page_ctx, user_prefs
                )
            except Exception as strategy_error:
                logger.warning(
                    f"Strategy execution failed for {image_path}: {str(strategy_error)}, "
                    "falling back to base placement"
                )
                return await self._fallback_to_base_placement(
                    image_path, image_entry, image_metadata
                )

            if isinstance(decision_result, Error):
                logger.warning(
                    f"Intelligent placement failed for {image_path}: {decision_result.error}, "
                    "falling back to base placement"
                )
                return await self._fallback_to_base_placement(
                    image_path, image_entry, image_metadata
                )

            decision = decision_result.unwrap()

            # Apply layout optimization if enabled
            layout_impact = {}
            if self.layout_analyzer and page_ctx:
                layout_impact = await self._analyze_layout_impact(decision, page_ctx)

            # Generate LaTeX command using enhanced methods
            size_spec = self._size_to_spec(decision.size, content_ctx)

            # Use our enhanced wrap command for wrap placements
            if (
                hasattr(decision.placement, "value")
                and "wrap" in decision.placement.value
            ):
                latex_command = self._generate_wrap_command(
                    image_path,
                    image_entry.get("title", ""),
                    decision.placement,
                    size_spec,
                    self._generate_label(image_entry),
                    content_ctx,
                )
            else:
                # Use base class method for other placements
                latex_command = self._generate_placement_command(
                    image_path,
                    image_entry,
                    decision.placement,
                    size_spec,
                )

            # Apply output optimization if enabled
            optimization_applied = False
            if (
                self.output_optimizer
                and self.enhanced_config.enable_output_optimization
            ):
                optimization_applied = await self._apply_output_optimization(
                    image_metadata, decision
                )

            # Create enhanced result
            result = EnhancedPlacementResult(
                latex_command=latex_command,
                placement=decision.placement,
                size_spec=self._size_to_spec(decision.size, content_ctx),
                requires_packages=self._get_required_packages(decision.placement),
                caption=image_entry.get("title"),
                confidence=decision.confidence,
                reasoning=[f.reasoning for f in decision.factors],
                alternative_placements=[
                    f"{alt[0].value} (score: {alt[1]:.2f})"
                    for alt in decision.alternative_placements
                ],
                optimization_applied=optimization_applied,
                layout_impact=layout_impact,
                processing_metadata={
                    "strategy_used": decision.metadata.get("strategy", "unknown"),
                    "specialized_strategy": strategy_name,
                    "content_type": content_ctx.content_type.value,
                    "analysis_factors": len(decision.factors),
                    "overall_score": decision.overall_score,
                },
            )

            logger.info(
                f"Enhanced placement for {image_path}: {decision.placement.value} "
                f"(confidence: {decision.confidence:.2f})"
            )

            return Success(result)

        except Exception as e:
            logger.error(f"Enhanced placement failed for {image_path}: {str(e)}")
            return Error(f"Enhanced placement failed: {str(e)}")

    def place_image(
        self,
        image_path: Path,
        image_entry: dict[str, Any],
        context_hint: str | None = None,
    ) -> PlacementResult:
        """Maintain backward compatibility with original API.

        This method provides the same API as the base ImagePlacer while
        optionally using enhanced features when available.
        """
        logger.warning(
            "place_image (smart) is deprecated; prefer --placement-mode=manual."
        )
        # If intelligent placement is disabled, use base implementation
        if not self.enhanced_config.enable_intelligent_placement:
            return super().place_image(image_path, image_entry, context_hint)

        # Use enhanced placement asynchronously
        try:
            # Create basic context from hint
            content_context = {"type": context_hint} if context_hint else None

            # Run enhanced placement in event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                enhanced_result = loop.run_until_complete(
                    self.place_image_enhanced(image_path, image_entry, content_context)
                )

                if isinstance(enhanced_result, Error):
                    logger.warning(
                        f"Enhanced placement failed: {enhanced_result.error}, "
                        "falling back to base placement"
                    )
                    return super().place_image(image_path, image_entry, context_hint)
                else:
                    # Convert enhanced result to base result
                    enhanced = enhanced_result.unwrap()
                    return PlacementResult(
                        latex_command=enhanced.latex_command,
                        placement=enhanced.placement,
                        size_spec=enhanced.size_spec,
                        requires_packages=enhanced.requires_packages,
                        caption=enhanced.caption,
                    )
            finally:
                loop.close()

        except Exception as e:
            logger.error(f"Error in enhanced placement: {str(e)}, falling back to base")
            return super().place_image(image_path, image_entry, context_hint)

    async def _create_image_metadata(
        self, image_path: Path, image_entry: dict[str, Any]
    ) -> ImageMetadata:
        """Create comprehensive image metadata from available information."""
        # Check if image file exists - this is critical for proper error handling
        if not image_path.exists():
            raise ValueError(f"Image file not found: {image_path}")

        # Extract dimensions if available
        dimensions = None
        # In a real implementation, this would analyze the actual image file
        # For now, create placeholder dimensions
        dimensions = ImageDimensions.from_dimensions(800, 600)

        # Determine characteristics from entry data
        characteristics = []
        if "creature" in str(image_entry).lower():
            characteristics.append(ImageCharacteristic.PORTRAIT)
        if "map" in str(image_entry).lower():
            characteristics.append(ImageCharacteristic.TECHNICAL)
        if "art" in str(image_entry).lower():
            characteristics.append(ImageCharacteristic.ARTISTIC)

        # Extract content hints
        content_hints = []
        entry_str = str(image_entry).lower()
        hint_keywords = {
            "creature": "creature",
            "monster": "creature",
            "dragon": "creature",
            "beast": "creature",
            "goblin": "creature",
            "orc": "creature",
            "character": "npc",
            "map": "map",
            "item": "item",
            "weapon": "item",
            "armor": "item",
            "spell": "spell",
            "location": "location",
            "environment": "environment",
        }

        for keyword, hint in hint_keywords.items():
            if keyword in entry_str:
                content_hints.append(hint)

        file_size = image_path.stat().st_size

        return ImageMetadata(
            path=str(image_path),
            local_path=image_path,
            dimensions=dimensions,
            file_size_bytes=file_size,
            characteristics=characteristics,
            alt_text=image_entry.get("alt"),
            title=image_entry.get("title"),
            content_hints=content_hints,
            quality_score=0.7,  # Default assumption
            source_context=image_entry,
        )

    def _create_content_context(
        self, context_data: dict[str, Any] | None, image_entry: dict[str, Any]
    ) -> ContentContext:
        """Create content context from available data."""
        if not context_data:
            context_data = {}

        # Determine content type
        content_type = ContentType.UNKNOWN
        type_hint = context_data.get("type", "").lower()

        type_mapping = {
            "creature": ContentType.BESTIARY,
            "monster": ContentType.BESTIARY,
            "bestiary": ContentType.BESTIARY,
            "adventure": ContentType.ADVENTURE,
            "item": ContentType.ITEM_COLLECTION,
            "item_collection": ContentType.ITEM_COLLECTION,
            "equipment": ContentType.ITEM_COLLECTION,
            "spell": ContentType.SPELL_COLLECTION,
            "spell_collection": ContentType.SPELL_COLLECTION,
            "background": ContentType.BACKGROUND,
            "class": ContentType.CLASS_FEATURE,
            "chapter": ContentType.CHAPTER_INTRO,
        }

        content_type = type_mapping.get(type_hint, ContentType.UNKNOWN)

        return ContentContext(
            content_type=content_type,
            section_title=context_data.get("section_title"),
            surrounding_text=context_data.get("surrounding_text", ""),
            word_count=context_data.get("word_count", 500),  # Default estimate
            text_density=context_data.get("text_density", 0.6),
            has_other_images=context_data.get("has_other_images", False),
            nearby_images=context_data.get("nearby_images", []),
            structural_elements=context_data.get("structural_elements", []),
            reading_flow_position=context_data.get("reading_flow_position", "middle"),
        )

    def _create_document_context(
        self, context_data: dict[str, Any] | None
    ) -> DocumentContext:
        """Create document context from available data."""
        if not context_data:
            context_data = {}

        return DocumentContext(
            total_pages=context_data.get("total_pages", 50),  # Default estimate
            current_page=context_data.get("current_page", 1),
            page_position=context_data.get("page_position", 0.5),
            chapter_number=context_data.get("chapter_number"),
            section_depth=context_data.get("section_depth", 1),
            document_style=context_data.get("document_style", "standard"),
            target_format=context_data.get("target_format", "pdf"),
            column_layout=context_data.get("column_layout", "single"),
            margin_size=context_data.get("margin_size", "normal"),
        )

    def _create_page_context(self, context_data: dict[str, Any]) -> PageContext:
        """Create page context from available data."""
        return PageContext(
            available_width=context_data.get("available_width", 500.0),
            available_height=context_data.get("available_height", 700.0),
            column_width=context_data.get("column_width", 450.0),
            margin_width=context_data.get("margin_width", 50.0),
            current_fill=context_data.get("current_fill", 0.5),
            remaining_space=context_data.get("remaining_space", 350.0),
            has_header=context_data.get("has_header", True),
            has_footer=context_data.get("has_footer", True),
            is_chapter_start=context_data.get("is_chapter_start", False),
        )

    def _create_user_preferences(self) -> UserPreferences:
        """Create user preferences from configuration."""
        return UserPreferences(
            prefer_inline=not self.enhanced_config.enable_text_wrapping,
            prefer_wrapped=self.enhanced_config.enable_text_wrapping,
            prefer_margins=self.enhanced_config.enable_margin_images,
            optimization_target=self.enhanced_config.optimization_target,
        )

    def _select_placement_strategy(
        self, content_context: ContentContext
    ) -> ContentAwarePlacementStrategy:
        """Select the appropriate placement strategy based on content type."""
        if (
            self.enhanced_config.use_specialized_strategies
            and content_context.content_type != ContentType.UNKNOWN
        ):
            return create_specialized_strategy(content_context.content_type)
        else:
            return self.content_aware_strategy or ContentAwarePlacementStrategy()

    async def _analyze_layout_impact(
        self, decision: Any, page_context: PageContext
    ) -> dict[str, float]:
        """Analyze the layout impact of a placement decision."""
        if not self.layout_analyzer:
            return {}

        # Simplified layout impact analysis
        space_analysis = self.layout_analyzer.analyze_page_space(page_context)

        return {
            "space_utilization": min(
                1.0, space_analysis.remaining_space / space_analysis.total_space
            ),
            "readability_impact": 0.8,  # Placeholder
            "aesthetic_contribution": decision.confidence,
        }

    async def _apply_output_optimization(
        self, image_metadata: ImageMetadata, decision: Any
    ) -> bool:
        """Apply output optimization if configured."""
        if not self.output_optimizer:
            return False

        try:
            # Apply optimization based on target
            if self.enhanced_config.optimization_target == OptimizationTarget.DIGITAL:
                result = self.output_optimizer.optimize_for_digital(image_metadata)
                return result.is_success()
            elif self.enhanced_config.optimization_target == OptimizationTarget.PRINT:
                result = self.output_optimizer.optimize_for_print(image_metadata)
                return result.is_success()
            else:
                hybrid_result = self.output_optimizer.create_hybrid_optimization(
                    image_metadata
                )
                return hybrid_result.is_success()

        except Exception as e:
            logger.error(f"Output optimization failed: {str(e)}")
            return False

    async def _fallback_to_base_placement(
        self,
        image_path: Path,
        image_entry: dict[str, Any],
        image_metadata: ImageMetadata,
    ) -> Result[EnhancedPlacementResult, str]:
        """Fallback to base placement method when enhanced features fail."""
        try:
            base_result = super().place_image(image_path, image_entry)

            # Convert to enhanced result
            enhanced_result = EnhancedPlacementResult(
                latex_command=base_result.latex_command,
                placement=base_result.placement,
                size_spec=base_result.size_spec,
                requires_packages=base_result.requires_packages,
                caption=base_result.caption,
                confidence=0.6,  # Moderate confidence for base method
                reasoning=["Base placement method used"],
                processing_metadata={"strategy_used": "base_fallback"},
            )

            return Success(enhanced_result)

        except Exception as e:
            return Error(f"Fallback placement failed: {str(e)}")

    def _size_to_spec(
        self, size: Any, content_context: ContentContext | None = None
    ) -> str:
        """Convert size enum to LaTeX specification with context-aware sizing.

        Args:
            size: Size specification from placement decision
            content_context: Content context for intelligent sizing

        Returns:
            LaTeX width specification compatible with wrapfigure environment
        """
        # Determine layout mode - default to two-column for 5e content
        layout_mode = "twocolumn"  # Most 5e content uses two-column layout
        content_type = None

        if content_context:
            content_type = (
                content_context.content_type.value
                if content_context.content_type
                else None
            )

        # For item compendiums and similar content, use column-aware sizing
        # Note: wrapfigure size parameter must be a simple width, not complex includegraphics parameters
        if layout_mode == "twocolumn":
            # In two-column layout, textwidth spans both columns
            # We want images to fit within a single column

            if content_type == "item":
                # Item images should be smaller and not dominate the layout
                return "0.6\\columnwidth"
            elif content_type == "spell":
                # Spell images also conservative sizing
                return "0.7\\columnwidth"
            elif content_type == "creature":
                # Creature images can be larger but still within column
                return "0.9\\columnwidth"
            else:
                # General content in two-column layout
                return "0.8\\columnwidth"

        # Single column or full-width layouts (fallback)
        return "0.8\\textwidth"

    def _get_includegraphics_params(
        self, size: Any, content_context: ContentContext | None = None
    ) -> str:
        """Get includegraphics parameters with height constraints.

        Args:
            size: Size specification from placement decision
            content_context: Content context for intelligent sizing

        Returns:
            LaTeX includegraphics parameters with width and height constraints
        """
        # Determine layout mode - default to two-column for 5e content
        layout_mode = "twocolumn"  # Most 5e content uses two-column layout
        content_type = None

        if content_context:
            content_type = (
                content_context.content_type.value
                if content_context.content_type
                else None
            )

        # For item compendiums and similar content, use column-aware sizing with height constraints
        if layout_mode == "twocolumn":
            if content_type == "item":
                # Item images: constrain both width and height to prevent page overflow
                return "width=0.6\\columnwidth,height=0.2\\textheight,keepaspectratio"
            elif content_type == "spell":
                # Spell images: conservative sizing with height constraint
                return "width=0.7\\columnwidth,height=0.25\\textheight,keepaspectratio"
            elif content_type == "creature":
                # Creature images: larger but still constrained
                return "width=0.9\\columnwidth,height=0.3\\textheight,keepaspectratio"
            else:
                # General content in two-column layout
                return "width=0.8\\columnwidth,height=0.3\\textheight,keepaspectratio"

        # Single column or full-width layouts (fallback)
        return "width=0.8\\textwidth,height=0.4\\textheight,keepaspectratio"

    def _generate_wrap_command(
        self,
        image_path: Path,
        title: str,
        placement: Any,  # ImagePlacement
        size_spec: str,
        label: str | None = None,
        content_context: ContentContext | None = None,
    ) -> str:
        """Generate wrapped image command with enhanced sizing.

        Override base class method to use improved sizing with height constraints.
        """
        side = (
            "l"
            if str(placement).endswith("WRAP_LEFT") or "wrap-left" in str(placement)
            else "r"
        )

        # Get improved includegraphics parameters with height constraints
        graphics_params = self._get_includegraphics_params(None, content_context)

        command = f"""\\begin{{wrapfigure}}{{{side}}}{{{size_spec}}}
    \\centering
    \\includegraphics[{graphics_params}]{{{image_path}}}"""

        if title:
            command += f"\n    \\caption{{{title}}}"

        if label:
            command += f"\n    \\label{{{label}}}"

        command += "\n\\end{wrapfigure}"
        return command

    def get_placement_statistics(self) -> dict[str, Any]:
        """Get statistics about placement decisions made."""
        return {
            "intelligent_placement_enabled": self.enhanced_config.enable_intelligent_placement,
            "content_analysis_enabled": self.enhanced_config.enable_content_analysis,
            "layout_optimization_enabled": self.enhanced_config.enable_layout_optimization,
            "output_optimization_enabled": self.enhanced_config.enable_output_optimization,
            "cache_size": len(self._placement_cache),
            "optimization_target": self.enhanced_config.optimization_target.value,
        }

    def clear_placement_cache(self) -> None:
        """Clear the placement decision cache."""
        self._placement_cache.clear()
        if self.content_aware_strategy:
            # Clear strategy cache if available
            pass
        logger.debug("Cleared placement decision cache")

"""Bestiary-specific image integration for creature statblocks.

This module provides intelligent image integration capabilities specifically
tailored for creature statblocks and bestiary content, building on the
Phase 2 ContentAwarePlacementStrategy system.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from studiorum.core.logging import get_logger
from studiorum.core.result import Error, Result, Success
from studiorum.latex_engine.core.images.placement_models import (
    ContentContext,
    ContentType,
    DocumentContext,
    ImageCharacteristic,
    ImageMetadata,
    OptimizationTarget,
    PageContext,
)
from studiorum.renderers.core.interfaces import RenderingContext

if TYPE_CHECKING:
    from ..content_aware_strategy import ContentAwarePlacementStrategy
    from ..enhanced_image_placer import EnhancedImagePlacer
    from ..image_processor import ImageProcessor

logger = get_logger(__name__)


class BestiaryIntegrationConfig(BaseModel):
    """Configuration for bestiary image integration."""

    enable_creature_portraits: bool = Field(
        default=True, description="Enable creature portrait integration"
    )
    enable_environment_images: bool = Field(
        default=True, description="Enable environment/habitat images"
    )
    enable_action_illustrations: bool = Field(
        default=True, description="Enable action and ability illustrations"
    )
    preferred_portrait_placement: str = Field(
        default="margin", description="Preferred placement for creature portraits"
    )
    max_images_per_creature: int = Field(
        default=3, ge=1, le=10, description="Maximum images per creature"
    )
    portrait_max_width: str = Field(
        default="0.4\\textwidth", description="Maximum width for creature portraits"
    )
    environment_max_width: str = Field(
        default="0.6\\textwidth", description="Maximum width for environment images"
    )
    enable_intelligent_sizing: bool = Field(
        default=True, description="Enable intelligent image sizing based on content"
    )


class CreatureImageMetadata(BaseModel):
    """Metadata for creature-specific images."""

    creature_name: str
    creature_type: str | None = None
    challenge_rating: str | None = None
    size: str | None = None
    environment: list[str] = Field(default_factory=list)
    image_type: str = Field(default="portrait")  # portrait, environment, action
    confidence_score: float = Field(default=0.5, ge=0.0, le=1.0)
    source_context: dict[str, Any] = Field(default_factory=dict)


class BestiaryImageResult(BaseModel):
    """Result of bestiary image integration."""

    latex_command: str
    images_processed: int
    placement_strategy: str
    integration_metadata: dict[str, Any] = Field(default_factory=dict)


class BestiaryImageIntegration:
    """Intelligent image integration for creature statblocks and bestiary content.

    This class provides sophisticated image discovery, analysis, and integration
    specifically designed for D&D 5e creature content, using the Phase 2
    ContentAwarePlacementStrategy system.
    """

    def __init__(
        self,
        config: BestiaryIntegrationConfig | None = None,
        image_processor: ImageProcessor | None = None,
        enhanced_placer: EnhancedImagePlacer | None = None,
    ) -> None:
        """Initialize the bestiary image integration.

        Args:
            config: Integration configuration
            image_processor: Image processor for handling images
            enhanced_placer: Enhanced image placer for intelligent placement
        """
        self.config = config or BestiaryIntegrationConfig()
        self._image_processor = image_processor
        self._enhanced_placer = enhanced_placer
        self._content_aware_strategy: ContentAwarePlacementStrategy | None = None

        logger.debug("Initialized BestiaryImageIntegration")

    async def integrate_creature_images(
        self,
        creature_data: dict[str, Any],
        context: RenderingContext,
        available_images: list[dict[str, Any]] | None = None,
    ) -> Result[BestiaryImageResult, str]:
        """Integrate images for a creature statblock.

        Args:
            creature_data: Creature information dictionary
            context: Current rendering context
            available_images: Pre-discovered images for the creature

        Returns:
            Result containing integrated LaTeX or error message
        """
        try:
            creature_name = creature_data.get("name", "Unknown Creature")
            logger.info(f"Integrating images for creature: {creature_name}")

            # Discover creature images if not provided
            if available_images is None:
                discovery_result = await self._discover_creature_images(
                    creature_data, context
                )
                if isinstance(discovery_result, Error):
                    return Error(f"Image discovery failed: {discovery_result.error}")

                available_images = discovery_result.unwrap()

            if not available_images:
                logger.debug(f"No images found for creature: {creature_name}")
                return Success(
                    BestiaryImageResult(
                        latex_command="% No creature images available",
                        images_processed=0,
                        placement_strategy="none",
                        integration_metadata={"creature_name": creature_name},
                    )
                )

            # Analyze and categorize images
            categorized_images = self._categorize_creature_images(
                available_images, creature_data
            )

            # Select best images based on configuration and context
            selected_images = self._select_optimal_images(
                categorized_images, creature_data, context
            )

            if not selected_images:
                return Success(
                    BestiaryImageResult(
                        latex_command="% No suitable creature images found",
                        images_processed=0,
                        placement_strategy="none",
                        integration_metadata={"creature_name": creature_name},
                    )
                )

            # Generate integrated LaTeX
            latex_result = await self._generate_integrated_latex(
                selected_images, creature_data, context
            )

            if latex_result.is_error():
                return Error("Failed to generate bestiary LaTeX")

            latex_command = latex_result.unwrap()

            result = BestiaryImageResult(
                latex_command=latex_command,
                images_processed=len(selected_images),
                placement_strategy="content_aware_bestiary",
                integration_metadata={
                    "creature_name": creature_name,
                    "image_types": [img["type"] for img in selected_images],
                    "total_candidates": len(available_images),
                },
            )

            logger.info(
                f"Successfully integrated {len(selected_images)} images for {creature_name}"
            )

            return Success(result)

        except Exception as e:
            logger.error(f"Bestiary image integration failed: {str(e)}")
            return Error(f"Integration failed: {str(e)}")

    async def _discover_creature_images(
        self, creature_data: dict[str, Any], context: RenderingContext
    ) -> Result[list[dict[str, Any]], str]:
        """Discover available images for a creature.

        This method would integrate with image source registries and
        search for creature-specific images based on metadata.
        """
        try:
            creature_name = creature_data.get("name", "")
            creature_type = creature_data.get("type", "")
            creature_data.get("source", "")

            # Build search terms
            search_terms = [creature_name.lower()]
            if creature_type:
                search_terms.append(creature_type.lower())

            # For now, simulate image discovery
            # In a real implementation, this would query:
            # - ImageSourceRegistry
            # - Local asset directories
            # - 5etools-img database
            # - User-provided image mappings

            discovered_images = []

            # Simulate discovering a portrait
            if self.config.enable_creature_portraits:
                portrait_candidates = [
                    {
                        "href": {
                            "type": "external",
                            "path": f"creatures/{creature_name.lower()}_portrait.webp",
                        },
                        "title": f"{creature_name} Portrait",
                        "type": "portrait",
                        "confidence": 0.8,
                        "altText": f"Portrait of {creature_name}",
                    }
                ]
                discovered_images.extend(portrait_candidates)

            # Simulate discovering environment images
            if self.config.enable_environment_images:
                environments = creature_data.get("environment", [])
                for env in environments[:2]:  # Limit to 2 environment images
                    env_image = {
                        "href": {
                            "type": "external",
                            "path": f"environments/{env.lower()}.webp",
                        },
                        "title": f"{env} Environment",
                        "type": "environment",
                        "confidence": 0.6,
                        "altText": f"{env} environment where {creature_name} can be found",
                    }
                    discovered_images.append(env_image)

            logger.debug(
                f"Discovered {len(discovered_images)} candidate images for {creature_name}"
            )
            return Success(discovered_images)

        except Exception as e:
            return Error(f"Image discovery failed: {str(e)}")

    def _categorize_creature_images(
        self, images: list[dict[str, Any]], creature_data: dict[str, Any]
    ) -> dict[str, list[dict[str, Any]]]:
        """Categorize images by type and suitability for the creature."""
        categories: dict[str, list[dict[str, Any]]] = {
            "portrait": [],
            "environment": [],
            "action": [],
            "other": [],
        }

        for image in images:
            image_type = image.get("type", "other")
            if image_type not in categories:
                image_type = "other"

            # Add creature-specific metadata
            enhanced_image = image.copy()
            enhanced_image["creature_metadata"] = CreatureImageMetadata(
                creature_name=creature_data.get("name", "Unknown"),
                creature_type=creature_data.get("type"),
                challenge_rating=creature_data.get("cr"),
                size=creature_data.get("size"),
                environment=creature_data.get("environment", []),
                image_type=image_type,
                confidence_score=image.get("confidence", 0.5),
                source_context=creature_data,
            ).model_dump()

            categories[image_type].append(enhanced_image)

        return categories

    def _select_optimal_images(
        self,
        categorized_images: dict[str, list[dict[str, Any]]],
        creature_data: dict[str, Any],
        context: RenderingContext,
    ) -> list[dict[str, Any]]:
        """Select the most appropriate images based on context and configuration."""
        selected = []
        max_images = self.config.max_images_per_creature

        # Prioritize portrait images
        portraits = categorized_images.get("portrait", [])
        if portraits and self.config.enable_creature_portraits:
            # Select highest confidence portrait
            best_portrait = max(portraits, key=lambda x: x.get("confidence", 0))
            selected.append(best_portrait)

        # Add environment images if space allows
        if len(selected) < max_images and self.config.enable_environment_images:
            environments = categorized_images.get("environment", [])
            # Select up to 2 environment images
            for env_img in environments[: min(2, max_images - len(selected))]:
                selected.append(env_img)

        # Add action images if configured and space allows
        if len(selected) < max_images and self.config.enable_action_illustrations:
            actions = categorized_images.get("action", [])
            remaining_slots = max_images - len(selected)
            selected.extend(actions[:remaining_slots])

        logger.debug(
            f"Selected {len(selected)} images from {sum(len(imgs) for imgs in categorized_images.values())} candidates"
        )
        return selected

    async def _generate_integrated_latex(
        self,
        selected_images: list[dict[str, Any]],
        creature_data: dict[str, Any],
        context: RenderingContext,
    ) -> Result[str, str]:
        """Generate integrated LaTeX for the selected creature images."""
        try:
            if not selected_images:
                return Success("% No creature images to integrate")

            latex_parts = []

            # Process each image with appropriate placement
            for i, image in enumerate(selected_images):
                image_type = image.get("type", "other")

                # Create content context for bestiary content
                content_context = self._create_bestiary_context(creature_data, image)

                if self._enhanced_placer:
                    # Use enhanced placement for optimal integration
                    result = await self._place_image_with_enhancement(
                        image, content_context, context
                    )
                    match result:
                        case Success(latex):
                            latex_parts.append(latex)
                            continue
                        case Error(_):
                            pass  # Fall through to basic placement

                # Fallback to basic placement
                basic_latex = self._create_basic_creature_image_latex(image, image_type)
                latex_parts.append(basic_latex)

            # Combine all LaTeX parts
            final_latex = "\n\n".join(latex_parts)
            return Success(final_latex)

        except Exception as e:
            return Error(f"LaTeX generation failed: {str(e)}")

    def _create_bestiary_context(
        self, creature_data: dict[str, Any], image: dict[str, Any]
    ) -> dict[str, Any]:
        """Create content context specifically for bestiary content."""
        return {
            "type": "bestiary",
            "content_type": ContentType.BESTIARY,
            "creature_name": creature_data.get("name"),
            "creature_type": creature_data.get("type"),
            "challenge_rating": creature_data.get("cr"),
            "image_type": image.get("type", "portrait"),
            "section_title": f"{creature_data.get('name', 'Creature')} Statblock",
            "surrounding_text": "creature statblock",
            "word_count": 800,  # Typical statblock length
            "text_density": 0.9,  # High density for statblocks
            "has_other_images": len(image.get("siblings", [])) > 0,
            "reading_flow_position": "side",  # Statblocks often benefit from side placement
        }

    async def _place_image_with_enhancement(
        self,
        image: dict[str, Any],
        content_context: dict[str, Any],
        context: RenderingContext,
    ) -> Result[str, str]:
        """Place image using enhanced placement capabilities."""
        try:
            if not self._enhanced_placer:
                return Error("Enhanced placer not available")

            # Convert image path (this would be more sophisticated in real implementation)
            image_path = Path("placeholder.png")  # Placeholder

            # Use enhanced placement
            result = await self._enhanced_placer.place_image_enhanced(
                image_path, image, content_context
            )

            if isinstance(result, Error):
                return Error(f"Enhanced placement failed: {result.error}")

            enhanced_result = result.unwrap()
            return Success(enhanced_result.latex_command)

        except Exception as e:
            return Error(f"Enhanced placement error: {str(e)}")

    def _create_basic_creature_image_latex(
        self, image: dict[str, Any], image_type: str
    ) -> str:
        """Create basic LaTeX for creature images as fallback."""
        href = image.get("href", {})
        title = image.get("title", "")

        # Extract image path
        if isinstance(href, dict):
            image_path = href.get("path", href.get("url", "placeholder.png"))
        else:
            image_path = str(href)

        # Determine width based on image type
        if image_type == "portrait":
            width = self.config.portrait_max_width
            placement = "[htbp]"
        elif image_type == "environment":
            width = self.config.environment_max_width
            placement = "[htbp]"
        else:
            width = "0.5\\textwidth"
            placement = "[htbp]"

        if title:
            return (
                f"\\begin{{figure}}{placement}\n"
                f"    \\centering\n"
                f"    \\includegraphics[width={width}]{{{image_path}}}\n"
                f"    \\caption{{{title}}}\n"
                f"\\end{{figure}}"
            )
        else:
            return (
                f"\\begin{{center}}\n"
                f"    \\includegraphics[width={width}]{{{image_path}}}\n"
                f"\\end{{center}}"
            )

    def get_integration_statistics(self) -> dict[str, Any]:
        """Get statistics about integration operations."""
        return {
            "config": self.config.model_dump(),
            "has_image_processor": self._image_processor is not None,
            "has_enhanced_placer": self._enhanced_placer is not None,
        }

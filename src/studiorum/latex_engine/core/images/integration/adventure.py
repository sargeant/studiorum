"""Adventure-specific image integration for narrative content and campaigns.

This module provides intelligent image integration capabilities specifically
tailored for adventure content including chapters, locations, NPCs, and
atmospheric illustrations, building on the Phase 2 ContentAwarePlacementStrategy system.
"""

from __future__ import annotations

import asyncio
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
    ImageDimensions,
    ImageMetadata,
    OptimizationTarget,
    PageContext,
)
from studiorum.renderers.core.interfaces import RenderingContext

if TYPE_CHECKING:
    from ..content_aware_strategy import ContentAwarePlacementStrategy
    from ..enhanced_image_placer import EnhancedImagePlacer
    from ..gallery_processor import GalleryProcessor
    from ..image_processor import ImageProcessor

logger = get_logger(__name__)


class AdventureIntegrationConfig(BaseModel):
    """Configuration for adventure image integration."""

    enable_chapter_openers: bool = Field(
        default=True, description="Enable chapter opening art"
    )
    enable_location_maps: bool = Field(
        default=True, description="Enable location and regional maps"
    )
    enable_npc_portraits: bool = Field(
        default=True, description="Enable NPC portrait integration"
    )
    enable_atmospheric_scenes: bool = Field(
        default=True, description="Enable atmospheric scene illustrations"
    )
    enable_chapter_galleries: bool = Field(
        default=True, description="Enable chapter-specific image galleries"
    )
    chapter_opener_placement: str = Field(
        default="chapter_start", description="Placement strategy for chapter openers"
    )
    map_placement_preference: str = Field(
        default="inline", description="Preferred placement for maps"
    )
    npc_portrait_size: str = Field(
        default="0.25\\textwidth", description="Default size for NPC portraits"
    )
    atmospheric_placement: str = Field(
        default="margin", description="Placement for atmospheric illustrations"
    )
    max_images_per_chapter: int = Field(
        default=8, ge=1, le=20, description="Maximum images per chapter"
    )
    enable_decorative_elements: bool = Field(
        default=True, description="Enable decorative LaTeX elements"
    )
    chapter_opener_style: str = Field(
        default="full_width", description="Style for chapter opening images"
    )


class AdventureImageMetadata(BaseModel):
    """Metadata for adventure-specific images."""

    adventure_name: str
    chapter_name: str | None = None
    chapter_number: int | None = None
    location: str | None = None
    npcs: list[str] = Field(default_factory=list)
    themes: list[str] = Field(default_factory=list)
    chapter_type: str = Field(
        default="narrative"
    )  # opening, narrative, dungeon, conclusion
    image_type: str = Field(
        default="illustration"
    )  # opener, map, portrait, scene, gallery
    is_chapter_opener: bool = Field(default=False)
    atmosphere: str | None = None
    difficulty_context: str | None = None
    narrative_context: dict[str, Any] = Field(default_factory=dict)
    confidence_score: float = Field(default=0.5, ge=0.0, le=1.0)
    source_context: dict[str, Any] = Field(default_factory=dict)


class AdventureImageResult(BaseModel):
    """Result of adventure image integration."""

    latex_command: str
    chapters_processed: int
    images_integrated: int
    layout_used: str
    opener_images_count: int = Field(default=0)
    map_images_count: int = Field(default=0)
    npc_images_count: int = Field(default=0)
    atmospheric_images_count: int = Field(default=0)
    integration_metadata: dict[str, Any] = Field(default_factory=dict)


class AdventureImageIntegration:
    """Intelligent image integration for adventure content and campaigns.

    This class provides sophisticated image discovery, categorization, and
    integration specifically designed for D&D 5e adventure modules, supporting
    chapter openers, location maps, NPC portraits, and atmospheric scenes.
    """

    def __init__(
        self,
        image_processor: ImageProcessor,
        enhanced_placer: EnhancedImagePlacer,
        content_aware_strategy: ContentAwarePlacementStrategy,
        gallery_processor: GalleryProcessor,
        config: AdventureIntegrationConfig | None = None,
    ) -> None:
        """Initialize adventure image integration.

        Args:
            image_processor: Core image processing component
            enhanced_placer: Enhanced image placement system
            content_aware_strategy: Content-aware placement strategy
            gallery_processor: Gallery processing component
            config: Adventure integration configuration

        """
        self.config = config or AdventureIntegrationConfig()
        self._image_processor = image_processor
        self._enhanced_placer = enhanced_placer
        self._content_aware_strategy = content_aware_strategy
        self._gallery_processor = gallery_processor

    async def integrate_adventure_images(
        self,
        adventure_content: dict[str, Any],
        rendering_context: RenderingContext,
    ) -> Result[AdventureImageResult, str]:
        """Integrate images for adventure content with intelligent categorization.

        Args:
            adventure_content: Adventure content data
            rendering_context: Context for rendering operations

        Returns:
            Result containing adventure image integration data or error

        """
        try:
            logger.debug(
                "Starting adventure image integration",
                extra={
                    "adventure": adventure_content.get("name", "unknown"),
                    "chapter_count": len(
                        adventure_content.get("data", {}).get("chapter", [])
                    ),
                },
            )

            # Extract adventure metadata
            adventure_metadata = self._extract_adventure_metadata(adventure_content)

            # Discover adventure-specific images
            image_discovery_result = await self._discover_adventure_images(
                adventure_metadata, rendering_context
            )
            if isinstance(image_discovery_result, Error):
                return image_discovery_result.with_context(
                    "Failed to discover adventure images",
                    operation="adventure_image_integration",
                    adventure_name=adventure_metadata.get("name", "unknown"),
                )

            discovered_images = image_discovery_result.unwrap()

            # Categorize images by type and purpose
            categorized_images = self._categorize_adventure_images(
                discovered_images, adventure_metadata
            )

            # Select optimal images for integration
            selected_images = self._select_optimal_adventure_images(
                categorized_images, adventure_metadata
            )

            # Generate integrated LaTeX with decorative elements
            latex_result = await self._generate_integrated_adventure_latex(
                selected_images, adventure_metadata, rendering_context
            )
            if isinstance(latex_result, Error):
                return latex_result.with_context(
                    "Failed to generate adventure LaTeX",
                    operation="adventure_latex_generation",
                    images_count=len(selected_images),
                )

            # Create result summary
            result = AdventureImageResult(
                latex_command=latex_result.unwrap(),
                chapters_processed=len(adventure_metadata.get("chapters", [])),
                images_integrated=len(selected_images),
                layout_used=self.config.chapter_opener_placement,
                opener_images_count=len(
                    [img for img in selected_images if img.is_chapter_opener]
                ),
                map_images_count=len(
                    [img for img in selected_images if img.image_type == "map"]
                ),
                npc_images_count=len(
                    [img for img in selected_images if img.image_type == "portrait"]
                ),
                atmospheric_images_count=len(
                    [img for img in selected_images if img.image_type == "scene"]
                ),
                integration_metadata={
                    "adventure_name": adventure_metadata.get("adventure_name", ""),
                    "processing_time": "estimated",
                    "decorative_elements": self.config.enable_decorative_elements,
                },
            )

            logger.info(
                "Adventure image integration completed successfully",
                extra={
                    "chapters_processed": result.chapters_processed,
                    "images_integrated": result.images_integrated,
                },
            )

            return Success(result)

        except Exception as e:
            error_msg = f"Adventure image integration failed: {e}"
            logger.error(error_msg, exc_info=True)
            return Error(error_msg)

    async def _discover_adventure_images(
        self,
        adventure_metadata: dict[str, Any],
        rendering_context: RenderingContext,
    ) -> Result[list[ImageMetadata], str]:
        """Discover images relevant to adventure content.

        Args:
            adventure_metadata: Adventure metadata for image discovery
            rendering_context: Context for image discovery operations

        Returns:
            Result containing list of discovered images or error

        """
        try:
            discovered_images: list[ImageMetadata] = []
            adventure_name = adventure_metadata.get("adventure_name", "")

            # Discovery patterns for adventure content
            discovery_patterns = [
                # Chapter openers
                f"{adventure_name.lower().replace(' ', '_')}_chapter_*",
                f"chapter_*_{adventure_name.lower().replace(' ', '_')}",
                "chapter_opener_*",
                # Location maps
                f"{adventure_name.lower().replace(' ', '_')}_map_*",
                f"*_map_{adventure_name.lower().replace(' ', '_')}",
                "location_map_*",
                # NPC portraits
                f"{adventure_name.lower().replace(' ', '_')}_npc_*",
                f"npc_*_{adventure_name.lower().replace(' ', '_')}",
                "portrait_*",
                # Atmospheric scenes
                f"{adventure_name.lower().replace(' ', '_')}_scene_*",
                f"atmospheric_*_{adventure_name.lower().replace(' ', '_')}",
                "scene_*",
                "atmosphere_*",
            ]

            # Add location-specific patterns
            for location in adventure_metadata.get("locations", []):
                location_key = location.lower().replace(" ", "_")
                discovery_patterns.extend(
                    [
                        f"{location_key}_*",
                        f"*_{location_key}",
                        f"{location_key}_map",
                        f"{location_key}_scene",
                    ]
                )

            # Add NPC-specific patterns
            for npc in adventure_metadata.get("npcs", []):
                npc_key = npc.lower().replace(" ", "_")
                discovery_patterns.extend(
                    [
                        f"{npc_key}_*",
                        f"*_{npc_key}",
                        f"portrait_{npc_key}",
                        f"{npc_key}_portrait",
                    ]
                )

            # Execute discovery using image processor
            for pattern in discovery_patterns:
                try:
                    # This would use the actual image discovery system
                    # For now, we create sample metadata
                    sample_images = await self._create_sample_adventure_images(
                        pattern, adventure_metadata
                    )
                    discovered_images.extend(sample_images)
                except Exception as pattern_error:
                    logger.debug(
                        f"Discovery pattern failed: {pattern}",
                        extra={"error": str(pattern_error)},
                    )

            logger.debug(
                f"Discovered {len(discovered_images)} adventure images",
                extra={
                    "adventure": adventure_name,
                    "patterns_used": len(discovery_patterns),
                },
            )

            return Success(discovered_images)

        except Exception as e:
            error_msg = f"Adventure image discovery failed: {e}"
            logger.error(error_msg, exc_info=True)
            return Error(error_msg)

    def _categorize_adventure_images(
        self,
        discovered_images: list[ImageMetadata],
        adventure_metadata: dict[str, Any],
    ) -> dict[str, list[AdventureImageMetadata]]:
        """Categorize discovered images by adventure content type.

        Args:
            discovered_images: List of discovered image metadata
            adventure_metadata: Adventure metadata for categorization

        Returns:
            Dictionary of categorized adventure images

        """
        categorized: dict[str, list[AdventureImageMetadata]] = {
            "chapter_openers": [],
            "location_maps": [],
            "npc_portraits": [],
            "atmospheric_scenes": [],
            "gallery_collections": [],
        }

        for img in discovered_images:
            # Determine image category based on characteristics and context
            adventure_img = self._create_adventure_image_metadata(
                img, adventure_metadata
            )

            if adventure_img.is_chapter_opener or adventure_img.image_type == "opener":
                categorized["chapter_openers"].append(adventure_img)
            elif adventure_img.image_type == "map":
                categorized["location_maps"].append(adventure_img)
            elif adventure_img.image_type == "portrait":
                categorized["npc_portraits"].append(adventure_img)
            elif adventure_img.image_type == "scene":
                categorized["atmospheric_scenes"].append(adventure_img)
            else:
                categorized["gallery_collections"].append(adventure_img)

        logger.debug(
            "Adventure images categorized",
            extra={
                "chapter_openers": len(categorized["chapter_openers"]),
                "location_maps": len(categorized["location_maps"]),
                "npc_portraits": len(categorized["npc_portraits"]),
                "atmospheric_scenes": len(categorized["atmospheric_scenes"]),
            },
        )

        return categorized

    def _select_optimal_adventure_images(
        self,
        categorized_images: dict[str, list[AdventureImageMetadata]],
        adventure_metadata: dict[str, Any],
    ) -> list[AdventureImageMetadata]:
        """Select optimal images for adventure integration.

        Args:
            categorized_images: Categorized adventure images
            adventure_metadata: Adventure metadata for selection

        Returns:
            List of selected adventure images

        """
        selected_images: list[AdventureImageMetadata] = []
        max_images = self.config.max_images_per_chapter

        # Priority selection based on configuration
        if self.config.enable_chapter_openers:
            # Select best chapter openers (one per chapter)
            chapter_openers = categorized_images["chapter_openers"]
            chapter_count = len(adventure_metadata.get("chapters", []))
            selected_openers = sorted(
                chapter_openers, key=lambda x: x.confidence_score, reverse=True
            )[: min(chapter_count, len(chapter_openers))]
            selected_images.extend(selected_openers)

        if self.config.enable_location_maps:
            # Select location maps based on importance
            location_maps = categorized_images["location_maps"]
            selected_maps = sorted(
                location_maps, key=lambda x: x.confidence_score, reverse=True
            )[: min(3, len(location_maps))]  # Max 3 maps per adventure
            selected_images.extend(selected_maps)

        if self.config.enable_npc_portraits:
            # Select key NPC portraits
            npc_portraits = categorized_images["npc_portraits"]
            selected_npcs = sorted(
                npc_portraits, key=lambda x: x.confidence_score, reverse=True
            )[: min(5, len(npc_portraits))]  # Max 5 NPCs per adventure
            selected_images.extend(selected_npcs)

        if self.config.enable_atmospheric_scenes:
            # Select atmospheric scenes for narrative enhancement
            atmospheric_scenes = categorized_images["atmospheric_scenes"]
            selected_scenes = sorted(
                atmospheric_scenes, key=lambda x: x.confidence_score, reverse=True
            )[: min(4, len(atmospheric_scenes))]  # Max 4 scenes per adventure
            selected_images.extend(selected_scenes)

        # Apply global limit per chapter if needed
        if len(selected_images) > max_images:
            selected_images = sorted(
                selected_images, key=lambda x: x.confidence_score, reverse=True
            )[:max_images]

        logger.debug(
            f"Selected {len(selected_images)} adventure images for integration"
        )
        return selected_images

    async def _generate_integrated_adventure_latex(
        self,
        selected_images: list[AdventureImageMetadata],
        adventure_metadata: dict[str, Any],
        rendering_context: RenderingContext,
    ) -> Result[str, str]:
        """Generate integrated LaTeX with decorative elements for adventure images.

        Args:
            selected_images: Selected adventure images for integration
            adventure_metadata: Adventure metadata
            rendering_context: Context for LaTeX generation

        Returns:
            Result containing generated LaTeX or error

        """
        try:
            latex_commands: list[str] = []

            # Group images by chapter for organized integration
            images_by_chapter = self._group_images_by_chapter(selected_images)

            for chapter_key, chapter_images in images_by_chapter.items():
                # Chapter opener with decorative elements
                chapter_openers = [
                    img for img in chapter_images if img.is_chapter_opener
                ]
                if chapter_openers and self.config.enable_chapter_openers:
                    opener = chapter_openers[0]
                    opener_latex = await self._create_chapter_opener_latex(
                        opener, adventure_metadata, rendering_context
                    )
                    if isinstance(opener_latex, Success):
                        latex_commands.append(opener_latex.unwrap())

                # Location maps with enhanced placement
                map_images = [img for img in chapter_images if img.image_type == "map"]
                for map_img in map_images:
                    map_latex = await self._create_location_map_latex(
                        map_img, adventure_metadata, rendering_context
                    )
                    if isinstance(map_latex, Success):
                        latex_commands.append(map_latex.unwrap())

                # NPC portraits with context
                npc_images = [
                    img for img in chapter_images if img.image_type == "portrait"
                ]
                for npc_img in npc_images:
                    npc_latex = await self._create_npc_portrait_latex(
                        npc_img, adventure_metadata, rendering_context
                    )
                    if isinstance(npc_latex, Success):
                        latex_commands.append(npc_latex.unwrap())

                # Atmospheric scenes
                scene_images = [
                    img for img in chapter_images if img.image_type == "scene"
                ]
                for scene_img in scene_images:
                    scene_latex = await self._create_atmospheric_scene_latex(
                        scene_img, adventure_metadata, rendering_context
                    )
                    if isinstance(scene_latex, Success):
                        latex_commands.append(scene_latex.unwrap())

            # Create gallery collections if enabled
            if self.config.enable_chapter_galleries:
                gallery_latex = await self._create_adventure_gallery_latex(
                    selected_images, adventure_metadata, rendering_context
                )
                if isinstance(gallery_latex, Success):
                    latex_commands.append(gallery_latex.unwrap())

            final_latex = "\n\n".join(latex_commands)
            logger.debug(
                f"Generated adventure LaTeX with {len(latex_commands)} commands"
            )

            return Success(final_latex)

        except Exception as e:
            error_msg = f"Adventure LaTeX generation failed: {e}"
            logger.error(error_msg, exc_info=True)
            return Error(error_msg)

    def _extract_adventure_metadata(
        self, adventure_content: dict[str, Any]
    ) -> dict[str, Any]:
        """Extract metadata from adventure content for image discovery.

        Args:
            adventure_content: Adventure content data

        Returns:
            Dictionary of extracted adventure metadata

        """
        metadata = {
            "adventure_name": adventure_content.get("name", "Unknown Adventure"),
            "chapters": [],
            "locations": set(),
            "npcs": set(),
            "themes": set(),
        }

        # Extract chapter information
        adventure_data = adventure_content.get("data", {})
        chapters = adventure_data.get("chapter", [])

        for chapter_data in chapters:
            chapter_info = {
                "name": chapter_data.get("name", ""),
                "number": chapter_data.get("ordinal", 0),
                "type": self._determine_chapter_type(chapter_data),
            }
            metadata["chapters"].append(chapter_info)

            # Extract locations and NPCs from chapter entries
            entries = chapter_data.get("entries", [])
            self._extract_chapter_entities(entries, metadata)

        # Convert sets to lists for JSON serialization
        metadata["locations"] = list(metadata["locations"])
        metadata["npcs"] = list(metadata["npcs"])
        metadata["themes"] = list(metadata["themes"])

        return metadata

    def _determine_chapter_type(self, chapter_data: dict[str, Any]) -> str:
        """Determine the type of chapter for specialized image handling.

        Args:
            chapter_data: Chapter content data

        Returns:
            String indicating chapter type

        """
        chapter_name = chapter_data.get("name", "").lower()

        if any(
            keyword in chapter_name
            for keyword in ["introduction", "prologue", "beginning"]
        ):
            return "opening"
        elif any(
            keyword in chapter_name for keyword in ["dungeon", "tomb", "lair", "cavern"]
        ):
            return "dungeon"
        elif any(
            keyword in chapter_name for keyword in ["conclusion", "epilogue", "finale"]
        ):
            return "conclusion"
        else:
            return "narrative"

    def _extract_chapter_entities(
        self, entries: list[dict[str, Any]], metadata: dict[str, Any]
    ) -> None:
        """Extract locations, NPCs, and themes from chapter entries.

        Args:
            entries: Chapter entry data
            metadata: Metadata dictionary to populate

        """
        for entry in entries:
            if isinstance(entry, dict):
                # Look for location references
                if "location" in entry or "place" in entry:
                    location = entry.get("location") or entry.get("place")
                    if location:
                        metadata["locations"].add(location)

                # Look for NPC references
                if "npc" in entry or "character" in entry or "name" in entry:
                    npc = entry.get("npc") or entry.get("character")
                    if npc:
                        metadata["npcs"].add(npc)

                # Look for theme keywords
                entry_text = str(entry.get("entries", "")).lower()
                theme_keywords = [
                    "horror",
                    "mystery",
                    "combat",
                    "exploration",
                    "social",
                ]
                for theme in theme_keywords:
                    if theme in entry_text:
                        metadata["themes"].add(theme)

                # Recursive processing for nested entries
                if "entries" in entry and isinstance(entry["entries"], list):
                    self._extract_chapter_entities(entry["entries"], metadata)

    def _create_adventure_image_metadata(
        self,
        base_image: ImageMetadata,
        adventure_metadata: dict[str, Any],
    ) -> AdventureImageMetadata:
        """Create adventure-specific image metadata from base image data.

        Args:
            base_image: Base image metadata
            adventure_metadata: Adventure context metadata

        Returns:
            Adventure-specific image metadata

        """
        # Determine image type and chapter context from base metadata
        image_type = "illustration"
        is_chapter_opener = False
        chapter_name = None
        chapter_number = None

        # Analyze image characteristics for adventure context
        if "opener" in base_image.path.lower() or "chapter" in base_image.path.lower():
            image_type = "opener"
            is_chapter_opener = True
        elif "map" in base_image.path.lower():
            image_type = "map"
        elif "portrait" in base_image.path.lower() or "npc" in base_image.path.lower():
            image_type = "portrait"
        elif any(
            keyword in base_image.path.lower() for keyword in ["scene", "atmosphere"]
        ):
            image_type = "scene"

        return AdventureImageMetadata(
            adventure_name=adventure_metadata.get("adventure_name", ""),
            chapter_name=chapter_name,
            chapter_number=chapter_number,
            image_type=image_type,
            is_chapter_opener=is_chapter_opener,
            themes=adventure_metadata.get("themes", []),
            confidence_score=0.7,  # Default confidence for adventure images
            source_context={"base_image": base_image.model_dump()},
        )

    def _group_images_by_chapter(
        self, images: list[AdventureImageMetadata]
    ) -> dict[str, list[AdventureImageMetadata]]:
        """Group images by chapter for organized integration.

        Args:
            images: List of adventure images to group

        Returns:
            Dictionary of images grouped by chapter

        """
        grouped: dict[str, list[AdventureImageMetadata]] = {}

        for image in images:
            chapter_key = image.chapter_name or "general"
            if chapter_key not in grouped:
                grouped[chapter_key] = []
            grouped[chapter_key].append(image)

        return grouped

    async def _create_chapter_opener_latex(
        self,
        opener_image: AdventureImageMetadata,
        adventure_metadata: dict[str, Any],
        rendering_context: RenderingContext,
    ) -> Result[str, str]:
        """Create LaTeX for chapter opener with decorative elements.

        Args:
            opener_image: Chapter opener image metadata
            adventure_metadata: Adventure context
            rendering_context: Rendering context

        Returns:
            Result containing LaTeX command or error

        """
        try:
            # Enhanced chapter opener with decorative elements
            decorative_elements = ""
            if self.config.enable_decorative_elements:
                decorative_elements = """
                \\begin{tikzpicture}[remember picture,overlay]
                  \\node[anchor=north west,inner sep=0pt] at (current page.north west) {%
                    \\includegraphics[width=\\paperwidth,height=0.3\\paperheight,keepaspectratio]{placeholder_opener}%
                  };
                  \\draw[line width=2pt,color=dndred] ([yshift=-0.3\\paperheight]current page.north west) -- ([yshift=-0.3\\paperheight]current page.north east);
                \\end{tikzpicture}
                """

            latex = f"""
            % Chapter Opener: {opener_image.adventure_name}
            {decorative_elements if self.config.enable_decorative_elements else ""}
            \\begin{{figure}}[t]
                \\centering
                \\includegraphics[width={self.config.chapter_opener_style == "full_width" and "\\textwidth" or "0.8\\textwidth"}]{{placeholder_chapter_opener}}
                \\caption*{{\\textit{{{opener_image.adventure_name} - {opener_image.chapter_name or "Chapter Opener"}}}}}
            \\end{{figure}}
            """

            return Success(latex.strip())

        except Exception as e:
            return Error(f"Chapter opener LaTeX generation failed: {e}")

    async def _create_location_map_latex(
        self,
        map_image: AdventureImageMetadata,
        adventure_metadata: dict[str, Any],
        rendering_context: RenderingContext,
    ) -> Result[str, str]:
        """Create LaTeX for location maps with context.

        Args:
            map_image: Location map image metadata
            adventure_metadata: Adventure context
            rendering_context: Rendering context

        Returns:
            Result containing LaTeX command or error

        """
        try:
            placement = self.config.map_placement_preference

            latex = f"""
            % Location Map: {map_image.location or "Adventure Location"}
            \\begin{{figure}}[{"h" if placement == "inline" else "htbp"}]
                \\centering
                \\includegraphics[width=0.9\\textwidth]{{placeholder_location_map}}
                \\caption{{\\textbf{{{map_image.location or "Adventure Map"}}}}}
                \\label{{map:{map_image.location or "adventure"}.lower().replace(' ', '_')}}
            \\end{{figure}}
            """

            return Success(latex.strip())

        except Exception as e:
            return Error(f"Location map LaTeX generation failed: {e}")

    async def _create_npc_portrait_latex(
        self,
        npc_image: AdventureImageMetadata,
        adventure_metadata: dict[str, Any],
        rendering_context: RenderingContext,
    ) -> Result[str, str]:
        """Create LaTeX for NPC portraits with character context.

        Args:
            npc_image: NPC portrait image metadata
            adventure_metadata: Adventure context
            rendering_context: Rendering context

        Returns:
            Result containing LaTeX command or error

        """
        try:
            latex = f"""
            % NPC Portrait
            \\begin{{wrapfigure}}{{r}}{{{self.config.npc_portrait_size}}}
                \\centering
                \\includegraphics[width={self.config.npc_portrait_size}]{{placeholder_npc_portrait}}
                \\caption*{{\\textit{{Character Portrait}}}}
            \\end{{wrapfigure}}
            """

            return Success(latex.strip())

        except Exception as e:
            return Error(f"NPC portrait LaTeX generation failed: {e}")

    async def _create_atmospheric_scene_latex(
        self,
        scene_image: AdventureImageMetadata,
        adventure_metadata: dict[str, Any],
        rendering_context: RenderingContext,
    ) -> Result[str, str]:
        """Create LaTeX for atmospheric scenes.

        Args:
            scene_image: Scene image metadata
            adventure_metadata: Adventure context
            rendering_context: Rendering context

        Returns:
            Result containing LaTeX command or error

        """
        try:
            placement = self.config.atmospheric_placement

            if placement == "margin":
                latex = """
                % Atmospheric Scene
                \\marginpar{\\includegraphics[width=\\marginparwidth]{placeholder_scene}}
                """
            else:
                latex = """
                % Atmospheric Scene
                \\begin{figure}[htbp]
                    \\centering
                    \\includegraphics[width=0.6\\textwidth]{placeholder_scene}
                    \\caption*{\\textit{Atmospheric Illustration}}
                \\end{figure}
                """

            return Success(latex.strip())

        except Exception as e:
            return Error(f"Atmospheric scene LaTeX generation failed: {e}")

    async def _create_adventure_gallery_latex(
        self,
        selected_images: list[AdventureImageMetadata],
        adventure_metadata: dict[str, Any],
        rendering_context: RenderingContext,
    ) -> Result[str, str]:
        """Create gallery layout for adventure image collections.

        Args:
            selected_images: Selected adventure images
            adventure_metadata: Adventure context
            rendering_context: Rendering context

        Returns:
            Result containing gallery LaTeX or error

        """
        try:
            # Use existing gallery processor for collection layout
            [
                ImageMetadata(
                    path=f"placeholder_{img.image_type}_{i}",
                    local_path=Path(f"placeholder_{i}"),
                    characteristics=[ImageCharacteristic.DECORATIVE],
                    dimensions=ImageDimensions.from_dimensions(800, 600),
                    file_size_bytes=1024000,
                )
                for i, img in enumerate(selected_images[:6])  # Max 6 for gallery
            ]

            # This would use the actual gallery processor
            gallery_latex = """
            % Adventure Image Gallery
            \\begin{figure}[htbp]
                \\centering
                \\begin{subfigure}{0.3\\textwidth}
                    \\includegraphics[width=\\textwidth]{placeholder_gallery_1}
                \\end{subfigure}
                \\hfill
                \\begin{subfigure}{0.3\\textwidth}
                    \\includegraphics[width=\\textwidth]{placeholder_gallery_2}
                \\end{subfigure}
                \\hfill
                \\begin{subfigure}{0.3\\textwidth}
                    \\includegraphics[width=\\textwidth]{placeholder_gallery_3}
                \\end{subfigure}
                \\caption{Adventure Gallery}
            \\end{figure}
            """

            return Success(gallery_latex.strip())

        except Exception as e:
            return Error(f"Adventure gallery LaTeX generation failed: {e}")

    async def _create_sample_adventure_images(
        self,
        pattern: str,
        adventure_metadata: dict[str, Any],
    ) -> list[ImageMetadata]:
        """Create sample image metadata for development/testing.

        Args:
            pattern: Discovery pattern used
            adventure_metadata: Adventure context metadata

        Returns:
            List of sample image metadata

        """
        # This is a placeholder implementation for testing
        # In production, this would interface with the actual image discovery system
        sample_images = []

        if "chapter" in pattern.lower():
            sample_images.append(
                ImageMetadata(
                    path=f"chapter_opener_{pattern}",
                    local_path=Path(f"/placeholder/chapter_opener_{pattern}.jpg"),
                    characteristics=[ImageCharacteristic.ARTISTIC],
                    dimensions=ImageDimensions.from_dimensions(1920, 1080),
                    file_size_bytes=2048000,
                )
            )
        elif "map" in pattern.lower():
            sample_images.append(
                ImageMetadata(
                    path=f"location_map_{pattern}",
                    local_path=Path(f"/placeholder/location_map_{pattern}.jpg"),
                    characteristics=[ImageCharacteristic.INFORMATIONAL],
                    dimensions=ImageDimensions.from_dimensions(1600, 1200),
                    file_size_bytes=1536000,
                )
            )

        return sample_images

    def get_integration_statistics(self) -> dict[str, Any]:
        """Get statistics about adventure image integration.

        Returns:
            Dictionary containing integration statistics

        """
        return {
            "config": self.config.model_dump(),
            "capabilities": [
                "chapter_openers",
                "location_maps",
                "npc_portraits",
                "atmospheric_scenes",
                "decorative_elements",
                "gallery_collections",
            ],
        }

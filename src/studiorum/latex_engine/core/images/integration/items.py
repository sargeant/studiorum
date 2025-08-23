"""Item-specific image integration for magic item collections.

This module provides intelligent image integration capabilities specifically
tailored for magic items and equipment collections, supporting both individual
item illustrations and comparative collections with grid layouts.
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
    ImageCharacteristic,
    ImageMetadata,
    OptimizationTarget,
)
from studiorum.renderers.core.interfaces import RenderingContext

if TYPE_CHECKING:
    from ..enhanced_image_placer import EnhancedImagePlacer
    from ..gallery_processor import GalleryProcessor
    from ..image_processor import ImageProcessor

logger = get_logger(__name__)


class ItemIntegrationConfig(BaseModel):
    """Configuration for item image integration."""

    enable_item_illustrations: bool = Field(
        default=True, description="Enable individual item illustrations"
    )
    enable_collection_galleries: bool = Field(
        default=True, description="Enable item collection gallery layouts"
    )
    enable_comparison_views: bool = Field(
        default=True, description="Enable side-by-side item comparisons"
    )
    enable_category_grouping: bool = Field(
        default=True, description="Enable grouping by item category"
    )
    max_items_per_gallery: int = Field(
        default=6, ge=2, le=12, description="Maximum items per gallery"
    )
    preferred_gallery_layout: str = Field(
        default="grid", description="Preferred layout for item galleries"
    )
    item_image_max_width: str = Field(
        default="0.3\\textwidth", description="Maximum width for individual items"
    )
    collection_columns: int = Field(
        default=3, ge=2, le=4, description="Columns for collection galleries"
    )
    enable_rarity_sizing: bool = Field(
        default=True, description="Size items by rarity (legendary items larger)"
    )


class ItemImageMetadata(BaseModel):
    """Metadata for item-specific images."""

    item_name: str
    item_type: str | None = None
    rarity: str | None = None
    category: str | None = None
    subcategory: str | None = None
    image_type: str = Field(default="illustration")  # illustration, variant, collection
    is_magical: bool = Field(default=False)
    collection_context: str | None = None
    confidence_score: float = Field(default=0.5, ge=0.0, le=1.0)
    source_context: dict[str, Any] = Field(default_factory=dict)


class ItemImageResult(BaseModel):
    """Result of item image integration."""

    latex_command: str
    items_processed: int
    layout_used: str
    integration_metadata: dict[str, Any] = Field(default_factory=dict)


class ItemImageIntegration:
    """Intelligent image integration for magic items and equipment collections.

    This class provides sophisticated image discovery, categorization, and
    integration specifically designed for D&D 5e magic items and equipment,
    supporting both individual illustrations and collection galleries.
    """

    def __init__(
        self,
        config: ItemIntegrationConfig | None = None,
        image_processor: ImageProcessor | None = None,
        gallery_processor: GalleryProcessor | None = None,
        enhanced_placer: EnhancedImagePlacer | None = None,
    ) -> None:
        """Initialize the item image integration.

        Args:
            config: Integration configuration
            image_processor: Image processor for handling individual images
            gallery_processor: Gallery processor for collection layouts
            enhanced_placer: Enhanced image placer for intelligent placement
        """
        self.config = config or ItemIntegrationConfig()
        self._image_processor = image_processor
        self._gallery_processor = gallery_processor
        self._enhanced_placer = enhanced_placer

        logger.debug("Initialized ItemImageIntegration")

    async def integrate_item_collection(
        self,
        items_data: list[dict[str, Any]],
        context: RenderingContext,
        collection_metadata: dict[str, Any] | None = None,
    ) -> Result[ItemImageResult, str]:
        """Integrate images for a collection of magic items.

        Args:
            items_data: List of item information dictionaries
            context: Current rendering context
            collection_metadata: Additional metadata about the collection

        Returns:
            Result containing integrated LaTeX or error message
        """
        try:
            collection_name = (
                collection_metadata.get("name", "Item Collection")
                if collection_metadata
                else "Item Collection"
            )
            logger.info(
                f"Integrating images for item collection: {collection_name} ({len(items_data)} items)"
            )

            # Discover and categorize item images
            item_images = []
            for item_data in items_data:
                discovery_result = await self._discover_item_images(item_data, context)
                if discovery_result.is_success():
                    images = discovery_result.unwrap()
                    item_images.extend(images)

            if not item_images:
                logger.debug(f"No images found for item collection: {collection_name}")
                return Success(
                    ItemImageResult(
                        latex_command="% No item images available",
                        items_processed=0,
                        layout_used="none",
                        integration_metadata={"collection_name": collection_name},
                    )
                )

            # Group items by category if enabled
            if self.config.enable_category_grouping:
                grouped_result = await self._create_categorized_galleries(
                    item_images, items_data, context, collection_metadata
                )
            else:
                grouped_result = await self._create_unified_gallery(
                    item_images, items_data, context, collection_metadata
                )

            if grouped_result.is_error():
                return Error("Failed to create item gallery")

            latex_command = grouped_result.unwrap()

            result = ItemImageResult(
                latex_command=latex_command,
                items_processed=len(
                    [img for img in item_images if img.get("processed", False)]
                ),
                layout_used="categorized"
                if self.config.enable_category_grouping
                else "unified",
                integration_metadata={
                    "collection_name": collection_name,
                    "total_items": len(items_data),
                    "total_images": len(item_images),
                    "categories": self._extract_categories(item_images),
                },
            )

            logger.info(
                f"Successfully integrated item collection {collection_name} "
                f"with {len(item_images)} images"
            )

            return Success(result)

        except Exception as e:
            logger.error(f"Item collection integration failed: {str(e)}")
            return Error(f"Integration failed: {str(e)}")

    async def integrate_single_item(
        self,
        item_data: dict[str, Any],
        context: RenderingContext,
        placement_hint: str | None = None,
    ) -> Result[ItemImageResult, str]:
        """Integrate images for a single magic item.

        Args:
            item_data: Item information dictionary
            context: Current rendering context
            placement_hint: Optional placement hint for the image

        Returns:
            Result containing integrated LaTeX or error message
        """
        try:
            item_name = item_data.get("name", "Unknown Item")
            logger.info(f"Integrating images for item: {item_name}")

            # Discover item images
            discovery_result = await self._discover_item_images(item_data, context)
            if isinstance(discovery_result, Error):
                return Error(f"Image discovery failed: {discovery_result.error}")

            available_images = discovery_result.unwrap()

            if not available_images:
                logger.debug(f"No images found for item: {item_name}")
                return Success(
                    ItemImageResult(
                        latex_command="% No item images available",
                        items_processed=0,
                        layout_used="none",
                        integration_metadata={"item_name": item_name},
                    )
                )

            # Select best image
            selected_image = self._select_optimal_item_image(
                available_images, item_data, context
            )

            # Generate LaTeX
            latex_result = await self._generate_single_item_latex(
                selected_image, item_data, context, placement_hint
            )

            if latex_result.is_error():
                return Error("Failed to generate item LaTeX")

            latex_command = latex_result.unwrap()

            result = ItemImageResult(
                latex_command=latex_command,
                items_processed=1,
                layout_used="single",
                integration_metadata={
                    "item_name": item_name,
                    "image_type": selected_image.get("type", "illustration"),
                    "rarity": item_data.get("rarity"),
                },
            )

            logger.info(f"Successfully integrated image for item: {item_name}")

            return Success(result)

        except Exception as e:
            logger.error(f"Single item integration failed: {str(e)}")
            return Error(f"Integration failed: {str(e)}")

    async def _discover_item_images(
        self, item_data: dict[str, Any], context: RenderingContext
    ) -> Result[list[dict[str, Any]], str]:
        """Discover available images for an item."""
        try:
            item_name = item_data.get("name", "")
            item_type = item_data.get("type", "")
            rarity = item_data.get("rarity", "")

            # Build search terms
            search_terms = [item_name.lower()]
            if item_type:
                search_terms.append(item_type.lower())

            # For now, simulate item image discovery
            # In a real implementation, this would query:
            # - ImageSourceRegistry
            # - Item art databases
            # - Equipment illustration collections
            # - User-provided mappings

            discovered_images = []

            # Simulate discovering item illustration
            if self.config.enable_item_illustrations:
                base_illustration = {
                    "href": {
                        "type": "external",
                        "path": f"items/{item_name.lower().replace(' ', '_')}_illustration.webp",
                    },
                    "title": f"{item_name}",
                    "type": "illustration",
                    "confidence": 0.7,
                    "altText": f"Illustration of {item_name}",
                    "item_metadata": ItemImageMetadata(
                        item_name=item_name,
                        item_type=item_type,
                        rarity=rarity,
                        category=self._categorize_item(item_data),
                        is_magical=rarity not in ["", "common", "mundane"],
                        image_type="illustration",
                        confidence_score=0.7,
                        source_context=item_data,
                    ).model_dump(),
                }
                discovered_images.append(base_illustration)

            # Simulate discovering variants for valuable items
            if rarity in ["rare", "very rare", "legendary", "artifact"]:
                variant_image = {
                    "href": {
                        "type": "external",
                        "path": f"items/{item_name.lower().replace(' ', '_')}_variant.webp",
                    },
                    "title": f"{item_name} (Variant)",
                    "type": "variant",
                    "confidence": 0.5,
                    "altText": f"Alternative view of {item_name}",
                    "item_metadata": ItemImageMetadata(
                        item_name=item_name,
                        item_type=item_type,
                        rarity=rarity,
                        category=self._categorize_item(item_data),
                        is_magical=True,
                        image_type="variant",
                        confidence_score=0.5,
                        source_context=item_data,
                    ).model_dump(),
                }
                discovered_images.append(variant_image)

            logger.debug(
                f"Discovered {len(discovered_images)} candidate images for {item_name}"
            )
            return Success(discovered_images)

        except Exception as e:
            return Error(f"Item image discovery failed: {str(e)}")

    def _categorize_item(self, item_data: dict[str, Any]) -> str:
        """Categorize item based on its properties."""
        item_type = item_data.get("type", "").lower()

        # Map 5e item types to categories
        category_mapping = {
            "weapon": "weapons",
            "armor": "armor",
            "shield": "armor",
            "ring": "jewelry",
            "amulet": "jewelry",
            "necklace": "jewelry",
            "wand": "magical_implements",
            "staff": "magical_implements",
            "rod": "magical_implements",
            "potion": "consumables",
            "scroll": "consumables",
            "ammunition": "consumables",
            "adventuring gear": "equipment",
            "tool": "equipment",
            "instrument": "equipment",
            "mount": "creatures",
            "vehicle": "vehicles",
        }

        for item_keyword, category in category_mapping.items():
            if item_keyword in item_type:
                return category

        # Check if it's wondrous
        if "wondrous" in item_type:
            return "wondrous_items"

        return "miscellaneous"

    def _select_optimal_item_image(
        self,
        available_images: list[dict[str, Any]],
        item_data: dict[str, Any],
        context: RenderingContext,
    ) -> dict[str, Any]:
        """Select the best image for a single item."""
        if not available_images:
            return {}

        # Prefer illustrations over variants
        illustrations = [
            img for img in available_images if img.get("type") == "illustration"
        ]
        if illustrations:
            return max(illustrations, key=lambda x: x.get("confidence", 0))

        # Fallback to highest confidence image
        return max(available_images, key=lambda x: x.get("confidence", 0))

    async def _create_categorized_galleries(
        self,
        item_images: list[dict[str, Any]],
        items_data: list[dict[str, Any]],
        context: RenderingContext,
        collection_metadata: dict[str, Any] | None,
    ) -> Result[str, str]:
        """Create galleries organized by item category."""
        try:
            # Group images by category
            categories: dict[str, list[dict[str, Any]]] = {}
            for image in item_images:
                metadata = image.get("item_metadata", {})
                category = metadata.get("category", "miscellaneous")
                if category not in categories:
                    categories[category] = []
                categories[category].append(image)

            latex_parts = []

            # Generate gallery for each category
            for category, images in categories.items():
                if not images:
                    continue

                # Limit images per category
                selected_images = images[: self.config.max_items_per_gallery]

                # Create gallery entry
                gallery_entry = {
                    "type": "gallery",
                    "images": selected_images,
                    "layout": self.config.preferred_gallery_layout,
                    "columns": self.config.collection_columns,
                    "title": f"{category.replace('_', ' ').title()} Items",
                    "caption": f"Collection of {category.replace('_', ' ')} items",
                }

                if self._gallery_processor:
                    result = self._gallery_processor.process_gallery(
                        gallery_entry, context
                    )
                    if result.is_success():
                        processed_gallery = result.unwrap()
                        latex_parts.append(processed_gallery.latex_command)
                        continue

                # Fallback to basic gallery layout
                basic_gallery = self._create_basic_item_gallery(
                    selected_images, category, context
                )
                latex_parts.append(basic_gallery)

            return Success("\n\n".join(latex_parts))

        except Exception as e:
            return Error(f"Categorized gallery creation failed: {str(e)}")

    async def _create_unified_gallery(
        self,
        item_images: list[dict[str, Any]],
        items_data: list[dict[str, Any]],
        context: RenderingContext,
        collection_metadata: dict[str, Any] | None,
    ) -> Result[str, str]:
        """Create a single unified gallery for all items."""
        try:
            # Select best images up to limit
            selected_images = item_images[: self.config.max_items_per_gallery]

            collection_name = (
                collection_metadata.get("name", "Item Collection")
                if collection_metadata
                else "Item Collection"
            )

            gallery_entry = {
                "type": "gallery",
                "images": selected_images,
                "layout": self.config.preferred_gallery_layout,
                "columns": self.config.collection_columns,
                "title": collection_name,
                "caption": "Collection of magic items and equipment",
            }

            if self._gallery_processor:
                result = self._gallery_processor.process_gallery(gallery_entry, context)
                if result.is_success():
                    processed_gallery = result.unwrap()
                    return Success(processed_gallery.latex_command)

            # Fallback to basic gallery
            basic_gallery = self._create_basic_item_gallery(
                selected_images, collection_name, context
            )
            return Success(basic_gallery)

        except Exception as e:
            return Error(f"Unified gallery creation failed: {str(e)}")

    async def _generate_single_item_latex(
        self,
        image: dict[str, Any],
        item_data: dict[str, Any],
        context: RenderingContext,
        placement_hint: str | None,
    ) -> Result[str, str]:
        """Generate LaTeX for a single item image."""
        try:
            if not image:
                return Success("% No item image available")

            # Create content context for item
            content_context = self._create_item_context(
                item_data, image, placement_hint
            )

            if self._enhanced_placer:
                # Use enhanced placement
                result = await self._place_image_with_enhancement(
                    image, content_context, context
                )
                if result.is_success():
                    return result

            # Fallback to basic placement
            basic_latex = self._create_basic_item_latex(image, item_data)
            return Success(basic_latex)

        except Exception as e:
            return Error(f"Single item LaTeX generation failed: {str(e)}")

    def _create_item_context(
        self,
        item_data: dict[str, Any],
        image: dict[str, Any],
        placement_hint: str | None,
    ) -> dict[str, Any]:
        """Create content context for item content."""
        return {
            "type": "item_collection",
            "content_type": ContentType.ITEM_COLLECTION,
            "item_name": item_data.get("name"),
            "item_type": item_data.get("type"),
            "rarity": item_data.get("rarity"),
            "image_type": image.get("type", "illustration"),
            "section_title": f"{item_data.get('name', 'Item')} Description",
            "surrounding_text": "item description",
            "word_count": 300,  # Typical item description length
            "text_density": 0.7,
            "has_other_images": False,
            "reading_flow_position": placement_hint or "inline",
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

            # Convert image path (placeholder for real implementation)
            image_path = Path("placeholder.png")

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

    def _create_basic_item_latex(
        self, image: dict[str, Any], item_data: dict[str, Any]
    ) -> str:
        """Create basic LaTeX for item images as fallback."""
        href = image.get("href", {})
        title = image.get("title", "")

        # Extract image path
        if isinstance(href, dict):
            image_path = href.get("path", href.get("url", "placeholder.png"))
        else:
            image_path = str(href)

        # Determine width based on rarity
        rarity = item_data.get("rarity", "").lower()
        if self.config.enable_rarity_sizing:
            if rarity in ["legendary", "artifact"]:
                width = "0.5\\textwidth"
            elif rarity in ["rare", "very rare"]:
                width = "0.4\\textwidth"
            else:
                width = self.config.item_image_max_width
        else:
            width = self.config.item_image_max_width

        if title:
            return (
                f"\\begin{{figure}}[htbp]\n"
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

    def _create_basic_item_gallery(
        self,
        images: list[dict[str, Any]],
        category_name: str,
        context: RenderingContext,
    ) -> str:
        """Create basic gallery layout for items."""
        if not images:
            return "% No items in gallery"

        latex_parts = ["\\begin{figure}[htbp]", "\\centering"]
        latex_parts.append(f"% {category_name}")

        columns = min(self.config.collection_columns, len(images))
        image_width = f"{0.9 / columns}\\textwidth"

        for i, image in enumerate(images):
            href = image.get("href", {})
            title = image.get("title", "")

            if isinstance(href, dict):
                image_path = href.get("path", href.get("url", "placeholder.png"))
            else:
                image_path = str(href)

            latex_parts.extend(
                [
                    f"\\begin{{subfigure}}{{{image_width}}}",
                    "    \\centering",
                    f"    \\includegraphics[width=\\textwidth]{{{image_path}}}",
                ]
            )

            if title:
                latex_parts.append(f"    \\caption{{{title}}}")

            latex_parts.append("\\end{subfigure}")

            # Add spacing
            if (i + 1) % columns == 0 and i < len(images) - 1:
                latex_parts.append("\\\\[1em]")
            elif i < len(images) - 1:
                latex_parts.append("\\hfill")

        latex_parts.extend(
            [
                f"\\caption{{{category_name}}}",
                "\\end{figure}",
            ]
        )

        return "\n".join(latex_parts)

    def _extract_categories(self, images: list[dict[str, Any]]) -> list[str]:
        """Extract unique categories from images."""
        categories = set()
        for image in images:
            metadata = image.get("item_metadata", {})
            category = metadata.get("category")
            if category:
                categories.add(category)
        return list(categories)

    def get_integration_statistics(self) -> dict[str, Any]:
        """Get statistics about integration operations."""
        return {
            "config": self.config.model_dump(),
            "has_image_processor": self._image_processor is not None,
            "has_gallery_processor": self._gallery_processor is not None,
            "has_enhanced_placer": self._enhanced_placer is not None,
        }

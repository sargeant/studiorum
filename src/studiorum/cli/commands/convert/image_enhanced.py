"""Enhanced image CLI options and processing.

This module provides enhanced image processing capabilities for the CLI,
integrating Phase 4 image services with command-line options for fine-grained
control over image processing and placement.

Created: 2025-01-23
Status: Phase 4 - Service Integration
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import typer
from rich import print as rprint

from studiorum.cli.config_factory import get_with_images_default
from studiorum.core.config.unified_config import get_app_config
from studiorum.latex_engine.core.images.placement_models import OptimizationTarget

logger = logging.getLogger(__name__)


def get_enhanced_image_options() -> dict[str, Any]:
    """Get enhanced image CLI options for conversion commands.

    Returns:
        Dictionary of enhanced image CLI options with sensible defaults
    """
    return {
        # Basic image control (backward compatible)
        "with_images": typer.Option(
            get_with_images_default(),
            "--images/--no-images",
            help="Include images in the document",
            rich_help_panel="Image Options",
        ),
        # Image quality and optimization
        "image_quality": typer.Option(
            None,
            "--image-quality",
            help="Image quality preset: digital, print, hybrid, high, low",
            rich_help_panel="Image Options",
        ),
        # Image placement strategy
        "image_placement": typer.Option(
            None,
            "--image-placement",
            help="Image placement strategy: intelligent, simple, float, inline",
            rich_help_panel="Image Options",
        ),
        # Gallery processing options
        "gallery_layout": typer.Option(
            None,
            "--gallery-layout",
            help="Gallery layout type: grid, showcase, sequential, comparison",
            rich_help_panel="Image Options",
        ),
        # Image source configuration
        "image_sources": typer.Option(
            None,
            "--image-sources",
            help="Comma-separated list of image sources to use",
            rich_help_panel="Image Options",
        ),
        # Advanced options
        "preload_images": typer.Option(
            True,
            "--preload-images/--no-preload-images",
            help="Preload images for faster processing",
            rich_help_panel="Advanced Image Options",
        ),
        "image_cache": typer.Option(
            True,
            "--image-cache/--no-image-cache",
            help="Use image caching for improved performance",
            rich_help_panel="Advanced Image Options",
        ),
        "sync_sources": typer.Option(
            False,
            "--sync-sources",
            help="Sync Git-based image sources before processing",
            rich_help_panel="Advanced Image Options",
        ),
        # Content-specific options
        "bestiary_images": typer.Option(
            True,
            "--bestiary-images/--no-bestiary-images",
            help="Include creature artwork in bestiary sections",
            rich_help_panel="Content-Specific Images",
        ),
        "item_images": typer.Option(
            True,
            "--item-images/--no-item-images",
            help="Include item illustrations",
            rich_help_panel="Content-Specific Images",
        ),
        "adventure_images": typer.Option(
            True,
            "--adventure-images/--no-adventure-images",
            help="Include adventure artwork (maps, NPCs, scenes)",
            rich_help_panel="Content-Specific Images",
        ),
        "chapter_art": typer.Option(
            True,
            "--chapter-art/--no-chapter-art",
            help="Include chapter opening artwork",
            rich_help_panel="Content-Specific Images",
        ),
    }


def apply_image_config_hierarchy(**cli_args: Any) -> dict[str, Any]:
    """Apply image configuration hierarchy: CLI args > user config > app defaults.

    Args:
        **cli_args: Command-line arguments related to image processing

    Returns:
        Dictionary with resolved image configuration
    """
    app_config = get_app_config()

    # Extract CLI values
    with_images = cli_args.get("with_images")
    image_quality = cli_args.get("image_quality")
    image_placement = cli_args.get("image_placement")
    gallery_layout = cli_args.get("gallery_layout")
    image_sources = cli_args.get("image_sources")
    preload_images = cli_args.get("preload_images")
    image_cache = cli_args.get("image_cache")
    sync_sources = cli_args.get("sync_sources")
    bestiary_images = cli_args.get("bestiary_images")
    item_images = cli_args.get("item_images")
    adventure_images = cli_args.get("adventure_images")
    chapter_art = cli_args.get("chapter_art")

    # Get app config defaults
    images_config = (
        getattr(app_config, "images", None) if hasattr(app_config, "images") else None
    )
    rendering_config = getattr(app_config.rendering, "content", None)

    # Apply hierarchy for each configuration option
    actual_config = {
        # Basic image control
        "include_images": (
            with_images
            if with_images is not None
            else getattr(rendering_config, "include_images", True)
            if rendering_config
            else True
        ),
        # Image quality/optimization
        "image_quality": (
            image_quality or getattr(rendering_config, "image_quality", "hybrid")
            if rendering_config
            else "hybrid"
        ),
        # Optimization target based on quality setting
        "optimization_target": _resolve_optimization_target(
            str(
                image_quality or getattr(rendering_config, "image_quality", "hybrid")
                if rendering_config
                else "hybrid"
            )
        ),
        # Placement strategy
        "placement_strategy": (
            image_placement
            or getattr(images_config, "placement_strategy", "intelligent")
            if images_config
            else "intelligent"
        ),
        # Gallery settings
        "gallery_layout": (
            gallery_layout or getattr(images_config, "gallery_layout", "grid")
            if images_config
            else "grid"
        ),
        # Source management
        "image_sources": (
            image_sources.split(",")
            if image_sources
            else None or getattr(images_config, "enabled_sources", None)
            if images_config
            else None
        ),
        # Performance options
        "preload_images": (
            preload_images
            if preload_images is not None
            else getattr(images_config, "preload_images", True)
            if images_config
            else True
        ),
        "use_cache": (
            image_cache
            if image_cache is not None
            else getattr(images_config, "use_cache", True)
            if images_config
            else True
        ),
        "sync_sources": (
            sync_sources
            if sync_sources is not None
            else getattr(images_config, "sync_sources", False)
            if images_config
            else False
        ),
        # Content-specific options
        "enable_bestiary_images": (
            bestiary_images
            if bestiary_images is not None
            else getattr(images_config, "bestiary_images", True)
            if images_config
            else True
        ),
        "enable_item_images": (
            item_images
            if item_images is not None
            else getattr(images_config, "item_images", True)
            if images_config
            else True
        ),
        "enable_adventure_images": (
            adventure_images
            if adventure_images is not None
            else getattr(images_config, "adventure_images", True)
            if images_config
            else True
        ),
        "enable_chapter_art": (
            chapter_art
            if chapter_art is not None
            else getattr(images_config, "chapter_art", True)
            if images_config
            else True
        ),
    }

    return actual_config


def _resolve_optimization_target(quality: str) -> OptimizationTarget:
    """Resolve image quality setting to optimization target.

    Args:
        quality: Quality setting string

    Returns:
        OptimizationTarget enum value
    """
    quality_map = {
        "digital": OptimizationTarget.DIGITAL,
        "print": OptimizationTarget.PRINT,
        "hybrid": OptimizationTarget.HYBRID,
        "high": OptimizationTarget.PRINT,  # High quality defaults to print optimization
        "low": OptimizationTarget.BANDWIDTH,  # Low quality optimizes for bandwidth
    }

    return quality_map.get(quality.lower(), OptimizationTarget.HYBRID)


class EnhancedImageProcessor:
    """Enhanced image processor for CLI operations."""

    # Type annotations for instance variables
    image_registry: Any
    enhanced_placer: Any
    adventure_integration: Any
    bestiary_integration: Any
    item_integration: Any
    gallery_processor: Any
    config: dict[str, Any]

    def __init__(self, image_config: dict[str, Any]):
        """Initialize enhanced image processor.

        Args:
            image_config: Resolved image configuration
        """
        self.config = image_config

        # Services will be injected by the CLI command
        self.image_registry = None
        self.enhanced_placer = None
        self.adventure_integration = None
        self.bestiary_integration = None
        self.item_integration = None
        self.gallery_processor = None

    async def setup_services(self) -> None:
        """Setup image services from the service container."""
        try:
            # For now, use direct factory creation to avoid complex service container issues
            # This will be refactored once service container integration is fully stable
            from studiorum.core.services.image_factories.image_factory import (
                ImageServiceFactory,
            )

            factory = ImageServiceFactory()

            # Create services directly using factory
            self.image_registry = factory.create_source_registry()
            self.enhanced_placer = factory.create_enhanced_placer()
            self.gallery_processor = factory.create_gallery_processor()

            # Integration services
            self.bestiary_integration = factory.create_bestiary_integration()
            self.item_integration = factory.create_item_integration()
            self.adventure_integration = factory.create_adventure_integration()

            logger.debug("Image services setup completed using factory")

        except Exception as e:
            logger.warning(f"Failed to setup image services: {e}")
            # Graceful fallback to None services
            self.image_registry = None
            self.enhanced_placer = None
            self.gallery_processor = None
            self.bestiary_integration = None
            self.item_integration = None
            self.adventure_integration = None

    async def preprocess_content(self, content_items: list[Any]) -> None:
        """Preprocess content for enhanced image processing.

        Args:
            content_items: List of content items to preprocess
        """
        if not self.config.get("include_images", True):
            logger.debug("Images disabled, skipping preprocessing")
            return

        try:
            if self.config.get("sync_sources", False) and self.image_registry:
                rprint("[cyan]Syncing image sources...[/cyan]")
                await self.image_registry.sync_sources()

            if self.config.get("preload_images", True) and self.adventure_integration:
                rprint("[cyan]Preloading images...[/cyan]")
                # Preload images for adventure content
                for item in content_items:
                    if (
                        hasattr(item, "content_type")
                        and item.content_type == "adventure"
                    ):
                        await self._preload_adventure_images(item)

            logger.debug("Content preprocessing completed")

        except Exception as e:
            logger.warning(f"Image preprocessing failed: {e}")

    async def _preload_adventure_images(self, adventure_item: Any) -> None:
        """Preload images for adventure content.

        Args:
            adventure_item: Adventure content item
        """
        if not self.adventure_integration:
            return

        try:
            # Discover and preload adventure images
            adventure_metadata = getattr(adventure_item, "metadata", {})
            await self.adventure_integration.discover_adventure_images(
                adventure_metadata
            )

        except Exception as e:
            logger.warning(f"Failed to preload adventure images: {e}")

    def get_rendering_context_metadata(self) -> dict[str, Any]:
        """Get metadata for rendering context with enhanced image configuration.

        Returns:
            Dictionary with image-related metadata for rendering context
        """
        return {
            "enhanced_images_enabled": self.config.get("include_images", True),
            "image_optimization_target": self.config.get(
                "optimization_target", OptimizationTarget.HYBRID
            ),
            "image_placement_strategy": self.config.get(
                "placement_strategy", "intelligent"
            ),
            "gallery_layout_type": self.config.get("gallery_layout", "grid"),
            "bestiary_images_enabled": self.config.get("enable_bestiary_images", True),
            "item_images_enabled": self.config.get("enable_item_images", True),
            "adventure_images_enabled": self.config.get(
                "enable_adventure_images", True
            ),
            "chapter_art_enabled": self.config.get("enable_chapter_art", True),
            "image_caching_enabled": self.config.get("use_cache", True),
            "image_processor": self,  # Reference to processor for services
        }


def create_enhanced_image_processor(cli_args: dict[str, Any]) -> EnhancedImageProcessor:
    """Create enhanced image processor from CLI arguments.

    Args:
        cli_args: Command-line arguments

    Returns:
        Configured EnhancedImageProcessor instance
    """
    image_config = apply_image_config_hierarchy(**cli_args)
    return EnhancedImageProcessor(image_config)


def display_image_config_summary(image_config: dict[str, Any]) -> None:
    """Display summary of resolved image configuration.

    Args:
        image_config: Resolved image configuration
    """
    if not image_config.get("include_images", True):
        rprint("[yellow]Images disabled[/yellow]")
        return

    rprint("[green]Enhanced Image Configuration:[/green]")
    rprint(f"  Quality: {image_config.get('image_quality', 'hybrid')}")
    rprint(f"  Placement: {image_config.get('placement_strategy', 'intelligent')}")
    rprint(f"  Gallery Layout: {image_config.get('gallery_layout', 'grid')}")
    rprint(f"  Preload Images: {image_config.get('preload_images', True)}")
    rprint(f"  Use Cache: {image_config.get('use_cache', True)}")

    content_types = []
    if image_config.get("enable_bestiary_images", True):
        content_types.append("bestiary")
    if image_config.get("enable_item_images", True):
        content_types.append("items")
    if image_config.get("enable_adventure_images", True):
        content_types.append("adventures")
    if image_config.get("enable_chapter_art", True):
        content_types.append("chapter art")

    if content_types:
        rprint(f"  Content Types: {', '.join(content_types)}")

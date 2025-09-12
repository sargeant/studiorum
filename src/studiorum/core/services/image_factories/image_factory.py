"""Image service factory implementation.

This module provides factory functions for creating all image-related services
with proper configuration and dependencies. These factories are used by the
ServiceContainer for dependency injection.

Created: 2025-01-23
Status: Phase 4 - Service Integration
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from studiorum.core.assets.image_sources import ImageSourceRegistry
from studiorum.core.config.unified_config import get_app_config
from studiorum.latex_engine.core.images import (
    create_adventure_integration,
    create_enhanced_placer,
    create_image_registry,
    create_layout_analyzer,
    create_output_optimizer,
)
from studiorum.latex_engine.core.images.enhanced_image_placer import EnhancedImagePlacer
from studiorum.latex_engine.core.images.gallery_processor import GalleryProcessor
from studiorum.latex_engine.core.images.integration.adventure import (
    AdventureImageIntegration,
)
from studiorum.latex_engine.core.images.integration.bestiary import (
    BestiaryImageIntegration,
)
from studiorum.latex_engine.core.images.integration.items import ItemImageIntegration
from studiorum.latex_engine.core.images.layout_analyzer import LayoutAnalyzer
from studiorum.latex_engine.core.images.output_optimizer import OutputOptimizer
from studiorum.latex_engine.core.images.placement_models import OptimizationTarget
from studiorum.latex_engine.core.images.registry.adventure_registry import (
    AdventureImageRegistry,
)

if TYPE_CHECKING:
    from studiorum.core.services.container import ServiceContainer

logger = logging.getLogger(__name__)


class ImageServiceFactory:
    """Factory for creating image-related services with proper configuration."""

    def __init__(self, container: ServiceContainer | None = None):
        """Initialize factory with optional container reference.

        Args:
            container: Service container for dependency resolution
        """
        self._container = container
        self._config = get_app_config()

    def create_source_registry(self) -> ImageSourceRegistry:
        """Create image source registry with configured sources.

        Returns:
            Configured ImageSourceRegistry instance
        """
        logger.debug("Creating ImageSourceRegistry")

        registry = ImageSourceRegistry()

        # Add configured image sources (if any)
        if hasattr(self._config, "image") and hasattr(self._config.image, "sources"):
            for _ in self._config.image.sources:
                # Sources are already handled by consumers of the registry in this phase
                pass

        return registry

    def create_enhanced_placer(
        self, source_registry: ImageSourceRegistry | None = None
    ) -> EnhancedImagePlacer:
        """Create enhanced image placer with intelligent features.

        Args:
            source_registry: Optional image source registry dependency

        Returns:
            Configured EnhancedImagePlacer instance
        """
        logger.debug("Creating EnhancedImagePlacer")

        # Use factory function with enhanced features enabled
        placer = create_enhanced_placer(
            config=None,  # Use defaults
            enable_all_features=True,
        )

        return placer

    def create_layout_analyzer(self) -> LayoutAnalyzer:
        """Create layout analyzer for intelligent placement.

        Returns:
            Configured LayoutAnalyzer instance
        """
        logger.debug("Creating LayoutAnalyzer")
        return create_layout_analyzer()

    def create_output_optimizer(self) -> OutputOptimizer:
        """Create output optimizer with target profiles.

        Returns:
            Configured OutputOptimizer instance
        """
        logger.debug("Creating OutputOptimizer")

        # TODO: Add target parameter support to create_output_optimizer factory
        # For now, use default cache configuration
        return create_output_optimizer(cache_dir=None)

    def create_gallery_processor(
        self,
        image_placer: EnhancedImagePlacer | None = None,
        source_registry: ImageSourceRegistry | None = None,
    ) -> GalleryProcessor:
        """Create gallery processor for multi-image layouts.

        Args:
            image_placer: Optional enhanced image placer dependency
            source_registry: Optional image source registry dependency

        Returns:
            Configured GalleryProcessor instance
        """
        logger.debug("Creating GalleryProcessor")

        # Create with dependencies or defaults
        if image_placer is None:
            image_placer = self.create_enhanced_placer(source_registry)

        return GalleryProcessor(
            config=None,  # Use default config
            image_processor=None,  # Will be created as needed
        )

    def create_bestiary_integration(
        self,
        source_registry: ImageSourceRegistry | None = None,
        image_placer: EnhancedImagePlacer | None = None,
    ) -> BestiaryImageIntegration:
        """Create bestiary image integration service.

        Args:
            source_registry: Optional image source registry dependency
            image_placer: Optional enhanced image placer dependency

        Returns:
            Configured BestiaryImageIntegration instance
        """
        logger.debug("Creating BestiaryImageIntegration")

        return BestiaryImageIntegration(
            config=None,  # Use default config
            image_processor=None,  # Will be created as needed
            enhanced_placer=image_placer
            or self.create_enhanced_placer(source_registry),
        )

    def create_item_integration(
        self,
        source_registry: ImageSourceRegistry | None = None,
        image_placer: EnhancedImagePlacer | None = None,
    ) -> ItemImageIntegration:
        """Create item image integration service.

        Args:
            source_registry: Optional image source registry dependency
            image_placer: Optional enhanced image placer dependency

        Returns:
            Configured ItemImageIntegration instance
        """
        logger.debug("Creating ItemImageIntegration")

        return ItemImageIntegration(
            config=None,  # Use default config
            image_processor=None,  # Will be created as needed
            gallery_processor=None,  # Will be created as needed
            enhanced_placer=image_placer
            or self.create_enhanced_placer(source_registry),
        )

    def create_adventure_integration(
        self,
        source_registry: ImageSourceRegistry | None = None,
        image_placer: EnhancedImagePlacer | None = None,
        gallery_processor: GalleryProcessor | None = None,
    ) -> AdventureImageIntegration:
        """Create adventure image integration service.

        Args:
            source_registry: Optional image source registry dependency
            image_placer: Optional enhanced image placer dependency
            gallery_processor: Optional gallery processor dependency

        Returns:
            Configured AdventureImageIntegration instance
        """
        logger.debug("Creating AdventureImageIntegration")

        # Use factory function with correct parameters
        return create_adventure_integration(
            image_processor=None,  # Will use default
            enhanced_placer=image_placer
            or self.create_enhanced_placer(source_registry),
            config=None,  # Use default config
        )

    def create_adventure_registry(
        self,
        source_registry: ImageSourceRegistry | None = None,
        output_optimizer: OutputOptimizer | None = None,
    ) -> AdventureImageRegistry:
        """Create adventure image registry for batch processing.

        Args:
            source_registry: Optional image source registry dependency
            output_optimizer: Optional output optimizer dependency

        Returns:
            Configured AdventureImageRegistry instance
        """
        logger.debug("Creating AdventureImageRegistry")

        # Use factory function with correct parameters
        return create_image_registry(
            image_processor=None,  # Will use default
            storage_path=None,  # Will use default path
        )


# Factory functions for container registration


async def create_image_source_registry_service(
    container: ServiceContainer,
) -> ImageSourceRegistry:
    """Factory function for ImageSourceRegistry service.

    Args:
        container: Service container for dependency resolution

    Returns:
        Configured ImageSourceRegistry instance
    """
    factory = ImageServiceFactory(container)
    return factory.create_source_registry()


async def create_enhanced_image_placer_service(
    container: ServiceContainer,
) -> EnhancedImagePlacer:
    """Factory function for EnhancedImagePlacer service.

    Args:
        container: Service container for dependency resolution

    Returns:
        Configured EnhancedImagePlacer instance
    """
    factory = ImageServiceFactory(container)

    # Create enhanced placer directly without container dependency for now
    # This avoids protocol type issues while service container matures
    return factory.create_enhanced_placer(None)


async def create_layout_analyzer_service(
    container: ServiceContainer,
) -> LayoutAnalyzer:
    """Factory function for LayoutAnalyzer service.

    Args:
        container: Service container for dependency resolution

    Returns:
        Configured LayoutAnalyzer instance
    """
    factory = ImageServiceFactory(container)
    return factory.create_layout_analyzer()


async def create_output_optimizer_service(
    container: ServiceContainer,
) -> OutputOptimizer:
    """Factory function for OutputOptimizer service.

    Args:
        container: Service container for dependency resolution

    Returns:
        Configured OutputOptimizer instance
    """
    factory = ImageServiceFactory(container)
    return factory.create_output_optimizer()


async def create_gallery_processor_service(
    container: ServiceContainer,
) -> GalleryProcessor:
    """Factory function for GalleryProcessor service.

    Args:
        container: Service container for dependency resolution

    Returns:
        Configured GalleryProcessor instance
    """
    factory = ImageServiceFactory(container)

    # Create gallery processor directly without container dependencies for now
    return factory.create_gallery_processor(None, None)


async def create_bestiary_integration_service(
    container: ServiceContainer,
) -> BestiaryImageIntegration:
    """Factory function for BestiaryImageIntegration service.

    Args:
        container: Service container for dependency resolution

    Returns:
        Configured BestiaryImageIntegration instance
    """
    factory = ImageServiceFactory(container)

    # Create bestiary integration directly without container dependencies for now
    return factory.create_bestiary_integration(None, None)


async def create_item_integration_service(
    container: ServiceContainer,
) -> ItemImageIntegration:
    """Factory function for ItemImageIntegration service.

    Args:
        container: Service container for dependency resolution

    Returns:
        Configured ItemImageIntegration instance
    """
    factory = ImageServiceFactory(container)

    # Create item integration directly without container dependencies for now
    return factory.create_item_integration(None, None)


async def create_adventure_integration_service(
    container: ServiceContainer,
) -> AdventureImageIntegration:
    """Factory function for AdventureImageIntegration service.

    Args:
        container: Service container for dependency resolution

    Returns:
        Configured AdventureImageIntegration instance
    """
    factory = ImageServiceFactory(container)

    # Create adventure integration directly without container dependencies for now
    return factory.create_adventure_integration(None, None, None)


async def create_adventure_registry_service(
    container: ServiceContainer,
) -> AdventureImageRegistry:
    """Factory function for AdventureImageRegistry service.

    Args:
        container: Service container for dependency resolution

    Returns:
        Configured AdventureImageRegistry instance
    """
    factory = ImageServiceFactory(container)

    # Create adventure registry directly without container dependencies for now
    return factory.create_adventure_registry(None, None)

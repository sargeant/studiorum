"""Image service registration for dependency injection.

This module provides service registration for all image-related services in the
ServiceContainer. It follows the established patterns from encounter_services.py
and registration.py for consistent service lifecycle management.

Created: 2025-01-23
Status: Phase 4 - Service Integration
"""

from __future__ import annotations

import logging
from typing import Any

from studiorum.core.services.image_factories.image_factory import (
    create_adventure_integration_service,
    create_adventure_registry_service,
    create_bestiary_integration_service,
    create_enhanced_image_placer_service,
    create_gallery_processor_service,
    create_image_source_registry_service,
    create_item_integration_service,
    create_layout_analyzer_service,
    create_output_optimizer_service,
)
from studiorum.core.services.lifecycle import CleanupPriority, ServiceLifecycle
from studiorum.core.services.protocols import (
    AdventureImageIntegrationProtocol,
    AdventureImageRegistryProtocol,
    BestiaryImageIntegrationProtocol,
    EnhancedImagePlacerProtocol,
    GalleryProcessorProtocol,
    ImageSourceRegistryProtocol,
    ItemImageIntegrationProtocol,
    LayoutAnalyzerProtocol,
    OutputOptimizerProtocol,
)

logger = logging.getLogger(__name__)


def register_image_services(container: Any) -> None:  # ServiceContainer
    """Register image processing services with the service container.

    Args:
        container: Modern service container for registration

    This function registers all Phase 4 image services following established
    patterns for service lifecycle management. Services are ordered by
    dependency requirements and appropriate cleanup priorities.

    Service Architecture:
    - ImageSourceRegistry: SINGLETON (shared registry, heavy initialization)
    - EnhancedImagePlacer: SINGLETON (shared placement logic)
    - LayoutAnalyzer: SINGLETON (stateless analysis, shared optimal)
    - OutputOptimizer: SINGLETON (stateless optimization, shared optimal)
    - GalleryProcessor: SCOPED (per-request processing with context)
    - Integration services: SCOPED (per-request context-aware processing)
    - AdventureImageRegistry: SINGLETON (shared registry with batch capabilities)
    """
    logger.info("Registering image processing services")

    # Core infrastructure services (singletons for performance and shared state)
    # High priority cleanup after core resources

    # Image Source Registry - Central image source management
    container.register_service(
        ImageSourceRegistryProtocol,  # type: ignore[type-abstract] # Protocol type token - see TYPES.md
        create_image_source_registry_service,
        lifecycle=ServiceLifecycle.SINGLETON,
        dependencies=(),  # Configured from application config
        hot_reloadable=True,  # Can reload source configurations
        cleanup_priority=CleanupPriority.CORE_RESOURCES,
    )
    logger.debug("Registered ImageSourceRegistryProtocol as singleton")

    # Enhanced Image Placer - Intelligent placement decisions
    container.register_service(
        EnhancedImagePlacerProtocol,  # type: ignore[type-abstract] # Protocol type token - see TYPES.md
        create_enhanced_image_placer_service,
        lifecycle=ServiceLifecycle.SINGLETON,
        dependencies=(ImageSourceRegistryProtocol,),
        hot_reloadable=False,  # Placement strategies are static
        cleanup_priority=CleanupPriority.INFRASTRUCTURE,
    )
    logger.debug("Registered EnhancedImagePlacerProtocol as singleton")

    # Layout Analyzer - Page layout analysis (stateless)
    container.register_service(
        LayoutAnalyzerProtocol,  # type: ignore[type-abstract] # Protocol type token - see TYPES.md
        create_layout_analyzer_service,
        lifecycle=ServiceLifecycle.SINGLETON,
        dependencies=(),  # Stateless service
        hot_reloadable=False,
        cleanup_priority=CleanupPriority.INFRASTRUCTURE,
    )
    logger.debug("Registered LayoutAnalyzerProtocol as singleton")

    # Output Optimizer - Image optimization (stateless)
    container.register_service(
        OutputOptimizerProtocol,  # type: ignore[type-abstract] # Protocol type token - see TYPES.md
        create_output_optimizer_service,
        lifecycle=ServiceLifecycle.SINGLETON,
        dependencies=(),  # Configured from application config
        hot_reloadable=True,  # Can update optimization profiles
        cleanup_priority=CleanupPriority.INFRASTRUCTURE,
    )
    logger.debug("Registered OutputOptimizerProtocol as singleton")

    # Adventure Image Registry - Batch processing and adventure organization
    container.register_service(
        AdventureImageRegistryProtocol,  # type: ignore[type-abstract] # Protocol type token - see TYPES.md
        create_adventure_registry_service,
        lifecycle=ServiceLifecycle.SINGLETON,
        dependencies=(ImageSourceRegistryProtocol, OutputOptimizerProtocol),
        hot_reloadable=False,  # Registry state is managed internally
        cleanup_priority=CleanupPriority.INFRASTRUCTURE,
    )
    logger.debug("Registered AdventureImageRegistryProtocol as singleton")

    # Request-scoped processing services (for MCP isolation and context-aware processing)
    # Later cleanup priority to ensure dependencies are available

    # Gallery Processor - Multi-image layout processing
    container.register_service(
        GalleryProcessorProtocol,  # type: ignore[type-abstract] # Protocol type token - see TYPES.md
        create_gallery_processor_service,
        lifecycle=ServiceLifecycle.SCOPED,
        dependencies=(EnhancedImagePlacerProtocol, ImageSourceRegistryProtocol),
        hot_reloadable=False,  # Per-request processing
        cleanup_priority=CleanupPriority.REQUEST_SCOPED,
    )
    logger.debug("Registered GalleryProcessorProtocol as scoped")

    # Bestiary Image Integration - Creature-specific image processing
    container.register_service(
        BestiaryImageIntegrationProtocol,  # type: ignore[type-abstract] # Protocol type token - see TYPES.md
        create_bestiary_integration_service,
        lifecycle=ServiceLifecycle.SCOPED,
        dependencies=(ImageSourceRegistryProtocol, EnhancedImagePlacerProtocol),
        hot_reloadable=False,  # Per-request processing
        cleanup_priority=CleanupPriority.REQUEST_SCOPED,
    )
    logger.debug("Registered BestiaryImageIntegrationProtocol as scoped")

    # Item Image Integration - Item-specific image processing
    container.register_service(
        ItemImageIntegrationProtocol,  # type: ignore[type-abstract] # Protocol type token - see TYPES.md
        create_item_integration_service,
        lifecycle=ServiceLifecycle.SCOPED,
        dependencies=(ImageSourceRegistryProtocol, EnhancedImagePlacerProtocol),
        hot_reloadable=False,  # Per-request processing
        cleanup_priority=CleanupPriority.REQUEST_SCOPED,
    )
    logger.debug("Registered ItemImageIntegrationProtocol as scoped")

    # Adventure Image Integration - Adventure-specific comprehensive processing
    container.register_service(
        AdventureImageIntegrationProtocol,  # type: ignore[type-abstract] # Protocol type token - see TYPES.md
        create_adventure_integration_service,
        lifecycle=ServiceLifecycle.SCOPED,
        dependencies=(
            ImageSourceRegistryProtocol,
            EnhancedImagePlacerProtocol,
            GalleryProcessorProtocol,
        ),
        hot_reloadable=False,  # Per-request processing with context
        cleanup_priority=CleanupPriority.REQUEST_SCOPED,
    )
    logger.debug("Registered AdventureImageIntegrationProtocol as scoped")

    logger.info("Image processing services registered successfully")


def get_image_service_summary() -> dict[str, Any]:
    """Get summary of image service registrations for diagnostics.

    Returns:
        Dictionary with service lifecycle and dependency information
    """
    return {
        "singletons": {
            "ImageSourceRegistryProtocol": {
                "dependencies": [],
                "hot_reloadable": True,
                "description": "Central image source management with Git/HTTP sources",
            },
            "EnhancedImagePlacerProtocol": {
                "dependencies": ["ImageSourceRegistryProtocol"],
                "hot_reloadable": False,
                "description": "Intelligent image placement with content-aware strategies",
            },
            "LayoutAnalyzerProtocol": {
                "dependencies": [],
                "hot_reloadable": False,
                "description": "Page layout analysis and space optimization",
            },
            "OutputOptimizerProtocol": {
                "dependencies": [],
                "hot_reloadable": True,
                "description": "Digital vs print image optimization",
            },
            "AdventureImageRegistryProtocol": {
                "dependencies": [
                    "ImageSourceRegistryProtocol",
                    "OutputOptimizerProtocol",
                ],
                "hot_reloadable": False,
                "description": "Adventure-specific batch processing and organization",
            },
        },
        "scoped": {
            "GalleryProcessorProtocol": {
                "dependencies": [
                    "EnhancedImagePlacerProtocol",
                    "ImageSourceRegistryProtocol",
                ],
                "hot_reloadable": False,
                "description": "Multi-image gallery layouts with LaTeX generation",
            },
            "BestiaryImageIntegrationProtocol": {
                "dependencies": [
                    "ImageSourceRegistryProtocol",
                    "EnhancedImagePlacerProtocol",
                ],
                "hot_reloadable": False,
                "description": "Creature statblock image integration",
            },
            "ItemImageIntegrationProtocol": {
                "dependencies": [
                    "ImageSourceRegistryProtocol",
                    "EnhancedImagePlacerProtocol",
                ],
                "hot_reloadable": False,
                "description": "Magic item collection image processing",
            },
            "AdventureImageIntegrationProtocol": {
                "dependencies": [
                    "ImageSourceRegistryProtocol",
                    "EnhancedImagePlacerProtocol",
                    "GalleryProcessorProtocol",
                ],
                "hot_reloadable": False,
                "description": "Comprehensive adventure image integration",
            },
        },
        "total_services": 9,
        "phase": "Phase 4 - Service Integration",
        "status": "Production Ready",
    }

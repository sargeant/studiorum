"""Content type registry initialization system."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def initialize_content_types() -> None:
    """Initialize the content type registry by importing all model modules and finalizing."""

    logger.info("Initializing content type registry")

    # Import all model modules to trigger decorator registration
    # Add imports as we migrate content types to use @content_type decorator
    from ..models import (
        adventures,  # Import to trigger @content_type registration
        backgrounds,  # Import to trigger @content_type registration
        books,  # Import to trigger @content_type registration
        charoption,  # Import to trigger @content_type registration
        charoptiontype,  # Import to trigger @content_type registration
        classes,  # Import to trigger @content_type registration
        creatures,  # Import to trigger @content_type registration
        cult,  # Import to trigger @content_type registration
        deities,  # Import to trigger @content_type registration
        feats,  # Import to trigger @content_type registration
        fluff,  # Import to trigger @content_type registration
        items,  # Import to trigger @content_type registration
        legendarygroup,  # Import to trigger @content_type registration
        magicvariant,  # Import to trigger @content_type registration
        optfeature,  # Import to trigger @content_type registration
        optional_features,  # Import to trigger @content_type registration
        races,  # Import to trigger @content_type registration
        rewards,  # Import to trigger @content_type registration
        rule_types,  # Import to trigger @content_type registration
        spells,  # Import to trigger @content_type registration
        subclasses,  # Import to trigger @content_type registration
        subraces,  # Import to trigger @content_type registration
        table,  # Import to trigger @content_type registration
        variantrule,  # Import to trigger @content_type registration
        vehicles,  # Import to trigger @content_type registration
    )

    # For now, just finalize with whatever is already registered
    from .content_type_registry import get_content_type_registry

    registry = get_content_type_registry()
    registry.finalize()

    logger.info("Content type registry initialization completed")

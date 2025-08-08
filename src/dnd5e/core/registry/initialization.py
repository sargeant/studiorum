"""Content type registry initialization system."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def initialize_content_types() -> None:
    """Initialize the content type registry by importing all model modules and finalizing."""

    logger.info("Initializing content type registry")

    # Import all model modules to trigger @content_type decorator registration
    from ..models import (
        adventures,
        backgrounds,
        books,
        charoption,
        charoptiontype,
        classes,
        creatures,
        cult,
        deities,
        feats,
        fluff,
        items,
        legendarygroup,
        magicvariant,
        optfeature,
        optional_features,
        psionic,
        races,
        recipe,
        rewards,
        rule_types,
        spells,
        subclasses,
        subraces,
        table,
        trap,
        variantrule,
        vehicles,
    )

    # For now, just finalize with whatever is already registered
    from .content_type_registry import get_content_type_registry

    registry = get_content_type_registry()
    registry.finalize()

    logger.info("Content type registry initialization completed")

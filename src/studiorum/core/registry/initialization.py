"""Content type registry initialization system."""

from __future__ import annotations

from studiorum.core.logging import get_logger

logger = get_logger(__name__)


def initialize_content_types() -> None:
    """Initialize the content type registry by importing all model modules and finalizing."""

    logger.info("Initializing content type registry")

    # Import all model modules to trigger @content_type decorator registration
    from ..models import (
        adventures,
        backgrounds,
        baseitems,
        books,
        charoption,
        charoptiontype,
        classes,
        creatures,
        cults,
        decks,
        deities,
        diseases,
        facilities,
        feats,
        fluff,
        itemmastery,
        itemproperties,
        items,
        legendarygroup,
        magicvariant,
        objects,
        optional_features,
        psionic,
        races,
        recipes,
        rewards,
        rule_types,
        spells,
        subclasses,
        subraces,
        table,
        traps,
        variantrule,
        vehicles,
    )

    # For now, just finalize with whatever is already registered
    from .content_type_registry import get_content_type_registry

    registry = get_content_type_registry()
    registry.finalize()

    logger.info("Content type registry initialization completed")

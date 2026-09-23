"""Content type registry initialization system."""

from __future__ import annotations

from studiorum.core.logging import get_logger

logger = get_logger(__name__)


def initialize_content_types() -> None:
    """Initialize the content type registry by importing all model modules and finalizing."""

    logger.info("Initializing content type registry")

    # Import all model modules to trigger @content_type decorator registration.
    # The imports are unused by design, hence the noqa markers.
    from ..models import (
        adventures,  # noqa: F401
        backgrounds,  # noqa: F401
        baseitems,  # noqa: F401
        books,  # noqa: F401
        charoption,  # noqa: F401
        charoptiontype,  # noqa: F401
        classes,  # noqa: F401
        creatures,  # noqa: F401
        cults,  # noqa: F401
        decks,  # noqa: F401
        deities,  # noqa: F401
        diseases,  # noqa: F401
        facilities,  # noqa: F401
        feats,  # noqa: F401
        fluff,  # noqa: F401
        itemmastery,  # noqa: F401
        itemproperties,  # noqa: F401
        items,  # noqa: F401
        legendarygroup,  # noqa: F401
        magicvariant,  # noqa: F401
        objects,  # noqa: F401
        optional_features,  # noqa: F401
        psionic,  # noqa: F401
        races,  # noqa: F401
        recipes,  # noqa: F401
        rewards,  # noqa: F401
        rule_types,  # noqa: F401
        spells,  # noqa: F401
        subclasses,  # noqa: F401
        subraces,  # noqa: F401
        table,  # noqa: F401
        traps,  # noqa: F401
        variantrule,  # noqa: F401
        vehicles,  # noqa: F401
    )

    # For now, just finalize with whatever is already registered
    from .content_type_registry import get_content_type_registry

    registry = get_content_type_registry()
    registry.finalize()

    logger.info("Content type registry initialization completed")

"""Factories for template processing services."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from studiorum.core.services.protocols import (
        OmnidexerProtocol,
        TagResolverProtocol,
        TemplateServiceProtocol,
    )


def create_template_service(
    tag_resolver: TagResolverProtocol,
    omnidexer: OmnidexerProtocol,
) -> TemplateServiceProtocol:
    """Factory for template service.

    Args:
        tag_resolver: Tag resolver service for processing tags
        omnidexer: Omnidexer service for content resolution

    Returns:
        Template service implementing TemplateServiceProtocol
    """
    from .template_service import TemplateService

    return TemplateService(
        tag_resolver=tag_resolver,  # type: ignore[arg-type]
        omnidexer=omnidexer,  # type: ignore[arg-type]
    )

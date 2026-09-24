"""What tools receive through ``Depends``."""

from __future__ import annotations

from typing import Annotated

from fastmcp import Context
from fastmcp.dependencies import CurrentContext
from pydantic import Field

from studiorum.services import Services

SrdOnly = Annotated[
    bool | None,
    Field(
        description="Only content 5etools marks as in the 2014 or 5.2 SRD. "
        "Default: the server's setting, true unless it runs with --all-content"
    ),
]


def get_services(ctx: Context = CurrentContext()) -> Services:
    """The Services the server lifespan loaded."""
    services: Services = ctx.lifespan_context["services"]
    return services


def srd_default(ctx: Context = CurrentContext()) -> bool:
    """Whether content tools keep to the SRD when a call doesn't say."""
    return bool(ctx.lifespan_context.get("srd_only", True))

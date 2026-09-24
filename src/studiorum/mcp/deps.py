"""What tools receive through ``Depends``."""

from __future__ import annotations

from fastmcp import Context
from fastmcp.dependencies import CurrentContext

from studiorum.services import Services


def get_services(ctx: Context = CurrentContext()) -> Services:
    """The Services the server lifespan loaded."""
    services: Services = ctx.lifespan_context["services"]
    return services

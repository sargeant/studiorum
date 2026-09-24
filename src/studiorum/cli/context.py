"""How CLI commands reach the Services the root callback built."""

from __future__ import annotations

import click

from studiorum.core.config.unified_config import get_app_config
from studiorum.latex_engine.services.template_service import (
    set_template_service_provider,
)
from studiorum.services import Services, build_services

# Services for code that runs outside a CLI invocation: tests that call
# command functions directly, and scripts.
_fallback: Services | None = None


def install_services(ctx: click.Context, services: Services) -> None:
    """Make ``services`` the ones this invocation's commands and templates use."""
    ctx.obj = services
    set_template_service_provider(lambda: services.template_service)


def get_services() -> Services:
    """The Services of the current CLI invocation.

    Outside an invocation, builds one from get_app_config() and keeps it until
    reset_services().
    """
    ctx = click.get_current_context(silent=True)
    if ctx is not None:
        obj = ctx.find_root().obj
        if isinstance(obj, Services):
            return obj

    global _fallback
    if _fallback is None:
        services = build_services(get_app_config())
        set_template_service_provider(lambda: services.template_service)
        _fallback = services
    return _fallback


def reset_services() -> None:
    """Forget the fallback Services (for tests)."""
    global _fallback
    _fallback = None
    set_template_service_provider(None)

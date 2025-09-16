"""
CLI utility functions for accessing shared services.

This module delegates to the new CLI services module for proper separation of concerns.
Maintains backwards compatibility for existing CLI commands.
"""

from typing import Any, TypeVar

from studiorum.core.loaders.omnidexer import Omnidexer
from studiorum.core.protocols.progress import ProgressCallback
from studiorum.core.services.protocols import ContentListWriterProtocol
from studiorum.core.text.tag_resolver import TagResolver

T = TypeVar("T")


def get_omnidexer(*, progress_callback: ProgressCallback | None = None) -> Omnidexer:
    """Get omnidexer instance for CLI commands.

    Delegates to CLI services module for proper service access patterns.

    Args:
        progress_callback: Optional progress callback for data loading

    Returns:
        Omnidexer instance ready for use
    """
    from studiorum.cli.services import get_cli_omnidexer

    return get_cli_omnidexer(progress_callback=progress_callback)


def get_tag_resolver() -> TagResolver:
    """Get tag resolver instance for CLI commands.

    Delegates to CLI services module for proper service access patterns.

    Returns:
        TagResolver instance ready for use
    """
    from studiorum.cli.services import get_cli_tag_resolver

    return get_cli_tag_resolver()


def get_content_list_writer() -> ContentListWriterProtocol:
    """Get content list writer instance for CLI commands.

    Delegates to CLI services module for proper service access patterns.

    Returns:
        ContentListWriterProtocol instance ready for use
    """
    from studiorum.cli.services import get_cli_content_list_writer

    return get_cli_content_list_writer()


def resolve_option[T](value: T) -> T:
    """Resolve a Typer OptionInfo/ArgumentInfo to its default value if needed.

    When CLI functions are called directly from tests, parameters that are
    defined with typer.Option() or typer.Argument() are passed as the
    OptionInfo/ArgumentInfo objects themselves rather than their resolved
    values. This function extracts the default value when needed.

    Args:
        value: Either a regular value or a Typer OptionInfo/ArgumentInfo object

    Returns:
        The resolved value (either the input value or its default)

    Example:
        ```python
        # In CLI function:
        def my_command(
            file: Path | None = typer.Option(None, "--file")
        ):
            # Resolve for test compatibility
            file = resolve_option(file)
            # Now file is always Path | None, never OptionInfo
        ```
    """
    # Check if this is a Typer Option/Argument object by looking for 'default' attribute
    # We avoid importing typer.models.OptionInfo to keep this lightweight
    # and avoid circular dependencies
    if hasattr(value, "default"):
        # This is a Typer Option/Argument, return its default
        return value.default  # type: ignore[attr-defined,no-any-return]
    # Regular value, return as-is
    return value


def resolve_options(**kwargs: Any) -> dict[str, Any]:
    """Resolve multiple Typer OptionInfo objects at once.

    Convenience function for resolving multiple parameters in one call.

    Args:
        **kwargs: Named parameters to resolve

    Returns:
        Dictionary with same keys but resolved values

    Example:
        ```python
        # In CLI function:
        def my_command(
            file: Path | None = typer.Option(None),
            name: str = typer.Option("default")
        ):
            # Resolve all at once
            resolved = resolve_options(file=file, name=name)
            file = resolved["file"]
            name = resolved["name"]
        ```
    """
    return {key: resolve_option(value) for key, value in kwargs.items()}


def reset_cli_services() -> None:
    """Reset CLI service instances for command isolation."""
    from studiorum.cli.services import reset_cli_services

    reset_cli_services()

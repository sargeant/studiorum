"""Enhanced error handling for the unified architecture.

This module provides structured error handling for the new architectural components:
- Content source errors
- Reference tracking errors
- Configuration hierarchy errors
- Template composition errors

All errors provide rich context for debugging and user-friendly messages.
"""

from collections.abc import Callable
from typing import Any

from ..logging.logger import get_logger


class ArchitectureError(Exception):
    """Base exception for architecture-related errors."""

    def __init__(self, message: str, context: dict[str, Any] | None = None):
        super().__init__(message)
        self.context = context or {}

    def __str__(self) -> str:
        base_message = super().__str__()
        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            return f"{base_message} (Context: {context_str})"
        return base_message


class ContentSourceError(ArchitectureError):
    """Errors related to content source operations."""

    def __init__(
        self,
        message: str,
        source_location: str = "unknown",
        source_type: str = "unknown",
        **context: Any,
    ) -> None:
        context.update({"source_location": source_location, "source_type": source_type})
        super().__init__(message, context)


class ContentValidationError(ContentSourceError):
    """Errors during content validation."""

    def __init__(
        self, message: str, validation_errors: list[str] | None = None, **context: Any
    ) -> None:
        if validation_errors:
            context["validation_errors"] = validation_errors
        super().__init__(message, **context)


class ContentLoadingError(ContentSourceError):
    """Errors during content loading."""

    def __init__(
        self,
        message: str,
        items_processed: int = 0,
        items_failed: int = 0,
        **context: Any,
    ) -> None:
        context.update(
            {"items_processed": items_processed, "items_failed": items_failed}
        )
        super().__init__(message, **context)


class ReferenceTrackingError(ArchitectureError):
    """Errors related to reference tracking operations."""

    def __init__(
        self,
        message: str,
        reference_type: str = "unknown",
        reference_name: str = "unknown",
        **context: Any,
    ) -> None:
        context.update(
            {"reference_type": reference_type, "reference_name": reference_name}
        )
        super().__init__(message, context)


class ConfigurationError(ArchitectureError):
    """Errors related to configuration hierarchy."""

    def __init__(
        self,
        message: str,
        config_key: str = "unknown",
        config_source: str = "unknown",
        **context: Any,
    ) -> None:
        context.update({"config_key": config_key, "config_source": config_source})
        super().__init__(message, context)


class TemplateCompositionError(ArchitectureError):
    """Errors related to template composition."""

    def __init__(
        self,
        message: str,
        template_name: str = "unknown",
        component_name: str = "unknown",
        **context: Any,
    ) -> None:
        context.update(
            {"template_name": template_name, "component_name": component_name}
        )
        super().__init__(message, context)


def handle_content_source_error(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to handle content source errors consistently."""

    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except ContentSourceError:
            # Re-raise architecture errors as-is
            raise
        except Exception as e:
            # Wrap other exceptions in ContentSourceError
            source_location = (
                getattr(args[0], "location", "unknown") if args else "unknown"
            )
            source_type = type(args[0]).__name__ if args else "unknown"

            # Extract clean error message
            if hasattr(e, "args") and e.args:
                original_error = str(e.args[0])
            else:
                original_error = str(e)

            raise ContentSourceError(
                f"Unexpected error in content source operation: {e}",
                source_location=source_location,
                source_type=source_type,
                original_error=original_error,
                original_type=type(e).__name__,
            ) from e

    return wrapper


def handle_reference_tracking_error(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to handle reference tracking errors consistently."""
    import inspect

    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except ReferenceTrackingError:
            # Re-raise architecture errors as-is
            raise
        except Exception as e:
            # Extract context from arguments and function defaults
            reference_type = kwargs.get("content_type", "unknown")
            reference_name = kwargs.get("name", "unknown")

            # If not found in kwargs, check function signature for defaults
            if reference_type == "unknown" or reference_name == "unknown":
                try:
                    sig = inspect.signature(func)
                    # Get bound arguments to resolve defaults
                    bound_args = sig.bind(*args, **kwargs)
                    bound_args.apply_defaults()

                    if reference_type == "unknown":
                        reference_type = bound_args.arguments.get(
                            "content_type", "unknown"
                        )
                    if reference_name == "unknown":
                        reference_name = bound_args.arguments.get("name", "unknown")
                except Exception:
                    # If signature inspection fails, fall back to defaults
                    pass

            # Extract clean error message
            if hasattr(e, "args") and e.args:
                original_error = str(e.args[0])
            else:
                original_error = str(e)

            raise ReferenceTrackingError(
                f"Unexpected error in reference tracking: {e}",
                reference_type=reference_type,
                reference_name=reference_name,
                original_error=original_error,
                original_type=type(e).__name__,
            ) from e

    return wrapper


def format_error_for_user(error: ArchitectureError) -> str:
    """Format an architecture error for user-friendly display."""
    if isinstance(error, ContentValidationError):
        return f"Content validation failed: {error}"
    elif isinstance(error, ContentLoadingError):
        return f"Content loading failed: {error}"
    elif isinstance(error, ContentSourceError):
        return f"Content source error: {error}"
    elif isinstance(error, ReferenceTrackingError):
        return f"Reference tracking error: {error}"
    elif isinstance(error, ConfigurationError):
        return f"Configuration error: {error}"
    elif isinstance(error, TemplateCompositionError):
        return f"Template error: {error}"
    else:
        return f"Architecture error: {error}"


def log_architecture_error(error: ArchitectureError, logger: Any = None) -> None:
    """Log an architecture error with full context."""
    if logger is None:
        logger = get_logger(__name__)

    # Log the error with full context
    error_type = type(error).__name__
    logger.error(f"{error_type}: {error}")

    if error.context:
        logger.error(f"Error context: {error.context}")

    # Log the original exception if available
    if hasattr(error, "__cause__") and error.__cause__:
        logger.error(f"Original exception: {error.__cause__}")

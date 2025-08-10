"""Base context protocol and implementation for unified context management.

This module provides the foundation for all context objects in the system,
standardizing common patterns while allowing for specialized functionality.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Protocol, TypeVar

from pydantic import BaseModel, Field

from dnd5e.core.config.unified_config import ApplicationConfig

T = TypeVar("T")


class BaseContext(Protocol):
    """Base protocol for all context objects.

    This protocol defines the minimal interface that all context objects
    must implement, providing standardized access to core services and
    source information.
    """

    @property
    def content_type(self) -> str:
        """The content type this context is associated with."""
        ...

    @property
    def source_info(self) -> dict[str, Any]:
        """Source information for debugging and error reporting."""
        ...

    @property
    def omnidexer(self) -> Any:  # Avoid circular import
        """Access to the content indexer for lookups."""
        ...


class ContextualError(Exception):
    """Base exception class that includes context information."""

    def __init__(self, message: str, context: BaseContext | None = None) -> None:
        super().__init__(message)
        self.context = context

    def __str__(self) -> str:
        base_msg = super().__str__()
        if self.context is None:
            return base_msg

        source_info = self.context.source_info
        if source_info:
            source_str = ", ".join(
                f"{k}={v}" for k, v in source_info.items() if v is not None
            )
            return f"{base_msg} (context: {source_str})"

        return f"{base_msg} (content_type: {self.context.content_type})"


class Context(BaseModel, ABC):
    """Abstract base implementation for context objects.

    This provides common functionality that most context objects need,
    including validation, configuration access, and standardized patterns.
    """

    model_config = {"arbitrary_types_allowed": True}

    # Core services - these will be injected by the container
    omnidexer: Any = Field(default=None, description="Content indexer for lookups")

    # Source information for debugging
    source_file: str | None = Field(default=None, description="Source file path")
    source_section: str | None = Field(
        default=None, description="Section within source"
    )
    line_number: int | None = Field(default=None, description="Line number in source")

    @property
    @abstractmethod
    def content_type(self) -> str:
        """The content type this context is associated with."""
        pass

    @property
    def source_info(self) -> dict[str, Any]:
        """Source information for debugging and error reporting."""
        return {
            "content_type": self.content_type,
            "source_file": self.source_file,
            "source_section": self.source_section,
            "line_number": self.line_number,
        }

    def create_error(self, message: str) -> ContextualError:
        """Create a contextual error with this context attached."""
        return ContextualError(message, self)

    def copy_with_source(
        self,
        source_file: str | None = None,
        source_section: str | None = None,
        line_number: int | None = None,
        **updates: Any,
    ) -> BaseContext:
        """Create a copy with updated source information."""
        update_dict = {
            "source_file": source_file or self.source_file,
            "source_section": source_section or self.source_section,
            "line_number": line_number or self.line_number,
            **updates,
        }
        return self.model_copy(update=update_dict)


class DocumentContext(Context):
    """Context for document-level operations.

    This context provides document-wide state and configuration,
    serving as the base for rendering and processing operations.
    """

    # Document metadata
    document_type: str = Field(default="general", description="Document type")
    current_section: str = Field(default="", description="Current document section")
    current_page: int = Field(default=0, description="Current page number")

    # Document state tracking
    float_count: int = Field(default=0, description="Number of floats on current page")
    sidebar_count: int = Field(default=0, description="Number of sidebars")
    table_count: int = Field(default=0, description="Number of tables")

    # Processing modes
    appendix_mode: bool = Field(
        default=False, description="Whether in appendix generation"
    )
    validation_mode: str = Field(default="strict", description="Validation strictness")

    @property
    def content_type(self) -> str:
        return self.document_type


class ProcessingContext[T](Context):
    """Generic context for content processing operations.

    This context wraps content being processed and provides
    access to processing configuration and state.
    """

    # Content being processed
    content: T = Field(description="Content being processed")
    content_type_name: str = Field(description="Name of the content type")

    # Processing configuration
    processing_options: dict[str, Any] = Field(
        default_factory=dict, description="Processing options"
    )

    @property
    def content_type(self) -> str:
        return self.content_type_name

    def get_option(self, key: str, default: Any = None) -> Any:
        """Get a processing option with optional default."""
        return self.processing_options.get(key, default)

    def set_option(self, key: str, value: Any) -> ProcessingContext[T]:
        """Create a copy with an updated processing option."""
        new_options = self.processing_options.copy()
        new_options[key] = value
        return self.model_copy(update={"processing_options": new_options})


class ServiceContext(Context):
    """Context that provides access to application services.

    This context is used when operations need access to multiple
    application services and configuration.
    """

    # Application configuration (can be ApplicationConfig or LaTeXConfig)
    config: Any = Field(
        default=None,
        description="Application configuration (ApplicationConfig or LaTeXConfig)",
    )

    # Additional services (injected as needed)
    tag_resolver: Any = Field(default=None, description="Tag resolver service")
    cross_ref_manager: Any = Field(default=None, description="Cross-reference manager")
    hyperlink_manager: Any = Field(default=None, description="Hyperlink manager")
    content_tracker: Any = Field(default=None, description="Content tracker")

    @property
    def content_type(self) -> str:
        return "service"

    def has_service(self, service_name: str) -> bool:
        """Check if a service is available."""
        return getattr(self, service_name, None) is not None

    def get_service(self, service_name: str) -> Any:
        """Get a service, raising an error if not available."""
        service = getattr(self, service_name, None)
        if service is None:
            raise ValueError(f"Service '{service_name}' not available in context")
        return service


# Utility functions for context creation and management


def create_processing_context[T](
    content: T,
    content_type: str,
    omnidexer: Any = None,
    source_file: str | None = None,
    source_section: str | None = None,
    **options: Any,
) -> ProcessingContext[T]:
    """Create a processing context for content.

    Args:
        content: The content to process
        content_type: The type name of the content
        omnidexer: Content indexer instance
        source_file: Source file path
        source_section: Source section name
        **options: Additional processing options

    Returns:
        Configured processing context
    """
    return ProcessingContext(
        content=content,
        content_type_name=content_type,
        omnidexer=omnidexer,
        source_file=source_file,
        source_section=source_section,
        processing_options=options,
    )


def create_document_context(
    document_type: str = "general",
    omnidexer: Any = None,
    current_section: str = "",
    **options: Any,
) -> DocumentContext:
    """Create a document context.

    Args:
        document_type: Type of document being processed
        omnidexer: Content indexer instance
        current_section: Current section being processed
        **options: Additional document options

    Returns:
        Configured document context
    """
    return DocumentContext(
        document_type=document_type,
        omnidexer=omnidexer,
        current_section=current_section,
        **options,
    )


def create_service_context(
    omnidexer: Any = None,
    config: ApplicationConfig | None = None,
    **services: Any,
) -> ServiceContext:
    """Create a service context.

    Args:
        omnidexer: Content indexer instance
        config: Application configuration
        **services: Additional services to inject

    Returns:
        Configured service context
    """
    return ServiceContext(
        omnidexer=omnidexer,
        config=config,
        **services,
    )

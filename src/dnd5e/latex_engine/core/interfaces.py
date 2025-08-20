"""LaTeX engine interfaces and protocols."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from pathlib import Path
from typing import Optional, Protocol, runtime_checkable

from dnd5e.core.models.document_metadata import DocumentMetadata
from dnd5e.renderers.core.interfaces import RenderingContext


@runtime_checkable
class CompilationResult(Protocol):
    """Result of LaTeX compilation."""

    success: bool
    output_file: Path | None
    error_message: str | None


@runtime_checkable
class LaTeXEngineProtocol(Protocol):
    """Protocol for LaTeX document generation engines."""

    def render_document(
        self, content: Sequence[dict | object], context: RenderingContext
    ) -> str:
        """Render content to LaTeX string.

        Args:
            content: List of content items to render
            context: Rendering context with omnidexer, metadata, etc.

        Returns:
            Complete LaTeX document as string
        """
        ...

    def compile_to_pdf(
        self, latex_content: str, output_path: Path, config: object | None = None
    ) -> CompilationResult:
        """Compile LaTeX content to PDF.

        Args:
            latex_content: LaTeX source code
            output_path: Path where PDF should be written
            config: Optional compilation configuration

        Returns:
            CompilationResult with success status and details
        """
        ...

    def validate_environment(self) -> bool:
        """Check if LaTeX environment is properly configured.

        Returns:
            True if LaTeX can be used, False otherwise
        """
        ...


class LaTeXEngine(ABC):
    """Abstract base class for LaTeX engines."""

    @abstractmethod
    def render_document(
        self, content: Sequence[dict | object], context: RenderingContext
    ) -> str:
        """Render content to LaTeX string."""
        ...

    @abstractmethod
    def compile_to_pdf(
        self, latex_content: str, output_path: Path, config: object | None = None
    ) -> CompilationResult:
        """Compile LaTeX content to PDF."""
        ...

    @abstractmethod
    def validate_environment(self) -> bool:
        """Check if LaTeX environment is available."""
        ...


@runtime_checkable
class LaTeXEngineFactory(Protocol):
    """Factory for creating LaTeX engines."""

    def create_engine(self, config: object | None = None) -> LaTeXEngineProtocol:
        """Create configured LaTeX engine instance.

        Args:
            config: Optional configuration object

        Returns:
            Configured LaTeX engine
        """
        ...

    def create_mock_engine(self) -> LaTeXEngineProtocol:
        """Create mock LaTeX engine for testing.

        Returns:
            Mock LaTeX engine that doesn't require LaTeX installation
        """
        ...

"""
Unified configuration system for 5e2pdf.

This module consolidates the various configuration patterns throughout the codebase
into a single, cohesive Pydantic-based configuration system. It replaces the
scattered TypedDict and separate config classes with a hierarchical structure.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class LoggingConfig(BaseModel):
    """Configuration for application logging."""

    level: str = Field(
        default="WARNING",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )
    format: str = Field(
        default=(
            "%(log_color)s%(levelname)-8s%(reset)s "
            "%(blue)s%(name)s%(reset)s: %(message)s"
        ),
        description="Log format string for colorlog",
    )

    @field_validator("level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level is supported."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of {valid_levels}")
        return v.upper()


class PathsConfig(BaseModel):
    """Configuration for file and directory paths."""

    data_path: Path | None = Field(
        default=None, description="Path to D&D 5e data files"
    )
    assets_path: Path = Field(default=Path("assets"), description="Path to asset files")
    output_path: Path = Field(
        default=Path("output"), description="Path for generated output files"
    )
    build_path: Path = Field(
        default=Path("build"), description="Path for build artifacts"
    )
    font_dir: Path | None = Field(
        default=None, description="Directory containing custom fonts"
    )


class ProcessingConfig(BaseModel):
    """Configuration for content processing."""

    max_workers: int = Field(
        default=5, ge=1, le=16, description="Maximum number of worker processes"
    )
    enable_caching: bool = Field(default=True, description="Enable content caching")
    cache_ttl: int = Field(
        default=3600, ge=0, description="Cache time-to-live in seconds"
    )


class ContentConfig(BaseModel):
    """Configuration for content inclusion."""

    include_images: bool = Field(default=False, description="Include images by default")
    # Appendix configuration
    appendix_spells: bool = Field(
        default=False, description="Generate spell appendices by default"
    )
    appendix_items: bool = Field(
        default=False, description="Generate item appendices by default"
    )
    appendix_creatures: bool = Field(
        default=False, description="Generate creature appendices by default"
    )
    # Default source resolution
    default_sources: list[str] = Field(
        default=["xphb", "xmm", "xdmg"],
        description="Default sources for content resolution when no source specified in tags",
    )


class CompilationConfig(BaseModel):
    """Configuration for compilation behavior."""

    auto_compile_pdf: bool = Field(
        default=False, description="Automatically compile to PDF"
    )


class ValidationConfig(BaseModel):
    """Configuration for content validation."""

    strictness: Literal["strict", "normal", "lenient"] = Field(
        default="normal", description="Validation strictness level"
    )
    enable_summary: bool = Field(
        default=False, description="Enable validation error summary reporting"
    )
    max_duplicate_errors: int = Field(
        default=1, ge=0, description="Maximum times to log identical validation errors"
    )


def _default_fallback_engines() -> list[Literal["lualatex", "xelatex", "pdflatex"]]:
    """Default factory for fallback engines."""
    return ["xelatex"]


class LaTeXEngineConfig(BaseModel):
    """Configuration for LaTeX compilation engines."""

    primary_engine: Literal["lualatex", "xelatex", "pdflatex"] = Field(
        default="lualatex", description="Primary LaTeX engine to use"
    )
    fallback_engines: list[Literal["lualatex", "xelatex", "pdflatex"]] = Field(
        default_factory=_default_fallback_engines,
        description="Fallback engines if primary fails",
    )
    timeout: int = Field(
        default=300, ge=30, description="Compilation timeout in seconds"
    )
    max_passes: int = Field(
        default=3, ge=1, le=10, description="Maximum compilation passes"
    )
    show_progress: bool = Field(default=True, description="Show compilation progress")
    keep_temp_files: bool = Field(
        default=False, description="Keep temporary compilation files for debugging"
    )


class LaTeXDocumentConfig(BaseModel):
    """Configuration for LaTeX document structure and styling."""

    document_class: str = Field(
        default="dndbook",
        description="LaTeX document class (dndbook, dndarticle, article, book)",
    )
    class_options: list[str] = Field(
        default_factory=lambda: ["justified", "twocolumn"],
        description="Document class options",
    )
    paper_size: Literal["letter", "a4", "a5"] = Field(
        default="letter", description="Paper size"
    )
    font_size: Literal["10pt", "11pt", "12pt"] = Field(
        default="11pt", description="Base font size"
    )
    font_scheme: Literal["dmsguild", "commercial", "system"] = Field(
        default="dmsguild", description="Font scheme to use"
    )
    background: Literal["full", "none", "print"] = Field(
        default="full", description="Background style (full, none, print)"
    )
    high_contrast: bool = Field(
        default=False, description="Use high contrast mode for printing"
    )
    justified_text: bool = Field(default=False, description="Justify text columns")
    fancy_headers: bool = Field(default=True, description="Use fancy page headers")
    two_column: bool = Field(default=True, description="Use two-column layout")
    show_toc: bool = Field(default=True, description="Include table of contents")
    show_index: bool = Field(default=True, description="Include alphabetical index")
    fonts: Literal["wotc", "dmsguild"] | None = Field(
        default=None, description="Font package to use (wotc, dmsguild)"
    )
    no_outline: bool = Field(
        default=False, description="Disable document outline generation"
    )


class LaTeXRenderingConfig(BaseModel):
    """Configuration for LaTeX content rendering."""

    enable_hyperlinks: bool = Field(
        default=True, description="Enable hyperlinks in PDF"
    )
    enable_cross_refs: bool = Field(default=True, description="Enable cross-references")
    auto_page_refs: bool = Field(
        default=True, description="Automatically add page references"
    )
    hyperlink_styles: dict[str, dict[str, Any]] = Field(
        default_factory=dict, description="Custom hyperlink styling"
    )
    cross_ref_format: str = Field(
        default="see page~\\pageref{{{label}}}",
        description="Format string for cross-references",
    )
    appendix_organization: Literal["alphabetical", "source", "type"] = Field(
        default="alphabetical", description="How to organize appendix content"
    )


class LaTeXConfig(BaseModel):
    """Complete LaTeX configuration."""

    engine: LaTeXEngineConfig = Field(
        default_factory=LaTeXEngineConfig, description="Engine configuration"
    )
    document: LaTeXDocumentConfig = Field(
        default_factory=LaTeXDocumentConfig, description="Document configuration"
    )
    rendering: LaTeXRenderingConfig = Field(
        default_factory=LaTeXRenderingConfig, description="Rendering configuration"
    )


class RenderingConfig(BaseModel):
    """Configuration for content rendering."""

    template_dir: Path | None = Field(
        default=None, description="Custom template directory"
    )
    output_format: Literal["latex", "pdf", "html"] = Field(
        default="latex", description="Output format"
    )
    debug: bool = Field(default=False, description="Enable debug mode")
    strict_mode: bool = Field(default=False, description="Enable strict validation")
    content: ContentConfig = Field(
        default_factory=ContentConfig, description="Content configuration"
    )
    compilation: CompilationConfig = Field(
        default_factory=CompilationConfig, description="Compilation configuration"
    )
    latex: LaTeXConfig = Field(
        default_factory=LaTeXConfig, description="LaTeX-specific configuration"
    )


class ApplicationConfig(BaseSettings):
    """
    Complete application configuration.

    This replaces the scattered Settings, LaTeXConfig, and various TypedDict
    configurations with a single, comprehensive configuration system.
    """

    logging: LoggingConfig = Field(
        default_factory=LoggingConfig, description="Logging configuration"
    )
    paths: PathsConfig = Field(
        default_factory=PathsConfig, description="Path configuration"
    )
    processing: ProcessingConfig = Field(
        default_factory=ProcessingConfig, description="Processing configuration"
    )
    validation: ValidationConfig = Field(
        default_factory=ValidationConfig, description="Validation configuration"
    )
    rendering: RenderingConfig = Field(
        default_factory=RenderingConfig, description="Rendering configuration"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_prefix="DND5E_",
        env_nested_delimiter="__",
    )

    def model_post_init(self, __context: Any) -> None:
        """Post-process configuration after parsing."""
        # Ensure output directory exists
        self.paths.output_path.mkdir(parents=True, exist_ok=True)
        self.paths.build_path.mkdir(parents=True, exist_ok=True)


# Global configuration instance
_app_config: ApplicationConfig | None = None


def get_app_config() -> ApplicationConfig:
    """Get the global application configuration instance."""
    global _app_config
    if _app_config is None:
        _app_config = ApplicationConfig()
    return _app_config


def reset_app_config() -> None:
    """Reset the global configuration instance (for testing)."""
    global _app_config
    _app_config = None


# Convenience functions for backward compatibility
def get_settings() -> ApplicationConfig:
    """Backward compatibility alias for get_app_config()."""
    return get_app_config()


def reset_settings() -> None:
    """Backward compatibility alias for reset_app_config()."""
    reset_app_config()

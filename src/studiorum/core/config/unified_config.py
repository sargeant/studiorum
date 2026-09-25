"""
Unified configuration system for studiorum.

This module consolidates the various configuration patterns throughout the codebase
into a single, cohesive Pydantic-based configuration system. It replaces the
scattered TypedDict and separate config classes with a hierarchical structure.
"""

from __future__ import annotations

import os
from contextvars import ContextVar
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)

from studiorum.core.config.data_sources import DataConfig

CONFIG_FILE_ENV = "STUDIORUM_CONFIG_FILE"

# The YAML file ApplicationConfig reads, set only while load_config() builds one.
# Constructing ApplicationConfig directly reads no file: defaults and environment.
_config_file: ContextVar[Path | None] = ContextVar("_config_file", default=None)


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


class FluffRenderingConfig(BaseModel):
    """Configuration for fluff content rendering (Phase 5)."""

    enabled: bool = Field(
        default=False, description="Enable fluff rendering by default"
    )
    placement: Literal["before", "after", "sidebar"] = Field(
        default="before", description="Default fluff placement relative to main content"
    )
    deduplication: bool = Field(
        default=True,
        description="Enable fluff deduplication to avoid repetitive content",
    )
    sections: list[str] = Field(
        default_factory=list,
        description="Optional section filtering - if specified, only these sections will be included",
    )
    allowed_sources: list[str] = Field(
        default_factory=list,
        description="Optional source filtering - if specified, only fluff from these sources will be included",
    )


class ContentConfig(BaseModel):
    """Configuration for content inclusion."""

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
    # Fluff configuration (Phase 5)
    fluff: FluffRenderingConfig = Field(
        default_factory=FluffRenderingConfig,
        description="Fluff content rendering configuration",
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
        default=300, ge=30, description="Seconds latexmk may run for each engine"
    )


class LaTeXDocumentConfig(BaseModel):
    """The LaTeX document's class, layout and front and back matter.

    The defaults give the class options documents have always rendered with:
    ``letterpaper, 11pt, bg=full, twocolumn, stats=modern``.
    """

    document_class: Literal["dndbook", "dndarticle"] = Field(
        default="dndbook", description="LaTeX document class"
    )
    extra_class_options: list[str] = Field(
        default_factory=list,
        description="Class options with no field of their own, passed after the rest",
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
    fancy_headers: bool = Field(
        default=False, description="Use the class's fancy page decorations"
    )
    two_column: bool = Field(default=True, description="Use two-column layout")
    show_toc: bool = Field(default=True, description="Include table of contents")
    show_index: bool = Field(default=False, description="Include alphabetical index")
    fonts: Literal["wotc", "dmsguild"] | None = Field(
        default=None, description="Font package to use (wotc, dmsguild)"
    )
    no_outline: bool = Field(
        default=False, description="Disable document outline generation"
    )
    statblock: Literal["2014", "classic", "2024", "modern"] = Field(
        default="2024",
        description="Statblock style (2014/classic for legacy, 2024/modern for updated)",
    )

    @property
    def statblock_year(self) -> Literal["2014", "2024"]:
        return "2024" if self.statblock in ("2024", "modern") else "2014"

    def class_options(self) -> list[str]:
        """The options for ``\\documentclass``, without duplicates."""
        options = [f"{self.paper_size}paper", self.font_size, f"bg={self.background}"]
        if self.high_contrast:
            options.append("highcontrast")
        if self.justified_text:
            options.append("justified")
        if self.fancy_headers:
            options.append("fancy")
        options.append("twocolumn" if self.two_column else "onecolumn")
        if self.fonts:
            options.append(f"fonts={self.fonts}")
        if self.no_outline:
            options.append("nooutline")
        if self.statblock_year == "2024":
            options.append("stats=modern")
        options.extend(self.extra_class_options)
        return list(dict.fromkeys(options))


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


FIVETOOLS_IMG_CHECKOUT = Path.home() / "Code" / "5etools-img"


class ImageConfig(BaseModel):
    """Where images come from and where converted copies go."""

    include_images: bool = Field(
        default=False, description="Include images by default (--images)"
    )
    image_directory: Path | None = Field(
        default=None,
        validate_default=True,
        description=(
            "A 5etools-img checkout, which 5etools image paths are relative to. "
            "Defaults to ~/Code/5etools-img when that exists."
        ),
    )
    cache_dir: Path | None = Field(
        default=None,
        description="Where converted and downloaded images go (default: <cache>/images)",
    )

    @field_validator("image_directory", mode="after")
    @classmethod
    def _default_image_directory(cls, v: Path | None) -> Path | None:
        if v is not None:
            return v.expanduser()
        return FIVETOOLS_IMG_CHECKOUT if FIVETOOLS_IMG_CHECKOUT.is_dir() else None


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
    image: ImageConfig = Field(
        default_factory=ImageConfig, description="Image asset configuration"
    )
    data: DataConfig = Field(
        default_factory=DataConfig, description="Data directories and homebrew"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_prefix="STUDIORUM_",
        env_nested_delimiter="__",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Precedence: init kwargs, then environment, then the YAML file, then defaults."""
        sources: tuple[PydanticBaseSettingsSource, ...] = (
            init_settings,
            env_settings,
            dotenv_settings,
        )
        config_file = _config_file.get()
        if config_file is not None:
            sources += (YamlConfigSettingsSource(settings_cls, yaml_file=config_file),)
        return sources

    @model_validator(mode="before")
    @classmethod
    def _reject_old_data_sections(cls, values: Any) -> Any:
        """Name the replacement when a config file still has the old sections."""
        if isinstance(values, dict):
            old = [k for k in ("data_sources", "content_sources") if k in values]
            if old:
                raise ValueError(
                    f"{' and '.join(old)} were replaced by data.dirs (5etools-shaped "
                    "data directories) and data.homebrew (homebrew files or "
                    "directories); see docs/user-guide/configuration.md"
                )
        return values

    def model_post_init(self, __context: Any) -> None:
        """Post-process configuration after parsing."""
        # Ensure output directory exists
        self.paths.output_path.mkdir(parents=True, exist_ok=True)
        self.paths.build_path.mkdir(parents=True, exist_ok=True)


# Global configuration instance
_app_config: ApplicationConfig | None = None


class ConfigFileNotFoundError(FileNotFoundError):
    """A configuration file was named explicitly but does not exist."""


def get_default_config_path() -> Path:
    """The configuration file: STUDIORUM_CONFIG_FILE, else ~/.studiorum/config.yaml."""
    named = os.environ.get(CONFIG_FILE_ENV)
    if named:
        return Path(named).expanduser()
    return Path.home() / ".studiorum" / "config.yaml"


def load_config(config_file: Path | None = None) -> ApplicationConfig:
    """Load the application configuration.

    Reads ``config_file`` if given, else the file ``STUDIORUM_CONFIG_FILE``
    names, else ``~/.studiorum/config.yaml`` if it exists. Environment
    variables override the file.

    Raises:
        ConfigFileNotFoundError: The file was named explicitly (argument or
            environment variable) and does not exist.
        pydantic.ValidationError: The file does not match the schema.
    """
    explicit = config_file is not None or bool(os.environ.get(CONFIG_FILE_ENV))
    path = config_file.expanduser() if config_file else get_default_config_path()
    if not path.exists():
        if explicit:
            raise ConfigFileNotFoundError(f"Configuration file not found: {path}")
        return ApplicationConfig()

    token = _config_file.set(path)
    try:
        return ApplicationConfig()
    finally:
        _config_file.reset(token)


def get_app_config() -> ApplicationConfig:
    """The process-wide configuration, loaded on first use with load_config()."""
    global _app_config
    if _app_config is None:
        _app_config = load_config()
    return _app_config


def get_default_sources() -> list[str]:
    """Get default sources for content resolution from config."""
    return get_app_config().rendering.content.default_sources


def reset_app_config() -> None:
    """Reset the global configuration instance (for testing)."""
    global _app_config
    _app_config = None


def set_app_config(config: ApplicationConfig) -> None:
    """Set the global application configuration instance."""
    global _app_config
    _app_config = config

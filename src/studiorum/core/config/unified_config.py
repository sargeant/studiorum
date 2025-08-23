"""
Unified configuration system for studiorum.

This module consolidates the various configuration patterns throughout the codebase
into a single, cohesive Pydantic-based configuration system. It replaces the
scattered TypedDict and separate config classes with a hierarchical structure.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

if TYPE_CHECKING:
    from studiorum.core.assets.image_sources import ImageSourceConfig


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


class MCPConfig(BaseModel):
    """Configuration for MCP server functionality."""

    enabled: bool = Field(default=False, description="Enable MCP server functionality")
    host: str = Field(default="localhost", description="MCP server host address")
    port: int = Field(default=8080, description="MCP server port", ge=0)
    max_concurrent_requests: int = Field(
        default=10, description="Maximum concurrent MCP requests", gt=0
    )
    request_timeout: int = Field(
        default=30, description="Request timeout in seconds", gt=0
    )
    memory_limit_mb: int = Field(
        default=1024, description="Memory limit for MCP operations in MB", gt=0
    )

    # Performance tuning
    cache_size_mb: int = Field(
        default=256, description="Cache size for MCP operations in MB", gt=0
    )
    preload_content_types: list[str] = Field(
        default_factory=list,
        description="Content types to preload for faster MCP responses",
    )

    # Security and reliability
    enable_hot_reload: bool = Field(
        default=False, description="Enable hot-reload of configuration changes"
    )
    log_requests: bool = Field(
        default=True, description="Log MCP requests for monitoring"
    )


class ImageConfig(BaseModel):
    """Configuration for image asset management and Phase 4 processing."""

    # Core image processing
    enabled: bool = Field(default=True, description="Enable image processing")
    cache_dir: Path | None = Field(
        default=None, description="Custom image cache directory"
    )
    default_cache_ttl_hours: int = Field(
        default=24,
        ge=1,
        le=168,
        description="Default cache TTL for image sources (hours)",
    )
    max_cache_size_mb: int = Field(
        default=1024, ge=10, le=10240, description="Maximum total cache size in MB"
    )
    cleanup_interval_hours: int = Field(
        default=24, ge=1, le=168, description="How often to run cache cleanup (hours)"
    )
    sources: list[ImageSourceConfig] = Field(
        default_factory=list, description="Configured image sources"
    )

    # Phase 4: Image Processing Options
    image_quality: str = Field(
        default="hybrid",
        pattern=r"^(digital|print|hybrid|high|low)$",
        description="Image quality mode: digital (web-optimized), print (high-res), hybrid (balanced), high (max quality), low (compact)",
    )
    placement_strategy: str = Field(
        default="intelligent",
        pattern=r"^(intelligent|simple|float|inline)$",
        description="Image placement strategy: intelligent (AI-guided), simple (basic rules), float (LaTeX floats), inline (in-text)",
    )
    gallery_layout: str = Field(
        default="grid",
        pattern=r"^(grid|showcase|sequential|comparison)$",
        description="Gallery layout mode: grid (thumbnails), showcase (featured), sequential (ordered), comparison (side-by-side)",
    )
    enable_intelligent_placement: bool = Field(
        default=True,
        description="Enable AI-powered intelligent image placement optimization",
    )
    enable_content_analysis: bool = Field(
        default=True,
        description="Enable content analysis for context-aware image selection",
    )
    enable_layout_optimization: bool = Field(
        default=True,
        description="Enable automatic layout optimization for better readability",
    )
    enable_output_optimization: bool = Field(
        default=True,
        description="Enable output format optimization (resolution, compression, format selection)",
    )

    # Phase 4: Content-Specific Image Options
    bestiary_images: bool = Field(
        default=True,
        description="Include creature images in bestiary content",
    )
    item_images: bool = Field(
        default=True,
        description="Include item and equipment images",
    )
    adventure_images: bool = Field(
        default=True,
        description="Include adventure maps, scenes, and narrative images",
    )
    chapter_art: bool = Field(
        default=True,
        description="Include chapter headers and decorative artwork",
    )

    # Phase 4: Performance Options
    preload_images: bool = Field(
        default=True,
        description="Preload frequently used images for faster processing",
    )
    use_cache: bool = Field(
        default=True,
        description="Enable image caching system for performance optimization",
    )
    sync_sources_on_startup: bool = Field(
        default=False,
        description="Synchronize all image sources on application startup (slower startup, faster runtime)",
    )
    parallel_processing: bool = Field(
        default=True,
        description="Enable parallel image processing for performance gains",
    )
    max_concurrent_downloads: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum number of concurrent image downloads",
    )

    # Phase 4: Advanced Options
    enabled_sources: list[str] | None = Field(
        default=None,
        description="List of enabled source names (None = all enabled). Use to filter specific image sources.",
    )
    fallback_to_placeholders: bool = Field(
        default=True,
        description="Generate placeholder images when source images are unavailable",
    )
    generate_missing_alt_text: bool = Field(
        default=True,
        description="Auto-generate alt text for accessibility when missing from source",
    )

    # Legacy compatibility
    include_images_default: bool = Field(
        default=False, description="Default value for including images in content"
    )

    # Default 5etools-img source
    enable_default_5etools_source: bool = Field(
        default=True,
        description="Automatically configure default 5etools image sources",
    )

    def model_post_init(self, __context: Any) -> None:
        """Post-process configuration after parsing."""
        if self.enable_default_5etools_source and not self.sources:
            self._add_default_sources()

    def _add_default_sources(self) -> None:
        """Add default 5etools image sources."""
        try:
            import studiorum.core.assets.image_sources as img_sources

            # Create specific source types instead of using the union
            default_sources: list[img_sources.ImageSourceConfig] = [
                img_sources.GitImageSourceConfig(
                    name="5etools-img-git",
                    repository_url="https://github.com/5etools-mirror-3/5etools-img.git",
                    priority=10,
                    enabled=True,
                    cache_ttl_hours=168,  # 1 week
                ),
                img_sources.HttpApiImageSourceConfig(
                    name="5etools-img-http",
                    base_url="https://raw.githubusercontent.com/5etools-mirror-3/5etools-img/main",
                    priority=20,
                    enabled=True,
                    cache_ttl_hours=24,
                ),
            ]

            self.sources.extend(default_sources)
        except ImportError:
            # If image_sources module isn't available yet, skip default sources
            pass

    @property
    def cache_directory(self) -> Path:
        """Get the cache directory path."""
        if self.cache_dir:
            return self.cache_dir
        return Path.home() / ".studiorum" / "image_cache"

    @property
    def quality(self) -> str:
        """Get image quality setting for backward compatibility."""
        return self.image_quality

    @property
    def max_cache_size_gb(self) -> float:
        """Get max cache size in GB."""
        return self.max_cache_size_mb / 1024.0

    @property
    def is_high_performance_mode(self) -> bool:
        """Check if high performance options are enabled."""
        return (
            self.parallel_processing
            and self.preload_images
            and self.use_cache
            and self.max_concurrent_downloads >= 3
        )

    @property
    def enabled_content_types(self) -> set[str]:
        """Get set of enabled content type identifiers."""
        content_types = set()
        if self.bestiary_images:
            content_types.add("bestiary")
        if self.item_images:
            content_types.add("items")
        if self.adventure_images:
            content_types.add("adventures")
        if self.chapter_art:
            content_types.add("chapter_art")
        return content_types

    @property
    def is_intelligent_processing_enabled(self) -> bool:
        """Check if AI-powered intelligent processing is fully enabled."""
        return (
            self.enable_intelligent_placement
            and self.enable_content_analysis
            and self.enable_layout_optimization
        )

    def get_active_sources(self) -> list[ImageSourceConfig]:
        """Get list of currently active image sources based on enabled_sources filter."""
        if self.enabled_sources is None:
            return [
                source for source in self.sources if getattr(source, "enabled", True)
            ]

        # Filter sources by name
        enabled_names = set(self.enabled_sources)
        return [
            source
            for source in self.sources
            if getattr(source, "name", None) in enabled_names
            and getattr(source, "enabled", True)
        ]

    def should_process_content_type(self, content_type: str) -> bool:
        """Check if images should be processed for a specific content type."""
        content_type_map = {
            "bestiary": self.bestiary_images,
            "monster": self.bestiary_images,
            "creature": self.bestiary_images,
            "items": self.item_images,
            "item": self.item_images,
            "equipment": self.item_images,
            "adventures": self.adventure_images,
            "adventure": self.adventure_images,
            "chapter": self.chapter_art,
            "chapter_art": self.chapter_art,
        }
        return content_type_map.get(content_type.lower(), False)

    def get_quality_settings(self) -> dict[str, str | int | bool]:
        """Get quality settings optimized for the current image_quality mode."""
        quality_configs: dict[str, dict[str, str | int | bool]] = {
            "digital": {"format": "webp", "quality": 85, "optimize": True},
            "print": {"format": "png", "quality": 95, "dpi": 300},
            "hybrid": {"format": "auto", "quality": 90, "optimize": True},
            "high": {"format": "png", "quality": 100, "optimize": False},
            "low": {"format": "jpeg", "quality": 70, "optimize": True},
        }
        return quality_configs.get(self.image_quality, quality_configs["hybrid"])

    def validate_configuration(self) -> list[str]:
        """Validate the image configuration and return list of warnings/issues."""
        issues = []

        # Performance validation
        if self.parallel_processing and self.max_concurrent_downloads > 10:
            issues.append(
                f"High concurrent downloads ({self.max_concurrent_downloads}) may impact performance"
            )

        # Quality vs performance tradeoffs
        if self.image_quality in ("high", "print") and not self.use_cache:
            issues.append(
                "High quality mode without caching may cause slow performance"
            )

        # Source validation
        if self.enabled_sources:
            available_names = {getattr(source, "name", None) for source in self.sources}
            invalid_names = set(self.enabled_sources) - available_names
            if invalid_names:
                issues.append(
                    f"Invalid source names in enabled_sources: {invalid_names}"
                )

        # Content type validation
        if not any(
            [
                self.bestiary_images,
                self.item_images,
                self.adventure_images,
                self.chapter_art,
            ]
        ):
            issues.append("No content types enabled - images will not be processed")

        return issues


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
    mcp: MCPConfig = Field(
        default_factory=MCPConfig, description="MCP server configuration"
    )
    image: ImageConfig = Field(
        default_factory=ImageConfig, description="Image asset configuration"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_prefix="STUDIORUM_",
        env_nested_delimiter="__",
    )

    def model_post_init(self, __context: Any) -> None:
        """Post-process configuration after parsing."""
        # Ensure output directory exists
        self.paths.output_path.mkdir(parents=True, exist_ok=True)
        self.paths.build_path.mkdir(parents=True, exist_ok=True)


# Build models to resolve forward references
def _rebuild_models() -> None:
    """Rebuild models to resolve forward references."""
    try:
        # Import the module and make ImageSourceConfig available globally
        from studiorum.core.assets.image_sources import ImageSourceConfig

        globals()["ImageSourceConfig"] = ImageSourceConfig

        ImageConfig.model_rebuild()
        ApplicationConfig.model_rebuild()
    except ImportError:
        # If image_sources module isn't available yet, skip rebuild
        pass


# Rebuild models immediately when module is imported
# This ensures forward references are resolved even for direct instantiation
_rebuild_models()

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


def set_app_config(config: ApplicationConfig) -> None:
    """Set the global application configuration instance."""
    global _app_config
    _app_config = config


# Convenience functions for backward compatibility
def get_settings() -> ApplicationConfig:
    """Backward compatibility alias for get_app_config()."""
    return get_app_config()


def reset_settings() -> None:
    """Backward compatibility alias for reset_app_config()."""
    reset_app_config()

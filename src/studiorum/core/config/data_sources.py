"""Configuration models for three-tier data source architecture.

This module implements the three-tier configuration system for data sources,
separating data repositories from content attribution.

Key Components:
- SRDDataSourceConfig: Bundled SRD data configuration
- PrimaryDataOverrideConfig: Optional primary data override
- ExtensionDataSourceConfig: Extension data sources (homebrew, URLs)
- SourceAttributionConfig: Content attribution (separate concern)
- DataSourcesConfig: Complete data sources configuration
- ContentSource and ContentConfiguration: the directory and GitHub sources
  that the loaders read when no primary override is enabled

Architecture:
1. SRD Data: Always available bundled content
2. Primary Override: Optional 5etools-compatible replacement
3. Extensions: Additive homebrew and custom content
4. Attribution: Source metadata for content filtering
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class DataSourceType(str, Enum):
    """Types of data sources."""

    SRD = "srd"
    FIVE_TOOLS_COMPATIBLE = "5etools-compatible"
    DIRECTORY = "directory"
    FILE = "file"
    URL = "url"
    GIT = "git"


class SRDDataSourceConfig(BaseModel):
    """Configuration for bundled SRD data."""

    enabled: bool = Field(default=True, description="Whether SRD data is enabled")
    path: str = Field(default="bundled://srd-data", description="Path to SRD data")
    description: str = Field(default="System Reference Document content")


class PrimaryDataOverrideConfig(BaseModel):
    """Configuration for primary data override."""

    enabled: bool = Field(
        default=False, description="Whether primary override is enabled"
    )
    source: str | None = Field(None, description="Path or URL to primary data source")
    type: DataSourceType = Field(default=DataSourceType.FIVE_TOOLS_COMPATIBLE)
    branch: str | None = Field(None, description="Git branch (for git sources)")
    path: str | None = Field(
        None, description="Path within repository (for git sources)"
    )
    description: str | None = Field(
        None, description="Description of primary data source"
    )

    @field_validator("source")
    @classmethod
    def validate_source_when_enabled(cls, v: str | None, info: Any) -> str | None:
        """Validate that source is provided when enabled."""
        if info.data.get("enabled", False) and not v:
            raise ValueError("Primary override requires source when enabled")
        return v


class ExtensionDataSourceConfig(BaseModel):
    """Configuration for extension data source."""

    name: str = Field(..., description="Unique name for this extension")
    type: DataSourceType = Field(..., description="Type of extension source")
    source: str = Field(..., description="Path or URL to extension source")
    enabled: bool = Field(default=True, description="Whether extension is enabled")
    branch: str | None = Field(None, description="Git branch (for git sources)")
    path: str | None = Field(
        None, description="Path within repository (for git sources)"
    )
    description: str | None = Field(None, description="Description of extension")
    refresh_interval: int | None = Field(
        None, description="Refresh interval in seconds (for URL sources)"
    )


class SourceAttributionConfig(BaseModel):
    """Configuration for content source attribution."""

    default_priorities: dict[str, int] = Field(
        default_factory=lambda: {
            "SRD": 100,
            "PHB": 10,
            "MM": 20,
            "DMG": 30,
            "XGE": 40,
            "TCE": 50,
            "HOMEBREW": 1000,
        },
        description="Default priorities for source types",
    )

    custom_sources: dict[str, dict[str, Any]] = Field(
        default_factory=dict, description="Custom source configurations"
    )

    priority_resolution: Literal["highest", "lowest", "first", "last"] = Field(
        default="highest", description="How to resolve priority conflicts"
    )

    allow_duplicates: bool = Field(
        default=False,
        description="Whether to allow duplicate content from multiple sources",
    )

    show_source_info: bool = Field(
        default=True, description="Whether to include source info in output"
    )

    prefer_official: bool = Field(
        default=True, description="Whether to prefer official sources in searches"
    )


class DataSourcesConfig(BaseModel):
    """Complete data sources configuration."""

    # Three-tier configuration
    srd: SRDDataSourceConfig = Field(default_factory=lambda: SRDDataSourceConfig())
    primary_override: PrimaryDataOverrideConfig = Field(
        default_factory=lambda: PrimaryDataOverrideConfig()
    )
    extensions: list[ExtensionDataSourceConfig] = Field(default_factory=list)

    # Attribution configuration (separate concern)
    source_attribution: SourceAttributionConfig = Field(
        default_factory=lambda: SourceAttributionConfig()
    )

    # Performance settings
    performance: dict[str, Any] = Field(
        default_factory=lambda: {
            "caching": {
                "content_cache": {"enabled": True, "ttl": 3600, "max_entries": 10000},
                "index_cache": {"enabled": True, "ttl": 1800},
                "network_cache": {"enabled": True, "ttl": 300},
            },
            "memory": {
                "lazy_loading": True,
                "stream_large_files": True,
                "max_memory_usage": "512MB",
            },
        }
    )

    # Security settings
    security: dict[str, Any] = Field(
        default_factory=lambda: {
            "allowed_paths": [
                "~/Code/5etools-src/**",
                "~/.studiorum/**",
                "/opt/studiorum-data/**",
            ],
            "allowed_urls": [
                "https://github.com/**",
                "https://raw.githubusercontent.com/**",
            ],
            "ssl_verify": True,
            "timeout": 30,
            "max_file_size": "100MB",
            "max_total_size": "1GB",
        }
    )

    def get_enabled_extensions(self) -> list[ExtensionDataSourceConfig]:
        """Get list of enabled extension sources."""
        return [ext for ext in self.extensions if ext.enabled]

    def get_extension_by_name(self, name: str) -> ExtensionDataSourceConfig | None:
        """Get extension by name."""
        for ext in self.extensions:
            if ext.name == name:
                return ext
        return None

    def add_extension(self, extension: ExtensionDataSourceConfig) -> None:
        """Add a new extension source."""
        # Check for duplicate names
        if self.get_extension_by_name(extension.name):
            raise ValueError(f"Extension with name '{extension.name}' already exists")
        self.extensions.append(extension)

    def remove_extension(self, name: str) -> bool:
        """Remove an extension source by name."""
        for i, ext in enumerate(self.extensions):
            if ext.name == name:
                del self.extensions[i]
                return True
        return False

    def is_primary_enabled(self) -> bool:
        """Check if primary data override is enabled and configured."""
        return self.primary_override.enabled and bool(self.primary_override.source)

    def get_active_data_sources(self) -> list[str]:
        """Get list of active data source descriptions."""
        sources = []

        if self.srd.enabled:
            sources.append("SRD (bundled)")

        if self.is_primary_enabled():
            desc = self.primary_override.description or "Primary Override"
            sources.append(f"{desc} (primary)")

        for ext in self.get_enabled_extensions():
            desc = ext.description or ext.name
            sources.append(f"{desc} (extension)")

        return sources

    def validate_configuration(self) -> list[str]:
        """Validate configuration and return list of warnings/issues."""
        issues = []

        # Validate primary override
        if self.primary_override.enabled and not self.primary_override.source:
            issues.append("Primary override enabled but no source specified")

        # Validate extension sources
        for ext in self.extensions:
            if ext.enabled:
                if ext.type in [DataSourceType.DIRECTORY, DataSourceType.FILE]:
                    # Check if path exists (basic validation) - but only warn, don't error
                    try:
                        path = Path(ext.source).expanduser()
                        if not path.exists():
                            issues.append(
                                f"Extension '{ext.name}' source not found: {path} (warning)"
                            )
                    except Exception:
                        issues.append(
                            f"Extension '{ext.name}' has invalid path: {ext.source}"
                        )

                elif ext.type == DataSourceType.URL:
                    # Basic URL validation
                    if not ext.source.startswith(("http://", "https://")):
                        issues.append(
                            f"Extension '{ext.name}' has invalid URL: {ext.source}"
                        )

        # Validate source attribution
        if not self.source_attribution.default_priorities:
            issues.append("No source attribution priorities configured")

        # Check for duplicate extension names
        names = [ext.name for ext in self.extensions]
        if len(names) != len(set(names)):
            issues.append("Duplicate extension names found")

        return issues


class SourceType(str, Enum):
    """Types of content sources."""

    GITHUB = "github"
    DIRECTORY = "directory"
    WEB = "web"  # Future feature


class ContentSource(BaseModel):
    """Configuration for a content source."""

    name: str = Field(..., description="Unique name for this source")
    type: SourceType = Field(..., description="Type of content source")
    enabled: bool = Field(default=True, description="Whether this source is active")
    priority: int = Field(
        default=1, description="Priority order (lower = higher priority)"
    )

    # GitHub source fields
    url: str | None = Field(None, description="GitHub repository URL or web URL")
    branch: str | None = Field(default="master", description="Git branch to use")

    # Directory source fields
    path: str | Path | None = Field(None, description="Local directory path")

    # Update settings
    auto_update: bool = Field(
        default=True, description="Automatically update this source"
    )
    update_interval: str = Field(default="daily", description="Update frequency")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate source name is safe for filesystem."""
        if not v.replace("-", "").replace("_", "").isalnum():
            raise ValueError(
                "Source name must contain only alphanumeric characters, "
                "hyphens, and underscores"
            )
        return v

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str | None, info: Any) -> str | None:
        """Validate URL is provided for web/github sources."""
        if info.data.get("type") in [SourceType.GITHUB, SourceType.WEB] and not v:
            raise ValueError(f"URL is required for {info.data.get('type')} sources")
        return v

    @field_validator("path")
    @classmethod
    def validate_path(cls, v: str | Path | None, info: Any) -> Path | None:
        """Validate path is provided for directory sources."""
        if info.data.get("type") == SourceType.DIRECTORY:
            if not v:
                raise ValueError("Path is required for directory sources")
            return Path(v).expanduser().resolve()
        return Path(v).expanduser().resolve() if v else None


def _find_project_root() -> Path:
    """Find the directory holding test-data/ and srd-data/, starting from cwd."""
    current = Path.cwd()
    for candidate in [current, *current.parents]:
        if (candidate / "test-data").exists() and (candidate / "srd-data").exists():
            return candidate
    # Without a project root the default sources point at missing directories
    return current


def default_content_sources() -> list[ContentSource]:
    """The test-data and SRD directories of the nearest project root."""
    project_root = _find_project_root()
    return [
        ContentSource(
            name="test-data",
            type=SourceType.DIRECTORY,
            path=project_root / "test-data",
            priority=0,
        ),
        ContentSource(
            name="srd",
            type=SourceType.DIRECTORY,
            path=project_root / "srd-data",
            priority=1,
        ),
    ]


class ContentConfiguration(BaseModel):
    """The content sources the loaders read, with the directory for clones."""

    content_sources: list[ContentSource] = Field(
        default_factory=list, description="List of content sources"
    )
    cache_dir: Path = Field(
        default_factory=lambda: Path.home() / ".cache" / "studiorum",
        description="Cache directory",
    )

    def model_post_init(self, __context: Any) -> None:
        """Make sure the clone directory exists."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get_enabled_sources(self) -> list[ContentSource]:
        """Get list of enabled sources sorted by priority."""
        enabled = [source for source in self.content_sources if source.enabled]
        return sorted(enabled, key=lambda x: (x.priority, x.name))

    def get_source_by_name(self, name: str) -> ContentSource | None:
        """Get source by name."""
        for source in self.content_sources:
            if source.name == name:
                return source
        return None

    def add_source(self, source: ContentSource) -> None:
        """Add a new content source."""
        if self.get_source_by_name(source.name):
            raise ValueError(f"Source with name '{source.name}' already exists")
        self.content_sources.append(source)

    def remove_source(self, name: str) -> bool:
        """Remove a content source by name."""
        for i, source in enumerate(self.content_sources):
            if source.name == name:
                del self.content_sources[i]
                return True
        return False

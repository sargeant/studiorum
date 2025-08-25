"""Configuration models for three-tier data source architecture.

This module implements the new three-tier configuration system for data sources,
separating data repositories from content attribution as part of Package 4
configuration refactoring.

Key Components:
- SRDDataSourceConfig: Bundled SRD data configuration
- PrimaryDataOverrideConfig: Optional primary data override
- ExtensionDataSourceConfig: Extension data sources (homebrew, URLs)
- SourceAttributionConfig: Content attribution (separate concern)
- DataSourcesConfig: Complete data sources configuration

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

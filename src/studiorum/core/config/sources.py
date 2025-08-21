"""Content source configuration and management."""

import os
from enum import Enum
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator


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


class LaTeXFormattingConfig(BaseModel):
    """LaTeX formatting preferences."""

    paper_size: str | None = Field(
        default=None, description="Paper size (letter, a4, a5)"
    )
    fonts: str | None = Field(default=None, description="Font package (wotc, dmsguild)")
    no_outline: bool | None = Field(
        default=None, description="Disable document outline"
    )
    font_size: str | None = Field(
        default=None, description="Base font size (10pt, 11pt, 12pt)"
    )
    background: str | None = Field(
        default=None, description="Background style (full, none, print)"
    )
    high_contrast: bool | None = Field(
        default=None, description="Use high contrast mode"
    )
    two_column: bool | None = Field(default=None, description="Use two-column layout")
    justified: bool | None = Field(default=None, description="Justify text columns")


class ContentConfiguration(BaseModel):
    """Main content configuration."""

    version: str = Field(default="1.0", description="Configuration version")
    content_sources: list[ContentSource] = Field(
        default_factory=list, description="List of content sources"
    )

    # LaTeX formatting preferences
    latex: LaTeXFormattingConfig = Field(
        default_factory=LaTeXFormattingConfig,
        description="LaTeX formatting preferences",
    )

    # Cache and storage settings
    cache_dir: Path = Field(
        default_factory=lambda: Path.home() / ".cache" / "5e2pdf",
        description="Cache directory",
    )
    config_dir: Path = Field(
        default_factory=lambda: Path.home() / ".config" / "5e2pdf",
        description="Config directory",
    )

    # Global update settings
    auto_update_enabled: bool = Field(
        default=True, description="Enable automatic updates"
    )
    update_check_interval: str = Field(
        default="daily", description="How often to check for updates"
    )

    # Content processing settings
    parallel_downloads: int = Field(
        default=3, description="Number of parallel downloads"
    )
    content_index_ttl: int = Field(
        default=3600, description="Content index cache TTL in seconds"
    )

    def model_post_init(self, __context: Any) -> None:
        """Post-process configuration after parsing."""
        # Ensure directories exist
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.config_dir.mkdir(parents=True, exist_ok=True)

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
        # Check for duplicate names
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


class ContentConfigManager:
    """Manages loading and saving of content configuration."""

    def __init__(self, config_path: Path | None = None):
        """Initialize config manager."""
        if config_path is None:
            config_path = self._get_default_config_path()
        self.config_path = config_path
        self._config: ContentConfiguration | None = None

    def _get_default_config_path(self) -> Path:
        """Get the default configuration file path."""
        # Check for environment variable override first
        config_file = os.environ.get("DND5E_CONFIG_FILE")
        if config_file:
            return Path(config_file)

        # Cross-platform config directory
        if os.name == "nt":  # Windows
            config_dir = (
                Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
                / "5e2pdf"
            )
        else:  # Unix-like (macOS, Linux)
            config_dir = (
                Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
                / "5e2pdf"
            )

        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir / "config.yaml"

    def load_config(self) -> ContentConfiguration:
        """Load configuration from file or create default."""
        if self._config is not None:
            return self._config

        if not self.config_path.exists():
            self._config = self._create_default_config()
            self.save_config()
        else:
            try:
                with open(self.config_path, encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                self._config = ContentConfiguration.model_validate(data)
            except Exception as e:
                raise ValueError(
                    f"Failed to load configuration from {self.config_path}: {e}"
                )

        return self._config

    def save_config(self) -> None:
        """Save configuration to file."""
        if self._config is None:
            return

        # Ensure directory exists
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert to dict and handle Path objects
        data = self._config.model_dump(mode="json")

        with open(self.config_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

    def _create_default_config(self) -> ContentConfiguration:
        """Create default configuration with recommended sources."""
        config = ContentConfiguration()

        # Add test-data source (highest priority for testing)
        config.add_source(
            ContentSource(
                name="test-data",
                type=SourceType.DIRECTORY,
                path=Path("test-data"),
                enabled=True,
                priority=0,  # Highest priority
                url=None,
            )
        )

        # Add SRD source
        config.add_source(
            ContentSource(
                name="srd",
                type=SourceType.DIRECTORY,
                path=Path("srd-data"),
                enabled=True,
                priority=1,
                url=None,
            )
        )

        return config

    def get_config(self) -> ContentConfiguration:
        """Get current configuration."""
        return self.load_config()

    def update_config(self, config: ContentConfiguration) -> None:
        """Update configuration and save to file."""
        self._config = config
        self.save_config()

    def reset_to_defaults(self) -> ContentConfiguration:
        """Reset configuration to defaults."""
        self._config = self._create_default_config()
        self.save_config()
        return self._config


# Global config manager instance
_config_manager: ContentConfigManager | None = None


def get_config_manager() -> ContentConfigManager:
    """Get global configuration manager instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ContentConfigManager()
    return _config_manager


def get_content_config() -> ContentConfiguration:
    """Get current content configuration."""
    return get_config_manager().get_config()


def reset_config_manager() -> None:
    """Reset global config manager for testing."""
    import tempfile

    global _config_manager
    # Use a temporary directory for tests to avoid system config conflicts
    temp_dir = Path(tempfile.mkdtemp())
    _config_manager = ContentConfigManager(temp_dir / "test_config.yaml")

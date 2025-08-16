# Configuration System API Documentation

## Table of Contents

This page covers the configuration system APIs:

- [Settings](#settings)
- [LaTeX Configuration](#latex-configuration)
- [Content Sources](#content-sources)
- [Path Configuration](#path-configuration)
- [Environment Variables](#environment-variables)
- [Configuration Loading](#configuration-loading)
- [Validation](#validation)

## Overview

The configuration system provides comprehensive settings management for 5e2pdf, supporting environment variables, configuration files, and programmatic configuration. Built on Pydantic Settings, it offers type-safe configuration with validation and automatic environment variable binding.

### Key Features

- **Environment variable integration** with automatic type conversion
- **Configuration file support** (YAML, TOML, .env files)
- **Type-safe settings** with Pydantic validation
- **Hierarchical configuration** with override priorities
- **LaTeX-specific configuration** for document generation
- **Content source management** for data files

## Settings

**Location**: `src/dnd5e/core/config/settings.py`

Main application settings with environment variable support.

### Settings Class

```python
class Settings(BaseSettings):
    """Application settings with environment variable support."""

    # Logging configuration
    log_level: str = Field(default="WARNING", alias="LOG_LEVEL")
    log_format: str = Field(default="...", description="Log format string")

    # Data paths
    data_path: Path | None = Field(default=None, alias="DATA_PATH")
    assets_path: Path = Field(default=Path("assets"), alias="ASSETS_PATH")
    output_path: Path = Field(default=Path("output"), alias="OUTPUT_PATH")
    build_path: Path = Field(default=Path("build"), alias="BUILD_PATH")

    # Processing options
    max_workers: int = Field(default=4, alias="MAX_WORKERS")
    enable_caching: bool = Field(default=True, alias="ENABLE_CACHING")
    cache_ttl: int = Field(default=3600, alias="CACHE_TTL")

    # LaTeX options
    latex_engine: str = Field(default="lualatex", alias="LATEX_ENGINE")
    default_paper_size: str = Field(default="letterpaper", alias="DEFAULT_PAPER_SIZE")
    font_dir: Path | None = Field(default=None, alias="FONT_DIR")

    # Validation options
    validation_strictness: str = Field(default="normal", alias="VALIDATION_STRICTNESS")
    validation_summary: bool = Field(default=False, alias="VALIDATION_SUMMARY")
    max_duplicate_errors: int = Field(default=1, alias="MAX_DUPLICATE_ERRORS")
```

### Usage

#### Basic Settings

```python
from dnd5e.core.config.settings import Settings

# Load settings from environment and .env file
settings = Settings()

print(f"Log level: {settings.log_level}")
print(f"Data path: {settings.data_path}")
print(f"LaTeX engine: {settings.latex_engine}")
```

#### Environment Variable Override

```bash
# Set environment variables
export LOG_LEVEL=DEBUG
export DATA_PATH=/path/to/5etools/data
export LATEX_ENGINE=xelatex
export MAX_WORKERS=8

# Python will automatically use these values
python -c "from dnd5e.core.config.settings import Settings; print(Settings().log_level)"
# Output: DEBUG
```

#### Programmatic Configuration

```python
# Override settings programmatically
settings = Settings(
    log_level="INFO",
    data_path=Path("/custom/data/path"),
    max_workers=2,
    enable_caching=False
)

# Validate settings
if settings.validation_strictness not in ["strict", "normal", "lenient"]:
    raise ValueError("Invalid validation strictness")
```

### Configuration Model

```python
model_config = SettingsConfigDict(
    env_file=".env",              # Load from .env file
    env_file_encoding="utf-8",    # File encoding
    case_sensitive=False,         # Case-insensitive env vars
    env_prefix="",                # No prefix required
)
```

## LaTeX Configuration

**Location**: `src/dnd5e/core/config/latex_config.py`

Specialized configuration for LaTeX document generation.

### LaTeXDocumentConfig

```python
class LaTeXDocumentConfig(BaseModel):
    """Configuration for LaTeX document generation."""

    # Document class selection
    document_class: str = Field(default="dndbook")
    class_options: list[str] = Field(default_factory=lambda: ["justified", "twocolumn"])

    # Font configuration
    font_scheme: str = Field(default="dmsguild")

    # Paper and output
    paper_size: str = Field(default="letterpaper")
    font_size: str = Field(default="11pt")

    # Visual options
    background: str | None = Field(default=None)
    high_contrast: bool = Field(default=False)
    justified_text: bool = Field(default=True)
    fancy_headers: bool = Field(default=False)

    # Content options
    two_column: bool = Field(default=True)
    include_toc: bool = Field(default=True)
    include_index: bool = Field(default=False)

    # Custom options
    custom_class_options: list[str] = Field(default_factory=list)
```

### Usage Examples

#### Basic LaTeX Configuration

```python
from dnd5e.core.config.latex_config import LaTeXDocumentConfig

# Default configuration for D&D books
config = LaTeXDocumentConfig()
print(f"Document class: {config.document_class}")  # dndbook
print(f"Paper size: {config.paper_size}")          # letterpaper
print(f"Two column: {config.two_column}")          # True
```

#### Custom Document Configuration

```python
# Configuration for adventure handouts
adventure_config = LaTeXDocumentConfig(
    document_class="dndarticle",
    class_options=["bg", "justified"],
    paper_size="a4paper",
    font_size="10pt",
    background="print",
    two_column=False,
    include_toc=False,
    fancy_headers=True
)

# Configuration for high-contrast printing
print_config = LaTeXDocumentConfig(
    high_contrast=True,
    background=None,  # No background for printing
    justified_text=False,
    class_options=["justified", "twocolumn", "highcontrast"]
)
```

#### Font Scheme Configuration

```python
# Commercial fonts (requires font license)
commercial_config = LaTeXDocumentConfig(
    font_scheme="commercial",
    custom_class_options=["scaledfonts"]
)

# System fonts (uses system-installed fonts)
system_config = LaTeXDocumentConfig(
    font_scheme="system",
    document_class="dndarticle"  # Better system font support
)
```

### Validation

The LaTeX configuration includes comprehensive validation:

```python
# Document class validation
@field_validator("document_class")
@classmethod
def validate_document_class(cls, v: str) -> str:
    valid_classes = ["dndbook", "dndarticle"]
    if v not in valid_classes:
        raise ValueError(f"Document class must be one of: {valid_classes}")
    return v

# Font scheme validation
@field_validator("font_scheme")
@classmethod
def validate_font_scheme(cls, v: str) -> str:
    valid_schemes = ["dmsguild", "commercial", "system"]
    if v not in valid_schemes:
        raise ValueError(f"Font scheme must be one of: {valid_schemes}")
    return v
```

### Advanced Configuration

#### Template Engine Configuration

```python
class LaTeXTemplateConfig(BaseModel):
    """Configuration for LaTeX template engine."""

    template_debug: bool = Field(default=False)
    auto_reload: bool = Field(default=False)
    cache_size: int = Field(default=128)
    optimize_whitespace: bool = Field(default=True)

    # Custom delimiters
    variable_start: str = Field(default="<#")
    variable_end: str = Field(default="#>")
    block_start: str = Field(default="<@")
    block_end: str = Field(default="@>")
```

#### Engine Configuration

```python
class LaTeXEngineConfig(BaseModel):
    """Configuration for LaTeX engines."""

    preferred_engine: str = Field(default="lualatex")
    fallback_engines: list[str] = Field(default_factory=lambda: ["xelatex", "pdflatex"])

    # Engine-specific options
    lualatex_options: list[str] = Field(default_factory=lambda: [
        "-interaction=nonstopmode",
        "-file-line-error",
        "-synctex=1"
    ])

    xelatex_options: list[str] = Field(default_factory=lambda: [
        "-interaction=nonstopmode",
        "-file-line-error",
        "-synctex=1",
        "-shell-escape"
    ])
```

## Content Sources

**Location**: `src/dnd5e/core/config/sources.py`

Configuration for content data sources and automatic updates.

### Default Sources Configuration

**Location**: `src/dnd5e/core/config/unified_config.py`

The content configuration now includes default sources that are automatically used when no specific sources are provided to content collectors (spells, creatures, items).

#### ContentConfig

```python
class ContentConfig(BaseModel):
    """Content-related configuration settings."""

    default_sources: list[str] = Field(
        default_factory=lambda: ["xphb", "xmm", "xdmg"],
        description="Default source abbreviations used when none specified"
    )

    content_validation: str = Field(
        default="normal",
        description="Content validation level"
    )

    enable_content_tracking: bool = Field(
        default=True,
        description="Enable content tracking for appendices"
    )
```

#### Usage in Content Collection

```python
from dnd5e.cli.config_factory import get_default_sources
from dnd5e.core.services.creature_collector import CreatureCollector

# Automatic default source resolution
collector = CreatureCollector()

# When no sources specified, uses default sources
creatures = collector.collect_creatures_by_cr(1)  # Uses ["xphb", "xmm", "xdmg"]

# Explicit sources override defaults
creatures = collector.collect_creatures_by_cr(1, sources=["mm"])  # Uses only MM

# Helper function for default sources
default_sources = get_default_sources()
print(f"Default sources: {default_sources}")  # ["xphb", "xmm", "xdmg"]
```

#### Benefits

- **Consistent Behavior**: All content collectors use same default sources
- **Appendix Deduplication**: Eliminates duplicate content in appendices (e.g., "Skeleton" vs "skeleton")
- **User Convenience**: No need to specify sources for common use cases
- **Configurable**: Can be overridden via environment variables or configuration

#### Environment Configuration

```bash
# Override default sources via environment
export DND5E_CONTENT__DEFAULT_SOURCES='["phb", "mm", "dmg"]'

# Or in .env file
DND5E_CONTENT__DEFAULT_SOURCES=["phb","mm","dmg"]
```

### SourceType

```python
class SourceType(str, Enum):
    """Types of content sources."""

    GITHUB = "github"
    DIRECTORY = "directory"
    WEB = "web"  # Future feature
```

### ContentSource

```python
class ContentSource(BaseModel):
    """Configuration for a content source."""

    name: str = Field(..., description="Unique name for this source")
    type: SourceType = Field(..., description="Type of content source")
    enabled: bool = Field(default=True, description="Whether this source is active")
    priority: int = Field(default=1, description="Priority order (lower = higher priority)")

    # GitHub source fields
    url: str | None = Field(None, description="GitHub repository URL")
    branch: str | None = Field(default="master", description="Git branch to use")

    # Directory source fields
    path: str | Path | None = Field(None, description="Local directory path")

    # Update settings
    auto_update: bool = Field(default=True, description="Automatically update this source")
    update_interval: str = Field(default="daily", description="Update frequency")
```

### Usage Examples

#### GitHub Source Configuration

```python
from dnd5e.core.config.sources import ContentSource, SourceType

# Official 5etools data
official_source = ContentSource(
    name="5etools-official",
    type=SourceType.GITHUB,
    url="https://github.com/5etools-mirror-1/5etools-data",
    branch="master",
    priority=1,  # Highest priority
    auto_update=True
)

# Homebrew content
homebrew_source = ContentSource(
    name="5etools-homebrew",
    type=SourceType.GITHUB,
    url="https://github.com/TheGiddyLimit/homebrew",
    branch="master",
    priority=2,
    auto_update=False  # Manual updates only
)
```

#### Directory Source Configuration

```python
# Local data directory
local_source = ContentSource(
    name="local-data",
    type=SourceType.DIRECTORY,
    path="/path/to/local/5etools/data",
    priority=0,  # Highest priority (overrides others)
    enabled=True
)

# Development data
dev_source = ContentSource(
    name="dev-data",
    type=SourceType.DIRECTORY,
    path="./data/dev",
    priority=3,
    enabled=False  # Disabled by default
)
```

### ContentConfiguration

```python
class ContentConfiguration(BaseModel):
    """Main content configuration."""

    version: str = Field(default="1.0", description="Configuration version")
    content_sources: list[ContentSource] = Field(
        default_factory=list, description="List of content sources"
    )
```

#### Configuration File Example

```yaml
# content-sources.yaml
version: "1.0"
content_sources:
  - name: "5etools-official"
    type: "github"
    url: "https://github.com/5etools-mirror-1/5etools-data"
    branch: "master"
    priority: 1
    auto_update: true

  - name: "local-homebrew"
    type: "directory"
    path: "~/Documents/DnD/homebrew-data"
    priority: 2
    enabled: true
    auto_update: false
```

### Validation

Content sources include comprehensive validation:

```python
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
```

## Path Configuration

**Location**: `src/dnd5e/core/config/paths.py`

Standardized path management for application directories.

### Functions

#### get_config_dir

```python
def get_config_dir() -> Path
```

Gets the configuration directory following platform conventions.

**Returns:**
- `Path`: Configuration directory path

**Example:**
```python
from dnd5e.core.config.paths import get_config_dir

config_dir = get_config_dir()
# Linux: ~/.config/5e2pdf
# macOS: ~/Library/Application Support/5e2pdf
# Windows: %APPDATA%/5e2pdf
```

#### get_data_dir

```python
def get_data_dir() -> Path
```

Gets the data directory for content files.

#### get_cache_dir

```python
def get_cache_dir() -> Path
```

Gets the cache directory for temporary files.

### Usage Example

```python
from dnd5e.core.config.paths import get_config_dir, get_data_dir, get_cache_dir

# Setup application directories
config_dir = get_config_dir()
data_dir = get_data_dir()
cache_dir = get_cache_dir()

# Ensure directories exist
config_dir.mkdir(parents=True, exist_ok=True)
data_dir.mkdir(parents=True, exist_ok=True)
cache_dir.mkdir(parents=True, exist_ok=True)

# Use in configuration
settings = Settings(
    data_path=data_dir,
    build_path=cache_dir / "build"
)
```

## Environment Variables

Comprehensive environment variable support with automatic type conversion.

### Core Settings

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `LOG_LEVEL` | str | "WARNING" | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `DATA_PATH` | Path | None | Path to 5etools data files |
| `OUTPUT_PATH` | Path | "output" | Path for generated files |
| `CACHE_TTL` | int | 3600 | Cache time-to-live in seconds |
| `MAX_WORKERS` | int | 4 | Maximum worker processes |

### LaTeX Settings

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `LATEX_ENGINE` | str | "lualatex" | LaTeX engine (lualatex, xelatex, pdflatex) |
| `DEFAULT_PAPER_SIZE` | str | "letterpaper" | Default paper size |
| `FONT_DIR` | Path | None | Custom font directory |

### Validation Settings

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `VALIDATION_STRICTNESS` | str | "normal" | Validation mode (strict, normal, lenient) |
| `VALIDATION_SUMMARY` | bool | False | Enable validation summaries |
| `MAX_DUPLICATE_ERRORS` | int | 1 | Max duplicate error logs |

### Usage Examples

#### Shell Configuration

```bash
# Development environment
export LOG_LEVEL=DEBUG
export DATA_PATH=/home/user/5etools-data
export LATEX_ENGINE=xelatex
export MAX_WORKERS=2
export VALIDATION_STRICTNESS=strict

# Production environment
export LOG_LEVEL=WARNING
export ENABLE_CACHING=true
export CACHE_TTL=7200
export VALIDATION_STRICTNESS=normal
```

#### .env File

```bash
# .env file for development
LOG_LEVEL=DEBUG
DATA_PATH=./data/5etools
OUTPUT_PATH=./output
BUILD_PATH=./build
LATEX_ENGINE=lualatex
DEFAULT_PAPER_SIZE=letterpaper
ENABLE_CACHING=true
CACHE_TTL=3600
MAX_WORKERS=4
VALIDATION_STRICTNESS=normal
VALIDATION_SUMMARY=true
```

#### Docker Environment

```yaml
# docker-compose.yml
version: '3.8'
services:
  5e2pdf:
    image: 5e2pdf:latest
    environment:
      - LOG_LEVEL=INFO
      - DATA_PATH=/app/data
      - OUTPUT_PATH=/app/output
      - LATEX_ENGINE=xelatex
      - MAX_WORKERS=2
      - ENABLE_CACHING=true
    volumes:
      - ./data:/app/data
      - ./output:/app/output
```

## Configuration Loading

### Hierarchical Loading

Configuration is loaded in order of precedence:

1. **Command line arguments** (highest priority)
2. **Environment variables**
3. **Configuration files** (.env, config.yaml)
4. **Default values** (lowest priority)

### Loading Functions

#### load_settings

```python
def load_settings(config_file: Path | None = None) -> Settings:
    """Load settings with optional config file."""

    if config_file and config_file.exists():
        # Load from specific config file
        return Settings(_env_file=config_file)
    else:
        # Load from default locations
        return Settings()
```

#### load_latex_config

```python
def load_latex_config(settings: Settings) -> LaTeXDocumentConfig:
    """Load LaTeX configuration from settings."""

    return LaTeXDocumentConfig(
        latex_engine=settings.latex_engine,
        paper_size=settings.default_paper_size,
        # ... map other settings
    )
```

### Usage Examples

#### Application Startup

```python
from dnd5e.core.config.settings import Settings
from dnd5e.core.config.latex_config import LaTeXDocumentConfig

def initialize_application():
    """Initialize application with configuration."""

    # Load main settings
    settings = Settings()

    # Setup logging
    setup_logging(settings.log_level)

    # Load LaTeX configuration
    latex_config = LaTeXDocumentConfig(
        paper_size=settings.default_paper_size
    )

    # Validate data path
    if settings.data_path and not settings.data_path.exists():
        raise FileNotFoundError(f"Data path not found: {settings.data_path}")

    return settings, latex_config
```

#### Configuration Override

```python
def create_custom_config(overrides: dict[str, Any]) -> Settings:
    """Create settings with custom overrides."""

    # Start with defaults
    settings = Settings()

    # Apply overrides
    for key, value in overrides.items():
        if hasattr(settings, key):
            setattr(settings, key, value)
        else:
            raise ValueError(f"Unknown setting: {key}")

    return settings

# Usage
custom_settings = create_custom_config({
    "log_level": "DEBUG",
    "max_workers": 1,
    "enable_caching": False
})
```

## Validation

### Settings Validation

```python
from pydantic import ValidationError
from dnd5e.core.config.settings import Settings

def validate_settings(settings_dict: dict[str, Any]) -> Settings:
    """Validate settings dictionary."""

    try:
        settings = Settings(**settings_dict)

        # Additional validation
        if settings.max_workers < 1:
            raise ValueError("max_workers must be at least 1")

        if settings.cache_ttl < 0:
            raise ValueError("cache_ttl must be non-negative")

        return settings

    except ValidationError as e:
        print("Configuration validation errors:")
        for error in e.errors():
            print(f"  {error['loc'][0]}: {error['msg']}")
        raise
```

### LaTeX Configuration Validation

```python
def validate_latex_config(config: LaTeXDocumentConfig) -> None:
    """Validate LaTeX configuration compatibility."""

    # Check document class and options compatibility
    if config.document_class == "dndarticle" and config.two_column:
        raise ValueError("dndarticle class doesn't support two_column option")

    # Validate font scheme and document class compatibility
    if config.font_scheme == "commercial" and config.document_class != "dndbook":
        raise ValueError("Commercial fonts require dndbook document class")

    # Check paper size and font size compatibility
    if config.paper_size == "a5paper" and config.font_size == "12pt":
        raise ValueError("12pt font too large for A5 paper")
```

### Content Source Validation

```python
def validate_content_sources(sources: list[ContentSource]) -> None:
    """Validate content source configuration."""

    # Check for duplicate names
    names = [source.name for source in sources]
    if len(names) != len(set(names)):
        raise ValueError("Content source names must be unique")

    # Validate GitHub sources
    for source in sources:
        if source.type == SourceType.GITHUB:
            if not source.url:
                raise ValueError(f"GitHub source {source.name} requires URL")
            if not source.url.startswith("https://github.com/"):
                raise ValueError(f"Invalid GitHub URL: {source.url}")

        elif source.type == SourceType.DIRECTORY:
            if not source.path:
                raise ValueError(f"Directory source {source.name} requires path")
            if not source.path.exists():
                raise ValueError(f"Directory not found: {source.path}")
```

## Usage Examples

### Complete Configuration Setup

```python
from pathlib import Path
from dnd5e.core.config.settings import Settings
from dnd5e.core.config.latex_config import LaTeXDocumentConfig
from dnd5e.core.config.sources import ContentSource, SourceType

def setup_application_config():
    """Setup complete application configuration."""

    # Load main settings
    settings = Settings()

    # Create LaTeX configuration for book generation
    latex_config = LaTeXDocumentConfig(
        document_class="dndbook",
        class_options=["bg", "justified", "twocolumn"],
        paper_size=settings.default_paper_size,
        font_scheme="dmsguild",
        include_toc=True,
        include_index=False
    )

    # Setup content sources
    sources = [
        ContentSource(
            name="official-data",
            type=SourceType.GITHUB,
            url="https://github.com/5etools-mirror-1/5etools-data",
            priority=1,
            auto_update=True
        ),
        ContentSource(
            name="local-data",
            type=SourceType.DIRECTORY,
            path=settings.data_path or Path("./data"),
            priority=0,  # Higher priority than GitHub
            enabled=True
        )
    ]

    return settings, latex_config, sources

# Initialize application
app_settings, app_latex_config, app_sources = setup_application_config()
```

### Environment-Specific Configuration

```python
def get_environment_config(environment: str):
    """Get configuration for specific environment."""

    if environment == "development":
        return Settings(
            log_level="DEBUG",
            enable_caching=False,
            max_workers=1,
            validation_strictness="strict"
        )

    elif environment == "testing":
        return Settings(
            log_level="WARNING",
            enable_caching=True,
            cache_ttl=60,  # Short cache for tests
            max_workers=2,
            validation_strictness="strict"
        )

    elif environment == "production":
        return Settings(
            log_level="WARNING",
            enable_caching=True,
            cache_ttl=3600,
            max_workers=4,
            validation_strictness="normal"
        )

    else:
        raise ValueError(f"Unknown environment: {environment}")

# Usage
import os
env = os.getenv("ENVIRONMENT", "development")
config = get_environment_config(env)
```

### Configuration Debugging

```python
def debug_configuration(settings: Settings):
    """Print configuration for debugging."""

    print("=== Configuration Debug Info ===")
    print(f"Log level: {settings.log_level}")
    print(f"Data path: {settings.data_path}")
    print(f"Output path: {settings.output_path}")
    print(f"LaTeX engine: {settings.latex_engine}")
    print(f"Max workers: {settings.max_workers}")
    print(f"Caching enabled: {settings.enable_caching}")
    print(f"Cache TTL: {settings.cache_ttl} seconds")
    print(f"Validation strictness: {settings.validation_strictness}")

    # Check paths exist
    if settings.data_path:
        print(f"Data path exists: {settings.data_path.exists()}")

    print(f"Output path exists: {settings.output_path.exists()}")
    print("================================")

# Usage
debug_configuration(Settings())
```

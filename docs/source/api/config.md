# Configuration Management

Configuration system for customizing 5e2pdf behavior.

## Settings

Core application settings and configuration.

```{eval-rst}
.. automodule:: dnd5e.core.config.settings
   :members:
   :undoc-members:
   :show-inheritance:
```

**Example Usage:**

```python
from dnd5e.core.config import get_settings, Settings

# Get current settings
settings = get_settings()
print(f"Data directory: {settings.data_dir}")
print(f"Cache enabled: {settings.enable_cache}")

# Create custom settings
custom_settings = Settings(
    data_dir="/custom/data/path",
    enable_cache=False,
    log_level="DEBUG"
)
```

## Path Configuration

```{eval-rst}
.. automodule:: dnd5e.core.config.paths
   :members:
   :undoc-members:
   :show-inheritance:
```

## LaTeX Configuration

LaTeX-specific configuration options for PDF generation.

**Example LaTeX Configuration:**
```python
from dnd5e.core.config.settings import Settings

settings = Settings(
    latex_engine="lualatex",
    paper_size="letter",
    columns=2,
    font_family="Times"
)
```

## Source Configuration

Content source configuration and management.

**Example Source Configuration:**
```python
from dnd5e.core.config.settings import Settings

settings = Settings(
    default_sources=["PHB", "MM", "DMG"],
    source_priority="newest",
    validate_sources=True
)
```

## Configuration Hierarchy

Settings are loaded in the following order (later values override earlier ones):

1. **Default values** (built into the application)
2. **System configuration** (`/etc/5e2pdf/config.yaml`)
3. **User configuration** (`~/.5e2pdf/config.yaml`)
4. **Project configuration** (`./5e2pdf.yaml`)
5. **Environment variables** (prefixed with `DND5E_`)
6. **Command-line arguments** (highest priority)

### Configuration Files

#### User Configuration (`~/.5e2pdf/config.yaml`)

```yaml
# Data and caching
data_dir: "~/.5e2pdf/data"
cache_dir: "~/.5e2pdf/cache"
enable_cache: true
cache_ttl: 86400  # 24 hours

# Logging
log_level: "INFO"
log_file: "~/.5e2pdf/logs/app.log"

# LaTeX settings
latex:
  engine: "lualatex"
  paper_size: "letter"
  font_family: "Times"
  font_size: 10
  columns: 2
  margins:
    top: "2cm"
    bottom: "2cm"
    left: "1.5cm"
    right: "1.5cm"

# Source settings
sources:
  default: "5etools"
  update_interval: 604800  # 1 week
  validate_on_load: true
```

#### Project Configuration (`./5e2pdf.yaml`)

```yaml
# Project-specific overrides
output_dir: "./output"
template_dir: "./templates"

# Content filtering
default_sources: ["PHB", "MM", "DMG"]
exclude_content_types: ["variant", "reprint"]

# Rendering preferences
latex:
  columns: 1
  paper_size: "A4"
  include_toc: true
  include_index: true
```

### Environment Variables

All settings can be overridden with environment variables:

```bash
# Data configuration
export DND5E_DATA_DIR="/opt/5e2pdf/data"
export DND5E_CACHE_ENABLED=false

# LaTeX configuration
export DND5E_LATEX_ENGINE="pdflatex"
export DND5E_LATEX_PAPER_SIZE="A4"
export DND5E_LATEX_COLUMNS=1

# Logging
export DND5E_LOG_LEVEL="DEBUG"
export DND5E_LOG_FILE="/var/log/5e2pdf.log"
```

## Configuration Validation

Settings are validated using Pydantic:

```python
from pydantic import ValidationError
from dnd5e.core.config import Settings

try:
    settings = Settings(
        log_level="INVALID_LEVEL",  # Will raise validation error
        cache_ttl=-1                # Will raise validation error
    )
except ValidationError as e:
    print(f"Configuration error: {e}")
```

## Dynamic Configuration

### Runtime Configuration Changes

```python
from dnd5e.core.config import get_settings

# Get mutable settings instance
settings = get_settings()

# Modify settings at runtime
settings.log_level = "DEBUG"
settings.enable_cache = False

# Changes take effect immediately
```

### Context-Specific Configuration

```python
from dnd5e.core.config import with_settings

# Temporary configuration override
with with_settings(log_level="DEBUG", enable_cache=False):
    # Code runs with modified settings
    omnidexer = Omnidexer()  # Uses DEBUG logging, no cache

# Settings restored after context
```

## Configuration Profiles

```python
from dnd5e.core.config import Settings, load_profile

# Development profile
dev_settings = load_profile("development")
assert dev_settings.log_level == "DEBUG"
assert dev_settings.enable_cache == False

# Production profile
prod_settings = load_profile("production")
assert prod_settings.log_level == "WARNING"
assert prod_settings.enable_cache == True

# Custom profile
custom_settings = load_profile("custom", {
    "data_dir": "/custom/path",
    "latex": {"columns": 3}
})
```

## LaTeX-Specific Configuration

### Paper and Output

```python
from dnd5e.core.config.latex import LaTeXConfig

latex_config = LaTeXConfig(
    paper_size="A4",        # A4, letter, legal, A3, A5
    orientation="portrait", # portrait, landscape
    columns=2,              # 1, 2, 3
    column_sep="1cm",       # Space between columns
    margins={
        "top": "2.5cm",
        "bottom": "2.5cm",
        "left": "2cm",
        "right": "2cm"
    }
)
```

### Fonts and Typography

```python
latex_config = LaTeXConfig(
    font_family="Times",     # Times, Helvetica, Computer Modern
    font_size=10,           # Base font size in points
    line_spacing=1.2,       # Line spacing multiplier
    paragraph_spacing="0.5em",
    fonts={
        "title": {"family": "Helvetica", "size": 16, "weight": "bold"},
        "heading": {"family": "Helvetica", "size": 12, "weight": "bold"},
        "body": {"family": "Times", "size": 10},
        "caption": {"family": "Helvetica", "size": 9, "style": "italic"}
    }
)
```

### Document Structure

```python
latex_config = LaTeXConfig(
    include_toc=True,        # Table of contents
    include_index=True,      # Alphabetical index
    include_bookmarks=True,  # PDF bookmarks
    number_sections=True,    # Section numbering
    toc_depth=3,            # TOC depth
    section_breaks={
        "chapter": "page",   # Page break before chapters
        "section": "column", # Column break before sections
        "subsection": "none" # No break before subsections
    }
)
```

## Advanced Configuration

### Custom Configuration Sources

```python
from dnd5e.core.config import ConfigSource

class DatabaseConfigSource(ConfigSource):
    """Load configuration from database."""

    def load_config(self) -> dict:
        # Load from database
        return {"log_level": "INFO", "enable_cache": True}

# Register custom source
register_config_source("database", DatabaseConfigSource())
```

### Configuration Watching

```python
from dnd5e.core.config import watch_config

def on_config_change(old_settings, new_settings):
    """Called when configuration changes."""
    print(f"Log level changed: {old_settings.log_level} -> {new_settings.log_level}")

# Watch for configuration file changes
watch_config(callback=on_config_change)
```

### Configuration File Validation

```python
from dnd5e.core.config import validate_config

# Validate configuration before use
try:
    validate_config("~/.5e2pdf/config.yaml")
    print("Configuration is valid")
except ValidationError as e:
    print(f"Configuration errors: {e}")
```

See {doc}`/user-guide/installation` for initial setup and {doc}`/user-guide/advanced-features` for advanced configuration scenarios.

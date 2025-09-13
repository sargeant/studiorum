# Configuration Guide

This guide covers all configuration options available in Studiorum, from basic usage to advanced customization.

## Configuration Methods

Studiorum can be configured in three ways, with the following priority order (highest to lowest):

1. **Command-line arguments** - Override specific settings for individual commands
2. **Configuration file** - Persistent settings in `studiorum.yaml`
3. **Environment variables** - System-wide settings

## Configuration File

### Location and Setup

Create a `studiorum.yaml` file in your project directory or home directory:

```bash
# Project-specific configuration
./studiorum.yaml

# User-wide configuration
~/.studiorum/studiorum.yaml
```

### Basic Configuration

```yaml
# Basic studiorum.yaml
data_sources:
  primary_override:
    enabled: true
    source: "~/Code/5etools-src/data"

rendering:
  include_images: true
  output_format: "latex"

images:
  image_directory: "~/Code/5etools-img"
  image_quality: "print"
```

## Data Sources Configuration

Configure where Studiorum finds 5e content data.

### Three-Tier Data Architecture

```yaml
data_sources:
  # Tier 1: SRD (always available, bundled with Studiorum)
  srd:
    enabled: true

  # Tier 2: Primary Override (optional, high-quality data)
  primary_override:
    enabled: true
    source: "~/Code/5etools-src/data"
    type: "five_tools_compatible"

  # Tier 3: Extensions (homebrew, additional content)
  extensions:
    - name: "homebrew-spells"
      type: "directory"
      source: "~/homebrew/spells"
    - name: "custom-content"
      type: "url"
      source: "https://example.com/homebrew.json"

  # Source Attribution (which 5e books content belongs to)
  source_attribution:
    default_priorities:
      SRD: 100
      HOMEBREW: 1000
    priority_resolution: "highest"
```

### Data Source Types

**five_tools_compatible**: Full 5etools data repository
```yaml
primary_override:
  enabled: true
  source: "~/Code/5etools-src/data"
  type: "five_tools_compatible"
```

**directory**: Local directory with JSON files
```yaml
extensions:
  - name: "homebrew"
    type: "directory"
    source: "~/my-homebrew/"
```

**url**: Remote JSON file or API endpoint
```yaml
extensions:
  - name: "remote-content"
    type: "url"
    source: "https://api.example.com/spells.json"
```

## Rendering Configuration

Control how content is processed and output.

### Basic Rendering Settings

```yaml
rendering:
  # Output format
  output_format: "latex"  # latex, markdown

  # Content inclusion
  include_images: true
  include_fluff: false
  include_appendices: true

  # Quality settings
  content_quality: "high"  # low, medium, high

  # LaTeX-specific settings
  latex:
    document_class: "dndbook"
    geometry: "a4paper"
    font_size: "10pt"
```

### Template Customization

```yaml
rendering:
  templates:
    # Custom template directory
    template_directory: "~/my-templates"

    # Template overrides
    overrides:
      creature: "custom-creature.tex.j2"
      spell: "custom-spell.tex.j2"

    # Template variables
    variables:
      campaign_name: "My Campaign"
      author: "Your Name"
      date: "2024"
```

### Content Processing

```yaml
rendering:
  content:
    # Text processing
    process_tags: true
    resolve_references: true
    generate_index: true

    # Fluff content
    include_fluff: true
    fluff_placement: "inline"  # inline, appendix, separate

    # Cross-references
    cross_reference_format: "page"  # page, section, both
```

## Images Configuration

Configure image processing and placement.

### Basic Image Settings

```yaml
images:
  # Image directory
  image_directory: "~/Code/5etools-img"

  # Processing options
  include_images: true
  image_quality: "print"  # digital, print, hybrid
  image_placement: "intelligent"  # intelligent, simple

  # Performance
  preload_images: true
  enable_image_cache: true
  max_concurrent_downloads: 5
```

### Content-Specific Images

```yaml
images:
  # Control image types
  bestiary_images: true
  item_images: true
  adventure_images: true
  chapter_art: true

  # Gallery settings
  gallery_layout: "grid"  # grid, showcase, sequential, comparison

  # Sizing and placement
  max_width_percent: 80
  max_height_percent: 60

  # Format handling
  preserve_transparency: false
  background_color: "#f9f7f1"
```

### Image Sources

```yaml
image_sources:
  - name: "5etools-official"
    source_type: "git_repo"
    git_repo_url: "https://github.com/5etools-mirror-3/5etools-img.git"
    priority: 10
    cache_ttl_hours: 168

  - name: "user-assets"
    source_type: "local_dir"
    local_path: "~/5e/custom-artwork"
    priority: 5  # Higher priority than official

  - name: "fallback-web"
    source_type: "http_api"
    base_url: "https://5e.tools/img"
    priority: 50
```

## Logging Configuration

Control debug output and logging behavior.

### Basic Logging

```yaml
logging:
  # Log level
  level: "INFO"  # DEBUG, INFO, WARNING, ERROR

  # Output destination
  output: "console"  # console, file, both

  # Log file settings (if output includes file)
  file_path: "~/.studiorum/logs/studiorum.log"
  max_file_size: "10MB"
  backup_count: 5
```

### Advanced Logging

```yaml
logging:
  # Component-specific levels
  components:
    image_processor: "DEBUG"
    latex_engine: "INFO"
    content_merger: "WARNING"

  # Performance logging
  performance:
    enabled: true
    log_slow_operations: true
    slow_operation_threshold: 5.0  # seconds

  # Integration logging (Logfire)
  logfire:
    enabled: true
    project_token: "your-token-here"
```

## Environment Variables

Override configuration using environment variables.

### Common Environment Variables

```bash
# Data sources
export STUDIORUM_DATA_SOURCES__PRIMARY_OVERRIDE__SOURCE="~/Code/5etools-src/data"
export STUDIORUM_DATA_SOURCES__PRIMARY_OVERRIDE__ENABLED=true

# Images
export STUDIORUM_IMAGE__IMAGE_DIRECTORY="~/Code/5etools-img"
export STUDIORUM_IMAGE__INCLUDE_IMAGES=true
export STUDIORUM_IMAGE__IMAGE_QUALITY="print"

# Logging
export STUDIORUM_LOGGING_LEVEL="DEBUG"
export STUDIORUM_PROGRESS=false  # Disable progress bars

# Performance
export STUDIORUM_DEBUG_TRACEBACK=true  # Full error tracebacks
```

### Variable Naming Convention

Environment variables follow this pattern:
```
STUDIORUM_<SECTION>__<SUBSECTION>__<SETTING>=value
```

Examples:
- `STUDIORUM_IMAGES__INCLUDE_IMAGES=true`
- `STUDIORUM_RENDERING__OUTPUT_FORMAT="latex"`
- `STUDIORUM_LOGGING__LEVEL="DEBUG"`

## Command-Line Overrides

Override any configuration setting using command-line flags.

### Common CLI Options

```bash
# Image settings
studiorum convert adventure cos --images --image-quality print
studiorum convert creatures --bestiary-images --no-item-images

# Data source overrides
studiorum convert spells --sources srd phb xge

# Output settings
studiorum convert adventure --output custom-name.tex
studiorum convert creatures --format latex

# Performance options
studiorum convert adventure --preload-images --image-cache
```

### Debug and Troubleshooting

```bash
# Enable debug logging for single command
STUDIORUM_LOGGING_LEVEL=DEBUG studiorum convert adventure cos

# Disable progress bars
STUDIORUM_PROGRESS=false studiorum convert adventure cos

# Full error tracebacks
STUDIORUM_DEBUG_TRACEBACK=true studiorum convert adventure cos
```

## Complete Configuration Example

Here's a comprehensive `studiorum.yaml` example:

```yaml
# Complete studiorum.yaml configuration
data_sources:
  srd:
    enabled: true

  primary_override:
    enabled: true
    source: "~/Code/5etools-src/data"
    type: "five_tools_compatible"

  extensions:
    - name: "homebrew-content"
      type: "directory"
      source: "~/homebrew/"

  source_attribution:
    default_priorities:
      SRD: 100
      HOMEBREW: 1000
    priority_resolution: "highest"

rendering:
  output_format: "latex"
  include_images: true
  include_fluff: true
  include_appendices: true

  content:
    process_tags: true
    resolve_references: true
    generate_index: true

  latex:
    document_class: "dndbook"
    geometry: "a4paper"
    font_size: "10pt"

images:
  image_directory: "~/Code/5etools-img"
  include_images: true
  image_quality: "print"
  image_placement: "intelligent"

  preload_images: true
  enable_image_cache: true
  max_concurrent_downloads: 5

  bestiary_images: true
  item_images: true
  adventure_images: true
  chapter_art: true

  gallery_layout: "grid"

image_sources:
  - name: "5etools-official"
    source_type: "git_repo"
    git_repo_url: "https://github.com/5etools-mirror-3/5etools-img.git"
    priority: 10

  - name: "user-assets"
    source_type: "local_dir"
    local_path: "~/5e/custom-artwork"
    priority: 5

logging:
  level: "INFO"
  output: "console"

  performance:
    enabled: true
    log_slow_operations: true
    slow_operation_threshold: 5.0
```

## Configuration Validation

### Check Current Configuration

```bash
# Show all current settings
studiorum config show

# Show specific sections
studiorum config show --section images
studiorum config show --section data_sources

# Validate configuration
studiorum config validate
```

### Common Configuration Issues

**Data source not found:**
```bash
# Check if primary override path exists
ls ~/Code/5etools-src/data/

# Verify SRD fallback is enabled
studiorum config show --section data_sources.srd
```

**Image processing fails:**
```bash
# Check image directory exists
ls ~/Code/5etools-img/

# Verify environment variable is set
echo $STUDIORUM_IMAGE__IMAGE_DIRECTORY

# Test with single item
studiorum convert items "Bag of Holding" --images
```

**LaTeX compilation errors:**
```bash
# Check LaTeX installation
pdflatex --version

# Test without images first
studiorum convert adventure cos --no-images
```

## Migration and Upgrades

### Upgrading Configuration

When upgrading Studiorum, your configuration may need updates:

```bash
# Backup current config
cp studiorum.yaml studiorum.yaml.backup

# Check for breaking changes
studiorum config migrate --check

# Apply automatic migrations
studiorum config migrate --apply
```

### Legacy Configuration

Studiorum maintains backward compatibility with older config formats:

```yaml
# Legacy format (still supported)
data_directory: "~/Code/5etools-src/data"
image_directory: "~/Code/5etools-img"

# New format (recommended)
data_sources:
  primary_override:
    source: "~/Code/5etools-src/data"
images:
  image_directory: "~/Code/5etools-img"
```

---

For troubleshooting configuration issues, see [Troubleshooting](troubleshooting.md). For advanced development configuration, see the [Developer Guide](../developer-guide/getting-started.md).

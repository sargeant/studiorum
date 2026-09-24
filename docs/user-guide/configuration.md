# Configuration Guide

This guide covers all configuration options available in Studiorum, from basic usage to advanced customization.

## Configuration Methods

Studiorum reads its settings from, highest priority first:

1. **Environment variables** (`STUDIORUM_*`)
2. **The configuration file**
3. **Defaults**

Command-line options override all three for the command they are given to.

## Configuration File

### Location

Studiorum reads `~/.studiorum/config.yaml`. Name another file with
`studiorum -c path/to/config.yaml` or the `STUDIORUM_CONFIG_FILE` environment
variable; a file named either way must exist.

### Basic Configuration

```yaml
data:
  dirs:
    - ~/Code/5etools-src/data

image:
  image_directory: ~/Code/5etools-img
```

## Data Configuration

The `data` section says where the 5e content comes from.

```yaml
data:
  # 5etools-shaped data directories, highest priority first
  dirs:
    - ~/Code/5etools-src/data
  # Homebrew JSON files, or directories of them, loaded after the dirs
  homebrew:
    - ~/homebrew/my-creatures.json
    - ~/homebrew/campaign/
```

`dirs` are directories laid out like the `data/` folder of a 5etools checkout:
top-level files such as `spells.json` and `items.json`, and `bestiary/`,
`spells/` and `class/` folders whose `index.json` files list their contents.
Adventure and book text in `adventure/` and `book/` is read when an adventure or
book is converted. `homebrew` files are in the 5etools homebrew format.

When two entities have the same type, name and source, the first one loaded
wins: dirs in the order given, then homebrew.

Without a `data` section, Studiorum uses the repository's `test-data/` and
`srd-data/` if it is run from inside the repository.

Check what is configured with `studiorum data show`, or `studiorum doctor`.

## Rendering Configuration

Control how content is processed and output.

### Basic Rendering Settings

```yaml
rendering:
  # Output format
  output_format: "latex"  # latex, markdown

  # Content inclusion
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

Three settings control images. See [Images](images.md) for how they are used.

```yaml
image:
  # Include images when a convert command has neither --images nor --no-images
  include_images: false

  # A 5etools-img checkout. Defaults to ~/Code/5etools-img when that exists.
  image_directory: ~/Code/5etools-img

  # Where converted PNGs and downloaded images go (default: <cache>/images)
  cache_dir: null
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
- `STUDIORUM_IMAGE__INCLUDE_IMAGES=true`
- `STUDIORUM_RENDERING__OUTPUT_FORMAT="latex"`
- `STUDIORUM_LOGGING__LEVEL="DEBUG"`

## Command-Line Overrides

Override any configuration setting using command-line flags.

### Common CLI Options

```bash
# Images
studiorum convert adventure cos --images

# Data source overrides
studiorum convert spells --sources srd phb xge

# Output settings
studiorum convert adventure --output custom-name.tex
studiorum convert creatures --format latex
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
data:
  dirs:
    - ~/Code/5etools-src/data
  homebrew:
    - ~/homebrew/

rendering:
  output_format: "latex"
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

image:
  image_directory: ~/Code/5etools-img
  include_images: true

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
studiorum data show

# Check the configuration, data and cache
studiorum doctor
```

### Common Configuration Issues

**Data not found:**
```bash
# List the data directories and homebrew, with their file counts
studiorum data show
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

### From data_sources and content_sources

The `data_sources` and `content_sources` sections were replaced by `data`.
Studiorum stops with an error naming the replacement if it finds them. Move the
directory from `data_sources.primary_override.source` (or the directory
`content_sources`) into `data.dirs`, and each extension's `source` into
`data.homebrew`. GitHub and URL sources are gone: clone or download them and
list the local path.

---

For troubleshooting configuration issues, see [Troubleshooting](troubleshooting.md). For advanced development configuration, see the [Developer Guide](../developer-guide/getting-started.md).

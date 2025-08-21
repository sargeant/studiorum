# Configuration Reference

This guide covers all configuration options for 5e2pdf, including environment variables, configuration files, and command-line options.

## Configuration Hierarchy

5e2pdf uses a layered configuration system with the following precedence (highest to lowest):

1. **Command-line arguments** - Override all other settings
2. **Environment variables** - Override config files
3. **User config file** - `~/.5e2pdf/config.yaml`
4. **Project config file** - `./5e2pdf.yaml` or `./test-config.yaml`
5. **Default values** - Built-in defaults

## Environment Variables

### Core Configuration

```bash
# Data and Source Paths
export DND5E_DATA_PATH=/path/to/5etools/data  # Location of 5etools JSON data
export DND5E_CONFIG_FILE=test-config.yaml     # Use custom config file
export DND5E_CACHE_DIR=~/.5e2pdf/cache       # Cache directory location
export DND5E_OUTPUT_DIR=./output             # Default output directory

# Processing Options
export DND5E_MAX_WORKERS=4                   # Parallel processing threads
export DND5E_TIMEOUT=300                     # Operation timeout in seconds
export DND5E_MEMORY_LIMIT=2048              # Memory limit in MB
```

### Debug and Development

```bash
# Debug Flags
export DND5E_DEBUG=1                         # Enable debug mode globally
export DND5E_DEBUG_ENTRY_PROCESSING=1        # Show detailed entry processing
export DND5E_STRICT_ENTRY_PROCESSING=1       # Fail on unknown entry types
export DND5E_DISABLE_TAG_FALLBACK=1          # Show raw tags when resolution fails

# Logging
export DND5E_LOG_LEVEL=DEBUG                 # Set log level (DEBUG, INFO, WARNING, ERROR)
export DND5E_LOG_FILE=~/.5e2pdf/debug.log   # Custom log file location
export DND5E_LOG_FORMAT=json                 # Log format (text, json)
```

### LaTeX Configuration

```bash
# LaTeX Engine Settings
export DND5E_LATEX_ENGINE=lualatex          # LaTeX engine (pdflatex, xelatex, lualatex)
export DND5E_LATEX_QUIET=1                  # Suppress LaTeX output
export DND5E_LATEX_VERBOSE=1                # Show all LaTeX output
export DND5E_LATEX_TEMPLATE_PATH=~/dnd-template  # Path to DND-5e-LaTeX-Template

# LaTeX Processing
export DND5E_LATEX_RUNS=2                   # Number of LaTeX compilation runs
export DND5E_LATEX_INTERACTION=nonstopmode  # LaTeX interaction mode
export DND5E_LATEX_SHELL_ESCAPE=1          # Enable shell escape for LaTeX
```

### Testing

```bash
# Test Configuration
export DND5E_TEST_MODE=1                    # Enable test mode
export DND5E_TEST_DATA_PATH=./test-data    # Test data location
export DND5E_TEST_FAST=1                   # Skip slow tests
export DND5E_TEST_PARALLEL=0               # Disable parallel test execution
```

## Configuration File Format

### Basic Structure

```yaml
# ~/.5e2pdf/config.yaml or ./5e2pdf.yaml

# Version for config compatibility checking
version: "1.0"

# Source configuration
sources:
  default:
    - phb
    - dmg
    - mm

  custom:
    path: ~/my-homebrew
    enabled: true

# Data paths
paths:
  data: ~/5etools-data/data
  cache: ~/.5e2pdf/cache
  output: ./output
  templates: ~/dnd-template

# Processing options
processing:
  max_workers: 4
  timeout: 300
  memory_limit: 2048
  batch_size: 100

# LaTeX configuration
latex:
  engine: lualatex
  template: DND-5e-LaTeX-Template
  runs: 2
  quiet: false
  verbose: false
  interaction: nonstopmode
  shell_escape: true

# Output options
output:
  format: pdf  # latex, pdf
  open_after: true
  compress: false

# Debug settings
debug:
  enabled: false
  entry_processing: false
  strict_mode: false
  tag_fallback: true

# Logging
logging:
  level: INFO
  file: ~/.5e2pdf/app.log
  format: text
  max_size: 10485760  # 10MB
  backup_count: 5
```

### Test Configuration

```yaml
# test-config.yaml - Used for isolated testing

version: "1.0"

# Use test data sources
sources:
  test:
    - test-adventure
    - test-book
    - test-creatures

paths:
  data: ./tests/fixtures/data
  cache: ./tests/.cache
  output: ./tests/output

# Faster processing for tests
processing:
  max_workers: 1
  timeout: 60

# Skip PDF generation in tests
output:
  format: latex
  open_after: false

debug:
  enabled: true
  strict_mode: true
```

## Command-Line Options

### Global Options

```bash
5e2pdf [GLOBAL_OPTIONS] COMMAND [COMMAND_OPTIONS]

Global Options:
  --config PATH        Use custom config file
  --debug             Enable debug output
  --verbose           Enable verbose output
  --quiet             Suppress output
  --no-cache          Disable caching
  --version           Show version
  --help              Show help
```

### Convert Command Options

```bash
5e2pdf convert [TYPE] [NAME] [OPTIONS]

Options:
  --output PATH       Output file path
  --format FORMAT     Output format (latex, pdf)
  --open             Open PDF after generation
  --no-images        Skip image processing
  --no-appendix      Skip appendix generation

Filtering:
  --source SOURCE    Limit to specific source
  --class CLASS      Filter by class (spells)
  --level RANGE      Filter by level (spells)
  --cr RANGE         Filter by CR (creatures)
  --type TYPE        Filter by type (items)
  --rarity RARITY    Filter by rarity (items)
```

### Setup Command Options

```bash
5e2pdf setup [COMMAND] [OPTIONS]

Commands:
  wizard            Run interactive setup
  check            Check configuration
  reset            Reset to defaults

Options:
  --force          Force operation without confirmation
  --defaults       Use all default values
```

## Source Management

### Adding Sources

```yaml
# In config.yaml
sources:
  homebrew:
    path: ~/my-homebrew-content
    enabled: true
    priority: 10  # Higher priority overrides lower

  third-party:
    url: https://example.com/data
    enabled: false
    cache_ttl: 86400  # Cache for 24 hours
```

### Source Priority

Sources are loaded in priority order (highest first):
1. Command-line specified sources
2. User homebrew (priority 10+)
3. Default sources (priority 0)

## Performance Tuning

### Memory Management

```yaml
processing:
  # Reduce memory usage
  batch_size: 50      # Process fewer items at once
  max_workers: 2      # Use fewer parallel workers
  lazy_loading: true  # Load data on demand

  # Cache settings
  cache:
    enabled: true
    max_size: 536870912  # 512MB
    ttl: 3600           # 1 hour
    compression: true
```

### Speed Optimization

```yaml
processing:
  # Increase speed (uses more memory)
  batch_size: 500
  max_workers: 8
  preload_all: true   # Load all data upfront

  # Parallel processing
  parallel:
    adventures: true
    books: true
    bulk_convert: true
```

## Output Customization

### LaTeX Customization

```yaml
latex:
  # Custom preamble
  preamble: |
    \usepackage{custom-package}
    \setmainfont{Custom Font}

  # Document class options
  document_class: dndbook
  class_options:
    - letterpaper
    - twocolumn
    - openany

  # Custom commands
  custom_commands:
    mycommand: '\newcommand{\mycommand}[1]{#1}'
```

### PDF Options

```yaml
output:
  pdf:
    compress: true
    embed_fonts: true
    pdf_version: "1.7"
    metadata:
      author: "Your Name"
      title: "Custom D&D Content"
      subject: "5e Rules"
      keywords: "D&D, 5e, homebrew"
```

## Profiles

Use profiles for different use cases:

```yaml
# config.yaml
profiles:
  development:
    debug:
      enabled: true
      strict_mode: true
    output:
      format: latex

  production:
    debug:
      enabled: false
    output:
      format: pdf
      compress: true

  quick:
    processing:
      max_workers: 1
      batch_size: 10
    latex:
      runs: 1
      quiet: true

# Activate profile
active_profile: development
```

Use profiles via command line:
```bash
5e2pdf --profile production convert adventure cos
```

## Validation

### Config Validation

```bash
# Validate configuration
5e2pdf setup check

# Test specific config file
5e2pdf setup check --config my-config.yaml

# Verbose validation output
5e2pdf setup check --verbose
```

### Common Validation Errors

1. **Invalid source path**: Source directory doesn't exist
2. **Missing LaTeX**: LaTeX engine not found in PATH
3. **Invalid version**: Config version incompatible
4. **Permission denied**: Can't write to output/cache directory

## Migration

### Upgrading Configuration

When upgrading 5e2pdf, configuration may need migration:

```bash
# Check if migration needed
5e2pdf setup migrate --check

# Perform migration (backs up old config)
5e2pdf setup migrate

# Migrate specific file
5e2pdf setup migrate --config old-config.yaml --output new-config.yaml
```

### Version Compatibility

| 5e2pdf Version | Config Version | Notes |
|---------------|---------------|--------|
| 0.1.x | 1.0 | Initial format |
| 0.2.x | 1.1 | Added profiles |
| 0.3.x | 1.2 | Added source priority |

## Best Practices

1. **Use profiles** for different workflows (dev/prod/test)
2. **Set memory limits** to prevent system overload
3. **Enable caching** for repeated conversions
4. **Use test-config.yaml** for testing to ensure isolation
5. **Version control** your config files
6. **Use environment variables** for sensitive data
7. **Validate config** after changes

## Troubleshooting Configuration

### Debug Configuration Loading

```bash
# Show configuration resolution
DND5E_DEBUG=1 5e2pdf setup check

# Show which config file is used
5e2pdf --debug convert adventure cos 2>&1 | grep "Config loaded"

# Test with minimal config
5e2pdf --config /dev/null convert adventure cos
```

### Reset Configuration

```bash
# Complete reset
rm -rf ~/.5e2pdf/
5e2pdf setup wizard

# Reset only config (keep cache)
rm ~/.5e2pdf/config.yaml
5e2pdf setup wizard --keep-cache
```

## Related Documentation

- [Environment Variables Guide](../troubleshooting.md#environment-variables-for-debugging)
- [Quickstart Tutorial](quickstart-tutorial.md)
- [CLI Reference](../library-reference/cli.md)
- [Testing Configuration](../developer/contributing/testing-requirements.md)

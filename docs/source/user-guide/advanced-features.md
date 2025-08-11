# Advanced Features

Advanced configuration and customization options for power users.

## LaTeX Document Customization

### Document Classes and Layout

5e2pdf supports extensive LaTeX document customization:

```bash
# Use different document classes
5e2pdf convert adventure cos --document-class dndbook
5e2pdf convert book phb --document-class dndarticle

# Paper sizes
5e2pdf convert adventure lmop --paper letter  # Default
5e2pdf convert adventure lmop --paper a4
5e2pdf convert adventure lmop --paper a5

# Font options
5e2pdf convert book mm --fonts wotc      # Official WOTC styling
5e2pdf convert book mm --fonts dmsguild  # DM's Guild styling

# Layout options
5e2pdf convert adventure cos --two-column    # Default two-column
5e2pdf convert adventure cos --one-column    # Single column
5e2pdf convert book phb --justified          # Justified text
5e2pdf convert book phb --not-justified      # Left-aligned text
```

### Background and Theme Options

```bash
# Background styles
5e2pdf convert adventure cos --background full   # Full backgrounds
5e2pdf convert adventure cos --background print  # Print-friendly
5e2pdf convert adventure cos --background none   # No backgrounds

# High contrast mode for accessibility
5e2pdf convert book phb --high-contrast

# Font sizes
5e2pdf convert adventure lmop --font-size 10pt
5e2pdf convert adventure lmop --font-size 11pt
5e2pdf convert adventure lmop --font-size 12pt
```

### Advanced Document Options

```bash
# Disable document outline/bookmarks
5e2pdf convert book phb --no-outline

# Include table of contents and indices
5e2pdf convert book phb --index        # Include alphabetical index
5e2pdf convert adventure cos --images  # Include image processing
```

## Content Source Management

### Source Types and Configuration

5e2pdf supports multiple content source types:

```bash
# List all sources with details
5e2pdf sources list

# Add GitHub repository source
5e2pdf sources add
# (Interactive prompts guide you through GitHub setup)

# Add local directory source
5e2pdf sources add
# (Interactive prompts guide you through local directory setup)
```

### Source Priority and Management

```bash
# Update all sources
5e2pdf sources update

# Remove specific source
5e2pdf sources remove source-name

# Check source status and statistics
5e2pdf stats sources
```

## Bulk Operations and Automation

### Bulk Conversion with Concurrency

```bash
# Convert multiple adventures with concurrency control
5e2pdf convert bulk cos lmop hotdq --type adventure --concurrent 4

# Mixed content types
5e2pdf convert bulk cos phb mm --type mixed --output-dir ./output

# Custom output directory structure
5e2pdf convert bulk cos lmop --type adventure --output-dir ./adventures
```

### Automation and Scripting

```bash
# Quick conversion for automation
5e2pdf quick input.json --pdf --output result.tex

# Batch processing with shell scripting
for file in *.json; do
    5e2pdf convert supplement "$file" --pdf
done

# Find and convert all JSON files
find ./content -name "*.json" -exec 5e2pdf convert supplement {} --pdf \;
```

## Advanced Content Processing

### Content Type Flexibility

5e2pdf supports extensive content types from 5e.tools:

- **Core Content**: adventures, books, creatures, spells, items
- **Character Options**: classes, races, backgrounds, feats
- **Game Mechanics**: conditions, actions, hazards, traps
- **Supplemental**: tables, variant rules, deities

```bash
# View supported content types in loaded data
5e2pdf list content --type spell
5e2pdf list content --type creature --limit 20
5e2pdf stats content creature
```

### Content Analysis and Statistics

```bash
# Detailed content analysis
5e2pdf stats overview              # System-wide statistics
5e2pdf stats content spell         # Spell-specific analysis
5e2pdf stats sources               # Source breakdown

# Content information and discovery
5e2pdf info content "Curse of Strahd"    # Detailed content info
5e2pdf info file adventure.json           # File analysis
```

## Performance Optimization

### Caching and Performance

```bash
# Content caching is enabled by default
# Cache location varies by system:
# - macOS: ~/.5e2pdf/cache/
# - Linux: ~/.cache/5e2pdf/
# - Windows: %APPDATA%\5e2pdf\cache\

# Performance tips for large conversions:
5e2pdf convert bulk cos lmop hotdq --concurrent 2  # Limit concurrency
5e2pdf convert adventure cos --no-images            # Skip image processing
```

### Memory Management

For large datasets or resource-constrained systems:

```bash
# Process individual files instead of bulk operations
5e2pdf convert adventure cos
5e2pdf convert adventure lmop

# Use quick convert for simple transformations
5e2pdf quick simple-content.json --type auto
```

## Configuration Management

### Setup and Configuration

```bash
# Interactive setup wizard
5e2pdf setup wizard

# Check system configuration
5e2pdf setup check

# Reset to default configuration
5e2pdf setup reset
```

### Environment and Debugging

```bash
# Debug mode for troubleshooting
5e2pdf --debug convert adventure cos

# Verbose logging
5e2pdf --verbose stats overview

# Check system status
5e2pdf setup check
```

## Integration and Workflows

### Development and Testing Workflows

```bash
# Test LaTeX compilation without full conversion
5e2pdf convert adventure cos --no-pdf  # Generate .tex only
5e2pdf convert adventure cos --pdf     # Full compilation

# Quick testing of content files
5e2pdf quick test.json --type adventure --output test-output.tex
```

### Content Validation and Quality

```bash
# File analysis before conversion
5e2pdf info file unknown-content.json

# Content statistics for quality assessment
5e2pdf stats content spell     # Analyze spell data quality
5e2pdf stats sources           # Source content breakdown
```

## System Integration

### Directory Structure

5e2pdf follows standard directory conventions:

```
~/.5e2pdf/                 # Configuration directory
├── config.yaml           # Main configuration
├── cache/                 # Content cache
├── sources/               # Downloaded sources
└── logs/                  # Application logs

./output/                  # Default output directory
├── adventures/            # Adventure conversions
├── books/                 # Book conversions
├── supplements/           # Supplement conversions
└── bulk/                  # Bulk operation outputs
```

### Environment Variables

Configure 5e2pdf behavior with environment variables:

```bash
# Set default configuration paths
export DND5E_CONFIG_DIR="$HOME/my-5e2pdf-config"
export DND5E_CACHE_DIR="$HOME/my-cache"
export DND5E_OUTPUT_DIR="./my-output"

# LaTeX engine preferences
export DND5E_LATEX_ENGINE="lualatex"

# Debug and logging
export DND5E_LOG_LEVEL="DEBUG"
export DND5E_VERBOSE="true"
```

## Troubleshooting Advanced Issues

### LaTeX Compilation Problems

```bash
# Test LaTeX installation
5e2pdf setup check

# Generate LaTeX only for debugging
5e2pdf convert adventure cos --no-pdf

# Check LaTeX engines individually
lualatex --version
pdflatex --version
xelatex --version
```

### Content Source Issues

```bash
# Verify source connectivity
5e2pdf sources list

# Reset and reconfigure sources
5e2pdf setup reset
5e2pdf setup wizard

# Check source statistics
5e2pdf stats sources
```

### Performance Issues

```bash
# Limit concurrent operations
5e2pdf convert bulk cos lmop --concurrent 1

# Skip resource-intensive operations
5e2pdf convert adventure cos --no-images

# Use quick mode for simple conversions
5e2pdf quick simple.json --pdf
```

## Next Steps

- **Developer Documentation**: For extending 5e2pdf functionality, see the [Developer Guide](../developer/index.md)
- **API Integration**: Explore programmatic usage through the Python API
- **Custom Templates**: Learn about LaTeX template customization in the developer documentation

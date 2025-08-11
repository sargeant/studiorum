# Basic Usage

Learn the essential commands and workflows for converting D&D content to PDF with 5e2pdf.

## Command Overview

The `5e2pdf` command-line tool provides several commands for different tasks:

| Command | Purpose | Example |
|---------|---------|---------|
| `convert` | Convert content to PDF | `5e2pdf convert --source PHB --content-type spell` |
| `list` | List available content | `5e2pdf list sources` |
| `info` | Show content information | `5e2pdf info --name "Fireball"` |
| `stats` | Display content statistics | `5e2pdf stats --source PHB` |
| `setup` | Initialize configuration | `5e2pdf setup --interactive` |

### Getting Help

```bash
# General help
5e2pdf --help

# Command-specific help
5e2pdf convert --help
5e2pdf list --help
```

## Basic Conversion Workflows

### Converting Spells

```bash
# All spells from Player's Handbook
5e2pdf convert --source PHB --content-type spell --output phb-spells.pdf

# Spells by level
5e2pdf convert --source PHB --content-type spell --level 3 --output level-3-spells.pdf

# Spells by school
5e2pdf convert --source PHB --content-type spell --school evocation --output evocation-spells.pdf

# Specific spells
5e2pdf convert --source PHB --content-type spell --names "Fireball,Magic Missile,Cure Wounds" --output selected-spells.pdf
```

### Converting Creatures

```bash
# All creatures from Monster Manual
5e2pdf convert --source MM --content-type monster --output mm-monsters.pdf

# Creatures by challenge rating
5e2pdf convert --source MM --content-type monster --cr "1-5" --output low-cr-monsters.pdf

# Creatures by type
5e2pdf convert --source MM --content-type monster --type "humanoid,beast" --output npc-animals.pdf

# Specific creatures
5e2pdf convert --source MM --content-type monster --names "Ancient Red Dragon,Troll" --output boss-monsters.pdf
```

### Converting Items

```bash
# All magic items
5e2pdf convert --source DMG --content-type item --rarity "uncommon,rare" --output magic-items.pdf

# Weapons and armor
5e2pdf convert --source PHB --content-type item --type "weapon,armor" --output equipment.pdf

# Consumables
5e2pdf convert --source DMG --content-type item --type "potion,scroll" --output consumables.pdf
```

### Converting Classes and Races

```bash
# Player classes
5e2pdf convert --source PHB --content-type class --output phb-classes.pdf

# Player races
5e2pdf convert --source PHB --content-type race --output phb-races.pdf

# Specific class with subclasses
5e2pdf convert --source PHB --content-type class --names "Wizard" --include-subclasses --output wizard-guide.pdf
```

## Content Discovery

### Listing Available Content

```bash
# List all sources
5e2pdf list sources

# List content types in a source
5e2pdf list content-types --source PHB

# List specific content
5e2pdf list spells --source PHB --limit 10
5e2pdf list monsters --source MM --cr "5+"
```

### Getting Content Information

```bash
# Basic content info
5e2pdf info --source PHB --name "Fireball"

# Detailed content info
5e2pdf info --source MM --name "Ancient Red Dragon" --verbose

# Content statistics
5e2pdf stats --source PHB
5e2pdf stats --content-type spell --all-sources
```

## Output Customization

### File Formats

```bash
# PDF output (default)
5e2pdf convert --source PHB --content-type spell --output spells.pdf

# LaTeX source
5e2pdf convert --source PHB --content-type spell --format latex --output spells.tex

# Both PDF and LaTeX
5e2pdf convert --source PHB --content-type spell --format both --output spells
```

### Output Options

```bash
# Single column output
5e2pdf convert --source PHB --content-type spell --columns 1 --output single-column.pdf

# A4 paper size
5e2pdf convert --source PHB --content-type spell --paper-size A4 --output a4-spells.pdf

# Custom margins
5e2pdf convert --source PHB --content-type spell --margins "2cm,2cm,1.5cm,1.5cm" --output custom-margins.pdf
```

### Content Organization

```bash
# Group by level/type
5e2pdf convert --source PHB --content-type spell --group-by level --output spells-by-level.pdf

# Include table of contents
5e2pdf convert --source PHB --content-type spell --include-toc --output spells-with-toc.pdf

# Include alphabetical index
5e2pdf convert --source PHB --content-type spell --include-index --output spells-with-index.pdf
```

## Working with Multiple Sources

### Combining Sources

```bash
# Multiple sources
5e2pdf convert --source "PHB,XGE,TCE" --content-type spell --output all-spells.pdf

# All official sources
5e2pdf convert --source official --content-type spell --output official-spells.pdf

# Include homebrew
5e2pdf convert --source "PHB,homebrew" --content-type spell --output extended-spells.pdf
```

### Source Priority

```bash
# Prefer newer sources for duplicates
5e2pdf convert --source "PHB,XGE,TCE" --content-type spell --source-priority newest --output latest-spells.pdf

# Use specific source for conflicts
5e2pdf convert --source "PHB,XGE" --content-type spell --prefer-source TCE --output tce-preferred.pdf
```

## Filtering and Selection

### Basic Filters

```bash
# Level-based filtering
5e2pdf convert --content-type spell --level "1-3" --output low-level-spells.pdf
5e2pdf convert --content-type spell --level "7+" --output high-level-spells.pdf

# CR-based filtering (monsters)
5e2pdf convert --content-type monster --cr "0.5-2" --output weak-monsters.pdf

# Rarity-based filtering (items)
5e2pdf convert --content-type item --rarity "common,uncommon" --output basic-magic-items.pdf
```

### Advanced Filters

```bash
# Text-based filtering
5e2pdf convert --content-type spell --description-contains "fire" --output fire-spells.pdf

# School/type combinations
5e2pdf convert --content-type spell --school "evocation,destruction" --level "3+" --output combat-spells.pdf

# Custom filter expressions
5e2pdf convert --content-type monster --filter "type=='humanoid' and cr >= 1" --output humanoid-npcs.pdf
```

## Configuration and Preferences

### Setting Defaults

```bash
# Set default source
5e2pdf config set default_source PHB

# Set default output directory
5e2pdf config set output_dir ./pdfs

# Set LaTeX engine preference
5e2pdf config set latex.engine lualatex
```

### Using Configuration Files

Create `~/.5e2pdf/config.yaml`:

```yaml
# Default settings
default_source: "PHB"
output_dir: "~/Documents/D&D/PDFs"

# LaTeX preferences
latex:
  engine: "lualatex"
  paper_size: "letter"
  columns: 2
  font_family: "Times"

# Content preferences
content:
  include_toc: true
  include_index: true
  group_by_default: true
```

### Environment Variables

```bash
# Override settings with environment variables
export DND5E_DEFAULT_SOURCE="PHB,MM,DMG"
export DND5E_OUTPUT_DIR="./output"
export DND5E_LATEX_ENGINE="lualatex"

# Run with environment settings
5e2pdf convert --content-type spell
```

## Common Workflows

### DM Preparation

```bash
# Session prep: relevant monsters for level 5 party
5e2pdf convert --content-type monster --cr "3-7" --type "humanoid,beast,monstrosity" --output session-monsters.pdf

# NPC stat blocks
5e2pdf convert --content-type monster --source "MM,VGM" --type humanoid --cr "0-2" --output npcs.pdf

# Magic items for treasure
5e2pdf convert --content-type item --rarity "uncommon,rare" --type "weapon,armor,wondrous" --output treasure.pdf
```

### Player Reference

```bash
# Spell reference for wizard
5e2pdf convert --content-type spell --class wizard --level "1-5" --output wizard-spells.pdf

# Class features
5e2pdf convert --content-type class --names "Wizard" --include-subclasses --output wizard-reference.pdf

# Equipment guide
5e2pdf convert --content-type item --source PHB --type "weapon,armor,adventuring-gear" --output equipment-guide.pdf
```

### Campaign Preparation

```bash
# Adventure content
5e2pdf convert --content-type adventure --names "Lost Mine of Phandelver" --output lmop.pdf

# Regional monsters
5e2pdf convert --content-type monster --environment "forest,mountain" --cr "1-8" --output regional-monsters.pdf

# Setting-specific content
5e2pdf convert --source "SCAG,SKT" --content-type "background,spell,monster" --output sword-coast.pdf
```

## Troubleshooting Common Issues

### Performance Issues

```bash
# Limit content for testing
5e2pdf convert --content-type spell --limit 10 --output test.pdf

# Use faster compilation
5e2pdf convert --content-type spell --latex-engine lualatex --fast-compile --output quick-test.pdf

# Enable caching
5e2pdf config set enable_cache true
```

### Output Issues

```bash
# Validate content before conversion
5e2pdf convert --content-type spell --validate --output validated-spells.pdf

# Debug mode for detailed logs
5e2pdf --log-level DEBUG convert --content-type spell --output debug-spells.pdf

# Check LaTeX compilation
5e2pdf convert --content-type spell --keep-tex --output spells-with-source.pdf
```

### Content Issues

```bash
# Update content sources
5e2pdf setup --update-sources

# Verify data integrity
5e2pdf stats --validate

# Reset configuration
5e2pdf setup --reset
```

## Performance Tips

### Optimizing Builds

- **Use caching**: Enable content and compilation caching
- **Choose fast LaTeX engine**: LuaLaTeX is typically faster than PDFLaTeX
- **Limit content**: Use filters to reduce content size
- **Parallel processing**: Enable parallel compilation for large documents

### Memory Management

- **Stream processing**: For very large datasets, use streaming mode
- **Chunk processing**: Break large conversions into smaller chunks
- **Clear cache**: Periodically clear cache files to free disk space

## Next Steps

- **Advanced Features**: Learn about [custom templates and advanced filtering](advanced-features.md)
- **Troubleshooting**: Get help with [common issues and solutions](troubleshooting.md)
- **API Usage**: Explore the [Python API](../api/index.md) for programmatic access
- **Examples**: See [practical examples](../examples/index.md) for specific use cases

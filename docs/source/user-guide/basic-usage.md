# Basic Usage

Learn the essential commands and workflows for converting D&D content to PDF with 5e2pdf.

## Command Overview

The `5e2pdf` command-line tool provides several commands for different tasks:

| Command | Purpose | Example |
|---------|---------|---------|
| `convert` | Convert content to PDF | `5e2pdf convert adventure cos` |
| | • Convert spells | `5e2pdf convert spells --class wizard` |
| | • Convert creatures | `5e2pdf convert creatures --cr 1-5 --type dragon` |
| `list` | List available content | `5e2pdf list sources` |
| `info` | Show content information | `5e2pdf info content cos` |
| `stats` | Display content statistics | `5e2pdf stats overview` |
| `setup` | Initialize configuration | `5e2pdf setup wizard` |
| `sources` | Manage content sources | `5e2pdf sources list` |

### Getting Help

```bash
# General help
5e2pdf --help

# Command-specific help
5e2pdf convert --help
5e2pdf list --help
```

## Content Conversion

### Converting Adventures

```bash
# Convert adventure by abbreviation
5e2pdf convert adventure cos

# Convert adventure from local file
5e2pdf convert adventure /path/to/adventure.json

# Convert with PDF compilation
5e2pdf convert adventure lmop --pdf

# Specify output file
5e2pdf convert adventure hotdq --output my-adventure.tex
```

### Converting Books

```bash
# Convert sourcebook by abbreviation
5e2pdf convert book phb

# Convert book from local file
5e2pdf convert book /path/to/book.json

# Convert with custom title
5e2pdf convert book mm --title "Monster Manual Custom"
```

### Converting Spells

The spell conversion system provides powerful tools for creating custom spell books with advanced filtering, sorting, and class-based selection.

#### Basic Spell Conversion

```bash
# Convert specific spells by name (wizard use case)
5e2pdf convert spells "fireball" "magic missile" "counterspell"

# Class-based filtering (cleric use case)
5e2pdf convert spells --class wizard --level 1-5

# Multiple classes
5e2pdf convert spells --class wizard,sorcerer --max-level 3

# With PDF compilation
5e2pdf convert spells --class cleric --level 1-3 --pdf
```

#### Advanced Filtering

```bash
# Level filtering
5e2pdf convert spells --class wizard --level 1-9      # Level range
5e2pdf convert spells --class wizard --max-level 5    # Maximum level
5e2pdf convert spells --levels 1,3,5                  # Specific levels

# School filtering
5e2pdf convert spells --class wizard --school evocation,abjuration
5e2pdf convert spells --school e,a                    # Using abbreviations

# Component filtering
5e2pdf convert spells --class wizard --no-material    # No material components
5e2pdf convert spells --somatic --verbal              # Require somatic and verbal
5e2pdf convert spells --concentration                 # Concentration spells only

# Combat filtering
5e2pdf convert spells --damage-type fire,cold         # Damage types
5e2pdf convert spells --save dex,wis                  # Saving throw types
5e2pdf convert spells --attack-spell                  # Spells with attack rolls

# Source filtering
5e2pdf convert spells --sources PHB,XGE --class wizard
5e2pdf convert spells --sources XPHB "wish"           # Specific source only
```

#### Sorting and Organization

```bash
# Group by spell level (default)
5e2pdf convert spells --class wizard --sort level

# Alphabetical ordering
5e2pdf convert spells --class wizard --sort name

# Table of contents control
5e2pdf convert spells --class wizard --toc            # Include TOC (default)
5e2pdf convert spells --class wizard --no-toc         # Exclude TOC
```

#### Optional and Variant Spells

```bash
# Include optional/variant class spells
5e2pdf convert spells --class wizard --optional-spells "tasha's mind whip"

# TCE variant spells for multiple classes
5e2pdf convert spells --sources TCE --class wizard,sorcerer --optional-spells

# Combine standard and optional spells
5e2pdf convert spells --class wizard --level 1-5 --optional-spells --sources PHB,TCE
```

#### Input Methods

```bash
# Read spell names from file
5e2pdf convert spells --from-file my-spell-list.txt

# Read from stdin
echo -e "fireball\nmagic missile" | 5e2pdf convert spells --from-stdin

# Mixed approach: names + filtering
5e2pdf convert spells "fireball" "wish" --class wizard --level 1-5
```

#### Output Customization

```bash
# Custom title and output
5e2pdf convert spells --class wizard --title "My Wizard Spells" --output wizard-spells.tex

# Custom LaTeX styling
5e2pdf convert spells --class cleric --background print --fonts wotc --paper a4

# Two-column layout
5e2pdf convert spells --class wizard --two-column --pdf
```

### Converting Creatures

The creature conversion system provides powerful filtering options for creating custom bestiaries and encounter references with comprehensive D&D 5e creature data.

#### Basic Creature Conversion

```bash
# Convert specific creatures by name
5e2pdf convert creatures "goblin" "orc" "ancient red dragon"

# Challenge Rating filtering
5e2pdf convert creatures --cr 1-5            # CR range
5e2pdf convert creatures --cr 1               # Specific CR
5e2pdf convert creatures --min-cr 10          # Minimum CR
5e2pdf convert creatures --max-cr 5           # Maximum CR

# Creature type filtering
5e2pdf convert creatures --type dragon        # Dragons only
5e2pdf convert creatures --type humanoid,fey  # Multiple types

# With PDF compilation
5e2pdf convert creatures --cr 1-3 --type beast --pdf
```

#### Advanced Filtering

```bash
# Size filtering
5e2pdf convert creatures --size large,huge
5e2pdf convert creatures --size tiny          # Tiny creatures only

# Combat abilities
5e2pdf convert creatures --legendary          # Legendary actions
5e2pdf convert creatures --spellcasting       # Spellcasting ability
5e2pdf convert creatures --multiattack        # Multiattack ability

# Movement and senses
5e2pdf convert creatures --fly                # Flying speed
5e2pdf convert creatures --swim               # Swimming speed
5e2pdf convert creatures --darkvision         # Darkvision
5e2pdf convert creatures --blindsight         # Blindsight

# Combat statistics
5e2pdf convert creatures --min-ac 15 --max-ac 20    # Armor Class range
5e2pdf convert creatures --min-hp 50 --max-hp 200   # Hit Points range

# Source filtering
5e2pdf convert creatures --sources MM,VGM --cr 1-10
```

#### Input Methods

```bash
# Read creature names from file
5e2pdf convert creatures --from-file encounter-list.txt

# Read from stdin
echo -e "goblin\norc\nbugbear" | 5e2pdf convert creatures --from-stdin

# Mixed approach: names + filtering
5e2pdf convert creatures "goblin" "orc" --cr 1-5 --type humanoid
```

#### Output Customization

```bash
# Custom title and output
5e2pdf convert creatures --cr 1-5 --title "Low-Level Encounters" --output encounters.tex

# Table of contents control
5e2pdf convert creatures --type dragon --toc     # Include TOC (default)
5e2pdf convert creatures --type dragon --no-toc  # Exclude TOC

# Two-column layout for smaller creatures
5e2pdf convert creatures --cr 0-2 --two-column --pdf
```

#### Common Use Cases

```bash
# Encounter building for specific CR
5e2pdf convert creatures --cr 5 --legendary

# Type-based collections
5e2pdf convert creatures --type undead --pdf --title "Undead Compendium"

# Adventure-appropriate creatures
5e2pdf convert creatures --cr 1-8 --type humanoid,beast,monstrosity

# Boss monster collection
5e2pdf convert creatures --min-cr 15 --legendary --pdf

# Flying encounters
5e2pdf convert creatures --fly --cr 3-10 --pdf --title "Aerial Encounters"
```

### Converting Supplements

```bash
# Convert mixed content from JSON file
5e2pdf convert supplement my-homebrew.json

# Include only specific content types
5e2pdf convert supplement supplements.json --type spell --type creature

# Compile to PDF
5e2pdf convert supplement content.json --pdf
```

### Bulk Conversion

```bash
# Convert multiple adventures
5e2pdf convert bulk cos lmop hotdq --type adventure

# Convert multiple books
5e2pdf convert bulk phb mm dmg --type book

# Mixed content with custom output directory
5e2pdf convert bulk cos phb --type mixed --output-dir ./converted
```

## Content Discovery

### Listing Available Content

```bash
# List all configured sources
5e2pdf list sources

# List available adventures
5e2pdf list adventures

# List available books
5e2pdf list books

# List content in loaded data
5e2pdf list content --type spell --limit 10

# List files in directories
5e2pdf list files --dir ./data
```

### Getting Content Information

```bash
# Get adventure info
5e2pdf info content cos

# Get book info
5e2pdf info content phb

# Get file information
5e2pdf info file /path/to/content.json

# Search for content by name
5e2pdf info content "Curse of Strahd"
```

### Content Statistics

```bash
# Overview of all content
5e2pdf stats overview

# Statistics for specific content type
5e2pdf stats content spell

# Statistics by source
5e2pdf stats sources
```

## Source Management

### Managing Content Sources

```bash
# List configured sources
5e2pdf sources list

# Add new source
5e2pdf sources add

# Remove source
5e2pdf sources remove source-name

# Update sources
5e2pdf sources update
```

## Output Options

### LaTeX Customization

```bash
# Two-column layout
5e2pdf convert adventure cos --two-column

# Single column layout
5e2pdf convert adventure cos --one-column

# Custom document class
5e2pdf convert book phb --document-class dndbook

# Paper size
5e2pdf convert adventure cos --paper a4

# Font options
5e2pdf convert book mm --fonts wotc

# Background style
5e2pdf convert adventure lmop --background print
```

### Content Options

```bash
# Include images
5e2pdf convert adventure cos --images

# Exclude images
5e2pdf convert adventure cos --no-images

# Include items and creatures in adventures
5e2pdf convert adventure cos --items --creatures

# Custom title
5e2pdf convert book phb --title "My Custom PHB"
```

## Configuration

### Setup Wizard

```bash
# Interactive setup
5e2pdf setup wizard

# Check current setup
5e2pdf setup check

# Reset to defaults
5e2pdf setup reset
```

### Quick Operations

```bash
# Quick convert single file
5e2pdf quick input.json --pdf

# Test LaTeX compilation
5e2pdf quick test.json --type auto --output test.tex
```

## Common Workflows

### DM Session Preparation

```bash
# Convert adventure for session
5e2pdf convert adventure lmop --pdf --images

# Get adventure information
5e2pdf info content lmop

# Check what content is available
5e2pdf list adventures
```

### Spell Book Creation

```bash
# Create wizard spell book for levels 1-5
5e2pdf convert spells --class wizard --level 1-5 --pdf --title "Wizard Spells (1-5)"

# Create specific spell collection for quick reference
5e2pdf convert spells "fireball" "counterspell" "magic missile" --pdf

# Create cleric spell book with healing focus
5e2pdf convert spells --class cleric --level 1-3 --school abjuration,evocation --pdf

# Include optional TCE spells
5e2pdf convert spells --class wizard --sources PHB,TCE --optional-spells --pdf
```

### Bestiary Creation

```bash
# Create encounter-specific bestiary
5e2pdf convert creatures --cr 1-5 --pdf --title "Low-Level Encounters"

# Create type-focused collections
5e2pdf convert creatures --type dragon --pdf --title "Dragon Compendium"

# Create boss monster reference
5e2pdf convert creatures --min-cr 10 --legendary --pdf --title "Boss Monsters"

# Create specific encounter list
5e2pdf convert creatures "goblin" "orc" "bugbear" --pdf --title "Goblinoid Encounters"

# Create adventure-appropriate bestiary
5e2pdf convert creatures --cr 1-8 --type humanoid,beast,monstrosity --pdf
```

### Homebrew Content

```bash
# Convert custom content file
5e2pdf convert supplement my-spells.json --pdf

# Create custom spell book from homebrew
5e2pdf convert spells --from-file homebrew-spells.txt --pdf

# Bulk convert homebrew files
find ./homebrew -name "*.json" -exec 5e2pdf convert supplement {} --pdf \;
```

### Content Management

```bash
# Check system status
5e2pdf setup check

# Update content sources
5e2pdf sources update

# View content statistics
5e2pdf stats overview
```

## Performance Tips

- **Use caching**: Configuration caching is enabled by default
- **PDF compilation**: LuaLaTeX is the default engine for best results
- **Bulk operations**: Use `convert bulk` for multiple items
- **Local files**: Direct file conversion is faster than source lookup

## Troubleshooting Common Issues

### Content Not Found

```bash
# Check available adventures
5e2pdf list adventures

# Check available books
5e2pdf list books

# Verify sources are configured
5e2pdf sources list
```

### LaTeX Compilation Issues

```bash
# Test without PDF compilation first
5e2pdf convert adventure cos --no-pdf

# Check LaTeX installation
5e2pdf setup check

# Use debug mode for more information
5e2pdf --debug convert adventure cos
```

### Source Issues

```bash
# Reset sources to defaults
5e2pdf setup reset

# Run setup wizard again
5e2pdf setup wizard

# Check source status
5e2pdf sources list
```

## Next Steps

- **Source Management**: Learn about [content sources and configuration](../developer/index.md)
- **LaTeX Customization**: Explore document styling options in the developer guide
- **Troubleshooting**: Get help with [common issues](troubleshooting.md)

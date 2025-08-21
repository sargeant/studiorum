# Quick Start Guide

Get up and running with 5e2pdf in minutes.

## Installation

### Prerequisites

- Python 3.12 or higher
- LaTeX distribution (TeX Live, MacTeX, or MiKTeX)
- Git (for development installation)

### Install from PyPI

```bash
pip install 5e2pdf
```

### Development Installation

```bash
git clone https://github.com/sargeant/5e2pdf.git
cd 5e2pdf
uv sync
```

## First PDF Generation

### 1. Basic Spell Compendium

Generate a PDF of all spells from the Player's Handbook:

```bash
5e2pdf spell --source PHB --output phb-spells.pdf
```

### 2. Creature Stat Blocks

Create stat blocks for low-level creatures:

```bash
5e2pdf creature --cr "0-2" --output starter-creatures.pdf
```

### 3. Class Features

Extract all features for a specific class:

```bash
5e2pdf class-feature --class Fighter --output fighter-features.pdf
```

## Common Use Cases

### DM Session Prep

```bash
# Generate encounter-appropriate creatures
5e2pdf creature --cr "4-6" --environment "forest,mountain" --output session-encounters.pdf

# Create reference for specific adventure
5e2pdf adventure --name "Lost Mine of Phandelver" --chapter 1 --output lmop-chapter1.pdf
```

### Player Reference

```bash
# Spell list for your caster
5e2pdf spell --class Wizard --level "1-3" --output wizard-spells-1-3.pdf

# Magic items by rarity
5e2pdf item --type "magic item" --rarity "uncommon,rare" --output magic-items.pdf
```

### Custom Collections

```bash
# Homebrew-friendly monsters
5e2pdf creature --source "homebrew,third-party" --output homebrew-creatures.pdf

# Official adventures only
5e2pdf adventure --official-only --output official-adventures.pdf
```

## Configuration

### Data Sources

5e2pdf automatically downloads and caches data from 5e.tools. You can also specify local data directories:

```bash
export DND5E_DATA_PATH="/path/to/local/5etools/data"
5e2pdf spell --source PHB
```

### Output Customization

Create custom LaTeX templates and styles:

```bash
# Use custom template
5e2pdf spell --template custom-spell-template.tex --output custom-spells.pdf

# Adjust paper size and margins
5e2pdf creature --paper a4 --margin 1in --output a4-creatures.pdf
```

## Troubleshooting

### Common Issues

**LaTeX not found:**
```bash
# Ubuntu/Debian
sudo apt-get install texlive-full

# macOS (with Homebrew)
brew install --cask mactex

# Windows
# Download and install MiKTeX from miktex.org
```

**Memory issues with large datasets:**
```bash
# Limit memory usage
5e2pdf spell --max-memory 1GB --source PHB

# Process in batches
5e2pdf creature --batch-size 50 --output creatures-batch.pdf
```

**Missing fonts:**
```bash
# Install additional LaTeX packages
tlmgr install collection-fontsrecommended
```

### Getting Help

- Use `5e2pdf --help` for command-line options
- Check the [troubleshooting guide](troubleshooting.md) for detailed solutions
- Report issues on [GitHub](https://github.com/sargeant/5e2pdf/issues)

## Next Steps

- Read the [User Guide](basic-usage.md) for detailed usage instructions
- Explore [Examples](examples/index.md) for advanced use cases
- Check out the [Developer Guide](getting-started.md) if you want to contribute or extend 5e2pdf

Ready to dive deeper? Continue to the [User Guide](basic-usage.md) →

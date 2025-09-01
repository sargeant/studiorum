---
title: Converting Content
description: Advanced options for converting 5e content to LaTeX/PDF format
---

# Converting Content

Learn how to use studiorum's powerful conversion capabilities to create professional 5e documents.

## Content Types

Studiorum supports converting various types of 5e content:

### Adventures

Convert full adventures:

```bash
# Basic adventure conversion
studiorum convert adventure TEST

# With appendices for referenced content
studiorum convert adventure "my-awesome-adventure" \
    --creatures --spells --items --output adventure.tex
```

### Creatures

Convert individual creatures or groups:

```bash
# Single creature
studiorum convert creatures "Young Red Dragon" --sources SRD

# Multiple creatures by CR
studiorum convert creatures --cr 15-20 --sources SRD

# By type, using the 2014 style statblocks
studiorum convert creatures --type dragon --statblock 2014 --sources SRD

# Low CR creatures who can see your invisible players
studiorum convert creatures --cr 1-5 --blindsight --sources SRD

# All SRD creatures
studiorum convert creatures  --sources SRD
```

### Spells

Convert spells with automatic formatting:

```bash
# Single spell
studiorum convert spell "Fireball" --sources SRD

# By level
studiorum convert spells --level 3 --sources SRD

# By school
studiorum convert spells --school evocation --sources SRD
```

### Items

Convert magic items and equipment:

```bash
# Magic items
studiorum convert items --type magic --sources SRD

# Specific rarity
studiorum convert items --rarity legendary --sources SRD
```

## Output Formats

### LaTeX Output

Generate LaTeX files for maximum customization:

```bash
studiorum convert adventure TEST --output test-adventure.tex
```

This allows you to edit `test-adventure.tex` to fix up any issues or revise the layout as you see fit. When ready, use your preferred LaTeX compiler to build:

```bash
## Two passes used so LaTeX can build the table-of-contents.
## Studiorum handles this if you call with --pdf
xelatex test-adventure.tex && xelatex test-adventure.tex
```

### PDF Output

Generate PDFs directly using your preferred LaTeX compiler:

```bash
# Edit ~/.studiorum/config.yml
# Set rendering.latex.engine.primary_engine to
# pdflatex, xelatex, lualatex, etc.
studiorum convert adventure TEST \
    --pdf
    --output test.pdf
```

## Advanced Options

### Content Filtering

Filter content by source, assuming you have the data for it:

```bash
# Only spells from my homebrew and their homebrew:
studiorum convert spells --sources MY-HOMEBREW,THEIR-HOMEBREW
```

## Configuration

### Global Settings

Configure default behavior in `~/.studiorum/config.yaml`:

```yaml
rendering:
  content:
    default_sources:
    # If you got bored of typing `--source srd` every time
      - SRD

  latex:
    engine:
      primary_engine: xelatex
```

## Next Steps

- **[CLI Reference](cli-reference.md)**: Complete command documentation
- **[MCP Setup](mcp-setup.md)**: Integrate with AI agents
- **[Developer Guide](../developer-guide/index.md)**: Build custom integrations

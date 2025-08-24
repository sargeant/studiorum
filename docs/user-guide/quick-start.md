---
title: Quick Start
description: Get up and running with studiorum in minutes
---

# Quick Start

Get up and running with studiorum to convert D&D 5e content into professional PDFs.

## Installation

Install studiorum using pip or uv:

=== "uv (Recommended)"

    ```bash
    uv add studiorum
    ```

=== "pip"

    ```bash
    pip install studiorum
    ```

## Basic Usage

### Convert a Creature

Convert a single creature to PDF:

```bash
studiorum convert creature "Ancient Red Dragon" --output dragon.tex
pdflatex dragon.tex
```

### Convert an Adventure

Convert a full adventure with appendices:

```bash
studiorum convert adventure "Lost Mine of Phandelver" \
    --creatures --spells --items \
    --output lmop.tex
```

### List Available Content

See what content is available:

```bash
# List adventures
studiorum list adventures

# List creatures by challenge rating
studiorum list creatures --cr 10-15

# List spells by level
studiorum list spells --level 3
```

## Configuration

Create a configuration file at `~/.studiorum/config.yaml`:

```yaml
# Data sources
sources:
  enabled:
    - PHB  # Player's Handbook
    - DMG  # Dungeon Master's Guide
    - MM   # Monster Manual
    - VGtM # Volo's Guide to Monsters

# LaTeX settings
latex:
  compiler: pdflatex
  template: dnd-5e

# Output preferences
output:
  include_toc: true
  include_index: true
```

## Next Steps

- **[Converting Content](converting-content.md)**: Learn advanced conversion options
- **[CLI Reference](cli-reference.md)**: Complete command reference
- **[MCP Setup](mcp-setup.md)**: Integrate with AI agents
- **[Troubleshooting](troubleshooting.md)**: Common issues and solutions

## Getting Help

- Check the [troubleshooting guide](troubleshooting.md) for common issues
- Browse the [CLI reference](cli-reference.md) for all commands
- Join our community discussions on GitHub

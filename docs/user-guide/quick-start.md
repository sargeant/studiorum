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
studiorum convert creatures --type dragon --output dragons.tex
xelatex dragon.tex
```

### List Available Content

See what content is available:

```bash
# List adventures
studiorum list adventures

# List creatures
studiorum list content --type creature

# List spells
studiorum list content --type spell

# List items
studiorum list content --type item

```

## Configuration

> Needs content

## Next Steps

- **[Converting Content](converting-content.md)**: Learn advanced conversion options
- **[CLI Reference](cli-reference.md)**: Complete command reference
- **[MCP Setup](mcp-setup.md)**: Integrate with AI agents
- **[Troubleshooting](troubleshooting.md)**: Common issues and solutions

## Getting Help

- Check the [troubleshooting guide](troubleshooting.md) for common issues
- Browse the [CLI reference](cli-reference.md) for all commands
- Join our community discussions on GitHub

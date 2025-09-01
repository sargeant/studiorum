---
title: Quick Start
description: Get up and running with studiorum in minutes
---

# Quick Start

Get up and running with Studiorum to convert 5e content into professional PDFs.

## Installation

Install Studiorum by cloning the Github repository. In the future it will be available on PyPi so you can use `pip` or `uv`.

=== "Clone Git Repo"

    ```bash
    git clone https://github.com/sargeant/studiorum.git
    cd studiorum
    uv sync
    . .venv/bin/activate
    ```

=== "uv"

    ```bash
    # Studiorum is not available on PyPi yet. Future feature.
    uv add studiorum
    ```

=== "pip"

    ```bash
    # Studiorum is not available on PyPi yet. Future feature.
    pip install studiorum
    ```

### LaTeX

You'll need a LaTeX installation to build the PDFs.

=== "macOS"

    ```bash
    # Install MacTeX (full distribution)
    brew install --cask mactex

    # Or BasicTeX (minimal)
    brew install --cask basictex
    ```

=== "Ubuntu/Debian"

    ```bash
    # Full installation
    sudo apt-get install texlive-full

    # Minimal installation
    sudo apt-get install texlive-latex-base texlive-latex-extra
    ```

=== "Windows"

    Download and install [MiKTeX](https://miktex.org/download) or [TeX Live](https://www.tug.org/texlive/).

#### LaTeX template

We build on the great work of others by using an open source template for the LaTeX document processing language. In the future we plan to automatically handle the install, but for now please [install the template manually](https://github.com/ashonit/DND-5e-LaTeX-Template).

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

# List creatures
studiorum list content --type creature

# List spells
studiorum list content --type spell

# List items
studiorum list content --type item

# List adventures
studiorum list adventures

# List books
studiorum list books

```

### Add More Content

If you have a directory of 5etools compatible JSON, you can configure Studiorum to load that data as it's primary data-source.

```bash
studiorum data set-primary <path to 5etools data>
```

## Configuration

The user configuration is stored in `~/.studiorum/config.yml`. You can see your entire configuration setup (defaults + user settings) by running:

```bash
studiorum config show
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

# User Guide

Comprehensive guide to using 5e2pdf for creating custom D&D 5e PDF documents.

## Overview

The User Guide covers everything you need to know to effectively use 5e2pdf for converting D&D content to beautifully formatted LaTeX and PDF documents. Whether you're a DM preparing for sessions or a player creating reference materials, this guide will help you get the most out of 5e2pdf.

## What You'll Learn

- **[Installation](installation.md)**: Development setup and dependencies
- **[Basic Usage](basic-usage.md)**: Core commands and common workflows
- **[Advanced Features](advanced-features.md)**: Customization, bulk operations, and power-user techniques
- **[Troubleshooting](troubleshooting.md)**: Solutions for common issues and debugging tips

## Getting Started

If you're new to 5e2pdf, start with the [Installation Guide](installation.md) to set up the development environment, then explore the [Basic Usage](basic-usage.md) guide for common workflows.

## What 5e2pdf Can Do

### Content Conversion

- **Adventures**: Convert D&D adventures (Curse of Strahd, Lost Mine of Phandelver, etc.) to professionally formatted PDFs
- **Books**: Transform sourcebooks (Player's Handbook, Monster Manual, etc.) into customizable documents
- **Supplements**: Process homebrew content and mixed JSON files with spells, creatures, and items
- **Bulk Operations**: Convert multiple files efficiently with concurrent processing

### Output Formats

- **LaTeX**: Generate high-quality LaTeX documents with authentic D&D styling
- **PDF**: Compile directly to PDF using modern LaTeX engines (LuaLaTeX, PDFLaTeX, XeLaTeX)
- **Customizable**: Multiple document classes, layouts, fonts, and styling options

### Content Sources

- **5e.tools Integration**: Work with official 5e.tools JSON data format
- **Local Files**: Process local JSON files and homebrew content
- **Multiple Sources**: GitHub repositories, local directories, and configurable source management

## Core Commands

5e2pdf provides several main commands:

```bash
# Content conversion
5e2pdf convert adventure cos        # Convert adventure by abbreviation
5e2pdf convert book phb             # Convert book by abbreviation
5e2pdf convert supplement file.json # Convert mixed content from file
5e2pdf convert bulk cos lmop hotdq  # Bulk convert multiple items

# Content discovery
5e2pdf list adventures              # Show available adventures
5e2pdf list books                   # Show available books
5e2pdf info content cos             # Get detailed content information

# System management
5e2pdf setup wizard                 # Interactive configuration
5e2pdf sources list                 # Manage content sources
5e2pdf stats overview               # Content statistics
```

## Key Features

### Document Customization

- Multiple LaTeX document classes (dndbook, dndarticle)
- Paper size options (letter, A4, A5)
- Layout control (single/two-column, justified/left-aligned)
- Font and styling options (WOTC official, DM's Guild)
- Background and theme control

### Content Management

- Intelligent content type detection
- Source prioritization and management
- Caching for improved performance
- Comprehensive content statistics and analysis

### Quality and Compatibility

- Official D&D 5e styling and formatting
- Professional LaTeX output
- Cross-platform compatibility (macOS, Linux, Windows)
- Modern Python 3.12+ and UV package management

## Quick Start Workflow

1. **Install**: Follow the [installation guide](installation.md) to set up 5e2pdf
2. **Configure**: Run `5e2pdf setup wizard` to configure content sources
3. **Convert**: Try `5e2pdf convert adventure cos` for your first conversion
4. **Explore**: Use `5e2pdf list adventures` to see what content is available

## Common Use Cases

### DM Session Preparation

```bash
# Convert adventure for tonight's session
5e2pdf convert adventure lmop --pdf --images

# Get information about the adventure
5e2pdf info content lmop
```

### Player References

```bash
# Create custom spell reference
5e2pdf convert supplement my-spells.json --pdf

# Convert sourcebook sections
5e2pdf convert book phb --title "Custom PHB Reference"
```

### Homebrew Content

```bash
# Convert homebrew creatures and items
5e2pdf convert supplement homebrew-content.json --pdf

# Bulk process multiple homebrew files
5e2pdf convert bulk file1.json file2.json file3.json --type mixed
```

## System Requirements

### Minimum

- **Python**: 3.12+
- **Package Manager**: UV
- **LaTeX**: Any modern distribution (MacTeX, TeX Live, MiKTeX)
- **RAM**: 4GB
- **Disk Space**: 2GB

### Recommended

- **RAM**: 8GB+
- **LaTeX**: Full installation with extended packages
- **Disk Space**: 5GB+ for caching and multiple conversions

## Support and Community

- **Documentation**: Complete user and developer guides
- **Troubleshooting**: Comprehensive problem-solving resources
- **GitHub Issues**: Bug reports and feature requests
- **Open Source**: Full source code available for customization

## Table of Contents

```{toctree}
:maxdepth: 2

installation
basic-usage
advanced-features
troubleshooting
```

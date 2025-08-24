---
title: Converting Content
description: Advanced options for converting 5e content to LaTeX/PDF format
---

# Converting Content

Learn how to use studiorum's powerful conversion capabilities to create professional 5e documents.

## Content Types

Studiorum supports converting various types of 5e content:

### Adventures

Convert full adventures with automatic cross-references:

```bash
# Basic adventure conversion
studiorum convert adventure "sample-adventure"

# With appendices for referenced content
studiorum convert adventure "sample-adventure" \
    --creatures --spells --items --output adventure.tex
```

### Creatures

Convert individual creatures or groups:

```bash
# Single creature
studiorum convert creature "Ancient Red Dragon"

# Multiple creatures by CR
studiorum convert creatures --cr 15-20

# By type
studiorum convert creatures --type dragon
```

### Spells

Convert spells with automatic formatting:

```bash
# Single spell
studiorum convert spell "Fireball"

# By level
studiorum convert spells --level 3

# By school
studiorum convert spells --school evocation
```

### Items

Convert magic items and equipment:

```bash
# Magic items
studiorum convert items --type magic

# Specific rarity
studiorum convert items --rarity legendary
```

## Output Formats

### LaTeX Output

Generate LaTeX files for maximum customization:

```bash
studiorum convert adventure "Storm King's Thunder" \
    --format latex \
    --output skt.tex
```

### PDF Output

Generate PDFs directly using your preferred LaTeX compiler:

```bash
studiorum convert adventure "Waterdeep Dragon Heist" \
    --format pdf \
    --compiler xelatex \
    --output wdh.pdf
```

## Advanced Options

### Templates

Use different LaTeX templates:

```bash
# Official 5e template
studiorum convert --template dnd-5e creature "Tarrasque"

# Custom template
studiorum convert --template custom.tex creature "Lich"
```

### Content Filtering

Filter content by source books:

```bash
# Only PHB content
studiorum convert spells --sources PHB

# Exclude certain sources
studiorum convert creatures --exclude-sources UA,HB
```

### Cross-References

Control automatic cross-referencing:

```bash
# Enable all cross-references
studiorum convert adventure "Tomb of Annihilation" \
    --cross-references all

# Disable cross-references
studiorum convert adventure "Out of the Abyss" \
    --no-cross-references
```

## Batch Processing

### Multiple Adventures

Process multiple adventures:

```bash
#!/bin/bash
for adventure in "LMoP" "HotDQ" "RoT" "PotA"; do
    studiorum convert adventure "$adventure" \
        --creatures --spells --items \
        --output "${adventure,,}.tex"
done
```

### Campaign Compendium

Create a complete campaign compendium:

```bash
studiorum convert adventures \
    --campaign "Tyranny of Dragons" \
    --merge \
    --toc \
    --index \
    --output tod-complete.tex
```

## Configuration

### Global Settings

Configure default behavior in `~/.studiorum/config.yaml`:

```yaml
conversion:
  # Default appendices to include
  default_appendices:
    - creatures
    - spells
    - items

  # Cross-reference settings
  cross_references:
    enabled: true
    auto_detect: true

  # Template settings
  template:
    default: dnd-5e
    path: ~/.studiorum/templates/
```

### Per-Project Settings

Use project-specific configuration:

```yaml
# project/.studiorum.yaml
sources:
  enabled:
    - PHB
    - XGtE
    - TCE

output:
  format: pdf
  compiler: xelatex

conversion:
  include_toc: true
  include_index: false
```

## Integration Examples

### GitHub Actions

Automate PDF generation:

```yaml
name: Generate PDFs
on: [push]
jobs:
  generate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      - run: pip install studiorum
      - run: studiorum convert adventure "Custom Campaign" --output campaign.pdf
      - uses: actions/upload-artifact@v4
        with:
          path: campaign.pdf
```

### Docker

Use in containerized environments:

```dockerfile
FROM python:3.12-slim
RUN pip install studiorum
RUN apt-get update && apt-get install -y texlive-latex-extra
COPY . /campaign
WORKDIR /campaign
CMD ["studiorum", "convert", "adventure", "My Campaign", "--output", "campaign.pdf"]
```

## Best Practices

### Performance

- Use `--parallel` for batch operations
- Cache frequently used content with `--cache`
- Use `--incremental` for large documents

### Quality

- Validate content with `--strict`
- Use `--lint` to check for issues
- Enable `--verbose` for detailed logs

### Organization

- Use consistent naming conventions
- Organize output files by campaign/session
- Version control your configuration files

## Troubleshooting

Common issues and solutions:

### Memory Issues

For large conversions:

```bash
# Increase memory limit
export STUDIORUM_MAX_MEMORY=4G
studiorum convert adventure "Large Campaign"
```

### Missing Content

When content is not found:

```bash
# Check available sources
studiorum sources list

# Update content index
studiorum index refresh
```

### LaTeX Compilation Errors

Debug LaTeX issues:

```bash
# Generate LaTeX only
studiorum convert creature "Beholder" --format latex --debug

# Use different compiler
studiorum convert --compiler lualatex creature "Beholder"
```

## Next Steps

- **[CLI Reference](cli-reference.md)**: Complete command documentation
- **[MCP Setup](mcp-setup.md)**: Integrate with AI agents
- **[Developer Guide](../developer-guide/index.md)**: Build custom integrations

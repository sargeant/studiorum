# CLI Reference

The command-line interface for 5e2pdf, providing easy access to all functionality.

## Main Application

```{eval-rst}
.. automodule:: dnd5e.cli.main
   :members:
   :undoc-members:
   :show-inheritance:
```

## Commands Module

```{eval-rst}
.. automodule:: dnd5e.cli.commands
   :members:
   :undoc-members:
   :show-inheritance:
```

## Available Commands

The CLI provides the following commands:

### convert
Convert D&D content to PDF format.

```bash
5e2pdf convert --source PHB --content-type spell --output spells.pdf
```

### list
List available content sources and types.

```bash
5e2pdf list sources
5e2pdf list content-types
```

### info
Display information about specific content.

```bash
5e2pdf info --source PHB --name "Fireball"
```

### stats
Show statistics about loaded content.

```bash
5e2pdf stats --source all
```

### setup
Initialize configuration and download content sources.

```bash
5e2pdf setup --interactive
```

## Configuration

The CLI respects configuration from:
- Command-line arguments (highest priority)
- Environment variables (prefixed with `DND5E_`)
- Configuration files (`~/.5e2pdf/config.yaml`)
- Default values (lowest priority)

## Examples

### Basic Usage

```bash
# Convert all PHB spells to PDF
5e2pdf convert --source PHB --content-type spell

# Convert specific creatures
5e2pdf convert --source MM --content-type creature --filter "Ancient Dragon"

# List available content
5e2pdf list sources
5e2pdf list content-types --source PHB
```

### Advanced Usage

```bash
# Custom template and output
5e2pdf convert \
  --source PHB \
  --content-type spell \
  --template custom_spell_template.tex \
  --output custom_spells.pdf \
  --paper-size A4 \
  --columns 2

# Batch processing
5e2pdf convert --source all --content-type all --output-dir ./pdfs/
```

## Error Handling

The CLI provides detailed error messages and logging:

```bash
# Enable debug logging
5e2pdf --log-level DEBUG convert --source PHB

# Validate content before conversion
5e2pdf convert --validate --source PHB --content-type spell
```

See {doc}`/troubleshooting` for common issues and solutions.

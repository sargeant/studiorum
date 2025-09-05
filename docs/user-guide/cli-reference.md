---
title: CLI Reference
description: Complete command-line interface reference for studiorum
---

# CLI Reference

!!! warning "Documentation is work in progress"
    Some of the features described here are planned or got revised without the documentation being updated.
    Use `studioum <command> --help` to see current capabilities.

Complete reference for all studiorum command-line interface commands and options.

## Global Options

Available for all commands:

```bash
studiorum [GLOBAL OPTIONS] COMMAND [COMMAND OPTIONS]
```

| Option | Description | Default |
|--------|-------------|---------|
| `--config FILE` | Configuration file path | `~/.studiorum/config.yaml` |
| `--verbose, -v` | Enable verbose output | `False` |
| `--quiet, -q` | Suppress non-error output | `False` |
| `--help, -h` | Show help message | - |
| `--version` | Show version information | - |

## convert

Convert 5e content to LaTeX or PDF format.

### convert adventure

Convert adventures with optional appendices:

```bash
studiorum convert adventure [OPTIONS] ADVENTURE_NAME
```

**Arguments:**

- `ADVENTURE_NAME`: Name or abbreviation of the adventure

**Options:**

| Option | Description | Default |
|--------|-------------|---------|
| `--output, -o FILE` | Output file path | Auto-generated |
| `--format FORMAT` | Output format (latex, pdf) | `latex` |
| `--compiler COMPILER` | LaTeX compiler (pdflatex, xelatex, lualatex) | `pdflatex` |
| `--creatures` | Include creatures appendix | `False` |
| `--spells` | Include spells appendix | `False` |
| `--items` | Include magic items appendix | `False` |
| `--ultimate-appendix` | Generate recursive appendices (creatures include spells, spells include creatures) | `False` |
| `--template TEMPLATE` | LaTeX template to use | `dnd-5e` |
| `--sources SOURCES` | Comma-separated source books | All enabled |
| `--exclude-sources SOURCES` | Sources to exclude | None |
| `--toc` | Include table of contents | `True` |
| `--index` | Include index | `False` |
| `--debug` | Enable debug output | `False` |

**Examples:**

```bash
# Basic adventure conversion
studiorum convert adventure "sample-adventure"

# With all appendices
studiorum convert adventure "example-adventure" --creatures --spells --items

# With recursive appendices (ultimate mode)
studiorum convert adventure "example-adventure" --creatures --ultimate-appendix

# Generate PDF directly
studiorum convert adventure "my-adventure" --format pdf --output adventure.pdf

# Use specific compiler
studiorum convert adventure "custom-adventure" --compiler xelatex
```

### convert creature

Convert individual creatures or groups:

```bash
studiorum convert creature [OPTIONS] CREATURE_NAME
studiorum convert creatures [OPTIONS]
```

**Arguments:**

- `CREATURE_NAME`: Name of the creature (for single conversion)

**Options:**

| Option | Description | Default |
|--------|-------------|---------|
| `--output, -o FILE` | Output file path | Auto-generated |
| `--format FORMAT` | Output format | `latex` |
| `--cr RANGE` | Challenge rating range (e.g., "5-10") | All |
| `--type TYPE` | Creature type filter | All |
| `--size SIZE` | Creature size filter | All |
| `--environment ENV` | Environment filter | All |
| `--legendary` | Include only legendary creatures | `False` |
| `--sources SOURCES` | Source book filter | All enabled |
| `--template TEMPLATE` | LaTeX template | `dnd-5e` |
| `--sort-by FIELD` | Sort by field (name, cr, type) | `name` |

**Examples:**

```bash
# Single creature
studiorum convert creature "Adult Red Dragon"

# Creatures by CR range
studiorum convert creatures --cr 10-15

# Dragons only
studiorum convert creatures --type dragon --legendary
```

### convert spell

Convert spells:

```bash
studiorum convert spell [OPTIONS] SPELL_NAME
studiorum convert spells [OPTIONS]
```

**Arguments:**

- `SPELL_NAME`: Name of the spell (for single conversion)

**Options:**

| Option | Description | Default |
|--------|-------------|---------|
| `--output, -o FILE` | Output file path | Auto-generated |
| `--format FORMAT` | Output format | `latex` |
| `--level LEVELS` | Spell level(s) (e.g., "1,3,5" or "1-5") | All |
| `--school SCHOOL` | Magic school filter | All |
| `--class CLASS` | Spell class filter | All |
| `--ritual` | Include only ritual spells | `False` |
| `--concentration` | Include only concentration spells | `False` |
| `--sources SOURCES` | Source book filter | All enabled |
| `--sort-by FIELD` | Sort by (name, level, school) | `level` |

**Examples:**

```bash
# Single spell
studiorum convert spell "Fireball"

# Third level spells
studiorum convert spells --level 3

# Evocation spells for wizards
studiorum convert spells --school evocation --class wizard

# Ritual spells
studiorum convert spells --ritual --level 1-5
```

### convert item

Convert magic items and equipment:

```bash
studiorum convert item [OPTIONS] ITEM_NAME
studiorum convert items [OPTIONS]
```

**Arguments:**

- `ITEM_NAME`: Name of the item (for single conversion)

**Options:**

| Option | Description | Default |
|--------|-------------|---------|
| `--output, -o FILE` | Output file path | Auto-generated |
| `--format FORMAT` | Output format | `latex` |
| `--rarity RARITY` | Item rarity filter | All |
| `--type TYPE` | Item type filter | All |
| `--attunement` | Requires attunement only | `False` |
| `--sources SOURCES` | Source book filter | All enabled |
| `--sort-by FIELD` | Sort by (name, rarity, type) | `name` |

**Examples:**

```bash
# Single item
studiorum convert item "Bag of Holding"

# Legendary weapons
studiorum convert items --rarity legendary --type weapon

# Items requiring attunement
studiorum convert items --attunement --rarity "rare,very rare"
```

## list

List available content in the database.

### list adventures

List available adventures:

```bash
studiorum list adventures [OPTIONS]
```

**Options:**

| Option | Description | Default |
|--------|-------------|---------|
| `--sources SOURCES` | Source book filter | All enabled |
| `--recent` | Show recently added content | `False` |
| `--format FORMAT` | Output format (table, json, yaml) | `table` |
| `--limit LIMIT` | Maximum results to show | 100 |

### list content --type creature

List available creatures:

```bash
studiorum list content --type creature [OPTIONS]
```

**Options:**

| Option | Description | Default |
|--------|-------------|---------|
| `--cr RANGE` | Challenge rating filter | All |
| `--type TYPE` | Creature type filter | All |
| `--size SIZE` | Size filter | All |
| `--environment ENV` | Environment filter | All |
| `--legendary` | Legendary creatures only | `False` |
| `--sources SOURCES` | Source book filter | All enabled |
| `--format FORMAT` | Output format | `table` |
| `--limit LIMIT` | Maximum results | 100 |
| `--sort-by FIELD` | Sort field | `name` |

### list content --type spell

List available spells:

```bash
studiorum list content --type spell [OPTIONS]
```

**Options:**

| Option | Description | Default |
|--------|-------------|---------|
| `--level LEVELS` | Spell level filter | All |
| `--school SCHOOL` | Magic school filter | All |
| `--class CLASS` | Spell class filter | All |
| `--ritual` | Ritual spells only | `False` |
| `--concentration` | Concentration spells only | `False` |
| `--sources SOURCES` | Source book filter | All enabled |
| `--format FORMAT` | Output format | `table` |
| `--limit LIMIT` | Maximum results | 100 |

### list content --type item

List available items:

```bash
studiorum list content --type item [OPTIONS]
```

**Options:**

| Option | Description | Default |
|--------|-------------|---------|
| `--rarity RARITY` | Item rarity filter | All |
| `--type TYPE` | Item type filter | All |
| `--attunement` | Requires attunement only | `False` |
| `--sources SOURCES` | Source book filter | All enabled |
| `--format FORMAT` | Output format | `table` |
| `--limit LIMIT` | Maximum results | 100 |

## search

Search across all content types:

```bash
studiorum search [OPTIONS] QUERY
```

**Arguments:**

- `QUERY`: Search query string

**Options:**

| Option | Description | Default |
|--------|-------------|---------|
| `--type TYPE` | Content type filter | All |
| `--sources SOURCES` | Source book filter | All enabled |
| `--format FORMAT` | Output format | `table` |
| `--limit LIMIT` | Maximum results | 50 |
| `--fuzzy` | Enable fuzzy matching | `False` |
| `--case-sensitive` | Case-sensitive search | `False` |

**Examples:**

```bash
# Basic search
studiorum search "dragon"

# Search creatures only
studiorum search "undead" --type creature

# Fuzzy search for misspellings
studiorum search "tarrasq" --fuzzy

# Search specific sources
studiorum search "fiend" --sources "MM,VGtM"
```

## index

Manage the content search index.

### index build

Build or rebuild the search index:

```bash
studiorum index build [OPTIONS]
```

**Options:**

| Option | Description | Default |
|--------|-------------|---------|
| `--rebuild` | Rebuild existing index | `False` |
| `--sources SOURCES` | Index specific sources only | All |
| `--optimize` | Optimize index after build | `True` |

### index status

Show index status and statistics:

```bash
studiorum index status [OPTIONS]
```

**Options:**

| Option | Description | Default |
|--------|-------------|---------|
| `--format FORMAT` | Output format | `table` |
| `--detailed` | Show detailed statistics | `False` |

### index refresh

Refresh index with latest content:

```bash
studiorum index refresh [OPTIONS]
```

**Options:**

| Option | Description | Default |
|--------|-------------|---------|
| `--incremental` | Only update changed content | `True` |
| `--sources SOURCES` | Refresh specific sources | All |

## data

Manage data repositories and sources.

### data list

List available data repositories:

```bash
studiorum data list [OPTIONS]
```

**Options:**

| Option | Description | Default |
|--------|-------------|---------|
| `--format FORMAT` | Output format (table, json) | `table` |

### data add-homebrew

Add homebrew content repository:

```bash
studiorum data add-homebrew [OPTIONS] PATH
```

**Arguments:**

- `PATH`: Path to homebrew content directory or file

**Options:**

| Option | Description | Default |
|--------|-------------|---------|
| `--name NAME` | Repository name | Auto-generated |
| `--description, -d DESC` | Repository description | None |

**Examples:**

```bash
# Add homebrew directory
studiorum data add-homebrew /path/to/homebrew --name "my-homebrew"

# Add single homebrew file
studiorum data add-homebrew homebrew.json -d "Custom monsters"
```

### data add-url

Add URL-based data repository:

```bash
studiorum data add-url [OPTIONS] URL
```

**Arguments:**

- `URL`: URL to remote data repository

**Options:**

| Option | Description | Default |
|--------|-------------|---------|
| `--name NAME` | Repository name | Auto-generated |
| `--description, -d DESC` | Repository description | None |

### data remove

Remove data repository:

```bash
studiorum data remove [OPTIONS] NAME
```

**Arguments:**

- `NAME`: Name of repository to remove

**Options:**

| Option | Description | Default |
|--------|-------------|---------|
| `--force` | Skip confirmation prompt | `False` |

## config

Manage configuration settings.

### config init

Initialize default configuration:

```bash
studiorum config init [OPTIONS]
```

**Options:**

| Option | Description | Default |
|--------|-------------|---------|
| `--force` | Overwrite existing config | `False` |
| `--minimal` | Create minimal config | `False` |
| `--interactive` | Interactive configuration | `False` |

### config show

Display current configuration:

```bash
studiorum config show [OPTIONS]
```

**Options:**

| Option | Description | Default |
|--------|-------------|---------|
| `--format FORMAT` | Output format (yaml, json) | `yaml` |
| `--sanitized` | Hide sensitive values | `True` |
| `--section SECTION` | Show specific section only | All |

### config validate

Validate configuration file:

```bash
studiorum config validate [OPTIONS] [CONFIG_FILE]
```

**Arguments:**

- `CONFIG_FILE`: Configuration file to validate (optional)

**Options:**

| Option | Description | Default |
|--------|-------------|---------|
| `--strict` | Strict validation mode | `False` |
| `--fix` | Attempt to fix issues | `False` |

### config set

Set configuration values:

```bash
studiorum config set [OPTIONS] KEY VALUE
```

**Arguments:**

- `KEY`: Configuration key (e.g., "sources.default")
- `VALUE`: Value to set

**Examples:**

```bash
# Set default output format
studiorum config set output.format pdf

# Set LaTeX compiler
studiorum config set latex.compiler xelatex

# Enable cache
studiorum config set cache.enabled true
```

## cache

Manage conversion cache.

### cache clear

Clear conversion cache:

```bash
studiorum cache clear [OPTIONS]
```

**Options:**

| Option | Description | Default |
|--------|-------------|---------|
| `--type TYPE` | Cache type to clear | All |
| `--older-than DAYS` | Clear entries older than N days | All |
| `--keep-recent COUNT` | Keep N most recent entries | 0 |

### cache stats

Show cache statistics:

```bash
studiorum cache stats [OPTIONS]
```

**Options:**

| Option | Description | Default |
|--------|-------------|---------|
| `--format FORMAT` | Output format | `table` |
| `--detailed` | Show detailed statistics | `False` |

## mcp

MCP (Model Context Protocol) server commands.

### mcp run

Start the MCP server:

```bash
studiorum mcp run [OPTIONS]
```

**Options:**

| Option | Description | Default |
|--------|-------------|---------|
| `--host HOST` | Server host address | `127.0.0.1` |
| `--port PORT` | Server port | Auto |
| `--debug` | Enable debug logging | `False` |
| `--log-level LEVEL` | Logging level | `INFO` |
| `--config FILE` | MCP configuration file | Auto |

### mcp test

Test MCP tools:

```bash
studiorum mcp test [OPTIONS] TOOL_NAME [ARGS...]
```

**Arguments:**

- `TOOL_NAME`: Name of the MCP tool to test
- `ARGS`: Tool-specific arguments

**Examples:**

```bash
# Test creature lookup
studiorum mcp test lookup_creature "Ancient Red Dragon"

# Test spell conversion
studiorum mcp test convert_spell "Fireball" --format latex
```

### mcp stats

Show MCP server statistics:

```bash
studiorum mcp stats [OPTIONS]
```

**Options:**

| Option | Description | Default |
|--------|-------------|---------|
| `--watch` | Watch statistics in real-time | `False` |
| `--format FORMAT` | Output format | `table` |

## health

System health and diagnostics.

### health check

Run system health checks:

```bash
studiorum health check [OPTIONS]
```

**Options:**

| Option | Description | Default |
|--------|-------------|---------|
| `--detailed` | Show detailed diagnostics | `False` |
| `--fix-issues` | Attempt to fix found issues | `False` |
| `--format FORMAT` | Output format | `table` |

### health version

Show detailed version information:

```bash
studiorum health version [OPTIONS]
```

**Options:**

| Option | Description | Default |
|--------|-------------|---------|
| `--format FORMAT` | Output format | `table` |
| `--check-updates` | Check for available updates | `False` |

## logs

View and manage logs.

### logs show

Display recent logs:

```bash
studiorum logs show [OPTIONS]
```

**Options:**

| Option | Description | Default |
|--------|-------------|---------|
| `--tail LINES` | Show last N lines | 100 |
| `--level LEVEL` | Filter by log level | All |
| `--component COMPONENT` | Filter by component | All |
| `--since TIME` | Show logs since time/date | All |
| `--follow, -f` | Follow log output | `False` |

### logs clear

Clear old log files:

```bash
studiorum logs clear [OPTIONS]
```

**Options:**

| Option | Description | Default |
|--------|-------------|---------|
| `--older-than DAYS` | Clear logs older than N days | 30 |
| `--keep-recent COUNT` | Keep N most recent log files | 10 |

## Environment Variables

Override configuration with environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `STUDIORUM_CONFIG_DIR` | Configuration directory | `~/.studiorum` |
| `STUDIORUM_DATA_DIR` | Data directory | `~/.studiorum/data` |
| `STUDIORUM_CACHE_DIR` | Cache directory | `~/.studiorum/cache` |
| `STUDIORUM_LOG_LEVEL` | Global log level | `INFO` |
| `STUDIORUM_MAX_MEMORY` | Maximum memory usage | System default |
| `STUDIORUM_PARALLEL_WORKERS` | Parallel processing workers | CPU count |

## Exit Codes

Studiorum uses standard exit codes:

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error |
| 2 | Command line error |
| 3 | Configuration error |
| 4 | Content not found |
| 5 | Conversion error |
| 6 | Network error |
| 7 | Permission error |
| 8 | System resource error |

## Examples

### Common Workflows

**Campaign Preparation**:

```bash
# Generate complete campaign materials
studiorum convert adventure "my-campaign" \
    --creatures --spells --items \
    --format pdf --output campaign-complete.pdf

# Create separate creature manual
studiorum convert creatures --sources SRD \
    --template creature-cards --output srd-creatures.pdf
```

**Custom Content**:

```bash
# Convert homebrew content
studiorum convert creatures --sources MY-HOMEBREW \
    --template custom --output homebrew-monsters.tex

# Merge with official content
studiorum convert adventure "Custom Campaign" \
    --sources MY-HOMEBREW --output campaign.pdf
```

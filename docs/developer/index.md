# Developer Documentation

This document provides a deep dive into the technical architecture, development workflow, and coding conventions for the 5e2pdf project.

## Architecture Overview

The project is built on a modern, asynchronous Python architecture designed for performance, extensibility, and type safety.

### ✅ **ALL PHASES COMPLETE** ✅

**Phase 1: Foundation (`src/core/`)**

- **Data Models** - Type-safe Pydantic v2 models for all D&D content types
- **Omnidexer System** - Efficient async data loading with hash-based indexing
- **Tag Resolution** - Complete `{@type name|source|display}` tag parsing with 25+ handlers
- **Configuration** - Environment-based settings with automatic path detection
- **Caching** - Performance optimization with disk-based caching system

**Phase 2: Rendering System (`src/renderers/`)**

- **Abstract Interfaces** - Clean renderer base classes for multiple output formats
- **LaTeX Pipeline** - Complete document generation with D&D-style templates
- **Content Renderers** - Specialized rendering for spells, creatures, items, adventures
- **Template Engine** - Flexible system with built-in D&D layouts and custom templates

**Phase 3: Modern CLI & Migration (`src/cli/`)**

- **Modern CLI** - Professional interface with Typer, Rich output, and async operations
- **Legacy Compatibility** - Full backwards compatibility for existing scripts and workflows
- **Build Integration** - Updated build scripts supporting both modern and legacy modes
- **Performance** - Optimized with caching, parallel processing, and efficient data loading

### 📊 **System Status**

- **100+ Tests** across all components with comprehensive coverage
- **Type Safety** throughout with modern Python patterns
- **Async Architecture** for optimal performance
- **Extensible Design** ready for new content types and output formats

## Directory Structure

```
5e2pdf/
├── src/                         # Python source code (MODERN ARCHITECTURE)
│   ├── core/                    # Core foundation modules
│   │   ├── models/              # Pydantic data models (Spell, Creature, Item, etc.)
│   │   ├── loaders/             # Data loading and omnidexer system
│   │   ├── indexer/             # Tag resolution and cross-referencing
│   │   ├── config/              # Configuration and settings management
│   │   └── cache.py             # Performance caching system
├── renderers/               # Modern rendering system
│   │   ├── base/                # Abstract renderer interfaces
│   │   └── latex/               # LaTeX-specific implementations
│   ├── cli/                     # Modern CLI interface with Typer
│   │   ├── commands/            # CLI command modules
│   │   ├── main.py              # Main CLI application
│   │   └── compat.py            # Legacy compatibility layer
├── assets/                      # Static resources
│   ├── fonts/                   # D&D-style fonts
│   ├── images/                  # Images and graphics
│   └── packages/                # LaTeX packages
├── json_data/                   # Input JSON files (managed by the tool)
├── output/                      # Generated LaTeX files
├── build/                       # LaTeX compilation artifacts (gitignored)
├── scripts/                     # Build automation scripts
├── tests/                       # Comprehensive test suite
│   ├── unit/                    # Unit tests for core components
│   ├── integration/             # Integration tests
│   └── fixtures/                # Test data and fixtures
├── pyproject.toml              # Modern Python project configuration
├── LICENSE                     # Project license
└── README.md                   # Main project README
```

## Development Workflow

### Running Tests

We use `pytest` for our comprehensive test suite.

```bash
# Run all tests
uv run pytest

# Run tests in a specific directory
uv run pytest tests/unit/

# Run a specific test file
uv run pytest tests/unit/test_omnidexer.py

# Run tests with a coverage report
uv run pytest --cov=src --cov-report=html
```

### Code Quality

We use `ruff` for linting, `black` for formatting, and `mypy` for static type checking.

```bash
# Format code
uv run black src/ tests/

# Lint code
uv run ruff check .

# Type checking
uv run mypy src/
```

### Architecture Usage Examples

#### Working with the Omnidexer

```python
import asyncio
from src.core.loaders.omnidexer import Omnidexer
from src.core.models.content import ContentType

async def example():
    # Create and load omnidexer
    omnidexer = Omnidexer()
    await omnidexer.load_all_data()

    # Find specific content
    fireball = omnidexer.find(ContentType.SPELL, "Fireball", "PHB")
    ancient_dragon = omnidexer.find(ContentType.CREATURE, "Ancient Red Dragon", "MM")

    # Search content
    fire_spells = omnidexer.search("Fire", ContentType.SPELL)
    all_creatures = omnidexer.get_all_by_type(ContentType.CREATURE)

    # Get statistics
    stats = omnidexer.get_statistics()
    print(f"Loaded {stats['total_items']} items")

asyncio.run(example())
```

#### Using the Tag Resolver

```python
import asyncio
from src.core.loaders.omnidexer import Omnidexer
from src.core.indexer.tag_resolver import TagResolver

async def example():
    omnidexer = Omnidexer()
    await omnidexer.load_all_data()

    resolver = TagResolver(omnidexer)

    # Process text with tags
    text = "Cast {@spell Fireball|PHB} at the {@creature Ancient Red Dragon|MM}!"
    latex_output = resolver.process_text(text)
    print(latex_output)
    # Output: "Cast \textit{Fireball} at the \textbf{Ancient Red Dragon}!"

asyncio.run(example())
```

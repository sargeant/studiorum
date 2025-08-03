# API Reference

Technical API documentation organized by functional area.

## Core APIs

```{toctree}
:maxdepth: 1

omnidexer
content-models
core-utilities
```

## Rendering & Output

```{toctree}
:maxdepth: 1

latex-rendering
```

## System Configuration

```{toctree}
:maxdepth: 1

configuration
```

## Overview

The API Documentation provides comprehensive reference material for all public interfaces in 5e2pdf. This includes:

- **Core APIs**: Primary interfaces for content loading, indexing, and rendering
- **LaTeX Rendering**: Document generation and LaTeX compilation system
- **Content Models**: Data structures representing D&D content
- **Core Utilities**: Cache system, text processing, and helper functions
- **Configuration APIs**: Settings and customization interfaces

## Key APIs

### [Omnidexer](omnidexer.md)

The omnidexer is 5e2pdf's content indexing and discovery system. It provides:

- Multi-index architecture for fast content lookup
- Deep indexing of nested content (class features, adventure sections, etc.)
- Type-safe content resolution with Pydantic validation
- Performance monitoring and statistics

**Key Classes:**
- `Omnidexer`: Main indexing class
- `IndexEntry`: Pydantic BaseModel for indexed content with hash and lookup key validation
- `DeepIndexable`: Protocol for content with nested items

### [LaTeX Rendering](latex-rendering.md)

The LaTeX rendering system provides complete document generation capabilities:

- Document rendering with template engine support
- Multi-engine LaTeX compilation (PDFLaTeX, XeLaTeX, LuaLaTeX)
- Recursive entry processing for complex content structures
- Unicode character mapping and LaTeX escaping
- Template management and configuration

**Key Classes:**
- `LaTeXDocumentRenderer`: Main document rendering interface
- `LaTeXTemplateEngine`: Jinja2-based template system
- `RecursiveEntryProcessor`: Processes nested 5etools content
- `LaTeXCompiler`: Multi-engine compilation management

### [Content Models](content-models.md)

Base classes and data structures for representing D&D content with comprehensive Pydantic validation:

- `BaseContent`: Base class for all content types with Pydantic validation
- `ContentType`: Enumeration of supported content types
- Specialized models for spells, creatures, items, adventures, books
- Infrastructure models for indexing, resolution, and layout
- Nested content support for complex structures
- Source metadata and validation

**Core Content Models:**
- `BaseContent`: Foundation for all content models
- `Spell`, `Creature`, `Item`: Core content type models with field validation
- `Adventure`, `Book`: Complex content with nested structures

**Infrastructure Models (Tier 3 Migration):**
- `IndexEntry`: Content indexing with hash and lookup key validation
- `ContentResolutionResult`: Search result validation and normalization
- `LayoutHint`, `LayoutContext`: Layout system with column count constraints
- `ContentReference`, `SpecialTag`: Tag processing with content type validation

### [Core Utilities](core-utilities.md)

Foundational utilities and helper functions used throughout the system:

- Unified caching system with disk-based persistence
- LaTeX text escaping with comprehensive Unicode support
- Spell reference parsing from 5etools tags
- Content type resolution and model selection
- Structured logging with colored output
- Protocol-based interfaces for extensibility

**Key Functions:**
- `escape_latex_text()`: LaTeX character escaping
- `cached()`: Function result caching decorator
- `SpellReferenceParser`: Extract spell references from text
- `ContentTypeResolver`: Automatic content type detection

### [Configuration](configuration.md)

Comprehensive configuration system with environment variable support:

- Application settings with Pydantic validation
- LaTeX-specific document and engine configuration
- Content source management for GitHub and directory sources
- Environment variable integration and .env file support
- Hierarchical configuration loading with override priorities

**Key Classes:**
- `Settings`: Main application configuration
- `LaTeXDocumentConfig`: Document generation settings
- `ContentSource`: Content data source configuration
- `LaTeXEngineConfig`: Compilation engine settings

## Usage Patterns

### Basic Content Loading

```python
from dnd5e.core.loaders.omnidexer import Omnidexer
from dnd5e.core.models.content import ContentType

# Initialize and load content
omnidexer = Omnidexer()
await omnidexer.load_all_data()

# Find specific content
spell = omnidexer.find(ContentType.SPELL, "Fireball", "PHB")
```

### Deep Indexing

```python
# Enable deep indexing for nested content
omnidexer = Omnidexer(enable_deep_indexing=True)
await omnidexer.load_all_data()

# Find nested content
action_surge = omnidexer.find(ContentType.CLASS_FEATURE, "Action Surge", "PHB")
adventure_section = omnidexer.find(ContentType.ADVENTURE_SECTION, "Chapter 1", "LMoP")
```

### Custom Content Types

```python
from dnd5e.core.interfaces import DeepIndexable
from dnd5e.core.models.content import BaseContent

class CustomContent(BaseContent, DeepIndexable):
    def get_deep_index_entries(self, omnidexer: "Omnidexer") -> list[BaseContent]:
        # Return nested content for indexing
        return self.extract_nested_items()
```

## API Stability

5e2pdf follows semantic versioning:

- **Major versions** (1.0, 2.0): Breaking API changes
- **Minor versions** (1.1, 1.2): New features, backward compatible
- **Patch versions** (1.1.1, 1.1.2): Bug fixes, backward compatible

## Deprecation Policy

When APIs need to change:

1. **Deprecation warnings** are added in the version before removal
2. **Migration guides** are provided for breaking changes
3. **Backward compatibility** is maintained for at least one major version

## Getting Help

- Check the [implementation guides](../system-guide/component-deep-dives/index.md) for detailed explanations
- Look at [examples](../../examples/index.md) for practical usage patterns
- Report API issues on [GitHub](https://github.com/sargeant/5e2pdf/issues)

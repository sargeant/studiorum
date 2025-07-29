# API Documentation

Complete reference for all public APIs in 5e2pdf.

## Table of Contents

```{toctree}
:maxdepth: 2

omnidexer
```

## Overview

The API Documentation provides comprehensive reference material for all public interfaces in 5e2pdf. This includes:

- **Core APIs**: Primary interfaces for content loading, indexing, and rendering
- **Content Models**: Data structures representing D&D content
- **Extension Points**: Interfaces for adding new content types and renderers
- **Configuration APIs**: Settings and customization interfaces

## Key APIs

### [Omnidexer](omnidexer.md)

The omnidexer is 5e2pdf's content indexing and discovery system. It provides:

- Multi-index architecture for fast content lookup
- Deep indexing of nested content (class features, adventure sections, etc.)
- Type-safe content resolution
- Performance monitoring and statistics

**Key Classes:**
- `Omnidexer`: Main indexing class
- `IndexEntry`: Indexed content metadata
- `DeepIndexable`: Protocol for content with nested items

### Content Models

Base classes and types for representing D&D content:

- `BaseContent`: Base class for all content types
- `ContentType`: Enumeration of supported content types
- Specific content models (Spell, Creature, Adventure, etc.)

### Parsers and Loaders

APIs for loading and parsing 5e.tools JSON data:

- Content loaders for different source types
- Entry parsers for complex JSON structures
- Validation and error handling

### Renderers

Interfaces for generating output formats:

- `BaseRenderer`: Abstract base for all renderers
- LaTeX-specific rendering components
- Template system for customization

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

- Check the [implementation guides](../implementation/index.md) for detailed explanations
- Look at [examples](../../examples/index.md) for practical usage patterns
- Report API issues on [GitHub](https://github.com/sargeant/5e2pdf/issues)

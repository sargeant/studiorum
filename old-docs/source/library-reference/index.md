# Library Reference

This section provides comprehensive API documentation for the 5e2pdf package.

## Overview

The 5e2pdf package is organized into several key modules:

- **CLI**: Command-line interface for converting D&D content to PDF
- **Core**: Business logic, data models, and content loading
- **Renderers**: Output generation in various formats (LaTeX/PDF)

## Quick Start

```python
from dnd5e.core.loaders import Omnidexer
from dnd5e.renderers.latex import LaTeXDocumentRenderer

# Load D&D content
omnidexer = Omnidexer()
spells = omnidexer.find(content_type="spell", source="PHB")

# Render to LaTeX
renderer = LaTeXDocumentRenderer()
output = renderer.render_content(spells)
```

## API Documentation

```{toctree}
:maxdepth: 2

api/index
cli
models
loaders
renderers
config
references
protocols
```

## Key Classes

The most commonly used classes in the API:

- {class}`dnd5e.core.loaders.omnidexer.Omnidexer` - Content loading and searching
- {class}`dnd5e.core.models.spells.Spell` - Spell data model
- {class}`dnd5e.core.models.creatures.Creature` - Creature data model
- {class}`dnd5e.renderers.latex.document.LaTeXDocumentRenderer` - LaTeX output generation
- {class}`dnd5e.core.config.settings.Settings` - Configuration management

## Configuration

See {doc}`config` for detailed configuration options and {doc}`/installation` for setup instructions.

## Examples

For practical usage examples, see:
- {doc}`/examples/index` - Code examples
- {doc}`/basic-usage` - User guide
- {doc}`/component-guides` - Implementation guides

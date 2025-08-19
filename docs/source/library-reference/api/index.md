# API Reference

```{eval-rst}
.. currentmodule:: dnd5e

This section contains the complete API reference for the 5e2pdf package, automatically
generated from the source code docstrings.

.. note::
   This is the technical API reference. For user guides and tutorials, see the
   :doc:`/user-guide/index` section.
```

## Core Modules

The `dnd5e` package is organized into the following main modules:

```{eval-rst}
.. autosummary::
   :toctree: generated
   :recursive:
   :maxdepth: 1

   dnd5e.core
   dnd5e.cli
   dnd5e.renderers
   dnd5e.utils
```

## Key Components

### Content Loading

```{eval-rst}
.. autoclass:: dnd5e.core.loaders.omnidexer.Omnidexer
   :members:
   :show-inheritance:
```

### Data Models

```{eval-rst}
.. automodule:: dnd5e.core.models
   :members:
   :show-inheritance:
```

### Rendering

```{eval-rst}
.. automodule:: dnd5e.renderers.latex
   :members:
   :show-inheritance:
```

### CLI Interface

```{eval-rst}
.. automodule:: dnd5e.cli.main
   :members:
   :show-inheritance:
```

## Quick Reference

The API documentation includes:

- **Class documentation**: Full class signatures with all methods and attributes
- **Function documentation**: Parameters, return types, and usage examples
- **Module documentation**: Module-level functions and constants
- **Cross-references**: Links between related components
- **Source code**: Direct links to the source code via the `[source]` link

## Common Entry Points

- {class}`~dnd5e.core.loaders.omnidexer.Omnidexer` - Main entry point for content loading
- {mod}`~dnd5e.cli.main` - CLI application entry point
- {class}`~dnd5e.core.result.Result` - Error handling pattern

---
title: Introduction
description: Architecture overview, API reference, and development patterns for building applications with studiorum
---

# Developer Guide

Build applications with studiorum's modern Python architecture for 5e content processing.

## Quick Start Examples

### Simple Content Access

Load and explore 5e content programmatically:

```python
from studiorum.cli.utils import get_omnidexer

# Get all spells
omnidexer = get_omnidexer()
spells = list(omnidexer.get_all_by_type("spell"))

# Find specific content
light = list(omnidexer.find_all("spell", "Light"))[0]
print(f"{light.name}: {light.get_level_text()}")
```

### Content Processing

Work with typed models and validation:

```python
from studiorum.cli.utils import get_omnidexer
from studiorum.core.models.spells import Spell

omnidexer = get_omnidexer()

# Access spell properties with full type safety
spell: Spell = list(omnidexer.find_all("spell", "Sacred Flame"))[0]
print(f"School: {spell.school}")         # "Evocation"
print(f"Verbal: {spell.components.verbal}")  # True

# Render processed spell text using the template pipeline
print(spell.get_text())
```

### Rendering Pipeline

Convert 5e content to LaTeX/PDF:

```python
from studiorum.cli.utils import get_omnidexer
from studiorum.core.references.content_tracker import ContentTracker
from studiorum.core.services.appendix_generator import AppendixGenerator, AppendixFlags
from studiorum.latex_engine.core.template_engine import LaTeXTemplateEngine

# Services
omnidexer = get_omnidexer()
template_engine = LaTeXTemplateEngine()

# Track content references
tracker = ContentTracker()
tracker.add_content("spell", "Guidance", "SRD")

# Generate appendices with referenced content
generator = AppendixGenerator(omnidexer, template_engine)
flags = AppendixFlags(spells=True)
appendices = generator.generate_appendices(tracker, flags)

# Each appendix contains ready-to-embed LaTeX content
for appendix in appendices:
    print(appendix.content)
```

## Development Path

1. **[Architecture](architecture.md)** - Understand the system design
1. **[Models](models.md)** - Work with typed 5e content models
1. **[API Reference](api/)** - Explore services and rendering systems

## Core Contribution

Contribute to studiorum itself:

1. **[Contributing](contributing.md)** - Development workflow and standards
1. **[Getting Started](getting-started.md#core-development)** - Contributor setup

---

## Resources

- 📖 **[Architecture Deep Dive](architecture.md)** - Complete system design
- 🔧 **[API Reference](api/)** - Comprehensive API documentation
- 🤖 **[AI Agent Patterns](ai-agents.md)** - MCP development guide
- 🚀 **[Contributing](contributing.md)** - Join the development community
- 💬 **[Discussions](https://github.com/sargeant/studiorum/discussions)** - Community support

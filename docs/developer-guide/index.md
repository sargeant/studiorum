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
print(f"{light.name}: {light.level}th level cantrip")
```

### Content Processing

Work with typed models and validation:

```python
from studiorum.core.models.spells import Spell

# Access spell properties with full type safety
spell: Spell = list(omnidexer.find_all("spell", "Sacred Flame"))[0]
print(f"School: {spell.school}")  # "Evocation"
print(f"Verbal: {spell.components.verbal}")  # True

# Process spell entries programmatically
for entry in spell.entries:
    if hasattr(entry, 'get_text'):
        print(entry.get_text())
```

### Rendering Pipeline

Convert 5e content to LaTeX/PDF:

```python
from studiorum.core.services.appendix_generator import AppendixGenerator
from studiorum.core.references.content_tracker import ContentTracker

# Track content references
tracker = ContentTracker()
tracker.add_content("spell", "Guidance", "SRD")

# Generate appendix with referenced content
appendix_gen = AppendixGenerator(omnidexer)
appendices = appendix_gen.generate_appendices(tracker, include_spells=True)

# Convert to LaTeX
for appendix in appendices:
    print(f"\\section{{{appendix.title}}}")
    for item in appendix.items:
        print(item.render_latex())
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

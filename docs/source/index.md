---
layout: landing
description: Convert D&D 5e JSON data from 5e.tools to beautifully formatted LaTeX/PDF documents
---

# 5e2pdf

```{rst-class} lead
Convert D&D 5e JSON data from [5e.tools](https://5e.tools) to beautifully formatted LaTeX/PDF documents.
```

```{warning}
This tool is under active development and not yet in a fully working state.
```

## Overview

5e2pdf is a Python CLI tool that transforms the comprehensive D&D 5e JSON datasets from 5e.tools into professional-quality PDF documents using LaTeX. Whether you're a DM preparing for sessions or a player creating reference materials, 5e2pdf provides the tools to create custom, print-ready D&D content.

## Key Features

```{grid} 1 2 3 3
:gutter: 3

```{grid-item-card} 📚 Comprehensive Content Support
:text-align: center

Works with all 5e.tools JSON data including spells, creatures, items, adventures, and more
```

```{grid-item-card} ✨ Professional Typography
:text-align: center

LaTeX-based rendering for publication-quality output with beautiful formatting
```

```{grid-item-card} 🔍 Deep Content Indexing
:text-align: center

Advanced omnidexer system discovers nested content like class features and adventure sections
```

```{grid-item-card} 🎯 Flexible Output
:text-align: center

Generate PDFs for specific content types, sources, or custom collections
```

```{grid-item-card} 🐍 Modern Python
:text-align: center

Built with Python 3.12, async/await, and full type safety
```

```{grid-item-card} 📖 Automated Documentation
:text-align: center

Sphinx-powered documentation with GitHub Pages deployment
```

## Quick Start

Get up and running with 5e2pdf in minutes:

````{grid} 1 1 2 2
:gutter: 2

```{grid-item-card} 1️⃣ Install
:text-align: center
:class-header: highlight-card

```bash
pip install 5e2pdf
```
```

```{grid-item-card} 2️⃣ Setup Sources
:text-align: center
:class-header: highlight-card

```bash
5e2pdf setup wizard
```
```

```{grid-item-card} 3️⃣ Generate a Book
:text-align: center
:class-header: highlight-card

```bash
5e2pdf convert book phb --pdf --a4
```
```

```{grid-item-card} 4️⃣ Create Adventures
:text-align: center
:class-header: highlight-card

```bash
5e2pdf convert adventure lmop --pdf
```
```
````

## Getting Started

````{grid} 1 1 3 3
:gutter: 3

```{grid-item-card} 📖 User Guide
:link: user-guide/index
:link-type: doc
:text-align: center

Complete guide for users getting started with 5e2pdf
```

```{grid-item-card} 🔧 API Reference
:link: api/index
:link-type: doc
:text-align: center

Comprehensive API documentation and references
```

```{grid-item-card} 💡 Examples
:link: examples/index
:link-type: doc
:text-align: center

Practical examples and tutorials to get you started
```
````

```{toctree}
:hidden:
:caption: For Users

quickstart
user-guide/index
```

```{toctree}
:hidden:
:caption: For Developers
:max_depth: 2

developer/index
developer/contributing
api/index
```

---

````{grid} 1 1 2 2
:gutter: 3
:class-container: action-section

```{grid-item-card}
:text-align: center
:class-header: action-button

[📚 Get Started](quickstart)
+++
Start using 5e2pdf today
```

```{grid-item-card}
:text-align: center
:class-header: action-button

[🐛 Report Issues](https://github.com/sargeant/5e2pdf/issues)
+++
Help improve 5e2pdf
```
````

## Project Information

````{grid} 1 2 4 4
:gutter: 2

```{grid-item-card} GitHub
:text-align: center

[sargeant/5e2pdf](https://github.com/sargeant/5e2pdf)
```

```{grid-item-card} Version
:text-align: center

{{version}}
```

```{grid-item-card} Python
:text-align: center

3.12+
```

```{grid-item-card} License
:text-align: center

MIT
```
````

---
```{rst-class} text-center lead
*Built with ❤️ for the D&D community*
```

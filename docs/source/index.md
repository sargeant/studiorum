# 5e2pdf Documentation

Convert D&D 5e JSON data from [5e.tools](https://5e.tools) to beautifully formatted LaTeX/PDF documents.

## Overview

5e2pdf is a Python CLI tool that transforms the comprehensive D&D 5e JSON datasets from 5e.tools into professional-quality PDF documents using LaTeX. Whether you're a DM preparing for sessions or a player creating reference materials, 5e2pdf provides the tools to create custom, print-ready D&D content.

## Key Features

- **Comprehensive Content Support**: Works with all 5e.tools JSON data including spells, creatures, items, adventures, and more
- **Professional Typography**: LaTeX-based rendering for publication-quality output
- **Deep Content Indexing**: Advanced omnidexer system discovers nested content like class features and adventure sections
- **Flexible Output**: Generate PDFs for specific content types, sources, or custom collections
- **Modern Python**: Built with Python 3.12, async/await, and full type safety

## Quick Start

```bash
# Install 5e2pdf
pip install 5e2pdf

# Generate a spell compendium
5e2pdf spell --source PHB --output phb-spells.pdf

# Create creature stat blocks
5e2pdf creature --cr "1-5" --type humanoid --output low-level-npcs.pdf

# Generate adventure content
5e2pdf adventure --name "Lost Mine of Phandelver" --output lmop.pdf
```

## Documentation Structure

```{toctree}
:maxdepth: 2
:caption: User Guide

quickstart
user-guide/index
```

```{toctree}
:maxdepth: 2
:caption: Developer Documentation

developer/index
```

```{toctree}
:maxdepth: 2
:caption: Examples

examples/index
```

## Project Information

- **GitHub**: [sargeant/5e2pdf](https://github.com/sargeant/5e2pdf)
- **Version**: 0.3.1
- **Python**: 3.12+
- **License**: MIT

## Community

- Report bugs or request features on [GitHub Issues](https://github.com/sargeant/5e2pdf/issues)
- Contribute to the project through [Pull Requests](https://github.com/sargeant/5e2pdf/pulls)
- Join discussions in the project's community spaces

---

*Built with ❤️ for the D&D community*

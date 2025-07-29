# 5e2pdf Documentation

```{warning}
This tool is under active development and not yet in a fully working state.
```

Convert D&D 5e JSON data from [5e.tools](https://5e.tools) to beautifully formatted LaTeX/PDF documents.

## Overview

5e2pdf is a Python CLI tool that transforms the comprehensive D&D 5e JSON datasets from 5e.tools into professional-quality PDF documents using LaTeX. Whether you're a DM preparing for sessions or a player creating reference materials, 5e2pdf provides the tools to create custom, print-ready D&D content.

## Key Features

- **Comprehensive Content Support**: Works with all 5e.tools JSON data including spells, creatures, items, adventures, and more
- **Professional Typography**: LaTeX-based rendering for publication-quality output
- **Deep Content Indexing**: Advanced omnidexer system discovers nested content like class features and adventure sections
- **Flexible Output**: Generate PDFs for specific content types, sources, or custom collections
- **Modern Python**: Built with Python 3.12, async/await, and full type safety
- **Automated Documentation**: Sphinx-powered documentation with GitHub Pages deployment

## Quick Start

```bash
# Install 5e2pdf
pip install 5e2pdf

# Setup your sources
5e2pdf setup wizard

# Make a book
5e2pdf convert book phb --pdf --a4 --bg=none

# Make an adventure
5e2pdf convert adventure lmop --pdf --letter --bg=print
```

## Documentation Structure

```{toctree}
:maxdepth: 2
:caption: For Users

quickstart
user-guide/index
```

```{toctree}
:maxdepth: 3
:caption: For Developers

developer/index
developer/contributing
examples/index
api/index
```

## Project Information

- **GitHub**: [sargeant/5e2pdf](https://github.com/sargeant/5e2pdf)
- **Version**: {{version}}
- **Python**: 3.12+
- **License**: MIT

## Community

- Report bugs or request features on [GitHub Issues](https://github.com/sargeant/5e2pdf/issues)
- Contribute to the project through [Pull Requests](https://github.com/sargeant/5e2pdf/pulls)
- Join discussions in the project's community spaces

---

*Built with ❤️ for the D&D community*

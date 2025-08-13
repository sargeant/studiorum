# 5e2pdf: D&D 5e to PDF Converter

[![Test Status](https://img.shields.io/github/actions/workflow/status/sargeant/5e2pdf/tests.yml)](https://github.com/sargeant/5e2pdf/actions)
[![Python Version](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![codecov](https://codecov.io/gh/sargeant/5e2pdf/graph/badge.svg?token=2BXDX48UO8)](https://codecov.io/gh/sargeant/5e2pdf)

> [!CAUTION]
> This project is under development and not yet in a working state.

## What is this?

5e2pdf is a powerful command-line tool for D&D players and Dungeon Masters who want to create high-quality, printable documents from digital source files. Whether you're compiling a custom spellbook, a bestiary for your campaign, or a full adventure module, this tool gives you the power to turn JSON data into professional-looking PDFs.

The JSON data uses the same format as 5e.tools – which means you can still load your homebrew and use their dynamic website with the interactive features.

## Features

- **High-Quality PDF Output**: Generates clean, readable PDFs using LaTeX.
- **5e.tools Compatibility**: Works with the 5e.tools JSON data format.
- **Content Management**: Easily manage multiple content sources.
- **Modern CLI**: A powerful and easy-to-use command-line interface.

## Status

This tool is ready to produce print ready PDFs, but has a few rough edges and challenges

| Status | Feature.       | Notes |
| :----: | :------------- | :----------------------- |
| ✅     | Adventures     | Some tables might require hand tuning. |
| ✅     | Books          | Some tables might require hand tuning  |
| ✅     | Spellbooks     | Feature complete.         |
| ❌     | Images         | Not implemented yet. Likely to require hand tuning after. |
| ❌     | DropCaseLine   | The big letter you get at the start of chapters. Proved to be more complicated with this architecture than expected. |
| ❌     | LaTeX compiler | Some support, but realisticly you probably want to edit the .tex output to tweak, then build with `xelatex $texFile` |

## Acknowledgements

This project wouldn't have been possible without the excellent LaTeX templates from [rpgtex](https://github.com/rpgtex/DND-5e-LaTeX-Template) and [ashonit](https://github.com/ashonit/DND-5e-LaTeX-Template).

## Quick Start

### 1. Install Dependencies

You'll need a working **Python 3.12+** environment and **XeLaTeX**.

First, install `uv`, a fast Python package manager:

```bash
# Manual install
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Check out the guide to [installing uv](https://docs.astral.sh/uv/getting-started/installation/)
for other packaging methods.

### 2. Install the Project

Clone the repository and install the required packages:

```bash
git clone https://github.com/sargeant/5e2pdf.git
cd 5e2pdf
uv sync
```

### 3. Configure Content Sources

Run the interactive setup wizard to configure the default content sources:

```bash
uv run 5e2pdf setup wizard
```

### 4. Convert a File

Now you can convert a JSON file to a PDF. For example, to convert a file of spells:

```bash
# This command assumes a 'spells.json' file exists in your directory
uv run 5e2pdf quick spells.json --pdf
```

## License

This project is licensed under the **MIT License**. See the [LICENSE](LICENSE) file for details.

## More Information

For more detailed technical information about the project's architecture, directory structure, and development workflow, please see our [**Developer Documentation**](docs/developer/index.html).

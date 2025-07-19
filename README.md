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
- **5e.tools Compatibility**: Works with the widely-used 5e.tools JSON format.
- **Content Management**: Easily manage multiple content sources.
- **Modern CLI**: A powerful and easy-to-use command-line interface.

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

Run the interactive setup wizard to download and configure the default content sources from 5e.tools:

```bash
uv run 5e2pdf setup wizard
```

### 4. Convert a File

Now you can convert a JSON file to a PDF. For example, to convert a file of spells:

```bash
# This command assumes a 'spells.json' file exists in your directory
uv run 5e2pdf quick spells.json --pdf
```

## Usage

The `5e2pdf` CLI is powerful and easy to use. Here are some common commands.

### Quick Convert

The fastest way to convert a single file.

```bash
# Convert a JSON file to a PDF
uv run 5e2pdf quick path/to/your/file.json --pdf

# Add a custom title and include images
uv run 5e2pdf quick adventure.json --title "My Grand Adventure" --images --pdf
```

### Manage Content Sources

Manage your local and remote content sources.

```bash
# List all configured sources
uv run 5e2pdf sources list

# Update all sources to the latest version
uv run 5e2pdf sources update

# Add a new source from a local directory
uv run 5e2pdf sources add my-content --type directory --path ~/my-dnd-json
```

For more detailed usage and advanced commands, please see our [Usage Guide](docs/user-guide/README.md).

## Contributing

Contributions are welcome! Whether you're fixing a bug, adding a feature, or improving documentation, we appreciate your help.

1. **Fork the repository** and clone it locally.
2. **Install development dependencies**: `uv sync --extra dev`
3. **Create a feature branch**: `git checkout -b feature/my-new-feature`
4. **Make your changes** and add tests.
5. **Run tests and quality checks**:

    ```bash
    uv run pytest
    uv run ruff check src tests
    uv run mypy src/
    ```

6. **Submit a pull request** with a clear description of your changes.

## License

This project is licensed under the **MIT License**. See the [LICENSE](LICENSE) file for details.

## More Information

For more detailed technical information about the project's architecture, directory structure, and development workflow, please see our [**Developer Documentation**](docs/developer/index.html).

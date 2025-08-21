# Studiorum: AI Toolkit for players of D&D 5e

[![Test Status](https://img.shields.io/github/actions/workflow/status/sargeant/studiorum/tests.yml)](https://github.com/sargeant/studiorum/actions)
[![Python Version](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![codecov](https://codecov.io/gh/sargeant/studiorum/graph/badge.svg?token=2BXDX48UO8)](https://codecov.io/gh/sargeant/studiorum)

> [!CAUTION]
> This project is under development. Some features are buggy; some don't work at at all. Check back for v1.0 soon.

## What is this?

Studiorum is a command-line and MCP tool for D&D players and Dungeon Masters. Using the MCP interface, you can connect AI tools to the complete system reference document (SRD) and explore or homebrew content.

Using the command-line interface you can generate print-quality PDFs of spells, creatures, or your homebrew adventures. Whether you're compiling a custom spellbook, a bestiary for your campaign, or a full adventure module, this tool gives you the power to turn your ideas into professional-looking PDFs.

The underlying data uses the same format as 5e.tools – which means you can still load your homebrew and use their dynamic website with the interactive features.

For full usage, check out the [documentation](https://studiorum.ai/docs/).

## Features

- **AI Integration**: MCP interface to bring mechanial details and homebrew power to AI.
- **Modern CLI**: A powerful and easy-to-use command-line interface.
- **High-Quality PDF Output**: Generates clean, readable PDFs using LaTeX.
- **5e.tools Compatibility**: Works with the 5e.tools JSON data format.
- **Content Management**: Easily manage multiple content sources.

## Getting data

This repository contains only content available under the [SRD](https://www.dndbeyond.com/srd). If you need additional data, you should look for a github source to add with `studiorum sources add my-data-source --type github --url X`.

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
git clone https://github.com/sargeant/studiorum.git
cd studiorum
uv sync
```

### 3. Configure Content Sources

Run the interactive setup wizard (no relation) to configure the default content sources:

```bash
uv run studiorum setup wizard
```

### 4. Make the SRD spellbook

Assuming you added the SRD datasource, you can now use the `5ep2df onvert spells` command:

```bash
# This assumes you have added the SRD datasource
uv run studiorum convert spells --pdf
```

## License

This project is licensed under the **MIT License**. See the [LICENSE](LICENSE) file for details.

## More Information

For more detailed technical information about the project's architecture, directory structure, and development workflow, please see our [**Developer Documentation**](http://studiorum.sargeant.net.nz/developer/index.html).

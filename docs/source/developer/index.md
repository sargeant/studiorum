# Developer Documentation

Technical documentation for contributors and developers extending 5e2pdf.

## Overview

The Developer Documentation provides in-depth technical information about 5e2pdf's architecture, APIs, and extension points. This section is intended for:

- Contributors wanting to submit pull requests
- Developers integrating 5e2pdf into other tools
- Advanced users creating custom renderers or parsers
- Anyone interested in understanding how 5e2pdf works internally

## Key Components

### API Documentation

Complete reference for all public APIs, including:

- **[Omnidexer API](api/omnidexer.md)**: Content indexing and discovery system
- Core models and content types
- Renderer interfaces
- Configuration and settings

### Implementation Guides

Detailed guides for understanding and extending key systems:

- **[Loader Architecture](implementation/loader-architecture.md)**: Sophisticated dual-file loading system with caching
- **[Deep Indexing](implementation/deep-indexing.md)**: How the omnidexer discovers nested content
- Content parsing and validation
- LaTeX rendering pipeline
- Performance optimization techniques

### Contributing

Information for contributors:

- **[Contributing Guide](contributing.md)**: How to contribute to the project
- **[Dependency Management](dependency-management.md)**: Dependency management strategy and best practices
- **[Troubleshooting](troubleshooting.md)**: Comprehensive error handling and debugging guide
- Code style and standards
- Testing requirements
- Pull request process

### Architecture

High-level system design and design decisions:

- **[System Architecture](architecture.md)**: Overall system structure
- Component relationships
- Data flow diagrams
- Extension points

## Development Setup

```bash
# Clone the repository
git clone https://github.com/sargeant/5e2pdf.git
cd 5e2pdf

# Set up development environment
uv sync --extra dev

# Run tests
uv run pytest

# Run linting
uv run ruff check src tests
```

## Project Structure

```
src/dnd5e/
├── cli/                 # Command-line interface
├── core/               # Core functionality
│   ├── loaders/        # Data loading and omnidexer
│   ├── models/         # Content models and types
│   ├── parsers/        # Content parsing logic
│   └── config/         # Configuration management
└── renderers/          # Output rendering (LaTeX, etc.)
    └── latex/          # LaTeX-specific rendering
```

## Getting Involved

- **Issues**: Report bugs or request features on [GitHub Issues](https://github.com/sargeant/5e2pdf/issues)
- **Discussions**: Join conversations about features and design
- **Pull Requests**: Contribute code improvements and new features
- **Documentation**: Help improve and expand documentation

## Code Quality

5e2pdf maintains high code quality standards:

- **Type Safety**: Full mypy compliance with Python 3.12 types
- **Testing**: Comprehensive test coverage with pytest
- **Linting**: Code formatting with ruff
- **Documentation**: Inline docstrings and comprehensive guides

## Table of Contents

```{toctree}
:maxdepth: 1
:caption: Project Information

architecture
contributing
dependency-management
troubleshooting
```

```{toctree}
:maxdepth: 2
:caption: Implementation Guides

implementation/index
```

```{toctree}
:maxdepth: 2
:caption: API Documentation

api/index
```

For detailed information on any of these topics, explore the sections below.

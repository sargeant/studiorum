# Developer Documentation

Technical documentation for contributors and developers extending 5e2pdf.

## Choose Your Path

The Developer Documentation is organized by audience and use case:

::::{grid} 1 2 2 3

:::{grid-item-card} Getting Started
:link: getting-started/index
:link-type: doc

Audience-specific onboarding for developers, AI agents, and new contributors.
:::

:::{grid-item-card} System Guide
:link: system-guide/index
:link-type: doc

Architecture overview and detailed component implementation guides.
:::

:::{grid-item-card} Development Workflows
:link: development-workflows/index
:link-type: doc

Methodologies, quality standards, and systematic approaches.
:::

:::{grid-item-card} API Reference
:link: api-reference/index
:link-type: doc

Technical API documentation organized by functional area.
:::

:::{grid-item-card} Contributing Guide
:link: contributing/index
:link-type: doc

Everything needed to contribute code, documentation, and improvements.
:::

::::

## Overview

This documentation serves multiple audiences:

- **Developers** - Strategic guidance for feature development and architectural decisions
- **AI Agents** - Systematic approaches, task frameworks, and quality validation patterns
- **New Contributors** - Progressive onboarding from first contribution to independent development

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

- **[Contributing Guide](contributing/contributing.md)**: How to contribute to the project
- **[Dependency Management](contributing/dependency-management.md)**: Dependency management strategy and best practices
- **[Troubleshooting](development-workflows/troubleshooting-strategies.md)**: Comprehensive error handling and debugging guide
- Code style and standards
- Testing requirements
- Pull request process

### Architecture

High-level system design and design decisions:

- **[System Architecture](system-guide/architecture-overview.md)**: Overall system structure
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
:maxdepth: 2
:caption: Getting Started

getting-started/index
```

```{toctree}
:maxdepth: 2
:caption: System Guide

system-guide/index
```

```{toctree}
:maxdepth: 2
:caption: Development Workflows

development-workflows/index
```

```{toctree}
:maxdepth: 2
:caption: API Reference

api-reference/index
```

```{toctree}
:maxdepth: 2
:caption: Contributing

contributing/index
```

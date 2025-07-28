# Implementation Guides

In-depth guides for understanding and extending 5e2pdf's core systems.

## Table of Contents

```{toctree}
:maxdepth: 2

deep-indexing
```

## Overview

The Implementation Guides provide detailed technical explanations of 5e2pdf's key systems and architectural decisions. These guides are essential reading for:

- **Contributors** wanting to understand the codebase
- **Developers** extending 5e2pdf with new features
- **Advanced users** optimizing performance or debugging issues
- **Maintainers** making architectural decisions

## Available Guides

### [Deep Indexing](deep-indexing.md)

Comprehensive guide to the omnidexer's deep indexing system:

- How nested content discovery works
- Implementation of the `DeepIndexable` protocol
- Performance considerations and optimization
- Adding support for new content types
- Testing strategies for deep indexing

### Coming Soon

Additional implementation guides will be added covering:

- **Content Parsing Pipeline**: How JSON data is transformed into content objects
- **LaTeX Rendering System**: Template-based document generation
- **Async Architecture**: How concurrent loading improves performance
- **Error Handling Strategies**: Graceful degradation and recovery
- **Memory Management**: Optimizing for large datasets
- **Plugin System**: Creating custom renderers and parsers

## Design Principles

5e2pdf follows several key design principles that guide implementation decisions:

### Type Safety First

- Full mypy compliance with Python 3.12 type annotations
- Runtime type checking where appropriate
- Clear type boundaries between components

### Performance by Design

- Async/await for I/O operations
- Efficient indexing structures
- Lazy loading where possible
- Memory-conscious data structures

### Graceful Degradation

- Continue processing when individual items fail
- Detailed logging for debugging
- Fallback values for missing data
- Clear error messages for users

### Extensibility

- Protocol-based design for adding new types
- Template system for custom output
- Plugin architecture for renderers
- Clear extension points

## Development Workflow

### Understanding the System

1. Start with the [Architecture Overview](../architecture.md)
2. Read relevant implementation guides
3. Explore the codebase with examples
4. Run tests to understand expected behavior

### Making Changes

1. Write tests first (TDD approach)
2. Implement changes following existing patterns
3. Update documentation
4. Ensure type checking passes
5. Run full test suite

### Testing Philosophy

- **Unit tests** for individual components
- **Integration tests** for system interactions
- **Performance tests** for critical paths
- **Regression tests** for bug fixes

## Code Organization

```
src/dnd5e/core/
├── interfaces.py       # Protocols and abstract base classes
├── models/            # Content models and types
├── loaders/           # Data loading and omnidexer
├── parsers/           # Content parsing logic
├── config/            # Configuration management
└── utils/             # Shared utilities
```

### Key Concepts

- **Models**: Data structures representing D&D content
- **Loaders**: Components that fetch and index content
- **Parsers**: Transform JSON data into content objects
- **Renderers**: Generate output in various formats
- **Interfaces**: Protocols defining component contracts

## Contributing Guidelines

Before implementing new features:

1. **Discuss the design** in GitHub issues
2. **Follow existing patterns** in the codebase
3. **Write comprehensive tests** for new functionality
4. **Update documentation** including implementation guides
5. **Consider performance impact** of changes

## Performance Considerations

When implementing new features:

- **Profile first**: Measure before optimizing
- **Async when I/O bound**: Use async/await for network/disk operations
- **Cache intelligently**: Balance memory usage vs. computation
- **Test with real data**: Use actual 5e.tools datasets for testing

## Getting Started

1. Read the [Deep Indexing Guide](deep-indexing.md) for a comprehensive example
2. Explore the source code with these concepts in mind
3. Run the test suite to understand expected behavior
4. Start with small contributions to understand the workflow

For questions about implementation details, open a discussion on GitHub or ask in the project's community spaces.

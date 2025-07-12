Architecture Overview
====================

This document provides a high-level overview of the 5e2pdf architecture and design principles.

System Overview
---------------

5e2pdf follows a modular, layered architecture designed for extensibility and maintainability:

.. code-block:: text

   ┌─────────────────────────────────────────────────────────────┐
   │                    CLI Layer (Typer)                       │
   │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
   │  │   Convert   │ │    List     │ │    Info     │  ...      │
   │  └─────────────┘ └─────────────┘ └─────────────┘           │
   └─────────────────────────────────────────────────────────────┘
   ┌─────────────────────────────────────────────────────────────┐
   │                  Application Layer                          │
   │  ┌─────────────────────────────┐ ┌─────────────────────────┐ │
   │  │     Rendering System        │ │    Content System       │ │
   │  │  ┌─────────┐ ┌────────────┐ │ │ ┌─────────┐ ┌─────────┐ │ │
   │  │  │ LaTeX   │ │  Template  │ │ │ │ Omnidx  │ │   Tag   │ │ │
   │  │  │Renderer │ │  System    │ │ │ │ System  │ │Resolver │ │ │
   │  │  └─────────┘ └────────────┘ │ │ └─────────┘ └─────────┘ │ │
   │  └─────────────────────────────┘ └─────────────────────────┘ │
   └─────────────────────────────────────────────────────────────┘
   ┌─────────────────────────────────────────────────────────────┐
   │                     Core Layer                              │
   │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
   │  │    Models   │ │   Loaders   │ │    Cache    │  ...      │
   │  │ (Pydantic)  │ │    (JSON)   │ │   System    │           │
   │  └─────────────┘ └─────────────┘ └─────────────┘           │
   └─────────────────────────────────────────────────────────────┘
   ┌─────────────────────────────────────────────────────────────┐
   │                     Data Layer                              │
   │           5etools JSON Data + User Content                  │
   └─────────────────────────────────────────────────────────────┘

Core Components
---------------

Data Models (src/core/models/)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Built using Pydantic for robust data validation and serialization:

- **Content Models**: Spell, Creature, Item, Adventure, Book
- **Base Types**: ContentType, Source, ContentItem
- **Validation**: Automatic JSON validation with helpful error messages
- **Type Safety**: Full type hints and runtime validation

Key Features:

- Flexible field handling for varying 5etools JSON structures
- Computed properties for formatted output
- Source tracking and validation
- Cross-reference support

Omnidexer System (src/core/loaders/)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The omnidexer is the central content management system:

- **Async Loading**: Parallel loading of JSON files for performance
- **Content Indexing**: Fast lookup by name, type, and source
- **Cross-Reference Resolution**: Links between content items
- **Caching**: Intelligent caching of loaded content

Components:

- ``Omnidexer``: Main coordinator class
- ``JSONLoader``: Handles JSON file parsing and validation
- ``SourceManager``: Manages source book metadata

Tag Resolution System (src/core/indexer/)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Handles inline references and cross-links in D&D content:

- **Tag Parsing**: Extracts ``{@spell fireball}`` style tags
- **Reference Resolution**: Finds target content items
- **LaTeX Generation**: Converts tags to appropriate LaTeX commands
- **Fallback Handling**: Graceful handling of missing references

Rendering Architecture
----------------------

Base Renderer Framework (src/renderers/base/)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Abstract framework for document generation:

- **Renderer Interface**: Abstract base for all renderers
- **Context System**: Manages rendering configuration and state
- **Content Dispatch**: Routes content types to appropriate handlers
- **Template System**: Pluggable template management

LaTeX Implementation (src/renderers/latex/)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Concrete LaTeX document generation:

- **Document Structure**: Handles preamble, body, and postamble
- **Content Renderers**: Specialized rendering for each content type
- **Template Management**: LaTeX template system with inheritance
- **Style Integration**: D&D-style formatting and layout

CLI Architecture
----------------

Command Structure (src/cli/)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Built using Typer for modern CLI development:

- **Modular Commands**: Separate modules for different command groups
- **Rich Output**: Colored, formatted terminal output
- **Progress Tracking**: Visual progress bars for long operations
- **Error Handling**: User-friendly error messages

Legacy Compatibility (src/cli/compat.py)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Backwards compatibility layer:

- **Argument Translation**: Maps old json2tex arguments to new system
- **Command Emulation**: Reproduces old behavior exactly
- **Migration Path**: Helps users transition to new CLI

Design Principles
-----------------

Modularity
~~~~~~~~~~

Each component has a single, well-defined responsibility:

- Models handle data validation and representation
- Loaders manage data acquisition and parsing
- Renderers handle output generation
- CLI provides user interface

This allows for:

- Easy testing of individual components
- Pluggable architectures (e.g., different output formats)
- Clear separation of concerns

Async-First Design
~~~~~~~~~~~~~~~~~~

Heavy operations use async/await for performance:

- Parallel JSON file loading
- Non-blocking I/O operations
- Responsive CLI during long operations

Type Safety
~~~~~~~~~~~

Comprehensive type hints throughout:

- Pydantic models for runtime validation
- mypy compatibility for static analysis
- IDE support with full autocomplete

Caching Strategy
~~~~~~~~~~~~~~~~

Multi-level caching for performance:

- **Memory Cache**: In-process caching of loaded content
- **Disk Cache**: Persistent caching of processed data
- **Smart Invalidation**: Cache invalidation based on file timestamps

Error Handling
~~~~~~~~~~~~~~

Graceful error handling at all levels:

- **Validation Errors**: Clear messages for malformed JSON
- **Missing Content**: Fallbacks for broken references
- **System Errors**: User-friendly error reporting

Extension Points
----------------

The architecture provides several extension points:

Content Types
~~~~~~~~~~~~~

Add new content types by:

1. Creating a new Pydantic model in ``src/core/models/``
2. Adding the type to ``ContentType`` enum
3. Implementing rendering logic in ``src/renderers/``

Output Formats
~~~~~~~~~~~~~~

Add new output formats by:

1. Implementing the ``BaseRenderer`` interface
2. Creating format-specific templates
3. Adding CLI commands for the new format

Data Sources
~~~~~~~~~~~~

Support new data sources by:

1. Implementing the ``BaseLoader`` interface
2. Adding source detection logic
3. Integrating with the omnidexer system

Performance Considerations
-------------------------

The system is designed for performance at scale:

- **Lazy Loading**: Content loaded only when needed
- **Parallel Processing**: Multiple files processed simultaneously  
- **Efficient Indexing**: Fast lookups using Python dictionaries
- **Caching**: Multiple levels of caching to avoid repeated work

Memory usage is managed through:

- **Streaming**: Large files processed in chunks
- **Weak References**: Automatic cleanup of unused content
- **Cache Limits**: Configurable cache size limits

Testing Strategy
---------------

The architecture supports comprehensive testing:

- **Unit Tests**: Each component tested in isolation
- **Integration Tests**: Full workflow testing
- **Mock Data**: Synthetic test data for reliable testing
- **Performance Tests**: Benchmarks for critical paths

See :doc:`testing` for detailed testing guidelines.
# Component Guides

Detailed implementation guides for each major system component.

## Core Systems

### Service Container Architecture

**Purpose**: Centralized dependency injection and lifecycle management

The service container provides a clean architectural foundation for managing complex application services, replacing scattered global singletons with centralized, type-safe service management.

**Key Benefits:**
- **Dependency Injection**: Type-safe service access with automatic dependency resolution
- **Lifecycle Management**: Proper initialization, cleanup, and resource management
- **Test Isolation**: Single `reset_global_container()` call replaces complex test setup
- **Performance**: Lazy initialization ensures services are created only when needed

For comprehensive implementation details, see {doc}`developer/system-guide/service-container`.

### Loader Architecture

**Purpose**: Intelligent content loading with dual-file support and caching

The loader architecture implements a 5etools-compatible dual-file system that separates metadata from content files, enabling efficient on-demand loading with intelligent caching and runtime merging.

**Key Components:**
- **Omnidexer**: Comprehensive indexing with SHA256 content hashing
- **ContentMerger**: Dual-file architecture implementation with LRU caching
- **ContentResolver**: Fuzzy matching for user abbreviations and partial names

For details, see {doc}`developer/system-guide/components`.

### Deep Indexing System

**Purpose**: Hierarchical content discovery and indexing for D&D content

The deep indexing system enables nested content discovery, making class features, spell references, adventure sections, and other hierarchical content discoverable through the omnidexer.

**Key Features:**
- **Protocol-Based Design**: `DeepIndexable` protocol for type-safe hierarchical indexing
- **Cycle Prevention**: Built-in protection against infinite recursion
- **Performance Optimized**: <50% processing overhead with intelligent caching
- **Full Backward Compatibility**: Existing code continues to work unchanged

For details, see {doc}`developer/system-guide/components`.

## Content Processing

### Tag System Architecture

**Purpose**: Unified tag processing and rendering architecture

The tag system provides comprehensive processing of 5etools tags through a unified architecture that separates business logic from presentation concerns.

**Key Features:**
- **AST-Based Parsing**: Lark parser with custom grammar for 5etools tag syntax
- **Core Handler System**: Protocol-based handlers for content extraction
- **Enhancement Pipeline**: Multi-stage presentation formatting
- **Type Safety**: Full Pydantic validation and Python 3.12 generics

For details, see {doc}`developer/system-guide/components`.

### Entry Types System

**Purpose**: Type-safe replacement for dict patterns with specialized Pydantic models

The entry types system provides 13+ specialized Pydantic models replacing `dict[str, Any]` patterns throughout the codebase.

**Key Benefits:**
- **Type Safety**: Compile-time guarantees with mypy compliance
- **Factory Pattern**: Automatic creation of appropriate entry types
- **Integration**: Seamless integration with content models and validation
- **Performance**: Optimized field access and validation caching

For details, see {doc}`developer/system-guide/components`.

### Content Parsing Pipeline

**Purpose**: Multi-stage transformation from 5etools JSON to typed Python objects

The content parsing system handles the sophisticated transformation of 5etools JSON data into strongly-typed Python objects with comprehensive validation.

**Key Components:**
- **BaseContent System**: Flexible source handling with ContentType enumeration
- **Specialized Models**: Spell, Creature, Item, Adventure, Book models
- **EntryParser**: Extracting nested content from complex structures
- **Validation System**: Strict/liberal modes with comprehensive error handling

For details, see {doc}`developer/system-guide/components`.

## Rendering & Output

### Image Processing Pipeline

**Purpose**: Complete image processing system for LaTeX documents

The image processing pipeline provides a 4-component system for handling images in LaTeX document generation.

**Key Components:**
- **FormatConverter**: WebP/PNG conversion with transparency handling
- **ImageOptimizer**: Size and quality optimization with context-aware strategies
- **ImagePlacer**: Intelligent LaTeX placement with floating figures and text wrapping
- **ImageProcessor**: Unified coordination of the complete pipeline

For details, see {doc}`developer/system-guide/components`.

### LaTeX Rendering System

**Purpose**: Sophisticated LaTeX rendering pipeline for document generation

The LaTeX rendering system provides multi-layered architecture with template-based document generation and comprehensive LaTeX compilation support.

**Key Features:**
- **LaTeXDocumentRenderer**: Content organization and structure building
- **Jinja2 Integration**: LaTeX-specific customizations and filters
- **RecursiveEntryProcessor**: Handling 40+ 5etools entry types
- **Multi-engine Compilation**: XeLaTeX, PDFLaTeX, LuaLaTeX support

For details, see {doc}`developer/system-guide/components`.

## Infrastructure & Configuration

### Unified Configuration System

**Purpose**: Hierarchical Pydantic-based configuration architecture

The configuration system provides a single source of truth consolidating scattered configuration patterns with comprehensive type safety.

**Key Features:**
- **Hierarchical Organization**: ApplicationConfig with specialized sub-configs
- **Environment Variable Support**: DND5E_ prefix with nested delimiter support
- **CLI Integration**: Seamless parameter defaults through configuration factory
- **Legacy Compatibility**: Bridges for existing configuration patterns

For details, see {doc}`developer/system-guide/components`.

### Error Handling System

**Purpose**: Type-safe Result[T, E] pattern and structured error management

The error handling system implements a complete Result pattern with structured error types and comprehensive error management strategies.

**Key Components:**
- **Result[T, E] Pattern**: Success/Error types with monadic operations
- **Structured Error Types**: ValidationError, ProcessingError, IOOperationError with rich context
- **Error Chaining**: Batch processing with collect_results for complex pipelines
- **Logging Integration**: Standardized ErrorContext with severity levels

For details, see {doc}`developer/system-guide/components`.

## Development Patterns

### Protocol-Based Design

The codebase extensively uses Python protocols for loose coupling:

- **Loose coupling** through Python protocols and interfaces
- **Testability** with easy mocking and dependency injection
- **Extensibility** via protocol implementations

### Type Safety First

- **Python 3.12 generics** throughout the codebase
- **Comprehensive type hints** with mypy enforcement
- **Pydantic validation models** for data integrity and type safety
- **Protocol-based interfaces** for clear contracts

### Performance Optimization

- **Lazy loading** of large content files
- **LRU caching** with TTL and file modification tracking
- **On-demand merging** reduces memory footprint
- **Efficient I/O** operations and resource management

### Graceful Degradation

- **Continue processing** when individual items fail
- **Detailed logging** for debugging
- **Fallback values** for missing data
- **Clear error messages** for users

## Extension Points

### Custom Content Types

- **New content types**: Extend base model classes
- **Custom validation**: Add validation protocols
- **Deep indexing**: Implement `DeepIndexable` for new types

### Rendering Extensions

- **Template engines**: Alternative to Jinja2
- **Output formats**: Beyond LaTeX/PDF
- **Post-processing**: Custom PDF manipulation

### Cache Backends

- **Custom loaders**: Implement `ContentLoader` protocol
- **Merger strategies**: Extend `ContentMerger` for new formats
- **Cache backends**: Pluggable cache implementations

For specific implementation guides and API details, see the individual component documentation linked above and the {doc}`library-reference/index`.

## Additional Developer Resources

```{toctree}
:hidden:
:maxdepth: 1

developer/error-handling-guide
```

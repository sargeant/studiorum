# Architecture and Dependency Management

This document describes the architectural patterns and dependency management principles used in the 5e2pdf project.

## Overview

The 5e2pdf project follows a layered architecture with clear separation of concerns and dependency injection patterns to maintain modularity and prevent circular dependencies.

## Architectural Layers

### 1. CLI Layer (`dnd5e/cli/`)

- **Purpose**: Command-line interface and user interaction
- **Allowed Dependencies**: `core`, `renderers`, `processors`
- **Key Components**:
  - `main.py` - Application entry point
  - `commands/` - CLI command implementations
- **Responsibilities**:
  - User interface and command parsing
  - Orchestrating business logic
  - Output formatting and display

### 2. Renderers Layer (`dnd5e/renderers/`)

- **Purpose**: Output generation (LaTeX, PDF, future formats)
- **Allowed Dependencies**: `core`
- **Key Components**:
  - `base/` - Base renderer classes and interfaces
  - `latex/` - LaTeX-specific rendering
  - `tags/` - Tag rendering system
- **Responsibilities**:
  - Converting content models to output formats
  - Template management
  - Format-specific logic

### 3. Processors Layer (`dnd5e/processors/`)

- **Purpose**: Data transformation and processing
- **Allowed Dependencies**: `core`
- **Key Components**:
  - `content/` - Content processing
  - `transformers/` - Data transformation
- **Responsibilities**:
  - Data validation and cleaning
  - Content transformation
  - Business rule application

### 4. Core Layer (`dnd5e/core/`)

- **Purpose**: Core business logic and data models
- **Allowed Dependencies**: None (foundational layer)
- **Key Components**:
  - `models/` - Pydantic data models
  - `loaders/` - Data loading and source management
  - `config/` - Configuration management
  - `indexer/` - Content indexing and cross-referencing
  - `sources/` - External data source management
- **Responsibilities**:
  - Domain models and business logic
  - Data persistence and retrieval
  - Core algorithms and utilities

## Dependency Injection System

The project uses a dependency injection system to reduce tight coupling and improve testability.

### Key Interfaces

Located in `dnd5e/core/interfaces.py`:

- `ContentLoader` - Protocol for content loading functionality
- `ContentTypeResolver` - Protocol for resolving content types
- `ContentIndexer` - Protocol for content indexing
- `TagResolver` - Protocol for tag resolution

### Service Locator Pattern

The `ServiceLocator` class provides a centralized registry for services:

```python
from dnd5e.core.interfaces import get_service_locator

locator = get_service_locator()
indexer = locator.get(ContentIndexer)
```

### Dependency Container

The `DependencyContainer` class in `dnd5e/core/dependency_injection.py` provides:

- Service registration and resolution
- Singleton pattern support
- Circular dependency detection
- Lazy initialization

### Usage Example

```python
from dnd5e.core.dependency_injection import get_dependency_container, inject

# Register a service
container = get_dependency_container()
container.register(MyService, MyServiceFactory())

# Inject dependencies
@inject(ContentIndexer, TagResolver)
def process_content(content, indexer, resolver):
    # indexer and resolver are automatically injected
    pass
```

## Circular Dependency Prevention

### Registry Pattern

The `ContentTypeRegistry` in `dnd5e/core/interfaces.py` breaks circular dependencies between content models and type resolution:

```python
from dnd5e.core.interfaces import get_content_type_registry

registry = get_content_type_registry()
registry.register(Adventure, ContentType.ADVENTURE)
content_type = registry.get_type(content_instance)
```

### Factory Pattern

The `ContentFactory` in `dnd5e/core/loaders/content_factory.py` eliminates the need for direct model imports in loaders:

```python
from dnd5e.core.loaders.content_factory import get_content_factory

factory = get_content_factory()
content = factory.create_content(data, ContentType.SPELL)
```

## Automated Checking

### Circular Import Detection

The project includes a circular import detector (`scripts/check_circular_imports.py`) that:

- Analyzes import dependencies using AST parsing
- Detects circular import chains
- Provides detailed violation reports
- Runs automatically in CI/CD

Usage:

```bash
python scripts/check_circular_imports.py src/dnd5e/ --fail-on-cycles
```

### Architectural Boundary Checking

The architectural boundary checker (`scripts/check_architectural_boundaries.py`) ensures:

- Layers only depend on allowed layers
- No upward dependencies (e.g., core cannot import from cli)
- Clear separation of concerns
- Runs automatically in CI/CD

Usage:

```bash
python scripts/check_architectural_boundaries.py src/dnd5e/ --fail-on-violations
```

## Best Practices

### Import Guidelines

1. **Use interfaces over concrete classes** when possible
2. **Prefer dependency injection** over direct instantiation
3. **Import from interfaces** rather than implementation modules
4. **Use factory patterns** for complex object creation
5. **Avoid importing from higher layers** (maintain dependency direction)

### Good Import Patterns

```python
# Good - using interfaces
from dnd5e.core.interfaces import ContentIndexer, get_service_locator

# Good - factory pattern
from dnd5e.core.loaders.content_factory import get_content_factory

# Good - dependency injection
from dnd5e.core.dependency_injection import inject
```

### Patterns to Avoid

```python
# Bad - direct imports of all model classes
from dnd5e.core.models.adventures import Adventure
from dnd5e.core.models.spells import Spell
# ... (importing many specific classes)

# Bad - importing from higher layers
from dnd5e.cli.commands.convert import ConvertCommand  # in core layer

# Bad - creating circular dependencies
from dnd5e.core.models.content import ContentType
from dnd5e.core.models.adventures import Adventure  # which imports content
```

### Testing Patterns

1. **Use dependency injection** for easier mocking
2. **Test interfaces** rather than implementations
3. **Mock external dependencies** through the service locator
4. **Use factory methods** for test data creation

## Configuration

### Service Configuration

Services are automatically configured in `dnd5e/core/dependency_injection.py`:

```python
def configure_services():
    container = get_dependency_container()

    # Register services
    container.register(ContentIndexer, OmnidexerFactory())
    container.register(TagResolver, TagResolverFactory())
    # ...
```

### Adding New Services

1. Define an interface in `dnd5e/core/interfaces.py`
2. Create a factory in `dnd5e/core/dependency_injection.py`
3. Register the service in `configure_services()`
4. Use dependency injection in consuming code

## Migration Guide

### From Direct Imports to Dependency Injection

**Before:**

```python
from dnd5e.core.loaders.omnidexer import Omnidexer
from dnd5e.core.indexer.tag_resolver import TagResolver

class MyClass:
    def __init__(self):
        self.omnidexer = Omnidexer()
        self.resolver = TagResolver(self.omnidexer)
```

**After:**

```python
from dnd5e.core.interfaces import ContentIndexer, TagResolver
from dnd5e.core.dependency_injection import get_dependency_container

class MyClass:
    def __init__(self, indexer: ContentIndexer = None, resolver: TagResolver = None):
        container = get_dependency_container()
        self.indexer = indexer or container.resolve(ContentIndexer)
        self.resolver = resolver or container.resolve(TagResolver)
```

### From ContentType.from_content() to Registry

**Before:**

```python
from dnd5e.core.models.content import ContentType
content_type = ContentType.from_content(content)
```

**After:**

```python
from dnd5e.core.content_type_resolver import get_content_type_resolver
resolver = get_content_type_resolver()
content_type = resolver.resolve_type(content)
```

## Monitoring and Maintenance

### CI/CD Integration

The following checks run automatically on every commit:

1. **Circular Import Detection** - Fails build if circular imports detected
2. **Architectural Boundary Checking** - Fails build if layer violations found
3. **Linting** - Ensures code quality and import organization
4. **Type Checking** - Validates type annotations and interfaces

### Regular Maintenance

- **Review dependency graphs** monthly using the analysis tools
- **Update architectural documentation** when adding new layers
- **Refactor tight coupling** identified during code reviews
- **Monitor service registration** to prevent service bloat

## Benefits

This architectural approach provides:

1. **Modularity** - Clear separation of concerns
2. **Testability** - Easy mocking and dependency injection
3. **Maintainability** - Reduced coupling and clear boundaries
4. **Extensibility** - Easy to add new features and layers
5. **Reliability** - Automated checking prevents architectural drift

## Conclusion

The 5e2pdf project's architectural patterns ensure a maintainable, testable, and extensible codebase. By following these guidelines and using the provided tools, developers can contribute effectively while maintaining code quality and architectural integrity.

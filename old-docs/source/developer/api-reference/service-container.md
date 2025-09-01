# Service Container API Reference

The service container provides centralized dependency injection and lifecycle management for 5e2pdf core services.

## Overview

The service container architecture replaces global singletons with managed dependencies, providing:

- **Lazy Initialization**: Services are created only when needed
- **Lifecycle Management**: Proper cleanup and resource management
- **Test Isolation**: Simple global state reset for testing
- **Type Safety**: Protocol-based service interfaces

## ServiceContainer Protocol

### Interface Definition

```python
from typing import Protocol
from dnd5e.core.container import ServiceContainer

class ServiceContainer(Protocol):
    def get_omnidexer(self) -> Omnidexer: ...
    def get_tag_resolver(self) -> TagResolver: ...
    def get_content_type_registry(self) -> ContentTypeRegistry: ...
    def get_display_manager(self) -> DisplayManager: ...
    def get_content_factory(self) -> ContentFactory: ...
    def get_content_type_resolver(self) -> RegistryBasedContentTypeResolver: ...
    def get_entry_registry(self) -> EntryTypeRegistry: ...
    def get_reference_manager(self) -> ReferenceManager: ...
    def get_app_config(self) -> ApplicationConfig: ...
    def close(self) -> None: ...
```

## Global Container Functions

### get_global_container()

Returns the global service container instance for CLI and application usage.

```python
from dnd5e.core.container import get_global_container

container = get_global_container()
omnidexer = container.get_omnidexer()
```

**Returns**: `DefaultServiceContainer` - The global container instance

**Usage Notes**:
- Container is lazily initialized on first access
- Services within the container are also lazily initialized
- Suitable for CLI commands and long-running application contexts

### reset_global_container()

Resets the global service container, creating a new instance and clearing all cached services.

```python
from dnd5e.core.container import reset_global_container

# Reset for test isolation
reset_global_container()
```

**Returns**: `None`

**Usage Notes**:
- **Primary use case**: Test isolation and cleanup
- Replaces complex individual singleton reset patterns
- Should be called in test `setup_method()` or `teardown_method()`

## Scoped Container Context Manager

### service_container()

Creates a new service container as a context manager with automatic cleanup.

```python
from dnd5e.core.container import service_container

with service_container() as container:
    omnidexer = container.get_omnidexer()
    # Use services...
# Container is automatically closed and cleaned up
```

**Returns**: `Iterator[ServiceContainer]` - Context manager yielding a container

**Usage Notes**:
- Provides complete isolation from global state
- Automatically calls `container.close()` on exit
- Ideal for batch processing or isolated operations

## Service Access Methods

### get_omnidexer()

Returns the Omnidexer instance for content indexing and loading.

```python
omnidexer = container.get_omnidexer()
omnidexer.load_all_data()
```

**Returns**: `Omnidexer` - The omnidexer service

**Initialization**: Lazy - created on first access with progress display

### get_tag_resolver()

Returns the TagResolver instance for cross-reference resolution.

```python
tag_resolver = container.get_tag_resolver()
resolved_tags = tag_resolver.resolve_tags(content)
```

**Returns**: `TagResolver` - The tag resolver service

**Dependencies**: Depends on Omnidexer (automatically injected)

### get_entry_registry()

Returns the EntryTypeRegistry instance for entry type validation.

```python
registry = container.get_entry_registry()
registry.validate_entry(entry_data, entry_type)
```

**Returns**: `EntryTypeRegistry` - The entry registry service

**Migration Note**: Replaces `dnd5e.core.entry_registry.get_registry()`

### get_reference_manager()

Returns the ReferenceManager instance for reference parsing and resolution.

```python
ref_manager = container.get_reference_manager()
references = ref_manager.parse_references(text)
```

**Returns**: `ReferenceManager` - The reference manager service

**Migration Note**: Replaces `dnd5e.core.unified_references.get_reference_manager()`

### Other Service Methods

- `get_content_type_registry()` → `ContentTypeRegistry`
- `get_display_manager()` → `DisplayManager`
- `get_content_factory()` → `ContentFactory`
- `get_content_type_resolver()` → `RegistryBasedContentTypeResolver`
- `get_app_config()` → `ApplicationConfig`

## Container Lifecycle

### Initialization

Services are initialized lazily when first accessed:

```python
container = get_global_container()
# No services created yet

omnidexer = container.get_omnidexer()
# Omnidexer now created and cached
# DisplayManager also created for progress display

tag_resolver = container.get_tag_resolver()
# TagResolver created, reuses existing Omnidexer
```

### Cleanup

```python
# Manual cleanup
container.close()

# Automatic cleanup with context manager
with service_container() as container:
    # Services automatically cleaned up
    pass
```

## Migration Guide

### From Global Singletons

**Before (Deprecated)**:
```python
from dnd5e.core.entry_registry import get_registry
from dnd5e.core.unified_references import get_reference_manager

registry = get_registry()  # Global singleton
ref_manager = get_reference_manager()  # Global singleton
```

**After (Recommended)**:
```python
from dnd5e.core.container import get_global_container

container = get_global_container()
registry = container.get_entry_registry()  # Service container
ref_manager = container.get_reference_manager()  # Service container
```

### Test Setup Migration

**Before (Complex)**:
```python
def setup_method(self) -> None:
    # Multiple individual resets required
    from dnd5e.core.cache import CacheManager
    from dnd5e.core.entry_registry import reset_entry_registry
    from dnd5e.core.unified_references import reset_reference_manager
    # ... 8+ more reset calls

    CacheManager.reset()
    reset_entry_registry()
    reset_reference_manager()
    # ... more resets
```

**After (Simple)**:
```python
def setup_method(self) -> None:
    from dnd5e.core.cache import CacheManager
    from dnd5e.core.container import reset_global_container
    from dnd5e.cli.main import reset_cli_globals

    # Single call handles most singletons
    reset_global_container()

    # Only legacy components need individual reset
    CacheManager.reset()
    reset_cli_globals()
```

## Error Handling

### Container State Errors

```python
container = get_global_container()
service = container.get_omnidexer()
container.close()

# This will raise RuntimeError
try:
    service = container.get_omnidexer()
except RuntimeError as e:
    print(f"Container closed: {e}")
```

### Service Initialization Errors

Service initialization errors are propagated normally:

```python
try:
    omnidexer = container.get_omnidexer()
except ConfigurationError as e:
    print(f"Failed to initialize omnidexer: {e}")
```

## Performance Considerations

### Lazy Loading Benefits

- **Startup Performance**: Only needed services are initialized
- **Memory Usage**: Unused services don't consume memory
- **Test Performance**: Tests only pay for services they use

### Caching Behavior

- Services are cached after first creation
- `reset_global_container()` clears all cached services
- New container instances start with empty caches

## Best Practices

### CLI Usage

```python
# CLI commands should use global container
from dnd5e.core.container import get_global_container

def convert_command():
    container = get_global_container()
    omnidexer = container.get_omnidexer()
    # ... use services
```

### Batch Processing

```python
# Use scoped container for isolation
from dnd5e.core.container import service_container

def process_multiple_books():
    for book in books:
        with service_container() as container:
            # Each book gets fresh services
            processor = BookProcessor(container)
            processor.process(book)
```

### Testing

```python
class TestContentProcessing:
    def setup_method(self):
        # Always reset container for test isolation
        reset_global_container()

    def test_processing(self):
        container = get_global_container()
        # ... test with clean state
```

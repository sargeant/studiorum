---
title: Services API
description: Core services, service container, and dependency injection patterns
---

# Services API

Studiorum's service architecture provides a flexible, type-safe foundation for dependency injection and service lifecycle management.

## Service Container

### ServiceContainer

The central service container manages all application services with full lifecycle support.

```python
from studiorum.core.services.container import ServiceContainer
from studiorum.core.services.lifecycle import ServiceLifecycle
from studiorum.core.services.protocols import OmnidexerProtocol

# Get global container instance
container = ServiceContainer.get_global_instance()

# Register a service
container.register_service(
    protocol=OmnidexerProtocol,
    factory=create_omnidexer_service,
    lifecycle=ServiceLifecycle.SINGLETON,
    dependencies=(ConfigProtocol,),
    hot_reloadable=True
)

from studiorum.core.services.protocols import OmnidexerProtocol
# Resolve services (sync)
omnidexer = container.get_service_sync(OmnidexerProtocol)

# Resolve services (async)
async def get_service_async():
    omnidexer = await container.get_service(OmnidexerProtocol)
    return omnidexer
```

#### Methods

**`register_service[T](protocol, factory, lifecycle, dependencies=(), **options)`**

Register a service with the container.

- **protocol**: Service protocol type
- **factory**: Factory function or class
- **lifecycle**: Service lifecycle strategy
- **dependencies**: Required dependency protocols
- **hot_reloadable**: Whether service supports hot reloading
- **cleanup_priority**: Cleanup order priority

```python
def register_service[T](
    self,
    protocol: type[T],
    factory: ServiceFactory[T] | AsyncServiceFactory[T],
    lifecycle: ServiceLifecycle,
    dependencies: tuple[type[Any], ...] = (),
    hot_reloadable: bool = False,
    cleanup_priority: CleanupPriority = CleanupPriority.NORMAL,
) -> None:
    """Register service with complete configuration."""
```

**`get_service[T](protocol) -> T`**

Resolve service by protocol (async).

```python
async def get_service[T](self, protocol: type[T]) -> T:
    """Type-safe async service resolution."""
```

**Sync Service Access**

For CLI and synchronous contexts, use dedicated sync factories and sync resolution:

```python
from studiorum.core.services.factories import (
    create_omnidexer_service_sync,
    create_data_source_manager_service_sync,
)
from studiorum.core.services.protocols import (
    OmnidexerProtocol,
    ContentResolverProtocol,
    TagResolverProtocol,
)

# Register sync factories in CLI container (global instance already registers these)
container.register_service(
    OmnidexerProtocol,
    create_omnidexer_service_sync,
    lifecycle=ServiceLifecycle.SINGLETON,
)

# Direct sync access via protocol tokens
omnidexer = container.get_service_sync(OmnidexerProtocol)
content_resolver = container.get_service_sync(ContentResolverProtocol)
tag_resolver = container.get_service_sync(TagResolverProtocol)
```

**Context Separation**: CLI and MCP contexts use different service registration patterns:

- **CLI**: Uses `SINGLETON` lifecycle with sync factories for performance
- **MCP**: Uses `ASYNC_RESOURCE` lifecycle with async factories for request isolation

### Service Lifecycles

Services support different lifecycle strategies:

```python
from studiorum.core.services.lifecycle import ServiceLifecycle

class ServiceLifecycle(Enum):
    SINGLETON = "singleton"     # One instance per container
    TRANSIENT = "transient"     # New instance per request
    SCOPED = "scoped"          # One instance per scope
    ASYNC_RESOURCE = "async_resource"  # Async lifecycle for MCP contexts
```

## Core Services

### AppendixGenerator Service

Generates appendix sections from tracked references using shared Jinja templates for entries.

```python
from studiorum.core.services.appendix_generator import AppendixGenerator, AppendixFlags
from studiorum.core.references.content_tracker import ContentTracker

tracker = ContentTracker()
# ... add tracked content (spells/items/creatures) ...

generator = AppendixGenerator(omnidexer, template_engine)
flags = AppendixFlags(spells=True, items=True, creatures=True)

# Single-level appendices
appendices = generator.generate_appendices(tracker, flags)

# Recursive (e.g., creatures→spells, spells→creatures)
appendices_recursive = generator.generate_recursive_appendices(tracker, flags, max_depth=2)

# Each AppendixSection has fields: title, content (LaTeX), content_type, item_count
for section in appendices:
    print(section.title, section.item_count)
```

Rendering details:
- Spells use `templates/spell_entry.tex.j2` which imports `_spell_render_block.tex.j2`.
- Items use `templates/item_entry.tex.j2` which imports `_item_render_block.tex.j2`.
- Creatures use `templates/creature_entry.tex.j2` which imports `_creature_render_block.tex.j2`.

Appendix layout:
- Current implementation assembles sections programmatically and embeds the per-entry rendered content.
- Planned unification will render complete sections via `templates/components/appendix_enhanced.tex.j2` for full template-driven assembly.

### Omnidexer Service

Content indexing and search service.

```python
from studiorum.core.services.protocols import OmnidexerProtocol

@runtime_checkable
class OmnidexerProtocol(Protocol):
    """Protocol for content indexing and search."""

    def is_loaded(self) -> bool:
        """Check if content is loaded."""

    def load_all_data(self) -> None:
        """Load all content data."""

    def get_creature_by_name(self, name: str) -> Creature | None:
        """Get creature by exact name."""

    def get_spell_by_name(self, name: str) -> Spell | None:
        """Get spell by exact name."""

    def get_adventure_by_name(self, name: str) -> Adventure | None:
        """Get adventure by name or abbreviation."""

    def search_creatures(
        self,
        query: str | None = None,
        *,
        challenge_rating: str | None = None,
        creature_type: str | None = None,
        size: str | None = None,
        environment: str | None = None,
    ) -> list[Creature]:
        """Search creatures with filters."""

    def search_spells(
        self,
        query: str | None = None,
        *,
        level: int | str | None = None,
        school: str | None = None,
        spell_class: str | None = None,
    ) -> list[Spell]:
        """Search spells with filters."""

    def get_all_by_type(self, content_type: str) -> list[Any]:
        """Get all content of specified type."""

    def get_statistics(self) -> dict[str, Any]:
        """Get content statistics."""
```

**Usage Examples**

```python
# Get omnidexer instance
from studiorum.core.services.protocols import OmnidexerProtocol
omnidexer = container.get_service_sync(OmnidexerProtocol)

# Load data if not already loaded
if not omnidexer.is_loaded():
    omnidexer.load_all_data()

# Get specific content
dragon = omnidexer.get_creature_by_name("Ancient Red Dragon")
fireball = omnidexer.get_spell_by_name("Fireball")
lmop = omnidexer.get_adventure_by_name("LMoP")

# Search with filters
high_cr_dragons = omnidexer.search_creatures(
    challenge_rating="15-30",
    creature_type="dragon"
)

wizard_spells = omnidexer.search_spells(
    level="1-3",
    spell_class="wizard"
)

# Get statistics
stats = omnidexer.get_statistics()
print(f"Loaded {stats['creature_count']} creatures")
```

### ContentResolver Service

Resolves content references and dependencies.

```python
from studiorum.core.services.protocols import ContentResolverProtocol

@runtime_checkable
class ContentResolverProtocol(Protocol):
    """Protocol for content resolution."""

    def resolve_creature(self, creature_id: str) -> Result[Creature, ResolveError]:
        """Resolve creature with validation."""

    def resolve_spell(self, spell_id: str) -> Result[Spell, ResolveError]:
        """Resolve spell with validation."""

    def resolve_adventure(self, adventure_id: str) -> Result[Adventure, ResolveError]:
        """Resolve adventure with all dependencies."""

    def resolve_item(self, item_id: str) -> Result[Item, ResolveError]:
        """Resolve magic item with validation."""
```

**Usage Examples**

```python
from studiorum.core.result import Success, Error

from studiorum.core.services.protocols import ContentResolverProtocol
resolver = container.get_service_sync(ContentResolverProtocol)

# Resolve with error handling
result = resolver.resolve_creature("ancient-red-dragon")
if isinstance(result, Error):
    print(f"Resolution failed: {result.error}")
else:
    creature = result.unwrap()
    print(f"Resolved: {creature.name}")

# Chain resolutions
adventure_result = resolver.resolve_adventure("curse-of-strahd")
if isinstance(adventure_result, Success):
    adventure = adventure_result.unwrap()
    print(f"Adventure: {adventure.name}")
    print(f"Chapters: {len(adventure.contents)}")
```

### TagResolver Service

Processes 5e content tags using the unified rendering pipeline.

```python
from studiorum.core.services.protocols import TagResolverProtocol
from studiorum.renderers.core.interfaces import RenderingContext

tag_resolver = container.get_service_sync(TagResolverProtocol)

# Process text with a minimal rendering context
context = RenderingContext(output_format="latex")
text = "The {@creature hobgoblin|SRD} attacks with its {@item scimitar|SRD}."
rendered = tag_resolver.process_text(text, context)
print(rendered)

# Discover supported tags
print(tag_resolver.get_supported_tag_types())
```

### TemplateService

LaTeX template rendering service with component injection and clean context binding.

```python
from studiorum.latex_engine.services.template_service import TemplateService
from studiorum.core.references.content_tracker import ContentTracker
from studiorum.core.services.protocols import (
    TextExtractionProtocol,
    LaTeXFormattingProtocol,
    TagResolverProtocol,
    OmnidexerProtocol,
)

# Resolve dependencies from the container
text_extractor = container.get_service_sync(TextExtractionProtocol)
latex_formatter = container.get_service_sync(LaTeXFormattingProtocol)
tag_resolver = container.get_service_sync(TagResolverProtocol)
omnidexer = container.get_service_sync(OmnidexerProtocol)

# Construct service and bind a ContentTracker context
template_service = TemplateService(
    text_extractor=text_extractor,
    latex_formatter=latex_formatter,
    tag_resolver=tag_resolver,
    omnidexer=omnidexer,
)

bound = template_service.bind_context(ContentTracker())

# Render one or many entries
single = bound.render_entry(entry)
many = bound.render_entries(entries)
```

## Async Request Context

For MCP server and async operations, use AsyncRequestContext:

```python
from studiorum.core.async_request_context import AsyncRequestContext

class AsyncRequestContext:
    """Request-scoped service context for async operations."""

    async def get_service[T](self, protocol: type[T]) -> T:
        """Get service instance for this request."""

    async def __aenter__(self) -> AsyncRequestContext:
        """Enter async context."""

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Clean up request-scoped resources."""
```

**Usage in MCP Tools**

```python
from studiorum.mcp.core.decorators import mcp_tool
from studiorum.core.async_request_context import AsyncRequestContext

@mcp_tool("lookup_creature")
async def lookup_creature_tool(
    ctx: AsyncRequestContext,
    name: str
) -> dict[str, Any]:
    """MCP tool using async request context."""

    # Get services for this request
    omnidexer = await ctx.get_service(OmnidexerProtocol)
    resolver = await ctx.get_service(ContentResolverProtocol)

    # Use services with full type safety
    creature = omnidexer.get_creature_by_name(name)
    if not creature:
        return {"error": f"Creature not found: {name}"}

    # Resolve additional data if needed
    resolution_result = resolver.resolve_creature(creature.id)
    if isinstance(resolution_result, Error):
        return {"error": f"Resolution failed: {resolution_result.error}"}

    resolved_creature = resolution_result.unwrap()
    return {
        "name": resolved_creature.name,
        "challenge_rating": resolved_creature.challenge_rating,
        "armor_class": resolved_creature.armor_class,
        # ... additional fields
    }
```

## Service Registration

### Built-in Services

Register all core services:

```python
def register_core_services(container: ServiceContainer) -> None:
    """Register all core application services."""

    # Configuration service
    container.register_service(
        ConfigProtocol,
        create_config_service,
        ServiceLifecycle.SINGLETON,
        hot_reloadable=True
    )

    # Content services
    container.register_service(
        OmnidexerProtocol,
        create_omnidexer_service,
        ServiceLifecycle.SINGLETON,
        dependencies=(ConfigProtocol,)
    )

    container.register_service(
        ContentResolverProtocol,
        create_content_resolver_service,
        ServiceLifecycle.SINGLETON,
        dependencies=(OmnidexerProtocol,)
    )

    # Tag processing
    container.register_service(
        TagResolverProtocol,
        create_tag_resolver_service,
        ServiceLifecycle.SINGLETON,
        dependencies=(OmnidexerProtocol, ConfigProtocol)
    )
```

### Custom Services

Register your own services:

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class MyServiceProtocol(Protocol):
    def process_data(self, data: str) -> str: ...

class MyService:
    def __init__(self, omnidexer: OmnidexerProtocol, config: ConfigProtocol):
        self.omnidexer = omnidexer
        self.config = config

    def process_data(self, data: str) -> str:
        # Custom processing logic
        return f"Processed: {data}"

def create_my_service(
    omnidexer: OmnidexerProtocol,
    config: ConfigProtocol
) -> MyService:
    """Factory function for custom service."""
    return MyService(omnidexer, config)

# Register custom service
container.register_service(
    MyServiceProtocol,
    create_my_service,
    ServiceLifecycle.SINGLETON,
    dependencies=(OmnidexerProtocol, ConfigProtocol)
)

# Use custom service
my_service = await container.get_service(MyServiceProtocol)
result = my_service.process_data("test data")
```

### Service Factories

Service factories can be functions or classes:

```python
# Function factory
def create_simple_service() -> SimpleService:
    return SimpleService()

# Function factory with dependencies
def create_complex_service(
    dep1: Dependency1Protocol,
    dep2: Dependency2Protocol
) -> ComplexService:
    return ComplexService(dep1, dep2)

# Class factory
class ServiceFactory:
    def __init__(self, config: ConfigProtocol):
        self.config = config

    def create(self) -> MyService:
        return MyService(self.config)

# Async factory
async def create_async_service() -> AsyncService:
    await initialize_async_resources()
    return AsyncService()
```

## Error Handling

Services use Result types for error handling:

```python
from studiorum.core.result import Result, Success, Error

class MyService:
    def risky_operation(self, input_data: str) -> Result[str, str]:
        """Operation that might fail."""

        if not input_data:
            return Error("Input cannot be empty")

        try:
            result = self._process_data(input_data)
            return Success(result)
        except ValueError as e:
            return Error(f"Processing failed: {e}")
        except Exception as e:
            return Error(f"Unexpected error: {e}")

# Usage with error handling
service = await container.get_service(MyServiceProtocol)
result = service.risky_operation("test input")

if isinstance(result, Error):
    logger.error(f"Operation failed: {result.error}")
else:
    processed_data = result.unwrap()
    logger.info(f"Success: {processed_data}")
```

## Service Configuration

Services can be configured through the application config:

```python
# Configuration model
class MyServiceConfig(BaseModel):
    enabled: bool = True
    batch_size: int = 100
    timeout_seconds: int = 30

class ApplicationConfig(BaseModel):
    # ... other config sections
    my_service: MyServiceConfig = MyServiceConfig()

# Service using configuration
class ConfigurableService:
    def __init__(self, config: ApplicationConfig):
        self.service_config = config.my_service
        self.batch_size = self.service_config.batch_size
        self.timeout = self.service_config.timeout_seconds

    def process_batch(self, items: list[Any]) -> list[Any]:
        # Use configured batch size
        batches = self._chunk_items(items, self.batch_size)
        return self._process_batches(batches)
```

## Testing Services

Test services in isolation:

```python
import pytest
from unittest.mock import Mock
from studiorum.core.services.container import ServiceContainer

class TestMyService:
    def setup_method(self):
        """Reset container for each test."""
        ServiceContainer.reset_global_instance()

    async def test_service_registration_and_resolution(self):
        """Test service container functionality."""
        container = ServiceContainer()

        # Register test service
        container.register_service(
            MyServiceProtocol,
            lambda: MyService(),
            ServiceLifecycle.SINGLETON
        )

        # Resolve and test
        service = await container.get_service(MyServiceProtocol)
        assert isinstance(service, MyService)

    async def test_service_with_mocked_dependencies(self):
        """Test service with mocked dependencies."""
        container = ServiceContainer()

        # Mock dependencies
        mock_omnidexer = Mock(spec=OmnidexerProtocol)
        mock_config = Mock(spec=ConfigProtocol)

        # Register mocks
        container.register_service(
            OmnidexerProtocol,
            lambda: mock_omnidexer,
            ServiceLifecycle.SINGLETON
        )

        container.register_service(
            ConfigProtocol,
            lambda: mock_config,
            ServiceLifecycle.SINGLETON
        )

        # Register service under test
        container.register_service(
            MyServiceProtocol,
            create_my_service,
            ServiceLifecycle.SINGLETON,
            dependencies=(OmnidexerProtocol, ConfigProtocol)
        )

        # Test service behavior
        service = await container.get_service(MyServiceProtocol)
        result = service.process_data("test")

        # Verify mocks were called
        assert mock_omnidexer.method_was_called
        assert result.startswith("Processed:")
```

## Performance Considerations

### Service Caching

Services are automatically cached based on lifecycle:

```python
# Singletons are cached in the container
omnidexer1 = await container.get_service(OmnidexerProtocol)
omnidexer2 = await container.get_service(OmnidexerProtocol)
assert omnidexer1 is omnidexer2  # Same cached instance

# Transient services are never cached
processor1 = await container.get_service(ProcessorProtocol)
processor2 = await container.get_service(ProcessorProtocol)
assert processor1 is not processor2  # Different instances
```

### Lazy Loading

Services support lazy initialization:

```python
class LazyService:
    def __init__(self):
        self._heavy_resource = None

    @property
    def heavy_resource(self):
        """Lazy load expensive resource."""
        if self._heavy_resource is None:
            self._heavy_resource = load_heavy_resource()
        return self._heavy_resource
```

### Memory Management

Use cleanup priorities for proper resource management:

```python
from studiorum.core.services.cleanup import CleanupPriority

# Register service with cleanup priority
container.register_service(
    DatabaseProtocol,
    create_database_service,
    ServiceLifecycle.SINGLETON,
    cleanup_priority=CleanupPriority.HIGH  # Clean up early
)

container.register_service(
    CacheProtocol,
    create_cache_service,
    ServiceLifecycle.SINGLETON,
    cleanup_priority=CleanupPriority.LOW  # Clean up late
)
```

## Next Steps

- **[Models API](models.md)**: Data models and validation
- **[Renderers API](renderers.md)**: Output rendering system
- **[Architecture Guide](../architecture.md)**: System design patterns

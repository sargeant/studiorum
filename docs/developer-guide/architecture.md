---
title: Architecture Overview
description: Understanding studiorum's design patterns, data flow, and component relationships
---

# Architecture Overview

Studiorum is built on a service-oriented architecture designed for extensibility, type safety, and performance. This document provides a comprehensive overview of the system's design.

## High-Level Architecture

<div class="mermaid">
graph TB
    subgraph DS ["Data Sources"]
        5E[5etools Data]
        LOCAL[Local Content]
        API[External APIs]
    end

    subgraph CP ["Core Processing"]
        MERGER[ContentMerger]
        OMNI[Omnidexer]
        RESOLVER[ContentResolver]
    end

    subgraph SC ["Service Container"]
        SCont[ServiceContainer]
        PROTO[Protocol Definitions]
        DI[Dependency Injection]
    end

    subgraph PP ["Processing Pipeline"]
        PARSER[TagParser]
        RENDERER[Renderers]
        TRACKER[ContentTracker]
    end

    subgraph OS ["Output Systems"]
        LATEX[LaTeX Engine]
        MCP[MCP Server]
        CLI[CLI Interface]
    end

    5E --> MERGER
    LOCAL --> MERGER
    API --> MERGER

    MERGER --> OMNI
    OMNI --> RESOLVER

    SCont --> OMNI
    PROTO --> SCont
    DI --> SCont

    RESOLVER --> PARSER
    PARSER --> RENDERER
    RENDERER --> TRACKER

    TRACKER --> LATEX
    TRACKER --> MCP
    TRACKER --> CLI
</div>

## Core Components

### Service Container Architecture

Studiorum uses a sophisticated service container for dependency injection and lifecycle management:

```python
# Core service container pattern
@dataclass
class ServiceDescriptor[T]:
    protocol: type[T]
    factory: ServiceFactory[T] | AsyncServiceFactory[T]
    lifecycle: ServiceLifecycle
    dependencies: tuple[type[Any], ...]

class ServiceContainer:
    """
    Manages service registration, instantiation, and lifecycle.
    Supports both sync and async services with protocol-based typing.
    """

    async def get_service[T](self, protocol: type[T]) -> T:
        """Type-safe service resolution with protocol validation."""

    def register_service[T](
        self,
        protocol: type[T],
        factory: ServiceFactory[T],
        lifecycle: ServiceLifecycle,
    ) -> None:
        """Register services with proper typing and dependency tracking."""
```

**Key Features**:

- **Protocol-based typing**: All services implement protocols for loose coupling
- **Lifecycle management**: Singleton, transient, and scoped service lifetimes
- **Dependency injection**: Automatic resolution of service dependencies
- **Hot reloading**: Support for configuration changes without restart
- **Cleanup ordering**: Proper shutdown sequence with priority-based cleanup

### Content Processing Pipeline

#### 1. Content Ingestion

```python
class ContentMerger:
    """
    Merges content from multiple sources with conflict resolution.
    Implements LRU caching and TTL-based invalidation.
    """

    def merge_sources(
        self,
        sources: list[ContentSource],
        strategy: MergeStrategy = MergeStrategy.PRIORITY_BASED
    ) -> MergedContent:
        """Intelligent content merging with conflict resolution."""
```

#### 2. Content Indexing

```python
class Omnidexer:
    """
    High-performance content indexing system.
    Provides fast lookup and search across all content types.
    """

    def index_content[T: DeepIndexable](self, content: T) -> IndexResult:
        """Deep indexing using the DeepIndexable protocol."""

    def search[T](
        self,
        query: SearchQuery,
        content_type: type[T]
    ) -> SearchResult[T]:
        """Type-safe content search with filtering and ranking."""
```

#### 3. Content Resolution

```python
class ContentResolver:
    """
    Resolves content references and builds complete content graphs.
    Handles cross-references, dependencies, and validation.
    """

    def resolve_adventure(self, adventure_id: str) -> Result[Adventure, ResolveError]:
        """Resolve adventure with all dependencies and cross-references."""
```

### Processing Architecture

#### Tag Processing System

Studiorum uses an AST-based tag processing system for 5e content:

```python
class TagParser:
    """
    Lark-based parser for 5etools tag syntax.
    Builds abstract syntax trees for complex tag structures.
    """

    def parse(self, content: str) -> TagAST:
        """Parse tagged content into structured AST."""

class TagResolver:
    """
    Resolves tag references and builds complete content structures.
    Integrates with ContentTracker for cross-reference management.
    """

    def resolve_tag(
        self,
        tag: TagNode,
        context: RenderingContext
    ) -> Result[ResolvedContent, TagError]:
        """Resolve individual tags with context awareness."""
```

#### Rendering Pipeline

```python
class RenderingContext:
    """
    Immutable context object carrying rendering state and configuration.
    Provides type-safe access to services and metadata.
    """

    output_format: str
    omnidexer: OmnidexerProtocol
    content_tracker: ContentTracker
    metadata: dict[str, Any]

class UnifiedTagRenderer:
    """
    Dispatches tag rendering to appropriate handlers.
    Supports multiple output formats and extensible handler system.
    """

    def render_tag(
        self,
        tag: ResolvedTag,
        context: RenderingContext
    ) -> str:
        """Render tag using appropriate format-specific handler."""
```

## Data Flow Architecture

### Request Processing Flow

<div class="mermaid">
sequenceDiagram
    participant Client
    participant CLI/MCP
    participant ServiceContainer
    participant ContentResolver
    participant Omnidexer
    participant TagProcessor
    participant Renderer
    participant LaTeXEngine

    Client->>CLI/MCP: Request conversion
    CLI/MCP->>ServiceContainer: Get required services
    ServiceContainer->>ContentResolver: Create resolver instance
    ContentResolver->>Omnidexer: Load content data
    ContentResolver->>TagProcessor: Parse content tags
    TagProcessor->>Renderer: Process with context
    Renderer->>LaTeXEngine: Generate output
    LaTeXEngine->>Client: Return formatted document
</div>

### Service Lifecycle Management

```python
@enum.unique
class ServiceLifecycle(enum.Enum):
    """Service instance lifecycle management strategies."""

    SINGLETON = "singleton"      # One instance per container
    TRANSIENT = "transient"      # New instance per request
    SCOPED = "scoped"           # One instance per scope (e.g., request)

class ServiceContainer:
    async def __aenter__(self) -> ServiceContainer:
        """Initialize all singleton services on container startup."""

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Cleanup services in reverse dependency order."""
```

## Type Safety Architecture

### Protocol-Based Design

Studiorum uses Python protocols extensively for type-safe interfaces:

```python
# Core service protocols
@runtime_checkable
class OmnidexerProtocol(Protocol):
    """Protocol for content indexing and search services."""

    def is_loaded(self) -> bool: ...
    def get_content[T](self, content_id: str, content_type: type[T]) -> T | None: ...
    async def search_async[T](self, query: SearchQuery) -> SearchResult[T]: ...

@runtime_checkable
class ContentResolverProtocol(Protocol):
    """Protocol for content resolution services."""

    def resolve_adventure(self, adventure_id: str) -> Result[Adventure, ResolveError]: ...
    def resolve_creature(self, creature_id: str) -> Result[Creature, ResolveError]: ...
```

### Result Type Pattern

All operations that can fail use Result types for explicit error handling:

```python
from typing import TypeVar, Generic, Union

T = TypeVar('T')
E = TypeVar('E')

class Success[T, E](Generic[T, E]):
    def __init__(self, value: T) -> None:
        self.value = value

    def unwrap(self) -> T:
        return self.value

class Error[T, E](Generic[T, E]):
    def __init__(self, error: E) -> None:
        self.error = error

    def with_context(self, message: str, **context: Any) -> Error:
        """Chain error context for better debugging."""
        return Error({
            "message": message,
            "underlying": self.error,
            "context": context
        })

Result = Union[Success[T, E], Error[T, E]]
```

### Content Model Architecture

All content follows structured Pydantic models with validation:

```python
class BaseContent(BaseModel):
    """Base class for all 5e content with common fields."""

    name: str
    source: Source
    page: int | None = None

    class Config:
        validate_assignment = True
        extra = "forbid"

class Creature(BaseContent):
    """Structured creature data with type validation."""

    size: CreatureSize
    creature_type: CreatureType
    challenge_rating: ChallengeRating
    armor_class: ArmorClass
    hit_points: HitPoints
    speeds: list[Speed]
    ability_scores: AbilityScores
    skills: list[Skill] = []
    damage_resistances: list[DamageType] = []
    # ... additional fields with full typing
```

## Async/Sync Architecture

### Hybrid Design Pattern

Studiorum intentionally uses a hybrid async/sync architecture:

```python
# CLI Context - Synchronous by design
class CLIContext:
    """Synchronous context for CLI operations."""

    def get_omnidexer(self) -> Omnidexer:
        from studiorum.core.services.container import ServiceContainer
        from studiorum.core.services.protocols import OmnidexerProtocol
        return ServiceContainer.get_global_instance().get_service_sync(OmnidexerProtocol)

# MCP Context - Asynchronous by design
class AsyncRequestContext:
    """Asynchronous context for MCP server operations."""

    async def get_service[T](self, protocol: type[T]) -> T:
        return await self.container.get_service(protocol)
```

**Design Rationale**:

- **CLI**: Sequential operations, simple debugging, direct user feedback
- **MCP**: Concurrent requests, isolation, scalable AI agent integration
- **Testing**: Easier to test sync code, async when needed for concurrency

### Service Access Patterns

```python
# Sync access pattern (CLI)
def convert_adventure_sync(adventure_name: str) -> Result[str, ConversionError]:
    omnidexer = get_omnidexer()  # Sync singleton access
    resolver = ContentResolver(omnidexer)
    return resolver.resolve_and_convert(adventure_name)

# Async access pattern (MCP)
async def convert_adventure_async(
    ctx: AsyncRequestContext,
    adventure_name: str
) -> Result[str, ConversionError]:
    omnidexer = await ctx.get_service(OmnidexerProtocol)
    resolver = await ctx.get_service(ContentResolverProtocol)
    return await resolver.resolve_and_convert_async(adventure_name)
```

## Observability Architecture

### Integrated Observability

Studiorum includes comprehensive observability through Logfire integration:

```python
class ObservableImageService:
    """Wraps services with automatic observability."""

    def __init__(self, wrapped_service: Any, observer: ImageProcessingObserver):
        self._wrapped = wrapped_service
        self._observer = observer

    def __getattr__(self, name: str) -> Any:
        """Automatically instrument all method calls."""
        attr = getattr(self._wrapped, name)
        if callable(attr):
            return self._create_observable_method(name, attr)
        return attr

    def _create_observable_method(self, method_name: str, method: Callable) -> Callable:
        """Create instrumented version of method with metrics collection."""
        def instrumented(*args, **kwargs):
            operation_id = self._observer.start_operation(
                stage=self._infer_stage(method_name),
                content_type=self._infer_content_type(args)
            )

            try:
                result = method(*args, **kwargs)
                self._observer.complete_operation(operation_id, result)
                return result
            except Exception as e:
                self._observer.fail_operation(operation_id, e)
                raise

        return instrumented
```

### Performance Monitoring

```python
@dataclass
class ProcessingStatistics:
    """Real-time processing statistics."""

    total_operations: int = 0
    successful_operations: int = 0
    failed_operations: int = 0
    average_duration_ms: float = 0.0

    operations_by_stage: dict[ImageProcessingStage, int] = field(default_factory=dict)
    operations_by_content_type: dict[ContentType, int] = field(default_factory=dict)

    def calculate_success_rate(self) -> float:
        """Calculate operation success rate."""
        if self.total_operations == 0:
            return 1.0
        return self.successful_operations / self.total_operations
```

## Extension Architecture

### Plugin System

Studiorum supports extensible plugins through well-defined interfaces:

```python
@runtime_checkable
class RendererPlugin(Protocol):
    """Protocol for custom renderer plugins."""

    def get_supported_formats(self) -> list[str]: ...
    def render_content(self, content: Any, context: RenderingContext) -> str: ...
    def get_plugin_info(self) -> PluginInfo: ...

class PluginManager:
    """Manages plugin registration and lifecycle."""

    def register_plugin(self, plugin: RendererPlugin) -> None:
        """Register a new renderer plugin."""

    def get_renderer(self, format_type: str) -> RendererPlugin | None:
        """Get appropriate renderer for format."""
```

### Custom Tag Handlers

```python
@runtime_checkable
class TagHandler(Protocol):
    """Protocol for custom tag handlers."""

    def get_supported_tags(self) -> list[str]: ...
    def handle_tag(self, tag: TagNode, context: RenderingContext) -> str: ...

# Custom handler example
class CustomCreatureHandler:
    def get_supported_tags(self) -> list[str]:
        return ["@custom_creature"]

    def handle_tag(self, tag: TagNode, context: RenderingContext) -> str:
        # Custom rendering logic
        return self.render_custom_creature(tag.attributes, context)
```

## Performance Architecture

### Optimized Service Access

The service container implements a dual-cache system for high-performance service resolution:

```python
class ServiceContainer:
    def get_service_sync[T](self, protocol: type[T]) -> T:
        """Optimized synchronous service access with dedicated caching."""
        # Fast-path singleton cache eliminates async overhead
        if cached := self._sync_singleton_cache.get(protocol):
            return cached

        # Cross-populate caches for future fast access
        service = asyncio.run(self.get_service(protocol))
        self._sync_singleton_cache[protocol] = service
        return service
```

**Performance Features**:
- **Fast-path caching**: Avoids expensive event loop creation for cached services
- **Cross-cache population**: Services created async are automatically available sync
- **Test optimization**: Direct synchronous creation in test environments
- **Singleton persistence**: ContentMerger and other singletons maintain warm caches

### Caching Strategy

Multi-level caching for optimal performance:

```python
class CacheManager:
    """Manages multiple cache levels with intelligent eviction."""

    def __init__(self):
        self.l1_cache = LRUCache(maxsize=1000)      # In-memory, fast
        self.l2_cache = DiskCache(maxsize=10000)    # Disk-based, persistent
        self.l3_cache = RedisCache()                # Distributed, scalable

    async def get[T](self, key: str, factory: Callable[[], T]) -> T:
        """Multi-level cache with write-through strategy."""

        # L1 - Memory cache
        if value := self.l1_cache.get(key):
            return value

        # L2 - Disk cache
        if value := await self.l2_cache.get(key):
            self.l1_cache[key] = value
            return value

        # L3 - Distributed cache
        if value := await self.l3_cache.get(key):
            self.l1_cache[key] = value
            await self.l2_cache.set(key, value)
            return value

        # Generate and cache
        value = await factory()
        await self._cache_at_all_levels(key, value)
        return value
```

### Parallel Processing

```python
class ParallelProcessor:
    """Manages parallel processing with resource limits."""

    def __init__(self, max_workers: int | None = None):
        self.max_workers = max_workers or os.cpu_count()
        self.semaphore = asyncio.Semaphore(self.max_workers)

    async def process_batch[T, R](
        self,
        items: list[T],
        processor: Callable[[T], Awaitable[R]],
        chunk_size: int = 10
    ) -> list[R]:
        """Process items in parallel with controlled concurrency."""

        async def process_with_semaphore(item: T) -> R:
            async with self.semaphore:
                return await processor(item)

        tasks = [process_with_semaphore(item) for item in items]
        return await asyncio.gather(*tasks)
```

## Security Architecture

### Input Validation

All external input goes through strict validation:

```python
class ContentValidator:
    """Validates all content input against schemas."""

    def validate_content_id(self, content_id: str) -> Result[str, ValidationError]:
        """Validate content identifiers against allowed patterns."""

    def validate_search_query(self, query: SearchQuery) -> Result[SearchQuery, ValidationError]:
        """Validate and sanitize search queries."""

    def validate_output_path(self, path: str) -> Result[Path, ValidationError]:
        """Validate output paths to prevent directory traversal."""
```

### Sandboxed Execution

LaTeX compilation runs in controlled environment:

```python
class SandboxedLaTeXEngine:
    """LaTeX compiler with security restrictions."""

    def __init__(self):
        self.allowed_packages = self._load_allowed_packages()
        self.restricted_commands = self._load_restricted_commands()

    def compile_latex(
        self,
        content: str,
        output_path: Path,
        compiler: LaTeXCompiler = LaTeXCompiler.PDFLATEX
    ) -> Result[Path, CompilationError]:
        """Compile LaTeX with security restrictions and resource limits."""

        # Validate content for dangerous patterns
        validation_result = self._validate_latex_content(content)
        if isinstance(validation_result, Error):
            return validation_result

        # Run in restricted environment
        return await self._run_sandboxed_compilation(content, output_path, compiler)
```

## Testing Architecture

### Test Categories

Studiorum uses a layered testing approach:

```python
# Unit tests - Fast, isolated
class TestContentResolver:
    def setup_method(self):
        from studiorum.core.services.container import ServiceContainer
        ServiceContainer.reset_global_instance()  # Ensure test isolation

    def test_resolve_creature_success(self):
        # Test with mocked dependencies
        pass

# Integration tests - Real data, no LaTeX
@pytest.mark.requires_data
class TestFullPipeline:
    def test_adventure_conversion_integration(self):
        # Test with real 5etools data
        pass

# LaTeX tests - Full compilation
@pytest.mark.latex_integration
class TestLaTeXOutput:
    def test_pdf_generation_complete(self):
        # Full LaTeX compilation test
        pass
```

### Service Container Testing

```python
class TestServiceContainer:
    """Test service container functionality in isolation."""

    async def test_service_registration_and_resolution(self):
        container = ServiceContainer()

        # Register test service
        container.register_service(
            TestProtocol,
            lambda: TestService(),
            ServiceLifecycle.SINGLETON
        )

        # Resolve and verify
        service = await container.get_service(TestProtocol)
        assert isinstance(service, TestService)

        # Verify singleton behavior
        service2 = await container.get_service(TestProtocol)
        assert service is service2
```

## Configuration Architecture

### Unified Configuration System

```python
class ApplicationConfig(BaseModel):
    """Complete application configuration with validation."""

    # Service configuration
    services: ServicesConfig = ServicesConfig()

    # Content sources
    sources: SourcesConfig = SourcesConfig()

    # Rendering settings
    rendering: RenderingConfig = RenderingConfig()

    # LaTeX engine
    latex: LaTeXConfig = LaTeXConfig()

    # MCP server
    mcp: MCPConfig = MCPConfig()

    # Observability
    observability: ObservabilityConfig = ObservabilityConfig()

    @classmethod
    def from_file(cls, config_path: Path) -> ApplicationConfig:
        """Load and validate configuration from file."""

    def merge_with_env(self) -> ApplicationConfig:
        """Override config values with environment variables."""
```

### Hot Reloading

```python
class ConfigurationManager:
    """Manages configuration with hot reloading support."""

    def __init__(self, config_path: Path):
        self.config_path = config_path
        self.current_config = self._load_config()
        self.observers: list[Callable[[ApplicationConfig], None]] = []

    def watch_for_changes(self) -> None:
        """Watch configuration file and reload on changes."""

    def register_observer(self, observer: Callable[[ApplicationConfig], None]) -> None:
        """Register callback for configuration changes."""

    def _reload_config(self) -> None:
        """Reload configuration and notify observers."""
        new_config = self._load_config()
        if new_config != self.current_config:
            self.current_config = new_config
            self._notify_observers(new_config)
```

### Error Handling

Studiorum uses Result types with type-safe error handling patterns:

```python
# Type-safe error handling with isinstance
if isinstance(result, Error):
    return Error(f"Operation failed: {result.error}")

# Type checker knows this is Success
value = result.unwrap()
```

**Error Management Features**:
- **Type-safe patterns**: Uses `isinstance()` checks rather than error predicates
- **Unified error types**: Centralized error definitions in `core.error_types`
- **No fallbacks**: System fails fast rather than using default fallback behavior

This architecture provides a solid foundation for building on studiorum while maintaining type safety, performance, and extensibility.

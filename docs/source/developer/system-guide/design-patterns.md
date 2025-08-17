# Design Patterns

Common patterns and conventions used throughout the 5e2pdf system.

## Core Design Patterns

### Protocol-Based Architecture

5e2pdf uses Python protocols to define clear interfaces between components:

```python
from typing import Protocol

class DeepIndexable(Protocol):
    def get_deep_index_entries(self, omnidexer: "Omnidexer") -> list[BaseContent]:
        """Return nested content for indexing."""
        ...
```

**Benefits:**
- Clear interface contracts
- Type safety with mypy
- Flexible implementations
- Easy testing with mocks

### Pydantic Model Validation

All content models use Pydantic for validation and type safety:

```python
from pydantic import BaseModel, Field

class IndexEntry(BaseModel):
    hash_id: str = Field(min_length=8, max_length=8)
    lookup_key: str = Field(min_length=1)
    content_type: ContentType
```

**Benefits:**
- Runtime validation
- Automatic serialization
- Clear error messages
- API documentation generation

### Command Configuration Hierarchy

Convert commands use a three-tier configuration hierarchy with shared base classes:

```python
class BaseConvertCommand:
    def apply_config_hierarchy(self, **cli_args) -> dict[str, Any]:
        """Apply: CLI args > user config > app defaults."""
        app_config = get_app_config()
        user_config = get_content_config()

        return {
            'paper_size': (
                cli_args.get('paper')
                or user_config.latex.paper_size
                or app_config.rendering.latex.document.paper_size
            ),
            # ... more config options
        }
```

**Benefits:**
- Single source of truth for configuration logic
- Consistent behavior across all commands
- Eliminates 300+ lines of duplicate code
- Easy to add new configuration options

### Unified Content Reference System

Commands use a unified reference tracking system that automatically captures references from both template tags and deep indexing:

```python
class AppendixMixin:
    def create_reference_manager(self, omnidexer=None):
        """Create unified content reference manager."""
        return ContentReferenceManager(omnidexer=omnidexer)

    def track_deep_index_references(self, reference_manager, content_items, context):
        """Track references from deep indexing automatically."""
        for content in content_items:
            if isinstance(content, DeepIndexable):
                reference_manager.track_deep_index_references(content, context)

# Usage in commands
reference_manager = appendix_mixin.create_reference_manager(omnidexer)
appendix_mixin.track_deep_index_references(
    reference_manager, creatures, "creature spellcasting"
)
```

**Benefits:**
- Eliminates manual bridge patterns between reference systems
- Automatic tracking from both template tags and deep indexing
- Single source of truth for all content references
- Unified appendix generation across all commands
- Reduces complex bridge code from 19 lines to 4 lines

### Synchronous I/O Pattern

I/O operations use efficient synchronous patterns for simplicity and reliability:

```python
def load_all_data(self) -> None:
    """Load all content data efficiently."""
    for content_type in ContentType:
        self._load_content_type(content_type)
```

**Benefits:**
- Simplified error handling
- Predictable execution flow
- Easier debugging and testing
- Reduced complexity

### Factory Pattern for Content Creation

Content objects are created through factory methods:

```python
@classmethod
def from_json(cls, data: dict[str, Any], source: str) -> "BaseContent":
    """Create content from JSON data."""
    return cls(
        name=data["name"],
        source=source,
        # ... other fields
    )
```

**Benefits:**
- Centralized creation logic
- Validation at construction
- Consistent initialization
- Easy to extend

### Caching Strategy

LRU caching with TTL for performance optimization:

```python
from functools import lru_cache
from typing import TypeVar, Callable

@lru_cache(maxsize=128)
def cached_operation(key: str) -> Any:
    """Expensive operation with caching."""
    return expensive_computation(key)
```

**Benefits:**
- Improved performance
- Memory management
- Configurable cache sizes
- Automatic eviction

### Registry Pattern

Dynamic registration and management of content types with automatic system integration:

```python
from dnd5e.core.registry import content_type, get_content_type_registry
from dnd5e.core.models.content import BaseContent

# Content types registered via decorator
@content_type(
    enum_value="disease",
    file_patterns=["disease", "diseases", "conditionsdiseases"],
    loader_type="json",
    statblock_tags=["disease"]
)
class Disease(BaseContent):
    """Disease content automatically registered with system."""
    symptoms: list[str] = Field(default_factory=list)

# Registry provides centralized access
registry = get_content_type_registry()
all_registrations = registry.get_all()
print(f"Registered types: {len(all_registrations)}")
```

**Registry Benefits:**
- Dynamic system extension without code modification
- Centralized metadata management for file patterns and loading
- Automatic integration with all system components
- Type-safe registration with validation
- Simplified content type addition workflow

**System Integration:**
The registry automatically integrates new content types with:
- ContentType enum (dynamic value addition)
- ContentFactory (model class registration)
- SourceManager (file pattern configuration)
- Omnidexer (content type recognition)
- LaTeX Renderer (statblock tag mapping)

### Decorator Pattern

Metadata-driven registration using Python decorators:

```python
from dnd5e.core.registry.decorator import content_type

@content_type(
    enum_value="reward",
    file_patterns=["reward", "rewards"],
    loader_type="json",
    statblock_tags=["reward", "treasure"]
)
class Reward(BaseContent):
    """Reward content with decorator-based metadata."""

    rarity: str = Field(..., description="Reward rarity")
    value: int = Field(ge=0, description="Gold piece value")

# Decorator automatically:
# 1. Registers the class with ContentTypeRegistry
# 2. Stores metadata for system integration
# 3. Enables automatic ContentType.REWARD creation
```

**Decorator Benefits:**
- Declarative configuration at class definition
- Metadata co-located with implementation
- Automatic registration during import
- Type safety with runtime validation
- Consistent parameter patterns

**Implementation Flow:**
```python
# 1. Decorator captures metadata during class definition
@content_type(enum_value="reward", file_patterns=["reward"])
class Reward(BaseContent): ...

# 2. Registry stores registration for later integration
registry.register("reward", Reward, ["reward"], "json")

# 3. System initialization applies registrations
initialize_content_types()

# 4. All systems updated automatically
assert ContentType.REWARD == "reward"
factory.create_content("reward", data)  # Works immediately
```

### Service Container Pattern

Dependency injection through a centralized service container for managing component lifecycles:

```python
from dnd5e.core.container import get_global_container, ServiceContainer

# Access services through the container
container = get_global_container()
omnidexer = container.get_omnidexer()
tag_resolver = container.get_tag_resolver()
entry_registry = container.get_entry_registry()
reference_manager = container.get_reference_manager()

# Context manager for scoped containers
from dnd5e.core.container import service_container

with service_container() as container:
    # Services are automatically cleaned up
    service = container.get_omnidexer()
    # ... use service
# Container automatically closed here
```

**Service Container Benefits:**
- Centralized dependency management
- Lazy initialization of expensive services
- Proper lifecycle management and cleanup
- Simplified test isolation
- Type-safe service access
- Support for both global and scoped containers

**Migration from Global Singletons:**

```python
# Old approach (deprecated)
from dnd5e.core.entry_registry import get_registry
registry = get_registry()  # Uses global singleton

# New approach (recommended)
from dnd5e.core.container import get_global_container
container = get_global_container()
registry = container.get_entry_registry()  # Uses service container
```

## Error Handling Patterns

### Result Pattern

Standardized error handling using Result[T, E] for type-safe operations:

```python
from dnd5e.core.result import Result, Success, Error
from dnd5e.core.error_types import ValidationError, create_validation_error

def validate_spell_level(level: int) -> Result[int, ValidationError]:
    """Validate spell level with Result pattern."""
    if not 1 <= level <= 9:
        error = create_validation_error(
            message=f"Spell level {level} must be between 1 and 9",
            field_name="level",
            suggestions=["Use a level between 1 and 9"]
        )
        return Error(error)
    return Success(level)

# Usage with type safety
result = validate_spell_level(3)
if result.is_success():
    level = result.unwrap()  # Type is guaranteed to be int
else:
    error = result.error     # Type is guaranteed to be ValidationError
    logger.error(f"Validation failed: {error.message}")
```

### Error Chaining

Chain operations that may fail without nested try-catch blocks:

```python
def process_spell_data(data: dict) -> Result[ProcessedSpell, ValidationError]:
    """Chain multiple validation steps."""
    return (
        validate_required_field(data, "name")
        .and_then(lambda name: validate_spell_level(data.get("level", 1)))
        .and_then(lambda level: validate_spell_school(data.get("school")))
        .and_then(lambda school: create_processed_spell(data))
    )

# If any step fails, the chain stops and returns the error
result = process_spell_data(spell_data)
processed_spell = result.unwrap_or_else(lambda error: create_fallback_spell(error))
```

### Batch Error Collection

Handle multiple errors in batch operations:

```python
from dnd5e.core.result import collect_results

def validate_spell_batch(spell_list: list[dict]) -> Result[list[Spell], list[ValidationError]]:
    """Validate multiple spells, collecting all errors."""
    results = [validate_spell_data(data) for data in spell_list]
    return collect_results(results)

# Usage - either all succeed or collect all errors
batch_result = validate_spell_batch(spell_data_list)
if batch_result.is_success():
    spells = batch_result.unwrap()  # All spells validated
else:
    errors = batch_result.error     # All validation errors
    logger.error(f"Found {len(errors)} validation errors")
```

### Structured Logging

Consistent error logging with rich context:

```python
from dnd5e.core.logging import get_logger

logger = get_logger(__name__)

def process_content(content_data: dict, source: str) -> Result[ProcessedContent, ValidationError]:
    """Process content with simple logging."""
    content_name = content_data.get("name", "unknown")
    logger.info(f"Starting content_processing for {content_name} from {source}")

    result = validate_and_process(content_data)

    if result.is_success():
        logger.info(f"content_processing completed successfully for {content_name}")
    else:
        error = result.error
        logger.error(f"content_processing failed for {content_name}: {error.message}")

    return result
```

### Graceful Degradation with Results

Continue processing with detailed error tracking:

```python
def process_content_list(content_list: list[dict]) -> tuple[list[ProcessedContent], list[ValidationError]]:
    """Process all content, separating successes and failures."""
    successes = []
    failures = []

    for content_data in content_list:
        result = process_content(content_data)
        if result.is_success():
            successes.append(result.unwrap())
        else:
            failures.append(result.error)

    return successes, failures
```

## Performance Patterns

### Lazy Loading

Load data only when needed:

```python
class ContentLoader:
    def __init__(self):
        self._cache: dict[str, Any] = {}

    @property
    def content(self) -> dict[str, Any]:
        if "content" not in self._cache:
            self._cache["content"] = self._load_content()
        return self._cache["content"]
```

### Batch Processing

Process items in batches for efficiency:

```python
def process_in_batches(items: list[Any], batch_size: int = 50) -> list[Any]:
    """Process items in batches to manage memory usage."""
    results = []
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        batch_results = process_batch(batch)
        results.extend(batch_results)
    return results
```

## Testing Patterns

### Mock Protocols

Use protocols for easy mocking:

```python
from unittest.mock import Mock

def test_with_mock_loader():
    mock_loader = Mock(spec=ContentLoader)
    mock_loader.load_content.return_value = test_data

    result = process_with_loader(mock_loader)
    assert result == expected_result
```

### Fixture Patterns

Consistent test data patterns:

```python
@pytest.fixture
def sample_spell() -> Spell:
    """Create a sample spell for testing."""
    return Spell(
        name="Test Spell",
        level=1,
        school="Evocation",
        # ... other fields
    )
```

## Integration Patterns

### Plugin Architecture

Extensible system through well-defined interfaces:

```python
class Renderer(Protocol):
    def render(self, content: BaseContent) -> str:
        """Render content to string format."""
        ...

class LatexRenderer:
    def render(self, content: BaseContent) -> str:
        # LaTeX-specific rendering
        return latex_output
```

### Configuration Management

Hierarchical configuration with environment overrides:

```python
from pydantic import BaseSettings

class Settings(BaseSettings):
    debug: bool = False
    cache_size: int = 128

    class Config:
        env_prefix = "DND5E_"
        env_file = ".env"
```

### Unified Context Pattern

5e2pdf implements a hierarchical context system for consistent state management across different operations:

```python
from dnd5e.core.base_context import BaseContext, Context, ServiceContext

class ProcessingContext[T](Context):
    """Generic context for type-safe processing operations."""
    content: T = Field(description="Content being processed")
    content_type_name: str = Field(description="Type identifier")
    processing_options: dict[str, Any] = Field(default_factory=dict)

class ServiceContext(Context):
    """Context with dependency injection support."""
    omnidexer: Omnidexer | None = Field(default=None)
    config: ApplicationConfig | LaTeXConfig | None = Field(default=None)
```

**Key Features:**
- **Type Safety**: Generic `ProcessingContext[T]` ensures type consistency
- **Service Injection**: `ServiceContext` provides standardized dependency access
- **Inheritance Hierarchy**: `BaseContext` → `Context` → specialized contexts
- **Pydantic Integration**: Full validation and serialization support

**Usage Pattern:**
```python
def process_content[T](content: T, context: ProcessingContext[T]) -> ProcessedResult[T]:
    # Type-safe processing with validated context
    if context.processing_options.get("validate", True):
        validate_content(content)
    return ProcessedResult(content=content, context=context)
```

### Unified Reference Pattern

The system uses a generic `Reference[T]` pattern for type-safe content resolution:

```python
from dnd5e.core.unified_references import Reference, ReferenceParser, ReferenceResolver

@dataclass(frozen=True)
class Reference[T]:
    """Generic reference to content of type T."""
    source: str = Field(description="Text/tag that created this reference")
    target: str = Field(description="Target identifier")
    content_type: type[T] = Field(description="Type of content referenced")
    display_text: str | None = Field(None, description="Custom display text")

class ReferenceResolver[T](ABC):
    """Abstract resolver for specific content types."""
    @abstractmethod
    def resolve(self, ref: Reference[T]) -> T | None: ...

    @abstractmethod
    def format_reference(self, ref: Reference[T], format_type: ReferenceFormat) -> str: ...
```

**Benefits:**
- **Type Safety**: `Reference[T]` prevents type confusion at compile time
- **Multi-format Support**: LaTeX, HTML, Markdown, Plain Text output
- **Caching**: Built-in `ReferenceCache` with type-safe operations
- **Extensibility**: Easy to add new content types and resolvers

**Usage Pattern:**
```python
# Create type-safe reference
spell_ref = Reference(
    source="@spell{fireball}",
    target="fireball",
    content_type=Spell,
    display_text="powerful fireball spell"
)

# Resolve with type safety
resolver = SpellReferenceResolver()
spell: Spell | None = resolver.resolve(spell_ref)  # Type is guaranteed
```

## Architectural Principles

### Single Responsibility

Each class has a single, well-defined purpose:

- `Omnidexer`: Content indexing and discovery
- `ContentParser`: JSON to object transformation
- `LaTeXRenderer`: PDF output generation

### Open/Closed Principle

Open for extension, closed for modification:

```python
class BaseProcessor:
    def process(self, content: BaseContent) -> Any:
        return self._process_content(content)

    def _process_content(self, content: BaseContent) -> Any:
        """Override in subclasses."""
        raise NotImplementedError

class SpellProcessor(BaseProcessor):
    def _process_content(self, content: Spell) -> SpellOutput:
        # Spell-specific processing
        return spell_output
```

### Dependency Inversion

Depend on abstractions, not concretions:

```python
class DocumentGenerator:
    def __init__(self, renderer: Renderer, loader: ContentLoader):
        self.renderer = renderer  # Protocol, not concrete class
        self.loader = loader      # Protocol, not concrete class
```

These patterns ensure consistency, maintainability, and extensibility throughout the codebase.

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
from dnd5e.core.logging_strategy import get_standardized_logger, error_logging_context

logger = get_standardized_logger(__name__)

def process_content(content_data: dict, source: str) -> Result[ProcessedContent, ValidationError]:
    """Process content with structured logging."""
    with error_logging_context(
        logger,
        "content_processing",
        content_name=content_data.get("name", "unknown"),
        file_path=source
    ) as context:
        result = validate_and_process(content_data)
        logger.log_result(result, "content_processing", context=context)
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

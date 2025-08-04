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

### Async/Await Pattern

I/O operations use async/await for performance:

```python
async def load_all_data(self) -> None:
    """Load all content data asynchronously."""
    tasks = [self._load_content_type(ct) for ct in ContentType]
    await asyncio.gather(*tasks)
```

**Benefits:**
- Non-blocking operations
- Better resource utilization
- Scalable performance
- Clean error handling

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

## Error Handling Patterns

### Graceful Degradation

Continue processing when individual items fail:

```python
results = []
for item in items:
    try:
        result = process_item(item)
        results.append(result)
    except ProcessingError as e:
        logger.warning(f"Failed to process {item}: {e}")
        # Continue with next item
```

### Structured Logging

Consistent logging patterns throughout the system:

```python
from dnd5e.core.logging import get_logger

logger = get_logger(__name__)

def process_content(content: BaseContent) -> None:
    logger.info(f"Processing {content.content_type} '{content.name}'")
    try:
        # ... processing logic
        logger.debug(f"Successfully processed {content.name}")
    except Exception as e:
        logger.error(f"Failed to process {content.name}: {e}")
        raise
```

### Validation Patterns

Multi-stage validation with clear error reporting:

```python
def validate_content(data: dict[str, Any]) -> None:
    """Validate content data with detailed error reporting."""
    errors = []

    if "name" not in data:
        errors.append("Missing required field 'name'")

    if errors:
        raise ValidationError(f"Content validation failed: {', '.join(errors)}")
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
async def process_in_batches(items: list[Any], batch_size: int = 50) -> list[Any]:
    """Process items in batches to manage memory usage."""
    results = []
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        batch_results = await process_batch(batch)
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
from dnd5e.core.base_context import BaseContext, CoreContext, ServiceContext

class ProcessingContext[T](CoreContext):
    """Generic context for type-safe processing operations."""
    content: T = Field(description="Content being processed")
    content_type_name: str = Field(description="Type identifier")
    processing_options: dict[str, Any] = Field(default_factory=dict)

class ServiceContext(CoreContext):
    """Context with dependency injection support."""
    omnidexer: Omnidexer | None = Field(default=None)
    config: ApplicationConfig | LaTeXConfig | None = Field(default=None)
```

**Key Features:**
- **Type Safety**: Generic `ProcessingContext[T]` ensures type consistency
- **Service Injection**: `ServiceContext` provides standardized dependency access
- **Inheritance Hierarchy**: `BaseContext` → `CoreContext` → specialized contexts
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

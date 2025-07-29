# Protocols and Interfaces

Protocol definitions for extensibility and loose coupling.

## Core Interfaces

Protocol definitions that define the core interfaces of the system.

```{eval-rst}
.. automodule:: dnd5e.core.interfaces
   :members:
   :undoc-members:
   :show-inheritance:
```

## Protocol Overview

The 5e2pdf system uses Python protocols (typing.Protocol) to define interfaces that enable:

- **Loose coupling** between components
- **Extensibility** through custom implementations
- **Type safety** with static type checking
- **Clear contracts** for component interactions

### Key Design Principles

1. **Protocol-based design**: Components depend on interfaces, not implementations
2. **Composition over inheritance**: Protocols define capabilities, not hierarchies
3. **Single responsibility**: Each protocol defines one clear responsibility
4. **Minimal interfaces**: Protocols contain only essential methods

## Data Access Protocols

### ContentLoader Protocol

```python
from typing import Protocol, List, Optional, AsyncIterator
from dnd5e.core.models import BaseContent, ContentType, Source

class ContentLoader(Protocol):
    """Protocol for content loading systems."""

    async def load_content(
        self,
        content_type: ContentType,
        source: Optional[Source] = None
    ) -> List[BaseContent]:
        """Load content of specified type from source."""
        ...

    async def load_all_content(self) -> AsyncIterator[BaseContent]:
        """Load all available content."""
        ...

    def get_available_sources(self) -> List[Source]:
        """Get list of available content sources."""
        ...

    def get_available_content_types(self) -> List[ContentType]:
        """Get list of available content types."""
        ...
```

**Implementation Example:**

```python
from dnd5e.core.interfaces import ContentLoader

class CustomContentLoader:
    """Custom implementation of ContentLoader protocol."""

    async def load_content(self, content_type, source=None):
        # Custom loading logic
        return await self._load_from_database(content_type, source)

    async def load_all_content(self):
        # Stream content from custom source
        async for item in self._stream_from_api():
            yield item

    def get_available_sources(self):
        return ["CustomSource1", "CustomSource2"]

    def get_available_content_types(self):
        return ["spell", "monster", "item"]
```

### ContentResolver Protocol

```python
class ContentResolver(Protocol):
    """Protocol for content resolution and searching."""

    def find(
        self,
        content_type: Optional[ContentType] = None,
        source: Optional[Source] = None,
        **filters
    ) -> List[BaseContent]:
        """Find content matching criteria."""
        ...

    def find_one(
        self,
        content_type: Optional[ContentType] = None,
        name: Optional[str] = None,
        **filters
    ) -> Optional[BaseContent]:
        """Find single content item."""
        ...

    def search(self, query: str) -> List[BaseContent]:
        """Full-text search across content."""
        ...
```

## Rendering Protocols

### Renderer Protocol

```python
class Renderer(Protocol):
    """Protocol for content rendering systems."""

    def render_content(
        self,
        content: List[BaseContent],
        **options
    ) -> str:
        """Render content to string output."""
        ...

    def render_to_file(
        self,
        content: List[BaseContent],
        output_path: str,
        **options
    ) -> None:
        """Render content directly to file."""
        ...

    def get_supported_formats(self) -> List[str]:
        """Get list of supported output formats."""
        ...
```

### TemplateEngine Protocol

```python
class TemplateEngine(Protocol):
    """Protocol for template processing systems."""

    def render_template(
        self,
        template_name: str,
        context: dict,
        **options
    ) -> str:
        """Render template with context data."""
        ...

    def get_available_templates(self) -> List[str]:
        """Get list of available templates."""
        ...

    def validate_template(self, template_name: str) -> bool:
        """Validate template syntax."""
        ...
```

## Indexing Protocols

### TagResolver Protocol

```python
class TagResolver(Protocol):
    """Protocol for tag resolution systems."""

    def resolve_tags(self, text: str) -> str:
        """Resolve all tags in text."""
        ...

    def resolve_tag(self, tag: str) -> Optional[str]:
        """Resolve single tag."""
        ...

    def get_supported_tag_types(self) -> List[str]:
        """Get supported tag types."""
        ...
```

### ReferenceIndex Protocol

```python
class ReferenceIndex(Protocol):
    """Protocol for content reference indexing."""

    def add_content(self, content: BaseContent) -> None:
        """Add content to index."""
        ...

    def find_references(self, query: str) -> List[Reference]:
        """Find references matching query."""
        ...

    def get_cross_references(self, content: BaseContent) -> List[Reference]:
        """Get cross-references for content."""
        ...
```

## Configuration Protocols

### ConfigProvider Protocol

```python
class ConfigProvider(Protocol):
    """Protocol for configuration providers."""

    def get_config(self, key: str, default=None):
        """Get configuration value."""
        ...

    def set_config(self, key: str, value) -> None:
        """Set configuration value."""
        ...

    def get_all_config(self) -> dict:
        """Get all configuration values."""
        ...

    def validate_config(self) -> bool:
        """Validate configuration."""
        ...
```

## Extension Protocols

### Plugin Protocol

```python
class Plugin(Protocol):
    """Protocol for plugin systems."""

    def initialize(self, context: PluginContext) -> None:
        """Initialize plugin with context."""
        ...

    def get_name(self) -> str:
        """Get plugin name."""
        ...

    def get_version(self) -> str:
        """Get plugin version."""
        ...

    def get_dependencies(self) -> List[str]:
        """Get plugin dependencies."""
        ...
```

### Middleware Protocol

```python
class Middleware(Protocol):
    """Protocol for middleware systems."""

    def process_content(
        self,
        content: BaseContent,
        context: ProcessingContext
    ) -> BaseContent:
        """Process content through middleware."""
        ...

    def get_priority(self) -> int:
        """Get middleware priority (lower = earlier)."""
        ...
```

## Usage Examples

### Implementing Custom Components

```python
# Custom renderer implementation
class JSONRenderer:
    """JSON output renderer."""

    def render_content(self, content, **options):
        return json.dumps([item.model_dump() for item in content], indent=2)

    def render_to_file(self, content, output_path, **options):
        with open(output_path, 'w') as f:
            f.write(self.render_content(content, **options))

    def get_supported_formats(self):
        return ["json"]

# Register with system
from dnd5e.renderers import register_renderer
register_renderer("json", JSONRenderer())
```

### Protocol Composition

```python
class AdvancedContentLoader:
    """Combines multiple protocols for advanced functionality."""

    def __init__(self, loader: ContentLoader, resolver: ContentResolver):
        self.loader = loader
        self.resolver = resolver

    async def load_and_filter(self, content_type, **filters):
        # Load content using loader protocol
        content = await self.loader.load_content(content_type)

        # Filter using resolver protocol
        filtered = []
        for item in content:
            if self._matches_filters(item, filters):
                filtered.append(item)

        return filtered
```

### Type Checking

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dnd5e.core.interfaces import ContentLoader, Renderer

def process_content(
    loader: ContentLoader,
    renderer: Renderer,
    content_type: str
) -> str:
    """Process content with type safety."""
    content = await loader.load_content(content_type)
    return renderer.render_content(content)
```

## Protocol Benefits

### Extensibility

```python
# Easy to add new implementations
class DatabaseContentLoader:
    """Load content from database."""
    # Implements ContentLoader protocol

class APIContentLoader:
    """Load content from REST API."""
    # Implements ContentLoader protocol

class CacheContentLoader:
    """Cached content loader."""
    # Implements ContentLoader protocol
```

### Testing

```python
# Easy mocking for tests
class MockContentLoader:
    """Mock loader for testing."""

    async def load_content(self, content_type, source=None):
        return [create_mock_content(content_type)]

    def get_available_sources(self):
        return ["TestSource"]

# Use in tests
def test_content_processing():
    loader = MockContentLoader()
    result = process_content(loader, "spell")
    assert len(result) > 0
```

### Dependency Injection

```python
# Configure components via protocols
def create_application(
    loader: ContentLoader,
    renderer: Renderer,
    resolver: TagResolver
) -> Application:
    """Create application with injected dependencies."""
    return Application(
        content_system=ContentSystem(loader, resolver),
        output_system=OutputSystem(renderer),
    )
```

See {doc}`/developer/architecture` for more details on the protocol-based architecture and {doc}`/developer/contributing` for guidelines on implementing new protocols.

# Context and Reference Systems API

## Table of Contents

This page covers the unified context and reference systems with the following sections:

- [Context System Overview](#context-system-overview)
- [Base Context Classes](#base-context-classes)
- [Specialized Context Classes](#specialized-context-classes)
- [Reference System Overview](#reference-system-overview)
- [Reference Classes](#reference-classes)
- [Parser and Resolver Interfaces](#parser-and-resolver-interfaces)
- [Usage Examples](#usage-examples)

## Context System Overview

The 5e2pdf context system provides a hierarchical approach to state management across different operations. It uses Pydantic models for validation and modern Python 3.12 generic syntax for type safety.

### Key Features

- **Type Safety**: Generic contexts ensure compile-time type consistency
- **Service Injection**: Standardized dependency access patterns
- **Pydantic Integration**: Full validation and serialization support
- **Inheritance Hierarchy**: Clear separation of concerns through base classes

## Base Context Classes

### Protocol: BaseContext

The foundational protocol that all contexts implement.

```python
from typing import Protocol, Any

class BaseContext(Protocol):
    """Base protocol for all context objects."""

    @property
    def content_type(self) -> str:
        """Return the type of content this context handles."""
        ...

    @property
    def source_info(self) -> dict[str, Any]:
        """Return source tracking information."""
        ...
```

### Class: Context

Base implementation providing common fields for all contexts.

```python
from pydantic import BaseModel, Field

class Context(BaseModel):
    """Core context with standardized source tracking and content fields."""

    # Content and processing
    omnidexer: Omnidexer | None = Field(default=None)
    source_file: str | None = Field(default=None)
    source_section: str | None = Field(default=None)
    line_number: int | None = Field(default=None)

    @property
    def content_type(self) -> str:
        return "core"
```

**Key Fields:**
- `omnidexer`: Content indexer instance for lookups
- `source_file`: Source file path for error reporting
- `source_section`: Section within source for debugging
- `line_number`: Line number for precise error location

### Class: ProcessingContext[T]

Generic context for type-safe processing operations.

```python
class ProcessingContext[T](Context):
    """Generic context for type-safe processing operations."""

    content: T = Field(description="Content being processed")
    content_type_name: str = Field(description="Type identifier")
    processing_options: dict[str, Any] = Field(default_factory=dict)
```

**Type Parameters:**
- `T`: The type of content being processed

**Usage:**
```python
# Type-safe spell processing
spell_context = ProcessingContext[Spell](
    content=fireball_spell,
    content_type_name="spell",
    processing_options={"validate": True}
)
```

### Class: ServiceContext

Context with dependency injection and service access.

```python
class ServiceContext(Context):
    """Context with standardized service access."""

    config: Any = Field(default=None)
    tag_resolver: Any = Field(default=None)
    cross_ref_manager: Any = Field(default=None)
    content_tracker: Any = Field(default=None)
```

**Service Fields:**
- `config`: Application or LaTeX configuration
- `tag_resolver`: Tag parsing and resolution service
- `cross_ref_manager`: Cross-reference management
- `content_tracker`: Content tracking for appendices

## Specialized Context Classes

### ValidationContext

Context for entry validation operations, inheriting from `ProcessingContext[Any]`.

```python
class ValidationContext(ProcessingContext[Any]):
    """Context for entry validation operations."""

    entry_data: Any = Field(description="Entry data to validate")
    validation_mode: ValidationMode | None = Field(default=None)
```

**Usage:**
```python
validation_context = ValidationContext(
    entry_data={"type": "section", "name": "Introduction"},
    content_type_name="entry",
    validation_mode=ValidationMode.STRICT
)
```

### RendererContext

Context for tag rendering operations, inheriting from `ServiceContext`.

```python
class RendererContext(ServiceContext):
    """Context for tag rendering operations."""

    renderer: Any = Field(description="Tag renderer instance")

    def render_node(self, node: ASTNode) -> str:
        """Render a node using the renderer."""
        return cast(str, self.renderer.render_node(node, self))
```

## Reference System Overview

The reference system provides type-safe content resolution with support for multiple output formats and comprehensive caching.

### Key Features

- **Type Safety**: Generic `Reference[T]` prevents type confusion
- **Multi-format Support**: LaTeX, HTML, Markdown, Plain Text output
- **Performance**: Built-in caching with type-safe operations
- **Extensibility**: Easy to add new content types and resolvers

## Reference Classes

### Dataclass: Reference[T]

Generic reference to content of type T.

```python
@dataclass(frozen=True)
class Reference[T]:
    """Generic reference to content of type T."""

    # Core identity
    source: str = Field(description="Text/tag that created this reference")
    target: str = Field(description="Target identifier")
    content_type: type[T] = Field(description="Type of content referenced")

    # Optional metadata
    source_book: str | None = Field(None, description="Source book abbreviation")
    display_text: str | None = Field(None, description="Custom display text")
    reference_type: ReferenceType = Field(default=ReferenceType.CONTENT)

    # LaTeX-specific metadata
    latex_label: str | None = Field(None, description="Generated LaTeX label")
    section: str | None = Field(None, description="Document section")
    page: int | None = Field(None, description="Page number if known")
```

**Type Parameters:**
- `T`: The type of content being referenced

**Methods:**
```python
def get_cache_key(self) -> str:
    """Generate a cache key for this reference."""

def with_latex_info(self, label: str, section: str | None = None, page: int | None = None) -> Reference[T]:
    """Create a copy with LaTeX-specific information added."""
```

### Enum: ReferenceType

Types of references supported by the system.

```python
class ReferenceType(str, Enum):
    CONTENT = "content"      # References to game content
    SECTION = "section"      # Document section references
    PAGE = "page"           # Page references
    EXTERNAL = "external"    # External document references
    CROSS_REF = "cross_ref"  # Cross-references within document
    HYPERLINK = "hyperlink"  # Web/external hyperlinks
```

### Enum: ReferenceFormat

Output formats for reference rendering.

```python
class ReferenceFormat(str, Enum):
    LATEX = "latex"          # LaTeX markup for PDF generation
    HTML = "html"            # HTML markup for web output
    MARKDOWN = "markdown"    # Markdown format
    PLAIN_TEXT = "plain_text" # Plain text representation
```

## Parser and Resolver Interfaces

### Abstract Class: ReferenceParser[T]

Base class for extracting references from text.

```python
class ReferenceParser[T](ABC):
    """Abstract base class for extracting references from text."""

    @abstractmethod
    def extract_references(
        self, text: str, context: BaseContext | None = None
    ) -> list[Reference[T]]:
        """Extract all references of type T from the given text."""

    @abstractmethod
    def can_parse(self, text: str) -> bool:
        """Check if this parser can handle the given text."""

    @property
    @abstractmethod
    def supported_content_type(self) -> type[T]:
        """The content type this parser handles."""
```

### Abstract Class: ReferenceResolver[T]

Base class for resolving references to actual content.

```python
class ReferenceResolver[T](ABC):
    """Abstract base class for resolving references to actual content."""

    @abstractmethod
    def resolve(
        self, ref: Reference[T], context: BaseContext | None = None
    ) -> T | None:
        """Resolve reference to actual content object."""

    @abstractmethod
    def format_reference(
        self,
        ref: Reference[T],
        format_type: ReferenceFormat,
        resolved_content: T | None = None,
        context: BaseContext | None = None
    ) -> str:
        """Format reference for output in the specified format."""

    @property
    @abstractmethod
    def supported_content_type(self) -> type[T]:
        """The content type this resolver handles."""
```

### Class: ReferenceManager

Unified manager for parsing, resolving, and formatting references.

```python
class ReferenceManager:
    """Unified manager for reference operations."""

    def __init__(self, cache_size: int = 1000):
        """Initialize with optional cache size."""

    def register_parser(self, parser: ReferenceParser[T]) -> None:
        """Register a reference parser."""

    def register_resolver(self, resolver: ReferenceResolver[T]) -> None:
        """Register a reference resolver."""

    def parse_references(
        self, text: str, context: BaseContext | None = None
    ) -> list[Reference]:
        """Parse all references from text using registered parsers."""

    def resolve_reference[U](
        self, ref: Reference[U], context: BaseContext | None = None
    ) -> U | None:
        """Resolve a single reference to its content."""

    def format_reference[U](
        self,
        ref: Reference[U],
        format_type: ReferenceFormat,
        context: BaseContext | None = None
    ) -> str:
        """Format a reference for output."""

    def resolve_and_format(
        self,
        text: str,
        format_type: ReferenceFormat,
        context: BaseContext | None = None
    ) -> str:
        """Parse, resolve, and format all references in text."""
```

## Usage Examples

### Creating and Using Contexts

```python
from dnd5e.core.base_context import ProcessingContext, ServiceContext
from dnd5e.core.models.spells import Spell

# Create a type-safe processing context
spell = Spell(name="Fireball", level=3)
context = ProcessingContext[Spell](
    content=spell,
    content_type_name="spell",
    source_file="spells.json",
    processing_options={"validate_components": True}
)

# Create a service context with dependencies
service_context = ServiceContext(
    omnidexer=my_omnidexer,
    config=my_latex_config,
    tag_resolver=my_tag_resolver
)
```

### Working with References

```python
from dnd5e.core.unified_references import Reference, ReferenceManager, ReferenceFormat
from dnd5e.core.models.spells import Spell

# Create a type-safe reference
spell_ref = Reference(
    source="@spell{fireball}",
    target="fireball",
    content_type=Spell,
    display_text="the fireball spell"
)

# Set up reference management
manager = ReferenceManager()
manager.register_parser(SpellReferenceParser())
manager.register_resolver(SpellReferenceResolver())

# Parse and resolve references in text
text = "Cast @spell{fireball} for massive damage!"
formatted = manager.resolve_and_format(text, ReferenceFormat.LATEX)
# Result: "Cast \\hyperref[spell:fireball]{the fireball spell} for massive damage!"
```

### Custom Reference Implementations

```python
class CreatureReferenceParser(ReferenceParser[Creature]):
    """Parser for creature references in text."""

    def extract_references(self, text: str, context: BaseContext | None = None) -> list[Reference[Creature]]:
        # Extract @creature{name} patterns
        matches = re.findall(r'@creature\{([^}]+)\}', text)
        return [
            Reference(
                source=f"@creature{{{match}}}",
                target=match,
                content_type=Creature,
                reference_type=ReferenceType.CONTENT
            )
            for match in matches
        ]

    def can_parse(self, text: str) -> bool:
        return "@creature{" in text

    @property
    def supported_content_type(self) -> type[Creature]:
        return Creature

class CreatureReferenceResolver(ReferenceResolver[Creature]):
    """Resolver for creature references."""

    def __init__(self, omnidexer: Omnidexer):
        self.omnidexer = omnidexer

    def resolve(self, ref: Reference[Creature], context: BaseContext | None = None) -> Creature | None:
        return self.omnidexer.find(ContentType.CREATURE, ref.target)

    def format_reference(
        self,
        ref: Reference[Creature],
        format_type: ReferenceFormat,
        resolved_content: Creature | None = None,
        context: BaseContext | None = None
    ) -> str:
        display = ref.display_text or ref.target

        if format_type == ReferenceFormat.LATEX:
            return f"\\hyperref[creature:{ref.target}]{{{display}}}"
        elif format_type == ReferenceFormat.MARKDOWN:
            return f"[{display}](#{ref.target})"
        else:
            return display

    @property
    def supported_content_type(self) -> type[Creature]:
        return Creature
```

This unified system provides type safety, consistency, and extensibility across all context and reference operations in 5e2pdf.

# System Components

This guide provides a concise overview of 5e2pdf's major components. For implementation details, see the API reference.

## Core Architecture

### Service Container
Central dependency injection system managing all services:
- **Location**: `dnd5e.core.container`
- **Services**: Omnidexer, ContentMerger, TagResolver, SpellClassLookup, AppendixGenerator
- **Pattern**: Singleton with lazy initialization
- **Testing**: Use `reset_global_container()` between tests

### Result Pattern
Type-safe error handling throughout the system:
- **Location**: `dnd5e.core.result`
- **Types**: `Result[T, E]`, `Success[T]`, `Error[E]`
- **Usage**: Replace exceptions with explicit error returns
- **Operations**: `map()`, `and_then()`, `unwrap_or()`

## Content Pipeline

### 1. Loading (Omnidexer)
**Purpose**: Index and load 5etools JSON data
**Location**: `dnd5e.core.loaders.omnidexer`

```python
omnidexer = get_omnidexer()
omnidexer.load_all_data()
creatures = omnidexer.get_all_by_type("creature")
```

**Key Features**:
- Dual-file system (metadata + content)
- Deep indexing via `DeepIndexable` protocol
- LRU caching with TTL
- Source filtering and management

### 2. Content Resolution
**Purpose**: Resolve references and build complete content
**Location**: `dnd5e.core.resolvers.content_resolver`

```python
resolver = ContentResolver(omnidexer)
result = resolver.resolve_adventure("LMoP")
if result.is_success:
    adventure = result.content
```

**Key Features**:
- Handles cross-references
- Builds complete content trees
- Tracks dependencies

### 3. Tag Processing
**Purpose**: Parse and render 5etools tags
**Location**: `dnd5e.core.text.tag_parser`, `tag_resolver`

```python
tag_resolver = get_tag_resolver()
rendered = tag_resolver.resolve("{@creature goblin}")
```

**Components**:
- **Parser**: Lark-based AST generation
- **Handlers**: Tag-specific processors (13+ types)
- **Enhancers**: Multi-stage formatting pipeline
- **Grammar**: `tag_grammar.lark` defines syntax

### 4. Entry Processing
**Purpose**: Process recursive entry structures
**Location**: `dnd5e.renderers.latex.entry_processor`

```python
processor = RecursiveEntryProcessor()
latex = processor.process_entries(entries, context)
```

**Handles**:
- Recursive entry structures
- Type-specific rendering
- Tag resolution
- Content tracking

### 5. Document Rendering
**Purpose**: Generate complete LaTeX documents
**Location**: `dnd5e.renderers.latex.document`

```python
renderer = LaTeXDocumentRenderer()
latex = renderer.render_document(content, context)
```

**Features**:
- Template-based generation
- Appendix creation
- Cross-reference management
- Progress tracking

## Specialized Systems

### Configuration
**Location**: `dnd5e.core.config.unified_config`
**Pattern**: Hierarchical Pydantic models
**Access**: `get_app_config()`
**Environment**: `DND5E_*` variables

### Entry Types
**Location**: `dnd5e.core.models.entry_types`
**Purpose**: Type-safe entry models
**Factory**: `create_entry(type, data)`
**Types**: 13+ specialized Pydantic models

### Image Processing
**Location**: `dnd5e.renderers.latex.images`
**Pipeline**:
1. FormatConverter: WebP→PNG
2. ImageOptimizer: Size/quality
3. ImagePlacer: LaTeX placement
4. ImageProcessor: Orchestration

### Error Tracking
**Location**: `dnd5e.core.validation.error_tracker`
**Purpose**: Collect validation errors
**Modes**: Strict, liberal, minimal
**Integration**: Result pattern

### Content Tracking
**Location**: `dnd5e.core.references.content_tracker`
**Purpose**: Track referenced content
**Usage**: Appendix generation
**Export**: `export_for_appendix()`

## Data Flow

```mermaid
graph LR
    JSON[5etools JSON] --> O[Omnidexer]
    O --> CR[ContentResolver]
    CR --> EP[EntryProcessor]
    EP --> TR[TagResolver]
    TR --> DR[DocumentRenderer]
    DR --> LaTeX[LaTeX Output]
    LaTeX --> PDF[PDF]
```

## Testing Patterns

### Unit Tests
```python
def setup_method(self):
    reset_test_environment()
    reset_global_container()
```

### Integration Tests
```python
@pytest.mark.needs_data
def test_with_real_data(test_data_omnidexer):
    # Uses fixture with real 5etools data
    pass
```

### Performance Tests
```python
@pytest.mark.benchmark
def test_performance(benchmark):
    result = benchmark(function_to_test)
```

## Extension Points

### Custom Tag Handlers
Implement `TagHandler` protocol:
```python
class CustomHandler(TagHandler):
    def can_handle(self, tag_type: str) -> bool:
        return tag_type == "custom"

    def handle(self, node: TagNode, context: RenderingContext) -> str:
        return f"Custom: {node.name}"
```

### Custom Entry Types
Extend `BaseEntry`:
```python
class CustomEntry(BaseEntry):
    type: Literal["custom"] = "custom"
    custom_field: str
```

### Custom Enhancers
Implement `Enhancer` protocol:
```python
class CustomEnhancer(Enhancer):
    def enhance(self, content: str, context: RenderingContext) -> str:
        return content.replace("old", "new")
```

## Performance Considerations

### Caching
- Omnidexer: LRU cache with TTL
- ContentMerger: In-memory cache
- TagResolver: Result caching

### Lazy Loading
- Service container: On-demand initialization
- Omnidexer: Load only requested types
- Deep indexing: Index on access

### Batch Processing
- `collect_results()`: Process multiple items
- Error tracking: Batch validation
- Content tracking: Deferred resolution

## Common Pitfalls

1. **Global State**: Always reset between tests
2. **Tag Recursion**: Use max depth limits
3. **Memory Usage**: Clear caches periodically
4. **File Paths**: Use absolute paths
5. **Parallel Tests**: Ensure proper isolation

## Quick Reference

| Component | Location | Purpose |
|-----------|----------|---------|
| Omnidexer | `core.loaders.omnidexer` | Content loading |
| ContentResolver | `core.resolvers` | Reference resolution |
| TagResolver | `core.text.tag_resolver` | Tag processing |
| EntryProcessor | `renderers.latex.entry_processor` | Entry rendering |
| DocumentRenderer | `renderers.latex.document` | Document generation |
| ServiceContainer | `core.container` | Dependency injection |
| Result | `core.result` | Error handling |
| ContentTracker | `core.references.content_tracker` | Appendix tracking |

## See Also

- [Architecture Overview](architecture-overview.md) - High-level system design
- [API Reference](/library-reference/api/index.md) - Detailed API documentation
- [Entry System Guide](entry-system-guide.md) - Entry processing details
- [Performance Optimization](/developer/performance-optimization.md) - Performance tuning

# Tag Processing and Cross-References

Systems for tag processing, content indexing, and cross-referencing.

## Tag System Architecture

The tag system uses a unified architecture with clear separation of concerns:

- **Text Processing** (`src/dnd5e/core/text/`) - Parse 5etools tags into AST
- **Core Handlers** (`src/dnd5e/renderers/core/`) - Extract structured information
- **Enhancement Pipeline** - Apply format-specific presentation
- **Content Indexing** (`src/dnd5e/core/indexer/`) - Cross-references and content tracking

For comprehensive architecture details, see the [Tag System Architecture Guide](../developer/system-guide/component-deep-dives/tag-system-architecture.md).

## Tag Parser

AST-based parsing of 5etools tag syntax with Lark grammar.

```{eval-rst}
.. automodule:: dnd5e.core.text.tag_parser
   :members:
   :undoc-members:
   :show-inheritance:
```

**Example Usage:**

```python
from dnd5e.core.text.tag_parser import TagParser

# Parse 5etools tags into AST
parser = TagParser()
ast = parser.parse("The {@spell fireball|PHB} spell deals {@dice 8d6} fire damage.")

# AST contains typed nodes for each tag
for node in ast.children:
    if hasattr(node, 'tag_type'):
        print(f"Tag: {node.tag_type}, Name: {node.name}")
```

## Tag Resolver

Text processing integration that resolves tags within document content.

```{eval-rst}
.. automodule:: dnd5e.core.text.tag_resolver
   :members:
   :undoc-members:
   :show-inheritance:
```

**Example Usage:**

```python
from dnd5e.core.text.tag_resolver import TagResolver
from dnd5e.renderers.core.interfaces import RenderingContext

# Setup resolver with context
resolver = TagResolver()
context = RenderingContext(
    output_format="latex",
    omnidexer=my_omnidexer
)

# Process text with tags
text = "Cast {@spell fireball} for {@dice 8d6} fire damage."
processed = resolver.resolve_tags(text, context)
print(processed)  # "Cast \hyperref[spell:fireball]{\textit{fireball}} for 8d6 fire damage."
```

## Core Tag Handlers

Business logic handlers for different tag types.

```{eval-rst}
.. automodule:: dnd5e.renderers.core.handlers
   :members:
   :undoc-members:
   :show-inheritance:
```

## Reference Index

```{eval-rst}
.. automodule:: dnd5e.core.indexer.reference_index
   :members:
   :undoc-members:
   :show-inheritance:
```

## Supported Tag Types

The tag system processes 5etools tags with full support for content references, formatting, and game mechanics:

### Content Reference Tags

| Tag Type | Syntax | Example | Description |
|----------|--------|---------|-------------|
| Spell | `{@spell name\|source\|display\|page}` | `{@spell fireball\|PHB\|the fireball spell\|241}` | Spell reference (italic) |
| Creature | `{@creature name\|source\|display\|page}` | `{@creature goblin\|MM\|Goblin Warrior\|166}` | Creature reference (bold) |
| Item | `{@item name\|source\|display\|page}` | `{@item longsword\|PHB\|magic sword\|149}` | Item reference (italic) |
| Class | `{@class name\|source\|display\|page}` | `{@class wizard\|PHB\|Wizard\|112}` | Class reference (bold) |
| Feat | `{@feat name\|source\|display\|page}` | `{@feat alert\|PHB\|Alert\|165}` | Feat reference (bold) |
| Race | `{@race name\|source\|display\|page}` | `{@race elf\|PHB\|High Elf\|23}` | Race reference (plain) |
| Background | `{@background name\|source\|display\|page}` | `{@background acolyte\|PHB\|Acolyte\|127}` | Background reference (plain) |
| Condition | `{@condition name}` | `{@condition charmed}` | Condition reference (italic) |
| Adventure | `{@adventure display\|source\|page}` | `{@adventure Lost Mine of Phandelver\|Starter Set\|1}` | Adventure reference |
| Book | `{@book display\|source\|page}` | `{@book Player's Handbook\|PHB\|1}` | Book reference |

### Formatting Tags

| Tag Type | Syntax | Example | Description |
|----------|--------|---------|-------------|
| Italic | `{@i text}` | `{@i emphasis}` | Italic formatting |
| Bold | `{@b text}` | `{@b important}` | Bold formatting |
| Code | `{@code text}` | `{@code function()}` | Monospace formatting |
| Typewriter | `{@tt text}` | `{@tt literal}` | Typewriter formatting |

### Game Mechanics Tags

| Tag Type | Syntax | Example | Description |
|----------|--------|---------|-------------|
| Dice | `{@dice expression}` | `{@dice 2d6+3}` | Dice expression |
| DC | `{@dc value}` | `{@dc 15}` | Difficulty Class |

### Advanced Tag Features

#### Nested Formatting

The tag system supports complex nested formatting:

```
{@i {@b important italic text}}     # Italic bold text
{@b Casting {@i fireball}}           # Bold with italic word
{@code {@spell fireball}}            # Code-formatted spell reference
```

#### Parameter Structure

Most content tags follow a consistent 4-parameter structure:

1. **Name** (required): Content identifier
2. **Source** (optional): Source book abbreviation
3. **Display Text** (optional): Custom display text
4. **Page** (optional): Page number reference

```
{@spell fireball|PHB|the fireball spell|241}
{@creature goblin|MM}                         # Minimal form
{@item longsword}                             # Name only
```

#### Content Validation

Tags are validated against the omnidexer content database:

- **Valid references**: Generate hyperlinks and proper formatting
- **Invalid references**: Show warnings in debug mode, render as plain text
- **Missing content**: Graceful fallback with original text

#### Processing Pipeline

1. **Parsing**: Text with tags → AST nodes
2. **Handler Selection**: Tag type → CoreTagHandler
3. **Information Extraction**: AST → ContentReferenceInfo
4. **Enhancement**: Multi-stage presentation formatting
5. **Output**: Final formatted text (LaTeX, HTML, etc.)

## Performance and Debugging

### Debug Mode

Enable debug mode to see detailed tag processing information:

```python
context = RenderingContext(
    output_format="latex",
    debug_mode=True,
    omnidexer=my_omnidexer
)

# Process tags with debug output
result = resolver.resolve_tags(text, context)
# Shows: parsing time, handler selection, validation warnings
```

### Performance Optimization

- **Parser Caching**: AST nodes cached by input text hash
- **Handler Caching**: ContentReferenceInfo cached per node type
- **Service Reuse**: Omnidexer and other services shared across processing
- **Batch Processing**: Multiple tags processed efficiently together

## Integration Points

The tag system integrates seamlessly with:

- **Document Rendering**: LaTeX document generation with automatic tag processing
- **CLI Commands**: `uv run 5e2pdf convert adventure "CoS"` processes all tags automatically
- **Service Container**: Dependency injection provides omnidexer and content tracker
- **Content Tracking**: Tags automatically registered for appendix generation

For comprehensive implementation details, see the [Tag System Architecture Guide](../developer/system-guide/component-deep-dives/tag-system-architecture.md).

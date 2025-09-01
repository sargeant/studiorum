# Understanding the 5etools Entry System

The entry system is the heart of 5e2pdf's content processing. This guide explains how 5etools structures its data and how we process it.

## What Are Entries?

In 5etools, an "entry" is the fundamental unit of content. Entries can be:

- **Simple strings**: Plain text content
- **Rich objects**: Structured data with type, content, and metadata
- **Nested structures**: Entries containing other entries (recursive)

## Entry Types Overview

### Basic Entry Structure

```python
# Simple string entry
entry = "This is a simple text entry"

# Typed entry object
entry = {
    "type": "entries",
    "name": "Combat",
    "entries": [
        "When combat starts...",
        "Roll initiative by..."
    ]
}
```

### Common Entry Types

| Type | Purpose | Structure |
|------|---------|-----------|
| `entries` | Generic container | `{"type": "entries", "name": "...", "entries": [...]}` |
| `list` | Bullet/numbered lists | `{"type": "list", "items": [...]}` |
| `table` | Tabular data | `{"type": "table", "caption": "...", "colLabels": [...], "rows": [...]}` |
| `inset` | Sidebar/callout box | `{"type": "inset", "name": "...", "entries": [...]}` |
| `insetReadaloud` | Read-aloud text box | `{"type": "insetReadaloud", "entries": [...]}` |
| `quote` | Quoted text | `{"type": "quote", "entries": [...], "by": "..."}` |
| `image` | Images | `{"type": "image", "href": {...}}` |
| `abilityDc` | Save DC notation | `{"type": "abilityDc", "name": "...", "attributes": [...]}` |
| `abilityAttackMod` | Attack modifier | `{"type": "abilityAttackMod", "name": "...", "attributes": [...]}` |

## The Tag System

5etools uses tags to create cross-references and format content. Tags use the `{@tag ...}` syntax.

### Common Tags

```text
{@creature goblin}           # Link to a creature
{@spell magic missile}       # Link to a spell
{@item longsword}           # Link to an item
{@b bold text}              # Bold formatting
{@i italic text}            # Italic formatting
{@dice 1d20+5}              # Dice notation
{@damage 2d6}               # Damage notation
{@dc 15}                    # Difficulty class
{@skill Athletics}          # Skill reference
{@condition poisoned}        # Condition reference
```

### Tag Processing

Tags are processed by the `TagResolver` using an AST-based parser:

```python
from dnd5e.core.text.tag_parser import TagParser

parser = TagParser()
result = parser.parse("{@creature goblin|goblins}")
# Results in a CreatureNode with name="goblin" and display_text="goblins"
```

## Recursive Processing

Entries are recursive - they can contain other entries. The `RecursiveEntryProcessor` handles this:

```python
from dnd5e.renderers.latex.entry_processor import RecursiveEntryProcessor

processor = RecursiveEntryProcessor()

# Process a complex nested structure
entry = {
    "type": "entries",
    "name": "Chapter 1",
    "entries": [
        "Introduction text with {@creature goblin} reference.",
        {
            "type": "list",
            "items": [
                "First item",
                "Second item with {@spell magic missile}"
            ]
        }
    ]
}

latex_output = processor.process(entry, context)
```

## Entry Creation Factory

Use the `create_entry()` factory for type-safe entry creation:

```python
from dnd5e.core.entry_factory import create_entry

# Create a simple text entry
text_entry = create_entry("Simple text")

# Create a typed entry
list_entry = create_entry({
    "type": "list",
    "items": ["Item 1", "Item 2"]
})

# The factory handles validation and type conversion
```

## Real-World Example

Here's how a spell entry looks in 5etools data:

```json
{
    "name": "Fireball",
    "level": 3,
    "school": "V",
    "time": [{"number": 1, "unit": "action"}],
    "range": {"type": "point", "distance": {"type": "feet", "amount": 150}},
    "components": {"v": true, "s": true, "m": "a tiny ball of bat guano"},
    "duration": [{"type": "instant"}],
    "entries": [
        "A bright streak flashes from your pointing finger...",
        "Each creature in a 20-foot-radius sphere...",
        {
            "type": "entries",
            "name": "At Higher Levels",
            "entries": [
                "When you cast this spell using a spell slot of 4th level or higher..."
            ]
        }
    ]
}
```

## Processing Pipeline

1. **Load**: Raw JSON data from 5etools
2. **Parse**: Convert to Python dictionaries
3. **Validate**: Check structure with Pydantic models
4. **Process**: Recursive entry processing with tag resolution
5. **Render**: Convert to target format (LaTeX, HTML, etc.)

```python
# Complete pipeline example
from dnd5e.core.loaders.omnidexer import Omnidexer
from dnd5e.renderers.latex.entry_processor import RecursiveEntryProcessor
from dnd5e.renderers.core.interfaces import RenderingContext

# Load data
omnidexer = Omnidexer()
omnidexer.load_all_data()

# Get content
spell = omnidexer.get_by_name("spell", "fireball")

# Create context
context = RenderingContext(
    output_format="latex",
    omnidexer=omnidexer,
    metadata={}
)

# Process entries
processor = RecursiveEntryProcessor()
latex_output = processor.process(spell.entries, context)
```

## Advanced Entry Types

### Tables with Special Features

```python
table_entry = {
    "type": "table",
    "caption": "Random Encounters",
    "colLabels": ["d20", "Encounter"],
    "colStyles": ["text-center", "text-left"],
    "rows": [
        ["1-5", "No encounter"],
        ["6-10", "{@creature goblin|2d4 goblins}"],
        ["11-15", "{@creature wolf|1d6 wolves}"]
    ]
}
```

### Nested Insets

```python
inset_entry = {
    "type": "inset",
    "name": "Sidebar: Magic Items",
    "entries": [
        "Magic items in this adventure:",
        {
            "type": "list",
            "items": [
                "{@item bag of holding}",
                "{@item +1 weapon||+1 longsword}"
            ]
        }
    ]
}
```

## Debugging Entry Processing

### Enable Debug Mode

```bash
# Show detailed entry processing
export DND5E_DEBUG_ENTRY_PROCESSING=1

# Strict mode - fail on unknown entry types
export DND5E_STRICT_ENTRY_PROCESSING=1

# Disable tag fallback (show raw tags on error)
export DND5E_DISABLE_TAG_FALLBACK=1
```

### Common Issues

1. **Unknown Entry Type**: Check if it's implemented in `RecursiveEntryProcessor`
2. **Tag Resolution Fails**: Verify the referenced content exists
3. **Nested Entries Lost**: Ensure recursive processing is enabled
4. **Formatting Issues**: Check LaTeX escaping in tag resolver

## Best Practices

1. **Always Use the Factory**: `create_entry()` provides validation
2. **Handle Unknown Types**: Implement fallback for new entry types
3. **Preserve Structure**: Don't flatten nested entries unnecessarily
4. **Track References**: Use `ContentTracker` for appendix generation
5. **Test Recursively**: Entry structures can be deeply nested

## Extending the Entry System

To add a new entry type:

1. Define the structure in `src/dnd5e/core/models/entry.py`
2. Add processing in `RecursiveEntryProcessor._process_typed_entry()`
3. Create LaTeX template if needed
4. Add tests with real 5etools data
5. Document the new type here

## Related Documentation

- [Advanced Entry System Guide](entry-system-advanced.md) - Complex patterns and optimization
- [System Components](components.md) - Overview of all major components
- [RecursiveEntryProcessor API](../../library-reference/renderers.md#recursive-entry-processor)

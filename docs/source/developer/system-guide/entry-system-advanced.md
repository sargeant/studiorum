# Advanced Entry System Guide

This guide covers advanced topics in the 5etools entry system, including complex patterns, performance optimization, and edge cases.

## Complex Entry Patterns

### Conditional Entries

Some entries contain conditional content based on context:

```python
# Scaling spell entries
scaling_entry = {
    "type": "entries",
    "name": "At Higher Levels",
    "entries": [
        "When you cast this spell using a spell slot of {0} level or higher, "
        "the damage increases by {@damage 1d6} for each slot level above {1}."
    ]
}

# Variant entries
variant_entry = {
    "type": "entries",
    "name": "Variant: Spell Points",
    "entries": [
        "Instead of spell slots, you can use spell points...",
        {
            "type": "table",
            "caption": "Spell Point Cost",
            "colLabels": ["Spell Level", "Point Cost"],
            "rows": [
                ["1st", "2"],
                ["2nd", "3"],
                ["3rd", "5"]
            ]
        }
    ]
}
```

### Deep Nesting Patterns

Adventures often have deeply nested structures:

```python
adventure_chapter = {
    "type": "entries",
    "name": "Chapter 1: Goblin Arrows",
    "id": "001",
    "entries": [
        {
            "type": "entries",
            "name": "Part 1: Ambush",
            "entries": [
                "Read the following:",
                {
                    "type": "insetReadaloud",
                    "entries": [
                        "The road winds through rocky terrain..."
                    ]
                },
                {
                    "type": "entries",
                    "name": "Goblin Tactics",
                    "entries": [
                        "The {@creature goblin|goblins} attack from hiding...",
                        {
                            "type": "list",
                            "items": [
                                "They focus fire on spellcasters",
                                "Use bonus action to hide",
                                "Retreat when reduced to half numbers"
                            ]
                        }
                    ]
                }
            ]
        }
    ]
}
```

## Performance Optimization

### Entry Caching Strategies

```python
from functools import lru_cache
from dnd5e.renderers.latex.entry_processor import RecursiveEntryProcessor

class OptimizedEntryProcessor(RecursiveEntryProcessor):
    @lru_cache(maxsize=1024)
    def _process_cached_string(self, text: str, context_hash: int) -> str:
        """Cache processed strings with tags."""
        return self._process_text_with_tags(text, self._rebuild_context(context_hash))

    def process_entry(self, entry, context):
        if isinstance(entry, str):
            # Hash the context for cache key
            context_hash = self._hash_context(context)
            return self._process_cached_string(entry, context_hash)
        return super().process_entry(entry, context)
```

### Batch Processing

For large documents like adventures:

```python
class BatchEntryProcessor:
    def __init__(self):
        self.tag_cache = {}
        self.content_tracker = ContentTracker()

    def process_batch(self, entries: List, context: RenderingContext):
        """Process multiple entries with shared cache."""
        # Pre-populate tag cache
        self._preload_references(entries)

        results = []
        for entry in entries:
            result = self._process_with_cache(entry, context)
            results.append(result)

        return results

    def _preload_references(self, entries):
        """Extract and preload all tag references."""
        tags = self._extract_all_tags(entries)
        for tag in tags:
            self.tag_cache[tag] = self._resolve_tag(tag)
```

## Edge Cases and Solutions

### Circular References

```python
# Problem: Spell A references Spell B which references Spell A
spell_a = {
    "name": "Counterspell",
    "entries": ["...can counter {@spell dispel magic}..."]
}

spell_b = {
    "name": "Dispel Magic",
    "entries": ["...similar to {@spell counterspell}..."]
}

# Solution: Track resolution depth
class CircularSafeResolver:
    def __init__(self, max_depth=3):
        self.max_depth = max_depth
        self.resolution_stack = []

    def resolve_tag(self, tag, context):
        if tag in self.resolution_stack:
            return f"[{tag}]"  # Fallback for circular ref

        if len(self.resolution_stack) >= self.max_depth:
            return f"[{tag}]"  # Max depth reached

        self.resolution_stack.append(tag)
        try:
            return self._do_resolve(tag, context)
        finally:
            self.resolution_stack.pop()
```

### Malformed Entry Recovery

```python
def safe_process_entry(entry, context):
    """Process entry with fallback for malformed data."""
    try:
        if isinstance(entry, dict):
            if "type" not in entry:
                # Infer type from structure
                if "items" in entry:
                    entry["type"] = "list"
                elif "rows" in entry:
                    entry["type"] = "table"
                else:
                    entry["type"] = "entries"

            return process_typed_entry(entry, context)

        return process_string_entry(entry, context)

    except Exception as e:
        # Log error and return safe fallback
        logger.warning(f"Failed to process entry: {e}")
        return "\\textit{[Content processing error]}"
```

## Custom Entry Types

### Creating Domain-Specific Entries

```python
# Custom entry type for homebrew content
class HomebrewEntry:
    type = "homebrew"

    def __init__(self, data):
        self.author = data.get("author", "Unknown")
        self.content = data.get("entries", [])
        self.source = data.get("source", "HB")

    def to_latex(self, context):
        return f"""
\\begin{{homebrewbox}}
\\textbf{{Homebrew by {self.author}}}\\\\
{self._process_content(self.content, context)}
\\end{{homebrewbox}}
"""

# Register custom type
ENTRY_PROCESSORS["homebrew"] = HomebrewEntry
```

### Entry Type Discovery

```python
def discover_entry_types(data_path: Path) -> Set[str]:
    """Scan 5etools data to discover all entry types."""
    entry_types = set()

    def scan_entries(obj):
        if isinstance(obj, dict):
            if "type" in obj:
                entry_types.add(obj["type"])
            for value in obj.values():
                scan_entries(value)
        elif isinstance(obj, list):
            for item in obj:
                scan_entries(item)

    for file in data_path.glob("**/*.json"):
        with open(file) as f:
            data = json.load(f)
            scan_entries(data)

    return entry_types
```

## Entry Validation

### Schema Validation

```python
from pydantic import BaseModel, Field, validator

class EntrySchema(BaseModel):
    type: str
    name: Optional[str] = None
    entries: Optional[List[Union[str, dict]]] = None

    @validator("type")
    def validate_type(cls, v):
        known_types = {"entries", "list", "table", "inset", ...}
        if v not in known_types:
            logger.warning(f"Unknown entry type: {v}")
        return v

    @validator("entries")
    def validate_recursive(cls, v):
        if v:
            for entry in v:
                if isinstance(entry, dict):
                    EntrySchema(**entry)  # Recursive validation
        return v
```

### Content Validation

```python
def validate_entry_references(entry, omnidexer):
    """Validate that all tag references exist."""
    issues = []

    def check_tags(text):
        if not isinstance(text, str):
            return

        tags = re.findall(r'{@(\w+) ([^}]+)}', text)
        for tag_type, reference in tags:
            if tag_type in ["creature", "spell", "item"]:
                if not omnidexer.exists(tag_type, reference):
                    issues.append(f"Missing {tag_type}: {reference}")

    def scan_entry(e):
        if isinstance(e, str):
            check_tags(e)
        elif isinstance(e, dict):
            for value in e.values():
                scan_entry(value)
        elif isinstance(e, list):
            for item in e:
                scan_entry(item)

    scan_entry(entry)
    return issues
```

## Entry Transformation

### Cross-Format Conversion

```python
class EntryConverter:
    """Convert entries between formats."""

    def to_markdown(self, entry):
        """Convert entry to Markdown."""
        if isinstance(entry, str):
            return self._tags_to_markdown(entry)

        if entry.get("type") == "entries":
            lines = [f"## {entry.get('name', '')}", ""]
            for e in entry.get("entries", []):
                lines.append(self.to_markdown(e))
            return "\n".join(lines)

        if entry.get("type") == "list":
            lines = []
            for item in entry.get("items", []):
                lines.append(f"- {self.to_markdown(item)}")
            return "\n".join(lines)

        # ... other types

    def to_html(self, entry):
        """Convert entry to HTML."""
        # Similar pattern for HTML
        pass
```

### Entry Merging

```python
def merge_entries(base_entry, override_entry):
    """Merge two entries, with override taking precedence."""
    if isinstance(base_entry, str):
        return override_entry

    if not isinstance(base_entry, dict) or not isinstance(override_entry, dict):
        return override_entry

    merged = base_entry.copy()

    for key, value in override_entry.items():
        if key == "entries" and key in merged:
            # Merge entry lists
            merged[key] = merged[key] + value
        else:
            merged[key] = value

    return merged
```

## Memory Management

### Entry Streaming

For very large documents:

```python
class StreamingEntryProcessor:
    """Process entries in streaming fashion to reduce memory."""

    def process_stream(self, entry_generator, context):
        """Process entries one at a time."""
        for entry in entry_generator:
            result = self.process_single(entry, context)
            yield result
            # Clear caches periodically
            if self.processed_count % 100 == 0:
                self.clear_caches()

    def process_file(self, filepath, context):
        """Stream process a large JSON file."""
        with open(filepath) as f:
            data = ijson.items(f, 'entries.item')
            for result in self.process_stream(data, context):
                yield result
```

## Testing Entry Processing

### Property-Based Testing

```python
from hypothesis import given, strategies as st

# Generate random valid entries
entry_strategy = st.recursive(
    st.one_of(
        st.text(),
        st.dictionaries(
            st.just("type"), st.just("entries"),
            min_size=1
        )
    ),
    lambda children: st.dictionaries(
        st.sampled_from(["type", "name", "entries"]),
        st.one_of(st.text(), children, st.lists(children))
    )
)

@given(entry_strategy)
def test_entry_processing_never_crashes(entry):
    """Entry processor should handle any valid structure."""
    processor = RecursiveEntryProcessor()
    context = create_test_context()

    try:
        result = processor.process(entry, context)
        assert result is not None
        assert isinstance(result, str)
    except KnownEntryError:
        pass  # Known limitations are OK
```

### Regression Testing

```python
def create_entry_regression_tests():
    """Generate tests from real 5etools data."""
    test_cases = []

    for file in Path("data").glob("**/*.json"):
        with open(file) as f:
            data = json.load(f)

        # Extract entries
        entries = extract_all_entries(data)

        for i, entry in enumerate(entries[:10]):  # Sample
            test_cases.append({
                "name": f"{file.stem}_{i}",
                "input": entry,
                "expected": process_entry(entry)  # Current output
            })

    # Save for regression testing
    with open("test_entries.json", "w") as f:
        json.dump(test_cases, f, indent=2)
```

## Debugging Tools

### Entry Inspector

```python
class EntryInspector:
    """Debug tool for analyzing entry structures."""

    def inspect(self, entry, max_depth=3):
        """Print entry structure."""
        self._inspect_recursive(entry, 0, max_depth)

    def _inspect_recursive(self, entry, depth, max_depth):
        indent = "  " * depth

        if depth >= max_depth:
            print(f"{indent}...")
            return

        if isinstance(entry, str):
            preview = entry[:50] + "..." if len(entry) > 50 else entry
            print(f"{indent}STR: {preview}")

        elif isinstance(entry, dict):
            print(f"{indent}DICT[{entry.get('type', 'untyped')}]:")
            for key, value in entry.items():
                print(f"{indent}  {key}:")
                self._inspect_recursive(value, depth + 2, max_depth)

        elif isinstance(entry, list):
            print(f"{indent}LIST[{len(entry)}]:")
            for i, item in enumerate(entry[:3]):  # First 3 items
                print(f"{indent}  [{i}]:")
                self._inspect_recursive(item, depth + 2, max_depth)
            if len(entry) > 3:
                print(f"{indent}  ... +{len(entry) - 3} more")
```

### Entry Profiler

```python
import cProfile
import pstats

def profile_entry_processing(entry, context):
    """Profile entry processing performance."""
    profiler = cProfile.Profile()

    profiler.enable()
    result = process_entry(entry, context)
    profiler.disable()

    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(20)  # Top 20 functions

    return result
```

## Best Practices Summary

1. **Cache aggressively** - Entry processing is often repeated
2. **Validate early** - Catch malformed entries at load time
3. **Stream when possible** - Don't load entire adventures into memory
4. **Test with real data** - 5etools data has many edge cases
5. **Profile regularly** - Entry processing is a hot path
6. **Document new types** - Keep this guide updated
7. **Handle errors gracefully** - Never crash on bad entries

## See Also

- {doc}`entry-system-guide` - Basic entry system guide
- {doc}`component-deep-dives/tag-system-architecture` - Tag processing details
- {doc}`/user-guide/troubleshooting` - Common entry issues
- {doc}`/library-reference/api/index` - Entry processor API

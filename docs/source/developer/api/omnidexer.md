# Omnidexer API Documentation

## Table of Contents

This page covers the Omnidexer API documentation with the following sections:

- Overview
- Class: Omnidexer
- Class: IndexEntry
- Protocol: DeepIndexable
- Functions and Utilities
- Configuration
- Performance Monitoring

## Overview

The Omnidexer provides a comprehensive content indexing and discovery system for D&D content. With deep indexing capabilities, it can discover and index nested content within complex data structures, making every piece of content searchable and cross-referenceable.

### Key Features

- **Multi-Index Architecture**: Hash, type, source, and name-based indexing
- **Deep Content Discovery**: Automatic indexing of nested content via DeepIndexable protocol
- **Cycle Prevention**: Intelligent duplicate detection and prevention
- **Performance Monitoring**: Built-in benchmarking and statistics
- **Type Safety**: Full mypy compliance with proper union types

## Class: Omnidexer

### Constructor

```python
def __init__(self, enable_deep_indexing: bool = True) -> None
```

Creates a new Omnidexer instance.

**Parameters:**
- `enable_deep_indexing` (bool): Whether to enable deep indexing of nested content. Defaults to `True`.

**Example:**
```python
# Enable deep indexing (default)
omnidexer = Omnidexer()

# Disable deep indexing for performance
omnidexer = Omnidexer(enable_deep_indexing=False)
```

### Core Methods

#### `load_all_data()`

```python
async def load_all_data(self) -> None
```

Loads all available D&D content from configured sources and indexes it.

**Raises:**
- `LoadingError`: If content loading fails
- `ValidationError`: If content validation fails

**Example:**
```python
omnidexer = Omnidexer()
await omnidexer.load_all_data()
print(f"Loaded {len(omnidexer._index)} items")
```

#### `find()`

```python
def find(
    self,
    content_type: ContentType,
    name: str,
    source: str
) -> BaseContent | None
```

Finds a specific content item by exact match.

**Parameters:**
- `content_type` (ContentType): The type of content to find
- `name` (str): Exact name of the content
- `source` (str): Source abbreviation (e.g., "PHB", "MM", "DMG")

**Returns:**
- `BaseContent | None`: The found content item, or None if not found

**Example:**
```python
# Find a spell
fireball = omnidexer.find(ContentType.SPELL, "Fireball", "PHB")

# Find a class feature (requires deep indexing)
action_surge = omnidexer.find(ContentType.CLASS_FEATURE, "Action Surge", "PHB")

# Find adventure content
cave_section = omnidexer.find(ContentType.ADVENTURE_SECTION, "The Goblin Cave", "LMoP")
```

#### `find_all()`

```python
def find_all(self, content_type: ContentType) -> list[BaseContent]
```

Finds all content items of a specific type.

**Parameters:**
- `content_type` (ContentType): The type of content to find

**Returns:**
- `list[BaseContent]`: List of all content items of the specified type

**Example:**
```python
# Get all spells
all_spells = omnidexer.find_all(ContentType.SPELL)

# Get all adventure sections (deep indexed content)
all_sections = omnidexer.find_all(ContentType.ADVENTURE_SECTION)

# Get all class features
all_features = omnidexer.find_all(ContentType.CLASS_FEATURE)
```

#### `find_by_source()`

```python
def find_by_source(self, source: str) -> list[BaseContent]
```

Finds all content from a specific source.

**Parameters:**
- `source` (str): Source abbreviation

**Returns:**
- `list[BaseContent]`: List of all content from the specified source

**Example:**
```python
# Get all content from Player's Handbook
phb_content = omnidexer.find_by_source("PHB")

# Get all content from Monster Manual
mm_content = omnidexer.find_by_source("MM")
```

#### `find_by_name()`

```python
def find_by_name(self, name: str) -> list[BaseContent]
```

Finds all content with a specific name (across all types and sources).

**Parameters:**
- `name` (str): Name to search for

**Returns:**
- `list[BaseContent]`: List of all content with the specified name

**Example:**
```python
# Find all content named "Fireball" (might include spell, magic item, etc.)
fireball_items = omnidexer.find_by_name("Fireball")
```

#### `find_by_hash()`

```python
def find_by_hash(self, hash_id: str) -> BaseContent | None
```

Finds content by its unique hash identifier.

**Parameters:**
- `hash_id` (str): Unique hash identifier

**Returns:**
- `BaseContent | None`: The content with the specified hash, or None if not found

**Example:**
```python
# Get hash from an IndexEntry
entry = omnidexer._index[hash_id]
content = omnidexer.find_by_hash(entry.hash_id)
```

### Advanced Methods

#### `get_content_types()`

```python
def get_content_types(self) -> set[ContentType]
```

Gets all content types currently indexed.

**Returns:**
- `set[ContentType]`: Set of all indexed content types

**Example:**
```python
types = omnidexer.get_content_types()
print(f"Indexed types: {[t.value for t in sorted(types)]}")
```

#### `get_sources()`

```python
def get_sources(self) -> set[str]
```

Gets all sources currently indexed.

**Returns:**
- `set[str]`: Set of all source abbreviations

**Example:**
```python
sources = omnidexer.get_sources()
print(f"Available sources: {sorted(sources)}")
```

#### `get_performance_stats()`

```python
def get_performance_stats(self) -> dict[str, any]
```

Gets performance statistics for the omnidexer.

**Returns:**
- `dict`: Dictionary containing performance metrics

**Example:**
```python
stats = omnidexer.get_performance_stats()
print(f"Total items: {stats['total_items']}")
print(f"Load time: {stats['load_time']:.2f}s")
print(f"Deep indexed items: {stats['deep_indexed_items']}")
```

### Properties

#### `total_items`

```python
@property
def total_items(self) -> int
```

Total number of indexed items.

#### `deep_indexing_enabled`

```python
@property
def deep_indexing_enabled(self) -> bool
```

Whether deep indexing is currently enabled.

#### `indexed_hashes`

```python
@property
def indexed_hashes(self) -> set[str]
```

Set of all hash IDs that have been indexed (for cycle prevention).

## Class: IndexEntry

**Pydantic BaseModel** representing an indexed content item with comprehensive validation.

*Migrated from dataclass to Pydantic BaseModel in Tier 3 migration for enhanced validation and type safety.*

### Constructor

```python
@classmethod
def create(
    cls,
    content: BaseContent,
    content_type: ContentType
) -> IndexEntry
```

Creates an IndexEntry for a content item with automatic hash and key generation.

**Parameters:**
- `content` (BaseContent): The content to index
- `content_type` (ContentType): Type of the content

**Returns:**
- `IndexEntry`: New index entry with validated fields

**Example:**
```python
# Create index entry for a spell
spell = Spell(name="Fireball", source="PHB", ...)
entry = IndexEntry.create(spell, ContentType.SPELL)
print(f"Hash: {entry.hash_id}")  # 8-character hash
print(f"Key: {entry.lookup_key}")  # "fireball|phb"
```

### Fields and Validation

#### `content: Any`

The indexed content object. Currently uses `Any` type with TODO to migrate to `BaseContent` once fully Pydantic.

**Validation:**
- Accepts any content object through `arbitrary_types_allowed` configuration

#### `content_type: ContentType`

Enum specifying the type of indexed content.

**Validation:**
- Must be a valid ContentType enum value

#### `hash_id: str`

Unique 8-character hash identifier for the content.

**Validation:**
- Exactly 8 characters (enforced by `min_length=8, max_length=8`)
- Must contain only alphanumeric characters
- Automatically converted to lowercase
- Generated using SHA256 hash of content identifier

**Generation Logic:**
```python
# Hash generation from content
identifier = f"{content_type.value}:{content.name}:{source_abbrev}"
hash_id = hashlib.sha256(identifier.encode()).hexdigest()[:8]
```

#### `lookup_key: str`

Normalized lookup key for case-insensitive searches.

**Validation:**
- Minimum length of 1 character
- Must contain '|' separator between name and source
- Automatically normalized to lowercase with stripped whitespace
- Format: `"{name}|{source}"`

**Example Values:**
```python
"fireball|phb"          # Spell from Player's Handbook
"action surge|phb"      # Class feature from PHB
"goblin|mm"            # Creature from Monster Manual
```

### Validation Features

#### Hash ID Validation

```python
@field_validator("hash_id")
@classmethod
def validate_hash_id(cls, v: str) -> str:
    """Validate hash ID format."""
    if not v.isalnum():
        raise ValueError("Hash ID must contain only alphanumeric characters")
    return v.lower()
```

**Benefits:**
- Ensures consistent lowercase format
- Prevents special characters that could cause lookup issues
- Guarantees alphanumeric-only identifiers

#### Lookup Key Validation

```python
@field_validator("lookup_key")
@classmethod
def validate_lookup_key(cls, v: str) -> str:
    """Validate and normalize lookup key."""
    normalized = v.strip().lower()
    if "|" not in normalized:
        raise ValueError(
            "Lookup key must contain '|' separator between name and source"
        )
    return normalized
```

**Benefits:**
- Enforces consistent format for search operations
- Automatic normalization prevents case-sensitivity issues
- Validates required separator for proper parsing

### Configuration

```python
class Config:
    arbitrary_types_allowed = True
```

Allows the model to accept complex objects like `BaseContent` instances that may not yet be fully Pydantic-compatible.

### Migration Benefits

The Pydantic migration provides several advantages over the original dataclass:

1. **Field Validation**: Automatic validation of hash format and lookup key structure
2. **Type Safety**: Enhanced type checking with Pydantic's validation system
3. **Data Normalization**: Automatic lowercase conversion and whitespace handling
4. **Error Messages**: Clear validation error messages for debugging
5. **Future Compatibility**: Ready for `BaseContent` Pydantic migration
6. **Serialization**: Built-in JSON serialization capabilities

### Compatibility Notes

- Maintains the same public interface as the original dataclass
- `create()` classmethod provides the same functionality
- All existing code using IndexEntry continues to work unchanged
- Added validation prevents invalid entries from being created

## Protocol: DeepIndexable

Defines the interface for content that can expose nested indexable items.

### Method

#### `get_deep_index_entries()`

```python
def get_deep_index_entries(self, omnidexer: "Omnidexer") -> list[BaseContent]
```

Returns immediate child content that should be indexed.

**Parameters:**
- `omnidexer` (Omnidexer): The omnidexer instance for resolving references

**Returns:**
- `list[BaseContent]`: List of child content items to index

**Implementation Guidelines:**
- Return only immediate children, not deeply nested content
- Handle errors gracefully with logging
- Use the omnidexer parameter for reference resolution
- Validate content before returning

**Example Implementation:**
```python
def get_deep_index_entries(self, omnidexer: "Omnidexer") -> list[BaseContent]:
    nested_content = []
    try:
        for item in self.nested_items:
            try:
                parsed_item = self._parse_item(item, omnidexer)
                if parsed_item:
                    nested_content.append(parsed_item)
            except Exception as e:
                logger.warning(f"Failed to parse item {item}: {e}")
                continue
    except Exception as e:
        logger.error(f"Failed to extract nested content: {e}")

    return nested_content
```

## Functions and Utilities

### Content Type Resolution

#### `resolve_content_type()`

```python
def resolve_content_type(content: BaseContent) -> ContentType
```

Resolves the appropriate ContentType for a content object.

**Parameters:**
- `content` (BaseContent): Content object to analyze

**Returns:**
- `ContentType`: Resolved content type

### Hash Generation

#### `generate_content_hash()`

```python
def generate_content_hash(
    content_type: ContentType,
    name: str,
    source: str,
    parent_name: str | None = None
) -> str
```

Generates a unique hash for content identification.

**Parameters:**
- `content_type` (ContentType): Type of content
- `name` (str): Content name
- `source` (str): Content source
- `parent_name` (str | None): Parent name for nested content

**Returns:**
- `str`: Unique hash identifier

## Configuration

### Environment Variables

- `DND5E_ENABLE_DEEP_INDEXING`: Set to "false" to disable deep indexing by default
- `DND5E_INDEX_PERFORMANCE_LOGGING`: Set to "true" to enable performance logging

### Configuration Files

Deep indexing can be configured via the settings system:

```python
from dnd5e.core.config.settings import Settings

settings = Settings()
settings.omnidexer.enable_deep_indexing = True
settings.omnidexer.performance_monitoring = True
```

## Performance Monitoring

### Metrics Available

The omnidexer tracks several performance metrics:

```python
stats = omnidexer.get_performance_stats()

# Available metrics:
stats = {
    'total_items': 1500,                    # Total indexed items
    'deep_indexed_items': 800,              # Items added via deep indexing
    'load_time': 2.8,                       # Total loading time in seconds
    'deep_indexing_overhead': 0.128,        # Additional time for deep indexing
    'memory_usage': 45.2,                   # Memory usage in MB
    'index_sizes': {                        # Size of each index
        'hash': 1500,
        'type': 15,
        'source': 25,
        'name': 1200
    },
    'content_type_counts': {                # Count by content type
        'spell': 350,
        'creature': 200,
        'class_feature': 180,
        'adventure_section': 95,
        # ...
    }
}
```

### Performance Best Practices

1. **Monitor Load Times**: Keep total load time under 5 seconds for good user experience
2. **Watch Memory Usage**: Deep indexing increases memory usage by ~15%
3. **Profile Regularly**: Use `get_performance_stats()` to track performance trends
4. **Disable When Needed**: For performance-critical applications, disable deep indexing

### Troubleshooting Performance Issues

If experiencing slow performance:

1. **Check Deep Indexing Overhead**:
   ```python
   stats = omnidexer.get_performance_stats()
   if stats['deep_indexing_overhead'] > 1.0:  # >100% overhead
       # Consider disabling deep indexing
       omnidexer = Omnidexer(enable_deep_indexing=False)
   ```

2. **Monitor Memory Usage**:
   ```python
   import psutil
   memory_mb = psutil.Process().memory_info().rss / 1024 / 1024
   if memory_mb > 500:  # >500MB
       # Investigate memory usage patterns
   ```

3. **Profile Content Types**:
   ```python
   stats = omnidexer.get_performance_stats()
   type_counts = stats['content_type_counts']
   # Look for unexpectedly high counts
   ```

---

This API documentation provides comprehensive coverage of the Omnidexer deep indexing system. For implementation examples and guides, see `docs/omnidexer-deep-indexing.md` and `docs/examples/deep-indexing.py`.

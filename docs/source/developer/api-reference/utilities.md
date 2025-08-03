# Core Utilities API Documentation

## Table of Contents

This page covers the core utility APIs:

- [Cache System](#cache-system)
- [LaTeX Utilities](#latex-utilities)
- [Reference Parsing](#reference-parsing)
- [Content Type Resolution](#content-type-resolution)
- [Logging Utilities](#logging-utilities)
- [Interface Protocols](#interface-protocols)
- [Exception Classes](#exception-classes)

## Overview

The core utilities provide foundational functionality used throughout 5e2pdf. These utilities handle caching, text processing, reference parsing, and other common operations needed by the content processing and rendering systems.

### Key Features

- **Unified caching system** with disk-based persistence
- **LaTeX text escaping** with Unicode support
- **Spell reference parsing** from 5etools tags
- **Content type resolution** for automatic model selection
- **Structured logging** with context and formatting
- **Protocol-based interfaces** for extensibility

## Cache System

**Location**: `src/dnd5e/core/cache.py`

Unified caching system using diskcache for improved performance with persistent storage.

### CacheManager

Singleton cache manager providing unified interface to disk-based caching.

#### Class Methods

##### get_instance

```python
@classmethod
def get_instance(cls) -> Cache
```

Gets the singleton cache instance, creating it if necessary.

**Returns:**
- `Cache`: The global cache instance

**Example:**
```python
from dnd5e.core.cache import CacheManager

cache = CacheManager.get_instance()
cache.set("key", "value", expire=3600)  # Cache for 1 hour
```

##### clear

```python
@classmethod
def clear(cls) -> None
```

Clears the entire cache.

**Example:**
```python
CacheManager.clear()  # Remove all cached data
```

##### get_stats

```python
@classmethod
def get_stats(cls) -> dict[str, Any]
```

Gets comprehensive cache statistics.

**Returns:**
- `dict[str, Any]`: Statistics including size, entries, and limits

**Example:**
```python
stats = CacheManager.get_stats()
print(f"Cache size: {stats['total_size_mb']:.1f}MB")
print(f"Total entries: {stats['total_entries']}")
```

### Functions

#### get_cache

```python
def get_cache() -> Cache
```

Gets the global cache instance (convenience function).

**Returns:**
- `Cache`: The global cache instance

#### cached

```python
def cached(
    key_func: Callable[..., str] | None = None,
    ttl: timedelta | None = None,
) -> Callable[..., Any]
```

Decorator for caching function results with automatic key generation.

**Parameters:**
- `key_func` (Callable | None): Function to generate cache key from arguments
- `ttl` (timedelta | None): Cache time-to-live

**Returns:**
- `Callable`: Decorated function with caching

**Example:**
```python
from datetime import timedelta
from dnd5e.core.cache import cached

@cached(
    key_func=lambda name, source: f"spell:{name}:{source}",
    ttl=timedelta(hours=1)
)
def find_spell(name: str, source: str):
    # Expensive operation - results cached for 1 hour
    return load_spell_from_database(name, source)

# First call - loads from database and caches
spell1 = find_spell("Fireball", "PHB")

# Second call - returns cached result
spell2 = find_spell("Fireball", "PHB")  # Fast cache hit
```

### Cache Configuration

Default cache settings can be customized:

```python
from dnd5e.core.cache import CACHE_SETTINGS, CACHE_DIR

# Default settings
CACHE_SETTINGS = {
    "size_limit": 100 * 1024 * 1024,  # 100MB
    "eviction_policy": "least-recently-used",
    "timeout": 1,  # Database connection timeout
}

# Custom cache directory
CACHE_DIR = Path.cwd() / ".cache"
```

## LaTeX Utilities

**Location**: `src/dnd5e/core/latex_utils.py`

Utilities for LaTeX text processing and character escaping.

### Functions

#### escape_latex_text

```python
def escape_latex_text(text: str) -> str
```

Escapes special LaTeX characters and Unicode characters in text with comprehensive character handling.

**Parameters:**
- `text` (str): Text to escape for LaTeX output

**Returns:**
- `str`: LaTeX-safe text with proper character escaping

**Features:**
- Escapes LaTeX special characters (`{`, `}`, `$`, `&`, `%`, `#`, `^`, `_`, `~`)
- Handles Unicode characters (`—`, `–`, `"`, `"`, `…`, `°`, etc.)
- Preserves ASCII apostrophes for natural text (e.g., "Player's")
- Intentionally does not escape backslashes to avoid double-escaping

**Example:**
```python
from dnd5e.core.latex_utils import escape_latex_text

# LaTeX special characters
text = "Cost: 50gp & requires attunement"
safe_text = escape_latex_text(text)
# Result: "Cost: 50gp \\& requires attunement"

# Unicode characters
text = "The spell deals 3d6 damage—devastating!"
safe_text = escape_latex_text(text)
# Result: "The spell deals 3d6 damage---devastating!"

# Smart quotes
text = '"Special" components are required'
safe_text = escape_latex_text(text)
# Result: "``Special'' components are required"

# Preserves ASCII apostrophes
text = "Player's Handbook, page 257"
safe_text = escape_latex_text(text)
# Result: "Player's Handbook, page 257" (unchanged)
```

### Character Mappings

The function uses comprehensive character mappings:

#### LaTeX Special Characters

```python
latex_chars = {
    "{": "\\{",
    "}": "\\}",
    "$": "\\$",
    "&": "\\&",
    "%": "\\%",
    "#": "\\#",
    "^": "\\textasciicircum{}",
    "_": "\\_",
    "~": "\\textasciitilde{}",
}
```

#### Unicode Replacements

```python
unicode_replacements = {
    "—": "---",              # Em dash
    "–": "--",               # En dash
    """: "``",               # Left double quote
    """: "''",               # Right double quote
    "…": "\\ldots{}",        # Ellipsis
    "°": "\\textdegree{}",   # Degree symbol
    "©": "\\copyright{}",    # Copyright symbol
    "®": "\\textregistered{}", # Registered trademark
    "™": "\\texttrademark{}", # Trademark symbol
}
```

## Reference Parsing

**Location**: `src/dnd5e/core/references.py`

Utilities for parsing spell references and cross-references from 5etools content.

### SpellReference

Data class representing a parsed spell reference.

```python
@dataclass
class SpellReference:
    """Represents a parsed spell reference."""

    name: str
    source: str | None = None
    display_text: str | None = None
    original_tag: str = ""
```

#### Methods

##### __str__

```python
def __str__(self) -> str
```

Returns string representation of the spell reference.

**Returns:**
- `str`: Display text, or "Name (Source)", or just name

**Example:**
```python
ref1 = SpellReference(name="Fireball", source="PHB")
print(str(ref1))  # "Fireball (PHB)"

ref2 = SpellReference(name="Fireball", display_text="the fireball spell")
print(str(ref2))  # "the fireball spell"
```

### SpellReferenceParser

Parser for extracting spell references from 5etools text content.

#### Class Attributes

##### SPELL_TAG_PATTERN

```python
SPELL_TAG_PATTERN = re.compile(
    r"\{@spell\s+([^}]+)\}", re.IGNORECASE | re.MULTILINE
)
```

Regex pattern for matching `{@spell ...}` tags in text.

#### Class Methods

##### extract_spell_references

```python
@classmethod
def extract_spell_references(cls, text: str) -> list[SpellReference]
```

Extracts all spell references from text content.

**Parameters:**
- `text` (str): Text to parse for spell references

**Returns:**
- `list[SpellReference]`: List of parsed spell references

**Example:**
```python
from dnd5e.core.references import SpellReferenceParser

text = "You can cast {@spell fireball} or {@spell magic missile|PHB|the magic missile spell}."

references = SpellReferenceParser.extract_spell_references(text)
for ref in references:
    print(f"Found: {ref.name} from {ref.source}")
```

#### Supported Formats

The parser handles multiple reference formats:

```python
# Format 1: Spell name only
"{@spell fireball}"
# Result: SpellReference(name="fireball")

# Format 2: Spell name with source
"{@spell magic missile|PHB}"
# Result: SpellReference(name="magic missile", source="PHB")

# Format 3: Spell name, source, and display text
"{@spell detect magic|PHB|the detect magic spell}"
# Result: SpellReference(name="detect magic", source="PHB", display_text="the detect magic spell")
```

### SpellReferenceResolver

Resolves spell references to actual content objects using the omnidexer.

```python
class SpellReferenceResolver:
    """Resolves spell references to actual spell objects."""

    def __init__(self, omnidexer: "Omnidexer"):
        self.omnidexer = omnidexer
```

#### Methods

##### resolve_reference

```python
def resolve_reference(self, reference: SpellReference) -> BaseContent | None
```

Resolves a spell reference to the actual spell content.

**Parameters:**
- `reference` (SpellReference): Reference to resolve

**Returns:**
- `BaseContent | None`: Resolved spell object or None if not found

**Example:**
```python
from dnd5e.core.references import SpellReferenceResolver

resolver = SpellReferenceResolver(omnidexer)
reference = SpellReference(name="fireball", source="PHB")

spell = resolver.resolve_reference(reference)
if spell:
    print(f"Resolved: {spell.name} (Level {spell.level})")
```

## Content Type Resolution

**Location**: `src/dnd5e/core/content_type_resolver.py`

Automatic content type detection and resolution for JSON data.

### ContentTypeResolver

Resolves content types from JSON data using pattern matching and heuristics.

```python
class ContentTypeResolver:
    """Resolves content types from JSON data."""

    def __init__(self) -> None:
        self._type_resolvers: list[Callable] = []
        self._initialized = False
```

#### Methods

##### resolve_type

```python
def resolve_type(self, content: BaseContent) -> ContentType
```

Determines content type from content object.

**Parameters:**
- `content` (BaseContent): Content object to analyze

**Returns:**
- `ContentType`: Determined content type

##### resolve_from_json

```python
def resolve_from_json(self, data: dict[str, Any]) -> ContentType | None
```

Determines content type from raw JSON data.

**Parameters:**
- `data` (dict): Raw JSON data from 5etools

**Returns:**
- `ContentType | None`: Determined content type or None if unknown

**Example:**
```python
from dnd5e.core.content_type_resolver import get_content_type_resolver

resolver = get_content_type_resolver()

# Spell data
spell_data = {
    "name": "Fireball",
    "level": 3,
    "school": "evocation"
}
content_type = resolver.resolve_from_json(spell_data)
# Returns: ContentType.SPELL

# Creature data
creature_data = {
    "name": "Ancient Red Dragon",
    "cr": "24",
    "ac": [{"ac": 22}]
}
content_type = resolver.resolve_from_json(creature_data)
# Returns: ContentType.CREATURE
```

##### register_resolver

```python
def register_resolver(self, resolver_func: Callable[[dict], ContentType | None]) -> None
```

Registers a custom content type resolver function.

**Parameters:**
- `resolver_func` (Callable): Function that takes JSON data and returns ContentType or None

**Example:**
```python
def custom_homebrew_resolver(data: dict) -> ContentType | None:
    if data.get("_meta", {}).get("homebrew"):
        return ContentType("homebrew")
    return None

resolver.register_resolver(custom_homebrew_resolver)
```

### Functions

#### get_content_type_resolver

```python
def get_content_type_resolver() -> ContentTypeResolver
```

Gets the global content type resolver instance.

**Returns:**
- `ContentTypeResolver`: Global resolver instance

## Logging Utilities

**Location**: `src/dnd5e/core/logging/logger.py`

Centralized logging system with colored output and consistent formatting.

### Functions

#### setup_logging

```python
def setup_logging(level: str = "WARNING") -> None
```

Configures the root logger for the application with colored output.

**Parameters:**
- `level` (str): Minimum logging level ("DEBUG", "INFO", "WARNING", "ERROR")

**Example:**
```python
from dnd5e.core.logging import setup_logging

# Setup logging for development
setup_logging("DEBUG")

# Setup logging for production
setup_logging("WARNING")
```

#### get_logger

```python
def get_logger(name: str) -> logging.Logger
```

Gets a logger instance for a specific module with consistent formatting.

**Parameters:**
- `name` (str): Logger name (typically `__name__`)

**Returns:**
- `logging.Logger`: Configured logger instance

**Example:**
```python
from dnd5e.core.logging import get_logger

logger = get_logger(__name__)

logger.info("Processing started")
logger.warning("Malformed entry encountered")
logger.error("Failed to load content", exc_info=True)
```

### Log Formatting

The logging system uses colored output with consistent formatting:

```python
formatter = colorlog.ColoredFormatter(
    "%(log_color)s%(levelname)-8s%(reset)s %(blue)s%(name)s%(reset)s: %(message)s",
    log_colors={
        "DEBUG": "cyan",
        "INFO": "green",
        "WARNING": "yellow",
        "ERROR": "red",
        "CRITICAL": "red,bg_white",
    }
)
```

## Interface Protocols

**Location**: `src/dnd5e/core/interfaces.py`

Protocol definitions for extensible interfaces throughout the system.

### DeepIndexable

Protocol for content that can provide nested indexable entries.

```python
class DeepIndexable(Protocol):
    """Protocol for content that supports deep indexing."""

    def get_deep_index_entries(self, omnidexer: "Omnidexer") -> list[BaseContent]:
        """Return nested content for deep indexing."""
        ...
```

**Example Implementation:**
```python
from dnd5e.core.interfaces import DeepIndexable

class CustomAdventure(BaseContent, DeepIndexable):
    def get_deep_index_entries(self, omnidexer: "Omnidexer") -> list[BaseContent]:
        """Extract all nested content for indexing."""
        entries = []

        # Extract sections
        for section in self.sections:
            entries.append(section)

        # Extract tables, NPCs, etc.
        entries.extend(self.extract_nested_content())

        return entries
```

### ContentProcessor

Protocol for content processing components.

```python
class ContentProcessor(Protocol):
    """Protocol for content processors."""

    def process(self, content: BaseContent, context: Any) -> dict[str, Any]:
        """Process content and return enhanced data."""
        ...

    def supports_content_type(self, content_type: ContentType) -> bool:
        """Check if processor supports the content type."""
        ...
```

## Exception Classes

**Location**: `src/dnd5e/core/exceptions.py`

Structured exception classes with rich context information.

### DnD5eError

Base exception for all 5e2pdf errors.

```python
class DnD5eError(Exception):
    """Base exception for all D&D 5e processing errors."""
    pass
```

### EntryProcessingError

Exception for entry processing issues with contextual information.

```python
class EntryProcessingError(DnD5eError):
    """Exception for entry processing issues with context."""

    def __init__(
        self,
        message: str,
        entry: dict[str, Any] | None = None,
        source: str | None = None,
        parent_name: str | None = None,
        entry_type: str | None = None,
    ):
        self.entry = entry
        self.source = source
        self.parent_name = parent_name
        self.entry_type = entry_type

        # Build contextual error message
        context_parts = []
        if source:
            context_parts.append(f"source: {source}")
        if parent_name:
            context_parts.append(f"parent: {parent_name}")
        if entry_type:
            context_parts.append(f"type: {entry_type}")

        if context_parts:
            context_str = " (" + ", ".join(context_parts) + ")"
            super().__init__(f"{message}{context_str}")
        else:
            super().__init__(message)
```

**Example:**
```python
from dnd5e.core.exceptions import EntryProcessingError

try:
    process_entry(entry_data)
except Exception as e:
    raise EntryProcessingError(
        message="Failed to process spell entry",
        entry=entry_data,
        source="PHB",
        parent_name="Spells by Class",
        entry_type="spell"
    ) from e
```

### Specialized Exceptions

#### UnknownEntryTypeError

```python
class UnknownEntryTypeError(EntryProcessingError):
    """Exception raised when an unknown entry type is encountered."""
```

#### EntryValidationError

```python
class EntryValidationError(EntryProcessingError):
    """Exception raised when entry validation fails."""

    def __init__(
        self,
        message: str,
        field_name: str | None = None,
        entry: dict[str, Any] | None = None,
        source: str | None = None,
        parent_name: str | None = None,
        entry_type: str | None = None,
    ):
        self.field_name = field_name
        # ... additional initialization
```

#### MalformedEntryError

```python
class MalformedEntryError(EntryProcessingError):
    """Exception raised when an entry has structural problems."""
```

## Usage Examples

### Complete Cache Setup

```python
from datetime import timedelta
from dnd5e.core.cache import cached, CacheManager

# Setup custom cache settings
CacheManager._instance = None  # Reset singleton

@cached(ttl=timedelta(hours=2))
def expensive_computation(data_id: str):
    """Expensive operation cached for 2 hours."""
    return perform_complex_analysis(data_id)

# Use cached function
result = expensive_computation("spell_analysis")

# Check cache stats
stats = CacheManager.get_stats()
print(f"Cache usage: {stats['total_size_mb']:.1f}MB")
```

### Text Processing Pipeline

```python
from dnd5e.core.latex_utils import escape_latex_text
from dnd5e.core.references import SpellReferenceParser

def process_description_text(raw_text: str) -> str:
    """Process D&D description text for LaTeX output."""

    # Extract spell references for cross-linking
    references = SpellReferenceParser.extract_spell_references(raw_text)

    # Process each reference
    processed_text = raw_text
    for ref in references:
        # Replace with LaTeX cross-reference
        latex_ref = f"\\spellref{{{ref.name}}}"
        processed_text = processed_text.replace(ref.original_tag, latex_ref)

    # Escape remaining text for LaTeX
    safe_text = escape_latex_text(processed_text)

    return safe_text

# Example usage
raw_text = "The wizard casts {@spell fireball|PHB} dealing 8d6 fire damage!"
processed = process_description_text(raw_text)
# Result: "The wizard casts \\spellref{fireball} dealing 8d6 fire damage!"
```

### Custom Content Type Resolver

```python
from dnd5e.core.content_type_resolver import get_content_type_resolver
from dnd5e.core.models.content import ContentType

def register_homebrew_resolver():
    """Register custom resolver for homebrew content."""

    def homebrew_resolver(data: dict) -> ContentType | None:
        # Check for homebrew markers
        if data.get("_meta", {}).get("homebrew"):
            return ContentType("homebrew")

        # Check for custom source indicators
        source = data.get("source", "")
        if source.startswith("HB_"):
            return ContentType("homebrew")

        return None

    resolver = get_content_type_resolver()
    resolver.register_resolver(homebrew_resolver)

# Register custom resolver
register_homebrew_resolver()

# Use resolver
resolver = get_content_type_resolver()
homebrew_data = {
    "name": "Custom Spell",
    "source": "HB_MyCollection",
    "level": 5
}

content_type = resolver.resolve_from_json(homebrew_data)
# Returns: ContentType("homebrew")
```

### Error Handling with Context

```python
from dnd5e.core.exceptions import EntryProcessingError, EntryValidationError
from dnd5e.core.logging import get_logger

logger = get_logger(__name__)

def robust_entry_processing(entry_data: dict, source: str):
    """Process entry with comprehensive error handling."""

    try:
        # Validate entry structure
        if not isinstance(entry_data.get("name"), str):
            raise EntryValidationError(
                message="Name must be a string",
                field_name="name",
                entry=entry_data,
                source=source
            )

        # Process entry
        return process_entry_content(entry_data)

    except EntryValidationError as e:
        logger.warning(f"Validation error: {e}")
        if e.field_name:
            logger.debug(f"Problem field: {e.field_name}")
        raise

    except Exception as e:
        # Wrap unexpected errors with context
        raise EntryProcessingError(
            message=f"Unexpected error during processing: {e}",
            entry=entry_data,
            source=source,
            entry_type=entry_data.get("type", "unknown")
        ) from e
```

## Performance Considerations

### Cache Optimization

```python
# Configure cache for your use case
from dnd5e.core.cache import CACHE_SETTINGS

# For development (smaller cache, faster iteration)
CACHE_SETTINGS.update({
    "size_limit": 10 * 1024 * 1024,  # 10MB
    "eviction_policy": "least-recently-used"
})

# For production (larger cache, better performance)
CACHE_SETTINGS.update({
    "size_limit": 500 * 1024 * 1024,  # 500MB
    "eviction_policy": "least-frequently-used"
})
```

### Text Processing Optimization

```python
# Batch text processing for better performance
def process_text_batch(texts: list[str]) -> list[str]:
    """Process multiple texts efficiently."""

    # Pre-compile regex patterns
    ref_parser = SpellReferenceParser()

    results = []
    for text in texts:
        # Extract references once
        references = ref_parser.extract_spell_references(text)

        # Process text
        processed = escape_latex_text(text)
        results.append(processed)

    return results
```

### Memory Management

```python
# Use weak references for large cached objects
import weakref
from typing import WeakValueDictionary

class OptimizedCache:
    """Cache with weak references for memory efficiency."""

    def __init__(self):
        self._cache: WeakValueDictionary = weakref.WeakValueDictionary()

    def get_or_create(self, key: str, factory: Callable):
        """Get cached object or create with factory."""
        obj = self._cache.get(key)
        if obj is None:
            obj = factory()
            self._cache[key] = obj
        return obj
```

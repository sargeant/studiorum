# Loaders and Data Access

Systems for loading and accessing D&D content data.

## Omnidexer

The primary interface for content loading and searching.

```{eval-rst}
.. automodule:: dnd5e.core.loaders.omnidexer
   :members:
   :undoc-members:
   :show-inheritance:
```

**Example Usage:**

```python
from dnd5e.core.loaders import Omnidexer

# Initialize omnidexer
omnidexer = Omnidexer()

# Load all data
await omnidexer.load_all_data()

# Search for content
spells = omnidexer.find(content_type="spell", source="PHB")
fireball = omnidexer.find_one(content_type="spell", name="Fireball")

# Filter content
fire_spells = omnidexer.find(
    content_type="spell",
    filter_func=lambda s: "fire" in s.description.lower()
)

# Get statistics
stats = omnidexer.get_stats()
print(f"Total spells: {stats['spell']}")
```

## Base Loaders

```{eval-rst}
.. automodule:: dnd5e.core.loaders.base
   :members:
   :undoc-members:
   :show-inheritance:
```

## JSON Data Loader

```{eval-rst}
.. automodule:: dnd5e.core.loaders.json_loader
   :members:
   :undoc-members:
   :show-inheritance:
```

## Source Management

Content source discovery and management functionality, including support for the dual-file architecture used by adventures and books.

### Dual-File Architecture

The loader system implements a dual-file architecture for adventures and books that separates metadata from content:

- **Metadata files** (`adventures.json`, `books.json`): Lightweight index files loaded at startup
- **Content files** (`adventure-*.json`, `book-*.json`): Heavy content data loaded on-demand

**Example Source Management:**
```python
from dnd5e.core.loaders import ConfigurableSourceManager, Omnidexer

# Source manager with dual-file support
source_manager = ConfigurableSourceManager()

# Get metadata files (loaded by omnidexer)
metadata_files = source_manager.get_metadata_files()
print(f"Adventure metadata files: {metadata_files[ContentType.ADVENTURE]}")

# Get content files (for on-demand loading)
content_files = source_manager.get_content_files()
print(f"Adventure content files: {content_files[ContentType.ADVENTURE]}")

# Omnidexer automatically uses only metadata files
omnidexer = Omnidexer(source_manager)
await omnidexer.load_all_data()

# Results in ~61 adventures (metadata only) instead of 94 duplicates
stats = omnidexer.get_statistics()
print(f"Adventures loaded: {stats['by_type'].get('adventure', 0)}")
```

## Performance and Caching

The loaders use several optimization strategies:

### Disk Caching
```python
from dnd5e.core.loaders import Omnidexer

# Configure cache settings
omnidexer = Omnidexer(
    cache_dir="~/.5e2pdf/cache",
    cache_ttl=86400  # 24 hours
)
```

### Lazy Loading
```python
# Content is loaded on-demand
spells = omnidexer.find(content_type="spell")  # Fast - uses index
spell_data = spells[0].description  # Loads full data when accessed
```

### Batch Operations
```python
# Efficient batch loading
content_types = ["spell", "monster", "item"]
all_content = await omnidexer.load_content_types(content_types)
```

## Search and Filtering

### Basic Search
```python
# By content type
spells = omnidexer.find(content_type="spell")

# By source
phb_content = omnidexer.find(source="PHB")

# By name (exact match)
fireball = omnidexer.find_one(name="Fireball")

# By name (partial match)
fire_spells = omnidexer.find(name_contains="fire")
```

### Advanced Filtering
```python
# Custom filter functions
def high_level_spells(spell):
    return spell.level >= 7

powerful_spells = omnidexer.find(
    content_type="spell",
    filter_func=high_level_spells
)

# Complex queries
battle_ready = omnidexer.find(
    content_type="spell",
    filter_func=lambda s: (
        s.level <= 3 and
        "damage" in s.description.lower() and
        s.time.startswith("1 action")
    )
)
```

### Search Performance
```python
# Use indexes for best performance
omnidexer.find(content_type="spell")  # Fast - indexed
omnidexer.find(source="PHB")  # Fast - indexed
omnidexer.find(name="Fireball")  # Fast - indexed

# Filter functions are slower but flexible
omnidexer.find(filter_func=custom_filter)  # Slower - scans all data
```

## Error Handling

```python
from dnd5e.core.loaders.exceptions import (
    LoaderError,
    ContentNotFoundError,
    SourceNotAvailableError
)

try:
    content = omnidexer.find_one(name="NonexistentSpell")
except ContentNotFoundError:
    print("Content not found")

try:
    await omnidexer.load_source("INVALID_SOURCE")
except SourceNotAvailableError:
    print("Source not available")
```

## Data Sources

The system supports multiple data sources:

- **5etools JSON**: Primary source for comprehensive D&D data
- **Homebrew Content**: Custom user-defined content
- **Third-party Sources**: Additional community content

See {doc}`/advanced-features` for configuration details.

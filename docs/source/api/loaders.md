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

Content source discovery and management functionality.

**Example Source Management:**
```python
from dnd5e.core.loaders import Omnidexer

omnidexer = Omnidexer()

# Get available sources
sources = omnidexer.get_available_sources()
print(f"Available sources: {sources}")

# Update sources
await omnidexer.update_sources()

# Validate source integrity
is_valid = await omnidexer.validate_sources()
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

See {doc}`/user-guide/advanced-features` for configuration details.

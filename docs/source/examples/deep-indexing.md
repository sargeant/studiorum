# Deep Indexing Example

```{note}
This page demonstrates the deep indexing functionality implemented in the Omnidexer system.
```

## Overview

The deep indexing example shows how to use the Omnidexer to create comprehensive cross-references and relationships between D&D content elements.

## Python Implementation

The complete implementation is available as a Python script:

[Download deep-indexing.py](deep-indexing.py)

## Key Concepts

### Cross-Reference Generation

The system automatically identifies and creates links between:
- Spells referenced in class descriptions
- Items mentioned in monster stat blocks
- Conditions referenced in spell effects
- Rules cited in feature descriptions

### Index Structure

```python
# Example index structure
index = {
    'spells': {
        'fireball': {
            'referenced_by': ['wizard', 'sorcerer', 'evocation_school'],
            'references': ['fire_damage', 'dexterity_save'],
            'related_items': ['wand_of_fireballs'],
        }
    }
}
```

### Performance Optimization

- Lazy loading of content
- Efficient graph traversal algorithms
- Caching of computed relationships

## Usage Examples

### Basic Deep Indexing

```python
from dnd5e.omnidexer import DeepIndexer

# Initialize the indexer
indexer = DeepIndexer()

# Load content and build indexes
indexer.load_content('path/to/5etools/data')
indexer.build_deep_index()

# Query relationships
spell_refs = indexer.get_references('fireball')
print(f"Fireball is referenced by: {spell_refs}")
```

### Advanced Filtering

```python
# Filter by content type
wizard_spells = indexer.filter_by_class('wizard')

# Find circular references
circular = indexer.find_circular_references()

# Generate relationship graph
graph = indexer.export_graph_data()
```

## Implementation Details

For detailed implementation information, see:
- [Omnidexer API Documentation](../developer/api-reference/core-apis.md)
- [System Components Guide](../developer/system-guide/components.md)

## Running the Example

```bash
# Execute the example script
uv run python docs/source/examples/deep-indexing.py

# With custom data path
uv run python docs/source/examples/deep-indexing.py --data-path /path/to/data

# Enable verbose output
uv run python docs/source/examples/deep-indexing.py --verbose
```

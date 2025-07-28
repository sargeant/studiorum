# Examples

Practical examples and code samples for using 5e2pdf effectively.

## Table of Contents

```{toctree}
:maxdepth: 2

deep-indexing
```

## Overview

The Examples section provides practical, runnable code samples that demonstrate how to use 5e2pdf's features effectively. Examples are organized by complexity and use case, making it easy to find the right starting point for your needs.

## Available Examples

### [Deep Indexing Examples](deep-indexing.py)

Comprehensive examples of using the omnidexer's deep indexing system:

- Basic content loading and querying
- Working with nested content (class features, adventure sections)
- Performance comparison and optimization
- Custom content implementation
- Troubleshooting and debugging techniques

**Run the example:**
```bash
cd docs/source/examples
python deep-indexing.py
```

## Example Categories

### Getting Started

Basic examples for new users:

```python
from dnd5e.core.loaders.omnidexer import Omnidexer
from dnd5e.core.models.content import ContentType

# Simple content loading
omnidexer = Omnidexer()
await omnidexer.load_all_data()

# Find a spell
fireball = omnidexer.find(ContentType.SPELL, "Fireball", "PHB")
print(f"Found: {fireball.name}")
```

### Common Use Cases

Examples for typical workflows:

```python
# DM session preparation
creatures = omnidexer.find_all(ContentType.CREATURE)
forest_creatures = [c for c in creatures if "forest" in c.environment]

# Player reference creation
wizard_spells = [s for s in omnidexer.find_all(ContentType.SPELL)
                if "wizard" in s.classes]
```

### Advanced Techniques

Complex examples for power users:

```python
# Custom content filtering
def find_low_level_content(omnidexer, max_level=3):
    results = []
    for content_type in [ContentType.SPELL, ContentType.CREATURE]:
        items = omnidexer.find_all(content_type)
        filtered = [i for i in items if getattr(i, 'level', 0) <= max_level]
        results.extend(filtered)
    return results
```

## Interactive Examples

### Jupyter Notebooks

For interactive exploration:

```bash
# Install Jupyter support
pip install jupyter

# Run example notebooks
jupyter notebook examples/
```

### Command Line Examples

Quick command-line examples:

```bash
# Generate spell reference
5e2pdf spell --class Wizard --level "1-3" --output wizard-spells.pdf

# Create creature compendium
5e2pdf creature --cr "0-5" --type "humanoid,beast" --output basic-creatures.pdf

# Extract adventure content
5e2pdf adventure-section --adventure "Lost Mine of Phandelver" --output lmop-sections.pdf
```

## Performance Examples

### Benchmarking

```python
import time
from dnd5e.core.loaders.omnidexer import Omnidexer

# Compare performance with/without deep indexing
async def benchmark_loading():
    # Without deep indexing
    start = time.time()
    shallow = Omnidexer(enable_deep_indexing=False)
    await shallow.load_all_data()
    shallow_time = time.time() - start

    # With deep indexing
    start = time.time()
    deep = Omnidexer(enable_deep_indexing=True)
    await deep.load_all_data()
    deep_time = time.time() - start

    print(f"Shallow: {shallow_time:.2f}s, Deep: {deep_time:.2f}s")
    print(f"Overhead: {((deep_time - shallow_time) / shallow_time) * 100:.1f}%")
```

### Memory Optimization

```python
import psutil
import gc

def monitor_memory_usage():
    """Monitor memory usage during content loading."""
    process = psutil.Process()

    initial_memory = process.memory_info().rss / 1024 / 1024  # MB
    print(f"Initial memory: {initial_memory:.1f} MB")

    omnidexer = Omnidexer()
    await omnidexer.load_all_data()

    loaded_memory = process.memory_info().rss / 1024 / 1024  # MB
    print(f"After loading: {loaded_memory:.1f} MB")
    print(f"Memory increase: {loaded_memory - initial_memory:.1f} MB")

    # Force garbage collection
    gc.collect()

    gc_memory = process.memory_info().rss / 1024 / 1024  # MB
    print(f"After GC: {gc_memory:.1f} MB")
```

## Integration Examples

### With Other Tools

Examples of integrating 5e2pdf with other systems:

```python
# Flask web service
from flask import Flask, request, send_file
from dnd5e.core.loaders.omnidexer import Omnidexer

app = Flask(__name__)
omnidexer = None

@app.before_first_request
async def setup():
    global omnidexer
    omnidexer = Omnidexer()
    await omnidexer.load_all_data()

@app.route('/api/spell/<name>')
def get_spell(name):
    spell = omnidexer.find(ContentType.SPELL, name, request.args.get('source', 'PHB'))
    return spell.to_dict() if spell else {"error": "Not found"}, 404
```

### Custom Renderers

```python
from dnd5e.renderers.base import BaseRenderer

class MarkdownRenderer(BaseRenderer):
    """Custom renderer for Markdown output."""

    def render_spell(self, spell):
        return f"""
# {spell.name}

*{spell.level} {spell.school}*

**Range:** {spell.range}
**Duration:** {spell.duration}
**Components:** {spell.components}

{spell.description}
"""
```

## Testing Examples

### Unit Test Patterns

```python
import pytest
from dnd5e.core.loaders.omnidexer import Omnidexer
from dnd5e.core.models.content import ContentType

@pytest.mark.asyncio
async def test_omnidexer_basic_functionality():
    """Test basic omnidexer operations."""
    omnidexer = Omnidexer()
    await omnidexer.load_all_data()

    # Test that we can find known content
    assert omnidexer.find(ContentType.SPELL, "Fireball", "PHB") is not None

    # Test content counts are reasonable
    spells = omnidexer.find_all(ContentType.SPELL)
    assert len(spells) > 100  # Should have many spells
```

### Mock Data Examples

```python
from unittest.mock import Mock

def create_mock_spell():
    """Create a mock spell for testing."""
    spell = Mock()
    spell.name = "Test Spell"
    spell.source = "TEST"
    spell.level = 1
    spell.school = "evocation"
    spell.range = "30 feet"
    spell.duration = "Instantaneous"
    spell.components = "V, S"
    spell.description = "A test spell that does test things."
    return spell
```

## Troubleshooting Examples

### Debug Logging

```python
import logging
from dnd5e.core.loaders.omnidexer import Omnidexer

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('dnd5e')

omnidexer = Omnidexer()
await omnidexer.load_all_data()

# Debug specific content issues
problematic_content = omnidexer.find(ContentType.SPELL, "Problem Spell", "TEST")
if not problematic_content:
    logger.debug("Could not find Problem Spell - checking alternatives")
    alternatives = omnidexer.find_by_name("Problem Spell")
    for alt in alternatives:
        logger.debug(f"Found alternative: {alt.name} from {alt.source}")
```

### Performance Profiling

```python
import cProfile
import pstats
from dnd5e.core.loaders.omnidexer import Omnidexer

async def profile_loading():
    """Profile omnidexer loading performance."""
    omnidexer = Omnidexer()

    # Profile the loading process
    profiler = cProfile.Profile()
    profiler.enable()

    await omnidexer.load_all_data()

    profiler.disable()

    # Analyze results
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative').print_stats(20)
```

## Contributing Examples

We welcome contributions of new examples! When adding examples:

1. **Make them runnable**: Include all necessary imports and setup
2. **Add documentation**: Explain what the example demonstrates
3. **Test them**: Ensure examples work with current 5e2pdf version
4. **Follow patterns**: Use consistent style with existing examples

To contribute an example:

1. Create a new file in `docs/source/examples/`
2. Add it to the table of contents in this file
3. Include a brief description and usage instructions
4. Submit a pull request

## Getting Help

If you're having trouble with any examples:

1. Check that you have the latest version of 5e2pdf
2. Ensure all dependencies are installed
3. Look at the [troubleshooting guide](../user-guide/troubleshooting.md)
4. Ask for help in [GitHub Discussions](https://github.com/sargeant/5e2pdf/discussions)

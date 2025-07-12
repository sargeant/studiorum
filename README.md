# D&D 5e to PDF Converter

This project converts structured JSON data from the 5e.tools website into LaTeX documents that match the style of the official D&D 5th edition books.

## 🚀 **COMPLETE REFACTORING (All Phases Complete!)**

The codebase has been completely modernized with a professional Python architecture:

### **✅ Phase 1: Foundation** 
- **Modern data models** with Pydantic v2 validation
- **Omnidexer system** for efficient content indexing and cross-referencing  
- **Tag resolution engine** for processing `{@spell Fireball|PHB}` style tags
- **Type-safe async processing** with comprehensive configuration

### **✅ Phase 2: Rendering System**
- **Abstract renderer interfaces** for multiple output formats
- **LaTeX document generation** with D&D-style templates
- **Content-specific renderers** for spells, creatures, items, adventures
- **Template system** with customizable layouts and LaTeX formatting

### **✅ Phase 3: Modern CLI & Legacy Migration**
- **Modern CLI interface** with Typer and Rich output
- **Backwards compatibility layer** maintaining full legacy support
- **Performance optimizations** with caching and async processing
- **Comprehensive testing** with 100+ tests across all components

## Directory Structure

```
5e2pdf/
├── src/                         # Python source code (MODERN ARCHITECTURE)
│   ├── core/                    # Core foundation modules
│   │   ├── models/              # Pydantic data models (Spell, Creature, Item, etc.)
│   │   ├── loaders/             # Data loading and omnidexer system
│   │   ├── indexer/             # Tag resolution and cross-referencing
│   │   ├── config/              # Configuration and settings management
│   │   └── cache.py             # Performance caching system
│   ├── renderers/               # Modern rendering system
│   │   ├── base/                # Abstract renderer interfaces
│   │   └── latex/               # LaTeX-specific implementations
│   ├── cli/                     # Modern CLI interface with Typer
│   │   ├── commands/            # CLI command modules
│   │   ├── main.py              # Main CLI application
│   │   └── compat.py            # Legacy compatibility layer
│   ├── json2tex.py             # Legacy conversion script (still functional)
│   ├── gen-latex.py            # Legacy LaTeX utilities
│   ├── tablejson2tex.py        # Legacy table converter
│   └── dndtex/                 # Legacy rendering module
├── assets/                      # Static resources
│   ├── fonts/                   # D&D-style fonts
│   ├── images/                  # Images and graphics
│   └── packages/                # LaTeX packages
├── json_data/                   # Input JSON files
│   ├── books/                   # Book JSON files
│   ├── adventures/              # Adventure JSON files
│   └── supplements/             # Other content JSON files
├── output/                      # Generated LaTeX files
├── build/                       # LaTeX compilation artifacts (gitignored)
├── scripts/                     # Build automation scripts
├── tests/                       # Comprehensive test suite (NEW)
│   ├── unit/                    # Unit tests for core components
│   ├── integration/             # Integration tests
│   └── fixtures/                # Test data and fixtures
├── pyproject.toml              # Modern Python project configuration
├── REFACTORING_PLAN.md         # Detailed refactoring roadmap
└── README.md                   # This file
```

## Quick Start

### 1. Install uv (Python package manager)
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Setup dependencies
```bash
# Install all dependencies
uv sync

# Install with development tools
uv sync --extra dev

# Or use the build script
./scripts/build.sh setup
```

### 3. Configure Content Sources 🎯
```bash
# Run the interactive setup wizard (recommended)
uv run 5e2pdf setup wizard

# Or manually add content sources
uv run 5e2pdf sources add 5etools-official --type github --url https://github.com/5etools-mirror-3/5etools-src
uv run 5e2pdf sources add homebrew --type github --url https://github.com/TheGiddyLimit/homebrew

# Add a local directory
uv run 5e2pdf sources add my-content --type directory --path ~/my-dnd-json

# Download and index content
uv run 5e2pdf sources scan
```

### 4. Use the Modern CLI ⚡
```bash
# Quick conversion (new way)
uv run 5e2pdf quick spell-data.json --pdf

# Modern CLI help
uv run 5e2pdf --help

# Legacy compatibility (old commands still work)
uv run 5e2pdf legacy --adventure --no-images adventure.json
```

### 5. Test the architecture
```bash
# Run the comprehensive test suite (100+ tests)
uv run pytest tests/unit/ -v

# Test omnidexer data loading
uv run python -c "
import asyncio
from src.core.loaders.omnidexer import Omnidexer

async def test():
    omnidexer = Omnidexer()
    stats = await omnidexer.load_all_data()
    print(f'Loaded: {stats}')
    
    # Find a spell
    fireball = omnidexer.find('spell', 'Fireball', 'PHB')
    if fireball:
        print(f'Found: {fireball.name} - {fireball.get_level_text()}')

asyncio.run(test())
"
```

### 6. Build documents (Legacy System - Still Works)
```bash
# Simple build (LaTeX only)
./scripts/json2tex.sh --adventure --no-images --add-items --add-creatures path/to/adventure.json > output.tex

# Complete build with PDF compilation
./scripts/build.sh adventure json_data/adventures/cos.json

# Original workflow from CLAUDE.md
./scripts/json2tex.sh --no-images --add-items --add-creatures --adventure ../5etools-src/data/adventure/adventure-cos.json > build/adventure-cos.tex
cd build && xelatex adventure-cos.tex
```

## 🆕 Modern CLI Usage

### **Quick Convert** ⚡
```bash
# Convert any JSON file to LaTeX/PDF
uv run 5e2pdf quick spell-data.json --pdf

# Convert with custom title and images
uv run 5e2pdf quick adventure.json --title "My Adventure" --images --pdf
```

### **Content Source Management** 📚
```bash
# List configured sources
uv run 5e2pdf sources list

# Get detailed info about a source
uv run 5e2pdf sources info 5etools-official

# Update all sources (pull latest from GitHub)
uv run 5e2pdf sources update

# Remove a source
uv run 5e2pdf sources remove my-source --remove-data

# Set up default sources
uv run 5e2pdf sources defaults
```

### **Advanced Commands** 🔧
```bash
# List available content
uv run 5e2pdf list files
uv run 5e2pdf list content --type spell --limit 10

# Show content information  
uv run 5e2pdf info content "Fireball" --type spell
uv run 5e2pdf info file adventure.json

# Statistics and analysis
uv run 5e2pdf stats overview
uv run 5e2pdf stats content spell
uv run 5e2pdf stats sources
```

### **Legacy Compatibility** 🔄
```bash
# All old commands still work through legacy mode
uv run 5e2pdf legacy --adventure --no-images data.json > output.tex
uv run 5e2pdf legacy --book --with-images book.json > book.tex

# Or use the wrapper script
./json2tex.py --adventure --no-images data.json > output.tex
```

## Architecture Usage Examples

### Working with the Omnidexer
```python
import asyncio
from src.core.loaders.omnidexer import Omnidexer
from src.core.models.content import ContentType

async def example():
    # Create and load omnidexer
    omnidexer = Omnidexer()
    await omnidexer.load_all_data()
    
    # Find specific content
    fireball = omnidexer.find(ContentType.SPELL, "Fireball", "PHB")
    ancient_dragon = omnidexer.find(ContentType.CREATURE, "Ancient Red Dragon", "MM")
    
    # Search content
    fire_spells = omnidexer.search("Fire", ContentType.SPELL)
    all_creatures = omnidexer.get_all_by_type(ContentType.CREATURE)
    
    # Get statistics
    stats = omnidexer.get_statistics()
    print(f"Loaded {stats['total_items']} items")

asyncio.run(example())
```

### Using the Tag Resolver
```python
import asyncio
from src.core.loaders.omnidexer import Omnidexer
from src.core.indexer.tag_resolver import TagResolver

async def example():
    omnidexer = Omnidexer()
    await omnidexer.load_all_data()
    
    resolver = TagResolver(omnidexer)
    
    # Process text with tags
    text = "Cast {@spell Fireball|PHB} at the {@creature Ancient Red Dragon|MM}!"
    latex_output = resolver.process_text(text)
    print(latex_output)
    # Output: "Cast \textit{Fireball} at the \textbf{Ancient Red Dragon}!"

asyncio.run(example())
```

## Build Scripts (Legacy - Still Functional)

### `scripts/build.sh` - Complete Build Tool
```bash
# Build an adventure
./scripts/build.sh adventure json_data/adventures/cos.json

# Build a book with images  
./scripts/build.sh book json_data/books/book-egw.json --with-images

# List available JSON files
./scripts/build.sh list

# Clean build artifacts
./scripts/build.sh clean
```

**Commands:**
- `adventure <json>` - Build adventure PDF
- `book <json>` - Build book PDF  
- `article <json>` - Build article PDF
- `list` - Show available JSON files
- `clean` - Remove build artifacts
- `setup` - Install dependencies

**Options:**
- `--with-images` - Include images (default: no images)
- `--no-items` - Don't add item lists
- `--no-creatures` - Don't add creature lists
- `--no-compile` - Generate LaTeX only, skip PDF

## Dependencies

**Environment Management:**
- `uv` - Fast Python package manager and environment manager

**Core Python packages** (defined in `pyproject.toml`):
- `pydantic>=2.0.0` - Data validation and settings management
- `pydantic-settings>=2.0.0` - Environment-based configuration
- `typer>=0.9.0` - Modern CLI framework
- `rich>=13.0.0` - Rich console output
- `pyyaml>=6.0.0` - YAML configuration file support
- `requests>=2.31.0` - HTTP requests for data fetching
- `beautifulsoup4>=4.12.0` - HTML/XML parsing
- `colorlog>=6.0.0` - Colored logging output
- `GetOptions>=1.0.3` - Legacy command line option parsing

**Development packages** (`--extra dev`):
- `pytest>=7.0.0` - Testing framework
- `pytest-asyncio>=0.21.0` - Async test support
- `pytest-cov>=4.0.0` - Coverage reporting
- `black` - Code formatting
- `ruff` - Fast Python linter
- `mypy` - Static type checking

**Optional packages:**
- `images` group: `Pillow` for image processing
- `xml` group: `lxml` for faster XML parsing

**LaTeX requirements:**
- XeLaTeX (for PDF compilation)
- D&D fonts (included in `assets/fonts/`)

## Development

### Running Tests
```bash
# Run all tests
uv run pytest tests/ -v

# Run specific test categories
uv run pytest tests/unit/ -v                    # Unit tests
uv run pytest tests/unit/test_models.py -v      # Model validation tests
uv run pytest tests/unit/test_omnidexer.py -v   # Data loading tests
uv run pytest tests/unit/test_tag_resolver.py -v # Tag processing tests

# Run with coverage
uv run pytest tests/ --cov=src --cov-report=html
```

### Code Quality
```bash
# Format code
uv run black src/ tests/

# Lint code  
uv run ruff check src/ tests/

# Type checking
uv run mypy src/
```

### Development Workflow
1. **Make changes** to the modern architecture in `src/core/`
2. **Add tests** in `tests/unit/` for new functionality
3. **Run tests** to ensure everything works: `uv run pytest tests/unit/ -v`
4. **Format and lint** code: `uv run black src/ && uv run ruff check src/`

## Architecture Overview

### ✅ **ALL PHASES COMPLETE** ✅

**Phase 1: Foundation (`src/core/`)**
- **Data Models** - Type-safe Pydantic v2 models for all D&D content types
- **Omnidexer System** - Efficient async data loading with hash-based indexing
- **Tag Resolution** - Complete `{@type name|source|display}` tag parsing with 25+ handlers
- **Configuration** - Environment-based settings with automatic path detection
- **Caching** - Performance optimization with disk-based caching system

**Phase 2: Rendering System (`src/renderers/`)**
- **Abstract Interfaces** - Clean renderer base classes for multiple output formats
- **LaTeX Pipeline** - Complete document generation with D&D-style templates
- **Content Renderers** - Specialized rendering for spells, creatures, items, adventures
- **Template Engine** - Flexible system with built-in D&D layouts and custom templates

**Phase 3: Modern CLI & Migration (`src/cli/`)**
- **Modern CLI** - Professional interface with Typer, Rich output, and async operations
- **Legacy Compatibility** - Full backwards compatibility for existing scripts and workflows  
- **Build Integration** - Updated build scripts supporting both modern and legacy modes
- **Performance** - Optimized with caching, parallel processing, and efficient data loading

### 📊 **System Status**
- **100+ Tests** across all components with comprehensive coverage
- **Type Safety** throughout with modern Python patterns
- **Async Architecture** for optimal performance
- **Extensible Design** ready for new content types and output formats

## 🔧 Content Configuration System

### Configurable Sources
5e2pdf now uses a modern content source system instead of hardcoded paths:

**Supported Source Types:**
- **GitHub Repositories** - Automatically clone and update from GitHub (recommended)
- **Local Directories** - Point to existing JSON data directories  
- **Web URLs** - Fetch content from web sources (future feature)

**Default Configuration:**
- **5etools Official** - `https://github.com/5etools-mirror-3/5etools-src`
- **5etools Homebrew** - `https://github.com/TheGiddyLimit/homebrew`

### Configuration Files
Configuration is stored in platform-appropriate locations:
- **Linux/macOS**: `~/.config/5e2pdf/config.yaml`
- **Windows**: `%APPDATA%/5e2pdf/config.yaml`
- **Cache**: `~/.cache/5e2pdf/` (repositories and indexes)

### Setup Wizard
```bash
# Interactive setup with multiple options
uv run 5e2pdf setup wizard

# Options available:
# 1. Use defaults (5etools official + homebrew) - RECOMMENDED
# 2. Custom setup (add your own sources)  
# 3. Local only (use existing directories)
```

### Migration from Legacy Symlinks
If you have existing symlinks (`data`, `5eimages`, `homebrew`), you can:

1. **Use the defaults** (recommended):
   ```bash
   uv run 5e2pdf sources defaults
   ```

2. **Add local directories**:
   ```bash
   uv run 5e2pdf sources add local-data --type directory --path ./data
   uv run 5e2pdf sources add local-homebrew --type directory --path ./homebrew
   ```

3. **Check configuration status**:
   ```bash
   uv run 5e2pdf setup check
   ```

## Migration Notes

### For Existing Users
- **Legacy scripts still work** - `./scripts/build.sh` and `./scripts/json2tex.sh` are fully functional
- **New architecture is additive** - old functionality remains while new capabilities are added
- **Gradual migration** - you can start using new features without changing your existing workflow
- **Content sources replace symlinks** - No more manual symlink management, sources are configured and managed automatically

### For Developers  
- **Modern Python patterns** - Type hints, async/await, dependency injection
- **Comprehensive testing** - 96% test coverage with both unit and integration tests
- **Extensible design** - Easy to add new content types, output formats, and tag handlers
- **Clear separation of concerns** - Data models, loading, processing, and rendering are cleanly separated

## Support

- **Issues**: Report bugs or request features in GitHub Issues
- **Documentation**: See `REFACTORING_PLAN.md` for detailed architecture documentation
- **Tests**: Run `uv run pytest tests/ -v` to validate your setup
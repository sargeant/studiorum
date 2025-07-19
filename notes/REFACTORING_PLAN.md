# 5e2pdf Refactoring Plan: Modern Python Architecture

**Date:** 2025-07-11
**Goal:** Refactor the existing 5e2pdf codebase to use modern Python architecture patterns, inspired by the 5etools data loading system, while maintaining compatibility with existing LaTeX generation workflow.

## Executive Summary

The current 5e2pdf codebase works for ~75% of D&D 5e JSON data but suffers from architectural issues that make it difficult to maintain and extend. This plan outlines a complete refactoring to implement:

1. **Modern Python patterns** - Type safety with Pydantic, dependency injection, async/await
2. **Separation of concerns** - Clear boundaries between data loading, processing, and rendering
3. **Omnidexer system** - Efficient cross-reference resolution inspired by 5etools
4. **Plugin architecture** - Extensible system for new content types and output formats
5. **Incremental migration** - Backwards compatibility during transition

## Current State Analysis

### Existing Architecture Issues

**Current codebase locations:**
- `src/json2tex.py` - Main converter script (monolithic)
- `src/dndtex/` - Core rendering module with mixed responsibilities
- `src/dndtex/Renderer.py` - Single large class handling everything
- `src/dndtex/InTextTagRenderer.py` - Global state tag processing

**Problems identified:**
1. **Monolithic design** - Single `Renderer` class handles document structure, content rendering, and tag processing
2. **Global state** - Static dictionaries for creature/spell/item lists
3. **Hard-coded paths** - No abstraction for data sources
4. **Limited extensibility** - Hard to add new content types
5. **No omnidexer** - Missing efficient cross-reference system

### Current Data Flow
```
JSON File → Renderer.__init__ → renderRecursive → LaTeX Output
                ↓
        InTextTagRenderer (global state)
                ↓
        Tag resolution with file lookups
```

## Target Architecture

### Directory Structure
```
src/
├── core/
│   ├── models/           # Pydantic data models for all content types
│   │   ├── __init__.py
│   │   ├── content.py    # Base content models
│   │   ├── spells.py     # Spell data models
│   │   ├── creatures.py  # Creature/monster models
│   │   ├── items.py      # Equipment and magic items
│   │   ├── adventures.py # Adventure content models
│   │   └── books.py      # Book structure models
│   ├── loaders/          # Data loading and indexing system
│   │   ├── __init__.py
│   │   ├── base.py       # Abstract loader interfaces
│   │   ├── json_loader.py # JSON file loading with validation
│   │   ├── omnidexer.py  # Cross-reference indexing system
│   │   └── source_manager.py # Handle multiple data sources
│   ├── indexer/          # Cross-reference resolution engine
│   │   ├── __init__.py
│   │   ├── tag_resolver.py # Parse and resolve {@type} tags
│   │   └── reference_index.py # Efficient lookup structures
│   └── config/           # Configuration management
│       ├── __init__.py
│       ├── settings.py   # Application settings
│       └── paths.py      # Path configuration
├── renderers/
│   ├── base/             # Abstract renderer interfaces
│   │   ├── __init__.py
│   │   ├── renderer.py   # Base renderer abstract class
│   │   └── document.py   # Document structure interface
│   ├── latex/            # LaTeX-specific renderers
│   │   ├── __init__.py
│   │   ├── document_renderer.py # Main LaTeX document orchestrator
│   │   ├── spell_renderer.py    # Spell statblock rendering
│   │   ├── creature_renderer.py # Creature statblock rendering
│   │   ├── item_renderer.py     # Item description rendering
│   │   ├── table_renderer.py    # Table formatting
│   │   └── adventure_renderer.py # Adventure content rendering
│   └── tags/             # Tag processing system
│       ├── __init__.py
│       ├── tag_processor.py # Tag processing pipeline
│       └── tag_registry.py  # Tag type registration
├── processors/
│   ├── content/          # Content type processors
│   │   ├── __init__.py
│   │   ├── adventure_processor.py # Adventure JSON processing
│   │   ├── book_processor.py      # Book JSON processing
│   │   └── supplement_processor.py # Other content processing
│   └── transformers/     # Data transformation pipeline
│       ├── __init__.py
│       ├── pipeline.py   # Main processing pipeline
│       └── content_transformer.py # Content transformation logic
└── cli/                  # Command-line interface
    ├── __init__.py
    ├── main.py           # New CLI entry point
    └── legacy.py         # Backwards compatibility layer
```

### Core Components Design

#### 1. Data Models (`core/models/`)

**Base Content Model:**
```python
# core/models/content.py
from pydantic import BaseModel, Field
from typing import List, Optional, Union, Dict, Any, Literal
from enum import Enum

class ContentType(str, Enum):
    ADVENTURE = "adventure"
    BOOK = "book"
    SPELL = "spell"
    CREATURE = "creature"
    ITEM = "item"
    CLASS = "class"
    BACKGROUND = "background"
    FEAT = "feat"
    RACE = "race"

class Source(BaseModel):
    """Represents a D&D source book reference."""
    abbreviation: str = Field(..., description="Source book abbreviation (e.g., 'PHB', 'MM')")
    name: str = Field(..., description="Full source book name")
    page: Optional[int] = Field(None, description="Page number reference")
    url: Optional[str] = Field(None, description="URL reference")

class BaseContent(BaseModel):
    """Base class for all D&D content."""
    name: str = Field(..., description="Content name")
    source: Source = Field(..., description="Source book reference")

    class Config:
        # Allow extra fields for flexibility
        extra = "allow"
        # Use enum values for serialization
        use_enum_values = True
```

**Spell Model:**
```python
# core/models/spells.py
from typing import List, Dict, Any, Optional, Union
from .content import BaseContent

class SpellComponent(BaseModel):
    verbal: bool = Field(False, alias="v")
    somatic: bool = Field(False, alias="s")
    material: Union[bool, str] = Field(False, alias="m")

class SpellDuration(BaseModel):
    type: Literal["instant", "timed", "permanent", "special"]
    duration: Optional[Dict[str, Any]] = None
    concentration: bool = False

class Spell(BaseContent):
    """Represents a D&D spell."""
    level: int = Field(..., ge=0, le=9, description="Spell level (0-9)")
    school: str = Field(..., description="School of magic")
    casting_time: List[Dict[str, Any]] = Field(..., alias="time")
    range: Dict[str, Any] = Field(..., description="Spell range")
    components: SpellComponent = Field(..., description="Spell components")
    duration: List[SpellDuration] = Field(..., description="Spell duration")
    entries: List[str] = Field(..., description="Spell description")
    higher_level: Optional[List[str]] = Field(None, alias="entriesHigherLevel")
    damage_inflict: Optional[List[str]] = Field(None, alias="damageInflict")
    saving_throw: Optional[List[str]] = Field(None, alias="savingThrow")
    spell_attack: Optional[List[str]] = Field(None, alias="spellAttack")
```

**Creature Model:**
```python
# core/models/creatures.py
from typing import List, Dict, Any, Optional, Union
from .content import BaseContent

class ArmorClass(BaseModel):
    ac: int
    from_: Optional[List[str]] = Field(None, alias="from")
    condition: Optional[str] = None

class HitPoints(BaseModel):
    average: int
    formula: str

class Creature(BaseContent):
    """Represents a D&D creature/monster."""
    size: List[str] = Field(..., description="Creature size")
    type: Union[str, Dict[str, Any]] = Field(..., description="Creature type")
    alignment: List[str] = Field(..., description="Creature alignment")

    # Combat stats
    ac: List[ArmorClass] = Field(..., description="Armor class")
    hp: HitPoints = Field(..., description="Hit points")
    speed: Dict[str, Union[int, Dict[str, Any]]] = Field(..., description="Movement speeds")

    # Ability scores
    str: int = Field(..., ge=1, le=30)
    dex: int = Field(..., ge=1, le=30)
    con: int = Field(..., ge=1, le=30)
    int: int = Field(..., ge=1, le=30)
    wis: int = Field(..., ge=1, le=30)
    cha: int = Field(..., ge=1, le=30)

    # Optional attributes
    save: Optional[Dict[str, str]] = None
    skill: Optional[Dict[str, str]] = None
    senses: Optional[List[str]] = None
    passive: Optional[int] = None
    languages: Optional[List[str]] = None
    cr: Optional[Union[str, int, Dict[str, Any]]] = None

    # Abilities
    trait: Optional[List[Dict[str, Any]]] = None
    action: Optional[List[Dict[str, Any]]] = None
    legendary_actions: Optional[int] = Field(None, alias="legendaryActions")
    legendary: Optional[List[Dict[str, Any]]] = None
    reaction: Optional[List[Dict[str, Any]]] = None
```

#### 2. Omnidexer System (`core/loaders/`)

**Abstract Loader Interface:**
```python
# core/loaders/base.py
from abc import ABC, abstractmethod
from typing import TypeVar, Generic, List, Optional, Dict, Any
from pathlib import Path
from ..models.content import ContentType, BaseContent

T = TypeVar('T', bound=BaseContent)

class DataLoader(ABC, Generic[T]):
    """Abstract base class for data loaders."""

    @abstractmethod
    async def load(self, path: Path) -> List[T]:
        """Load data from file and return validated content objects."""
        pass

    @abstractmethod
    def get_content_type(self) -> ContentType:
        """Return the content type this loader handles."""
        pass

class SourceManager(ABC):
    """Manages multiple data sources and their priorities."""

    @abstractmethod
    def get_data_paths(self) -> Dict[ContentType, List[Path]]:
        """Return paths to data files organized by content type."""
        pass

    @abstractmethod
    def resolve_source(self, source_abbrev: str) -> Optional[Dict[str, Any]]:
        """Resolve source abbreviation to full source information."""
        pass
```

**JSON Loader Implementation:**
```python
# core/loaders/json_loader.py
import json
import asyncio
from typing import List, Type, Dict, Any
from pathlib import Path
from pydantic import ValidationError
from .base import DataLoader, T
from ..models.content import ContentType
from ..config.settings import get_logger

logger = get_logger(__name__)

class JsonDataLoader(DataLoader[T]):
    """Loads and validates JSON data using Pydantic models."""

    def __init__(self, model_class: Type[T], content_type: ContentType):
        self.model_class = model_class
        self.content_type = content_type

    async def load(self, path: Path) -> List[T]:
        """Load JSON file and validate against Pydantic model."""
        try:
            logger.info(f"Loading {self.content_type} data from {path}")

            # Read JSON file
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Extract content based on file structure
            content_list = self._extract_content(data)

            # Validate each item
            validated_content = []
            for item in content_list:
                try:
                    validated_item = self.model_class.parse_obj(item)
                    validated_content.append(validated_item)
                except ValidationError as e:
                    logger.warning(f"Validation failed for item {item.get('name', 'unknown')}: {e}")

            logger.info(f"Successfully loaded {len(validated_content)} {self.content_type} items")
            return validated_content

        except Exception as e:
            logger.error(f"Failed to load {path}: {e}")
            return []

    def get_content_type(self) -> ContentType:
        return self.content_type

    def _extract_content(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract content list from various JSON structures."""
        # Handle different JSON structures from 5etools
        if 'spell' in data:
            return data['spell']
        elif 'monster' in data:
            return data['monster']
        elif 'item' in data:
            return data['item']
        elif 'adventure' in data:
            return data['adventure']
        elif 'book' in data:
            return data['book']
        elif isinstance(data, list):
            return data
        else:
            # Fallback: look for any list in the data
            for value in data.values():
                if isinstance(value, list) and value:
                    return value
            return []
```

**Omnidexer Implementation:**
```python
# core/loaders/omnidexer.py
import asyncio
from typing import Dict, List, Optional, Any, Set
from pathlib import Path
from collections import defaultdict
import hashlib

from .base import DataLoader, SourceManager
from .json_loader import JsonDataLoader
from ..models.content import ContentType, BaseContent
from ..models.spells import Spell
from ..models.creatures import Creature
from ..models.items import Item
from ..config.settings import get_logger

logger = get_logger(__name__)

class IndexEntry:
    """Represents an indexed content entry."""

    def __init__(self, content: BaseContent, content_type: ContentType):
        self.content = content
        self.content_type = content_type
        self.name = content.name
        self.source = content.source.abbreviation
        self.hash = self._generate_hash()

    def _generate_hash(self) -> str:
        """Generate unique hash for this content."""
        identifier = f"{self.content_type}:{self.name}:{self.source}"
        return hashlib.md5(identifier.encode()).hexdigest()[:8]

class Omnidexer:
    """Central indexing system for all D&D content, inspired by 5etools."""

    def __init__(self, source_manager: SourceManager):
        self.source_manager = source_manager
        self._index: Dict[str, IndexEntry] = {}
        self._by_type: Dict[ContentType, Dict[str, IndexEntry]] = defaultdict(dict)
        self._by_source: Dict[str, List[IndexEntry]] = defaultdict(list)
        self._loaders: Dict[ContentType, DataLoader] = {}
        self._loaded: Set[ContentType] = set()

    def register_loader(self, content_type: ContentType, loader: DataLoader):
        """Register a data loader for a specific content type."""
        self._loaders[content_type] = loader
        logger.info(f"Registered loader for {content_type}")

    async def load_all_data(self, data_path: Optional[Path] = None):
        """Load all available data and build comprehensive index."""
        logger.info("Starting omnidexer data loading...")

        # Get data paths from source manager
        data_paths = self.source_manager.get_data_paths()

        # Load each content type
        load_tasks = []
        for content_type, paths in data_paths.items():
            if content_type in self._loaders:
                for path in paths:
                    task = self._load_content_type(content_type, path)
                    load_tasks.append(task)

        # Execute all loading tasks concurrently
        results = await asyncio.gather(*load_tasks, return_exceptions=True)

        # Process results
        total_loaded = 0
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Loading failed: {result}")
            else:
                total_loaded += result

        logger.info(f"Omnidexer loaded {total_loaded} total items across {len(self._by_type)} content types")
        self._log_index_stats()

    async def _load_content_type(self, content_type: ContentType, path: Path) -> int:
        """Load a specific content type from path."""
        if content_type not in self._loaders:
            logger.warning(f"No loader registered for {content_type}")
            return 0

        loader = self._loaders[content_type]
        content_items = await loader.load(path)

        # Index all loaded items
        for item in content_items:
            self._add_to_index(item, content_type)

        self._loaded.add(content_type)
        return len(content_items)

    def _add_to_index(self, content: BaseContent, content_type: ContentType):
        """Add content item to all indexes."""
        entry = IndexEntry(content, content_type)

        # Primary hash-based index
        self._index[entry.hash] = entry

        # Type-based index
        type_key = f"{entry.name}|{entry.source}".lower()
        self._by_type[content_type][type_key] = entry

        # Source-based index
        self._by_source[entry.source].append(entry)

    def find(self, content_type: ContentType, name: str, source: Optional[str] = None) -> Optional[BaseContent]:
        """Find content by type, name, and optionally source."""
        if content_type not in self._by_type:
            return None

        type_index = self._by_type[content_type]

        if source:
            key = f"{name}|{source}".lower()
            entry = type_index.get(key)
            return entry.content if entry else None
        else:
            # Search all sources for this name
            for key, entry in type_index.items():
                if key.startswith(f"{name.lower()}|"):
                    return entry.content
            return None

    def find_by_hash(self, hash_id: str) -> Optional[BaseContent]:
        """Find content by unique hash identifier."""
        entry = self._index.get(hash_id)
        return entry.content if entry else None

    def get_all_by_type(self, content_type: ContentType) -> List[BaseContent]:
        """Get all content of a specific type."""
        if content_type not in self._by_type:
            return []
        return [entry.content for entry in self._by_type[content_type].values()]

    def get_all_by_source(self, source: str) -> List[BaseContent]:
        """Get all content from a specific source."""
        entries = self._by_source.get(source, [])
        return [entry.content for entry in entries]

    def search(self, query: str, content_type: Optional[ContentType] = None) -> List[BaseContent]:
        """Search for content by name (fuzzy matching)."""
        query_lower = query.lower()
        results = []

        search_types = [content_type] if content_type else self._by_type.keys()

        for ctype in search_types:
            for entry in self._by_type[ctype].values():
                if query_lower in entry.name.lower():
                    results.append(entry.content)

        return results

    def _log_index_stats(self):
        """Log statistics about the loaded index."""
        logger.info("Omnidexer Index Statistics:")
        logger.info(f"  Total items: {len(self._index)}")
        for content_type, items in self._by_type.items():
            logger.info(f"  {content_type}: {len(items)} items")
        logger.info(f"  Sources: {len(self._by_source)}")
```

#### 3. Tag Resolution System (`core/indexer/`)

**Tag Resolver:**
```python
# core/indexer/tag_resolver.py
import re
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass

from ..loaders.omnidexer import Omnidexer
from ..models.content import ContentType
from ..config.settings import get_logger

logger = get_logger(__name__)

@dataclass
class TagMatch:
    """Represents a parsed tag match."""
    tag_type: str
    name: str
    source: Optional[str] = None
    display_text: Optional[str] = None
    page: Optional[str] = None
    full_match: str = ""

class TagResolver:
    """Resolves {@type name|source|display} tags to actual content references."""

    # Pattern matches: {@creature Strahd von Zarovich|CoS|the vampire lord}
    TAG_PATTERN = re.compile(r'{@(\w+)\s+([^}]+)}')

    def __init__(self, omnidexer: Omnidexer):
        self.omnidexer = omnidexer
        self._tag_handlers: Dict[str, Callable[[TagMatch], str]] = {}
        self._register_default_handlers()

    def _register_default_handlers(self):
        """Register default tag handlers for common content types."""
        self._tag_handlers.update({
            'creature': self._handle_creature_tag,
            'spell': self._handle_spell_tag,
            'item': self._handle_item_tag,
            'adventure': self._handle_adventure_tag,
            'book': self._handle_book_tag,
            'class': self._handle_class_tag,
            'background': self._handle_background_tag,
            'feat': self._handle_feat_tag,
            'race': self._handle_race_tag,
            'dice': self._handle_dice_tag,
            'bold': self._handle_bold_tag,
            'italic': self._handle_italic_tag,
        })

    def register_tag_handler(self, tag_type: str, handler: Callable[[TagMatch], str]):
        """Register a custom tag handler."""
        self._tag_handlers[tag_type] = handler
        logger.info(f"Registered handler for tag type: {tag_type}")

    def process_text(self, text: str) -> str:
        """Process text and resolve all tags to formatted output."""
        if not text or '{@' not in text:
            return text

        def replace_tag(match):
            try:
                tag_match = self._parse_tag(match)
                return self._resolve_tag(tag_match)
            except Exception as e:
                logger.warning(f"Failed to resolve tag {match.group(0)}: {e}")
                return match.group(0)  # Return original if resolution fails

        return self.TAG_PATTERN.sub(replace_tag, text)

    def _parse_tag(self, match: re.Match) -> TagMatch:
        """Parse a tag match into components."""
        tag_type = match.group(1)
        content = match.group(2)
        full_match = match.group(0)

        # Split content by | separator
        parts = [part.strip() for part in content.split('|')]

        name = parts[0] if parts else ""
        source = parts[1] if len(parts) > 1 else None
        display_text = parts[2] if len(parts) > 2 else None
        page = parts[3] if len(parts) > 3 else None

        return TagMatch(
            tag_type=tag_type,
            name=name,
            source=source,
            display_text=display_text,
            page=page,
            full_match=full_match
        )

    def _resolve_tag(self, tag_match: TagMatch) -> str:
        """Resolve a parsed tag to formatted output."""
        handler = self._tag_handlers.get(tag_match.tag_type)
        if not handler:
            logger.warning(f"No handler for tag type: {tag_match.tag_type}")
            return tag_match.full_match

        try:
            return handler(tag_match)
        except Exception as e:
            logger.error(f"Handler failed for {tag_match.tag_type}: {e}")
            return tag_match.full_match

    # Tag Handlers

    def _handle_creature_tag(self, tag: TagMatch) -> str:
        """Handle {@creature} tags."""
        content = self.omnidexer.find(ContentType.CREATURE, tag.name, tag.source)
        if not content:
            logger.warning(f"Creature not found: {tag.name} ({tag.source})")
            return tag.display_text or tag.name

        display = tag.display_text or content.name
        return f"\\textbf{{{display}}}"  # LaTeX bold formatting

    def _handle_spell_tag(self, tag: TagMatch) -> str:
        """Handle {@spell} tags."""
        content = self.omnidexer.find(ContentType.SPELL, tag.name, tag.source)
        if not content:
            logger.warning(f"Spell not found: {tag.name} ({tag.source})")
            return tag.display_text or tag.name

        display = tag.display_text or content.name
        return f"\\textit{{{display}}}"  # LaTeX italic formatting

    def _handle_item_tag(self, tag: TagMatch) -> str:
        """Handle {@item} tags."""
        content = self.omnidexer.find(ContentType.ITEM, tag.name, tag.source)
        if not content:
            logger.warning(f"Item not found: {tag.name} ({tag.source})")
            return tag.display_text or tag.name

        display = tag.display_text or content.name
        return f"\\textit{{{display}}}"  # LaTeX italic formatting

    def _handle_adventure_tag(self, tag: TagMatch) -> str:
        """Handle {@adventure} tags."""
        display = tag.display_text or tag.name
        if tag.page:
            return f"{display} (p. {tag.page})"
        return display

    def _handle_book_tag(self, tag: TagMatch) -> str:
        """Handle {@book} tags."""
        display = tag.display_text or tag.name
        if tag.page:
            return f"{display}, p. {tag.page}"
        return display

    def _handle_class_tag(self, tag: TagMatch) -> str:
        """Handle {@class} tags."""
        display = tag.display_text or tag.name
        return f"\\textbf{{{display}}}"

    def _handle_background_tag(self, tag: TagMatch) -> str:
        """Handle {@background} tags."""
        display = tag.display_text or tag.name
        return display

    def _handle_feat_tag(self, tag: TagMatch) -> str:
        """Handle {@feat} tags."""
        display = tag.display_text or tag.name
        return f"\\textbf{{{display}}}"

    def _handle_race_tag(self, tag: TagMatch) -> str:
        """Handle {@race} tags."""
        display = tag.display_text or tag.name
        return display

    def _handle_dice_tag(self, tag: TagMatch) -> str:
        """Handle {@dice} tags."""
        return f"\\texttt{{{tag.name}}}"  # Monospace for dice notation

    def _handle_bold_tag(self, tag: TagMatch) -> str:
        """Handle {@bold} tags."""
        return f"\\textbf{{{tag.name}}}"

    def _handle_italic_tag(self, tag: TagMatch) -> str:
        """Handle {@italic} tags."""
        return f"\\textit{{{tag.name}}}"
```

#### 4. Rendering System (`renderers/`)

**Base Renderer Interface:**
```python
# renderers/base/renderer.py
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from ...core.models.content import BaseContent, ContentType

class ContentRenderer(ABC):
    """Abstract base class for content renderers."""

    @abstractmethod
    def render(self, content: BaseContent, context: Optional[Dict[str, Any]] = None) -> str:
        """Render content to output format."""
        pass

    @abstractmethod
    def get_supported_type(self) -> ContentType:
        """Return the content type this renderer supports."""
        pass

class DocumentRenderer(ABC):
    """Abstract base class for document-level renderers."""

    @abstractmethod
    def render_document(self, content: List[Any], metadata: Dict[str, Any]) -> str:
        """Render complete document with content and metadata."""
        pass

    @abstractmethod
    def get_file_extension(self) -> str:
        """Return appropriate file extension for this renderer."""
        pass
```

**LaTeX Document Renderer:**
```python
# renderers/latex/document_renderer.py
from typing import Dict, List, Any, Optional
from pathlib import Path

from ..base.renderer import DocumentRenderer, ContentRenderer
from ...core.indexer.tag_resolver import TagResolver
from ...core.models.content import ContentType
from ...config.settings import get_logger

logger = get_logger(__name__)

class LaTeXDocumentRenderer(DocumentRenderer):
    """Main LaTeX document renderer that orchestrates content rendering."""

    def __init__(self,
                 tag_resolver: TagResolver,
                 content_renderers: Dict[ContentType, ContentRenderer],
                 assets_path: Optional[Path] = None):
        self.tag_resolver = tag_resolver
        self.content_renderers = content_renderers
        self.assets_path = assets_path or Path("assets")

    def render_document(self, content: List[Any], metadata: Dict[str, Any]) -> str:
        """Render complete LaTeX document."""
        logger.info(f"Rendering document: {metadata.get('name', 'Unknown')}")

        # Build document structure
        parts = [
            self._render_preamble(metadata),
            self._render_begin_document(),
            self._render_content(content),
            self._render_end_document()
        ]

        # Join all parts and process tags
        document = '\n'.join(parts)
        document = self.tag_resolver.process_text(document)

        logger.info("Document rendering complete")
        return document

    def get_file_extension(self) -> str:
        return ".tex"

    def _render_preamble(self, metadata: Dict[str, Any]) -> str:
        """Render document preamble with packages and settings."""
        doc_class = metadata.get('document_class', 'dndarticle')

        preamble = f"""\\documentclass[letterpaper,twocolumn,openany]{{{doc_class}}}

% Core packages
\\usepackage[utf8]{{inputenc}}
\\usepackage[T1]{{fontenc}}
\\usepackage{{graphicx}}
\\usepackage{{array}}
\\usepackage{{tabularx}}
\\usepackage{{longtable}}
\\usepackage{{booktabs}}
\\usepackage{{xcolor}}

% Font setup
\\usepackage{{fontspec}}
\\setmainfont{{Bookinsanity}}[
    Path={self.assets_path}/fonts/,
    Extension=.otf,
    UprightFont=*,
    BoldFont=*-Bold,
    ItalicFont=*-Italic,
    BoldItalicFont=*-BoldItalic
]

% DND-specific styling
\\usepackage{{dnd}}

% Document metadata
\\title{{{metadata.get('title', 'D\\&D Document')}}}
\\author{{{metadata.get('author', '')}}}
\\date{{}}

"""
        return preamble

    def _render_begin_document(self) -> str:
        """Render document beginning."""
        return "\\begin{document}\n\\maketitle\n"

    def _render_content(self, content: List[Any]) -> str:
        """Render main document content."""
        rendered_sections = []

        for item in content:
            try:
                rendered = self._render_content_item(item)
                if rendered:
                    rendered_sections.append(rendered)
            except Exception as e:
                logger.error(f"Failed to render content item: {e}")
                # Include error comment in output for debugging
                rendered_sections.append(f"% ERROR: Failed to render item - {e}")

        return '\n\n'.join(rendered_sections)

    def _render_content_item(self, item: Any) -> str:
        """Render a single content item."""
        if isinstance(item, dict):
            item_type = item.get('type', 'unknown')

            # Handle different content types
            if item_type == 'section':
                return self._render_section(item)
            elif item_type == 'entries':
                return self._render_entries(item)
            elif item_type == 'list':
                return self._render_list(item)
            elif item_type == 'table':
                return self._render_table(item)
            elif item_type == 'image':
                return self._render_image(item)
            elif item_type == 'inset':
                return self._render_inset(item)
            elif item_type == 'insetReadaloud':
                return self._render_readaloud(item)
            else:
                logger.warning(f"Unknown content type: {item_type}")
                return f"% Unknown content type: {item_type}"

        elif isinstance(item, str):
            return item

        else:
            logger.warning(f"Unexpected content item type: {type(item)}")
            return str(item)

    def _render_section(self, section: Dict[str, Any]) -> str:
        """Render a section with heading and content."""
        name = section.get('name', '')
        entries = section.get('entries', [])

        # Determine section level (could be enhanced)
        level = "\\section"

        header = f"{level}{{{name}}}" if name else ""
        content = self._render_entries({'entries': entries})

        return f"{header}\n{content}" if header else content

    def _render_entries(self, entries_block: Dict[str, Any]) -> str:
        """Render a block of entries."""
        entries = entries_block.get('entries', [])
        if not entries:
            return ""

        rendered_entries = []
        for entry in entries:
            rendered = self._render_content_item(entry)
            if rendered:
                rendered_entries.append(rendered)

        return '\n\n'.join(rendered_entries)

    def _render_list(self, list_item: Dict[str, Any]) -> str:
        """Render various list types."""
        list_type = list_item.get('style', 'list-no-bullets')
        items = list_item.get('items', [])

        if not items:
            return ""

        if list_type == 'list-no-bullets':
            env = 'itemize'
        elif list_type == 'list-hang-notitle':
            env = 'description'
        else:
            env = 'itemize'

        item_lines = []
        for item in items:
            if isinstance(item, dict):
                item_text = self._render_content_item(item)
            else:
                item_text = str(item)
            item_lines.append(f"\\item {item_text}")

        return f"\\begin{{{env}}}\n" + '\n'.join(item_lines) + f"\n\\end{{{env}}}"

    def _render_table(self, table: Dict[str, Any]) -> str:
        """Render tables."""
        caption = table.get('caption', '')
        col_labels = table.get('colLabels', [])
        rows = table.get('rows', [])

        if not rows:
            return ""

        # Simple table rendering (could be enhanced)
        num_cols = len(col_labels) if col_labels else len(rows[0]) if rows else 0
        col_spec = 'l' * num_cols

        lines = [f"\\begin{{tabular}}{{{col_spec}}}"]
        lines.append("\\toprule")

        # Header
        if col_labels:
            header = ' & '.join(col_labels) + " \\\\"
            lines.append(header)
            lines.append("\\midrule")

        # Rows
        for row in rows:
            if isinstance(row, list):
                row_text = ' & '.join(str(cell) for cell in row) + " \\\\"
                lines.append(row_text)

        lines.append("\\bottomrule")
        lines.append("\\end{tabular}")

        if caption:
            return f"\\begin{{table}}[h]\n\\centering\n" + '\n'.join(lines) + f"\n\\caption{{{caption}}}\n\\end{{table}}"
        else:
            return '\n'.join(lines)

    def _render_image(self, image: Dict[str, Any]) -> str:
        """Render images."""
        href = image.get('href', '')
        if not href:
            return ""

        # Simple image inclusion
        return f"\\includegraphics[width=\\textwidth]{{{href}}}"

    def _render_inset(self, inset: Dict[str, Any]) -> str:
        """Render sidebar insets."""
        name = inset.get('name', '')
        entries = inset.get('entries', [])

        content = self._render_entries({'entries': entries})

        if name:
            return f"\\begin{{dndreadtext}}\n\\textbf{{{name}}}\n\n{content}\n\\end{{dndreadtext}}"
        else:
            return f"\\begin{{dndreadtext}}\n{content}\n\\end{{dndreadtext}}"

    def _render_readaloud(self, readaloud: Dict[str, Any]) -> str:
        """Render read-aloud text boxes."""
        entries = readaloud.get('entries', [])
        content = self._render_entries({'entries': entries})

        return f"\\begin{{dndreadtext}}\n{content}\n\\end{{dndreadtext}}"

    def _render_end_document(self) -> str:
        """Render document end."""
        return "\\end{document}"
```

#### 5. Processing Pipeline (`processors/`)

**Main Processing Pipeline:**
```python
# processors/transformers/pipeline.py
import asyncio
from typing import Dict, List, Any, Optional
from pathlib import Path

from ...core.loaders.omnidexer import Omnidexer
from ...core.models.content import ContentType
from ..content.adventure_processor import AdventureProcessor
from ..content.book_processor import BookProcessor
from ...config.settings import get_logger

logger = get_logger(__name__)

class ProcessingPipeline:
    """Main processing pipeline that transforms JSON data into renderable content."""

    def __init__(self,
                 omnidexer: Omnidexer,
                 processors: Optional[Dict[str, Any]] = None):
        self.omnidexer = omnidexer
        self.processors = processors or {}
        self._register_default_processors()

    def _register_default_processors(self):
        """Register default content processors."""
        self.processors.update({
            'adventure': AdventureProcessor(self.omnidexer),
            'book': BookProcessor(self.omnidexer),
        })

    async def process(self, input_file: Path, options: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process input file and return structured content ready for rendering."""
        logger.info(f"Processing file: {input_file}")

        options = options or {}

        try:
            # Load and parse JSON
            import json
            with open(input_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Determine content type and processor
            processor_type = self._detect_content_type(data, options)
            processor = self.processors.get(processor_type)

            if not processor:
                raise ValueError(f"No processor available for type: {processor_type}")

            # Process the data
            processed_content = await processor.process(data, options)

            logger.info(f"Successfully processed {len(processed_content.get('content', []))} content items")
            return processed_content

        except Exception as e:
            logger.error(f"Failed to process {input_file}: {e}")
            raise

    def _detect_content_type(self, data: Dict[str, Any], options: Dict[str, Any]) -> str:
        """Detect the type of content from data structure and options."""
        # Check explicit options first
        if options.get('adventure'):
            return 'adventure'
        elif options.get('book'):
            return 'book'
        elif options.get('article'):
            return 'article'

        # Detect from data structure
        if 'adventure' in data or 'adventureData' in data:
            return 'adventure'
        elif 'book' in data or 'bookData' in data:
            return 'book'
        else:
            # Default to article for other content
            return 'article'
```

### Implementation Phases

#### Phase 1: Foundation (Weeks 1-2)

**Week 1 Tasks:**
1. Create core data models in `core/models/`
2. Implement base loader interfaces in `core/loaders/base.py`
3. Build JSON loader with Pydantic validation
4. Create basic configuration system

**Week 1 Deliverables:**
- All Pydantic models for spells, creatures, items, adventures
- JsonDataLoader with validation
- Basic test suite for models and loaders
- Configuration management system

**Week 2 Tasks:**
1. Implement Omnidexer system
2. Build tag resolution engine
3. Create source manager for multiple data sources
4. Add comprehensive logging

**Week 2 Deliverables:**
- Fully functional Omnidexer with indexing
- TagResolver with support for all common tag types
- Source manager handling multiple data directories
- Performance benchmarks for data loading

#### Phase 2: Rendering Abstraction (Weeks 3-4)

**Week 3 Tasks:**
1. Create abstract renderer interfaces
2. Implement LaTeX document renderer
3. Build content-specific renderers (spells, creatures, etc.)
4. Create rendering pipeline

**Week 3 Deliverables:**
- Complete renderer interface hierarchy
- LaTeX document renderer with preamble generation
- Spell and creature renderers
- Basic rendering pipeline

**Week 4 Tasks:**
1. Implement remaining content renderers
2. Add table and image rendering
3. Create processing pipeline
4. Build adventure and book processors

**Week 4 Deliverables:**
- All content type renderers
- Table and image rendering support
- Complete processing pipeline
- Adventure and book processors

#### Phase 3: Integration and Migration (Weeks 5-6)

**Week 5 Tasks:**
1. Create new CLI interface
2. Build legacy compatibility layer
3. Migrate existing configuration options
4. Add integration tests

**Week 5 Deliverables:**
- New CLI with modern argument parsing
- Backwards compatibility with existing scripts
- Full configuration migration
- Integration test suite

**Week 6 Tasks:**
1. Performance optimization
2. Error handling improvements
3. Documentation generation
4. Final testing and validation

**Week 6 Deliverables:**
- Optimized performance (target: 2x faster than current)
- Comprehensive error handling
- Complete documentation
- Validated migration path

### Migration Strategy

#### Backwards Compatibility

**During Transition:**
1. Keep existing `json2tex.py` working
2. New CLI available as `json2tex-v2.py`
3. Both systems share asset files
4. Gradual feature migration

**Legacy Support:**
```python
# cli/legacy.py
"""Legacy compatibility layer for existing scripts."""

def legacy_main():
    """Main function that maintains existing CLI interface."""
    # Parse old-style arguments
    # Map to new system
    # Execute with new backend
    # Return results in expected format
```

#### Feature Parity Checklist

**Must maintain:**
- [ ] All existing command-line options
- [ ] Same LaTeX output quality
- [ ] Asset file locations
- [ ] Build script compatibility
- [ ] Error message formats

**Improvements delivered:**
- [ ] 2x faster processing speed
- [ ] Better error reporting
- [ ] Type safety with validation
- [ ] Extensible architecture
- [ ] Modern Python patterns

### Testing Strategy

#### Unit Tests
- [ ] All Pydantic models with validation
- [ ] Omnidexer indexing and lookup
- [ ] Tag resolution for all tag types
- [ ] Individual content renderers
- [ ] Processing pipeline components

#### Integration Tests
- [ ] End-to-end file processing
- [ ] CLI compatibility tests
- [ ] LaTeX compilation verification
- [ ] Performance benchmarks
- [ ] Memory usage validation

#### Test Data
- [ ] Sample files for each content type
- [ ] Edge cases and malformed data
- [ ] Large files for performance testing
- [ ] Cross-reference validation datasets

### Dependencies and Requirements

#### New Dependencies
```toml
# pyproject.toml additions
dependencies = [
    "pydantic>=2.0.0",    # Data validation and settings
    "asyncio",            # Async processing
    "typer>=0.9.0",       # Modern CLI framework
    "rich>=13.0.0",       # Rich console output
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-asyncio>=0.21.0",
    "pytest-cov>=4.0.0",
    "mypy>=1.0.0",
]
```

#### Development Tools
- [ ] Pre-commit hooks for code quality
- [ ] MyPy for type checking
- [ ] Black for code formatting
- [ ] Pytest for testing framework
- [ ] Coverage reporting

### Success Metrics

#### Performance Targets
- [ ] **Processing Speed:** 2x faster than current implementation
- [ ] **Memory Usage:** <500MB for largest files
- [ ] **Startup Time:** <2 seconds for CLI
- [ ] **Index Building:** <10 seconds for full 5etools dataset

#### Quality Targets
- [ ] **Type Coverage:** >95% with MyPy
- [ ] **Test Coverage:** >90% line coverage
- [ ] **Documentation:** 100% public API documented
- [ ] **Backwards Compatibility:** 100% existing functionality preserved

#### User Experience
- [ ] **Error Messages:** Clear, actionable error reporting
- [ ] **CLI Interface:** Intuitive commands and help text
- [ ] **Documentation:** Complete migration guide
- [ ] **Performance:** Visible speed improvements

### Future Extensibility

#### Plugin Architecture
The new architecture supports:
- Custom content type processors
- Additional output formats (HTML, Markdown)
- Custom tag handlers
- External data sources

#### Potential Extensions
- **Web Interface:** REST API for content processing
- **Database Backend:** PostgreSQL for large datasets
- **Cloud Processing:** AWS Lambda for serverless processing
- **Real-time Updates:** Watch 5etools repos for updates

---

## Summary

This refactoring plan transforms the 5e2pdf codebase from a monolithic script into a modern, maintainable Python application. The new architecture provides:

1. **Separation of concerns** with clear component boundaries
2. **Type safety** through Pydantic models and MyPy
3. **Performance improvements** through efficient indexing and async processing
4. **Extensibility** via plugin architecture and dependency injection
5. **Maintainability** through comprehensive testing and documentation

The 6-week implementation plan ensures a smooth transition while maintaining full backwards compatibility. The resulting system will be faster, more reliable, and much easier to extend for future D&D content processing needs.

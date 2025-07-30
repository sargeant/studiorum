# Content Models API Documentation

## Table of Contents

This page covers the content model APIs:

- [BaseContent](#basecontent)
- [ContentType](#contenttype)
- [Source](#source)
- [Spell Models](#spell-models)
- [Creature Models](#creature-models)
- [Item Models](#item-models)
- [Adventure Models](#adventure-models)
- [Book Models](#book-models)
- [Character Content Models](#character-content-models)
- [Nested Content Models](#nested-content-models)
- [Validation and Error Handling](#validation-and-error-handling)

## Overview

The content models provide strongly-typed representations of D&D content from 5etools JSON data. Built on Pydantic v2, these models offer comprehensive validation, flexible parsing, and rich functionality for content manipulation.

### Key Features

- **Type Safety**: Full Python 3.12 type annotations with mypy compliance
- **Flexible Parsing**: Handles multiple input formats and malformed data gracefully
- **Rich Functionality**: Computed properties, formatting methods, and content extraction
- **Extensible Design**: Protocol-based architecture for custom content types
- **Comprehensive Validation**: Configurable validation modes for different use cases

## BaseContent

**Location**: `src/dnd5e/core/models/content.py`

Base class for all D&D content models.

### Class Definition

```python
class BaseContent(BaseModel):
    """Base class for all D&D content."""

    model_config = ConfigDict(
        extra="allow",          # Allow extra fields from 5etools
        use_enum_values=True,   # Serialize enums as values
    )

    name: str = Field(..., description="Content name")
    source: Source = Field(..., description="Source book reference")
```

### Constructor

```python
def __init__(self, **data: Any) -> None
```

Creates a content object from 5etools JSON data.

**Parameters:**
- `**data`: Keyword arguments from JSON data

**Example:**
```python
from dnd5e.core.models.content import BaseContent

content = BaseContent(
    name="Sample Content",
    source="PHB"  # Automatically converted to Source object
)
```

### Fields

#### name

```python
name: str = Field(..., description="Content name")
```

The display name of the content item.

#### source

```python
source: Source = Field(..., description="Source book reference")
```

Source book information. Accepts string, dict, or Source object.

**Input formats:**
```python
# String format
source="PHB"

# Dict format
source={"abbreviation": "PHB", "page": 123}

# Source object
source=Source(abbreviation="PHB", name="Player's Handbook", page=123)
```

### Validation

The base content model includes flexible source parsing:

```python
@field_validator("source", mode="before")
@classmethod
def parse_source(cls, v: str | dict[str, str] | Source) -> dict[str, str] | Source:
    """Handle flexible source format parsing."""
    if isinstance(v, str):
        return {"abbreviation": v, "name": v}
    return v
```

## ContentType

**Location**: `src/dnd5e/core/models/content.py`

Enumeration of supported D&D content types.

### Enum Definition

```python
class ContentType(str, Enum):
    """Enumeration of supported D&D content types."""

    # Core content types
    ADVENTURE = "adventure"
    BOOK = "book"
    SPELL = "spell"
    CREATURE = "creature"
    ITEM = "item"
    CLASS = "class"
    CLASS_FEATURE = "classFeature"
    SUBCLASS_FEATURE = "subclassFeature"
    BACKGROUND = "background"
    FEAT = "feat"
    RACE = "race"
    SUPPLEMENT = "supplement"

    # Fluff content types
    SPELL_FLUFF = "spellFluff"
    CREATURE_FLUFF = "creatureFluff"
    ITEM_FLUFF = "itemFluff"

    # Adventure nested content types
    ADVENTURE_SECTION = "adventureSection"
    ADVENTURE_TABLE = "adventureTable"
    ADVENTURE_NPC = "adventureNpc"
    ADVENTURE_LOCATION = "adventureLocation"
    ADVENTURE_INSET = "adventureInset"

    # Book nested content types
    BOOK_SECTION = "bookSection"
    VARIANT_RULE = "variantRule"
    BOOK_TABLE = "bookTable"
    BOOK_INSET = "bookInset"
```

### Class Methods

#### from_content

```python
@classmethod
def from_content(cls, content: BaseContent) -> ContentType
```

Determines content type from content object.

**Parameters:**
- `content` (BaseContent): Content object to analyze

**Returns:**
- `ContentType`: Corresponding content type

**Example:**
```python
from dnd5e.core.models.spells import Spell
from dnd5e.core.models.content import ContentType

spell = Spell(name="Fireball", ...)
content_type = ContentType.from_content(spell)
# Returns: ContentType.SPELL
```

## Source

**Location**: `src/dnd5e/core/models/content.py`

Represents a D&D source book reference.

### Class Definition

```python
class Source(BaseModel):
    """Represents a D&D source book reference."""

    abbreviation: str = Field(..., description="Source book abbreviation (e.g., 'PHB', 'MM')")
    name: str | None = Field(None, description="Full source book name")
    page: int | None = Field(None, description="Page number reference")
    url: str | None = Field(None, description="URL reference")
```

### Constructor

```python
def __init__(self, **data: Any) -> None
```

**Example:**
```python
from dnd5e.core.models.content import Source

# Minimal source
source = Source(abbreviation="PHB")

# Complete source
source = Source(
    abbreviation="PHB",
    name="Player's Handbook",
    page=257,
    url="https://example.com"
)
```

### Methods

#### model_post_init

```python
def model_post_init(self, __context: dict | None) -> None
```

Sets name to abbreviation if not provided.

#### __str__

```python
def __str__(self) -> str
```

Returns formatted source reference.

**Returns:**
- `str`: Formatted as "PHB, p. 257" or just "PHB" if no page

**Example:**
```python
source = Source(abbreviation="PHB", page=257)
print(str(source))  # "PHB, p. 257"
```

## Spell Models

**Location**: `src/dnd5e/core/models/spells.py`

Models for representing spell data with comprehensive D&D mechanics.

### Spell

Main spell content model with full 5etools compatibility.

```python
class Spell(BaseContent):
    """Spell content model with comprehensive D&D mechanics."""

    level: int = Field(..., description="Spell level (0-9)")
    school: str = Field(..., description="School of magic")
    time: list[SpellTime] = Field(..., description="Casting time")
    range: SpellRange = Field(..., description="Spell range")
    components: SpellComponent = Field(..., description="V/S/M components")
    duration: list[SpellDuration] = Field(..., description="Duration")
    entries: list[Any] = Field(..., description="Spell description entries")

    # Optional fields
    ritual: bool = Field(False, description="Can be cast as ritual")
    classes: dict[str, list[str]] | None = Field(None, description="Class availability")
    damage: dict[str, Any] | None = Field(None, description="Damage information")
    save: dict[str, str] | None = Field(None, description="Saving throw info")
```

#### Methods

##### get_formatted_level

```python
def get_formatted_level(self) -> str
```

Returns human-readable spell level.

**Returns:**
- `str`: "Cantrip", "1st-level", "2nd-level", etc.

##### get_formatted_components

```python
def get_formatted_components(self) -> str
```

Returns formatted component string.

**Returns:**
- `str`: "V, S, M (component description)"

##### get_formatted_duration

```python
def get_formatted_duration(self) -> str
```

Returns formatted duration string.

**Returns:**
- `str`: "Instantaneous", "Concentration, up to 1 minute", etc.

### SpellComponent

```python
class SpellComponent(BaseModel):
    """Represents spell components (V, S, M)."""

    verbal: bool = Field(False, alias="v", description="Verbal component required")
    somatic: bool = Field(False, alias="s", description="Somatic component required")
    material: bool | str = Field(False, alias="m", description="Material component")
```

#### Validation

```python
@field_validator("material", mode="before")
@classmethod
def parse_material(cls, v: Any) -> bool | str:
    """Handle various material component formats."""
    if isinstance(v, dict) and "text" in v:
        return str(v["text"])
    elif isinstance(v, str):
        return v
    return bool(v)
```

### SpellTime

```python
class SpellTime(BaseModel):
    """Represents casting time."""

    number: int = Field(1, description="Number of time units")
    unit: str = Field(..., description="Time unit (action, bonus action, etc.)")
    condition: str | None = Field(None, description="Conditional casting time")
```

### SpellRange

```python
class SpellRange(BaseModel):
    """Represents spell range."""

    type: str = Field(..., description="Range type (point, line, cone, etc.)")
    distance: dict[str, Any] | None = Field(None, description="Distance specification")
```

### SpellDuration

```python
class SpellDuration(BaseModel):
    """Represents spell duration."""

    type: Literal["instant", "timed", "permanent", "special"]
    duration: dict[str, Any] | None = None
    concentration: bool = False
```

## Creature Models

**Location**: `src/dnd5e/core/models/creatures.py`

Models for monster and NPC data with computed statistics.

### Creature

```python
class Creature(BaseContent):
    """Monster/NPC model with comprehensive stat block support."""

    # Basic information
    type: str | dict[str, Any] = Field(..., description="Creature type")
    size: str = Field(..., description="Size category")
    alignment: str | list[str] = Field(..., description="Alignment")

    # Combat statistics
    ac: list[ArmorClass] = Field(..., description="Armor class")
    hp: HitPoints = Field(..., description="Hit points")
    speed: Speed = Field(..., description="Movement speeds")

    # Ability scores
    str: int = Field(..., description="Strength score")
    dex: int = Field(..., description="Dexterity score")
    con: int = Field(..., description="Constitution score")
    int: int = Field(..., description="Intelligence score")
    wis: int = Field(..., description="Wisdom score")
    cha: int = Field(..., description="Charisma score")

    # Derived statistics
    save: dict[str, str] | None = Field(None, description="Saving throws")
    skill: dict[str, str] | None = Field(None, description="Skills")
    passive: int | None = Field(None, description="Passive Perception")

    # Challenge and experience
    cr: str | int | dict[str, Any] = Field(..., description="Challenge rating")
```

#### Properties

##### ability_scores

```python
@property
def ability_scores(self) -> dict[str, int]
```

Returns all ability scores as a dictionary.

##### ability_modifiers

```python
@property
def ability_modifiers(self) -> dict[str, int]
```

Calculates and returns all ability modifiers.

#### Methods

##### get_proficiency_bonus

```python
def get_proficiency_bonus(self) -> int
```

Calculates proficiency bonus from challenge rating.

**Returns:**
- `int`: Proficiency bonus (2-6)

##### get_formatted_type

```python
def get_formatted_type(self) -> str
```

Returns formatted creature type with size and alignment.

**Returns:**
- `str`: "Medium humanoid (human), lawful good"

### ArmorClass

```python
class ArmorClass(BaseModel):
    """Represents creature armor class."""

    ac: int | None = Field(None, description="Armor class value")
    from_: list[str] | None = Field(None, alias="from", description="AC sources")
    condition: str | None = Field(None, description="Conditional AC")
    special: str | None = Field(None, description="Special AC description")
```

### HitPoints

```python
class HitPoints(BaseModel):
    """Represents creature hit points."""

    average: int | None = Field(None, description="Average hit points")
    formula: str | None = Field(None, description="Hit dice formula")
    special: str | None = Field(None, description="Special HP description")
```

### Speed

```python
class Speed(BaseModel):
    """Represents creature movement speeds."""

    walk: int | dict[str, Any] | None = Field(None, description="Walking speed")
    fly: int | dict[str, Any] | None = Field(None, description="Flying speed")
    swim: int | dict[str, Any] | None = Field(None, description="Swimming speed")
    climb: int | dict[str, Any] | None = Field(None, description="Climbing speed")
    burrow: int | dict[str, Any] | None = Field(None, description="Burrowing speed")
```

## Item Models

**Location**: `src/dnd5e/core/models/items.py`

Models for equipment, magic items, and treasure.

### Item

```python
class Item(BaseContent):
    """Equipment and magic item model."""

    type: str = Field(..., description="Item type category")
    rarity: str | None = Field(None, description="Item rarity")
    weight: int | float | None = Field(None, description="Item weight in pounds")
    value: int | None = Field(None, description="Item value in copper pieces")

    # Equipment properties
    ac: int | None = Field(None, description="Armor class (for armor)")
    damage: str | None = Field(None, description="Damage dice (for weapons)")
    property: list[str] | None = Field(None, description="Weapon/armor properties")

    # Magic item properties
    requires_attunement: bool = Field(False, description="Requires attunement")
    charges: int | None = Field(None, description="Number of charges")

    # Description
    entries: list[Any] = Field(default_factory=list, description="Item description")
```

#### Methods

##### get_formatted_value

```python
def get_formatted_value(self) -> str
```

Returns formatted value in appropriate currency.

**Returns:**
- `str`: "50 gp", "2 sp", "5 cp", etc.

##### is_magic_item

```python
def is_magic_item(self) -> bool
```

Determines if item is magical based on rarity and properties.

**Returns:**
- `bool`: True if item is magical

##### get_formatted_properties

```python
def get_formatted_properties(self) -> str
```

Returns comma-separated property list.

**Returns:**
- `str`: "Light, finesse, thrown (range 20/60)"

## Adventure Models

**Location**: `src/dnd5e/core/models/adventures.py`

Models for adventure content with chapter structure.

### Adventure

```python
class Adventure(BaseContent):
    """Adventure content model with chapter organization."""

    id: str = Field(..., description="Adventure identifier")
    storyline: str | None = Field(None, description="Adventure storyline/campaign")
    level: dict[str, int] | None = Field(None, description="Level range")
    published: str | None = Field(None, description="Publication date")

    # Content structure
    contents: list[dict[str, Any]] = Field(default_factory=list, description="Table of contents")

    # Adventure data
    adventure: list[dict[str, Any]] = Field(default_factory=list, description="Adventure content")
```

#### Properties

##### chapters

```python
@property
def chapters(self) -> list[Chapter]
```

Returns parsed chapter objects from adventure content.

##### has_content

```python
@property
def has_content(self) -> bool
```

Determines if adventure has actual content (not just metadata).

#### Methods

##### get_level_range

```python
def get_level_range(self) -> str
```

Returns formatted level range.

**Returns:**
- `str`: "1st-5th level", "Any level", etc.

##### get_deep_index_entries

```python
def get_deep_index_entries(self) -> list[IndexEntry]
```

Extracts all indexable content from the adventure.

**Returns:**
- `list[IndexEntry]`: All indexable content entries

### Chapter

**Location**: `src/dnd5e/core/models/chapter.py`

```python
class Chapter(BaseModel):
    """Represents an adventure or book chapter."""

    name: str = Field(..., description="Chapter name")
    index: int | None = Field(None, description="Chapter number/index")
    entries: list[Any] = Field(default_factory=list, description="Chapter content")
    page: int | None = Field(None, description="Starting page number")
```

## Book Models

**Location**: `src/dnd5e/core/models/books.py`

Models for rulebooks and supplements.

### Book

```python
class Book(BaseContent):
    """Book/supplement content model."""

    id: str = Field(..., description="Book identifier")
    group: str | None = Field(None, description="Book group/category")
    published: str | None = Field(None, description="Publication date")

    # Content structure
    contents: list[dict[str, Any]] = Field(default_factory=list, description="Table of contents")

    # Book data
    book: list[dict[str, Any]] = Field(default_factory=list, description="Book content")
```

#### Properties

##### chapters

```python
@property
def chapters(self) -> list[Chapter]
```

Returns parsed chapter objects from book content.

##### has_content

```python
@property
def has_content(self) -> bool
```

Determines if book has actual content.

## Character Content Models

### Class

**Location**: `src/dnd5e/core/models/classes.py`

```python
class Class(BaseContent):
    """Character class model."""

    hd: dict[str, int] = Field(..., description="Hit dice information")
    proficiency: list[str] = Field(..., description="Proficiency categories")
    startingProficiencies: dict[str, Any] = Field(..., description="Starting proficiencies")
    startingEquipment: dict[str, Any] | None = Field(None, description="Starting equipment")

    # Class features
    classFeatures: list[str] = Field(default_factory=list, description="Class feature references")
    subclassTitle: str | None = Field(None, description="Subclass title")

    # Class table
    classTableGroups: list[dict[str, Any]] | None = Field(None, description="Class progression table")
```

### Race

**Location**: `src/dnd5e/core/models/races.py`

```python
class Race(BaseContent):
    """Player race model."""

    size: str | list[str] = Field(..., description="Size category")
    speed: int | dict[str, Any] = Field(..., description="Base speed")

    # Racial traits
    entries: list[Any] = Field(default_factory=list, description="Racial trait descriptions")
    ability: list[dict[str, Any]] | None = Field(None, description="Ability score increases")

    # Optional traits
    darkvision: int | None = Field(None, description="Darkvision range")
    languages: dict[str, Any] | None = Field(None, description="Known languages")
    skillProficiencies: dict[str, Any] | None = Field(None, description="Skill proficiencies")
```

### Background

**Location**: `src/dnd5e/core/models/backgrounds.py`

```python
class Background(BaseContent):
    """Character background model."""

    skillProficiencies: dict[str, Any] | None = Field(None, description="Skill proficiencies")
    languageProficiencies: dict[str, Any] | None = Field(None, description="Language proficiencies")
    toolProficiencies: dict[str, Any] | None = Field(None, description="Tool proficiencies")
    startingEquipment: dict[str, Any] | None = Field(None, description="Starting equipment")

    # Background feature
    entries: list[Any] = Field(default_factory=list, description="Background descriptions")
```

### Feat

**Location**: `src/dnd5e/core/models/feats.py`

```python
class Feat(BaseContent):
    """Feat/feature model."""

    prerequisite: dict[str, Any] | None = Field(None, description="Feat prerequisites")
    ability: list[dict[str, Any]] | None = Field(None, description="Ability score improvements")
    entries: list[Any] = Field(..., description="Feat description")

    # Additional properties
    additionalSpells: list[dict[str, Any]] | None = Field(None, description="Spells granted by feat")
```

## Nested Content Models

**Location**: `src/dnd5e/core/models/nested_content.py`

Models for content extracted from adventures and books.

### Section

```python
class Section(BaseContent):
    """Represents a section within an adventure or book."""

    entries: list[Any] = Field(default_factory=list, description="Section content")
    page: int | None = Field(None, description="Page number")
    chapter: str | None = Field(None, description="Chapter reference")
    depth: int = Field(1, description="Nesting depth")
```

### Table

```python
class Table(BaseContent):
    """Represents a table with structured data."""

    colLabels: list[str] = Field(..., description="Column headers")
    colStyles: list[str] | None = Field(None, description="Column styling")
    rows: list[list[Any]] = Field(..., description="Table rows")
    caption: str | None = Field(None, description="Table caption")
```

#### Methods

##### to_latex

```python
def to_latex(self) -> str
```

Generates LaTeX table representation.

**Returns:**
- `str`: LaTeX table code using DND template

### Inset

```python
class Inset(BaseContent):
    """Represents sidebar or inset content."""

    entries: list[Any] = Field(..., description="Inset content")
    inset_type: str = Field("sidebar", description="Type of inset")
```

### VariantRule

```python
class VariantRule(BaseContent):
    """Represents an optional/variant rule."""

    entries: list[Any] = Field(..., description="Rule description")
    ruleType: str | None = Field(None, description="Type of rule")
```

## Validation and Error Handling

### Validation Modes

Content models support different validation modes:

```python
from dnd5e.core.entry_registry import ValidationMode

# Strict validation - fails on unknown fields
ValidationMode.STRICT

# Liberal validation - warns on unknown fields
ValidationMode.LIBERAL

# Permissive validation - ignores unknown fields
ValidationMode.PERMISSIVE
```

### Custom Validation

Add custom validation to models:

```python
from pydantic import field_validator, model_validator

class CustomSpell(Spell):
    """Spell with additional validation."""

    @field_validator("level")
    @classmethod
    def validate_spell_level(cls, v: int) -> int:
        if not 0 <= v <= 9:
            raise ValueError(f"Spell level must be 0-9, got {v}")
        return v

    @model_validator(mode="after")
    def validate_cantrip_school(self) -> "CustomSpell":
        if self.level == 0 and self.school not in ["evocation", "conjuration"]:
            raise ValueError("Cantrips must be evocation or conjuration")
        return self
```

### Error Context

Content models provide rich error context:

```python
from dnd5e.core.exceptions import EntryProcessingError

try:
    spell = Spell(**invalid_data)
except ValidationError as e:
    # Pydantic validation errors
    for error in e.errors():
        print(f"Field {error['loc']}: {error['msg']}")

except EntryProcessingError as e:
    # 5e2pdf specific errors with context
    print(f"Error: {e}")
    if e.source:
        print(f"Source: {e.source}")
    if e.entry:
        print(f"Entry: {e.entry}")
```

## Usage Examples

### Basic Content Creation

```python
from dnd5e.core.models.spells import Spell

# Create spell from JSON data
spell_data = {
    "name": "Magic Missile",
    "source": "PHB",
    "level": 1,
    "school": "evocation",
    "time": [{"number": 1, "unit": "action"}],
    "range": {"type": "point", "distance": {"type": "feet", "amount": 120}},
    "components": {"v": True, "s": True},
    "duration": [{"type": "instant"}],
    "entries": ["You create three glowing darts of magical force..."]
}

spell = Spell(**spell_data)
print(f"Level: {spell.get_formatted_level()}")
print(f"Components: {spell.get_formatted_components()}")
```

### Content Type Resolution

```python
from dnd5e.core.models.content import ContentType

# Determine content type from object
content_type = ContentType.from_content(spell)
print(f"Content type: {content_type}")  # ContentType.SPELL

# Use in conditional logic
if content_type == ContentType.SPELL:
    print(f"Processing spell: {spell.name}")
```

### Deep Indexing

```python
from dnd5e.core.models.adventures import Adventure

# Load adventure with deep indexing
adventure = Adventure(**adventure_data)

if hasattr(adventure, 'get_deep_index_entries'):
    index_entries = adventure.get_deep_index_entries()
    print(f"Found {len(index_entries)} indexable items")

    for entry in index_entries:
        print(f"- {entry.name} ({entry.type})")
```

### Flexible Source Handling

```python
from dnd5e.core.models.content import Source

# Various source input formats
sources = [
    "PHB",                                          # String
    {"abbreviation": "MM", "page": 123},           # Dict
    Source(abbreviation="VGtM", name="Volo's Guide to Monsters")  # Object
]

for source_data in sources:
    content = BaseContent(name="Test", source=source_data)
    print(f"Source: {content.source}")
```

### Batch Processing with Validation

```python
from pydantic import ValidationError

def process_content_batch(data_list: list[dict]) -> list[BaseContent]:
    """Process multiple content items with error handling."""

    results = []
    errors = []

    for i, data in enumerate(data_list):
        try:
            # Determine content type and create appropriate model
            if "level" in data and "school" in data:
                content = Spell(**data)
            elif "cr" in data and "ac" in data:
                content = Creature(**data)
            else:
                content = BaseContent(**data)

            results.append(content)

        except ValidationError as e:
            errors.append(f"Item {i}: {e}")
        except Exception as e:
            errors.append(f"Item {i}: Unexpected error: {e}")

    if errors:
        print(f"Processing completed with {len(errors)} errors:")
        for error in errors:
            print(f"  {error}")

    return results
```

## Performance Considerations

### Memory Usage

Content models are designed for efficiency:

```python
# Use __slots__ for memory optimization in custom models
class OptimizedContent(BaseContent):
    __slots__ = ('name', 'source', '_custom_field')

    def __init__(self, **data):
        super().__init__(**data)
        self._custom_field = None
```

### Lazy Loading

Implement lazy loading for expensive operations:

```python
from functools import cached_property

class LazyAdventure(Adventure):
    """Adventure with lazy-loaded properties."""

    @cached_property
    def extracted_content(self) -> list[BaseContent]:
        """Lazily extract nested content."""
        return self._extract_all_content()

    @cached_property
    def content_by_type(self) -> dict[ContentType, list[BaseContent]]:
        """Group content by type for efficient access."""
        grouped = {}
        for content in self.extracted_content:
            content_type = ContentType.from_content(content)
            grouped.setdefault(content_type, []).append(content)
        return grouped
```

### Serialization

Optimize serialization for large datasets:

```python
# Efficient JSON serialization
def serialize_content_batch(content_items: list[BaseContent]) -> str:
    """Serialize content batch efficiently."""

    # Use model_dump for Pydantic v2
    serialized = [item.model_dump(exclude_unset=True) for item in content_items]

    # Use orjson for faster serialization if available
    try:
        import orjson
        return orjson.dumps(serialized).decode()
    except ImportError:
        import json
        return json.dumps(serialized)
```

## Thread Safety

Content models are generally thread-safe for read operations:

- **Immutable after creation**: Models should not be modified after validation
- **Computed properties**: Use `@cached_property` for thread-safe caching
- **Shared instances**: Safe to share model instances between threads

For concurrent modification:

```python
import threading
from copy import deepcopy

class ThreadSafeContent:
    """Thread-safe wrapper for content models."""

    def __init__(self, content: BaseContent):
        self._content = content
        self._lock = threading.RLock()

    def get_copy(self) -> BaseContent:
        """Get thread-safe copy of content."""
        with self._lock:
            return deepcopy(self._content)

    def update(self, **updates) -> BaseContent:
        """Create updated copy with new data."""
        with self._lock:
            data = self._content.model_dump()
            data.update(updates)
            return type(self._content)(**data)
```

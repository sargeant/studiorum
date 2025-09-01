# Coding Standards

Code style and quality requirements for 5e2pdf contributions.

## Code Style Guidelines

### Python Version and Features

5e2pdf targets Python 3.12+ and uses modern Python features:

```python
# Use Python 3.12+ type hints
from typing import override
from collections.abc import Sequence

class SpellProcessor:
    def __init__(self, spells: Sequence[Spell]) -> None:
        self.spells = spells

    @override
    def process(self) -> ProcessingResult:
        """Override annotation for clarity."""
        return super().process()
```

### Code Formatting

#### Ruff Configuration
The project uses ruff for both linting and formatting:

```bash
# Format code automatically
uv run ruff format src/ tests/

# Check for style issues
uv run ruff check src/ tests/

# Fix auto-fixable issues
uv run ruff check --fix src/ tests/
```

#### Line Length and Wrapping
- Maximum line length: 88 characters
- Use Black-compatible formatting rules
- Break long expressions at logical points

```python
# Good: Logical breaking points
spell_description = (
    "A bright streak flashes from your pointing finger to a point "
    "you choose within range and then blossoms with a low roar "
    "into an explosion of flame."
)

# Good: Function argument wrapping
def create_spell_renderer(
    template_engine: TemplateEngine,
    output_format: OutputFormat,
    validation_mode: ValidationMode = ValidationMode.STRICT,
) -> SpellRenderer:
    pass
```

#### Import Organization
Imports are automatically organized by ruff:

```python
# Standard library imports (alphabetical)
import json
from pathlib import Path
from typing import Any, Optional

# Third-party imports (alphabetical)
import click
from pydantic import BaseModel, Field

# Local imports (alphabetical within each level)
from dnd5e.core.config import Config
from dnd5e.core.models import BaseContent, ContentType
from dnd5e.core.models.spells import Spell
```

### Naming Conventions

#### Variables and Functions
```python
# Use snake_case for variables and functions
spell_count = 0
content_types = [ContentType.SPELL, ContentType.MONSTER]

def parse_spell_data(raw_data: dict[str, Any]) -> Spell:
    """Parse raw JSON data into Spell object."""
    pass

# Use descriptive names
def calculate_spell_save_dc(
    base_dc: int,
    ability_modifier: int,
    proficiency_bonus: int
) -> int:
    """Calculate spell save DC using D&D 5e rules."""
    return base_dc + ability_modifier + proficiency_bonus
```

#### Classes and Types
```python
# Use PascalCase for classes
class SpellParser:
    """Parse spell data from various formats."""
    pass

class ContentValidationError(ValueError):
    """Raised when content fails validation."""
    pass

# Use PascalCase for type aliases
SpellList = list[Spell]
ContentMapping = dict[ContentType, list[BaseContent]]
```

#### Constants
```python
# Use SCREAMING_SNAKE_CASE for constants
MAX_SPELL_LEVEL = 9
DEFAULT_CACHE_SIZE = 128
SUPPORTED_CONTENT_TYPES = frozenset([
    ContentType.SPELL,
    ContentType.MONSTER,
    ContentType.ITEM,
])
```

#### Private Members
```python
class ContentProcessor:
    def __init__(self) -> None:
        self._cache: dict[str, Any] = {}  # Protected member
        self.__secret_key = "internal"   # Private member

    def _validate_content(self, content: BaseContent) -> bool:
        """Protected method for internal use."""
        pass

    def __generate_cache_key(self, content: BaseContent) -> str:
        """Private method for implementation details."""
        pass
```

## Type Annotations

### Comprehensive Type Hints

All functions, methods, and class attributes must have type annotations:

```python
from typing import Any, Optional, Union
from collections.abc import Sequence, Mapping

class SpellRenderer:
    """Render spells in various formats."""

    # Class attributes with types
    default_format: str = "latex"
    supported_formats: frozenset[str] = frozenset(["latex", "html", "markdown"])

    def __init__(
        self,
        config: Config,
        template_cache: Optional[Mapping[str, str]] = None
    ) -> None:
        """Initialize renderer with configuration."""
        self.config: Config = config
        self.template_cache: Mapping[str, str] = template_cache or {}
        self._rendered_count: int = 0

    def render_spell(
        self,
        spell: Spell,
        format_type: str = "latex"
    ) -> str:
        """Render single spell to specified format."""
        pass

    def render_multiple(
        self,
        spells: Sequence[Spell]
    ) -> list[str]:
        """Render multiple spells."""
        pass
```

### Generic Types
```python
from typing import TypeVar, Generic, Protocol

# Type variables for generic classes
T = TypeVar('T', bound=BaseContent)
K = TypeVar('K')
V = TypeVar('V')

class ContentCache(Generic[K, V]):
    """Generic cache for content objects."""

    def __init__(self) -> None:
        self._cache: dict[K, V] = {}

    def get(self, key: K) -> Optional[V]:
        """Get cached value by key."""
        return self._cache.get(key)

    def set(self, key: K, value: V) -> None:
        """Cache value with key."""
        self._cache[key] = value

# Protocol for type safety
class Renderable(Protocol):
    """Protocol for objects that can be rendered."""

    def render(self, format_type: str) -> str:
        """Render object to specified format."""
        ...
```

### Union Types and Optional
```python
# Use modern union syntax (Python 3.10+)
def process_content(
    content: Spell | Monster | Item,
    output_format: str | None = None
) -> str | None:
    """Process various content types."""
    pass

# Use Optional for clarity when needed
from typing import Optional

def find_spell(
    name: str,
    source: Optional[str] = None
) -> Optional[Spell]:
    """Find spell by name and optional source."""
    pass
```

## Error Handling

### Exception Hierarchy
```python
# Define clear exception hierarchy
class DND5eError(Exception):
    """Base exception for all 5e2pdf errors."""
    pass

class ContentError(DND5eError):
    """Base exception for content-related errors."""
    pass

class ValidationError(ContentError):
    """Content validation failed."""

    def __init__(self, message: str, field_name: str | None = None) -> None:
        super().__init__(message)
        self.field_name = field_name

class ParsingError(ContentError):
    """Content parsing failed."""

    def __init__(
        self,
        message: str,
        source_file: str | None = None,
        line_number: int | None = None
    ) -> None:
        super().__init__(message)
        self.source_file = source_file
        self.line_number = line_number
```

### Error Handling Patterns
```python
# Use specific exception handling
def parse_spell_level(level_data: Any) -> int:
    """Parse spell level with clear error handling."""
    try:
        level = int(level_data)
    except (ValueError, TypeError) as e:
        raise ValidationError(
            f"Invalid spell level: {level_data!r}",
            field_name="level"
        ) from e

    if not 0 <= level <= 9:
        raise ValidationError(
            f"Spell level must be 0-9, got {level}",
            field_name="level"
        )

    return level

# Use context managers for resource management
def load_content_file(file_path: Path) -> dict[str, Any]:
    """Load content file with proper error handling."""
    try:
        with open(file_path, 'r') as file:
            content = file.read()
            return json.loads(content)
    except FileNotFoundError:
        raise ContentError(f"Content file not found: {file_path}")
    except json.JSONDecodeError as e:
        raise ParsingError(
            f"Invalid JSON in {file_path}: {e}",
            source_file=str(file_path),
            line_number=e.lineno
        )
```

## Pydantic Model Standards

### Model Design Patterns
```python
from pydantic import BaseModel, Field, validator, root_validator

class Spell(BaseModel):
    """D&D 5e spell with comprehensive validation."""

    # Required fields with validation
    name: str = Field(min_length=1, max_length=100, description="Spell name")
    level: int = Field(ge=0, le=9, description="Spell level (0-9)")
    school: str = Field(description="School of magic")

    # Optional fields with defaults
    ritual: bool = Field(default=False, description="Can be cast as ritual")
    concentration: bool = Field(default=False, description="Requires concentration")

    # Complex fields with validation
    casting_time: list[str] = Field(
        min_items=1,
        description="Casting time requirements"
    )
    range_distance: dict[str, Any] = Field(
        alias="range",
        description="Spell range information"
    )

    # Field validators
    @validator('school')
    def validate_school(cls, v: str) -> str:
        """Validate spell school."""
        valid_schools = {
            "Abjuration", "Conjuration", "Divination", "Enchantment",
            "Evocation", "Illusion", "Necromancy", "Transmutation"
        }
        if v not in valid_schools:
            raise ValueError(f"Invalid school: {v}")
        return v

    # Model validators for cross-field validation
    @root_validator
    def validate_concentration_and_duration(cls, values: dict[str, Any]) -> dict[str, Any]:
        """Validate concentration requirements."""
        concentration = values.get('concentration', False)
        duration = values.get('duration', [])

        if concentration and not any('concentration' in d.lower() for d in duration):
            raise ValueError("Concentration spells must specify concentration in duration")

        return values

    # Custom configuration
    class Config:
        allow_population_by_field_name = True
        validate_assignment = True
        extra = "forbid"  # Reject unknown fields
```

### Validation Patterns
```python
# Use Field constraints for simple validation
class Monster(BaseModel):
    name: str = Field(min_length=1, description="Monster name")
    challenge_rating: float = Field(ge=0, le=30, description="Challenge rating")
    hit_points: int = Field(gt=0, description="Hit points")
    armor_class: int = Field(ge=1, le=30, description="Armor class")

# Use custom validators for complex logic
@validator('hit_dice')
def validate_hit_dice(cls, v: str) -> str:
    """Validate hit dice format (e.g., '8d10+16')."""
    import re
    pattern = r'^\d+d\d+(\+\d+)?$'
    if not re.match(pattern, v):
        raise ValueError(f"Invalid hit dice format: {v}")
    return v

# Use root validators for cross-field validation
@root_validator
def validate_spell_slots(cls, values: dict[str, Any]) -> dict[str, Any]:
    """Validate spell slot progression."""
    caster_level = values.get('caster_level', 0)
    spell_slots = values.get('spell_slots', {})

    # Validate spell slot counts based on caster level
    max_spell_level = min(9, (caster_level + 1) // 2)
    for level_str, slots in spell_slots.items():
        level = int(level_str)
        if level > max_spell_level:
            raise ValueError(f"Caster level {caster_level} cannot have level {level} spells")

    return values
```

## I/O and Resource Management Patterns

### Efficient I/O Operations
```python
# Use efficient I/O operations
def load_all_spells() -> list[Spell]:
    """Load all spells from data sources."""
    file_paths = discover_spell_files()

    # Process files with error handling
    spells = []
    for path in file_paths:
        try:
            spell_list = load_spell_file(path)
            spells.extend(spell_list)
        except Exception as e:
            logger.warning(f"Failed to load spell file {path}: {e}")

    return spells

# Use context managers for resource management
from contextlib import contextmanager
from typing import Generator

@contextmanager
def with_content_lock(content_id: str) -> Generator[None, None, None]:
    """Acquire exclusive lock on content for modification."""
    lock = acquire_content_lock(content_id)
    try:
        yield
    finally:
        release_content_lock(lock)

# Proper error handling with retries
def fetch_remote_content(url: str) -> dict[str, Any]:
    """Fetch content from remote URL with retries."""
    import requests
    import time

    for attempt in range(3):
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            if attempt == 2:  # Last attempt
                raise ContentError(f"Failed to fetch {url}: {e}")
            time.sleep(2 ** attempt)  # Exponential backoff
```

## Documentation Standards

### Docstring Format
Use Google-style docstrings:

```python
def calculate_spell_attack_bonus(
    ability_modifier: int,
    proficiency_bonus: int,
    magical_bonus: int = 0
) -> int:
    """Calculate spell attack bonus using D&D 5e rules.

    The spell attack bonus is calculated as:
    ability modifier + proficiency bonus + magical bonus

    Args:
        ability_modifier: Relevant ability modifier (usually INT, WIS, or CHA)
        proficiency_bonus: Character's proficiency bonus
        magical_bonus: Additional magical bonus from items or features

    Returns:
        Total spell attack bonus

    Raises:
        ValueError: If any modifier is outside reasonable bounds

    Example:
        >>> calculate_spell_attack_bonus(ability_modifier=4, proficiency_bonus=3)
        7
        >>> calculate_spell_attack_bonus(4, 3, magical_bonus=1)
        8
    """
    if not -5 <= ability_modifier <= 10:
        raise ValueError(f"Ability modifier {ability_modifier} out of range")

    if not 2 <= proficiency_bonus <= 6:
        raise ValueError(f"Proficiency bonus {proficiency_bonus} out of range")

    return ability_modifier + proficiency_bonus + magical_bonus
```

### Type Comments for Complex Types
```python
# Use type comments for complex generic types when helpful
spells_by_level: dict[int, list[Spell]] = {}  # Spells grouped by level
content_cache: dict[tuple[ContentType, str], BaseContent] = {}  # Cache by type and name
```

These coding standards ensure consistency, readability, and maintainability across the 5e2pdf codebase.

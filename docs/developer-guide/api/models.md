---
title: Models API
description: Pydantic data models for 5e content with full type safety and validation
---

# Models API

Studiorum uses Pydantic models to represent all 5e content with comprehensive type safety, validation, and serialization support.

## Base Models

### BaseContent

All content models inherit from BaseContent:

```python
from pydantic import BaseModel, ConfigDict, Field
from typing import Literal

class BaseContent(BaseModel):
    """Base class for all 5e content models."""

    model_config = ConfigDict(
        validate_assignment=True,  # Validate on attribute assignment
        extra="forbid",           # Prevent extra fields
        use_enum_values=True      # Serialize enums as values
    )

    name: str = Field(description="Content name")
    source: Source = Field(description="Source book information")
    page: int | None = Field(default=None, description="Page number in source")
```

### Source

Source book information:

```python
@dataclass(frozen=True)
class Source:
    """Immutable source book reference."""

    abbreviation: str      # "SRD", "MY-HOMEBREW", etc.
    full_name: str        # "My Awesome Homebrew"
    version: str = "1.0"  # Source version

    def __str__(self) -> str:
        return self.abbreviation
```

## Core Content Models

### Creatures

Comprehensive creature data model:

```python
from studiorum.core.models.creatures import (
    Creature,
    CreatureSize,
    CreatureType,
    ChallengeRating,
    ArmorClass,
    HitPoints,
    AbilityScores,
    Speed,
    Skill,
    Sense,
    Language,
    Action,
    LegendaryAction,
    SpecialAbility
)

class Creature(BaseContent):
    """Complete 5e creature model."""

    # Basic attributes
    size: CreatureSize
    creature_type: CreatureType
    alignment: Alignment | None = None

    # Combat stats
    challenge_rating: ChallengeRating
    armor_class: ArmorClass
    hit_points: HitPoints
    speeds: list[Speed]

    # Ability scores
    ability_scores: AbilityScores
    saving_throws: dict[AbilityType, int] = {}
    skills: list[Skill] = []

    # Resistances and immunities
    damage_vulnerabilities: list[DamageType] = []
    damage_resistances: list[DamageType] = []
    damage_immunities: list[DamageType] = []
    condition_immunities: list[ConditionType] = []

    # Senses and languages
    senses: list[Sense] = []
    languages: list[Language] = []

    # Abilities and actions
    special_abilities: list[SpecialAbility] = []
    actions: list[Action] = []
    legendary_actions: list[LegendaryAction] = []
    reactions: list[Action] = []
    lair_actions: list[str] = []
    regional_effects: list[str] = []

    # Spellcasting
    spellcasting: SpellcastingInfo | None = None

    @property
    def cr_numeric(self) -> float:
        """Get challenge rating as numeric value."""
        return self.challenge_rating.numeric_value

    @property
    def proficiency_bonus(self) -> int:
        """Calculate proficiency bonus from CR."""
        return self.challenge_rating.proficiency_bonus

    def get_modifier(self, ability: AbilityType) -> int:
        """Get ability modifier."""
        return self.ability_scores.get_modifier(ability)
```

#### Supporting Types

```python
from enum import Enum

class CreatureSize(Enum):
    TINY = "tiny"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    HUGE = "huge"
    GARGANTUAN = "gargantuan"

class CreatureType(Enum):
    ABERRATION = "aberration"
    BEAST = "beast"
    CELESTIAL = "celestial"
    CONSTRUCT = "construct"
    DRAGON = "dragon"
    ELEMENTAL = "elemental"
    FEY = "fey"
    FIEND = "fiend"
    GIANT = "giant"
    HUMANOID = "humanoid"
    MONSTROSITY = "monstrosity"
    OOZE = "ooze"
    PLANT = "plant"
    UNDEAD = "undead"

class ChallengeRating(BaseModel):
    """Challenge rating with XP calculation."""

    rating: str  # "1/8", "1", "10", etc.
    experience_points: int

    @property
    def numeric_value(self) -> float:
        """Convert rating string to numeric value."""
        if "/" in self.rating:
            num, den = self.rating.split("/")
            return float(num) / float(den)
        return float(self.rating)

    @property
    def proficiency_bonus(self) -> int:
        """Calculate proficiency bonus from CR."""
        cr = self.numeric_value
        if cr <= 4:
            return 2
        elif cr <= 8:
            return 3
        elif cr <= 12:
            return 4
        elif cr <= 16:
            return 5
        else:
            return 6

class AbilityScores(BaseModel):
    """Creature ability scores."""

    strength: int = Field(ge=1, le=30)
    dexterity: int = Field(ge=1, le=30)
    constitution: int = Field(ge=1, le=30)
    intelligence: int = Field(ge=1, le=30)
    wisdom: int = Field(ge=1, le=30)
    charisma: int = Field(ge=1, le=30)

    def get_modifier(self, ability: AbilityType) -> int:
        """Calculate ability modifier."""
        score = getattr(self, ability.value)
        return (score - 10) // 2
```

### Spells

Complete spell data model:

```python
from studiorum.core.models.spells import (
    Spell,
    SpellLevel,
    SpellSchool,
    SpellClass,
    CastingTime,
    SpellRange,
    Duration,
    Component,
    SpellDamage,
    HigherLevelEffect
)

class Spell(BaseContent):
    """Complete 5e spell model."""

    # Basic properties
    level: SpellLevel
    school: SpellSchool
    classes: list[SpellClass]

    # Casting information
    casting_time: CastingTime
    spell_range: SpellRange
    duration: Duration
    components: list[Component]

    # Spell details
    description: list[str]  # Structured description paragraphs
    higher_levels: HigherLevelEffect | None = None

    # Flags
    is_ritual: bool = False
    requires_concentration: bool = False

    # Optional properties
    damage: SpellDamage | None = None
    material_component: str | None = None

    @property
    def is_cantrip(self) -> bool:
        """Check if spell is a cantrip."""
        return self.level == SpellLevel.CANTRIP

    @property
    def spell_attack_bonus(self) -> str:
        """Get spell attack bonus formula."""
        return "spell attack bonus"

    @property
    def save_dc(self) -> str:
        """Get save DC formula."""
        return "spell save DC"

# Supporting enums
class SpellLevel(IntEnum):
    CANTRIP = 0
    FIRST = 1
    SECOND = 2
    THIRD = 3
    FOURTH = 4
    FIFTH = 5
    SIXTH = 6
    SEVENTH = 7
    EIGHTH = 8
    NINTH = 9

class SpellSchool(Enum):
    ABJURATION = "abjuration"
    CONJURATION = "conjuration"
    DIVINATION = "divination"
    ENCHANTMENT = "enchantment"
    EVOCATION = "evocation"
    ILLUSION = "illusion"
    NECROMANCY = "necromancy"
    TRANSMUTATION = "transmutation"
```

### Adventures

Structured adventure content:

```python
from studiorum.core.models.adventures import (
    Adventure,
    AdventureChapter,
    AdventureEntry,
    AdventureMetadata,
    PlayerLevels,
    AdventureType
)

class Adventure(BaseContent):
    """Complete adventure model."""

    # Metadata
    adventure_type: AdventureType
    levels: PlayerLevels
    description: str
    background: str | None = None

    # Content structure
    contents: list[AdventureChapter]

    # Additional data
    metadata: AdventureMetadata = AdventureMetadata()

    @property
    def chapter_count(self) -> int:
        """Get number of chapters."""
        return len(self.contents)

    @property
    def estimated_playtime(self) -> str:
        """Get estimated playtime."""
        return self.metadata.estimated_playtime or "Unknown"

class AdventureChapter(BaseModel):
    """Adventure chapter with nested entries."""

    name: str
    entries: list[AdventureEntry]
    order: int = 0

    @property
    def entry_count(self) -> int:
        """Get number of entries in chapter."""
        return len(self.entries)

class AdventureEntry(BaseModel):
    """Flexible adventure entry supporting various content types."""

    # Can be string, dict, or list for maximum flexibility
    content: str | dict[str, Any] | list[Any]
    entry_type: str = "text"

    @property
    def is_text(self) -> bool:
        """Check if entry is simple text."""
        return isinstance(self.content, str)

    @property
    def is_structured(self) -> bool:
        """Check if entry has structured data."""
        return isinstance(self.content, dict)
```

### Items

Magic items and equipment:

```python
from studiorum.core.models.items import (
    Item,
    ItemType,
    ItemRarity,
    AttunementRequirement,
    ItemProperty,
    WeaponProperty,
    ArmorProperty
)

class Item(BaseContent):
    """Magic item and equipment model."""

    # Basic properties
    item_type: ItemType
    rarity: ItemRarity

    # Requirements
    attunement: AttunementRequirement | None = None
    prerequisites: list[str] = []

    # Item details
    description: list[str]
    properties: list[ItemProperty] = []

    # Optional attributes
    weight: float | None = None
    cost: str | None = None  # "500 gp", "priceless", etc.

    # Weapon-specific
    weapon_properties: list[WeaponProperty] = []
    damage: str | None = None  # "1d8 slashing"

    # Armor-specific
    armor_properties: list[ArmorProperty] = []
    armor_class: int | str | None = None  # 14, "16 + Dex modifier", etc.

    @property
    def requires_attunement(self) -> bool:
        """Check if item requires attunement."""
        return self.attunement is not None

    @property
    def is_magical(self) -> bool:
        """Check if item is magical."""
        return self.rarity != ItemRarity.MUNDANE

class ItemRarity(Enum):
    MUNDANE = "mundane"
    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    VERY_RARE = "very rare"
    LEGENDARY = "legendary"
    ARTIFACT = "artifact"
```

## Model Validation

### Custom Validators

Models include custom validation logic:

```python
from pydantic import validator, root_validator

class Creature(BaseContent):
    # ... other fields ...

    @validator('challenge_rating')
    def validate_challenge_rating(cls, v):
        """Validate challenge rating is valid."""
        valid_ratings = [
            "0", "1/8", "1/4", "1/2",
            "1", "2", "3", "4", "5",
            # ... up to 30
        ]
        if v.rating not in valid_ratings:
            raise ValueError(f"Invalid challenge rating: {v.rating}")
        return v

    @validator('ability_scores')
    def validate_ability_scores(cls, v):
        """Validate ability scores are in valid range."""
        for ability in AbilityType:
            score = getattr(v, ability.value)
            if not 1 <= score <= 30:
                raise ValueError(f"{ability.value} must be between 1 and 30")
        return v

    @root_validator
    def validate_legendary_actions(cls, values):
        """Validate legendary creatures have legendary actions."""
        cr = values.get('challenge_rating')
        legendary_actions = values.get('legendary_actions', [])

        # High CR creatures should typically have legendary actions
        if cr and cr.numeric_value >= 10 and not legendary_actions:
            # This is a warning, not an error
            import warnings
            warnings.warn(f"High CR creature without legendary actions")

        return values
```

### Field Validation

Use Pydantic field validators:

```python
class Spell(BaseContent):
    level: int = Field(
        ge=0, le=9,
        description="Spell level (0-9)"
    )

    casting_time: str = Field(
        regex=r"^(1 action|1 bonus action|1 reaction|1 minute|10 minutes|1 hour|8 hours|24 hours)$",
        description="Standard casting time format"
    )

    spell_range: str = Field(
        min_length=1,
        description="Spell range (e.g., '30 feet', 'Self', 'Touch')"
    )

    @validator('components')
    def validate_components(cls, v):
        """Ensure at least one component is specified."""
        if not v:
            raise ValueError("Spell must have at least one component")
        return v
```

## Model Serialization

### JSON Serialization

Models support JSON serialization:

```python
# Serialize to dict
creature = Creature(
    name="Ancient Red Dragon",
    size=CreatureSize.GARGANTUAN,
    # ... other fields
)

creature_dict = creature.dict()
creature_json = creature.json()

# Deserialize from dict/JSON
restored_creature = Creature.parse_obj(creature_dict)
from_json = Creature.parse_raw(creature_json)

# Custom serialization options
creature_dict = creature.dict(
    exclude={'internal_id'},  # Exclude fields
    by_alias=True,           # Use field aliases
    exclude_none=True        # Skip None values
)
```

### Model Export

Export for different purposes:

```python
class Creature(BaseContent):
    # ... fields ...

    def to_stat_block(self) -> dict[str, Any]:
        """Export as stat block for rendering."""
        return {
            "name": self.name,
            "size_type": f"{self.size.value} {self.creature_type.value}",
            "armor_class": self.armor_class.display_value,
            "hit_points": self.hit_points.display_value,
            "speed": [speed.display for speed in self.speeds],
            "ability_scores": self.ability_scores.dict(),
            "challenge_rating": self.challenge_rating.rating,
            "actions": [action.dict() for action in self.actions],
            # ... other stat block fields
        }

    def to_reference(self) -> dict[str, str]:
        """Export as simple reference."""
        return {
            "name": self.name,
            "cr": self.challenge_rating.rating,
            "type": f"{self.size.value} {self.creature_type.value}",
            "source": str(self.source)
        }
```

## Model Relationships

### Content References

Models can reference other content:

```python
class SpellReference(BaseModel):
    """Reference to a spell."""

    name: str
    source: str | None = None
    level: int | None = None

    def resolve(self, omnidexer: OmnidexerProtocol) -> Spell | None:
        """Resolve reference to actual spell."""
        return omnidexer.get_spell_by_name(self.name)

class Creature(BaseContent):
    # ... other fields ...

    spells_known: list[SpellReference] = []

    def get_resolved_spells(
        self,
        omnidexer: OmnidexerProtocol
    ) -> list[Spell]:
        """Get all spells as resolved objects."""
        resolved = []
        for spell_ref in self.spells_known:
            spell = spell_ref.resolve(omnidexer)
            if spell:
                resolved.append(spell)
        return resolved
```

### Nested Content

Complex nested structures:

```python
class Action(BaseModel):
    """Creature action model."""

    name: str
    description: str
    action_type: ActionType = ActionType.ACTION

    # Attack information
    attack_bonus: int | None = None
    damage: list[DamageRoll] = []
    save_dc: int | None = None
    save_type: AbilityType | None = None

    # Usage limitations
    recharge: str | None = None  # "5-6", "Short Rest", etc.
    uses_per_day: int | None = None

class DamageRoll(BaseModel):
    """Damage roll information."""

    dice: str  # "2d6", "1d8+4", etc.
    damage_type: DamageType

    @property
    def average_damage(self) -> float:
        """Calculate average damage."""
        # Parse dice notation and calculate average
        return self._calculate_average(self.dice)

class Creature(BaseContent):
    # ... other fields ...

    actions: list[Action] = []

    def get_attack_actions(self) -> list[Action]:
        """Get only attack actions."""
        return [
            action for action in self.actions
            if action.attack_bonus is not None
        ]
```

## Model Extensions

### Custom Fields

Add custom fields to models:

```python
from pydantic import PrivateAttr

class Creature(BaseContent):
    # ... standard fields ...

    # Private attributes (not serialized)
    _encounter_multiplier: float = PrivateAttr(default=1.0)
    _custom_notes: str = PrivateAttr(default="")

    # Custom fields with defaults
    custom_tags: list[str] = []
    encounter_role: str | None = None
    difficulty_adjustment: float = 1.0

    def set_encounter_multiplier(self, multiplier: float) -> None:
        """Set encounter difficulty multiplier."""
        self._encounter_multiplier = multiplier

    def get_adjusted_cr(self) -> float:
        """Get CR adjusted for encounter difficulty."""
        base_cr = self.challenge_rating.numeric_value
        return base_cr * self._encounter_multiplier
```

### Model Mixins

Reusable functionality:

```python
class StatBlockMixin:
    """Mixin for content that can generate stat blocks."""

    def to_stat_block(self) -> dict[str, Any]:
        """Generate stat block representation."""
        raise NotImplementedError

    def format_stat_block(self, format_type: str = "latex") -> str:
        """Format stat block for specific output."""
        stat_block = self.to_stat_block()

        if format_type == "latex":
            return self._format_latex_stat_block(stat_block)
        elif format_type == "markdown":
            return self._format_markdown_stat_block(stat_block)
        else:
            raise ValueError(f"Unknown format: {format_type}")

class TaggedContentMixin:
    """Mixin for content with tag processing."""

    def process_tags(self, tag_resolver: TagResolverProtocol) -> None:
        """Process all tags in content."""
        # Find all string fields and process tags
        for field_name, field_value in self.__dict__.items():
            if isinstance(field_value, str):
                from studiorum.renderers.core.interfaces import RenderingContext
                processed = tag_resolver.process_text(field_value, RenderingContext(output_format="latex"))
                setattr(self, field_name, processed)

# Apply mixins
class Creature(BaseContent, StatBlockMixin, TaggedContentMixin):
    # ... creature fields ...

    def to_stat_block(self) -> dict[str, Any]:
        """Implement stat block generation."""
        return {
            "name": self.name,
            "type": f"{self.size.value} {self.creature_type.value}",
            # ... stat block data
        }
```

## Testing Models

### Model Testing Patterns

```python
import pytest
from pydantic import ValidationError

class TestCreatureModel:
    def test_creature_creation_with_valid_data(self):
        """Test creating creature with valid data."""
        creature = Creature(
            name="Test Creature",
            size=CreatureSize.MEDIUM,
            creature_type=CreatureType.HUMANOID,
            challenge_rating=ChallengeRating(rating="1", experience_points=200),
            armor_class=ArmorClass(base=15),
            hit_points=HitPoints(average=20, formula="4d8"),
            speeds=[Speed(type=SpeedType.WALK, distance=30)],
            ability_scores=AbilityScores(
                strength=10, dexterity=12, constitution=10,
                intelligence=10, wisdom=10, charisma=10
            ),
            source=Source("TEST", "Test Source")
        )

        assert creature.name == "Test Creature"
        assert creature.cr_numeric == 1.0
        assert creature.proficiency_bonus == 2

    def test_creature_validation_errors(self):
        """Test validation catches invalid data."""
        with pytest.raises(ValidationError) as exc_info:
            Creature(
                name="",  # Empty name should fail
                size=CreatureSize.MEDIUM,
                challenge_rating=ChallengeRating(rating="invalid", experience_points=0)
            )

        errors = exc_info.value.errors()
        assert len(errors) > 0
        assert any(error['field'] == 'name' for error in errors)

    def test_ability_score_modifiers(self):
        """Test ability score modifier calculation."""
        scores = AbilityScores(
            strength=8,   # -1 modifier
            dexterity=16, # +3 modifier
            constitution=10,  # +0 modifier
            intelligence=10,
            wisdom=10,
            charisma=10
        )

        assert scores.get_modifier(AbilityType.STRENGTH) == -1
        assert scores.get_modifier(AbilityType.DEXTERITY) == 3
        assert scores.get_modifier(AbilityType.CONSTITUTION) == 0
```

### Model Fixtures

Create reusable test data:

```python
@pytest.fixture
def sample_creature() -> Creature:
    """Create a sample creature for testing."""
    return Creature(
        name="Test Goblin",
        size=CreatureSize.SMALL,
        creature_type=CreatureType.HUMANOID,
        challenge_rating=ChallengeRating(rating="1/4", experience_points=50),
        armor_class=ArmorClass(base=15, source="Leather armor"),
        hit_points=HitPoints(average=7, formula="2d6"),
        speeds=[Speed(type=SpeedType.WALK, distance=30)],
        ability_scores=AbilityScores(
            strength=8, dexterity=14, constitution=10,
            intelligence=10, wisdom=8, charisma=8
        ),
        source=Source("TEST", "Test Source"),
        actions=[
            Action(
                name="Scimitar",
                description="Melee Weapon Attack: +4 to hit, reach 5 ft., one target. Hit: 1d6 + 2 slashing damage.",
                attack_bonus=4,
                damage=[DamageRoll(dice="1d6+2", damage_type=DamageType.SLASHING)]
            )
        ]
    )

@pytest.fixture
def sample_spell() -> Spell:
    """Create a sample spell for testing."""
    return Spell(
        name="Butterfly Kiss",
        level=SpellLevel.FIRST,
        school=SpellSchool.EVOCATION,
        classes=[SpellClass.WIZARD, SpellClass.SORCERER],
        casting_time=CastingTime(time="1 action"),
        spell_range=SpellRange(range="120 feet"),
        duration=Duration(duration="Instantaneous"),
        components=[Component.VERBAL, Component.SOMATIC],
        description=[
            "You create a swarm of colorful butterflies that gently fly towards your target.",
            "The butterflies land on the cheek of your target and gently flap their wings to tickle them."
        ],
        source=Source("MY-HOMEBREW", "My Awesome Homebrew")
    )
```

## Performance Considerations

### Model Optimization

Optimize models for performance:

```python
from pydantic import computed_field

class Creature(BaseContent):
    # ... fields ...

    @computed_field
    @property
    def display_name(self) -> str:
        """Cached display name computation."""
        return f"{self.name} (CR {self.challenge_rating.rating})"

    class Config:
        # Performance optimizations
        validate_assignment = True
        extra = "forbid"
        allow_reuse = True           # Reuse validators
        copy_on_model_validation = False  # Don't copy on validation
```

### Lazy Loading

Implement lazy loading for expensive operations:

```python
from functools import cached_property

class Adventure(BaseContent):
    # ... fields ...

    @cached_property
    def referenced_creatures(self) -> list[str]:
        """Extract creature references (expensive operation)."""
        creatures = set()
        for chapter in self.contents:
            for entry in chapter.entries:
                # Extract creature tags from entry content
                found_creatures = extract_creature_tags(entry.content)
                creatures.update(found_creatures)
        return sorted(creatures)

    @cached_property
    def word_count(self) -> int:
        """Calculate total word count (expensive operation)."""
        total_words = 0
        for chapter in self.contents:
            for entry in chapter.entries:
                if isinstance(entry.content, str):
                    total_words += len(entry.content.split())
        return total_words
```

## Next Steps

- **[Services API](services.md)**: Service container and dependency injection
- **[Renderers API](renderers.md)**: Output rendering and formatting
- **[Architecture Guide](../architecture.md)**: Overall system design

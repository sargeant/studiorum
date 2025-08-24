---
title: Model Usage Guide
description: Working with studiorum's Pydantic models for D&D 5e content
---

# Model Usage Guide

Studiorum provides comprehensive Pydantic models for all D&D 5e content types, enabling type-safe operations with full validation and serialization support.

## Basic Model Usage

### Loading Content

Get content through the Omnidexer service:

```python
from studiorum.core.container import get_global_container
from studiorum.core.models.creatures import Creature
from studiorum.core.models.spells import Spell

# Get omnidexer service
container = get_global_container()
omnidexer = container.get_omnidexer_sync()

# Load content by name
dragon = omnidexer.get_creature_by_name("Ancient Red Dragon")
fireball = omnidexer.get_spell_by_name("Fireball")
lmop = omnidexer.get_adventure_by_name("LMoP")

if dragon:
    print(f"Found {dragon.name} (CR {dragon.challenge_rating.rating})")
    print(f"AC: {dragon.armor_class.display_value}")
    print(f"HP: {dragon.hit_points.display_value}")
```

### Working with Results

Models are returned as Results for error handling:

```python
from studiorum.core.result import Success, Error

# Using content resolver for validation
resolver = container.get_content_resolver_sync()
result = resolver.resolve_creature("ancient-red-dragon")

if isinstance(result, Error):
    print(f"Failed to resolve: {result.error}")
else:
    creature = result.unwrap()
    print(f"Resolved: {creature.name}")

    # Access all creature properties
    print(f"Size: {creature.size.value}")
    print(f"Type: {creature.creature_type.value}")
    print(f"Alignment: {creature.alignment}")
```

## Working with Creatures

### Basic Creature Properties

```python
# Access basic creature information
print(f"Name: {creature.name}")
print(f"Size: {creature.size.value}")  # "gargantuan"
print(f"Type: {creature.creature_type.value}")  # "dragon"
print(f"Challenge Rating: {creature.challenge_rating.rating}")  # "24"

# Get numeric CR value
numeric_cr = creature.cr_numeric  # 24.0
proficiency_bonus = creature.proficiency_bonus  # 7

# Access ability scores
str_score = creature.ability_scores.strength  # 30
str_modifier = creature.get_modifier(AbilityType.STRENGTH)  # +10

print(f"Strength: {str_score} ({str_modifier:+d})")
```

### Combat Statistics

```python
# Armor class information
ac_value = creature.armor_class.base  # 22
ac_display = creature.armor_class.display_value  # "22 (Natural Armor)"

# Hit points
avg_hp = creature.hit_points.average  # 546
hp_formula = creature.hit_points.formula  # "28d20 + 252"
hp_display = creature.hit_points.display_value  # "546 (28d20 + 252)"

# Speeds
for speed in creature.speeds:
    print(f"{speed.type.value}: {speed.distance} ft")
    # "walk: 40 ft", "climb: 40 ft", "fly: 80 ft"
```

### Actions and Abilities

```python
# Special abilities (passive features)
for ability in creature.special_abilities:
    print(f"**{ability.name}**: {ability.description}")

# Actions (things the creature can do)
for action in creature.actions:
    print(f"**{action.name}**: {action.description}")

    if action.attack_bonus:
        print(f"  Attack bonus: +{action.attack_bonus}")

    for damage in action.damage:
        print(f"  Damage: {damage.dice} {damage.damage_type.value}")

# Legendary actions (high-CR creatures)
if creature.legendary_actions:
    print("Legendary Actions:")
    for legendary in creature.legendary_actions:
        print(f"**{legendary.name}** ({legendary.cost} action{'s' if legendary.cost != 1 else ''}): {legendary.description}")
```

### Searching Creatures

```python
# Search with filters
dragons = omnidexer.search_creatures(
    creature_type="dragon",
    challenge_rating="10-25"
)

undead = omnidexer.search_creatures(
    creature_type="undead",
    size="medium",
    environment="urban"
)

# Get creatures by source
mm_creatures = omnidexer.search_creatures(
    source="MM",
    challenge_rating="5-10"
)

for creature in dragons[:5]:  # First 5 results
    print(f"{creature.name} (CR {creature.challenge_rating.rating})")
```

## Working with Spells

### Basic Spell Properties

```python
spell = omnidexer.get_spell_by_name("Fireball")

print(f"Name: {spell.name}")
print(f"Level: {spell.level}")  # SpellLevel.THIRD (3)
print(f"School: {spell.school.value}")  # "evocation"
print(f"Casting Time: {spell.casting_time.display}")  # "1 action"
print(f"Range: {spell.spell_range.display}")  # "150 feet"
print(f"Duration: {spell.duration.display}")  # "Instantaneous"

# Components
components = []
if ComponentType.VERBAL in spell.components:
    components.append("V")
if ComponentType.SOMATIC in spell.components:
    components.append("S")
if ComponentType.MATERIAL in spell.components:
    components.append("M")
print(f"Components: {', '.join(components)}")

# Spell flags
if spell.is_ritual:
    print("Ritual spell")
if spell.requires_concentration:
    print("Requires concentration")
```

### Spell Description

```python
# Spell description (list of paragraphs)
for paragraph in spell.description:
    print(paragraph)

# Higher level effects
if spell.higher_levels:
    print(f"\n**At Higher Levels**: {spell.higher_levels.description}")

# Damage information (if applicable)
if spell.damage:
    print(f"Damage: {spell.damage.dice} {spell.damage.damage_type.value}")
    if spell.damage.scaling:
        print(f"Scales: +{spell.damage.scaling} per slot level")
```

### Searching Spells

```python
# Search by level and school
evocation_spells = omnidexer.search_spells(
    level=3,
    school="evocation"
)

# Search by class
wizard_spells = omnidexer.search_spells(
    spell_class="wizard",
    level="1-3"
)

# Search by properties
ritual_spells = omnidexer.search_spells(
    ritual=True,
    level="1-5"
)

concentration_spells = omnidexer.search_spells(
    concentration=True,
    school="enchantment"
)

for spell in wizard_spells[:10]:
    components_str = "".join([
        "V" if ComponentType.VERBAL in spell.components else "",
        "S" if ComponentType.SOMATIC in spell.components else "",
        "M" if ComponentType.MATERIAL in spell.components else ""
    ])
    print(f"{spell.name} (Level {spell.level}, {components_str})")
```

## Working with Adventures

### Adventure Structure

```python
adventure = omnidexer.get_adventure_by_name("Lost Mine of Phandelver")

print(f"Adventure: {adventure.name}")
print(f"Type: {adventure.adventure_type.value}")
print(f"Player Levels: {adventure.levels.min_level}-{adventure.levels.max_level}")
print(f"Chapters: {len(adventure.contents)}")

# Adventure metadata
if adventure.description:
    print(f"Description: {adventure.description}")

if adventure.background:
    print(f"Background: {adventure.background}")
```

### Chapter Navigation

```python
# Iterate through chapters
for i, chapter in enumerate(adventure.contents):
    print(f"Chapter {i + 1}: {chapter.name}")
    print(f"  Entries: {len(chapter.entries)}")

    # Look at first few entries
    for j, entry in enumerate(chapter.entries[:3]):
        if entry.is_text:
            preview = str(entry.content)[:100]
            print(f"    Entry {j + 1}: {preview}...")
        elif entry.is_structured:
            entry_type = entry.content.get("type", "unknown")
            print(f"    Entry {j + 1}: [{entry_type}] structured content")
```

### Extracting Adventure Content

```python
# Find all creature references in adventure
creature_references = set()
spell_references = set()

for chapter in adventure.contents:
    for entry in chapter.entries:
        if entry.is_text:
            text = str(entry.content)

            # Look for creature tags
            creature_tags = re.findall(r'\{@creature ([^}]+)\}', text)
            for tag in creature_tags:
                creature_name = tag.split('|')[0]  # Remove source reference
                creature_references.add(creature_name)

            # Look for spell tags
            spell_tags = re.findall(r'\{@spell ([^}]+)\}', text)
            for tag in spell_tags:
                spell_name = tag.split('|')[0]
                spell_references.add(spell_name)

print(f"Referenced creatures: {len(creature_references)}")
print(f"Referenced spells: {len(spell_references)}")

# Get actual objects for references
referenced_creatures = []
for name in creature_references:
    creature = omnidexer.get_creature_by_name(name)
    if creature:
        referenced_creatures.append(creature)

print(f"Found {len(referenced_creatures)} of {len(creature_references)} referenced creatures")
```

## Working with Items

### Basic Item Properties

```python
item = omnidexer.get_item_by_name("Bag of Holding")

print(f"Name: {item.name}")
print(f"Type: {item.item_type.value}")  # e.g., "wondrous item"
print(f"Rarity: {item.rarity.value}")  # e.g., "uncommon"

# Attunement requirements
if item.requires_attunement:
    if item.attunement.requirement:
        print(f"Attunement: {item.attunement.requirement}")
    else:
        print("Requires attunement")

# Item properties
if item.properties:
    print("Properties:")
    for prop in item.properties:
        print(f"  - {prop.name}: {prop.description}")
```

### Item Description

```python
# Multi-paragraph description
for paragraph in item.description:
    print(paragraph)

# Additional item details
if item.weight:
    print(f"Weight: {item.weight} lbs")

if item.cost:
    print(f"Cost: {item.cost}")

# Weapon-specific properties
if item.weapon_properties:
    weapon_props = [prop.value for prop in item.weapon_properties]
    print(f"Weapon Properties: {', '.join(weapon_props)}")

if item.damage:
    print(f"Damage: {item.damage}")

# Armor-specific properties
if item.armor_properties:
    print(f"Armor Type: {item.armor_properties[0].value}")

if item.armor_class:
    print(f"Armor Class: {item.armor_class}")
```

### Searching Items

```python
# Search by rarity
legendary_items = omnidexer.search_items(rarity="legendary")
rare_weapons = omnidexer.search_items(
    rarity="rare",
    item_type="weapon"
)

# Search by attunement
attunement_items = omnidexer.search_items(attunement=True)

# Search by source
phb_items = omnidexer.search_items(source="PHB")

for item in legendary_items[:5]:
    attune_str = " (attunement)" if item.requires_attunement else ""
    print(f"{item.name} - {item.rarity.value} {item.item_type.value}{attune_str}")
```

## Model Validation and Serialization

### Creating Models

```python
from studiorum.core.models.creatures import (
    Creature, CreatureSize, CreatureType, ChallengeRating,
    ArmorClass, HitPoints, AbilityScores, Speed, SpeedType
)
from studiorum.core.models.sources import Source

# Create a custom creature
custom_creature = Creature(
    name="Custom Goblin",
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
    source=Source("CUSTOM", "Custom Content")
)

print(f"Created: {custom_creature.name} (CR {custom_creature.challenge_rating.rating})")
```

### Validation

```python
from pydantic import ValidationError

try:
    # This will fail validation
    invalid_creature = Creature(
        name="",  # Empty name
        size=CreatureSize.MEDIUM,
        creature_type=CreatureType.HUMANOID,
        challenge_rating=ChallengeRating(rating="invalid", experience_points=0),
        # Missing required fields...
    )
except ValidationError as e:
    print("Validation errors:")
    for error in e.errors():
        print(f"  {error['loc']}: {error['msg']}")
```

### Serialization

```python
# Convert to dictionary
creature_dict = custom_creature.dict()
print(f"Serialized to {len(creature_dict)} fields")

# Convert to JSON
creature_json = custom_creature.json()
with open("custom_creature.json", "w") as f:
    f.write(creature_json)

# Load from dictionary/JSON
restored_creature = Creature.parse_obj(creature_dict)
from_json = Creature.parse_raw(creature_json)

assert restored_creature.name == custom_creature.name
```

### Custom Serialization

```python
# Export for specific use cases
stat_block_data = custom_creature.dict(
    include={
        'name', 'size', 'creature_type', 'challenge_rating',
        'armor_class', 'hit_points', 'speeds', 'ability_scores',
        'actions', 'special_abilities'
    }
)

# Exclude internal fields
public_data = custom_creature.dict(
    exclude={'_internal_id', '_cache_data'}
)

# Use aliases for external APIs
api_data = custom_creature.dict(by_alias=True)
```

## Advanced Model Usage

### Model Relationships

```python
# Models can reference each other
class SpellReference(BaseModel):
    name: str
    source: str | None = None

    def resolve(self, omnidexer) -> Spell | None:
        return omnidexer.get_spell_by_name(self.name)

# Get creature's spells (if spellcaster)
if hasattr(creature, 'spells_known'):
    resolved_spells = []
    for spell_ref in creature.spells_known:
        spell = spell_ref.resolve(omnidexer)
        if spell:
            resolved_spells.append(spell)

    print(f"Creature knows {len(resolved_spells)} spells:")
    for spell in resolved_spells:
        print(f"  {spell.name} (Level {spell.level})")
```

### Custom Model Fields

```python
# Extend models with custom data
from pydantic import PrivateAttr

class EnhancedCreature(Creature):
    # Additional public fields
    encounter_notes: list[str] = []
    custom_tactics: str | None = None

    # Private fields (not serialized)
    _encounter_multiplier: float = PrivateAttr(default=1.0)
    _dm_notes: str = PrivateAttr(default="")

    def set_encounter_difficulty(self, multiplier: float) -> None:
        """Adjust creature difficulty for encounter balancing."""
        self._encounter_multiplier = multiplier

    def get_effective_cr(self) -> float:
        """Get CR adjusted for encounter difficulty."""
        return self.cr_numeric * self._encounter_multiplier
```

### Model Queries and Filtering

```python
# Complex filtering using model properties
def filter_creatures_by_role(creatures: list[Creature], role: str) -> list[Creature]:
    """Filter creatures by combat role."""
    if role == "tank":
        return [c for c in creatures if c.armor_class.base >= 16 and c.hit_points.average >= 100]
    elif role == "damage":
        return [c for c in creatures if any(
            action.damage for action in c.actions
            if action.damage and any(dmg.average_damage > 15 for dmg in action.damage)
        )]
    elif role == "support":
        return [c for c in creatures if any(
            "heal" in action.description.lower() or "buff" in action.description.lower()
            for action in c.actions
        )]
    else:
        return creatures

# Usage
all_creatures = omnidexer.search_creatures(challenge_rating="5-10")
tank_creatures = filter_creatures_by_role(all_creatures, "tank")
damage_dealers = filter_creatures_by_role(all_creatures, "damage")

print(f"Found {len(tank_creatures)} tank creatures")
print(f"Found {len(damage_dealers)} damage dealer creatures")
```

### Model Composition

```python
# Combine multiple models for complex operations
class EncounterBuilder:
    def __init__(self, omnidexer):
        self.omnidexer = omnidexer

    def build_encounter(
        self,
        party_level: int,
        party_size: int,
        environment: str,
        theme: str | None = None
    ) -> dict[str, Any]:
        """Build a complete encounter."""

        # Get suitable creatures
        creatures = self.omnidexer.search_creatures(
            challenge_rating=f"1-{party_level + 2}",
            environment=environment
        )

        # Apply theme filtering
        if theme:
            creatures = self._filter_by_theme(creatures, theme)

        # Select encounter creatures
        encounter_creatures = self._balance_encounter(
            creatures, party_level, party_size
        )

        # Get environmental spells/effects
        environmental_effects = self._get_environmental_effects(environment)

        # Get relevant items (treasure)
        treasure_items = self._generate_treasure(party_level)

        return {
            "creatures": encounter_creatures,
            "environmental_effects": environmental_effects,
            "treasure": treasure_items,
            "estimated_difficulty": self._calculate_difficulty(
                encounter_creatures, party_level, party_size
            )
        }
```

## Performance Considerations

### Efficient Model Operations

```python
# Batch operations are more efficient
creature_names = ["Goblin", "Hobgoblin", "Bugbear", "Orc", "Ogre"]

# ❌ Inefficient - multiple individual lookups
creatures = []
for name in creature_names:
    creature = omnidexer.get_creature_by_name(name)
    if creature:
        creatures.append(creature)

# ✅ Better - batch lookup
creatures = omnidexer.get_creatures_by_names(creature_names)

# ✅ Even better - use search with filters when possible
low_cr_humanoids = omnidexer.search_creatures(
    creature_type="humanoid",
    challenge_rating="1/8-2"
)
```

### Memory Management

```python
from functools import cached_property

class OptimizedCreature(Creature):
    @cached_property
    def stat_block_text(self) -> str:
        """Expensive operation - cache the result."""
        return self._generate_stat_block_text()

    @cached_property
    def search_keywords(self) -> set[str]:
        """Generate search keywords once."""
        keywords = {self.name.lower()}
        keywords.add(self.creature_type.value)
        keywords.add(self.size.value)
        keywords.update(ability.name.lower() for ability in self.special_abilities)
        return keywords
```

### Large Dataset Handling

```python
# Use generators for large datasets
def process_all_creatures():
    """Process all creatures without loading everything into memory."""

    # Get creature count first
    stats = omnidexer.get_statistics()
    total_creatures = stats.get('creature_count', 0)

    # Process in batches
    batch_size = 100
    for offset in range(0, total_creatures, batch_size):
        creature_batch = omnidexer.get_creatures_batch(offset, batch_size)

        for creature in creature_batch:
            yield process_single_creature(creature)

# Usage
for result in process_all_creatures():
    print(f"Processed: {result}")
```

## Next Steps

- **[Services API](api/services.md)**: Work with service container and protocols
- **[Renderers API](api/renderers.md)**: Generate LaTeX/PDF output from models
- **[Architecture Guide](architecture.md)**: Understand the overall system design
- **[Getting Started](getting-started.md)**: Set up development environment

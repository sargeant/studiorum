"""Standardized factory fixtures for test data generation.

This module provides consistent factory functions for creating test data
across the entire test suite, reducing duplication and improving maintainability.
"""

from pathlib import Path
from typing import Any, Optional

import pytest

# ============================================================================
# Content Data Factories
# ============================================================================


@pytest.fixture
def make_spell():
    """Factory for creating spell data with customizable attributes."""

    def _make_spell(
        name: str = "Fireball",
        level: int = 3,
        school: str = "V",
        source: str | None = "PHB",
        page: int = 241,
        **overrides: Any,
    ) -> dict[str, Any]:
        """Create spell data with defaults and overrides."""
        defaults = {
            "name": name,
            "source": {
                "abbreviation": source,
                "name": "Player's Handbook" if source == "PHB" else source,
                "page": page,
            },
            "level": level,
            "school": school,
            "time": [{"number": 1, "unit": "action"}],
            "range": {"type": "point", "distance": {"type": "feet", "amount": 150}},
            "components": {
                "v": True,
                "s": True,
                "m": "a tiny ball of bat guano and sulfur",
            },
            "duration": [{"type": "instant"}],
            "entries": ["A bright streak flashes from your pointing finger."],
        }
        return {**defaults, **overrides}

    return _make_spell


@pytest.fixture
def make_creature():
    """Factory for creating creature data with customizable attributes."""

    def _make_creature(
        name: str = "Ancient Red Dragon",
        cr: str = "24",
        creature_type: str = "dragon",
        size: str = "G",
        source: str | None = "MM",
        **overrides: Any,
    ) -> dict[str, Any]:
        """Create creature data with defaults and overrides."""
        defaults = {
            "name": name,
            "source": {
                "abbreviation": source,
                "name": "Monster Manual" if source == "MM" else source,
                "page": 98,
            },
            "size": [size],
            "type": creature_type,
            "alignment": ["C", "E"],
            "ac": [{"ac": 22, "from": ["natural armor"]}],
            "hp": {"average": 546, "formula": "28d20 + 252"},
            "speed": {"walk": 40, "climb": 40, "fly": 80},
            "str": 30,
            "dex": 10,
            "con": 29,
            "int": 18,
            "wis": 15,
            "cha": 23,
            "cr": cr,
        }
        return {**defaults, **overrides}

    return _make_creature


@pytest.fixture
def make_item():
    """Factory for creating item data with customizable attributes."""

    def _make_item(
        name: str = "Longsword",
        item_type: str = "M",
        rarity: str = "none",
        value: int = 1500,
        source: str | None = "PHB",
        **overrides: Any,
    ) -> dict[str, Any]:
        """Create item data with defaults and overrides."""
        defaults = {
            "name": name,
            "source": {
                "abbreviation": source,
                "name": "Player's Handbook" if source == "PHB" else source,
                "page": 149,
            },
            "type": item_type,
            "rarity": rarity,
            "value": value,
            "weight": 3,
            "property": ["V"],
            "dmg1": "1d8",
            "dmgType": "S",
            "entries": ["A versatile weapon used by many warriors."],
        }
        return {**defaults, **overrides}

    return _make_item


@pytest.fixture
def make_book():
    """Factory for creating book data with customizable attributes."""

    def _make_book(
        name: str = "Player's Handbook",
        book_id: str = "PHB",
        published: str = "2014-08-19",
        **overrides: Any,
    ) -> dict[str, Any]:
        """Create book data with defaults and overrides."""
        defaults = {
            "name": name,
            "id": book_id,
            "source": book_id,
            "published": published,
            "group": "core",
            "contents": [
                {
                    "name": "Introduction",
                    "headers": ["Welcome to 5e"],
                    "entries": ["Welcome to the world's greatest roleplaying game!"],
                }
            ],
        }
        return {**defaults, **overrides}

    return _make_book


@pytest.fixture
def make_adventure():
    """Factory for creating adventure data with customizable attributes."""

    def _make_adventure(
        name: str = "Sample Adventure",
        adventure_id: str = "SAMP",
        published: str = "2014-07-15",
        **overrides: Any,
    ) -> dict[str, Any]:
        """Create adventure data with defaults and overrides."""
        defaults = {
            "name": name,
            "id": adventure_id,
            "source": adventure_id,
            "published": published,
            "level": {"start": 1, "end": 5},
            "contents": [{"name": "Introduction", "entries": ["Welcome adventurers!"]}],
        }
        return {**defaults, **overrides}

    return _make_adventure


# ============================================================================
# Entry Type Factories
# ============================================================================


@pytest.fixture
def make_table_entry():
    """Factory for creating table entries."""

    def _make_table_entry(
        caption: str = "Random Encounters",
        col_labels: list | None = None,
        rows: list | None = None,
        **overrides: Any,
    ) -> dict[str, Any]:
        """Create table entry with defaults and overrides."""
        defaults = {
            "type": "table",
            "caption": caption,
            "colLabels": col_labels or ["d100", "Encounter"],
            "colStyles": ["col-2 text-center", "col-10"],
            "rows": rows or [["01-50", "No encounter"], ["51-00", "Random encounter"]],
        }
        return {**defaults, **overrides}

    return _make_table_entry


@pytest.fixture
def make_list_entry():
    """Factory for creating list entries."""

    def _make_list_entry(
        items: list | None = None, style: str = "list-disc", **overrides: Any
    ) -> dict[str, Any]:
        """Create list entry with defaults and overrides."""
        defaults = {
            "type": "list",
            "style": style,
            "items": items or ["First item", "Second item", "Third item"],
        }
        return {**defaults, **overrides}

    return _make_list_entry


@pytest.fixture
def make_options_entry():
    """Factory for creating options entries."""

    def _make_options_entry(
        count: int = 1, entries: list | None = None, **overrides: Any
    ) -> dict[str, Any]:
        """Create options entry with defaults and overrides."""
        defaults = {
            "type": "options",
            "count": count,
            "entries": entries
            or [
                {
                    "type": "item",
                    "name": "Option A",
                    "entries": ["Description of option A"],
                },
                {
                    "type": "item",
                    "name": "Option B",
                    "entries": ["Description of option B"],
                },
            ],
        }
        return {**defaults, **overrides}

    return _make_options_entry


# ============================================================================
# Model Object Factories
# ============================================================================


@pytest.fixture
def make_spell_object(make_spell):
    """Factory for creating Spell model objects."""
    from studiorum.core.models.spells import Spell

    def _make_spell_object(**kwargs) -> Spell:
        """Create a Spell object with custom attributes."""
        data = make_spell(**kwargs)
        return Spell.model_validate(data)

    return _make_spell_object


@pytest.fixture
def make_creature_object(make_creature):
    """Factory for creating Creature model objects."""
    from studiorum.core.models.creatures import Creature

    def _make_creature_object(**kwargs) -> Creature:
        """Create a Creature object with custom attributes."""
        data = make_creature(**kwargs)
        return Creature.model_validate(data)

    return _make_creature_object


@pytest.fixture
def make_item_object(make_item):
    """Factory for creating Item model objects."""
    from studiorum.core.models.items import Item

    def _make_item_object(**kwargs) -> Item:
        """Create an Item object with custom attributes."""
        data = make_item(**kwargs)
        return Item.model_validate(data)

    return _make_item_object


# ============================================================================
# Test Environment Factories
# ============================================================================


@pytest.fixture
def make_test_data_dir(tmp_path: Path):
    """Factory for creating test data directories with custom content."""
    import json

    def _make_test_data_dir(
        spells: list | None = None,
        creatures: list | None = None,
        items: list | None = None,
        books: list | None = None,
        adventures: list | None = None,
    ) -> Path:
        """Create a test data directory with specified content."""
        data_dir = tmp_path / "test_data"
        data_dir.mkdir()

        # Create spell data
        if spells is not None:
            spell_dir = data_dir / "spells"
            spell_dir.mkdir()
            spell_file = spell_dir / "spells-test.json"
            spell_file.write_text(json.dumps({"spell": spells}))

        # Create creature data
        if creatures is not None:
            creature_dir = data_dir / "bestiary"
            creature_dir.mkdir()
            creature_file = creature_dir / "bestiary-test.json"
            creature_file.write_text(json.dumps({"monster": creatures}))

        # Create item data
        if items is not None:
            item_dir = data_dir / "items"
            item_dir.mkdir()
            item_file = item_dir / "items-test.json"
            item_file.write_text(json.dumps({"item": items}))

        # Create book data
        if books is not None:
            book_dir = data_dir / "book"
            book_dir.mkdir()
            book_file = book_dir / "book-test.json"
            book_file.write_text(json.dumps({"data": books}))

        # Create adventure data
        if adventures is not None:
            adventure_dir = data_dir / "adventure"
            adventure_dir.mkdir()
            adventure_file = adventure_dir / "adventure-test.json"
            adventure_file.write_text(json.dumps({"data": adventures}))

        return data_dir

    return _make_test_data_dir


@pytest.fixture
def make_omnidexer(make_test_data_dir):
    """Factory for creating configured Omnidexer instances."""
    from studiorum.core.loaders.omnidexer import Omnidexer
    from tests.test_helpers import reset_test_environment

    def _make_omnidexer(
        spells: list | None = None,
        creatures: list | None = None,
        items: list | None = None,
        **kwargs,
    ) -> Omnidexer:
        """Create an Omnidexer with specified test data."""
        # Reset environment for clean state
        reset_test_environment()

        # Create test data directory
        make_test_data_dir(spells=spells, creatures=creatures, items=items, **kwargs)

        # Create and configure omnidexer
        omnidexer = Omnidexer()
        # Configure with test data path
        # Note: Actual configuration would depend on how Omnidexer accepts paths

        return omnidexer

    return _make_omnidexer


@pytest.fixture
def make_tag_resolver():
    """Factory for creating TagResolver instances."""
    from unittest.mock import Mock

    from studiorum.core.text.tag_resolver import TagResolver

    def _make_tag_resolver(omnidexer=None) -> TagResolver:
        """Create a TagResolver with optional omnidexer."""
        if omnidexer is None:
            from studiorum.core.loaders.omnidexer import Omnidexer

            omnidexer = Mock(spec=Omnidexer)
        return TagResolver(omnidexer)

    return _make_tag_resolver


# ============================================================================
# Encounter/Combat Factories
# ============================================================================


@pytest.fixture
def make_encounter_creature():
    """Factory for creating EncounterCreature objects."""
    from studiorum.core.models.encounter_types import XP
    from studiorum.core.services.encounter_collector import EncounterCreature

    def _make_encounter_creature(
        creature=None,
        quantity: int = 1,
        tactical_role: str = "combatant",
        xp_contribution: int = 100,
        environmental_suitability: float = 1.0,
        threat_rating: float = 1.0,
        **kwargs,
    ) -> EncounterCreature:
        """Create an EncounterCreature with custom attributes."""
        if creature is None:
            # Create a minimal creature object for testing
            creature = type(
                "TestCreature",
                (),
                {
                    "name": "Goblin",
                    "cr": "1/4",
                    "type": {"type": "humanoid"},
                    "source": {"abbreviation": "MM", "page": 166},
                },
            )()

        return EncounterCreature(
            creature=creature,
            quantity=quantity,
            tactical_role=tactical_role,
            xp_contribution=XP(xp_contribution),
            environmental_suitability=environmental_suitability,
            threat_rating=threat_rating,
            **kwargs,
        )

    return _make_encounter_creature


@pytest.fixture
def make_encounter_generation_result():
    """Factory for creating EncounterGenerationResult objects."""
    from studiorum.core.models.encounter_types import XP, EncounterId
    from studiorum.core.services.encounter_collector import EncounterGenerationResult

    def _make_encounter_generation_result(
        encounter_id: str | None = None,
        creatures: list | None = None,
        total_base_xp: int = 500,
        total_adjusted_xp: int = 750,
        difficulty_rating: str = "medium",
        balance_score: float = 0.75,
        tactical_analysis: dict | None = None,
        environmental_fit: float = 0.8,
        rebalance_suggestions: list | None = None,
        generation_time_ms: float = 125.0,
        **overrides,
    ) -> EncounterGenerationResult:
        """Create an EncounterGenerationResult with custom attributes."""
        import uuid

        if encounter_id is None:
            encounter_id = f"test_encounter_{str(uuid.uuid4())[:8]}"

        if creatures is None:
            from studiorum.core.models.encounter_types import XP
            from studiorum.core.services.encounter_collector import EncounterCreature

            # Create a simple test creature
            test_creature = type(
                "TestCreature",
                (),
                {
                    "name": "Goblin",
                    "cr": "1/4",
                    "type": {"type": "humanoid"},
                    "source": {"abbreviation": "MM", "page": 166},
                },
            )()

            creatures = [
                EncounterCreature(
                    creature=test_creature,
                    quantity=3,
                    tactical_role="minion",
                    xp_contribution=XP(total_base_xp),
                    environmental_suitability=environmental_fit,
                )
            ]

        if tactical_analysis is None:
            tactical_analysis = {
                "total_creatures": sum(c.quantity for c in creatures),
                "unique_creature_types": len(creatures),
                "creature_roles": {"minion": 3},
                "capabilities": {
                    "has_ranged_attackers": True,
                    "has_spellcasters": False,
                    "has_tanks": True,
                },
                "action_economy": {
                    "action_ratio": 1.25,
                    "balance_assessment": "balanced",
                },
            }

        if rebalance_suggestions is None:
            rebalance_suggestions = [
                "Consider adding variety with different creature types",
                "Balance looks good for the target difficulty",
            ]

        defaults = {
            "encounter_id": EncounterId(encounter_id),
            "creatures": creatures,
            "total_base_xp": XP(total_base_xp),
            "total_adjusted_xp": XP(total_adjusted_xp),
            "difficulty_rating": difficulty_rating,
            "balance_score": balance_score,
            "tactical_analysis": tactical_analysis,
            "environmental_fit": environmental_fit,
            "rebalance_suggestions": rebalance_suggestions,
            "generation_time_ms": generation_time_ms,
        }

        return EncounterGenerationResult(**{**defaults, **overrides})

    return _make_encounter_generation_result


@pytest.fixture
def make_party_composition():
    """Factory for creating PartyComposition objects."""
    from studiorum.core.models.encounter_types import PartyComposition, PartyLevel

    def _make_party_composition(
        size: int = 4,
        level: int = 5,
        individual_levels: list[int] | None = None,
        **overrides,
    ) -> PartyComposition:
        """Create a PartyComposition with custom attributes."""
        defaults = {
            "size": size,
            "level": PartyLevel(level),
            "individual_levels": individual_levels,
        }

        return PartyComposition(**{**defaults, **overrides})

    return _make_party_composition


# ============================================================================
# LaTeX/Rendering Factories
# ============================================================================


@pytest.fixture
def make_latex_context():
    """Factory for creating LaTeX rendering contexts."""
    from studiorum.latex_engine.core.context import LaTeXContext

    def _make_latex_context(
        document_type: str = "book", images: bool = True, **overrides: Any
    ) -> LaTeXContext:
        """Create a LaTeX context with custom settings."""
        return LaTeXContext(document_type=document_type, images=images, **overrides)

    return _make_latex_context


@pytest.fixture
def make_renderer_config():
    """Factory for creating renderer configuration."""

    def _make_renderer_config(
        output_format: str = "latex",
        images: bool = True,
        debug: bool = False,
        **overrides: Any,
    ) -> dict[str, Any]:
        """Create renderer configuration with defaults and overrides."""
        defaults = {
            "format": output_format,
            "images": images,
            "debug": debug,
            "output_dir": "/tmp/test_output",
            "template_dir": None,
        }
        return {**defaults, **overrides}

    return _make_renderer_config

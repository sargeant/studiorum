r"""Regression tests to ensure no unresolved tags appear in rendered output.

These tests exercise the entry renderers with minimal content objects and
assert that the LaTeX produced by templates does not contain unresolved
5e.tools tag syntax ("{@...}") or its escaped variant ("\{@...").
"""

from __future__ import annotations

from typing import Any

import pytest

from studiorum.latex_engine.core.entry_renderers import (
    CreatureEntryRenderer,
    ItemEntryRenderer,
    SpellEntryRenderer,
)
from studiorum.renderers.core.interfaces import RenderingContext
from tests.test_helpers import reset_test_environment


def _has_unresolved_tags(s: str) -> bool:
    """Check whether rendered output still contains unresolved tags."""
    return "{@" in s or "\\{@" in s


@pytest.mark.rendering
class TestNoUnresolvedTags:
    """Ensure rendered entries do not contain unresolved tags."""

    def setup_method(self) -> None:
        """Reset environment for isolation and predictable configuration."""
        reset_test_environment()

    def test_spell_no_unresolved_tags(self) -> None:
        from studiorum.core.models.spells import Spell

        spell_data: dict[str, Any] = {
            "name": "Test Bolt",
            "source": {"abbreviation": "TST", "name": "Test Source"},
            "level": 1,
            "school": "E",
            "time": [{"number": 1, "unit": "action"}],
            "range": {"type": "point", "distance": {"type": "feet", "amount": 60}},
            "components": {"v": True, "s": True, "m": False},
            "duration": [{"type": "instant"}],
            "entries": [
                "A bolt of test energy streaks toward a target you can see.",
                {"type": "list", "items": ["Line one", "Line two"]},
            ],
            "entriesHigherLevel": [
                {
                    "type": "entries",
                    "name": "At Higher Levels",
                    "entries": ["The damage increases by 1d6 for each slot above 1st."],
                }
            ],
        }

        spell = Spell.model_validate(spell_data)
        ctx = RenderingContext(output_format="latex")

        latex = SpellEntryRenderer().render(spell, ctx)
        assert latex and not _has_unresolved_tags(latex)

    def test_creature_no_unresolved_tags(self) -> None:
        from studiorum.core.models.creatures import Creature

        creature_data: dict[str, Any] = {
            "name": "Test Goblin",
            "source": {"abbreviation": "TST", "name": "Test Source"},
            "size": ["Small"],
            "type": "humanoid",
            "alignment": ["neutral"],
            "ac": [12],
            "hp": {"average": 7, "formula": "2d6"},
            "speed": {"walk": 30},
            "str": 8,
            "dex": 14,
            "con": 10,
            "int": 10,
            "wis": 8,
            "cha": 8,
            "trait": [
                {
                    "name": "Nimble Escape",
                    "entries": [
                        "The goblin can take the Disengage or Hide action as a bonus action on each of its turns."
                    ],
                }
            ],
            "action": [
                {
                    "name": "Scimitar",
                    "entries": [
                        "Melee Weapon Attack: +4 to hit, reach 5 ft., one target. Hit: 5 (1d6 + 2) slashing damage."
                    ],
                }
            ],
        }

        creature = Creature.model_validate(creature_data)
        ctx = RenderingContext(output_format="latex")

        latex = CreatureEntryRenderer().render(creature, ctx)
        assert latex and not _has_unresolved_tags(latex)

    def test_items_no_unresolved_tags(self) -> None:
        from studiorum.core.models.items import Item

        items_data = [
            {
                "name": "Test Wand",
                "source": {"abbreviation": "TST", "name": "Test Source"},
                "type": "wand",
                "rarity": "uncommon",
                "value": 500,
                "entries": ["This wand hums softly when held."],
            },
            {
                "name": "Light Armor",
                "source": {"abbreviation": "TST", "name": "Test Source"},
                "type": "LA",
                "rarity": "common",
                "value": 45,
                "entries": ["A simple suit of light armor."],
            },
            {
                "name": "Potion of Testing",
                "source": {"abbreviation": "TST", "name": "Test Source"},
                "type": "potion",
                "rarity": "rare",
                "value": {"amount": 150, "unit": "gp"},
                "entries": ["Drinking this potion makes you feel… tested."],
            },
        ]

        ctx = RenderingContext(output_format="latex")
        renderer = ItemEntryRenderer()

        for data in items_data:
            item = Item.model_validate(data)
            latex = renderer.render(item, ctx)
            assert latex and not _has_unresolved_tags(latex)

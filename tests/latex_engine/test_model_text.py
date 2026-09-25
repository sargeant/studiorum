"""Creature fields with 5etools markup, as LaTeX."""

from studiorum.core.models.creatures import Ability, Creature
from studiorum.latex_engine.core import model_text
from studiorum.renderers.tags import TagResolver

CREATURE = Creature.model_validate(
    {
        "name": "Knight",
        "source": "MM",
        "size": ["M"],
        "type": "humanoid",
        "alignment": ["N"],
        "ac": [{"ac": 18, "from": ["{@item plate armor|phb}"]}, 12],
        "hp": {"average": 52},
        "speed": {"walk": 30},
        "str": 16,
        "dex": 11,
        "con": 14,
        "int": 11,
        "wis": 11,
        "cha": 15,
        "cr": "3",
        "senses": ["{@sense darkvision|XPHB} 60 ft."],
    }
)


def test_ability_names_render_tags() -> None:
    ability = Ability(name="Fire Breath {@recharge 5}", entries=[])
    assert (
        model_text.ability_name_text(ability, None, TagResolver())
        == "Fire Breath (Recharge 5--6)"
    )


def test_armour_class_renders_its_sources() -> None:
    assert (
        model_text.creature_ac_text(CREATURE, TagResolver())
        == "18 (\\textit{plate armor}), 12"
    )


def test_senses_render_tags() -> None:
    assert (
        model_text.creature_senses_text(CREATURE, TagResolver())
        == "\\textit{darkvision} 60 ft."
    )

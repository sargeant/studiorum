"""Content models accept the shapes 5etools ships (each case trimmed from its data)."""

from __future__ import annotations

from studiorum.core.models.additional_spells import SpellChoice, SpellList, SpellUses
from studiorum.core.models.content import Reprint
from studiorum.core.models.optional_features import OptionalFeature
from studiorum.core.models.spells import ScalingLevelDice, Spell
from studiorum.core.models.subclasses import Subclass
from studiorum.core.models.subraces import Subrace
from studiorum.core.models.traps import Trap
from studiorum.core.models.variantrule import VariantRule


def test_reprints_take_both_forms() -> None:
    rule = VariantRule.model_validate(
        {
            "name": "Falling",
            "source": "XGE",
            "entries": ["..."],
            "reprintedAs": ["Falling|XDMG", {"uid": "Falling|XPHB", "tag": "hazard"}],
        }
    )

    assert rule.reprinted_as == [
        "Falling|XDMG",
        Reprint(uid="Falling|XPHB", tag="hazard"),
    ]


def test_subclass_spells_take_every_5etools_form() -> None:
    subclass = Subclass.model_validate(
        {
            "name": "Arcana Domain",
            "shortName": "Arcana",
            "source": "SCAG",
            "className": "Cleric",
            "classSource": "PHB",
            "subclassFeatures": ["Arcana Domain|Cleric||Arcana|SCAG|1"],
            "spellsKnownProgression": [0, 0, 3, 4],
            "additionalSpells": [
                {
                    "ability": "wis",
                    "known": {
                        "1": {"_": [{"choose": "level=0|class=Wizard", "count": 2}]}
                    },
                    "prepared": {"1": ["detect magic", "magic missile"]},
                    "innate": {
                        "3": [{"choose": {"from": ["blade ward|xphb#c"], "count": 1}}],
                        "9": {"daily": {"1e": ["lesser restoration|xphb"]}},
                    },
                    "expanded": {"s1": [{"all": "level=0|class=Cleric"}]},
                }
            ],
        }
    )

    assert subclass.spells_known_progression == [0, 0, 3, 4]
    [spells] = subclass.additional_spells or []
    assert spells.known == {
        "1": SpellUses.model_validate(
            {"_": [{"choose": "level=0|class=Wizard", "count": 2}]}
        )
    }
    assert spells.innate is not None
    assert spells.innate["3"] == [
        SpellChoice(
            choose=SpellList.model_validate({"from": ["blade ward|xphb#c"], "count": 1})
        )
    ]
    assert isinstance(spells.innate["9"], SpellUses)


def test_an_invocation_can_require_a_chosen_cantrip() -> None:
    feature = OptionalFeature.model_validate(
        {
            "name": "Agonizing Blast",
            "source": "XPHB",
            "featureType": ["EI"],
            "prerequisite": [
                {
                    "level": {"level": 2, "class": {"name": "Warlock"}},
                    "spell": [
                        {
                            "choose": "level=0|class=Warlock",
                            "entry": "a Warlock Cantrip That Deals Damage",
                            "entrySummary": "Warlock Cantrip That Deals Damage",
                        }
                    ],
                }
            ],
            "entries": ["..."],
        }
    )

    assert feature.prerequisite is not None
    [required] = feature.prerequisite[0].spell or []
    assert not isinstance(required, str)
    assert required.choose == "level=0|class=Warlock"


def test_trap_parts_are_entries() -> None:
    trap = Trap.model_validate(
        {
            "name": "Bear Trap",
            "source": "XGE",
            "trapHazType": "MECH",
            "trigger": ["A creature steps on the trap."],
            "countermeasures": [
                "A DC 10 Wisdom check spots it.",
                {"type": "list", "items": ["x"]},
            ],
        }
    )

    assert trap.trigger == ["A creature steps on the trap."]
    assert trap.countermeasures is not None
    assert len(trap.countermeasures) == 2


def _spell(**extra: object) -> Spell:
    return Spell.model_validate(
        {
            "name": "Booming Blade",
            "source": "TCE",
            "level": 0,
            "school": "V",
            "time": [{"number": 1, "unit": "action"}],
            "range": {"type": "point", "distance": {"type": "self"}},
            "components": {"s": True, "m": "a melee weapon worth at least 1 sp"},
            "duration": [{"type": "timed", "duration": {"type": "round", "amount": 1}}],
            "entries": ["..."],
            **extra,
        }
    )


def test_spells_keep_srd_names_and_several_scalings() -> None:
    assert _spell(srd="Arcane Hand").srd == "Arcane Hand"

    spell = _spell(
        scalingLevelDice=[
            {"label": "melee damage", "scaling": {"5": "1d8", "11": "2d8"}},
            {"label": "thunder damage", "scaling": {"1": "1d8", "5": "2d8"}},
        ]
    )

    assert isinstance(spell.scaling_level_dice, list)
    assert all(isinstance(s, ScalingLevelDice) for s in spell.scaling_level_dice)
    assert spell.get_scaling_table() == {5: "1d8", 11: "2d8"}


def test_a_subrace_can_have_a_plain_speed_and_no_entries() -> None:
    subrace = Subrace.model_validate(
        {
            "name": "Gavony",
            "source": "PSI",
            "raceName": "Human (Innistrad)",
            "raceSource": "PSI",
            "speed": 40,
        }
    )

    assert subrace.speed == 40
    assert subrace.entries == []

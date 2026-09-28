"""A small data set for the MCP tools: SRD entries from srd-data, and copies without the flag."""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from studiorum.config import ApplicationConfig, DataConfig, set_app_config

SRD_DATA = Path(__file__).parents[2] / "srd-data"
NOT_SRD = ("srd", "srd52", "basicRules", "basicRules2024")


# One section too long for a page: three paragraphs of 10,000 characters
LONG = ["word " * 2000] * 3
ADVENTURE_TEXT = [
    {
        "type": "section",
        "name": "Welcome",
        "id": "000",
        "entries": [
            "Hello {@creature goblin|MM|goblins}.",
            {
                "type": "entries",
                "name": "Hooks",
                "id": "001",
                "entries": ["A hook.", {"type": "list", "items": ["one", "two"]}],
            },
            {
                "type": "section",
                "name": "Background",
                "id": "004",
                "entries": ["Long ago. See {@adventure the side trek|TB-ST}."],
            },
        ],
    },
    {
        "type": "section",
        "name": "The Cave",
        "id": "002",
        "entries": [
            {"type": "entries", "name": "Big Room", "id": "003", "entries": LONG},
            {
                "type": "table",
                "caption": "Loot",
                "colLabels": ["{@dice d4}", "Item"],
                "rows": [["1", "{@item Potion of Healing|DMG}"], ["2-4", "Nothing"]],
            },
            {"type": "statblock", "tag": "creature", "name": "Goblin", "source": "MM"},
            # Not in the data set
            {"type": "statblock", "tag": "creature", "name": "Owlbear", "source": "MM"},
            {"type": "insetReadaloud", "entries": ["You smell smoke."]},
            {
                "type": "entries",
                "name": "Guards",
                "id": "005",
                "entries": [
                    {
                        "type": "statblock",
                        "tag": "creature",
                        "name": "Goblin",
                        "source": "SRD",
                    }
                ],
            },
            "Past the guards, {@area the big room|003|x} holds a {@item Potion of Healing|DMG}.",
        ],
    },
]


def _pick(path: Path, key: str, names: set[str]) -> list[dict[str, Any]]:
    entries = json.loads(path.read_text())[key]
    found = [e for e in entries if e["name"] in names]
    assert {e["name"] for e in found} == names
    return found


def _not_srd(entry: dict[str, Any], name: str) -> dict[str, Any]:
    copy = {k: v for k, v in entry.items() if k not in NOT_SRD}
    return copy | {"name": name, "source": "HB"}


def _write(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))


@pytest.fixture
def mcp_data(tmp_path: Path) -> Iterator[Path]:
    """Point the server's configuration at the small data set."""
    spells = _pick(
        SRD_DATA / "spells" / "spells-srd.json", "spell", {"Fireball", "Alarm"}
    )
    fireball = next(s for s in spells if s["name"] == "Fireball")
    alarm = next(s for s in spells if s["name"] == "Alarm")
    # The SRD Alarm reprinted in the XPHB
    alarm_2024 = {**alarm, "source": "XPHB"}
    alarm["reprintedAs"] = ["Alarm|XPHB"]
    _write(tmp_path / "spells" / "index.json", {"SRD": "spells-srd.json"})
    _write(
        tmp_path / "spells" / "spells-srd.json",
        {"spell": [*spells, alarm_2024, _not_srd(fireball, "Hellfire Orb")]},
    )

    creatures = _pick(
        SRD_DATA / "bestiary" / "bestiary-srd.json",
        "monster",
        {"Goblin", "Young Red Dragon", "Acolyte"},
    )
    goblin = next(c for c in creatures if c["name"] == "Goblin")
    # A Flee Mortals-style minion: CR 1/4, but worth 10 XP
    minion = _not_srd(goblin, "Goblin Minion") | {"cr": {"cr": "1/4", "xp": 10}}
    # A statblock a spell summons: a type to choose, and no CR
    familiar = {
        k: v for k, v in _not_srd(goblin, "Battle Familiar").items() if k != "cr"
    } | {"type": {"type": {"choose": ["celestial", "fey", "fiend"]}}}
    _write(tmp_path / "bestiary" / "index.json", {"SRD": "bestiary-srd.json"})
    _write(
        tmp_path / "bestiary" / "bestiary-srd.json",
        {"monster": [*creatures, _not_srd(goblin, "Goblin Sneak"), minion, familiar]},
    )

    items = _pick(SRD_DATA / "items.json", "item", {"Amulet of Health", "Ale (mug)"})
    amulet = next(i for i in items if i["name"] == "Amulet of Health")
    _write(
        tmp_path / "items.json",
        {"item": [*items, _not_srd(amulet, "Amulet of Grit")]},
    )

    _write(
        tmp_path / "items-base.json",
        {
            "itemType": [
                {"name": "Food and Drink", "abbreviation": "FD", "source": "PHB"}
            ]
        },
    )

    _write(
        tmp_path / "books.json",
        {
            "book": [
                {
                    "name": "Test Book",
                    "id": "TB",
                    "source": "TB",
                    "published": "2020-01-01",
                    "group": "core",
                    "author": "Tests",
                    "contents": [{"name": "Rules"}],
                }
            ]
        },
    )
    _write(
        tmp_path / "adventures.json",
        {
            "adventure": [
                {
                    "name": "Test Adventure",
                    "id": "TA",
                    "source": "TA",
                    "published": "2019-01-01",
                    "group": "supplement",
                    "storyline": "Tests",
                    "contents": [{"name": "Welcome"}, {"name": "The Cave"}],
                },
                {
                    "name": "Test Book Side Trek",
                    "id": "TB-ST",
                    "source": "TB",
                    "published": "2021-01-01",
                    "storyline": "Tests",
                    "contents": [{"name": "Trek"}],
                },
            ]
        },
    )

    _write(
        tmp_path / "variantrules.json",
        {
            "variantrule": [
                {
                    "name": "Action Options",
                    "source": "DMG",
                    "entries": [
                        "Options for combat.",
                        {
                            "type": "entries",
                            "name": "Climb onto a Bigger Creature",
                            "entries": ["Climb on, as a special grapple check."],
                        },
                        {
                            "type": "entries",
                            "name": "Tumble",
                            "entries": ["Tumble through a hostile creature's space."],
                        },
                    ],
                },
                {
                    "name": "Unarmed Strike",
                    "source": "XPHB",
                    "srd52": True,
                    "entries": [
                        "A blow to damage, grapple, or shove a target.",
                        {
                            "type": "entries",
                            "name": "Grapple",
                            "entries": ["The target has the Grappled condition."],
                        },
                    ],
                },
            ]
        },
    )
    _write(
        tmp_path / "actions.json",
        {
            "action": [
                {
                    "name": "Climb onto a Bigger Creature",
                    "source": "DMG",
                    "fromVariant": "Action Options",
                    "entries": ["Climb on, as a special grapple check."],
                }
            ]
        },
    )
    _write(
        tmp_path / "conditionsdiseases.json",
        {
            "condition": [
                {
                    "name": "Grappled",
                    "source": "XPHB",
                    "srd52": True,
                    "entries": ["Your {@variantrule Speed|XPHB} is 0."],
                },
                {
                    "name": "Incapacitated",
                    "source": "XPHB",
                    "srd52": True,
                    "entries": ["You can't take any action."],
                },
                {
                    "name": "Prone",
                    "source": "XPHB",
                    "srd52": True,
                    "entries": ["You can only crawl."],
                },
                {
                    "name": "Unconscious",
                    "source": "XPHB",
                    "srd52": True,
                    "entries": [
                        "You have the {@condition Incapacitated|XPHB} and "
                        "{@condition Prone|XPHB} conditions.",
                        "While {@condition Incapacitated|XPHB}, you drop what you hold.",
                    ],
                },
            ]
        },
    )

    _write(
        tmp_path / "languages.json",
        {
            "language": [
                # A later book's entry that only names the language
                {"name": "Elvish", "source": "DSotDQ", "page": 1},
                {
                    "name": "Elvish",
                    "source": "XPHB",
                    "srd52": True,
                    "type": "standard",
                    "typicalSpeakers": ["{@race Elf|XPHB|Elves}"],
                    "script": "Elvish",
                },
            ]
        },
    )

    _write(
        tmp_path / "feats.json",
        {"feat": _pick(SRD_DATA / "feats.json", "feat", {"Grappler"})},
    )

    wizard = json.loads((SRD_DATA / "class" / "class-wizard.json").read_text())
    _write(tmp_path / "class" / "class-wizard.json", wizard)

    _write(tmp_path / "adventure" / "adventure-ta.json", {"data": ADVENTURE_TEXT})
    _write(
        tmp_path / "adventure" / "adventure-tb-st.json",
        {
            "data": [
                {
                    "type": "section",
                    "name": "Trek",
                    "id": "200",
                    "entries": [
                        "Go.",
                        # In book order, worst match for "traps" and "detonate" first
                        {
                            "type": "entries",
                            "name": "12. Forge of Traps",
                            "id": "201",
                            "entries": ["Old runes detonated."],
                        },
                        {
                            "type": "entries",
                            "name": "Mousetraps",
                            "id": "202",
                            "entries": ["They detonate when touched."],
                        },
                        {
                            "type": "entries",
                            "name": "Spell List",
                            "id": "204",
                            "entries": [
                                {
                                    "type": "table",
                                    "colLabels": ["Spell"],
                                    "rows": [["{@spell Detonate|TB}"]],
                                }
                            ],
                        },
                        {
                            "type": "entries",
                            "name": "Traps",
                            "id": "203",
                            "entries": [
                                {
                                    "type": "statblock",
                                    "tag": "spell",
                                    "name": "Detonate",
                                    "source": "TB",
                                }
                            ],
                        },
                    ],
                }
            ]
        },
    )
    _write(
        tmp_path / "book" / "book-tb.json",
        {
            "data": [
                {
                    "type": "section",
                    "name": "Rules",
                    "id": "100",
                    "entries": ["Roll a {@dice d20}."],
                }
            ]
        },
    )

    set_app_config(ApplicationConfig(data=DataConfig(dirs=[tmp_path])))
    yield tmp_path

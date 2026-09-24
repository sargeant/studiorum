"""A small data set for the MCP tools: SRD entries from srd-data, and copies without the flag."""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from studiorum.core.config.data_sources import DataConfig
from studiorum.core.config.unified_config import ApplicationConfig, set_app_config

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
                "entries": ["Long ago."],
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
                        "source": "MM",
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
    _write(tmp_path / "bestiary" / "index.json", {"SRD": "bestiary-srd.json"})
    _write(
        tmp_path / "bestiary" / "bestiary-srd.json",
        {"monster": [*creatures, _not_srd(goblin, "Goblin Sneak")]},
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
                }
            ]
        },
    )

    _write(
        tmp_path / "variantrules.json",
        {
            "variantrule": [
                {
                    "name": "Unarmed Strike",
                    "source": "XPHB",
                    "srd52": True,
                    "entries": ["A blow to damage, grapple, or shove a target."],
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
                }
            ]
        },
    )

    wizard = json.loads((SRD_DATA / "class" / "class-wizard.json").read_text())
    _write(tmp_path / "class" / "class-wizard.json", wizard)

    _write(tmp_path / "adventure" / "adventure-ta.json", {"data": ADVENTURE_TEXT})
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

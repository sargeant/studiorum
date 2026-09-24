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
    _write(tmp_path / "spells" / "index.json", {"SRD": "spells-srd.json"})
    _write(
        tmp_path / "spells" / "spells-srd.json",
        {"spell": [*spells, _not_srd(fireball, "Hellfire Orb")]},
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
        tmp_path / "books.json",
        {
            "book": [
                {
                    "name": "Test Book",
                    "id": "TB",
                    "source": "TB",
                    "published": "2020-01-01",
                    "group": "core",
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
                }
            ]
        },
    )

    set_app_config(ApplicationConfig(data=DataConfig(dirs=[tmp_path])))
    yield tmp_path

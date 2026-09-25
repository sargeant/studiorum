"""Races merged with their subraces, as 5etools' races page does."""

from pathlib import Path

import pytest

from studiorum.core.loaders.data_dir import DataDir, DataSet
from studiorum.core.loaders.omnidexer import Omnidexer
from studiorum.core.loaders.subraces import merge, subrace_name
from studiorum.core.models.content import ContentType

HALF_ELF = {
    "name": "Half-Elf",
    "source": "PHB",
    "srd": True,
    "size": ["M"],
    "speed": 30,
    "ability": [{"cha": 2}],
    "entries": [
        {"type": "entries", "name": "Age", "entries": ["..."]},
        {"type": "entries", "name": "Skill Versatility", "entries": ["Two skills."]},
    ],
}
MARK = {
    "name": "Variant; Mark of Detection",
    "source": "ERLW",
    "raceName": "Half-Elf",
    "raceSource": "PHB",
    "ability": [{"wis": 1}],
    "overwrite": {"ability": True},
    "entries": [
        {
            "type": "entries",
            "name": "Deductive Intuition",
            "entries": ["Insight."],
            "data": {"overwrite": "Skill Versatility"},
        },
        {"type": "entries", "name": "Magical Detection", "entries": ["Detect."]},
    ],
}


@pytest.mark.parametrize(
    ("race", "subrace", "name"),
    [
        ("Genasi", "Air", "Genasi (Air)"),
        ("Elf (Zendikar)", "Tajuru", "Elf (Zendikar; Tajuru)"),
        ("Human", None, "Human"),
    ],
)
def test_subrace_names_follow_5etools(
    race: str, subrace: str | None, name: str
) -> None:
    assert subrace_name(race, subrace) == name


def test_a_subrace_overwrites_and_extends_its_race() -> None:
    [merged] = merge([HALF_ELF], [MARK])

    assert merged["name"] == "Half-Elf (Variant; Mark of Detection)"
    assert merged["source"] == "ERLW"
    assert merged["ability"] == [{"wis": 1}]
    assert [e["name"] for e in merged["entries"]] == [
        "Age",
        "Deductive Intuition",
        "Magical Detection",
    ]
    assert "srd" not in merged
    assert "raceName" not in merged
    assert HALF_ELF["entries"][1]["name"] == "Skill Versatility"


def test_a_subrace_without_its_race_or_name_is_skipped() -> None:
    orphan = {**MARK, "raceName": "Nobody"}
    default = {k: v for k, v in MARK.items() if k != "name"}

    assert merge([HALF_ELF], [orphan, default]) == []


def test_the_loader_adds_merged_subraces_as_races(tmp_path: Path) -> None:
    import json

    (tmp_path / "races.json").write_text(
        json.dumps({"race": [HALF_ELF], "subrace": [MARK]})
    )
    omnidexer = Omnidexer(DataSet((DataDir(tmp_path),)))
    omnidexer.load_all_data()

    found = omnidexer.find(
        ContentType.RACE, "Half-Elf (Variant; Mark of Detection)", "ERLW"
    )

    assert found is not None
    assert omnidexer.find(ContentType.RACE, "Half-Elf", "PHB") is not None

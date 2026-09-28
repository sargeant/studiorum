"""The spell class lookup reads generated/ from the configured data directories."""

import json
from pathlib import Path

from studiorum.config import ApplicationConfig, DataConfig, set_app_config
from studiorum.data.loaders import spell_class_lookup
from studiorum.data.loaders.spell_class_lookup import (
    LOOKUP_FILE,
    SpellClassLookupService,
)


def _data_dir(root: Path, lookup: dict[str, object]) -> Path:
    (root / "generated").mkdir(parents=True)
    (root / "generated" / LOOKUP_FILE).write_text(json.dumps(lookup))
    return root


def test_the_lookup_comes_from_the_configured_data_dirs(tmp_path: Path) -> None:
    first = _data_dir(
        tmp_path / "a",
        {"phb": {"fireball": {"class": {"PHB": {"Wizard": True}}}}},
    )
    second = _data_dir(
        tmp_path / "b",
        {
            "phb": {
                "fireball": {"class": {"PHB": {"Sorcerer": True}}},
                "shield": {"class": {"PHB": {"Wizard": True}}},
            }
        },
    )
    set_app_config(ApplicationConfig(data=DataConfig(dirs=[first, second])))
    spell_class_lookup.reset()

    lookup = SpellClassLookupService()
    fireball = lookup.get_spell_classes("Fireball", "PHB")
    shield = lookup.get_spell_classes("Shield", "PHB")

    # The first directory wins a clash; the second fills in what it lacks
    assert fireball is not None
    assert [c.name for c in fireball.fromClassList] == ["Wizard"]
    assert shield is not None
    assert [c.name for c in shield.fromClassList] == ["Wizard"]


def test_no_lookup_file_means_no_classes(tmp_path: Path) -> None:
    set_app_config(ApplicationConfig(data=DataConfig(dirs=[tmp_path])))

    assert SpellClassLookupService().get_spell_classes("Fireball", "PHB") is None

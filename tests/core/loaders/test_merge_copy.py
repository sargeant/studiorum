"""merge_copy resolves _copy on raw JSON the way 5etools does."""

from typing import Any

from studiorum.core.loaders.merge_copy import resolve_copies


def _mm(name: str, **fields: Any) -> dict[str, Any]:
    return {"name": name, "source": "MM", **fields}


def _veteran() -> dict[str, Any]:
    return _mm(
        "Veteran",
        cr="3",
        str=16,
        ac=[{"ac": 17, "from": ["{@item splint armor|PHB}"]}],
        action=[
            {"name": "Multiattack", "entries": ["The veteran makes two attacks."]},
            {"name": "Longsword", "entries": ["{@hit 5} to hit, the veteran"]},
        ],
        environment=["urban"],
        page=350,
    )


def _resolve(*monsters: dict[str, Any], **kwargs: Any) -> list[Any]:
    return resolve_copies({"monster": list(monsters)}, **kwargs)


def test_a_copy_keeps_its_own_fields_and_inherits_the_rest() -> None:
    npc = {
        "name": "Captain Nobody",
        "source": "XYZ",
        "cr": "5",
        "action": [{"name": "Shout", "entries": ["Loudly."]}],
        "_copy": {"name": "Veteran", "source": "MM"},
    }
    assert _resolve(_veteran(), npc) == []
    assert npc["cr"] == "5"
    assert npc["action"] == [{"name": "Shout", "entries": ["Loudly."]}]
    assert npc["str"] == 16
    assert npc["ac"][0]["ac"] == 17
    assert npc["_isCopy"] is True
    assert "_copy" not in npc


def test_preserved_properties_need_preserve() -> None:
    plain = {"name": "A", "source": "X", "_copy": {"name": "Veteran", "source": "MM"}}
    kept = {
        "name": "B",
        "source": "X",
        "_copy": {"name": "Veteran", "source": "MM", "_preserve": {"page": True}},
    }
    _resolve(_veteran(), plain, kept)
    assert "page" not in plain
    assert "environment" not in plain
    assert kept["page"] == 350
    assert "environment" not in kept


def test_null_removes_an_inherited_property() -> None:
    npc = {
        "name": "A",
        "source": "X",
        "ac": None,
        "_copy": {"name": "Veteran", "source": "MM"},
    }
    _resolve(_veteran(), npc)
    assert "ac" not in npc


def test_mods_edit_the_copy_not_the_parent() -> None:
    veteran = _veteran()
    npc = {
        "name": "Bob",
        "source": "X",
        "_copy": {
            "name": "Veteran",
            "source": "MM",
            "_mod": {
                "*": {
                    "mode": "replaceTxt",
                    "replace": "the veteran",
                    "with": "Bob",
                    "flags": "i",
                },
                "action": [
                    {"mode": "prependArr", "items": {"name": "First", "entries": []}},
                    {"mode": "removeArr", "names": "Multiattack"},
                ],
            },
        },
    }
    _resolve(veteran, npc)
    assert [a["name"] for a in npc["action"]] == ["First", "Longsword"]
    assert npc["action"][1]["entries"] == ["{@hit 5} to hit, Bob"]
    assert [a["name"] for a in veteran["action"]] == ["Multiattack", "Longsword"]
    assert veteran["action"][1]["entries"] == ["{@hit 5} to hit, the veteran"]


def test_replace_txt_leaves_tags_alone_and_expands_groups() -> None:
    parent = _mm(
        "P", trait=[{"name": "T", "entries": ["the goblin hits {@creature goblin}"]}]
    )
    child = {
        "name": "C",
        "source": "X",
        "_copy": {
            "name": "P",
            "source": "MM",
            "_mod": {
                "trait": {
                    "mode": "replaceTxt",
                    "replace": "(the )goblin",
                    "with": "$1hobgoblin",
                }
            },
        },
    }
    _resolve(parent, child)
    assert child["trait"][0]["entries"] == ["the hobgoblin hits {@creature goblin}"]


def test_variables_resolve_against_the_copy() -> None:
    parent = _mm("Knight", cr="3", str=16, isNamedCreature=False)
    child = {
        "name": "Sir Test",
        "source": "X",
        "isNamedCreature": True,
        "_copy": {
            "name": "Knight",
            "source": "MM",
            "_mod": {
                "action": {
                    "mode": "appendArr",
                    "items": {
                        "name": "Hit",
                        "entries": [
                            "<$title_short_name$> attacks: {@hit <$to_hit__str$>}, DC <$dc__str$>"
                        ],
                    },
                }
            },
        },
    }
    _resolve(parent, child)
    assert child["action"][0]["entries"] == ["Sir attacks: {@hit +5}, DC 13"]


def test_copy_of_a_copy_resolves_the_parent_first() -> None:
    middle = {
        "name": "Middle",
        "source": "X",
        "hp": 9,
        "_copy": {"name": "Veteran", "source": "MM"},
    }
    leaf = {"name": "Leaf", "source": "X", "_copy": {"name": "Middle", "source": "X"}}
    assert _resolve(leaf, middle, _veteran()) == []
    assert leaf["hp"] == 9
    assert leaf["str"] == 16
    assert "_copy" not in middle


def test_templates_apply_mods_and_root_properties() -> None:
    templates = [
        {
            "name": "Big",
            "source": "X",
            "apply": {
                "_root": {"size": ["L"], "str": 1},
                "_mod": {"trait": {"mode": "appendArr", "items": {"name": "Huge"}}},
            },
        },
        {"name": "Bigger", "source": "X", "_copy": {"name": "Big", "source": "X"}},
    ]
    child = {
        "name": "C",
        "source": "X",
        "str": 20,
        "_copy": {
            "name": "Veteran",
            "source": "MM",
            "_templates": [{"name": "bigger", "source": "x"}],
        },
    }
    assert _resolve(_veteran(), child, templates={"monster": templates}) == []
    assert child["size"] == ["L"]
    assert child["str"] == 20
    assert child["trait"] == [{"name": "Huge"}]
    assert child["_copy_templates"] == [{"name": "bigger", "source": "x"}]


def test_insert_arr_without_an_index_inserts_at_the_start() -> None:
    child = {
        "name": "C",
        "source": "X",
        "_copy": {
            "name": "Veteran",
            "source": "MM",
            "_mod": {"action": {"mode": "insertArr", "items": {"name": "Zero"}}},
        },
    }
    _resolve(_veteran(), child)
    assert child["action"][0] == {"name": "Zero"}


def test_a_missing_parent_is_reported_and_the_copy_left_alone() -> None:
    orphan = {
        "name": "Orphan",
        "source": "X",
        "_copy": {"name": "Nobody", "source": "MM"},
    }
    failures = _resolve(orphan)
    assert [(f.prop, f.name) for f in failures] == [("monster", "Orphan")]
    assert "_copy" in orphan


def test_a_failing_mod_is_reported() -> None:
    child = {
        "name": "C",
        "source": "X",
        "_copy": {
            "name": "Veteran",
            "source": "MM",
            "_mod": {"action": {"mode": "removeArr", "names": "Not There"}},
        },
    }
    failures = _resolve(_veteran(), child)
    assert len(failures) == 1
    assert "Not There" in failures[0].message


def test_items_are_keyed_by_inherited_source_and_deities_by_pantheon() -> None:
    items = [
        {"name": "Base", "inherits": {"source": "DMG"}, "weight": 1},
        {"name": "Child", "source": "X", "_copy": {"name": "Base", "source": "DMG"}},
    ]
    deities = [
        {"name": "Odin", "pantheon": "Norse", "source": "PHB", "title": "Allfather"},
        {"name": "Odin", "pantheon": "Other", "source": "PHB", "title": "Wrong"},
        {
            "name": "Odin",
            "pantheon": "Norse",
            "source": "X",
            "_copy": {"name": "Odin", "pantheon": "Norse", "source": "PHB"},
        },
    ]
    assert resolve_copies({"item": items, "deity": deities}) == []
    assert items[1]["weight"] == 1
    assert deities[2]["title"] == "Allfather"

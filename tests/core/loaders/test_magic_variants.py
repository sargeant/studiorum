"""expand builds specific magic items from base items and generic variants."""

from studiorum.core.loaders.magic_variants import expand

LONGSWORD = {
    "name": "Longsword",
    "source": "PHB",
    "edition": "classic",
    "type": "M",
    "weapon": True,
    "dmgType": "S",
    "value": 1500,
    "weight": 3,
    "srd": True,
    "page": 149,
}
NET = LONGSWORD | {"name": "Net", "net": True, "value": 100}
PLUS_ONE = {
    "name": "+1 Weapon",
    "source": "DMG",
    "edition": "classic",
    "requires": [{"weapon": True}],
    "excludes": {"net": True},
    "inherits": {
        "namePrefix": "+1 ",
        "source": "DMG",
        "rarity": "uncommon",
        "bonusWeapon": "+1",
        "srd": True,
        "entries": ["A {=bonusWeapon} {=baseName/l} dealing {=dmgType} damage."],
    },
}


def test_a_variant_applies_to_the_base_items_it_requires() -> None:
    [item] = expand([LONGSWORD, NET], [PLUS_ONE])

    assert item["name"] == "+1 Longsword"
    assert (item["source"], item["rarity"], item["bonusWeapon"]) == (
        "DMG",
        "uncommon",
        "+1",
    )
    assert item["entries"] == ["A +1 longsword dealing Slashing damage."]
    assert item["baseItem"] == "longsword|phb"
    assert item["genericVariant"] == {"name": "+1 Weapon", "source": "DMG"}
    # A magic item takes neither the base item's value nor its page
    assert "value" not in item and "page" not in item
    assert item["srd"] is True


def test_editions_pair_as_5etools_pairs_them() -> None:
    longsword_2024 = LONGSWORD | {"source": "XPHB", "edition": "one"}
    plus_one_2024 = PLUS_ONE | {"edition": "one"}

    assert expand([longsword_2024], [PLUS_ONE]) == []
    assert [i["name"] for i in expand([longsword_2024], [plus_one_2024])] == [
        "+1 Longsword"
    ]
    assert expand([LONGSWORD], [plus_one_2024]) == []


def test_names_expressions_and_resistances() -> None:
    variant = {
        "name": "Of Fire",
        "source": "DMG",
        "edition": "classic",
        "requires": [{"type": "M"}],
        "inherits": {
            "nameRemove": "sword",
            "nameSuffix": "blade of Fire Resistance",
            "source": "DMG",
            "valueExpression": "[[baseItem.value]] * 4",
            "resist": ["fire"],
        },
    }
    base = LONGSWORD | {"vulnerable": ["fire", "cold"]}

    [item] = expand([base], [variant])

    assert item["name"] == "Longblade of Fire Resistance"
    assert item["value"] == 6000
    # A granted resistance leaves the vulnerabilities
    assert (item["resist"], item["vulnerable"]) == (["fire"], ["cold"])

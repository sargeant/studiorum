from studiorum.core.text.prerequisites import prerequisite_entry
from studiorum.core.text.strings import common_suffix, join_conjunct, ordinal


def test_join_conjunct_uses_the_oxford_comma() -> None:
    assert join_conjunct(["a"], ", ", " or ") == "a"
    assert join_conjunct(["a", "b"], ", ", " or ") == "a or b"
    assert join_conjunct(["a", "b", "c"], ", ", " or ") == "a, b, or c"


def test_common_suffix_is_whole_words() -> None:
    assert common_suffix(["Strength 13", "Dexterity 13"]) == " 13"
    assert common_suffix(["Alert"]) == "Alert"
    assert common_suffix(["a b", "c d"]) == ""


def test_ordinal() -> None:
    assert [ordinal(n) for n in (1, 2, 3, 4, 11, 12, 21)] == [
        "1st", "2nd", "3rd", "4th", "11th", "12th", "21st",
    ]  # fmt: skip


def test_classic_and_one_wording() -> None:
    # XPHB's Grappler: two ways to qualify, sharing the level
    grappler = [
        {"level": 4, "ability": [{"str": 13}]},
        {"level": 4, "ability": [{"dex": 13}]},
    ]
    assert prerequisite_entry(grappler) == (
        "Prerequisites: 4th level, Strength or Dexterity 13 or higher"
    )
    assert prerequisite_entry(grappler, style="one") == (
        "Prerequisites: Level 4+, Strength or Dexterity 13+"
    )


def test_choices_share_their_common_parts() -> None:
    prereqs = [
        {"level": 4, "race": [{"name": "elf"}]},
        {"level": 4, "race": [{"name": "half-elf"}]},
    ]
    assert prerequisite_entry(prereqs) == "Prerequisites: 4th level, Elf or Half-Elf"


def test_tags_stay_for_the_renderer() -> None:
    assert prerequisite_entry([{"feat": ["alert|xphb"]}], skip_prefix=True) == (
        "{@feat alert|xphb}"
    )
    assert prerequisite_entry([{"spell": ["eldritch blast#c"]}]) == (
        "Prerequisite: {@spell eldritch blast} cantrip"
    )


def test_none_is_empty() -> None:
    assert prerequisite_entry(None) == ""
    assert prerequisite_entry([]) == ""

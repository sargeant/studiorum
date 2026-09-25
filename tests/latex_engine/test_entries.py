"""EntryRenderer: 5etools entries to LaTeX."""

from dataclasses import dataclass
from unittest.mock import Mock

import pytest

from studiorum.core.models.content import ContentType
from studiorum.core.models.creatures import Ability, Creature
from studiorum.core.references.content_tracker import ContentTracker
from studiorum.latex_engine.core.template_engine import environment
from studiorum.latex_engine.entries import (
    EntryError,
    EntryRenderer,
    Style,
    column_spec,
    creature_ac_text,
    creature_senses_text,
)


def render(entry: object, style: Style | None = None) -> str:
    return EntryRenderer(style=style).entry(entry)


def test_strings_render_tags_and_track_references() -> None:
    tracker = ContentTracker()
    out = EntryRenderer(tracker=tracker).entry("Cast {@spell fireball} & run")

    assert out == "Cast \\textit{fireball} \\& run"
    assert "spell" in tracker.export_for_appendix()


def test_render_takes_a_list_a_thing_with_entries_or_one_entry() -> None:
    renderer = EntryRenderer()

    assert renderer.render(["a", "b"]) == "a\n\nb"
    assert renderer.render({"type": "entries", "name": "X", "entries": ["a"]}) == "a"
    assert renderer.render("a") == "a"


@pytest.mark.parametrize(
    ("style", "commands"),
    [
        (Style(), ["section", "subsubsection", "paragraph"]),
        (Style(book=True), ["section", "subsection", "subsubsection"]),
        (
            Style(content_type="spell"),
            ["subsubsection", "subparagraph", "subparagraph"],
        ),
        (Style(content_type="item"), ["subsubsection", "subparagraph", "subparagraph"]),
        (Style(sidebar=True), ["subsubsection", "subparagraph", "subparagraph"]),
    ],
)
def test_section_headings_follow_the_style(style: Style, commands: list[str]) -> None:
    """A section heads at its depth, a named block one level below its own."""
    tree = {
        "type": "section",
        "name": "A",
        "entries": [
            {
                "type": "entries",
                "name": "B",
                "entries": [{"name": "C", "type": "entries"}],
            }
        ],
    }
    assert render(tree, style) == "\n\n".join(
        f"\\{command}{{{name}}}" for command, name in zip(commands, "ABC", strict=True)
    )


def test_lists() -> None:
    assert render({"type": "list", "items": ["a", "b"]}) == (
        "\\begin{itemize}\n\\item a\n\\item b\n\\end{itemize}"
    )
    assert render({"type": "list", "style": "ordered", "items": ["a"]}).startswith(
        "\\begin{enumerate}"
    )
    assert render({"type": "list", "items": []}) == ""


def test_hanging_list_labels_items_by_name() -> None:
    out = render(
        {
            "type": "list",
            "style": "list-hang-notitle",
            "items": [
                {"type": "item", "name": "Fire", "entry": "Hot"},
                {"type": "item", "name": "Ice:", "entry": "Cold"},
                "plain",
            ],
        }
    )
    assert out == (
        "\\begin{description}\n\\item[Fire.] Hot\n\\item[Ice:] Cold\n"
        "\\item[\\mbox{}] plain\n\\end{description}"
    )


def test_an_unnamed_block_breaks_out_of_a_hanging_list() -> None:
    out = render(
        {
            "type": "list",
            "style": "list-hang",
            "items": ["a", {"type": "entries", "entries": ["block"]}, "b"],
        }
    )
    assert out == (
        "\\begin{description}\n\\item[\\mbox{}] a\n\\end{description}\nblock\n"
        "\\begin{description}\n\\item[\\mbox{}] b\n\\end{description}"
    )


def test_credits_list_wraps_named_blocks_in_a_list() -> None:
    out = render(
        {
            "type": "list",
            "style": "list-hang-notitle",
            "items": [
                {"type": "list", "items": ["Lead"]},
                {"type": "entries", "name": "Studio", "entries": ["Sam"]},
            ],
        }
    )
    assert out.startswith("\\begin{itemize}\n\\item Lead\n\\end{itemize}\n")
    assert "\\begin{description}\n\\item[Studio.] " in out
    assert out.endswith("\\end{description}")


def test_table() -> None:
    out = render(
        {
            "type": "table",
            "caption": "Loot & More",
            "colLabels": ["{@dice d6}", "Item"],
            "colStyles": ["col-2 text-center", "col-10"],
            "rows": [
                ["1", "Gold"],
                [{"type": "cell", "roll": {"min": 2, "max": 6}}, "Gems"],
            ],
        }
    )
    assert out == (
        "% Table: Loot & More\n"
        "\\begin{DndTable}[header={Loot \\& More}]{cX}\n"
        "d6 & Item \\\\\n1 & Gold \\\\\n2–6 & Gems \\\\\n\\end{DndTable}"
    )
    assert render({"type": "table", "rows": []}) == "% Empty table"


def test_column_spec_stretches_wide_tables() -> None:
    assert column_spec([], 3) == "lll"
    assert column_spec(["col-2 text-center", "col-10"], 2) == "cX"
    assert column_spec(["col-3", "col-1 text-center", "col-1 text-center"] * 2, 6) == (
        "lXXlXX"
    )


def test_insets_are_sidebars_with_deeper_headings() -> None:
    out = render(
        {
            "type": "inset",
            "name": "Note & Aside",
            "entries": [{"type": "entries", "name": "Sub", "entries": ["x"]}],
        }
    )
    assert out == (
        "\\begin{DndSidebar}{Note \\& Aside}\n\\paragraph{Sub}\n\nx\n\\end{DndSidebar}"
    )
    assert render({"type": "insetReadaloud", "entries": ["Hush"]}) == (
        "\\begin{DndReadAloud}\nHush\n\\end{DndReadAloud}"
    )


def test_quote() -> None:
    assert render({"type": "quote", "entries": ["Hi"], "by": "Sam"}) == (
        "\\begin{quotation}\n\\em\nHi\n\n\\hfill --- Sam\n\\end{quotation}"
    )


def test_run_in_entries() -> None:
    assert render({"type": "actions", "name": "Dash", "entries": ["Go."]}) == (
        "\\textbf{Dash.} Go."
    )
    assert render({"type": "item", "name": "Key", "entry": "Opens"}) == (
        "\\textbf{Key.} Opens"
    )
    assert render({"type": "abilityDc", "attributes": ["int"]}) == (
        "\\textbf{Save DC:} 8 + proficiency bonus + Intelligence modifier"
    )
    assert render({"type": "bonus", "value": 2}) == "+2"
    assert render({"type": "bonusSpeed", "value": -5}) == "-5 ft."
    assert render({"type": "dice", "toRoll": [{"number": 2, "faces": 6}]}) == "2d6"
    assert render({"type": "attack", "name": "Bite", "entries": ["x"]}) == (
        "\\textit{Bite.} x"
    )
    assert render({"type": "variantSub", "name": "Alt", "entries": ["x"]}) == (
        "\\textit{Alt:} x"
    )
    assert render({"type": "variant", "name": "Rule", "entries": ["x"]}) == (
        "\\textbf{Variant: Rule}\n\nx"
    )
    assert render({"type": "abilityGeneric", "name": "Note", "text": "x"}) == (
        "\\textbf{Note:} x"
    )
    assert render({"type": "options", "entries": ["a", "b"]}) == (
        "\\begin{itemize}\n\\item a\n\\item b\n\\end{itemize}"
    )


SPELLCASTING = {
    "type": "spellcasting",
    "name": "Spellcasting",
    "headerEntries": ["It casts:"],
    "spells": {"0": {"spells": ["light"]}, "1": {"slots": 2, "spells": ["shield"]}},
    "daily": {"1e": ["{@spell fly}"]},
}


def test_spellcasting_uses_monster_macros_in_statblocks() -> None:
    out = render(SPELLCASTING, Style(monster_spells=True))
    assert out == (
        "\\textbf{Spellcasting.}\nIt casts:\n"
        "\\textbf{1e:} \\textit{fly}\n"
        "\\begin{DndMonsterSpells}\n"
        "  \\DndMonsterSpellLevel{light}\n"
        "  \\DndMonsterSpellLevel[1][2]{shield}\n"
        "\\end{DndMonsterSpells}"
    )


def test_spellcasting_uses_bold_labels_elsewhere() -> None:
    out = render(SPELLCASTING)
    assert "\\begin{DndMonsterSpells}" not in out
    assert "\\textbf{Cantrips (at will):} light" in out
    assert "\\textbf{1st level (2 slots):} shield" in out


def test_generic_entries_render_name_and_text() -> None:
    assert render({"type": "somethingNew", "name": "N", "text": "t"}) == (
        "\\subsection{N}\n\nt\n\nt"
    )


def test_unresolved_statblock_is_a_heading() -> None:
    renderer = EntryRenderer(omnidexer=Mock(find=Mock(return_value=None)))
    assert renderer.entry(
        {"type": "statblock", "tag": "creature", "name": "Nobody"}
    ) == ("\\section{Nobody}")


@pytest.mark.parametrize(
    ("statblock", "lookup"),
    [
        ({"tag": "spell", "name": "Wish"}, (ContentType.SPELL, "Wish", "PHB")),
        (
            {"tag": "charoption", "name": "Echo", "source": "VRGR"},
            (ContentType.CHAROPTION, "Echo", "VRGR"),
        ),
        (
            {"prop": "monsterFluff", "tag": "creature", "name": "Orc", "source": "MM"},
            (ContentType.CREATURE_FLUFF, "Orc", "MM"),
        ),
    ],
)
def test_statblocks_look_up_their_prop_or_tag(
    statblock: dict[str, str], lookup: tuple[object, ...]
) -> None:
    find = Mock(return_value=None)
    EntryRenderer(omnidexer=Mock(find=find)).entry({"type": "statblock", **statblock})

    find.assert_called_once_with(*lookup)


def test_statblocks_of_unknown_kinds_are_a_heading() -> None:
    find = Mock()
    out = EntryRenderer(omnidexer=Mock(find=find)).entry(
        {"type": "statblock", "tag": "crochet", "name": "Cube"}
    )

    assert out == "\\section{Cube}"
    find.assert_not_called()


def test_models_and_dataclasses_render_as_their_dicts() -> None:
    @dataclass
    class Block:
        type: str
        entries: list[str]

    assert render(Block("entries", ["x"])) == "x"
    assert render(3) == "3"


def test_a_failure_names_where_it_happened() -> None:
    tree = {
        "type": "section",
        "name": "Chapter",
        "entries": [{"type": "table", "name": "Loot", "rows": 5}],
    }
    with pytest.raises(EntryError, match="table entry at Chapter › Loot"):
        render(tree)
    with pytest.raises(EntryError, match="Cannot render a object"):
        render(object())


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
        environment().filters["safe_processed_name"](ability)
        == "Fire Breath (Recharge 5--6)"
    )


def test_armour_class_renders_its_sources() -> None:
    assert creature_ac_text(CREATURE) == "18 (\\textit{plate armor}), 12"


def test_senses_render_tags() -> None:
    assert creature_senses_text(CREATURE) == "\\textit{darkvision} 60 ft."


def _statblock_in_section(creature: Creature) -> str:
    renderer = EntryRenderer(
        omnidexer=Mock(find=Mock(return_value=creature)), style=Style(book=True)
    )
    return renderer.entry(
        {
            "type": "section",
            "name": "Knights",
            "entries": [{"type": "statblock", "tag": "creature", "name": "Knight"}],
        }
    )


def test_creature_statblocks_sit_in_the_text() -> None:
    out = _statblock_in_section(CREATURE)

    assert "\\begin{DndMonster}{Knight}" in out
    assert "FloatBarrier" not in out


def test_a_wide_statblock_floats_to_the_end_of_its_section() -> None:
    legendary = CREATURE.model_copy(
        update={"legendary": [Ability(name="Charge", entries=["It moves."])]}
    )
    out = _statblock_in_section(legendary)

    assert "\\begin{DndMonster}[float*=tp" in out
    assert out.endswith("\\FloatBarrier")


def test_statblocks_take_their_display_name() -> None:
    renderer = EntryRenderer(omnidexer=Mock(find=Mock(return_value=CREATURE)))
    out = renderer.entry(
        {
            "type": "statblock",
            "tag": "creature",
            "name": "Knight",
            "displayName": "Sir Knight",
        }
    )

    assert "\\begin{DndMonster}{Sir Knight}" in out

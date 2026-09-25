"""Content as the entries 5etools' compact renderer shows."""

from studiorum.core.compact import compact_entries
from studiorum.core.models.feats import Feat
from studiorum.core.models.recipes import Recipe
from studiorum.core.models.table import Table, TableGroup


def test_a_table_is_a_table_entry_without_a_caption_that_repeats_its_name() -> None:
    table = Table.model_validate(
        {
            "name": "Mortuary Encounters",
            "source": "AATM",
            "caption": "Mortuary Encounters",
            "colLabels": ["d10", "Encounter"],
            "rows": [["1", "A zombie."], {"type": "row", "row": [2, "Nothing."]}],
            "chapter": {"name": "The Mortuary", "index": 1},
        }
    )

    assert compact_entries(table, None) == [
        {
            "type": "table",
            "colLabels": ["d10", "Encounter"],
            "rows": [["1", "A zombie."], {"type": "row", "row": [2, "Nothing."]}],
        }
    ]


def test_a_table_group_is_its_tables() -> None:
    group = TableGroup.model_validate(
        {
            "name": "Giant Encounters",
            "source": "BGG",
            "tables": [
                {"type": "table", "caption": "Levels 1-4", "rows": [["1", "A"]]},
                {"type": "table", "caption": "Levels 5-10", "rows": [["1", "B"]]},
            ],
        }
    )

    assert [t["caption"] for t in compact_entries(group, None)] == [
        "Levels 1-4",
        "Levels 5-10",
    ]


def test_other_content_is_its_entries() -> None:
    feat = Feat.model_validate({"name": "Alert", "source": "PHB", "entries": ["Hi."]})

    assert compact_entries(feat, None) == ["Hi."]


def test_a_recipe_lays_out_servings_ingredients_instructions_and_notes() -> None:
    recipe = Recipe.model_validate(
        {
            "name": "Stew",
            "source": "HF",
            "serves": {"min": 4, "max": 6},
            "ingredients": [
                {
                    "type": "ingredient",
                    "entry": "{=amount1/v} cup flour",
                    "amount1": 0.25,
                },
                "Salt",
                {
                    "type": "entries",
                    "name": "For the sauce",
                    "entries": [
                        {
                            "type": "ingredient",
                            "entry": "{=amount3/v} egg",
                            "amount3": 1,
                        }
                    ],
                },
            ],
            "instructions": ["Stir."],
            "noteCook": ["Tasty."],
        }
    )

    assert compact_entries(recipe, None) == [
        "{@b Serves} 4 to 6",
        {
            "type": "inset",
            "name": "Ingredients",
            "entries": [
                {
                    "type": "list",
                    "items": [
                        {"type": "ingredient", "entry": "¼ cup flour", "amount1": 0.25},
                        "Salt",
                    ],
                },
                {
                    "type": "entries",
                    "name": "For the sauce",
                    "entries": [
                        {
                            "type": "list",
                            "items": [
                                {"type": "ingredient", "entry": "1 egg", "amount3": 1}
                            ],
                        }
                    ],
                },
            ],
        },
        "Stir.",
        {"type": "entries", "name": "Cook's Notes", "entries": ["{@i Tasty.}"]},
    ]

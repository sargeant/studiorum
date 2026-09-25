"""5etools' property templates, ``{=name/modifiers}``."""

import pytest

from studiorum.core.text.properties import (
    apply_properties,
    number_to_text,
    number_to_vulgar,
)


def test_templates_fill_inside_tags() -> None:
    assert apply_properties(
        ["{=baseName/a} {@item {=baseName}|PHB}", {"entries": ["{=baseName/at}"]}],
        {"baseName": "axe"},
    ) == ["an {@item axe|PHB}", {"entries": ["An"]}]


def test_without_props_each_string_reads_the_object_around_it() -> None:
    ingredients = [
        {"type": "ingredient", "entry": "{=amount1/v} cup flour", "amount1": 0.25},
        {"type": "ingredient", "entry": "{=amount1/xt} eggs", "amount1": 2},
        "{=amount1/v} left alone",
    ]

    assert apply_properties(ingredients) == [
        {"type": "ingredient", "entry": "¼ cup flour", "amount1": 0.25},
        {"type": "ingredient", "entry": "Two eggs", "amount1": 2},
        "{=amount1/v} left alone",
    ]


@pytest.mark.parametrize(
    ("number", "text"),
    [(2, "2"), (0.5, "½"), (1.25, "1¼"), (0.33, "⅓"), (1.67, "1⅔"), (0.3, "3/10")],
)
def test_numbers_as_vulgar_fractions(number: float, text: str) -> None:
    assert number_to_vulgar(number) == text


@pytest.mark.parametrize(
    ("number", "text"), [(3, "three"), (21, "twenty-one"), (40, "forty"), (120, "120")]
)
def test_numbers_as_words(number: int, text: str) -> None:
    assert number_to_text(number) == text

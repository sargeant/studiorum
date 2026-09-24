"""CONTENT_MODELS maps every content type to its model, and back."""

import pytest

from studiorum.core.models.content import ContentType
from studiorum.core.models.content_models import (
    CONTENT_MODELS,
    FLUFF_TYPES,
    content_type_of,
    create_content,
)
from studiorum.core.models.fluff import BaseFluff, SpellFluff
from studiorum.core.models.spells import Spell


def test_every_content_type_but_reference_has_a_model() -> None:
    assert set(ContentType) - set(CONTENT_MODELS) == {ContentType.REFERENCE}


def test_fluff_types_are_the_fluff_models() -> None:
    assert ContentType.CREATURE_FLUFF in FLUFF_TYPES
    assert ContentType.FLUFF in FLUFF_TYPES
    assert ContentType.CREATURE not in FLUFF_TYPES


@pytest.mark.parametrize(("content_type", "model"), list(CONTENT_MODELS.items()))
def test_content_type_of_round_trips(
    content_type: ContentType, model: type[BaseFluff]
) -> None:
    item = model.model_construct(name="X", source={"abbreviation": "PHB"})
    assert content_type_of(item) == content_type


def test_content_type_of_uses_the_nearest_base_for_a_subclass() -> None:
    class LocalSpellFluff(SpellFluff):
        pass

    item = LocalSpellFluff(name="X", source="PHB")
    assert content_type_of(item) == ContentType.FLUFF


def test_create_content_validates_with_the_model() -> None:
    spell = create_content(
        {
            "name": "Light",
            "source": "PHB",
            "level": 0,
            "school": "V",
            "time": [{"number": 1, "unit": "action"}],
            "range": {"type": "point", "distance": {"type": "touch"}},
            "components": {"v": True},
            "duration": [{"type": "timed", "duration": {"type": "hour", "amount": 1}}],
            "entries": ["You touch one object."],
        },
        ContentType.SPELL,
    )
    assert isinstance(spell, Spell)


def test_create_content_rejects_a_type_without_a_model() -> None:
    with pytest.raises(ValueError, match="Unsupported content type"):
        create_content({}, ContentType.REFERENCE)

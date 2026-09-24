"""Content models accept the shapes 5etools ships (each case trimmed from its data)."""

from __future__ import annotations

from studiorum.core.models.content import Reprint
from studiorum.core.models.variantrule import VariantRule


def test_reprints_take_both_forms() -> None:
    rule = VariantRule.model_validate(
        {
            "name": "Falling",
            "source": "XGE",
            "entries": ["..."],
            "reprintedAs": ["Falling|XDMG", {"uid": "Falling|XPHB", "tag": "hazard"}],
        }
    )

    assert rule.reprinted_as == [
        "Falling|XDMG",
        Reprint(uid="Falling|XPHB", tag="hazard"),
    ]

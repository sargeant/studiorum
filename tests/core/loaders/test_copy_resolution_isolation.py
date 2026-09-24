"""Resolving a _copy must leave the source creature unchanged."""

from types import SimpleNamespace
from unittest.mock import Mock

from studiorum.core.resolvers.copy_resolver import CopyResolver


def test_mod_on_copy_does_not_edit_source() -> None:
    source = SimpleNamespace(
        name="Adult Silver Dragon",
        trait=[{"name": "Legendary Resistance", "entries": ["The dragon succeeds."]}],
        action=[{"name": "Multiattack", "entries": ["The dragon attacks."]}],
    )
    target = SimpleNamespace(name="Stalagma")
    copy_ref = {
        "name": "Adult Silver Dragon",
        "_mod": {
            "*": {
                "mode": "replaceTxt",
                "replace": "the dragon",
                "with": "Stalagma",
                "flags": "i",
            },
            "trait": {
                "mode": "appendArr",
                "items": {"name": "Extra", "entries": ["x"]},
            },
        },
    }

    CopyResolver(Mock())._apply_copy_resolution_direct(
        target, source, copy_ref, "Stalagma"
    )

    assert target.action[0]["entries"] == ["Stalagma attacks."]
    assert len(target.trait) == 2
    assert source.action[0]["entries"] == ["The dragon attacks."]
    assert source.trait == [
        {"name": "Legendary Resistance", "entries": ["The dragon succeeds."]}
    ]

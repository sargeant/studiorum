"""Omnidexer lookups answer from the index in memory, never from an earlier run."""

from studiorum.core.loaders.omnidexer import Omnidexer
from studiorum.core.models.content import ContentType


def test_lookups_do_not_outlive_the_index(test_data_omnidexer: Omnidexer) -> None:
    creature = ContentType("creature")
    assert test_data_omnidexer.find(creature, "Goblin") is not None
    assert test_data_omnidexer.search("Goblin", creature)

    # A second omnidexer that has loaded nothing must not see the first one's
    # results, as it did when find and search went through the disk cache.
    empty = Omnidexer()
    assert empty.find(creature, "Goblin") is None
    assert empty.search("Goblin", creature) == []

"""Catalogue lookups answer from the index in memory, never from an earlier run."""

from studiorum.data.catalogue import Catalogue
from studiorum.data.loaders.data_dir import DataSet
from studiorum.data.models.content import ContentType


def test_lookups_do_not_outlive_the_index(test_data_catalogue: Catalogue) -> None:
    creature = ContentType("creature")
    assert test_data_catalogue.find(creature, "Goblin") is not None
    assert test_data_catalogue.search("Goblin", creature)

    # A second catalogue that has loaded nothing must not see the first one's
    # results, as it did when find and search went through the disk cache.
    empty = Catalogue(DataSet(()))
    assert empty.find(creature, "Goblin") is None
    assert empty.search("Goblin", creature) == []

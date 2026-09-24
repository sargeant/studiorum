"""Tests for the class options LaTeXDocumentConfig produces."""

import pytest
from pydantic import ValidationError

from studiorum.core.config.unified_config import LaTeXDocumentConfig


def test_defaults_match_documents_rendered_before_the_merge() -> None:
    assert LaTeXDocumentConfig().class_options() == [
        "letterpaper",
        "11pt",
        "bg=full",
        "twocolumn",
        "stats=modern",
    ]


def test_every_typed_field_reaches_the_class_options() -> None:
    config = LaTeXDocumentConfig(
        paper_size="a4",
        font_size="10pt",
        background="print",
        high_contrast=True,
        justified_text=True,
        fancy_headers=True,
        two_column=False,
        fonts="wotc",
        no_outline=True,
        statblock="2014",
    )

    assert config.class_options() == [
        "a4paper",
        "10pt",
        "bg=print",
        "highcontrast",
        "justified",
        "fancy",
        "onecolumn",
        "fonts=wotc",
        "nooutline",
    ]


def test_extra_class_options_come_last_without_duplicates() -> None:
    config = LaTeXDocumentConfig(extra_class_options=["draft", "twocolumn"])

    assert config.class_options()[-2:] == ["stats=modern", "draft"]


def test_the_old_class_options_key_is_ignored() -> None:
    config = LaTeXDocumentConfig.model_validate({"class_options": ["justified"]})

    assert "justified" not in config.class_options()


def test_document_class_must_be_a_dnd_class() -> None:
    with pytest.raises(ValidationError):
        LaTeXDocumentConfig.model_validate({"document_class": "article"})

"""5etools tags rendered to LaTeX."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from studiorum.core.config.unified_config import load_config
from studiorum.core.references.content_tracker import ContentTracker
from studiorum.renderers.context import RenderingContext
from studiorum.renderers.tags import TagResolver, render
from studiorum.services import build_services


@pytest.fixture
def resolver() -> TagResolver:
    return TagResolver()


@pytest.mark.parametrize(
    ("text", "latex"),
    [
        ("plain & 50% $5", r"plain \& 50\% \$5"),
        ("{@creature goblin|MM}", r"\textbf{goblin}"),
        ("{@creature goblin|MM|goblins}", r"\textbf{goblins}"),
        ("{@spell fireball}", r"\textit{fireball}"),
        ("{@item +1 longsword|DMG}", r"\textit{+1 longsword}"),
        ("{@race elf}", "elf"),
        ("{@condition frightened}", "frightened"),
        ("{@variantrule Cone [Area of Effect]|XPHB|Cone}", "Cone"),
        ("{@skill Perception}", r"\textit{Perception}"),
        ("{@b bold}", r"\textbf{bold}"),
        ("{@i italic}", r"\textit{italic}"),
        ("{@b Dungeons & Dragons}", r"\textsc{Dungeons \& Dragons}"),
        ("{@dice 1d6 + 2}", "1d6 + 2"),
        ("{@damage 2d6}", "2d6"),
        ("{@dc 15}", "DC 15"),
        ("{@hit 5}", "+5"),
        ("{@hit -1}", "-1"),
        ("{@ability con 14}", "+2"),
        ("{@savingThrow con 3}", "+3"),
        ("{@skillCheck athletics 4}", "+4"),
        ("{@chance 25}", "25 percent"),
        ("{@chance 50|half the time}", "half the time"),
        ("{@recharge 5}", "(Recharge 5--6)"),
        ("{@recharge}", "(Recharge 6)"),
        ("{@recharge 4|m}", "Recharge 4--6"),
        ("{@atk mw}", "Melee Weapon Attack:"),
        ("{@atk rs,ms}", "Ranged Spell or Melee Spell Attack:"),
        ("{@h}", "Hit: "),
        ("{@hom}", r"\textit{Hit or Miss:}"),
        ("{@actSave dex}", r"\textit{Dexterity Saving Throw:}"),
        ("{@actSaveFail 2}", r"\textit{Second Failure:}"),
        ("{@actSaveFailBy 5}", r"\textit{Failure by 5 or more:}"),
        ("{@actResponse d}", r"\textit{Response---}"),
        ("{@hitYourSpellAttack}", "your spell attack modifier"),
        ("{@note a {@spell light} note}", r"\textit{a \textit{light} note}"),
        ("{@link Site|https://x.org/a#b}", r"\href{https://x.org/a\#b}{Site}"),
        ("{@quickref difficult terrain||3}", r"\textit{difficult terrain}"),
        ("{@adventure Chapter 2|LMoP|2}", "Chapter 2"),
        ("{@book chapter 5|PHB|5}", "chapter 5"),
        ("{@area Cragmaw Hideout|0a1|x}", "Cragmaw Hideout"),
        ("{@vehicle Ship of the Line|GoS}", "Ship of the Line"),
        ("{@classFeature Rage|Barbarian||1}", "Rage"),
        (
            "{@b bold {@spell fireball} & more}",
            r"\textbf{bold \textit{fireball} \& more}",
        ),
        ("{@filter 1st|spells|level=1} level", "1st level"),
        ("{@area 5|123} and {@area 6|124|u}", "area 5 and Area 6"),
        ("{@scaledamage 8d6|3-9|1d6}", "1d6"),
        ("{@dice d6;d8} {@damage (level)d4|1d4} {@d20 4}", "d6/d8 1d4 +4"),
    ],
)
def test_tag(resolver: TagResolver, text: str, latex: str) -> None:
    assert resolver.process_text(text) == latex


def test_nested_display_text_renders_recursively(resolver: TagResolver) -> None:
    text = "{@creature goblin|MM|the {@i sneaky} goblin}"
    assert resolver.process_text(text) == r"\textbf{the \textit{sneaky} goblin}"


def test_unhandled_tag_renders_escaped_display_text(resolver: TagResolver) -> None:
    text = "Ride the {@vehicle Ship of the Line|GoS} & go"
    assert resolver.process_text(text) == r"Ride the Ship of the Line \& go"


def test_unknown_tag_renders_display_text_and_warns_once() -> None:
    with (
        patch("studiorum.renderers.tags._warned", set()),
        patch("studiorum.renderers.tags.logger") as logger,
    ):
        latex = render("{@notATag first|second|shown & {@b bold}} x")
        render("{@notATag again}")
    assert latex == r"shown \& \textbf{bold} x"
    logger.warning.assert_called_once()
    assert "@notATag" in logger.warning.call_args.args[0]


def test_references_are_tracked_including_nested_ones(resolver: TagResolver) -> None:
    tracker = ContentTracker()
    context = RenderingContext(output_format="latex", content_tracker=tracker)
    resolver.process_text(
        "{@note see {@creature goblin|MM}} and {@spell fireball|PHB|Fire}", context
    )
    tracked = {
        (c.content_type, c.name, c.source) for c in tracker.get_tracked_content()
    }
    assert tracked == {("creature", "goblin", "MM"), ("spell", "fireball", "PHB")}


def test_resolver_is_built_without_loading_data() -> None:
    services = build_services(load_config(Path("tests/test-config.yaml")))
    with patch.object(
        type(services), "load_omnidexer", side_effect=AssertionError("loaded")
    ):
        latex = services.tag_resolver.process_text("{@spell fireball}")
    assert latex == r"\textit{fireball}"

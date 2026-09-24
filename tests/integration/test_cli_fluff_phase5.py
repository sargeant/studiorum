"""The --fluff options of the creature, spell and item compendiums."""

from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from studiorum.cli.main import app

REPO_ROOT = Path(__file__).resolve().parents[2]

CASES = {
    "creature": ["creatures", "Goblin"],
    "spell": ["spells", "Fireball"],
    "item": ["items", "Longsword"],
}


class TestCLIFluffPhase5Integration:
    """The fluff options reach the fluff matcher."""

    @pytest.mark.parametrize("kind", sorted(CASES))
    def test_fluff_filters_reach_the_matcher(
        self, kind: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(REPO_ROOT)
        with patch("studiorum.core.services.fluff_matcher.FluffMatcher") as matcher:
            match = getattr(matcher.return_value, f"match_{kind}_fluff")
            match.return_value = None
            result = CliRunner().invoke(
                app,
                [
                    "convert",
                    *CASES[kind],
                    "--sources",
                    "SRD",
                    "--fluff",
                    "--fluff-sections",
                    "lair,regional",
                    "--fluff-sources",
                    "mm",
                    "--output",
                    str(tmp_path / "out.tex"),
                ],
            )

        assert result.exit_code == 0, result.output
        assert f"No fluff content found for any {kind}s" in result.output
        assert match.call_args.kwargs == {
            "allowed_sections": ["lair", "regional"],
            "allowed_sources": ["MM"],
        }

    def test_fluff_configuration_integration(self):
        """Test that fluff configuration is properly integrated."""
        from studiorum.core.config.unified_config import (
            ApplicationConfig,
            FluffRenderingConfig,
        )

        # Test default configuration
        config = ApplicationConfig()
        fluff_config = config.rendering.content.fluff

        assert isinstance(fluff_config, FluffRenderingConfig)
        assert fluff_config.enabled is False  # Default
        assert fluff_config.placement == "before"
        assert fluff_config.deduplication is True
        assert fluff_config.sections == []
        assert fluff_config.allowed_sources == []

    def test_fluff_configuration_custom_values(self):
        """Test custom fluff configuration values."""
        from studiorum.core.config.unified_config import (
            ApplicationConfig,
            ContentConfig,
            FluffRenderingConfig,
            RenderingConfig,
        )

        # Create custom fluff config
        custom_fluff_config = FluffRenderingConfig(
            enabled=True,
            placement="after",
            sections=["lair", "tactics"],
            allowed_sources=["MM", "VGM"],
        )

        content_config = ContentConfig(fluff=custom_fluff_config)
        rendering_config = RenderingConfig(content=content_config)
        config = ApplicationConfig(rendering=rendering_config)

        fluff_config = config.rendering.content.fluff
        assert fluff_config.enabled is True
        assert fluff_config.placement == "after"
        assert fluff_config.sections == ["lair", "tactics"]
        assert fluff_config.allowed_sources == ["MM", "VGM"]

    @pytest.mark.parametrize("command", ["creatures", "spells", "items"])
    def test_fluff_options_are_listed_in_help(self, command: str) -> None:
        result = CliRunner().invoke(app, ["convert", command, "--help"])

        assert result.exit_code == 0
        for option in (
            "--fluff",
            "--fluff-sections",
            "--fluff-sources",
            "--with-fluff-images",
        ):
            assert option in result.output


@pytest.mark.parametrize("kind", sorted(CASES))
def test_fluff_images_render_as_converted_pngs(
    kind: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from PIL import Image

    from studiorum.core.models.fluff import BaseFluff

    img = tmp_path / "5etools-img"
    (img / "fluff").mkdir(parents=True)
    Image.new("RGB", (4, 8)).save(img / "fluff" / "Art.webp", "WEBP")
    monkeypatch.setenv("STUDIORUM_IMAGE__IMAGE_DIRECTORY", str(img))
    monkeypatch.chdir(REPO_ROOT)
    name = CASES[kind][1]
    fluff = BaseFluff.model_validate(
        {
            "name": name,
            "source": "SRD",
            "entries": ["Some lore."],
            "images": [
                {
                    "type": "image",
                    "href": {"type": "internal", "path": "fluff/Art.webp"},
                }
            ],
        }
    )
    output = tmp_path / "out.tex"
    with patch("studiorum.core.services.fluff_matcher.FluffMatcher") as matcher:
        getattr(matcher.return_value, f"match_{kind}_fluff").return_value = fluff
        result = CliRunner().invoke(
            app,
            [
                "convert",
                *CASES[kind],
                "--sources",
                "SRD",
                "--fluff",
                "--with-fluff-images",
                "--images",
                "--output",
                str(output),
            ],
        )

    assert result.exit_code == 0, result.output
    lines = [line for line in output.read_text().splitlines() if "/Art-" in line]
    assert len(lines) == 1
    assert lines[0].startswith("\\StudiorumImageInline*{")
    assert lines[0].endswith(".png}{}")

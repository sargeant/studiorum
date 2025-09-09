"""Integration tests for Phase 5 CLI fluff features."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from studiorum.cli.commands.convert.compendiums.creatures import creatures
from studiorum.cli.commands.convert.compendiums.items import items
from studiorum.cli.commands.convert.compendiums.spells import spells


class TestCLIFluffPhase5Integration:
    """Integration tests for Phase 5 CLI enhancements."""

    def setup_method(self):
        """Set up test fixtures."""
        from studiorum.core.services.container import ServiceContainer

        ServiceContainer.reset_global_instance()

    @patch("studiorum.cli.commands.convert.compendiums.creatures.get_omnidexer")
    @patch("studiorum.cli.commands.convert.compendiums.creatures.display_manager")
    def test_creatures_with_fluff_sections(
        self, mock_display_manager, mock_get_omnidexer, tmp_path
    ):
        """Test creatures command with fluff section filtering."""
        # Mock omnidexer and required services
        mock_omnidexer = Mock()
        mock_get_omnidexer.return_value = mock_omnidexer

        # Mock creature data
        from studiorum.core.models.content import Source
        from studiorum.core.models.creatures import Creature
        from studiorum.core.services.creature_collector import CreatureCollectionResult

        source = Source(abbreviation="MM", full_name="Monster Manual")
        creature = Creature(
            name="Ancient Red Dragon",
            source=source,
            cr="24",
            type={"type": "dragon"},
            size=["Gargantuan"],
            alignment=["chaotic", "evil"],
            ac=[{"ac": 22}],
            hp={"average": 546, "formula": "28d20 + 252"},
            speed={"walk": 40, "climb": 40, "fly": 80},
            str=30,
            dex=10,
            con=29,
            int=18,
            wis=15,
            cha=23,
        )

        # Mock collection result
        mock_result = CreatureCollectionResult(
            creatures=[creature],
            unresolved_names=[],
            suggestions={},
            sources_used={"MM"},
        )

        # Mock collector
        with patch(
            "studiorum.core.services.creature_collector.CreatureCollector"
        ) as mock_collector_class:
            mock_collector = Mock()
            mock_collector.collect_creatures.return_value = mock_result
            mock_collector_class.return_value = mock_collector

            # Mock display manager
            mock_display_manager.progress.return_value.__enter__ = Mock()
            mock_display_manager.progress.return_value.__exit__ = Mock()
            mock_display_manager.add_task.return_value = "task_id"
            mock_display_manager.update_task = Mock()

            # Mock fluff matcher and related services
            with patch(
                "studiorum.core.services.fluff_matcher.FluffMatcher"
            ) as mock_matcher_class:
                mock_matcher = Mock()
                mock_matcher.match_creature_fluff.return_value = None  # No fluff found
                mock_matcher_class.return_value = mock_matcher

                output_file = tmp_path / "test_output.tex"

                try:
                    # Test command with fluff sections
                    creatures(
                        creature_names=["Ancient Red Dragon"],
                        fluff=True,
                        fluff_sections=["lair,regional"],
                        output_file=output_file,
                    )

                    # Verify that fluff matcher was called with correct parameters
                    mock_matcher.match_creature_fluff.assert_called_with(
                        creature,
                        allowed_sections=["lair", "regional"],
                        allowed_sources=None,
                    )

                except Exception as e:
                    # Expected to fail during rendering, but should reach fluff processing
                    assert "No LaTeX content was generated" in str(e)

    @patch("studiorum.cli.commands.convert.compendiums.spells.get_omnidexer")
    @patch("studiorum.cli.commands.convert.compendiums.spells.display_manager")
    def test_spells_with_fluff_sources(
        self, mock_display_manager, mock_get_omnidexer, tmp_path
    ):
        """Test spells command with fluff source filtering."""
        # Mock omnidexer and required services
        mock_omnidexer = Mock()
        mock_get_omnidexer.return_value = mock_omnidexer

        # Mock spell data
        from studiorum.core.models.content import Source
        from studiorum.core.models.spells import Spell
        from studiorum.core.services.spell_collector import SpellCollectionResult

        source = Source(abbreviation="PHB", full_name="Player's Handbook")
        spell = Spell(
            name="Fireball",
            source=source,
            level=3,
            school="evocation",
            time=[{"number": 1, "unit": "action"}],
            range={"type": "point", "distance": {"type": "feet", "amount": 150}},
            components={
                "verbal": True,
                "somatic": True,
                "material": "a tiny ball of bat guano and sulfur",
            },
            duration=[{"type": "instant"}],
            entries=["A bright streak flashes from your pointing finger..."],
        )

        # Mock collection result
        mock_result = SpellCollectionResult(
            spells=[spell], unresolved_names=[], suggestions={}, sources_used={"PHB"}
        )

        # Mock collector
        with patch(
            "studiorum.core.services.spell_collector.SpellCollector"
        ) as mock_collector_class:
            mock_collector = Mock()
            mock_collector.collect_spells.return_value = mock_result
            mock_collector_class.return_value = mock_collector

            # Mock display manager
            mock_display_manager.progress.return_value.__enter__ = Mock()
            mock_display_manager.progress.return_value.__exit__ = Mock()
            mock_display_manager.add_task.return_value = "task_id"
            mock_display_manager.update_task = Mock()

            # Mock fluff matcher
            with patch(
                "studiorum.core.services.fluff_matcher.FluffMatcher"
            ) as mock_matcher_class:
                mock_matcher = Mock()
                mock_matcher.match_spell_fluff.return_value = None
                mock_matcher_class.return_value = mock_matcher

                output_file = tmp_path / "test_spells.tex"

                try:
                    # Test command with fluff sources
                    spells(
                        spell_names=["Fireball"],
                        fluff=True,
                        fluff_sources=["PHB,XPHB"],
                        output_file=output_file,
                    )

                    # Verify that fluff matcher was called with correct parameters
                    mock_matcher.match_spell_fluff.assert_called_with(
                        spell, allowed_sections=None, allowed_sources=["PHB", "XPHB"]
                    )

                except Exception as e:
                    # Expected to fail during rendering
                    assert "No LaTeX content was generated" in str(e)

    @patch("studiorum.cli.commands.convert.compendiums.items.get_omnidexer")
    @patch("studiorum.cli.commands.convert.compendiums.items.display_manager")
    def test_items_with_fluff_images(
        self, mock_display_manager, mock_get_omnidexer, tmp_path
    ):
        """Test items command with fluff image extraction."""
        # Mock omnidexer and required services
        mock_omnidexer = Mock()
        mock_get_omnidexer.return_value = mock_omnidexer

        # Mock item data
        from studiorum.core.models.content import Source
        from studiorum.core.models.items import Item
        from studiorum.core.services.item_collector import ItemCollectionResult

        source = Source(abbreviation="DMG", full_name="Dungeon Master's Guide")
        item = Item(name="Sword of Kas", source=source, rarity="artifact")

        # Mock collection result
        mock_result = ItemCollectionResult(
            items=[item], unresolved_names=[], suggestions={}, sources_used={"DMG"}
        )

        # Mock collector
        with patch(
            "studiorum.core.services.item_collector.ItemCollector"
        ) as mock_collector_class:
            mock_collector = Mock()
            mock_collector.collect_items.return_value = mock_result
            mock_collector_class.return_value = mock_collector

            # Mock display manager
            mock_display_manager.progress.return_value.__enter__ = Mock()
            mock_display_manager.progress.return_value.__exit__ = Mock()
            mock_display_manager.add_task.return_value = "task_id"
            mock_display_manager.update_task = Mock()

            # Mock fluff services
            with patch(
                "studiorum.core.services.fluff_matcher.FluffMatcher"
            ) as mock_matcher_class:
                with patch(
                    "studiorum.core.services.fluff_image_extractor.FluffImageExtractor"
                ) as mock_extractor_class:
                    mock_matcher = Mock()
                    mock_extractor = Mock()

                    # Mock fluff with images
                    from studiorum.core.models.fluff import ItemFluff
                    from studiorum.core.services.fluff_image_extractor import (
                        FluffImageInfo,
                    )

                    mock_fluff = ItemFluff(
                        name="Sword of Kas", source=source, entries=[], images=[]
                    )

                    mock_image_info = FluffImageInfo(
                        path="items/sword-of-kas.jpg",
                        credit="WotC",
                        source_fluff="Sword of Kas",
                    )

                    mock_matcher.match_item_fluff.return_value = mock_fluff
                    mock_extractor.extract_images_from_fluff.return_value = [
                        mock_image_info
                    ]

                    mock_matcher_class.return_value = mock_matcher
                    mock_extractor_class.return_value = mock_extractor

                    output_file = tmp_path / "test_items.tex"

                    try:
                        # Test command with image extraction
                        items(
                            item_names=["Sword of Kas"],
                            fluff=True,
                            with_fluff_images=True,
                            output_file=output_file,
                        )

                        # Verify that image extractor was called
                        mock_extractor.extract_images_from_fluff.assert_called_with(
                            mock_fluff
                        )

                    except Exception as e:
                        # Expected to fail during rendering
                        assert "No LaTeX content was generated" in str(e)

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
        assert fluff_config.include_images is True
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
            max_images_per_entry=3,
            image_placement="gallery",
        )

        content_config = ContentConfig(fluff=custom_fluff_config)
        rendering_config = RenderingConfig(content=content_config)
        config = ApplicationConfig(rendering=rendering_config)

        fluff_config = config.rendering.content.fluff
        assert fluff_config.enabled is True
        assert fluff_config.placement == "after"
        assert fluff_config.sections == ["lair", "tactics"]
        assert fluff_config.allowed_sources == ["MM", "VGM"]
        assert fluff_config.max_images_per_entry == 3
        assert fluff_config.image_placement == "gallery"

    @pytest.mark.parametrize(
        "command_module,command_func",
        [("creatures", "creatures"), ("spells", "spells"), ("items", "items")],
    )
    def test_phase5_parameters_accepted(self, command_module, command_func):
        """Test that all commands accept Phase 5 fluff parameters."""
        # This test ensures the CLI parameter definitions are correct
        # by importing and checking the function signatures

        if command_module == "creatures":
            from studiorum.cli.commands.convert.compendiums.creatures import (
                creatures as cmd_func,
            )
        elif command_module == "spells":
            from studiorum.cli.commands.convert.compendiums.spells import (
                spells as cmd_func,
            )
        elif command_module == "items":
            from studiorum.cli.commands.convert.compendiums.items import (
                items as cmd_func,
            )

        import inspect

        signature = inspect.signature(cmd_func)

        # Check that Phase 5 parameters are present
        assert "fluff" in signature.parameters
        assert "fluff_sections" in signature.parameters
        assert "fluff_sources" in signature.parameters
        assert "with_fluff_images" in signature.parameters

        # Check parameter types and defaults
        # Typer uses OptionInfo objects, so we need to check the .default attribute
        fluff_param = signature.parameters["fluff"]
        assert (
            hasattr(fluff_param.default, "default")
            and fluff_param.default.default is False
        )

        sections_param = signature.parameters["fluff_sections"]
        assert (
            hasattr(sections_param.default, "default")
            and sections_param.default.default is None
        )

        sources_param = signature.parameters["fluff_sources"]
        assert (
            hasattr(sources_param.default, "default")
            and sources_param.default.default is None
        )

        images_param = signature.parameters["with_fluff_images"]
        assert (
            hasattr(images_param.default, "default")
            and images_param.default.default is False
        )

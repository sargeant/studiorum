"""Integration tests for Phase 2 intelligent image placement system.

This module tests the complete integration of all Phase 2 components working
together in realistic scenarios.
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from studiorum.latex_engine.core.images import (
    ContentType,
    EnhancedPlacementConfig,
    OptimizationTarget,
    analyze_and_place_image,
    create_content_context_from_hint,
    create_enhanced_placer,
    create_layout_analyzer,
    create_output_optimizer,
    create_specialized_strategy,
)
from studiorum.latex_engine.core.images.image_placer import ImagePlacement


class TestFactoryFunctions:
    """Test factory functions for creating components."""

    def test_create_enhanced_placer_default(self):
        """Test creating enhanced placer with defaults."""
        placer = create_enhanced_placer()

        assert placer.enhanced_config.enable_intelligent_placement is True
        assert placer.enhanced_config.enable_content_analysis is True
        assert placer.enhanced_config.optimization_target == OptimizationTarget.HYBRID

    def test_create_enhanced_placer_custom_config(self):
        """Test creating enhanced placer with custom config."""
        config = EnhancedPlacementConfig(
            enable_output_optimization=True,
            optimization_target=OptimizationTarget.PRINT,
        )

        placer = create_enhanced_placer(config)

        assert placer.enhanced_config.enable_output_optimization is True
        assert placer.enhanced_config.optimization_target == OptimizationTarget.PRINT

    def test_create_enhanced_placer_minimal_features(self):
        """Test creating enhanced placer with minimal features."""
        placer = create_enhanced_placer(enable_all_features=False)

        assert placer.enhanced_config.enable_intelligent_placement is False
        assert placer.enhanced_config.enable_content_analysis is False

    def test_create_layout_analyzer_default(self):
        """Test creating layout analyzer with defaults."""
        analyzer = create_layout_analyzer()

        assert analyzer.constraints.max_images_per_page == 4
        assert analyzer.constraints.min_text_block_size == 200

    def test_create_output_optimizer_default(self):
        """Test creating output optimizer with defaults."""
        optimizer = create_output_optimizer()

        assert optimizer.cache_dir.name == "image_optimization_cache"
        assert len(optimizer.profiles) > 0

    def test_create_output_optimizer_custom_cache(self):
        """Test creating output optimizer with custom cache."""
        optimizer = create_output_optimizer("/tmp/custom_cache")

        assert str(optimizer.cache_dir) == "/tmp/custom_cache"

    def test_create_specialized_strategy_bestiary(self):
        """Test creating bestiary strategy."""
        strategy = create_specialized_strategy(ContentType.BESTIARY)

        from studiorum.latex_engine.core.images.specialized_strategies import (
            BestiaryPlacementStrategy,
        )

        assert isinstance(strategy, BestiaryPlacementStrategy)

    def test_create_content_context_from_hint_creature(self):
        """Test creating context from creature hint."""
        context = create_content_context_from_hint("creature")

        assert context["type"] == "creature"
        assert context["word_count"] == 300  # Creature-specific default
        assert "statblock" in context["structural_elements"]

    def test_create_content_context_from_hint_with_additional(self):
        """Test creating context with additional information."""
        additional = {
            "section_title": "Ancient Dragons",
            "has_other_images": True,
        }

        context = create_content_context_from_hint("creature", additional)

        assert context["type"] == "creature"
        assert context["section_title"] == "Ancient Dragons"
        assert context["has_other_images"] is True


class TestCompleteWorkflows:
    """Test complete workflows using integrated components."""

    def setup_method(self):
        """Set up test fixtures."""
        self.test_image_path = "/tmp/test_dragon.png"
        self.test_image_entry = {
            "title": "Ancient Red Dragon",
            "alt": "A fearsome ancient red dragon breathing fire",
            "source": "Monster Manual",
        }

    @pytest.mark.asyncio
    async def test_analyze_and_place_image_bestiary(self):
        """Test complete analysis and placement for bestiary content."""
        with (
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "stat") as mock_stat,
        ):
            mock_stat.return_value.st_size = 2 * 1024 * 1024  # 2MB

            result = await analyze_and_place_image(
                self.test_image_path,
                self.test_image_entry,
                ContentType.BESTIARY,
                content_context={"section_title": "Ancient Dragons"},
                optimization_target=OptimizationTarget.PRINT,
            )

            assert result.confidence > 0.0
            assert len(result.reasoning) > 0
            assert result.processing_metadata["content_type"] == "bestiary"
            assert "BestiaryPlacementStrategy" in result.processing_metadata.get(
                "specialized_strategy", ""
            )

    @pytest.mark.asyncio
    async def test_analyze_and_place_image_adventure(self):
        """Test complete analysis for adventure content."""
        map_entry = {
            "title": "Dungeon Level 1",
            "alt": "Map of the first dungeon level",
            "tags": ["map", "location"],
        }

        with (
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "stat") as mock_stat,
        ):
            mock_stat.return_value.st_size = 5 * 1024 * 1024  # 5MB map

            result = await analyze_and_place_image(
                "/tmp/dungeon_map.png",
                map_entry,
                ContentType.ADVENTURE,
                content_context={
                    "section_title": "The Lost Temple",
                    "reading_flow_position": "start",
                },
            )

            assert result.processing_metadata["content_type"] == "adventure"
            # Maps often get full-width placement
            assert result.placement in {
                ImagePlacement.FULL_WIDTH,
                ImagePlacement.FLOAT_TOP,
                ImagePlacement.FLOAT_HERE,
            }

    @pytest.mark.asyncio
    async def test_analyze_and_place_image_items(self):
        """Test complete analysis for item collection."""
        sword_entry = {
            "title": "Flametongue Longsword",
            "alt": "A magical longsword with flames along the blade",
            "rarity": "rare",
        }

        with (
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "stat") as mock_stat,
        ):
            mock_stat.return_value.st_size = 500 * 1024  # 500KB

            result = await analyze_and_place_image(
                "/tmp/flametongue.png",
                sword_entry,
                ContentType.ITEM_COLLECTION,
                content_context={
                    "nearby_images": ["mace.png", "bow.png"],  # Other items
                    "structural_elements": ["table"],
                },
            )

            assert result.processing_metadata["content_type"] == "item_collection"
            # Items in collections often use consistent placement
            assert result.placement in {
                ImagePlacement.INLINE,
                ImagePlacement.FLOAT_TOP,
                ImagePlacement.WRAP_RIGHT,
            }

    @pytest.mark.asyncio
    async def test_workflow_error_handling(self):
        """Test error handling in complete workflow."""
        # Test with non-existent image
        with pytest.raises(ValueError, match="Placement analysis failed"):
            await analyze_and_place_image(
                "/nonexistent/image.png",
                self.test_image_entry,
                ContentType.BESTIARY,
            )

    def test_backward_compatibility_workflow(self):
        """Test that enhanced features work with legacy interfaces."""
        placer = create_enhanced_placer()

        with (
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "stat") as mock_stat,
        ):
            mock_stat.return_value.st_size = 1024

            # Should work with old-style API
            result = placer.place_image(
                Path(self.test_image_path),
                self.test_image_entry,
                "creature",  # Old-style context hint
            )

            # Should get standard PlacementResult
            from studiorum.latex_engine.core.images import PlacementResult

            assert isinstance(result, PlacementResult)
            assert result.latex_command is not None


class TestComponentIntegration:
    """Test integration between different Phase 2 components."""

    def test_strategy_with_layout_analyzer(self):
        """Test strategy working with layout analyzer."""
        from studiorum.latex_engine.core.images.placement_models import (
            ContentContext,
            ContentType,
            PageContext,
        )

        create_specialized_strategy(ContentType.BESTIARY)
        analyzer = create_layout_analyzer()

        # Create test page context
        page_context = PageContext(
            available_width=500.0,
            available_height=700.0,
            column_width=450.0,
            margin_width=50.0,
            current_fill=0.6,
            remaining_space=280.0,
        )

        # Analyze page space
        space_analysis = analyzer.analyze_page_space(page_context)

        assert space_analysis.remaining_space > 0
        assert len(space_analysis.optimal_image_sizes) > 0

        # Check that recommended sizes make sense for available space
        for size, fit_score in space_analysis.optimal_image_sizes:
            assert 0.0 <= fit_score <= 1.0

    def test_output_optimizer_with_profiles(self):
        """Test output optimizer profile integration."""
        optimizer = create_output_optimizer()

        profiles = optimizer.get_optimization_profiles()
        assert len(profiles) > 0

        # Test specific profiles exist
        profile_names = [p.name for p in profiles]
        expected_profiles = [
            "web_optimized",
            "print_production",
            "balanced_hybrid",
            "accessibility",
        ]

        for expected in expected_profiles:
            assert expected in profile_names

    def test_enhanced_placer_component_integration(self):
        """Test that enhanced placer properly integrates all components."""
        config = EnhancedPlacementConfig(
            enable_intelligent_placement=True,
            enable_content_analysis=True,
            enable_layout_optimization=True,
            enable_output_optimization=True,
        )

        placer = create_enhanced_placer(config)

        # All components should be initialized
        assert placer.content_aware_strategy is not None
        assert placer.layout_analyzer is not None
        assert placer.output_optimizer is not None

        # Statistics should reflect enabled features
        stats = placer.get_placement_statistics()
        assert stats["intelligent_placement_enabled"] is True
        assert stats["content_analysis_enabled"] is True
        assert stats["layout_optimization_enabled"] is True
        assert stats["output_optimization_enabled"] is True


class TestRealWorldScenarios:
    """Test scenarios that mirror real-world usage patterns."""

    @pytest.mark.asyncio
    async def test_monster_manual_layout(self):
        """Test layout scenario resembling Monster Manual content."""
        # Create enhanced placer for bestiary content
        placer = create_enhanced_placer()

        # Simulate multiple creature images
        creatures = [
            ("ancient_dragon.png", {"title": "Ancient Red Dragon", "cr": "24"}),
            ("young_dragon.png", {"title": "Young Red Dragon", "cr": "10"}),
            ("wyrmling.png", {"title": "Red Dragon Wyrmling", "cr": "4"}),
        ]

        with (
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "stat") as mock_stat,
        ):
            mock_stat.return_value.st_size = 800 * 1024  # 800KB each

            results = []
            for image_name, entry in creatures:
                context = create_content_context_from_hint(
                    "creature",
                    {
                        "section_title": "Red Dragons",
                        "has_other_images": len(results) > 0,
                    },
                )

                result = await placer.place_image_enhanced(
                    Path(f"/tmp/{image_name}"),
                    entry,
                    context,
                )

                assert result.is_success()
                results.append(result.value)

            # All should be bestiary-optimized
            for result in results:
                assert result.processing_metadata["content_type"] == "bestiary"
                # Creatures should prefer wrapped placement
                assert result.placement in {
                    ImagePlacement.WRAP_LEFT,
                    ImagePlacement.WRAP_RIGHT,
                    ImagePlacement.FLOAT_HERE,
                }

    @pytest.mark.asyncio
    async def test_adventure_module_layout(self):
        """Test layout scenario resembling adventure module content."""
        placer = create_enhanced_placer()

        # Mix of adventure content types
        adventure_images = [
            ("region_map.png", {"title": "Regional Map", "type": "map"}),
            ("sage_npc.png", {"title": "Elara the Sage", "type": "npc"}),
            ("temple_exterior.png", {"title": "Temple Entrance", "type": "scene"}),
            ("dungeon_level1.png", {"title": "Level 1", "type": "map"}),
        ]

        with (
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "stat") as mock_stat,
        ):
            mock_stat.return_value.st_size = 1.5 * 1024 * 1024  # 1.5MB each

            for i, (image_name, entry) in enumerate(adventure_images):
                context = create_content_context_from_hint(
                    "adventure",
                    {
                        "section_title": f"Chapter {i + 1}",
                        "reading_flow_position": "start" if i % 2 == 0 else "middle",
                    },
                )

                result = await placer.place_image_enhanced(
                    Path(f"/tmp/{image_name}"),
                    entry,
                    context,
                )

                assert result.is_success()

                # Unwrap the result to access placement data
                placement_result = result.unwrap()

                # Maps should often be full-width or prominent
                if "map" in entry.get("type", ""):
                    assert placement_result.placement in {
                        ImagePlacement.FULL_WIDTH,
                        ImagePlacement.FLOAT_TOP,
                        ImagePlacement.FLOAT_HERE,
                    }

    def test_performance_with_caching(self):
        """Test performance benefits of caching."""
        config = EnhancedPlacementConfig(cache_placement_decisions=True)
        placer = create_enhanced_placer(config)

        # Verify cache is initially empty
        stats = placer.get_placement_statistics()
        assert stats["cache_size"] == 0

        # Clear cache should work without errors
        placer.clear_placement_cache()

    def test_accessibility_optimization_scenario(self):
        """Test accessibility-focused optimization."""
        optimizer = create_output_optimizer()

        # Get accessibility profile
        profiles = optimizer.get_optimization_profiles()
        accessibility_profile = next(p for p in profiles if p.name == "accessibility")

        assert accessibility_profile.target == OptimizationTarget.ACCESSIBILITY
        assert accessibility_profile.config.preserve_transparency is True
        assert "accessibility" in " ".join(accessibility_profile.use_cases).lower()

    def test_bandwidth_constrained_scenario(self):
        """Test bandwidth-optimized scenario."""
        optimizer = create_output_optimizer()

        # Get bandwidth profile
        profiles = optimizer.get_optimization_profiles()
        bandwidth_profile = next(p for p in profiles if p.name == "bandwidth_optimized")

        assert bandwidth_profile.target == OptimizationTarget.BANDWIDTH
        assert bandwidth_profile.config.max_file_size_mb <= 1.0
        assert bandwidth_profile.config.quality_priority < 0.5


class TestErrorRecoveryAndFallbacks:
    """Test error recovery and fallback mechanisms."""

    def test_graceful_degradation_component_failures(self):
        """Test graceful degradation when components fail."""
        # Test with failed component initialization
        with patch(
            "studiorum.latex_engine.core.images.enhanced_image_placer.ContentAwarePlacementStrategy",
            side_effect=Exception("Component failed"),
        ):
            # Should still create placer but with features disabled
            placer = create_enhanced_placer()

            stats = placer.get_placement_statistics()
            assert stats["intelligent_placement_enabled"] is False

    @pytest.mark.asyncio
    async def test_fallback_chain_integration(self):
        """Test complete fallback chain when enhanced features fail."""
        placer = create_enhanced_placer()

        # Mock all enhanced features to fail
        with (
            patch.object(placer, "content_aware_strategy", None),
            patch.object(placer, "layout_analyzer", None),
            patch.object(placer, "output_optimizer", None),
        ):
            with (
                patch.object(Path, "exists", return_value=True),
                patch.object(Path, "stat") as mock_stat,
            ):
                mock_stat.return_value.st_size = 1024

                # Should still work via fallback to base placement
                result = placer.place_image(
                    Path("/tmp/test.png"),
                    {"title": "Test Image"},
                    "creature",
                )

                from studiorum.latex_engine.core.images import PlacementResult

                assert isinstance(result, PlacementResult)
                assert result.latex_command is not None

    def test_memory_and_resource_cleanup(self):
        """Test that components properly clean up resources."""
        placer = create_enhanced_placer()
        analyzer = create_layout_analyzer()
        optimizer = create_output_optimizer()

        # Add some data to caches
        placer._placement_cache["test"] = "data"
        analyzer._page_cache["test"] = "data"

        # Clear caches
        placer.clear_placement_cache()
        assert len(placer._placement_cache) == 0

        # Get cache stats should work
        cache_stats = optimizer.get_cache_statistics()
        assert "cache_directory" in cache_stats
        assert "total_files" in cache_stats

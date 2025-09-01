"""Tests for EnhancedImagePlacer.

This module tests the enhanced image placer that integrates all Phase 2
intelligent placement capabilities while maintaining backward compatibility.
"""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from studiorum.latex_engine.core.images.enhanced_image_placer import (
    EnhancedImagePlacer,
    EnhancedPlacementConfig,
    EnhancedPlacementResult,
)
from studiorum.latex_engine.core.images.image_placer import (
    ImagePlacement,
    PlacementResult,
)
from studiorum.latex_engine.core.images.placement_models import (
    ContentType,
    OptimizationTarget,
)


class TestEnhancedPlacementConfig:
    """Test EnhancedPlacementConfig model."""

    def test_create_enhanced_config(self):
        """Test creating enhanced placement configuration."""
        config = EnhancedPlacementConfig(
            enable_intelligent_placement=True,
            enable_content_analysis=True,
            enable_layout_optimization=True,
            enable_output_optimization=True,
            optimization_target=OptimizationTarget.PRINT,
            use_specialized_strategies=True,
        )

        assert config.enable_intelligent_placement is True
        assert config.enable_content_analysis is True
        assert config.optimization_target == OptimizationTarget.PRINT
        assert config.use_specialized_strategies is True

    def test_enhanced_config_defaults(self):
        """Test enhanced configuration defaults."""
        config = EnhancedPlacementConfig()

        assert config.enable_intelligent_placement is True
        assert config.enable_content_analysis is True
        assert config.optimization_target == OptimizationTarget.HYBRID
        assert config.cache_placement_decisions is True

    def test_enhanced_config_inherits_base(self):
        """Test that enhanced config inherits base config fields."""
        config = EnhancedPlacementConfig(
            enable_text_wrapping=False,
            enable_margin_images=True,
            default_placement=ImagePlacement.FLOAT_TOP,
        )

        # Should have both base and enhanced fields
        assert config.enable_text_wrapping is False
        assert config.enable_margin_images is True
        assert config.default_placement == ImagePlacement.FLOAT_TOP
        assert config.enable_intelligent_placement is True  # Enhanced field


class TestEnhancedPlacementResult:
    """Test EnhancedPlacementResult model."""

    def test_create_enhanced_result(self):
        """Test creating enhanced placement result."""
        result = EnhancedPlacementResult(
            latex_command="\\includegraphics[width=0.5\\textwidth]{test.png}",
            placement=ImagePlacement.WRAP_RIGHT,
            size_spec="0.5\\textwidth",
            requires_packages=["graphicx", "wrapfig"],
            caption="Test Image",
            confidence=0.85,
            reasoning=["Good aspect ratio", "Matches content type"],
            alternative_placements=["wrap-left (0.7)", "float-here (0.6)"],
            optimization_applied=True,
        )

        assert result.confidence == 0.85
        assert len(result.reasoning) == 2
        assert len(result.alternative_placements) == 2
        assert result.optimization_applied is True

    def test_enhanced_result_inherits_base(self):
        """Test that enhanced result inherits base result fields."""
        result = EnhancedPlacementResult(
            latex_command="\\includegraphics{test.png}",
            placement=ImagePlacement.INLINE,
            size_spec="0.3\\textwidth",
            requires_packages=["graphicx"],
        )

        # Should have base fields
        assert result.latex_command == "\\includegraphics{test.png}"
        assert result.placement == ImagePlacement.INLINE
        assert result.size_spec == "0.3\\textwidth"
        assert result.requires_packages == ["graphicx"]

        # Should have enhanced fields with defaults
        assert result.confidence == 0.5
        assert result.reasoning == []
        assert result.optimization_applied is False


class TestEnhancedImagePlacer:
    """Test EnhancedImagePlacer implementation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = EnhancedPlacementConfig(
            enable_intelligent_placement=True,
            enable_content_analysis=True,
            enable_layout_optimization=True,
            enable_output_optimization=False,  # Disabled for simpler testing
        )
        self.placer = EnhancedImagePlacer(self.config)

        # Create test image path and entry
        self.test_image_path = Path("/tmp/test_creature.png")
        self.test_image_entry = {
            "title": "Ancient Red Dragon",
            "alt": "A fearsome red dragon",
            "source": "MM",
        }

    def test_initialization_with_intelligent_features(self):
        """Test initialization with intelligent features enabled."""
        config = EnhancedPlacementConfig(enable_intelligent_placement=True)
        placer = EnhancedImagePlacer(config)

        assert placer.enhanced_config.enable_intelligent_placement is True
        assert placer.content_aware_strategy is not None
        assert placer.layout_analyzer is not None

    def test_initialization_without_intelligent_features(self):
        """Test initialization with intelligent features disabled."""
        config = EnhancedPlacementConfig(enable_intelligent_placement=False)
        placer = EnhancedImagePlacer(config)

        assert placer.enhanced_config.enable_intelligent_placement is False
        assert placer.content_aware_strategy is None

    def test_initialization_fallback_on_error(self):
        """Test initialization falls back gracefully on component errors."""
        config = EnhancedPlacementConfig(enable_intelligent_placement=True)

        # Mock component initialization to raise error
        with patch(
            "studiorum.latex_engine.core.images.enhanced_image_placer.ContentAwarePlacementStrategy",
            side_effect=Exception("Init failed"),
        ):
            placer = EnhancedImagePlacer(config)

            # Should fall back to disabled state
            assert placer.enhanced_config.enable_intelligent_placement is False

    @pytest.mark.asyncio
    async def test_place_image_enhanced_basic(self):
        """Test basic enhanced image placement."""
        # Mock file existence
        with (
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "stat") as mock_stat,
        ):
            mock_stat.return_value.st_size = 1024 * 1024  # 1MB

            result = await self.placer.place_image_enhanced(
                self.test_image_path,
                self.test_image_entry,
                {"type": "creature"},
            )

            assert result.is_success()
            enhanced_result = result.value

            assert isinstance(enhanced_result, EnhancedPlacementResult)
            assert 0.0 <= enhanced_result.confidence <= 1.0
            assert len(enhanced_result.reasoning) > 0
            assert len(enhanced_result.processing_metadata) > 0

    @pytest.mark.asyncio
    async def test_place_image_enhanced_with_contexts(self):
        """Test enhanced placement with full context information."""
        content_context = {
            "type": "creature",
            "section_title": "Dragons",
            "word_count": 400,
            "text_density": 0.7,
            "structural_elements": ["statblock"],
        }

        document_context = {
            "total_pages": 50,
            "current_page": 15,
            "chapter_number": 3,
            "target_format": "pdf",
        }

        page_context = {
            "available_width": 500.0,
            "available_height": 700.0,
            "current_fill": 0.3,
            "remaining_space": 490.0,
        }

        with (
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "stat") as mock_stat,
        ):
            mock_stat.return_value.st_size = 500 * 1024  # 500KB

            result = await self.placer.place_image_enhanced(
                self.test_image_path,
                self.test_image_entry,
                content_context,
                document_context,
                page_context,
            )

            assert result.is_success()
            enhanced_result = result.value

            # Should use specialized strategy for creature
            assert enhanced_result.processing_metadata["content_type"] == "bestiary"
            assert len(enhanced_result.layout_impact) > 0

    @pytest.mark.asyncio
    async def test_place_image_enhanced_fallback_on_error(self):
        """Test fallback to base placement when enhanced features fail."""
        # Mock strategy to fail
        with patch.object(self.placer, "_select_placement_strategy") as mock_strategy:
            mock_strategy.return_value.determine_placement = AsyncMock(
                side_effect=Exception("Strategy failed")
            )

            with (
                patch.object(Path, "exists", return_value=True),
                patch.object(Path, "stat") as mock_stat,
            ):
                mock_stat.return_value.st_size = 1024

                result = await self.placer.place_image_enhanced(
                    self.test_image_path,
                    self.test_image_entry,
                )

                # Should still succeed via fallback
                assert result.is_success()
                enhanced_result = result.value

                assert (
                    "fallback" in enhanced_result.processing_metadata["strategy_used"]
                )

    @pytest.mark.asyncio
    async def test_place_image_enhanced_disabled_features(self):
        """Test enhanced placement with intelligent features disabled."""
        disabled_config = EnhancedPlacementConfig(enable_intelligent_placement=False)
        disabled_placer = EnhancedImagePlacer(disabled_config)

        with (
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "stat") as mock_stat,
        ):
            mock_stat.return_value.st_size = 1024

            result = await disabled_placer.place_image_enhanced(
                self.test_image_path,
                self.test_image_entry,
            )

            assert result.is_success()
            enhanced_result = result.value

            # Should use base placement
            assert enhanced_result.confidence == 0.6  # Default for base method

    def test_place_image_backward_compatibility(self):
        """Test backward compatibility with original place_image method."""
        with (
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "stat") as mock_stat,
        ):
            mock_stat.return_value.st_size = 1024

            # Should work with original signature
            result = self.placer.place_image(
                self.test_image_path,
                self.test_image_entry,
                "creature",
            )

            assert isinstance(result, PlacementResult)
            assert result.latex_command is not None
            assert result.placement is not None

    def test_place_image_fallback_to_base(self):
        """Test place_image falls back to base implementation on errors."""
        # Mock enhanced placement to fail
        with patch.object(
            self.placer,
            "place_image_enhanced",
            side_effect=Exception("Enhanced failed"),
        ):
            result = self.placer.place_image(
                self.test_image_path,
                self.test_image_entry,
                "creature",
            )

            # Should still work via base implementation
            assert isinstance(result, PlacementResult)

    def test_place_image_disabled_intelligent_features(self):
        """Test place_image with intelligent features disabled."""
        disabled_config = EnhancedPlacementConfig(enable_intelligent_placement=False)
        disabled_placer = EnhancedImagePlacer(disabled_config)

        result = disabled_placer.place_image(
            self.test_image_path,
            self.test_image_entry,
            "creature",
        )

        # Should use base implementation directly
        assert isinstance(result, PlacementResult)

    def test_create_image_metadata(self):
        """Test image metadata creation from file and entry."""
        with (
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "stat") as mock_stat,
        ):
            mock_stat.return_value.st_size = 2048

            # Run the async method
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                metadata = loop.run_until_complete(
                    self.placer._create_image_metadata(
                        self.test_image_path,
                        self.test_image_entry,
                    )
                )
            finally:
                loop.close()

            assert metadata.path == str(self.test_image_path)
            assert metadata.local_path == self.test_image_path
            assert metadata.title == "Ancient Red Dragon"
            assert metadata.file_size_bytes == 2048
            assert "creature" in metadata.content_hints

    def test_create_content_context(self):
        """Test content context creation from data."""
        context_data = {
            "type": "creature",
            "section_title": "Ancient Dragons",
            "word_count": 350,
            "has_other_images": True,
        }

        context = self.placer._create_content_context(
            context_data, self.test_image_entry
        )

        assert context.content_type == ContentType.BESTIARY
        assert context.section_title == "Ancient Dragons"
        assert context.word_count == 350
        assert context.has_other_images is True

    def test_create_content_context_type_mapping(self):
        """Test content type mapping from hints."""
        test_cases = [
            ("adventure", ContentType.ADVENTURE),
            ("item", ContentType.ITEM_COLLECTION),
            ("spell", ContentType.SPELL_COLLECTION),
            ("unknown_type", ContentType.UNKNOWN),
        ]

        for hint, expected_type in test_cases:
            context = self.placer._create_content_context({"type": hint}, {})
            assert context.content_type == expected_type

    def test_create_document_context(self):
        """Test document context creation."""
        context_data = {
            "total_pages": 100,
            "current_page": 25,
            "chapter_number": 5,
            "target_format": "pdf",
        }

        context = self.placer._create_document_context(context_data)

        assert context.total_pages == 100
        assert context.current_page == 25
        assert context.chapter_number == 5
        assert context.target_format == "pdf"

    def test_create_document_context_defaults(self):
        """Test document context with defaults."""
        context = self.placer._create_document_context(None)

        assert context.total_pages == 50  # Default estimate
        assert context.current_page == 1

    def test_create_page_context(self):
        """Test page context creation."""
        context_data = {
            "available_width": 500.0,
            "available_height": 700.0,
            "current_fill": 0.4,
            "is_chapter_start": True,
        }

        context = self.placer._create_page_context(context_data)

        assert context.available_width == 500.0
        assert context.available_height == 700.0
        assert context.current_fill == 0.4
        assert context.is_chapter_start is True

    def test_create_user_preferences(self):
        """Test user preferences creation from config."""
        config = EnhancedPlacementConfig(
            enable_text_wrapping=False,
            enable_margin_images=True,
            optimization_target=OptimizationTarget.PRINT,
        )
        placer = EnhancedImagePlacer(config)

        prefs = placer._create_user_preferences()

        assert prefs.prefer_inline is True  # Inverse of text wrapping
        assert prefs.prefer_wrapped is False
        assert prefs.prefer_margins is True
        assert prefs.optimization_target == OptimizationTarget.PRINT

    def test_select_placement_strategy_specialized(self):
        """Test specialized strategy selection."""
        from studiorum.latex_engine.core.images.placement_models import ContentContext

        # Test bestiary strategy selection
        bestiary_context = ContentContext(content_type=ContentType.BESTIARY)
        strategy = self.placer._select_placement_strategy(bestiary_context)

        # Should be a specialized strategy (if enabled)
        from studiorum.latex_engine.core.images.specialized_strategies import (
            BestiaryPlacementStrategy,
        )

        if self.placer.enhanced_config.use_specialized_strategies:
            assert isinstance(strategy, BestiaryPlacementStrategy)

    def test_select_placement_strategy_fallback(self):
        """Test fallback to base strategy for unknown content."""
        from studiorum.latex_engine.core.images.placement_models import ContentContext

        unknown_context = ContentContext(content_type=ContentType.UNKNOWN)
        strategy = self.placer._select_placement_strategy(unknown_context)

        # Should be base content-aware strategy
        from studiorum.latex_engine.core.images.content_aware_strategy import (
            ContentAwarePlacementStrategy,
        )

        assert isinstance(strategy, ContentAwarePlacementStrategy)

    def test_get_placement_statistics(self):
        """Test placement statistics reporting."""
        stats = self.placer.get_placement_statistics()

        assert "intelligent_placement_enabled" in stats
        assert "content_analysis_enabled" in stats
        assert "optimization_target" in stats
        assert "cache_size" in stats

        assert isinstance(stats["intelligent_placement_enabled"], bool)
        assert isinstance(stats["cache_size"], int)

    def test_clear_placement_cache(self):
        """Test clearing placement cache."""
        # Add something to cache
        self.placer._placement_cache["test_key"] = "test_value"
        assert len(self.placer._placement_cache) > 0

        self.placer.clear_placement_cache()
        assert len(self.placer._placement_cache) == 0

    def test_base_config_compatibility(self):
        """Test that enhanced config is compatible with base ImagePlacer."""
        # Enhanced config should work with base placement methods
        config = EnhancedPlacementConfig(
            default_placement=ImagePlacement.WRAP_LEFT,
            enable_text_wrapping=True,
        )
        placer = EnhancedImagePlacer(config)

        # Base config should be properly initialized
        assert placer.config.default_placement == ImagePlacement.WRAP_LEFT
        assert placer.config.enable_text_wrapping is True

    @pytest.mark.asyncio
    async def test_layout_impact_analysis(self):
        """Test layout impact analysis integration."""
        from studiorum.latex_engine.core.images.placement_models import (
            PageContext,
            PlacementDecision,
        )

        page_context = PageContext(
            available_width=500.0,
            available_height=700.0,
            column_width=450.0,
            margin_width=50.0,
            current_fill=0.3,
            remaining_space=490.0,
        )

        decision = PlacementDecision(
            placement=ImagePlacement.WRAP_RIGHT,
            size="medium",
            confidence=0.8,
            factors=[],
            overall_score=0.7,
        )

        impact = await self.placer._analyze_layout_impact(decision, page_context)

        assert "space_utilization" in impact
        assert "readability_impact" in impact
        assert "aesthetic_contribution" in impact

        # Values should be in valid range
        for value in impact.values():
            assert 0.0 <= value <= 1.0

    @pytest.mark.asyncio
    async def test_output_optimization_integration(self):
        """Test output optimization integration."""
        # Enable output optimization
        config = EnhancedPlacementConfig(enable_output_optimization=True)
        placer = EnhancedImagePlacer(config)

        from studiorum.latex_engine.core.images.placement_models import ImageMetadata

        image_metadata = ImageMetadata(
            path="/test/image.png",
            file_size_bytes=1024,
        )

        decision = MagicMock()
        decision.confidence = 0.8

        # Mock optimizer - need to properly mock the chain for hybrid optimization
        with patch.object(placer, "output_optimizer") as mock_optimizer:
            # The _apply_output_optimization method uses create_hybrid_optimization by default
            mock_optimizer.create_hybrid_optimization.return_value.is_success.return_value = True

            optimized = await placer._apply_output_optimization(
                image_metadata, decision
            )

            assert optimized is True
            mock_optimizer.create_hybrid_optimization.assert_called_once()

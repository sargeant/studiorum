"""Tests for ContentAwarePlacementStrategy.

This module tests the core intelligent placement strategy with multi-factor
weighted decision making.
"""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from studiorum.latex_engine.core.images.content_aware_strategy import (
    ContentAwarePlacementStrategy,
    PlacementWeights,
    UserPreferences,
)
from studiorum.latex_engine.core.images.image_placer import ImagePlacement, ImageSize
from studiorum.latex_engine.core.images.placement_models import (
    ContentContext,
    ContentType,
    DocumentContext,
    ImageCharacteristic,
    ImageDimensions,
    ImageMetadata,
    OptimizationTarget,
    PageContext,
)


class TestPlacementWeights:
    """Test PlacementWeights model and normalization."""

    def test_create_placement_weights(self):
        """Test creating placement weights."""
        weights = PlacementWeights(
            image_characteristics=0.3,
            content_flow=0.2,
            page_position=0.1,
            surrounding_context=0.2,
            user_preferences=0.1,
            technical_constraints=0.1,
        )

        assert weights.image_characteristics == 0.3
        assert weights.content_flow == 0.2
        assert weights.page_position == 0.1

    def test_normalize_weights(self):
        """Test weight normalization."""
        weights = PlacementWeights(
            image_characteristics=0.6,
            content_flow=0.4,
            page_position=0.2,
            surrounding_context=0.4,
            user_preferences=0.2,
            technical_constraints=0.2,
        )

        normalized = weights.normalize()

        # Total should be approximately 1.0
        total = (
            normalized.image_characteristics
            + normalized.content_flow
            + normalized.page_position
            + normalized.surrounding_context
            + normalized.user_preferences
            + normalized.technical_constraints
        )

        assert total == pytest.approx(1.0, abs=0.001)

    def test_normalize_zero_weights(self):
        """Test normalization with all zero weights."""
        weights = PlacementWeights(
            image_characteristics=0.0,
            content_flow=0.0,
            page_position=0.0,
            surrounding_context=0.0,
            user_preferences=0.0,
            technical_constraints=0.0,
        )

        normalized = weights.normalize()

        # Should set equal weights when all are zero
        expected_weight = 1.0 / 6
        assert normalized.image_characteristics == pytest.approx(
            expected_weight, abs=0.001
        )
        assert normalized.content_flow == pytest.approx(expected_weight, abs=0.001)


class TestUserPreferences:
    """Test UserPreferences model."""

    def test_create_user_preferences(self):
        """Test creating user preferences."""
        prefs = UserPreferences(
            prefer_inline=True,
            prefer_wrapped=False,
            prefer_margins=True,
            optimization_target=OptimizationTarget.PRINT,
        )

        assert prefs.prefer_inline is True
        assert prefs.prefer_wrapped is False
        assert prefs.prefer_margins is True
        assert prefs.optimization_target == OptimizationTarget.PRINT

    def test_user_preferences_defaults(self):
        """Test user preferences defaults."""
        prefs = UserPreferences()

        assert prefs.prefer_inline is False
        assert prefs.prefer_wrapped is True
        assert prefs.optimization_target == OptimizationTarget.HYBRID
        assert prefs.max_image_width == 0.8
        assert prefs.min_image_width == 0.2

    def test_user_preferences_validation(self):
        """Test user preferences validation."""
        # Image width bounds should be valid
        with pytest.raises(ValueError):
            UserPreferences(max_image_width=1.5)  # Too high

        with pytest.raises(ValueError):
            UserPreferences(min_image_width=0.05)  # Too low


class TestContentAwarePlacementStrategy:
    """Test ContentAwarePlacementStrategy implementation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.strategy = ContentAwarePlacementStrategy()

        # Create test image metadata
        self.image_metadata = ImageMetadata(
            path="/test/creature.png",
            local_path=Path("/test/creature.png"),
            dimensions=ImageDimensions.from_dimensions(400, 600),
            characteristics=[ImageCharacteristic.PORTRAIT],
            content_hints=["creature"],
            quality_score=0.8,
        )

        # Create test content context
        self.content_context = ContentContext(
            content_type=ContentType.BESTIARY,
            section_title="Ancient Dragons",
            word_count=300,
            text_density=0.7,
        )

        # Create test document context
        self.document_context = DocumentContext(
            total_pages=50,
            current_page=10,
            chapter_number=2,
        )

    @pytest.mark.asyncio
    async def test_determine_placement_basic(self):
        """Test basic placement determination."""
        result = await self.strategy.determine_placement(
            self.image_metadata,
            self.content_context,
            self.document_context,
        )

        assert result.is_success()
        decision = result.value

        assert isinstance(decision.placement, ImagePlacement)
        assert isinstance(decision.size, ImageSize)
        assert 0.0 <= decision.confidence <= 1.0
        assert 0.0 <= decision.overall_score <= 1.0
        assert len(decision.factors) > 0

    @pytest.mark.asyncio
    async def test_determine_placement_with_page_context(self):
        """Test placement determination with page context."""
        page_context = PageContext(
            available_width=500.0,
            available_height=700.0,
            column_width=450.0,
            margin_width=50.0,
            current_fill=0.3,
            remaining_space=490.0,
        )

        result = await self.strategy.determine_placement(
            self.image_metadata,
            self.content_context,
            self.document_context,
            page_context,
        )

        assert result.is_success()
        decision = result.value

        # Should have page position factor
        factor_names = [f.name for f in decision.factors]
        assert "Page Position" in factor_names

    @pytest.mark.asyncio
    async def test_determine_placement_with_user_preferences(self):
        """Test placement determination with user preferences."""
        user_prefs = UserPreferences(
            prefer_inline=True,
            prefer_wrapped=False,
        )

        result = await self.strategy.determine_placement(
            self.image_metadata,
            self.content_context,
            self.document_context,
            user_prefs=user_prefs,
        )

        assert result.is_success()
        decision = result.value

        # Should have user preferences factor
        factor_names = [f.name for f in decision.factors]
        assert "User Preferences" in factor_names

    @pytest.mark.asyncio
    async def test_analyze_image_characteristics(self):
        """Test image characteristics analysis."""
        user_prefs = UserPreferences()

        factor = await self.strategy._analyze_image_characteristics(
            self.image_metadata, user_prefs
        )

        assert factor.name == "Image Characteristics"
        assert 0.0 <= factor.score <= 1.0
        assert factor.weight == self.strategy.weights.image_characteristics
        assert len(factor.reasoning) > 0

    @pytest.mark.asyncio
    async def test_analyze_image_characteristics_artistic(self):
        """Test image characteristics analysis for artistic images."""
        artistic_image = ImageMetadata(
            path="/test/art.png",
            characteristics=[ImageCharacteristic.ARTISTIC],
            quality_score=0.9,
        )

        user_prefs = UserPreferences()

        factor = await self.strategy._analyze_image_characteristics(
            artistic_image, user_prefs
        )

        # Artistic images should get higher scores
        assert factor.score > 0.6
        assert "artistic" in factor.reasoning.lower()

    @pytest.mark.asyncio
    async def test_analyze_content_flow(self):
        """Test content flow analysis."""
        factor = await self.strategy._analyze_content_flow(
            self.content_context, self.document_context
        )

        assert factor.name == "Content Flow"
        assert 0.0 <= factor.score <= 1.0
        assert factor.weight == self.strategy.weights.content_flow

    @pytest.mark.asyncio
    async def test_analyze_content_flow_bestiary(self):
        """Test content flow analysis for bestiary content."""
        bestiary_context = ContentContext(
            content_type=ContentType.BESTIARY,
            text_density=0.8,
            has_other_images=True,
        )

        factor = await self.strategy._analyze_content_flow(
            bestiary_context, self.document_context
        )

        # Bestiary content should get positive score
        assert "bestiary" in factor.reasoning.lower()

    @pytest.mark.asyncio
    async def test_analyze_page_position(self):
        """Test page position analysis."""
        page_context = PageContext(
            available_width=500.0,
            available_height=700.0,
            column_width=450.0,
            margin_width=50.0,
            current_fill=0.9,  # Nearly full page
            remaining_space=70.0,
        )

        factor = await self.strategy._analyze_page_position(
            self.document_context, page_context
        )

        assert factor.name == "Page Position"
        # Nearly full page should reduce score
        assert factor.score < 0.6

    @pytest.mark.asyncio
    async def test_analyze_surrounding_context(self):
        """Test surrounding context analysis."""
        context_with_tables = ContentContext(
            content_type=ContentType.BESTIARY,
            structural_elements=["table", "list"],
            word_count=100,  # Short content
        )

        factor = await self.strategy._analyze_surrounding_context(
            context_with_tables, self.image_metadata
        )

        assert factor.name == "Surrounding Context"
        # Tables and short content should reduce score
        assert factor.score < 0.7

    @pytest.mark.asyncio
    async def test_analyze_user_preferences(self):
        """Test user preferences analysis."""
        user_prefs = UserPreferences(
            prefer_inline=True,
            optimization_target=OptimizationTarget.PRINT,
        )

        factor = await self.strategy._analyze_user_preferences(
            user_prefs, self.image_metadata
        )

        assert factor.name == "User Preferences"
        # Inline preference should boost score
        assert factor.score > 0.6

    @pytest.mark.asyncio
    async def test_analyze_technical_constraints(self):
        """Test technical constraints analysis."""
        large_image = ImageMetadata(
            path="/test/large.png",
            file_size_bytes=10 * 1024 * 1024,  # 10MB - large
        )

        factor = await self.strategy._analyze_technical_constraints(
            large_image, self.document_context
        )

        assert factor.name == "Technical Constraints"
        # Large file should reduce score
        assert factor.score < 0.5

    def test_calculate_placement_scores(self):
        """Test placement score calculation."""
        from studiorum.latex_engine.core.images.placement_models import (
            create_placement_factor,
        )

        factors = [
            create_placement_factor("Factor 1", 0.5, 0.8, "Good"),
            create_placement_factor("Factor 2", 0.3, 0.6, "OK"),
            create_placement_factor("Factor 3", 0.2, 0.9, "Excellent"),
        ]

        user_prefs = UserPreferences()

        scores = self.strategy._calculate_placement_scores(factors, user_prefs)

        # Should return scores for all placement types
        assert len(scores) > 0
        for placement, score in scores.items():
            assert isinstance(placement, ImagePlacement)
            assert 0.0 <= score <= 1.0

    def test_determine_optimal_size(self):
        """Test optimal size determination."""
        size = self.strategy._determine_optimal_size(
            self.image_metadata,
            ImagePlacement.WRAP_RIGHT,
            self.content_context,
            UserPreferences(),
        )

        assert isinstance(size, ImageSize)

        # Portrait creature image should be PORTRAIT size when wrapped
        assert size == ImageSize.PORTRAIT

    def test_determine_optimal_size_full_width(self):
        """Test optimal size for full-width placement."""
        wide_image = ImageMetadata(
            path="/test/wide.png",
            dimensions=ImageDimensions.from_dimensions(1200, 400),  # Very wide
        )

        size = self.strategy._determine_optimal_size(
            wide_image,
            ImagePlacement.FULL_WIDTH,
            self.content_context,
            UserPreferences(),
        )

        assert size == ImageSize.FULL_WIDTH

    def test_calculate_confidence(self):
        """Test confidence calculation."""
        # Test with clear winner - larger gap for high confidence
        high_confidence_scores = {
            ImagePlacement.WRAP_RIGHT: 0.9,
            ImagePlacement.WRAP_LEFT: 0.4,  # Reduced from 0.5 to create larger gap
            ImagePlacement.FLOAT_HERE: 0.3,
        }

        confidence = self.strategy._calculate_confidence(high_confidence_scores, 0.9)

        # Large gap should give high confidence
        assert confidence > 0.7

    def test_calculate_confidence_close_scores(self):
        """Test confidence calculation with close scores."""
        # Test with close scores
        low_confidence_scores = {
            ImagePlacement.WRAP_RIGHT: 0.6,
            ImagePlacement.WRAP_LEFT: 0.58,
            ImagePlacement.FLOAT_HERE: 0.55,
        }

        confidence = self.strategy._calculate_confidence(low_confidence_scores, 0.6)

        # Small gap should give lower confidence
        assert confidence < 0.6

    def test_strategy_initialization(self):
        """Test strategy initialization with custom weights."""
        custom_weights = PlacementWeights(
            image_characteristics=0.4,
            content_flow=0.3,
            page_position=0.1,
            surrounding_context=0.1,
            user_preferences=0.05,
            technical_constraints=0.05,
        )

        strategy = ContentAwarePlacementStrategy(
            weights=custom_weights,
            enable_caching=False,
        )

        # Weights should be normalized
        total = (
            strategy.weights.image_characteristics
            + strategy.weights.content_flow
            + strategy.weights.page_position
            + strategy.weights.surrounding_context
            + strategy.weights.user_preferences
            + strategy.weights.technical_constraints
        )

        assert total == pytest.approx(1.0, abs=0.001)
        assert strategy.enable_caching is False

    @pytest.mark.asyncio
    async def test_concurrent_factor_analysis(self):
        """Test that factor analysis works concurrently."""
        # This test ensures asyncio.gather works correctly
        result = await self.strategy.determine_placement(
            self.image_metadata,
            self.content_context,
            self.document_context,
        )

        assert result.is_success()
        decision = result.value

        # Should have all expected factors
        factor_names = [f.name for f in decision.factors]
        expected_factors = [
            "Image Characteristics",
            "Content Flow",
            "Page Position",
            "Surrounding Context",
            "User Preferences",
            "Technical Constraints",
        ]

        for expected in expected_factors:
            assert expected in factor_names

    @pytest.mark.asyncio
    async def test_error_handling_in_factors(self):
        """Test error handling when factor analysis fails."""
        # Mock one of the factor analysis methods to raise an exception
        with patch.object(
            self.strategy,
            "_analyze_image_characteristics",
            side_effect=Exception("Test error"),
        ):
            result = await self.strategy.determine_placement(
                self.image_metadata,
                self.content_context,
                self.document_context,
            )

            assert result.is_error()
            assert "Test error" in str(result.error)

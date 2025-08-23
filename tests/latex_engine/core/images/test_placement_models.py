"""Tests for placement models and data structures.

This module tests the Pydantic models and factory functions used throughout
the Phase 2 intelligent placement system.
"""

from pathlib import Path

import pytest

from studiorum.latex_engine.core.images.image_placer import ImagePlacement, ImageSize
from studiorum.latex_engine.core.images.placement_models import (
    ContentContext,
    ContentType,
    DocumentContext,
    ImageCharacteristic,
    ImageDimensions,
    ImageMetadata,
    OptimizationConfig,
    OptimizationTarget,
    PageContext,
    PlacementDecision,
    PlacementFactor,
    create_default_optimization_config,
    create_placement_factor,
)


class TestImageDimensions:
    """Test ImageDimensions model and factory methods."""

    def test_create_from_dimensions_landscape(self):
        """Test creating landscape dimensions."""
        dims = ImageDimensions.from_dimensions(800, 600)

        assert dims.width == 800
        assert dims.height == 600
        assert dims.aspect_ratio == pytest.approx(1.333, abs=0.001)
        assert dims.is_landscape is True
        assert dims.is_portrait is False
        assert dims.is_square is False

    def test_create_from_dimensions_portrait(self):
        """Test creating portrait dimensions."""
        dims = ImageDimensions.from_dimensions(600, 800)

        assert dims.width == 600
        assert dims.height == 800
        assert dims.aspect_ratio == 0.75
        assert dims.is_landscape is False
        assert dims.is_portrait is True
        assert dims.is_square is False

    def test_create_from_dimensions_square(self):
        """Test creating square dimensions."""
        dims = ImageDimensions.from_dimensions(500, 500)

        assert dims.width == 500
        assert dims.height == 500
        assert dims.aspect_ratio == 1.0
        assert dims.is_landscape is False
        assert dims.is_portrait is False
        assert dims.is_square is True

    def test_create_from_dimensions_nearly_square(self):
        """Test creating nearly square dimensions within tolerance."""
        dims = ImageDimensions.from_dimensions(500, 480)

        assert dims.aspect_ratio == pytest.approx(1.042, abs=0.001)
        assert dims.is_square is True  # Within 0.1 tolerance


class TestImageMetadata:
    """Test ImageMetadata model."""

    def test_create_basic_metadata(self):
        """Test creating basic image metadata."""
        metadata = ImageMetadata(
            path="/test/image.png",
            local_path=Path("/test/image.png"),
            characteristics=[ImageCharacteristic.ARTISTIC],
            content_hints=["creature"],
            title="Test Creature",
        )

        assert metadata.path == "/test/image.png"
        assert metadata.local_path == Path("/test/image.png")
        assert ImageCharacteristic.ARTISTIC in metadata.characteristics
        assert "creature" in metadata.content_hints
        assert metadata.title == "Test Creature"
        assert metadata.quality_score == 0.5  # Default value

    def test_metadata_validation(self):
        """Test metadata field validation."""
        # Quality score should be between 0.0 and 1.0
        with pytest.raises(ValueError):
            ImageMetadata(path="/test.png", quality_score=1.5)

        with pytest.raises(ValueError):
            ImageMetadata(path="/test.png", quality_score=-0.1)


class TestContentContext:
    """Test ContentContext model."""

    def test_create_bestiary_context(self):
        """Test creating bestiary content context."""
        context = ContentContext(
            content_type=ContentType.BESTIARY,
            section_title="Ancient Dragons",
            word_count=350,
            has_other_images=True,
            structural_elements=["statblock", "table"],
        )

        assert context.content_type == ContentType.BESTIARY
        assert context.section_title == "Ancient Dragons"
        assert context.word_count == 350
        assert context.has_other_images is True
        assert "statblock" in context.structural_elements

    def test_context_defaults(self):
        """Test context model defaults."""
        context = ContentContext(content_type=ContentType.ADVENTURE)

        assert context.surrounding_text == ""
        assert context.word_count == 0
        assert context.text_density == 0.5
        assert context.has_other_images is False
        assert context.reading_flow_position == "middle"


class TestDocumentContext:
    """Test DocumentContext model."""

    def test_create_document_context(self):
        """Test creating document context."""
        context = DocumentContext(
            total_pages=100,
            current_page=25,
            chapter_number=3,
            document_style="narrative",
            target_format="pdf",
        )

        assert context.total_pages == 100
        assert context.current_page == 25
        assert context.chapter_number == 3
        assert context.document_style == "narrative"
        assert context.target_format == "pdf"

    def test_document_context_defaults(self):
        """Test document context defaults."""
        context = DocumentContext()

        assert context.total_pages == 1
        assert context.current_page == 1
        assert context.page_position == 0.5
        assert context.section_depth == 1


class TestPageContext:
    """Test PageContext model."""

    def test_create_page_context(self):
        """Test creating page context."""
        context = PageContext(
            available_width=500.0,
            available_height=700.0,
            column_width=450.0,
            margin_width=50.0,
            current_fill=0.3,
            remaining_space=490.0,
            is_chapter_start=True,
        )

        assert context.available_width == 500.0
        assert context.available_height == 700.0
        assert context.current_fill == 0.3
        assert context.is_chapter_start is True

    def test_page_context_validation(self):
        """Test page context field validation."""
        # Current fill should be between 0.0 and 1.0
        with pytest.raises(ValueError):
            PageContext(
                available_width=500.0,
                available_height=700.0,
                column_width=450.0,
                margin_width=50.0,
                current_fill=1.5,  # Invalid
                remaining_space=100.0,
            )


class TestPlacementFactor:
    """Test PlacementFactor model and factory."""

    def test_create_placement_factor(self):
        """Test creating a placement factor."""
        factor = create_placement_factor(
            name="Test Factor",
            weight=0.8,
            score=0.9,
            reasoning="Test reasoning",
        )

        assert factor.name == "Test Factor"
        assert factor.weight == 0.8
        assert factor.score == 0.9
        assert factor.reasoning == "Test reasoning"

    def test_placement_factor_clamping(self):
        """Test that placement factor values are clamped to valid ranges."""
        factor = create_placement_factor(
            name="Test Factor",
            weight=1.5,  # Should be clamped to 1.0
            score=-0.1,  # Should be clamped to 0.0
            reasoning="Clamping test",
        )

        assert factor.weight == 1.0
        assert factor.score == 0.0

    def test_placement_factor_validation(self):
        """Test placement factor field validation."""
        # Direct model creation should validate ranges
        with pytest.raises(ValueError):
            PlacementFactor(
                name="Test",
                weight=1.5,
                score=0.5,
                reasoning="Invalid weight",
            )


class TestPlacementDecision:
    """Test PlacementDecision model."""

    def test_create_placement_decision(self):
        """Test creating a placement decision."""
        factors = [
            create_placement_factor("Factor 1", 0.6, 0.8, "Good factor"),
            create_placement_factor("Factor 2", 0.4, 0.7, "Another factor"),
        ]

        decision = PlacementDecision(
            placement=ImagePlacement.WRAP_RIGHT,
            size=ImageSize.MEDIUM,
            confidence=0.85,
            factors=factors,
            overall_score=0.75,
            alternative_placements=[
                (ImagePlacement.FLOAT_HERE, 0.7),
                (ImagePlacement.WRAP_LEFT, 0.65),
            ],
        )

        assert decision.placement == ImagePlacement.WRAP_RIGHT
        assert decision.size == ImageSize.MEDIUM
        assert decision.confidence == 0.85
        assert len(decision.factors) == 2
        assert decision.overall_score == 0.75
        assert len(decision.alternative_placements) == 2

    def test_placement_decision_validation(self):
        """Test placement decision validation."""
        # Confidence should be between 0.0 and 1.0
        with pytest.raises(ValueError):
            PlacementDecision(
                placement=ImagePlacement.WRAP_RIGHT,
                size=ImageSize.MEDIUM,
                confidence=1.1,  # Invalid
                factors=[],
                overall_score=0.5,
            )


class TestOptimizationConfig:
    """Test OptimizationConfig model and factory."""

    def test_create_optimization_config(self):
        """Test creating optimization configuration."""
        config = OptimizationConfig(
            target=OptimizationTarget.DIGITAL,
            quality_priority=0.7,
            target_dpi=150,
            max_file_size_mb=2.0,
        )

        assert config.target == OptimizationTarget.DIGITAL
        assert config.quality_priority == 0.7
        assert config.target_dpi == 150
        assert config.max_file_size_mb == 2.0

    def test_optimization_config_validation(self):
        """Test optimization configuration validation."""
        # Quality priority should be between 0.0 and 1.0
        with pytest.raises(ValueError):
            OptimizationConfig(
                target=OptimizationTarget.DIGITAL,
                quality_priority=1.5,  # Invalid
            )

        # Target DPI should be within valid range
        with pytest.raises(ValueError):
            OptimizationConfig(
                target=OptimizationTarget.DIGITAL,
                target_dpi=50,  # Too low
            )

    def test_create_default_optimization_configs(self):
        """Test factory function for default optimization configs."""
        # Test digital optimization
        digital_config = create_default_optimization_config(OptimizationTarget.DIGITAL)
        assert digital_config.target == OptimizationTarget.DIGITAL
        assert digital_config.target_dpi == 96
        assert digital_config.max_file_size_mb == 2.0

        # Test print optimization
        print_config = create_default_optimization_config(OptimizationTarget.PRINT)
        assert print_config.target == OptimizationTarget.PRINT
        assert print_config.target_dpi == 300
        assert print_config.max_file_size_mb == 10.0

        # Test hybrid optimization
        hybrid_config = create_default_optimization_config(OptimizationTarget.HYBRID)
        assert hybrid_config.target == OptimizationTarget.HYBRID
        assert hybrid_config.target_dpi == 150
        assert hybrid_config.max_file_size_mb == 5.0

    def test_optimization_config_defaults(self):
        """Test optimization configuration defaults."""
        config = OptimizationConfig(target=OptimizationTarget.DIGITAL)

        assert config.quality_priority == 0.7
        assert config.target_dpi == 150
        assert config.colour_profile == "sRGB"
        assert config.compression_level == 0.8
        assert config.preserve_transparency is True


class TestContentType:
    """Test ContentType enum."""

    def test_content_type_values(self):
        """Test that ContentType has expected values."""
        assert ContentType.BESTIARY == "bestiary"
        assert ContentType.ADVENTURE == "adventure"
        assert ContentType.ITEM_COLLECTION == "item_collection"
        assert ContentType.SPELL_COLLECTION == "spell_collection"
        assert ContentType.UNKNOWN == "unknown"

    def test_content_type_coverage(self):
        """Test that we have content types for major D&D content."""
        expected_types = {
            "bestiary",
            "adventure",
            "item_collection",
            "spell_collection",
            "background",
            "class_feature",
            "chapter_intro",
            "sidebar",
            "unknown",
        }

        actual_types = {ct.value for ct in ContentType}
        assert expected_types.issubset(actual_types)


class TestImageCharacteristic:
    """Test ImageCharacteristic enum."""

    def test_image_characteristic_values(self):
        """Test that ImageCharacteristic has expected values."""
        assert ImageCharacteristic.PORTRAIT == "portrait"
        assert ImageCharacteristic.LANDSCAPE == "landscape"
        assert ImageCharacteristic.ARTISTIC == "artistic"
        assert ImageCharacteristic.TECHNICAL == "technical"

    def test_image_characteristic_coverage(self):
        """Test that we have characteristics for common image types."""
        expected_characteristics = {
            "portrait",
            "landscape",
            "square",
            "icon",
            "decorative",
            "informational",
            "artistic",
            "technical",
        }

        actual_characteristics = {ic.value for ic in ImageCharacteristic}
        assert expected_characteristics == actual_characteristics

"""Tests for LayoutAnalyzer.

This module tests the advanced layout analysis system including page space
analysis, page break prediction, and image sequence optimization.
"""

from pathlib import Path

import pytest

from studiorum.latex_engine.core.images.image_placer import ImagePlacement, ImageSize
from studiorum.latex_engine.core.images.layout_analyzer import (
    LayoutAnalyzer,
    LayoutConstraints,
    LayoutMetrics,
)
from studiorum.latex_engine.core.images.placement_models import (
    ContentFlow,
    DocumentContext,
    ImageCharacteristic,
    ImageMetadata,
    OptimizedPlacement,
    PageContext,
    PlacementDecision,
)


class TestLayoutConstraints:
    """Test LayoutConstraints model."""

    def test_create_layout_constraints(self):
        """Test creating layout constraints."""
        constraints = LayoutConstraints(
            min_text_block_size=300,
            max_images_per_page=6,
            min_space_between_images=0.15,
            avoid_orphan_widows=True,
            prefer_section_breaks=True,
            maintain_image_groups=True,
        )

        assert constraints.min_text_block_size == 300
        assert constraints.max_images_per_page == 6
        assert constraints.min_space_between_images == 0.15
        assert constraints.avoid_orphan_widows is True

    def test_layout_constraints_defaults(self):
        """Test layout constraints defaults."""
        constraints = LayoutConstraints()

        assert constraints.min_text_block_size == 200
        assert constraints.max_images_per_page == 4
        assert constraints.min_space_between_images == 0.1


class TestLayoutAnalyzer:
    """Test LayoutAnalyzer implementation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.constraints = LayoutConstraints(
            max_images_per_page=5,
            min_text_block_size=250,
        )
        self.analyzer = LayoutAnalyzer(self.constraints)

        # Create test page context
        self.page_context = PageContext(
            available_width=500.0,
            available_height=700.0,
            column_width=450.0,
            margin_width=50.0,
            current_fill=0.4,
            remaining_space=420.0,
            has_header=True,
            has_footer=True,
        )

    def test_initialization(self):
        """Test analyzer initialization."""
        analyzer = LayoutAnalyzer()

        # Should use default constraints
        assert analyzer.constraints.max_images_per_page == 4

        # Should initialize empty cache
        assert len(analyzer._page_cache) == 0

    def test_initialization_with_custom_constraints(self):
        """Test analyzer initialization with custom constraints."""
        custom_constraints = LayoutConstraints(max_images_per_page=8)
        analyzer = LayoutAnalyzer(custom_constraints)

        assert analyzer.constraints.max_images_per_page == 8

    def test_analyze_page_space(self):
        """Test page space analysis."""
        analysis = self.analyzer.analyze_page_space(self.page_context)

        assert analysis.total_space == 350000.0  # 500 * 700
        assert analysis.used_space == 140000.0  # total * 0.4 fill
        assert analysis.remaining_space == 210000.0

        # Should have space fragments
        assert len(analysis.space_fragments) > 0
        assert analysis.largest_contiguous_space > 0

        # Should have size recommendations
        assert len(analysis.optimal_image_sizes) > 0
        for size, fit_score in analysis.optimal_image_sizes:
            assert isinstance(size, ImageSize)
            assert 0.0 <= fit_score <= 1.0

    def test_analyze_page_space_nearly_full(self):
        """Test page space analysis for nearly full page."""
        full_page = PageContext(
            available_width=500.0,
            available_height=700.0,
            column_width=450.0,
            margin_width=50.0,
            current_fill=0.9,  # Nearly full
            remaining_space=70.0,
        )

        analysis = self.analyzer.analyze_page_space(full_page)

        assert analysis.current_fill == 0.9
        assert analysis.remaining_space < analysis.total_space * 0.2

        # Should recommend smaller images
        recommended_sizes = [size for size, _ in analysis.optimal_image_sizes]
        assert ImageSize.SMALL in recommended_sizes

    def test_analyze_page_space_mostly_empty(self):
        """Test page space analysis for mostly empty page."""
        empty_page = PageContext(
            available_width=500.0,
            available_height=700.0,
            column_width=450.0,
            margin_width=50.0,
            current_fill=0.1,  # Mostly empty
            remaining_space=630.0,
        )

        analysis = self.analyzer.analyze_page_space(empty_page)

        # Should recommend larger images
        recommended_sizes = [size for size, _ in analysis.optimal_image_sizes]
        assert (
            ImageSize.LARGE in recommended_sizes
            or ImageSize.FULL_WIDTH in recommended_sizes
        )

    def test_predict_page_breaks(self):
        """Test page break prediction."""
        content_flow = ContentFlow(
            total_length=10000,
            sections=[
                {
                    "type": "chapter",
                    "title": "Chapter 1",
                    "start_position": 0,
                    "end_position": 2000,
                },
                {
                    "type": "section",
                    "title": "Ancient Dragons",
                    "start_position": 2000,
                    "end_position": 5000,
                },
                {
                    "type": "subsection",
                    "title": "Red Dragons",
                    "start_position": 5000,
                    "end_position": 7500,
                },
                {
                    "type": "paragraph",
                    "start_position": 7500,
                    "end_position": 10000,
                },
            ],
            image_positions=[1500, 3500, 6000, 8500],
            reading_difficulty=0.6,
        )

        break_points = self.analyzer.predict_page_breaks(content_flow)

        assert len(break_points) > 0

        # Should have breaks at major section boundaries
        chapter_breaks = [
            bp for bp in break_points if "chapter" in bp.reasoning.lower()
        ]
        assert len(chapter_breaks) > 0

        # Break points should be sorted by position
        positions = [bp.position for bp in break_points]
        assert positions == sorted(positions)

        # All positions should be valid
        for bp in break_points:
            assert 0.0 <= bp.position <= 1.0
            assert 0.0 <= bp.quality_score <= 1.0

    def test_predict_page_breaks_with_images(self):
        """Test page break prediction considering image positions."""
        content_flow = ContentFlow(
            total_length=5000,
            sections=[
                {
                    "type": "section",
                    "start_position": 0,
                    "end_position": 2500,
                },
                {
                    "type": "section",
                    "start_position": 2500,
                    "end_position": 5000,
                },
            ],
            image_positions=[1000, 1100, 1200],  # Image cluster
            reading_difficulty=0.4,
        )

        break_points = self.analyzer.predict_page_breaks(content_flow)

        # Should have image-aware break points
        image_breaks = [bp for bp in break_points if "image" in bp.break_type]
        assert len(image_breaks) > 0

    def test_optimize_image_sequence_empty(self):
        """Test optimizing empty image sequence."""
        optimized = self.analyzer.optimize_image_sequence([])

        assert optimized == []

    def test_optimize_image_sequence_single_image(self):
        """Test optimizing single image."""
        image_metadata = ImageMetadata(path="/test/image.png")
        placement_decision = PlacementDecision(
            placement=ImagePlacement.WRAP_RIGHT,
            size=ImageSize.MEDIUM,
            confidence=0.8,
            factors=[],
            overall_score=0.7,
        )

        images = [(image_metadata, placement_decision)]
        optimized = self.analyzer.optimize_image_sequence(images)

        assert len(optimized) == 1
        assert isinstance(optimized[0], OptimizedPlacement)
        assert optimized[0].sequence_position == 0
        assert optimized[0].decision == placement_decision

    def test_optimize_image_sequence_multiple_images(self):
        """Test optimizing multiple images."""
        images = []
        for i in range(3):
            image_metadata = ImageMetadata(path=f"/test/image{i}.png")
            placement_decision = PlacementDecision(
                placement=ImagePlacement.WRAP_LEFT
                if i % 2 == 0
                else ImagePlacement.WRAP_RIGHT,
                size=ImageSize.MEDIUM,
                confidence=0.8,
                factors=[],
                overall_score=0.7,
            )
            images.append((image_metadata, placement_decision))

        optimized = self.analyzer.optimize_image_sequence(images)

        assert len(optimized) == 3

        # Should have sequence positions
        for i, placement in enumerate(optimized):
            assert placement.sequence_position == i
            assert isinstance(placement.page_impact, dict)
            assert len(placement.final_latex_command) > 0
            assert len(placement.required_packages) > 0

    def test_optimize_image_sequence_with_clustering(self):
        """Test sequence optimization detects and handles clustering."""
        # Create closely spaced images that might cause clustering issues
        images = []
        for i in range(4):
            image_metadata = ImageMetadata(
                path=f"/test/clustered{i}.png",
                content_hints=["creature"],  # All same type
            )
            placement_decision = PlacementDecision(
                placement=ImagePlacement.WRAP_RIGHT,
                size=ImageSize.MEDIUM,
                confidence=0.6,  # Lower confidence suggests potential issues
                factors=[],
                overall_score=0.6,
            )
            images.append((image_metadata, placement_decision))

        optimized = self.analyzer.optimize_image_sequence(images)

        # Should detect low coherence and apply adjustments
        layout_adjustments = []
        for placement in optimized:
            layout_adjustments.extend(placement.layout_adjustments)

        # Should have some layout adjustments for flow
        assert len(layout_adjustments) > 0

    def test_assess_layout_quality_no_images(self):
        """Test layout quality assessment with no images."""
        document_context = DocumentContext(total_pages=20)

        metrics = self.analyzer.assess_layout_quality([], document_context)

        assert isinstance(metrics, LayoutMetrics)
        assert metrics.space_utilization == 0.5  # Neutral
        assert metrics.readability_score == 0.8  # High for text-only
        assert metrics.aesthetic_score == 0.4  # Low without images
        assert metrics.technical_feasibility == 1.0  # Perfect for no images

    def test_assess_layout_quality_with_images(self):
        """Test layout quality assessment with images."""
        # Create optimized placements
        placements = []
        for i in range(3):
            decision = PlacementDecision(
                placement=ImagePlacement.WRAP_RIGHT,
                size=ImageSize.MEDIUM,
                confidence=0.8,
                factors=[],
                overall_score=0.7,
            )
            placement = OptimizedPlacement(
                decision=decision,
                layout_adjustments=[],
                sequence_position=i,
                page_impact={
                    "space_utilization": 0.1 + (i * 0.05),
                    "readability_impact": 0.8,
                    "aesthetic_contribution": 0.7,
                },
                neighbor_interactions=[],
                final_latex_command=f"% Image {i}",
                required_packages=["graphicx"],
            )
            placements.append(placement)

        document_context = DocumentContext(total_pages=20)

        metrics = self.analyzer.assess_layout_quality(placements, document_context)

        assert 0.0 <= metrics.space_utilization <= 1.0
        assert 0.0 <= metrics.content_density <= 1.0
        assert 0.0 <= metrics.image_distribution_score <= 1.0
        assert 0.0 <= metrics.readability_score <= 1.0
        assert 0.0 <= metrics.aesthetic_score <= 1.0
        assert 0.0 <= metrics.technical_feasibility <= 1.0

    def test_assess_layout_quality_overcrowded(self):
        """Test layout quality assessment for overcrowded layout."""
        # Create many placements (over the limit)
        placements = []
        for i in range(10):  # More than max_images_per_page (5)
            decision = PlacementDecision(
                placement=ImagePlacement.WRAP_RIGHT,
                size=ImageSize.MEDIUM,
                confidence=0.6,
                factors=[],
                overall_score=0.6,
            )
            placement = OptimizedPlacement(
                decision=decision,
                layout_adjustments=[],
                sequence_position=i,
                page_impact={"space_utilization": 0.2},
                neighbor_interactions=[],
                final_latex_command=f"% Image {i}",
                required_packages=["graphicx"],
            )
            placements.append(placement)

        document_context = DocumentContext(total_pages=2)  # Few pages

        metrics = self.analyzer.assess_layout_quality(placements, document_context)

        # Should detect overcrowding
        assert metrics.content_density > 0.8  # High density
        assert metrics.readability_score < 0.7  # Reduced readability

    def test_space_fragment_analysis(self):
        """Test space fragmentation analysis."""
        # Test with moderately filled page
        moderate_page = PageContext(
            available_width=500.0,
            available_height=700.0,
            column_width=450.0,
            margin_width=50.0,
            current_fill=0.5,
            remaining_space=300.0,
        )

        fragments = self.analyzer._analyze_space_fragments(moderate_page)

        assert len(fragments) > 0
        assert all(fragment > 0 for fragment in fragments)
        assert sum(fragments) <= moderate_page.remaining_space

    def test_image_size_recommendations(self):
        """Test image size recommendations based on space."""
        # Large available space
        large_fragments = [400.0, 200.0]
        recommendations = self.analyzer._recommend_image_sizes(
            self.page_context, large_fragments
        )

        assert len(recommendations) > 0

        # Should recommend larger sizes for large space
        sizes = [size for size, _ in recommendations]
        assert ImageSize.LARGE in sizes or ImageSize.FULL_WIDTH in sizes

        # All fit scores should be valid
        for size, fit_score in recommendations:
            assert 0.0 <= fit_score <= 1.0

    def test_break_quality_adjustment(self):
        """Test break point quality adjustment."""
        content_flow = ContentFlow(
            total_length=5000,
            image_positions=[950, 1000, 1050],  # Images near position 1000
            reading_difficulty=0.8,  # High difficulty
        )

        # Break near images should have reduced quality
        near_images_quality = self.analyzer._adjust_break_quality(
            0.8, 1000, content_flow
        )
        assert near_images_quality < 0.8

        # Break away from images should maintain quality
        away_from_images_quality = self.analyzer._adjust_break_quality(
            0.8, 2000, content_flow
        )
        # High difficulty content should boost quality slightly
        assert away_from_images_quality >= 0.8

    def test_break_deduplication(self):
        """Test break point deduplication."""
        from studiorum.latex_engine.core.images.placement_models import BreakPoint

        breaks = [
            BreakPoint(
                position=0.1,
                break_type="test",
                quality_score=0.7,
                reasoning="First break",
            ),
            BreakPoint(
                position=0.11,  # Very close to first
                break_type="test",
                quality_score=0.9,  # Higher quality
                reasoning="Better break",
            ),
            BreakPoint(
                position=0.5,  # Far from others
                break_type="test",
                quality_score=0.6,
                reasoning="Distant break",
            ),
        ]

        deduplicated = self.analyzer._deduplicate_breaks(breaks)

        # Should keep the higher quality break from the close pair
        assert len(deduplicated) == 2
        assert deduplicated[0].quality_score == 0.9  # Better of the close pair
        assert deduplicated[1].position == 0.5  # Distant break preserved

    def test_image_coherence_calculation(self):
        """Test image coherence calculation."""
        # Similar images should have high coherence
        similar_images = [
            ImageMetadata(
                path="/test/dragon1.png",
                characteristics=[ImageCharacteristic.PORTRAIT],
                content_hints=["creature"],
            ),
            ImageMetadata(
                path="/test/dragon2.png",
                characteristics=[ImageCharacteristic.PORTRAIT],
                content_hints=["creature"],
            ),
        ]

        coherence = self.analyzer._calculate_image_coherence(similar_images)
        assert coherence > 0.7  # High coherence

        # Diverse images should have lower coherence
        diverse_images = [
            ImageMetadata(
                path="/test/creature.png",
                characteristics=[ImageCharacteristic.PORTRAIT],
                content_hints=["creature"],
            ),
            ImageMetadata(
                path="/test/map.png",
                characteristics=[ImageCharacteristic.TECHNICAL],
                content_hints=["map"],
            ),
            ImageMetadata(
                path="/test/art.png",
                characteristics=[ImageCharacteristic.ARTISTIC],
                content_hints=["scene"],
            ),
        ]

        diverse_coherence = self.analyzer._calculate_image_coherence(diverse_images)
        assert diverse_coherence < coherence  # Lower than similar images

    def test_single_image_coherence(self):
        """Test coherence calculation with single image."""
        single_image = [ImageMetadata(path="/test/solo.png", characteristics=[])]

        coherence = self.analyzer._calculate_image_coherence(single_image)
        assert coherence == 1.0  # Perfect coherence for single image

    def test_empty_image_coherence(self):
        """Test coherence calculation with no images."""
        coherence = self.analyzer._calculate_image_coherence([])
        assert coherence == 0.0  # No coherence for empty list

"""Tests for AdventureImageIntegration functionality.

This module tests the adventure-specific image integration capabilities,
including chapter openers, location maps, NPC portraits, and atmospheric scenes.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from studiorum.core.result import Error, Success
from studiorum.latex_engine.core.images.integration.adventure import (
    AdventureImageIntegration,
    AdventureImageMetadata,
    AdventureImageResult,
    AdventureIntegrationConfig,
)
from studiorum.latex_engine.core.images.placement_models import (
    ImageCharacteristic,
    ImageDimensions,
    ImageMetadata,
)
from studiorum.renderers.core.interfaces import RenderingContext
from tests.test_helpers import reset_test_environment


class TestAdventureIntegrationConfig:
    """Test AdventureIntegrationConfig model."""

    def setup_method(self):
        reset_test_environment()

    def test_default_config(self):
        """Test default configuration values."""
        config = AdventureIntegrationConfig()

        assert config.enable_chapter_openers is True
        assert config.enable_location_maps is True
        assert config.enable_npc_portraits is True
        assert config.enable_atmospheric_scenes is True
        assert config.enable_chapter_galleries is True
        assert config.chapter_opener_placement == "chapter_start"
        assert config.max_images_per_chapter == 8
        assert config.enable_decorative_elements is True

    def test_custom_config(self):
        """Test custom configuration."""
        config = AdventureIntegrationConfig(
            enable_chapter_openers=False,
            max_images_per_chapter=12,
            chapter_opener_style="compact",
        )

        assert config.enable_chapter_openers is False
        assert config.max_images_per_chapter == 12
        assert config.chapter_opener_style == "compact"
        assert config.enable_decorative_elements is True  # Default preserved

    def test_config_validation(self):
        """Test configuration validation."""
        # Valid range
        config = AdventureIntegrationConfig(max_images_per_chapter=15)
        assert config.max_images_per_chapter == 15

        # Test boundary values
        config = AdventureIntegrationConfig(max_images_per_chapter=1)
        assert config.max_images_per_chapter == 1

        config = AdventureIntegrationConfig(max_images_per_chapter=20)
        assert config.max_images_per_chapter == 20


class TestAdventureImageMetadata:
    """Test AdventureImageMetadata model."""

    def setup_method(self):
        reset_test_environment()

    def test_basic_metadata(self):
        """Test basic metadata creation."""
        metadata = AdventureImageMetadata(
            adventure_name="Curse of Strahd",
            chapter_name="Chapter 1: Into the Mists",
        )

        assert metadata.adventure_name == "Curse of Strahd"
        assert metadata.chapter_name == "Chapter 1: Into the Mists"
        assert metadata.image_type == "illustration"  # Default
        assert metadata.confidence_score == 0.5  # Default

    def test_chapter_opener_metadata(self):
        """Test chapter opener specific metadata."""
        metadata = AdventureImageMetadata(
            adventure_name="Curse of Strahd",
            chapter_name="Chapter 1: Into the Mists",
            chapter_type="opening",
            image_type="opener",
            is_chapter_opener=True,
            themes=["gothic", "horror"],
        )

        assert metadata.is_chapter_opener is True
        assert metadata.image_type == "opener"
        assert metadata.chapter_type == "opening"
        assert "gothic" in metadata.themes
        assert "horror" in metadata.themes

    def test_npc_metadata(self):
        """Test NPC portrait metadata."""
        metadata = AdventureImageMetadata(
            adventure_name="Curse of Strahd",
            npcs=["Strahd von Zarovich", "Ireena Kolyana"],
            image_type="portrait",
            location="Castle Ravenloft",
        )

        assert len(metadata.npcs) == 2
        assert "Strahd von Zarovich" in metadata.npcs
        assert metadata.image_type == "portrait"
        assert metadata.location == "Castle Ravenloft"


class TestAdventureImageResult:
    """Test AdventureImageResult model."""

    def setup_method(self):
        reset_test_environment()

    def test_basic_result(self):
        """Test basic result creation."""
        result = AdventureImageResult(
            latex_command="\\includegraphics{test}",
            chapters_processed=3,
            images_integrated=5,
            layout_used="chapter_start",
        )

        assert result.latex_command == "\\includegraphics{test}"
        assert result.chapters_processed == 3
        assert result.images_integrated == 5
        assert result.layout_used == "chapter_start"
        assert result.opener_images_count == 0  # Default

    def test_detailed_result(self):
        """Test result with detailed counts."""
        result = AdventureImageResult(
            latex_command="\\begin{figure}...\\end{figure}",
            chapters_processed=5,
            images_integrated=12,
            layout_used="enhanced",
            opener_images_count=3,
            map_images_count=2,
            npc_images_count=4,
            atmospheric_images_count=3,
        )

        assert result.opener_images_count == 3
        assert result.map_images_count == 2
        assert result.npc_images_count == 4
        assert result.atmospheric_images_count == 3
        assert (
            result.opener_images_count
            + result.map_images_count
            + result.npc_images_count
            + result.atmospheric_images_count
            == 12
        )


class TestAdventureImageIntegration:
    """Test AdventureImageIntegration class."""

    def setup_method(self):
        reset_test_environment()

        # Create mock dependencies
        self.mock_processor = Mock()
        self.mock_placer = Mock()
        self.mock_strategy = Mock()
        self.mock_gallery = Mock()

        # Create test config
        self.config = AdventureIntegrationConfig(
            enable_decorative_elements=True,
            max_images_per_chapter=6,
        )

        # Create integration instance
        self.integration = AdventureImageIntegration(
            image_processor=self.mock_processor,
            enhanced_placer=self.mock_placer,
            content_aware_strategy=self.mock_strategy,
            gallery_processor=self.mock_gallery,
            config=self.config,
        )

    def test_initialization(self):
        """Test proper initialization."""
        assert self.integration.config.enable_decorative_elements is True
        assert self.integration.config.max_images_per_chapter == 6
        assert self.integration._image_processor is self.mock_processor
        assert self.integration._enhanced_placer is self.mock_placer

    def test_get_integration_statistics(self):
        """Test statistics retrieval."""
        stats = self.integration.get_integration_statistics()

        assert "config" in stats
        assert "capabilities" in stats
        assert "chapter_openers" in stats["capabilities"]
        assert "location_maps" in stats["capabilities"]
        assert "npc_portraits" in stats["capabilities"]
        assert "atmospheric_scenes" in stats["capabilities"]
        assert "decorative_elements" in stats["capabilities"]

    @pytest.mark.asyncio
    async def test_integrate_adventure_images_success(self):
        """Test successful adventure image integration."""
        # Create test adventure content
        adventure_content = {
            "name": "Curse of Strahd",
            "data": {
                "chapter": [
                    {
                        "name": "Chapter 1: Into the Mists",
                        "ordinal": 1,
                        "entries": [
                            {"location": "Barovia"},
                            {"npc": "Strahd von Zarovich"},
                        ],
                    }
                ]
            },
        }

        # Create test rendering context
        rendering_context = Mock(spec=RenderingContext)

        # Mock the integration methods
        with (
            patch.object(
                self.integration, "_discover_adventure_images"
            ) as mock_discover,
            patch.object(
                self.integration, "_generate_integrated_adventure_latex"
            ) as mock_generate,
        ):
            # Setup mock returns
            sample_images = [
                ImageMetadata(
                    path="strahd_chapter_opener",
                    local_path=Path("/test/opener.jpg"),
                    characteristics=[ImageCharacteristic.ARTISTIC],
                    dimensions=ImageDimensions.from_dimensions(1920, 1080),
                    file_size_bytes=2048000,
                )
            ]
            mock_discover.return_value = Success(sample_images)
            mock_generate.return_value = Success("\\includegraphics{test}")

            # Execute integration
            result = await self.integration.integrate_adventure_images(
                adventure_content, rendering_context
            )

            # Verify success
            assert isinstance(result, Success)
            adventure_result = result.value
            assert isinstance(adventure_result, AdventureImageResult)
            assert adventure_result.chapters_processed == 1
            assert adventure_result.latex_command == "\\includegraphics{test}"

    @pytest.mark.asyncio
    async def test_integrate_adventure_images_discovery_failure(self):
        """Test handling of image discovery failure."""
        adventure_content = {"name": "Test Adventure", "data": {"chapter": []}}
        rendering_context = Mock(spec=RenderingContext)

        with patch.object(
            self.integration, "_discover_adventure_images"
        ) as mock_discover:
            mock_discover.return_value = Error("Discovery failed")

            result = await self.integration.integrate_adventure_images(
                adventure_content, rendering_context
            )

            assert isinstance(result, Error)
            assert "Discovery failed" in str(result.error)

    @pytest.mark.asyncio
    async def test_integrate_adventure_images_latex_generation_failure(self):
        """Test handling of LaTeX generation failure."""
        adventure_content = {"name": "Test Adventure", "data": {"chapter": []}}
        rendering_context = Mock(spec=RenderingContext)

        with (
            patch.object(
                self.integration, "_discover_adventure_images"
            ) as mock_discover,
            patch.object(
                self.integration, "_generate_integrated_adventure_latex"
            ) as mock_generate,
        ):
            mock_discover.return_value = Success([])
            mock_generate.return_value = Error("LaTeX generation failed")

            result = await self.integration.integrate_adventure_images(
                adventure_content, rendering_context
            )

            assert isinstance(result, Error)
            assert "LaTeX generation failed" in str(result.error)

    def test_extract_adventure_metadata(self):
        """Test adventure metadata extraction."""
        adventure_content = {
            "name": "Curse of Strahd",
            "data": {
                "chapter": [
                    {
                        "name": "Chapter 1: Into the Mists",
                        "ordinal": 1,
                        "entries": [
                            {"location": "Village of Barovia"},
                            {"npc": "Ismark Kolyanovich"},
                        ],
                    },
                    {
                        "name": "Chapter 2: The Lands of Barovia",
                        "ordinal": 2,
                        "entries": [],
                    },
                ]
            },
        }

        metadata = self.integration._extract_adventure_metadata(adventure_content)

        assert metadata["adventure_name"] == "Curse of Strahd"
        assert len(metadata["chapters"]) == 2
        assert metadata["chapters"][0]["name"] == "Chapter 1: Into the Mists"
        assert metadata["chapters"][0]["number"] == 1
        assert "Village of Barovia" in metadata["locations"]
        assert "Ismark Kolyanovich" in metadata["npcs"]

    def test_determine_chapter_type(self):
        """Test chapter type determination."""
        # Test opening chapter
        chapter_data = {"name": "Introduction to Ravenloft"}
        chapter_type = self.integration._determine_chapter_type(chapter_data)
        assert chapter_type == "opening"

        # Test dungeon chapter
        chapter_data = {"name": "Castle Ravenloft Dungeon"}
        chapter_type = self.integration._determine_chapter_type(chapter_data)
        assert chapter_type == "dungeon"

        # Test conclusion chapter
        chapter_data = {"name": "Epilogue: After the Storm"}
        chapter_type = self.integration._determine_chapter_type(chapter_data)
        assert chapter_type == "conclusion"

        # Test narrative chapter
        chapter_data = {"name": "The Village of Barovia"}
        chapter_type = self.integration._determine_chapter_type(chapter_data)
        assert chapter_type == "narrative"

    def test_categorize_adventure_images(self):
        """Test adventure image categorization."""
        # Create test images
        discovered_images = [
            ImageMetadata(
                path="chapter_opener_1",
                local_path=Path("/test/opener1.jpg"),
                characteristics=[ImageCharacteristic.ARTISTIC],
                dimensions=ImageDimensions.from_dimensions(1920, 1080),
                file_size_bytes=2048000,
            ),
            ImageMetadata(
                path="barovia_map",
                local_path=Path("/test/map1.jpg"),
                characteristics=[ImageCharacteristic.INFORMATIONAL],
                dimensions=ImageDimensions.from_dimensions(1600, 1200),
                file_size_bytes=1536000,
            ),
            ImageMetadata(
                path="strahd_portrait",
                local_path=Path("/test/npc1.jpg"),
                characteristics=[ImageCharacteristic.PORTRAIT],
                dimensions=ImageDimensions.from_dimensions(800, 600),
                file_size_bytes=1024000,
            ),
        ]

        adventure_metadata = {
            "adventure_name": "Curse of Strahd",
            "chapters": [],
            "locations": ["Barovia"],
            "npcs": ["Strahd von Zarovich"],
            "themes": ["gothic", "horror"],
        }

        categorized = self.integration._categorize_adventure_images(
            discovered_images, adventure_metadata
        )

        # Verify categorization structure
        assert "chapter_openers" in categorized
        assert "location_maps" in categorized
        assert "npc_portraits" in categorized
        assert "atmospheric_scenes" in categorized
        assert "gallery_collections" in categorized

        # Note: The actual categorization would depend on the implementation
        # of _create_adventure_image_metadata method

    def test_select_optimal_adventure_images(self):
        """Test optimal image selection."""
        # Create categorized images
        categorized_images = {
            "chapter_openers": [
                AdventureImageMetadata(
                    adventure_name="Test", is_chapter_opener=True, confidence_score=0.9
                ),
                AdventureImageMetadata(
                    adventure_name="Test", is_chapter_opener=True, confidence_score=0.7
                ),
            ],
            "location_maps": [
                AdventureImageMetadata(
                    adventure_name="Test", image_type="map", confidence_score=0.8
                ),
            ],
            "npc_portraits": [],
            "atmospheric_scenes": [],
            "gallery_collections": [],
        }

        adventure_metadata = {"chapters": [{"name": "Chapter 1"}]}

        selected = self.integration._select_optimal_adventure_images(
            categorized_images, adventure_metadata
        )

        # Should select highest confidence images within limits
        assert len(selected) <= self.config.max_images_per_chapter

        # Chapter opener selection should be limited by chapter count
        selected_openers = [img for img in selected if img.is_chapter_opener]
        assert len(selected_openers) <= len(adventure_metadata["chapters"])

    def test_group_images_by_chapter(self):
        """Test image grouping by chapter."""
        images = [
            AdventureImageMetadata(adventure_name="Test", chapter_name="Chapter 1"),
            AdventureImageMetadata(adventure_name="Test", chapter_name="Chapter 1"),
            AdventureImageMetadata(adventure_name="Test", chapter_name="Chapter 2"),
            AdventureImageMetadata(
                adventure_name="Test",
                chapter_name=None,  # Should go to "general"
            ),
        ]

        grouped = self.integration._group_images_by_chapter(images)

        assert "Chapter 1" in grouped
        assert "Chapter 2" in grouped
        assert "general" in grouped
        assert len(grouped["Chapter 1"]) == 2
        assert len(grouped["Chapter 2"]) == 1
        assert len(grouped["general"]) == 1

    @pytest.mark.asyncio
    async def test_create_sample_adventure_images(self):
        """Test sample image creation for development."""
        sample_images = await self.integration._create_sample_adventure_images(
            "chapter_opener_test", {"adventure_name": "Test Adventure"}
        )

        assert isinstance(sample_images, list)
        # Implementation would return sample images for patterns containing "chapter"

    @pytest.mark.asyncio
    async def test_latex_generation_methods(self):
        """Test individual LaTeX generation methods."""
        test_image = AdventureImageMetadata(
            adventure_name="Test Adventure",
            chapter_name="Chapter 1",
            image_type="opener",
            is_chapter_opener=True,
        )

        adventure_metadata = {"adventure_name": "Test Adventure"}
        rendering_context = Mock(spec=RenderingContext)

        # Test chapter opener LaTeX generation
        result = await self.integration._create_chapter_opener_latex(
            test_image, adventure_metadata, rendering_context
        )

        assert isinstance(result, Success)
        latex = result.value
        assert "Chapter Opener" in latex
        assert "figure" in latex.lower()


class TestAdventureImageIntegrationAsync:
    """Test async functionality of AdventureImageIntegration."""

    def setup_method(self):
        reset_test_environment()

    @pytest.mark.asyncio
    async def test_async_image_discovery(self):
        """Test async image discovery functionality."""
        integration = AdventureImageIntegration(
            image_processor=Mock(),
            enhanced_placer=Mock(),
            content_aware_strategy=Mock(),
            gallery_processor=Mock(),
        )

        adventure_metadata = {
            "adventure_name": "Test Adventure",
            "locations": ["Test Location"],
            "npcs": ["Test NPC"],
        }

        Mock(spec=RenderingContext)

        # Test discovery with various patterns
        result = await integration._discover_adventure_images(
            "test_adventure", adventure_metadata
        )

        # Should return a Result type
        assert hasattr(result, "is_error")

    @pytest.mark.asyncio
    async def test_concurrent_processing(self):
        """Test concurrent processing of multiple adventures."""
        integration = AdventureImageIntegration(
            image_processor=Mock(),
            enhanced_placer=Mock(),
            content_aware_strategy=Mock(),
            gallery_processor=Mock(),
        )

        # Create multiple adventure contents
        adventures = [
            {"name": f"Adventure {i}", "data": {"chapter": []}} for i in range(3)
        ]

        rendering_context = Mock(spec=RenderingContext)

        # Mock successful discovery and generation
        with (
            patch.object(integration, "_discover_adventure_images") as mock_discover,
            patch.object(
                integration, "_generate_integrated_adventure_latex"
            ) as mock_generate,
        ):
            mock_discover.return_value = Success([])
            mock_generate.return_value = Success("\\test")

            # Process adventures concurrently
            tasks = [
                integration.integrate_adventure_images(adventure, rendering_context)
                for adventure in adventures
            ]

            results = await asyncio.gather(*tasks)

            # All should succeed
            assert all(isinstance(result, Success) for result in results)
            assert len(results) == 3


@pytest.mark.requires_data
class TestAdventureImageIntegrationWithData:
    """Integration tests with real data (slower, marked for optional execution)."""

    def setup_method(self):
        reset_test_environment()

    @pytest.mark.asyncio
    async def test_real_adventure_processing(self):
        """Test with realistic adventure data structure."""
        # This would use actual 5etools adventure data
        # Skip if no data available
        pytest.skip("Requires real adventure data")

    def test_large_adventure_handling(self):
        """Test handling of large adventures with many chapters."""
        # This would test performance with large datasets
        pytest.skip("Requires performance test data")

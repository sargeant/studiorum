"""Comprehensive tests for Phase 3 Content Integration components.

This test module covers:
- GalleryProcessor multi-image layout functionality
- RecursiveEntryProcessor gallery entry handling
- BestiaryImageIntegration creature statblock integration
- ItemImageIntegration magic item collection processing
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from studiorum.core.models.entry_types import GalleryEntry
from studiorum.core.result import Error, Success
from studiorum.latex_engine.core.entry_processor import RecursiveEntryProcessor
from studiorum.latex_engine.core.images.gallery_processor import (
    GalleryConfig,
    GalleryLayout,
    GalleryProcessor,
    ProcessedGallery,
)
from studiorum.latex_engine.core.images.image_processor import (
    ImageProcessingConfig,
    ImageProcessor,
)
from studiorum.latex_engine.core.images.integration.bestiary import (
    BestiaryImageIntegration,
    BestiaryImageResult,
    BestiaryIntegrationConfig,
    CreatureImageMetadata,
)
from studiorum.latex_engine.core.images.integration.items import (
    ItemImageIntegration,
    ItemImageMetadata,
    ItemImageResult,
    ItemIntegrationConfig,
)
from studiorum.renderers.core.interfaces import RenderingContext
from tests.test_helpers import reset_test_environment


class TestGalleryEntry:
    """Test the GalleryEntry Pydantic model."""

    def setup_method(self):
        reset_test_environment()

    def test_gallery_entry_creation(self):
        """Test creating a gallery entry with proper validation."""
        gallery_data = {
            "type": "gallery",
            "images": [
                {
                    "href": {"type": "external", "path": "image1.webp"},
                    "title": "First Image",
                },
                {
                    "href": {"type": "external", "path": "image2.webp"},
                    "title": "Second Image",
                },
            ],
            "layout": "grid",
            "caption": "Test gallery",
            "columns": 2,
        }

        gallery = GalleryEntry(**gallery_data)

        assert gallery.type == "gallery"
        assert len(gallery.images) == 2
        assert gallery.layout == "grid"
        assert gallery.caption == "Test gallery"
        assert gallery.columns == 2

    def test_gallery_entry_defaults(self):
        """Test gallery entry with default values."""
        gallery = GalleryEntry()

        assert gallery.type == "gallery"
        assert gallery.images == []
        assert gallery.layout is None
        assert gallery.caption is None
        assert gallery.columns is None

    def test_gallery_entry_validation(self):
        """Test gallery entry field validation."""
        with pytest.raises(ValueError):
            # Invalid columns (too high)
            GalleryEntry(columns=10)

        with pytest.raises(ValueError):
            # Invalid columns (too low)
            GalleryEntry(columns=0)


class TestGalleryProcessor:
    """Test the GalleryProcessor functionality."""

    def setup_method(self):
        reset_test_environment()
        self.mock_image_processor = Mock(spec=ImageProcessor)
        self.config = GalleryConfig()
        self.processor = GalleryProcessor(
            config=self.config, image_processor=self.mock_image_processor
        )
        self.context = RenderingContext(
            output_format="latex",
            metadata={"include_images": True},
        )

    def test_gallery_processor_initialization(self):
        """Test gallery processor initialization."""
        processor = GalleryProcessor()

        assert processor.config.default_layout == GalleryLayout.GRID
        assert processor.config.default_columns == 2
        assert processor._image_processor is None

    def test_process_empty_gallery(self):
        """Test processing empty gallery returns error."""
        gallery_entry = {"type": "gallery", "images": []}

        result = self.processor.process_gallery(gallery_entry, self.context)

        assert result.is_error()
        assert "contains no images" in str(result.error)  # type: ignore[attr-defined]

    def test_process_gallery_basic(self):
        """Test basic gallery processing with mock image processor."""
        # Mock image processor to return LaTeX
        self.mock_image_processor.process_image_entry.return_value = (
            "\\includegraphics[width=\\textwidth]{test.png}"
        )

        gallery_entry = {
            "type": "gallery",
            "images": [
                {"href": {"path": "image1.png"}, "title": "Image 1"},
                {"href": {"path": "image2.png"}, "title": "Image 2"},
            ],
            "layout": "grid",
            "caption": "Test Gallery",
        }

        result = self.processor.process_gallery(gallery_entry, self.context)

        assert result.is_success()
        processed = result.unwrap()
        assert isinstance(processed, ProcessedGallery)
        assert processed.layout_used == GalleryLayout.GRID
        assert processed.image_count == 2
        assert "\\begin{figure}" in processed.latex_command
        assert "Test Gallery" in processed.latex_command

    def test_determine_layout(self):
        """Test layout determination logic."""
        # Test known layouts
        assert (
            self.processor._determine_layout({"layout": "grid"}) == GalleryLayout.GRID
        )
        assert (
            self.processor._determine_layout({"layout": "showcase"})
            == GalleryLayout.SHOWCASE
        )
        assert (
            self.processor._determine_layout({"layout": "sequential"})
            == GalleryLayout.SEQUENTIAL
        )
        assert (
            self.processor._determine_layout({"layout": "comparison"})
            == GalleryLayout.COMPARISON
        )

        # Test unknown layout falls back to default
        assert (
            self.processor._determine_layout({"layout": "unknown"})
            == GalleryLayout.GRID
        )
        assert self.processor._determine_layout({}) == GalleryLayout.GRID

    def test_process_gallery_image_success(self):
        """Test successful individual image processing."""
        self.mock_image_processor.process_image_entry.return_value = (
            "\\includegraphics[width=\\textwidth]{test.png}"
        )

        image_data = {"href": {"path": "test.png"}, "title": "Test Image"}

        result = self.processor._process_gallery_image(image_data, self.context, 0)

        assert result.is_success()
        processed = result.unwrap()
        assert processed["title"] == "Test Image"
        assert processed["index"] == 0

    def test_process_gallery_image_fallback(self):
        """Test image processing fallback when no image processor available."""
        processor = GalleryProcessor()  # No image processor
        image_data = {"href": {"path": "test.png"}, "title": "Test Image"}

        result = processor._process_gallery_image(image_data, self.context, 0)

        assert result.is_success()
        processed = result.unwrap()
        assert "subfigure" in processed["latex_command"]

    def test_generate_grid_layout(self):
        """Test grid layout generation."""
        processed_images = [
            {"latex_command": "\\includegraphics{img1.png}", "title": "Image 1"},
            {"latex_command": "\\includegraphics{img2.png}", "title": "Image 2"},
        ]
        gallery_entry = {"columns": 2, "caption": "Grid Gallery"}

        result = self.processor._generate_grid_layout(processed_images, gallery_entry)

        assert result.is_success()
        latex = result.unwrap()
        assert "\\begin{figure}[htbp]" in latex
        assert "Grid Gallery" in latex
        assert "subfigure" in latex

    def test_generate_showcase_layout(self):
        """Test showcase layout generation."""
        processed_images = [
            {"latex_command": "\\includegraphics{main.png}", "title": "Main Image"},
            {"latex_command": "\\includegraphics{thumb1.png}", "title": "Thumb 1"},
            {"latex_command": "\\includegraphics{thumb2.png}", "title": "Thumb 2"},
        ]
        gallery_entry = {"caption": "Showcase Gallery"}

        result = self.processor._generate_showcase_layout(
            processed_images, gallery_entry
        )

        assert result.is_success()
        latex = result.unwrap()
        assert "0.7\\textwidth" in latex  # Main image width
        assert "0.15\\textwidth" in latex  # Thumbnail width
        assert "Showcase Gallery" in latex

    def test_generate_sequential_layout(self):
        """Test sequential layout generation."""
        processed_images = [
            {"latex_command": "\\includegraphics{img1.png}", "title": "Image 1"},
            {"latex_command": "\\includegraphics{img2.png}", "title": "Image 2"},
        ]
        gallery_entry = {"caption": "Sequential Gallery"}

        result = self.processor._generate_sequential_layout(
            processed_images, gallery_entry
        )

        assert result.is_success()
        latex = result.unwrap()
        assert "0.8\\textwidth" in latex  # Sequential image width
        assert "Sequential Gallery" in latex
        assert latex.count("\\begin{subfigure}") == 2

    def test_generate_comparison_layout(self):
        """Test comparison layout generation."""
        processed_images = [
            {"latex_command": "\\includegraphics{before.png}", "title": "Before"},
            {"latex_command": "\\includegraphics{after.png}", "title": "After"},
        ]
        gallery_entry = {"caption": "Comparison Gallery"}

        result = self.processor._generate_comparison_layout(
            processed_images, gallery_entry
        )

        assert result.is_success()
        latex = result.unwrap()
        assert "\\hfill" in latex  # Images side by side
        assert "Comparison Gallery" in latex

    def test_extract_image_command(self):
        """Test extracting includegraphics command from LaTeX."""
        latex_with_figure = """\\begin{figure}[htbp]
    \\centering
    \\includegraphics[width=0.5\\textwidth]{image.png}
    \\caption{Test}
\\end{figure}"""

        result = self.processor._extract_image_command(latex_with_figure)
        assert result == "\\includegraphics[width=0.5\\textwidth]{image.png}"

        # Test with just includegraphics
        just_includegraphics = "\\includegraphics[width=0.8\\textwidth]{test.png}"
        result = self.processor._extract_image_command(just_includegraphics)
        assert result == just_includegraphics

    def test_get_required_packages(self):
        """Test required LaTeX packages identification."""
        packages = self.processor._get_required_packages(GalleryLayout.GRID)
        assert "graphicx" in packages
        assert "subcaption" in packages
        assert "calc" in packages  # For grid layout


class TestRecursiveEntryProcessorGallery:
    """Test gallery processing integration in RecursiveEntryProcessor."""

    def setup_method(self):
        reset_test_environment()
        self.mock_image_processor = Mock(spec=ImageProcessor)
        self.processor = RecursiveEntryProcessor(
            image_processor=self.mock_image_processor
        )
        self.context = RenderingContext(
            output_format="latex",
            metadata={"include_images": True},
        )

    def test_process_gallery_entry(self):
        """Test processing gallery entry through entry processor."""
        gallery_entry = {
            "type": "gallery",
            "images": [
                {"href": {"path": "img1.png"}, "title": "Image 1"},
                {"href": {"path": "img2.png"}, "title": "Image 2"},
            ],
            "layout": "grid",
        }

        result = self.processor.process_entry_dict(gallery_entry, self.context)

        assert isinstance(result, str)
        assert len(result) > 0
        # Should contain LaTeX gallery structure
        assert "\\begin{figure}" in result or "subfigure" in result

    def test_process_gallery_images_disabled(self):
        """Test gallery processing when images are disabled."""
        context_no_images = RenderingContext(
            output_format="latex",
            metadata={"include_images": False},
        )

        gallery_entry = {
            "type": "gallery",
            "images": [{"href": {"path": "img.png"}, "title": "Image"}],
            "title": "Test Gallery",
        }

        result = self.processor.process_entry_dict(gallery_entry, context_no_images)

        assert "% Gallery placeholder: Test Gallery" in result

    def test_process_gallery_basic_fallback(self):
        """Test basic gallery processing fallback."""
        gallery_entry = {
            "type": "gallery",
            "images": [
                {"href": {"path": "img1.png"}, "title": "Image 1"},
                {"href": {"path": "img2.png"}, "title": "Image 2"},
            ],
            "caption": "Fallback Gallery",
        }

        # Mock gallery processor to fail, forcing fallback
        with patch.object(self.processor, "_get_gallery_processor", return_value=None):
            result = self.processor._process_gallery_basic(gallery_entry, self.context)

        assert "\\begin{figure}[htbp]" in result
        assert "Fallback Gallery" in result
        assert "subfigure" in result

    def test_get_gallery_processor(self):
        """Test gallery processor lazy initialization."""
        # First call should create processor
        processor = self.processor._get_gallery_processor()
        assert processor is not None

        # Second call should return same instance
        processor2 = self.processor._get_gallery_processor()
        assert processor is processor2


class TestBestiaryImageIntegration:
    """Test bestiary-specific image integration."""

    def setup_method(self):
        reset_test_environment()
        self.config = BestiaryIntegrationConfig()
        self.mock_image_processor = Mock(spec=ImageProcessor)
        self.mock_enhanced_placer = AsyncMock()
        self.integration = BestiaryImageIntegration(
            config=self.config,
            image_processor=self.mock_image_processor,
            enhanced_placer=self.mock_enhanced_placer,
        )
        self.context = RenderingContext(output_format="latex", metadata={})

    def test_bestiary_integration_initialization(self):
        """Test bestiary integration initialization."""
        integration = BestiaryImageIntegration()

        assert integration.config.enable_creature_portraits is True
        assert integration.config.max_images_per_creature == 3
        assert integration._image_processor is None

    @pytest.mark.asyncio
    async def test_integrate_creature_images_success(self):
        """Test successful creature image integration."""
        creature_data = {
            "name": "Ancient Red Dragon",
            "type": "dragon",
            "cr": "24",
            "size": "Gargantuan",
            "environment": ["mountains", "caves"],
        }

        # Mock image discovery
        mock_images = [
            {
                "href": {"path": "dragon_portrait.webp"},
                "title": "Ancient Red Dragon",
                "type": "portrait",
                "confidence": 0.9,
            }
        ]

        with patch.object(
            self.integration, "_discover_creature_images"
        ) as mock_discover:
            mock_discover.return_value = Success(mock_images)

            with patch.object(
                self.integration, "_generate_integrated_latex"
            ) as mock_generate:
                mock_generate.return_value = Success("\\includegraphics{dragon.png}")

                result = await self.integration.integrate_creature_images(
                    creature_data, self.context
                )

        assert result.is_success()
        processed = result.unwrap()
        assert isinstance(processed, BestiaryImageResult)
        assert processed.images_processed == 1
        assert "Ancient Red Dragon" in processed.integration_metadata["creature_name"]

    @pytest.mark.asyncio
    async def test_integrate_creature_images_no_images(self):
        """Test creature integration with no available images."""
        creature_data = {"name": "Goblin", "type": "humanoid"}

        with patch.object(
            self.integration, "_discover_creature_images"
        ) as mock_discover:
            mock_discover.return_value = Success([])

            result = await self.integration.integrate_creature_images(
                creature_data, self.context
            )

        assert result.is_success()
        processed = result.unwrap()
        assert processed.images_processed == 0
        assert processed.placement_strategy == "none"

    @pytest.mark.asyncio
    async def test_discover_creature_images(self):
        """Test creature image discovery logic."""
        creature_data = {
            "name": "Owlbear",
            "type": "monstrosity",
            "environment": ["forest"],
        }

        result = await self.integration._discover_creature_images(
            creature_data, self.context
        )

        assert result.is_success()
        images = result.unwrap()
        assert len(images) >= 1  # Should find at least portrait

        # Check portrait image
        portrait = next((img for img in images if img["type"] == "portrait"), None)
        assert portrait is not None
        assert "owlbear" in portrait["href"]["path"].lower()

    def test_categorize_creature_images(self):
        """Test creature image categorization."""
        images = [
            {"type": "portrait", "confidence": 0.8},
            {"type": "environment", "confidence": 0.6},
            {"type": "action", "confidence": 0.7},
        ]
        creature_data = {"name": "Dragon", "type": "dragon", "cr": "15"}

        categorized = self.integration._categorize_creature_images(
            images, creature_data
        )

        assert "portrait" in categorized
        assert "environment" in categorized
        assert "action" in categorized
        assert len(categorized["portrait"]) == 1
        assert len(categorized["environment"]) == 1
        assert len(categorized["action"]) == 1

    def test_select_optimal_images(self):
        """Test optimal image selection logic."""
        categorized = {
            "portrait": [
                {"confidence": 0.9, "type": "portrait"},
                {"confidence": 0.7, "type": "portrait"},
            ],
            "environment": [
                {"confidence": 0.6, "type": "environment"},
                {"confidence": 0.8, "type": "environment"},
            ],
            "action": [],
        }
        creature_data = {"name": "Test Creature"}

        selected = self.integration._select_optimal_images(
            categorized, creature_data, self.context
        )

        # Should select highest confidence portrait and up to 2 environments
        assert len(selected) <= self.config.max_images_per_creature
        assert selected[0]["confidence"] == 0.9  # Best portrait
        assert any(img["confidence"] == 0.8 for img in selected)  # Best environment

    @pytest.mark.asyncio
    async def test_generate_integrated_latex(self):
        """Test integrated LaTeX generation."""
        selected_images = [
            {"type": "portrait", "href": {"path": "dragon.png"}, "title": "Dragon"}
        ]
        creature_data = {"name": "Dragon", "type": "dragon"}

        # Mock enhanced placement
        self.mock_enhanced_placer.place_image_enhanced.return_value = Success(
            Mock(latex_command="\\includegraphics{enhanced.png}")
        )

        result = await self.integration._generate_integrated_latex(
            selected_images, creature_data, self.context
        )

        assert result.is_success()
        latex = result.unwrap()
        assert isinstance(latex, str)
        assert len(latex) > 0

    def test_create_bestiary_context(self):
        """Test bestiary content context creation."""
        creature_data = {
            "name": "Tarrasque",
            "type": "monstrosity",
            "cr": "30",
        }
        image = {"type": "portrait"}

        context = self.integration._create_bestiary_context(creature_data, image)

        assert context["type"] == "bestiary"
        assert context["creature_name"] == "Tarrasque"
        assert context["creature_type"] == "monstrosity"
        assert context["challenge_rating"] == "30"
        assert context["image_type"] == "portrait"

    def test_create_basic_creature_image_latex(self):
        """Test basic creature image LaTeX creation."""
        image = {
            "href": {"path": "creature.png"},
            "title": "Test Creature",
        }

        latex = self.integration._create_basic_creature_image_latex(image, "portrait")

        assert "\\begin{figure}" in latex
        assert "Test Creature" in latex
        assert "creature.png" in latex
        assert self.config.portrait_max_width in latex

    def test_get_integration_statistics(self):
        """Test integration statistics retrieval."""
        stats = self.integration.get_integration_statistics()

        assert "config" in stats
        assert "has_image_processor" in stats
        assert "has_enhanced_placer" in stats
        assert stats["has_image_processor"] is True
        assert stats["has_enhanced_placer"] is True


class TestItemImageIntegration:
    """Test item-specific image integration."""

    def setup_method(self):
        reset_test_environment()
        self.config = ItemIntegrationConfig()
        self.mock_image_processor = Mock(spec=ImageProcessor)
        self.mock_gallery_processor = Mock()
        self.mock_enhanced_placer = AsyncMock()
        self.integration = ItemImageIntegration(
            config=self.config,
            image_processor=self.mock_image_processor,
            gallery_processor=self.mock_gallery_processor,
            enhanced_placer=self.mock_enhanced_placer,
        )
        self.context = RenderingContext(output_format="latex", metadata={})

    def test_item_integration_initialization(self):
        """Test item integration initialization."""
        integration = ItemImageIntegration()

        assert integration.config.enable_item_illustrations is True
        assert integration.config.max_items_per_gallery == 6
        assert integration._image_processor is None

    @pytest.mark.asyncio
    async def test_integrate_item_collection_success(self):
        """Test successful item collection integration."""
        items_data = [
            {
                "name": "Flame Tongue",
                "type": "weapon",
                "rarity": "rare",
            },
            {
                "name": "Ring of Protection",
                "type": "ring",
                "rarity": "rare",
            },
        ]
        collection_metadata = {"name": "Magic Items"}

        # Mock successful gallery processing
        mock_processed_gallery = Mock()
        mock_processed_gallery.latex_command = "\\begin{figure}Gallery\\end{figure}"
        self.mock_gallery_processor.process_gallery.return_value = Success(
            mock_processed_gallery
        )

        with patch.object(self.integration, "_discover_item_images") as mock_discover:
            mock_discover.side_effect = [
                Success([{"name": "flame_tongue", "type": "illustration"}]),
                Success([{"name": "ring_protection", "type": "illustration"}]),
            ]

            result = await self.integration.integrate_item_collection(
                items_data, self.context, collection_metadata
            )

        assert result.is_success()
        processed = result.unwrap()
        assert isinstance(processed, ItemImageResult)
        assert processed.layout_used in ["categorized", "unified"]
        assert "Magic Items" in processed.integration_metadata["collection_name"]

    @pytest.mark.asyncio
    async def test_integrate_single_item_success(self):
        """Test successful single item integration."""
        item_data = {
            "name": "Vorpal Sword",
            "type": "weapon",
            "rarity": "legendary",
        }

        with patch.object(self.integration, "_discover_item_images") as mock_discover:
            mock_images = [
                {
                    "href": {"path": "vorpal_sword.png"},
                    "title": "Vorpal Sword",
                    "type": "illustration",
                    "confidence": 0.9,
                }
            ]
            mock_discover.return_value = Success(mock_images)

            with patch.object(
                self.integration, "_generate_single_item_latex"
            ) as mock_generate:
                mock_generate.return_value = Success("\\includegraphics{sword.png}")

                result = await self.integration.integrate_single_item(
                    item_data, self.context
                )

        assert result.is_success()
        processed = result.unwrap()
        assert processed.items_processed == 1
        assert processed.layout_used == "single"

    @pytest.mark.asyncio
    async def test_discover_item_images(self):
        """Test item image discovery logic."""
        item_data = {
            "name": "Bag of Holding",
            "type": "wondrous item",
            "rarity": "uncommon",
        }

        result = await self.integration._discover_item_images(item_data, self.context)

        assert result.is_success()
        images = result.unwrap()
        assert len(images) >= 1  # Should find at least illustration

        # Check illustration image
        illustration = next(
            (img for img in images if img["type"] == "illustration"), None
        )
        assert illustration is not None
        assert "bag_of_holding" in illustration["href"]["path"].lower()

    def test_categorize_item(self):
        """Test item categorization logic."""
        # Test weapon
        weapon_data = {"type": "weapon (longsword)"}
        assert self.integration._categorize_item(weapon_data) == "weapons"

        # Test armor
        armor_data = {"type": "armor (chain mail)"}
        assert self.integration._categorize_item(armor_data) == "armor"

        # Test wondrous item
        wondrous_data = {"type": "wondrous item"}
        assert self.integration._categorize_item(wondrous_data) == "wondrous_items"

        # Test unknown type
        unknown_data = {"type": "mysterious object"}
        assert self.integration._categorize_item(unknown_data) == "miscellaneous"

    def test_select_optimal_item_image(self):
        """Test optimal item image selection."""
        available_images = [
            {"type": "illustration", "confidence": 0.8},
            {"type": "variant", "confidence": 0.9},
            {"type": "illustration", "confidence": 0.6},
        ]
        item_data = {"name": "Test Item"}

        selected = self.integration._select_optimal_item_image(
            available_images, item_data, self.context
        )

        # Should prefer illustration over variant, with highest confidence
        assert selected["type"] == "illustration"
        assert selected["confidence"] == 0.8

    @pytest.mark.asyncio
    async def test_create_categorized_galleries(self):
        """Test categorized gallery creation."""
        item_images = [
            {
                "item_metadata": {
                    "category": "weapons",
                    "item_name": "Sword",
                },
                "href": {"path": "sword.png"},
            },
            {
                "item_metadata": {
                    "category": "armor",
                    "item_name": "Shield",
                },
                "href": {"path": "shield.png"},
            },
        ]
        items_data = []
        collection_metadata = {"name": "Test Collection"}

        # Mock gallery processor success
        mock_gallery = Mock()
        mock_gallery.latex_command = "\\begin{figure}Category Gallery\\end{figure}"
        self.mock_gallery_processor.process_gallery.return_value = Success(mock_gallery)

        result = await self.integration._create_categorized_galleries(
            item_images, items_data, self.context, collection_metadata
        )

        assert result.is_success()
        latex = result.unwrap()
        assert isinstance(latex, str)
        assert len(latex) > 0

    @pytest.mark.asyncio
    async def test_create_unified_gallery(self):
        """Test unified gallery creation."""
        item_images = [
            {"href": {"path": "item1.png"}, "title": "Item 1"},
            {"href": {"path": "item2.png"}, "title": "Item 2"},
        ]
        items_data = []
        collection_metadata = {"name": "Unified Collection"}

        # Mock gallery processor success
        mock_gallery = Mock()
        mock_gallery.latex_command = "\\begin{figure}Unified Gallery\\end{figure}"
        self.mock_gallery_processor.process_gallery.return_value = Success(mock_gallery)

        result = await self.integration._create_unified_gallery(
            item_images, items_data, self.context, collection_metadata
        )

        assert result.is_success()
        latex = result.unwrap()
        assert "Unified Gallery" in latex

    def test_create_item_context(self):
        """Test item content context creation."""
        item_data = {
            "name": "Holy Avenger",
            "type": "weapon",
            "rarity": "legendary",
        }
        image = {"type": "illustration"}

        context = self.integration._create_item_context(item_data, image, "inline")

        assert context["type"] == "item_collection"
        assert context["item_name"] == "Holy Avenger"
        assert context["item_type"] == "weapon"
        assert context["rarity"] == "legendary"
        assert context["reading_flow_position"] == "inline"

    def test_create_basic_item_latex(self):
        """Test basic item LaTeX creation."""
        image = {
            "href": {"path": "legendary_item.png"},
            "title": "Legendary Artifact",
        }
        item_data = {"rarity": "legendary"}

        latex = self.integration._create_basic_item_latex(image, item_data)

        assert "\\begin{figure}" in latex
        assert "Legendary Artifact" in latex
        assert "legendary_item.png" in latex
        # Should use larger width for legendary items if rarity sizing enabled
        if self.config.enable_rarity_sizing:
            assert "0.5\\textwidth" in latex

    def test_create_basic_item_gallery(self):
        """Test basic item gallery creation."""
        images = [
            {"href": {"path": "item1.png"}, "title": "Item 1"},
            {"href": {"path": "item2.png"}, "title": "Item 2"},
        ]

        latex = self.integration._create_basic_item_gallery(
            images, "weapons", self.context
        )

        assert "\\begin{figure}[htbp]" in latex
        assert "weapons" in latex
        assert "subfigure" in latex
        assert latex.count("\\begin{subfigure}") == 2

    def test_extract_categories(self):
        """Test category extraction from images."""
        images = [
            {"item_metadata": {"category": "weapons"}},
            {"item_metadata": {"category": "armor"}},
            {"item_metadata": {"category": "weapons"}},  # Duplicate
            {"item_metadata": {}},  # No category
        ]

        categories = self.integration._extract_categories(images)

        assert len(categories) == 2
        assert "weapons" in categories
        assert "armor" in categories

    def test_get_integration_statistics(self):
        """Test integration statistics retrieval."""
        stats = self.integration.get_integration_statistics()

        assert "config" in stats
        assert "has_image_processor" in stats
        assert "has_gallery_processor" in stats
        assert "has_enhanced_placer" in stats
        assert stats["has_image_processor"] is True
        assert stats["has_gallery_processor"] is True
        assert stats["has_enhanced_placer"] is True


class TestPhase3Integration:
    """Integration tests for Phase 3 components working together."""

    def setup_method(self):
        reset_test_environment()
        self.mock_image_processor = Mock(spec=ImageProcessor)
        self.context = RenderingContext(
            output_format="latex",
            metadata={"include_images": True},
        )

    def test_end_to_end_gallery_processing(self):
        """Test complete gallery processing from entry to LaTeX."""
        # Create entry processor with image processor
        entry_processor = RecursiveEntryProcessor(
            image_processor=self.mock_image_processor
        )

        # Mock image processor responses
        self.mock_image_processor.process_image_entry.return_value = (
            "\\includegraphics[width=\\textwidth]{test.png}"
        )

        # Create gallery entry
        gallery_entry = {
            "type": "gallery",
            "images": [
                {"href": {"path": "dragon1.png"}, "title": "Ancient Dragon"},
                {"href": {"path": "dragon2.png"}, "title": "Young Dragon"},
            ],
            "layout": "comparison",
            "caption": "Dragon Age Comparison",
        }

        # Process the gallery
        result = entry_processor.process_entry_dict(gallery_entry, self.context)

        assert isinstance(result, str)
        assert "\\begin{figure}" in result
        assert "Dragon Age Comparison" in result
        assert "subfigure" in result

    @pytest.mark.asyncio
    async def test_bestiary_with_gallery_integration(self):
        """Test bestiary integration potentially using gallery layouts."""
        bestiary_integration = BestiaryImageIntegration()

        # Mock creature with multiple images (could trigger gallery)
        creature_data = {
            "name": "Chromatic Dragon",
            "type": "dragon",
            "cr": "20",
            "environment": ["mountains", "caves", "lairs"],
        }

        # Simulate discovery of multiple images
        with patch.object(
            bestiary_integration, "_discover_creature_images"
        ) as mock_discover:
            mock_images = [
                {"type": "portrait", "confidence": 0.9},
                {"type": "environment", "confidence": 0.7},
                {"type": "action", "confidence": 0.8},
            ]
            mock_discover.return_value = Success(mock_images)

            with patch.object(
                bestiary_integration, "_generate_integrated_latex"
            ) as mock_generate:
                mock_generate.return_value = Success(
                    "\\begin{figure}Multiple dragon images\\end{figure}"
                )

                result = await bestiary_integration.integrate_creature_images(
                    creature_data, self.context
                )

        assert result.is_success()
        processed = result.unwrap()
        assert processed.images_processed == 3  # All images selected

    @pytest.mark.asyncio
    async def test_item_collection_with_gallery_layout(self):
        """Test item collection using gallery processor."""
        # Create item integration with gallery processor
        mock_gallery_processor = Mock()
        mock_gallery = Mock()
        mock_gallery.latex_command = "\\begin{figure}Magic Item Collection\\end{figure}"
        mock_gallery_processor.process_gallery.return_value = Success(mock_gallery)

        item_integration = ItemImageIntegration(
            gallery_processor=mock_gallery_processor
        )

        # Create collection of magical weapons
        items_data = [
            {"name": "Flame Tongue", "type": "weapon", "rarity": "rare"},
            {"name": "Frost Brand", "type": "weapon", "rarity": "very rare"},
            {"name": "Vorpal Sword", "type": "weapon", "rarity": "legendary"},
        ]

        with patch.object(item_integration, "_discover_item_images") as mock_discover:
            # Each item has an image
            mock_discover.side_effect = [
                Success([{"type": "illustration", "confidence": 0.8}]),
                Success([{"type": "illustration", "confidence": 0.9}]),
                Success([{"type": "illustration", "confidence": 0.7}]),
            ]

            result = await item_integration.integrate_item_collection(
                items_data, self.context, {"name": "Magical Weapons"}
            )

        assert result.is_success()
        processed = result.unwrap()
        assert "Magic Item Collection" in processed.latex_command
        assert processed.integration_metadata["collection_name"] == "Magical Weapons"

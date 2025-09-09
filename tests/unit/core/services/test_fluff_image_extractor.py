"""Tests for FluffImageExtractor service."""

from unittest.mock import Mock

import pytest

from studiorum.core.models.content import Source
from studiorum.core.models.fluff import BaseFluff, FluffEntry, FluffImage
from studiorum.core.services.fluff_image_extractor import (
    FluffImageExtractor,
    FluffImageInfo,
)


@pytest.fixture
def mock_omnidexer():
    """Create a mock omnidexer."""
    return Mock()


@pytest.fixture
def sample_fluff_with_images():
    """Create sample fluff content with images."""
    source = Source(abbreviation="MM", full_name="Monster Manual")

    # Create images in the images field
    # Use dict format since BaseFluff.parse_images expects dicts
    images = [
        {
            "type": "image",
            "href": {"path": "creatures/dragon.jpg"},
            "credit": "Wizards of the Coast",
        },
        {"type": "illustration", "href": {"path": "maps/dragon-lair.png"}},
    ]

    # Create entries with embedded image references
    # Use dict format since BaseFluff.parse_entries expects dicts
    entries = [
        {
            "name": "Description",
            "content": "A fearsome dragon {@img creatures/dragon-breath.png} breathes fire.",
        },
        {
            "type": "image",
            "href": {"path": "creatures/dragon-variant.jpg"},
            "credit": "Fan Art",
        },
        {
            "name": "Lore",
            "content": "See artwork at https://example.com/dragon.jpg for reference.",
        },
    ]

    return BaseFluff(
        name="Ancient Red Dragon", source=source, entries=entries, images=images
    )


class TestFluffImageInfo:
    """Test FluffImageInfo class."""

    def test_basic_properties(self):
        """Test basic FluffImageInfo properties."""
        info = FluffImageInfo(
            path="creatures/dragon.jpg",
            credit="WotC",
            image_type="image",
            source_fluff="Ancient Red Dragon",
            source_abbreviation="MM",
        )

        assert info.path == "creatures/dragon.jpg"
        assert info.filename == "dragon.jpg"
        assert info.extension == ".jpg"
        assert info.is_supported_format() is True

    def test_unsupported_format(self):
        """Test unsupported image format detection."""
        info = FluffImageInfo(path="document.pdf")
        assert info.extension == ".pdf"
        assert info.is_supported_format() is False

    def test_to_dict(self):
        """Test conversion to dictionary."""
        info = FluffImageInfo(
            path="creatures/dragon.png",
            credit="Artist Name",
            alt_text="Dragon illustration",
        )

        result = info.to_dict()

        assert result["path"] == "creatures/dragon.png"
        assert result["credit"] == "Artist Name"
        assert result["alt_text"] == "Dragon illustration"
        assert result["filename"] == "dragon.png"
        assert result["extension"] == ".png"
        assert result["supported"] is True


class TestFluffImageExtractor:
    """Test FluffImageExtractor service."""

    def setup_method(self):
        """Set up test fixtures."""
        from studiorum.core.services.container import ServiceContainer

        ServiceContainer.reset_global_instance()

    def test_extract_from_images_field(self, mock_omnidexer, sample_fluff_with_images):
        """Test extracting images from the dedicated images field."""
        extractor = FluffImageExtractor(mock_omnidexer)

        images = extractor.extract_images_from_fluff(sample_fluff_with_images)

        # Should find all images: 2 from images field + 1 from image entry + 1 embedded + 1 URL
        assert len(images) == 5

        # Should find 2 images specifically from the images field (source_fluff context indicates they came from images field)
        # Plus 1 from an entry with type="image"
        images_field_count = sum(
            1 for img in images if img.image_type in ["image", "illustration"]
        )
        assert images_field_count == 3

        # Check first image details
        dragon_image = next(img for img in images if "dragon.jpg" in img.path)
        assert dragon_image.credit == "Wizards of the Coast"
        assert dragon_image.source_fluff == "Ancient Red Dragon"
        assert dragon_image.source_abbreviation == "MM"

    def test_extract_from_entry_references(
        self, mock_omnidexer, sample_fluff_with_images
    ):
        """Test extracting images from entry content."""
        extractor = FluffImageExtractor(mock_omnidexer)

        images = extractor.extract_images_from_fluff(sample_fluff_with_images)

        # Should find embedded image reference
        embedded_images = [img for img in images if img.image_type == "embedded"]
        assert len(embedded_images) >= 1

        breath_image = next(
            (img for img in embedded_images if "dragon-breath.png" in img.path), None
        )
        assert breath_image is not None
        assert breath_image.source_fluff == "Ancient Red Dragon"

    def test_extract_from_image_entries(self, mock_omnidexer, sample_fluff_with_images):
        """Test extracting images from image-type entries."""
        extractor = FluffImageExtractor(mock_omnidexer)

        images = extractor.extract_images_from_fluff(sample_fluff_with_images)

        # Should find image from entry with type="image"
        variant_image = next(
            (img for img in images if "dragon-variant.jpg" in img.path), None
        )
        assert variant_image is not None
        assert variant_image.credit == "Fan Art"

    def test_extract_url_images(self, mock_omnidexer, sample_fluff_with_images):
        """Test extracting images from URLs in text."""
        extractor = FluffImageExtractor(mock_omnidexer)

        images = extractor.extract_images_from_fluff(sample_fluff_with_images)

        # Should find URL image
        url_images = [img for img in images if img.image_type == "url"]
        assert len(url_images) >= 1

        url_image = next(
            (img for img in url_images if "example.com/dragon.jpg" in img.path), None
        )
        assert url_image is not None
        assert url_image.metadata.get("is_external_url") is True

    def test_alt_text_generation(self, mock_omnidexer):
        """Test automatic alt text generation."""
        source = Source(abbreviation="PHB", full_name="Player's Handbook")
        fluff = BaseFluff(
            name="Fireball",
            source=source,
            images=[
                {
                    "type": "image",
                    "href": {"path": "spells/fireball.png"},
                    "credit": "John Artist",
                }
            ],
        )

        extractor = FluffImageExtractor(mock_omnidexer)
        images = extractor.extract_images_from_fluff(fluff)

        assert len(images) == 1
        assert "Illustration for Fireball" in images[0].alt_text
        assert "John Artist" in images[0].alt_text

    def test_filter_images_by_type(self, mock_omnidexer):
        """Test filtering images by type."""
        extractor = FluffImageExtractor(mock_omnidexer)

        images = [
            FluffImageInfo(path="image1.jpg", image_type="image"),
            FluffImageInfo(path="image2.png", image_type="illustration"),
            FluffImageInfo(path="image3.gif", image_type="embedded"),
        ]

        filtered = extractor.filter_images_by_type(images, ["image", "illustration"])
        assert len(filtered) == 2
        assert all(img.image_type in ["image", "illustration"] for img in filtered)

    def test_filter_images_by_format(self, mock_omnidexer):
        """Test filtering images by format support."""
        extractor = FluffImageExtractor(mock_omnidexer)

        images = [
            FluffImageInfo(path="image1.jpg"),  # Supported
            FluffImageInfo(path="image2.png"),  # Supported
            FluffImageInfo(path="document.pdf"),  # Unsupported
            FluffImageInfo(path="video.mp4"),  # Unsupported
        ]

        supported = extractor.filter_images_by_format(images, supported_only=True)
        assert len(supported) == 2
        assert all(img.is_supported_format() for img in supported)

        all_images = extractor.filter_images_by_format(images, supported_only=False)
        assert len(all_images) == 4

    def test_image_statistics(self, mock_omnidexer):
        """Test image statistics generation."""
        extractor = FluffImageExtractor(mock_omnidexer)

        images = [
            FluffImageInfo(
                path="image1.jpg",
                image_type="image",
                source_abbreviation="MM",
                credit="Artist1",
                caption="Caption1",
            ),
            FluffImageInfo(
                path="image2.png",
                image_type="illustration",
                source_abbreviation="PHB",
                is_external_url=True,
            ),
            FluffImageInfo(
                path="document.pdf",  # Unsupported format
                image_type="image",
                source_abbreviation="MM",
            ),
        ]

        stats = extractor.get_image_statistics(images)

        assert stats["total_images"] == 3
        assert stats["by_type"]["image"] == 2
        assert stats["by_type"]["illustration"] == 1
        assert stats["by_format"][".jpg"] == 1
        assert stats["by_format"][".png"] == 1
        assert stats["by_format"][".pdf"] == 1
        assert stats["by_source"]["MM"] == 2
        assert stats["by_source"]["PHB"] == 1
        assert stats["supported_formats"] == 2
        assert stats["external_urls"] == 1
        assert stats["has_credits"] == 1
        assert stats["has_captions"] == 1

    def test_create_image_manifest(self, mock_omnidexer):
        """Test creation of image manifest."""
        extractor = FluffImageExtractor(mock_omnidexer)

        images = [
            FluffImageInfo(path="image1.jpg", image_type="image"),
            FluffImageInfo(path="image2.png", image_type="illustration"),
        ]

        manifest = extractor.create_image_manifest(images)

        assert manifest["version"] == "1.0.0"
        assert manifest["generated_by"] == "FluffImageExtractor"
        assert "statistics" in manifest
        assert "images" in manifest
        assert len(manifest["images"]) == 2
        assert manifest["statistics"]["total_images"] == 2

    def test_caption_extraction(self, mock_omnidexer):
        """Test caption extraction from text context."""
        extractor = FluffImageExtractor(mock_omnidexer)

        text = "Here is an image {@img dragon.jpg} showing a mighty dragon in flight."
        caption = extractor._extract_caption_near_image(text, text.find("{@img"))

        assert caption is not None
        assert "mighty dragon" in caption

    def test_empty_fluff_returns_no_images(self, mock_omnidexer):
        """Test that empty fluff returns no images."""
        source = Source(abbreviation="MM", full_name="Monster Manual")
        empty_fluff = BaseFluff(
            name="Empty Fluff", source=source, entries=[], images=[]
        )

        extractor = FluffImageExtractor(mock_omnidexer)
        images = extractor.extract_images_from_fluff(empty_fluff)

        assert len(images) == 0

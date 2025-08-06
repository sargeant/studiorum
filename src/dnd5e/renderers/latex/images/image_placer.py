"""Image placement and text wrapping for LaTeX documents."""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class ImagePlacement(str, Enum):
    """Image placement options for LaTeX."""

    INLINE = "inline"  # Inline with text
    FLOAT_HERE = "here"  # Float here if possible
    FLOAT_TOP = "top"  # Float to top of page
    FLOAT_BOTTOM = "bottom"  # Float to bottom of page
    FLOAT_PAGE = "page"  # Float to separate page
    WRAP_LEFT = "wrap-left"  # Wrap text around left side
    WRAP_RIGHT = "wrap-right"  # Wrap text around right side
    MARGIN = "margin"  # Place in margin
    FULL_WIDTH = "full-width"  # Span full page width


class ImageSize(str, Enum):
    """Standard image sizes for different content types."""

    SMALL = "small"  # Icons, small decorations
    MEDIUM = "medium"  # Standard content images
    LARGE = "large"  # Feature images
    FULL_COLUMN = "full-column"  # Full column width
    FULL_WIDTH = "full-width"  # Full page width
    PORTRAIT = "portrait"  # Tall images (creatures, NPCs)


class PlacementConfig(BaseModel):
    """Configuration for image placement."""

    default_placement: ImagePlacement = Field(default=ImagePlacement.FLOAT_HERE)
    default_size: ImageSize = Field(default=ImageSize.MEDIUM)
    enable_text_wrapping: bool = Field(default=True)
    enable_margin_images: bool = Field(default=False)
    caption_position: str = Field(default="bottom")  # "top", "bottom", "none"
    figure_separation: str = Field(default="12pt")
    wrap_lines: int = Field(default=10, description="Minimum lines for text wrapping")


class PlacementResult(BaseModel):
    """Result of image placement calculation."""

    latex_command: str
    placement: ImagePlacement
    size_spec: str
    requires_packages: list[str]
    caption: str | None = None


class ImagePlacer:
    """Handles intelligent image placement and text wrapping in LaTeX documents.

    Generates appropriate LaTeX commands for different image placement scenarios
    including floating figures, wrapped text, and margin images.
    """

    def __init__(self, config: PlacementConfig | None = None) -> None:
        """Initialize the image placer.

        Args:
            config: Placement configuration
        """
        self.config = config or PlacementConfig()

    def place_image(
        self,
        image_path: Path,
        image_entry: dict[str, Any],
        context_hint: str | None = None,
    ) -> PlacementResult:
        """Generate LaTeX placement command for an image.

        Args:
            image_path: Path to processed image file
            image_entry: Original image entry data
            context_hint: Context hint for placement strategy

        Returns:
            Placement result with LaTeX command
        """
        # Determine placement strategy
        placement = self._determine_placement(image_entry, context_hint)
        size_spec = self._determine_size_spec(image_entry, context_hint, placement)

        # Generate LaTeX command based on placement
        latex_command = self._generate_placement_command(
            image_path, image_entry, placement, size_spec
        )

        # Determine required packages
        required_packages = self._get_required_packages(placement)

        return PlacementResult(
            latex_command=latex_command,
            placement=placement,
            size_spec=size_spec,
            requires_packages=required_packages,
            caption=image_entry.get("title"),
        )

    def _determine_placement(
        self, image_entry: dict[str, Any], context_hint: str | None = None
    ) -> ImagePlacement:
        """Determine optimal image placement based on content and context.

        Args:
            image_entry: Image entry data
            context_hint: Context hint (creature, item, chapter-art, etc.)

        Returns:
            Optimal image placement
        """
        # Check for explicit placement hint in image entry
        if "placement" in image_entry:
            placement_str = image_entry["placement"].lower()
            for placement in ImagePlacement:
                if placement.value == placement_str:
                    return placement

        # Use context-based placement strategy
        if context_hint == "creature":
            # Creatures often benefit from wrapped placement
            return ImagePlacement.WRAP_RIGHT
        elif context_hint == "item":
            # Items can be smaller and wrapped
            return ImagePlacement.WRAP_LEFT
        elif context_hint == "chapter-art":
            # Chapter art should be prominent
            return ImagePlacement.FULL_WIDTH
        elif context_hint == "decoration":
            # Decorative elements can be in margins
            return (
                ImagePlacement.MARGIN
                if self.config.enable_margin_images
                else ImagePlacement.INLINE
            )
        else:
            # Use default placement
            return self.config.default_placement

    def _determine_size_spec(
        self,
        image_entry: dict[str, Any],
        context_hint: str | None = None,
        placement: ImagePlacement = ImagePlacement.FLOAT_HERE,
    ) -> str:
        """Determine LaTeX size specification for image.

        Args:
            image_entry: Image entry data
            context_hint: Context hint
            placement: Image placement

        Returns:
            LaTeX size specification
        """
        # Check for explicit size hint
        if "size" in image_entry:
            size_hint = image_entry["size"].lower()
            return self._size_hint_to_spec(size_hint, placement)

        # Use context-based sizing
        if context_hint == "creature":
            if placement in {ImagePlacement.WRAP_LEFT, ImagePlacement.WRAP_RIGHT}:
                return "0.4\\textwidth"
            else:
                return "0.6\\textwidth"
        elif context_hint == "item":
            return "0.3\\textwidth"
        elif context_hint == "chapter-art":
            return "\\textwidth"
        elif context_hint == "decoration":
            return "0.2\\textwidth"
        else:
            # Default sizing based on placement
            return self._default_size_for_placement(placement)

    def _size_hint_to_spec(self, size_hint: str, placement: ImagePlacement) -> str:
        """Convert size hint to LaTeX specification.

        Args:
            size_hint: Size hint string
            placement: Image placement

        Returns:
            LaTeX size specification
        """
        size_map = {
            "small": "0.2\\textwidth",
            "medium": "0.5\\textwidth",
            "large": "0.8\\textwidth",
            "full": "\\textwidth",
            "column": "\\columnwidth",
        }

        # Adjust for wrapped images (they need to be smaller)
        if placement in {ImagePlacement.WRAP_LEFT, ImagePlacement.WRAP_RIGHT}:
            wrap_size_map = {
                "small": "0.15\\textwidth",
                "medium": "0.35\\textwidth",
                "large": "0.5\\textwidth",
                "full": "0.6\\textwidth",
                "column": "0.45\\textwidth",
            }
            return wrap_size_map.get(size_hint, "0.4\\textwidth")

        return size_map.get(size_hint, "0.5\\textwidth")

    def _default_size_for_placement(self, placement: ImagePlacement) -> str:
        """Get default size specification for placement type.

        Args:
            placement: Image placement

        Returns:
            LaTeX size specification
        """
        size_map = {
            ImagePlacement.INLINE: "0.3\\textwidth",
            ImagePlacement.FLOAT_HERE: "0.6\\textwidth",
            ImagePlacement.FLOAT_TOP: "0.8\\textwidth",
            ImagePlacement.FLOAT_BOTTOM: "0.8\\textwidth",
            ImagePlacement.FLOAT_PAGE: "\\textwidth",
            ImagePlacement.WRAP_LEFT: "0.4\\textwidth",
            ImagePlacement.WRAP_RIGHT: "0.4\\textwidth",
            ImagePlacement.MARGIN: "0.2\\textwidth",
            ImagePlacement.FULL_WIDTH: "\\textwidth",
        }
        return size_map.get(placement, "0.5\\textwidth")

    def _generate_placement_command(
        self,
        image_path: Path,
        image_entry: dict[str, Any],
        placement: ImagePlacement,
        size_spec: str,
    ) -> str:
        """Generate LaTeX command for image placement.

        Args:
            image_path: Path to image file
            image_entry: Image entry data
            placement: Image placement
            size_spec: Size specification

        Returns:
            LaTeX command string
        """
        title = image_entry.get("title", "")
        label = self._generate_label(image_entry)

        if placement == ImagePlacement.INLINE:
            return self._generate_inline_command(image_path, size_spec)
        elif placement in {ImagePlacement.WRAP_LEFT, ImagePlacement.WRAP_RIGHT}:
            return self._generate_wrap_command(
                image_path, title, placement, size_spec, label
            )
        elif placement == ImagePlacement.MARGIN:
            return self._generate_margin_command(image_path, title, size_spec)
        elif placement == ImagePlacement.FULL_WIDTH:
            return self._generate_full_width_command(image_path, title, label)
        else:
            return self._generate_float_command(
                image_path, title, placement, size_spec, label
            )

    def _generate_inline_command(self, image_path: Path, size_spec: str) -> str:
        """Generate inline image command.

        Args:
            image_path: Path to image
            size_spec: Size specification

        Returns:
            LaTeX command
        """
        return f"\\includegraphics[width={size_spec}]{{{image_path}}}"

    def _generate_wrap_command(
        self,
        image_path: Path,
        title: str,
        placement: ImagePlacement,
        size_spec: str,
        label: str | None = None,
    ) -> str:
        """Generate wrapped image command.

        Args:
            image_path: Path to image
            title: Image caption
            placement: Wrap placement (left/right)
            size_spec: Size specification
            label: Optional label

        Returns:
            LaTeX command using wrapfig
        """
        side = "l" if placement == ImagePlacement.WRAP_LEFT else "r"

        command = f"""\\begin{{wrapfigure}}{{{side}}}{{{size_spec}}}
    \\centering
    \\includegraphics[width={size_spec}]{{{image_path}}}"""

        if title:
            command += f"\n    \\caption{{{title}}}"

        if label:
            command += f"\n    \\label{{{label}}}"

        command += "\n\\end{wrapfigure}"
        return command

    def _generate_margin_command(
        self,
        image_path: Path,
        title: str,
        size_spec: str,
    ) -> str:
        """Generate margin image command.

        Args:
            image_path: Path to image
            title: Image caption
            size_spec: Size specification

        Returns:
            LaTeX command for margin placement
        """
        # Using marginpar for margin images
        command = f"\\marginpar{{\\includegraphics[width={size_spec}]{{{image_path}}}"

        if title:
            command += f"\\\\\\small {title}"

        command += "}"
        return command

    def _generate_full_width_command(
        self,
        image_path: Path,
        title: str,
        label: str | None = None,
    ) -> str:
        """Generate full-width image command.

        Args:
            image_path: Path to image
            title: Image caption
            label: Optional label

        Returns:
            LaTeX command for full-width placement
        """
        command = f"""\\begin{{figure*}}[t]
    \\centering
    \\includegraphics[width=\\textwidth]{{{image_path}}}"""

        if title:
            command += f"\n    \\caption{{{title}}}"

        if label:
            command += f"\n    \\label{{{label}}}"

        command += "\n\\end{figure*}"
        return command

    def _generate_float_command(
        self,
        image_path: Path,
        title: str,
        placement: ImagePlacement,
        size_spec: str,
        label: str | None = None,
    ) -> str:
        """Generate floating figure command.

        Args:
            image_path: Path to image
            title: Image caption
            placement: Float placement
            size_spec: Size specification
            label: Optional label

        Returns:
            LaTeX command for floating figure
        """
        # Convert placement to LaTeX float specifier
        float_spec_map = {
            ImagePlacement.FLOAT_HERE: "htbp",
            ImagePlacement.FLOAT_TOP: "t",
            ImagePlacement.FLOAT_BOTTOM: "b",
            ImagePlacement.FLOAT_PAGE: "p",
        }
        float_spec = float_spec_map.get(placement, "htbp")

        command = f"""\\begin{{figure}}[{float_spec}]
    \\centering
    \\includegraphics[width={size_spec}]{{{image_path}}}"""

        if title:
            command += f"\n    \\caption{{{title}}}"

        if label:
            command += f"\n    \\label{{{label}}}"

        command += "\n\\end{figure}"
        return command

    def _generate_label(self, image_entry: dict[str, Any]) -> str | None:
        """Generate LaTeX label for image.

        Args:
            image_entry: Image entry data

        Returns:
            LaTeX label or None
        """
        if "id" in image_entry:
            return f"fig:{image_entry['id']}"
        elif "title" in image_entry:
            # Create label from title
            title = image_entry["title"].lower()
            label = "".join(c if c.isalnum() else "-" for c in title)
            return f"fig:{label}"
        else:
            return None

    def _get_required_packages(self, placement: ImagePlacement) -> list[str]:
        """Get required LaTeX packages for placement type.

        Args:
            placement: Image placement

        Returns:
            List of required package names
        """
        packages = ["graphicx"]  # Always needed for includegraphics

        if placement in {ImagePlacement.WRAP_LEFT, ImagePlacement.WRAP_RIGHT}:
            packages.append("wrapfig")
        elif placement == ImagePlacement.FULL_WIDTH:
            packages.append("float")
        elif placement in {
            ImagePlacement.FLOAT_HERE,
            ImagePlacement.FLOAT_TOP,
            ImagePlacement.FLOAT_BOTTOM,
            ImagePlacement.FLOAT_PAGE,
        }:
            packages.append("float")

        return packages

"""Gallery processor for handling multi-image layouts in LaTeX documents.

This module provides comprehensive gallery processing capabilities,
building on the Phase 1 and Phase 2 image systems to handle
collections of images with intelligent layout strategies.
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from pydantic import BaseModel, Field

from studiorum.core.logging import get_logger
from studiorum.core.result import Error, Result, Success
from studiorum.renderers.core.interfaces import RenderingContext

if TYPE_CHECKING:
    from .enhanced_image_placer import EnhancedImagePlacer
    from .image_processor import ImageProcessor

logger = get_logger(__name__)


class GalleryLayout(Enum):
    """Supported gallery layout types."""

    GRID = "grid"
    SHOWCASE = "showcase"
    SEQUENTIAL = "sequential"
    COMPARISON = "comparison"


class GalleryConfig(BaseModel):
    """Configuration for gallery processing."""

    default_layout: GalleryLayout = Field(
        default=GalleryLayout.GRID, description="Default layout when not specified"
    )
    default_columns: int = Field(
        default=2, ge=1, le=6, description="Default columns for grid layout"
    )
    max_images_per_row: int = Field(
        default=4, ge=1, le=6, description="Maximum images per row in any layout"
    )
    enable_captions: bool = Field(
        default=True, description="Enable individual image captions"
    )
    enable_subcaptions: bool = Field(
        default=True, description="Enable subcaptions for individual images"
    )
    default_image_width: str = Field(
        default="0.45\\textwidth", description="Default width for individual images"
    )
    gallery_margin: str = Field(
        default="1em", description="Margin around the entire gallery"
    )
    image_separation: str = Field(
        default="0.02\\textwidth", description="Separation between images"
    )
    # Enhanced decorative options for Phase 3
    enable_decorative_elements: bool = Field(
        default=True,
        description="Enable decorative LaTeX elements for showcase layouts",
    )
    showcase_decorative_style: str = Field(
        default="elegant",
        description="Style for showcase decorations: elegant, gothic, modern",
    )
    enable_featured_borders: bool = Field(
        default=True, description="Enable decorative borders for featured images"
    )
    decorative_color_scheme: str = Field(
        default="dndred", description="Color scheme for decorative elements"
    )
    chapter_opener_enhancements: bool = Field(
        default=True, description="Enable enhanced chapter opener presentation"
    )


class ProcessedGallery(BaseModel):
    """Result of gallery processing."""

    latex_command: str
    layout_used: GalleryLayout
    image_count: int
    required_packages: list[str] = Field(default_factory=list)
    caption: str | None = None
    title: str | None = None
    processing_metadata: dict[str, Any] = Field(default_factory=dict)


class GalleryProcessor:
    """Processor for handling multi-image gallery layouts.

    Integrates with Phase 1 ImageProcessor and Phase 2 EnhancedImagePlacer
    to provide sophisticated gallery layout capabilities.
    """

    def __init__(
        self,
        config: GalleryConfig | None = None,
        image_processor: ImageProcessor | None = None,
    ) -> None:
        """Initialize the gallery processor.

        Args:
            config: Gallery processing configuration
            image_processor: Image processor for handling individual images
        """
        self.config = config or GalleryConfig()
        self._image_processor = image_processor
        self._enhanced_placer: EnhancedImagePlacer | None = None

        logger.debug("Initialized GalleryProcessor")

    def process_gallery(
        self,
        gallery_entry: dict[str, Any],
        context: RenderingContext,
    ) -> Result[ProcessedGallery, str]:
        """Process a gallery entry into LaTeX code.

        Args:
            gallery_entry: Gallery entry dictionary
            context: Current rendering context

        Returns:
            Result containing processed gallery or error message
        """
        try:
            # Extract gallery information
            images = gallery_entry.get("images", [])
            if not images:
                return Error("Gallery contains no images")

            # Determine layout
            layout = self._determine_layout(gallery_entry)

            # Process individual images
            processed_images = []
            for i, image_data in enumerate(images):
                result = self._process_gallery_image(image_data, context, i)
                match result:
                    case Success(value):
                        processed_images.append(value)
                    case Error(error):
                        logger.warning(f"Failed to process gallery image {i}: {error}")
                        continue

            if not processed_images:
                return Error("No images could be processed in gallery")

            # Generate LaTeX based on layout
            latex_result = self._generate_gallery_latex(
                processed_images, layout, gallery_entry
            )

            if latex_result.is_error():
                from studiorum.core.result import Error as ErrorType

                if isinstance(latex_result, ErrorType):
                    return Error(latex_result.error)
                else:
                    return Error("Unknown error in latex generation")

            latex_command = latex_result.unwrap()

            # Create result
            processed_gallery = ProcessedGallery(
                latex_command=latex_command,
                layout_used=layout,
                image_count=len(processed_images),
                required_packages=self._get_required_packages(layout),
                caption=gallery_entry.get("caption"),
                title=gallery_entry.get("title"),
                processing_metadata={
                    "original_image_count": len(images),
                    "processed_image_count": len(processed_images),
                    "layout_strategy": layout.value,
                },
            )

            logger.info(
                f"Processed gallery with {len(processed_images)} images "
                f"using {layout.value} layout"
            )

            return Success(processed_gallery)

        except Exception as e:
            logger.error(f"Gallery processing failed: {str(e)}")
            return Error(f"Gallery processing failed: {str(e)}")

    def _determine_layout(self, gallery_entry: dict[str, Any]) -> GalleryLayout:
        """Determine the appropriate layout for the gallery."""
        layout_str = gallery_entry.get("layout", "").lower()

        layout_mapping = {
            "grid": GalleryLayout.GRID,
            "showcase": GalleryLayout.SHOWCASE,
            "sequential": GalleryLayout.SEQUENTIAL,
            "comparison": GalleryLayout.COMPARISON,
        }

        return layout_mapping.get(layout_str, self.config.default_layout)

    def _process_gallery_image(
        self, image_data: dict[str, Any], context: RenderingContext, index: int
    ) -> Result[dict[str, Any], str]:
        """Process a single image within the gallery context."""
        try:
            # Add gallery context to image processing
            gallery_context = {
                "gallery_position": index,
                "in_gallery": True,
                "compact_mode": True,
            }

            # If we have an image processor, use it
            if self._image_processor:
                # Create a copy of context with gallery information
                gallery_metadata = context.metadata.copy()
                gallery_metadata.update(gallery_context)

                gallery_rendering_context = RenderingContext(
                    output_format=context.output_format,
                    debug_mode=context.debug_mode,
                    omnidexer=context.omnidexer,
                    content_tracker=context.content_tracker,
                    tag_resolver=context.tag_resolver,
                    metadata=gallery_metadata,
                )

                latex_command = self._image_processor.process_image_entry(
                    image_data, gallery_rendering_context
                )
            else:
                # Fallback to basic processing
                latex_command = self._process_image_basic(image_data)

            return Success(
                {
                    "latex_command": latex_command,
                    "title": image_data.get("title"),
                    "href": image_data.get("href"),
                    "altText": image_data.get("altText"),
                    "index": index,
                }
            )

        except Exception as e:
            return Error(f"Failed to process image {index}: {str(e)}")

    def _process_image_basic(self, image_data: dict[str, Any]) -> str:
        """Basic fallback image processing for gallery context."""
        href = image_data.get("href")
        title = image_data.get("title")

        if not href:
            return "% Missing image reference"

        # Extract image path
        if isinstance(href, dict):
            image_path = href.get("path", href.get("url", ""))
        else:
            image_path = str(href)

        if not image_path:
            return "% Invalid image reference"

        # Generate basic LaTeX for gallery context (no figure environment)
        width_spec = self.config.default_image_width

        if title:
            return (
                f"\\begin{{subfigure}}{{{width_spec}}}\n"
                f"    \\centering\n"
                f"    \\includegraphics[width=\\textwidth]{{{image_path}}}\n"
                f"    \\caption{{{title}}}\n"
                f"\\end{{subfigure}}"
            )
        else:
            return (
                f"\\begin{{subfigure}}{{{width_spec}}}\n"
                f"    \\centering\n"
                f"    \\includegraphics[width=\\textwidth]{{{image_path}}}\n"
                f"\\end{{subfigure}}"
            )

    def _generate_gallery_latex(
        self,
        processed_images: list[dict[str, Any]],
        layout: GalleryLayout,
        gallery_entry: dict[str, Any],
    ) -> Result[str, str]:
        """Generate LaTeX code for the complete gallery."""
        try:
            if layout == GalleryLayout.GRID:
                return self._generate_grid_layout(processed_images, gallery_entry)
            elif layout == GalleryLayout.SHOWCASE:
                return self._generate_showcase_layout(processed_images, gallery_entry)
            elif layout == GalleryLayout.SEQUENTIAL:
                return self._generate_sequential_layout(processed_images, gallery_entry)
            elif layout == GalleryLayout.COMPARISON:
                return self._generate_comparison_layout(processed_images, gallery_entry)
            else:
                return Error(f"Unsupported layout: {layout}")

        except Exception as e:
            return Error(f"LaTeX generation failed: {str(e)}")

    def _generate_grid_layout(
        self, processed_images: list[dict[str, Any]], gallery_entry: dict[str, Any]
    ) -> Result[str, str]:
        """Generate grid layout LaTeX using the gallery template."""
        columns = min(
            gallery_entry.get("columns", self.config.default_columns),
            self.config.max_images_per_row,
        )

        title = gallery_entry.get("title", "")
        caption = gallery_entry.get("caption", "")

        # Calculate image width based on columns
        # Account for separation between images
        if columns == 1:
            image_width = "0.9\\textwidth"
        elif columns == 2:
            image_width = "0.48\\textwidth"  # Roughly (1 - 0.02*1)/2
        elif columns == 3:
            image_width = "0.31\\textwidth"  # Roughly (1 - 0.02*2)/3
        else:
            # For more columns, use calc package syntax
            separation_total = f"{columns - 1} * {self.config.image_separation}"
            image_width = (
                f"\\dimexpr(\\textwidth - {separation_total})/{columns}\\relax"
            )

        # Render via gallery template
        return self._render_gallery_template(
            layout="grid",
            processed_images=processed_images,
            gallery_entry=gallery_entry,
            template_params={
                "columns": columns,
                "image_width": image_width,
                "title": title,
                "caption": caption,
            },
        )

    def _generate_showcase_layout(
        self, processed_images: list[dict[str, Any]], gallery_entry: dict[str, Any]
    ) -> Result[str, str]:
        """Generate enhanced showcase layout via gallery template (no inline LaTeX)."""
        title = gallery_entry.get("title", "")
        caption = gallery_entry.get("caption", "")

        # Render via gallery template
        return self._render_gallery_template(
            layout="showcase",
            processed_images=processed_images,
            gallery_entry=gallery_entry,
            template_params={
                "title": title,
                "caption": caption,
                "decorative_enabled": self.config.enable_decorative_elements,
                "decorative_style": self.config.showcase_decorative_style,
                "decorative_color": self.config.decorative_color_scheme,
                "featured_borders": self.config.enable_featured_borders,
                "main_width": "0.7\\textwidth",
                "thumb_width": "0.15\\textwidth",
            },
        )

    def _generate_sequential_layout(
        self, processed_images: list[dict[str, Any]], gallery_entry: dict[str, Any]
    ) -> Result[str, str]:
        """Generate sequential layout using the gallery template."""
        title = gallery_entry.get("title", "")
        caption = gallery_entry.get("caption", "")
        image_width = "0.8\\textwidth"

        return self._render_gallery_template(
            layout="sequential",
            processed_images=processed_images,
            gallery_entry=gallery_entry,
            template_params={
                "image_width": image_width,
                "title": title,
                "caption": caption,
                "gallery_margin": self.config.gallery_margin,
            },
        )

    def _generate_comparison_layout(
        self, processed_images: list[dict[str, Any]], gallery_entry: dict[str, Any]
    ) -> Result[str, str]:
        """Generate comparison layout using the gallery template."""
        title = gallery_entry.get("title", "")
        caption = gallery_entry.get("caption", "")

        # Use equal width for all images
        num_images = min(len(processed_images), self.config.max_images_per_row)
        per_image_width = f"{0.9 / max(1, num_images)}\\textwidth"

        return self._render_gallery_template(
            layout="comparison",
            processed_images=processed_images,
            gallery_entry=gallery_entry,
            template_params={
                "per_image_width": per_image_width,
                "title": title,
                "caption": caption,
            },
        )

    def _render_gallery_template(
        self,
        *,
        layout: str,
        processed_images: list[dict[str, Any]],
        gallery_entry: dict[str, Any],
        template_params: dict[str, Any] | None = None,
    ) -> Result[str, str]:
        r"""Render the gallery via the Jinja2 template.

        This uses _gallery_render_block.tex.j2 and calls \StudiorumImage for each image.
        """
        try:
            from studiorum.latex_engine.core.template_engine import LaTeXTemplateEngine

            engine = LaTeXTemplateEngine()
            template = engine.env.get_template("_gallery_render_block.tex.j2")

            # Prepare image data for template
            include_images = True  # entry processor guards disabled images earlier
            draft_flag = "draft=true" if not include_images else None

            images_for_template: list[dict[str, Any]] = []
            for img in processed_images:
                path = ""
                href = img.get("href")
                if isinstance(href, dict):
                    path = href.get("path") or href.get("url") or ""
                if not path:
                    # Fallback: extract from latex_command
                    path = self._extract_image_path(img.get("latex_command", ""))

                options = ",".join(
                    [opt for opt in ([draft_flag] if draft_flag else []) if opt]
                )
                images_for_template.append(
                    {
                        "path": path,
                        "title": img.get("title") or "",
                        "options": options,
                        # Allow per-image width override if needed
                        "subfigure_width": None,
                    }
                )

            params: dict[str, Any] = {
                "layout": layout,
                "title": gallery_entry.get("title") or "",
                "caption": gallery_entry.get("caption") or "",
                "images": images_for_template,
                "env_placement": "htbp",
                "gallery_margin": self.config.gallery_margin,
            }
            if template_params:
                params.update(template_params)

            rendered = template.render(**params)
            return Success(rendered)
        except Exception as e:
            logger.error(f"Gallery template render failed: {e}", exc_info=True)
            return Error(f"Gallery template render failed: {e}")

    def _extract_image_command(self, latex_command: str) -> str:
        """Extract just the includegraphics command from processed LaTeX."""
        # Look for includegraphics command
        lines = latex_command.split("\n")
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("\\includegraphics"):
                return stripped

        # If no includegraphics found, return original
        return latex_command

    def _get_required_packages(self, layout: GalleryLayout) -> list[str]:
        """Get LaTeX packages required for the layout."""
        packages = ["graphicx", "subcaption"]

        # Add layout-specific packages if needed
        if layout in [GalleryLayout.GRID, GalleryLayout.SHOWCASE]:
            packages.append("calc")  # For width calculations

        # Add decorative packages for enhanced showcase layouts
        if layout == GalleryLayout.SHOWCASE and self.config.enable_decorative_elements:
            packages.extend(["tikz", "xcolor"])  # For decorative elements

        return packages

    def _generate_showcase_decorative_header(
        self, gallery_entry: dict[str, Any]
    ) -> list[str]:
        """Generate decorative header elements for showcase layout.

        Args:
            gallery_entry: Gallery entry data

        Returns:
            List of LaTeX lines for decorative header
        """
        if not self.config.enable_decorative_elements:
            return []

        title = gallery_entry.get("title", "")
        style = self.config.showcase_decorative_style
        color = self.config.decorative_color_scheme

        decorative_lines = [
            "    % Showcase decorative header",
            "    \\begin{tikzpicture}[remember picture,overlay]",
        ]

        if style == "elegant":
            decorative_lines.extend(
                [
                    f"        \\draw[line width=1.5pt,color={color}!60] ",
                    "              ([yshift=-5pt]current page.north west) -- ",
                    "              ([yshift=-5pt]current page.north east);",
                    f"        \\node[color={color}!80,font=\\Large\\bfseries] ",
                    "              at ([yshift=-10pt]current page.north) ",
                    f"              {{{title or 'Featured Gallery'}}};",
                ]
            )
        elif style == "gothic":
            decorative_lines.extend(
                [
                    f"        \\draw[line width=2pt,color={color}!70,decorate,",
                    "              decoration={zigzag,amplitude=1pt,segment length=5pt}] ",
                    "              ([yshift=-8pt]current page.north west) -- ",
                    "              ([yshift=-8pt]current page.north east);",
                ]
            )
        elif style == "modern":
            decorative_lines.extend(
                [
                    f"        \\fill[color={color}!20] ",
                    "              ([yshift=-3pt]current page.north west) rectangle ",
                    "              ([yshift=-15pt]current page.north east);",
                    f"        \\draw[line width=1pt,color={color}] ",
                    "              ([yshift=-15pt]current page.north west) -- ",
                    "              ([yshift=-15pt]current page.north east);",
                ]
            )

        decorative_lines.append("    \\end{tikzpicture}")
        decorative_lines.append("    \\\\[1em]")

        return decorative_lines

    def _generate_showcase_decorative_footer(
        self, gallery_entry: dict[str, Any]
    ) -> list[str]:
        """Generate decorative footer elements for showcase layout.

        Args:
            gallery_entry: Gallery entry data

        Returns:
            List of LaTeX lines for decorative footer
        """
        if not self.config.enable_decorative_elements:
            return []

        style = self.config.showcase_decorative_style
        color = self.config.decorative_color_scheme

        decorative_lines = [
            "    % Showcase decorative footer",
            "    \\\\[0.5em]",
            "    \\begin{tikzpicture}",
        ]

        if style == "elegant":
            decorative_lines.extend(
                [
                    f"        \\draw[line width=1pt,color={color}!40] ",
                    "              (0,0) -- (\\textwidth,0);",
                    "        \\foreach \\x in {0.2\\textwidth,0.4\\textwidth,0.6\\textwidth,0.8\\textwidth} ",
                    f"            \\node[circle,fill={color}!30,inner sep=1pt] at (\\x,0) {{}};",
                ]
            )
        elif style == "gothic":
            decorative_lines.extend(
                [
                    f"        \\draw[line width=1.5pt,color={color}!50,decorate,",
                    "              decoration={coil,amplitude=2pt,segment length=8pt}] ",
                    "              (0,0) -- (\\textwidth,0);",
                ]
            )
        elif style == "modern":
            decorative_lines.extend(
                [
                    f"        \\fill[color={color}!15] ",
                    "              (0,-2pt) rectangle (\\textwidth,2pt);",
                    f"        \\draw[line width=0.5pt,color={color}] ",
                    "              (0,2pt) -- (\\textwidth,2pt);",
                    f"        \\draw[line width=0.5pt,color={color}] ",
                    "              (0,-2pt) -- (\\textwidth,-2pt);",
                ]
            )

        decorative_lines.append("    \\end{tikzpicture}")

        return decorative_lines

    def create_chapter_opener_showcase(
        self,
        opener_image: dict[str, Any],
        chapter_context: dict[str, Any],
        context: RenderingContext,
    ) -> Result[ProcessedGallery, str]:
        """Create enhanced chapter opener showcase with decorative elements.

        Args:
            opener_image: Chapter opener image data
            chapter_context: Chapter context information
            context: Rendering context

        Returns:
            Result containing processed chapter opener gallery or error
        """
        try:
            if not self.config.chapter_opener_enhancements:
                # Fall back to standard processing
                return self.process_gallery(
                    {
                        "images": [opener_image],
                        "layout": "showcase",
                        "title": chapter_context.get("chapter_name", "Chapter Opener"),
                    },
                    context,
                )

            # Enhanced chapter opener processing
            chapter_name = chapter_context.get("chapter_name", "Chapter")
            adventure_name = chapter_context.get("adventure_name", "")

            # Process the opener image
            processed_result = self._process_gallery_image(opener_image, context, 0)
            if isinstance(processed_result, Error):
                return Error(
                    f"Failed to process chapter opener: {processed_result.error}"
                )

            processed_image = processed_result.unwrap()

            # Generate enhanced LaTeX for chapter opener
            latex_parts = [
                "% Enhanced Chapter Opener with Decorative Elements",
                "\\begin{figure}[t!]",
                "    \\centering",
            ]

            if self.config.enable_decorative_elements:
                # Full-width decorative chapter opener
                latex_parts.extend(
                    [
                        "    \\begin{tikzpicture}[remember picture,overlay]",
                        "        % Background decorative element",
                        f"        \\fill[color={self.config.decorative_color_scheme}!5] ",
                        "              ([yshift=-50pt]current page.north west) rectangle ",
                        "              ([yshift=-200pt]current page.north east);",
                        "        % Chapter opener image",
                        "        \\node[anchor=north,inner sep=0pt] ",
                        "              at ([yshift=-60pt]current page.north) {",
                        f"            \\includegraphics[width=0.9\\textwidth,height=120pt,keepaspectratio]{{{self._extract_image_path(processed_image['latex_command'])}}}",
                        "        };",
                        "        % Decorative border",
                        f"        \\draw[line width=3pt,color={self.config.decorative_color_scheme}] ",
                        "              ([yshift=-55pt]current page.north west) rectangle ",
                        "              ([yshift=-185pt]current page.north east);",
                        "        % Chapter title overlay",
                        "        \\node[color=white,font=\\Huge\\bfseries,drop shadow] ",
                        "              at ([yshift=-120pt]current page.north) ",
                        f"              {{{chapter_name}}};",
                        "    \\end{tikzpicture}",
                        "    \\vspace{150pt}  % Space for overlay content",
                    ]
                )
            else:
                # Standard chapter opener
                latex_parts.extend(
                    [
                        f"    \\includegraphics[width=\\textwidth]{{{self._extract_image_path(processed_image['latex_command'])}}}",
                        f"    \\caption*{{\\Large\\textbf{{{chapter_name}}}}}",
                    ]
                )

            latex_parts.append("\\end{figure}")
            latex_parts.append("\\clearpage  % Start chapter on new page")

            final_latex = "\n".join(latex_parts)

            result = ProcessedGallery(
                latex_command=final_latex,
                layout_used=GalleryLayout.SHOWCASE,
                image_count=1,
                required_packages=self._get_required_packages(GalleryLayout.SHOWCASE)
                + ["shadowtext"],
                title=f"{adventure_name} - {chapter_name}"
                if adventure_name
                else chapter_name,
                processing_metadata={
                    "chapter_opener": True,
                    "enhanced_decorations": self.config.enable_decorative_elements,
                    "decorative_style": self.config.showcase_decorative_style,
                },
            )

            return Success(result)

        except Exception as e:
            return Error(f"Chapter opener showcase creation failed: {str(e)}")

    def _extract_image_path(self, latex_command: str) -> str:
        """Extract image path from includegraphics command.

        Args:
            latex_command: LaTeX command containing includegraphics

        Returns:
            Image path or placeholder if not found
        """
        import re

        # Look for includegraphics with path
        match = re.search(r"\\includegraphics\[[^\]]*\]\{([^}]+)\}", latex_command)
        if match:
            return match.group(1)

        # Simple pattern without options
        match = re.search(r"\\includegraphics\{([^}]+)\}", latex_command)
        if match:
            return match.group(1)

        # Fallback
        return "placeholder_chapter_opener"

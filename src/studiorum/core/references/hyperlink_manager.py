"""Hyperlink management for PDF navigation and styling."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator

from studiorum.core.logging import get_logger

logger = get_logger(__name__)


class HyperlinkStyle(BaseModel):
    """Configuration for hyperlink appearance."""

    color: str = Field(default="black", description="LaTeX color name")
    border: bool = Field(default=False, description="Whether to show border")
    underline: bool = Field(default=False, description="Whether to underline")
    font_style: str = Field(default="normal", description="Font style")

    @field_validator("color")
    @classmethod
    def validate_latex_color(cls, v: str) -> str:
        """Validate LaTeX color names to prevent compilation errors."""
        # Common LaTeX color names that should always work
        valid_colors = {
            "black",
            "white",
            "red",
            "green",
            "blue",
            "cyan",
            "magenta",
            "yellow",
            "gray",
            "grey",
            "darkgray",
            "darkgrey",
            "lightgray",
            "lightgrey",
            "brown",
            "lime",
            "olive",
            "orange",
            "pink",
            "purple",
            "teal",
            "violet",
            "darkgreen",
            "navy",
            "maroon",
        }

        color_lower = v.lower().strip()
        if color_lower not in valid_colors:
            # Allow it but log a warning for unknown colors
            logger.warning(f"Unknown LaTeX color '{v}' - may cause compilation issues")

        return v.strip()

    @field_validator("font_style")
    @classmethod
    def validate_font_style(cls, v: str) -> str:
        """Validate font style options."""
        valid_styles = {"normal", "bold", "italic", "bolditalic"}

        style_lower = v.lower().strip()
        if style_lower not in valid_styles:
            raise ValueError(f"Invalid font style '{v}'. Must be one of {valid_styles}")

        return style_lower


class HyperlinkManager:
    """Manages hyperlink generation and styling for PDF navigation."""

    def __init__(self) -> None:
        self.enabled = True
        self.auto_page_refs = True

        # Default styles for different content types
        self.content_styles: dict[str, HyperlinkStyle] = {
            "creature": HyperlinkStyle(color="black", font_style="bold"),
            "spell": HyperlinkStyle(color="blue", font_style="italic"),
            "item": HyperlinkStyle(color="purple", font_style="italic"),
            "class": HyperlinkStyle(color="darkgreen", font_style="bold"),
            "race": HyperlinkStyle(color="brown", font_style="normal"),
            "background": HyperlinkStyle(color="gray", font_style="normal"),
            "feat": HyperlinkStyle(color="orange", font_style="bold"),
            "condition": HyperlinkStyle(color="red", font_style="italic"),
            "adventure": HyperlinkStyle(color="navy", font_style="italic"),
            "book": HyperlinkStyle(color="navy", font_style="italic"),
            "default": HyperlinkStyle(color="black", font_style="normal"),
        }

        # Content types that should include page references
        self.page_ref_types = {
            "creature",
            "spell",
            "item",
            "class",
            "race",
            "background",
            "feat",
            "adventure",
            "book",
        }

        # Content types that should not be hyperlinked
        self.no_hyperlink_types = {"filter", "loader"}

    def should_create_hyperlink(self, content_type: str) -> bool:
        """Check if hyperlinks should be created for this content type."""
        return self.enabled and content_type not in self.no_hyperlink_types

    def create_hyperlink(
        self,
        text: str,
        ref_id: str,
        content_type: str = "default",
        include_page_ref: bool | None = None,
        custom_style: HyperlinkStyle | None = None,
    ) -> str:
        """Create a LaTeX hyperlink with appropriate styling."""
        if not self.should_create_hyperlink(content_type):
            return text

        # Get style for content type
        style = custom_style or self.content_styles.get(
            content_type, self.content_styles["default"]
        )

        # Apply text formatting based on style
        formatted_text = self._apply_text_formatting(text, style)

        # Create basic hyperlink
        hyperlink = f"\\hyperref[{ref_id}]{{{formatted_text}}}"

        # Add page reference if appropriate
        if include_page_ref is None:
            include_page_ref = (
                self.auto_page_refs and content_type in self.page_ref_types
            )

        if include_page_ref:
            hyperlink += f" (p. \\pageref{{{ref_id}}})"

        # Apply hyperlink styling
        if style.color != "black" or style.border or style.underline:
            hyperlink = self._apply_hyperlink_styling(hyperlink, style)

        return hyperlink

    def _apply_text_formatting(self, text: str, style: HyperlinkStyle) -> str:
        """Apply text formatting based on style."""
        if style.font_style == "bold":
            return f"\\textbf{{{text}}}"
        elif style.font_style == "italic":
            return f"\\textit{{{text}}}"
        elif style.font_style == "bolditalic":
            return f"\\textbf{{\\textit{{{text}}}}}"
        else:
            return text

    def _apply_hyperlink_styling(self, hyperlink: str, style: HyperlinkStyle) -> str:
        """Apply hyperlink-specific styling."""
        styling_options = []

        if style.color != "black":
            styling_options.append(f"linkcolor={style.color}")

        if style.border:
            styling_options.append("pdfborder={0 0 1}")
        else:
            styling_options.append("pdfborder={0 0 0}")

        if style.underline:
            styling_options.append("colorlinks=true")

        if styling_options:
            # Wrap in hypersetup for local styling
            return f"{{\\hypersetup{{{','.join(styling_options)}}}{hyperlink}}}"

        return hyperlink

    def create_external_link(
        self, text: str, url: str, style: HyperlinkStyle | None = None
    ) -> str:
        """Create a hyperlink to an external URL."""
        if not self.enabled:
            return text

        style = style or self.content_styles["default"]
        formatted_text = self._apply_text_formatting(text, style)

        # Create external hyperlink
        hyperlink = f"\\href{{{url}}}{{{formatted_text}}}"

        # Apply styling
        if style.color != "black" or style.border or style.underline:
            hyperlink = self._apply_hyperlink_styling(hyperlink, style)

        return hyperlink

    def create_section_reference(
        self, text: str, section_label: str, ref_type: str = "nameref"
    ) -> str:
        """Create a reference to a document section."""
        if not self.enabled:
            return text

        if ref_type == "nameref":
            return f"\\nameref{{{section_label}}}"
        elif ref_type == "ref":
            return f"\\ref{{{section_label}}}"
        elif ref_type == "pageref":
            return f"page \\pageref{{{section_label}}}"
        elif ref_type == "autoref":
            return f"\\autoref{{{section_label}}}"
        else:
            return f"\\hyperref[{section_label}]{{{text}}}"

    def create_footnote_reference(self, text: str, footnote_id: str) -> str:
        """Create a reference to a footnote."""
        return f"\\footref{{{footnote_id}}}"

    def set_content_style(self, content_type: str, style: HyperlinkStyle) -> None:
        """Set hyperlink style for a content type."""
        self.content_styles[content_type] = style

    def set_page_reference_types(self, content_types: set[str]) -> None:
        """Set which content types should include page references."""
        self.page_ref_types = content_types.copy()

    def enable_hyperlinks(self, enable: bool = True) -> None:
        """Enable or disable hyperlink generation."""
        self.enabled = enable

    def enable_auto_page_refs(self, enable: bool = True) -> None:
        """Enable or disable automatic page references."""
        self.auto_page_refs = enable

    def get_latex_packages(self) -> list[str]:
        """Get required LaTeX packages for hyperlink functionality."""
        return [
            "hyperref",  # Core hyperlink functionality
            "xcolor",  # Color support
            "nameref",  # Named references
            "footmisc",  # Footnote references
        ]

    def get_latex_setup_commands(self) -> list[str]:
        """Get LaTeX setup commands for hyperlink configuration."""
        return [
            "\\hypersetup{",
            "    colorlinks=true,",
            "    linkcolor=black,",
            "    urlcolor=blue,",
            "    citecolor=black,",
            "    filecolor=black,",
            "    pdfborder={0 0 0},",
            "    bookmarksdepth=3,",
            "    bookmarksopen=true",
            "}",
        ]

    def create_bookmark(self, title: str, level: int = 0) -> str:
        """Create a PDF bookmark."""
        return (
            f"\\pdfbookmark[{level}]{{{title}}}{{{self._sanitize_bookmark_id(title)}}}"
        )

    def _sanitize_bookmark_id(self, title: str) -> str:
        """Sanitize title for use as bookmark ID."""
        import re

        sanitized = re.sub(r"[^a-zA-Z0-9]+", "-", title.lower())
        return sanitized.strip("-")

    def validate_hyperlinks(self, content: str) -> list[dict[str, str]]:
        """Validate hyperlinks in content and return any issues."""
        import re

        issues = []

        # Find all hyperref commands
        hyperref_pattern = r"\\hyperref\[([^\]]+)\]\{[^}]+\}"
        href_pattern = r"\\href\{([^}]+)\}\{[^}]+\}"

        # Check internal references
        for match in re.finditer(hyperref_pattern, content):
            ref_id = match.group(1)
            if not self._is_valid_reference_id(ref_id):
                issues.append(
                    {
                        "type": "invalid_ref_id",
                        "ref_id": ref_id,
                        "message": f"Invalid reference ID: {ref_id}",
                    }
                )

        # Check external URLs
        for match in re.finditer(href_pattern, content):
            url = match.group(1)
            if not self._is_valid_url(url):
                issues.append(
                    {
                        "type": "invalid_url",
                        "url": url,
                        "message": f"Invalid URL: {url}",
                    }
                )

        return issues

    def _is_valid_reference_id(self, ref_id: str) -> bool:
        """Check if reference ID is valid."""
        import re

        return bool(re.match(r"^[a-zA-Z0-9_:-]+$", ref_id))

    def _is_valid_url(self, url: str) -> bool:
        """Check if URL is valid."""
        import re

        url_pattern = r"^https?://[^\s/$.?#].[^\s]*$"
        return bool(re.match(url_pattern, url))

    def get_hyperlink_statistics(self, content: str) -> dict[str, Any]:
        """Get statistics about hyperlinks in content."""
        import re

        stats: dict[str, Any] = {
            "total_internal_links": 0,
            "total_external_links": 0,
            "by_content_type": {},
            "broken_links": 0,
        }

        # Count internal hyperlinks
        hyperref_pattern = r"\\hyperref\[([^\]]+)\]"
        internal_matches = re.findall(hyperref_pattern, content)
        stats["total_internal_links"] = len(internal_matches)

        # Count by content type (extract from ref_id)
        for ref_id in internal_matches:
            if ":" in ref_id:
                content_type = ref_id.split(":", 1)[0]
                if content_type not in stats["by_content_type"]:
                    stats["by_content_type"][content_type] = 0
                stats["by_content_type"][content_type] += 1

        # Count external links
        href_pattern = r"\\href\{[^}]+\}"
        external_matches = re.findall(href_pattern, content)
        stats["total_external_links"] = len(external_matches)

        return stats

"""Sidebar and inset environment management for D&D content."""

from typing import Any

from ....core.models.content import ContentType
from .base import (
    ContentLayoutManager,
    EnvironmentWrapper,
    FloatPosition,
    LayoutContext,
    LayoutHint,
    SidebarType,
)


class SidebarManager(ContentLayoutManager):
    """Manages sidebar and inset environments for supplementary content."""

    def __init__(self, config: dict[str, Any] | None = None):
        """Initialize the sidebar manager."""
        super().__init__(config)

        # Sidebar type preferences by content type
        self.content_sidebar_types = {
            ContentType.ADVENTURE: SidebarType.READ_ALOUD,
            ContentType.BACKGROUND: SidebarType.SIDEBAR,
            ContentType.CLASS: SidebarType.SIDEBAR,
            ContentType.RACE: SidebarType.SIDEBAR,
            ContentType.FEAT: SidebarType.COMMENT,
            ContentType.SPELL: SidebarType.COMMENT,
            ContentType.ITEM: SidebarType.COMMENT,
        }

        # Default positioning for sidebar types
        self.sidebar_positions = {
            SidebarType.SIDEBAR: FloatPosition.BOTTOM,
            SidebarType.COMMENT: FloatPosition.HERE,
            SidebarType.READ_ALOUD: FloatPosition.HERE,
            SidebarType.AREA: FloatPosition.TOP,
            SidebarType.SUB_AREA: FloatPosition.HERE,
        }

        # Maximum sidebars per page
        self.max_sidebars_per_page = self.config.get("max_sidebars_per_page", 2)

        # Sidebar width preferences
        self.sidebar_widths = {
            "narrow": "0.3\\textwidth",
            "medium": "0.4\\textwidth",
            "wide": "0.5\\textwidth",
            "full": "\\textwidth",
        }

    def get_supported_content_types(self) -> set[ContentType]:
        """Support content types that benefit from sidebars."""
        return {
            ContentType.ADVENTURE,
            ContentType.BACKGROUND,
            ContentType.CLASS,
            ContentType.RACE,
            ContentType.FEAT,
            ContentType.SPELL,
            ContentType.ITEM,
        }

    def can_handle(self, context: LayoutContext) -> bool:
        """Handle sidebar management when explicitly requested or beneficial."""
        return bool(
            context.hints
            and context.hints.sidebar_type is not None
            and context.sidebar_count < self.max_sidebars_per_page
        )

    def get_priority(self) -> int:
        """Medium priority for sidebar decisions."""
        return 60

    def apply_layout(self, content: str, context: LayoutContext) -> str:
        """Apply sidebar environment to content."""
        if not content.strip() or not context.hints:
            return content

        sidebar_type = context.hints.sidebar_type
        if not sidebar_type:
            return content

        # Determine sidebar configuration
        position = self._determine_sidebar_position(context)
        title = self._extract_sidebar_title(content, sidebar_type)

        # Apply sidebar environment
        return self._apply_sidebar_environment(
            content, sidebar_type, position, title, context
        )

    def _determine_sidebar_position(self, context: LayoutContext) -> FloatPosition:
        """Determine optimal sidebar position."""
        # Use explicit hint first
        if context.hints and context.hints.sidebar_position:
            return context.hints.sidebar_position

        # Use sidebar type default
        if context.hints is None:
            return FloatPosition.HERE
        sidebar_type = context.hints.sidebar_type
        if sidebar_type is None:
            return FloatPosition.HERE
        default_pos = self.sidebar_positions.get(sidebar_type, FloatPosition.HERE)

        # Optimize based on context
        return self._optimize_sidebar_position(default_pos, context)

    def _optimize_sidebar_position(
        self, position: FloatPosition, context: LayoutContext
    ) -> FloatPosition:
        """Optimize sidebar position based on layout context."""
        # Avoid too many sidebars at the same position
        if context.sidebar_count >= 1:
            if position == FloatPosition.BOTTOM:
                return FloatPosition.TOP
            elif position == FloatPosition.TOP:
                return FloatPosition.BOTTOM

        # Adjust for page position
        if context.page_position == "top" and position == FloatPosition.TOP:
            return FloatPosition.HERE
        elif context.page_position == "bottom" and position == FloatPosition.BOTTOM:
            return FloatPosition.HERE

        return position

    def _extract_sidebar_title(self, content: str, sidebar_type: SidebarType) -> str:
        """Extract or generate appropriate sidebar title."""
        # Look for existing title markers
        lines = content.split("\n")
        first_line = lines[0].strip() if lines else ""

        # Check for LaTeX section commands
        section_commands = [
            "\\section",
            "\\subsection",
            "\\subsubsection",
            "\\paragraph",
        ]
        for cmd in section_commands:
            if first_line.startswith(cmd):
                # Extract title from LaTeX command
                start = first_line.find("{")
                end = first_line.rfind("}")
                if start != -1 and end != -1:
                    return first_line[start + 1 : end]

        # Check for markdown-style headers
        if first_line.startswith("#"):
            return first_line.lstrip("#").strip()

        # Check for bold text that might be a title
        if first_line.startswith("**") and first_line.endswith("**"):
            return first_line[2:-2]

        # Generate default titles based on sidebar type
        return self._generate_default_title(sidebar_type)

    def _generate_default_title(self, sidebar_type: SidebarType) -> str:
        """Generate default title for sidebar type."""
        titles = {
            SidebarType.SIDEBAR: "Information",
            SidebarType.COMMENT: "Note",
            SidebarType.READ_ALOUD: "Read Aloud",
            SidebarType.AREA: "Area",
            SidebarType.SUB_AREA: "Location",
        }
        return titles.get(sidebar_type, "Sidebar")

    def _apply_sidebar_environment(
        self,
        content: str,
        sidebar_type: SidebarType,
        position: FloatPosition,
        title: str,
        context: LayoutContext,
    ) -> str:
        """Apply the appropriate sidebar environment."""
        # Clean content by removing title if it was extracted
        content = self._clean_sidebar_content(content, title)

        # Build environment options
        options = self._build_sidebar_options(position, context)

        # Apply environment wrapper
        return EnvironmentWrapper.wrap_environment(
            content=content,
            environment=sidebar_type.value,
            options=options,
            title=title if title else None,
        )

    def _clean_sidebar_content(self, content: str, title: str) -> str:
        """Clean sidebar content by removing extracted title."""
        lines = content.split("\n")
        if not lines:
            return content

        first_line = lines[0].strip()

        # Remove title if it was extracted from first line
        section_commands = [
            "\\section",
            "\\subsection",
            "\\subsubsection",
            "\\paragraph",
        ]

        # Check if first line contains the title
        if any(cmd in first_line for cmd in section_commands):
            if title in first_line:
                lines = lines[1:]  # Remove first line
        elif first_line.startswith("#") and title in first_line:
            lines = lines[1:]
        elif first_line.startswith("**") and first_line.endswith("**"):
            if title == first_line[2:-2]:
                lines = lines[1:]

        return "\n".join(lines).strip()

    def _build_sidebar_options(
        self, position: FloatPosition, context: LayoutContext
    ) -> str:
        """Build LaTeX options string for sidebar environment."""
        options = []

        # Add float position
        if position != FloatPosition.HERE:
            if position == FloatPosition.FULL_WIDTH_BOTTOM:
                options.append("float*=b")
            else:
                options.append(f"float={position.value}")

        # Add width if specified in hints
        if context.hints and hasattr(context.hints, "sidebar_width"):
            width = context.hints.sidebar_width
            if width in self.sidebar_widths:
                options.append(f"width={self.sidebar_widths[width]}")
            else:
                options.append(f"width={width}")

        return ",".join(options) if options else ""

    def create_read_aloud_text(self, content: str, title: str = "Read Aloud") -> str:
        """Create a read-aloud text box for adventure content."""
        return EnvironmentWrapper.wrap_environment(
            content=content, environment=SidebarType.READ_ALOUD.value, title=title
        )

    def create_area_description(self, content: str, area_name: str) -> str:
        """Create an area description for adventure locations."""
        return f"\\DndArea{{{area_name}}}\n{content}"

    def create_sub_area_description(self, content: str, sub_area_name: str) -> str:
        """Create a sub-area description for adventure locations."""
        return f"\\DndSubArea{{{sub_area_name}}}\n{content}"

    def create_design_comment(self, content: str, title: str = "Design Note") -> str:
        """Create a design comment sidebar."""
        return EnvironmentWrapper.wrap_environment(
            content=content, environment=SidebarType.COMMENT.value, title=title
        )

    def optimize_sidebar_placement(self, content_blocks: list[str]) -> list[str]:
        """Optimize sidebar placement across content blocks."""
        optimized = []
        sidebar_count = 0

        for i, block in enumerate(content_blocks):
            if self._contains_sidebar(block):
                sidebar_count += 1

                # Spread sidebars evenly
                if sidebar_count > self.max_sidebars_per_page:
                    # Add page break suggestion
                    optimized.append("\\needspace{10\\baselineskip}\n")
                    sidebar_count = 1

                optimized.append(block)
            else:
                optimized.append(block)

                # Reset count after substantial content
                if len(block.strip()) > 200:
                    sidebar_count = max(0, sidebar_count - 1)

        return optimized

    def _contains_sidebar(self, content: str) -> bool:
        """Check if content contains sidebar environments."""
        sidebar_indicators = [
            "\\begin{DndSidebar}",
            "\\begin{DndComment}",
            "\\begin{DndReadAloud}",
            "\\DndArea{",
            "\\DndSubArea{",
        ]
        return any(indicator in content for indicator in sidebar_indicators)

    def get_sidebar_layout_hints(
        self, content_type: ContentType, content_length: int
    ) -> LayoutHint:
        """Get layout hints for optimal sidebar usage."""
        hint = LayoutHint()

        # Determine if content would benefit from sidebar treatment
        if content_length < 100:  # Short content works well in sidebars
            hint.sidebar_type = self.content_sidebar_types.get(content_type)
            hint.sidebar_position = FloatPosition.HERE
        elif content_length < 300:  # Medium content
            if content_type in {ContentType.FEAT, ContentType.SPELL}:
                hint.sidebar_type = SidebarType.COMMENT
                hint.sidebar_position = FloatPosition.BOTTOM

        # Adventure content gets special treatment
        if content_type == ContentType.ADVENTURE:
            # Check for read-aloud indicators
            hint.sidebar_type = SidebarType.READ_ALOUD
            hint.sidebar_position = FloatPosition.HERE

        return hint

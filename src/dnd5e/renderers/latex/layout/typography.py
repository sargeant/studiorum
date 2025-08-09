"""Advanced typography features for D&D content."""

from typing import Any

from ....core.models.content import ContentType
from ....core.registry import get_content_type_registry
from .base import (
    ContentLayoutManager,
    LayoutContext,
    LayoutHint,
)


class TypographyManager(ContentLayoutManager):
    """Manages advanced typography features for professional D&D documents."""

    def __init__(self, config: dict[str, Any] | None = None):
        """Initialize the typography manager."""
        super().__init__(config)

        # Typography preferences by content type (Phase 3 migration)
        self.content_typography = self._build_typography_preferences()

        # Font styles for different emphasis levels
        self.emphasis_styles = {
            "subtle": "\\emph",
            "medium": "\\textbf",
            "strong": "\\textsc",
        }

        # Special typography commands
        self.typography_commands = {
            "drop_cap": "\\lettrine",
            "small_caps": "\\textsc",
            "fancy_quote": "\\enquote",
            "game_term": "\\textit",
            "spell_name": "\\emph",
            "creature_name": "\\textbf",
        }

    def _build_typography_preferences(self) -> dict[ContentType, dict[str, Any]]:
        """Build content type to typography preferences mapping using registry.

        Returns dynamic mapping based on available content types,
        following Phase 3 migration pattern.

        Returns:
            Dictionary mapping content types to typography preferences
        """
        # Base typography preferences
        typography_map = {
            "adventure": {
                "use_drop_caps": True,
                "emphasis_style": "strong",
                "quote_style": "fancy",
            },
            "book": {
                "use_drop_caps": True,
                "emphasis_style": "strong",
                "quote_style": "fancy",
            },
            "class": {
                "use_drop_caps": False,
                "emphasis_style": "medium",
                "section_spacing": "loose",
            },
            "subclass": {
                "use_drop_caps": False,
                "emphasis_style": "medium",
                "section_spacing": "normal",
            },
            "race": {
                "use_drop_caps": False,
                "emphasis_style": "medium",
                "section_spacing": "normal",
            },
            "subrace": {
                "use_drop_caps": False,
                "emphasis_style": "subtle",
                "section_spacing": "normal",
            },
            "background": {
                "use_drop_caps": False,
                "emphasis_style": "medium",
                "section_spacing": "loose",
            },
            "spell": {
                "use_drop_caps": False,
                "emphasis_style": "subtle",
                "compact_spacing": True,
            },
            "item": {
                "use_drop_caps": False,
                "emphasis_style": "subtle",
                "compact_spacing": True,
            },
            "creature": {
                "use_drop_caps": False,
                "emphasis_style": "medium",
                "section_spacing": "compact",
            },
            "feat": {
                "use_drop_caps": False,
                "emphasis_style": "subtle",
                "compact_spacing": True,
            },
        }

        # Build preferences from registry
        registry = get_content_type_registry()
        preferences = {}

        for content_type_str, metadata in registry.get_all().items():
            try:
                content_type = ContentType(content_type_str)
            except ValueError:
                # Skip content types that don't exist as enum members (like fluff types)
                continue

            if content_type_str in typography_map:
                preferences[content_type] = typography_map[content_type_str]
            else:
                # Default typography for unknown content types
                preferences[content_type] = {
                    "use_drop_caps": False,
                    "emphasis_style": "subtle",
                    "compact_spacing": True,
                }

        return preferences

    def get_supported_content_types(self) -> set[ContentType]:
        """Support all registered content types for typography enhancement."""
        registry = get_content_type_registry()
        content_types = set()
        for content_type_str in registry.get_all():
            try:
                content_types.add(ContentType(content_type_str))
            except ValueError:
                # Skip content types that don't exist as enum members (like fluff types)
                continue
        return content_types

    def can_handle(self, context: LayoutContext) -> bool:
        """Handle typography for content that benefits from enhancement."""
        return bool(
            context.hints
            and (
                context.hints.use_drop_cap
                or context.hints.emphasis_level > 0
                or self._content_needs_typography(context)
            )
        )

    def get_priority(self) -> int:
        """Low-medium priority for typography (applied after layout)."""
        return 30

    def apply_layout(self, content: str, context: LayoutContext) -> str:
        """Apply typography enhancements to content."""
        if not content.strip():
            return content

        # Apply various typography enhancements
        enhanced_content = content

        # Drop caps for chapter/section beginnings
        if self._should_use_drop_cap(context):
            enhanced_content = self._apply_drop_cap(enhanced_content)

        # Game term emphasis
        enhanced_content = self._enhance_game_terms(enhanced_content, context)

        # Quote formatting
        enhanced_content = self._enhance_quotes(enhanced_content, context)

        # Spacing optimization
        enhanced_content = self._optimize_spacing(enhanced_content, context)

        # Special character handling
        enhanced_content = self._handle_special_characters(enhanced_content)

        return enhanced_content

    def _content_needs_typography(self, context: LayoutContext) -> bool:
        """Determine if content would benefit from typography enhancement."""
        content_type = context.content_type

        # Adventure content always benefits from typography
        if content_type.value == "adventure":
            return True

        # Long-form content benefits from typography
        long_form_types = {"class", "race", "background"}
        return content_type.value in long_form_types

    def _should_use_drop_cap(self, context: LayoutContext) -> bool:
        """Determine if drop caps should be used."""
        if context.hints and context.hints.use_drop_cap:
            return True

        # Use drop caps for adventure content and chapter beginnings
        if context.content_type.value == "adventure":
            return True

        return False

    def _apply_drop_cap(self, content: str) -> str:
        """Apply drop cap to the first letter of content."""
        lines = content.split("\n")
        if not lines:
            return content

        # Find first substantial paragraph
        first_paragraph_index = 0
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped and not stripped.startswith("\\") and len(stripped) > 20:
                first_paragraph_index = i
                break
        else:
            return content  # No suitable paragraph found

        first_line = lines[first_paragraph_index].strip()
        if len(first_line) < 5:
            return content

        # Extract first letter and rest of line
        first_char = first_line[0]
        rest_of_line = first_line[1:]

        # Apply lettrine (drop cap)
        drop_cap_line = (
            f"\\lettrine{{{first_char}}}{{{rest_of_line[:10]}}}{rest_of_line[10:]}"
        )

        lines[first_paragraph_index] = drop_cap_line
        return "\n".join(lines)

    def _enhance_game_terms(self, content: str, context: LayoutContext) -> str:
        """Enhance D&D game terms with appropriate typography."""
        # Common D&D terms that should be emphasized
        game_terms = [
            r"\bArmor Class\b",
            r"\bHit Points\b",
            r"\bChallenge Rating\b",
            r"\bProficiency Bonus\b",
            r"\bSaving Throw\b",
            r"\bAbility Check\b",
            r"\bAttack Roll\b",
            r"\bDamage Roll\b",
            r"\bInitiative\b",
            r"\bAdvantage\b",
            r"\bDisadvantage\b",
        ]

        # Spell names (capitalized words in quotes)
        spell_pattern = r'"([A-Z][a-z\s]+)"'

        # Creature names (when mentioned in text)
        creature_pattern = r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+\(CR\s+\d+\)"

        import re

        enhanced = content

        # Emphasize game terms
        for term_pattern in game_terms:
            enhanced = re.sub(
                term_pattern,
                lambda m: f"\\textit{{{m.group(0)}}}",
                enhanced,
                flags=re.IGNORECASE,
            )

        # Emphasize spell names
        enhanced = re.sub(spell_pattern, lambda m: f"\\emph{{{m.group(1)}}}", enhanced)

        # Emphasize creature names
        enhanced = re.sub(
            creature_pattern,
            lambda m: f"\\textbf{{{m.group(1)}}} (CR {m.group(2)})",
            enhanced,
        )

        return enhanced

    def _enhance_quotes(self, content: str, context: LayoutContext) -> str:
        """Enhance quotation marks and dialogue."""
        import re

        enhanced = content

        # Replace straight quotes with proper LaTeX quotes
        enhanced = re.sub(r'"([^"]+)"', r"``\1\'\'", enhanced)
        enhanced = re.sub(r"'([^']+)'", r"`\1\'", enhanced)

        # Enhance read-aloud text (often in italics)
        read_aloud_pattern = r"\*([^*]+)\*"
        enhanced = re.sub(read_aloud_pattern, r"\\textit{\1}", enhanced)

        return enhanced

    def _optimize_spacing(self, content: str, context: LayoutContext) -> str:
        """Optimize spacing for better typography."""
        content_type = context.content_type

        enhanced = content

        # Add proper spacing after sections
        if content_type.value in {"class", "race"}:
            enhanced = enhanced.replace("\n\n", "\n\n\\medskip\n")

        # Tighter spacing for compact content
        elif content_type.value in {"spell", "feat"}:
            enhanced = enhanced.replace("\n\n\n", "\n\n")

        # Adventure content gets loose spacing
        elif content_type.value == "adventure":
            enhanced = enhanced.replace("\n\n", "\n\n\\bigskip\n")

        return enhanced

    def _handle_special_characters(self, content: str) -> str:
        """Handle special characters and symbols properly."""
        # Common replacements for better typography
        replacements = {
            "...": "\\ldots{}",
            "--": "---",  # em dash
            " - ": " --- ",  # em dash with spaces
            "(c)": "\\copyright{}",
            "(r)": "\\textregistered{}",
            "(tm)": "\\texttrademark{}",
            "1/2": "\\textonehalf{}",
            "1/4": "\\textonequarter{}",
            "3/4": "\\textthreequarters{}",
        }

        enhanced = content
        for find, replace in replacements.items():
            enhanced = enhanced.replace(find, replace)

        # Handle degree symbols
        import re

        enhanced = re.sub(r"(\d+)\s*degrees?", r"\1\\degree{}", enhanced)

        return enhanced

    def create_fancy_header(self, title: str, level: int = 1) -> str:
        """Create a fancy header with appropriate typography."""
        if level == 1:
            return f"\\section{{\\textsc{{{title}}}}}"
        elif level == 2:
            return f"\\subsection{{\\textbf{{{title}}}}}"
        elif level == 3:
            return f"\\subsubsection{{\\emph{{{title}}}}}"
        else:
            return f"\\paragraph{{{title}}}"

    def create_emphasis_text(self, text: str, level: int = 1) -> str:
        """Create emphasized text with appropriate level."""
        if level == 1:
            return f"\\emph{{{text}}}"
        elif level == 2:
            return f"\\textbf{{{text}}}"
        elif level == 3:
            return f"\\textsc{{{text}}}"
        else:
            return text

    def create_game_term(self, term: str) -> str:
        """Format a D&D game term appropriately."""
        return f"\\textit{{{term}}}"

    def create_spell_reference(self, spell_name: str) -> str:
        """Create a properly formatted spell reference."""
        return f"\\emph{{{spell_name}}}"

    def create_creature_reference(
        self, creature_name: str, cr: str | None = None
    ) -> str:
        """Create a properly formatted creature reference."""
        if cr:
            return f"\\textbf{{{creature_name}}} (CR {cr})"
        else:
            return f"\\textbf{{{creature_name}}}"

    def add_kerning_optimization(self, content: str) -> str:
        """Add kerning optimization for better character spacing."""
        # Common letter combinations that benefit from kerning
        kerning_pairs = {
            "AV": "A\\kern-0.1em V",
            "AW": "A\\kern-0.1em W",
            "AY": "A\\kern-0.1em Y",
            "FA": "F\\kern-0.1em A",
            "LT": "L\\kern-0.1em T",
            "LV": "L\\kern-0.1em V",
            "LW": "L\\kern-0.1em W",
            "LY": "L\\kern-0.1em Y",
            "PA": "P\\kern-0.1em A",
            "TA": "T\\kern-0.1em A",
            "VA": "V\\kern-0.1em A",
            "WA": "W\\kern-0.1em A",
            "YA": "Y\\kern-0.1em A",
        }

        enhanced = content
        for pair, replacement in kerning_pairs.items():
            enhanced = enhanced.replace(pair, replacement)

        return enhanced

    def get_typography_layout_hints(self, content_type: ContentType) -> LayoutHint:
        """Get layout hints optimized for typography."""
        hint = LayoutHint()

        # Set typography preferences based on content type
        if content_type.value == "adventure":
            hint.use_drop_cap = True
            hint.emphasis_level = 2
            hint.space_before = "\\bigskip"
            hint.space_after = "\\medskip"
        elif content_type.value in {"class", "race"}:
            hint.emphasis_level = 1
            hint.space_before = "\\medskip"
            hint.space_after = "\\smallskip"
        elif content_type.value in {"spell", "feat"}:
            hint.emphasis_level = 1
            hint.space_before = "\\smallskip"

        return hint

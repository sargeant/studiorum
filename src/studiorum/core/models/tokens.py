"""Token data models for 5e creature tokens."""

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..services.token_image_resolver import TokenImageResolver
    from .creatures import Creature


@dataclass
class TokenData:
    """Individual token data for a single creature."""

    creature_name: str
    image_path: Path | None
    size: str | list[str]  # Creatures can have multiple sizes
    count: int = 1
    source: str = ""
    cr: str = ""

    def get_display_name(self) -> str:
        """Get display name for the token."""
        return self.creature_name

    def get_size_category(self) -> str:
        """Get normalized size category for layout purposes."""
        # Normalize size abbreviations to full names
        size_mapping = {
            "T": "tiny",
            "S": "small",
            "M": "medium",
            "L": "large",
            "H": "huge",
            "G": "gargantuan",
        }

        if isinstance(self.size, list):
            # Use first size if multiple
            primary_size = self.size[0] if self.size else "medium"
        else:
            primary_size = str(self.size)

        # Convert to lowercase and map abbreviations
        normalized = primary_size.lower()
        return size_mapping.get(normalized.upper(), normalized)


@dataclass
class TokenSheet:
    """Complete token sheet configuration and data."""

    tokens_by_size: dict[str, list[TokenData]]
    paper_size: str
    margins: float
    column_config: dict[str, int]

    @classmethod
    def from_creatures(
        cls,
        creatures: list["Creature"],
        image_resolver: "TokenImageResolver",
        default_count: int = 1,
        paper_size: str = "letter",
        margins: float = 0.25,
        column_config: dict[str, int] | None = None,
    ) -> "TokenSheet":
        """Create token sheet from creature list."""
        if column_config is None:
            column_config = {
                "tiny": 6,
                "small": 6,
                "medium": 6,
                "large": 3,
                "huge": 2,
                "gargantuan": 1,
            }

        # Group tokens by size
        tokens_by_size: dict[str, list[TokenData]] = {}

        for creature in creatures:
            # Resolve token image - this now automatically converts WebP to PNG
            image_path = image_resolver.resolve_token_image(creature)

            # Extract creature info
            creature_size = creature.size if hasattr(creature, "size") else ["M"]
            creature_source = (
                creature.source.abbreviation
                if hasattr(creature, "source")
                and hasattr(creature.source, "abbreviation")
                else ""
            )
            creature_cr = (
                creature.get_cr_text() if hasattr(creature, "get_cr_text") else ""
            )

            # Create token data
            token = TokenData(
                creature_name=creature.name,
                image_path=image_path,  # Already converted to PNG if needed
                size=creature_size,
                count=default_count,
                source=creature_source,
                cr=creature_cr,
            )

            # Get normalized size category
            size_category = token.get_size_category()

            # Add to appropriate size group
            if size_category not in tokens_by_size:
                tokens_by_size[size_category] = []
            tokens_by_size[size_category].append(token)

        return cls(
            tokens_by_size=tokens_by_size,
            paper_size=paper_size,
            margins=margins,
            column_config=column_config,
        )

    def get_size_order(self) -> list[str]:
        """Get ordered list of sizes for rendering."""
        # Standard 5e size order
        size_order = ["tiny", "small", "medium", "large", "huge", "gargantuan"]
        return [size for size in size_order if size in self.tokens_by_size]

    def get_total_token_count(self) -> int:
        """Get total number of tokens across all sizes."""
        total = 0
        for size_tokens in self.tokens_by_size.values():
            total += sum(token.count for token in size_tokens)
        return total

    def get_tokens_for_size(self, size: str) -> list[TokenData]:
        """Get all tokens for a specific size category."""
        return self.tokens_by_size.get(size, [])

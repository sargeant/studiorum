"""ItemProperty content type models for D&D 5e.

Provides Pydantic models for weapon and armor properties that define
special characteristics and behaviors of equipment.
"""

from typing import Any

from pydantic import Field

from ..registry import content_type
from .content import BaseContent


@content_type(
    enum_value="itemProperty",
    file_patterns=["itemProperty", "itemproperties", "items-base"],
    loader_type="json",
    statblock_tags=["itemProperty"],
)
class ItemProperty(BaseContent):
    """An item property that defines special weapon or armor characteristics.

    Item properties represent standardized characteristics like 'finesse',
    'heavy', 'versatile' that can be applied to weapons and armor to
    define their special behaviors and requirements.
    """

    # Core identifying information
    abbreviation: str = Field(..., description="Short abbreviation for the property")
    template: str | None = Field(None, description="Template string for rendering")

    # Property classification
    category: str | None = Field(None, description="Property category")
    applies_to: list[str] = Field(
        default_factory=list,
        alias="appliesTo",
        description="What types of items this property applies to",
    )

    # Mechanical effects
    effects: list[dict[str, Any]] = Field(
        default_factory=list, description="Mechanical effects of this property"
    )
    prerequisites: dict[str, Any] | None = Field(
        None, description="Prerequisites for using this property"
    )
    restrictions: list[str] = Field(
        default_factory=list, description="Restrictions imposed by this property"
    )

    # Display and reference
    display_name: str | None = Field(
        None, alias="displayName", description="Full display name of the property"
    )

    def get_display_name(self) -> str:
        """Get display name for the property."""
        if self.display_name:
            return self.display_name
        # Try to extract from entries if available
        if self.entries:
            for entry in self.entries:
                if isinstance(entry, dict) and entry.get("name"):
                    return entry["name"]
        return self.name

    def get_abbreviation(self) -> str:
        """Get the property abbreviation."""
        return self.abbreviation

    def has_template(self) -> bool:
        """Check if this property has a template."""
        return bool(self.template)

    def has_effects(self) -> bool:
        """Check if this property has defined mechanical effects."""
        return len(self.effects) > 0

    def has_prerequisites(self) -> bool:
        """Check if this property has prerequisites."""
        return self.prerequisites is not None

    def has_restrictions(self) -> bool:
        """Check if this property imposes restrictions."""
        return len(self.restrictions) > 0

    def applies_to_item_type(self, item_type: str) -> bool:
        """Check if this property applies to a specific item type."""
        if not self.applies_to:
            return True  # No restrictions means applies to all
        return item_type.lower() in [t.lower() for t in self.applies_to]

    def get_template_variables(self) -> list[str]:
        """Extract template variables from the template string."""
        if not self.template:
            return []

        import re

        # Find all {{variable}} patterns
        variables = re.findall(r"\{\{(\w+)\}\}", self.template)
        return variables

    def render_template(self, variables: dict[str, str] | None = None) -> str:
        """Render the template with provided variables."""
        if not self.template:
            return self.get_display_name()

        if not variables:
            variables = {}

        # Default variables
        default_vars = {
            "prop_name": self.get_display_name(),
            "prop_name_lower": self.get_display_name().lower(),
            "abbreviation": self.abbreviation,
        }

        # Merge with provided variables
        render_vars = {**default_vars, **variables}

        # Simple template rendering
        result = self.template
        for var, value in render_vars.items():
            result = result.replace("{{" + var + "}}", str(value))

        return result

    def is_weapon_property(self) -> bool:
        """Check if this is a weapon property."""
        weapon_indicators = ["weapon", "attack", "damage", "range"]
        property_name = self.name.lower()

        for indicator in weapon_indicators:
            if indicator in property_name:
                return True

        # Check if applies_to includes weapons
        if self.applies_to:
            return any("weapon" in item_type.lower() for item_type in self.applies_to)

        return False

    def is_armor_property(self) -> bool:
        """Check if this is an armor property."""
        armor_indicators = ["armor", "ac", "defense"]
        property_name = self.name.lower()

        for indicator in armor_indicators:
            if indicator in property_name:
                return True

        # Check if applies_to includes armor
        if self.applies_to:
            return any("armor" in item_type.lower() for item_type in self.applies_to)

        return False

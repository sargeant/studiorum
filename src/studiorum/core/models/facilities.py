"""Facility content models for bastion building systems."""

from typing import Any

from pydantic import BaseModel, Field

from ..registry import content_type
from .content import BaseContent


class FacilityHirelings(BaseModel):
    """Represents hireling requirements for a facility."""

    exact: int | None = Field(None, description="Exact number of hirelings needed")
    min: int | None = Field(None, description="Minimum hirelings needed")
    max: int | None = Field(None, description="Maximum hirelings supported")

    def get_hireling_count(self) -> str:
        """Get a formatted hireling count description."""
        if self.exact:
            return str(self.exact)
        elif self.min and self.max:
            return f"{self.min}-{self.max}"
        elif self.min:
            return f"{self.min}+"
        else:
            return "0"


class FacilityPrerequisite(BaseModel):
    """Represents prerequisites for building a facility."""

    spellcasting_focus: list[str] | bool | None = Field(
        None, alias="spellcastingFocus", description="Required spellcasting focus types"
    )
    level: int | None = Field(None, description="Minimum character level")
    other: str | None = Field(None, description="Other prerequisites")


@content_type(
    enum_value="facility",
    file_patterns=["facility", "facilities", "bastions"],
    loader_type="json",
    statblock_tags=["facility"],
)
class Facility(BaseContent):
    """Bastion facilities for stronghold construction."""

    # Core facility properties
    facility_type: str = Field(
        ..., alias="facilityType", description="Type of facility (basic, special)"
    )
    level: int | None = Field(None, description="Facility level requirement")

    # Prerequisites
    prerequisite: list[FacilityPrerequisite] = Field(
        default_factory=list, description="Prerequisites for construction"
    )

    # Space and staffing
    space: list[str] = Field(
        default_factory=list, description="Space requirements (cramped, roomy, etc.)"
    )
    hirelings: list[FacilityHirelings] = Field(
        default_factory=list, description="Hireling requirements"
    )

    # Functionality
    orders: list[str] = Field(
        default_factory=list, description="Available orders/actions"
    )

    # Optional properties
    cost: dict[str, Any] | None = Field(None, description="Construction cost")
    maintenance: dict[str, Any] | None = Field(
        None, description="Maintenance requirements"
    )

    def is_basic_facility(self) -> bool:
        """Check if this is a basic facility."""
        return self.facility_type == "basic"

    def is_special_facility(self) -> bool:
        """Check if this is a special facility."""
        return self.facility_type == "special"

    def get_space_requirement(self) -> str:
        """Get the primary space requirement."""
        return self.space[0] if self.space else "unknown"

    def requires_spellcasting(self) -> bool:
        """Check if facility requires spellcasting ability."""
        for prereq in self.prerequisite:
            if prereq.spellcasting_focus:
                return True
        return False

    def get_required_focus_types(self) -> list[str]:
        """Get all required spellcasting focus types."""
        focus_types: list[str] = []
        for prereq in self.prerequisite:
            if prereq.spellcasting_focus:
                if isinstance(prereq.spellcasting_focus, list):
                    focus_types.extend(prereq.spellcasting_focus)
                elif isinstance(prereq.spellcasting_focus, bool):
                    focus_types.append("any")
        return list(set(focus_types))  # Remove duplicates

    def get_hireling_requirement(self) -> str:
        """Get a summary of hireling requirements."""
        if not self.hirelings:
            return "0"
        return self.hirelings[0].get_hireling_count()

    def supports_order(self, order: str) -> bool:
        """Check if facility supports a specific order."""
        return order in self.orders

    def get_available_orders(self) -> list[str]:
        """Get all available orders."""
        return self.orders.copy()

    def is_cramped(self) -> bool:
        """Check if facility has cramped space."""
        return "cramped" in self.space

    def is_roomy(self) -> bool:
        """Check if facility has roomy space."""
        return "roomy" in self.space

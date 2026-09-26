"""Facility content models for bastion building systems."""

from typing import Any

from pydantic import BaseModel, Field

from .content import BaseContent
from .feats import Prerequisite


class FacilityHirelings(BaseModel):
    """Represents hireling requirements for a facility."""

    exact: int | None = Field(None, description="Exact number of hirelings needed")
    min: int | None = Field(None, description="Minimum hirelings needed")
    max: int | None = Field(None, description="Maximum hirelings supported")
    space: str | None = Field(None, description="The facility size this applies to")


class Facility(BaseContent):
    """Bastion facilities for stronghold construction."""

    # Core facility properties
    facility_type: str = Field(
        ..., alias="facilityType", description="Type of facility (basic, special)"
    )
    level: int | None = Field(None, description="Facility level requirement")

    # Prerequisites
    prerequisite: list[Prerequisite] = Field(
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

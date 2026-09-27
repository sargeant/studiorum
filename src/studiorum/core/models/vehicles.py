"""Vehicle models for 5e content."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from studiorum.core.models.content import BaseContent
from studiorum.core.models.feats import Prerequisite


class VehicleArmor(BaseModel):
    """Vehicle armor class information."""

    ac: int = Field(..., description="Armor class value")
    from_: list[str] = Field(
        default_factory=list, alias="from", description="Armor source"
    )


class VehicleHitPoints(BaseModel):
    """Vehicle hit points information."""

    hp: int | None = Field(None, description="Hit points")
    average: int | None = Field(None, description="Average hit points")
    formula: str | None = Field(None, description="Hit point formula")
    dt: int | None = Field(None, description="Damage threshold")
    mt: int | None = Field(None, description="Mishap threshold")


class Vehicle(BaseContent):
    """Represents a 5e vehicle (ship, land vehicle, etc.)."""

    vehicle_type: str | None = Field(
        None, alias="vehicleType", description="Type of vehicle"
    )
    size: list[str] | str | None = Field(None, description="Vehicle size")
    dimensions: list[str] | None = Field(None, description="Vehicle dimensions")
    weight: int | None = Field(None, description="Vehicle weight in pounds")
    cost: int | None = Field(None, description="Vehicle cost in copper pieces")
    ac: list[int | VehicleArmor] | int | None = Field(
        None, description="Base armor class"
    )
    hp: int | VehicleHitPoints | dict[str, Any] | None = Field(
        None, description="Base hit points"
    )
    speed: int | dict[str, Any] | None = Field(None, description="Base speed")
    entries: list[str | dict[str, Any]] | None = Field(
        None, description="Vehicle description"
    )

    def __str__(self) -> str:
        return f"{self.name} ({self.source})"


class VehicleUpgrade(BaseContent):
    """A ship upgrade or an infernal war machine's weapon, armour or gadget."""

    upgrade_type: list[str] = Field(
        default_factory=list, alias="upgradeType", description="Upgrade type codes"
    )
    prerequisite: list[Prerequisite] | None = None
    cost: int | None = Field(None, description="Cost in copper pieces")
    entries: list[Any] = Field(default_factory=list)

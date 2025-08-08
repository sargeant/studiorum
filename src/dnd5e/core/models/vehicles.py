"""Vehicle models for D&D content."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from ..registry import content_type
from .content import BaseContent, Source


class VehicleArmor(BaseModel):
    """Vehicle armor class information."""

    ac: int = Field(..., description="Armor class value")
    from_: list[str] = Field(
        default_factory=list, alias="from", description="Armor source"
    )


class VehicleHitPoints(BaseModel):
    """Vehicle hit points information."""

    hp: int = Field(..., description="Hit points")
    dt: int | None = Field(None, description="Damage threshold")


class VehicleSpeed(BaseModel):
    """Vehicle speed information."""

    mode: str = Field(..., description="Movement mode (e.g., 'sail', 'walk')")
    speed: int = Field(..., description="Speed value")
    condition: str | None = Field(None, description="Speed condition")


@content_type(
    enum_value="vehicle",
    file_patterns=["vehicle", "vehicles"],
    statblock_tags=["vehicle"],
    loader_type="json",
)
class Vehicle(BaseContent):
    """Represents a D&D vehicle (ship, land vehicle, etc.)."""

    vehicle_type: str | None = Field(
        None, alias="vehicleType", description="Type of vehicle"
    )
    size: list[str] = Field(default_factory=list, description="Vehicle size")
    dimensions: list[str] = Field(
        default_factory=list, description="Vehicle dimensions"
    )
    weight: int | None = Field(None, description="Vehicle weight in pounds")
    cost: int | None = Field(None, description="Vehicle cost in copper pieces")
    ac: list[int] = Field(default_factory=list, description="Base armor class")
    hp: int | None = Field(None, description="Base hit points")
    speed: int | None = Field(None, description="Base speed")
    carrying_capacity: int | None = Field(
        None, alias="carryingCapacity", description="Carrying capacity in pounds"
    )
    crew: int | None = Field(None, description="Required crew size")
    passenger: int | None = Field(None, description="Passenger capacity")

    # Enhanced vehicle stats
    veh_ac: list[VehicleArmor] = Field(
        default_factory=list, alias="vehAc", description="Vehicle armor class details"
    )
    veh_hp: list[VehicleHitPoints] = Field(
        default_factory=list, alias="vehHp", description="Vehicle hit points details"
    )
    veh_speed: list[VehicleSpeed] = Field(
        default_factory=list, alias="vehSpeed", description="Vehicle speed details"
    )

    # Description and entries
    entries: list[str | dict[str, Any]] = Field(
        default_factory=list, description="Vehicle description"
    )

    def __str__(self) -> str:
        return f"{self.name} ({self.source})"

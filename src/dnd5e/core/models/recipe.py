"""Recipe content model."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import Field, field_validator

from ..registry import content_type
from .content import BaseContent
from .entry_types import Entry


class DishType(str, Enum):
    """Enumeration of dish types."""

    ENTREE = "entree"
    SNACK = "snack"
    DESSERT = "dessert"
    SIDE = "side"
    APPETIZER = "appetizer"
    DRINK = "drink"
    SOUP = "soup"
    SALAD = "salad"
    UNKNOWN = "unknown"


class DietType(str, Enum):
    """Enumeration of dietary classifications."""

    CARNIVOROUS = "C"  # Carnivorous
    VEGETARIAN = "V"  # Vegetarian
    OMNIVOROUS = "O"  # Omnivorous
    UNKNOWN = "X"  # Unknown/Not specified


@content_type(
    enum_value="recipe",
    file_patterns=["recipe", "recipes"],
    loader_type="json",
    statblock_tags=["recipe"],
)
class Recipe(BaseContent):
    """Recipe model for cooking recipes and culinary content.

    Recipes represent D&D-themed cooking instructions with ingredients,
    dietary information, and serving details.
    """

    # Required fields
    recipe_type: str = Field(..., description="Type of recipe", alias="type")
    ingredients: list[dict[str, Any]] = Field(
        ..., description="Recipe ingredients with amounts"
    )
    instructions: list[str] = Field(..., description="Cooking instructions")

    # Optional fields
    alias: list[str] | None = Field(None, description="Alternative names")
    dish_types: list[DishType] = Field(
        default_factory=list, description="Types of dish", alias="dishTypes"
    )
    diet: DietType = Field(DietType.UNKNOWN, description="Dietary classification")
    serves: dict[str, Any] | None = Field(None, description="Serving information")
    makes: dict[str, Any] | None = Field(None, description="Quantity made")
    time: dict[str, Any] | None = Field(None, description="Cooking times")
    equipment: list[str] | None = Field(None, description="Required equipment")
    entries: list[Entry] = Field(
        default_factory=list, description="Additional description entries"
    )
    fluff: list[Entry] | None = Field(None, description="Flavor text")
    additional_sources: list[dict[str, Any]] | None = Field(
        None,
        description="Additional sources for this recipe",
        alias="additionalSources",
    )
    other_sources: list[dict[str, Any]] | None = Field(
        None,
        description="Other sources that reference this recipe",
        alias="otherSources",
    )
    reprinted_as: list[str] | None = Field(
        None, description="Reprints of this recipe", alias="reprintedAs"
    )

    @field_validator("recipe_type", mode="before")
    @classmethod
    def validate_recipe_type(cls, v: Any) -> str:
        """Validate recipe type."""
        if not v:
            raise ValueError("Recipe type cannot be empty")
        return str(v)

    @field_validator("ingredients", mode="before")
    @classmethod
    def validate_ingredients(cls, v: Any) -> list[dict[str, Any]]:
        """Validate ingredients structure."""
        if not v or not isinstance(v, list):
            raise ValueError("Recipe must have ingredients")
        return list(v)  # Explicit conversion to ensure type safety

    @field_validator("instructions", mode="before")
    @classmethod
    def validate_instructions(cls, v: Any) -> list[str]:
        """Validate instructions structure."""
        if not v or not isinstance(v, list):
            raise ValueError("Recipe must have instructions")
        return [str(item) for item in v]  # Explicit conversion to ensure type safety

    @field_validator("dish_types", mode="before")
    @classmethod
    def validate_dish_types(cls, v: Any) -> list[DishType]:
        """Validate and normalize dish types."""
        if not v:
            return []
        if isinstance(v, str):
            try:
                return [DishType(v.lower())]
            except ValueError:
                return [DishType.UNKNOWN]
        if isinstance(v, list):
            types = []
            for item in v:
                try:
                    types.append(DishType(str(item).lower()))
                except ValueError:
                    types.append(DishType.UNKNOWN)
            return types
        return []

    @field_validator("diet", mode="before")
    @classmethod
    def validate_diet(cls, v: Any) -> DietType:
        """Validate and normalize diet type."""
        if isinstance(v, str):
            try:
                return DietType(v.upper())
            except ValueError:
                return DietType.UNKNOWN
        return DietType.UNKNOWN

    @field_validator("name", mode="before")
    @classmethod
    def validate_name(cls, v: Any) -> str:
        """Validate that name is not empty."""
        if not v or not str(v).strip():
            raise ValueError("Recipe name cannot be empty")
        return str(v).strip()

    def get_recipe_type(self) -> str:
        """Get the recipe type."""
        return self.recipe_type

    def get_dish_types(self) -> list[DishType]:
        """Get list of dish types."""
        return self.dish_types or []

    def get_primary_dish_type(self) -> DishType:
        """Get the primary (first) dish type."""
        types = self.get_dish_types()
        return types[0] if types else DishType.UNKNOWN

    def get_diet_type(self) -> DietType:
        """Get the dietary classification."""
        return self.diet

    def get_diet_description(self) -> str:
        """Get human-readable diet description."""
        descriptions = {
            DietType.CARNIVOROUS: "Carnivorous",
            DietType.VEGETARIAN: "Vegetarian",
            DietType.OMNIVOROUS: "Omnivorous",
            DietType.UNKNOWN: "Not specified",
        }
        return descriptions.get(self.diet, "Unknown")

    def is_vegetarian(self) -> bool:
        """Check if recipe is vegetarian."""
        return self.diet == DietType.VEGETARIAN

    def is_carnivorous(self) -> bool:
        """Check if recipe is carnivorous."""
        return self.diet == DietType.CARNIVOROUS

    def is_omnivorous(self) -> bool:
        """Check if recipe is omnivorous."""
        return self.diet == DietType.OMNIVOROUS

    def has_serving_info(self) -> bool:
        """Check if recipe has serving information."""
        return bool(self.serves)

    def has_makes_info(self) -> bool:
        """Check if recipe has quantity information."""
        return bool(self.makes)

    def has_timing_info(self) -> bool:
        """Check if recipe has timing information."""
        return bool(self.time)

    def requires_equipment(self) -> bool:
        """Check if recipe requires special equipment."""
        return bool(self.equipment)

    def get_ingredient_count(self) -> int:
        """Get the number of ingredients."""
        return len(self.ingredients)

    def get_instruction_count(self) -> int:
        """Get the number of instruction steps."""
        return len(self.instructions)

    def get_serving_count(self) -> int | None:
        """Get exact serving count if available."""
        if not self.serves:
            return None
        if isinstance(self.serves, dict):
            return self.serves.get("exact")
        return None

    def get_serving_note(self) -> str | None:
        """Get serving note if available."""
        if not self.serves:
            return None
        if isinstance(self.serves, dict):
            return self.serves.get("note")
        return None

    def get_prep_time(self) -> str | None:
        """Get preparation time if available."""
        if not self.time or not isinstance(self.time, dict):
            return None
        return self.time.get("prep")

    def get_cook_time(self) -> str | None:
        """Get cooking time if available."""
        if not self.time or not isinstance(self.time, dict):
            return None
        return self.time.get("cook")

    def get_total_time(self) -> str | None:
        """Get total time if available."""
        if not self.time or not isinstance(self.time, dict):
            return None
        return self.time.get("total")

    def get_equipment_list(self) -> list[str]:
        """Get list of required equipment."""
        return self.equipment or []

    def get_ingredient_by_type(self, ingredient_type: str) -> list[dict[str, Any]]:
        """Get ingredients of a specific type."""
        return [ing for ing in self.ingredients if ing.get("type") == ingredient_type]

    def has_alias(self) -> bool:
        """Check if recipe has alternative names."""
        return bool(self.alias)

    def get_aliases(self) -> list[str]:
        """Get list of alternative names."""
        return self.alias or []

    def has_fluff(self) -> bool:
        """Check if recipe has flavor text."""
        return bool(self.fluff)

    def get_complexity_rating(self) -> str:
        """Get a complexity rating based on ingredients and instructions."""
        ingredient_count = self.get_ingredient_count()
        instruction_count = self.get_instruction_count()
        equipment_required = self.requires_equipment()

        complexity_score = ingredient_count + instruction_count
        if equipment_required:
            complexity_score += 2

        if complexity_score <= 5:
            return "Simple"
        elif complexity_score <= 10:
            return "Moderate"
        else:
            return "Complex"

    def get_recipe_summary(self) -> str:
        """Get a summary description of this recipe."""
        parts = [self.get_diet_description()]

        dish_types = self.get_dish_types()
        if dish_types and dish_types[0] != DishType.UNKNOWN:
            # Handle both string and enum values for robustness
            dish_names = []
            for dt in dish_types:
                if isinstance(dt, DishType):
                    dish_names.append(dt.value)
                else:
                    dish_names.append(str(dt))
            parts.append(f"{'/'.join(dish_names)}")

        parts.append(f"{self.get_ingredient_count()} ingredients")
        parts.append(f"{self.get_instruction_count()} steps")
        parts.append(f"{self.get_complexity_rating().lower()} complexity")

        if self.has_serving_info():
            serving_count = self.get_serving_count()
            if serving_count:
                parts.append(f"serves {serving_count}")

        return ", ".join(parts)

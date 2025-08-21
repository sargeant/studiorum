"""Recipe content models for crafting and cooking systems."""

from typing import Any

from pydantic import BaseModel, Field

from ..registry import content_type
from .content import BaseContent


class RecipeIngredient(BaseModel):
    """Represents an ingredient in a recipe."""

    type: str = Field("ingredient", description="Type of ingredient entry")
    entry: str = Field(..., description="Ingredient description with amounts")
    amount1: float | None = Field(None, description="Primary amount")
    amount2: float | None = Field(None, description="Secondary amount")

    def get_description(self) -> str:
        """Get the formatted ingredient description."""
        return self.entry


class RecipeServing(BaseModel):
    """Represents serving information for a recipe."""

    note: str | None = Field(None, description="Serving note (e.g., 'as a snack')")
    exact: int | None = Field(None, description="Exact number of servings")
    min: int | None = Field(None, description="Minimum servings")
    max: int | None = Field(None, description="Maximum servings")

    def get_serving_description(self) -> str:
        """Get a formatted serving description."""
        if self.exact:
            base = f"Serves {self.exact}"
        elif self.min and self.max:
            base = f"Serves {self.min}-{self.max}"
        elif self.min:
            base = f"Serves {self.min}+"
        else:
            base = "Serves unknown"

        if self.note:
            return f"{base} {self.note}"
        return base


@content_type(
    enum_value="recipe",
    file_patterns=["recipe", "recipes"],
    loader_type="json",
    statblock_tags=["recipe"],
)
class Recipe(BaseContent):
    """Crafting and cooking recipes."""

    # Core recipe properties
    alias: list[str] = Field(default_factory=list, description="Alternative names")
    type: str | None = Field(
        None, description="Recipe category (Uncommon Cuisine, etc.)"
    )

    # Recipe classification
    dish_types: list[str] = Field(
        default_factory=list, alias="dishTypes", description="Types of dish"
    )
    diet: str | None = Field(None, description="Dietary requirements")

    # Serving information
    serves: RecipeServing | None = Field(None, description="Serving information")

    # Ingredients and instructions
    ingredients: list[RecipeIngredient] = Field(
        default_factory=list, description="Recipe ingredients"
    )
    instructions: list[str] = Field(
        default_factory=list, description="Cooking/crafting instructions"
    )

    # Time and difficulty
    time: dict[str, Any] | None = Field(
        None, description="Preparation and cooking times"
    )
    difficulty: str | None = Field(None, description="Recipe difficulty level")

    # Equipment needed
    equipment: list[str] = Field(
        default_factory=list, description="Required tools/equipment"
    )

    def get_primary_name(self) -> str:
        """Get the primary name (first alias if available, otherwise name)."""
        return self.alias[0] if self.alias else self.name

    def get_all_names(self) -> list[str]:
        """Get all names including aliases."""
        names = [self.name]
        names.extend(self.alias)
        return names

    def is_cuisine(self) -> bool:
        """Check if this is a cooking recipe."""
        return bool(self.type and "cuisine" in self.type.lower())

    def is_crafting(self) -> bool:
        """Check if this is a crafting recipe."""
        return not self.is_cuisine()

    def get_ingredient_count(self) -> int:
        """Get the number of ingredients."""
        return len(self.ingredients)

    def has_dietary_restrictions(self) -> bool:
        """Check if recipe has dietary restrictions."""
        return self.diet is not None and self.diet != ""

    def get_dish_type_display(self) -> str:
        """Get a display string for dish types."""
        return ", ".join(self.dish_types) if self.dish_types else "unspecified"

"""Tests for Recipe content type migration to decorator system."""

import pytest
from pydantic import ValidationError

from tests.test_helpers import reset_test_environment


class TestRecipeMigration:
    """Test Recipe content type decorator registration and functionality."""

    def setup_method(self) -> None:
        """Set up test fixtures with complete environment reset."""
        reset_test_environment()

    def test_recipe_decorator_registers_automatically(self) -> None:
        """Test that @content_type decorator registers Recipe automatically."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        # Verify enum was created dynamically
        from dnd5e.core.models.content import ContentType

        assert hasattr(ContentType, "RECIPE")
        assert ContentType.RECIPE == "recipe"

    def test_recipe_content_factory_integration(self) -> None:
        """Test Recipe works with ContentFactory."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test creating an "Orc" Bacon recipe
        orc_bacon_data = {
            "name": '"Orc" Bacon',
            "alias": ["The Pork of Gruumsh"],
            "source": {"abbreviation": "HF", "full": "Heroes' Feast"},
            "page": 156,
            "type": "Uncommon Cuisine",
            "dishTypes": ["snack"],
            "diet": "X",
            "serves": {"note": "as a snack", "exact": 4},
            "ingredients": [
                {
                    "type": "ingredient",
                    "entry": "{=amount1/v} pound thick-cut bacon",
                    "amount1": 1,
                },
                {
                    "type": "ingredient",
                    "entry": "{=amount1/v} tablespoons light brown sugar",
                    "amount1": 3,
                },
                {
                    "type": "ingredient",
                    "entry": "{=amount1/v} teaspoon freshly ground black pepper",
                    "amount1": 0.5,
                },
            ],
            "instructions": [
                "Preheat the oven to 375°F with a rack in the middle of the oven.",
                "Arrange the bacon slices on the rack, laying them tight against each other.",
                "Meanwhile, in a small bowl, mix together the brown sugar, pepper, garlic powder, and orange juice.",
            ],
        }

        content = factory.create_content(orc_bacon_data, ContentType.RECIPE)

        assert content.name == '"Orc" Bacon'
        assert content.source.abbreviation == "HF"
        assert content.get_recipe_type() == "Uncommon Cuisine"
        assert content.get_ingredient_count() == 3
        assert content.get_instruction_count() == 3
        assert content.has_alias() is True
        assert "The Pork of Gruumsh" in content.get_aliases()
        assert content.get_serving_count() == 4
        assert content.get_serving_note() == "as a snack"

    def test_recipe_dish_types_and_diet(self) -> None:
        """Test Recipe dish type and diet classification."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType
        from dnd5e.core.models.recipe import DietType, DishType

        factory = ContentFactory()

        # Test vegetarian dessert
        dessert_data = {
            "name": "Elven Honey Cakes",
            "source": {"abbreviation": "TEST", "full": "Test Source"},
            "type": "Dessert",
            "dishTypes": ["dessert"],
            "diet": "V",
            "ingredients": [
                {"type": "ingredient", "entry": "2 cups flour"},
                {"type": "ingredient", "entry": "1 cup honey"},
            ],
            "instructions": ["Mix ingredients.", "Bake until golden."],
        }

        content = factory.create_content(dessert_data, ContentType.RECIPE)

        assert content.get_primary_dish_type() == DishType.DESSERT
        assert content.get_diet_type() == DietType.VEGETARIAN
        assert content.is_vegetarian() is True
        assert content.is_carnivorous() is False
        assert content.get_diet_description() == "Vegetarian"

    def test_recipe_serving_and_timing_info(self) -> None:
        """Test Recipe serving and timing information."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test comprehensive timing and serving
        timed_data = {
            "name": "Dragon Steak",
            "source": {"abbreviation": "TEST", "full": "Test Source"},
            "type": "Main Course",
            "dishTypes": ["entree"],
            "diet": "C",
            "serves": {"exact": 6, "note": "hearty portions"},
            "makes": {"exact": 1, "unit": "steak"},
            "time": {"prep": "15 minutes", "cook": "30 minutes", "total": "45 minutes"},
            "equipment": ["grill", "tongs", "meat thermometer"],
            "ingredients": [
                {"type": "ingredient", "entry": "1 dragon steak (3 lbs)"},
                {"type": "ingredient", "entry": "Salt and pepper to taste"},
            ],
            "instructions": [
                "Season the dragon steak with salt and pepper.",
                "Grill over high heat until desired doneness.",
            ],
        }

        content = factory.create_content(timed_data, ContentType.RECIPE)

        assert content.has_serving_info() is True
        assert content.has_makes_info() is True
        assert content.has_timing_info() is True
        assert content.requires_equipment() is True
        assert content.get_serving_count() == 6
        assert content.get_serving_note() == "hearty portions"
        assert content.get_prep_time() == "15 minutes"
        assert content.get_cook_time() == "30 minutes"
        assert content.get_total_time() == "45 minutes"
        assert len(content.get_equipment_list()) == 3
        assert "grill" in content.get_equipment_list()

    def test_recipe_complexity_rating(self) -> None:
        """Test Recipe complexity rating system."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test simple recipe
        simple_data = {
            "name": "Simple Toast",
            "source": {"abbreviation": "TEST", "full": "Test Source"},
            "type": "Simple",
            "ingredients": [{"type": "ingredient", "entry": "1 slice bread"}],
            "instructions": ["Toast the bread.", "Serve warm."],
        }

        simple_recipe = factory.create_content(simple_data, ContentType.RECIPE)
        assert simple_recipe.get_complexity_rating() == "Simple"

        # Test complex recipe
        complex_data = {
            "name": "Beholder Eye Soup",
            "source": {"abbreviation": "TEST", "full": "Test Source"},
            "type": "Master Chef Special",
            "equipment": ["cauldron", "magic flame", "crystal ladle"],
            "ingredients": [
                {"type": "ingredient", "entry": "12 beholder eyes"},
                {"type": "ingredient", "entry": "Dragon bone broth"},
                {"type": "ingredient", "entry": "Rare spices"},
                {"type": "ingredient", "entry": "Unicorn tears"},
                {"type": "ingredient", "entry": "Phoenix feather"},
                {"type": "ingredient", "entry": "Mithril dust"},
            ],
            "instructions": [
                "Prepare the mystical cauldron.",
                "Carefully extract beholder eye juices.",
                "Simmer dragon bone broth for 3 hours.",
                "Add rare spices in specific order.",
                "Incorporate unicorn tears drop by drop.",
                "Grind phoenix feather to powder.",
                "Stir counterclockwise while chanting.",
                "Add mithril dust at moonrise.",
                "Strain through enchanted cloth.",
                "Serve in crystal bowls.",
            ],
        }

        complex_recipe = factory.create_content(complex_data, ContentType.RECIPE)
        assert complex_recipe.get_complexity_rating() == "Complex"

    def test_recipe_ingredient_filtering(self) -> None:
        """Test Recipe ingredient filtering functionality."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test recipe with different ingredient types
        mixed_data = {
            "name": "Mixed Recipe",
            "source": {"abbreviation": "TEST", "full": "Test Source"},
            "type": "Test Recipe",
            "ingredients": [
                {"type": "ingredient", "entry": "Main ingredient 1"},
                {"type": "ingredient", "entry": "Main ingredient 2"},
                {"type": "garnish", "entry": "Garnish 1"},
                {"type": "garnish", "entry": "Garnish 2"},
                {"type": "seasoning", "entry": "Salt"},
            ],
            "instructions": ["Combine ingredients.", "Season and garnish."],
        }

        content = factory.create_content(mixed_data, ContentType.RECIPE)

        main_ingredients = content.get_ingredient_by_type("ingredient")
        garnishes = content.get_ingredient_by_type("garnish")
        seasonings = content.get_ingredient_by_type("seasoning")

        assert len(main_ingredients) == 2
        assert len(garnishes) == 2
        assert len(seasonings) == 1

    def test_recipe_summary_functionality(self) -> None:
        """Test Recipe summary generation."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test comprehensive recipe summary
        summary_data = {
            "name": "Tavern Stew",
            "source": {"abbreviation": "TEST", "full": "Test Source"},
            "type": "Hearty Meal",
            "dishTypes": ["entree", "soup"],
            "diet": "O",
            "serves": {"exact": 8},
            "ingredients": [
                {"type": "ingredient", "entry": "Beef chunks"},
                {"type": "ingredient", "entry": "Potatoes"},
                {"type": "ingredient", "entry": "Carrots"},
            ],
            "instructions": ["Brown the meat.", "Add vegetables.", "Simmer for hours."],
        }

        content = factory.create_content(summary_data, ContentType.RECIPE)

        summary = content.get_recipe_summary()
        assert "Omnivorous" in summary
        assert "entree/soup" in summary
        assert "3 ingredients" in summary
        assert "3 steps" in summary
        assert "serves 8" in summary

    def test_recipe_minimal_data(self) -> None:
        """Test Recipe with minimal required data."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test with minimal data
        minimal_data = {
            "name": "Minimal Recipe",
            "source": {"abbreviation": "TEST", "full": "Test Source"},
            "type": "Basic",
            "ingredients": [{"type": "ingredient", "entry": "Something"}],
            "instructions": ["Do something."],
        }

        content = factory.create_content(minimal_data, ContentType.RECIPE)

        assert content.name == "Minimal Recipe"
        assert content.get_recipe_type() == "Basic"
        assert content.get_ingredient_count() == 1
        assert content.get_instruction_count() == 1
        assert content.has_alias() is False
        assert content.has_serving_info() is False
        assert content.has_timing_info() is False
        assert content.requires_equipment() is False

    def test_recipe_validation_errors(self) -> None:
        """Test Recipe validation errors."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.models.content import ContentType

        factory = ContentFactory()

        # Test with empty name
        with pytest.raises(ValidationError):
            invalid_data = {
                "name": "",  # Empty name should fail
                "source": {"abbreviation": "TEST", "full": "Test Source"},
                "type": "Test",
                "ingredients": [{"type": "ingredient", "entry": "Something"}],
                "instructions": ["Do something."],
            }
            factory.create_content(invalid_data, ContentType.RECIPE)

        # Test with empty ingredients
        with pytest.raises(ValidationError):
            invalid_data = {
                "name": "Test Recipe",
                "source": {"abbreviation": "TEST", "full": "Test Source"},
                "type": "Test",
                "ingredients": [],  # Empty ingredients should fail
                "instructions": ["Do something."],
            }
            factory.create_content(invalid_data, ContentType.RECIPE)

        # Test with empty instructions
        with pytest.raises(ValidationError):
            invalid_data = {
                "name": "Test Recipe",
                "source": {"abbreviation": "TEST", "full": "Test Source"},
                "type": "Test",
                "ingredients": [{"type": "ingredient", "entry": "Something"}],
                "instructions": [],  # Empty instructions should fail
            }
            factory.create_content(invalid_data, ContentType.RECIPE)

    def test_recipe_omnidexer_integration(self) -> None:
        """Test Recipe integration with Omnidexer."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.omnidexer import Omnidexer
        from dnd5e.core.models.content import ContentType

        omnidexer = Omnidexer()

        # Verify Recipe is registered with Omnidexer loaders
        supported_types = omnidexer.get_supported_types()
        assert ContentType.RECIPE in supported_types

        # Verify loader type assignment
        json_types = omnidexer._JSON_CONTENT_TYPES
        assert ContentType.RECIPE in json_types

    def test_recipe_file_patterns(self) -> None:
        """Test Recipe file pattern integration."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.configurable_source_manager import (
            ConfigurableSourceManager,
        )
        from dnd5e.core.models.content import ContentType

        # Get content patterns from registry manager
        content_patterns = getattr(ConfigurableSourceManager, "content_patterns", {})

        # Verify Recipe patterns are registered
        assert ContentType.RECIPE in content_patterns
        patterns = content_patterns[ContentType.RECIPE]
        assert "recipe" in patterns
        assert "recipes" in patterns

    def test_recipe_registry_consistency(self) -> None:
        """Test that Recipe registration is consistent across systems."""
        from dnd5e.core.registry.initialization import initialize_content_types

        initialize_content_types()

        from dnd5e.core.loaders.content_factory import ContentFactory
        from dnd5e.core.loaders.omnidexer import Omnidexer
        from dnd5e.core.models.content import ContentType
        from dnd5e.core.registry.content_type_registry import get_content_type_registry

        # Check registry has Recipe
        registry = get_content_type_registry()
        registrations = registry.get_all()

        # registrations is a dict[str, ContentTypeMetadata]
        recipe_registration = registrations.get("recipe")
        assert recipe_registration is not None
        assert recipe_registration.enum_value == "recipe"

        # Check ContentFactory has Recipe
        factory = ContentFactory()
        supported_factory_types = factory.get_supported_types()
        assert ContentType.RECIPE in supported_factory_types

        # Check Omnidexer has Recipe
        omnidexer = Omnidexer()
        supported_omnidexer_types = omnidexer.get_supported_types()
        assert ContentType.RECIPE in supported_omnidexer_types

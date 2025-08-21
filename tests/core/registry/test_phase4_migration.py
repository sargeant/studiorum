"""Test Phase 4: Specialized Systems content type migration."""

import pytest

from tests.test_helpers import reset_test_environment


class TestPhase4Migration:
    """Test Phase 4 specialized systems content types."""

    def setup_method(self) -> None:
        """Set up test environment."""
        reset_test_environment()

    def test_trap_content_type_registration(self) -> None:
        """Test that Trap content type is registered."""
        from studiorum.core.models.content import ContentType
        from studiorum.core.registry import initialize_content_types

        initialize_content_types()

        # Verify enum was created
        assert hasattr(ContentType, "TRAP")
        assert ContentType.TRAP == "trap"

        # Verify content creation works
        from studiorum.core.loaders.content_factory import ContentFactory

        factory = ContentFactory()

        trap_data = {
            "name": "Pit Trap",
            "source": {"abbreviation": "DMG"},
            "trapHazType": "MECH",
            "rating": [{"tier": 1, "threat": "dangerous"}],
            "entries": ["A 10-foot deep pit trap."],
        }

        content = factory.create_content(trap_data, ContentType.TRAP)
        assert content.name == "Pit Trap"
        assert content.trap_haz_type == "MECH"
        assert content.is_mechanical()
        assert not content.is_magical()

    def test_object_content_type_registration(self) -> None:
        """Test that Object content type is registered."""
        from studiorum.core.models.content import ContentType
        from studiorum.core.registry import initialize_content_types

        initialize_content_types()

        # Verify enum was created
        assert hasattr(ContentType, "OBJECT")
        assert ContentType.OBJECT == "object"

        # Verify content creation works
        from studiorum.core.loaders.content_factory import ContentFactory

        factory = ContentFactory()

        object_data = {
            "name": "Ballista",
            "source": {"abbreviation": "DMG"},
            "size": ["L"],
            "objectType": "SW",
            "ac": 15,
            "hp": 50,
            "entries": ["A siege weapon ballista."],
            "actionEntries": [
                {
                    "type": "entries",
                    "name": "Ballista Bolt",
                    "entries": ["Ranged attack with ballista."],
                }
            ],
        }

        content = factory.create_content(object_data, ContentType.OBJECT)
        assert content.name == "Ballista"
        assert content.get_primary_size() == "L"
        assert content.is_siege_weapon()
        assert content.is_destructible()
        assert content.has_actions()

    def test_cult_content_type_registration(self) -> None:
        """Test that Cult content type is registered."""
        from studiorum.core.models.content import ContentType
        from studiorum.core.registry import initialize_content_types

        initialize_content_types()

        # Verify enum was created
        assert hasattr(ContentType, "CULT")
        assert ContentType.CULT == "cult"

        # Verify content creation works
        from studiorum.core.loaders.content_factory import ContentFactory

        factory = ContentFactory()

        cult_data = {
            "name": "Cult of Asmodeus",
            "source": {"abbreviation": "MTF"},
            "type": "Diabolical",
            "entries": ["A cult devoted to the lord of the Nine Hells."],
        }

        content = factory.create_content(cult_data, ContentType.CULT)
        assert content.name == "Cult of Asmodeus"
        assert content.type == "Diabolical"
        assert content.is_diabolical()
        assert not content.is_elder_evil()

    def test_boon_content_type_registration(self) -> None:
        """Test that Boon content type is registered."""
        from studiorum.core.models.content import ContentType
        from studiorum.core.registry import initialize_content_types

        initialize_content_types()

        # Verify enum was created
        assert hasattr(ContentType, "BOON")
        assert ContentType.BOON == "boon"

        # Verify content creation works
        from studiorum.core.loaders.content_factory import ContentFactory

        factory = ContentFactory()

        boon_data = {
            "name": "Blessing of Health",
            "source": {"abbreviation": "DMG"},
            "entries": ["A divine blessing that grants immunity to disease."],
        }

        content = factory.create_content(boon_data, ContentType.BOON)
        assert content.name == "Blessing of Health"
        assert content.is_permanent()  # No duration specified

    def test_recipe_content_type_registration(self) -> None:
        """Test that Recipe content type is registered."""
        from studiorum.core.models.content import ContentType
        from studiorum.core.registry import initialize_content_types

        initialize_content_types()

        # Verify enum was created
        assert hasattr(ContentType, "RECIPE")
        assert ContentType.RECIPE == "recipe"

        # Verify content creation works
        from studiorum.core.loaders.content_factory import ContentFactory

        factory = ContentFactory()

        recipe_data = {
            "name": "Goodberry Pie",
            "source": {"abbreviation": "HF"},
            "type": "Uncommon Cuisine",
            "dishTypes": ["dessert"],
            "diet": "V",
            "serves": {"exact": 6, "note": "as dessert"},
            "ingredients": [
                {"type": "ingredient", "entry": "1 cup fresh goodberries", "amount1": 1}
            ],
            "entries": ["A magical pie made with goodberries."],
        }

        content = factory.create_content(recipe_data, ContentType.RECIPE)
        assert content.name == "Goodberry Pie"
        assert content.is_cuisine()
        assert not content.is_crafting()
        assert content.has_dietary_restrictions()
        assert content.get_ingredient_count() == 1

    def test_facility_content_type_registration(self) -> None:
        """Test that Facility content type is registered."""
        from studiorum.core.models.content import ContentType
        from studiorum.core.registry import initialize_content_types

        initialize_content_types()

        # Verify enum was created
        assert hasattr(ContentType, "FACILITY")
        assert ContentType.FACILITY == "facility"

        # Verify content creation works
        from studiorum.core.loaders.content_factory import ContentFactory

        factory = ContentFactory()

        facility_data = {
            "name": "Arcane Study",
            "source": {"abbreviation": "XDMG"},
            "facilityType": "special",
            "level": 5,
            "prerequisite": [{"spellcastingFocus": ["arcane", "tool"]}],
            "space": ["roomy"],
            "hirelings": [{"exact": 1}],
            "orders": ["craft"],
            "entries": ["A place of quiet magical research."],
        }

        content = factory.create_content(facility_data, ContentType.FACILITY)
        assert content.name == "Arcane Study"
        assert content.is_special_facility()
        assert not content.is_basic_facility()
        assert content.requires_spellcasting()
        assert "arcane" in content.get_required_focus_types()
        assert content.supports_order("craft")
        assert content.is_roomy()

    def test_all_phase4_content_types_registered(self) -> None:
        """Test that all Phase 4 content types are registered."""
        from studiorum.core.models.content import ContentType
        from studiorum.core.registry import initialize_content_types

        initialize_content_types()

        # Check all Phase 4 content types
        phase4_types = ["TRAP", "OBJECT", "CULT", "BOON", "RECIPE", "FACILITY"]

        for content_type in phase4_types:
            assert hasattr(ContentType, content_type), (
                f"ContentType.{content_type} not found"
            )

    def test_content_factory_supports_all_phase4_types(self) -> None:
        """Test that ContentFactory supports all Phase 4 content types."""
        from studiorum.core.loaders.content_factory import ContentFactory
        from studiorum.core.models.content import ContentType
        from studiorum.core.registry import initialize_content_types

        initialize_content_types()

        factory = ContentFactory()
        supported_types = factory.get_supported_types()

        phase4_types = [
            ContentType.TRAP,
            ContentType.OBJECT,
            ContentType.CULT,
            ContentType.BOON,
            ContentType.RECIPE,
            ContentType.FACILITY,
        ]

        for content_type in phase4_types:
            assert content_type in supported_types, (
                f"{content_type.value} not supported by ContentFactory"
            )

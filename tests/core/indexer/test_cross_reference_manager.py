"""Tests for cross-reference manager."""

import pytest

from dnd5e.core.indexer.cross_reference_manager import (
    CrossReference,
    CrossReferenceManager,
)


class TestCrossReference:
    """Test CrossReference dataclass."""

    def test_cross_reference_creation(self):
        """Test creating cross-reference."""
        ref = CrossReference(
            id="creature:dragon",
            content_type="creature",
            name="Dragon",
            source="MM",
            page="88",
            latex_label="creature:dragon",
        )

        assert ref.id == "creature:dragon"
        assert ref.content_type == "creature"
        assert ref.name == "Dragon"
        assert ref.source == "MM"
        assert ref.page == "88"
        assert ref.latex_label == "creature:dragon"
        assert ref.referenced_count == 0

    def test_cross_reference_defaults(self):
        """Test cross-reference with default values."""
        ref = CrossReference(
            id="spell:fireball",
            content_type="spell",
            name="Fireball",
        )

        assert ref.source is None
        assert ref.page is None
        assert ref.latex_label is None
        assert ref.section is None
        assert ref.referenced_count == 0


class TestCrossReferenceManager:
    """Test cross-reference manager."""

    def setup_method(self):
        """Set up test fixtures."""
        self.manager = CrossReferenceManager()

    def test_manager_initialization(self):
        """Test manager initialization."""
        assert len(self.manager.references) == 0
        assert self.manager.reference_format == "page"
        assert self.manager.label_prefix == ""
        assert self.manager.auto_page_refs is True

    def test_register_content(self):
        """Test content registration."""
        ref_id = self.manager.register_content(
            content_type="creature",
            name="Ancient Red Dragon",
            source="MM",
            page="98",
        )

        assert ref_id == "creature:ancient-red-dragon"
        assert ref_id in self.manager.references

        ref = self.manager.references[ref_id]
        assert ref.content_type == "creature"
        assert ref.name == "Ancient Red Dragon"
        assert ref.source == "MM"
        assert ref.page == "98"
        assert ref.referenced_count == 1

    def test_register_duplicate_content(self):
        """Test registering same content multiple times."""
        ref_id1 = self.manager.register_content("spell", "Fireball")
        ref_id2 = self.manager.register_content("spell", "Fireball")

        assert ref_id1 == ref_id2
        assert len(self.manager.references) == 1
        assert self.manager.references[ref_id1].referenced_count == 2

    def test_generate_reference_id(self):
        """Test reference ID generation."""
        test_cases = [
            ("creature", "Ancient Red Dragon", "creature:ancient-red-dragon"),
            (
                "spell",
                "Mordenkainen's Magnificent Mansion",
                "creature:mordenkainen-s-magnificent-mansion",
            ),
            ("item", "Bag of Holding", "creature:bag-of-holding"),
            ("class", "Fighter", "creature:fighter"),
        ]

        for content_type, name, expected in test_cases:
            result = self.manager.generate_reference_id(content_type, name)
            # Note: the expected values in test_cases have wrong prefix, fixing:
            expected = expected.replace("creature:", f"{content_type}:")
            assert result == expected

    def test_generate_latex_label(self):
        """Test LaTeX label generation."""
        ref_id = "creature:dragon"
        label = self.manager.generate_latex_label(ref_id)
        assert label == "creature:dragon"

        # Test with prefix
        self.manager.set_label_prefix("doc")
        label_with_prefix = self.manager.generate_latex_label(ref_id)
        assert label_with_prefix == "doc:creature:dragon"

    def test_sanitize_for_id(self):
        """Test ID sanitization."""
        test_cases = [
            ("Ancient Red Dragon", "ancient-red-dragon"),
            ("Sphere of Annihilation", "sphere-of-annihilation"),
            ("AC (Armor Class)", "ac-armor-class"),
            ("", "unnamed"),
            ("Multiple   Spaces", "multiple-spaces"),
            ("Special!@#$%Characters", "special-characters"),
        ]

        for input_text, expected in test_cases:
            result = self.manager._sanitize_for_id(input_text)
            assert result == expected

    def test_get_reference(self):
        """Test getting reference by ID."""
        ref_id = self.manager.register_content("item", "Sword of Sharpness")
        ref = self.manager.get_reference(ref_id)

        assert ref is not None
        assert ref.name == "Sword of Sharpness"
        assert ref.content_type == "item"

        # Test non-existent reference
        assert self.manager.get_reference("non:existent") is None

    def test_get_reference_by_name(self):
        """Test getting reference by name and type."""
        self.manager.register_content("spell", "Magic Missile")
        ref = self.manager.get_reference_by_name("spell", "Magic Missile")

        assert ref is not None
        assert ref.name == "Magic Missile"
        assert ref.content_type == "spell"

    def test_create_latex_reference(self):
        """Test creating LaTeX reference commands."""
        ref_id = self.manager.register_content("creature", "Dragon")

        # Test hyperref
        hyperref = self.manager.create_latex_reference(ref_id, "Dragon")
        assert "\\hyperref[creature:dragon]{Dragon}" in hyperref
        assert "\\pageref{creature:dragon}" in hyperref

        # Test ref only
        ref_only = self.manager.create_latex_reference(
            ref_id, ref_type="ref", include_page_ref=False
        )
        assert ref_only == "\\ref{creature:dragon}"

        # Test pageref only
        pageref = self.manager.create_latex_reference(ref_id, ref_type="pageref")
        assert pageref == "\\pageref{creature:dragon}"

    def test_create_latex_label(self):
        """Test creating LaTeX label commands."""
        ref_id = self.manager.register_content("spell", "Fireball")
        label = self.manager.create_latex_label(ref_id)

        assert label == "\\label{spell:fireball}"

    def test_get_references_by_type(self):
        """Test getting references by content type."""
        self.manager.register_content("creature", "Dragon")
        self.manager.register_content("creature", "Orc")
        self.manager.register_content("spell", "Fireball")

        creatures = self.manager.get_references_by_type("creature")
        spells = self.manager.get_references_by_type("spell")

        assert len(creatures) == 2
        assert len(spells) == 1
        assert all(ref.content_type == "creature" for ref in creatures)
        assert all(ref.content_type == "spell" for ref in spells)

    def test_reference_statistics(self):
        """Test reference statistics generation."""
        # Register various content
        self.manager.register_content("creature", "Dragon")
        self.manager.register_content("creature", "Dragon")  # Duplicate
        self.manager.register_content("spell", "Fireball")
        self.manager.register_content("item", "Sword")

        stats = self.manager.get_reference_statistics()

        assert stats["total_references"] == 3  # Unique references
        assert stats["by_type"]["creature"] == 1
        assert stats["by_type"]["spell"] == 1
        assert stats["by_type"]["item"] == 1

        # Most referenced should have Dragon first (referenced twice)
        assert stats["most_referenced"][0]["name"] == "Dragon"
        assert stats["most_referenced"][0]["count"] == 2

    def test_export_for_latex_document(self):
        """Test exporting for LaTeX document."""
        self.manager.register_content("creature", "Dragon", source="MM", page="88")
        self.manager.register_content("spell", "Fireball", source="PHB", page="241")

        export = self.manager.export_for_latex_document()

        assert "references" in export
        assert "labels" in export
        assert "by_type" in export

        # Check that references were created (keys should be the actual ref_ids)
        assert len(export["references"]) == 2

        # Find the creature reference by checking all references
        creature_ref = None
        for ref_id, ref_data in export["references"].items():
            if ref_data["name"] == "Dragon" and ref_data["type"] == "creature":
                creature_ref = ref_data
                break

        assert creature_ref is not None
        assert creature_ref["name"] == "Dragon"
        assert creature_ref["source"] == "MM"
        assert creature_ref["page"] == "88"

        # Check by_type grouping
        assert "creature" in export["by_type"]
        assert "spell" in export["by_type"]
        assert len(export["by_type"]["creature"]) == 1
        assert len(export["by_type"]["spell"]) == 1

    def test_validate_references(self):
        """Test reference validation."""
        # Valid reference
        self.manager.register_content("creature", "Dragon")

        # Create invalid reference by manipulating internal state
        invalid_ref = CrossReference(
            id="invalid:ref",
            content_type="creature",
            name="Invalid",
            latex_label="invalid--label!!",  # Invalid LaTeX label
        )
        self.manager.references["invalid:ref"] = invalid_ref

        issues = self.manager.validate_references()

        # Should find the invalid label
        assert len(issues) >= 1
        assert any(issue["type"] == "invalid_label" for issue in issues)

    def test_set_reference_format(self):
        """Test setting reference format."""
        self.manager.set_reference_format("section")
        assert self.manager.reference_format == "section"

        with pytest.raises(ValueError):
            self.manager.set_reference_format("invalid")

    def test_set_label_prefix(self):
        """Test setting label prefix."""
        self.manager.set_label_prefix("my-doc")
        assert self.manager.label_prefix == "my-doc"

        # Test with special characters
        self.manager.set_label_prefix("Special!@#Characters")
        assert self.manager.label_prefix == "special-characters"

    def test_clear_references(self):
        """Test clearing all references."""
        self.manager.register_content("creature", "Dragon")
        self.manager.register_content("spell", "Fireball")

        assert len(self.manager.references) == 2

        self.manager.clear_references()

        assert len(self.manager.references) == 0

    def test_merge_references(self):
        """Test merging references from another manager."""
        other_manager = CrossReferenceManager()
        other_manager.register_content("creature", "Dragon")
        other_manager.register_content("spell", "Fireball")

        # Register same dragon in main manager
        self.manager.register_content("creature", "Dragon")

        assert len(self.manager.references) == 1

        self.manager.merge_references(other_manager)

        # Should have 2 unique references, with Dragon having count of 2
        assert len(self.manager.references) == 2
        dragon_ref = self.manager.get_reference("creature:dragon")
        assert dragon_ref.referenced_count == 2


class TestCrossReferenceManagerEdgeCases:
    """Test edge cases and error conditions."""

    def setup_method(self):
        """Set up test fixtures."""
        self.manager = CrossReferenceManager()

    def test_empty_name_handling(self):
        """Test handling of empty names."""
        ref_id = self.manager.register_content("creature", "")
        assert ref_id == "creature:unnamed"

    def test_none_name_handling(self):
        """Test handling of None names."""
        # This should probably raise an error or be handled gracefully
        with pytest.raises((TypeError, AttributeError)):
            self.manager.register_content("creature", None)

    def test_unicode_names(self):
        """Test handling of Unicode names."""
        ref_id = self.manager.register_content(
            "creature", "Дракон"
        )  # Dragon in Cyrillic
        # Should sanitize to safe ASCII
        assert ref_id.startswith("creature:")
        assert ref_id != "creature:дракон"  # Should be sanitized

    def test_very_long_names(self):
        """Test handling of very long names."""
        long_name = "A" * 1000
        ref_id = self.manager.register_content("creature", long_name)

        # Should handle gracefully
        assert ref_id.startswith("creature:")
        assert len(ref_id) < 1100  # Should not be excessively long


if __name__ == "__main__":
    pytest.main([__file__])

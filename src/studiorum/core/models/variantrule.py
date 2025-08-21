"""Variant rule content model."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import Field, field_validator

from ..registry import content_type
from .content import BaseContent
from .entry_types import Entry


class RuleType(str, Enum):
    """Enumeration of rule types in D&D."""

    CORE = "C"  # Core rules
    OPTIONAL = "O"  # Optional rules
    VARIANT = "V"  # Variant rules
    LAIR_ACTION = "LA"  # Lair actions
    REGIONAL_EFFECT = "RE"  # Regional effects
    UNKNOWN = "U"  # Unknown/other


@content_type(
    enum_value="variantrule",
    file_patterns=["variantrule", "variantrules"],
    loader_type="json",
    statblock_tags=["variantrule"],
)
class VariantRule(BaseContent):
    """Variant rule model for game rule variations and alternatives.

    Variant rules represent modifications or alternatives to core game mechanics,
    optional rules, and expanded rule systems.
    """

    # Required fields
    entries: list[Entry] = Field(
        default_factory=list, description="Rule description entries"
    )

    # Optional fields
    rule_type: RuleType = Field(
        RuleType.VARIANT,
        description="Type of rule (core, optional, variant, etc.)",
        alias="ruleType",
    )
    type: str | None = Field(None, description="Additional type classification")
    prerequisites: list[Entry] | None = Field(
        None, description="Prerequisites for using this rule"
    )
    implements: list[str] | None = Field(
        None, description="What this rule implements or replaces"
    )
    replaces: list[str] | None = Field(
        None, description="Rules that this variant replaces"
    )
    srd: bool | None = Field(None, description="Whether this rule is in the SRD")
    srd52: bool | None = Field(None, description="Whether this rule is in SRD 5.2")
    basic_rules: bool | None = Field(
        None, description="Whether this rule is in Basic Rules", alias="basicRules"
    )
    basic_rules_2024: bool | None = Field(
        None,
        description="Whether this rule is in 2024 Basic Rules",
        alias="basicRules2024",
    )
    legacy: bool | None = Field(None, description="Whether this is a legacy rule")
    additional_sources: list[dict[str, Any]] | None = Field(
        None,
        description="Additional sources for this rule",
        alias="additionalSources",
    )
    other_sources: list[dict[str, Any]] | None = Field(
        None,
        description="Other sources that reference this rule",
        alias="otherSources",
    )
    reprinted_as: list[str] | None = Field(
        None, description="Reprints of this rule", alias="reprintedAs"
    )

    @field_validator("rule_type", mode="before")
    @classmethod
    def validate_rule_type(cls, v: Any) -> RuleType:
        """Validate and normalize rule type."""
        if isinstance(v, str):
            try:
                return RuleType(v.upper())
            except ValueError:
                return RuleType.UNKNOWN
        return RuleType.VARIANT

    @field_validator("entries", mode="before")
    @classmethod
    def validate_entries(cls, v: Any) -> list[Entry]:
        """Validate entries structure."""
        if v is None:
            return []
        if isinstance(v, list):
            return v
        return []

    @field_validator("prerequisites", mode="before")
    @classmethod
    def validate_prerequisites(cls, v: Any) -> list[Entry] | None:
        """Validate prerequisites structure."""
        if v is None:
            return None
        if isinstance(v, list):
            # Let pydantic handle Entry validation later
            return v
        if isinstance(v, str | dict):
            # Let pydantic handle Entry validation later
            return [v]  # type: ignore[list-item]
        return None

    @field_validator("implements", mode="before")
    @classmethod
    def validate_implements(cls, v: Any) -> list[str] | None:
        """Validate implements list."""
        if v is None:
            return None
        if isinstance(v, str):
            return [v]
        if isinstance(v, list):
            return [str(item) for item in v]
        return None

    @field_validator("replaces", mode="before")
    @classmethod
    def validate_replaces(cls, v: Any) -> list[str] | None:
        """Validate replaces list."""
        if v is None:
            return None
        if isinstance(v, str):
            return [v]
        if isinstance(v, list):
            return [str(item) for item in v]
        return None

    @field_validator("name", mode="before")
    @classmethod
    def validate_name(cls, v: Any) -> str:
        """Validate that name is not empty."""
        if not v or not str(v).strip():
            raise ValueError("Variant rule name cannot be empty")
        return str(v).strip()

    def get_rule_type(self) -> RuleType:
        """Get the rule type enum."""
        return self.rule_type

    def get_rule_type_description(self) -> str:
        """Get a human-readable description of the rule type."""
        descriptions = {
            RuleType.CORE: "Core Rule",
            RuleType.OPTIONAL: "Optional Rule",
            RuleType.VARIANT: "Variant Rule",
            RuleType.LAIR_ACTION: "Lair Action",
            RuleType.REGIONAL_EFFECT: "Regional Effect",
            RuleType.UNKNOWN: "Unknown Rule Type",
        }
        return descriptions.get(self.rule_type, "Unknown Rule Type")

    def is_core_rule(self) -> bool:
        """Check if this is a core game rule."""
        return self.rule_type == RuleType.CORE

    def is_optional_rule(self) -> bool:
        """Check if this is an optional rule."""
        return self.rule_type == RuleType.OPTIONAL

    def is_variant_rule(self) -> bool:
        """Check if this is a variant rule."""
        return self.rule_type == RuleType.VARIANT

    def is_lair_action(self) -> bool:
        """Check if this is a lair action rule."""
        return self.rule_type == RuleType.LAIR_ACTION

    def is_regional_effect(self) -> bool:
        """Check if this is a regional effect rule."""
        return self.rule_type == RuleType.REGIONAL_EFFECT

    def has_prerequisites(self) -> bool:
        """Check if this rule has prerequisites."""
        return bool(self.prerequisites)

    def implements_rules(self) -> bool:
        """Check if this rule implements other rules."""
        return bool(self.implements)

    def replaces_rules(self) -> bool:
        """Check if this rule replaces other rules."""
        return bool(self.replaces)

    def is_srd_content(self) -> bool:
        """Check if this rule is part of the System Reference Document."""
        return self.srd is True or self.srd52 is True

    def is_basic_rules_content(self) -> bool:
        """Check if this rule is part of the Basic Rules."""
        return self.basic_rules is True or self.basic_rules_2024 is True

    def is_legacy_content(self) -> bool:
        """Check if this is legacy content."""
        return self.legacy is True

    def get_implemented_rules(self) -> list[str]:
        """Get list of rules this rule implements."""
        return self.implements or []

    def get_replaced_rules(self) -> list[str]:
        """Get list of rules this rule replaces."""
        return self.replaces or []

    def get_availability_summary(self) -> str:
        """Get a summary of where this rule is available."""
        availability = []

        if self.is_srd_content():
            if self.srd52:
                availability.append("SRD 5.2")
            elif self.srd:
                availability.append("SRD")

        if self.is_basic_rules_content():
            if self.basic_rules_2024:
                availability.append("Basic Rules 2024")
            elif self.basic_rules:
                availability.append("Basic Rules")

        if self.is_legacy_content():
            availability.append("Legacy")

        if not availability:
            availability.append("Supplement only")

        return ", ".join(availability)

    def get_rule_classification(self) -> str:
        """Get a classification summary of this rule."""
        classification = self.get_rule_type_description()

        if self.type:
            classification += f" ({self.type})"

        availability = self.get_availability_summary()
        if availability != "Supplement only":
            classification += f" - {availability}"

        return classification

    def get_entry_count(self) -> int:
        """Get the number of description entries."""
        return len(self.entries)

    def has_content(self) -> bool:
        """Check if this rule has description content."""
        return bool(self.entries)

    def get_modification_summary(self) -> str:
        """Get a summary of what this rule modifies."""
        modifications = []

        if self.implements_rules():
            impl_count = len(self.get_implemented_rules())
            modifications.append(
                f"implements {impl_count} rule{'s' if impl_count != 1 else ''}"
            )

        if self.replaces_rules():
            repl_count = len(self.get_replaced_rules())
            modifications.append(
                f"replaces {repl_count} rule{'s' if repl_count != 1 else ''}"
            )

        if self.has_prerequisites():
            modifications.append("has prerequisites")

        if not modifications:
            return "standalone rule"

        return ", ".join(modifications)

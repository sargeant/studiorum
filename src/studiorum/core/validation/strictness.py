"""Validation strictness levels and configuration."""

from enum import Enum


class ValidationStrictness(str, Enum):
    """Validation strictness levels."""

    STRICT = "strict"
    """Strict mode: Fail fast on any validation error."""

    NORMAL = "normal"
    """Normal mode: Log validation errors but continue processing."""

    LENIENT = "lenient"
    """Lenient mode: Minimal logging, maximum tolerance for data issues."""

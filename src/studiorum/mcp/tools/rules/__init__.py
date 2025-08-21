"""Rules intelligence tools for the Studiorum MCP server.

This package provides intelligent analysis of D&D 5e rules including:
- Cross-reference discovery and relationship analysis
- Rule combination validation with conflict detection
- Intelligent rule search with enhanced metadata
- Context-aware rule suggestions

All tools leverage existing infrastructure and follow established patterns
for performance (<200ms targets) and error handling.
"""

from .tools import (
    RULE_INTELLIGENCE_TOOLS,
    find_rule_cross_references,
    get_rule_suggestions,
    search_rules_intelligent,
    validate_rule_combination,
)

__all__ = [
    "find_rule_cross_references",
    "validate_rule_combination",
    "search_rules_intelligent",
    "get_rule_suggestions",
    "RULE_INTELLIGENCE_TOOLS",
]

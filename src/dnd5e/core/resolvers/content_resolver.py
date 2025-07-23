"""Content resolver for mapping user abbreviations to content objects."""

import difflib
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

from dnd5e.core.models.content import BaseContent, ContentType


class ResolutionStatus(Enum):
    """Status of content resolution attempt."""

    EXACT_MATCH = "exact_match"
    MULTIPLE_MATCHES = "multiple_matches"
    NO_MATCH = "no_match"
    FUZZY_MATCH = "fuzzy_match"


@dataclass
class ContentResolutionResult:
    """Result of content resolution attempt."""

    status: ResolutionStatus
    content: BaseContent | None = None
    matches: list[BaseContent] | None = None
    suggestions: list[str] | None = None
    query: str = ""

    def __post_init__(self) -> None:
        """Initialize default values."""
        if self.matches is None:
            self.matches = []
        if self.suggestions is None:
            self.suggestions = []

    @property
    def is_success(self) -> bool:
        """Check if resolution was successful."""
        return self.status == ResolutionStatus.EXACT_MATCH

    @property
    def needs_user_selection(self) -> bool:
        """Check if user needs to select from multiple matches."""
        return self.status == ResolutionStatus.MULTIPLE_MATCHES

    @property
    def has_suggestions(self) -> bool:
        """Check if suggestions are available."""
        return bool(self.suggestions and len(self.suggestions) > 0)


class ContentResolver:
    """Resolves user abbreviations to content objects using omnidexer."""

    def __init__(self, omnidexer: Any) -> None:
        """Initialize resolver with omnidexer instance.

        Args:
            omnidexer: The Omnidexer instance to use for content lookup
        """
        self.omnidexer = omnidexer

    def resolve_adventure(self, abbreviation: str) -> ContentResolutionResult:
        """Resolve abbreviation to an adventure.

        Args:
            abbreviation: User-provided abbreviation (e.g., "cos", "lmop")

        Returns:
            ContentResolutionResult with resolution details
        """
        return self._resolve_content(ContentType.ADVENTURE, abbreviation)

    def resolve_book(self, abbreviation: str) -> ContentResolutionResult:
        """Resolve abbreviation to a book.

        Args:
            abbreviation: User-provided abbreviation (e.g., "phb", "mm", "dmg")

        Returns:
            ContentResolutionResult with resolution details
        """
        return self._resolve_content(ContentType.BOOK, abbreviation)

    def resolve_any(
        self, abbreviation: str, content_type: ContentType | None = None
    ) -> ContentResolutionResult:
        """Resolve abbreviation to any content type.

        Args:
            abbreviation: User-provided abbreviation
            content_type: Optional specific content type to search

        Returns:
            ContentResolutionResult with resolution details
        """
        if content_type:
            return self._resolve_content(content_type, abbreviation)

        # Try all content types if not specified
        for ct in [ContentType.ADVENTURE, ContentType.BOOK]:
            result = self._resolve_content(ct, abbreviation)
            if result.is_success:
                return result

        # If no exact matches, return the first result with suggestions
        return self._resolve_content(ContentType.ADVENTURE, abbreviation)

    def find_suggestions(
        self, abbreviation: str, content_type: ContentType, limit: int = 5
    ) -> list[str]:
        """Find suggestions for misspelled abbreviations.

        Args:
            abbreviation: User-provided abbreviation
            content_type: Content type to search
            limit: Maximum number of suggestions

        Returns:
            List of suggested abbreviations
        """
        all_content = self.omnidexer.get_all_by_type(content_type)
        if not all_content:
            return []

        # Get all unique source abbreviations
        abbreviations = list(
            set(
                content.source.abbreviation.lower()
                for content in all_content
                if hasattr(content.source, "abbreviation")
            )
        )

        # Use difflib for fuzzy matching
        suggestions = difflib.get_close_matches(
            abbreviation.lower(), abbreviations, n=limit, cutoff=0.4
        )

        return suggestions

    def _resolve_content(
        self, content_type: ContentType, abbreviation: str
    ) -> ContentResolutionResult:
        """Internal method to resolve content by type and abbreviation.

        Args:
            content_type: Type of content to search for
            abbreviation: User-provided abbreviation

        Returns:
            ContentResolutionResult with resolution details
        """
        if not abbreviation.strip():
            return ContentResolutionResult(
                status=ResolutionStatus.NO_MATCH, query=abbreviation
            )

        # Normalize abbreviation for matching
        norm_abbrev = abbreviation.strip().lower()

        # Get all content of this type
        all_content = self.omnidexer.get_all_by_type(content_type)
        if not all_content:
            return ContentResolutionResult(
                status=ResolutionStatus.NO_MATCH, query=abbreviation
            )

        # Look for exact matches by source abbreviation
        exact_matches = [
            content
            for content in all_content
            if hasattr(content.source, "abbreviation")
            and content.source.abbreviation.lower() == norm_abbrev
        ]

        if len(exact_matches) == 1:
            return ContentResolutionResult(
                status=ResolutionStatus.EXACT_MATCH,
                content=exact_matches[0],
                query=abbreviation,
            )
        elif len(exact_matches) > 1:
            return ContentResolutionResult(
                status=ResolutionStatus.MULTIPLE_MATCHES,
                matches=exact_matches,
                query=abbreviation,
            )

        # Try fuzzy search by name if no exact abbreviation match
        search_results = self.omnidexer.search(abbreviation, content_type, limit=10)
        if search_results:
            # Check if any search result has a source abbreviation that closely matches
            fuzzy_matches = [
                content
                for content in search_results
                if hasattr(content.source, "abbreviation")
                and difflib.SequenceMatcher(
                    None, content.source.abbreviation.lower(), norm_abbrev
                ).ratio()
                > 0.6
            ]

            if len(fuzzy_matches) == 1:
                return ContentResolutionResult(
                    status=ResolutionStatus.FUZZY_MATCH,
                    content=fuzzy_matches[0],
                    query=abbreviation,
                )
            elif len(fuzzy_matches) > 1:
                return ContentResolutionResult(
                    status=ResolutionStatus.MULTIPLE_MATCHES,
                    matches=fuzzy_matches,
                    query=abbreviation,
                )

        # No matches found, provide suggestions
        suggestions = self.find_suggestions(abbreviation, content_type)
        return ContentResolutionResult(
            status=ResolutionStatus.NO_MATCH,
            suggestions=suggestions,
            query=abbreviation,
        )

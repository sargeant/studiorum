"""Content resolver for mapping user abbreviations to content objects.

Enhanced with async context integration and protocol-based service access
for modern MCP and CLI usage patterns.
"""

import asyncio
import difflib
from enum import Enum
from typing import TYPE_CHECKING, Any, Optional, Protocol, cast

from pydantic import BaseModel, ConfigDict, Field, field_validator

from studiorum.core.error_types import (
    ContentNotFoundError,
    MCPError,
)
from studiorum.core.loaders.content_merger import ContentMerger
from studiorum.core.logging import get_logger
from studiorum.core.models.content import BaseContent, ContentType
from studiorum.core.result import Error, Result, Success
from studiorum.core.services.protocols import OmnidexerProtocol, TagResolverProtocol

if TYPE_CHECKING:
    from studiorum.core.context import AsyncRequestContext
    from studiorum.core.loaders.omnidexer import Omnidexer
    from studiorum.core.models.item_filters import ItemFilterCriteria
    from studiorum.core.models.spell_filters import SpellFilterCriteria

logger = get_logger(__name__)


class ResolutionStatus(Enum):
    """Status of content resolution attempt."""

    EXACT_MATCH = "exact_match"
    MULTIPLE_MATCHES = "multiple_matches"
    NO_MATCH = "no_match"
    FUZZY_MATCH = "fuzzy_match"


class SpellResolutionResult(BaseModel):
    """Extended result for spell resolution with spell-specific metadata."""

    status: ResolutionStatus = Field(description="Status of the resolution attempt")
    spells: list[BaseContent] = Field(default_factory=list, description="Found spells")
    unresolved_names: list[str] = Field(
        default_factory=list, description="Names that couldn't be resolved"
    )
    suggestions: dict[str, list[str]] = Field(
        default_factory=dict, description="Suggestions for unresolved names"
    )
    total_found: int = Field(0, description="Total number of spells found")

    model_config = ConfigDict(arbitrary_types_allowed=True)


class ContentResolutionResult(BaseModel):
    """Result of content resolution attempt with comprehensive validation."""

    status: ResolutionStatus = Field(description="Status of the resolution attempt")
    content: BaseContent | None = Field(None, description="Resolved content if found")
    matches: list[BaseContent] = Field(
        default_factory=list, description="Multiple matches found"
    )
    suggestions: list[str] = Field(
        default_factory=list, description="Suggested alternatives"
    )
    query: str = Field(default="", description="Original query string")

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        """Validate query string (preserve original input for tracking)."""
        return v

    @field_validator("suggestions")
    @classmethod
    def validate_suggestions(cls, v: list[str]) -> list[str]:
        """Validate and clean suggestions list."""
        # Remove empty strings and duplicates while preserving order
        seen = set()
        cleaned = []
        for suggestion in v:
            cleaned_suggestion = suggestion.strip()
            if cleaned_suggestion and cleaned_suggestion not in seen:
                seen.add(cleaned_suggestion)
                cleaned.append(cleaned_suggestion)
        return cleaned

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

    model_config = ConfigDict(
        # Allow content objects (they should be Pydantic models too)
        arbitrary_types_allowed=True
    )


class ContentResolver:
    """Resolves user abbreviations to content objects using omnidexer.

    Enhanced with async context integration and protocol-based service access.
    Supports both legacy sync usage and modern async patterns for MCP integration.
    """

    def __init__(
        self,
        omnidexer: OmnidexerProtocol,
        tag_resolver: TagResolverProtocol | None = None,
        context: Optional["AsyncRequestContext"] = None,
    ) -> None:
        """Initialize resolver with protocol-validated services.

        Args:
            omnidexer: Protocol-validated omnidexer service
            tag_resolver: Optional tag resolver for entry processing
            context: Optional async request context for performance tracking
        """
        self.omnidexer = omnidexer
        self.tag_resolver = tag_resolver
        self.context = context

        # Initialize content merger using shared instance from omnidexer
        self.content_merger: ContentMerger | None = None

        # Try to get shared content merger from omnidexer first
        if hasattr(omnidexer, "get_content_merger"):
            self.content_merger = omnidexer.get_content_merger()
            if self.content_merger is not None:
                logger.debug("Using shared ContentMerger instance from omnidexer")
        elif hasattr(omnidexer, "_omnidexer") and hasattr(
            omnidexer._omnidexer, "get_content_merger"
        ):
            # Handle service wrapper - get shared instance from wrapped omnidexer
            self.content_merger = omnidexer._omnidexer.get_content_merger()
            if self.content_merger is not None:
                logger.debug(
                    "Using shared ContentMerger instance from wrapped omnidexer"
                )

        # Fallback to creating own instance if sharing not available
        if self.content_merger is None:
            logger.debug(
                "Shared ContentMerger not available, creating fallback instance"
            )
            # Check for source_manager on the omnidexer or its wrapped instance
            source_manager = None
            if hasattr(omnidexer, "source_manager"):
                source_manager = omnidexer.source_manager
            elif hasattr(omnidexer, "_omnidexer") and omnidexer._omnidexer is not None:
                # Handle service wrapper - get the actual omnidexer
                actual_omnidexer = omnidexer._omnidexer
                if hasattr(actual_omnidexer, "source_manager"):
                    source_manager = actual_omnidexer.source_manager

            if source_manager is not None:
                self.content_merger = ContentMerger(source_manager)
            else:
                logger.warning(
                    "No source manager found for content merger initialization"
                )

    @classmethod
    async def from_context(cls, context: "AsyncRequestContext") -> "ContentResolver":
        """Create resolver from context with protocol validation.

        Args:
            context: Async request context with protocol-based services

        Returns:
            ContentResolver instance with protocol-validated services
        """
        omnidexer = await context.get_service(OmnidexerProtocol)  # type: ignore[type-abstract] # Protocol type token - see TYPES.md
        tag_resolver = await context.get_service(TagResolverProtocol)  # type: ignore[type-abstract] # Protocol type token - see TYPES.md
        return cls(omnidexer, tag_resolver, context)

    def resolve_adventure(self, abbreviation: str) -> ContentResolutionResult:
        """Resolve abbreviation to an adventure.

        Args:
            abbreviation: User-provided abbreviation (e.g., "cos", "lmop")

        Returns:
            ContentResolutionResult with resolution details
        """
        adventure_type = ContentType("adventure")
        return self._resolve_content(adventure_type, abbreviation)

    def resolve_book(self, abbreviation: str) -> ContentResolutionResult:
        """Resolve abbreviation to a book.

        Args:
            abbreviation: User-provided abbreviation (e.g., "phb", "mm", "dmg")

        Returns:
            ContentResolutionResult with resolution details
        """
        book_type = ContentType("book")
        return self._resolve_content(book_type, abbreviation)

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
        adventure_type = ContentType("adventure")
        book_type = ContentType("book")
        for ct in [adventure_type, book_type]:
            result = self._resolve_content(ct, abbreviation)
            if result.is_success:
                return result

        # If no exact matches, return the first result with suggestions
        return self._resolve_content(adventure_type, abbreviation)

    def resolve_multiple(
        self, requests: list[tuple[str, ContentType]]
    ) -> list[ContentResolutionResult]:
        """Resolve multiple abbreviations concurrently for optimal performance.

        This method processes multiple resolution requests in parallel, which is
        particularly beneficial when multiple adventures/books need content loading.

        Args:
            requests: List of (abbreviation, content_type) tuples to resolve

        Returns:
            List of ContentResolutionResult objects corresponding to input requests
        """
        if not requests:
            return []

        # Create tasks for all resolution requests
        tasks = []
        for abbreviation, content_type in requests:
            task = self._resolve_content(content_type, abbreviation)
            tasks.append(task)

        # Execute all resolutions sequentially
        results = []
        for abbreviation, content_type in requests:
            try:
                results.append(self._resolve_content(content_type, abbreviation))
            except Exception:
                # Convert exception to failed resolution result
                results.append(
                    ContentResolutionResult(
                        status=ResolutionStatus.NO_MATCH,
                        query=abbreviation,
                        content=None,
                    )
                )

        return results

    def resolve_adventures_bulk(
        self, abbreviations: list[str]
    ) -> list[ContentResolutionResult]:
        """Resolve multiple adventures concurrently.

        Args:
            abbreviations: List of adventure abbreviations to resolve

        Returns:
            List of ContentResolutionResult objects
        """
        adventure_type = ContentType("adventure")
        requests = [(abbrev, adventure_type) for abbrev in abbreviations]
        return self.resolve_multiple(requests)

    def resolve_books_bulk(
        self, abbreviations: list[str]
    ) -> list[ContentResolutionResult]:
        """Resolve multiple books concurrently.

        Args:
            abbreviations: List of book abbreviations to resolve

        Returns:
            List of ContentResolutionResult objects
        """
        book_type = ContentType("book")
        requests = [(abbrev, book_type) for abbrev in abbreviations]
        return self.resolve_multiple(requests)

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
        # Protocol guarantees this method exists
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

    # Modern async methods with protocol validation and Result patterns

    async def resolve_adventure_async(
        self, abbreviation: str
    ) -> Result[BaseContent, MCPError]:
        """Async adventure resolution with protocol validation.

        Args:
            abbreviation: Adventure abbreviation to resolve

        Returns:
            Result containing resolved adventure or error details
        """
        try:
            # Performance monitoring
            if self.context:
                self.context.record_async_operation()

            # Apply context source filtering
            if self.context and self.context.sources:
                # Filter by sources if context specifies them
                # This would be implemented based on omnidexer's filtering capabilities
                pass

            # Async adventure lookup using sync method (to be enhanced)
            result = await asyncio.get_event_loop().run_in_executor(
                None, self.resolve_adventure, abbreviation
            )

            if result.is_success:
                if result.content is None:
                    return Error(
                        ContentNotFoundError(
                            message=f"Adventure '{abbreviation}' resolved successfully but content is None"
                        )
                    )
                return Success(result.content)
            else:
                # Convert resolution result to error
                if result.status == ResolutionStatus.NO_MATCH:
                    error = ContentNotFoundError(
                        message=f"Adventure '{abbreviation}' not found",
                        suggestions=result.suggestions,
                    )
                elif result.status == ResolutionStatus.MULTIPLE_MATCHES:
                    match_names = [match.name for match in result.matches[:5]]
                    error = ContentNotFoundError(
                        message=f"Multiple adventures found for '{abbreviation}'. Found: {', '.join(match_names)}",
                        suggestions=match_names,
                    )
                else:
                    error = ContentNotFoundError(
                        message=f"Adventure resolution failed for '{abbreviation}'"
                    )

                if self.context:
                    await self.context.add_async_error(error)
                return Error(error)

        except Exception as e:
            error = ContentNotFoundError(message=f"Adventure resolution failed: {e}")
            if self.context:
                await self.context.add_async_error(error)
            return Error(error)

    async def search_content_async(
        self, query: str, content_type: str
    ) -> Result[list[BaseContent], MCPError]:
        """Async content search with protocol validation.

        Args:
            query: Search query string
            content_type: Type of content to search for

        Returns:
            Result containing matching content list or error details
        """
        try:
            if self.context:
                self.context.record_async_operation()

            # Convert string content type to ContentType enum
            try:
                ct = ContentType(content_type)
            except ValueError:
                error = ContentNotFoundError(
                    message=f"Invalid content type: {content_type}"
                )
                if self.context:
                    await self.context.add_async_error(error)
                return Error(error)

            # Perform async search using omnidexer with type casting for extended interface
            def search_with_type() -> list[BaseContent]:
                if hasattr(self.omnidexer, "search") and hasattr(
                    self.omnidexer, "get_all_by_type"
                ):
                    # Cast to concrete type for extended search interface
                    from studiorum.core.loaders.omnidexer import Omnidexer

                    concrete_omnidexer = cast(Omnidexer, self.omnidexer)
                    return concrete_omnidexer.search(query, ct)
                else:
                    # Fallback to protocol interface
                    results = self.omnidexer.search(query)
                    return cast(list[BaseContent], results)

            search_results = await asyncio.get_event_loop().run_in_executor(
                None, search_with_type
            )

            if not search_results:
                error = ContentNotFoundError(
                    message=f"No {content_type} found matching '{query}'"
                )
                if self.context:
                    await self.context.add_async_error(error)
                return Error(error)

            # Apply tag resolution if tag resolver is available
            processed_results = search_results
            if self.tag_resolver and hasattr(search_results[0], "entries"):
                processed_results = []
                for content in search_results:
                    if hasattr(content, "entries") and content.entries:
                        # Process entries with tag resolver
                        # This would be implemented based on tag resolver's async API
                        processed_results.append(content)
                    else:
                        processed_results.append(content)

            return Success(processed_results)

        except Exception as e:
            error = ContentNotFoundError(message=f"Content search failed: {e}")
            if self.context:
                await self.context.add_async_error(error)
            return Error(error)

    async def resolve_spells_async(
        self, spell_names: list[str]
    ) -> Result[list[BaseContent], MCPError]:
        """Async spell resolution with fuzzy matching.

        Args:
            spell_names: List of spell names to resolve

        Returns:
            Result containing resolved spells or error details
        """
        try:
            if self.context:
                self.context.record_async_operation()

            # Use the existing sync method with async executor
            result = await asyncio.get_event_loop().run_in_executor(
                None, self.resolve_spells_by_names, spell_names
            )

            if result.status == ResolutionStatus.EXACT_MATCH or result.spells:
                return Success(result.spells)
            else:
                suggestions = []
                for name, name_suggestions in result.suggestions.items():
                    suggestions.extend(name_suggestions)

                error = ContentNotFoundError(
                    message=f"Spells not found: {', '.join(result.unresolved_names)}",
                    suggestions=suggestions[:10],  # Limit suggestions
                )
                if self.context:
                    await self.context.add_async_error(error)
                return Error(error)

        except Exception as e:
            error = ContentNotFoundError(message=f"Spell resolution failed: {e}")
            if self.context:
                await self.context.add_async_error(error)
            return Error(error)

    async def resolve_book_async(
        self, abbreviation: str
    ) -> Result[BaseContent, MCPError]:
        """Async book resolution with protocol validation.

        Args:
            abbreviation: Book abbreviation to resolve

        Returns:
            Result containing resolved book or error details
        """
        try:
            if self.context:
                self.context.record_async_operation()

            # Use sync method with async executor
            result = await asyncio.get_event_loop().run_in_executor(
                None, self.resolve_book, abbreviation
            )

            if result.is_success:
                if result.content is None:
                    return Error(
                        ContentNotFoundError(
                            message=f"Book '{abbreviation}' resolved successfully but content is None"
                        )
                    )
                return Success(result.content)
            else:
                if result.status == ResolutionStatus.NO_MATCH:
                    error = ContentNotFoundError(
                        message=f"Book '{abbreviation}' not found",
                        suggestions=result.suggestions,
                    )
                elif result.status == ResolutionStatus.MULTIPLE_MATCHES:
                    matches = [match.name for match in result.matches[:5]]
                    error = ContentNotFoundError(
                        message=f"Multiple books found for '{abbreviation}'",
                        suggestions=[f"Be more specific. Found: {', '.join(matches)}"],
                    )
                else:
                    error = ContentNotFoundError(
                        message=f"Book resolution failed for '{abbreviation}'"
                    )

                if self.context:
                    await self.context.add_async_error(error)
                return Error(error)

        except Exception as e:
            error = ContentNotFoundError(message=f"Book resolution failed: {e}")
            if self.context:
                await self.context.add_async_error(error)
            return Error(error)

    # Legacy sync wrapper methods for backward compatibility

    def resolve_adventure_sync(
        self, abbreviation: str
    ) -> Result[BaseContent, MCPError]:
        """Sync wrapper for adventure resolution."""
        return asyncio.run(self.resolve_adventure_async(abbreviation))

    def search_content_sync(
        self, query: str, content_type: str
    ) -> Result[list[BaseContent], MCPError]:
        """Sync wrapper for content search."""
        return asyncio.run(self.search_content_async(query, content_type))

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
        # Protocol guarantees this method exists
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
            # For adventures and books, merge metadata with content
            resolved_content = self._enrich_content_if_needed(
                exact_matches[0], content_type
            )
            return ContentResolutionResult(
                status=ResolutionStatus.EXACT_MATCH,
                content=resolved_content,
                query=abbreviation,
            )
        elif len(exact_matches) > 1:
            # Try to resolve ambiguity by preferring non-versioned content
            preferred_match = self._select_preferred_match(exact_matches)
            if preferred_match:
                resolved_content = self._enrich_content_if_needed(
                    preferred_match, content_type
                )
                return ContentResolutionResult(
                    status=ResolutionStatus.EXACT_MATCH,
                    content=resolved_content,
                    query=abbreviation,
                )
            return ContentResolutionResult(
                status=ResolutionStatus.MULTIPLE_MATCHES,
                matches=exact_matches,
                query=abbreviation,
            )

        # Try fuzzy search by name if no exact abbreviation match
        if hasattr(self.omnidexer, "search") and hasattr(
            self.omnidexer, "get_all_by_type"
        ):
            # Cast to concrete type for extended search interface
            from studiorum.core.loaders.omnidexer import Omnidexer

            concrete_omnidexer = cast(Omnidexer, self.omnidexer)
            search_results = concrete_omnidexer.search(
                abbreviation, content_type, limit=10
            )
        else:
            # Fallback to protocol interface
            protocol_results = self.omnidexer.search(abbreviation)
            search_results = cast(list[BaseContent], protocol_results)[:10]
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
                resolved_content = self._enrich_content_if_needed(
                    fuzzy_matches[0], content_type
                )
                return ContentResolutionResult(
                    status=ResolutionStatus.FUZZY_MATCH,
                    content=resolved_content,
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

    def _select_preferred_match(self, matches: list[BaseContent]) -> BaseContent | None:
        """Select the preferred match from multiple exact matches.

        When multiple content items have the same abbreviation, this method
        applies heuristics to select the most appropriate one:
        1. For PHB specifically, prefer the original "Player's Handbook (2014)" over the 2024 revised version
        2. Otherwise, prefer items without year suffixes in parentheses
        3. Prefer shorter names when all else is equal
        4. Return None if no clear preference can be determined

        Args:
            matches: List of content items with identical abbreviations

        Returns:
            The preferred match, or None if no clear preference exists
        """
        if not matches:
            return None
        if len(matches) == 1:
            return matches[0]

        # Special case for PHB: prefer the original 2014 version over the 2024 revised version
        # This ensures users get the classic PHB content when they request "phb"
        if len(matches) == 2 and all(
            hasattr(match.source, "abbreviation")
            and match.source.abbreviation.upper() == "PHB"
            for match in matches
        ):
            # Look for the 2014 version (with year suffix)
            versioned_2014 = [
                match
                for match in matches
                if "(2014)" in match.name or "Player's Handbook (2014)" == match.name
            ]
            if versioned_2014:
                return versioned_2014[0]

            # Fallback: prefer the one with year suffix (more specific)
            versioned = [
                match for match in matches if self._has_year_suffix(match.name)
            ]
            if versioned:
                return versioned[0]

        # Priority 1: Prefer items without year suffixes in parentheses
        non_versioned = [
            match for match in matches if not self._has_year_suffix(match.name)
        ]

        if len(non_versioned) == 1:
            return non_versioned[0]
        elif len(non_versioned) > 1:
            # Multiple non-versioned matches, use shorter name as tiebreaker
            return min(non_versioned, key=lambda x: len(x.name))

        # Priority 2: If all have year suffixes, prefer the shortest name
        return min(matches, key=lambda x: len(x.name))

    def _has_year_suffix(self, name: str) -> bool:
        """Check if a name has a year suffix in parentheses.

        Examples:
        - "Player's Handbook (2014)" -> True
        - "Player's Handbook" -> False
        - "Xanathar's Guide (2017)" -> True

        Args:
            name: The name to check

        Returns:
            True if the name has a year suffix in parentheses
        """
        import re

        # Look for pattern like "(2014)" or "(2024)" at the end of the name
        return bool(re.search(r"\(\d{4}\)\s*$", name))

    def _enrich_content_if_needed(
        self, content: BaseContent, content_type: ContentType
    ) -> BaseContent:
        """Enrich content with on-demand loading for dual-file types.

        For adventures and books, this method loads the content file and merges it
        with metadata to provide complete content. For other content types, returns
        the content unchanged.

        Args:
            content: The content object (likely metadata-only for adventures/books)
            content_type: The type of content being resolved

        Returns:
            Enriched content object with merged metadata+content data
        """
        # Only enrich adventures and books (dual-file types)
        adventure_type = ContentType("adventure")
        book_type = ContentType("book")
        if content_type not in [adventure_type, book_type]:
            return content

        # Extract content ID from the content object
        content_id = getattr(content, "id", None)
        if not content_id:
            logger.warning(
                f"No ID found for {content_type.value}, cannot load content file"
            )
            return content

        logger.debug(
            f"Enriching {content_type.value} '{content.name}' (ID: {content_id}) with content data"
        )

        try:
            # Load the content file
            if self.content_merger is None:
                logger.warning("Content merger not available, cannot enrich content")
                return content
            content_data = self.content_merger.load_content_file(
                content_type, content_id
            )

            # Convert content object to dict for merging
            if hasattr(content, "model_dump"):
                # Pydantic model
                metadata_dict = content.model_dump()
            elif hasattr(content, "__dict__"):
                # Regular object
                metadata_dict = content.__dict__.copy()
            else:
                # Fallback - convert to dict
                metadata_dict = dict(content)

            # Merge metadata and content data
            if self.content_merger is None:
                logger.warning("Content merger not available, cannot merge content")
                return content
            merged_data = self.content_merger.merge_metadata_content(
                metadata_dict, content_data
            )

            # Create new content object from merged data
            content_class = type(content)
            if hasattr(content_class, "model_validate"):
                # Pydantic model
                enriched_content = content_class.model_validate(merged_data)
            else:
                # Regular class - try to create instance
                enriched_content = content_class(**merged_data)

            logger.debug(
                f"Successfully enriched {content_type.value} with {len(merged_data.get('contents', []))} sections"
            )
            return enriched_content

        except Exception as e:
            logger.error(f"Failed to enrich {content_type.value} '{content.name}': {e}")
            # Return original content if enrichment fails
            return content

    def resolve_spells_by_names(self, names: list[str]) -> SpellResolutionResult:
        """Resolve multiple spells by name with fuzzy matching.

        Args:
            names: List of spell names to resolve

        Returns:
            SpellResolutionResult with found spells and unresolved names
        """
        result = SpellResolutionResult(status=ResolutionStatus.EXACT_MATCH)
        spell_type = ContentType("spell")

        for name in names:
            # Try exact match first - protocol guarantees this method exists
            matches = self.omnidexer.find_all(spell_type, name)

            if matches:
                # Add all exact matches
                result.spells.extend(matches)
                result.total_found += len(matches)
            else:
                # No exact match, try fuzzy matching
                suggestions = self._find_spell_suggestions(name)
                result.unresolved_names.append(name)
                if suggestions:
                    result.suggestions[name] = suggestions

        # Update status based on results
        if result.unresolved_names:
            if result.spells:
                result.status = ResolutionStatus.FUZZY_MATCH  # Partial success
            else:
                result.status = ResolutionStatus.NO_MATCH

        return result

    def resolve_spells_by_criteria(
        self, criteria: "SpellFilterCriteria"
    ) -> list[BaseContent]:
        """Resolve spells matching filter criteria.

        Args:
            criteria: SpellFilterCriteria object with filtering parameters

        Returns:
            List of matching spell objects
        """
        # Import here to avoid circular imports
        from ..services.spell_collector import SpellCollector

        collector = SpellCollector(cast("Omnidexer", self.omnidexer))
        result = collector.collect_spells(criteria)

        return result.spells

    def _find_spell_suggestions(self, name: str) -> list[str]:
        """Find suggestions for a misspelled spell name.

        Args:
            name: The spell name to find suggestions for

        Returns:
            List of suggested spell names
        """
        spell_type = ContentType("spell")
        # Protocol guarantees this method exists
        all_spells = self.omnidexer.get_all_by_type(spell_type)

        if not all_spells:
            return []

        # Get all spell names
        spell_names = []
        for spell in all_spells:
            spell_names.append(spell.name)

        # Use difflib for fuzzy matching
        suggestions = difflib.get_close_matches(name, spell_names, n=5, cutoff=0.4)

        return suggestions

    def resolve_items_by_names(self, names: list[str]) -> list[ContentResolutionResult]:
        """Resolve multiple items by name with fuzzy matching.

        Args:
            names: List of item names to resolve

        Returns:
            List of ContentResolutionResult with found items and unresolved names
        """
        results = []
        item_type = ContentType("item")

        for name in names:
            # Try exact match first - protocol guarantees this method exists
            matches = self.omnidexer.find_all(item_type, name)

            if matches and len(matches) == 1:
                results.append(
                    ContentResolutionResult(
                        status=ResolutionStatus.EXACT_MATCH,
                        content=matches[0],
                        query=name,
                    )
                )
            elif len(matches) > 1:
                results.append(
                    ContentResolutionResult(
                        status=ResolutionStatus.MULTIPLE_MATCHES,
                        matches=matches,
                        query=name,
                    )
                )
            else:
                # No exact match, find suggestions
                suggestions = self._find_item_suggestions(name)
                results.append(
                    ContentResolutionResult(
                        status=ResolutionStatus.NO_MATCH,
                        suggestions=suggestions,
                        query=name,
                    )
                )

        return results

    def resolve_items_by_criteria(
        self, criteria: "ItemFilterCriteria"
    ) -> list[BaseContent]:
        """Resolve items matching filter criteria.

        Args:
            criteria: ItemFilterCriteria object with filtering parameters

        Returns:
            List of matching item objects
        """
        # Import here to avoid circular imports
        from ..services.item_collector import ItemCollector

        collector = ItemCollector(cast("Omnidexer", self.omnidexer))
        result = collector.collect_items(criteria)

        return result.items

    def _find_item_suggestions(self, name: str) -> list[str]:
        """Find suggestions for a misspelled item name.

        Args:
            name: The item name to find suggestions for

        Returns:
            List of suggested item names
        """
        item_type = ContentType("item")
        # Protocol guarantees this method exists
        all_items = self.omnidexer.get_all_by_type(item_type)

        if not all_items:
            return []

        # Get all item names
        item_names = []
        for item in all_items:
            item_names.append(item.name)

        # Use difflib for fuzzy matching
        suggestions = difflib.get_close_matches(name, item_names, n=5, cutoff=0.4)

        return suggestions

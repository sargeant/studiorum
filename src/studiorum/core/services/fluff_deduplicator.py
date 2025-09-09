"""FluffDeduplicator service for preventing duplicate fluff content in compendiums."""

import hashlib
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..references.content_tracker import ContentTracker

from ..logging import get_logger
from ..models.fluff import BaseFluff

logger = get_logger(__name__)


class DeduplicationStrategy(str, Enum):
    """Strategy for handling duplicate fluff content."""

    STRICT = "strict"  # Hash content only, exact matches required
    LOOSE = "loose"  # Hash content + metadata, more flexible matching
    NONE = "none"  # Disable deduplication entirely


class FluffDeduplicator:
    """Service for preventing duplicate fluff content in compendiums.

    This service creates content hashes for fluff entries and prevents
    duplicate content from being included multiple times in generated
    documents. Particularly useful for shared content like dragon lairs
    that appear across multiple creature types.

    Example use case:
        Multiple dragon types often share identical lair descriptions
        and regional effects. The deduplicator detects this shared content
        and renders it once with cross-references rather than duplicating
        the same text multiple times.
    """

    def __init__(
        self,
        strategy: DeduplicationStrategy = DeduplicationStrategy.STRICT,
        content_tracker: "ContentTracker | None" = None,
    ) -> None:
        """Initialize the FluffDeduplicator.

        Args:
            strategy: Deduplication strategy to use
            content_tracker: Optional content tracker for cross-reference tracking
        """
        self.strategy = strategy
        self.content_tracker = content_tracker
        self._seen_hashes: set[str] = set()
        self._hash_to_content: dict[str, BaseFluff] = {}
        self._duplicate_references: dict[str, list[str]] = {}

    def should_include(self, fluff: BaseFluff) -> bool:
        """Check if fluff content is unique and should be included.

        Args:
            fluff: The fluff entry to check

        Returns:
            True if the fluff content should be included, False if it's a duplicate
        """
        if self.strategy == DeduplicationStrategy.NONE:
            return True

        content_hash = self._hash_fluff_content(fluff)

        if content_hash in self._seen_hashes:
            # Track this as a duplicate reference
            original_fluff = self._hash_to_content[content_hash]
            self._track_duplicate_reference(original_fluff, fluff)
            logger.debug(
                f"Duplicate fluff detected: '{fluff.name}' ({fluff.source.abbreviation}) "
                f"matches '{original_fluff.name}' ({original_fluff.source.abbreviation})"
            )
            return False

        # First time seeing this content - include it
        self._seen_hashes.add(content_hash)
        self._hash_to_content[content_hash] = fluff
        logger.debug(
            f"Including unique fluff: '{fluff.name}' ({fluff.source.abbreviation})"
        )
        return True

    def get_duplicate_references(self, fluff: BaseFluff) -> list[str]:
        """Get list of content names that reference the same fluff.

        Args:
            fluff: The fluff entry to check

        Returns:
            List of content names that would have shown the same fluff content
        """
        content_hash = self._hash_fluff_content(fluff)
        return self._duplicate_references.get(content_hash, [])

    def get_statistics(self) -> dict[str, int]:
        """Get deduplication statistics.

        Returns:
            Dictionary with statistics about processed and deduplicated content
        """
        total_duplicates = sum(
            len(refs) for refs in self._duplicate_references.values()
        )
        return {
            "unique_fluff_included": len(self._seen_hashes),
            "duplicate_fluff_detected": total_duplicates,
            "total_fluff_processed": len(self._seen_hashes) + total_duplicates,
            "deduplication_savings": total_duplicates,
        }

    def reset(self) -> None:
        """Reset the deduplicator state for a new document."""
        self._seen_hashes.clear()
        self._hash_to_content.clear()
        self._duplicate_references.clear()

    def _hash_fluff_content(self, fluff: BaseFluff) -> str:
        """Create a hash of fluff content for deduplication.

        Args:
            fluff: The fluff entry to hash

        Returns:
            Hash string representing the content
        """
        hasher = hashlib.sha256()

        if self.strategy == DeduplicationStrategy.STRICT:
            # STRICT: Only hash the actual text content
            content_text = fluff.get_text()
            if content_text:
                hasher.update(content_text.encode("utf-8"))

            # Include images for more comprehensive matching
            image_paths = fluff.get_image_paths()
            for path in sorted(image_paths):  # Sort for consistent hashing
                hasher.update(path.encode("utf-8"))

        elif self.strategy == DeduplicationStrategy.LOOSE:
            # LOOSE: Include content plus structural metadata
            content_text = fluff.get_text()
            if content_text:
                hasher.update(content_text.encode("utf-8"))

            # Include images
            image_paths = fluff.get_image_paths()
            for path in sorted(image_paths):  # Sort for consistent hashing
                hasher.update(path.encode("utf-8"))

            # Include metadata for looser matching
            # This catches cases where content is identical but metadata differs
            if hasattr(fluff, "type") and fluff.type:
                hasher.update(str(fluff.type).encode("utf-8"))

            # Include entry types and names for structural similarity
            for entry in fluff.entries:
                if entry.type:
                    hasher.update(entry.type.encode("utf-8"))
                if entry.name:
                    hasher.update(entry.name.encode("utf-8"))

        # NONE strategy should never call this method
        return hasher.hexdigest()

    def _track_duplicate_reference(
        self, original_fluff: BaseFluff, duplicate_fluff: BaseFluff
    ) -> None:
        """Track that duplicate_fluff references the same content as original_fluff.

        Args:
            original_fluff: The original fluff that was included
            duplicate_fluff: The duplicate fluff that was skipped
        """
        content_hash = self._hash_fluff_content(original_fluff)

        if content_hash not in self._duplicate_references:
            self._duplicate_references[content_hash] = []

        # Track the duplicate by name and source for reference generation
        duplicate_id = f"{duplicate_fluff.name} ({duplicate_fluff.source.abbreviation})"
        self._duplicate_references[content_hash].append(duplicate_id)

        # If we have a content tracker, register the cross-reference
        if self.content_tracker:
            # Track that the duplicate content references the original
            self.content_tracker.add_content(
                content_type="fluff_reference",
                name=f"{original_fluff.name} (shared with {duplicate_fluff.name})",
                source=original_fluff.source.abbreviation,
            )

    def get_service_name(self) -> str:
        """Return the service name for debugging and logging.

        Returns:
            Human-readable service name for identification
        """
        return "FluffDeduplicator"


def create_fluff_deduplicator_service(
    strategy: DeduplicationStrategy = DeduplicationStrategy.STRICT,
    content_tracker: "ContentTracker | None" = None,
) -> FluffDeduplicator:
    """Factory function for creating FluffDeduplicator instances.

    Args:
        strategy: Deduplication strategy to use
        content_tracker: Optional content tracker for cross-reference tracking

    Returns:
        Configured FluffDeduplicator instance
    """
    return FluffDeduplicator(strategy=strategy, content_tracker=content_tracker)

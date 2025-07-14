"""Content tracking for appendix generation."""

from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple


@dataclass
class TrackedContent:
    """Represents a piece of tracked content."""

    content_type: str
    name: str
    source: Optional[str] = None
    page: Optional[str] = None

    def __post_init__(self):
        """Normalize the content after initialization."""
        self.content_type = self.content_type.lower()
        self.name = self.name.strip()
        if self.source:
            self.source = self.source.strip()
        if self.page:
            self.page = self.page.strip()

    def to_tuple(self) -> Tuple[str, str, Optional[str]]:
        """Convert to tuple for set operations."""
        return (self.content_type, self.name, self.source)

    def __hash__(self) -> int:
        """Hash based on type, name, and source."""
        return hash(self.to_tuple())

    def __eq__(self, other) -> bool:
        """Equality based on type, name, and source."""
        if not isinstance(other, TrackedContent):
            return False
        return self.to_tuple() == other.to_tuple()


class ContentTracker:
    """Tracks content references for appendix generation."""

    def __init__(self):
        self._tracked_content: Set[TrackedContent] = set()
        self._content_counts: Dict[Tuple[str, str, Optional[str]], int] = {}

    def add_content(
        self,
        content_type: str,
        name: str,
        source: Optional[str] = None,
        page: Optional[str] = None,
    ) -> None:
        """Add content to tracking."""
        content = TrackedContent(content_type, name, source, page)

        # Add to set (handles deduplication automatically)
        self._tracked_content.add(content)

        # Track reference count
        key = content.to_tuple()
        self._content_counts[key] = self._content_counts.get(key, 0) + 1

    def get_tracked_content(self) -> List[TrackedContent]:
        """Get all tracked content in sorted order."""
        return sorted(
            list(self._tracked_content),
            key=lambda x: (x.content_type, x.name, x.source or ""),
        )

    def get_tracked_content_by_type(self, content_type: str) -> List[TrackedContent]:
        """Get tracked content filtered by type."""
        content_type = content_type.lower()
        return [
            content
            for content in self.get_tracked_content()
            if content.content_type == content_type
        ]

    def get_content_count(
        self, content_type: str, name: str, source: Optional[str] = None
    ) -> int:
        """Get the number of times specific content has been referenced."""
        key = (content_type.lower(), name.strip(), source.strip() if source else None)
        return self._content_counts.get(key, 0)

    def get_content_types(self) -> List[str]:
        """Get all content types that have been tracked."""
        types = set(content.content_type for content in self._tracked_content)
        return sorted(list(types))

    def get_statistics(self) -> Dict[str, int]:
        """Get tracking statistics."""
        stats = {
            "total_unique_content": len(self._tracked_content),
            "total_references": sum(self._content_counts.values()),
        }

        # Add per-type counts
        for content_type in self.get_content_types():
            type_content = self.get_tracked_content_by_type(content_type)
            stats[f"{content_type}_count"] = len(type_content)

        return stats

    def clear(self) -> None:
        """Clear all tracked content."""
        self._tracked_content.clear()
        self._content_counts.clear()

    def has_content(
        self, content_type: str, name: str, source: Optional[str] = None
    ) -> bool:
        """Check if specific content has been tracked."""
        content = TrackedContent(content_type, name, source)
        return content in self._tracked_content

    def remove_content(
        self, content_type: str, name: str, source: Optional[str] = None
    ) -> bool:
        """Remove specific content from tracking. Returns True if removed."""
        content = TrackedContent(content_type, name, source)
        if content in self._tracked_content:
            self._tracked_content.remove(content)
            key = content.to_tuple()
            if key in self._content_counts:
                del self._content_counts[key]
            return True
        return False

    def merge_tracker(self, other: "ContentTracker") -> None:
        """Merge another tracker's content into this one."""
        for content in other._tracked_content:
            # Add content (will handle deduplication)
            self.add_content(
                content.content_type, content.name, content.source, content.page
            )

    def export_for_appendix(self) -> Dict[str, List[Dict[str, str]]]:
        """Export tracked content in a format suitable for appendix generation."""
        result = {}

        for content_type in self.get_content_types():
            type_content = self.get_tracked_content_by_type(content_type)
            result[content_type] = []

            for content in type_content:
                entry = {
                    "name": content.name,
                    "type": content.content_type,
                }
                if content.source:
                    entry["source"] = content.source
                if content.page:
                    entry["page"] = content.page

                # Add reference count
                entry["reference_count"] = self.get_content_count(
                    content.content_type, content.name, content.source
                )

                result[content_type].append(entry)

        return result

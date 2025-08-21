"""Fast content indexing system for metadata-only search operations."""

import asyncio
import hashlib
import json
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from ..models.content import ContentType


@dataclass
class ContentMetadata:
    """Lightweight content metadata for fast searching."""

    id: str
    name: str
    content_type: str
    source: str
    search_terms: set[str]
    file_path: Path
    file_size: int
    last_modified: float

    def __post_init__(self) -> None:
        """Ensure search_terms is a set."""
        if isinstance(self.search_terms, list | tuple):
            self.search_terms = set(self.search_terms)


class FastContentIndex:
    """Ultra-fast content index built from file metadata without loading full content."""

    def __init__(self) -> None:
        self.metadata: dict[str, ContentMetadata] = {}
        self.search_index: dict[str, set[str]] = defaultdict(set)  # term -> content_ids
        self.type_groups: dict[str, set[str]] = defaultdict(set)  # type -> content_ids
        self.source_groups: dict[str, set[str]] = defaultdict(
            set
        )  # source -> content_ids
        self._last_built: datetime | None = None

    async def build_from_files(
        self, content_files: dict[ContentType, list[Path]]
    ) -> None:
        """Build index from file metadata without loading full content.

        Args:
            content_files: Dictionary mapping content types to file paths
        """
        index_tasks = []
        for content_type, file_paths in content_files.items():
            for file_path in file_paths:
                if file_path.exists():
                    task = self._index_file_metadata(content_type, file_path)
                    index_tasks.append(task)

        # Process files concurrently
        if index_tasks:
            await asyncio.gather(*index_tasks, return_exceptions=True)

        # Build search indices from metadata
        self._build_search_indices()
        self._last_built = datetime.now()

    async def _index_file_metadata(
        self, content_type: ContentType, file_path: Path
    ) -> None:
        """Extract metadata from file without full parsing.

        Args:
            content_type: Type of content being indexed
            file_path: Path to the content file
        """
        try:
            # Read first portion of JSON file to extract names/metadata
            with open(file_path, "r", encoding="utf-8") as f:
                # Read first 10KB to extract item names and basic metadata
                preview_content = f.read(10240)

            # Fast JSON parsing of preview to extract names
            metadata_items = await self._extract_metadata_from_preview(
                preview_content, content_type, file_path
            )

            for metadata in metadata_items:
                self.metadata[metadata.id] = metadata

        except Exception:  # nosec B110
            # Skip files that can't be indexed - don't fail entire indexing
            pass

    async def _extract_metadata_from_preview(
        self, preview: str, content_type: ContentType, file_path: Path
    ) -> list[ContentMetadata]:
        """Extract metadata from JSON preview.

        Args:
            preview: First portion of JSON file content
            content_type: Content type being processed
            file_path: Path to source file

        Returns:
            List of extracted metadata objects
        """
        metadata_items: list[ContentMetadata] = []

        try:
            # Get file stats
            stat_info = file_path.stat()
            file_size = stat_info.st_size
            last_modified = stat_info.st_mtime

            # Try to parse the preview as JSON
            try:
                preview_data = json.loads(preview)
            except json.JSONDecodeError:
                # Try to repair truncated JSON by adding closing brackets
                repaired = preview.rstrip() + "]}"
                try:
                    preview_data = json.loads(repaired)
                except json.JSONDecodeError:
                    return metadata_items

            # Extract items based on 5etools structure
            items_data = []
            if isinstance(preview_data, dict):
                # Look for common 5etools array keys
                for key in [
                    "spell",
                    "monster",
                    "item",
                    "class",
                    "race",
                    "feat",
                    "background",
                ]:
                    if key in preview_data and isinstance(preview_data[key], list):
                        items_data.extend(
                            preview_data[key][:50]
                        )  # Limit to first 50 items
                        break
                else:
                    # Check for 'data' key used in content files
                    if "data" in preview_data and isinstance(
                        preview_data["data"], list
                    ):
                        items_data = preview_data["data"][:50]
            elif isinstance(preview_data, list):
                items_data = preview_data[:50]

            # Process each item to create metadata
            for item in items_data:
                if not isinstance(item, dict) or "name" not in item:
                    continue

                # Extract basic info
                name = item.get("name", "")
                source = self._extract_source(item)

                if not name:
                    continue

                # Generate content ID
                content_id = self._generate_content_id(
                    content_type, name, source, file_path
                )

                # Extract search terms
                search_terms = self._extract_search_terms(item, content_type)

                metadata = ContentMetadata(
                    id=content_id,
                    name=name,
                    content_type=content_type.value,
                    source=source,
                    search_terms=search_terms,
                    file_path=file_path,
                    file_size=file_size,
                    last_modified=last_modified,
                )

                metadata_items.append(metadata)

        except Exception:  # nosec B110
            # Return what we could extract
            pass

        return metadata_items

    def _extract_source(self, item: dict[str, Any]) -> str:
        """Extract source information from content item.

        Args:
            item: Content item dictionary

        Returns:
            Source abbreviation or identifier
        """
        source = item.get("source", "Unknown")

        # Handle different source formats
        if isinstance(source, dict):
            return str(source.get("abbreviation", source.get("source", "Unknown")))
        elif isinstance(source, str):
            return source
        else:
            return str(source)

    def _extract_search_terms(
        self, item: dict[str, Any], content_type: ContentType
    ) -> set[str]:
        """Extract searchable terms from content item.

        Args:
            item: Content item dictionary
            content_type: Type of content

        Returns:
            Set of search terms
        """
        terms = set()

        # Always include name
        if "name" in item:
            name = item["name"].lower()
            terms.add(name)
            # Add individual words from name
            terms.update(word.strip() for word in name.split() if len(word.strip()) > 2)

        # Content-type specific term extraction
        if content_type.value == "spell":
            # Add spell school and level
            if "school" in item:
                school = item["school"]
                if isinstance(school, dict):
                    terms.add(school.get("name", "").lower())
                elif isinstance(school, str):
                    terms.add(school.lower())

            if "level" in item:
                terms.add(f"level {item['level']}")

        elif content_type.value == "monster":
            # Add creature type and size
            if "type" in item:
                creature_type = item["type"]
                if isinstance(creature_type, dict):
                    terms.add(creature_type.get("type", "").lower())
                elif isinstance(creature_type, str):
                    terms.add(creature_type.lower())

            if "size" in item:
                size = item["size"]
                if isinstance(size, list):
                    terms.update(s.lower() for s in size if isinstance(s, str))
                elif isinstance(size, str):
                    terms.add(size.lower())

        elif content_type.value == "item":
            # Add item type and rarity
            if "type" in item:
                item_type = item["type"]
                if isinstance(item_type, str):
                    terms.add(item_type.lower())

            if "rarity" in item:
                rarity = item["rarity"]
                if isinstance(rarity, str):
                    terms.add(rarity.lower())

        # Remove empty terms and very short terms
        return {term for term in terms if term and len(term) > 1}

    def _generate_content_id(
        self, content_type: ContentType, name: str, source: str, file_path: Path
    ) -> str:
        """Generate unique content ID.

        Args:
            content_type: Content type
            name: Content name
            source: Content source
            file_path: Source file path

        Returns:
            Unique content identifier
        """
        identifier = f"{content_type.value}:{name}:{source}:{file_path.name}"
        return hashlib.sha256(identifier.encode()).hexdigest()[:12]

    def _build_search_indices(self) -> None:
        """Build search indices from collected metadata."""
        self.search_index.clear()
        self.type_groups.clear()
        self.source_groups.clear()

        for content_id, metadata in self.metadata.items():
            # Build search term index
            for term in metadata.search_terms:
                if term:
                    self.search_index[term].add(content_id)

            # Build type index
            self.type_groups[metadata.content_type].add(content_id)

            # Build source index
            self.source_groups[metadata.source].add(content_id)

    def search(
        self, query: str, content_type: str | None = None, limit: int = 50
    ) -> list[ContentMetadata]:
        """Ultra-fast metadata search (<5ms).

        Args:
            query: Search query string
            content_type: Optional content type filter
            limit: Maximum results to return

        Returns:
            List of matching content metadata
        """
        if not query:
            return []

        query_terms = [
            term.lower().strip() for term in query.split() if len(term.strip()) > 1
        ]
        if not query_terms:
            return []

        # Find content IDs matching all query terms
        matching_ids = None

        for term in query_terms:
            # Look for exact matches and prefix matches
            term_matches = set()

            # Exact match
            if term in self.search_index:
                term_matches.update(self.search_index[term])

            # Prefix matching for better user experience
            for indexed_term, content_ids in self.search_index.items():
                if indexed_term.startswith(term):
                    term_matches.update(content_ids)

            # Intersect with previous results (AND logic)
            if matching_ids is None:
                matching_ids = term_matches
            else:
                matching_ids &= term_matches

            # Early exit if no matches
            if not matching_ids:
                break

        if not matching_ids:
            return []

        # Filter by content type if specified
        if content_type:
            type_matches = self.type_groups.get(content_type, set())
            matching_ids &= type_matches

        # Convert to metadata objects and sort by relevance
        results = []
        for content_id in matching_ids:
            if content_id in self.metadata:
                metadata = self.metadata[content_id]
                results.append(metadata)

        # Simple relevance scoring: prioritize exact name matches
        def relevance_score(meta: ContentMetadata) -> tuple[int, str]:
            # Higher score for exact name matches
            name_lower = meta.name.lower()
            query_lower = query.lower()

            if name_lower == query_lower:
                return (100, meta.name)
            elif query_lower in name_lower:
                return (50, meta.name)
            elif name_lower.startswith(query_lower):
                return (75, meta.name)
            else:
                return (1, meta.name)

        results.sort(key=relevance_score, reverse=True)
        return results[:limit]

    def get_by_type(self, content_type: str, limit: int = 100) -> list[ContentMetadata]:
        """Get all metadata for a specific content type.

        Args:
            content_type: Content type to retrieve
            limit: Maximum results

        Returns:
            List of metadata for the content type
        """
        content_ids = self.type_groups.get(content_type, set())
        results = []

        for content_id in content_ids:
            if content_id in self.metadata:
                results.append(self.metadata[content_id])
                if len(results) >= limit:
                    break

        return sorted(results, key=lambda m: m.name)

    def get_by_source(self, source: str, limit: int = 100) -> list[ContentMetadata]:
        """Get all metadata for a specific source.

        Args:
            source: Source to retrieve
            limit: Maximum results

        Returns:
            List of metadata for the source
        """
        content_ids = self.source_groups.get(source, set())
        results = []

        for content_id in content_ids:
            if content_id in self.metadata:
                results.append(self.metadata[content_id])
                if len(results) >= limit:
                    break

        return sorted(results, key=lambda m: (m.content_type, m.name))

    def get_statistics(self) -> dict[str, Any]:
        """Get index statistics.

        Returns:
            Dictionary with indexing statistics
        """
        return {
            "total_items": len(self.metadata),
            "content_types": len(self.type_groups),
            "sources": len(self.source_groups),
            "search_terms": len(self.search_index),
            "last_built": self._last_built.isoformat() if self._last_built else None,
            "by_type": {
                content_type: len(content_ids)
                for content_type, content_ids in self.type_groups.items()
            },
        }

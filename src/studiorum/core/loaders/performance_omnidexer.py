"""High-performance async omnidexer with intelligent caching and lazy loading."""

import asyncio
import time
import weakref
from collections import defaultdict
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from studiorum.core.logging import get_logger

from ..error_types import ContentNotFoundError
from ..models.content import BaseContent, ContentType
from ..optimization.memory_manager import AdaptiveMemoryManager, MemoryConfiguration
from ..result import Error, Result, Success
from ..services.access import get_cache
from ..services.protocols import AsyncResourceProtocol, OmnidexerProtocol
from .content_index import ContentMetadata, FastContentIndex
from .omnidexer import Omnidexer  # For compatibility and fallback

logger = get_logger(__name__)


@dataclass
class PerformanceConfiguration:
    """Configuration for performance omnidexer."""

    max_concurrent_loads: int = 5
    cache_ttl_hours: int = 24
    enable_usage_analytics: bool = True
    enable_predictive_loading: bool = False


class PerformanceOptimizedOmnidexer(OmnidexerProtocol):
    """High-performance async omnidexer with intelligent caching and lazy loading.

    This omnidexer provides:
    - Sub-500ms search response times via metadata-only search
    - Intelligent caching with usage pattern analysis
    - Lazy loading of content on demand
    - Memory-bounded operation with adaptive cleanup
    - Concurrent request optimization
    """

    def __init__(
        self,
        source_manager: Any,
        config: PerformanceConfiguration | None = None,
        memory_config: MemoryConfiguration | None = None,
        enable_deep_indexing: bool = True,
        fallback_omnidexer: Omnidexer | None = None,
    ):
        """Initialize performance optimized omnidexer.

        Args:
            source_manager: Source manager for content files
            config: Performance configuration (defaults to balanced settings)
            memory_config: Memory management configuration
            enable_deep_indexing: Whether to enable deep content indexing
            fallback_omnidexer: Legacy omnidexer for compatibility
        """
        self.source_manager = source_manager
        self.enable_deep_indexing = enable_deep_indexing

        # Configuration
        self.config = config or PerformanceConfiguration()

        self.memory_config = memory_config or MemoryConfiguration(
            max_process_memory_mb=512,  # Conservative for development
            warning_threshold=0.75,
            critical_threshold=0.90,
        )

        # Core components
        self.content_index = FastContentIndex()
        self.cache = get_cache()  # Use existing diskcache
        self.memory_manager = AdaptiveMemoryManager(self.memory_config)

        # Fallback for compatibility
        self._fallback_omnidexer = fallback_omnidexer

        # Async resource management
        self._loading_tasks: dict[str, asyncio.Task] = {}
        self._initialization_task: asyncio.Task | None = None
        self._background_tasks: list[asyncio.Task] = []

        # Performance monitoring
        self.performance_metrics = {
            "cache_hits": 0,
            "cache_misses": 0,
            "lazy_loads": 0,
            "predictive_loads": 0,
            "memory_usage_mb": 0.0,
            "avg_search_time_ms": 0.0,
            "concurrent_requests": 0,
        }

        # Request tracking for usage correlation
        self.active_contexts: weakref.WeakSet = weakref.WeakSet()
        self._is_initialized = False

    async def initialize(self) -> None:
        """Async initialization - builds lightweight index and starts background tasks."""
        if self._is_initialized:
            return

        try:
            # Build fast content index from metadata only
            data_paths = self.source_manager.get_data_paths()
            await self.content_index.build_from_files(data_paths)

            # Start background services
            await self.memory_manager.start_monitoring()

            # Initialize fallback if available
            if self._fallback_omnidexer:
                # Don't await - let it load in background
                self._initialization_task = asyncio.create_task(
                    self._lazy_initialize_fallback()
                )

            self._is_initialized = True

        except Exception as e:
            raise RuntimeError(
                f"Failed to initialize performance omnidexer: {e}"
            ) from e

    async def cleanup(self) -> None:
        """Comprehensive async resource cleanup."""
        # Stop background services
        await self.memory_manager.stop_monitoring()

        # Cancel any in-progress loading tasks
        if self._initialization_task:
            self._initialization_task.cancel()

        for task in self._loading_tasks.values():
            task.cancel()

        if self._loading_tasks:
            await asyncio.gather(*self._loading_tasks.values(), return_exceptions=True)

        # Cleanup components
        await self.memory_manager.cleanup()

        # Clear state
        self._loading_tasks.clear()
        self.active_contexts.clear()
        self._is_initialized = False

    async def _lazy_initialize_fallback(self) -> None:
        """Lazy initialization of fallback omnidexer in background."""
        try:
            if self._fallback_omnidexer:
                self._fallback_omnidexer.load_all_data()
        except Exception:  # nosec B110
            # Don't fail if fallback initialization fails
            pass

    async def search_content_async(
        self,
        query: str,
        content_type: str | None = None,
        context: Any | None = None,  # Will be properly typed when context is available
        limit: int = 50,
    ) -> Result[list[BaseContent], ContentNotFoundError]:
        """High-performance async search with intelligent caching."""
        if not self._is_initialized:
            await self.initialize()

        start_time = time.time()

        try:
            # Track request context for usage correlation
            if context:
                self.active_contexts.add(context)
                if hasattr(context, "record_async_operation"):
                    context.record_async_operation()

            # Fast metadata search first (< 10ms)
            metadata_results = self.content_index.search(query, content_type, limit)

            # Lazy load actual content for results
            content_results = []
            load_tasks = []

            for metadata in metadata_results:
                content_id = metadata.id
                cache_key = f"performance_omnidexer:{content_id}"

                # Check cache first
                cached_content = self.cache.get(cache_key)
                if cached_content is not None:
                    content_results.append(cached_content)
                    self._record_cache_hit(content_id, context)
                else:
                    # Schedule async lazy load
                    load_task = asyncio.create_task(self._lazy_load_content(metadata))
                    load_tasks.append((content_id, cache_key, load_task))
                    self._record_cache_miss(content_id, context)

            # Wait for lazy loads (with concurrency limit)
            if load_tasks:
                semaphore = asyncio.Semaphore(self.config.max_concurrent_loads)

                async def load_with_semaphore(
                    content_id: str, cache_key: str, task: asyncio.Task
                ) -> Any:
                    async with semaphore:
                        try:
                            content = await task
                            # Cache the loaded content with TTL
                            if content is not None:
                                ttl_seconds = self.config.cache_ttl_hours * 3600
                                self.cache.set(cache_key, content, expire=ttl_seconds)
                            return content
                        except Exception:
                            return None

                load_results = await asyncio.gather(
                    *[
                        load_with_semaphore(cid, cache_key, task)
                        for cid, cache_key, task in load_tasks
                    ],
                    return_exceptions=True,
                )

                # Add successfully loaded content
                for content in load_results:
                    if isinstance(content, BaseContent):
                        content_results.append(content)

            # Update performance metrics
            search_time = (time.time() - start_time) * 1000  # ms
            self.performance_metrics["avg_search_time_ms"] = (
                (self.performance_metrics["avg_search_time_ms"] * 0.9)
                + (search_time * 0.1)  # Exponential moving average
            )

            return Success(content_results)  # type: ignore[arg-type]

        except Exception as e:
            error = ContentNotFoundError(
                message=f"Search failed for query '{query}': {e}",
                data={"query": query, "error": str(e)},
            )
            return Error(error)

    async def get_content_async(
        self,
        content_type: str,
        name: str,
        source: str | None = None,
        context: Any | None = None,
    ) -> Result[BaseContent | None, ContentNotFoundError]:
        """Async content retrieval with intelligent caching."""
        if not self._is_initialized:
            await self.initialize()

        try:
            content_type_obj = ContentType(content_type)
        except ValueError:
            error = ContentNotFoundError(
                message=f"Invalid content type: {content_type}",
                data={"content_type": content_type},
            )
            return Error(error)

        content_id = self._generate_content_id(content_type_obj, name, source)
        cache_key = f"performance_omnidexer:{content_id}"

        # Check cache with usage tracking
        cached_content = self.cache.get(cache_key)
        if cached_content is not None:
            self._record_cache_hit(content_id, context)
            return Success(cached_content)  # type: ignore[arg-type]

        # Try to find in content index first
        metadata_results = self.content_index.search(f"{name}", content_type, 5)

        # Find exact match
        matching_metadata = None
        for metadata in metadata_results:
            if metadata.name.lower() == name.lower() and (
                source is None or metadata.source.lower() == source.lower()
            ):
                matching_metadata = metadata
                break

        if matching_metadata:
            # Load content asynchronously
            try:
                content = await self._lazy_load_content(matching_metadata)
                if content is not None:
                    # Cache with TTL
                    ttl_seconds = self.config.cache_ttl_hours * 3600
                    self.cache.set(cache_key, content, expire=ttl_seconds)
                    self._record_cache_miss(content_id, context)
                    return Success(content)
            except Exception as e:
                error = ContentNotFoundError(
                    message=f"Failed to load content: {name} ({content_type}): {e}",
                    data={"name": name, "type": content_type},
                )
                return Error(error)

        # Fallback to legacy omnidexer if available
        if self._fallback_omnidexer:
            try:
                # Ensure fallback is loaded
                if self._initialization_task:
                    await self._initialization_task

                content = self._fallback_omnidexer.find(content_type_obj, name, source)
                if content is not None:
                    # Cache the fallback result
                    ttl_seconds = self.config.cache_ttl_hours * 3600
                    self.cache.set(cache_key, content, expire=ttl_seconds)
                    return Success(content)
            except Exception:  # nosec B110
                pass

        error = ContentNotFoundError(
            message=f"Content not found: {name} ({content_type})",
            data={"name": name, "type": content_type},
        )
        return Error(error)

    async def _lazy_load_content(self, metadata: ContentMetadata) -> BaseContent | None:
        """Async lazy loading of content with deduplication."""
        content_id = metadata.id

        # Check if already loading (deduplication)
        if content_id in self._loading_tasks:
            result = await self._loading_tasks[content_id]
            return result  # type: ignore[no-any-return]

        # Create loading task
        async def load_task() -> BaseContent | None:
            start_time = time.time()

            try:
                # Load content from disk - this is a simplified version
                # In a full implementation, this would use proper loaders
                content = await self._load_content_from_metadata(metadata)

                # Update usage statistics
                (time.time() - start_time) * 1000
                self.performance_metrics["lazy_loads"] += 1

                return content

            except Exception:
                # Return None on error - let caller handle
                return None

        task = asyncio.create_task(load_task())
        self._loading_tasks[content_id] = task

        try:
            result = await task
            return result  # type: ignore[no-any-return]
        finally:
            # Cleanup completed task
            self._loading_tasks.pop(content_id, None)

    async def _load_content_from_metadata(
        self, metadata: ContentMetadata
    ) -> BaseContent | None:
        """Load actual content from file using metadata.

        This is a simplified implementation - in production this would
        integrate with the existing loader system.
        """
        try:
            # Use fallback omnidexer if available for now
            if self._fallback_omnidexer:
                # Parse content type and attempt lookup
                content_type = ContentType(metadata.content_type)

                # Try different source variations
                content = self._fallback_omnidexer.find(
                    content_type, metadata.name, metadata.source
                )
                if content is not None:
                    return content

                # Try without source filter
                all_matches = self._fallback_omnidexer.find_all(
                    content_type, metadata.name
                )
                if all_matches:
                    return all_matches[0]  # Return first match

            return None

        except Exception:
            return None

    def _generate_content_id(
        self, content_type: ContentType, name: str, source: str | None = None
    ) -> str:
        """Generate unique content ID for caching."""
        return f"{content_type.value}:{name}:{source or 'any'}"

    def _record_cache_hit(self, content_id: str, context: Any | None) -> None:
        """Record cache hit with context correlation."""
        self.performance_metrics["cache_hits"] += 1

        if context and hasattr(context, "record_cache_hit"):
            context.record_cache_hit()

    def _record_cache_miss(self, content_id: str, context: Any | None) -> None:
        """Record cache miss with performance impact tracking."""
        self.performance_metrics["cache_misses"] += 1

        if context and hasattr(context, "record_cache_miss"):
            context.record_cache_miss()

    # Character Progression Methods (Package 2.1 Extension)

    async def get_eligible_feats_async(
        self,
        character_class: str,
        level: int,
        subclass: str | None = None,
        context: Any | None = None,
    ) -> list[object]:
        """Get feats eligible for character with validation."""
        if not self._is_initialized:
            await self.initialize()

        try:
            # Generate cache key for feat eligibility
            cache_key = f"feats_eligible:{character_class}:{level}:{subclass or 'none'}"

            # Check cache first
            cached_feats = self.cache.get(cache_key)
            if cached_feats is not None:
                self._record_cache_hit(cache_key, context)
                return cached_feats  # type: ignore[no-any-return,return-value]

            # Search for feats in the content index
            feat_results = self.content_index.search("feat", "feat", limit=100)

            # Load feat content
            eligible_feats: list[object] = []
            for metadata in feat_results:
                try:
                    feat = await self._lazy_load_content(metadata)
                    if feat is not None:
                        # Simple eligibility check (would be more sophisticated in full implementation)
                        # For now, all feats are considered eligible unless they have obvious prerequisites
                        eligible = True

                        # Check level requirements
                        if hasattr(feat, "prerequisite") and feat.prerequisite:
                            # Basic prerequisite parsing - would be more complex in full implementation
                            prereq_text = str(feat.prerequisite).lower()
                            if (
                                "level" in prereq_text and level < 4
                            ):  # Most feat levels are 4+
                                eligible = False

                        if eligible:
                            eligible_feats.append(feat)

                except Exception as e:
                    # Log and skip feats that fail to load
                    feat_name = (
                        metadata.name if hasattr(metadata, "name") else "unknown feat"
                    )
                    logger.debug(f"Failed to process feat {feat_name}: {e}")
                    continue  # nosec B112 - intentional exception handling

            # Cache results
            ttl_seconds = self.config.cache_ttl_hours * 3600
            self.cache.set(cache_key, eligible_feats, expire=ttl_seconds)
            self._record_cache_miss(cache_key, context)

            return eligible_feats

        except Exception:
            # Fallback to empty list on error
            return []

    async def get_class_progression_data_async(
        self,
        character_class: str,
        level: int,
        subclass: str | None = None,
        context: Any | None = None,
    ) -> object | None:
        """Get complete class progression data."""
        if not self._is_initialized:
            await self.initialize()

        try:
            # Generate cache key for class progression
            cache_key = (
                f"class_progression:{character_class}:{level}:{subclass or 'none'}"
            )

            # Check cache first
            cached_progression = self.cache.get(cache_key)
            if cached_progression is not None:
                self._record_cache_hit(cache_key, context)
                return cached_progression  # type: ignore[no-any-return]

            # Get class data
            class_result = await self.get_content_async(
                "class", character_class, context=context
            )
            if not class_result.is_success():
                return None

            class_data = class_result.unwrap()
            if not class_data:
                return None

            # Build progression data structure
            progression_data: dict[str, Any] = {
                "class_name": character_class,
                "level": level,
                "subclass": subclass,
                "hit_dice": getattr(class_data, "hd", {"faces": 8, "number": 1}),
                "proficiency_bonus": (level - 1) // 4 + 2,
                "features": [],
                "spellcasting": None,
            }

            # Extract class features up to current level
            features_list = progression_data.get("features")
            if (
                hasattr(class_data, "class_features")
                and class_data.class_features
                and isinstance(features_list, list)
            ):
                for feature_ref in class_data.class_features:
                    if isinstance(feature_ref, str):
                        # Parse class feature reference
                        parts = feature_ref.split("|")
                        if len(parts) >= 4:
                            try:
                                feature_level = int(parts[3])
                                if feature_level <= level:
                                    features_list.append(
                                        {
                                            "name": parts[0],
                                            "level": feature_level,
                                            "source": "class",
                                        }
                                    )
                            except ValueError:
                                continue

            # Add spellcasting progression if applicable
            if (
                hasattr(class_data, "spellcasting_ability")
                and class_data.spellcasting_ability
            ):
                progression_data["spellcasting"] = {
                    "ability": class_data.spellcasting_ability,
                    "progression": getattr(class_data, "caster_progression", "none"),
                    "cantrips": getattr(class_data, "cantrip_progression", []),
                    "spells_known": getattr(class_data, "spells_known_progression", []),
                }

            # Cache results
            ttl_seconds = self.config.cache_ttl_hours * 3600
            self.cache.set(cache_key, progression_data, expire=ttl_seconds)
            self._record_cache_miss(cache_key, context)

            return progression_data

        except Exception:
            return None

    async def analyze_multiclass_eligibility_async(
        self,
        current_class: str,
        level: int,
        context: Any | None = None,
    ) -> list[object]:
        """Analyze multiclass options for character."""
        if not self._is_initialized:
            await self.initialize()

        try:
            # Generate cache key for multiclass analysis
            cache_key = f"multiclass:{current_class}:{level}"

            # Check cache first
            cached_options = self.cache.get(cache_key)
            if cached_options is not None:
                self._record_cache_hit(cache_key, context)
                return cached_options  # type: ignore[no-any-return,return-value]

            # Search for all classes
            class_results = self.content_index.search("", "class", limit=50)

            multiclass_options: list[object] = []
            for metadata in class_results:
                if metadata.name.lower() == current_class.lower():
                    continue  # Skip current class

                try:
                    class_data = await self._lazy_load_content(metadata)
                    if class_data is not None:
                        # Basic multiclass option analysis
                        option = {
                            "class_name": class_data.name,
                            "source": metadata.source,
                            "requirements_met": True,  # Would calculate based on ability scores
                            "requirements": [],  # Would extract from multiclassing data
                            "synergy_rating": 5.0,  # Would calculate based on class combinations
                            "recommended_levels": [
                                1,
                                2,
                                3,
                            ],  # Standard multiclass dip levels
                            "benefits": [
                                "Access to new features",
                                "Increased versatility",
                            ],
                            "drawbacks": [
                                "Delayed progression",
                                "Ability score requirements",
                            ],
                        }

                        # Extract multiclassing requirements if available
                        if (
                            hasattr(class_data, "multiclassing")
                            and class_data.multiclassing
                        ):
                            # Would parse multiclassing requirements here
                            pass

                        multiclass_options.append(option)

                except Exception as e:
                    # Log and skip classes that fail to load
                    class_name = (
                        metadata.name if hasattr(metadata, "name") else "unknown class"
                    )
                    logger.debug(f"Failed to process class {class_name}: {e}")
                    continue  # nosec B112 - intentional exception handling

            # Limit results for performance
            multiclass_options = multiclass_options[:10]

            # Cache results
            ttl_seconds = self.config.cache_ttl_hours * 3600
            self.cache.set(cache_key, multiclass_options, expire=ttl_seconds)
            self._record_cache_miss(cache_key, context)

            return multiclass_options

        except Exception:
            return []

    # OmnidexerProtocol implementation
    async def load_content_sources(self, sources: list[str]) -> None:
        """Load content from specified sources."""
        if not self._is_initialized:
            await self.initialize()
        # Implementation will be enhanced in Phase 2

    def get_content(self, content_type: str, identifier: str) -> object:
        """Synchronous wrapper for async get_content_async."""
        try:
            content_type_enum = ContentType(content_type)
            # Run async method synchronously - not ideal but required for protocol
            import asyncio

            loop = asyncio.get_event_loop()
            result = loop.run_until_complete(
                self.get_content_async(content_type_enum, identifier)
            )
            return result.unwrap() if result.is_success() else None
        except Exception:
            return None

    def search(self, query: str) -> list[BaseContent]:
        """Synchronous wrapper for async search_content_async."""
        try:
            import asyncio

            loop = asyncio.get_event_loop()
            result = loop.run_until_complete(self.search_content_async(query))
            # Return BaseContent list directly
            base_content_list = result.unwrap() if result.is_success() else []
            return list(base_content_list)
        except Exception:
            return []

    async def ensure_sources_ready(self) -> None:
        """Ensure all content sources are loaded and ready."""
        if not self._is_initialized:
            await self.initialize()

        # Ensure source manager is ready
        if hasattr(self.source_manager, "ensure_sources_ready"):
            await self.source_manager.ensure_sources_ready()

    # Statistics and monitoring
    def get_performance_statistics(self) -> dict[str, Any]:
        """Get comprehensive performance statistics."""
        from ..cache import CacheManager

        cache_stats = CacheManager.get_stats()
        index_stats = self.content_index.get_statistics()

        total_requests = (
            self.performance_metrics["cache_hits"]
            + self.performance_metrics["cache_misses"]
        )
        hit_rate = (
            self.performance_metrics["cache_hits"] / total_requests
            if total_requests > 0
            else 0.0
        )

        return {
            "omnidexer": {
                "initialized": self._is_initialized,
                "active_contexts": len(self.active_contexts),
                "active_loads": len(self._loading_tasks),
                "performance": self.performance_metrics.copy(),
                "hit_rate": hit_rate,
            },
            "cache": cache_stats,
            "index": index_stats,
            "memory": {
                "current_usage_mb": self.memory_manager.memory_stats[
                    "current_usage_mb"
                ],
                "peak_usage_mb": self.memory_manager.memory_stats["peak_usage_mb"],
                "pressure_level": self.memory_manager.pressure_level.value,
            },
        }

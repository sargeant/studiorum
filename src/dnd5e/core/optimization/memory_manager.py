"""Adaptive memory management system for bounded memory usage."""

import asyncio
import gc
import sys
import time
import weakref
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any

try:
    import psutil

    psutil_available = True
except ImportError:
    psutil = None  # type: ignore[assignment]
    psutil_available = False


class MemoryPressureLevel(Enum):
    """Memory pressure levels for adaptive behavior."""

    LOW = "low"  # < 50% usage
    MODERATE = "moderate"  # 50-75% usage
    HIGH = "high"  # 75-90% usage
    CRITICAL = "critical"  # > 90% usage


@dataclass
class MemoryConfiguration:
    """Memory management configuration."""

    max_process_memory_mb: int = 1024
    warning_threshold: float = 0.75
    critical_threshold: float = 0.90
    gc_pressure_threshold: float = 0.80
    emergency_eviction_ratio: float = 0.30  # Evict 30% in emergency
    monitor_interval_seconds: int = 10


class AdaptiveMemoryManager:
    """Manages memory pressure and triggers adaptive behaviors."""

    def __init__(self, config: MemoryConfiguration):
        self.config = config
        self.pressure_level = MemoryPressureLevel.LOW
        self.pressure_callbacks: dict[
            MemoryPressureLevel, list[Callable[[float], Awaitable[None]]]
        ] = {level: [] for level in MemoryPressureLevel}

        # Memory monitoring
        self._monitor_task: asyncio.Task | None = None
        self.memory_stats = {
            "current_usage_mb": 0.0,
            "peak_usage_mb": 0.0,
            "gc_collections": 0,
            "emergency_evictions": 0,
        }

    def register_pressure_callback(
        self, level: MemoryPressureLevel, callback: Callable[[float], Awaitable[None]]
    ) -> None:
        """Register callback for memory pressure level."""
        self.pressure_callbacks[level].append(callback)

    async def start_monitoring(self) -> None:
        """Start memory monitoring loop."""
        if not self._monitor_task:
            self._monitor_task = asyncio.create_task(self._memory_monitor_loop())

    async def stop_monitoring(self) -> None:
        """Stop memory monitoring and cleanup."""
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
            self._monitor_task = None

    async def cleanup(self) -> None:
        """Stop monitoring and cleanup resources."""
        await self.stop_monitoring()

    def get_current_memory_mb(self) -> float:
        """Get current process memory usage in MB."""
        if psutil_available and psutil is not None:
            try:
                process = psutil.Process()
                memory_info = process.memory_info()
                return float(memory_info.rss) / (1024 * 1024)
            except Exception:  # nosec B110
                pass

        # Fallback to basic Python memory info
        objects_size = sys.getsizeof(gc.get_objects())
        return float(objects_size) / (1024 * 1024)

    async def _memory_monitor_loop(self) -> None:
        """Monitor memory usage and trigger adaptive responses."""

        while True:
            try:
                await asyncio.sleep(self.config.monitor_interval_seconds)

                # Get current memory usage
                current_mb = self.get_current_memory_mb()

                self.memory_stats["current_usage_mb"] = current_mb
                self.memory_stats["peak_usage_mb"] = max(
                    self.memory_stats["peak_usage_mb"], current_mb
                )

                # Calculate pressure level
                usage_ratio = current_mb / self.config.max_process_memory_mb
                new_pressure_level = self._calculate_pressure_level(usage_ratio)

                # Trigger callbacks if pressure level changed
                if new_pressure_level != self.pressure_level:
                    await self._handle_pressure_change(new_pressure_level, usage_ratio)
                    self.pressure_level = new_pressure_level

                # Emergency actions for critical pressure
                if new_pressure_level == MemoryPressureLevel.CRITICAL:
                    await self._emergency_memory_management(usage_ratio)

            except asyncio.CancelledError:
                break
            except Exception:  # nosec B110
                # Log but continue monitoring
                pass

    def _calculate_pressure_level(self, usage_ratio: float) -> MemoryPressureLevel:
        """Calculate memory pressure level from usage ratio."""
        if usage_ratio >= self.config.critical_threshold:
            return MemoryPressureLevel.CRITICAL
        elif usage_ratio >= self.config.warning_threshold:
            return MemoryPressureLevel.HIGH
        elif usage_ratio >= 0.5:
            return MemoryPressureLevel.MODERATE
        else:
            return MemoryPressureLevel.LOW

    async def _handle_pressure_change(
        self, new_level: MemoryPressureLevel, usage_ratio: float
    ) -> None:
        """Handle memory pressure level change."""

        callbacks = self.pressure_callbacks[new_level]
        if callbacks:
            await asyncio.gather(
                *[callback(usage_ratio) for callback in callbacks],
                return_exceptions=True,
            )

    async def _emergency_memory_management(self, usage_ratio: float) -> None:
        """Emergency memory management for critical pressure."""

        # Trigger garbage collection
        gc.collect()
        self.memory_stats["gc_collections"] += 1

        # Trigger emergency callbacks
        callbacks = self.pressure_callbacks[MemoryPressureLevel.CRITICAL]
        if callbacks:
            await asyncio.gather(
                *[callback(usage_ratio) for callback in callbacks],
                return_exceptions=True,
            )

        self.memory_stats["emergency_evictions"] += 1


# Integration with cache for memory-aware eviction
class MemoryAwareCacheManager:
    """Cache manager that responds to memory pressure."""

    def __init__(
        self,
        memory_manager: AdaptiveMemoryManager,
        cache_ref: Any = None,  # Will be properly typed when cache is implemented
    ):
        self.memory_manager = memory_manager
        self._cache_ref = weakref.ref(cache_ref) if cache_ref else None

        # Register for memory pressure callbacks
        memory_manager.register_pressure_callback(
            MemoryPressureLevel.HIGH, self._handle_high_pressure
        )
        memory_manager.register_pressure_callback(
            MemoryPressureLevel.CRITICAL, self._handle_critical_pressure
        )

    @property
    def cache(self) -> Any | None:
        """Get cache instance if still alive."""
        return self._cache_ref() if self._cache_ref else None

    async def _handle_high_pressure(self, usage_ratio: float) -> None:
        """Handle high memory pressure - moderate cache cleanup."""

        cache = self.cache
        if not cache:
            return

        # Basic cleanup - this will be enhanced when cache is implemented
        if hasattr(cache, "clear_expired"):
            await cache.clear_expired()

    async def _handle_critical_pressure(self, usage_ratio: float) -> None:
        """Handle critical memory pressure - aggressive cache cleanup."""

        cache = self.cache
        if not cache:
            return

        # Aggressive cleanup
        if hasattr(cache, "emergency_cleanup"):
            await cache.emergency_cleanup(
                self.memory_manager.config.emergency_eviction_ratio
            )
        elif hasattr(cache, "clear"):
            await cache.clear()  # Last resort - clear everything

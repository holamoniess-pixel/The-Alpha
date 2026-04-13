#!/usr/bin/env python3
"""
ALPHA OMEGA - PERFORMANCE OPTIMIZER
Latency optimization, memory management, caching
Version: 2.0.0
"""

import asyncio
import logging
import time
import threading
import gc
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from collections import OrderedDict
import weakref

try:
    import psutil

    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


@dataclass
class PerformanceStats:
    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    memory_percent: float = 0.0
    disk_io_read_mb: float = 0.0
    disk_io_write_mb: float = 0.0
    network_sent_mb: float = 0.0
    network_recv_mb: float = 0.0
    thread_count: int = 0
    gc_collections: tuple = (0, 0, 0)
    timestamp: float = field(default_factory=time.time)


class LRUCache:
    """Thread-safe LRU cache with TTL support"""

    def __init__(self, max_size: int = 1000, ttl_seconds: float = 300):
        self.max_size = max_size
        self.ttl = ttl_seconds
        self._cache: OrderedDict = OrderedDict()
        self._timestamps: Dict[str, float] = {}
        self._lock = threading.RLock()
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key in self._cache:
                if time.time() - self._timestamps.get(key, 0) > self.ttl:
                    self._remove(key)
                    self._misses += 1
                    return None
                self._cache.move_to_end(key)
                self._hits += 1
                return self._cache[key]
            self._misses += 1
            return None

    def put(self, key: str, value: Any):
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            else:
                if len(self._cache) >= self.max_size:
                    self._cache.popitem(last=False)
            self._cache[key] = value
            self._timestamps[key] = time.time()

    def _remove(self, key: str):
        if key in self._cache:
            del self._cache[key]
            del self._timestamps[key]

    def clear(self):
        with self._lock:
            self._cache.clear()
            self._timestamps.clear()

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            total = self._hits + self._misses
            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": (self._hits / total * 100) if total > 0 else 0,
                "ttl": self.ttl,
            }


class MemoryPool:
    """Object pool for reducing allocation overhead"""

    def __init__(self, factory: Callable, max_pool_size: int = 100):
        self.factory = factory
        self.max_pool_size = max_pool_size
        self._pool: List[Any] = []
        self._lock = threading.Lock()
        self._created = 0
        self._reused = 0

    def acquire(self) -> Any:
        with self._lock:
            if self._pool:
                self._reused += 1
                return self._pool.pop()
        self._created += 1
        return self.factory()

    def release(self, obj: Any):
        with self._lock:
            if len(self._pool) < self.max_pool_size:
                if hasattr(obj, "reset"):
                    obj.reset()
                self._pool.append(obj)

    def stats(self) -> Dict[str, int]:
        return {
            "pool_size": len(self._pool),
            "created": self._created,
            "reused": self._reused,
            "max_pool_size": self.max_pool_size,
        }


class AsyncBatcher:
    """Batch multiple async operations for efficiency"""

    def __init__(self, batch_size: int = 10, max_wait_ms: float = 50):
        self.batch_size = batch_size
        self.max_wait_ms = max_wait_ms
        self._pending: List[tuple] = []
        self._lock = asyncio.Lock()
        self._batch_event = asyncio.Event()

    async def add(self, item: Any, processor: Callable) -> Any:
        future = asyncio.Future()

        async with self._lock:
            self._pending.append((item, future))
            if len(self._pending) >= self.batch_size:
                self._batch_event.set()

        return await future

    async def process_batch(self, processor: Callable):
        while True:
            await asyncio.wait_for(
                self._batch_event.wait(), timeout=self.max_wait_ms / 1000
            )

            async with self._lock:
                batch = self._pending[:]
                self._pending.clear()
                self._batch_event.clear()

            if batch:
                items = [item for item, _ in batch]
                try:
                    results = await processor(items)
                    for (_, future), result in zip(batch, results):
                        if not future.done():
                            future.set_result(result)
                except Exception as e:
                    for _, future in batch:
                        if not future.done():
                            future.set_exception(e)


class LatencyTracker:
    """Track operation latencies for optimization"""

    def __init__(self, max_samples: int = 1000):
        self.max_samples = max_samples
        self._latencies: Dict[str, List[float]] = {}
        self._lock = threading.Lock()

    def record(self, operation: str, latency_ms: float):
        with self._lock:
            if operation not in self._latencies:
                self._latencies[operation] = []
            self._latencies[operation].append(latency_ms)
            if len(self._latencies[operation]) > self.max_samples:
                self._latencies[operation].pop(0)

    def get_stats(self, operation: str) -> Dict[str, float]:
        with self._lock:
            if operation not in self._latencies or not self._latencies[operation]:
                return {"count": 0, "avg_ms": 0, "min_ms": 0, "max_ms": 0, "p95_ms": 0}

            latencies = sorted(self._latencies[operation])
            count = len(latencies)

            return {
                "count": count,
                "avg_ms": sum(latencies) / count,
                "min_ms": latencies[0],
                "max_ms": latencies[-1],
                "p95_ms": latencies[int(count * 0.95)]
                if count >= 20
                else latencies[-1],
            }

    def get_all_stats(self) -> Dict[str, Dict[str, float]]:
        return {op: self.get_stats(op) for op in self._latencies}


class PerformanceOptimizer:
    """Main performance optimization controller"""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = logging.getLogger("PerformanceOptimizer")

        self.enabled = self.config.get("enabled", True)
        self.cpu_limit = self.config.get("cpu_limit", 80)
        self.memory_limit = self.config.get("memory_limit", 85)
        self.gc_threshold = self.config.get("gc_threshold", 70)

        self._caches: Dict[str, LRUCache] = {}
        self._pools: Dict[str, MemoryPool] = {}
        self._latency_tracker = LatencyTracker()
        self._running = False
        self._monitor_thread = None

        self._stats = PerformanceStats()
        self._optimization_count = 0

        self._init_caches()

    def _init_caches(self):
        self._caches["command_results"] = LRUCache(max_size=500, ttl_seconds=60)
        self._caches["speech_results"] = LRUCache(max_size=200, ttl_seconds=30)
        self._caches["intent_cache"] = LRUCache(max_size=1000, ttl_seconds=300)
        self._caches["pattern_cache"] = LRUCache(max_size=300, ttl_seconds=600)

    async def initialize(self) -> bool:
        self.logger.info("Initializing Performance Optimizer...")

        gc.set_threshold(700, 10, 10)

        self._running = True
        self.logger.info("Performance Optimizer initialized")
        return True

    def get_cache(self, name: str) -> Optional[LRUCache]:
        return self._caches.get(name)

    def create_pool(self, name: str, factory: Callable, max_size: int = 100):
        self._pools[name] = MemoryPool(factory, max_size)
        self.logger.info(f"Created memory pool: {name}")

    def get_pool(self, name: str) -> Optional[MemoryPool]:
        return self._pools.get(name)

    def track_latency(self, operation: str, latency_ms: float):
        self._latency_tracker.record(operation, latency_ms)

    def get_latency_stats(self) -> Dict[str, Dict[str, float]]:
        return self._latency_tracker.get_all_stats()

    def update_stats(self):
        if not HAS_PSUTIL:
            return

        try:
            process = psutil.Process()

            self._stats.cpu_percent = process.cpu_percent()
            mem_info = process.memory_info()
            self._stats.memory_mb = mem_info.rss / (1024 * 1024)
            self._stats.memory_percent = process.memory_percent()
            self._stats.thread_count = process.num_threads()
            self._stats.gc_collections = gc.get_stats()[0]["collections"]
            self._stats.timestamp = time.time()
        except Exception as e:
            self.logger.debug(f"Failed to update stats: {e}")

    def optimize(self):
        if not self.enabled:
            return

        self.update_stats()

        if self._stats.memory_percent > self.gc_threshold:
            self.logger.info(
                f"Memory usage {self._stats.memory_percent:.1f}% > threshold, running GC"
            )
            gc.collect(2)
            self._optimization_count += 1

        if self._stats.cpu_percent > self.cpu_limit:
            self.logger.warning(
                f"CPU usage {self._stats.cpu_percent:.1f}% exceeds limit"
            )

        for name, cache in self._caches.items():
            stats = cache.stats()
            if stats["hit_rate"] < 50 and stats["misses"] > 100:
                self.logger.info(
                    f"Cache '{name}' hit rate low: {stats['hit_rate']:.1f}%"
                )

    async def start_monitoring(self):
        self.logger.info("Performance monitoring started")

        while self._running:
            try:
                self.optimize()
                await asyncio.sleep(5)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Monitoring error: {e}")
                await asyncio.sleep(10)

    def get_stats(self) -> Dict[str, Any]:
        self.update_stats()

        cache_stats = {name: cache.stats() for name, cache in self._caches.items()}
        pool_stats = {name: pool.stats() for name, pool in self._pools.items()}

        return {
            "cpu_percent": self._stats.cpu_percent,
            "memory_mb": self._stats.memory_mb,
            "memory_percent": self._stats.memory_percent,
            "thread_count": self._stats.thread_count,
            "optimizations_run": self._optimization_count,
            "caches": cache_stats,
            "pools": pool_stats,
            "latencies": self.get_latency_stats(),
        }

    def record_operation(self, operation: str):
        """Context manager for tracking operation latency"""

        class OperationTracker:
            def __init__(self, optimizer, op):
                self.optimizer = optimizer
                self.op = op
                self.start = None

            def __enter__(self):
                self.start = time.time()
                return self

            def __exit__(self, *args):
                latency = (time.time() - self.start) * 1000
                self.optimizer.track_latency(self.op, latency)

        return OperationTracker(self, operation)

    async def stop(self):
        self._running = False

        for cache in self._caches.values():
            cache.clear()

        self.logger.info("Performance optimizer stopped")

#!/usr/bin/env python3
"""
API Rate Limiting & Caching System for The Alpha
Advanced rate limiting with multiple strategies and intelligent caching
Version: 1.0.0
"""

import asyncio
import json
import logging
import sqlite3
import time
import hashlib
import re
import functools
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple, Callable, Union, Set
from dataclasses import dataclass, asdict
from enum import Enum
from abc import ABC, abstractmethod
import threading
import uuid


class RateLimitStrategy(Enum):
    """Rate limiting strategies"""

    FIXED_WINDOW = "fixed_window"
    SLIDING_WINDOW = "sliding_window"
    TOKEN_BUCKET = "token_bucket"
    LEAKY_BUCKET = "leaky_bucket"


class CacheStrategy(Enum):
    """Caching strategies"""

    MEMORY = "memory"
    SQLITE = "sqlite"
    REDIS = "redis"
    HYBRID = "hybrid"


class CacheExpiry(Enum):
    """Cache expiry strategies"""

    TTL = "ttl"
    LRU = "lru"  # Least Recently Used
    LFU = "lfu"  # Least Frequently Used
    FIFO = "fifo"  # First In First Out


@dataclass
class RateLimitConfig:
    """Rate limit configuration"""

    strategy: RateLimitStrategy
    limit: int  # Max requests
    window_seconds: int = 60  # Time window default: 1 minute
    burst_size: Optional[int] = None  # For token bucket
    refill_rate: Optional[float] = None  # Tokens per second
    block_duration: int = 600  # Block for 10 minutes if exceeded
    skip_if_whitelisted: bool = True
    skip_if_super_admin: bool = True
    custom_message: str = "Rate limit exceeded"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy": self.strategy.value,
            "limit": self.limit,
            "window_seconds": self.window_seconds,
            "burst_size": self.burst_size,
            "refill_rate": self.refill_rate,
            "block_duration": self.block_duration,
            "skip_if_whitelisted": self.skip_if_whitelisted,
            "skip_if_super_admin": self.skip_if_super_admin,
            "custom_message": self.custom_message,
        }


@dataclass
class CacheConfig:
    """Cache configuration"""

    strategy: CacheStrategy
    ttl_seconds: int = 300  # Default 5 minutes
    max_size: int = 10000  # Max cached items
    expiry_strategy: CacheExpiry = CacheExpiry.LRU
    compression_enabled: bool = True
    persistent: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy": self.strategy.value,
            "ttl_seconds": self.ttl_seconds,
            "max_size": self.max_size,
            "expiry_strategy": self.expiry_strategy.value,
            "compression_enabled": self.compression_enabled,
            "persistent": self.persistent,
        }


@dataclass
class RateLimitBucket:
    """Bucket for storing rate limit data"""

    key: str
    count: int
    window_start: float
    tokens: float
    last_refill: float
    blocked_until: float = 0


@dataclass
class CacheEntry:
    """Cache entry with metadata"""

    key: str
    data: Any
    created_at: float
    accessed_at: float
    access_count: int
    size_bytes: int
    ttl_seconds: int
    compressed: bool = False

    def is_expired(self) -> bool:
        """Check if cache entry is expired"""
        return time.time() > self.created_at + self.ttl_seconds

    def get_age(self) -> float:
        """Get age in seconds"""
        return time.time() - self.created_at


class RateLimitBackend(ABC):
    """Abstract base class for rate limit backends"""

    @abstractmethod
    async def get_bucket(self, key: str) -> Optional[RateLimitBucket]:
        pass

    @abstractmethod
    async def save_bucket(self, bucket: RateLimitBucket):
        pass

    @abstractmethod
    async def increment_counter(self, key: str, window_start: float) -> int:
        pass

    @abstractmethod
    async def get_window_count(self, key: str, window_start: float) -> int:
        pass

    @abstractmethod
    async def cleanup_old_entries(self, max_age_seconds: int):
        pass


class MemoryRateLimitBackend(RateLimitBackend):
    """In-memory rate limit backend"""

    def __init__(self):
        self.buckets: Dict[str, RateLimitBucket] = {}
        self.counters: Dict[str, Dict[float, int]] = {}
        self.lock = threading.RLock()

    async def get_bucket(self, key: str) -> Optional[RateLimitBucket]:
        with self.lock:
            return self.buckets.get(key)

    async def save_bucket(self, bucket: RateLimitBucket):
        with self.lock:
            self.buckets[bucket.key] = bucket

    async def increment_counter(self, key: str, window_start: float) -> int:
        with self.lock:
            if key not in self.counters:
                self.counters[key] = {}

            window_key = window_start
            if window_key not in self.counters[key]:
                self.counters[key][window_key] = 0

            self.counters[key][window_key] += 1
            return self.counters[key][window_key]

    async def get_window_count(self, key: str, window_start: float) -> int:
        with self.lock:
            if key not in self.counters:
                return 0

            window_key = window_start
            return self.counters[key].get(window_key, 0)

    async def cleanup_old_entries(self, max_age_seconds: int):
        with self.lock:
            cutoff = time.time() - max_age_seconds

            # Clean buckets
            self.buckets = {
                k: v for k, v in self.buckets.items() if v.window_start > cutoff
            }

            # Clean counters
            for key in list(self.counters.keys()):
                if key not in self.counters:
                    continue

                self.counters[key] = {
                    w: c for w, c in self.counters[key].items() if w > cutoff
                }

                if not self.counters[key]:
                    del self.counters[key]


class SQLiteRateLimitBackend(RateLimitBackend):
    """SQLite rate limit backend with persistence"""

    def __init__(self, db_path: str = "rate_limits.db"):
        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """Initialize SQLite database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Buckets table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rate_limit_buckets (
                bucket_key TEXT PRIMARY KEY,
                count INTEGER,
                window_start REAL,
                tokens REAL,
                last_refill REAL,
                blocked_until REAL DEFAULT 0,
                updated_at REAL
            )
        """)

        # Counters table for fixed/sliding window
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rate_limit_counters (
                counter_key TEXT NOT NULL,
                window_start REAL NOT NULL,
                count INTEGER,
                updated_at REAL,
                PRIMARY KEY (counter_key, window_start)
            )
        """)

        # Indexes
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_counters_key ON rate_limit_counters(counter_key)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_counters_window ON rate_limit_counters(window_start)"
        )

        conn.commit()
        conn.close()

    async def get_bucket(self, key: str) -> Optional[RateLimitBucket]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT bucket_key, count, window_start, tokens, last_refill, blocked_until
            FROM rate_limit_buckets WHERE bucket_key = ?
        """,
            (key,),
        )

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return RateLimitBucket(
            key=row[0],
            count=row[1],
            window_start=row[2],
            tokens=row[3] or 0,
            last_refill=row[4] or 0,
            blocked_until=row[5] or 0,
        )

    async def save_bucket(self, bucket: RateLimitBucket):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT OR REPLACE INTO rate_limit_buckets (
                bucket_key, count, window_start, tokens, last_refill, blocked_until, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (
                bucket.key,
                bucket.count,
                bucket.window_start,
                bucket.tokens,
                bucket.last_refill,
                bucket.blocked_until,
                time.time(),
            ),
        )

        conn.commit()
        conn.close()

    async def increment_counter(self, key: str, window_start: float) -> int:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Try to increment first
        cursor.execute(
            """
            INSERT OR REPLACE INTO rate_limit_counters (
                counter_key, window_start, count, updated_at
            ) VALUES (?, ?, COALESCE((SELECT count FROM rate_limit_counters 
                                    WHERE counter_key = ? AND window_start = ?), 0) + 1, ?)
        """,
            (key, window_start, key, window_start, time.time()),
        )

        # Get final count
        cursor.execute(
            """
            SELECT count FROM rate_limit_counters
            WHERE counter_key = ? AND window_start = ?
        """,
            (key, window_start),
        )

        count = cursor.fetchone()[0]
        conn.close()

        return count

    async def get_window_count(self, key: str, window_start: float) -> int:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT count FROM rate_limit_counters
            WHERE counter_key = ? AND window_start = ?
        """,
            (key, window_start),
        )

        row = cursor.fetchone()
        conn.close()

        return row[0] if row else 0

    async def cleanup_old_entries(self, max_age_seconds: int):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cutoff = time.time() - max_age_seconds

        # Clean old buckets
        cursor.execute("DELETE FROM rate_limit_buckets WHERE updated_at < ?", (cutoff,))

        # Clean old counters
        cursor.execute(
            "DELETE FROM rate_limit_counters WHERE window_start < ?", (cutoff,)
        )

        conn.commit()
        conn.close()


class CacheBackend(ABC):
    """Abstract base class for cache backends"""

    @abstractmethod
    async def get(self, key: str) -> Optional[CacheEntry]:
        pass

    @abstractmethod
    async def set(self, entry: CacheEntry):
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        pass

    @abstractmethod
    async def clear(self):
        pass

    @abstractmethod
    async def get_stats(self) -> Dict[str, Any]:
        pass


class HybridCacheBackend(CacheBackend):
    """Hybrid cache with memory + SQLite"""

    def __init__(self, db_path: str = "cache.db", max_memory_items: int = 1000):
        self.db_path = db_path
        self.max_memory_items = max_memory_items
        self.memory_cache: Dict[str, CacheEntry] = {}
        self.memory_access_order: List[str] = []
        self.lock = threading.RLock()
        self._init_database()

    def _init_database(self):
        """Initialize SQLite database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cache_entries (
                cache_key TEXT PRIMARY KEY,
                data TEXT NOT NULL,
                created_at REAL NOT NULL,
                accessed_at REAL NOT NULL,
                access_count INTEGER DEFAULT 1,
                size_bytes INTEGER,
                ttl_seconds INTEGER
            )
        """)

        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_cache_accessed ON cache_entries(accessed_at)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_cache_created ON cache_entries(created_at)"
        )

        conn.commit()
        conn.close()

    async def get(self, key: str) -> Optional[CacheEntry]:
        with self.lock:
            # Check memory cache first
            entry = self.memory_cache.get(key)
            if entry:
                if entry.is_expired():
                    # Remove expired
                    del self.memory_cache[key]
                    if key in self.memory_access_order:
                        self.memory_access_order.remove(key)
                else:
                    # Update access
                    entry.accessed_at = time.time()
                    entry.access_count += 1

                    # Move to end of access order
                    if key in self.memory_access_order:
                        self.memory_access_order.remove(key)
                    self.memory_access_order.append(key)

                    return entry

            # Check database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT cache_key, data, created_at, accessed_at, access_count, size_bytes, ttl_seconds
                FROM cache_entries WHERE cache_key = ?
            """,
                (key,),
            )

            row = cursor.fetchone()
            conn.close()

            if not row:
                return None

            entry = CacheEntry(
                key=row[0],
                data=json.loads(row[1]),
                created_at=row[2],
                accessed_at=row[3],
                access_count=row[4] or 1,
                size_bytes=row[5],
                ttl_seconds=row[6],
            )

            # Check expiry
            if entry.is_expired():
                # Delete expired
                await self.delete(key)
                return None

            # Update access
            entry.accessed_at = time.time()
            entry.access_count += 1

            # Cache in memory
            self._add_to_memory(entry)

            # Update database access
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                UPDATE cache_entries 
                SET accessed_at = ?, access_count = ?
                WHERE cache_key = ?
            """,
                (entry.accessed_at, entry.access_count, key),
            )

            conn.commit()
            conn.close()

            return entry

    def _add_to_memory(self, entry: CacheEntry):
        """Add entry to memory cache"""
        # Check if we need to evict
        if len(self.memory_cache) >= self.max_memory_items:
            self._evict_lru()

        self.memory_cache[entry.key] = entry

        if entry.key in self.memory_access_order:
            self.memory_access_order.remove(entry.key)
        self.memory_access_order.append(entry.key)

    def _evict_lru(self):
        """Evict least recently used item"""
        if self.memory_access_order:
            lru_key = self.memory_access_order.pop(0)
            if lru_key in self.memory_cache:
                del self.memory_cache[lru_key]

    async def set(self, entry: CacheEntry):
        with self.lock:
            # Add to memory
            self._add_to_memory(entry)

            # Add to database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT OR REPLACE INTO cache_entries (
                    cache_key, data, created_at, accessed_at, access_count,
                    size_bytes, ttl_seconds
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    entry.key,
                    json.dumps(entry.data),
                    entry.created_at,
                    entry.accessed_at,
                    entry.access_count,
                    entry.size_bytes,
                    entry.ttl_seconds,
                ),
            )

            conn.commit()
            conn.close()

    async def delete(self, key: str) -> bool:
        with self.lock:
            # Remove from memory
            if key in self.memory_cache:
                del self.memory_cache[key]

            if key in self.memory_access_order:
                self.memory_access_order.remove(key)

            # Remove from database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("DELETE FROM cache_entries WHERE cache_key = ?", (key,))

            conn.commit()
            conn.close()

            return cursor.rowcount > 0

    async def exists(self, key: str) -> bool:
        entry = await self.get(key)
        return entry is not None and not entry.is_expired()

    async def clear(self):
        with self.lock:
            self.memory_cache.clear()
            self.memory_access_order.clear()

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("DELETE FROM cache_entries")

            conn.commit()
            conn.close()

    async def get_stats(self) -> Dict[str, Any]:
        with self.lock:
            total_memory_size = sum(
                e.size_bytes for e in self.memory_cache.values() if e.size_bytes
            )
            expired_in_memory = sum(
                1 for e in self.memory_cache.values() if e.is_expired()
            )

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                "SELECT COUNT(*), SUM(access_count), SUM(size_bytes) FROM cache_entries"
            )
            count, total_access, total_size = cursor.fetchone()

            conn.close()

            return {
                "memory_items": len(self.memory_cache),
                "memory_size_bytes": total_memory_size,
                "memory_expired_items": expired_in_memory,
                "db_items": count or 0,
                "db_total_access": total_access or 0,
                "db_total_size_bytes": total_size or 0,
            }


class APIRateLimitCache:
    """
    API Rate Limiting & Caching System
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)

        # Configuration
        self.global_rate_limits: Dict[str, RateLimitConfig] = {}
        self.endpoint_rate_limits: Dict[str, Dict[str, RateLimitConfig]] = {}
        self.whitelisted_ips: Set[str] = set()
        self.blacklisted_ips: Set[str] = set()

        # Backends
        rate_limit_backend_type = self.config.get("rate_limit_backend", "sqlite")
        if rate_limit_backend_type == "sqlite":
            self.rate_limit_backend = SQLiteRateLimitBackend(
                self.config.get("rate_limit_db", "rate_limits.db")
            )
        else:
            self.rate_limit_backend = MemoryRateLimitBackend()

        self.cache_backend = HybridCacheBackend(
            self.config.get("cache_db", "cache.db"),
            self.config.get("max_memory_cache", 1000),
        )

        # Default rate limits
        self._setup_default_rate_limits()

        # Background cleanup
        self.cleanup_interval = self.config.get("cleanup_interval", 3600)  # 1 hour
        self._start_cleanup_task()

        # Stats
        self.stats = {
            "requests_total": 0,
            "requests_blocked": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "cache_evictions": 0,
            "rate_limits_hit": 0,
        }

        self.logger.info("API Rate Limiting & Caching System initialized")

    def _setup_default_rate_limits(self):
        """Setup default rate limits"""
        # Global rate limit
        self.global_rate_limits["default"] = RateLimitConfig(
            strategy=RateLimitStrategy.SLIDING_WINDOW,
            limit=1000,  # 1000 requests per minute
            window_seconds=60,
            block_duration=300,
        )

        # User-specific rate limit
        self.global_rate_limits["user"] = RateLimitConfig(
            strategy=RateLimitStrategy.SLIDING_WINDOW,
            limit=100,
            window_seconds=60,
            block_duration=300,
        )

        # IP-specific rate limit
        self.global_rate_limits["ip"] = RateLimitConfig(
            strategy=RateLimitStrategy.SLIDING_WINDOW,
            limit=200,
            window_seconds=60,
            block_duration=300,
        )

        # API key rate limit
        self.global_rate_limits["api_key"] = RateLimitConfig(
            strategy=RateLimitStrategy.TOKEN_BUCKET,
            limit=500,
            window_seconds=60,
            burst_size=50,
            refill_rate=8.33,  # 500 per minute = 8.33 per second
        )

    def _start_cleanup_task(self):
        """Start background cleanup task"""

        async def cleanup_loop():
            while True:
                try:
                    await asyncio.sleep(self.cleanup_interval)
                    await self._cleanup_old_data()
                except Exception as e:
                    self.logger.error(f"Cleanup task error: {e}")

        # Start in background
        asyncio.create_task(cleanup_loop())
        self.logger.info("Background cleanup task started")

    async def _cleanup_old_data(self):
        """Cleanup old rate limit and cache data"""
        self.logger.info("Starting cleanup of old rate limit and cache data")

        # Cleanup rate limit data older than 24 hours
        await self.rate_limit_backend.cleanup_old_entries(86400)

        # Cache stats
        cache_stats = await self.cache_backend.get_stats()
        self.logger.info(f"Cache stats: {cache_stats}")

        self.logger.info("Cleanup completed")

    def _calculate_request_signature(
        self, endpoint: str, params: Dict[str, Any], headers: Dict[str, Any] = None
    ) -> str:
        """Calculate cache signature for request"""
        # Create canonical representation
        canonical_parts = [endpoint]

        # Add sorted query params
        if params:
            sorted_params = sorted([(k, v) for k, v in params.items()])
            canonical_parts.append("&".join(f"{k}={v}" for k, v in sorted_params))

        # Add relevant headers
        if headers:
            relevant_headers = {
                k: v
                for k, v in headers.items()
                if k.lower() in ["authorization", "content-type", "accept"]
            }

            sorted_headers = sorted([(k, v) for k, v in relevant_headers.items()])
            canonical_parts.append("&".join(f"{k}:{v}" for k, v in sorted_headers))

        canonical_string = "|".join(canonical_parts)

        return hashlib.sha256(canonical_string.encode()).hexdigest()

    async def check_rate_limit(
        self,
        identifier: str,  # user_id, ip, or api_key
        identifier_type: str = "user",
        endpoint: str = None,
        weight: int = 1,
    ) -> Tuple[bool, Dict[str, Any]]:
        """Check rate limit for request"""
        self.stats["requests_total"] += 1

        # Check blacklist
        if identifier in self.blacklisted_ips:
            self.stats["requests_blocked"] += 1
            return False, {
                "allowed": False,
                "reason": "blacklisted",
                "retry_after": None,
            }

        # Check whitelist
        if identifier in self.whitelisted_ips:
            return True, {"allowed": True, "reason": "whitelisted"}

        # Get rate limit config
        config = self._get_rate_limit_config(identifier_type, endpoint)

        # Skipped for certain users
        if config.skip_if_whitelisted and identifier in self.whitelisted_ips:
            return True, {"allowed": True, "reason": "whitelisted"}

        # Limit key
        limit_key = f"{identifier_type}:{identifier}"
        if endpoint:
            limit_key += f":{endpoint}"

        # Check rate limit
        allowed, info = await self._check_rate_limit_strategy(limit_key, config, weight)

        if not allowed:
            self.stats["rate_limits_hit"] += 1

        return allowed, info

    def _get_rate_limit_config(
        self, identifier_type: str, endpoint: str = None
    ) -> RateLimitConfig:
        """Get rate limit config for identifier and endpoint"""
        # Check endpoint-specific config
        if endpoint and endpoint in self.endpoint_rate_limits:
            if identifier_type in self.endpoint_rate_limits[endpoint]:
                return self.endpoint_rate_limits[endpoint][identifier_type]

        # Check identifier type config
        if identifier_type in self.global_rate_limits:
            return self.global_rate_limits[identifier_type]

        # Return default
        return self.global_rate_limits.get(
            "default",
            RateLimitConfig(
                strategy=RateLimitStrategy.SLIDING_WINDOW, limit=100, window_seconds=60
            ),
        )

    async def _check_rate_limit_strategy(
        self, key: str, config: RateLimitConfig, weight: int = 1
    ) -> Tuple[bool, Dict[str, Any]]:
        """Check rate limit based on strategy"""
        now = time.time()

        if config.strategy == RateLimitStrategy.FIXED_WINDOW:
            return await self._check_fixed_window(key, config, weight, now)

        elif config.strategy == RateLimitStrategy.SLIDING_WINDOW:
            return await self._check_sliding_window(key, config, weight, now)

        elif config.strategy == RateLimitStrategy.TOKEN_BUCKET:
            return await self._check_token_bucket(key, config, weight, now)

        elif config.strategy == RateLimitStrategy.LEAKY_BUCKET:
            return await self._check_leaky_bucket(key, config, weight, now)

        return True, {"reason": "unknown_strategy"}

    async def _check_fixed_window(
        self, key: str, config: RateLimitConfig, weight: int, now: float
    ) -> Tuple[bool, Dict[str, Any]]:
        """Check fixed window rate limit"""
        # Calculate window start
        window_start = (now // config.window_seconds) * config.window_seconds

        # Get current count
        count = await self.rate_limit_backend.get_window_count(key, window_start)

        # Check if blocked
        bucket = await self.rate_limit_backend.get_bucket(key)
        if bucket and bucket.blocked_until > now:
            retry_after = bucket.blocked_until - now
            return False, {
                "allowed": False,
                "reason": "blocked",
                "retry_after": retry_after,
            }

        # Check limit (bucketed approach)
        if bucket and bucket.window_start != window_start:
            # New window, reset
            bucket.count = 0
            bucket.window_start = window_start
        elif not bucket:
            bucket = RateLimitBucket(
                key=key, count=0, window_start=window_start, tokens=0, last_refill=now
            )

        if bucket.count + weight > config.limit:
            # Block
            bucket.blocked_until = now + config.block_duration
            await self.rate_limit_backend.save_bucket(bucket)

            return False, {
                "allowed": False,
                "reason": "rate_limit_exceeded",
                "current_count": bucket.count,
                "limit": config.limit,
                "retry_after": config.block_duration,
            }

        # Allow
        bucket.count += weight
        await self.rate_limit_backend.save_bucket(bucket)

        return True, {
            "allowed": True,
            "current_count": bucket.count,
            "limit": config.limit,
            "remaining": config.limit - bucket.count,
        }

    async def _check_sliding_window(
        self, key: str, config: RateLimitConfig, weight: int, now: float
    ) -> Tuple[bool, Dict[str, Any]]:
        """Check sliding window rate limit"""
        # Calculate current window
        window_start = now - config.window_seconds

        # This is a simplified sliding window
        # In production, you'd use Redis with sorted sets for accurate sliding window

        # For now, approximate with fixed windows
        count = 0

        for i in range(config.window_seconds):
            check_window = window_start + i
            window_count = await self.rate_limit_backend.get_window_count(
                key, check_window
            )
            count += window_count

        # Check if blocked
        bucket = await self.rate_limit_backend.get_bucket(key)
        if bucket and bucket.blocked_until > now:
            retry_after = bucket.blocked_until - now
            return False, {
                "allowed": False,
                "reason": "blocked",
                "retry_after": retry_after,
            }

        if bucket is None:
            bucket = RateLimitBucket(
                key=key, count=0, window_start=now, tokens=0, last_refill=now
            )

        if count + weight > config.limit:
            # Block
            bucket.blocked_until = now + config.block_duration
            await self.rate_limit_backend.save_bucket(bucket)

            return False, {
                "allowed": False,
                "reason": "rate_limit_exceeded",
                "current_count": count,
                "limit": config.limit,
                "retry_after": config.block_duration,
            }

        # Allow and increment window
        await self.rate_limit_backend.increment_counter(key, now)
        bucket.count = count + weight
        await self.rate_limit_backend.save_bucket(bucket)

        return True, {
            "allowed": True,
            "current_count": count + weight,
            "limit": config.limit,
            "remaining": config.limit - (count + weight),
        }

    async def _check_token_bucket(
        self, key: str, config: RateLimitConfig, weight: int, now: float
    ) -> Tuple[bool, Dict[str, Any]]:
        """Check token bucket rate limit"""
        bucket = await self.rate_limit_backend.get_bucket(key)

        if not bucket:
            bucket = RateLimitBucket(
                key=key, count=0, window_start=now, tokens=config.limit, last_refill=now
            )

        # Check if blocked
        if bucket.blocked_until > now:
            retry_after = bucket.blocked_until - now
            return False, {
                "allowed": False,
                "reason": "blocked",
                "retry_after": retry_after,
            }

        # Refill tokens
        time_since_refill = now - bucket.last_refill
        refill_amount = time_since_refill * config.refill_rate
        bucket.tokens = min(bucket.tokens + refill_amount, config.limit)
        bucket.last_refill = now

        # Check if enough tokens
        if bucket.tokens < weight:
            return False, {
                "allowed": False,
                "reason": "rate_limit_exceeded",
                "current_tokens": bucket.tokens,
                "required_tokens": weight,
                "limit": config.limit,
                "refill_rate": config.refill_rate,
            }

        # Consume tokens
        bucket.tokens -= weight
        bucket.count += weight
        await self.rate_limit_backend.save_bucket(bucket)

        return True, {
            "allowed": True,
            "current_tokens": bucket.tokens,
            "limit": config.limit,
            "refill_rate": config.refill_rate,
        }

    async def _check_leaky_bucket(
        self, key: str, config: RateLimitConfig, weight: int, now: float
    ) -> Tuple[bool, Dict[str, Any]]:
        """Check leaky bucket rate limit (approximated)"""
        # Leaky bucket is similar to token bucket but with different semantics
        # For simplicity, we'll use token bucket approximation
        return await self._check_token_bucket(key, config, weight, now)

    async def get_cached_response(
        self,
        endpoint: str,
        params: Dict[str, Any] = None,
        headers: Dict[str, Any] = None,
    ) -> Optional[Any]:
        """Get cached response for request"""
        if params is None:
            params = {}
        if headers is None:
            headers = {}

        cache_key = self._calculate_request_signature(endpoint, params, headers)

        entry = await self.cache_backend.get(cache_key)

        if entry and not entry.is_expired():
            self.stats["cache_hits"] += 1
            return entry.data

        self.stats["cache_misses"] += 1
        return None

    async def cache_response(
        self,
        endpoint: str,
        params: Dict[str, Any],
        headers: Dict[str, Any],
        response: Any,
        ttl_seconds: int = None,
    ) -> bool:
        """Cache response for request"""
        cache_key = self._calculate_request_signature(endpoint, params, headers)

        default_ttl = self.config.get("default_cache_ttl", 300)
        entry = CacheEntry(
            key=cache_key,
            data=response,
            created_at=time.time(),
            accessed_at=time.time(),
            access_count=1,
            size_bytes=len(json.dumps(response)),
            ttl_seconds=ttl_seconds or default_ttl,
        )

        await self.cache_backend.set(entry)
        return True

    async def invalidate_cache(
        self, endpoint: str = None, params: Dict[str, Any] = None
    ):
        """Invalidate cache entries"""
        if endpoint:
            cache_key = self._calculate_request_signature(endpoint, params or {})
            await self.cache_backend.delete(cache_key)
        else:
            # Clear all cache
            await self.cache_backend.clear()

    async def get_cached_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        stats = await self.cache_backend.get_stats()
        stats.update(
            {
                "cache_hits": self.stats["cache_hits"],
                "cache_misses": self.stats["cache_misses"],
                "hit_rate": self.stats["cache_hits"]
                / max(self.stats["cache_hits"] + self.stats["cache_misses"], 1),
            }
        )
        return stats

    async def get_rate_limit_stats(self) -> Dict[str, Any]:
        """Get rate limit statistics"""
        return {
            "requests_total": self.stats["requests_total"],
            "requests_blocked": self.stats["requests_blocked"],
            "rate_limits_hit": self.stats["rate_limits_hit"],
            "block_rate": self.stats["requests_blocked"]
            / max(self.stats["requests_total"], 1),
        }

    def set_whitelist(self, ips: List[str]):
        """Set whitelisted IPs"""
        self.whitelisted_ips = set(ips)

    def add_to_whitelist(self, ip: str):
        """Add IP to whitelist"""
        self.whitelisted_ips.add(ip)

    def remove_from_whitelist(self, ip: str):
        """Remove IP from whitelist"""
        self.whitelisted_ips.discard(ip)

    def set_blacklist(self, ips: List[str]):
        """Set blacklisted IPs"""
        self.blacklisted_ips = set(ips)

    def add_to_blacklist(self, ip: str):
        """Add IP to blacklist"""
        self.blacklisted_ips.add(ip)

    def remove_from_blacklist(self, ip: str):
        """Remove IP from blacklist"""
        self.blacklisted_ips.discard(ip)

    def set_endpoint_rate_limit(
        self, endpoint: str, identifier_type: str, config: RateLimitConfig
    ):
        """Set endpoint-specific rate limit"""
        if endpoint not in self.endpoint_rate_limits:
            self.endpoint_rate_limits[endpoint] = {}

        self.endpoint_rate_limits[endpoint][identifier_type] = config

    def decorator(
        self,
        endpoint: str = None,
        identifier_type: str = "user",
        weight: int = 1,
        cache_ttl: int = None,
    ):
        """Decorator for rate limiting and caching"""

        def decorator_wrapper(func):
            @functools.wraps(func)
            async def wrapped(*args, **kwargs):
                # Extract context for rate limiting
                identifier = kwargs.get("user_id", "anonymous")
                ip_address = kwargs.get("ip_address", "127.0.0.1")

                # Check rate limit
                allowed, rate_info = await self.check_rate_limit(
                    identifier=identifier,
                    identifier_type=identifier_type,
                    endpoint=endpoint or func.__name__,
                    weight=weight,
                )

                if not allowed:
                    raise RateLimitExceededError(rate_info)

                # Check cache
                params = kwargs.copy()
                params.pop("user_id", None)
                params.pop("ip_address", None)

                cache_key = f"{endpoint or func.__name__}_{str(params)}"
                cached = await self.get_cached_response(
                    endpoint=endpoint or func.__name__, params=params
                )

                if cached is not None:
                    return cached

                # Execute function
                result = await func(*args, **kwargs)

                # Cache result
                if cache_ttl is not None and cache_ttl > 0:
                    await self.cache_response(
                        endpoint=endpoint or func.__name__,
                        params=params,
                        headers={},
                        response=result,
                        ttl_seconds=cache_ttl,
                    )

                return result

            return wrapped

        return decorator_wrapper


class RateLimitExceededError(Exception):
    """Rate limit exceeded exception"""

    def __init__(self, rate_info: Dict[str, Any]):
        self.rate_info = rate_info
        self.retry_after = rate_info.get("retry_after", 0)
        super().__init__(f"Rate limit exceeded: {rate_info}")


# Example usage and testing
async def test_rate_limit_cache_system():
    """Test the rate limiting and caching system"""

    print("Initializing API Rate Limiting & Caching System...")
    system = APIRateLimitCache(
        {
            "rate_limit_backend": "sqlite",
            "rate_limit_db": "test_rate_limits.db",
            "cache_db": "test_cache.db",
            "max_memory_cache": 500,
            "default_cache_ttl": 300,
        }
    )

    # Set up rate limits
    print("\n=== Setting Up Rate Limits ===")

    # Set strict rate limit for testing
    test_rate_limit = RateLimitConfig(
        strategy=RateLimitStrategy.SLIDING_WINDOW,
        limit=10,  # 10 requests per minute
        window_seconds=60,
    )

    system.set_endpoint_rate_limit(
        endpoint="test_api", identifier_type="user", config=test_rate_limit
    )

    # Test 1: Rate limiting - Allowed requests
    print("\n=== Test 1: Rate Limiting (Allowed) ===")
    user_id = "test_user_123"

    for i in range(5):
        allowed, info = await system.check_rate_limit(
            identifier=user_id, identifier_type="user", endpoint="test_api"
        )
        print(
            f"Request {i + 1}: allowed={allowed}, remaining={info.get('remaining', 'N/A')}"
        )
        await asyncio.sleep(0.1)  # Small delay between requests

    # Test 2: Rate limiting - Exceed limit
    print("\n=== Test 2: Rate Limiting (Exceeded) ===")

    for i in range(10):
        allowed, info = await system.check_rate_limit(
            identifier=user_id, identifier_type="user", endpoint="test_api"
        )
        print(
            f"Request {i + 6}: allowed={allowed}, remaining={info.get('remaining', 'N/A')}"
        )

    # Test 3: Caching
    print("\n=== Test 3: Caching ===")

    endpoint = "get_user_data"
    params = {"user_id": "123", "section": "profile"}
    response_data = {"user": {"id": "123", "name": "Test User", "score": 100}}

    # Cache miss
    cached = await system.get_cached_response(endpoint, params)
    print(f"Cache miss (expected): {cached is not None}")

    # Set cache
    await system.cache_response(endpoint, params, {}, response_data, ttl_seconds=60)
    print("Response cached")

    # Cache hit
    cached = await system.get_cached_response(endpoint, params)
    print(f"Cache hit (expected): {cached is not None}")
    print(f"Cached data: {cached}")

    # Test 4: Token bucket rate limit
    print("\n=== Test 4: Token Bucket Rate Limit ===")

    token_bucket_limit = RateLimitConfig(
        strategy=RateLimitStrategy.TOKEN_BUCKET,
        limit=20,
        window_seconds=60,
        burst_size=10,
        refill_rate=0.33,  # 20 per minute = 0.33 per second
    )

    system.set_endpoint_rate_limit(
        endpoint="token_api", identifier_type="user", config=token_bucket_limit
    )

    # Burst requests
    for i in range(12):
        allowed, info = await system.check_rate_limit(
            identifier="token_user", identifier_type="user", endpoint="token_api"
        )
        print(
            f"Burst request {i + 1}: allowed={allowed}, tokens={info.get('current_tokens', 'N/A')}"
        )

    # Test 5: Decorator usage
    print("\n=== Test 5: Decorator Usage ===")

    class TestAPI:
        def __init__(self, rate_limit_system):
            self.rate_limit = rate_limit_system

        @system.decorator(
            endpoint="expensive_operation",
            identifier_type="user",
            weight=2,
            cache_ttl=300,
        )
        async def expensive_operation(self, user_id: str, data_input: str):
            # Simulate expensive operation
            await asyncio.sleep(0.1)
            return {
                "result": f"Processed {data_input} for {user_id}",
                "timestamp": time.time(),
            }

    test_api = TestAPI(system)

    # First call (cache miss)
    result1 = await test_api.expensive_operation(
        user_id="user123", data_input="test data"
    )
    print(f"First call result: {result1}")

    # Second call (cache hit - faster)
    result2 = await test_api.expensive_operation(
        user_id="user123", data_input="test data"
    )
    print(f"Second call result: {result2}")
    print(
        f"Same timestamp (from cache): {result1.get('timestamp') == result2.get('timestamp')}"
    )

    # Test 6: Stats
    print("\n=== System Statistics ===")

    rate_stats = await system.get_rate_limit_stats()
    print("Rate Limit Stats:")
    print(json.dumps(rate_stats, indent=2))

    cache_stats = await system.get_cached_stats()
    print("\nCache Stats:")
    print(json.dumps(cache_stats, indent=2))

    print("\nRate Limiting & Caching system test completed!")


if __name__ == "__main__":
    import json

    asyncio.run(test_rate_limit_cache_system())

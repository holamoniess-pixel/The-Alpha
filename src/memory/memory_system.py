#!/usr/bin/env python3
"""
ALPHA OMEGA - HIGH-PERFORMANCE MEMORY SYSTEM
Hierarchical storage with intelligent caching
Version: 2.0.0
"""

import asyncio
import sqlite3
import json
import time
import threading
import hashlib
import pickle
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import OrderedDict
import logging


@dataclass
class MemoryEntry:
    id: Optional[int] = None
    timestamp: float = field(default_factory=time.time)
    entry_type: str = "generic"
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)
    importance: float = 1.0
    tags: List[str] = field(default_factory=list)


class LRUCache:
    def __init__(self, capacity: int = 1000):
        self.capacity = capacity
        self.cache: OrderedDict[str, Any] = OrderedDict()
        self._lock = threading.RLock()
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key in self.cache:
                self._hits += 1
                self.cache.move_to_end(key)
                return self.cache[key]
            self._misses += 1
            return None

    def put(self, key: str, value: Any):
        with self._lock:
            if key in self.cache:
                self.cache.move_to_end(key)
            else:
                if len(self.cache) >= self.capacity:
                    self.cache.popitem(last=False)
            self.cache[key] = value

    def delete(self, key: str):
        with self._lock:
            if key in self.cache:
                del self.cache[key]

    def clear(self):
        with self._lock:
            self.cache.clear()

    def stats(self) -> Dict[str, int]:
        with self._lock:
            total = self._hits + self._misses
            return {
                "size": len(self.cache),
                "capacity": self.capacity,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": (self._hits / total * 100) if total > 0 else 0,
            }


class MemorySystem:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger("MemorySystem")

        self.db_path = Path("data/memory.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._connection = None
        self._connection_lock = threading.RLock()

        self._hot_cache = LRUCache(capacity=1000)
        self._pattern_cache = LRUCache(capacity=500)
        self._context_cache = LRUCache(capacity=200)

        self._write_queue = []
        self._write_lock = threading.Lock()
        self._batch_size = 100
        self._flush_interval = 5.0

        self._stats = {
            "total_entries": 0,
            "patterns_stored": 0,
            "commands_stored": 0,
            "events_stored": 0,
        }

        self._running = False

    @property
    def connection(self) -> sqlite3.Connection:
        if self._connection is None:
            with self._connection_lock:
                if self._connection is None:
                    self._connection = sqlite3.connect(
                        str(self.db_path), check_same_thread=False, timeout=30.0
                    )
                    self._connection.execute("PRAGMA journal_mode=WAL")
                    self._connection.execute("PRAGMA synchronous=NORMAL")
                    self._connection.execute("PRAGMA cache_size=10000")
                    self._connection.execute("PRAGMA temp_store=MEMORY")
        return self._connection

    async def initialize(self) -> bool:
        self.logger.info("Initializing Memory System...")

        try:
            self._create_tables()
            self._load_cache()
            self._running = True
            self.logger.info("Memory System initialized successfully")
            return True
        except Exception as e:
            self.logger.error(f"Memory initialization failed: {e}")
            return False

    def _create_tables(self):
        tables = [
            """CREATE TABLE IF NOT EXISTS commands (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL DEFAULT (julianday('now') * 86400),
                command TEXT NOT NULL,
                intent TEXT,
                success INTEGER DEFAULT 0,
                response TEXT,
                context TEXT,
                execution_time_ms REAL,
                user_id TEXT DEFAULT 'default'
            )""",
            """CREATE TABLE IF NOT EXISTS patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_type TEXT NOT NULL,
                pattern_hash TEXT UNIQUE,
                pattern_data TEXT NOT NULL,
                frequency INTEGER DEFAULT 1,
                confidence REAL DEFAULT 0.0,
                first_seen REAL DEFAULT (julianday('now') * 86400),
                last_seen REAL DEFAULT (julianday('now') * 86400),
                metadata TEXT
            )""",
            """CREATE TABLE IF NOT EXISTS user_behavior (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                behavior_type TEXT NOT NULL,
                behavior_data TEXT NOT NULL,
                timestamp REAL DEFAULT (julianday('now') * 86400),
                session_id TEXT,
                context TEXT
            )""",
            """CREATE TABLE IF NOT EXISTS system_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                event_data TEXT NOT NULL,
                timestamp REAL DEFAULT (julianday('now') * 86400),
                severity TEXT DEFAULT 'info',
                component TEXT
            )""",
            """CREATE TABLE IF NOT EXISTS knowledge_base (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                confidence REAL DEFAULT 1.0,
                created_at REAL DEFAULT (julianday('now') * 86400),
                updated_at REAL DEFAULT (julianday('now') * 86400),
                UNIQUE(category, key)
            )""",
            """CREATE TABLE IF NOT EXISTS context_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                context_data TEXT NOT NULL,
                timestamp REAL DEFAULT (julianday('now') * 86400),
                relevance_score REAL DEFAULT 1.0
            )""",
            """CREATE TABLE IF NOT EXISTS workflow_sequences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workflow_name TEXT NOT NULL,
                sequence_data TEXT NOT NULL,
                frequency INTEGER DEFAULT 1,
                last_executed REAL,
                success_rate REAL DEFAULT 1.0,
                created_at REAL DEFAULT (julianday('now') * 86400)
            )""",
        ]

        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_commands_timestamp ON commands(timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_commands_intent ON commands(intent)",
            "CREATE INDEX IF NOT EXISTS idx_patterns_type ON patterns(pattern_type)",
            "CREATE INDEX IF NOT EXISTS idx_patterns_frequency ON patterns(frequency DESC)",
            "CREATE INDEX IF NOT EXISTS idx_events_type ON system_events(event_type)",
            "CREATE INDEX IF NOT EXISTS idx_events_timestamp ON system_events(timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_knowledge_category ON knowledge_base(category)",
        ]

        with self._connection_lock:
            for table_sql in tables:
                self.connection.execute(table_sql)
            for index_sql in indexes:
                self.connection.execute(index_sql)
            self.connection.commit()

    def _load_cache(self):
        cursor = self.connection.execute(
            """SELECT id, pattern_type, pattern_data, frequency, confidence 
               FROM patterns 
               WHERE last_seen > julianday('now') * 86400 - 86400 
               ORDER BY frequency DESC LIMIT 500"""
        )

        for row in cursor:
            cache_key = f"pattern_{row[0]}"
            self._pattern_cache.put(
                cache_key,
                {
                    "id": row[0],
                    "type": row[1],
                    "data": json.loads(row[2]),
                    "frequency": row[3],
                    "confidence": row[4],
                },
            )

        self._stats["patterns_stored"] = len(self._pattern_cache.cache)
        self.logger.info(f"Loaded {self._stats['patterns_stored']} patterns into cache")

    async def store_command(
        self,
        command: str,
        intent: str,
        success: bool,
        response: str,
        context: Dict[str, Any] = None,
        execution_time_ms: float = 0,
    ) -> int:
        cache_key = hashlib.md5(f"cmd_{command}_{time.time()}".encode()).hexdigest()

        entry = {
            "command": command,
            "intent": intent,
            "success": 1 if success else 0,
            "response": response[:1000] if response else None,
            "context": json.dumps(context) if context else None,
            "execution_time_ms": execution_time_ms,
            "timestamp": time.time(),
        }

        self._hot_cache.put(cache_key, entry)

        with self._write_lock:
            self._write_queue.append({"table": "commands", "data": entry})

            if len(self._write_queue) >= self._batch_size:
                await self._flush_write_queue()

        self._stats["commands_stored"] += 1
        return self._stats["commands_stored"]

    async def store_pattern(
        self, pattern_type: str, pattern_data: Dict[str, Any], confidence: float = 1.0
    ) -> int:
        pattern_json = json.dumps(pattern_data, sort_keys=True)
        pattern_hash = hashlib.sha256(pattern_json.encode()).hexdigest()

        cache_key = f"pattern_{pattern_hash}"
        cached = self._pattern_cache.get(cache_key)

        if cached:
            self.connection.execute(
                """UPDATE patterns 
                   SET frequency = frequency + 1,
                       last_seen = julianday('now') * 86400,
                       confidence = ?
                   WHERE pattern_hash = ?""",
                (confidence, pattern_hash),
            )
            self.connection.commit()
            return cached.get("id", 0)

        cursor = self.connection.execute(
            """INSERT INTO patterns (pattern_type, pattern_hash, pattern_data, confidence)
               VALUES (?, ?, ?, ?)""",
            (pattern_type, pattern_hash, pattern_json, confidence),
        )
        self.connection.commit()

        pattern_id = cursor.lastrowid

        self._pattern_cache.put(
            cache_key,
            {
                "id": pattern_id,
                "type": pattern_type,
                "data": pattern_data,
                "frequency": 1,
                "confidence": confidence,
            },
        )

        self._stats["patterns_stored"] += 1
        return pattern_id

    async def get_patterns(
        self, pattern_type: str = None, limit: int = 100, min_confidence: float = 0.0
    ) -> List[Dict[str, Any]]:
        query = """SELECT id, pattern_type, pattern_data, frequency, confidence, last_seen
                   FROM patterns WHERE confidence >= ?"""
        params = [min_confidence]

        if pattern_type:
            query += " AND pattern_type = ?"
            params.append(pattern_type)

        query += " ORDER BY frequency DESC, confidence DESC LIMIT ?"
        params.append(limit)

        cursor = self.connection.execute(query, params)

        patterns = []
        for row in cursor:
            patterns.append(
                {
                    "id": row[0],
                    "type": row[1],
                    "data": json.loads(row[2]),
                    "frequency": row[3],
                    "confidence": row[4],
                    "last_seen": row[5],
                }
            )

        return patterns

    async def store_event(
        self,
        event_type: str,
        event_data: Dict[str, Any],
        severity: str = "info",
        component: str = None,
    ):
        self.connection.execute(
            """INSERT INTO system_events (event_type, event_data, severity, component)
               VALUES (?, ?, ?, ?)""",
            (event_type, json.dumps(event_data), severity, component),
        )
        self.connection.commit()
        self._stats["events_stored"] += 1

    async def get_recent_commands(
        self, hours: int = 24, limit: int = 100
    ) -> List[Dict[str, Any]]:
        cursor = self.connection.execute(
            """SELECT command, intent, success, response, timestamp, execution_time_ms
               FROM commands
               WHERE timestamp > julianday('now') * 86400 - ?
               ORDER BY timestamp DESC LIMIT ?""",
            (hours * 3600, limit),
        )

        commands = []
        for row in cursor:
            commands.append(
                {
                    "command": row[0],
                    "intent": row[1],
                    "success": bool(row[2]),
                    "response": row[3],
                    "timestamp": row[4],
                    "execution_time_ms": row[5],
                }
            )

        return commands

    async def store_knowledge(
        self, category: str, key: str, value: Any, confidence: float = 1.0
    ):
        value_json = json.dumps(value) if not isinstance(value, str) else value

        self.connection.execute(
            """INSERT INTO knowledge_base (category, key, value, confidence, updated_at)
               VALUES (?, ?, ?, ?, julianday('now') * 86400)
               ON CONFLICT(category, key) 
               DO UPDATE SET value = ?, confidence = ?, updated_at = julianday('now') * 86400""",
            (category, key, value_json, confidence, value_json, confidence),
        )
        self.connection.commit()

    async def get_knowledge(
        self, category: str = None, key: str = None
    ) -> List[Dict[str, Any]]:
        if category and key:
            cursor = self.connection.execute(
                "SELECT category, key, value, confidence FROM knowledge_base WHERE category = ? AND key = ?",
                (category, key),
            )
        elif category:
            cursor = self.connection.execute(
                "SELECT category, key, value, confidence FROM knowledge_base WHERE category = ?",
                (category,),
            )
        else:
            cursor = self.connection.execute(
                "SELECT category, key, value, confidence FROM knowledge_base"
            )

        results = []
        for row in cursor:
            value = row[2]
            try:
                value = json.loads(value)
            except:
                pass
            results.append(
                {
                    "category": row[0],
                    "key": row[1],
                    "value": value,
                    "confidence": row[3],
                }
            )

        return results

    async def search(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        search_term = f"%{query}%"

        cursor = self.connection.execute(
            """SELECT 'command' as type, id, command as content, timestamp
               FROM commands WHERE command LIKE ? OR response LIKE ?
               UNION ALL
               SELECT 'pattern' as type, id, pattern_data as content, last_seen as timestamp
               FROM patterns WHERE pattern_data LIKE ?
               UNION ALL
               SELECT 'knowledge' as type, id, value as content, updated_at as timestamp
               FROM knowledge_base WHERE value LIKE ?
               ORDER BY timestamp DESC LIMIT ?""",
            (search_term, search_term, search_term, search_term, limit),
        )

        results = []
        for row in cursor:
            results.append(
                {"type": row[0], "id": row[1], "content": row[2], "timestamp": row[3]}
            )

        return results

    async def _flush_write_queue(self):
        if not self._write_queue:
            return

        with self._write_lock:
            batch = self._write_queue.copy()
            self._write_queue.clear()

        try:
            with self._connection_lock:
                for item in batch:
                    if item["table"] == "commands":
                        self.connection.execute(
                            """INSERT INTO commands (command, intent, success, response, context, execution_time_ms)
                               VALUES (?, ?, ?, ?, ?, ?)""",
                            (
                                item["data"]["command"],
                                item["data"]["intent"],
                                item["data"]["success"],
                                item["data"]["response"],
                                item["data"]["context"],
                                item["data"]["execution_time_ms"],
                            ),
                        )
                self.connection.commit()
        except Exception as e:
            self.logger.error(f"Error flushing write queue: {e}")

    async def start_maintenance(self):
        self.logger.info("Memory maintenance loop started")

        while self._running:
            try:
                await asyncio.sleep(3600)

                retention_days = self.config.get("memory_retention_days", 30)

                self.connection.execute(
                    "DELETE FROM commands WHERE timestamp < julianday('now') * 86400 - ?",
                    (retention_days * 86400,),
                )

                self.connection.execute(
                    "DELETE FROM system_events WHERE timestamp < julianday('now') * 86400 - 604800"
                )

                self.connection.execute("VACUUM")
                self.connection.commit()

                self.logger.debug("Memory maintenance completed")

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Maintenance error: {e}")
                await asyncio.sleep(300)

    def get_stats(self) -> Dict[str, Any]:
        cursor = self.connection.execute("SELECT COUNT(*) FROM commands")
        command_count = cursor.fetchone()[0]

        cursor = self.connection.execute("SELECT COUNT(*) FROM patterns")
        pattern_count = cursor.fetchone()[0]

        cursor = self.connection.execute("SELECT COUNT(*) FROM knowledge_base")
        knowledge_count = cursor.fetchone()[0]

        return {
            "total_commands": command_count,
            "total_patterns": pattern_count,
            "knowledge_entries": knowledge_count,
            "cache_stats": {
                "hot_cache": self._hot_cache.stats(),
                "pattern_cache": self._pattern_cache.stats(),
                "context_cache": self._context_cache.stats(),
            },
        }

    async def save_and_close(self):
        self._running = False

        await self._flush_write_queue()

        if self._connection:
            self._connection.commit()
            self._connection.close()

        self.logger.info("Memory system saved and closed")

    async def stop(self):
        await self.save_and_close()

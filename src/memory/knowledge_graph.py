#!/usr/bin/env python3
"""
ALPHA OMEGA - KNOWLEDGE GRAPH SYSTEM
Persistent Memory & Entity Relationship Graph
Version: 2.0.0
"""

import asyncio
import json
import logging
import time
import hashlib
import sqlite3
from pathlib import Path
from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
import threading
import math


class EntityType(Enum):
    PERSON = "person"
    FILE = "file"
    APPLICATION = "application"
    WEBSITE = "website"
    COMMAND = "command"
    CONCEPT = "concept"
    EVENT = "event"
    LOCATION = "location"
    ORGANIZATION = "organization"
    TOPIC = "topic"
    WORKFLOW = "workflow"
    PREFERENCE = "preference"
    SKILL = "skill"
    ERROR = "error"
    SOLUTION = "solution"


class RelationType(Enum):
    RELATED_TO = "related_to"
    CREATED_BY = "created_by"
    USED_WITH = "used_with"
    PART_OF = "part_of"
    DEPENDS_ON = "depends_on"
    FOLLOWS = "follows"
    PRECEDES = "precedes"
    SOLVES = "solves"
    CAUSED_BY = "caused_by"
    PREFERRED_OVER = "preferred_over"
    SIMILAR_TO = "similar_to"
    OPPOSITE_OF = "opposite_of"
    LOCATED_AT = "located_at"
    BELONGS_TO = "belongs_to"
    ACCESSED_BY = "accessed_by"
    TRIGGERED_BY = "triggered_by"
    RESULTS_IN = "results_in"


@dataclass
class Entity:
    id: str
    entity_type: EntityType
    name: str
    properties: Dict[str, Any] = field(default_factory=dict)
    embedding: List[float] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    access_count: int = 0
    importance: float = 0.5

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.entity_type.value,
            "name": self.name,
            "properties": self.properties,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "access_count": self.access_count,
            "importance": self.importance,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Entity":
        return cls(
            id=data["id"],
            entity_type=EntityType(data["type"]),
            name=data["name"],
            properties=data.get("properties", {}),
            created_at=data.get("created_at", time.time()),
            updated_at=data.get("updated_at", time.time()),
            access_count=data.get("access_count", 0),
            importance=data.get("importance", 0.5),
        )


@dataclass
class Relation:
    id: str
    source_id: str
    target_id: str
    relation_type: RelationType
    properties: Dict[str, Any] = field(default_factory=dict)
    weight: float = 1.0
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "type": self.relation_type.value,
            "properties": self.properties,
            "weight": self.weight,
            "created_at": self.created_at,
        }


@dataclass
class Memory:
    id: str
    content: str
    memory_type: str
    entities: List[str] = field(default_factory=list)
    embedding: List[float] = field(default_factory=list)
    importance: float = 0.5
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    access_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "type": self.memory_type,
            "entities": self.entities,
            "importance": self.importance,
            "created_at": self.created_at,
            "last_accessed": self.last_accessed,
            "access_count": self.access_count,
        }


class KnowledgeGraph:
    """Knowledge Graph with persistent storage and semantic search"""

    def __init__(self, db_path: str = "data/knowledge_graph.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger("KnowledgeGraph")

        self._lock = threading.RLock()
        self._entity_cache: Dict[str, Entity] = {}
        self._relation_cache: Dict[str, Relation] = {}
        self._memory_cache: Dict[str, Memory] = {}
        self._cache_size = 1000

        self._init_db()

    def _init_db(self):
        """Initialize SQLite database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS entities (
                    id TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    name TEXT NOT NULL,
                    properties TEXT,
                    created_at REAL,
                    updated_at REAL,
                    access_count INTEGER,
                    importance REAL
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS relations (
                    id TEXT PRIMARY KEY,
                    source_id TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    type TEXT NOT NULL,
                    properties TEXT,
                    weight REAL,
                    created_at REAL,
                    FOREIGN KEY (source_id) REFERENCES entities(id),
                    FOREIGN KEY (target_id) REFERENCES entities(id)
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    type TEXT NOT NULL,
                    entities TEXT,
                    importance REAL,
                    created_at REAL,
                    last_accessed REAL,
                    access_count INTEGER
                )
            """)

            conn.execute("CREATE INDEX IF NOT EXISTS idx_entity_type ON entities(type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_entity_name ON entities(name)")
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_relation_source ON relations(source_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_relation_target ON relations(target_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_memory_content ON memories(content)"
            )

            conn.commit()

    def _generate_id(self, *args) -> str:
        """Generate unique ID"""
        content = "|".join(str(a) for a in args)
        return hashlib.md5(content.encode()).hexdigest()[:12]

    async def add_entity(
        self,
        entity_type: EntityType,
        name: str,
        properties: Dict[str, Any] = None,
        importance: float = 0.5,
    ) -> Entity:
        """Add or update an entity"""
        with self._lock:
            entity_id = self._generate_id(entity_type.value, name)

            existing = self._get_entity_from_db(entity_id)
            if existing:
                existing.updated_at = time.time()
                existing.access_count += 1
                if properties:
                    existing.properties.update(properties)
                self._save_entity_to_db(existing)
                return existing

            entity = Entity(
                id=entity_id,
                entity_type=entity_type,
                name=name,
                properties=properties or {},
                importance=importance,
            )

            self._save_entity_to_db(entity)
            self._entity_cache[entity_id] = entity

            self.logger.debug(f"Added entity: {name} ({entity_type.value})")
            return entity

    def _get_entity_from_db(self, entity_id: str) -> Optional[Entity]:
        """Get entity from database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT * FROM entities WHERE id = ?", (entity_id,)
                )
                row = cursor.fetchone()
                if row:
                    return Entity(
                        id=row[0],
                        entity_type=EntityType(row[1]),
                        name=row[2],
                        properties=json.loads(row[3]) if row[3] else {},
                        created_at=row[4],
                        updated_at=row[5],
                        access_count=row[6],
                        importance=row[7],
                    )
        except Exception as e:
            self.logger.error(f"Error getting entity: {e}")
        return None

    def _save_entity_to_db(self, entity: Entity):
        """Save entity to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO entities 
                    (id, type, name, properties, created_at, updated_at, access_count, importance)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        entity.id,
                        entity.entity_type.value,
                        entity.name,
                        json.dumps(entity.properties),
                        entity.created_at,
                        entity.updated_at,
                        entity.access_count,
                        entity.importance,
                    ),
                )
                conn.commit()
        except Exception as e:
            self.logger.error(f"Error saving entity: {e}")

    async def add_relation(
        self,
        source_id: str,
        target_id: str,
        relation_type: RelationType,
        properties: Dict[str, Any] = None,
        weight: float = 1.0,
    ) -> Relation:
        """Add a relation between entities"""
        with self._lock:
            relation_id = self._generate_id(source_id, relation_type.value, target_id)

            relation = Relation(
                id=relation_id,
                source_id=source_id,
                target_id=target_id,
                relation_type=relation_type,
                properties=properties or {},
                weight=weight,
            )

            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO relations
                        (id, source_id, target_id, type, properties, weight, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            relation.id,
                            relation.source_id,
                            relation.target_id,
                            relation.relation_type.value,
                            json.dumps(relation.properties),
                            relation.weight,
                            relation.created_at,
                        ),
                    )
                    conn.commit()
            except Exception as e:
                self.logger.error(f"Error saving relation: {e}")

            self._relation_cache[relation_id] = relation
            return relation

    async def get_entity(self, entity_id: str) -> Optional[Entity]:
        """Get entity by ID"""
        if entity_id in self._entity_cache:
            return self._entity_cache[entity_id]
        return self._get_entity_from_db(entity_id)

    async def get_entity_by_name(
        self, name: str, entity_type: EntityType = None
    ) -> Optional[Entity]:
        """Get entity by name"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                if entity_type:
                    cursor = conn.execute(
                        "SELECT * FROM entities WHERE name = ? AND type = ?",
                        (name, entity_type.value),
                    )
                else:
                    cursor = conn.execute(
                        "SELECT * FROM entities WHERE name = ?", (name,)
                    )

                row = cursor.fetchone()
                if row:
                    return Entity(
                        id=row[0],
                        entity_type=EntityType(row[1]),
                        name=row[2],
                        properties=json.loads(row[3]) if row[3] else {},
                        created_at=row[4],
                        updated_at=row[5],
                        access_count=row[6],
                        importance=row[7],
                    )
        except Exception as e:
            self.logger.error(f"Error getting entity by name: {e}")
        return None

    async def get_related_entities(
        self,
        entity_id: str,
        relation_type: RelationType = None,
        max_depth: int = 2,
    ) -> List[Tuple[Entity, Relation]]:
        """Get entities related to a given entity"""
        results = []
        visited = set()
        queue = [(entity_id, 0)]

        while queue:
            current_id, depth = queue.pop(0)

            if current_id in visited or depth > max_depth:
                continue

            visited.add(current_id)

            try:
                with sqlite3.connect(self.db_path) as conn:
                    if relation_type:
                        cursor = conn.execute(
                            """
                            SELECT r.*, e.* FROM relations r
                            JOIN entities e ON r.target_id = e.id
                            WHERE r.source_id = ? AND r.type = ?
                            """,
                            (current_id, relation_type.value),
                        )
                    else:
                        cursor = conn.execute(
                            """
                            SELECT r.*, e.* FROM relations r
                            JOIN entities e ON r.target_id = e.id
                            WHERE r.source_id = ?
                            """,
                            (current_id,),
                        )

                    for row in cursor.fetchall():
                        relation_data = row[:7]
                        entity_data = row[7:]

                        entity = Entity(
                            id=entity_data[0],
                            entity_type=EntityType(entity_data[1]),
                            name=entity_data[2],
                            properties=json.loads(entity_data[3])
                            if entity_data[3]
                            else {},
                            created_at=entity_data[4],
                            updated_at=entity_data[5],
                            access_count=entity_data[6],
                            importance=entity_data[7],
                        )

                        relation = Relation(
                            id=relation_data[0],
                            source_id=relation_data[1],
                            target_id=relation_data[2],
                            relation_type=RelationType(relation_data[3]),
                            properties=json.loads(relation_data[4])
                            if relation_data[4]
                            else {},
                            weight=relation_data[5],
                            created_at=relation_data[6],
                        )

                        results.append((entity, relation))
                        queue.append((entity.id, depth + 1))

            except Exception as e:
                self.logger.error(f"Error getting related entities: {e}")

        return results

    async def search_entities(
        self,
        query: str,
        entity_type: EntityType = None,
        limit: int = 10,
    ) -> List[Entity]:
        """Search entities by name"""
        results = []

        try:
            with sqlite3.connect(self.db_path) as conn:
                if entity_type:
                    cursor = conn.execute(
                        """
                        SELECT * FROM entities 
                        WHERE name LIKE ? AND type = ?
                        ORDER BY importance DESC, access_count DESC
                        LIMIT ?
                        """,
                        (f"%{query}%", entity_type.value, limit),
                    )
                else:
                    cursor = conn.execute(
                        """
                        SELECT * FROM entities 
                        WHERE name LIKE ?
                        ORDER BY importance DESC, access_count DESC
                        LIMIT ?
                        """,
                        (f"%{query}%", limit),
                    )

                for row in cursor.fetchall():
                    entity = Entity(
                        id=row[0],
                        entity_type=EntityType(row[1]),
                        name=row[2],
                        properties=json.loads(row[3]) if row[3] else {},
                        created_at=row[4],
                        updated_at=row[5],
                        access_count=row[6],
                        importance=row[7],
                    )
                    results.append(entity)

        except Exception as e:
            self.logger.error(f"Error searching entities: {e}")

        return results

    async def add_memory(
        self,
        content: str,
        memory_type: str,
        entity_ids: List[str] = None,
        importance: float = 0.5,
    ) -> Memory:
        """Add a memory"""
        memory_id = self._generate_id(content, memory_type)

        memory = Memory(
            id=memory_id,
            content=content,
            memory_type=memory_type,
            entities=entity_ids or [],
            importance=importance,
        )

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO memories
                    (id, content, type, entities, importance, created_at, last_accessed, access_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        memory.id,
                        memory.content,
                        memory.memory_type,
                        json.dumps(memory.entities),
                        memory.importance,
                        memory.created_at,
                        memory.last_accessed,
                        memory.access_count,
                    ),
                )
                conn.commit()
        except Exception as e:
            self.logger.error(f"Error saving memory: {e}")

        self._memory_cache[memory_id] = memory
        return memory

    async def search_memories(
        self,
        query: str,
        memory_type: str = None,
        limit: int = 10,
    ) -> List[Memory]:
        """Search memories by content"""
        results = []

        try:
            with sqlite3.connect(self.db_path) as conn:
                if memory_type:
                    cursor = conn.execute(
                        """
                        SELECT * FROM memories 
                        WHERE content LIKE ? AND type = ?
                        ORDER BY importance DESC, last_accessed DESC
                        LIMIT ?
                        """,
                        (f"%{query}%", memory_type, limit),
                    )
                else:
                    cursor = conn.execute(
                        """
                        SELECT * FROM memories 
                        WHERE content LIKE ?
                        ORDER BY importance DESC, last_accessed DESC
                        LIMIT ?
                        """,
                        (f"%{query}%", limit),
                    )

                for row in cursor.fetchall():
                    memory = Memory(
                        id=row[0],
                        content=row[1],
                        memory_type=row[2],
                        entities=json.loads(row[3]) if row[3] else [],
                        importance=row[4],
                        created_at=row[5],
                        last_accessed=row[6],
                        access_count=row[7],
                    )
                    results.append(memory)

        except Exception as e:
            self.logger.error(f"Error searching memories: {e}")

        return results

    async def get_recent_memories(self, limit: int = 10) -> List[Memory]:
        """Get most recent memories"""
        results = []

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    SELECT * FROM memories 
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (limit,),
                )

                for row in cursor.fetchall():
                    memory = Memory(
                        id=row[0],
                        content=row[1],
                        memory_type=row[2],
                        entities=json.loads(row[3]) if row[3] else [],
                        importance=row[4],
                        created_at=row[5],
                        last_accessed=row[6],
                        access_count=row[7],
                    )
                    results.append(memory)

        except Exception as e:
            self.logger.error(f"Error getting recent memories: {e}")

        return results

    async def link_entities_to_memory(self, memory_id: str, entity_ids: List[str]):
        """Link entities to a memory"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "UPDATE memories SET entities = ? WHERE id = ?",
                    (json.dumps(entity_ids), memory_id),
                )
                conn.commit()
        except Exception as e:
            self.logger.error(f"Error linking entities: {e}")

    async def get_entity_context(
        self, entity_id: str, depth: int = 2
    ) -> Dict[str, Any]:
        """Get full context around an entity"""
        entity = await self.get_entity(entity_id)
        if not entity:
            return {}

        related = await self.get_related_entities(entity_id, max_depth=depth)

        context = {
            "entity": entity.to_dict(),
            "related_entities": [
                {"entity": e.to_dict(), "relation": r.to_dict()} for e, r in related
            ],
            "connections": len(related),
        }

        return context

    async def find_path(
        self,
        source_id: str,
        target_id: str,
        max_depth: int = 5,
    ) -> List[Tuple[Entity, Relation]]:
        """Find path between two entities using BFS"""
        if source_id == target_id:
            entity = await self.get_entity(source_id)
            return [(entity, None)] if entity else []

        visited = {source_id}
        queue = [(source_id, [])]

        while queue:
            current_id, path = queue.pop(0)

            if len(path) >= max_depth:
                continue

            related = await self.get_related_entities(current_id)

            for entity, relation in related:
                if entity.id == target_id:
                    return path + [(entity, relation)]

                if entity.id not in visited:
                    visited.add(entity.id)
                    queue.append((entity.id, path + [(entity, relation)]))

        return []

    async def get_important_entities(self, limit: int = 20) -> List[Entity]:
        """Get most important entities"""
        results = []

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    SELECT * FROM entities 
                    ORDER BY importance DESC, access_count DESC
                    LIMIT ?
                    """,
                    (limit,),
                )

                for row in cursor.fetchall():
                    entity = Entity(
                        id=row[0],
                        entity_type=EntityType(row[1]),
                        name=row[2],
                        properties=json.loads(row[3]) if row[3] else {},
                        created_at=row[4],
                        updated_at=row[5],
                        access_count=row[6],
                        importance=row[7],
                    )
                    results.append(entity)

        except Exception as e:
            self.logger.error(f"Error getting important entities: {e}")

        return results

    async def update_entity_importance(self, entity_id: str, delta: float):
        """Update entity importance"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    UPDATE entities 
                    SET importance = MIN(1.0, MAX(0.0, importance + ?)),
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (delta, time.time(), entity_id),
                )
                conn.commit()
        except Exception as e:
            self.logger.error(f"Error updating importance: {e}")

    async def consolidate_memories(self, older_than_days: int = 30):
        """Consolidate old memories (reduce importance of less accessed)"""
        cutoff_time = time.time() - (older_than_days * 86400)

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    UPDATE memories 
                    SET importance = importance * 0.8
                    WHERE created_at < ? AND access_count < 3
                    """,
                    (cutoff_time,),
                )

                conn.execute(
                    """
                    DELETE FROM memories 
                    WHERE created_at < ? AND importance < 0.1
                    """,
                    (cutoff_time,),
                )

                conn.commit()

        except Exception as e:
            self.logger.error(f"Error consolidating memories: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Get graph statistics"""
        stats = {
            "entities": 0,
            "relations": 0,
            "memories": 0,
            "entity_types": {},
            "relation_types": {},
        }

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM entities")
                stats["entities"] = cursor.fetchone()[0]

                cursor = conn.execute("SELECT COUNT(*) FROM relations")
                stats["relations"] = cursor.fetchone()[0]

                cursor = conn.execute("SELECT COUNT(*) FROM memories")
                stats["memories"] = cursor.fetchone()[0]

                cursor = conn.execute(
                    "SELECT type, COUNT(*) FROM entities GROUP BY type"
                )
                for row in cursor.fetchall():
                    stats["entity_types"][row[0]] = row[1]

                cursor = conn.execute(
                    "SELECT type, COUNT(*) FROM relations GROUP BY type"
                )
                for row in cursor.fetchall():
                    stats["relation_types"][row[0]] = row[1]

        except Exception as e:
            self.logger.error(f"Error getting stats: {e}")

        return stats

    async def export_graph(self) -> Dict[str, Any]:
        """Export entire graph as dict"""
        data = {
            "entities": [],
            "relations": [],
            "memories": [],
        }

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT * FROM entities")
                for row in cursor.fetchall():
                    data["entities"].append(
                        {
                            "id": row[0],
                            "type": row[1],
                            "name": row[2],
                            "properties": json.loads(row[3]) if row[3] else {},
                            "importance": row[7],
                        }
                    )

                cursor = conn.execute("SELECT * FROM relations")
                for row in cursor.fetchall():
                    data["relations"].append(
                        {
                            "id": row[0],
                            "source": row[1],
                            "target": row[2],
                            "type": row[3],
                            "weight": row[5],
                        }
                    )

                cursor = conn.execute("SELECT * FROM memories")
                for row in cursor.fetchall():
                    data["memories"].append(
                        {
                            "id": row[0],
                            "content": row[1],
                            "type": row[2],
                            "importance": row[4],
                        }
                    )

        except Exception as e:
            self.logger.error(f"Error exporting graph: {e}")

        return data

    async def clear(self):
        """Clear all data"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM entities")
                conn.execute("DELETE FROM relations")
                conn.execute("DELETE FROM memories")
                conn.commit()

            self._entity_cache.clear()
            self._relation_cache.clear()
            self._memory_cache.clear()

        except Exception as e:
            self.logger.error(f"Error clearing graph: {e}")

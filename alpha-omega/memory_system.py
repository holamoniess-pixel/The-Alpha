"""
Memory System - Unlimited hierarchical memory
Combines fast cache, vector database, and persistent storage
"""

import asyncio
import sqlite3
import json
import hashlib
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path

class MemorySystem:
    """
    Hierarchical memory system for unlimited storage
    """
    
    def __init__(self, cache_size_mb: int = 1000):
        self.cache_size_mb = cache_size_mb
        
        # Memory tiers
        self.hot_cache = {}  # In RAM cache
        self.sql_db = None  # SQLite for structured storage
        
        self.maintenance_running = False
        self.cache_size_limit = cache_size_mb * 1024 * 1024  # Convert to bytes
    
    async def initialize(self):
        """Initialize memory systems"""
        # Initialize SQL database
        Path("data").mkdir(exist_ok=True)
        self.sql_db = sqlite3.connect('data/memory.db')
        await self.create_tables()
    
    async def create_tables(self):
        """Create database tables"""
        cursor = self.sql_db.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY,
                content TEXT,
                timestamp DATETIME,
                type TEXT,
                priority INTEGER,
                access_count INTEGER DEFAULT 0,
                last_accessed DATETIME,
                hash TEXT UNIQUE
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY,
                user_input TEXT,
                ai_response TEXT,
                timestamp DATETIME,
                context TEXT
            )
        ''')
        
        self.sql_db.commit()
    
    async def store(self, content: str, memory_type: str = "general",
                   priority: int = 1):
        """Store a memory"""
        try:
            # Generate unique hash
            content_hash = hashlib.md5(content.encode()).hexdigest()
            
            # Store in hot cache
            cache_entry = {
                'content': content,
                'timestamp': datetime.now().isoformat(),
                'type': memory_type,
                'priority': priority
            }
            self.hot_cache[content_hash] = cache_entry
            
            # Store in SQL for structured queries
            cursor = self.sql_db.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO memories 
                (content, timestamp, type, priority, last_accessed, hash)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (content, datetime.now(), memory_type, priority, datetime.now(), content_hash))
            
            self.sql_db.commit()
            
            # Cleanup cache if needed
            await self.cleanup_cache()
            
        except Exception as e:
            print(f"Error storing memory: {e}")
    
    async def retrieve_context(self, query: str, limit: int = 5) -> str:
        """Retrieve relevant context for query"""
        try:
            # Search in hot cache first
            cache_results = []
            for content_hash, entry in self.hot_cache.items():
                if any(word in entry['content'].lower() for word in query.lower().split()):
                    cache_results.append(entry['content'])
            
            if cache_results:
                return "\n\n".join(cache_results[:limit])
            
            # Search SQL database
            cursor = self.sql_db.cursor()
            query_lower = f"%{query.lower()}%"
            
            cursor.execute('''
                SELECT content FROM memories 
                WHERE content LIKE ? OR type LIKE ?
                ORDER BY priority DESC, access_count DESC
                LIMIT ?
            ''', (query_lower, query_lower, limit))
            
            results = cursor.fetchall()
            if results:
                # Update access count
                for result in results:
                    await self.update_access_count(result[0])
                
                return "\n\n".join([result[0] for result in results])
            
            return ""
            
        except Exception as e:
            print(f"Error retrieving context: {e}")
            return ""
    
    async def store_conversation(self, user_input: str, ai_response: str, context: str = ""):
        """Store conversation history"""
        try:
            cursor = self.sql_db.cursor()
            cursor.execute('''
                INSERT INTO conversations (user_input, ai_response, timestamp, context)
                VALUES (?, ?, ?, ?)
            ''', (user_input, ai_response, datetime.now(), context))
            
            self.sql_db.commit()
        except Exception as e:
            print(f"Error storing conversation: {e}")
    
    async def get_conversation_history(self, limit: int = 10) -> List[Dict]:
        """Get recent conversation history"""
        try:
            cursor = self.sql_db.cursor()
            cursor.execute('''
                SELECT user_input, ai_response, timestamp 
                FROM conversations 
                ORDER BY timestamp DESC 
                LIMIT ?
            ''', (limit,))
            
            results = cursor.fetchall()
            return [
                {
                    'user_input': row[0],
                    'ai_response': row[1],
                    'timestamp': row[2]
                }
                for row in results
            ]
        except Exception as e:
            print(f"Error getting conversation history: {e}")
            return []
    
    async def search_memories(self, query: str, memory_type: str = None) -> List[Dict]:
        """Search memories by query and type"""
        try:
            cursor = self.sql_db.cursor()
            query_pattern = f"%{query.lower()}%"
            
            if memory_type:
                cursor.execute('''
                    SELECT content, timestamp, type, access_count 
                    FROM memories 
                    WHERE content LIKE ? AND type = ?
                    ORDER BY priority DESC, access_count DESC
                ''', (query_pattern, memory_type))
            else:
                cursor.execute('''
                    SELECT content, timestamp, type, access_count 
                    FROM memories 
                    WHERE content LIKE ?
                    ORDER BY priority DESC, access_count DESC
                ''', (query_pattern,))
            
            results = cursor.fetchall()
            return [
                {
                    'content': row[0],
                    'timestamp': row[1],
                    'type': row[2],
                    'access_count': row[3]
                }
                for row in results
            ]
        except Exception as e:
            print(f"Error searching memories: {e}")
            return []
    
    async def update_access_count(self, content: str):
        """Update access count for memory"""
        try:
            cursor = self.sql_db.cursor()
            cursor.execute('''
                UPDATE memories 
                SET access_count = access_count + 1, last_accessed = ?
                WHERE content = ?
            ''', (datetime.now(), content))
            
            self.sql_db.commit()
        except Exception as e:
            print(f"Error updating access count: {e}")
    
    async def cleanup_cache(self):
        """Clean up hot cache if it exceeds size limit"""
        try:
            # Simple size estimation
            total_size = 0
            for content_hash, entry in self.hot_cache.items():
                total_size += len(str(entry).encode())
            
            if total_size > self.cache_size_limit:
                # Remove oldest entries
                items_to_remove = len(self.hot_cache) // 2
                keys_to_remove = list(self.hot_cache.keys())[:items_to_remove]
                
                for key in keys_to_remove:
                    del self.hot_cache[key]
                    
        except Exception as e:
            print(f"Error cleaning cache: {e}")
    
    async def start_maintenance(self):
        """Background maintenance tasks"""
        self.maintenance_running = True
        
        while self.maintenance_running:
            try:
                # Cleanup old memories
                await self.cleanup_old_memories()
                
                # Optimize database
                await self.optimize_database()
                
                await asyncio.sleep(3600)  # Run every hour
                
            except Exception as e:
                print(f"Maintenance error: {e}")
    
    async def cleanup_old_memories(self):
        """Remove very old, low-priority memories"""
        try:
            cursor = self.sql_db.cursor()
            
            # Delete memories older than 90 days with priority 0
            cutoff_date = datetime.now() - timedelta(days=90)
            
            cursor.execute('''
                DELETE FROM memories
                WHERE timestamp < ? AND priority = 0
            ''', (cutoff_date,))
            
            self.sql_db.commit()
        except Exception as e:
            print(f"Error cleaning old memories: {e}")
    
    async def optimize_database(self):
        """Optimize database performance"""
        try:
            cursor = self.sql_db.cursor()
            cursor.execute('VACUUM')
            cursor.execute('ANALYZE')
            self.sql_db.commit()
        except Exception as e:
            print(f"Error optimizing database: {e}")
    
    async def get_memory_stats(self) -> Dict:
        """Get memory system statistics"""
        try:
            cursor = self.sql_db.cursor()
            
            # Total memories
            cursor.execute('SELECT COUNT(*) FROM memories')
            total_memories = cursor.fetchone()[0]
            
            # Total conversations
            cursor.execute('SELECT COUNT(*) FROM conversations')
            total_conversations = cursor.fetchone()[0]
            
            # Cache size
            cache_size = len(self.hot_cache)
            
            return {
                'total_memories': total_memories,
                'total_conversations': total_conversations,
                'cache_entries': cache_size,
                'maintenance_running': self.maintenance_running
            }
        except Exception as e:
            print(f"Error getting stats: {e}")
            return {}
    
    async def save_and_close(self):
        """Save and close memory systems"""
        self.maintenance_running = False
        if self.sql_db:
            self.sql_db.close()
        
        print("Memory system saved and closed")

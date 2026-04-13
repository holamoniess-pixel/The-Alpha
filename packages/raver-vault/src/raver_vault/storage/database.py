"""Database manager for RAVER Vault."""

import sqlite3
import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID

from raver_shared.schemas import VaultEntry


class DatabaseManager:
    """Manages SQLite database for vault storage."""
    
    def __init__(self, db_path: str = "raver_vault.db"):
        """Initialize database manager.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS vault_entries (
                    secret_id TEXT PRIMARY KEY,
                    service TEXT NOT NULL,
                    label TEXT NOT NULL,
                    owner_user_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    key_hash_sha256 TEXT NOT NULL,
                    ciphertext_b64 TEXT NOT NULL,
                    nonce_b64 TEXT NOT NULL,
                    kdf_params TEXT NOT NULL,
                    access_policy TEXT NOT NULL
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_service ON vault_entries(service)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_owner ON vault_entries(owner_user_id)
            """)
            
            conn.commit()
    
    def store_secret(self, entry: VaultEntry) -> bool:
        """Store encrypted secret in database.
        
        Args:
            entry: Vault entry to store
            
        Returns:
            True if successful
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO vault_entries 
                    (secret_id, service, label, owner_user_id, created_at, updated_at,
                     key_hash_sha256, ciphertext_b64, nonce_b64, kdf_params, access_policy)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    str(entry.secret_id),
                    entry.service,
                    entry.label,
                    str(entry.owner_user_id),
                    entry.created_at.isoformat(),
                    entry.updated_at.isoformat(),
                    entry.key_hash_sha256,
                    entry.ciphertext_b64,
                    entry.nonce_b64,
                    json.dumps(entry.kdf_params),
                    json.dumps(entry.access_policy)
                ))
                conn.commit()
                return True
        except Exception:
            return False
    
    def get_secret(self, secret_id: UUID) -> Optional[VaultEntry]:
        """Retrieve secret from database.
        
        Args:
            secret_id: UUID of secret to retrieve
            
        Returns:
            Vault entry if found, None otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    "SELECT * FROM vault_entries WHERE secret_id = ?",
                    (str(secret_id),)
                )
                row = cursor.fetchone()
                
                if row:
                    return VaultEntry(
                        secret_id=UUID(row["secret_id"]),
                        service=row["service"],
                        label=row["label"],
                        owner_user_id=UUID(row["owner_user_id"]),
                        created_at=datetime.fromisoformat(row["created_at"]),
                        updated_at=datetime.fromisoformat(row["updated_at"]),
                        key_hash_sha256=row["key_hash_sha256"],
                        ciphertext_b64=row["ciphertext_b64"],
                        nonce_b64=row["nonce_b64"],
                        kdf_params=json.loads(row["kdf_params"]),
                        access_policy=json.loads(row["access_policy"])
                    )
                return None
        except Exception:
            return None
    
    def list_user_secrets(self, user_id: UUID) -> List[VaultEntry]:
        """List all secrets for a user.
        
        Args:
            user_id: User UUID
            
        Returns:
            List of vault entries
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    "SELECT * FROM vault_entries WHERE owner_user_id = ? ORDER BY created_at DESC",
                    (str(user_id),)
                )
                
                entries = []
                for row in cursor.fetchall():
                    entries.append(VaultEntry(
                        secret_id=UUID(row["secret_id"]),
                        service=row["service"],
                        label=row["label"],
                        owner_user_id=UUID(row["owner_user_id"]),
                        created_at=datetime.fromisoformat(row["created_at"]),
                        updated_at=datetime.fromisoformat(row["updated_at"]),
                        key_hash_sha256=row["key_hash_sha256"],
                        ciphertext_b64=row["ciphertext_b64"],
                        nonce_b64=row["nonce_b64"],
                        kdf_params=json.loads(row["kdf_params"]),
                        access_policy=json.loads(row["access_policy"])
                    ))
                return entries
        except Exception:
            return []
    
    def delete_secret(self, secret_id: UUID) -> bool:
        """Delete secret from database.
        
        Args:
            secret_id: UUID of secret to delete
            
        Returns:
            True if successful
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "DELETE FROM vault_entries WHERE secret_id = ?",
                    (str(secret_id),)
                )
                conn.commit()
                return cursor.rowcount > 0
        except Exception:
            return False
    
    def search_secrets(self, user_id: UUID, query: str) -> List[VaultEntry]:
        """Search secrets by service or label.
        
        Args:
            user_id: User UUID
            query: Search query
            
        Returns:
            List of matching vault entries
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    """SELECT * FROM vault_entries 
                       WHERE owner_user_id = ? AND 
                       (service LIKE ? OR label LIKE ?) 
                       ORDER BY created_at DESC""",
                    (str(user_id), f"%{query}%", f"%{query}%")
                )
                
                entries = []
                for row in cursor.fetchall():
                    entries.append(VaultEntry(
                        secret_id=UUID(row["secret_id"]),
                        service=row["service"],
                        label=row["label"],
                        owner_user_id=UUID(row["owner_user_id"]),
                        created_at=datetime.fromisoformat(row["created_at"]),
                        updated_at=datetime.fromisoformat(row["updated_at"]),
                        key_hash_sha256=row["key_hash_sha256"],
                        ciphertext_b64=row["ciphertext_b64"],
                        nonce_b64=row["nonce_b64"],
                        kdf_params=json.loads(row["kdf_params"]),
                        access_policy=json.loads(row["access_policy"])
                    ))
                return entries
        except Exception:
            return []

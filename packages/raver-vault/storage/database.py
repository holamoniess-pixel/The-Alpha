"""
Database storage for encrypted secrets.
"""

import sqlite3
import json
import aiosqlite
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path

from ..raver_shared.schemas import VaultSecret


class SecretStorage:
    """SQLite-based storage for vault secrets."""
    
    def __init__(self, db_path: str = "raver_vault.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS vault_secrets (
                    secret_id TEXT PRIMARY KEY,
                    service TEXT NOT NULL,
                    label TEXT NOT NULL,
                    owner_user_id TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL,
                    key_hash_sha256 TEXT NOT NULL,
                    ciphertext_b64 TEXT NOT NULL,
                    nonce_b64 TEXT NOT NULL,
                    kdf_params TEXT NOT NULL,
                    access_policy TEXT NOT NULL
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS vault_users (
                    user_id TEXT PRIMARY KEY,
                    username TEXT NOT NULL,
                    roles TEXT NOT NULL,
                    voiceprint_id TEXT,
                    created_at TIMESTAMP NOT NULL,
                    last_active TIMESTAMP NOT NULL
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS vault_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)
            
            # Insert vault version
            conn.execute("""
                INSERT OR IGNORE INTO vault_metadata (key, value) 
                VALUES ('vault_version', '1.0')
            """)
            
            conn.commit()
    
    async def store_secret(self, secret: VaultSecret) -> bool:
        """Store a secret in the vault."""
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                await conn.execute("""
                    INSERT OR REPLACE INTO vault_secrets 
                    (secret_id, service, label, owner_user_id, created_at, updated_at,
                     key_hash_sha256, ciphertext_b64, nonce_b64, kdf_params, access_policy)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    secret.secret_id,
                    secret.service,
                    secret.label,
                    secret.owner_user_id,
                    secret.created_at.isoformat(),
                    secret.updated_at.isoformat(),
                    secret.key_hash_sha256,
                    secret.ciphertext_b64,
                    secret.nonce_b64,
                    json.dumps(secret.kdf_params),
                    json.dumps(secret.access_policy)
                ))
                await conn.commit()
                return True
        except Exception as e:
            print(f"Error storing secret: {e}")
            return False
    
    async def get_secret(self, secret_id: str) -> Optional[VaultSecret]:
        """Retrieve a secret by ID."""
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                conn.row_factory = aiosqlite.Row
                cursor = await conn.execute("""
                    SELECT * FROM vault_secrets WHERE secret_id = ?
                """, (secret_id,))
                row = await cursor.fetchone()
                
                if row:
                    return VaultSecret(
                        secret_id=row["secret_id"],
                        service=row["service"],
                        label=row["label"],
                        owner_user_id=row["owner_user_id"],
                        created_at=datetime.fromisoformat(row["created_at"]),
                        updated_at=datetime.fromisoformat(row["updated_at"]),
                        key_hash_sha256=row["key_hash_sha256"],
                        ciphertext_b64=row["ciphertext_b64"],
                        nonce_b64=row["nonce_b64"],
                        kdf_params=json.loads(row["kdf_params"]),
                        access_policy=json.loads(row["access_policy"])
                    )
                return None
        except Exception as e:
            print(f"Error retrieving secret: {e}")
            return None
    
    async def list_secrets(self, user_id: str) -> List[VaultSecret]:
        """List all secrets for a user."""
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                conn.row_factory = aiosqlite.Row
                cursor = await conn.execute("""
                    SELECT * FROM vault_secrets WHERE owner_user_id = ?
                    ORDER BY updated_at DESC
                """, (user_id,))
                rows = await cursor.fetchall()
                
                secrets = []
                for row in rows:
                    secrets.append(VaultSecret(
                        secret_id=row["secret_id"],
                        service=row["service"],
                        label=row["label"],
                        owner_user_id=row["owner_user_id"],
                        created_at=datetime.fromisoformat(row["created_at"]),
                        updated_at=datetime.fromisoformat(row["updated_at"]),
                        key_hash_sha256=row["key_hash_sha256"],
                        ciphertext_b64=row["ciphertext_b64"],
                        nonce_b64=row["nonce_b64"],
                        kdf_params=json.loads(row["kdf_params"]),
                        access_policy=json.loads(row["access_policy"])
                    ))
                return secrets
        except Exception as e:
            print(f"Error listing secrets: {e}")
            return []
    
    async def delete_secret(self, secret_id: str) -> bool:
        """Delete a secret from the vault."""
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                cursor = await conn.execute("""
                    DELETE FROM vault_secrets WHERE secret_id = ?
                """, (secret_id,))
                await conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            print(f"Error deleting secret: {e}")
            return False
    
    async def update_secret(self, secret: VaultSecret) -> bool:
        """Update an existing secret."""
        secret.updated_at = datetime.now()
        return await self.store_secret(secret)
    
    async def get_vault_metadata(self, key: str) -> Optional[str]:
        """Get vault metadata value."""
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                cursor = await conn.execute("""
                    SELECT value FROM vault_metadata WHERE key = ?
                """, (key,))
                row = await cursor.fetchone()
                return row[0] if row else None
        except Exception as e:
            print(f"Error getting metadata: {e}")
            return None
    
    async def set_vault_metadata(self, key: str, value: str) -> bool:
        """Set vault metadata value."""
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                await conn.execute("""
                    INSERT OR REPLACE INTO vault_metadata (key, value) VALUES (?, ?)
                """, (key, value))
                await conn.commit()
                return True
        except Exception as e:
            print(f"Error setting metadata: {e}")
            return False

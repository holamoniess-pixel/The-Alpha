"""
RAVER Vault Storage Module

Provides SQLite-based storage for encrypted secrets with metadata
and access control information.
"""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import uuid


@dataclass
class SecretEntry:
    """Represents a secret stored in the vault."""
    secret_id: str
    service: str
    label: str
    owner_user_id: str
    created_at: datetime
    updated_at: datetime
    key_hash_sha256: str
    ciphertext_b64: str
    nonce_b64: str
    kdf_params: Dict[str, Any]
    access_policy: Dict[str, Any]
    tags: List[str] = None
    description: str = ""
    is_deleted: bool = False
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        
        # Ensure datetime objects have timezone info
        if self.created_at.tzinfo is None:
            self.created_at = self.created_at.replace(tzinfo=timezone.utc)
        if self.updated_at.tzinfo is None:
            self.updated_at = self.updated_at.replace(tzinfo=timezone.utc)


class SecretStorage:
    """SQLite-based storage for vault secrets."""
    
    def __init__(self, vault_path: Optional[Path] = None):
        if vault_path is None:
            vault_path = Path.home() / ".raver" / "vault"
        
        self.vault_path = vault_path
        self.vault_path.mkdir(parents=True, exist_ok=True)
        self.db_path = self.vault_path / "secrets.db"
        
        self._initialize_database()
    
    def _initialize_database(self):
        """Initialize the secrets database."""
        with sqlite3.connect(self.db_path) as conn:
            # Create secrets table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS secrets (
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
                    access_policy TEXT NOT NULL,
                    tags TEXT,
                    description TEXT DEFAULT '',
                    is_deleted BOOLEAN DEFAULT FALSE
                )
            """)
            
            # Create indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_service ON secrets(service)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_owner ON secrets(owner_user_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_label ON secrets(label)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON secrets(created_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_is_deleted ON secrets(is_deleted)")
            
            # Create access logs table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS access_logs (
                    log_id TEXT PRIMARY KEY,
                    secret_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    ip_address TEXT,
                    user_agent TEXT,
                    success BOOLEAN NOT NULL,
                    reason TEXT,
                    FOREIGN KEY (secret_id) REFERENCES secrets (secret_id)
                )
            """)
            
            conn.execute("CREATE INDEX IF NOT EXISTS idx_access_secret_id ON access_logs(secret_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_access_user_id ON access_logs(user_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_access_timestamp ON access_logs(timestamp)")
            
            conn.commit()
    
    def store_secret(self, secret: SecretEntry) -> bool:
        """Store a new secret in the vault."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO secrets 
                    (secret_id, service, label, owner_user_id, created_at, updated_at,
                     key_hash_sha256, ciphertext_b64, nonce_b64, kdf_params, access_policy,
                     tags, description, is_deleted)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    json.dumps(secret.access_policy),
                    json.dumps(secret.tags),
                    secret.description,
                    secret.is_deleted
                ))
                conn.commit()
                return True
        except Exception:
            return False
    
    def get_secret(self, secret_id: str, include_deleted: bool = False) -> Optional[SecretEntry]:
        """Retrieve a secret by ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            query = "SELECT * FROM secrets WHERE secret_id = ?"
            params = [secret_id]
            
            if not include_deleted:
                query += " AND is_deleted = FALSE"
            
            cursor = conn.execute(query, params)
            row = cursor.fetchone()
            
            if row:
                return self._row_to_secret(row)
            return None
    
    def list_secrets(self,
                    user_id: Optional[str] = None,
                    service: Optional[str] = None,
                    tags: Optional[List[str]] = None,
                    include_deleted: bool = False,
                    limit: int = 1000) -> List[SecretEntry]:
        """List secrets with optional filters."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            query = "SELECT * FROM secrets WHERE 1=1"
            params = []
            
            if user_id:
                query += " AND owner_user_id = ?"
                params.append(user_id)
            
            if service:
                query += " AND service = ?"
                params.append(service)
            
            if tags:
                for tag in tags:
                    query += " AND tags LIKE ?"
                    params.append(f'%"{tag}"%')
            
            if not include_deleted:
                query += " AND is_deleted = FALSE"
            
            query += " ORDER BY updated_at DESC LIMIT ?"
            params.append(limit)
            
            cursor = conn.execute(query, params)
            secrets = []
            
            for row in cursor.fetchall():
                secrets.append(self._row_to_secret(row))
            
            return secrets
    
    def update_secret(self, secret_id: str, updates: Dict[str, Any]) -> bool:
        """Update a secret's metadata."""
        if not updates:
            return False
        
        # Always update the updated_at timestamp
        updates["updated_at"] = datetime.utcnow().isoformat()
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Build dynamic update query
                set_clauses = []
                params = []
                
                for key, value in updates.items():
                    if key in ["service", "label", "description", "ciphertext_b64", "nonce_b64", "key_hash_sha256"]:
                        set_clauses.append(f"{key} = ?")
                        params.append(value)
                    elif key in ["kdf_params", "access_policy", "tags"]:
                        set_clauses.append(f"{key} = ?")
                        params.append(json.dumps(value))
                    elif key == "updated_at":
                        set_clauses.append("updated_at = ?")
                        params.append(value)
                
                if set_clauses:
                    query = f"UPDATE secrets SET {', '.join(set_clauses)} WHERE secret_id = ?"
                    params.append(secret_id)
                    conn.execute(query, params)
                    conn.commit()
                    return True
                
            return False
        except Exception:
            return False
    
    def delete_secret(self, secret_id: str, user_id: str, permanent: bool = False) -> bool:
        """Delete a secret (soft delete by default)."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                if permanent:
                    conn.execute("DELETE FROM secrets WHERE secret_id = ? AND owner_user_id = ?", 
                               (secret_id, user_id))
                else:
                    conn.execute("""
                        UPDATE secrets 
                        SET is_deleted = TRUE, updated_at = ? 
                        WHERE secret_id = ? AND owner_user_id = ?
                    """, (datetime.utcnow().isoformat(), secret_id, user_id))
                conn.commit()
                return True
        except Exception:
            return False
    
    def search_secrets(self, query: str, user_id: Optional[str] = None) -> List[SecretEntry]:
        """Search secrets by label, description, or service."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            sql_query = """
                SELECT * FROM secrets 
                WHERE is_deleted = FALSE 
                AND (label LIKE ? OR description LIKE ? OR service LIKE ?)
            """
            params = [f"%{query}%", f"%{query}%", f"%{query}%"]
            
            if user_id:
                sql_query += " AND owner_user_id = ?"
                params.append(user_id)
            
            sql_query += " ORDER BY updated_at DESC LIMIT 100"
            
            cursor = conn.execute(sql_query, params)
            secrets = []
            
            for row in cursor.fetchall():
                secrets.append(self._row_to_secret(row))
            
            return secrets
    
    def log_access(self, secret_id: str, user_id: str, action: str, 
                   success: bool, reason: Optional[str] = None,
                   ip_address: Optional[str] = None,
                   user_agent: Optional[str] = None) -> bool:
        """Log access to a secret."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO access_logs 
                    (log_id, secret_id, user_id, action, timestamp, ip_address, user_agent, success, reason)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    str(uuid.uuid4()),
                    secret_id,
                    user_id,
                    action,
                    datetime.utcnow().isoformat(),
                    ip_address,
                    user_agent,
                    success,
                    reason
                ))
                conn.commit()
                return True
        except Exception:
            return False
    
    def get_access_logs(self, secret_id: Optional[str] = None,
                       user_id: Optional[str] = None,
                       limit: int = 1000) -> List[Dict[str, Any]]:
        """Get access logs with optional filters."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            query = "SELECT * FROM access_logs WHERE 1=1"
            params = []
            
            if secret_id:
                query += " AND secret_id = ?"
                params.append(secret_id)
            
            if user_id:
                query += " AND user_id = ?"
                params.append(user_id)
            
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            cursor = conn.execute(query, params)
            logs = []
            
            for row in cursor.fetchall():
                logs.append(dict(row))
            
            return logs
    
    def get_statistics(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Get vault statistics."""
        with sqlite3.connect(self.db_path) as conn:
            # Total secrets
            query = "SELECT COUNT(*) FROM secrets WHERE is_deleted = FALSE"
            params = []
            if user_id:
                query += " AND owner_user_id = ?"
                params.append(user_id)
            
            cursor = conn.execute(query, params)
            total_secrets = cursor.fetchone()[0]
            
            # Secrets by service
            query = "SELECT service, COUNT(*) FROM secrets WHERE is_deleted = FALSE"
            params = []
            if user_id:
                query += " AND owner_user_id = ?"
                params.append(user_id)
            query += " GROUP BY service"
            
            cursor = conn.execute(query, params)
            secrets_by_service = dict(cursor.fetchall())
            
            # Recent activity
            query = "SELECT COUNT(*) FROM access_logs WHERE timestamp > datetime('now', '-7 days')"
            params = []
            if user_id:
                query += " AND user_id = ?"
                params.append(user_id)
            
            cursor = conn.execute(query, params)
            recent_access = cursor.fetchone()[0]
            
            return {
                "total_secrets": total_secrets,
                "secrets_by_service": secrets_by_service,
                "recent_access_count": recent_access
            }
    
    def _row_to_secret(self, row: sqlite3.Row) -> SecretEntry:
        """Convert a database row to a SecretEntry object."""
        return SecretEntry(
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
            access_policy=json.loads(row["access_policy"]),
            tags=json.loads(row["tags"]) if row["tags"] else [],
            description=row["description"] or "",
            is_deleted=bool(row["is_deleted"])
        )

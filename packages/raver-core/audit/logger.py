"""
Audit Logger - Tamper-evident logging for security events.
"""

import json
import hashlib
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict

from ...raver_shared.schemas import ActionRequest, PolicyDecision
from .models import AuditEvent


@dataclass
class AuditEntry:
    """Single audit log entry."""
    entry_id: str
    timestamp: datetime
    event_type: str
    user_id: str
    request_id: Optional[str]
    action_type: Optional[str]
    target_resource: Optional[str]
    details: Dict[str, Any]
    hash_value: str
    previous_hash: Optional[str]


class AuditLogger:
    """Tamper-evident audit logging system."""
    
    def __init__(self, db_path: str = "raver_audit.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
        self._last_hash: Optional[str] = None
    
    def _init_database(self):
        """Initialize audit database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    entry_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    request_id TEXT,
                    action_type TEXT,
                    target_resource TEXT,
                    details TEXT NOT NULL,
                    hash_value TEXT NOT NULL,
                    previous_hash TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)
            
            # Initialize metadata
            conn.execute("""
                INSERT OR IGNORE INTO audit_metadata (key, value) 
                VALUES ('log_initialized', ?)
            """, (datetime.now().isoformat(),))
            
            conn.execute("""
                INSERT OR IGNORE INTO audit_metadata (key, value) 
                VALUES ('log_version', '1.0')
            """, (datetime.now().isoformat(),))
            
            conn.commit()
    
    async def initialize(self):
        """Initialize the audit logger."""
        # Get the last hash from database
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT hash_value FROM audit_log 
                ORDER BY timestamp DESC LIMIT 1
            """)
            row = cursor.fetchone()
            self._last_hash = row[0] if row else None
    
    async def cleanup(self):
        """Cleanup audit logger resources."""
        pass
    
    async def get_status(self) -> Dict[str, Any]:
        """Get audit logger status."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM audit_log")
            entry_count = cursor.fetchone()[0]
            
            cursor = conn.execute("""
                SELECT value FROM audit_metadata WHERE key = 'log_initialized'
            """)
            init_time = cursor.fetchone()
            
            return {
                "initialized": True,
                "entry_count": entry_count,
                "initialized_at": init_time[0] if init_time else None,
                "last_hash": self._last_hash[:16] + "..." if self._last_hash else None
            }
    
    async def log_request(self, request: ActionRequest, decision: PolicyDecision):
        """Log an action request and its policy decision."""
        await self._log_event(
            event_type="action_request",
            user_id=request.user_id,
            request_id=request.request_id,
            action_type=request.action_type.value,
            target_resource=request.target_resource,
            details={
                "request_parameters": request.parameters,
                "request_context": request.context,
                "policy_decision": {
                    "approved": decision.approved,
                    "risk_level": decision.risk_score.level.value,
                    "risk_score": decision.risk_score.score,
                    "approval_method": decision.approval_method.value,
                    "reason": decision.reason,
                    "rule_applied": decision.rule_applied
                }
            }
        )
    
    async def log_execution(self, request: ActionRequest, result: Dict[str, Any]):
        """Log the execution of an approved action."""
        await self._log_event(
            event_type="action_execution",
            user_id=request.user_id,
            request_id=request.request_id,
            action_type=request.action_type.value,
            target_resource=request.target_resource,
            details={
                "execution_result": result,
                "execution_time": datetime.now().isoformat()
            }
        )
    
    async def log_denial(self, request: ActionRequest, decision: PolicyDecision):
        """Log a denied action request."""
        await self._log_event(
            event_type="action_denied",
            user_id=request.user_id,
            request_id=request.request_id,
            action_type=request.action_type.value,
            target_resource=request.target_resource,
            details={
                "denial_reason": decision.reason,
                "risk_level": decision.risk_score.level.value,
                "risk_score": decision.risk_score.score,
                "rule_applied": decision.rule_applied
            }
        )
    
    async def log_cancellation(self, request: ActionRequest, reason: str):
        """Log a cancelled action request."""
        await self._log_event(
            event_type="action_cancelled",
            user_id=request.user_id,
            request_id=request.request_id,
            action_type=request.action_type.value,
            target_resource=request.target_resource,
            details={
                "cancellation_reason": reason,
                "cancelled_at": datetime.now().isoformat()
            }
        )
    
    async def log_system_pause(self, pause_request):
        """Log system pause event."""
        await self._log_event(
            event_type="system_pause",
            user_id=pause_request.user_id,
            request_id=None,
            action_type=None,
            target_resource=None,
            details={
                "pause_reason": pause_request.reason,
                "pause_timestamp": pause_request.timestamp.isoformat()
            }
        )
    
    async def log_system_resume(self, user_id: str):
        """Log system resume event."""
        await self._log_event(
            event_type="system_resume",
            user_id=user_id,
            request_id=None,
            action_type=None,
            target_resource=None,
            details={
                "resume_timestamp": datetime.now().isoformat()
            }
        )
    
    async def log_security_event(self, event_type: str, user_id: str, 
                                 details: Dict[str, Any]):
        """Log a security-related event."""
        await self._log_event(
            event_type=f"security_{event_type}",
            user_id=user_id,
            request_id=None,
            action_type=None,
            target_resource=None,
            details=details
        )
    
    async def get_audit_trail(self, user_id: Optional[str] = None,
                             event_type: Optional[str] = None,
                             limit: int = 100) -> List[Dict[str, Any]]:
        """Retrieve audit trail entries."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            query = "SELECT * FROM audit_log WHERE 1=1"
            params = []
            
            if user_id:
                query += " AND user_id = ?"
                params.append(user_id)
            
            if event_type:
                query += " AND event_type = ?"
                params.append(event_type)
            
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            
            return [dict(row) for row in rows]
    
    async def verify_integrity(self) -> Dict[str, Any]:
        """Verify the integrity of the audit log."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT entry_id, hash_value, previous_hash 
                FROM audit_log 
                ORDER BY timestamp ASC
            """)
            rows = cursor.fetchall()
            
        integrity_issues = []
        previous_hash = None
        
        for entry_id, hash_value, prev_hash in rows:
            # Verify chain integrity
            if prev_hash != previous_hash:
                integrity_issues.append({
                    "entry_id": entry_id,
                    "issue": "Hash chain broken",
                    "expected_previous": previous_hash,
                    "found_previous": prev_hash
                })
            
            # Verify entry hash
            entry_data = await self._get_entry_data(entry_id)
            calculated_hash = self._calculate_entry_hash(entry_data, previous_hash)
            
            if calculated_hash != hash_value:
                integrity_issues.append({
                    "entry_id": entry_id,
                    "issue": "Entry hash mismatch",
                    "expected": hash_value,
                    "calculated": calculated_hash
                })
            
            previous_hash = hash_value
        
        return {
            "verified": len(integrity_issues) == 0,
            "total_entries": len(rows),
            "issues": integrity_issues,
            "verification_time": datetime.now().isoformat()
        }
    
    async def _log_event(self, event_type: str, user_id: str,
                        request_id: Optional[str], action_type: Optional[str],
                        target_resource: Optional[str], details: Dict[str, Any]):
        """Log an event to the audit trail."""
        entry_id = f"{event_type}_{datetime.now().timestamp()}_{user_id}"
        timestamp = datetime.now()
        
        # Create entry
        entry = AuditEntry(
            entry_id=entry_id,
            timestamp=timestamp,
            event_type=event_type,
            user_id=user_id,
            request_id=request_id,
            action_type=action_type,
            target_resource=target_resource,
            details=details,
            hash_value="",  # Will be calculated
            previous_hash=self._last_hash
        )
        
        # Calculate hash
        entry.hash_value = self._calculate_entry_hash(entry, self._last_hash)
        
        # Store entry
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO audit_log 
                (entry_id, timestamp, event_type, user_id, request_id, 
                 action_type, target_resource, details, hash_value, previous_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                entry.entry_id,
                entry.timestamp.isoformat(),
                entry.event_type,
                entry.user_id,
                entry.request_id,
                entry.action_type,
                entry.target_resource,
                json.dumps(entry.details),
                entry.hash_value,
                entry.previous_hash
            ))
            conn.commit()
        
        # Update last hash
        self._last_hash = entry.hash_value
    
    def _calculate_entry_hash(self, entry: AuditEntry, previous_hash: Optional[str]) -> str:
        """Calculate hash for an audit entry."""
        # Create hash data
        hash_data = {
            "entry_id": entry.entry_id,
            "timestamp": entry.timestamp.isoformat(),
            "event_type": entry.event_type,
            "user_id": entry.user_id,
            "request_id": entry.request_id,
            "action_type": entry.action_type,
            "target_resource": entry.target_resource,
            "details": entry.details,
            "previous_hash": previous_hash
        }
        
        # Calculate SHA-256 hash
        hash_string = json.dumps(hash_data, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(hash_string.encode()).hexdigest()
    
    async def _get_entry_data(self, entry_id: str) -> Dict[str, Any]:
        """Get entry data for hash verification."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM audit_log WHERE entry_id = ?
            """, (entry_id,))
            row = cursor.fetchone()
            
            if row:
                return {
                    "entry_id": row["entry_id"],
                    "timestamp": row["timestamp"],
                    "event_type": row["event_type"],
                    "user_id": row["user_id"],
                    "request_id": row["request_id"],
                    "action_type": row["action_type"],
                    "target_resource": row["target_resource"],
                    "details": json.loads(row["details"]),
                    "previous_hash": row["previous_hash"]
                }
            return {}

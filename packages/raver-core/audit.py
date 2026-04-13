"""
RAVER Audit Logger

Provides tamper-evident, append-only logging for all system operations.
Ensures accountability and forensic capabilities for security auditing.
"""

import asyncio
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import threading
import uuid


class EventType(Enum):
    """Types of audit events."""
    INTENT_RECEIVED = "intent_received"
    POLICY_DENIED = "policy_denied"
    APPROVAL_REQUIRED = "approval_required"
    APPROVAL_GRANTED = "approval_granted"
    APPROVAL_DENIED = "approval_denied"
    ACTION_EXECUTED = "action_executed"
    ACTION_FAILED = "action_failed"
    SYSTEM_ERROR = "system_error"
    SYSTEM_PAUSED = "system_paused"
    SYSTEM_RESUMED = "system_resumed"
    SYSTEM_SHUTDOWN = "system_shutdown"
    VAULT_ACCESS = "vault_access"
    SECURITY_ALERT = "security_alert"
    NETWORK_ACTIVITY = "network_activity"
    USER_AUTHENTICATION = "user_authentication"


@dataclass
class AuditEvent:
    """Represents an audit log entry."""
    event_id: str
    event_type: EventType
    timestamp: datetime
    description: str
    user_id: str
    metadata: Dict[str, Any]
    session_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    severity: str = "INFO"  # INFO, WARNING, ERROR, CRITICAL
    
    def __post_init__(self):
        """Generate event_id if not provided."""
        if not self.event_id:
            self.event_id = str(uuid.uuid4())
        
        # Ensure timestamp is in UTC
        if self.timestamp.tzinfo is None:
            self.timestamp = self.timestamp.replace(tzinfo=timezone.utc)


class AuditLogger:
    """Tamper-evident audit logging system."""
    
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            db_path = Path.home() / ".raver" / "audit.db"
        
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._lock = threading.Lock()
        self._initialize_database()
    
    def _initialize_database(self):
        """Initialize the audit database with tamper-evident features."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT UNIQUE NOT NULL,
                    event_type TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    description TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    metadata TEXT NOT NULL,
                    session_id TEXT,
                    ip_address TEXT,
                    user_agent TEXT,
                    severity TEXT NOT NULL,
                    hash_chain TEXT NOT NULL,
                    previous_hash TEXT,
                    created_at TEXT NOT NULL
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp ON audit_events(timestamp)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_id ON audit_events(user_id)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_event_type ON audit_events(event_type)
            """)
            
            conn.commit()
    
    async def log_event(self, event: AuditEvent):
        """Log an audit event with tamper protection."""
        # Serialize event data
        event_data = {
            "event_id": event.event_id,
            "event_type": event.event_type.value,
            "timestamp": event.timestamp.isoformat(),
            "description": event.description,
            "user_id": event.user_id,
            "metadata": event.metadata,
            "session_id": event.session_id,
            "ip_address": event.ip_address,
            "user_agent": event.user_agent,
            "severity": event.severity
        }
        
        # Get previous hash for chain integrity
        previous_hash = self._get_previous_hash()
        
        # Calculate hash for this event
        event_hash = self._calculate_event_hash(event_data, previous_hash)
        
        with self._lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("""
                        INSERT INTO audit_events 
                        (event_id, event_type, timestamp, description, user_id, metadata,
                         session_id, ip_address, user_agent, severity, hash_chain, previous_hash, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        event.event_id,
                        event.event_type.value,
                        event.timestamp.isoformat(),
                        event.description,
                        event.user_id,
                        json.dumps(event.metadata),
                        event.session_id,
                        event.ip_address,
                        event.user_agent,
                        event.severity,
                        event_hash,
                        previous_hash,
                        datetime.utcnow().isoformat()
                    ))
                    conn.commit()
            except sqlite3.IntegrityError as e:
                # Log integrity violations to system log
                print(f"AUDIT INTEGRITY VIOLATION: {e}")
                raise
    
    def _get_previous_hash(self) -> str:
        """Get the hash of the most recent event."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT hash_chain FROM audit_events 
                ORDER BY id DESC LIMIT 1
            """)
            result = cursor.fetchone()
            return result[0] if result else ""
    
    def _calculate_event_hash(self, event_data: Dict[str, Any], previous_hash: str) -> str:
        """Calculate SHA-256 hash of event data plus previous hash."""
        # Create deterministic string representation
        hash_input = json.dumps(event_data, sort_keys=True, separators=(',', ':'))
        hash_input += previous_hash
        
        return hashlib.sha256(hash_input.encode()).hexdigest()
    
    def verify_integrity(self) -> Dict[str, Any]:
        """Verify the integrity of the audit log."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT id, event_id, hash_chain, previous_hash, metadata
                FROM audit_events 
                ORDER BY id ASC
            """)
            events = cursor.fetchall()
        
        if not events:
            return {"valid": True, "message": "No events to verify"}
        
        violations = []
        previous_hash = ""
        
        for i, (event_id, hash_chain, prev_hash, metadata) in enumerate(events):
            # Check previous hash consistency
            if i == 0:
                if prev_hash != "":
                    violations.append(f"First event has non-empty previous hash: {event_id}")
            else:
                if prev_hash != previous_hash:
                    violations.append(f"Hash chain broken at event: {event_id}")
            
            # Recalculate and verify hash
            event_data = json.loads(metadata)
            event_data["event_id"] = event_id
            calculated_hash = self._calculate_event_hash(event_data, previous_hash)
            
            if calculated_hash != hash_chain:
                violations.append(f"Hash mismatch for event: {event_id}")
            
            previous_hash = hash_chain
        
        return {
            "valid": len(violations) == 0,
            "violations": violations,
            "total_events": len(events)
        }
    
    async def query_events(self,
                          start_time: Optional[datetime] = None,
                          end_time: Optional[datetime] = None,
                          user_id: Optional[str] = None,
                          event_type: Optional[EventType] = None,
                          severity: Optional[str] = None,
                          limit: int = 1000) -> List[Dict[str, Any]]:
        """Query audit events with filters."""
        query = "SELECT * FROM audit_events WHERE 1=1"
        params = []
        
        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time.isoformat())
        
        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time.isoformat())
        
        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)
        
        if event_type:
            query += " AND event_type = ?"
            params.append(event_type.value)
        
        if severity:
            query += " AND severity = ?"
            params.append(severity)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            events = []
            
            for row in cursor.fetchall():
                event = dict(row)
                event['metadata'] = json.loads(event['metadata'])
                events.append(event)
            
            return events
    
    async def get_user_activity_summary(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """Get activity summary for a specific user."""
        start_time = datetime.utcnow() - timedelta(days=days)
        
        events = await self.query_events(
            start_time=start_time,
            user_id=user_id,
            limit=10000
        )
        
        # Count by event type
        event_counts = {}
        severity_counts = {}
        daily_activity = {}
        
        for event in events:
            # Count by type
            event_type = event['event_type']
            event_counts[event_type] = event_counts.get(event_type, 0) + 1
            
            # Count by severity
            severity = event['severity']
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
            
            # Daily activity
            date = event['timestamp'][:10]  # YYYY-MM-DD
            daily_activity[date] = daily_activity.get(date, 0) + 1
        
        return {
            "user_id": user_id,
            "period_days": days,
            "total_events": len(events),
            "event_counts": event_counts,
            "severity_counts": severity_counts,
            "daily_activity": daily_activity,
            "last_activity": events[0]['timestamp'] if events else None
        }
    
    async def export_events(self,
                           start_time: Optional[datetime] = None,
                           end_time: Optional[datetime] = None,
                           format: str = "json") -> str:
        """Export audit events in specified format."""
        events = await self.query_events(
            start_time=start_time,
            end_time=end_time,
            limit=100000
        )
        
        if format.lower() == "json":
            return json.dumps(events, indent=2, default=str)
        elif format.lower() == "csv":
            import csv
            import io
            
            output = io.StringIO()
            if events:
                writer = csv.DictWriter(output, fieldnames=events[0].keys())
                writer.writeheader()
                for event in events:
                    # Flatten metadata for CSV
                    flat_event = event.copy()
                    flat_event['metadata'] = json.dumps(event['metadata'])
                    writer.writerow(flat_event)
            
            return output.getvalue()
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get audit log statistics."""
        with sqlite3.connect(self.db_path) as conn:
            # Total events
            cursor = conn.execute("SELECT COUNT(*) FROM audit_events")
            total_events = cursor.fetchone()[0]
            
            # Events by type
            cursor = conn.execute("""
                SELECT event_type, COUNT(*) 
                FROM audit_events 
                GROUP BY event_type
            """)
            events_by_type = dict(cursor.fetchall())
            
            # Events by severity
            cursor = conn.execute("""
                SELECT severity, COUNT(*) 
                FROM audit_events 
                GROUP BY severity
            """)
            events_by_severity = dict(cursor.fetchall())
            
            # Date range
            cursor = conn.execute("""
                SELECT MIN(timestamp), MAX(timestamp) 
                FROM audit_events
            """)
            date_range = cursor.fetchone()
            
            return {
                "total_events": total_events,
                "events_by_type": events_by_type,
                "events_by_severity": events_by_severity,
                "date_range": {
                    "earliest": date_range[0],
                    "latest": date_range[1]
                },
                "integrity_check": self.verify_integrity()
            }

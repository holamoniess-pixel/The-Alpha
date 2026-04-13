"""Tamper-evident audit logger for RAVER."""

import asyncio
import hashlib
import json
import os
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID
import aiofiles

from raver_shared.schemas import AuditEvent, RiskLevel


class AuditLogger:
    """Tamper-evident audit logging system."""
    
    def __init__(self, log_dir: str = "audit_logs"):
        """Initialize audit logger.
        
        Args:
            log_dir: Directory to store audit logs
        """
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        self.current_log_file = self._get_current_log_file()
        self._lock = asyncio.Lock()
    
    def _get_current_log_file(self) -> str:
        """Get current log file path based on date."""
        date_str = datetime.utcnow().strftime("%Y-%m-%d")
        return os.path.join(self.log_dir, f"audit_{date_str}.log")
    
    def _calculate_hash(self, data: str, previous_hash: str = "") -> str:
        """Calculate chain hash for tamper evidence.
        
        Args:
            data: Data to hash
            previous_hash: Previous hash in chain
            
        Returns:
            SHA-256 hash
        """
        combined = f"{previous_hash}{data}"
        return hashlib.sha256(combined.encode()).hexdigest()
    
    async def log_event(
        self,
        event_type: str,
        source: str,
        action: str,
        result: str,
        user_id: Optional[UUID] = None,
        intent_id: Optional[UUID] = None,
        resource: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        risk_level: RiskLevel = RiskLevel.LOW
    ) -> AuditEvent:
        """Log an audit event.
        
        Args:
            event_type: Type of event
            source: Source component
            action: Action performed
            result: Result of action
            user_id: Optional user ID
            intent_id: Optional intent ID
            resource: Optional resource
            details: Optional additional details
            risk_level: Risk level of event
            
        Returns:
            Created audit event
        """
        event = AuditEvent(
            event_type=event_type,
            source=source,
            user_id=user_id,
            intent_id=intent_id,
            resource=resource,
            action=action,
            result=result,
            details=details or {},
            risk_level=risk_level
        )
        
        await self._write_event(event)
        return event
    
    async def _write_event(self, event: AuditEvent):
        """Write event to log file with chain hashing.
        
        Args:
            event: Audit event to write
        """
        async with self._lock:
            # Check if we need to rotate log file
            if self.current_log_file != self._get_current_log_file():
                self.current_log_file = self._get_current_log_file()
            
            # Get previous hash for chaining
            previous_hash = await self._get_last_hash()
            
            # Create log entry
            log_entry = {
                "event": event.dict(),
                "timestamp": event.timestamp.isoformat(),
                "previous_hash": previous_hash
            }
            
            # Calculate current hash
            log_data = json.dumps(log_entry, sort_keys=True, separators=(',', ':'))
            current_hash = self._calculate_hash(log_data, previous_hash)
            
            # Add hash to entry
            log_entry["hash"] = current_hash
            
            # Write to file
            async with aiofiles.open(self.current_log_file, 'a') as f:
                await f.write(json.dumps(log_entry) + '\n')
    
    async def _get_last_hash(self) -> str:
        """Get hash of last entry in current log file.
        
        Returns:
            Hash of last entry, empty string if no entries
        """
        try:
            if not os.path.exists(self.current_log_file):
                return ""
            
            async with aiofiles.open(self.current_log_file, 'r') as f:
                lines = await f.readlines()
                if not lines:
                    return ""
                
                last_line = lines[-1].strip()
                if not last_line:
                    return ""
                
                last_entry = json.loads(last_line)
                return last_entry.get("hash", "")
        except Exception:
            return ""
    
    async def verify_integrity(self, log_file: str = None) -> Dict[str, Any]:
        """Verify integrity of audit log chain.
        
        Args:
            log_file: Optional log file to verify, defaults to current
            
        Returns:
            Dictionary with verification results
        """
        if log_file is None:
            log_file = self.current_log_file
        
        if not os.path.exists(log_file):
            return {"valid": False, "error": "Log file not found"}
        
        try:
            async with aiofiles.open(log_file, 'r') as f:
                lines = await f.readlines()
            
            if not lines:
                return {"valid": True, "entries": 0}
            
            previous_hash = ""
            for i, line in enumerate(lines):
                line = line.strip()
                if not line:
                    continue
                
                entry = json.loads(line)
                stored_hash = entry.get("hash")
                entry_without_hash = {k: v for k, v in entry.items() if k != "hash"}
                
                log_data = json.dumps(entry_without_hash, sort_keys=True, separators=(',', ':'))
                calculated_hash = self._calculate_hash(log_data, previous_hash)
                
                if stored_hash != calculated_hash:
                    return {
                        "valid": False,
                        "error": f"Hash mismatch at line {i+1}",
                        "line": i+1
                    }
                
                previous_hash = stored_hash
            
            return {"valid": True, "entries": len(lines)}
        except Exception as e:
            return {"valid": False, "error": str(e)}
    
    async def query_events(
        self,
        user_id: Optional[UUID] = None,
        event_type: Optional[str] = None,
        source: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[AuditEvent]:
        """Query audit events with filters.
        
        Args:
            user_id: Filter by user ID
            event_type: Filter by event type
            source: Filter by source
            start_time: Filter start time
            end_time: Filter end time
            limit: Maximum number of events to return
            
        Returns:
            List of matching audit events
        """
        events = []
        
        # Get all log files in date range
        log_files = []
        if start_time and end_time:
            # Get files for date range
            current_date = start_time.date()
            while current_date <= end_time.date():
                date_str = current_date.strftime("%Y-%m-%d")
                log_file = os.path.join(self.log_dir, f"audit_{date_str}.log")
                if os.path.exists(log_file):
                    log_files.append(log_file)
                current_date += datetime.timedelta(days=1)
        else:
            # Get all log files
            for filename in os.listdir(self.log_dir):
                if filename.startswith("audit_") and filename.endswith(".log"):
                    log_files.append(os.path.join(self.log_dir, filename))
        
        # Sort log files
        log_files.sort()
        
        for log_file in log_files:
            if len(events) >= limit:
                break
            
            try:
                async with aiofiles.open(log_file, 'r') as f:
                    lines = await f.readlines()
                
                for line in lines:
                    if len(events) >= limit:
                        break
                    
                    line = line.strip()
                    if not line:
                        continue
                    
                    entry = json.loads(line)
                    event_data = entry["event"]
                    
                    # Apply filters
                    if user_id and event_data.get("user_id") != str(user_id):
                        continue
                    
                    if event_type and event_data.get("event_type") != event_type:
                        continue
                    
                    if source and event_data.get("source") != source:
                        continue
                    
                    event_timestamp = datetime.fromisoformat(event_data["timestamp"])
                    if start_time and event_timestamp < start_time:
                        continue
                    
                    if end_time and event_timestamp > end_time:
                        continue
                    
                    events.append(AuditEvent(**event_data))
            except Exception:
                continue
        
        return events[:limit]

"""
Audit models for RAVER Core.
"""

from datetime import datetime
from typing import Dict, Any, Optional
from pydantic import BaseModel


class AuditEvent(BaseModel):
    """Audit event model."""
    event_id: str
    timestamp: datetime
    event_type: str
    user_id: str
    request_id: Optional[str] = None
    action_type: Optional[str] = None
    target_resource: Optional[str] = None
    details: Dict[str, Any]
    severity: str = "info"  # info, warning, error, critical
    source: str = "raver-core"
    correlation_id: Optional[str] = None


class SecurityEvent(BaseModel):
    """Security-specific event model."""
    event_id: str
    timestamp: datetime
    event_type: str  # intrusion, data_breach, policy_violation, etc.
    severity: str  # low, medium, high, critical
    user_id: Optional[str] = None
    source_ip: Optional[str] = None
    target_resource: Optional[str] = None
    description: str
    details: Dict[str, Any]
    remediation_steps: list[str] = []
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None

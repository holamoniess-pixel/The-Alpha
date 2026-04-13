"""
Shared Pydantic schemas for RAVER components.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class UserRole(str, Enum):
    """User roles with different privilege levels."""
    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"


class ActionType(str, Enum):
    """Types of actions that can be performed."""
    PROCESS_TERMINATE = "process_terminate"
    FILE_MODIFY = "file_modify"
    NETWORK_CHANGE = "network_change"
    VAULT_ACCESS = "vault_access"
    UI_AUTOMATION = "ui_automation"
    SYSTEM_SCAN = "system_scan"
    LINK_INSPECT = "link_inspect"


class RiskLevel(str, Enum):
    """Risk levels for actions."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ApprovalMethod(str, Enum):
    """Methods for approving actions."""
    NONE = "none"
    UI_CONFIRM = "ui_confirm"
    VOICE_REAUTH = "voice_reauth"
    BIOMETRIC = "biometric"


class User(BaseModel):
    """User information."""
    user_id: str
    username: str
    roles: List[UserRole]
    voiceprint_id: Optional[str] = None
    created_at: datetime
    last_active: datetime


class ActionRequest(BaseModel):
    """Request to perform an action."""
    request_id: str
    user_id: str
    action_type: ActionType
    target_resource: str
    parameters: Dict[str, Any] = {}
    context: Dict[str, Any] = {}
    timestamp: datetime


class PolicyDecision(BaseModel):
    """Policy decision for an action request."""
    request_id: str
    approved: bool
    risk_level: RiskLevel
    approval_method: ApprovalMethod
    reason: str
    conditions: List[str] = []


class AuditLog(BaseModel):
    """Audit log entry."""
    log_id: str
    timestamp: datetime
    user_id: str
    action_type: ActionType
    target_resource: str
    decision: PolicyDecision
    execution_result: Optional[str] = None
    execution_error: Optional[str] = None


class Capability(BaseModel):
    """Capability definition."""
    capability_id: str
    verb: str
    resource: str
    description: str
    default_risk: RiskLevel


class VaultSecret(BaseModel):
    """Vault secret entry."""
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


class WebSocketMessage(BaseModel):
    """WebSocket message format."""
    message_type: str
    data: Dict[str, Any]
    timestamp: datetime
    user_id: Optional[str] = None


class SystemStatus(BaseModel):
    """System status information."""
    service_name: str
    status: str
    last_check: datetime
    details: Dict[str, Any] = {}


class LinkInspectionResult(BaseModel):
    """Result of link inspection."""
    url: str
    safe: bool
    confidence_score: float
    redirects: List[str] = []
    suspicious_patterns: List[str] = []
    has_forms: bool = False
    has_password_fields: bool = False
    recommendation: str


class SystemPauseRequest(BaseModel):
    """Request to pause system operations."""
    user_id: str
    reason: Optional[str] = None
    timestamp: datetime


class SystemPauseResponse(BaseModel):
    """Response to system pause request."""
    paused: bool
    paused_operations: List[str]
    message: str
    timestamp: datetime

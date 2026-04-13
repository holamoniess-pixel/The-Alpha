"""Pydantic schemas for RAVER system."""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, validator


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ApprovalMethod(str, Enum):
    NONE = "none"
    UI_CONFIRM = "ui_confirm"
    VOICE_REAUTH = "voice_reauth"
    BIOMETRIC = "biometric"
    MULTI_FACTOR = "multi_factor"


class Status(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"
    FAILED = "failed"
    PAUSED = "paused"


class User(BaseModel):
    user_id: UUID = Field(default_factory=uuid4)
    username: str
    voiceprint_id: Optional[UUID] = None
    roles: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_active: Optional[datetime] = None


class Role(BaseModel):
    role_name: str
    description: str
    capabilities: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Capability(BaseModel):
    name: str
    description: str
    resource_pattern: str  # e.g., "vault.read:*", "automation.click:*"
    risk_level: RiskLevel = RiskLevel.LOW
    requires_approval: bool = False
    approval_method: ApprovalMethod = ApprovalMethod.NONE


class Intent(BaseModel):
    intent_id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    command: str
    parsed_action: Optional[str] = None
    target_resource: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)
    context: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    status: Status = Status.PENDING


class PolicyDecision(BaseModel):
    decision_id: UUID = Field(default_factory=uuid4)
    intent_id: UUID
    risk_score: float = Field(ge=0.0, le=1.0)
    risk_level: RiskLevel
    approved: bool
    approval_method: Optional[ApprovalMethod] = None
    reason: str
    conditions: List[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class VaultEntry(BaseModel):
    secret_id: UUID = Field(default_factory=uuid4)
    service: str
    label: str
    owner_user_id: UUID
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    key_hash_sha256: str
    ciphertext_b64: str
    nonce_b64: str
    kdf_params: Dict[str, Any]
    access_policy: Dict[str, Any] = Field(default_factory=dict)


class Secret(BaseModel):
    secret_id: UUID
    service: str
    label: str
    owner_user_id: UUID
    created_at: datetime
    updated_at: datetime
    access_count: int = 0
    last_accessed: Optional[datetime] = None


class AuditEvent(BaseModel):
    event_id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    event_type: str
    source: str  # Which component generated this
    user_id: Optional[UUID] = None
    intent_id: Optional[UUID] = None
    resource: Optional[str] = None
    action: str
    result: str
    details: Dict[str, Any] = Field(default_factory=dict)
    risk_level: RiskLevel = RiskLevel.LOW


class SystemPause(BaseModel):
    pause_id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    reason: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    resumed_at: Optional[datetime] = None


class WebSocketMessage(BaseModel):
    message_id: UUID = Field(default_factory=uuid4)
    message_type: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    data: Dict[str, Any] = Field(default_factory=dict)
    target_user_id: Optional[UUID] = None


class DefenderStatus(BaseModel):
    status_id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    defender_enabled: bool
    last_scan_time: Optional[datetime] = None
    definitions_up_to_date: bool
    real_time_protection: bool
    threats_detected: int = 0


class LinkInspectionResult(BaseModel):
    inspection_id: UUID = Field(default_factory=uuid4)
    url: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    redirect_chain: List[str] = Field(default_factory=list)
    has_login_forms: bool = False
    has_password_fields: bool = False
    suspicious_patterns: List[str] = Field(default_factory=list)
    confidence_score: float = Field(ge=0.0, le=1.0)
    verdict: str  # "safe", "suspicious", "malicious", "unknown"
    recommendations: List[str] = Field(default_factory=list)

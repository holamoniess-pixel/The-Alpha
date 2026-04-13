"""
Policy models and enums for RAVER Core.
"""

from enum import Enum
from typing import Dict, Any, List
from pydantic import BaseModel


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


class RiskScore(BaseModel):
    """Risk assessment score."""
    level: RiskLevel
    score: float  # 0.0 to 1.0
    factors: List[str]
    confidence: float


class PolicyRule(BaseModel):
    """Individual policy rule."""
    rule_id: str
    name: str
    description: str
    action_types: List[str]
    user_roles: List[str]
    conditions: Dict[str, Any]
    risk_level: RiskLevel
    approval_method: ApprovalMethod
    enabled: bool = True


class PolicyDecision(BaseModel):
    """Policy decision for an action request."""
    approved: bool
    risk_score: RiskScore
    approval_method: ApprovalMethod
    reason: str
    conditions: List[str] = []
    rule_applied: str = None

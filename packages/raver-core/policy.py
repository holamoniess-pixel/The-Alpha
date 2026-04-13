"""
RAVER Policy Engine

Implements risk assessment, capability-based access control, and approval workflows
for all RAVER system operations.
"""

import asyncio
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, field

from .orchestrator import Intent, IntentType


class RiskScore(Enum):
    """Risk levels for system operations."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class ApprovalMethod(Enum):
    """Methods for obtaining user approval."""
    NONE = "none"
    UI_CONFIRM = "ui_confirm"
    VOICE_REAUTH = "voice_reauth"
    BIOMETRIC = "biometric"
    MULTI_FACTOR = "multi_factor"


class Capability(Enum):
    """System capabilities that can be granted to roles."""
    # Vault capabilities
    VAULT_READ = "vault.read"
    VAULT_WRITE = "vault.write"
    VAULT_DELETE = "vault.delete"
    
    # Automation capabilities
    AUTOMATION_CLICK = "automation.click"
    AUTOMATION_TYPE = "automation.type"
    AUTOMATION_SCREENSHOT = "automation.screenshot"
    
    # System capabilities
    SYSTEM_PROCESS_TERMINATE = "system.process.terminate"
    SYSTEM_PROCESS_LIST = "system.process.list"
    SYSTEM_SERVICE_CONTROL = "system.service.control"
    
    # Network capabilities
    NETWORK_LAN_SEND = "network.lan.send"
    NETWORK_INTERNET_REQUEST = "network.internet.request"
    NETWORK_FIREWALL_MODIFY = "network.firewall.modify"
    
    # Security capabilities
    SECURITY_SCAN = "security.scan"
    SECURITY_ISOLATE = "security.isolate"
    SECURITY_QUARANTINE = "security.quarantine"


class Role(Enum):
    """User roles with different privilege levels."""
    GUEST = "guest"
    USER = "user"
    POWER_USER = "power_user"
    ADMIN = "admin"
    SYSTEM = "system"


@dataclass
class PolicyRule:
    """Represents a policy rule for evaluating intents."""
    rule_id: str
    name: str
    description: str
    intent_types: List[IntentType]
    required_capabilities: List[Capability]
    risk_score: RiskScore
    approval_method: ApprovalMethod
    conditions: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class PolicyEvaluationResult:
    """Result of policy evaluation for an intent."""
    allowed: bool
    requires_approval: bool
    approval_method: ApprovalMethod
    risk_score: RiskScore
    reason: str
    matched_rules: List[str] = field(default_factory=list)
    missing_capabilities: List[Capability] = field(default_factory=list)


class PolicyEngine:
    """Evaluates intents against security policies and risk assessments."""
    
    def __init__(self):
        self.rules: Dict[str, PolicyRule] = {}
        self.role_capabilities: Dict[Role, Set[Capability]] = {}
        self.user_roles: Dict[str, Role] = {}
        self.risk_factors: Dict[str, Any] = {}
        self._initialize_default_policies()
    
    def _initialize_default_policies(self):
        """Initialize default security policies."""
        # Set up default role capabilities
        self.role_capabilities[Role.GUEST] = {
            Capability.VAULT_READ,
        }
        
        self.role_capabilities[Role.USER] = {
            Capability.VAULT_READ,
            Capability.VAULT_WRITE,
            Capability.AUTOMATION_CLICK,
            Capability.AUTOMATION_TYPE,
            Capability.AUTOMATION_SCREENSHOT,
            Capability.SYSTEM_PROCESS_LIST,
            Capability.NETWORK_LAN_SEND,
            Capability.SECURITY_SCAN,
        }
        
        self.role_capabilities[Role.POWER_USER] = self.role_capabilities[Role.USER].union({
            Capability.VAULT_DELETE,
            Capability.SYSTEM_PROCESS_TERMINATE,
            Capability.SYSTEM_SERVICE_CONTROL,
            Capability.NETWORK_INTERNET_REQUEST,
        })
        
        self.role_capabilities[Role.ADMIN] = self.role_capabilities[Role.POWER_USER].union({
            Capability.NETWORK_FIREWALL_MODIFY,
            Capability.SECURITY_ISOLATE,
            Capability.SECURITY_QUARANTINE,
        })
        
        self.role_capabilities[Role.SYSTEM] = set(Capability)  # System has all capabilities
        
        # Add default policy rules
        self._add_default_rules()
    
    def _add_default_rules(self):
        """Add default security rules."""
        
        # Vault access rules
        self.add_rule(PolicyRule(
            rule_id="vault_read_low",
            name="Vault Read Access",
            description="Allow reading from vault with UI confirmation for non-admins",
            intent_types=[IntentType.VAULT_ACCESS],
            required_capabilities=[Capability.VAULT_READ],
            risk_score=RiskScore.LOW,
            approval_method=ApprovalMethod.UI_CONFIRM,
            conditions={"operation": "read"}
        ))
        
        self.add_rule(PolicyRule(
            rule_id="vault_write_medium",
            name="Vault Write Access",
            description="Require voice re-auth for vault writes",
            intent_types=[IntentType.VAULT_ACCESS],
            required_capabilities=[Capability.VAULT_WRITE],
            risk_score=RiskScore.MEDIUM,
            approval_method=ApprovalMethod.VOICE_REAUTH,
            conditions={"operation": "write"}
        ))
        
        self.add_rule(PolicyRule(
            rule_id="vault_delete_high",
            name="Vault Delete Access",
            description="Require multi-factor auth for vault deletions",
            intent_types=[IntentType.VAULT_ACCESS],
            required_capabilities=[Capability.VAULT_DELETE],
            risk_score=RiskScore.HIGH,
            approval_method=ApprovalMethod.MULTI_FACTOR,
            conditions={"operation": "delete"}
        ))
        
        # System control rules
        self.add_rule(PolicyRule(
            rule_id="process_terminate_critical",
            name="Process Termination",
            description="Critical risk - require multi-factor auth",
            intent_types=[IntentType.SYSTEM_CONTROL],
            required_capabilities=[Capability.SYSTEM_PROCESS_TERMINATE],
            risk_score=RiskScore.CRITICAL,
            approval_method=ApprovalMethod.MULTI_FACTOR,
            conditions={"action": "terminate"}
        ))
        
        self.add_rule(PolicyRule(
            rule_id="service_control_high",
            name="Service Control",
            description="High risk - require biometric auth",
            intent_types=[IntentType.SYSTEM_CONTROL],
            required_capabilities=[Capability.SYSTEM_SERVICE_CONTROL],
            risk_score=RiskScore.HIGH,
            approval_method=ApprovalMethod.BIOMETRIC,
            conditions={"action": "service_control"}
        ))
        
        # Network rules
        self.add_rule(PolicyRule(
            rule_id="internet_request_medium",
            name="Internet Network Request",
            description="Medium risk - require voice re-auth",
            intent_types=[IntentType.NETWORK_ACTION],
            required_capabilities=[Capability.NETWORK_INTERNET_REQUEST],
            risk_score=RiskScore.MEDIUM,
            approval_method=ApprovalMethod.VOICE_REAUTH,
            conditions={"destination": "internet"}
        ))
        
        self.add_rule(PolicyRule(
            rule_id="firewall_modify_critical",
            name="Firewall Modification",
            description="Critical risk - require multi-factor auth",
            intent_types=[IntentType.NETWORK_ACTION],
            required_capabilities=[Capability.NETWORK_FIREWALL_MODIFY],
            risk_score=RiskScore.CRITICAL,
            approval_method=ApprovalMethod.MULTI_FACTOR,
            conditions={"action": "firewall_modify"}
        ))
        
        # Security action rules
        self.add_rule(PolicyRule(
            rule_id="security_isolate_critical",
            name="Security Isolation",
            description="Critical risk - require multi-factor auth",
            intent_types=[IntentType.SECURITY_ACTION],
            required_capabilities=[Capability.SECURITY_ISOLATE],
            risk_score=RiskScore.CRITICAL,
            approval_method=ApprovalMethod.MULTI_FACTOR,
            conditions={"action": "isolate"}
        ))
        
        # Automation rules
        self.add_rule(PolicyRule(
            rule_id="automation_low",
            name="Basic Automation",
            description="Low risk automation with UI confirmation",
            intent_types=[IntentType.AUTOMATION, IntentType.UI_INTERACTION],
            required_capabilities=[Capability.AUTOMATION_CLICK, Capability.AUTOMATION_TYPE],
            risk_score=RiskScore.LOW,
            approval_method=ApprovalMethod.UI_CONFIRM
        ))
    
    def add_rule(self, rule: PolicyRule):
        """Add a new policy rule."""
        self.rules[rule.rule_id] = rule
    
    def remove_rule(self, rule_id: str):
        """Remove a policy rule."""
        self.rules.pop(rule_id, None)
    
    def set_user_role(self, user_id: str, role: Role):
        """Set the role for a user."""
        self.user_roles[user_id] = role
    
    def get_user_role(self, user_id: str) -> Role:
        """Get the role for a user."""
        return self.user_roles.get(user_id, Role.GUEST)
    
    def get_user_capabilities(self, user_id: str) -> Set[Capability]:
        """Get all capabilities for a user based on their role."""
        role = self.get_user_role(user_id)
        return self.role_capabilities.get(role, set())
    
    async def evaluate_intent(self, intent: Intent) -> PolicyEvaluationResult:
        """Evaluate an intent against all applicable policies."""
        user_capabilities = self.get_user_capabilities(intent.user_id)
        matched_rules = []
        missing_capabilities = []
        highest_risk = RiskScore.LOW
        required_approval = ApprovalMethod.NONE
        
        # Find applicable rules
        for rule in self.rules.values():
            if not rule.enabled:
                continue
            
            # Check if rule applies to this intent type
            if intent.intent_type not in rule.intent_types:
                continue
            
            # Check rule conditions
            if not self._evaluate_conditions(rule.conditions, intent.parameters):
                continue
            
            # Check required capabilities
            rule_capabilities = set(rule.required_capabilities)
            missing = rule_capabilities - user_capabilities
            
            if missing:
                missing_capabilities.extend(missing)
                continue
            
            matched_rules.append(rule.rule_id)
            
            # Update highest risk and approval method
            if rule.risk_score.value > highest_risk.value:
                highest_risk = rule.risk_score
            
            # Use the most stringent approval method
            required_approval = self._get_stringent_approval(required_approval, rule.approval_method)
        
        # Determine if allowed and reason
        if missing_capabilities:
            return PolicyEvaluationResult(
                allowed=False,
                requires_approval=False,
                approval_method=ApprovalMethod.NONE,
                risk_score=highest_risk,
                reason=f"Missing required capabilities: {[cap.value for cap in missing_capabilities]}",
                missing_capabilities=missing_capabilities
            )
        
        if not matched_rules:
            return PolicyEvaluationResult(
                allowed=False,
                requires_approval=False,
                approval_method=ApprovalMethod.NONE,
                risk_score=RiskScore.LOW,
                reason="No applicable policy rules found"
            )
        
        requires_approval = required_approval != ApprovalMethod.NONE
        
        return PolicyEvaluationResult(
            allowed=True,
            requires_approval=requires_approval,
            approval_method=required_approval,
            risk_score=highest_risk,
            reason=f"Approved by rules: {matched_rules}",
            matched_rules=matched_rules
        )
    
    def _evaluate_conditions(self, conditions: Dict[str, Any], parameters: Dict[str, Any]) -> bool:
        """Evaluate rule conditions against intent parameters."""
        for key, expected_value in conditions.items():
            if key not in parameters:
                return False
            
            actual_value = parameters[key]
            
            # Handle different types of conditions
            if isinstance(expected_value, list):
                if actual_value not in expected_value:
                    return False
            elif isinstance(expected_value, dict):
                # Handle complex conditions (ranges, patterns, etc.)
                if not self._evaluate_complex_condition(expected_value, actual_value):
                    return False
            else:
                if actual_value != expected_value:
                    return False
        
        return True
    
    def _evaluate_complex_condition(self, condition: Dict[str, Any], actual_value: Any) -> bool:
        """Evaluate complex conditions like ranges, patterns, etc."""
        if "min" in condition and actual_value < condition["min"]:
            return False
        if "max" in condition and actual_value > condition["max"]:
            return False
        if "pattern" in condition and not str(actual_value).match(condition["pattern"]):
            return False
        
        return True
    
    def _get_stringent_approval(self, current: ApprovalMethod, new: ApprovalMethod) -> ApprovalMethod:
        """Get the most stringent approval method between two."""
        approval_hierarchy = {
            ApprovalMethod.NONE: 0,
            ApprovalMethod.UI_CONFIRM: 1,
            ApprovalMethod.VOICE_REAUTH: 2,
            ApprovalMethod.BIOMETRIC: 3,
            ApprovalMethod.MULTI_FACTOR: 4,
        }
        
        if approval_hierarchy[new] > approval_hierarchy[current]:
            return new
        return current
    
    def get_all_rules(self) -> List[PolicyRule]:
        """Get all policy rules."""
        return list(self.rules.values())
    
    def get_rule(self, rule_id: str) -> Optional[PolicyRule]:
        """Get a specific policy rule."""
        return self.rules.get(rule_id)
    
    def update_rule(self, rule_id: str, updates: Dict[str, Any]):
        """Update a policy rule."""
        if rule_id in self.rules:
            rule = self.rules[rule_id]
            for key, value in updates.items():
                if hasattr(rule, key):
                    setattr(rule, key, value)

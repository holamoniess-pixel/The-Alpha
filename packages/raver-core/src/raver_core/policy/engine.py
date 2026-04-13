"""Policy engine for RAVER zero-trust execution."""

import re
from typing import Dict, List, Optional, Tuple, Any
from uuid import UUID

from raver_shared.schemas import (
    Intent,
    PolicyDecision,
    Capability,
    RiskLevel,
    ApprovalMethod,
    Status
)


class PolicyEngine:
    """Zero-trust policy engine for intent evaluation."""
    
    def __init__(self):
        """Initialize policy engine with default capabilities and rules."""
        self.capabilities: Dict[str, Capability] = {}
        self.user_roles: Dict[UUID, List[str]] = {}
        self.role_capabilities: Dict[str, List[str]] = {}
        
        # Initialize default capabilities
        self._initialize_default_capabilities()
        
        # High-risk action patterns
        self.high_risk_patterns = [
            r'kill.*process',
            r'terminate.*process', 
            r'delete.*file',
            r'remove.*file',
            r'format.*disk',
            r'firewall.*change',
            r'network.*block',
            r'network.*allow',
            r'registry.*modify',
            r'system.*shutdown',
            r'system.*reboot',
            r'admin.*password',
            r'credential.*dump',
            r'secret.*extract',
            r'self.*update',
            r'auto.*update',
            r'install.*software',
            r'uninstall.*software'
        ]
    
    def _initialize_default_capabilities(self):
        """Initialize default system capabilities."""
        default_capabilities = [
            Capability(
                name="vault.read",
                description="Read secrets from vault",
                resource_pattern="vault.read:*",
                risk_level=RiskLevel.MEDIUM,
                requires_approval=True,
                approval_method=ApprovalMethod.UI_CONFIRM
            ),
            Capability(
                name="vault.write",
                description="Write secrets to vault",
                resource_pattern="vault.write:*",
                risk_level=RiskLevel.HIGH,
                requires_approval=True,
                approval_method=ApprovalMethod.UI_CONFIRM
            ),
            Capability(
                name="automation.click",
                description="Perform UI automation clicks",
                resource_pattern="automation.click:*",
                risk_level=RiskLevel.MEDIUM,
                requires_approval=False
            ),
            Capability(
                name="automation.type",
                description="Perform UI automation typing",
                resource_pattern="automation.type:*",
                risk_level=RiskLevel.MEDIUM,
                requires_approval=False
            ),
            Capability(
                name="process.list",
                description="List running processes",
                resource_pattern="process.list:*",
                risk_level=RiskLevel.LOW,
                requires_approval=False
            ),
            Capability(
                name="process.terminate",
                description="Terminate processes",
                resource_pattern="process.terminate:*",
                risk_level=RiskLevel.HIGH,
                requires_approval=True,
                approval_method=ApprovalMethod.UI_CONFIRM
            ),
            Capability(
                name="file.read",
                description="Read files",
                resource_pattern="file.read:*",
                risk_level=RiskLevel.LOW,
                requires_approval=False
            ),
            Capability(
                name="file.write",
                description="Write files",
                resource_pattern="file.write:*",
                risk_level=RiskLevel.MEDIUM,
                requires_approval=False
            ),
            Capability(
                name="network.request",
                description="Make network requests",
                resource_pattern="network.request:*",
                risk_level=RiskLevel.MEDIUM,
                requires_approval=True,
                approval_method=ApprovalMethod.UI_CONFIRM
            ),
            Capability(
                name="system.pause",
                description="Pause system operations",
                resource_pattern="system.pause:*",
                risk_level=RiskLevel.LOW,
                requires_approval=False
            )
        ]
        
        for cap in default_capabilities:
            self.capabilities[cap.name] = cap
    
    def evaluate_intent(self, intent: Intent) -> PolicyDecision:
        """Evaluate an intent against security policies.
        
        Args:
            intent: Intent to evaluate
            
        Returns:
            Policy decision with risk assessment and approval requirements
        """
        # Get user roles
        user_roles = self.user_roles.get(intent.user_id, [])
        
        # Parse intent into action and resource
        action, resource = self._parse_intent(intent)
        
        # Calculate base risk score
        risk_score, risk_level = self._calculate_risk_score(intent, action, resource)
        
        # Check if user has required capabilities
        required_capability = self._get_required_capability(action, resource)
        has_capability = self._check_user_capability(intent.user_id, required_capability)
        
        # Determine if approval is needed
        approval_method = self._determine_approval_method(
            risk_level, required_capability, has_capability
        )
        
        # Make decision
        approved = has_capability and not (approval_method != ApprovalMethod.NONE and risk_level == RiskLevel.CRITICAL)
        
        decision = PolicyDecision(
            intent_id=intent.intent_id,
            risk_score=risk_score,
            risk_level=risk_level,
            approved=approved,
            approval_method=approval_method,
            reason=self._generate_reason(approved, has_capability, risk_level, required_capability),
            conditions=self._generate_conditions(risk_level, approval_method)
        )
        
        return decision
    
    def _parse_intent(self, intent: Intent) -> Tuple[str, str]:
        """Parse intent into action and resource.
        
        Args:
            intent: Intent to parse
            
        Returns:
            Tuple of (action, resource)
        """
        command = intent.command.lower().strip()
        
        # Extract action using simple patterns
        if "pause" in command:
            return "system.pause", "system"
        elif "stop" in command or "kill" in command or "terminate" in command:
            return "process.terminate", "process"
        elif "list" in command or "show" in command:
            return "process.list", "process"
        elif "read" in command:
            return "file.read", "file"
        elif "write" in command or "create" in command:
            return "file.write", "file"
        elif "click" in command:
            return "automation.click", "ui"
        elif "type" in command or "input" in command:
            return "automation.type", "ui"
        elif "vault" in command or "secret" in command:
            if "get" in command or "read" in command:
                return "vault.read", "vault"
            elif "store" in command or "save" in command:
                return "vault.write", "vault"
        elif "network" in command or "request" in command:
            return "network.request", "network"
        
        # Default fallback
        return "unknown", "unknown"
    
    def _calculate_risk_score(self, intent: Intent, action: str, resource: str) -> Tuple[float, RiskLevel]:
        """Calculate risk score for intent.
        
        Args:
            intent: Intent to evaluate
            action: Parsed action
            resource: Target resource
            
        Returns:
            Tuple of (risk_score, risk_level)
        """
        base_score = 0.1  # Start with low risk
        
        # Check against high-risk patterns
        for pattern in self.high_risk_patterns:
            if re.search(pattern, intent.command, re.IGNORECASE):
                base_score += 0.4
                break
        
        # Resource-specific risk
        high_risk_resources = ["system", "process", "registry", "network", "vault"]
        if resource in high_risk_resources:
            base_score += 0.2
        
        # Action-specific risk
        high_risk_actions = ["terminate", "delete", "write", "modify", "change"]
        if any(action in high_risk_actions for high_risk_actions in [action]):
            base_score += 0.2
        
        # Cap at 1.0
        risk_score = min(base_score, 1.0)
        
        # Determine risk level
        if risk_score >= 0.8:
            risk_level = RiskLevel.CRITICAL
        elif risk_score >= 0.6:
            risk_level = RiskLevel.HIGH
        elif risk_score >= 0.4:
            risk_level = RiskLevel.MEDIUM
        else:
            risk_level = RiskLevel.LOW
        
        return risk_score, risk_level
    
    def _get_required_capability(self, action: str, resource: str) -> Optional[str]:
        """Get required capability for action/resource pair.
        
        Args:
            action: Action to perform
            resource: Target resource
            
        Returns:
            Required capability name or None
        """
        capability_name = f"{action}.{resource}"
        return capability_name if capability_name in self.capabilities else None
    
    def _check_user_capability(self, user_id: UUID, capability_name: str) -> bool:
        """Check if user has required capability.
        
        Args:
            user_id: User ID
            capability_name: Required capability
            
        Returns:
            True if user has capability
        """
        if not capability_name:
            return True  # No specific capability required
        
        user_roles = self.user_roles.get(user_id, [])
        
        for role in user_roles:
            role_caps = self.role_capabilities.get(role, [])
            if capability_name in role_caps:
                return True
        
        return False
    
    def _determine_approval_method(
        self,
        risk_level: RiskLevel,
        capability: Optional[str],
        has_capability: bool
    ) -> ApprovalMethod:
        """Determine required approval method.
        
        Args:
            risk_level: Calculated risk level
            capability: Required capability
            has_capability: Whether user has capability
            
        Returns:
            Required approval method
        """
        if not has_capability:
            return ApprovalMethod.UI_CONFIRM
        
        if risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            return ApprovalMethod.UI_CONFIRM
        
        if capability:
            cap_obj = self.capabilities.get(capability)
            if cap_obj and cap_obj.requires_approval:
                return cap_obj.approval_method
        
        return ApprovalMethod.NONE
    
    def _generate_reason(
        self,
        approved: bool,
        has_capability: bool,
        risk_level: RiskLevel,
        capability: Optional[str]
    ) -> str:
        """Generate reason for policy decision.
        
        Args:
            approved: Whether decision is approved
            has_capability: Whether user has capability
            risk_level: Risk level
            capability: Required capability
            
        Returns:
            Human-readable reason
        """
        if not has_capability:
            return f"User lacks required capability: {capability or 'unknown'}"
        
        if risk_level == RiskLevel.CRITICAL:
            return "Critical risk action requires explicit approval"
        
        if risk_level == RiskLevel.HIGH:
            return "High risk action requires approval"
        
        if approved:
            return "Action approved within policy bounds"
        else:
            return "Action blocked by policy"
    
    def _generate_conditions(self, risk_level: RiskLevel, approval_method: ApprovalMethod) -> List[str]:
        """Generate conditions for policy decision.
        
        Args:
            risk_level: Risk level
            approval_method: Required approval method
            
        Returns:
            List of conditions
        """
        conditions = []
        
        if approval_method != ApprovalMethod.NONE:
            conditions.append(f"Requires {approval_method.value} approval")
        
        if risk_level == RiskLevel.HIGH:
            conditions.append("High risk - monitor execution")
        elif risk_level == RiskLevel.CRITICAL:
            conditions.append("Critical risk - enhanced monitoring required")
        
        return conditions
    
    def assign_user_role(self, user_id: UUID, role: str):
        """Assign role to user.
        
        Args:
            user_id: User ID
            role: Role name
        """
        if user_id not in self.user_roles:
            self.user_roles[user_id] = []
        
        if role not in self.user_roles[user_id]:
            self.user_roles[user_id].append(role)
    
    def grant_role_capability(self, role: str, capability_name: str):
        """Grant capability to role.
        
        Args:
            role: Role name
            capability_name: Capability name
        """
        if role not in self.role_capabilities:
            self.role_capabilities[role] = []
        
        if capability_name not in self.role_capabilities[role]:
            self.role_capabilities[role].append(capability_name)

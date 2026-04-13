"""
Policy Engine - Evaluates requests against security policies.
"""

import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from pathlib import Path

from .models import RiskScore, ApprovalMethod, PolicyDecision, PolicyRule, RiskLevel
from ...raver_shared.schemas import ActionRequest, UserRole, ActionType


class RiskAssessor:
    """Assesses risk for action requests."""
    
    def __init__(self):
        self.risk_factors = {
            ActionType.PROCESS_TERMINATE: {
                "base_risk": 0.7,
                "factors": {
                    "system_process": 0.3,
                    "critical_process": 0.4,
                    "multiple_processes": 0.2
                }
            },
            ActionType.FILE_MODIFY: {
                "base_risk": 0.5,
                "factors": {
                    "system_directory": 0.4,
                    "executable_file": 0.3,
                    "sensitive_extension": 0.2
                }
            },
            ActionType.VAULT_ACCESS: {
                "base_risk": 0.3,
                "factors": {
                    "sensitive_service": 0.3,
                    "bulk_access": 0.2,
                    "unusual_time": 0.1
                }
            },
            ActionType.UI_AUTOMATION: {
                "base_risk": 0.6,
                "factors": {
                    "system_interaction": 0.3,
                    "sensitive_app": 0.2,
                    "automated_sequence": 0.2
                }
            },
            ActionType.LINK_INSPECT: {
                "base_risk": 0.2,
                "factors": {
                    "suspicious_domain": 0.4,
                    "file_download": 0.3,
                    "redirect_chain": 0.2
                }
            },
            ActionType.SYSTEM_SCAN: {
                "base_risk": 0.1,
                "factors": {
                    "deep_scan": 0.2,
                    "network_scan": 0.3
                }
            }
        }
    
    def assess_risk(self, request: ActionRequest) -> RiskScore:
        """Assess risk for an action request."""
        action_config = self.risk_factors.get(request.action_type, {"base_risk": 0.5, "factors": {}})
        
        # Start with base risk
        risk_score = action_config["base_risk"]
        factors = []
        
        # Apply risk factors based on request parameters
        if request.action_type == ActionType.PROCESS_TERMINATE:
            risk_score, factors = self._assess_process_risk(request, risk_score, factors)
        elif request.action_type == ActionType.FILE_MODIFY:
            risk_score, factors = self._assess_file_risk(request, risk_score, factors)
        elif request.action_type == ActionType.VAULT_ACCESS:
            risk_score, factors = self._assess_vault_risk(request, risk_score, factors)
        elif request.action_type == ActionType.UI_AUTOMATION:
            risk_score, factors = self._assess_ui_risk(request, risk_score, factors)
        elif request.action_type == ActionType.LINK_INSPECT:
            risk_score, factors = self._assess_link_risk(request, risk_score, factors)
        
        # Cap risk score at 1.0
        risk_score = min(risk_score, 1.0)
        
        # Determine risk level
        if risk_score >= 0.8:
            level = RiskLevel.CRITICAL
        elif risk_score >= 0.6:
            level = RiskLevel.HIGH
        elif risk_score >= 0.4:
            level = RiskLevel.MEDIUM
        else:
            level = RiskLevel.LOW
        
        return RiskScore(
            level=level,
            score=risk_score,
            factors=factors,
            confidence=0.8  # Default confidence
        )
    
    def _assess_process_risk(self, request: ActionRequest, base_score: float, 
                           factors: List[str]) -> tuple[float, List[str]]:
        """Assess risk for process termination."""
        process_name = request.target_resource.lower()
        
        # Check for system processes
        system_processes = ["winlogon", "csrss", "smss", "lsass", "services"]
        if any(sys_proc in process_name for sys_proc in system_processes):
            base_score += 0.3
            factors.append("System process termination")
        
        # Check for critical processes
        critical_processes = ["explorer", "wininit", "svchost"]
        if any(crit_proc in process_name for crit_proc in critical_processes):
            base_score += 0.2
            factors.append("Critical process termination")
        
        # Check for multiple processes
        if request.parameters.get("multiple", False):
            base_score += 0.2
            factors.append("Multiple process termination")
        
        return base_score, factors
    
    def _assess_file_risk(self, request: ActionRequest, base_score: float,
                         factors: List[str]) -> tuple[float, List[str]]:
        """Assess risk for file modification."""
        file_path = request.target_resource.lower()
        
        # Check for system directories
        system_dirs = ["windows", "system32", "program files"]
        if any(sys_dir in file_path for sys_dir in system_dirs):
            base_score += 0.4
            factors.append("System directory modification")
        
        # Check for executable files
        executable_extensions = [".exe", ".bat", ".cmd", ".ps1", ".dll"]
        if any(file_path.endswith(ext) for ext in executable_extensions):
            base_score += 0.3
            factors.append("Executable file modification")
        
        # Check for sensitive extensions
        sensitive_extensions = [".reg", ".ini", ".config", ".key"]
        if any(file_path.endswith(ext) for ext in sensitive_extensions):
            base_score += 0.2
            factors.append("Sensitive file modification")
        
        return base_score, factors
    
    def _assess_vault_risk(self, request: ActionRequest, base_score: float,
                          factors: List[str]) -> tuple[float, List[str]]:
        """Assess risk for vault access."""
        service = request.parameters.get("service", "").lower()
        
        # Check for sensitive services
        sensitive_services = ["bank", "financial", "crypto", "wallet", "password"]
        if any(sens_service in service for sens_service in sensitive_services):
            base_score += 0.3
            factors.append("Sensitive service access")
        
        # Check for bulk access
        if request.parameters.get("bulk", False):
            base_score += 0.2
            factors.append("Bulk vault access")
        
        # Check for unusual time (simplified)
        current_hour = datetime.now().hour
        if current_hour < 6 or current_hour > 22:
            base_score += 0.1
            factors.append("Unusual access time")
        
        return base_score, factors
    
    def _assess_ui_risk(self, request: ActionRequest, base_score: float,
                       factors: List[str]) -> tuple[float, List[str]]:
        """Assess risk for UI automation."""
        target = request.target_resource.lower()
        
        # Check for system interaction
        system_apps = ["task manager", "control panel", "settings", "registry"]
        if any(sys_app in target for sys_app in system_apps):
            base_score += 0.3
            factors.append("System application interaction")
        
        # Check for sensitive applications
        sensitive_apps = ["bank", "finance", "password", "crypto"]
        if any(sens_app in target for sens_app in sensitive_apps):
            base_score += 0.2
            factors.append("Sensitive application interaction")
        
        # Check for automated sequence
        if request.parameters.get("sequence", False):
            base_score += 0.2
            factors.append("Automated action sequence")
        
        return base_score, factors
    
    def _assess_link_risk(self, request: ActionRequest, base_score: float,
                         factors: List[str]) -> tuple[float, List[str]]:
        """Assess risk for link inspection."""
        url = request.target_resource.lower()
        
        # Check for suspicious domains
        suspicious_tlds = [".tk", ".ml", ".ga", ".cf", ".bit"]
        if any(url.endswith(tld) for tld in suspicious_tlds):
            base_score += 0.4
            factors.append("Suspicious top-level domain")
        
        # Check for file download
        if request.parameters.get("download", False):
            base_score += 0.3
            factors.append("File download requested")
        
        # Check for redirect chain
        if request.parameters.get("redirects", 0) > 3:
            base_score += 0.2
            factors.append("Long redirect chain")
        
        return base_score, factors


class PolicyEngine:
    """Main policy engine for evaluating action requests."""
    
    def __init__(self):
        self.risk_assessor = RiskAssessor()
        self.rules: List[PolicyRule] = []
        self.policy_file = Path("policy_rules.json")
        self._load_default_rules()
    
    async def initialize(self):
        """Initialize the policy engine."""
        if self.policy_file.exists():
            await self._load_rules()
        else:
            await self._save_rules()
    
    async def evaluate_request(self, request: ActionRequest, 
                              user_roles: List[UserRole]) -> PolicyDecision:
        """Evaluate an action request against policies."""
        # Assess risk
        risk_score = self.risk_assessor.assess_risk(request)
        
        # Find applicable rules
        applicable_rules = self._find_applicable_rules(request, user_roles)
        
        if not applicable_rules:
            # Default policy - deny high-risk actions
            if risk_score.level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
                return PolicyDecision(
                    approved=False,
                    risk_score=risk_score,
                    approval_method=ApprovalMethod.UI_CONFIRM,
                    reason="No applicable policy found for high-risk action",
                    conditions=["Default security policy"]
                )
            else:
                return PolicyDecision(
                    approved=True,
                    risk_score=risk_score,
                    approval_method=ApprovalMethod.NONE,
                    reason="Low-risk action approved by default",
                    conditions=["Default approval"]
                )
        
        # Apply the most restrictive applicable rule
        rule = max(applicable_rules, key=lambda r: self._rule_priority(r))
        
        # Determine approval method based on risk level and rule
        approval_method = self._determine_approval_method(risk_score, rule)
        
        # Make decision
        approved = self._should_approve(risk_score, rule, user_roles)
        
        return PolicyDecision(
            approved=approved,
            risk_score=risk_score,
            approval_method=approval_method,
            reason=f"Rule '{rule.name}' applied: {rule.description}",
            conditions=rule.conditions.get("requirements", []),
            rule_applied=rule.rule_id
        )
    
    def _find_applicable_rules(self, request: ActionRequest, 
                              user_roles: List[UserRole]) -> List[PolicyRule]:
        """Find rules that apply to the request."""
        applicable_rules = []
        
        for rule in self.rules:
            if not rule.enabled:
                continue
            
            # Check action type
            if request.action_type.value not in rule.action_types:
                continue
            
            # Check user roles
            user_role_values = [role.value for role in user_roles]
            if not any(role in rule.user_roles for role in user_role_values):
                continue
            
            # Check conditions
            if self._check_rule_conditions(rule, request):
                applicable_rules.append(rule)
        
        return applicable_rules
    
    def _check_rule_conditions(self, rule: PolicyRule, request: ActionRequest) -> bool:
        """Check if request meets rule conditions."""
        conditions = rule.conditions
        
        # Time-based conditions
        if "time_window" in conditions:
            time_window = conditions["time_window"]
            current_hour = datetime.now().hour
            start_hour = time_window.get("start", 0)
            end_hour = time_window.get("end", 23)
            
            if not (start_hour <= current_hour <= end_hour):
                return False
        
        # Resource-based conditions
        if "resource_patterns" in conditions:
            patterns = conditions["resource_patterns"]
            if not any(pattern in request.target_resource.lower() 
                      for pattern in patterns):
                return False
        
        # Parameter-based conditions
        if "required_parameters" in conditions:
            required_params = conditions["required_parameters"]
            for param in required_params:
                if param not in request.parameters:
                    return False
        
        return True
    
    def _determine_approval_method(self, risk_score: RiskScore, 
                                  rule: PolicyRule) -> ApprovalMethod:
        """Determine approval method based on risk and rule."""
        # High and critical risk always require approval
        if risk_score.level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            return ApprovalMethod.UI_CONFIRM
        
        # Medium risk may require voice re-auth
        if risk_score.level == RiskLevel.MEDIUM:
            return ApprovalMethod.VOICE_REAUTH
        
        # Use rule-defined method or default
        if rule.approval_method != ApprovalMethod.NONE:
            return rule.approval_method
        
        return ApprovalMethod.NONE
    
    def _should_approve(self, risk_score: RiskScore, rule: PolicyRule,
                       user_roles: List[UserRole]) -> bool:
        """Determine if action should be approved."""
        # Critical risk requires admin approval
        if risk_score.level == RiskLevel.CRITICAL:
            return UserRole.ADMIN in user_roles
        
        # High risk requires user or admin role
        if risk_score.level == RiskLevel.HIGH:
            return any(role in [UserRole.USER, UserRole.ADMIN] for role in user_roles)
        
        # Medium and low risk can be approved for authenticated users
        return any(role in [UserRole.USER, UserRole.ADMIN] for role in user_roles)
    
    def _rule_priority(self, rule: PolicyRule) -> int:
        """Calculate priority for rule selection."""
        priority = 0
        
        # Higher priority for more specific rules
        if len(rule.action_types) == 1:
            priority += 2
        
        if len(rule.user_roles) == 1:
            priority += 1
        
        # Higher priority for stricter approval methods
        approval_priority = {
            ApprovalMethod.NONE: 0,
            ApprovalMethod.VOICE_REAUTH: 1,
            ApprovalMethod.UI_CONFIRM: 2,
            ApprovalMethod.BIOMETRIC: 3
        }
        priority += approval_priority.get(rule.approval_method, 0)
        
        return priority
    
    def _load_default_rules(self):
        """Load default policy rules."""
        self.rules = [
            PolicyRule(
                rule_id="default_low_risk",
                name="Default Low Risk Policy",
                description="Allows low-risk actions without approval",
                action_types=["link_inspect", "system_scan"],
                user_roles=["admin", "user", "guest"],
                conditions={},
                risk_level=RiskLevel.LOW,
                approval_method=ApprovalMethod.NONE
            ),
            PolicyRule(
                rule_id="default_medium_risk",
                name="Default Medium Risk Policy",
                description="Requires voice re-auth for medium-risk actions",
                action_types=["vault_access", "file_modify"],
                user_roles=["admin", "user"],
                conditions={},
                risk_level=RiskLevel.MEDIUM,
                approval_method=ApprovalMethod.VOICE_REAUTH
            ),
            PolicyRule(
                rule_id="default_high_risk",
                name="Default High Risk Policy",
                description="Requires UI confirmation for high-risk actions",
                action_types=["ui_automation", "process_terminate"],
                user_roles=["admin", "user"],
                conditions={},
                risk_level=RiskLevel.HIGH,
                approval_method=ApprovalMethod.UI_CONFIRM
            ),
            PolicyRule(
                rule_id="admin_critical",
                name="Admin Critical Actions",
                description="Only admins can perform critical actions",
                action_types=["process_terminate", "file_modify"],
                user_roles=["admin"],
                conditions={"resource_patterns": ["windows", "system32"]},
                risk_level=RiskLevel.CRITICAL,
                approval_method=ApprovalMethod.UI_CONFIRM
            )
        ]
    
    async def _load_rules(self):
        """Load rules from file."""
        try:
            with open(self.policy_file, 'r') as f:
                rules_data = json.load(f)
                self.rules = [PolicyRule(**rule) for rule in rules_data]
        except Exception as e:
            print(f"Error loading policy rules: {e}")
            self._load_default_rules()
    
    async def _save_rules(self):
        """Save rules to file."""
        try:
            with open(self.policy_file, 'w') as f:
                rules_data = [rule.dict() for rule in self.rules]
                json.dump(rules_data, f, indent=2)
        except Exception as e:
            print(f"Error saving policy rules: {e}")
    
    async def get_status(self) -> Dict[str, Any]:
        """Get policy engine status."""
        return {
            "initialized": True,
            "rules_count": len(self.rules),
            "enabled_rules": len([r for r in self.rules if r.enabled]),
            "risk_assessor": "active"
        }

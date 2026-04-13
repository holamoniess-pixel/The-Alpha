"""
RAVER Vault Access Control Module

Provides role-based access control, permission checking, and access policies
for vault secrets and operations.
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, field
import uuid


class Permission(Enum):
    """Vault permissions."""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    SHARE = "share"
    ADMIN = "admin"


class AccessLevel(Enum):
    """Access levels for secrets."""
    PRIVATE = "private"      # Only owner
    TEAM = "team"           # Owner + specified users/roles
    ORG = "organization"    # All users in organization
    PUBLIC = "public"       # All authenticated users


@dataclass
class AccessPolicy:
    """Access policy for a secret."""
    policy_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    access_level: AccessLevel = AccessLevel.PRIVATE
    allowed_users: Set[str] = field(default_factory=set)
    allowed_roles: Set[str] = field(default_factory=set)
    denied_users: Set[str] = field(default_factory=set)
    denied_roles: Set[str] = field(default_factory=set)
    time_restrictions: Optional[Dict[str, Any]] = None
    ip_restrictions: Optional[List[str]] = None
    requires_approval: bool = False
    approval_users: Set[str] = field(default_factory=set)
    approval_roles: Set[str] = field(default_factory=set)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    created_by: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "policy_id": self.policy_id,
            "access_level": self.access_level.value,
            "allowed_users": list(self.allowed_users),
            "allowed_roles": list(self.allowed_roles),
            "denied_users": list(self.denied_users),
            "denied_roles": list(self.denied_roles),
            "time_restrictions": self.time_restrictions,
            "ip_restrictions": self.ip_restrictions,
            "requires_approval": self.requires_approval,
            "approval_users": list(self.approval_users),
            "approval_roles": list(self.approval_roles),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "created_by": self.created_by
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AccessPolicy':
        """Create from dictionary."""
        return cls(
            policy_id=data["policy_id"],
            access_level=AccessLevel(data["access_level"]),
            allowed_users=set(data.get("allowed_users", [])),
            allowed_roles=set(data.get("allowed_roles", [])),
            denied_users=set(data.get("denied_users", [])),
            denied_roles=set(data.get("denied_roles", [])),
            time_restrictions=data.get("time_restrictions"),
            ip_restrictions=data.get("ip_restrictions"),
            requires_approval=data.get("requires_approval", False),
            approval_users=set(data.get("approval_users", [])),
            approval_roles=set(data.get("approval_roles", [])),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            created_by=data["created_by"]
        )


@dataclass
class AccessRequest:
    """Represents an access request to a resource."""
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    resource_id: str = ""
    permission: Permission = Permission.READ
    requested_at: datetime = field(default_factory=datetime.utcnow)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AccessDecision:
    """Result of an access control decision."""
    allowed: bool
    permission: Permission
    reason: str
    requires_approval: bool = False
    approval_required_from: Set[str] = field(default_factory=set)
    conditions: Dict[str, Any] = field(default_factory=dict)
    decision_time: datetime = field(default_factory=datetime.utcnow)


class AccessController:
    """Controls access to vault resources based on policies."""
    
    def __init__(self):
        self.user_roles: Dict[str, Set[str]] = {}
        self.role_permissions: Dict[str, Set[Permission]] = {}
        self.policies: Dict[str, AccessPolicy] = {}
        self.pending_approvals: Dict[str, AccessRequest] = {}
        
        self._initialize_default_roles()
    
    def _initialize_default_roles(self):
        """Initialize default roles and permissions."""
        # Define default role permissions
        self.role_permissions = {
            "guest": {Permission.READ},
            "user": {Permission.READ, Permission.WRITE},
            "power_user": {Permission.READ, Permission.WRITE, Permission.SHARE},
            "admin": {Permission.READ, Permission.WRITE, Permission.DELETE, Permission.SHARE, Permission.ADMIN},
            "system": set(Permission)  # System has all permissions
        }
    
    def assign_role(self, user_id: str, role: str):
        """Assign a role to a user."""
        if user_id not in self.user_roles:
            self.user_roles[user_id] = set()
        self.user_roles[user_id].add(role)
    
    def remove_role(self, user_id: str, role: str):
        """Remove a role from a user."""
        if user_id in self.user_roles:
            self.user_roles[user_id].discard(role)
    
    def get_user_roles(self, user_id: str) -> Set[str]:
        """Get all roles for a user."""
        return self.user_roles.get(user_id, set())
    
    def get_user_permissions(self, user_id: str) -> Set[Permission]:
        """Get all permissions for a user based on their roles."""
        user_roles = self.get_user_roles(user_id)
        permissions = set()
        
        for role in user_roles:
            role_perms = self.role_permissions.get(role, set())
            permissions.update(role_perms)
        
        return permissions
    
    def create_policy(self, policy: AccessPolicy) -> str:
        """Create a new access policy."""
        self.policies[policy.policy_id] = policy
        return policy.policy_id
    
    def update_policy(self, policy_id: str, updates: Dict[str, Any]) -> bool:
        """Update an existing access policy."""
        if policy_id not in self.policies:
            return False
        
        policy = self.policies[policy_id]
        
        for key, value in updates.items():
            if hasattr(policy, key):
                if key in ["allowed_users", "denied_users", "approval_users"]:
                    setattr(policy, key, set(value))
                elif key in ["allowed_roles", "denied_roles", "approval_roles"]:
                    setattr(policy, key, set(value))
                elif key == "access_level":
                    setattr(policy, key, AccessLevel(value))
                else:
                    setattr(policy, key, value)
        
        policy.updated_at = datetime.utcnow()
        return True
    
    def delete_policy(self, policy_id: str) -> bool:
        """Delete an access policy."""
        return self.policies.pop(policy_id, None) is not None
    
    def check_access(self, request: AccessRequest, policy: AccessPolicy) -> AccessDecision:
        """Check if a user has access based on a policy."""
        user_id = request.user_id
        user_roles = self.get_user_roles(user_id)
        user_permissions = self.get_user_permissions(user_id)
        
        # Check denied lists first (deny overrides allow)
        if user_id in policy.denied_users:
            return AccessDecision(
                allowed=False,
                permission=request.permission,
                reason="User explicitly denied access"
            )
        
        if any(role in policy.denied_roles for role in user_roles):
            return AccessDecision(
                allowed=False,
                permission=request.permission,
                reason="User role explicitly denied access"
            )
        
        # Check if user has the required permission
        if request.permission not in user_permissions:
            return AccessDecision(
                allowed=False,
                permission=request.permission,
                reason="User lacks required permission"
            )
        
        # Check access level
        allowed = False
        
        if policy.access_level == AccessLevel.PUBLIC:
            allowed = True
        elif policy.access_level == AccessLevel.ORG:
            # Assuming all authenticated users are in the organization
            allowed = True
        elif policy.access_level == AccessLevel.TEAM:
            allowed = (user_id in policy.allowed_users or 
                      any(role in policy.allowed_roles for role in user_roles))
        elif policy.access_level == AccessLevel.PRIVATE:
            # Only allowed if explicitly allowed
            allowed = (user_id in policy.allowed_users or 
                      any(role in policy.allowed_roles for role in user_roles))
        
        if not allowed:
            return AccessDecision(
                allowed=False,
                permission=request.permission,
                reason="Access level does not permit access"
            )
        
        # Check time restrictions
        if policy.time_restrictions:
            if not self._check_time_restrictions(policy.time_restrictions):
                return AccessDecision(
                    allowed=False,
                    permission=request.permission,
                    reason="Access outside allowed time window"
                )
        
        # Check IP restrictions
        if policy.ip_restrictions and request.ip_address:
            if request.ip_address not in policy.ip_restrictions:
                return AccessDecision(
                    allowed=False,
                    permission=request.permission,
                    reason="IP address not allowed"
                )
        
        # Check if approval is required
        if policy.requires_approval:
            approval_users = set(policy.approval_users)
            approval_roles = set(policy.approval_roles)
            
            # Add users who have the required approval roles
            for user, roles in self.user_roles.items():
                if any(role in approval_roles for role in roles):
                    approval_users.add(user)
            
            return AccessDecision(
                allowed=False,
                permission=request.permission,
                reason="Approval required",
                requires_approval=True,
                approval_required_from=approval_users
            )
        
        return AccessDecision(
            allowed=True,
            permission=request.permission,
            reason="Access granted"
        )
    
    def _check_time_restrictions(self, restrictions: Dict[str, Any]) -> bool:
        """Check if current time satisfies time restrictions."""
        now = datetime.utcnow()
        
        # Check allowed days of week
        if "allowed_days" in restrictions:
            allowed_days = set(restrictions["allowed_days"])
            current_day = now.strftime("%A").lower()
            if current_day not in allowed_days:
                return False
        
        # Check allowed hours
        if "allowed_hours" in restrictions:
            allowed_hours = restrictions["allowed_hours"]
            current_hour = now.hour
            if isinstance(allowed_hours, list):
                if current_hour not in allowed_hours:
                    return False
            elif isinstance(allowed_hours, dict):
                start_hour = allowed_hours.get("start", 0)
                end_hour = allowed_hours.get("end", 23)
                if not (start_hour <= current_hour <= end_hour):
                    return False
        
        # Check date range
        if "start_date" in restrictions:
            start_date = datetime.fromisoformat(restrictions["start_date"])
            if now < start_date:
                return False
        
        if "end_date" in restrictions:
            end_date = datetime.fromisoformat(restrictions["end_date"])
            if now > end_date:
                return False
        
        return True
    
    def request_approval(self, request: AccessRequest) -> str:
        """Submit an access request for approval."""
        self.pending_approvals[request.request_id] = request
        return request.request_id
    
    def approve_request(self, request_id: str, approver_id: str) -> bool:
        """Approve an access request."""
        if request_id not in self.pending_approvals:
            return False
        
        request = self.pending_approvals[request_id]
        approver_roles = self.get_user_roles(approver_id)
        approver_permissions = self.get_user_permissions(approver_id)
        
        # Check if approver has approval permissions
        if Permission.ADMIN not in approver_permissions:
            return False
        
        # Remove from pending and grant access
        del self.pending_approvals[request_id]
        return True
    
    def deny_request(self, request_id: str, approver_id: str, reason: str = "") -> bool:
        """Deny an access request."""
        if request_id not in self.pending_approvals:
            return False
        
        request = self.pending_approvals[request_id]
        approver_permissions = self.get_user_permissions(approver_id)
        
        # Check if approver has approval permissions
        if Permission.ADMIN not in approver_permissions:
            return False
        
        # Remove from pending
        del self.pending_approvals[request_id]
        return True
    
    def get_pending_requests(self, approver_id: str) -> List[AccessRequest]:
        """Get pending approval requests for an approver."""
        approver_roles = self.get_user_roles(approver_id)
        approver_permissions = self.get_user_permissions(approver_id)
        
        # Only admins can see pending requests
        if Permission.ADMIN not in approver_permissions:
            return []
        
        return list(self.pending_approvals.values())
    
    def get_policy(self, policy_id: str) -> Optional[AccessPolicy]:
        """Get an access policy by ID."""
        return self.policies.get(policy_id)
    
    def list_policies(self, user_id: Optional[str] = None) -> List[AccessPolicy]:
        """List access policies, optionally filtered by creator."""
        policies = list(self.policies.values())
        
        if user_id:
            policies = [p for p in policies if p.created_by == user_id]
        
        return policies

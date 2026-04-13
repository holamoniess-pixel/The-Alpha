"""
Access control for vault operations.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum

from ...raver_shared.schemas import UserRole, VaultSecret


class AccessPolicy:
    """Access policy for vault operations."""
    
    def __init__(self, allowed_roles: List[UserRole], 
                 allowed_actions: List[str],
                 time_restrictions: Optional[Dict[str, Any]] = None):
        self.allowed_roles = allowed_roles
        self.allowed_actions = allowed_actions
        self.time_restrictions = time_restrictions or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert policy to dictionary."""
        return {
            "allowed_roles": [role.value for role in self.allowed_roles],
            "allowed_actions": self.allowed_actions,
            "time_restrictions": self.time_restrictions
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AccessPolicy":
        """Create policy from dictionary."""
        return cls(
            allowed_roles=[UserRole(role) for role in data["allowed_roles"]],
            allowed_actions=data["allowed_actions"],
            time_restrictions=data.get("time_restrictions")
        )


class AccessController:
    """Controls access to vault operations based on roles and policies."""
    
    def __init__(self):
        self.role_hierarchy = {
            UserRole.GUEST: 0,
            UserRole.USER: 1,
            UserRole.ADMIN: 2
        }
    
    def can_access_secret(self, user_roles: List[UserRole], 
                         secret: VaultSecret, 
                         action: str) -> bool:
        """
        Check if user can perform action on secret.
        
        Args:
            user_roles: List of user roles
            secret: Target secret
            action: Action to perform (read, write, delete)
            
        Returns:
            True if access is allowed
        """
        try:
            policy = AccessPolicy.from_dict(secret.access_policy)
            
            # Check role permission
            if not any(role in policy.allowed_roles for role in user_roles):
                return False
            
            # Check action permission
            if action not in policy.allowed_actions:
                return False
            
            # Check time restrictions
            if policy.time_restrictions:
                now = datetime.now()
                
                # Check business hours restriction
                if "business_hours" in policy.time_restrictions:
                    business_hours = policy.time_restrictions["business_hours"]
                    start_hour = business_hours.get("start", 9)
                    end_hour = business_hours.get("end", 17)
                    
                    if not (start_hour <= now.hour < end_hour):
                        return False
                
                # Check day restrictions
                if "allowed_days" in policy.time_restrictions:
                    allowed_days = policy.time_restrictions["allowed_days"]
                    current_day = now.weekday()  # 0 = Monday, 6 = Sunday
                    
                    if current_day not in allowed_days:
                        return False
            
            return True
            
        except Exception as e:
            print(f"Error checking access: {e}")
            return False
    
    def can_create_secret(self, user_roles: List[UserRole]) -> bool:
        """Check if user can create secrets."""
        return UserRole.USER in user_roles or UserRole.ADMIN in user_roles
    
    def can_delete_secret(self, user_roles: List[UserRole], 
                         secret: VaultSecret) -> bool:
        """Check if user can delete secret."""
        # Admin can delete any secret
        if UserRole.ADMIN in user_roles:
            return True
        
        # Users can only delete their own secrets
        if UserRole.USER in user_roles:
            return True  # Additional ownership check needed
        
        return False
    
    def get_user_capabilities(self, user_roles: List[UserRole]) -> List[str]:
        """Get list of capabilities for user roles."""
        capabilities = []
        
        for role in user_roles:
            if role == UserRole.GUEST:
                capabilities.extend([
                    "secrets.list_own",
                    "secrets.read_own"
                ])
            elif role == UserRole.USER:
                capabilities.extend([
                    "secrets.list_own",
                    "secrets.read_own",
                    "secrets.create_own",
                    "secrets.update_own",
                    "secrets.delete_own"
                ])
            elif role == UserRole.ADMIN:
                capabilities.extend([
                    "secrets.list_all",
                    "secrets.read_all",
                    "secrets.create_any",
                    "secrets.update_any",
                    "secrets.delete_any",
                    "users.create",
                    "users.update",
                    "users.delete",
                    "vault.configure"
                ])
        
        return list(set(capabilities))  # Remove duplicates
    
    def check_capability(self, user_roles: List[UserRole], 
                        required_capability: str) -> bool:
        """Check if user has specific capability."""
        user_capabilities = self.get_user_capabilities(user_roles)
        return required_capability in user_capabilities
    
    def create_default_policy(self, owner_role: UserRole) -> AccessPolicy:
        """Create default access policy for new secret."""
        if owner_role == UserRole.GUEST:
            allowed_roles = [UserRole.GUEST]
        elif owner_role == UserRole.USER:
            allowed_roles = [UserRole.USER, UserRole.ADMIN]
        else:  # ADMIN
            allowed_roles = [UserRole.ADMIN]
        
        return AccessPolicy(
            allowed_roles=allowed_roles,
            allowed_actions=["read", "update", "delete"],
            time_restrictions={}
        )

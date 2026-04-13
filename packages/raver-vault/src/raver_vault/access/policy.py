"""Access policy manager for RAVER Vault."""

from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import datetime, timedelta


class AccessPolicyManager:
    """Manages access policies for vault secrets."""
    
    def __init__(self):
        """Initialize access policy manager."""
        self.default_policies = {
            "owner": {
                "can_read": True,
                "can_write": True,
                "can_delete": True,
                "can_share": False
            },
            "admin": {
                "can_read": True,
                "can_write": True,
                "can_delete": True,
                "can_share": True
            },
            "readonly": {
                "can_read": True,
                "can_write": False,
                "can_delete": False,
                "can_share": False
            }
        }
    
    def check_access(
        self,
        user_id: UUID,
        secret_id: UUID,
        action: str,
        user_roles: List[str],
        access_policy: Dict[str, Any],
        owner_user_id: UUID
    ) -> bool:
        """Check if user has access to perform action on secret.
        
        Args:
            user_id: User requesting access
            secret_id: Secret being accessed
            action: Action to perform (read, write, delete, share)
            user_roles: List of user roles
            access_policy: Access policy for the secret
            owner_user_id: Owner of the secret
            
        Returns:
            True if access is granted
        """
        # Owner has full access
        if user_id == owner_user_id:
            return True
        
        # Check role-based access
        for role in user_roles:
            if role in self.default_policies:
                role_policy = self.default_policies[role]
                action_key = f"can_{action}"
                if role_policy.get(action_key, False):
                    # Check additional policy constraints
                    if self._check_additional_constraints(
                        user_id, secret_id, access_policy
                    ):
                        return True
        
        # Check explicit user permissions in access policy
        user_permissions = access_policy.get("user_permissions", {})
        if str(user_id) in user_permissions:
            user_perm = user_permissions[str(user_id)]
            if user_perm.get(f"can_{action}", False):
                return True
        
        return False
    
    def _check_additional_constraints(
        self,
        user_id: UUID,
        secret_id: UUID,
        access_policy: Dict[str, Any]
    ) -> bool:
        """Check additional access constraints.
        
        Args:
            user_id: User requesting access
            secret_id: Secret being accessed
            access_policy: Access policy constraints
            
        Returns:
            True if constraints are satisfied
        """
        # Check time-based access
        time_constraints = access_policy.get("time_constraints", {})
        if time_constraints:
            now = datetime.utcnow()
            
            # Check allowed hours
            allowed_hours = time_constraints.get("allowed_hours")
            if allowed_hours:
                current_hour = now.hour
                if current_hour not in allowed_hours:
                    return False
            
            # Check expiry
            expires_at = time_constraints.get("expires_at")
            if expires_at:
                expiry_time = datetime.fromisoformat(expires_at)
                if now > expiry_time:
                    return False
        
        # Check access count limits
        access_limits = access_policy.get("access_limits", {})
        if access_limits:
            # This would need to be implemented with audit tracking
            # For now, just pass through
            pass
        
        return True
    
    def create_access_policy(
        self,
        owner_permissions: Dict[str, bool] = None,
        user_permissions: Dict[str, Dict[str, bool]] = None,
        time_constraints: Dict[str, Any] = None,
        access_limits: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Create access policy for a secret.
        
        Args:
            owner_permissions: Permissions for owner
            user_permissions: Specific user permissions
            time_constraints: Time-based access constraints
            access_limits: Access count limits
            
        Returns:
            Access policy dictionary
        """
        policy = {
            "version": "1.0",
            "created_at": datetime.utcnow().isoformat()
        }
        
        if owner_permissions:
            policy["owner_permissions"] = owner_permissions
        
        if user_permissions:
            policy["user_permissions"] = user_permissions
        
        if time_constraints:
            policy["time_constraints"] = time_constraints
        
        if access_limits:
            policy["access_limits"] = access_limits
        
        return policy
    
    def grant_user_access(
        self,
        access_policy: Dict[str, Any],
        user_id: UUID,
        permissions: Dict[str, bool]
    ) -> Dict[str, Any]:
        """Grant specific permissions to a user.
        
        Args:
            access_policy: Existing access policy
            user_id: User to grant permissions to
            permissions: Permissions to grant
            
        Returns:
            Updated access policy
        """
        if "user_permissions" not in access_policy:
            access_policy["user_permissions"] = {}
        
        access_policy["user_permissions"][str(user_id)] = permissions
        access_policy["updated_at"] = datetime.utcnow().isoformat()
        
        return access_policy
    
    def revoke_user_access(
        self,
        access_policy: Dict[str, Any],
        user_id: UUID
    ) -> Dict[str, Any]:
        """Revoke all permissions for a user.
        
        Args:
            access_policy: Existing access policy
            user_id: User to revoke permissions from
            
        Returns:
            Updated access policy
        """
        if "user_permissions" in access_policy:
            access_policy["user_permissions"].pop(str(user_id), None)
            access_policy["updated_at"] = datetime.utcnow().isoformat()
        
        return access_policy

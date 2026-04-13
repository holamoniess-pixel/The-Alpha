"""
RAVER Vault Manager

Main interface for the vault system that combines cryptography, storage,
and access control into a unified API.
"""

import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

from .crypto import CryptoManager, KDFType
from .storage import SecretStorage, SecretEntry
from .access import AccessController, AccessPolicy, AccessLevel, AccessRequest, Permission


class VaultManager:
    """Main vault management interface."""
    
    def __init__(self, vault_path: Optional[Path] = None):
        self.crypto_manager = CryptoManager(vault_path)
        self.storage = SecretStorage(vault_path)
        self.access_controller = AccessController()
        self._current_user_id: Optional[str] = None
    
    def initialize_vault(self, password: str, admin_user_id: str = "admin") -> bool:
        """Initialize a new vault with an admin user."""
        try:
            # Initialize crypto
            success = self.crypto_manager.initialize_vault(password)
            if not success:
                return False
            
            # Set up admin user
            self.access_controller.assign_role(admin_user_id, "admin")
            self._current_user_id = admin_user_id
            
            return True
        except Exception:
            return False
    
    def unlock_vault(self, password: str, user_id: Optional[str] = None) -> bool:
        """Unlock the vault and set current user."""
        if not self.crypto_manager.unlock_vault(password):
            return False
        
        if user_id:
            self._current_user_id = user_id
        
        return True
    
    def lock_vault(self):
        """Lock the vault and clear current user."""
        self.crypto_manager.lock_vault()
        self._current_user_id = None
    
    def is_unlocked(self) -> bool:
        """Check if vault is unlocked."""
        return self.crypto_manager.is_unlocked()
    
    def set_current_user(self, user_id: str):
        """Set the current user context."""
        self._current_user_id = user_id
    
    def create_secret(self,
                     service: str,
                     label: str,
                     secret_data: str,
                     description: str = "",
                     tags: List[str] = None,
                     access_level: AccessLevel = AccessLevel.PRIVATE,
                     allowed_users: List[str] = None,
                     allowed_roles: List[str] = None) -> Optional[str]:
        """Create a new secret in the vault."""
        if not self.is_unlocked() or not self._current_user_id:
            return None
        
        try:
            # Encrypt the secret data
            secret_bytes = secret_data.encode('utf-8')
            encrypted_data = self.crypto_manager.encrypt_data(secret_bytes)
            
            # Create access policy
            policy = AccessPolicy(
                access_level=access_level,
                allowed_users=set(allowed_users or []),
                allowed_roles=set(allowed_roles or []),
                created_by=self._current_user_id
            )
            
            # Create secret entry
            secret = SecretEntry(
                secret_id=str(hashlib.sha256(f"{service}{label}{datetime.utcnow()}".encode()).hexdigest())[:32],
                service=service,
                label=label,
                owner_user_id=self._current_user_id,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                key_hash_sha256=hashlib.sha256(secret_bytes).hexdigest(),
                ciphertext_b64=encrypted_data["ciphertext"],
                nonce_b64=encrypted_data["nonce"],
                kdf_params=encrypted_data["algorithm"],
                access_policy=policy.to_dict(),
                tags=tags or [],
                description=description
            )
            
            # Store the secret
            success = self.storage.store_secret(secret)
            if success:
                # Store the access policy
                self.access_controller.create_policy(policy)
                
                # Log access
                self.storage.log_access(
                    secret.secret_id,
                    self._current_user_id,
                    "create",
                    True
                )
                
                return secret.secret_id
            
            return None
            
        except Exception:
            return None
    
    def get_secret(self, secret_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve and decrypt a secret."""
        if not self.is_unlocked() or not self._current_user_id:
            return None
        
        # Get secret from storage
        secret = self.storage.get_secret(secret_id)
        if not secret:
            return None
        
        # Check access permissions
        policy_data = secret.access_policy
        policy = AccessPolicy.from_dict(policy_data)
        
        request = AccessRequest(
            user_id=self._current_user_id,
            resource_id=secret_id,
            permission=Permission.READ
        )
        
        decision = self.access_controller.check_access(request, policy)
        
        if not decision.allowed:
            self.storage.log_access(
                secret_id,
                self._current_user_id,
                "read",
                False,
                decision.reason
            )
            return None
        
        try:
            # Decrypt the secret
            encrypted_data = {
                "ciphertext": secret.ciphertext_b64,
                "nonce": secret.nonce_b64
            }
            
            decrypted_bytes = self.crypto_manager.decrypt_data(encrypted_data)
            secret_data = decrypted_bytes.decode('utf-8')
            
            # Log successful access
            self.storage.log_access(
                secret_id,
                self._current_user_id,
                "read",
                True
            )
            
            return {
                "secret_id": secret.secret_id,
                "service": secret.service,
                "label": secret.label,
                "data": secret_data,
                "description": secret.description,
                "tags": secret.tags,
                "created_at": secret.created_at.isoformat(),
                "updated_at": secret.updated_at.isoformat(),
                "owner_user_id": secret.owner_user_id
            }
            
        except Exception as e:
            self.storage.log_access(
                secret_id,
                self._current_user_id,
                "read",
                False,
                f"Decryption failed: {str(e)}"
            )
            return None
    
    def update_secret(self,
                     secret_id: str,
                     service: Optional[str] = None,
                     label: Optional[str] = None,
                     secret_data: Optional[str] = None,
                     description: Optional[str] = None,
                     tags: Optional[List[str]] = None) -> bool:
        """Update an existing secret."""
        if not self.is_unlocked() or not self._current_user_id:
            return False
        
        # Get existing secret
        secret = self.storage.get_secret(secret_id)
        if not secret:
            return False
        
        # Check write permissions
        policy = AccessPolicy.from_dict(secret.access_policy)
        request = AccessRequest(
            user_id=self._current_user_id,
            resource_id=secret_id,
            permission=Permission.WRITE
        )
        
        decision = self.access_controller.check_access(request, policy)
        if not decision.allowed:
            self.storage.log_access(
                secret_id,
                self._current_user_id,
                "update",
                False,
                decision.reason
            )
            return False
        
        try:
            updates = {}
            
            # Update fields
            if service is not None:
                updates["service"] = service
            if label is not None:
                updates["label"] = label
            if description is not None:
                updates["description"] = description
            if tags is not None:
                updates["tags"] = tags
            
            # Update secret data if provided
            if secret_data is not None:
                secret_bytes = secret_data.encode('utf-8')
                encrypted_data = self.crypto_manager.encrypt_data(secret_bytes)
                
                updates["ciphertext_b64"] = encrypted_data["ciphertext"]
                updates["nonce_b64"] = encrypted_data["nonce"]
                updates["key_hash_sha256"] = hashlib.sha256(secret_bytes).hexdigest()
            
            # Store updates
            success = self.storage.update_secret(secret_id, updates)
            
            if success:
                self.storage.log_access(
                    secret_id,
                    self._current_user_id,
                    "update",
                    True
                )
            
            return success
            
        except Exception:
            return False
    
    def delete_secret(self, secret_id: str, permanent: bool = False) -> bool:
        """Delete a secret."""
        if not self.is_unlocked() or not self._current_user_id:
            return False
        
        # Get existing secret
        secret = self.storage.get_secret(secret_id)
        if not secret:
            return False
        
        # Check delete permissions
        policy = AccessPolicy.from_dict(secret.access_policy)
        request = AccessRequest(
            user_id=self._current_user_id,
            resource_id=secret_id,
            permission=Permission.DELETE
        )
        
        decision = self.access_controller.check_access(request, policy)
        if not decision.allowed:
            self.storage.log_access(
                secret_id,
                self._current_user_id,
                "delete",
                False,
                decision.reason
            )
            return False
        
        # Only owner can permanently delete
        if permanent and secret.owner_user_id != self._current_user_id:
            return False
        
        success = self.storage.delete_secret(secret_id, self._current_user_id, permanent)
        
        if success:
            self.storage.log_access(
                secret_id,
                self._current_user_id,
                "delete",
                True
            )
        
        return success
    
    def list_secrets(self,
                    service: Optional[str] = None,
                    tags: Optional[List[str]] = None,
                    include_deleted: bool = False) -> List[Dict[str, Any]]:
        """List secrets accessible to the current user."""
        if not self.is_unlocked() or not self._current_user_id:
            return []
        
        # Get all secrets
        all_secrets = self.storage.list_secrets(
            service=service,
            tags=tags,
            include_deleted=include_deleted
        )
        
        accessible_secrets = []
        
        for secret in all_secrets:
            # Check access permissions
            policy = AccessPolicy.from_dict(secret.access_policy)
            request = AccessRequest(
                user_id=self._current_user_id,
                resource_id=secret.secret_id,
                permission=Permission.READ
            )
            
            decision = self.access_controller.check_access(request, policy)
            
            if decision.allowed:
                accessible_secrets.append({
                    "secret_id": secret.secret_id,
                    "service": secret.service,
                    "label": secret.label,
                    "description": secret.description,
                    "tags": secret.tags,
                    "created_at": secret.created_at.isoformat(),
                    "updated_at": secret.updated_at.isoformat(),
                    "owner_user_id": secret.owner_user_id,
                    "access_level": policy.access_level.value
                })
        
        return accessible_secrets
    
    def search_secrets(self, query: str) -> List[Dict[str, Any]]:
        """Search secrets accessible to the current user."""
        if not self.is_unlocked() or not self._current_user_id:
            return []
        
        # Search in storage
        all_secrets = self.storage.search_secrets(query, self._current_user_id)
        
        accessible_secrets = []
        
        for secret in all_secrets:
            # Check access permissions
            policy = AccessPolicy.from_dict(secret.access_policy)
            request = AccessRequest(
                user_id=self._current_user_id,
                resource_id=secret.secret_id,
                permission=Permission.READ
            )
            
            decision = self.access_controller.check_access(request, policy)
            
            if decision.allowed:
                accessible_secrets.append({
                    "secret_id": secret.secret_id,
                    "service": secret.service,
                    "label": secret.label,
                    "description": secret.description,
                    "tags": secret.tags,
                    "created_at": secret.created_at.isoformat(),
                    "updated_at": secret.updated_at.isoformat(),
                    "owner_user_id": secret.owner_user_id,
                    "access_level": policy.access_level.value
                })
        
        return accessible_secrets
    
    def share_secret(self,
                    secret_id: str,
                    target_user_id: str,
                    access_level: AccessLevel = AccessLevel.TEAM) -> bool:
        """Share a secret with another user."""
        if not self.is_unlocked() or not self._current_user_id:
            return False
        
        # Get secret
        secret = self.storage.get_secret(secret_id)
        if not secret:
            return False
        
        # Only owner can share
        if secret.owner_user_id != self._current_user_id:
            return False
        
        # Update access policy
        policy = AccessPolicy.from_dict(secret.access_policy)
        policy.access_level = access_level
        policy.allowed_users.add(target_user_id)
        policy.updated_at = datetime.utcnow()
        
        # Store updated policy
        success = self.access_controller.update_policy(policy.policy_id, policy.to_dict())
        
        if success:
            # Update secret with new policy
            self.storage.update_secret(secret_id, {"access_policy": policy.to_dict()})
            
            self.storage.log_access(
                secret_id,
                self._current_user_id,
                "share",
                True,
                f"Shared with {target_user_id}"
            )
        
        return success
    
    def get_access_logs(self, secret_id: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get access logs for secrets."""
        if not self.is_unlocked() or not self._current_user_id:
            return []
        
        # Only admins can see all logs, users can only see their own
        user_roles = self.access_controller.get_user_roles(self._current_user_id)
        is_admin = "admin" in user_roles
        
        if not is_admin:
            # Users can only see logs for their own actions
            return self.storage.get_access_logs(user_id=self._current_user_id, limit=limit)
        else:
            # Admins can see all logs
            return self.storage.get_access_logs(secret_id=secret_id, limit=limit)
    
    def get_vault_statistics(self) -> Dict[str, Any]:
        """Get vault statistics."""
        if not self.is_unlocked() or not self._current_user_id:
            return {}
        
        user_roles = self.access_controller.get_user_roles(self._current_user_id)
        is_admin = "admin" in user_roles
        
        if is_admin:
            # Admins can see full statistics
            return self.storage.get_statistics()
        else:
            # Regular users can only see their own statistics
            return self.storage.get_statistics(user_id=self._current_user_id)
    
    def change_password(self, old_password: str, new_password: str) -> bool:
        """Change the vault master password."""
        return self.crypto_manager.change_password(old_password, new_password)
    
    def get_vault_info(self) -> Dict[str, Any]:
        """Get information about the vault."""
        key_info = self.crypto_manager.get_key_info()
        stats = self.get_vault_statistics()
        
        return {
            "unlocked": self.is_unlocked(),
            "current_user": self._current_user_id,
            "key_info": key_info,
            "statistics": stats
        }

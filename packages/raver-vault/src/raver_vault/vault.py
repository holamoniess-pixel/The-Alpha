"""Main Vault class for RAVER."""

import os
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID

from raver_shared.schemas import VaultEntry, Secret
from .crypto.encryption import EncryptionManager
from .storage.database import DatabaseManager
from .access.policy import AccessPolicyManager


class Vault:
    """Main vault interface for encrypted secret storage."""
    
    def __init__(self, db_path: str = "raver_vault.db", master_key: bytes = None):
        """Initialize vault.
        
        Args:
            db_path: Path to vault database
            master_key: Optional master encryption key
        """
        self.db_manager = DatabaseManager(db_path)
        self.encryption_manager = EncryptionManager(master_key)
        self.access_manager = AccessPolicyManager()
    
    def store_secret(
        self,
        service: str,
        label: str,
        secret_data: str,
        owner_user_id: UUID,
        access_policy: Dict[str, Any] = None
    ) -> UUID:
        """Store a new secret in the vault.
        
        Args:
            service: Service name (e.g., "openai", "github")
            label: Human-readable label
            secret_data: Secret data to encrypt
            owner_user_id: Owner user UUID
            access_policy: Optional access policy
            
        Returns:
            UUID of stored secret
        """
        # Encrypt the secret
        encrypted_data = self.encryption_manager.encrypt_secret(secret_data)
        
        # Create access policy if not provided
        if access_policy is None:
            access_policy = self.access_manager.create_access_policy()
        
        # Create vault entry
        entry = VaultEntry(
            service=service,
            label=label,
            owner_user_id=owner_user_id,
            key_hash_sha256=encrypted_data["key_hash_sha256"],
            ciphertext_b64=encrypted_data["ciphertext_b64"],
            nonce_b64=encrypted_data["nonce_b64"],
            kdf_params={},  # Using master key, no KDF needed
            access_policy=access_policy
        )
        
        # Store in database
        if self.db_manager.store_secret(entry):
            return entry.secret_id
        else:
            raise Exception("Failed to store secret")
    
    def retrieve_secret(
        self,
        secret_id: UUID,
        requesting_user_id: UUID,
        user_roles: List[str]
    ) -> Optional[str]:
        """Retrieve and decrypt a secret.
        
        Args:
            secret_id: UUID of secret to retrieve
            requesting_user_id: User requesting access
            user_roles: List of user roles
            
        Returns:
            Decrypted secret if access granted, None otherwise
        """
        # Get vault entry
        entry = self.db_manager.get_secret(secret_id)
        if not entry:
            return None
        
        # Check access permissions
        if not self.access_manager.check_access(
            requesting_user_id,
            secret_id,
            "read",
            user_roles,
            entry.access_policy,
            entry.owner_user_id
        ):
            return None
        
        # Decrypt and return secret
        encrypted_data = {
            "ciphertext_b64": entry.ciphertext_b64,
            "nonce_b64": entry.nonce_b64
        }
        
        try:
            return self.encryption_manager.decrypt_secret(encrypted_data)
        except Exception:
            return None
    
    def list_secrets(
        self,
        user_id: UUID,
        user_roles: List[str]
    ) -> List[Secret]:
        """List secrets accessible to user.
        
        Args:
            user_id: User UUID
            user_roles: List of user roles
            
        Returns:
            List of accessible secrets (without actual secret data)
        """
        # Get all user secrets
        entries = self.db_manager.list_user_secrets(user_id)
        
        accessible_secrets = []
        for entry in entries:
            # Check if user can read this secret
            if self.access_manager.check_access(
                user_id,
                entry.secret_id,
                "read",
                user_roles,
                entry.access_policy,
                entry.owner_user_id
            ):
                accessible_secrets.append(Secret(
                    secret_id=entry.secret_id,
                    service=entry.service,
                    label=entry.label,
                    owner_user_id=entry.owner_user_id,
                    created_at=entry.created_at,
                    updated_at=entry.updated_at
                ))
        
        return accessible_secrets
    
    def update_secret(
        self,
        secret_id: UUID,
        new_secret_data: str,
        requesting_user_id: UUID,
        user_roles: List[str]
    ) -> bool:
        """Update an existing secret.
        
        Args:
            secret_id: UUID of secret to update
            new_secret_data: New secret data
            requesting_user_id: User requesting update
            user_roles: List of user roles
            
        Returns:
            True if successful
        """
        # Get existing entry
        entry = self.db_manager.get_secret(secret_id)
        if not entry:
            return False
        
        # Check write permissions
        if not self.access_manager.check_access(
            requesting_user_id,
            secret_id,
            "write",
            user_roles,
            entry.access_policy,
            entry.owner_user_id
        ):
            return False
        
        # Encrypt new data
        encrypted_data = self.encryption_manager.encrypt_secret(new_secret_data)
        
        # Update entry
        entry.ciphertext_b64 = encrypted_data["ciphertext_b64"]
        entry.nonce_b64 = encrypted_data["nonce_b64"]
        entry.key_hash_sha256 = encrypted_data["key_hash_sha256"]
        entry.updated_at = datetime.utcnow()
        
        return self.db_manager.store_secret(entry)
    
    def delete_secret(
        self,
        secret_id: UUID,
        requesting_user_id: UUID,
        user_roles: List[str]
    ) -> bool:
        """Delete a secret.
        
        Args:
            secret_id: UUID of secret to delete
            requesting_user_id: User requesting deletion
            user_roles: List of user roles
            
        Returns:
            True if successful
        """
        # Get existing entry
        entry = self.db_manager.get_secret(secret_id)
        if not entry:
            return False
        
        # Check delete permissions
        if not self.access_manager.check_access(
            requesting_user_id,
            secret_id,
            "delete",
            user_roles,
            entry.access_policy,
            entry.owner_user_id
        ):
            return False
        
        return self.db_manager.delete_secret(secret_id)
    
    def grant_access(
        self,
        secret_id: UUID,
        target_user_id: UUID,
        permissions: Dict[str, bool],
        requesting_user_id: UUID,
        user_roles: List[str]
    ) -> bool:
        """Grant access to a secret for another user.
        
        Args:
            secret_id: UUID of secret
            target_user_id: User to grant access to
            permissions: Permissions to grant
            requesting_user_id: User requesting grant
            user_roles: List of user roles
            
        Returns:
            True if successful
        """
        # Get existing entry
        entry = self.db_manager.get_secret(secret_id)
        if not entry:
            return False
        
        # Check share permissions
        if not self.access_manager.check_access(
            requesting_user_id,
            secret_id,
            "share",
            user_roles,
            entry.access_policy,
            entry.owner_user_id
        ):
            return False
        
        # Update access policy
        updated_policy = self.access_manager.grant_user_access(
            entry.access_policy,
            target_user_id,
            permissions
        )
        
        entry.access_policy = updated_policy
        entry.updated_at = datetime.utcnow()
        
        return self.db_manager.store_secret(entry)
    
    def search_secrets(
        self,
        user_id: UUID,
        user_roles: List[str],
        query: str
    ) -> List[Secret]:
        """Search secrets by service or label.
        
        Args:
            user_id: User UUID
            user_roles: List of user roles
            query: Search query
            
        Returns:
            List of matching secrets
        """
        # Search in database
        entries = self.db_manager.search_secrets(user_id, query)
        
        # Filter by access permissions
        accessible_secrets = []
        for entry in entries:
            if self.access_manager.check_access(
                user_id,
                entry.secret_id,
                "read",
                user_roles,
                entry.access_policy,
                entry.owner_user_id
            ):
                accessible_secrets.append(Secret(
                    secret_id=entry.secret_id,
                    service=entry.service,
                    label=entry.label,
                    owner_user_id=entry.owner_user_id,
                    created_at=entry.created_at,
                    updated_at=entry.updated_at
                ))
        
        return accessible_secrets

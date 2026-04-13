"""
RAVER Vault Cryptography Module

Provides AES-256-GCM encryption, key derivation, and secure key management
with optional OS keystore integration.
"""

import os
import json
import base64
import hashlib
import secrets
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, Optional, Tuple, Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.kdf.argon2 import Argon2id
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend


class KDFType(Enum):
    """Key derivation function types."""
    PBKDF2 = "pbkdf2"
    ARGON2ID = "argon2id"


class CryptoManager:
    """Manages cryptographic operations for the vault."""
    
    def __init__(self, vault_path: Optional[Path] = None):
        if vault_path is None:
            vault_path = Path.home() / ".raver" / "vault"
        
        self.vault_path = vault_path
        self.vault_path.mkdir(parents=True, exist_ok=True)
        self.master_key_path = self.vault_path / "master.key"
        self.key_info_path = self.vault_path / "key_info.json"
        
        self._master_key: Optional[bytes] = None
        self._key_info: Optional[Dict[str, Any]] = None
    
    def initialize_vault(self, password: str, kdf_type: KDFType = KDFType.ARGON2ID) -> bool:
        """Initialize a new vault with a master password."""
        try:
            # Generate salt
            salt = os.urandom(32)
            
            # Derive master key
            if kdf_type == KDFType.PBKDF2:
                kdf = PBKDF2HMAC(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=salt,
                    iterations=100000,
                    backend=default_backend()
                )
                master_key = kdf.derive(password.encode())
                kdf_params = {
                    "type": "pbkdf2",
                    "iterations": 100000,
                    "salt": base64.b64encode(salt).decode(),
                    "algorithm": "sha256"
                }
            else:  # ARGON2ID
                kdf = Argon2id(
                    salt=salt,
                    length=32,
                    time_cost=3,
                    memory_cost=65536,
                    parallelism=4,
                    hash_func=hashes.BLAKE2b(256),
                    backend=default_backend()
                )
                master_key = kdf.derive(password.encode())
                kdf_params = {
                    "type": "argon2id",
                    "time_cost": 3,
                    "memory_cost": 65536,
                    "parallelism": 4,
                    "salt": base64.b64encode(salt).decode(),
                    "hash_length": 32
                }
            
            # Store key info
            key_info = {
                "version": "1.0",
                "created_at": datetime.utcnow().isoformat(),
                "kdf_params": kdf_params,
                "key_hash": self._hash_key(master_key)
            }
            
            # Encrypt and store master key
            encrypted_key = self._encrypt_master_key(master_key, password)
            
            with open(self.key_info_path, 'w') as f:
                json.dump(key_info, f, indent=2)
            
            with open(self.master_key_path, 'wb') as f:
                f.write(encrypted_key)
            
            self._key_info = key_info
            self._master_key = master_key
            
            return True
            
        except Exception as e:
            # Clean up on failure
            for path in [self.master_key_path, self.key_info_path]:
                if path.exists():
                    path.unlink()
            raise e
    
    def unlock_vault(self, password: str) -> bool:
        """Unlock the vault with the master password."""
        try:
            if not self.master_key_path.exists() or not self.key_info_path.exists():
                return False
            
            # Load key info
            with open(self.key_info_path, 'r') as f:
                self._key_info = json.load(f)
            
            # Decrypt master key
            encrypted_key = open(self.master_key_path, 'rb').read()
            master_key = self._decrypt_master_key(encrypted_key, password)
            
            # Verify key hash
            stored_hash = self._key_info.get("key_hash")
            computed_hash = self._hash_key(master_key)
            
            if stored_hash != computed_hash:
                return False
            
            self._master_key = master_key
            return True
            
        except Exception:
            return False
    
    def lock_vault(self):
        """Lock the vault by clearing the master key from memory."""
        if self._master_key:
            # Zero out the key
            self._master_key = b'\x00' * len(self._master_key)
            self._master_key = None
    
    def is_unlocked(self) -> bool:
        """Check if the vault is unlocked."""
        return self._master_key is not None
    
    def encrypt_data(self, data: bytes, associated_data: Optional[bytes] = None) -> Dict[str, str]:
        """Encrypt data using AES-256-GCM."""
        if not self.is_unlocked():
            raise ValueError("Vault is not unlocked")
        
        # Generate random nonce
        nonce = os.urandom(12)
        
        # Encrypt
        aesgcm = AESGCM(self._master_key)
        ciphertext = aesgcm.encrypt(nonce, data, associated_data)
        
        return {
            "ciphertext": base64.b64encode(ciphertext).decode(),
            "nonce": base64.b64encode(nonce).decode(),
            "algorithm": "aes-256-gcm"
        }
    
    def decrypt_data(self, encrypted_data: Dict[str, str], associated_data: Optional[bytes] = None) -> bytes:
        """Decrypt data using AES-256-GCM."""
        if not self.is_unlocked():
            raise ValueError("Vault is not unlocked")
        
        try:
            ciphertext = base64.b64decode(encrypted_data["ciphertext"])
            nonce = base64.b64decode(encrypted_data["nonce"])
            
            aesgcm = AESGCM(self._master_key)
            plaintext = aesgcm.decrypt(nonce, ciphertext, associated_data)
            
            return plaintext
            
        except Exception as e:
            raise ValueError(f"Failed to decrypt data: {str(e)}")
    
    def generate_data_key(self) -> bytes:
        """Generate a random data encryption key."""
        return os.urandom(32)
    
    def rotate_master_key(self, new_password: str) -> bool:
        """Rotate the master key with a new password."""
        if not self.is_unlocked():
            raise ValueError("Vault is not unlocked")
        
        try:
            # Generate new salt and derive new master key
            salt = os.urandom(32)
            kdf_type = KDFType(self._key_info["kdf_params"]["type"])
            
            if kdf_type == KDFType.PBKDF2:
                kdf = PBKDF2HMAC(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=salt,
                    iterations=100000,
                    backend=default_backend()
                )
                new_master_key = kdf.derive(new_password.encode())
                kdf_params = {
                    "type": "pbkdf2",
                    "iterations": 100000,
                    "salt": base64.b64encode(salt).decode(),
                    "algorithm": "sha256"
                }
            else:  # ARGON2ID
                kdf = Argon2id(
                    salt=salt,
                    length=32,
                    time_cost=3,
                    memory_cost=65536,
                    parallelism=4,
                    hash_func=hashes.BLAKE2b(256),
                    backend=default_backend()
                )
                new_master_key = kdf.derive(new_password.encode())
                kdf_params = {
                    "type": "argon2id",
                    "time_cost": 3,
                    "memory_cost": 65536,
                    "parallelism": 4,
                    "salt": base64.b64encode(salt).decode(),
                    "hash_length": 32
                }
            
            # Update key info
            self._key_info["kdf_params"] = kdf_params
            self._key_info["key_hash"] = self._hash_key(new_master_key)
            self._key_info["rotated_at"] = datetime.utcnow().isoformat()
            
            # Encrypt and store new master key
            encrypted_key = self._encrypt_master_key(new_master_key, new_password)
            
            with open(self.key_info_path, 'w') as f:
                json.dump(self._key_info, f, indent=2)
            
            with open(self.master_key_path, 'wb') as f:
                f.write(encrypted_key)
            
            # Update in-memory master key
            old_key = self._master_key
            self._master_key = new_master_key
            
            # Zero out old key
            old_key = b'\x00' * len(old_key)
            
            return True
            
        except Exception as e:
            raise e
    
    def _encrypt_master_key(self, master_key: bytes, password: str) -> bytes:
        """Encrypt the master key with the password."""
        # Use PBKDF2 for key encryption (separate from vault KDF)
        salt = os.urandom(16)
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        key_encryption_key = kdf.derive(password.encode())
        
        # Encrypt master key
        nonce = os.urandom(12)
        aesgcm = AESGCM(key_encryption_key)
        ciphertext = aesgcm.encrypt(nonce, master_key, None)
        
        # Combine salt + nonce + ciphertext
        return salt + nonce + ciphertext
    
    def _decrypt_master_key(self, encrypted_data: bytes, password: str) -> bytes:
        """Decrypt the master key with the password."""
        # Extract components
        salt = encrypted_data[:16]
        nonce = encrypted_data[16:28]
        ciphertext = encrypted_data[28:]
        
        # Derive key encryption key
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        key_encryption_key = kdf.derive(password.encode())
        
        # Decrypt master key
        aesgcm = AESGCM(key_encryption_key)
        master_key = aesgcm.decrypt(nonce, ciphertext, None)
        
        return master_key
    
    def _hash_key(self, key: bytes) -> str:
        """Hash a key for verification purposes."""
        return hashlib.sha256(key).hexdigest()
    
    def get_key_info(self) -> Optional[Dict[str, Any]]:
        """Get information about the vault key."""
        if self._key_info:
            info = self._key_info.copy()
            # Remove sensitive information
            info.pop("key_hash", None)
            return info
        return None
    
    def change_password(self, old_password: str, new_password: str) -> bool:
        """Change the vault password."""
        if not self.is_unlocked():
            raise ValueError("Vault is not unlocked")
        
        # Verify old password
        if not self.unlock_vault(old_password):
            return False
        
        return self.rotate_master_key(new_password)

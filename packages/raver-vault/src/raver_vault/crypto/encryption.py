"""Encryption manager for RAVER Vault."""

import base64
import hashlib
import json
import os
from typing import Dict, Any, Tuple
from uuid import UUID

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend


class EncryptionManager:
    """Manages AES-256-GCM encryption for vault secrets."""
    
    def __init__(self, master_key: bytes = None):
        """Initialize encryption manager.
        
        Args:
            master_key: Optional master key. If not provided, generates one.
        """
        if master_key is None:
            self.master_key = os.urandom(32)  # 256-bit key
        else:
            self.master_key = master_key
            
        self.backend = default_backend()
    
    def derive_key(self, password: str, salt: bytes = None, iterations: int = 100000) -> Tuple[bytes, bytes]:
        """Derive encryption key from password using PBKDF2.
        
        Args:
            password: User password
            salt: Optional salt. If not provided, generates one.
            iterations: Number of PBKDF2 iterations
            
        Returns:
            Tuple of (derived_key, salt)
        """
        if salt is None:
            salt = os.urandom(16)
            
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=iterations,
            backend=self.backend
        )
        
        key = kdf.derive(password.encode())
        return key, salt
    
    def encrypt_secret(self, plaintext: str, key: bytes = None) -> Dict[str, str]:
        """Encrypt secret using AES-256-GCM.
        
        Args:
            plaintext: Secret to encrypt
            key: Optional encryption key. If not provided, uses master key.
            
        Returns:
            Dictionary with encrypted data
        """
        if key is None:
            key = self.master_key
            
        aesgcm = AESGCM(key)
        nonce = os.urandom(12)  # 96-bit nonce for GCM
        ciphertext = aesgcm.encrypt(nonce, plaintext.encode(), None)
        
        return {
            "ciphertext_b64": base64.b64encode(ciphertext).decode(),
            "nonce_b64": base64.b64encode(nonce).decode(),
            "key_hash_sha256": hashlib.sha256(key).hexdigest()
        }
    
    def decrypt_secret(self, encrypted_data: Dict[str, str], key: bytes = None) -> str:
        """Decrypt secret using AES-256-GCM.
        
        Args:
            encrypted_data: Dictionary with encrypted data
            key: Optional decryption key. If not provided, uses master key.
            
        Returns:
            Decrypted plaintext
            
        Raises:
            ValueError: If decryption fails
        """
        if key is None:
            key = self.master_key
            
        try:
            ciphertext = base64.b64decode(encrypted_data["ciphertext_b64"])
            nonce = base64.b64decode(encrypted_data["nonce_b64"])
            
            aesgcm = AESGCM(key)
            plaintext = aesgcm.decrypt(nonce, ciphertext, None)
            
            return plaintext.decode()
        except Exception as e:
            raise ValueError(f"Decryption failed: {str(e)}")
    
    def create_kdf_params(self, salt: bytes, iterations: int = 100000) -> Dict[str, Any]:
        """Create KDF parameters for storage.
        
        Args:
            salt: Salt used for key derivation
            iterations: Number of iterations
            
        Returns:
            KDF parameters dictionary
        """
        return {
            "algorithm": "PBKDF2-HMAC-SHA256",
            "salt_b64": base64.b64encode(salt).decode(),
            "iterations": iterations,
            "key_length": 32
        }
    
    def verify_key_hash(self, key: bytes, expected_hash: str) -> bool:
        """Verify key hash matches expected hash.
        
        Args:
            key: Key to verify
            expected_hash: Expected SHA-256 hash
            
        Returns:
            True if hash matches
        """
        actual_hash = hashlib.sha256(key).hexdigest()
        return actual_hash == expected_hash

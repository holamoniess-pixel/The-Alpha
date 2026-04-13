"""
Crypto manager for secure encryption operations.
"""

import os
import base64
import hashlib
import secrets
from enum import Enum
from typing import Dict, Any, Tuple
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend


class KDFType(str, Enum):
    """Key derivation function types."""
    PBKDF2 = "pbkdf2"
    ARGON2 = "argon2"


class CryptoManager:
    """Manages cryptographic operations for the vault."""
    
    def __init__(self):
        self.backend = default_backend()
        self.key_size = 32  # 256 bits
        self.nonce_size = 12  # 96 bits for GCM
    
    def derive_key(self, password: str, salt: bytes, kdf_type: KDFType = KDFType.PBKDF2, 
                   iterations: int = 100000) -> bytes:
        """Derive encryption key from password."""
        if kdf_type == KDFType.PBKDF2:
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=self.key_size,
                salt=salt,
                iterations=iterations,
                backend=self.backend
            )
            return kdf.derive(password.encode())
        else:
            # For now, fallback to PBKDF2 for Argon2
            # In production, use argon2-cffi library
            return self.derive_key(password, salt, KDFType.PBKDF2, iterations)
    
    def generate_salt(self) -> bytes:
        """Generate random salt for key derivation."""
        return os.urandom(16)
    
    def generate_nonce(self) -> bytes:
        """Generate random nonce for AES-GCM."""
        return os.urandom(self.nonce_size)
    
    def encrypt(self, plaintext: str, key: bytes) -> Tuple[bytes, bytes]:
        """
        Encrypt plaintext using AES-256-GCM.
        
        Args:
            plaintext: Text to encrypt
            key: 32-byte encryption key
            
        Returns:
            Tuple of (ciphertext, nonce)
        """
        aesgcm = AESGCM(key)
        nonce = self.generate_nonce()
        ciphertext = aesgcm.encrypt(nonce, plaintext.encode(), None)
        return ciphertext, nonce
    
    def decrypt(self, ciphertext: bytes, key: bytes, nonce: bytes) -> str:
        """
        Decrypt ciphertext using AES-256-GCM.
        
        Args:
            ciphertext: Encrypted data
            key: 32-byte encryption key
            nonce: 12-byte nonce
            
        Returns:
            Decrypted plaintext
            
        Raises:
            ValueError: If decryption fails (tampered data)
        """
        aesgcm = AESGCM(key)
        try:
            plaintext = aesgcm.decrypt(nonce, ciphertext, None)
            return plaintext.decode()
        except Exception as e:
            raise ValueError(f"Decryption failed: {e}")
    
    def hash_key(self, key: bytes) -> str:
        """Hash a key for verification purposes."""
        return hashlib.sha256(key).hexdigest()
    
    def encrypt_secret(self, secret: str, password: str, kdf_type: KDFType = KDFType.PBKDF2) -> Dict[str, Any]:
        """
        Encrypt a secret with password-based key derivation.
        
        Returns:
            Dictionary with encrypted data and metadata
        """
        salt = self.generate_salt()
        key = self.derive_key(password, salt, kdf_type)
        ciphertext, nonce = self.encrypt(secret, key)
        
        return {
            "ciphertext_b64": base64.b64encode(ciphertext).decode(),
            "nonce_b64": base64.b64encode(nonce).decode(),
            "salt_b64": base64.b64encode(salt).decode(),
            "kdf_type": kdf_type.value,
            "key_hash": self.hash_key(key)
        }
    
    def decrypt_secret(self, encrypted_data: Dict[str, Any], password: str) -> str:
        """
        Decrypt a secret using password and metadata.
        
        Args:
            encrypted_data: Dictionary with encrypted data and metadata
            password: Password for decryption
            
        Returns:
            Decrypted secret
        """
        ciphertext = base64.b64decode(encrypted_data["ciphertext_b64"])
        nonce = base64.b64decode(encrypted_data["nonce_b64"])
        salt = base64.b64decode(encrypted_data["salt_b64"])
        kdf_type = KDFType(encrypted_data["kdf_type"])
        
        key = self.derive_key(password, salt, kdf_type)
        
        # Verify key hash if present
        if "key_hash" in encrypted_data:
            expected_hash = encrypted_data["key_hash"]
            actual_hash = self.hash_key(key)
            if expected_hash != actual_hash:
                raise ValueError("Invalid password or corrupted data")
        
        return self.decrypt(ciphertext, key, nonce)
    
    def generate_secure_random(self, length: int = 32) -> str:
        """Generate a secure random string."""
        return secrets.token_urlsafe(length)

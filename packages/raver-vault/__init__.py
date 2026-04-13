"""
RAVER Vault Package

Encrypted secret storage with AES-256-GCM encryption, OS keystore integration,
and role-based access control for secure credential management.
"""

__version__ = "0.1.0"
__author__ = "RAVER Team"

from .vault import VaultManager
from .crypto import CryptoManager, KDFType
from .storage import SecretStorage
from .access import AccessController, AccessPolicy

__all__ = [
    "VaultManager",
    "CryptoManager", 
    "KDFType",
    "SecretStorage",
    "AccessController",
    "AccessPolicy"
]

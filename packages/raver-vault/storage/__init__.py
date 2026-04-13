"""
Storage module for RAVER Vault
Handles persistent storage of encrypted secrets.
"""

from .database import SecretStorage

__all__ = ["SecretStorage"]

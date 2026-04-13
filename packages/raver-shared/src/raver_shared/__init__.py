"""RAVER Shared - Common schemas and IPC contracts."""

__version__ = "0.1.0"

from .schemas import (
    AuditEvent,
    Capability,
    Intent,
    PolicyDecision,
    Role,
    Secret,
    User,
    VaultEntry,
)

__all__ = [
    "AuditEvent",
    "Capability", 
    "Intent",
    "PolicyDecision",
    "Role",
    "Secret",
    "User",
    "VaultEntry",
]

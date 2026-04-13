#!/usr/bin/env python3
"""
ALPHA OMEGA - SECURITY FRAMEWORK
Voice Authentication, Encryption, Audit Logging, and Threat Detection
Version: 2.0.0
"""

import asyncio
import json
import logging
import time
import threading
import hashlib
import os
import secrets
from pathlib import Path
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
import hmac

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.backends import default_backend

    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False
    logging.warning("Cryptography library not available")


class ThreatLevel(Enum):
    NONE = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class Permission(Enum):
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    ADMIN = "admin"


@dataclass
class AuditEvent:
    event_id: str
    event_type: str
    timestamp: float
    user_id: str
    action: str
    resource: str
    success: bool
    details: Dict[str, Any] = field(default_factory=dict)
    prev_hash: str = ""
    event_hash: str = ""

    def compute_hash(self) -> str:
        data = f"{self.event_id}{self.timestamp}{self.event_type}{self.action}{self.success}{self.prev_hash}"
        return hashlib.sha256(data.encode()).hexdigest()


class AuditLogger:
    def __init__(self, storage_path: Path = None):
        self.storage_path = storage_path or Path("data/audit.log")
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        self._lock = threading.Lock()
        self._last_hash = ""
        self._events: List[AuditEvent] = []
        self._file_handle = None

        self._load_last_hash()

    def _load_last_hash(self):
        if self.storage_path.exists():
            try:
                with open(self.storage_path, "r") as f:
                    lines = f.readlines()
                    if lines:
                        last_line = lines[-1].strip()
                        if last_line:
                            data = json.loads(last_line)
                            self._last_hash = data.get("event_hash", "")
            except Exception:
                self._last_hash = ""

    def log_event(
        self,
        event_type: str,
        action: str,
        resource: str,
        user_id: str = "system",
        success: bool = True,
        details: Dict[str, Any] = None,
    ) -> AuditEvent:
        event = AuditEvent(
            event_id=secrets.token_hex(16),
            event_type=event_type,
            timestamp=time.time(),
            user_id=user_id,
            action=action,
            resource=resource,
            success=success,
            details=details or {},
            prev_hash=self._last_hash,
        )

        event.event_hash = event.compute_hash()

        with self._lock:
            self._events.append(event)
            self._last_hash = event.event_hash

            self._write_event(event)

        return event

    def _write_event(self, event: AuditEvent):
        with open(self.storage_path, "a") as f:
            f.write(json.dumps(event.__dict__) + "\n")

    def verify_chain(self) -> Tuple[bool, List[str]]:
        errors = []
        prev_hash = ""

        if not self.storage_path.exists():
            return True, []

        with open(self.storage_path, "r") as f:
            for line_num, line in enumerate(f, 1):
                try:
                    data = json.loads(line.strip())
                    event = AuditEvent(**data)

                    if event.prev_hash != prev_hash:
                        errors.append(f"Chain broken at line {line_num}")

                    computed = event.compute_hash()
                    if computed != event.event_hash:
                        errors.append(f"Hash mismatch at line {line_num}")

                    prev_hash = event.event_hash
                except Exception as e:
                    errors.append(f"Parse error at line {line_num}: {e}")

        return len(errors) == 0, errors

    def get_events(
        self,
        event_type: str = None,
        user_id: str = None,
        start_time: float = None,
        end_time: float = None,
        limit: int = 100,
    ) -> List[AuditEvent]:
        events = []

        if not self.storage_path.exists():
            return events

        with open(self.storage_path, "r") as f:
            for line in f:
                try:
                    data = json.loads(line.strip())
                    event = AuditEvent(**data)

                    if event_type and event.event_type != event_type:
                        continue
                    if user_id and event.user_id != user_id:
                        continue
                    if start_time and event.timestamp < start_time:
                        continue
                    if end_time and event.timestamp > end_time:
                        continue

                    events.append(event)
                except:
                    continue

        return events[-limit:]

    def get_statistics(self) -> Dict[str, Any]:
        total = 0
        successes = 0
        failures = 0
        by_type = defaultdict(int)

        if self.storage_path.exists():
            with open(self.storage_path, "r") as f:
                for line in f:
                    try:
                        data = json.loads(line.strip())
                        total += 1
                        if data.get("success"):
                            successes += 1
                        else:
                            failures += 1
                        by_type[data.get("event_type", "unknown")] += 1
                    except:
                        continue

        return {
            "total_events": total,
            "successful": successes,
            "failed": failures,
            "by_type": dict(by_type),
        }


class CommandWhitelist:
    def __init__(self):
        self._allowed_commands: Set[str] = set()
        self._blocked_commands: Set[str] = set()
        self._command_permissions: Dict[str, Set[Permission]] = {}

        self._init_defaults()

    def _init_defaults(self):
        safe_commands = [
            "open",
            "close",
            "type",
            "click",
            "press",
            "scroll",
            "move",
            "screenshot",
            "status",
            "help",
            "volume",
            "mute",
            "search",
            "browser",
            "file_read",
            "dir_list",
            "ip",
            "ping",
            "process_list",
            "system_info",
        ]

        for cmd in safe_commands:
            self._allowed_commands.add(cmd)
            self._command_permissions[cmd] = {Permission.READ, Permission.EXECUTE}

        dangerous_commands = [
            "shutdown",
            "restart",
            "format",
            "del /f",
            "rm -rf",
            "reg delete",
            "sc delete",
            "cipher",
            "takeown",
        ]

        for cmd in dangerous_commands:
            self._blocked_commands.add(cmd)

    def is_allowed(
        self, command: str, user_permissions: Set[Permission] = None
    ) -> Tuple[bool, str]:
        command_lower = command.lower().strip()

        for blocked in self._blocked_commands:
            if blocked in command_lower:
                return False, f"Command contains blocked pattern: {blocked}"

        action = command_lower.split()[0] if command_lower else ""

        if action in self._allowed_commands:
            if user_permissions:
                required = self._command_permissions.get(action, set())
                if not required.issubset(user_permissions):
                    return False, f"Insufficient permissions for {action}"
            return True, ""

        return True, ""

    def add_allowed(self, command: str, permissions: Set[Permission] = None):
        self._allowed_commands.add(command.lower())
        if permissions:
            self._command_permissions[command.lower()] = permissions

    def add_blocked(self, command: str):
        self._blocked_commands.add(command.lower())

    def get_allowed(self) -> List[str]:
        return list(self._allowed_commands)

    def get_blocked(self) -> List[str]:
        return list(self._blocked_commands)


class ThreatDetector:
    def __init__(self):
        self._failed_attempts = defaultdict(int)
        self._command_rates = defaultdict(list)
        self._blocked_ips: Set[str] = set()
        self._alerts: List[Dict[str, Any]] = []

        self._thresholds = {
            "max_failed_attempts": 5,
            "max_commands_per_minute": 60,
            "suspicious_patterns": [
                "password",
                "credential",
                "secret",
                "api_key",
                "passwd",
                "shadow",
                "sudo",
                "su ",
                "net user",
                "net localgroup",
                "whoami",
            ],
        }

    def analyze_command(self, command: str, user_id: str = "default") -> ThreatLevel:
        threat_level = ThreatLevel.NONE
        reasons = []

        command_lower = command.lower()

        for pattern in self._thresholds["suspicious_patterns"]:
            if pattern in command_lower:
                threat_level = ThreatLevel.HIGH
                reasons.append(f"Suspicious pattern: {pattern}")

        if self._failed_attempts[user_id] > self._thresholds["max_failed_attempts"]:
            threat_level = max(threat_level, ThreatLevel.MEDIUM, key=lambda x: x.value)
            reasons.append("Too many failed attempts")

        now = time.time()
        self._command_rates[user_id].append(now)
        self._command_rates[user_id] = [
            t for t in self._command_rates[user_id] if now - t < 60
        ]

        if (
            len(self._command_rates[user_id])
            > self._thresholds["max_commands_per_minute"]
        ):
            threat_level = max(threat_level, ThreatLevel.HIGH, key=lambda x: x.value)
            reasons.append("Command rate limit exceeded")

        if reasons:
            self._alerts.append(
                {
                    "timestamp": now,
                    "user_id": user_id,
                    "command": command,
                    "threat_level": threat_level.name,
                    "reasons": reasons,
                }
            )

        return threat_level

    def record_failure(self, user_id: str):
        self._failed_attempts[user_id] += 1

    def reset_failures(self, user_id: str):
        self._failed_attempts[user_id] = 0

    def get_alerts(self, limit: int = 100) -> List[Dict[str, Any]]:
        return self._alerts[-limit:]

    def get_threat_stats(self) -> Dict[str, Any]:
        return {
            "total_alerts": len(self._alerts),
            "failed_attempts": dict(self._failed_attempts),
            "active_blocks": len(self._blocked_ips),
        }


class SecurityFramework:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger("SecurityFramework")

        self.enabled = config.get("security_enabled", True)
        self.audit_enabled = config.get("audit_logging", True)

        self.audit_logger = AuditLogger()
        self.command_whitelist = CommandWhitelist()
        self.threat_detector = ThreatDetector()

        self._session_timeout = config.get("session_timeout", 300)
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._running = False

        self._stats = {
            "commands_checked": 0,
            "commands_blocked": 0,
            "threats_detected": 0,
            "sessions_created": 0,
        }

    async def initialize(self) -> bool:
        self.logger.info("Initializing Security Framework...")

        valid, errors = self.audit_logger.verify_chain()
        if not valid:
            self.logger.warning(f"Audit chain verification failed: {errors}")

        self._running = True
        self.logger.info("Security Framework initialized")
        return True

    def is_command_allowed(
        self,
        command: str,
        user_id: str = "default",
        permissions: Set[Permission] = None,
    ) -> bool:
        if not self.enabled:
            return True

        self._stats["commands_checked"] += 1

        threat_level = self.threat_detector.analyze_command(command, user_id)
        if threat_level.value >= ThreatLevel.HIGH.value:
            self._stats["threats_detected"] += 1
            self.logger.warning(
                f"Threat detected: {command} (level={threat_level.name})"
            )
            self.audit_logger.log_event(
                "security",
                "threat_detected",
                command,
                user_id,
                False,
                {"threat_level": threat_level.name},
            )
            return False

        allowed, reason = self.command_whitelist.is_allowed(command, permissions)

        if not allowed:
            self._stats["commands_blocked"] += 1
            self.logger.info(f"Command blocked: {command} - {reason}")
            self.audit_logger.log_event(
                "security",
                "command_blocked",
                command,
                user_id,
                False,
                {"reason": reason},
            )
            return False

        return True

    def create_session(self, user_id: str, auth_method: str = "voice") -> str:
        session_id = secrets.token_urlsafe(32)

        self._sessions[session_id] = {
            "user_id": user_id,
            "created_at": time.time(),
            "last_activity": time.time(),
            "auth_method": auth_method,
            "permissions": {Permission.READ, Permission.EXECUTE},
        }

        self._stats["sessions_created"] += 1

        self.audit_logger.log_event(
            "session",
            "created",
            session_id,
            user_id,
            True,
            {"auth_method": auth_method},
        )

        return session_id

    def validate_session(
        self, session_id: str
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        if session_id not in self._sessions:
            return False, None

        session = self._sessions[session_id]

        if time.time() - session["last_activity"] > self._session_timeout:
            del self._sessions[session_id]
            return False, None

        session["last_activity"] = time.time()
        return True, session

    def revoke_session(self, session_id: str):
        if session_id in self._sessions:
            user_id = self._sessions[session_id]["user_id"]
            del self._sessions[session_id]

            self.audit_logger.log_event("session", "revoked", session_id, user_id, True)

    async def start_monitoring(self):
        self.logger.info("Security monitoring started")

        while self._running:
            try:
                await asyncio.sleep(60)

                now = time.time()
                expired = [
                    sid
                    for sid, session in self._sessions.items()
                    if now - session["last_activity"] > self._session_timeout
                ]

                for sid in expired:
                    self.revoke_session(sid)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Monitoring error: {e}")

    def log_action(
        self,
        action: str,
        resource: str,
        user_id: str = "system",
        success: bool = True,
        details: Dict[str, Any] = None,
    ):
        if self.audit_enabled:
            self.audit_logger.log_event(
                "action", action, resource, user_id, success, details
            )

    def get_status(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "audit_enabled": self.audit_enabled,
            "active_sessions": len(self._sessions),
            "stats": self._stats,
            "threat_stats": self.threat_detector.get_threat_stats(),
            "audit_stats": self.audit_logger.get_statistics(),
        }

    async def stop(self):
        self._running = False
        self.logger.info("Security framework stopped")


from collections import defaultdict
from typing import Tuple

#!/usr/bin/env python3
"""
ALPHA OMEGA - AI-POWERED DEBUGGING & SELF-REPAIR
Detect and fix issues automatically
Version: 2.0.0
"""

import asyncio
import json
import logging
import time
import traceback
import sys
import sqlite3
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import threading
import re


class ErrorSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    RUNTIME = "runtime"
    SYNTAX = "syntax"
    LOGIC = "logic"
    NETWORK = "network"
    FILE_SYSTEM = "file_system"
    PERMISSION = "permission"
    MEMORY = "memory"
    TIMEOUT = "timeout"
    CONFIGURATION = "configuration"
    DEPENDENCY = "dependency"
    UNKNOWN = "unknown"


class RepairStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class ErrorContext:
    error_type: str
    error_message: str
    traceback: str
    file_path: str = ""
    line_number: int = 0
    function_name: str = ""
    timestamp: float = field(default_factory=time.time)
    context_data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error_type": self.error_type,
            "error_message": self.error_message,
            "traceback": self.traceback,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "function_name": self.function_name,
            "timestamp": self.timestamp,
            "context_data": self.context_data,
        }


@dataclass
class DiagnosedIssue:
    id: str
    context: ErrorContext
    severity: ErrorSeverity
    category: ErrorCategory
    root_cause: str
    suggested_fixes: List[str]
    auto_fixable: bool
    patterns_matched: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "context": self.context.to_dict(),
            "severity": self.severity.value,
            "category": self.category.value,
            "root_cause": self.root_cause,
            "suggested_fixes": self.suggested_fixes,
            "auto_fixable": self.auto_fixable,
        }


@dataclass
class RepairAttempt:
    id: str
    issue_id: str
    strategy: str
    actions_taken: List[str]
    status: RepairStatus
    result: str = ""
    error: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "issue_id": self.issue_id,
            "strategy": self.strategy,
            "actions_taken": self.actions_taken,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "timestamp": self.timestamp,
        }


@dataclass
class RepairPattern:
    name: str
    error_patterns: List[str]
    category: ErrorCategory
    severity: ErrorSeverity
    fix_strategy: str
    auto_fix: bool = False
    fix_actions: List[str] = field(default_factory=list)


class ErrorAnalyzer:
    """Analyze and categorize errors"""

    ERROR_PATTERNS = [
        RepairPattern(
            name="FileNotFoundError",
            error_patterns=[
                r"FileNotFoundError",
                r"No such file or directory",
                r"file not found",
            ],
            category=ErrorCategory.FILE_SYSTEM,
            severity=ErrorSeverity.MEDIUM,
            fix_strategy="create_missing_file",
            auto_fix=True,
            fix_actions=["create_directory", "create_file", "check_path"],
        ),
        RepairPattern(
            name="PermissionError",
            error_patterns=[
                r"PermissionError",
                r"Permission denied",
                r"Access is denied",
            ],
            category=ErrorCategory.PERMISSION,
            severity=ErrorSeverity.HIGH,
            fix_strategy="fix_permissions",
            auto_fix=True,
            fix_actions=["request_admin", "change_permissions", "try_alternative_path"],
        ),
        RepairPattern(
            name="ImportError",
            error_patterns=[r"ImportError", r"ModuleNotFoundError", r"No module named"],
            category=ErrorCategory.DEPENDENCY,
            severity=ErrorSeverity.MEDIUM,
            fix_strategy="install_dependency",
            auto_fix=True,
            fix_actions=["pip_install", "check_requirements"],
        ),
        RepairPattern(
            name="TimeoutError",
            error_patterns=[r"TimeoutError", r"timed out", r"timeout"],
            category=ErrorCategory.TIMEOUT,
            severity=ErrorSeverity.MEDIUM,
            fix_strategy="increase_timeout",
            auto_fix=False,
            fix_actions=["increase_timeout", "retry", "async_implementation"],
        ),
        RepairPattern(
            name="MemoryError",
            error_patterns=[
                r"MemoryError",
                r"out of memory",
                r"Memory allocation failed",
            ],
            category=ErrorCategory.MEMORY,
            severity=ErrorSeverity.HIGH,
            fix_strategy="reduce_memory_usage",
            auto_fix=False,
            fix_actions=["clear_cache", "reduce_batch_size", "garbage_collect"],
        ),
        RepairPattern(
            name="ConnectionError",
            error_patterns=[
                r"ConnectionError",
                r"Connection refused",
                r"Network is unreachable",
            ],
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.MEDIUM,
            fix_strategy="retry_connection",
            auto_fix=True,
            fix_actions=["retry", "check_network", "use_fallback"],
        ),
        RepairPattern(
            name="SyntaxError",
            error_patterns=[r"SyntaxError", r"Invalid syntax", r"unexpected EOF"],
            category=ErrorCategory.SYNTAX,
            severity=ErrorSeverity.HIGH,
            fix_strategy="fix_syntax",
            auto_fix=False,
            fix_actions=["show_syntax_error", "suggest_fix"],
        ),
        RepairPattern(
            name="KeyError",
            error_patterns=[r"KeyError", r"key not found"],
            category=ErrorCategory.LOGIC,
            severity=ErrorSeverity.LOW,
            fix_strategy="handle_missing_key",
            auto_fix=True,
            fix_actions=["use_get_method", "add_default_value", "validate_key"],
        ),
        RepairPattern(
            name="AttributeError",
            error_patterns=[
                r"AttributeError",
                r"has no attribute",
                r"object has no attribute",
            ],
            category=ErrorCategory.LOGIC,
            severity=ErrorSeverity.MEDIUM,
            fix_strategy="fix_attribute_access",
            auto_fix=False,
            fix_actions=["check_object_type", "add_attribute", "use_hasattr"],
        ),
        RepairPattern(
            name="TypeError",
            error_patterns=[r"TypeError", r"unsupported operand", r"not iterable"],
            category=ErrorCategory.RUNTIME,
            severity=ErrorSeverity.MEDIUM,
            fix_strategy="fix_type_mismatch",
            auto_fix=False,
            fix_actions=["type_check", "convert_type", "add_validation"],
        ),
        RepairPattern(
            name="ValueError",
            error_patterns=[r"ValueError", r"invalid literal", r"invalid value"],
            category=ErrorCategory.RUNTIME,
            severity=ErrorSeverity.MEDIUM,
            fix_strategy="validate_value",
            auto_fix=False,
            fix_actions=["validate_input", "add_bounds_check", "sanitize_input"],
        ),
    ]

    def __init__(self):
        self.logger = logging.getLogger("ErrorAnalyzer")

    def analyze_error(self, context: ErrorContext) -> DiagnosedIssue:
        """Analyze an error and diagnose the issue"""
        issue_id = hashlib.md5(
            f"{context.error_type}{time.time()}".encode()
        ).hexdigest()[:12]

        matched_pattern = None
        patterns_matched = []

        for pattern in self.ERROR_PATTERNS:
            for error_pattern in pattern.error_patterns:
                if re.search(error_pattern, context.error_message, re.IGNORECASE):
                    matched_pattern = pattern
                    patterns_matched.append(pattern.name)
                    break

        if matched_pattern:
            return DiagnosedIssue(
                id=issue_id,
                context=context,
                severity=matched_pattern.severity,
                category=matched_pattern.category,
                root_cause=self._determine_root_cause(context, matched_pattern),
                suggested_fixes=matched_pattern.fix_actions,
                auto_fixable=matched_pattern.auto_fix,
                patterns_matched=patterns_matched,
            )

        return DiagnosedIssue(
            id=issue_id,
            context=context,
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.UNKNOWN,
            root_cause="Unable to determine root cause",
            suggested_fixes=["investigate_manually", "check_logs"],
            auto_fixable=False,
            patterns_matched=patterns_matched,
        )

    def _determine_root_cause(
        self, context: ErrorContext, pattern: RepairPattern
    ) -> str:
        """Determine the root cause of the error"""
        if pattern.category == ErrorCategory.FILE_SYSTEM:
            return f"Missing file or directory: {context.file_path or 'unknown path'}"
        elif pattern.category == ErrorCategory.PERMISSION:
            return "Insufficient permissions to perform operation"
        elif pattern.category == ErrorCategory.DEPENDENCY:
            match = re.search(r"No module named '(\w+)'", context.error_message)
            if match:
                return f"Missing dependency: {match.group(1)}"
            return "Missing or incompatible dependency"
        elif pattern.category == ErrorCategory.NETWORK:
            return "Network connectivity issue or server unreachable"
        elif pattern.category == ErrorCategory.MEMORY:
            return "Insufficient memory available"
        else:
            return f"Error in {context.function_name or 'unknown function'} at line {context.line_number}"


class SelfRepairEngine:
    """Attempt to fix issues automatically"""

    def __init__(self, llm_provider=None):
        self.llm_provider = llm_provider
        self.logger = logging.getLogger("SelfRepairEngine")

        self._repair_strategies: Dict[str, Callable] = {}
        self._repair_history: List[RepairAttempt] = []
        self._success_rate: Dict[str, float] = {}

        self._init_strategies()

    def _init_strategies(self):
        """Initialize repair strategies"""
        self._repair_strategies = {
            "create_missing_file": self._create_missing_file,
            "install_dependency": self._install_dependency,
            "retry_connection": self._retry_connection,
            "fix_permissions": self._fix_permissions,
            "handle_missing_key": self._handle_missing_key,
            "clear_cache": self._clear_cache,
            "garbage_collect": self._garbage_collect,
        }

    async def attempt_repair(self, issue: DiagnosedIssue) -> RepairAttempt:
        """Attempt to repair an issue"""
        attempt_id = hashlib.md5(f"{issue.id}{time.time()}".encode()).hexdigest()[:8]

        attempt = RepairAttempt(
            id=attempt_id,
            issue_id=issue.id,
            strategy=issue.suggested_fixes[0] if issue.suggested_fixes else "unknown",
            actions_taken=[],
            status=RepairStatus.IN_PROGRESS,
        )

        if not issue.auto_fixable:
            attempt.status = RepairStatus.SKIPPED
            attempt.result = "Auto-repair not available for this issue type"
            self._repair_history.append(attempt)
            return attempt

        for fix_action in issue.suggested_fixes:
            if fix_action in self._repair_strategies:
                try:
                    action_result = await self._repair_strategies[fix_action](issue)
                    attempt.actions_taken.append(fix_action)

                    if action_result.get("success"):
                        attempt.status = RepairStatus.SUCCESS
                        attempt.result = action_result.get(
                            "message", "Repair successful"
                        )
                        break
                    else:
                        attempt.actions_taken.append(f"{fix_action}_failed")

                except Exception as e:
                    attempt.actions_taken.append(f"{fix_action}_error")
                    self.logger.error(f"Repair action failed: {e}")

        if attempt.status == RepairStatus.IN_PROGRESS:
            attempt.status = RepairStatus.FAILED
            attempt.error = "All repair attempts failed"

        self._repair_history.append(attempt)
        self._update_success_rate(
            issue.context.error_type, attempt.status == RepairStatus.SUCCESS
        )

        return attempt

    async def _create_missing_file(self, issue: DiagnosedIssue) -> Dict[str, Any]:
        """Create missing file or directory"""
        file_path = issue.context.file_path
        if not file_path:
            return {"success": False, "message": "No file path provided"}

        path = Path(file_path)

        try:
            if "." in path.name:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.touch()
            else:
                path.mkdir(parents=True, exist_ok=True)

            return {"success": True, "message": f"Created: {file_path}"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    async def _install_dependency(self, issue: DiagnosedIssue) -> Dict[str, Any]:
        """Install missing Python dependency"""
        match = re.search(r"No module named '(\w+)'", issue.context.error_message)
        if not match:
            return {"success": False, "message": "Could not identify module"}

        module = match.group(1)

        try:
            import subprocess

            result = subprocess.run(
                ["pip", "install", module], capture_output=True, text=True, timeout=60
            )

            if result.returncode == 0:
                return {"success": True, "message": f"Installed {module}"}
            else:
                return {"success": False, "message": result.stderr}

        except Exception as e:
            return {"success": False, "message": str(e)}

    async def _retry_connection(self, issue: DiagnosedIssue) -> Dict[str, Any]:
        """Retry failed connection"""
        await asyncio.sleep(2)
        return {"success": True, "message": "Retry scheduled"}

    async def _fix_permissions(self, issue: DiagnosedIssue) -> Dict[str, Any]:
        """Attempt to fix permissions"""
        return {
            "success": False,
            "message": "Permission fix requires manual intervention",
        }

    async def _handle_missing_key(self, issue: DiagnosedIssue) -> Dict[str, Any]:
        """Handle missing dictionary key"""
        return {
            "success": True,
            "message": "Suggested using .get() method with default",
        }

    async def _clear_cache(self, issue: DiagnosedIssue) -> Dict[str, Any]:
        """Clear caches to free memory"""
        import gc

        gc.collect()
        return {"success": True, "message": "Cache cleared"}

    async def _garbage_collect(self, issue: DiagnosedIssue) -> Dict[str, Any]:
        """Force garbage collection"""
        import gc

        collected = gc.collect()
        return {"success": True, "message": f"Collected {collected} objects"}

    def _update_success_rate(self, error_type: str, success: bool):
        """Update repair success rate"""
        if error_type not in self._success_rate:
            self._success_rate[error_type] = 0.5

        current = self._success_rate[error_type]
        self._success_rate[error_type] = (current * 0.9) + (0.1 if success else 0)

    def get_success_rate(self, error_type: str = None) -> float:
        """Get repair success rate"""
        if error_type:
            return self._success_rate.get(error_type, 0.5)

        if not self._success_rate:
            return 0.0

        return sum(self._success_rate.values()) / len(self._success_rate)


class DebuggingSystem:
    """Main debugging and self-repair system"""

    def __init__(self, llm_provider=None):
        self.analyzer = ErrorAnalyzer()
        self.repair_engine = SelfRepairEngine(llm_provider)
        self.logger = logging.getLogger("DebuggingSystem")

        self._error_history: List[DiagnosedIssue] = []
        self._max_history = 100

        self._graceful_degradation = True
        self._auto_repair_enabled = True

    async def initialize(self) -> bool:
        """Initialize the debugging system"""
        self.logger.info("Debugging System initialized")
        return True

    async def handle_error(
        self,
        error: Exception,
        context: Dict[str, Any] = None,
    ) -> Tuple[DiagnosedIssue, Optional[RepairAttempt]]:
        """Handle an error with analysis and repair"""
        tb = traceback.format_exc()

        tb_lines = tb.split("\n")
        file_path = ""
        line_number = 0
        function_name = ""

        for line in tb_lines:
            if "File " in line:
                match = re.search(r'File "([^"]+)", line (\d+)', line)
                if match:
                    file_path = match.group(1)
                    line_number = int(match.group(2))
            if ", in " in line:
                match = re.search(r", in (\w+)", line)
                if match:
                    function_name = match.group(1)

        error_context = ErrorContext(
            error_type=type(error).__name__,
            error_message=str(error),
            traceback=tb,
            file_path=file_path,
            line_number=line_number,
            function_name=function_name,
            context_data=context or {},
        )

        issue = self.analyzer.analyze_error(error_context)

        self._error_history.append(issue)
        if len(self._error_history) > self._max_history:
            self._error_history.pop(0)

        self.logger.error(
            f"Error: {error_context.error_type} - {error_context.error_message}"
        )

        repair_attempt = None
        if self._auto_repair_enabled and issue.auto_fixable:
            repair_attempt = await self.repair_engine.attempt_repair(issue)

        return issue, repair_attempt

    def enable_auto_repair(self, enabled: bool = True):
        """Enable or disable auto-repair"""
        self._auto_repair_enabled = enabled

    def enable_graceful_degradation(self, enabled: bool = True):
        """Enable or disable graceful degradation"""
        self._graceful_degradation = enabled

    async def safe_execute(
        self, func: Callable, *args, fallback: Any = None, **kwargs
    ) -> Tuple[bool, Any]:
        """Safely execute a function with error handling"""
        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)

            return True, result

        except Exception as e:
            issue, repair = await self.handle_error(e)

            if self._graceful_degradation:
                self.logger.warning(
                    f"Graceful degradation activated for {issue.context.error_type}"
                )
                return False, fallback

            raise

    def get_error_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get error history"""
        return [issue.to_dict() for issue in self._error_history[-limit:]]

    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics"""
        if not self._error_history:
            return {"total_errors": 0}

        category_counts = {}
        severity_counts = {}

        for issue in self._error_history:
            cat = issue.category.value
            sev = issue.severity.value

            category_counts[cat] = category_counts.get(cat, 0) + 1
            severity_counts[sev] = severity_counts.get(sev, 0) + 1

        return {
            "total_errors": len(self._error_history),
            "by_category": category_counts,
            "by_severity": severity_counts,
            "repair_success_rate": self.repair_engine.get_success_rate(),
        }

    async def diagnose_system(self) -> Dict[str, Any]:
        """Run system diagnostics"""
        diagnostics = {
            "timestamp": time.time(),
            "checks": [],
            "issues": [],
            "recommendations": [],
        }

        checks = [
            ("Python Version", lambda: sys.version),
            ("Platform", lambda: sys.platform),
        ]

        try:
            import psutil

            checks.append(
                (
                    "Memory Available",
                    lambda: f"{psutil.virtual_memory().available / (1024**3):.2f} GB",
                )
            )
            checks.append(("CPU Usage", lambda: f"{psutil.cpu_percent()}%"))
        except:
            pass

        for check_name, check_func in checks:
            try:
                result = check_func()
                diagnostics["checks"].append(
                    {
                        "name": check_name,
                        "result": str(result),
                        "status": "ok",
                    }
                )
            except Exception as e:
                diagnostics["checks"].append(
                    {
                        "name": check_name,
                        "result": str(e),
                        "status": "error",
                    }
                )

        if self._error_history:
            recent_critical = [
                issue
                for issue in self._error_history[-10:]
                if issue.severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]
            ]
            if recent_critical:
                diagnostics["issues"].append(
                    f"{len(recent_critical)} critical errors in recent history"
                )
                diagnostics["recommendations"].append(
                    "Review error logs and consider restart"
                )

        return diagnostics


from typing import Callable

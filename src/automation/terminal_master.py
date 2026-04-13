#!/usr/bin/env python3
"""
ALPHA OMEGA - TERMINAL/CLI MASTER MODE
Natural language to command translation with safety
Version: 2.0.0
"""

import asyncio
import json
import logging
import os
import subprocess
import time
import shlex
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import platform
import re


class CommandRisk(Enum):
    SAFE = "safe"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    DANGEROUS = "dangerous"


class CommandType(Enum):
    FILE = "file"
    SYSTEM = "system"
    NETWORK = "network"
    PROCESS = "process"
    PACKAGE = "package"
    GIT = "git"
    DOCKER = "docker"
    CUSTOM = "custom"


@dataclass
class CommandTemplate:
    name: str
    template: str
    description: str
    command_type: CommandType
    risk: CommandRisk
    parameters: List[str] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)
    platform: List[str] = field(default_factory=lambda: ["windows", "linux", "macos"])

    def render(self, params: Dict[str, str]) -> str:
        result = self.template
        for key, value in params.items():
            result = result.replace(f"{{{key}}}", value)
        return result


@dataclass
class ParsedCommand:
    original: str
    command: str
    args: List[str]
    risk: CommandRisk
    command_type: CommandType
    safe: bool
    explanation: str
    alternatives: List[str] = field(default_factory=list)


@dataclass
class CommandResult:
    success: bool
    command: str
    stdout: str
    stderr: str
    return_code: int
    duration_ms: float
    risk: CommandRisk
    undo_command: str = ""


class TerminalMaster:
    """Natural language terminal command system"""

    DANGEROUS_PATTERNS = [
        r"\brm\s+-rf\s+/",
        r"\bformat\s+",
        r"\bdel\s+/[sS]",
        r"\bmkfs\b",
        r"\bdd\s+if=",
        r"\b:(){:|:&};:",
        r"\bchmod\s+-R\s+777\s+/",
        r"\bchown\s+-R\s+",
        r">\s*/dev/sd",
        r"\bshutdown\b",
        r"\breboot\b",
        r"\bhalt\b",
        r"\binit\s+0",
        r"\binit\s+6",
        r"\bpoweroff\b",
        r"\biexpress\b",
        r"\breg\s+delete\b",
        r"\bnetsh\s+\w+\s+delete\b",
        r"\bbcdedit\s+/delete\b",
        r"\bdiskpart\b",
        r"\bfdisk\b",
        r":%\s*s/",
        r"truncate\s+-s\s+0",
    ]

    COMMAND_TEMPLATES = {
        "list_files": CommandTemplate(
            name="list_files",
            template="dir" if platform.system() == "Windows" else "ls -la",
            description="List files in directory",
            command_type=CommandType.FILE,
            risk=CommandRisk.SAFE,
            examples=["list files", "show files", "what's in this folder"],
        ),
        "change_directory": CommandTemplate(
            name="change_directory",
            template="cd {path}",
            description="Change current directory",
            command_type=CommandType.FILE,
            risk=CommandRisk.SAFE,
            parameters=["path"],
            examples=["go to Documents", "cd to downloads", "change to folder xyz"],
        ),
        "create_directory": CommandTemplate(
            name="create_directory",
            template="mkdir {name}",
            description="Create a new directory",
            command_type=CommandType.FILE,
            risk=CommandRisk.LOW,
            parameters=["name"],
            examples=["create folder test", "make directory projects"],
        ),
        "delete_file": CommandTemplate(
            name="delete_file",
            template="del {file}" if platform.system() == "Windows" else "rm {file}",
            description="Delete a file",
            command_type=CommandType.FILE,
            risk=CommandRisk.MEDIUM,
            parameters=["file"],
            examples=["delete file.txt", "remove test.doc"],
        ),
        "copy_file": CommandTemplate(
            name="copy_file",
            template="copy {source} {dest}"
            if platform.system() == "Windows"
            else "cp {source} {dest}",
            description="Copy a file",
            command_type=CommandType.FILE,
            risk=CommandRisk.LOW,
            parameters=["source", "dest"],
            examples=["copy file.txt to backup", "duplicate document.pdf"],
        ),
        "move_file": CommandTemplate(
            name="move_file",
            template="move {source} {dest}"
            if platform.system() == "Windows"
            else "mv {source} {dest}",
            description="Move a file",
            command_type=CommandType.FILE,
            risk=CommandRisk.LOW,
            parameters=["source", "dest"],
            examples=["move file.txt to folder", "relocate document"],
        ),
        "find_file": CommandTemplate(
            name="find_file",
            template="dir /s /b {name}"
            if platform.system() == "Windows"
            else "find . -name {name}",
            description="Find a file",
            command_type=CommandType.FILE,
            risk=CommandRisk.SAFE,
            parameters=["name"],
            examples=["find file.txt", "search for document.pdf"],
        ),
        "grep_content": CommandTemplate(
            name="grep_content",
            template="findstr {pattern} {file}"
            if platform.system() == "Windows"
            else "grep {pattern} {file}",
            description="Search content in files",
            command_type=CommandType.FILE,
            risk=CommandRisk.SAFE,
            parameters=["pattern", "file"],
            examples=["search for error in log.txt", "find text hello in file"],
        ),
        "current_directory": CommandTemplate(
            name="current_directory",
            template="cd",
            description="Show current directory",
            command_type=CommandType.FILE,
            risk=CommandRisk.SAFE,
            examples=["where am I", "current folder", "pwd"],
        ),
        "system_info": CommandTemplate(
            name="system_info",
            template="systeminfo" if platform.system() == "Windows" else "uname -a",
            description="Get system information",
            command_type=CommandType.SYSTEM,
            risk=CommandRisk.SAFE,
            examples=["system info", "about this computer", "machine details"],
        ),
        "disk_usage": CommandTemplate(
            name="disk_usage",
            template="wmic logicaldisk get size,freespace,caption"
            if platform.system() == "Windows"
            else "df -h",
            description="Show disk usage",
            command_type=CommandType.SYSTEM,
            risk=CommandRisk.SAFE,
            examples=["disk space", "how much space left", "storage info"],
        ),
        "process_list": CommandTemplate(
            name="process_list",
            template="tasklist" if platform.system() == "Windows" else "ps aux",
            description="List running processes",
            command_type=CommandType.PROCESS,
            risk=CommandRisk.SAFE,
            examples=["running processes", "what's running", "show tasks"],
        ),
        "kill_process": CommandTemplate(
            name="kill_process",
            template="taskkill /PID {pid}"
            if platform.system() == "Windows"
            else "kill {pid}",
            description="Kill a process",
            command_type=CommandType.PROCESS,
            risk=CommandRisk.HIGH,
            parameters=["pid"],
            examples=["kill process 1234", "stop program"],
        ),
        "network_connections": CommandTemplate(
            name="network_connections",
            template="netstat -an",
            description="Show network connections",
            command_type=CommandType.NETWORK,
            risk=CommandRisk.SAFE,
            examples=["network connections", "what ports are open"],
        ),
        "ip_address": CommandTemplate(
            name="ip_address",
            template="ipconfig"
            if platform.system() == "Windows"
            else "ifconfig || ip addr",
            description="Show IP address",
            command_type=CommandType.NETWORK,
            risk=CommandRisk.SAFE,
            examples=["my ip", "what's my ip address", "network config"],
        ),
        "ping": CommandTemplate(
            name="ping",
            template="ping {host}",
            description="Ping a host",
            command_type=CommandType.NETWORK,
            risk=CommandRisk.SAFE,
            parameters=["host"],
            examples=["ping google.com", "check connection to server"],
        ),
        "git_status": CommandTemplate(
            name="git_status",
            template="git status",
            description="Git repository status",
            command_type=CommandType.GIT,
            risk=CommandRisk.SAFE,
            examples=["git status", "what changed", "repo status"],
        ),
        "git_log": CommandTemplate(
            name="git_log",
            template="git log --oneline -10",
            description="Recent git commits",
            command_type=CommandType.GIT,
            risk=CommandRisk.SAFE,
            examples=["git history", "recent commits", "show log"],
        ),
        "docker_ps": CommandTemplate(
            name="docker_ps",
            template="docker ps -a",
            description="List Docker containers",
            command_type=CommandType.DOCKER,
            risk=CommandRisk.SAFE,
            examples=["docker containers", "running containers"],
        ),
    }

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = logging.getLogger("TerminalMaster")

        self._command_history: List[Tuple[str, CommandResult]] = []
        self._max_history = 100
        self._require_confirmation = self.config.get("require_confirmation", True)
        self._allowed_commands: set = set()
        self._blocked_commands: set = set()

    def parse_natural_command(self, text: str) -> ParsedCommand:
        """Parse natural language to terminal command"""
        text_lower = text.lower().strip()

        if text_lower.startswith(("run ", "execute ", "command ", "cmd ")):
            text_lower = " ".join(text_lower.split()[1:])

        command = None
        command_type = CommandType.CUSTOM
        risk = CommandRisk.LOW
        explanation = ""

        if any(word in text_lower for word in ["list", "show", "display", "ls", "dir"]):
            if any(
                word in text_lower
                for word in ["file", "folder", "directory", "content"]
            ):
                command = self.COMMAND_TEMPLATES["list_files"].template
                command_type = CommandType.FILE
                risk = CommandRisk.SAFE
                explanation = "List files in current directory"

        elif any(word in text_lower for word in ["delete", "remove", "rm", "del"]):
            match = re.search(
                r"(?:delete|remove|rm|del)\s+(?:file\s+)?['\"]?(\S+)", text_lower
            )
            if match:
                filename = match.group(1)
                template = self.COMMAND_TEMPLATES["delete_file"]
                command = template.render({"file": filename})
                command_type = CommandType.FILE
                risk = CommandRisk.MEDIUM
                explanation = f"Delete file: {filename}"

        elif any(word in text_lower for word in ["copy", "cp", "duplicate"]):
            command = self.COMMAND_TEMPLATES["copy_file"].template
            command_type = CommandType.FILE
            risk = CommandRisk.LOW
            explanation = "Copy file operation"

        elif any(word in text_lower for word in ["move", "mv", "relocate"]):
            command = self.COMMAND_TEMPLATES["move_file"].template
            command_type = CommandType.FILE
            risk = CommandRisk.LOW
            explanation = "Move file operation"

        elif any(word in text_lower for word in ["find", "search", "locate"]):
            match = re.search(r"(?:find|search|locate)\s+['\"]?(\S+)", text_lower)
            if match:
                name = match.group(1)
                template = self.COMMAND_TEMPLATES["find_file"]
                command = template.render({"name": name})
                command_type = CommandType.FILE
                risk = CommandRisk.SAFE
                explanation = f"Find file: {name}"

        elif any(word in text_lower for word in ["ip", "address", "network"]):
            command = self.COMMAND_TEMPLATES["ip_address"].template
            command_type = CommandType.NETWORK
            risk = CommandRisk.SAFE
            explanation = "Show IP address configuration"

        elif any(word in text_lower for word in ["process", "running", "task"]):
            if any(word in text_lower for word in ["list", "show", "all"]):
                command = self.COMMAND_TEMPLATES["process_list"].template
                command_type = CommandType.PROCESS
                risk = CommandRisk.SAFE
                explanation = "List running processes"

        elif any(word in text_lower for word in ["ping", "connectivity"]):
            match = re.search(r"ping\s+(\S+)", text_lower)
            if match:
                host = match.group(1)
                template = self.COMMAND_TEMPLATES["ping"]
                command = template.render({"host": host})
                command_type = CommandType.NETWORK
                risk = CommandRisk.SAFE
                explanation = f"Ping host: {host}"

        elif any(word in text_lower for word in ["disk", "space", "storage"]):
            command = self.COMMAND_TEMPLATES["disk_usage"].template
            command_type = CommandType.SYSTEM
            risk = CommandRisk.SAFE
            explanation = "Show disk usage"

        elif any(word in text_lower for word in ["system", "info", "machine"]):
            command = self.COMMAND_TEMPLATES["system_info"].template
            command_type = CommandType.SYSTEM
            risk = CommandRisk.SAFE
            explanation = "Show system information"

        elif any(word in text_lower for word in ["git"]):
            if "status" in text_lower:
                command = self.COMMAND_TEMPLATES["git_status"].template
                command_type = CommandType.GIT
                risk = CommandRisk.SAFE
                explanation = "Show git status"
            elif "log" in text_lower or "history" in text_lower:
                command = self.COMMAND_TEMPLATES["git_log"].template
                command_type = CommandType.GIT
                risk = CommandRisk.SAFE
                explanation = "Show recent git commits"

        elif any(word in text_lower for word in ["docker"]):
            command = self.COMMAND_TEMPLATES["docker_ps"].template
            command_type = CommandType.DOCKER
            risk = CommandRisk.SAFE
            explanation = "List Docker containers"

        else:
            words = text.split()
            if words:
                command = " ".join(words)
                command_type = CommandType.CUSTOM
                risk = self._assess_risk(command)
                explanation = f"Execute: {command}"

        safe = risk in [CommandRisk.SAFE, CommandRisk.LOW]

        return ParsedCommand(
            original=text,
            command=command or "",
            args=shlex.split(command) if command else [],
            risk=risk,
            command_type=command_type,
            safe=safe,
            explanation=explanation,
        )

    def _assess_risk(self, command: str) -> CommandRisk:
        """Assess risk level of a command"""
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, command, re.IGNORECASE):
                return CommandRisk.DANGEROUS

        dangerous_keywords = [
            "format",
            "wipe",
            "destroy",
            "killall",
            "shutdown",
            "reboot",
            "halt",
        ]
        for kw in dangerous_keywords:
            if kw in command.lower():
                return CommandRisk.HIGH

        medium_keywords = [
            "delete",
            "remove",
            "rm",
            "del",
            "format",
            "fdisk",
            "reg delete",
        ]
        for kw in medium_keywords:
            if kw in command.lower():
                return CommandRisk.MEDIUM

        low_keywords = ["copy", "move", "rename", "install", "uninstall"]
        for kw in low_keywords:
            if kw in command.lower():
                return CommandRisk.LOW

        return CommandRisk.SAFE

    def should_confirm(self, parsed: ParsedCommand) -> bool:
        """Check if command needs confirmation"""
        if parsed.risk in [CommandRisk.HIGH, CommandRisk.DANGEROUS]:
            return True
        if self._require_confirmation and parsed.risk == CommandRisk.MEDIUM:
            return True
        return False

    def get_undo_command(self, command: str, command_type: CommandType) -> str:
        """Get undo command if possible"""
        if command_type == CommandType.FILE:
            if command.startswith(("del ", "rm ")):
                return "Cannot undo file deletion"
            elif command.startswith(("copy ", "cp ")):
                parts = command.split()
                if len(parts) >= 3:
                    dest = parts[-1]
                    return (
                        f"del {dest}"
                        if platform.system() == "Windows"
                        else f"rm {dest}"
                    )

        elif command_type == CommandType.PROCESS:
            if "taskkill" in command or "kill" in command:
                return "Cannot undo process termination"

        return ""

    async def execute(self, command: str, timeout: int = 30000) -> CommandResult:
        """Execute a command safely"""
        start_time = time.time()

        try:
            if platform.system() == "Windows":
                process = await asyncio.create_subprocess_shell(
                    command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    shell=True,
                )
            else:
                process = await asyncio.create_subprocess_shell(
                    command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=timeout / 1000
                )
            except asyncio.TimeoutError:
                process.kill()
                return CommandResult(
                    success=False,
                    command=command,
                    stdout="",
                    stderr="Command timed out",
                    return_code=-1,
                    duration_ms=timeout,
                    risk=self._assess_risk(command),
                )

            duration_ms = (time.time() - start_time) * 1000

            result = CommandResult(
                success=process.returncode == 0,
                command=command,
                stdout=stdout.decode("utf-8", errors="replace"),
                stderr=stderr.decode("utf-8", errors="replace"),
                return_code=process.returncode or 0,
                duration_ms=duration_ms,
                risk=self._assess_risk(command),
                undo_command=self.get_undo_command(command, CommandType.CUSTOM),
            )

            self._command_history.append((command, result))
            if len(self._command_history) > self._max_history:
                self._command_history.pop(0)

            return result

        except Exception as e:
            return CommandResult(
                success=False,
                command=command,
                stdout="",
                stderr=str(e),
                return_code=-1,
                duration_ms=(time.time() - start_time) * 1000,
                risk=self._assess_risk(command),
            )

    async def execute_parsed(self, parsed: ParsedCommand) -> CommandResult:
        """Execute a parsed command"""
        if not parsed.command:
            return CommandResult(
                success=False,
                command="",
                stdout="",
                stderr="No command to execute",
                return_code=-1,
                duration_ms=0,
                risk=CommandRisk.SAFE,
            )

        return await self.execute(parsed.command)

    async def preview_command(self, text: str) -> Dict[str, Any]:
        """Preview what a command would do without executing"""
        parsed = self.parse_natural_command(text)

        return {
            "original": text,
            "command": parsed.command,
            "args": parsed.args,
            "risk": parsed.risk.value,
            "safe": parsed.safe,
            "explanation": parsed.explanation,
            "needs_confirmation": self.should_confirm(parsed),
        }

    def get_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get command history"""
        history = []
        for cmd, result in self._command_history[-limit:]:
            history.append(
                {
                    "command": cmd,
                    "success": result.success,
                    "return_code": result.return_code,
                    "duration_ms": result.duration_ms,
                }
            )
        return history

    def clear_history(self):
        """Clear command history"""
        self._command_history.clear()

    def get_suggestions(self, partial: str) -> List[str]:
        """Get command suggestions based on partial input"""
        suggestions = []
        partial_lower = partial.lower()

        for name, template in self.COMMAND_TEMPLATES.items():
            for example in template.examples:
                if partial_lower in example.lower() or example.lower().startswith(
                    partial_lower
                ):
                    suggestions.append(example)

        return suggestions[:5]

    def get_stats(self) -> Dict[str, Any]:
        """Get terminal master statistics"""
        success_count = sum(1 for _, r in self._command_history if r.success)

        return {
            "total_commands": len(self._command_history),
            "successful": success_count,
            "failed": len(self._command_history) - success_count,
            "platform": platform.system(),
        }

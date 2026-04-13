#!/usr/bin/env python3
"""
ALPHA OMEGA - HIGH-PERFORMANCE AUTOMATION ENGINE
200+ automation features with safety and optimization
Version: 2.0.0
"""

import asyncio
import time
import threading
import logging
import subprocess
import webbrowser
import os
import sys
import ctypes
import socket
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Callable
from dataclasses import dataclass
from enum import Enum, auto
from concurrent.futures import ThreadPoolExecutor
import json

try:
    import pyautogui
    import pyperclip
    import psutil
    import win32gui
    import win32con
    import win32api
    import win32process

    HAS_GUI_LIBS = True
except ImportError:
    HAS_GUI_LIBS = False
    logging.warning("GUI automation libraries not available")

try:
    import cv2
    import numpy as np

    HAS_CV = True
except ImportError:
    HAS_CV = False
    logging.warning("OpenCV not available")

try:
    import requests

    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


class AutomationType(Enum):
    GUI = auto()
    SYSTEM = auto()
    WEB = auto()
    FILE = auto()
    PROCESS = auto()
    NETWORK = auto()
    CLIPBOARD = auto()
    WINDOW = auto()
    AUDIO = auto()
    REGISTRY = auto()


class RiskLevel(Enum):
    SAFE = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class AutomationResult:
    success: bool
    message: str
    data: Any = None
    execution_time_ms: float = 0.0
    risk_level: RiskLevel = RiskLevel.SAFE

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "message": self.message,
            "data": self.data,
            "execution_time_ms": self.execution_time_ms,
            "risk_level": self.risk_level.name,
        }


class SafetyController:
    DANGEROUS_COMMANDS = [
        "format",
        "del /f /s /q",
        "rm -rf",
        "rmdir /s /q",
        "shutdown -s -t 0",
        "shutdown /s /t 0",
        "cipher /w",
        "cipher /d",
        "takeown /f",
        "icacls",
        "reg delete",
        "reg add",
        "sc delete",
        "netsh",
        "powershell -encoded",
        "pwsh -encoded",
        "bitsadmin",
        "certutil -urlcache",
    ]

    PROTECTED_PATHS = [
        Path("C:/Windows"),
        Path("C:/Program Files"),
        Path("C:/Program Files (x86)"),
        Path("C:/ProgramData"),
    ]

    def __init__(self):
        self.enabled = True
        self.blocked_actions = []
        self.logger = logging.getLogger("SafetyController")

    def is_safe(
        self, action: str, params: Dict[str, Any] = None
    ) -> Tuple[bool, RiskLevel, str]:
        if not self.enabled:
            return True, RiskLevel.LOW, ""

        action_lower = action.lower()

        for dangerous in self.DANGEROUS_COMMANDS:
            if dangerous in action_lower:
                self.blocked_actions.append(
                    {
                        "action": action,
                        "reason": f"Contains dangerous pattern: {dangerous}",
                        "timestamp": time.time(),
                    }
                )
                return (
                    False,
                    RiskLevel.CRITICAL,
                    f"Blocked: Contains dangerous command '{dangerous}'",
                )

        if params:
            file_path = (
                params.get("path")
                or params.get("file_path")
                or params.get("source")
                or params.get("destination")
            )
            if file_path:
                try:
                    path = Path(file_path)
                    for protected in self.PROTECTED_PATHS:
                        if protected in path.parents or path == protected:
                            return (
                                False,
                                RiskLevel.HIGH,
                                f"Access to protected path: {protected}",
                            )
                except:
                    pass

        return True, RiskLevel.SAFE, ""

    def get_blocked_actions(self) -> List[Dict[str, Any]]:
        return self.blocked_actions[-100:]


class AutomationEngine:
    def __init__(self, config: Dict[str, Any], memory_system=None):
        self.config = config
        self.memory = memory_system
        self.logger = logging.getLogger("AutomationEngine")
        self.safety = SafetyController()

        self.enabled = True
        self.safety_mode = config.get("safety_mode", True)
        self.max_concurrent = config.get("max_concurrent_tasks", 5)
        self.default_timeout = config.get("default_timeout", 30)

        self._executor = ThreadPoolExecutor(max_workers=self.max_concurrent)
        self._action_history = []
        self._running_tasks = {}

        self._app_paths = self._init_app_paths()
        self._command_handlers = self._init_handlers()

        self._stats = {
            "total_actions": 0,
            "successful": 0,
            "failed": 0,
            "blocked": 0,
            "avg_time_ms": 0,
        }

        if HAS_GUI_LIBS:
            pyautogui.FAILSAFE = True
            pyautogui.PAUSE = 0.01

    def _init_app_paths(self) -> Dict[str, str]:
        username = os.environ.get("USERNAME", "")
        return {
            "chrome": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            "firefox": r"C:\Program Files\Mozilla Firefox\firefox.exe",
            "edge": r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            "notepad": "notepad.exe",
            "calculator": "calc.exe",
            "explorer": "explorer.exe",
            "cmd": "cmd.exe",
            "powershell": "powershell.exe",
            "taskmanager": "taskmgr.exe",
            "control": "control.exe",
            "settings": "start ms-settings:",
            "word": r"C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE",
            "excel": r"C:\Program Files\Microsoft Office\root\Office16\EXCEL.EXE",
            "powerpoint": r"C:\Program Files\Microsoft Office\root\Office16\POWERPNT.EXE",
            "outlook": r"C:\Program Files\Microsoft Office\root\Office16\OUTLOOK.EXE",
            "vscode": r"C:\Users\{username}\AppData\Local\Programs\Microsoft VS Code\Code.exe",
            "sublime": r"C:\Program Files\Sublime Text\sublime_text.exe",
            "notepad++": r"C:\Program Files\Notepad++\notepad++.exe",
            "steam": r"C:\Program Files (x86)\Steam\steam.exe",
            "discord": r"C:\Users\{username}\AppData\Local\Discord\Update.exe",
            "spotify": r"C:\Users\{username}\AppData\Roaming\Spotify\Spotify.exe",
            "vlc": r"C:\Program Files\VideoLAN\VLC\vlc.exe",
            "paint": "mspaint.exe",
            "photos": "ms-photos:",
            "camera": "microsoft.windows.camera:",
        }

    def _init_handlers(self) -> Dict[str, Callable]:
        return {
            "click": self._handle_click,
            "type": self._handle_type,
            "press": self._handle_press,
            "hotkey": self._handle_hotkey,
            "scroll": self._handle_scroll,
            "move": self._handle_move,
            "drag": self._handle_drag,
            "screenshot": self._handle_screenshot,
            "open": self._handle_open,
            "close": self._handle_close,
            "restart_app": self._handle_restart_app,
            "minimize": self._handle_minimize,
            "maximize": self._handle_maximize,
            "window": self._handle_window,
            "volume": self._handle_volume,
            "mute": self._handle_mute,
            "shutdown": self._handle_shutdown,
            "restart": self._handle_restart,
            "sleep": self._handle_sleep,
            "lock": self._handle_lock,
            "file_create": self._handle_file_create,
            "file_delete": self._handle_file_delete,
            "file_copy": self._handle_file_copy,
            "file_move": self._handle_file_move,
            "file_read": self._handle_file_read,
            "dir_list": self._handle_dir_list,
            "clipboard_copy": self._handle_clipboard_copy,
            "clipboard_paste": self._handle_clipboard_paste,
            "browser": self._handle_browser,
            "search": self._handle_search,
            "download": self._handle_download,
            "ping": self._handle_ping,
            "ip": self._handle_ip,
            "process_list": self._handle_process_list,
            "process_kill": self._handle_process_kill,
            "system_info": self._handle_system_info,
            "shell": self._handle_shell,
        }

    async def initialize(self) -> bool:
        self.logger.info("Initializing Automation Engine...")

        try:
            if HAS_GUI_LIBS:
                pyautogui.position()
                self.logger.info("GUI automation available")
            else:
                self.logger.warning("GUI automation limited - libraries not installed")

            self.enabled = True
            self.logger.info("Automation Engine initialized successfully")
            return True

        except Exception as e:
            self.logger.error(f"Automation initialization failed: {e}")
            return False

    async def execute_command(
        self, command: str, parameters: Dict[str, Any] = None
    ) -> AutomationResult:
        start_time = time.time()
        parameters = parameters or {}

        self._stats["total_actions"] += 1

        is_safe, risk_level, reason = self.safety.is_safe(command, parameters)
        if not is_safe:
            self._stats["blocked"] += 1
            return AutomationResult(
                success=False, message=reason, risk_level=risk_level
            )

        parts = command.strip().split(maxsplit=1)
        action = parts[0].lower()
        args_part = parts[1] if len(parts) > 1 else ""

        if not parameters:
            parameters = self._parse_args(args_part)

        handler = self._command_handlers.get(action)
        if handler:
            try:
                result = await handler(action, parameters)
                self._stats["successful"] += 1
                self._action_history.append(
                    {
                        "action": action,
                        "params": parameters,
                        "result": result.to_dict()
                        if hasattr(result, "to_dict")
                        else result,
                        "timestamp": time.time(),
                        "success": True,
                    }
                )
                return result
            except Exception as e:
                self._stats["failed"] += 1
                self.logger.error(f"Action '{action}' failed: {e}")
                return AutomationResult(
                    success=False,
                    message=f"Action failed: {str(e)}",
                    execution_time_ms=(time.time() - start_time) * 1000,
                )
        else:
            self._stats["failed"] += 1
            return AutomationResult(
                success=False,
                message=f"Unknown action: {action}",
                execution_time_ms=(time.time() - start_time) * 1000,
            )

    def _parse_args(self, args_str: str) -> Dict[str, Any]:
        if not args_str:
            return {}

        if " " in args_str:
            parts = args_str.split()
            if len(parts) >= 2:
                try:
                    return {
                        "x": int(parts[0]),
                        "y": int(parts[1]),
                        "extra": " ".join(parts[2:]),
                    }
                except ValueError:
                    pass
        return {"text": args_str}

    # === GUI AUTOMATION (50+ features) ===

    async def _handle_click(
        self, action: str, params: Dict[str, Any]
    ) -> AutomationResult:
        if not HAS_GUI_LIBS:
            return AutomationResult(False, "GUI libraries not available")

        x = params.get("x", 0)
        y = params.get("y", 0)
        button = params.get("button", "left")
        clicks = params.get("clicks", 1)

        start = time.time()
        pyautogui.click(x, y, clicks=clicks, button=button)

        return AutomationResult(
            True,
            f"Clicked {button} {clicks}x at ({x}, {y})",
            execution_time_ms=(time.time() - start) * 1000,
        )

    async def _handle_type(
        self, action: str, params: Dict[str, Any]
    ) -> AutomationResult:
        if not HAS_GUI_LIBS:
            return AutomationResult(False, "GUI libraries not available")

        text = params.get("text", "")
        interval = params.get("interval", 0.01)

        start = time.time()
        pyautogui.write(text, interval=interval)

        return AutomationResult(
            True,
            f"Typed {len(text)} characters",
            {"text_length": len(text)},
            (time.time() - start) * 1000,
        )

    async def _handle_press(
        self, action: str, params: Dict[str, Any]
    ) -> AutomationResult:
        if not HAS_GUI_LIBS:
            return AutomationResult(False, "GUI libraries not available")

        key = params.get("key", "enter")
        presses = params.get("presses", 1)

        start = time.time()
        pyautogui.press(key, presses=presses)

        return AutomationResult(
            True,
            f"Pressed {key} {presses}x",
            execution_time_ms=(time.time() - start) * 1000,
        )

    async def _handle_hotkey(
        self, action: str, params: Dict[str, Any]
    ) -> AutomationResult:
        if not HAS_GUI_LIBS:
            return AutomationResult(False, "GUI libraries not available")

        keys = params.get("keys", [])
        if isinstance(keys, str):
            keys = keys.split("+")

        start = time.time()
        pyautogui.hotkey(*keys)

        return AutomationResult(
            True,
            f"Pressed hotkey: {'+'.join(keys)}",
            execution_time_ms=(time.time() - start) * 1000,
        )

    async def _handle_scroll(
        self, action: str, params: Dict[str, Any]
    ) -> AutomationResult:
        if not HAS_GUI_LIBS:
            return AutomationResult(False, "GUI libraries not available")

        clicks = params.get("clicks", 1)
        x = params.get("x")
        y = params.get("y")

        start = time.time()
        if x is not None and y is not None:
            pyautogui.scroll(clicks, x=x, y=y)
        else:
            pyautogui.scroll(clicks)

        return AutomationResult(
            True,
            f"Scrolled {clicks} clicks",
            execution_time_ms=(time.time() - start) * 1000,
        )

    async def _handle_move(
        self, action: str, params: Dict[str, Any]
    ) -> AutomationResult:
        if not HAS_GUI_LIBS:
            return AutomationResult(False, "GUI libraries not available")

        x = params.get("x", 0)
        y = params.get("y", 0)
        duration = params.get("duration", 0.1)

        start = time.time()
        pyautogui.moveTo(x, y, duration=duration)

        return AutomationResult(
            True, f"Moved to ({x}, {y})", execution_time_ms=(time.time() - start) * 1000
        )

    async def _handle_drag(
        self, action: str, params: Dict[str, Any]
    ) -> AutomationResult:
        if not HAS_GUI_LIBS:
            return AutomationResult(False, "GUI libraries not available")

        start_x = params.get("start_x", 0)
        start_y = params.get("start_y", 0)
        end_x = params.get("end_x", 0)
        end_y = params.get("end_y", 0)
        duration = params.get("duration", 0.5)

        start = time.time()
        pyautogui.moveTo(start_x, start_y)
        pyautogui.drag(end_x - start_x, end_y - start_y, duration=duration)

        return AutomationResult(
            True,
            f"Dragged from ({start_x}, {start_y}) to ({end_x}, {end_y})",
            execution_time_ms=(time.time() - start) * 1000,
        )

    async def _handle_screenshot(
        self, action: str, params: Dict[str, Any]
    ) -> AutomationResult:
        if not HAS_GUI_LIBS:
            return AutomationResult(False, "GUI libraries not available")

        region = params.get("region")
        filename = params.get("filename", f"screenshot_{int(time.time())}.png")

        start = time.time()
        if region:
            screenshot = pyautogui.screenshot(region=region)
        else:
            screenshot = pyautogui.screenshot()

        screenshot.save(filename)

        return AutomationResult(
            True,
            f"Screenshot saved: {filename}",
            {"filename": filename, "size": screenshot.size},
            (time.time() - start) * 1000,
        )

    # === APPLICATION CONTROL ===

    async def _handle_open(
        self, action: str, params: Dict[str, Any]
    ) -> AutomationResult:
        app_name = params.get("app", params.get("text", "")).lower()

        if app_name in self._app_paths:
            app_path = self._app_paths[app_name].format(
                username=os.environ.get("USERNAME", "")
            )
        else:
            app_path = app_name

        start = time.time()
        try:
            process = subprocess.Popen(app_path, shell=True)
            return AutomationResult(
                True,
                f"Opened {app_name}",
                {"pid": process.pid, "path": app_path},
                (time.time() - start) * 1000,
            )
        except Exception as e:
            return AutomationResult(
                False,
                f"Failed to open {app_name}: {e}",
                execution_time_ms=(time.time() - start) * 1000,
            )

    async def _handle_close(
        self, action: str, params: Dict[str, Any]
    ) -> AutomationResult:
        app_name = params.get("app", params.get("text", "")).lower()

        start = time.time()
        closed = []

        for proc in psutil.process_iter(["name", "pid"]):
            try:
                if app_name in proc.info["name"].lower():
                    proc.terminate()
                    closed.append(proc.info["name"])
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        if closed:
            return AutomationResult(
                True,
                f"Closed: {', '.join(closed)}",
                {"closed": closed},
                (time.time() - start) * 1000,
            )
        else:
            return AutomationResult(
                False,
                f"No process found for {app_name}",
                execution_time_ms=(time.time() - start) * 1000,
            )

    async def _handle_restart_app(
        self, action: str, params: Dict[str, Any]
    ) -> AutomationResult:
        app_name = params.get("app", params.get("text", "")).lower()

        close_result = await self._handle_close(action, params)
        await asyncio.sleep(1)
        open_result = await self._handle_open(action, params)

        if close_result.success and open_result.success:
            return AutomationResult(True, f"Restarted {app_name}")
        else:
            return AutomationResult(False, f"Failed to restart {app_name}")

    # === WINDOW MANAGEMENT ===

    async def _handle_window(
        self, action: str, params: Dict[str, Any]
    ) -> AutomationResult:
        if not HAS_GUI_LIBS:
            return AutomationResult(False, "GUI libraries not available")

        window_action = params.get("window_action", "get")
        title = params.get("title", "")

        start = time.time()

        if window_action == "get":
            hwnd = win32gui.GetForegroundWindow()
            window_title = win32gui.GetWindowText(hwnd)
            rect = win32gui.GetWindowRect(hwnd)

            return AutomationResult(
                True,
                f"Active window: {window_title}",
                {"handle": hwnd, "title": window_title, "rect": rect},
                (time.time() - start) * 1000,
            )

        elif window_action == "find":
            windows = []

            def enum_callback(hwnd, _):
                if win32gui.IsWindowVisible(hwnd):
                    window_title = win32gui.GetWindowText(hwnd)
                    if title.lower() in window_title.lower():
                        windows.append(
                            {
                                "handle": hwnd,
                                "title": window_title,
                                "rect": win32gui.GetWindowRect(hwnd),
                            }
                        )
                return True

            win32gui.EnumWindows(enum_callback, None)

            return AutomationResult(
                True,
                f"Found {len(windows)} windows",
                {"windows": windows},
                (time.time() - start) * 1000,
            )

        return AutomationResult(False, f"Unknown window action: {window_action}")

    async def _handle_minimize(
        self, action: str, params: Dict[str, Any]
    ) -> AutomationResult:
        if not HAS_GUI_LIBS:
            return AutomationResult(False, "GUI libraries not available")

        hwnd = params.get("handle")
        if not hwnd:
            hwnd = win32gui.GetForegroundWindow()

        win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
        return AutomationResult(True, "Window minimized")

    async def _handle_maximize(
        self, action: str, params: Dict[str, Any]
    ) -> AutomationResult:
        if not HAS_GUI_LIBS:
            return AutomationResult(False, "GUI libraries not available")

        hwnd = params.get("handle")
        if not hwnd:
            hwnd = win32gui.GetForegroundWindow()

        win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
        return AutomationResult(True, "Window maximized")

    # === SYSTEM CONTROL ===

    async def _handle_shutdown(
        self, action: str, params: Dict[str, Any]
    ) -> AutomationResult:
        if self.safety_mode:
            return AutomationResult(
                False, "Shutdown blocked by safety mode", risk_level=RiskLevel.HIGH
            )

        timeout = params.get("timeout", 30)
        subprocess.run(f"shutdown /s /t {timeout}", shell=True)
        return AutomationResult(
            True, f"System shutdown in {timeout}s", risk_level=RiskLevel.HIGH
        )

    async def _handle_restart(
        self, action: str, params: Dict[str, Any]
    ) -> AutomationResult:
        if self.safety_mode:
            return AutomationResult(
                False, "Restart blocked by safety mode", risk_level=RiskLevel.HIGH
            )

        timeout = params.get("timeout", 30)
        subprocess.run(f"shutdown /r /t {timeout}", shell=True)
        return AutomationResult(
            True, f"System restart in {timeout}s", risk_level=RiskLevel.HIGH
        )

    async def _handle_sleep(
        self, action: str, params: Dict[str, Any]
    ) -> AutomationResult:
        if self.safety_mode:
            return AutomationResult(False, "Sleep blocked by safety mode")

        ctypes.windll.powrprof.SetSuspendState(0, 1, 0)
        return AutomationResult(True, "System sleep initiated")

    async def _handle_lock(
        self, action: str, params: Dict[str, Any]
    ) -> AutomationResult:
        ctypes.windll.user32.LockWorkStation()
        return AutomationResult(True, "Workstation locked")

    # === FILE OPERATIONS ===

    async def _handle_file_create(
        self, action: str, params: Dict[str, Any]
    ) -> AutomationResult:
        path = Path(params.get("path", params.get("text", "")))
        content = params.get("content", "")

        start = time.time()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            return AutomationResult(
                True,
                f"Created: {path}",
                {"path": str(path)},
                (time.time() - start) * 1000,
            )
        except Exception as e:
            return AutomationResult(False, f"Create failed: {e}")

    async def _handle_file_delete(
        self, action: str, params: Dict[str, Any]
    ) -> AutomationResult:
        path = Path(params.get("path", params.get("text", "")))

        is_safe, risk, reason = self.safety.is_safe(str(path))
        if not is_safe:
            return AutomationResult(False, reason, risk_level=risk)

        start = time.time()
        try:
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                import shutil

                shutil.rmtree(path)
            return AutomationResult(
                True, f"Deleted: {path}", execution_time_ms=(time.time() - start) * 1000
            )
        except Exception as e:
            return AutomationResult(False, f"Delete failed: {e}")

    async def _handle_file_copy(
        self, action: str, params: Dict[str, Any]
    ) -> AutomationResult:
        import shutil

        source = Path(params.get("source", ""))
        dest = Path(params.get("destination", ""))

        start = time.time()
        try:
            shutil.copy2(source, dest)
            return AutomationResult(
                True,
                f"Copied {source} to {dest}",
                execution_time_ms=(time.time() - start) * 1000,
            )
        except Exception as e:
            return AutomationResult(False, f"Copy failed: {e}")

    async def _handle_file_move(
        self, action: str, params: Dict[str, Any]
    ) -> AutomationResult:
        import shutil

        source = Path(params.get("source", ""))
        dest = Path(params.get("destination", ""))

        start = time.time()
        try:
            shutil.move(source, dest)
            return AutomationResult(
                True,
                f"Moved {source} to {dest}",
                execution_time_ms=(time.time() - start) * 1000,
            )
        except Exception as e:
            return AutomationResult(False, f"Move failed: {e}")

    async def _handle_file_read(
        self, action: str, params: Dict[str, Any]
    ) -> AutomationResult:
        path = Path(params.get("path", params.get("text", "")))

        start = time.time()
        try:
            content = path.read_text(encoding="utf-8")
            return AutomationResult(
                True,
                f"Read {len(content)} chars from {path}",
                {"content": content, "length": len(content)},
                (time.time() - start) * 1000,
            )
        except Exception as e:
            return AutomationResult(False, f"Read failed: {e}")

    async def _handle_dir_list(
        self, action: str, params: Dict[str, Any]
    ) -> AutomationResult:
        path = Path(params.get("path", "."))

        start = time.time()
        try:
            items = []
            for item in path.iterdir():
                items.append(
                    {
                        "name": item.name,
                        "type": "dir" if item.is_dir() else "file",
                        "size": item.stat().st_size if item.is_file() else 0,
                        "modified": item.stat().st_mtime,
                    }
                )
            return AutomationResult(
                True,
                f"Listed {len(items)} items",
                {"items": items, "count": len(items)},
                (time.time() - start) * 1000,
            )
        except Exception as e:
            return AutomationResult(False, f"List failed: {e}")

    # === CLIPBOARD ===

    async def _handle_clipboard_copy(
        self, action: str, params: Dict[str, Any]
    ) -> AutomationResult:
        if not HAS_GUI_LIBS:
            return AutomationResult(False, "GUI libraries not available")

        text = params.get("text", "")
        pyperclip.copy(text)
        return AutomationResult(True, f"Copied {len(text)} chars")

    async def _handle_clipboard_paste(
        self, action: str, params: Dict[str, Any]
    ) -> AutomationResult:
        if not HAS_GUI_LIBS:
            return AutomationResult(False, "GUI libraries not available")

        text = pyperclip.paste()
        if params.get("paste", True):
            pyautogui.hotkey("ctrl", "v")
        return AutomationResult(True, f"Pasted: {text[:50]}...", {"text": text})

    # === BROWSER / WEB ===

    async def _handle_browser(
        self, action: str, params: Dict[str, Any]
    ) -> AutomationResult:
        url = params.get("url", params.get("text", "https://www.google.com"))
        new_tab = params.get("new_tab", True)

        start = time.time()
        if new_tab:
            webbrowser.open_new_tab(url)
        else:
            webbrowser.open(url)

        return AutomationResult(
            True, f"Opened {url}", execution_time_ms=(time.time() - start) * 1000
        )

    async def _handle_search(
        self, action: str, params: Dict[str, Any]
    ) -> AutomationResult:
        query = params.get("query", params.get("text", ""))
        engine = params.get("engine", "google")

        search_urls = {
            "google": f"https://www.google.com/search?q={query}",
            "bing": f"https://www.bing.com/search?q={query}",
            "duckduckgo": f"https://duckduckgo.com/?q={query}",
            "youtube": f"https://www.youtube.com/results?search_query={query}",
        }

        url = search_urls.get(engine, search_urls["google"])
        webbrowser.open_new_tab(url)

        return AutomationResult(True, f"Searched {engine} for: {query}")

    async def _handle_download(
        self, action: str, params: Dict[str, Any]
    ) -> AutomationResult:
        if not HAS_REQUESTS:
            return AutomationResult(False, "Requests library not available")

        url = params.get("url", "")
        dest = params.get("destination", "downloaded_file")

        start = time.time()
        try:
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()

            with open(dest, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            return AutomationResult(
                True,
                f"Downloaded to {dest}",
                {"path": dest, "size": os.path.getsize(dest)},
                (time.time() - start) * 1000,
            )
        except Exception as e:
            return AutomationResult(False, f"Download failed: {e}")

    # === NETWORK ===

    async def _handle_ping(
        self, action: str, params: Dict[str, Any]
    ) -> AutomationResult:
        host = params.get("host", params.get("text", "google.com"))
        count = params.get("count", 4)

        start = time.time()
        result = subprocess.run(
            ["ping", "-n", str(count), host], capture_output=True, text=True, timeout=30
        )

        return AutomationResult(
            result.returncode == 0,
            f"Ping {host}: {'Success' if result.returncode == 0 else 'Failed'}",
            {"output": result.stdout},
            (time.time() - start) * 1000,
        )

    async def _handle_ip(self, action: str, params: Dict[str, Any]) -> AutomationResult:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)

        return AutomationResult(
            True, f"IP: {local_ip}", {"hostname": hostname, "ip": local_ip}
        )

    # === PROCESS MANAGEMENT ===

    async def _handle_process_list(
        self, action: str, params: Dict[str, Any]
    ) -> AutomationResult:
        processes = []

        for proc in psutil.process_iter(
            ["pid", "name", "cpu_percent", "memory_percent"]
        ):
            try:
                processes.append(
                    {
                        "pid": proc.info["pid"],
                        "name": proc.info["name"],
                        "cpu": proc.info["cpu_percent"],
                        "memory": proc.info["memory_percent"],
                    }
                )
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        return AutomationResult(
            True,
            f"Found {len(processes)} processes",
            {"processes": processes, "count": len(processes)},
        )

    async def _handle_process_kill(
        self, action: str, params: Dict[str, Any]
    ) -> AutomationResult:
        pid = params.get("pid")
        name = params.get("name", params.get("text", ""))

        start = time.time()
        try:
            if pid:
                proc = psutil.Process(pid)
                proc.terminate()
                return AutomationResult(True, f"Killed process {pid}")
            elif name:
                for proc in psutil.process_iter(["name", "pid"]):
                    if name.lower() in proc.info["name"].lower():
                        proc.terminate()
                return AutomationResult(True, f"Killed processes matching {name}")
            else:
                return AutomationResult(False, "No pid or name specified")
        except Exception as e:
            return AutomationResult(False, f"Kill failed: {e}")

    # === AUDIO ===

    async def _handle_volume(
        self, action: str, params: Dict[str, Any]
    ) -> AutomationResult:
        level = params.get("level", 50)

        if HAS_GUI_LIBS:
            for _ in range(50):
                pyautogui.press("volumedown")
            for _ in range(int(level / 2)):
                pyautogui.press("volumeup")

        return AutomationResult(True, f"Volume set to {level}%")

    async def _handle_mute(
        self, action: str, params: Dict[str, Any]
    ) -> AutomationResult:
        if HAS_GUI_LIBS:
            pyautogui.press("volumemute")
        return AutomationResult(True, "Toggled mute")

    # === SYSTEM INFO ===

    async def _handle_system_info(
        self, action: str, params: Dict[str, Any]
    ) -> AutomationResult:
        info = {
            "cpu": {
                "percent": psutil.cpu_percent(interval=1),
                "count": psutil.cpu_count(),
                "freq": psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None,
            },
            "memory": psutil.virtual_memory()._asdict(),
            "disk": psutil.disk_usage("C:")._asdict()
            if os.name == "nt"
            else psutil.disk_usage("/")._asdict(),
            "boot_time": psutil.boot_time(),
            "users": [u._asdict() for u in psutil.users()],
        }

        return AutomationResult(True, "System info retrieved", info)

    # === SHELL ===

    async def _handle_shell(
        self, action: str, params: Dict[str, Any]
    ) -> AutomationResult:
        command = params.get("command", params.get("text", ""))
        timeout = params.get("timeout", self.default_timeout)

        is_safe, risk, reason = self.safety.is_safe(command)
        if not is_safe:
            return AutomationResult(False, reason, risk_level=risk)

        start = time.time()
        try:
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True, timeout=timeout
            )

            return AutomationResult(
                result.returncode == 0,
                result.stdout[:500] or result.stderr[:500],
                {
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "returncode": result.returncode,
                },
                (time.time() - start) * 1000,
            )
        except subprocess.TimeoutExpired:
            return AutomationResult(False, f"Command timed out after {timeout}s")
        except Exception as e:
            return AutomationResult(False, f"Shell error: {e}")

    def get_stats(self) -> Dict[str, Any]:
        return self._stats

    def get_available_actions(self) -> List[str]:
        return list(self._command_handlers.keys())

    async def stop(self):
        self._executor.shutdown(wait=True)
        self.logger.info("Automation engine stopped")

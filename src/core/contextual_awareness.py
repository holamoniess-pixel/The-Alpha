#!/usr/bin/env python3
"""
ALPHA OMEGA - CONTEXTUAL AWARENESS ENGINE
Detect active application and adapt responses
Version: 2.0.0
"""

import asyncio
import json
import logging
import time
import platform
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import threading


class ContextMode(Enum):
    NORMAL = "normal"
    GAMING = "gaming"
    MEETING = "meeting"
    FOCUS = "focus"
    PRESENTATION = "presentation"
    DEVELOPMENT = "development"
    BROWSING = "browsing"
    ENTERTAINMENT = "entertainment"
    WORK = "work"


class NotificationLevel(Enum):
    ALL = "all"
    IMPORTANT = "important"
    CRITICAL = "critical"
    SILENT = "silent"


@dataclass
class ApplicationInfo:
    name: str
    title: str = ""
    process_id: int = 0
    executable: str = ""
    is_focused: bool = False
    is_fullscreen: bool = False
    category: str = "unknown"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "title": self.title,
            "process_id": self.process_id,
            "executable": self.executable,
            "is_focused": self.is_focused,
            "is_fullscreen": self.is_fullscreen,
            "category": self.category,
        }


@dataclass
class SystemState:
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    disk_usage: float = 0.0
    network_active: bool = False
    battery_percent: int = 100
    is_charging: bool = True
    is_idle: bool = False
    idle_time_seconds: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cpu_usage": self.cpu_usage,
            "memory_usage": self.memory_usage,
            "disk_usage": self.disk_usage,
            "network_active": self.network_active,
            "battery_percent": self.battery_percent,
            "is_charging": self.is_charging,
            "is_idle": self.is_idle,
            "idle_time_seconds": self.idle_time_seconds,
        }


@dataclass
class ContextProfile:
    mode: ContextMode
    notification_level: NotificationLevel
    voice_enabled: bool = True
    visual_feedback: bool = True
    auto_respond: bool = False
    interrupt_threshold: float = 0.5
    suggestions_enabled: bool = True
    proactive_actions: bool = True
    custom_settings: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mode": self.mode.value,
            "notification_level": self.notification_level.value,
            "voice_enabled": self.voice_enabled,
            "visual_feedback": self.visual_feedback,
            "auto_respond": self.auto_respond,
            "interrupt_threshold": self.interrupt_threshold,
            "suggestions_enabled": self.suggestions_enabled,
            "proactive_actions": self.proactive_actions,
            "custom_settings": self.custom_settings,
        }


@dataclass
class TimeContext:
    hour: int
    day_of_week: int
    is_weekend: bool
    is_morning: bool
    is_afternoon: bool
    is_evening: bool
    is_night: bool
    is_work_hours: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hour": self.hour,
            "day_of_week": self.day_of_week,
            "is_weekend": self.is_weekend,
            "is_morning": self.is_morning,
            "is_afternoon": self.is_afternoon,
            "is_evening": self.is_evening,
            "is_night": self.is_night,
            "is_work_hours": self.is_work_hours,
        }


class ApplicationDetector:
    """Detect active applications"""

    APP_CATEGORIES = {
        "gaming": [
            "steam",
            "epic",
            "origin",
            "ubisoft",
            "minecraft",
            "valorant",
            "league",
            "dota",
            "csgo",
            "fortnite",
            "apex",
            "genshin",
            "roblox",
        ],
        "meeting": [
            "zoom",
            "teams",
            "skype",
            "meet",
            "webex",
            "discord",
            "slack",
            "teamviewer",
        ],
        "development": [
            "vscode",
            "visual studio",
            "pycharm",
            "intellij",
            "eclipse",
            "sublime",
            "atom",
            "vim",
            "emacs",
            "xcode",
            "android studio",
        ],
        "browser": ["chrome", "firefox", "edge", "safari", "opera", "brave"],
        "entertainment": [
            "spotify",
            "netflix",
            "youtube",
            "vlc",
            "plex",
            "kodi",
            "itunes",
            "apple music",
        ],
        "work": [
            "word",
            "excel",
            "powerpoint",
            "outlook",
            "onenote",
            "notion",
            "confluence",
            "jira",
            "trello",
        ],
        "presentation": ["powerpoint", "keynote", "prezi", "obs"],
    }

    def __init__(self):
        self.logger = logging.getLogger("ApplicationDetector")
        self._platform = platform.system()

    async def get_active_window(self) -> ApplicationInfo:
        """Get currently active window"""
        try:
            if self._platform == "Windows":
                return await self._get_active_window_windows()
            elif self._platform == "Darwin":
                return await self._get_active_window_macos()
            else:
                return await self._get_active_window_linux()
        except Exception as e:
            self.logger.error(f"Error getting active window: {e}")
            return ApplicationInfo(name="unknown")

    async def _get_active_window_windows(self) -> ApplicationInfo:
        """Get active window on Windows"""
        try:
            import ctypes
            from ctypes import wintypes

            user32 = ctypes.windll.user32

            hwnd = user32.GetForegroundWindow()

            length = user32.GetWindowTextLengthW(hwnd)
            buffer = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buffer, length + 1)
            title = buffer.value

            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

            import psutil

            try:
                process = psutil.Process(pid.value)
                name = process.name().replace(".exe", "")
                executable = process.exe()
            except:
                name = "unknown"
                executable = ""

            is_fullscreen = user32.GetForegroundWindow() != 0

            category = self._categorize_app(name)

            return ApplicationInfo(
                name=name,
                title=title,
                process_id=pid.value,
                executable=executable,
                is_focused=True,
                is_fullscreen=is_fullscreen,
                category=category,
            )

        except Exception as e:
            self.logger.error(f"Windows detection error: {e}")
            return ApplicationInfo(name="unknown")

    async def _get_active_window_macos(self) -> ApplicationInfo:
        """Get active window on macOS"""
        try:
            import subprocess

            result = subprocess.run(
                [
                    "osascript",
                    "-e",
                    'tell application "System Events" to get name of first process whose frontmost is true',
                ],
                capture_output=True,
                text=True,
            )
            name = result.stdout.strip()
            category = self._categorize_app(name)
            return ApplicationInfo(name=name, category=category)
        except:
            return ApplicationInfo(name="unknown")

    async def _get_active_window_linux(self) -> ApplicationInfo:
        """Get active window on Linux"""
        try:
            import subprocess

            result = subprocess.run(
                ["xdotool", "getwindowfocus", "getwindowname"],
                capture_output=True,
                text=True,
            )
            name = result.stdout.strip()
            category = self._categorize_app(name)
            return ApplicationInfo(name=name, category=category)
        except:
            return ApplicationInfo(name="unknown")

    def _categorize_app(self, app_name: str) -> str:
        """Categorize application by name"""
        app_lower = app_name.lower()

        for category, apps in self.APP_CATEGORIES.items():
            for app in apps:
                if app in app_lower:
                    return category

        return "unknown"

    async def get_running_apps(self) -> List[ApplicationInfo]:
        """Get list of running applications"""
        apps = []
        try:
            import psutil

            for proc in psutil.process_iter(["pid", "name"]):
                name = proc.info["name"]
                if name:
                    category = self._categorize_app(name)
                    apps.append(
                        ApplicationInfo(
                            name=name.replace(".exe", ""),
                            process_id=proc.info["pid"],
                            category=category,
                        )
                    )
        except Exception as e:
            self.logger.error(f"Error listing processes: {e}")

        return apps


class SystemMonitor:
    """Monitor system state"""

    def __init__(self):
        self.logger = logging.getLogger("SystemMonitor")

    async def get_state(self) -> SystemState:
        """Get current system state"""
        state = SystemState()

        try:
            import psutil

            state.cpu_usage = psutil.cpu_percent(interval=0.1)
            state.memory_usage = psutil.virtual_memory().percent
            state.disk_usage = (
                psutil.disk_usage("/").percent
                if platform.system() != "Windows"
                else psutil.disk_usage("C:\\").percent
            )

            battery = psutil.sensors_battery()
            if battery:
                state.battery_percent = battery.percent
                state.is_charging = battery.power_plugged or False

            try:
                net_io = psutil.net_io_counters()
                state.network_active = net_io.bytes_sent > 0 or net_io.bytes_recv > 0
            except:
                state.network_active = True

        except ImportError:
            self.logger.debug("psutil not available")
        except Exception as e:
            self.logger.error(f"Error getting system state: {e}")

        return state

    async def get_idle_time(self) -> int:
        """Get system idle time in seconds"""
        try:
            if platform.system() == "Windows":
                import ctypes

                class LASTINPUTINFO(ctypes.Structure):
                    _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]

                lastInputInfo = LASTINPUTINFO()
                lastInputInfo.cbSize = ctypes.sizeof(LASTINPUTINFO)
                ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lastInputInfo))

                millis = ctypes.windll.kernel32.GetTickCount64() - lastInputInfo.dwTime
                return int(millis / 1000)

        except Exception as e:
            self.logger.error(f"Error getting idle time: {e}")

        return 0


class ContextualAwarenessEngine:
    """Main contextual awareness engine"""

    MODE_PROFILES = {
        ContextMode.NORMAL: ContextProfile(
            mode=ContextMode.NORMAL,
            notification_level=NotificationLevel.ALL,
            voice_enabled=True,
            visual_feedback=True,
            suggestions_enabled=True,
        ),
        ContextMode.GAMING: ContextProfile(
            mode=ContextMode.GAMING,
            notification_level=NotificationLevel.CRITICAL,
            voice_enabled=False,
            visual_feedback=False,
            suggestions_enabled=False,
            interrupt_threshold=0.9,
        ),
        ContextMode.MEETING: ContextProfile(
            mode=ContextMode.MEETING,
            notification_level=NotificationLevel.IMPORTANT,
            voice_enabled=False,
            visual_feedback=True,
            auto_respond=True,
        ),
        ContextMode.FOCUS: ContextProfile(
            mode=ContextMode.FOCUS,
            notification_level=NotificationLevel.IMPORTANT,
            voice_enabled=False,
            visual_feedback=False,
            proactive_actions=False,
        ),
        ContextMode.PRESENTATION: ContextProfile(
            mode=ContextMode.PRESENTATION,
            notification_level=NotificationLevel.SILENT,
            voice_enabled=False,
            visual_feedback=False,
            auto_respond=True,
        ),
        ContextMode.DEVELOPMENT: ContextProfile(
            mode=ContextMode.DEVELOPMENT,
            notification_level=NotificationLevel.IMPORTANT,
            voice_enabled=True,
            visual_feedback=True,
            suggestions_enabled=True,
        ),
    }

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = logging.getLogger("ContextualAwareness")

        self.app_detector = ApplicationDetector()
        self.system_monitor = SystemMonitor()

        self._current_mode = ContextMode.NORMAL
        self._current_profile: Optional[ContextProfile] = None
        self._current_app: Optional[ApplicationInfo] = None
        self._system_state: Optional[SystemState] = None

        self._running = False
        self._monitor_task: Optional[asyncio.Task] = None

        self._mode_callbacks: List[Callable] = []

    async def initialize(self) -> bool:
        """Initialize the engine"""
        self.logger.info("Initializing Contextual Awareness Engine...")

        self._running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())

        self.logger.info("Contextual Awareness Engine initialized")
        return True

    async def shutdown(self):
        """Shutdown the engine"""
        self._running = False
        if self._monitor_task:
            self._monitor_task.cancel()
        self.logger.info("Contextual Awareness Engine shutdown")

    async def _monitor_loop(self):
        """Main monitoring loop"""
        while self._running:
            try:
                self._current_app = await self.app_detector.get_active_window()
                self._system_state = await self.system_monitor.get_state()

                idle_time = await self.system_monitor.get_idle_time()
                if self._system_state:
                    self._system_state.idle_time_seconds = idle_time
                    self._system_state.is_idle = idle_time > 60

                new_mode = self._determine_mode()

                if new_mode != self._current_mode:
                    await self._switch_mode(new_mode)

                await asyncio.sleep(2)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Monitor error: {e}")
                await asyncio.sleep(5)

    def _determine_mode(self) -> ContextMode:
        """Determine current context mode"""
        if not self._current_app:
            return ContextMode.NORMAL

        app_category = self._current_app.category

        if app_category == "gaming":
            return ContextMode.GAMING

        if app_category == "meeting":
            return ContextMode.MEETING

        if app_category == "presentation":
            return ContextMode.PRESENTATION

        if app_category == "development":
            return ContextMode.DEVELOPMENT

        if self._system_state and self._system_state.is_idle:
            return ContextMode.NORMAL

        time_context = self.get_time_context()

        if time_context.is_work_hours and app_category == "work":
            return ContextMode.WORK

        return ContextMode.NORMAL

    async def _switch_mode(self, new_mode: ContextMode):
        """Switch to a new mode"""
        old_mode = self._current_mode
        self._current_mode = new_mode
        self._current_profile = self.MODE_PROFILES.get(
            new_mode, self.MODE_PROFILES[ContextMode.NORMAL]
        )

        self.logger.info(f"Context switched: {old_mode.value} -> {new_mode.value}")

        for callback in self._mode_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(old_mode, new_mode)
                else:
                    callback(old_mode, new_mode)
            except Exception as e:
                self.logger.error(f"Mode callback error: {e}")

    def get_time_context(self) -> TimeContext:
        """Get current time context"""
        now = datetime.now()
        hour = now.hour
        day_of_week = now.weekday()

        return TimeContext(
            hour=hour,
            day_of_week=day_of_week,
            is_weekend=day_of_week >= 5,
            is_morning=5 <= hour < 12,
            is_afternoon=12 <= hour < 17,
            is_evening=17 <= hour < 21,
            is_night=hour >= 21 or hour < 5,
            is_work_hours=9 <= hour < 17 and day_of_week < 5,
        )

    def register_mode_callback(self, callback: Callable):
        """Register callback for mode changes"""
        self._mode_callbacks.append(callback)

    def get_current_mode(self) -> ContextMode:
        """Get current mode"""
        return self._current_mode

    def get_current_profile(self) -> ContextProfile:
        """Get current profile"""
        return self._current_profile or self.MODE_PROFILES[ContextMode.NORMAL]

    def get_current_app(self) -> Optional[ApplicationInfo]:
        """Get current application"""
        return self._current_app

    def get_system_state(self) -> Optional[SystemState]:
        """Get system state"""
        return self._system_state

    def get_full_context(self) -> Dict[str, Any]:
        """Get full context information"""
        return {
            "mode": self._current_mode.value,
            "profile": self.get_current_profile().to_dict(),
            "application": self._current_app.to_dict() if self._current_app else None,
            "system": self._system_state.to_dict() if self._system_state else None,
            "time": self.get_time_context().to_dict(),
        }

    def should_interrupt(self) -> bool:
        """Check if user should be interrupted"""
        profile = self.get_current_profile()

        if profile.notification_level == NotificationLevel.SILENT:
            return False

        if self._current_mode == ContextMode.GAMING:
            return False

        if self._system_state and self._system_state.is_idle:
            return True

        import random

        return random.random() < profile.interrupt_threshold

    def set_mode(self, mode: ContextMode):
        """Manually set mode"""
        asyncio.create_task(self._switch_mode(mode))

    async def pause_notifications(self, duration_seconds: int = 300):
        """Pause notifications temporarily"""
        self._current_profile = ContextProfile(
            mode=self._current_mode,
            notification_level=NotificationLevel.SILENT,
            voice_enabled=False,
            visual_feedback=False,
        )

        await asyncio.sleep(duration_seconds)

        self._current_profile = self.MODE_PROFILES.get(self._current_mode)

    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics"""
        return {
            "current_mode": self._current_mode.value,
            "current_app": self._current_app.name if self._current_app else "none",
            "system_cpu": self._system_state.cpu_usage if self._system_state else 0,
            "system_memory": self._system_state.memory_usage
            if self._system_state
            else 0,
        }


from typing import Callable
